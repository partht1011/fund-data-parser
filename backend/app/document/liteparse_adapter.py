"""Local PDF adapter.

The production path prefers LiteParse. The lightweight prototype uses pdfplumber's
positioned words as a compatibility backend when LiteParse is not installed. Both
paths terminate at ParsedPage, so provider types never enter the business parser.
"""

from collections.abc import Iterable
from pathlib import Path
from statistics import median
from typing import Any

import pdfplumber

from app.config.schema import LayoutHints
from app.document.page_model import PageBlock, ParsedPage
from app.domain.models import BoundingBox


def _group_lines(words: Iterable[dict[str, Any]], tolerance: float = 3.0) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    row_tops: list[float] = []
    for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
        top = float(word["top"])
        target = next((i for i, row_top in enumerate(row_tops) if abs(row_top - top) <= tolerance), None)
        if target is None:
            rows.append([word])
            row_tops.append(top)
        else:
            rows[target].append(word)
            row_tops[target] = median(float(item["top"]) for item in rows[target])
    pairs = zip(row_tops, rows, strict=True)
    return [sorted(row, key=lambda item: float(item["x0"])) for _, row in sorted(pairs)]


def _join_words(words: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    previous_x1: float | None = None
    for word in words:
        text = str(word["text"]).strip()
        if not text:
            continue
        gap = float(word["x0"]) - previous_x1 if previous_x1 is not None else 0
        if parts and gap > 1.2:
            parts.append(" ")
        parts.append(text)
        previous_x1 = float(word["x1"])
    return "".join(parts).strip()


class LiteParseAdapter:
    """Return positioned, column-aware lines using a local-only parser."""

    def parse(self, pdf_path: Path, page_numbers: list[int] | None = None, layout: LayoutHints | None = None) -> list[ParsedPage]:
        requested = set(page_numbers or [])
        hints = layout or LayoutHints()
        parsed: list[ParsedPage] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, 1):
                if requested and page_number not in requested:
                    continue
                words = page.extract_words(x_tolerance=1.5, y_tolerance=2.5, keep_blank_chars=False)
                columns = self._split_columns(words, float(page.width), hints)
                blocks: list[PageBlock] = []
                for column_index, column_words in enumerate(columns):
                    for row_index, row in enumerate(_group_lines(column_words)):
                        text = _join_words(row)
                        if not text:
                            continue
                        top = min(float(word["top"]) for word in row)
                        bottom = max(float(word["bottom"]) for word in row)
                        block_type = "header" if top < 28 else "footer" if bottom > float(page.height) - 28 else "table"
                        blocks.append(
                            PageBlock(
                                page_number=page_number,
                                text=text,
                                bbox=BoundingBox(
                                    x0=min(float(word["x0"]) for word in row),
                                    y0=top,
                                    x1=max(float(word["x1"]) for word in row),
                                    y1=bottom,
                                ),
                                block_type=block_type,
                                row_index=row_index,
                                column_index=column_index,
                            )
                        )
                parsed.append(
                    ParsedPage(
                        page_number=page_number,
                        width=float(page.width),
                        height=float(page.height),
                        blocks=blocks,
                        source="liteparse",
                    )
                )
        return parsed

    @staticmethod
    def _split_columns(words: list[dict[str, Any]], width: float, hints: LayoutHints) -> list[list[dict[str, Any]]]:
        if hints.columns == 1:
            return [words]
        split = width * hints.split_ratio
        left = [word for word in words if (float(word["x0"]) + float(word["x1"])) / 2 < split]
        right = [word for word in words if (float(word["x0"]) + float(word["x1"])) / 2 >= split]
        if hints.columns == 2:
            return [left, right]
        # Financial schedules have dense text in both halves. Avoid splitting cover or prose pages.
        left_rows = len(_group_lines(left))
        right_rows = len(_group_lines(right))
        if min(left_rows, right_rows) >= 8 and len(words) >= 40:
            return [left, right]
        return [words]
