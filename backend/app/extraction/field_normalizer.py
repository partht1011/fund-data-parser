import re
from decimal import Decimal, InvalidOperation

import pycountry

_CURRENCY = re.compile(r"(?:USD|EUR|GBP|[$€£])", re.IGNORECASE)
_NULL_NUMBERS = {"", "-", "--", "—", "–"}

DEFAULT_COUNTRY_ALIASES = {
    "south korea": "KOR",
    "korea, republic of": "KOR",
    "russia": "RUS",
    "taiwan": "TWN",
    "united kingdom": "GBR",
    "united states": "USA",
}


def parse_decimal(value: str | None) -> Decimal | None:
    """Parse common financial-report formats without silently coercing text."""
    if value is None:
        return None
    cleaned = (
        value.replace("\u00a0", " ")
        .replace("\u202f", " ")
        .replace("−", "-")
        .replace("†", "")
        .strip()
    )
    if cleaned in _NULL_NUMBERS:
        return None
    cleaned = _CURRENCY.sub("", cleaned).strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1].strip()
    elif cleaned.endswith("-"):
        negative = True
        cleaned = cleaned[:-1].strip()
    cleaned = re.sub(r"[,\s]", "", cleaned)
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", cleaned):
        raise ValueError(f"invalid numeric value: {value}")
    try:
        number = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric value: {value}") from exc
    return -number if negative else number


def normalize_country(name: str | None, aliases: dict[str, str] | None = None) -> str | None:
    if not name:
        return None
    cleaned = re.sub(r"\s+", " ", name).strip(" .")
    combined = {**DEFAULT_COUNTRY_ALIASES, **{k.lower(): v for k, v in (aliases or {}).items()}}
    if cleaned.lower() in combined:
        return combined[cleaned.lower()]
    if len(cleaned) == 3 and pycountry.countries.get(alpha_3=cleaned.upper()):
        return cleaned.upper()
    match = pycountry.countries.get(name=cleaned)
    if match is None:
        try:
            match = pycountry.countries.search_fuzzy(cleaned)[0]
        except LookupError:
            return None
    return str(match.alpha_3)


def normalize_security_name(value: str) -> str:
    cleaned = re.sub(r"\.{2,}", " ", value)
    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
    cleaned = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", cleaned)
    cleaned = re.sub(r"\s+([,.)])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s+", "(", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_sector(description: str) -> tuple[str, str | None]:
    match = re.search(r"\(([^()]*[A-Za-z][^()]*)\)\s*(?:\(\d+\))*$", description)
    if not match:
        return description, None
    sector = re.sub(r"\s+", " ", match.group(1)).strip()
    security = (description[: match.start()] + description[match.end() :]).strip()
    return security, sector
