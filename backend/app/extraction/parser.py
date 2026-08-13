import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.config.schema import FundConfig
from app.document.page_model import PageBlock, ParsedPage
from app.domain.enums import ParserSource, ValidationStatus
from app.domain.models import HoldingRecord, ScheduleRange
from app.extraction.context import ParseContext
from app.extraction.field_normalizer import (
    extract_sector,
    normalize_country,
    normalize_security_name,
    parse_decimal,
)
from app.extraction.row_classifier import (
    is_footnote,
    is_noise,
    is_total,
    match_security_type,
    section_heading,
)

CURRENCY = r"(?:[$€£]|USD|EUR|GBP)"
NUMBER_CORE = r"(?:\d{1,3}(?:[,\u00a0\u202f ]\d{3})+|\d+)(?:\.\d+)?"
NUMBER_ATOM = rf"(?:{CURRENCY}\s*)?[+-]?\s*{NUMBER_CORE}"
NUMBER = rf"(?:(?:{CURRENCY}\s*)?\(\s*{NUMBER_ATOM}\s*\)|{NUMBER_ATOM}-?)"
SHARE_FIRST = re.compile(rf"^\s*(?P<amount>{NUMBER})\s+(?P<name>.+?)\s+(?P<value>{NUMBER})\s*$")
SECURITY_FIRST = re.compile(rf"^\s*(?P<name>.+?)\s+(?P<amount>{NUMBER})\s+(?P<value>{NUMBER})\s*$")

DEBT_MARKERS = (
    "bond",
    "note",
    "obligation",
    "mortgage",
    "loan",
    "floating rate",
    "government securit",
)
EQUITY_MARKERS = ("stock", "equity", "fund", "reit")


@dataclass
class ExtractionResult:
    holdings: list[HoldingRecord] = field(default_factory=list)
    printed_totals: dict[str, Decimal] = field(default_factory=dict)
    issues: list["ExtractionIssue"] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractionIssue:
    code: str
    message: str
    page_number: int
    field_name: str | None = None
    security_name: str | None = None


@dataclass
class PendingRow:
    text: str
    block: PageBlock


class HoldingParser:
    def parse(
        self,
        pages: list[ParsedPage],
        schedule: ScheduleRange,
        config: FundConfig,
        parser_source: ParserSource | None = None,
    ) -> ExtractionResult:
        if schedule.report_date is None:
            return ExtractionResult()
        context = ParseContext()
        output = ExtractionResult()
        pending: PendingRow | None = None
        selected = [page for page in pages if schedule.start_page <= page.page_number <= schedule.end_page]
        for page in selected:
            page_parser_source = (
                ParserSource.REMOTE
                if page.source == "mistral"
                else parser_source or ParserSource.LOCAL
            )
            if not config.hierarchy.carry_context_across_pages:
                context = ParseContext()
            for block in page.blocks:
                text = re.sub(r"\s+", " ", block.text).strip()
                compact_text = re.sub(r"[^a-z0-9]", "", text.lower())
                if any(
                    re.sub(r"[^a-z0-9]", "", heading.lower()) in compact_text
                    for heading in config.holding_stop_headings
                ):
                    self._report_unfinished_row(pending, output)
                    return output
                if self._is_document_chrome(text, config) or is_noise(text, config):
                    continue
                security_type = match_security_type(text, config)
                if security_type:
                    repeated_context = security_type == context.security_type and "continued" in text.lower()
                    context.security_type = security_type
                    if not repeated_context:
                        context.reset_second_level()
                        self._report_unfinished_row(pending, output)
                        pending = None
                    continue
                heading = section_heading(text)
                if heading:
                    if config.hierarchy.second_level == "country":
                        context.country_iso3 = normalize_country(heading, config.country_aliases)
                        context.sector = None
                    else:
                        context.sector = heading
                        context.country_iso3 = None
                    context.current_issuer = None
                    self._report_unfinished_row(pending, output)
                    pending = None
                    continue
                if is_total(text):
                    self._capture_total(text, context, output)
                    self._report_unfinished_row(pending, output)
                    pending = None
                    continue
                if config.rules.ignore_footnotes and is_footnote(text):
                    continue
                if not re.search(r"[A-Za-z]", text) and not context.current_issuer:
                    continue

                combined = f"{pending.text} {text}" if pending else text
                source_block = pending.block if pending else block
                matched = None
                if pending and self._looks_like_row_start(text):
                    standalone = self._match_row(text, config, bool(context.current_issuer))
                    if standalone:
                        self._report_unfinished_row(pending, output)
                        pending = None
                        matched = standalone
                        source_block = block
                if matched is None:
                    matched = self._match_row(combined, config, bool(context.current_issuer))
                if matched:
                    try:
                        record = self._to_record(
                            matched,
                            source_block,
                            schedule,
                            config,
                            context,
                            page_parser_source,
                            output,
                        )
                    except Exception as exc:
                        output.issues.append(
                            ExtractionIssue(
                                code="row_parse_failed",
                                message=(
                                    "A candidate holding row could not be parsed; other rows were "
                                    f"preserved ({type(exc).__name__})."
                                ),
                                page_number=source_block.page_number,
                            )
                        )
                        record = None
                    if record:
                        output.holdings.append(record)
                        context.current_issuer = self._issuer_from_record(record.security_name)
                    pending = None
                    continue

                if self._looks_like_row_start(text):
                    pending = PendingRow(text=text, block=block)
                elif pending and config.rules.allow_multiline_security_name:
                    pending.text = combined
                elif self._looks_like_issuer(text):
                    context.current_issuer = normalize_security_name(text)
        self._report_unfinished_row(pending, output)
        return output

    @staticmethod
    def _report_unfinished_row(
        pending: PendingRow | None, output: ExtractionResult
    ) -> None:
        if pending is None:
            return
        output.issues.append(
            ExtractionIssue(
                code="holding_row_incomplete",
                message=(
                    "A candidate holding row ended before its numeric fields could be "
                    "assembled; other holdings were preserved."
                ),
                page_number=pending.block.page_number,
                security_name=pending.text[:120],
            )
        )

    @staticmethod
    def _is_document_chrome(text: str, config: FundConfig) -> bool:
        compact = re.sub(r"[^a-z]", "", text.lower())
        patterns = [*config.fund_name_patterns, *config.schedule_headings]
        is_date_line = re.fullmatch(
            r"(?:January|February|March|April|May|June|July|August|September|October|"
            r"November|December)\s+\d{1,2},\s*20\d{2}(?:\s*\(Unaudited\))?",
            text,
            re.IGNORECASE,
        )
        return (
            any(re.sub(r"[^a-z]", "", pattern.lower()) in compact for pattern in patterns)
            or bool(is_date_line)
            or bool(re.search(r"\b(19|20)\d{2}\s*\(Unaudited\)", text, re.IGNORECASE))
        )

    @staticmethod
    def _match_row(
        text: str, config: FundConfig, allow_issuer_terms: bool = False
    ) -> re.Match[str] | None:
        patterns = [SECURITY_FIRST, SHARE_FIRST] if config.rules.security_first else [SHARE_FIRST, SECURITY_FIRST]
        for pattern in patterns:
            match = pattern.match(text)
            if match and (allow_issuer_terms or re.search(r"[A-Za-z]", match.group("name"))):
                return match
        return None

    def _to_record(
        self,
        match: re.Match[str],
        block: PageBlock,
        schedule: ScheduleRange,
        config: FundConfig,
        context: ParseContext,
        parser_source: ParserSource,
        output: ExtractionResult,
    ) -> HoldingRecord | None:
        name = normalize_security_name(match.group("name"))
        if is_total(name):
            return None
        if context.current_issuer and self._starts_with_terms(name):
            name = f"{context.current_issuer} {name}"
        sector = context.sector
        if config.hierarchy.sector_source == "description":
            name, embedded_sector = extract_sector(name)
            sector = embedded_sector or sector
        amount, amount_failed = self._safe_decimal(
            match.group("amount"), "amount", name, block, output
        )
        market_value, market_value_failed = self._safe_decimal(
            match.group("value"), "market_value", name, block, output
        )
        if market_value is not None:
            market_value *= config.rules.value_scale
        number_of_shares, principal_amount, review = self._assign_amount(
            amount, context.security_type
        )
        review = review or amount_failed or market_value_failed
        return HoldingRecord(
            fund_name=schedule.fund_name,
            report_date=schedule.report_date or date.min,
            security_name=name,
            security_type=context.security_type,
            country_iso3=context.country_iso3,
            sector=sector,
            number_of_shares=number_of_shares,
            principal_amount=principal_amount,
            market_value=market_value,
            source_page=block.page_number,
            source_bbox=block.bbox,
            parser_source=parser_source,
            validation_status=ValidationStatus.REVIEW if review else ValidationStatus.PASS,
        )

    @staticmethod
    def _safe_decimal(
        raw_value: str,
        field_name: str,
        security_name: str,
        block: PageBlock,
        output: ExtractionResult,
    ) -> tuple[Decimal | None, bool]:
        try:
            return parse_decimal(raw_value), False
        except ValueError:
            output.issues.append(
                ExtractionIssue(
                    code="numeric_parse_failed",
                    message=(
                        f"Could not parse {field_name.replace('_', ' ')} for "
                        f"{security_name!r}; the field was left null."
                    ),
                    page_number=block.page_number,
                    field_name=field_name,
                    security_name=security_name,
                )
            )
            return None, True

    @staticmethod
    def _assign_amount(amount: Decimal | None, security_type: str | None) -> tuple[Decimal | None, Decimal | None, bool]:
        lower = (security_type or "").lower()
        if any(marker in lower for marker in DEBT_MARKERS):
            return None, amount, False
        if any(marker in lower for marker in EQUITY_MARKERS):
            return amount, None, False
        return None, None, amount is not None

    @staticmethod
    def _starts_with_terms(name: str) -> bool:
        return bool(re.match(r"^(?:\d+(?:\.\d+)?%|\d{2}/\d{2}/\d{4}|due\b)", name, re.IGNORECASE))

    @staticmethod
    def _looks_like_row_start(text: str) -> bool:
        return bool(re.match(rf"^\s*{NUMBER}\s+[A-Za-z]", text)) or bool(
            re.search(rf"[A-Za-z].*\s{NUMBER}\s*$", text)
        )

    @staticmethod
    def _looks_like_issuer(text: str) -> bool:
        return len(text) <= 90 and bool(re.search(r"[A-Za-z]", text)) and not re.search(r"\d", text)

    @staticmethod
    def _issuer_from_record(name: str) -> str:
        match = re.split(r"\s+\d+(?:\.\d+)?%", name, maxsplit=1)
        return match[0].strip()

    @staticmethod
    def _capture_total(text: str, context: ParseContext, output: ExtractionResult) -> None:
        values = re.findall(NUMBER, text)
        if not values:
            return
        section = context.sector or context.country_iso3 or context.security_type
        section_key = re.sub(r"[^a-z0-9]", "", (section or "").lower())
        text_key = re.sub(r"[^a-z0-9]", "", text.lower())
        if section and section_key in text_key:
            try:
                value = parse_decimal(values[-1])
            except ValueError:
                return
            if value is not None:
                output.printed_totals[section] = value
