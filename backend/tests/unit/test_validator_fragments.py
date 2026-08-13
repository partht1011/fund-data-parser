from decimal import Decimal

from app.domain.enums import ParserSource
from app.domain.models import HoldingRecord
from app.extraction.parser import ExtractionResult
from app.validation.validator import Validator


def test_rate_only_security_fragment_requires_review(schedule):
    range_ = schedule("Example Fund")
    record = HoldingRecord(
        fund_name=range_.fund_name,
        report_date=range_.report_date,
        security_name="Term SOFR + 1.77% thereafter)(5)",
        security_type="Corporate Bonds",
        sector="Commercial Banks",
        principal_amount=Decimal("10000000"),
        market_value=Decimal("9856363"),
        source_page=6,
        parser_source=ParserSource.LOCAL,
    )

    validations = Validator().validate(range_, ExtractionResult(holdings=[record]))

    assert record.validation_status == "review"
    assert any(item.code == "security_name_fragment" for item in validations)
