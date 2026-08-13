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


def test_share_class_continuation_uses_previous_issuer(
    load_config, make_pages, schedule
):
    config = load_config("blackrock")
    pages = make_pages(
        [[
            "Short-Term Securities",
            "United States—0.2%",
            "BlackRock Liquidity Funds, T-Fund, Institutional",
            "Shares, 4.16%(a)(b) 2,296,729 2,296,729",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert result.issues == []
    assert result.holdings[0].security_name == (
        "Black Rock Liquidity Funds, T-Fund, Institutional Shares, 4.16%(a)(b)"
    )


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


def test_repeated_section_heading_keeps_issuer_context(
    load_config, make_pages, schedule
):
    config = load_config("hartford")
    pages = make_pages(
        [
            [
                "CORPORATE BONDS -46.7%",
                "Commercial Banks -9.2%",
                "Bank of Example Corp.",
                "1,000,000 4.50%, 01/01/2030 990,000",
            ],
            [
                "CORPORATE BONDS -46.7% -(continued)",
                "Commercial Banks -9.2% -(continued)",
                "2,000,000 5.00%, 01/01/2032 1,950,000",
            ],
        ]
    )
    result = HoldingParser().parse(
        pages, schedule(config.display_name, 2), config, ParserSource.LOCAL
    )
    assert result.issues == []
    assert result.holdings[-1].security_name == (
        "Bank of Example Corp. 5.00%, 01/01/2032"
    )


def test_debt_row_assembles_issuer_and_floating_rate_across_lines(
    load_config, make_pages, schedule
):
    config = load_config("hartford")
    pages = make_pages(
        [[
            "CORPORATE BONDS -46.7%",
            "Commercial Banks -4.3%",
            "BNP Paribas SA 1.90%, 09/30/2028,",
            "(1.90% fixed rate until 09/30/2027;",
            "6 mo. USD SOFR + 1.61%",
            "5,200,000 thereafter)(2)(5) 4,863,754",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert result.issues == []
    assert len(result.holdings) == 1
    record = result.holdings[0]
    assert record.security_name == (
        "BNP Paribas SA 1.90%, 09/30/2028, (1.90% fixed rate until "
        "09/30/2027; 6 mo. USD SOFR + 1.61% thereafter)(2)(5)"
    )
    assert record.principal_amount == Decimal("5200000")
    assert record.market_value == Decimal("4863754")


def test_debt_issuer_may_begin_with_digits(load_config, make_pages, schedule):
    config = load_config("hartford")
    pages = make_pages(
        [[
            "CORPORATE BONDS -46.7%",
            "Pharmaceuticals -1.7%",
            "1261229 BC Ltd. 10.00%,",
            "4,930,000 04/15/2032(2) 4,827,328",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert result.issues == []
    assert result.holdings[0].security_name == "1261229 BC Ltd. 10.00%, 04/15/2032(2)"
    assert result.holdings[0].principal_amount == Decimal("4930000")


def test_debt_row_supports_iso_currency_amount_prefix(load_config, make_pages, schedule):
    config = load_config("hartford")
    pages = make_pages(
        [[
            "CORPORATE BONDS -46.7%",
            "Telecommunications -0.8%",
            "America Movil SAB de CV 9.50%,",
            "MXN 43,930,000 01/27/2031 2,226,950",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert result.issues == []
    record = result.holdings[0]
    assert record.security_name == "America Movil SAB de CV 9.50%, 01/27/2031"
    assert record.principal_amount == Decimal("43930000")
    assert record.market_value == Decimal("2226950")


def test_company_suffix_is_not_consumed_as_currency(
    load_config, make_pages, schedule
):
    config = load_config("hartford")
    pages = make_pages(
        [[
            "COMMON STOCKS -43.0%",
            "Capital Goods -5.5%",
            "2,174,716 BAE Systems PLC 50,415,652",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert result.issues == []
    record = result.holdings[0]
    assert record.security_name == "BAE Systems PLC"
    assert record.number_of_shares == Decimal("2174716")
    assert record.market_value == Decimal("50415652")


def test_repeated_debt_terms_reuse_issuer_without_duplicate_type_word(
    load_config, make_pages, schedule
):
    config = load_config("hartford")
    pages = make_pages(
        [[
            "FOREIGN GOVERNMENT OBLIGATIONS -5.0%",
            "Dominican Republic -0.1%",
            "Dominican Republic International Bonds",
            "$ 4,752,000 4.50%, 01/30/2030(1) 4,416,509",
            "3,135,000 Bonds 4.88%, 09/23/2032(1) 2,811,311",
        ]]
    )
    result = HoldingParser().parse(pages, schedule(config.display_name), config)
    assert result.issues == []
    assert [record.security_name for record in result.holdings] == [
        "Dominican Republic International Bonds 4.50%, 01/30/2030(1)",
        "Dominican Republic International Bonds 4.88%, 09/23/2032(1)",
    ]
