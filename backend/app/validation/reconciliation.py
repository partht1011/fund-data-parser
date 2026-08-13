from collections import defaultdict
from decimal import Decimal

from app.domain.enums import Severity
from app.domain.models import HoldingRecord, ValidationResult


def reconcile_sections(
    records: list[HoldingRecord], printed_totals: dict[str, Decimal], tolerance: Decimal
) -> list[ValidationResult]:
    sums: dict[str, Decimal] = defaultdict(Decimal)
    pages: dict[str, int] = {}
    for record in records:
        section = record.sector or record.country_iso3 or record.security_type
        if section and record.market_value is not None:
            sums[section] += record.market_value
            pages.setdefault(section, record.source_page)
    results: list[ValidationResult] = []
    for section, expected in printed_totals.items():
        actual = sums.get(section, Decimal(0))
        difference = abs(expected - actual)
        results.append(
            ValidationResult(
                code="section_reconciliation_pass" if difference <= tolerance else "section_reconciliation_failed",
                severity=Severity.INFO if difference <= tolerance else Severity.ERROR,
                message=f"{section}: extracted {actual} vs printed {expected} (difference {difference})",
                page_number=pages.get(section),
                section_name=section,
            )
        )
    return results
