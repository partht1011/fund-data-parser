from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class FileStorage:
    def __init__(self, data_dir: Path) -> None:
        self.documents_dir = data_dir / "documents"
        self.remote_dir = data_dir / "remote-responses"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.remote_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, upload: UploadFile) -> tuple[str, Path, int]:
        document_id = str(uuid4())
        target = self.documents_dir / f"{document_id}.pdf"
        size = 0
        with target.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                output.write(chunk)
        return document_id, target, size

    def remote_response_path(self, document_id: str, pages: list[int]) -> Path:
        suffix = "-".join(str(page) for page in pages)
        return self.remote_dir / f"{document_id}-pages-{suffix}.json"
