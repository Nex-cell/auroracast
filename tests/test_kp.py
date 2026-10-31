from datetime import datetime, timezone

import pytest

from auroracast.ingest.kp import parse


def payload(times, values, statuses):
    return {"datetime": times, "Kp": values, "status": statuses, "meta": {"source": "GFZ Potsdam"}}


def test_parse_valid_rows():
    rows = parse(payload(["2024-05-10T21:00:00Z", "2026-10-31T12:00:00Z"], [8.333, 2.333], ["def", "pre"]))
    assert rows == [
        (datetime(2024, 5, 10, 21, tzinfo=timezone.utc), 8.333, "def"),
        (datetime(2026, 10, 31, 12, tzinfo=timezone.utc), 2.333, "pre"),
    ]


@pytest.mark.parametrize("ts, kp, status", [
    ("2026-10-31T13:00:00Z", 2.0, "def"),    # not on the 3-hour grid
    ("2026-10-31T12:00:00Z", 9.333, "def"),  # out of range
    ("2026-10-31T12:00:00Z", 2.5, "def"),    # not a third
    ("2026-10-31T12:00:00Z", None, "def"),   # missing value
    ("2026-10-31T12:00:00Z", 2.0, "xyz"),    # unknown status
])
def test_parse_skips_invalid_rows(ts, kp, status):
    assert parse(payload([ts], [kp], [status])) == []


def test_parse_rejects_mismatched_lists():
    with pytest.raises(ValueError):
        parse(payload(["2026-10-31T12:00:00Z"], [2.0, 3.0], ["pre"]))
