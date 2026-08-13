import json
import logging
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config.repository import ConfigRepository
from app.config.schema import FundConfig
from app.document.docling_adapter import DoclingAdapter
from app.document.liteparse_adapter import LiteParseAdapter
from app.document.mistral_adapter import RemoteDocumentParser
from app.document.page_model import ParsedPage
from app.document.schedule_locator import ScheduleLocator
from app.domain.enums import JobStatus, ParserSource, ValidationStatus
from app.domain.models import (
    BoundingBox,
    HoldingRecord,
    ParseResult,
    ScheduleRange,
    ValidationResult,
)
from app.extraction.parser import HoldingParser
from app.storage.models import DocumentRow, HoldingRow, ParseJobRow, ValidationRow
from app.validation.validator import Validator, should_use_remote

logger = logging.getLogger(__name__)


class ImportService:
    def __init__(
        self,
        session: Session,
        remote_adapter: RemoteDocumentParser,
        local_adapter: LiteParseAdapter | None = None,
        docling_adapter: DoclingAdapter | None = None,
    ) -> None:
        self.session = session
        self.remote_adapter = remote_adapter
        self.local_adapter = local_adapter or LiteParseAdapter()
        self.docling_adapter = docling_adapter or DoclingAdapter(self.local_adapter)
        self.locator = ScheduleLocator()
        self.parser = HoldingParser()
        self.validator = Validator()

    def run(self, job_id: str) -> None:
        job = self._require_job(job_id)
        document = self.session.get(DocumentRow, job.document_id)
        if document is None:
            self._fail(job, "Document not found")
            return
        started = time.perf_counter()
        try:
            job.status = JobStatus.PROCESSING
            job.current_stage = "Scanning document locally"
            self.session.commit()
            configs = ConfigRepository(self.session).list()
            config = self._choose_config(Path(document.storage_path), configs, job.fund_id)
            if config is None:
                raise ValueError("No saved configuration matches this document")
            job.fund_id = config.fund_id
            job.config_version = config.version

            scan_pages = self.local_adapter.parse(Path(document.storage_path), layout=config.layout_hints)
            ranges = self.locator.locate(scan_pages, config)
            schedule = ranges[0] if ranges else None
            if schedule is None:
                extraction = self.parser.parse([], self._empty_schedule(config), config)
                validations = self.validator.validate(None, extraction)
                self._persist(job, config, None, extraction.holdings, validations, [])
                return

            page_numbers = list(range(schedule.start_page, schedule.end_page + 1))
            job.current_stage = "Structuring schedule pages with Docling"
            job.pages_processed = len(page_numbers)
            job.local_page_count = len(page_numbers)
            self.session.commit()
            structured = self.docling_adapter.parse_pages(Path(document.storage_path), page_numbers, config.layout_hints)
            extraction = self.parser.parse(structured, schedule, config, ParserSource.LOCAL)
            validations = self.validator.validate(
                schedule, extraction, Decimal(config.rules.reconciliation_tolerance)
            )
            remote_pages: list[int] = []
            attempted_remote_pages: list[int] = []
            if should_use_remote(validations) and config.fallback.enabled and self.remote_adapter.available:
                attempted_remote_pages = self._failed_pages(validations, page_numbers)
                job.current_stage = "Retrying failed pages with Mistral OCR"
                self.session.commit()
                try:
                    remote = self.remote_adapter.parse_pages(
                        Path(document.storage_path), attempted_remote_pages, document.id
                    )
                    if not remote:
                        raise RuntimeError("Remote parser returned no usable pages")
                    remote_pages = sorted({page.page_number for page in remote})
                    merged = self._replace_pages(structured, remote)
                    extraction = self.parser.parse(merged, schedule, config)
                    validations = self.validator.validate(
                        schedule, extraction, Decimal(config.rules.reconciliation_tolerance)
                    )
                except Exception as exc:
                    logger.warning(
                        "remote fallback unavailable after local parse",
                        extra={
                            "context": {
                                "job_id": job.id,
                                "document_id": document.id,
                                "pages": attempted_remote_pages,
                                "error_type": type(exc).__name__,
                            }
                        },
                    )
                    validations.append(
                        ValidationResult(
                            code="remote_fallback_failed",
                            severity="warning",
                            message=(
                                "Local extraction was preserved, but remote recovery failed. "
                                "Review the affected pages or retry later."
                            ),
                            page_number=(
                                attempted_remote_pages[0]
                                if attempted_remote_pages
                                else schedule.start_page
                            ),
                        )
                    )
            elif should_use_remote(validations) and (
                not config.fallback.enabled or not self.remote_adapter.available
            ):
                reason = (
                    "disabled by this fund configuration"
                    if not config.fallback.enabled
                    else "MISTRAL_API_KEY is not set"
                )
                validations.append(
                    ValidationResult(
                        code="remote_fallback_unavailable",
                        severity="warning",
                        message=(
                            f"Local validation found review items; remote fallback is {reason}. "
                            "Successful holdings were preserved."
                        ),
                        page_number=schedule.start_page,
                    )
                )
            self._mark_failed_pages_for_review(extraction.holdings, validations)
            self._persist(job, config, schedule, extraction.holdings, validations, remote_pages)
            logger.info(
                "import completed",
                extra={
                    "context": {
                        "job_id": job.id,
                        "document_id": document.id,
                        "fund_id": config.fund_id,
                        "config_version": config.version,
                        "schedule_page_range": [schedule.start_page, schedule.end_page],
                        "local_parse_duration": round(time.perf_counter() - started, 3),
                        "remote_pages_called": attempted_remote_pages,
                        "remote_pages_used": remote_pages,
                        "holding_count": len(extraction.holdings),
                        "validation_error_count": sum(v.severity == "error" for v in validations),
                    }
                },
            )
        except Exception as exc:
            logger.exception("import failed", extra={"context": {"job_id": job_id}})
            self._fail(job, str(exc))

    def result(self, job_id: str) -> ParseResult:
        job = self._require_job(job_id)
        holdings = [self._holding_model(row) for row in self.session.scalars(select(HoldingRow).where(HoldingRow.job_id == job_id)).all()]
        validations = [self._validation_model(row) for row in self.session.scalars(select(ValidationRow).where(ValidationRow.job_id == job_id)).all()]
        if not job.fund_name or not job.report_date or not job.config_version:
            raise ValueError("Job has no completed result")
        return ParseResult(
            fund_name=job.fund_name,
            report_date=job.report_date,
            holdings=holdings,
            validations=validations,
            pages_used_remote=json.loads(job.remote_pages_json),
            config_version=job.config_version,
        )

    def _choose_config(self, path: Path, configs: list[FundConfig], requested: str | None) -> FundConfig | None:
        if requested:
            return next((config for config in configs if config.fund_id == requested), None)
        first_pages = self.local_adapter.parse(path)
        compact = "".join(page.text for page in first_pages).lower().replace(" ", "")
        return next(
            (
                config
                for config in configs
                if any(pattern.lower().replace(" ", "") in compact for pattern in config.fund_name_patterns)
            ),
            None,
        )

    def _persist(
        self,
        job: ParseJobRow,
        config: FundConfig,
        schedule: ScheduleRange | None,
        holdings: list[HoldingRecord],
        validations: list[ValidationResult],
        remote_pages: list[int],
    ) -> None:
        self.session.execute(delete(HoldingRow).where(HoldingRow.job_id == job.id))
        self.session.execute(delete(ValidationRow).where(ValidationRow.job_id == job.id))
        for record in holdings:
            record_id = str(uuid4())
            record.id = record_id
            self.session.add(
                HoldingRow(
                    id=record_id,
                    job_id=job.id,
                    fund_name=record.fund_name,
                    report_date=record.report_date,
                    security_name=record.security_name,
                    security_type=record.security_type,
                    country_iso3=record.country_iso3,
                    sector=record.sector,
                    number_of_shares=record.number_of_shares,
                    principal_amount=record.principal_amount,
                    market_value=record.market_value,
                    source_page=record.source_page,
                    source_bbox_json=record.source_bbox.model_dump_json() if record.source_bbox else None,
                    parser_source=record.parser_source,
                    validation_status=record.validation_status,
                )
            )
        for validation in validations:
            self.session.add(
                ValidationRow(
                    id=str(uuid4()),
                    job_id=job.id,
                    code=validation.code,
                    severity=validation.severity,
                    message=validation.message,
                    page_number=validation.page_number,
                    section_name=validation.section_name,
                )
            )
        if schedule is not None:
            job.fund_name = schedule.fund_name
            job.report_date = schedule.report_date
        has_errors = any(validation.severity == "error" for validation in validations)
        job.status = JobStatus.COMPLETE
        job.current_stage = "Complete - review required" if has_errors else "Complete"
        job.remote_page_count = len(remote_pages)
        job.remote_pages_json = json.dumps(remote_pages)
        job.holding_count = len(holdings)
        self.session.commit()

    @staticmethod
    def _replace_pages(local: list[ParsedPage], remote: list[ParsedPage]) -> list[ParsedPage]:
        replacements = {page.page_number: page for page in remote}
        return [replacements.get(page.page_number, page) for page in local]

    @staticmethod
    def _failed_pages(validations: list[ValidationResult], fallback: list[int]) -> list[int]:
        pages = sorted({item.page_number for item in validations if item.severity == "error" and item.page_number})
        return pages or fallback[:1]

    @staticmethod
    def _mark_failed_pages_for_review(
        holdings: list[HoldingRecord], validations: list[ValidationResult]
    ) -> None:
        failed_pages = {
            validation.page_number
            for validation in validations
            if validation.severity == "error" and validation.page_number is not None
        }
        for holding in holdings:
            if holding.source_page in failed_pages:
                holding.validation_status = ValidationStatus.REVIEW

    @staticmethod
    def _empty_schedule(config: FundConfig) -> ScheduleRange:
        return ScheduleRange(fund_name=config.display_name, report_date=None, start_page=1, end_page=1)

    def _require_job(self, job_id: str) -> ParseJobRow:
        job = self.session.get(ParseJobRow, job_id)
        if job is None:
            raise LookupError("Job not found")
        return job

    def _fail(self, job: ParseJobRow, message: str) -> None:
        job.status = JobStatus.FAILED
        job.current_stage = "Failed"
        job.error_message = message
        self.session.commit()

    @staticmethod
    def _holding_model(row: HoldingRow) -> HoldingRecord:
        return HoldingRecord(
            id=row.id,
            fund_name=row.fund_name,
            report_date=row.report_date,
            security_name=row.security_name,
            security_type=row.security_type,
            country_iso3=row.country_iso3,
            sector=row.sector,
            number_of_shares=row.number_of_shares,
            principal_amount=row.principal_amount,
            market_value=row.market_value,
            source_page=row.source_page,
            source_bbox=BoundingBox.model_validate_json(row.source_bbox_json) if row.source_bbox_json else None,
            parser_source=row.parser_source,
            validation_status=row.validation_status,
        )

    @staticmethod
    def _validation_model(row: ValidationRow) -> ValidationResult:
        return ValidationResult.model_validate(row)
