"""Backfill NASA OMNI 1-min solar wind into the `omni_1min` hypertable, one yearly file at a time.

Each file (~160 MB) is downloaded to a temporary file, loaded and deleted again. Reruns are
safe: minutes already in the table are skipped.

Usage:
    python -m auroracast.ingest.omni --years 1998 2025   # inclusive
"""

import argparse
import logging
import tempfile
from collections.abc import Iterable, Iterator
from datetime import datetime, timedelta, timezone

import psycopg
import requests

from auroracast.config import load_config
from auroracast.db import connect, ensure_schema

log = logging.getLogger(__name__)

# Fixed-width layout from NASA's HRO_format.txt: name -> (start, end, fill value).
FIELDS = {
    "imf_source": (14, 17, 99),
    "plasma_source": (17, 20, 99),
    "timeshift_s": (32, 39, 999999),
    "bt": (59, 67, 9999.99),
    "bx_gsm": (67, 75, 9999.99),
    "by_gsm": (91, 99, 9999.99),
    "bz_gsm": (99, 107, 9999.99),
    "flow_speed": (123, 131, 99999.9),
    "density": (155, 162, 999.99),
    "temperature": (162, 171, 9999999.0),
    "flow_pressure": (171, 177, 99.99),
    "ey": (177, 184, 999.99),
}
INT_FIELDS = {"imf_source", "plasma_source", "timeshift_s"}
MEASUREMENTS = list(FIELDS)[3:]
COLUMNS = ["time_tag", *FIELDS]


def parse_line(line: str) -> tuple | None:
    """One file line -> table row, fill values as NULL; None if the minute has no measurement."""
    year, doy, hour, minute = int(line[:4]), int(line[4:8]), int(line[8:11]), int(line[11:14])
    ts = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=doy - 1, hours=hour, minutes=minute)
    values = {}
    for name, (start, end, fill) in FIELDS.items():
        value = float(line[start:end])
        values[name] = None if value >= fill else (int(value) if name in INT_FIELDS else value)
    if all(values[name] is None for name in MEASUREMENTS):
        return None
    return (ts, *values.values())


def parse_lines(lines: Iterable[str]) -> Iterator[tuple]:
    return (row for row in map(parse_line, lines) if row is not None)


def load_rows(conn: psycopg.Connection, rows: Iterable[tuple]) -> int:
    """Bulk-load through a temp table so existing minutes are skipped; returns rows newly inserted."""
    with conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE omni_load (LIKE omni_1min) ON COMMIT DROP")
        with cur.copy(f"COPY omni_load ({', '.join(COLUMNS)}) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
        cur.execute("INSERT INTO omni_1min SELECT * FROM omni_load ON CONFLICT (time_tag) DO NOTHING")
        inserted = cur.rowcount
    conn.commit()
    return inserted


def load_year(conn: psycopg.Connection, year: int, cfg: dict) -> int:
    url = cfg["url_template"].format(year=year)
    with tempfile.TemporaryFile("w+b") as tmp:
        with requests.get(url, stream=True, timeout=cfg["request_timeout_seconds"]) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=1 << 20):
                tmp.write(chunk)
        size_mb = tmp.tell() / 1e6
        tmp.seek(0)
        inserted = load_rows(conn, parse_lines(line.decode("ascii") for line in tmp))
    log.info("omni %d: %.0f MB downloaded, %d rows inserted", year, size_mb, inserted)
    return inserted


def backfill(first_year: int, last_year: int, cfg: dict | None = None) -> None:
    """Load the years in order; a failed year is logged and retried on the next run."""
    cfg = (cfg or load_config())["omni"]
    failed = []
    with connect() as conn:
        for year in range(first_year, last_year + 1):
            try:
                load_year(conn, year, cfg)
            except (requests.RequestException, psycopg.Error, ValueError) as exc:
                conn.rollback()
                log.exception("omni %d failed", year)
                failed.append(f"{year}: {exc}")
    if failed:
        raise RuntimeError("OMNI backfill incomplete, rerun for: " + "; ".join(failed))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs=2, type=int, required=True, metavar=("FIRST", "LAST"),
                        help="years to load (inclusive)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    with connect() as conn:
        ensure_schema(conn)
    backfill(*args.years)


if __name__ == "__main__":
    main()
