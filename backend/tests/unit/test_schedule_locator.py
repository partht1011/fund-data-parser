from app.document.schedule_locator import ScheduleLocator


def test_locator_merges_continuations_and_stops_at_next_fund(load_config, make_pages):
    config = load_config("hartford")
    pages = make_pages(
        [
            [
                "The Hartford Balanced Income Fund",
                "Schedule of Investments",
                "April 30, 2025 (Unaudited)",
            ],
            [
                "The Hartford Balanced Income Fund",
                "Schedule of Investments – (continued)",
            ],
            ["The Hartford Checks and Balances Fund", "Schedule of Investments"],
        ]
    )
    ranges = ScheduleLocator().locate(pages, config)
    assert len(ranges) == 1
    assert ranges[0].start_page == 1
    assert ranges[0].end_page == 2
    assert ranges[0].report_date.isoformat() == "2025-04-30"


def test_locator_recognizes_statement_heading_split_across_columns(
    load_config, make_pages
):
    config = load_config("gsam")
    pages = make_pages(
        [
            [
                "GOLDMAN SACHS INTERNATIONAL EQUITY INCOME FUND",
                "Schedule of Investments",
                "April 30, 2024 (Unaudited)",
            ],
            ["Shares Dividend Rate Value", "NET ASSETS – 100.0%"],
            ["Statements of Assets and", "Liabilities", "April 30, 2024"],
        ]
    )
    ranges = ScheduleLocator().locate(pages, config)
    assert [(item.start_page, item.end_page) for item in ranges] == [(1, 2)]
