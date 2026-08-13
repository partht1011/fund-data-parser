import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Protocol

import httpx

from app.core.settings import Settings
from app.document.page_model import PageBlock, ParsedPage
from app.domain.models import BoundingBox

logger = logging.getLogger(__name__)


class RemoteDocumentParser(Protocol):
    @property
    def available(self) -> bool: ...

    def parse_pages(self, pdf_path: Path, pages: list[int], document_id: str) -> list[ParsedPage]: ...


class DisabledRemoteAdapter:
    available = False

    def parse_pages(self, pdf_path: Path, pages: list[int], document_id: str) -> list[ParsedPage]:
        return []


class MistralOcrAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def available(self) -> bool:
        return bool(self.settings.mistral_api_key)

    def parse_pages(self, pdf_path: Path, pages: list[int], document_id: str) -> list[ParsedPage]:
        if not self.available:
            return []
        try:
            from mistralai.client import Mistral  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("Install the 'remote' dependency group to enable Mistral OCR") from exc

        started = time.perf_counter()
        http_client = httpx.Client(timeout=self.settings.remote_timeout_seconds)
        client = Mistral(api_key=self.settings.mistral_api_key, client=http_client)
        response: Any = None
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                encoded = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
                response = client.ocr.process(
                    model=self.settings.mistral_ocr_model,
                    document={
                        "type": "document_url",
                        "document_url": f"data:application/pdf;base64,{encoded}",
                    },
                    pages=[page - 1 for page in pages],
                    table_format="markdown",
                    include_blocks=True,
                    include_image_base64=False,
                )
                break
            except Exception as exc:  # provider errors are converted at this boundary
                last_error = exc
                if attempt == 0:
                    time.sleep(0.25)
        if response is None:
            http_client.close()
            raise RuntimeError(f"Mistral OCR failed after one retry: {last_error}")

        raw = response.model_dump(mode="json") if hasattr(response, "model_dump") else response
        raw_text = json.dumps(raw, default=str)
        response_path = self.settings.data_dir / "remote-responses" / f"{document_id}-pages-{'-'.join(map(str, pages))}.json"
        response_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.write_text(raw_text, encoding="utf-8")
        elapsed = time.perf_counter() - started
        logger.info(
            "remote OCR completed",
            extra={
                "context": {
                    "document_id": document_id,
                    "pages": pages,
                    "duration_seconds": round(elapsed, 3),
                    "provider_status": "success",
                    "response_size": len(raw_text),
                }
            },
        )
        http_client.close()
        return self._convert_response(raw, pages)

    @staticmethod
    def _convert_response(raw: Any, requested_pages: list[int]) -> list[ParsedPage]:
        raw_pages = raw.get("pages", []) if isinstance(raw, dict) else []
        parsed: list[ParsedPage] = []
        for index, item in enumerate(raw_pages):
            page_number = requested_pages[index] if index < len(requested_pages) else int(item.get("index", index)) + 1
            markdown = str(item.get("markdown", ""))
            blocks = [
                PageBlock(
                    page_number=page_number,
                    text=line.strip(" |"),
                    bbox=BoundingBox(x0=0, y0=float(row), x1=1, y1=float(row + 1)),
                    block_type="table" if "|" in line else "text",
                    row_index=row,
                    column_index=0,
                )
                for row, line in enumerate(markdown.splitlines())
                if line.strip(" |")
            ]
            parsed.append(ParsedPage(page_number=page_number, blocks=blocks, source="mistral"))
        return parsed
