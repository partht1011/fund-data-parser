from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import remote_adapter
from app.document.mistral_adapter import RemoteDocumentParser
from app.domain.models import (
    CorrectionRequest,
    HoldingRecord,
    JobResponse,
    ParseResult,
    ValidationResult,
)
from app.services.import_service import ImportService
from app.storage.database import get_session
from app.storage.models import HoldingRow, ParseJobRow, UserCorrectionRow, ValidationRow

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)) -> ParseJobRow:
    row = session.get(ParseJobRow, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return row


@router.get("/jobs/{job_id}/results", response_model=ParseResult)
def get_results(
    job_id: str,
    session: Session = Depends(get_session),
    remote: RemoteDocumentParser = Depends(remote_adapter),
) -> ParseResult:
    try:
        return ImportService(session, remote).result(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/validations", response_model=list[ValidationResult])
def get_validations(job_id: str, session: Session = Depends(get_session)) -> list[ValidationRow]:
    if session.get(ParseJobRow, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list(session.scalars(select(ValidationRow).where(ValidationRow.job_id == job_id)).all())


@router.post("/jobs/{job_id}/records/{record_id}/correction", response_model=HoldingRecord)
def correct_record(
    job_id: str,
    record_id: str,
    request: CorrectionRequest,
    session: Session = Depends(get_session),
) -> HoldingRecord:
    row = session.get(HoldingRow, record_id)
    if row is None or row.job_id != job_id:
        raise HTTPException(status_code=404, detail="Holding record not found")
    old_value = getattr(row, request.field_name)
    value: object = request.value
    if request.field_name in {"number_of_shares", "principal_amount", "market_value"}:
        try:
            raw_value = request.value
            value = Decimal(raw_value) if raw_value else None
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Correction is not a valid decimal") from exc
    setattr(row, request.field_name, value)
    row.validation_status = "pass"
    session.add(
        UserCorrectionRow(
            id=str(uuid4()),
            job_id=job_id,
            record_id=record_id,
            field_name=request.field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=request.value,
        )
    )
    session.commit()
    session.refresh(row)
    return ImportService._holding_model(row)
