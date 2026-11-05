from datetime import datetime, timezone

from auroracast.ingest.omni import COLUMNS, parse_line, parse_lines

# Real lines from omni_min2024.asc: IMF only (plasma filled), then IMF + plasma.
IMF_ONLY = "2024   1  0  0 51 99   2 999 100   6207      9  0.01 999999    5.34    4.12   -3.34   -0.66   -3.08   -1.45    0.01    0.04 99999.9 99999.9 99999.9 99999.9 999.99 9999999. 99.99 999.99 999.99 999.9 9999.99 9999.99 9999.99   13.86   -0.88   -0.83    20   -10    10     0    -1     6    10   0.19 99.9"
BOTH = "2024   1  0  3 51 51   7   1 100   6288      9  0.02     47    5.34    4.10   -3.34   -0.60   -3.09   -1.39    0.01    0.38   304.4  -303.6    -9.7    19.9   7.87   35314.  1.46   0.42   1.88   8.0  255.89   23.69   12.84   13.91   -0.87   -0.90    20   -10    10     0     0     6     9   0.14  4.9"


def row(line):
    return dict(zip(COLUMNS, parse_line(line)))


def test_parse_line_reads_measurements():
    r = row(BOTH)
    assert r["time_tag"] == datetime(2024, 1, 1, 0, 3, tzinfo=timezone.utc)
    assert (r["imf_source"], r["plasma_source"], r["timeshift_s"]) == (51, 51, 6288)
    assert (r["bt"], r["bx_gsm"], r["by_gsm"], r["bz_gsm"]) == (5.34, 4.10, -3.09, -1.39)
    assert (r["flow_speed"], r["density"], r["temperature"]) == (304.4, 7.87, 35314.0)
    assert (r["flow_pressure"], r["ey"]) == (1.46, 0.42)


def test_parse_line_turns_fill_values_into_null():
    r = row(IMF_ONLY)
    assert r["plasma_source"] is None
    assert r["bz_gsm"] == -1.45
    assert all(r[c] is None for c in ("flow_speed", "density", "temperature", "flow_pressure", "ey"))


def test_day_of_year_handles_leap_years():
    line = "2024 366 23 59" + BOTH[14:]
    assert row(line)["time_tag"] == datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc)


def test_minutes_without_any_measurement_are_dropped():
    empty = IMF_ONLY.replace("    5.34    4.12   -3.34   -0.66   -3.08   -1.45",
                             " 9999.99 9999.99 9999.99 9999.99 9999.99 9999.99")
    assert parse_line(empty) is None
    assert len(list(parse_lines([empty, BOTH]))) == 1
