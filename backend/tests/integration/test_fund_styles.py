from decimal import Decimal

import pytest

from app.extraction.parser import HoldingParser


@pytest.mark.parametrize(
    ("config_name", "lines", "expected"),
    [
        (
            "blackrock",
            ["Common Stocks", "Canada—6.5%", "Teck Resources Ltd., Class B 742,465 $25,387,670"],
            {"country_iso3": "CAN", "number_of_shares": Decimal("742465")},
        ),
        (
            "gsam",
            ["Common Stocks – 97.1%", "Australia–6.0%", "930,611 Rio Tinto PLC (Materials) $62,965,873"],
            {"country_iso3": "AUS", "sector": "Materials"},
        ),
        (
            "hartford",
            ["CONVERTIBLE BONDS -0.2%", "Healthcare - Products -0.0%", "1,400,000 Qiagen NV 2.50%, 09/10/2031(1) 1,421,215"],
            {"sector": "Healthcare - Products", "principal_amount": Decimal("1400000")},
        ),
    ],
)
def test_configured_fund_styles(config_name, lines, expected, load_config, make_pages, schedule):
    config = load_config(config_name)
    result = HoldingParser().parse(make_pages([lines]), schedule(config.display_name), config)
    assert len(result.holdings) == 1
    for field, value in expected.items():
        assert getattr(result.holdings[0], field) == value
