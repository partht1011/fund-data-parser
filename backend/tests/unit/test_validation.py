from datetime import date
from decimal import Decimal

from app.domain.enums import ParserSource, Severity
from app.domain.models import HoldingRecord, ScheduleRange, ValidationResult
from app.extraction.parser import ExtractionResult
from app.validation.reconciliation import reconcile_sections
from app.validation.validator import Validator, should_use_remote


def test_exact_section_reconciliation():
    records = [
        HoldingRecord(
            fund_name="Fund",
            report_date=date(2025, 1, 1),
            security_name="A",
            country_iso3="CAN",
            number_of_shares=Decimal("2"),
            market_value=Decimal("10.10"),
            source_page=1,
            parser_source=ParserSource.LOCAL,
        ),
        HoldingRecord(
            fund_name="Fund",
            report_date=date(2025, 1, 1),
            security_name="B",
            country_iso3="CAN",
            number_of_shares=Decimal("3"),
            market_value=Decimal("20.20"),
            source_page=1,
            parser_source=ParserSource.LOCAL,
        ),
    ]
    result = reconcile_sections(records, {"CAN": Decimal("30.30")}, Decimal("0"))
    assert result[0].code == "section_reconciliation_pass"


def test_remote_routing_depends_on_error_severity():
    assert should_use_remote([ValidationResult(code="x", severity=Severity.ERROR, message="bad")])
    assert not should_use_remote([ValidationResult(code="x", severity=Severity.WARNING, message="check")])


def test_document_checks_require_holdings():
    schedule = ScheduleRange(fund_name="Fund", report_date=date(2025, 1, 1), start_page=1, end_page=1)
    results = Validator().validate(schedule, ExtractionResult())
    assert any(result.code == "holdings_missing" for result in results)
