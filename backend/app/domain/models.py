from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, PlainSerializer

from app.domain.enums import JobStatus, ParserSource, Severity, ValidationStatus

JsonDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda value: str(value), return_type=str, when_used="json"),
]


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class HoldingRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    fund_name: str
    report_date: date
    security_name: str
    security_type: str | None = None
    country_iso3: str | None = None
    sector: str | None = None
    number_of_shares: JsonDecimal | None = None
    principal_amount: JsonDecimal | None = None
    market_value: JsonDecimal | None = None
    source_page: int
    source_bbox: BoundingBox | None = None
    parser_source: ParserSource
    validation_status: ValidationStatus = ValidationStatus.PASS


class ValidationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    code: str
    severity: Severity
    message: str
    page_number: int | None = None
    section_name: str | None = None


class ParseResult(BaseModel):
    fund_name: str
    report_date: date
    holdings: list[HoldingRecord]
    validations: list[ValidationResult]
    pages_used_remote: list[int]
    config_version: str


class ScheduleRange(BaseModel):
    fund_name: str
    report_date: date | None
    start_page: int
    end_page: int


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class ParseRequest(BaseModel):
    fund_id: str | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    fund_id: str | None
    config_version: str | None
    status: JobStatus
    current_stage: str
    pages_processed: int = 0
    local_page_count: int = 0
    remote_page_count: int = 0
    holding_count: int = 0
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class CorrectionRequest(BaseModel):
    field_name: Literal[
        "security_name",
        "security_type",
        "country_iso3",
        "sector",
        "number_of_shares",
        "principal_amount",
        "market_value",
    ]
    value: str | None = None
    update_config: bool = False


class ConfigSummary(BaseModel):
    fund_id: str
    version: str
    display_name: str
