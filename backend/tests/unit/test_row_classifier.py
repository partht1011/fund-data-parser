from app.extraction.row_classifier import (
    is_total,
    match_header_alias,
    match_security_type,
    section_heading,
)


def test_security_type_alias(load_config):
    config = load_config("hartford")
    assert match_security_type("CORPORATE BONDS -46.7% -(continued)", config) == "Corporate Bonds"


def test_ambiguous_header_aliases_are_identified(load_config):
    config = load_config("hartford")
    matches = match_header_alias("Shares or Principal Amount     Market Value", config)
    assert matches == {"number_of_shares", "principal_amount", "market_value"}


def test_total_is_not_a_holding():
    assert is_total("Total Convertible Bonds (cost $17,550,623) $17,378,846")


def test_total_tolerates_pdf_character_duplication():
    assert is_total("TOTTTAL INVESTMENTS – 99.7% (Cost $1,278,718,439)")


def test_cost_reconciliation_line_is_not_a_holding():
    assert is_total("(Cost $1,241,561,785) $1,378,552,253")
    assert is_total("(Cost: $1,039,929,444) 1,146,418,342")


def test_section_heading_handles_unicode_dash():
    assert section_heading("South Korea—2.5%") == "South Korea"


def test_security_type_heading_allows_percentage_footnote(load_config):
    config = load_config("hartford")
    assert (
        match_security_type("SENIOR FLOATING RATE INTERESTS - 0.1%(14)", config)
        == "Senior Floating Rate Interests"
    )
