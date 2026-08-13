import re

from app.config.schema import FundConfig

PERCENT_HEADING = re.compile(
    r"^(?P<label>.+?)\s*(?:—|–|-)\s*[\d.]+%"
    r"(?:\s*(?:—|–|-)?\s*\(?continued\)?)?\s*$",
    re.IGNORECASE,
)


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def match_header_alias(text: str, config: FundConfig) -> set[str]:
    key = compact(text)
    aliases_by_field: dict[str, list[str]] = {
        "security_name": config.column_aliases.security_name,
        "number_of_shares": config.column_aliases.number_of_shares,
        "principal_amount": config.column_aliases.principal_amount,
        "market_value": config.column_aliases.market_value,
    }
    matches: set[str] = set()
    for field_name in aliases_by_field:
        field_aliases: list[str] = aliases_by_field[field_name]
        if any(compact(alias) in key for alias in field_aliases):
            matches.add(field_name)
    return matches


def is_noise(text: str, config: FundConfig) -> bool:
    value = text.strip()
    lower = value.lower()
    if not value:
        return True
    if "the accompanying notes" in lower or "percentage shown" in lower:
        return True
    if lower in {"shares", "value", "market value", "security", "description"}:
        return True
    aliases: list[str] = [
        *config.column_aliases.security_name,
        *config.column_aliases.number_of_shares,
        *config.column_aliases.principal_amount,
        *config.column_aliases.market_value,
    ]
    if all(compact(alias) in compact(value) for alias in aliases[:1]) and (
        "value" in lower or "shares" in lower or "principal" in lower
    ):
        return True
    return bool(re.fullmatch(r"\d{1,3}", value))


def is_total(text: str) -> bool:
    lower = text.strip().lower()
    compacted = compact(lower)
    fuzzy_total = bool(re.match(r"^(?:sub)?to+t+a+l", compacted))
    cost_line = bool(re.match(r"^\(?cost(?:\s|[$€£])", lower))
    return cost_line or fuzzy_total or lower.startswith(("net assets", "other assets less"))


def is_footnote(text: str) -> bool:
    value = text.strip()
    return bool(re.match(r"^\(?[a-z0-9]{1,2}\)\s+", value, re.IGNORECASE))


def match_security_type(text: str, config: FundConfig) -> str | None:
    label = PERCENT_HEADING.match(text)
    candidate = label.group("label") if label else text
    candidate_key = compact(candidate.replace("(continued)", ""))
    for canonical, aliases in config.security_types.items():
        if candidate_key in {compact(canonical), *(compact(alias) for alias in aliases)}:
            return canonical
    return None


def section_heading(text: str) -> str | None:
    match = PERCENT_HEADING.match(text.strip())
    return re.sub(r"\s+", " ", match.group("label")).strip() if match else None
