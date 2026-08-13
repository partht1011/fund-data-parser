from dataclasses import dataclass


@dataclass
class ParseContext:
    security_type: str | None = None
    country_iso3: str | None = None
    sector: str | None = None
    current_issuer: str | None = None

    def reset_second_level(self) -> None:
        self.country_iso3 = None
        self.sector = None
        self.current_issuer = None
