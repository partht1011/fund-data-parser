from datetime import date
from pathlib import Path

import pytest

from app.config.repository import ConfigRepository
from app.config.schema import FundConfig
from app.document.page_model import PageBlock, ParsedPage
from app.domain.models import BoundingBox, ScheduleRange


@pytest.fixture
def load_config():
    defaults = Path(__file__).parents[1] / "app" / "config" / "defaults"

    def load(name: str) -> FundConfig:
        return ConfigRepository._load_yaml((defaults / f"{name}.yaml").read_text(encoding="utf-8"))

    return load


@pytest.fixture
def make_pages():
    def make(lines_by_page: list[list[str]], source: str = "docling") -> list[ParsedPage]:
        pages = []
        for page_number, lines in enumerate(lines_by_page, 1):
            pages.append(
                ParsedPage(
                    page_number=page_number,
                    width=594,
                    height=774,
                    source=source,
                    blocks=[
                        PageBlock(
                            page_number=page_number,
                            text=text,
                            bbox=BoundingBox(x0=20, y0=40 + index * 10, x1=280, y1=48 + index * 10),
                            block_type="table",
                            row_index=index,
                            column_index=0,
                        )
                        for index, text in enumerate(lines)
                    ],
                )
            )
        return pages

    return make


@pytest.fixture
def schedule():
    def make(fund_name: str, end_page: int = 1) -> ScheduleRange:
        return ScheduleRange(
            fund_name=fund_name,
            report_date=date(2025, 8, 31),
            start_page=1,
            end_page=end_page,
        )

    return make
