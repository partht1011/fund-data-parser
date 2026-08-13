from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.document.page_model import ParsedPage
from app.domain.enums import JobStatus
from app.services.import_service import ImportService
from app.storage.database import Base
from app.storage.models import DocumentRow, HoldingRow, ParseJobRow, ValidationRow


class StaticLocalAdapter:
    def __init__(self, pages: list[ParsedPage]) -> None:
        self.pages = pages

    def parse(self, pdf_path: Path, page_numbers=None, layout=None):
        return self.pages


class StaticDoclingAdapter:
    def __init__(self, pages: list[ParsedPage]) -> None:
        self.pages = pages

    def parse_pages(self, pdf_path: Path, pages: list[int], layout):
        return self.pages


class FailingRemoteAdapter:
    available = True

    def __init__(self) -> None:
        self.calls: list[list[int]] = []

    def parse_pages(self, pdf_path: Path, pages: list[int], document_id: str):
        self.calls.append(pages)
        raise TimeoutError("simulated provider outage")


def test_remote_failure_preserves_local_records_and_completes_for_review(
    make_pages,
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    pdf_path = Path("fixture.pdf")
    pages = make_pages(
        [[
            "BlackRock International Fund",
            "Schedule of Investments",
            "August 31, 2025",
            "Common Stocks",
            "Canada—6.5%",
            "Teck Resources Ltd., Class B 742,465 25,387,670",
            "12,345 Broken Security",
        ]]
    )
    document = DocumentRow(
        id="doc-1",
        original_filename="sample.pdf",
        storage_path=str(pdf_path),
        content_type="application/pdf",
        size_bytes=7,
    )
    job = ParseJobRow(
        id="job-1",
        document_id=document.id,
        fund_id="blackrock_international",
        status=JobStatus.QUEUED,
        current_stage="Queued",
    )
    session.add_all([document, job])
    session.commit()
    remote = FailingRemoteAdapter()

    ImportService(
        session,
        remote,
        local_adapter=StaticLocalAdapter(pages),
        docling_adapter=StaticDoclingAdapter(pages),
    ).run(job.id)

    assert job.status == JobStatus.COMPLETE
    assert job.current_stage == "Complete - review required"
    assert job.error_message is None
    assert job.holding_count == 1
    assert job.remote_page_count == 0
    assert job.remote_pages_json == "[]"
    assert remote.calls == [[1]]
    holding = session.scalars(select(HoldingRow)).one()
    assert holding.security_name == "Teck Resources Ltd., Class B"
    # An unresolved fragment is page-scoped; it must not contaminate a valid record.
    assert holding.validation_status == "pass"
    validation_codes = set(session.scalars(select(ValidationRow.code)).all())
    assert {"holding_row_incomplete", "remote_fallback_failed"} <= validation_codes
