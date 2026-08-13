import re
from datetime import date

from app.config.schema import FundConfig
from app.document.page_model import ParsedPage
from app.domain.models import ScheduleRange

DATE_PATTERN = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s*"
    r"(?P<day>\d{1,2}),\s*(?P<year>20\d{2})",
    re.IGNORECASE,
)
MONTHS = {
    name.lower(): index
    for index, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        1,
    )
}


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _heading_tokens(value: str) -> set[str]:
    stop_words = {"and", "of", "the", "to"}
    tokens = set()
    for word in re.findall(r"[a-z]+", value.lower()):
        normalized = re.sub(r"(.)\1{2,}", r"\1", word).rstrip("s")
        if normalized not in stop_words and len(normalized) > 2:
            tokens.add(normalized)
    return tokens


def _has_heading(page: ParsedPage, heading: str) -> bool:
    """Match headings even when a two-column PDF splits one title into blocks."""
    if _compact(heading) in _compact(page.text):
        return True
    positioned = [
        block.text
        for block in page.blocks
        if block.bbox is None or block.bbox.y0 <= 140
    ]
    top_text = " ".join(positioned[:20])
    expected = _heading_tokens(heading)
    actual = _heading_tokens(top_text)
    return bool(expected) and expected.issubset(actual)


class ScheduleLocator:
    def locate(self, pages: list[ParsedPage], config: FundConfig) -> list[ScheduleRange]:
        starts: list[int] = []
        for page in pages:
            text_key = _compact(page.text)
            has_schedule = any(_has_heading(page, heading) for heading in config.schedule_headings)
            has_fund = any(_compact(pattern) in text_key for pattern in config.fund_name_patterns)
            if has_schedule and has_fund:
                starts.append(page.page_number)
        if not starts:
            return []

        ranges: list[ScheduleRange] = []
        for start in starts:
            if ranges and start <= ranges[-1].end_page:
                continue
            end = start
            consecutive_pages_without_schedule_heading = 0
            report_date = self._find_date(pages, start)
            for page in (item for item in pages if item.page_number > start):
                page_key = _compact(page.text)
                if any(_has_heading(page, stop) for stop in config.stop_headings):
                    break
                has_schedule = any(
                    _has_heading(page, heading) for heading in config.schedule_headings
                )
                has_other_fund_schedule = has_schedule and not any(
                    _compact(pattern) in page_key for pattern in config.fund_name_patterns
                )
                if has_other_fund_schedule:
                    break
                if has_schedule:
                    consecutive_pages_without_schedule_heading = 0
                else:
                    consecutive_pages_without_schedule_heading += 1
                    if consecutive_pages_without_schedule_heading > 1:
                        break
                end = page.page_number
            ranges.append(
                ScheduleRange(
                    fund_name=config.display_name,
                    report_date=report_date,
                    start_page=start,
                    end_page=end,
                )
            )
        return ranges

    @staticmethod
    def _find_date(pages: list[ParsedPage], start: int) -> date | None:
        candidates = [page for page in pages if start - 1 <= page.page_number <= start + 1]
        for page in candidates:
            match = DATE_PATTERN.search(page.text)
            if match:
                return date(
                    int(match.group("year")),
                    MONTHS[match.group("month").lower()],
                    int(match.group("day")),
                )
        return None
