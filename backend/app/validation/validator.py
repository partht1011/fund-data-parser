import re
from decimal import Decimal

import pycountry

from app.domain.enums import Severity, ValidationStatus
from app.domain.models import HoldingRecord, ScheduleRange, ValidationResult
from app.extraction.parser import ExtractionResult
from app.extraction.row_classifier import is_total
from app.validation.reconciliation import reconcile_sections


class Validator:
    def validate(
        self,
        schedule: ScheduleRange | None,
        extraction: ExtractionResult,
        tolerance: Decimal = Decimal(0),
    ) -> list[ValidationResult]:
        results = [
            ValidationResult(
                code=issue.code,
                severity=Severity.ERROR,
                message=issue.message,
                page_number=issue.page_number,
                section_name=issue.security_name,
            )
            for issue in extraction.issues
        ]
        if schedule is None:
            results.append(self._error("schedule_range_missing", "No Schedule of Investments range was found"))
            return results
        if not schedule.fund_name:
            results.append(self._error("fund_name_missing", "Fund name is missing"))
        if schedule.report_date is None:
            results.append(self._error("report_date_missing", "Report date is missing", schedule.start_page))
        if not extraction.holdings:
            results.append(self._error("holdings_missing", "No holdings were extracted", schedule.start_page))
        for record in extraction.holdings:
            self._validate_record(record, results)
        results.extend(reconcile_sections(extraction.holdings, extraction.printed_totals, tolerance))
        if not any(result.severity == Severity.ERROR for result in results):
            results.append(
                ValidationResult(
                    code="document_accepted",
                    severity=Severity.INFO,
                    message=f"Accepted {len(extraction.holdings)} holding records",
                    page_number=schedule.start_page,
                )
            )
        return results

    @staticmethod
    def _validate_record(record: HoldingRecord, results: list[ValidationResult]) -> None:
        if not record.security_name or is_total(record.security_name):
            record.validation_status = ValidationStatus.REVIEW
            results.append(Validator._error("invalid_security_name", "Record has an invalid security name", record.source_page))
        elif Validator._looks_like_security_fragment(record.security_name):
            record.validation_status = ValidationStatus.REVIEW
            results.append(
                ValidationResult(
                    code="security_name_fragment",
                    severity=Severity.ERROR,
                    message=(
                        f"Security name appears to be an unassembled row fragment: "
                        f"{record.security_name}"
                    ),
                    page_number=record.source_page,
                    section_name=record.security_name,
                )
            )
        if record.country_iso3 and pycountry.countries.get(alpha_3=record.country_iso3) is None:
            record.validation_status = ValidationStatus.REVIEW
            results.append(Validator._error("invalid_country", f"Invalid ISO3 code {record.country_iso3}", record.source_page))
        if record.number_of_shares is None and record.principal_amount is None:
            record.validation_status = ValidationStatus.REVIEW
            results.append(
                ValidationResult(
                    code="amount_unassigned",
                    severity=Severity.WARNING,
                    message=f"Could not safely classify amount for {record.security_name}",
                    page_number=record.source_page,
                )
            )

    @staticmethod
    def _error(code: str, message: str, page: int | None = None) -> ValidationResult:
        return ValidationResult(code=code, severity=Severity.ERROR, message=message, page_number=page)

    @staticmethod
    def _looks_like_security_fragment(name: str) -> bool:
        return bool(
            re.match(
                r"^(?:thereafter\b|(?:term\s+)?sofr\b|(?:\d+\s+(?:mo\.|yr\.)\s+)?"
                r"(?:usd\s+)?cmt\b|euribor\b|sonia\b|shares?\s*,)",
                name.strip(),
                re.IGNORECASE,
            )
        )


def should_use_remote(validations: list[ValidationResult]) -> bool:
    return any(validation.severity == Severity.ERROR for validation in validations)
