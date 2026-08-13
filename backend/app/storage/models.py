from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.database import Base


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ParseJobRow(Base):
    __tablename__ = "parse_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    fund_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    config_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    current_stage: Mapped[str] = mapped_column(String(80), default="queued")
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    local_page_count: Mapped[int] = mapped_column(Integer, default=0)
    remote_page_count: Mapped[int] = mapped_column(Integer, default=0)
    holding_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fund_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    remote_pages_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    holdings: Mapped[list["HoldingRow"]] = relationship(cascade="all, delete-orphan")
    validations: Mapped[list["ValidationRow"]] = relationship(cascade="all, delete-orphan")


class FundConfigRow(Base):
    __tablename__ = "fund_configs"

    fund_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    current_version: Mapped[str] = mapped_column(String(40))
    yaml_content: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ConfigVersionRow(Base):
    __tablename__ = "config_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fund_id: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(40))
    yaml_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class HoldingRow(Base):
    __tablename__ = "holding_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("parse_jobs.id"), index=True)
    fund_name: Mapped[str] = mapped_column(String(255))
    report_date: Mapped[date] = mapped_column(Date)
    security_name: Mapped[str] = mapped_column(Text)
    security_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    country_iso3: Mapped[str | None] = mapped_column(String(3), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(180), nullable=True)
    number_of_shares: Mapped[Decimal | None] = mapped_column(Numeric(30, 8), nullable=True)
    principal_amount: Mapped[Decimal | None] = mapped_column(Numeric(30, 8), nullable=True)
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 8), nullable=True)
    source_page: Mapped[int] = mapped_column(Integer)
    source_bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parser_source: Mapped[str] = mapped_column(String(20))
    validation_status: Mapped[str] = mapped_column(String(20))


class ValidationRow(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("parse_jobs.id"), index=True)
    code: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_name: Mapped[str | None] = mapped_column(String(180), nullable=True)


class UserCorrectionRow(Base):
    __tablename__ = "user_corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("parse_jobs.id"), index=True)
    record_id: Mapped[str] = mapped_column(ForeignKey("holding_records.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(80))
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
