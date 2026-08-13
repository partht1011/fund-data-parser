from typing import Literal

from pydantic import BaseModel

from app.domain.models import BoundingBox


class PageBlock(BaseModel):
    page_number: int
    text: str
    bbox: BoundingBox | None = None
    block_type: Literal["text", "title", "table", "header", "footer", "unknown"]
    row_index: int | None = None
    column_index: int | None = None


class ParsedPage(BaseModel):
    page_number: int
    width: float | None = None
    height: float | None = None
    blocks: list[PageBlock]
    source: Literal["liteparse", "docling", "mistral"]

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.blocks)
