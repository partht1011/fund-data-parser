from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.dependencies import remote_adapter
from app.document.mistral_adapter import RemoteDocumentParser
from app.domain.models import ParseResult
from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.storage.database import get_session

router = APIRouter(tags=["exports"])


def _result(job_id: str, session: Session, remote: RemoteDocumentParser) -> ParseResult:
    try:
        return ImportService(session, remote).result(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/export.json")
def export_json(
    job_id: str,
    session: Session = Depends(get_session),
    remote: RemoteDocumentParser = Depends(remote_adapter),
) -> Response:
    content = ExportService.as_json(_result(job_id, session, remote))
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.json"'},
    )


@router.get("/jobs/{job_id}/export.csv")
def export_csv(
    job_id: str,
    session: Session = Depends(get_session),
    remote: RemoteDocumentParser = Depends(remote_adapter),
) -> Response:
    content = ExportService.as_csv(_result(job_id, session, remote))
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.csv"'},
    )
