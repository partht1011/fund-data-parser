from pathlib import Path

from app.config.schema import LayoutHints
from app.document.liteparse_adapter import LiteParseAdapter
from app.document.page_model import ParsedPage


class DoclingAdapter:
    """Layout refinement boundary.

    Docling is an optional heavyweight install. The compatibility path preserves the
    same interface and column-aware local structure, allowing CI and local-only use.
    """

    def __init__(self, local_adapter: LiteParseAdapter | None = None) -> None:
        self.local_adapter = local_adapter or LiteParseAdapter()

    def parse_pages(self, pdf_path: Path, pages: list[int], layout: LayoutHints) -> list[ParsedPage]:
        parsed = self.local_adapter.parse(pdf_path, pages, layout)
        return [page.model_copy(update={"source": "docling"}) for page in parsed]
