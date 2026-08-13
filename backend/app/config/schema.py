from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ColumnAliases(BaseModel):
    security_name: list[str] = Field(default_factory=lambda: ["Security", "Description"])
    number_of_shares: list[str] = Field(default_factory=lambda: ["Shares", "Quantity"])
    principal_amount: list[str] = Field(
        default_factory=lambda: ["Principal Amount", "Shares or Principal Amount"]
    )
    market_value: list[str] = Field(default_factory=lambda: ["Value", "Market Value"])


class HierarchyConfig(BaseModel):
    first_level: Literal["security_type"] = "security_type"
    second_level: Literal["country", "sector"]
    sector_source: Literal["description"] | None = None
    carry_context_across_pages: bool = True


class ParserRules(BaseModel):
    allow_multiline_security_name: bool = True
    ignore_totals: bool = True
    ignore_footnotes: bool = True
    security_first: bool = False
    value_scale: int = 1
    reconciliation_tolerance: str = "0"


class FallbackConfig(BaseModel):
    enabled: bool = True


class LayoutHints(BaseModel):
    columns: int | Literal["auto"] = "auto"
    split_ratio: float = 0.5


class FundConfig(BaseModel):
    fund_id: str
    version: str
    display_name: str
    fund_name_patterns: list[str]
    schedule_headings: list[str]
    stop_headings: list[str] = Field(
        default_factory=lambda: [
            "Statement of Assets and Liabilities",
            "Statements of Assets and Liabilities",
            "Notes to Financial Statements",
        ]
    )
    holding_stop_headings: list[str] = Field(default_factory=list)
    column_aliases: ColumnAliases = Field(default_factory=ColumnAliases)
    hierarchy: HierarchyConfig
    security_types: dict[str, list[str]]
    country_aliases: dict[str, str] = Field(default_factory=dict)
    rules: ParserRules = Field(default_factory=ParserRules)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    layout_hints: LayoutHints = Field(default_factory=LayoutHints)

    @field_validator("fund_name_patterns", "schedule_headings")
    @classmethod
    def require_patterns(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("at least one pattern is required")
        return value
