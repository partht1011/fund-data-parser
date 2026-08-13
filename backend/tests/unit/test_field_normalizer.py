from decimal import Decimal

import pytest

from app.extraction.field_normalizer import extract_sector, normalize_country, parse_decimal


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$1,499,000", Decimal("1499000")),
        ("$ (91,984)", Decimal("-91984")),
        ("($91,984)", Decimal("-91984")),
        ("EUR 91 984", Decimal("91984")),
        ("91\u202f984-", Decimal("-91984")),
        ("(24,010.50)", Decimal("-24010.50")),
        ("—", None),
        (None, None),
    ],
)
def test_parse_decimal(raw, expected):
    assert parse_decimal(raw) == expected


@pytest.mark.parametrize(
    ("country", "expected"),
    [("Canada", "CAN"), ("Japan", "JPN"), ("South Korea", "KOR"), ("United Kingdom", "GBR")],
)
def test_country_normalization(country, expected):
    assert normalize_country(country) == expected


def test_unknown_country_is_null():
    assert normalize_country("Atlantis") is None


def test_invalid_numeric_text_is_rejected():
    with pytest.raises(ValueError, match="invalid numeric value"):
        parse_decimal("not a number")


def test_sector_is_extracted_from_gsam_description():
    security, sector = extract_sector("Rio Tinto PLC (Materials)")
    assert security == "Rio Tinto PLC"
    assert sector == "Materials"
