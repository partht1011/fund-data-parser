from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import remote_adapter
from app.core.settings import get_settings
from app.document.mistral_adapter import RemoteDocumentParser
from app.domain.enums import JobStatus
from app.domain.models import DocumentResponse, JobResponse, ParseRequest
from app.services.import_service import ImportService
from app.storage.database import SessionLocal, get_session
from app.storage.files import FileStorage
from app.storage.models import DocumentRow, ParseJobRow

router = APIRouter(tags=["documents"])


def _run_import(job_id: str, remote: RemoteDocumentParser) -> None:
    with SessionLocal() as session:
        ImportService(session, remote).run(job_id)


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...), session: Session = Depends(get_session)
) -> DocumentRow:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted")
    storage = FileStorage(get_settings().data_dir)
    document_id, path, size = await storage.save_upload(file)
    if size == 0:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    if path.read_bytes()[:5] != b"%PDF-":
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail="File does not contain a valid PDF header")
    row = DocumentRow(
        id=document_id,
        original_filename=file.filename,
        storage_path=str(path.resolve()),
        content_type=file.content_type or "application/pdf",
        size_bytes=size,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, session: Session = Depends(get_session)) -> DocumentRow:
    row = session.get(DocumentRow, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return row


@router.post("/documents/{document_id}/parse", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def parse_document(
    document_id: str,
    request: ParseRequest,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    remote: RemoteDocumentParser = Depends(remote_adapter),
) -> ParseJobRow:
    if session.get(DocumentRow, document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    row = ParseJobRow(
        id=str(uuid4()),
        document_id=document_id,
        fund_id=request.fund_id,
        status=JobStatus.QUEUED,
        current_stage="Queued",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    background.add_task(_run_import, row.id, remote)
    return row
