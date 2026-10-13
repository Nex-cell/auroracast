from datetime import datetime, timezone

from auroracast.ingest.rtsw import FEEDS, parse_records, parse_time_tag

WIND_COLUMNS = FEEDS["wind"][2]

# Trimmed records as returned by rtsw_wind_1m.json
ACTIVE = {"time_tag": "2026-10-01T12:41:00", "active": True, "source": "SOLAR1",
          "proton_speed": 296.3, "proton_density": 3.15, "proton_temperature": 39364, "overall_quality": 0}
INACTIVE = {"time_tag": "2026-10-02T12:37:04", "active": False, "source": "IMAP",
            "proton_speed": 284.57, "proton_density": 9.03, "proton_temperature": 37044, "overall_quality": 0}


def test_parse_time_tag_is_utc():
    assert parse_time_tag("2026-10-02T12:37:04") == datetime(2026, 10, 2, 12, 37, 4, tzinfo=timezone.utc)
    assert parse_time_tag("2026-10-02T14:37:04+02:00") == datetime(2026, 10, 2, 12, 37, 4, tzinfo=timezone.utc)


def test_parse_records_keeps_all_spacecraft():
    rows = parse_records([ACTIVE, INACTIVE], WIND_COLUMNS)
    assert [(r[1], r[2]) for r in rows] == [("SOLAR1", True), ("IMAP", False)]
    assert rows[0][3:7] == (296.3, 3.15, 39364, 0)
    assert rows[0][-1].obj == ACTIVE  # full record kept as payload


def test_parse_records_skips_incomplete_and_tolerates_missing_fields():
    rows = parse_records([{"source": "ACE"}, {"time_tag": "2026-10-02T00:00:00", "source": "ACE"}], WIND_COLUMNS)
    assert len(rows) == 1
    assert rows[0][2] is False
    assert rows[0][3:7] == (None, None, None, None)
