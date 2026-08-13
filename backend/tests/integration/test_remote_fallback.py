from pathlib import Path

from app.domain.enums import ParserSource
from app.extraction.parser import HoldingParser
from app.validation.validator import Validator, should_use_remote


class FakeRemoteAdapter:
    available = True

    def __init__(self, pages):
        self.pages = pages
        self.calls: list[list[int]] = []

    def parse_pages(self, pdf_path: Path, pages: list[int], document_id: str):
        self.calls.append(pages)
        return self.pages


def test_failed_local_validation_calls_fake_remote_and_succeeds(load_config, make_pages, schedule):
    config = load_config("blackrock")
    range_ = schedule(config.display_name)
    parser = HoldingParser()
    validator = Validator()
    local_pages = make_pages([["Common Stocks", "Canada—6.5%", "Unreadable scan"]])
    local = parser.parse(local_pages, range_, config)
    local_validations = validator.validate(range_, local)
    assert should_use_remote(local_validations)

    remote_pages = make_pages(
        [["Common Stocks", "Canada—6.5%", "Teck Resources Ltd., Class B 742,465 25,387,670"]],
        source="mistral",
    )
    remote = FakeRemoteAdapter(remote_pages)
    retry_pages = remote.parse_pages(Path("fixture.pdf"), [1], "doc-1")
    retried = parser.parse(retry_pages, range_, config, ParserSource.REMOTE)
    retried_validations = validator.validate(range_, retried)

    assert remote.calls == [[1]]
    assert not should_use_remote(retried_validations)
    assert retried.holdings[0].parser_source == ParserSource.REMOTE
