from decimal import Decimal

import app.extraction.parser as parser_module
from app.domain.enums import ParserSource
from app.extraction.parser import HoldingParser


def test_blackrock_security_first_row(load_config, make_pages, schedule):
    config = load_config("blackrock")
    pages = make_pages(
        [["Common Stocks", "Canada—6.5%", "Teck Resources Ltd., Class B 742,465 $ 25,387,670"]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert len(result.holdings) == 1
    record = result.holdings[0]
    assert record.security_name == "Teck Resources Ltd., Class B"
    assert record.country_iso3 == "CAN"
    assert record.number_of_shares == Decimal("742465")
    assert record.market_value == Decimal("25387670")


def test_report_date_line_is_not_a_holding(load_config, make_pages, schedule):
    config = load_config("blackrock")
    pages = make_pages(
        [[
            "August 31, 2025",
            "Common Stocks",
            "Canada—6.5%",
            "Teck Resources Ltd., Class B 742,465 $ 25,387,670",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert [record.security_name for record in result.holdings] == ["Teck Resources Ltd., Class B"]


def test_holding_stop_heading_prevents_disclosure_rows(load_config, make_pages, schedule):
    config = load_config("blackrock")
    pages = make_pages(
        [[
            "Common Stocks",
            "Canada—6.5%",
            "Teck Resources Ltd., Class B 742,465 25,387,670",
            "Affiliates",
            "Disclosure Table 100 200",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert len(result.holdings) == 1


def test_bad_row_isolated_while_later_holdings_survive(load_config, make_pages, schedule):
    config = load_config("gsam")
    pages = make_pages(
        [[
            "Common Stocks – 97.1%",
            "Australia–6.0%",
            "12,345 Broken Security $ malformed",
            "930,611 Rio Tinto PLC (Materials) $62,965,873",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert [record.security_name for record in result.holdings] == ["Rio Tinto PLC"]
    assert result.issues[0].code == "holding_row_incomplete"


def test_numeric_failure_marks_only_record_for_review(
    monkeypatch, load_config, make_pages, schedule
):
    config = load_config("blackrock")
    original = parser_module.parse_decimal

    def fail_market_value(value):
        if value == "25,387,670":
            raise ValueError("simulated malformed value")
        return original(value)

    monkeypatch.setattr(parser_module, "parse_decimal", fail_market_value)
    pages = make_pages(
        [["Common Stocks", "Canada—6.5%", "Teck Resources Ltd., Class B 742,465 25,387,670"]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert len(result.holdings) == 1
    assert result.holdings[0].market_value is None
    assert result.holdings[0].validation_status == "review"
    assert result.issues[0].code == "numeric_parse_failed"


def test_cost_line_does_not_create_a_record_or_validation_issue(
    load_config, make_pages, schedule
):
    config = load_config("gsam")
    pages = make_pages(
        [[
            "Common Stocks – 97.1%",
            "Australia–6.0%",
            "930,611 Rio Tinto PLC (Materials) $62,965,873",
            "TOTTTAL COMMON STOCKS",
            "(Cost $1,241,561,785) $1,378,552,253",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert [record.security_name for record in result.holdings] == ["Rio Tinto PLC"]
    assert result.issues == []


def test_gsam_wrapped_row_and_embedded_sector(load_config, make_pages, schedule):
    config = load_config("gsam")
    pages = make_pages(
        [[
            "Common Stocks – 97.1%",
            "Denmark–1.5%",
            "161,406 Novo Nordisk A/S, Class",
            "B (Pharmaceuticals,",
            "Biotechnology & Life Sciences) 20,699,078",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    record = result.holdings[0]
    assert record.security_name == "Novo Nordisk A/S, Class B"
    assert record.sector == "Pharmaceuticals, Biotechnology & Life Sciences"
    assert record.country_iso3 == "DNK"


def test_hartford_context_carries_to_continuation_page(load_config, make_pages, schedule):
    config = load_config("hartford")
    pages = make_pages(
        [
            ["CORPORATE BONDS -46.7%", "Aerospace & Defense -1.3%", "Boeing Co."],
            ["CORPORATE BONDS -46.7% -(continued)", "25,000 3.63%, 02/01/2031 23,358"],
        ]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name, 2), config, ParserSource.LOCAL)
    record = result.holdings[0]
    assert record.security_name == "Boeing Co. 3.63%, 02/01/2031"
    assert record.security_type == "Corporate Bonds"
    assert record.sector == "Aerospace & Defense"
    assert record.principal_amount == Decimal("25000")
    assert record.number_of_shares is None
