"""Ingest the planetary Kp index from GFZ Potsdam into the `kp` table.

Live mode (default) re-fetches the last `live_lookback_days`. That picks up new and revised
preliminary values ('pre', published while an interval is still running) and the monthly
definitive values ('def'). Every change seen live is appended to `kp_revisions` with the time
it was seen, which is what "Kp published before t" (leakage rule 3) is reconstructed from.

Backfill mode loads history year by year. Those rows get no first_seen_at and no revisions,
because their publication was not observed.

Usage:
    python -m auroracast.ingest.kp                        # live poll
    python -m auroracast.ingest.kp --backfill 1998 2026   # history, inclusive years
"""

import argparse
import logging
from datetime import datetime, timedelta, timezone

import psycopg
import requests

from auroracast.config import load_config
from auroracast.db import connect, ensure_schema
from auroracast.ingest.rtsw import parse_time_tag

log = logging.getLogger(__name__)

STATUSES = {"pre", "def"}

# Upsert the latest values; only rows whose value or status changed are written, and (live mode
# only, seen_at not NULL) recorded in kp_revisions. Returns the number of new or changed intervals.
UPSERT_SQL = """
WITH incoming AS (
    SELECT * FROM unnest(%(ts)s::timestamptz[], %(kp)s::float8[], %(status)s::text[])
        AS t(interval_start, kp, status)
), changed AS (
    INSERT INTO kp AS cur (interval_start, kp, status, first_seen_at, updated_at)
    SELECT interval_start, kp, status, %(seen_at)s::timestamptz, now() FROM incoming
    ON CONFLICT (interval_start) DO UPDATE
        SET kp = EXCLUDED.kp, status = EXCLUDED.status, updated_at = now(),
            first_seen_at = COALESCE(cur.first_seen_at, EXCLUDED.first_seen_at)
        WHERE (cur.kp, cur.status) IS DISTINCT FROM (EXCLUDED.kp, EXCLUDED.status)
    RETURNING interval_start, kp, status
), revisions AS (
    INSERT INTO kp_revisions (interval_start, seen_at, kp, status)
    SELECT interval_start, %(seen_at)s::timestamptz, kp, status FROM changed
    WHERE %(seen_at)s::timestamptz IS NOT NULL
)
SELECT count(*) FROM changed
"""


def fetch(url: str, start: datetime, end: datetime, timeout: float) -> dict:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    resp = requests.get(url, params={"start": start.strftime(fmt), "end": end.strftime(fmt), "index": "Kp"},
                        timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def parse(payload: dict) -> list[tuple[datetime, float, str]]:
    """Validate the GFZ response (parallel lists datetime / Kp / status) into rows; bad rows are skipped."""
    times, values, statuses = payload["datetime"], payload["Kp"], payload["status"]
    if not len(times) == len(values) == len(statuses):
        raise ValueError(f"GFZ lists differ in length: {len(times)}/{len(values)}/{len(statuses)}")
    rows, bad = [], []
    for raw_ts, kp, status in zip(times, values, statuses):
        ts = parse_time_tag(raw_ts)
        on_grid = ts.hour % 3 == 0 and ts.minute == 0 and ts.second == 0
        on_thirds = kp is not None and abs(kp * 3 - round(kp * 3)) < 0.01
        if on_grid and on_thirds and 0 <= kp <= 9 and status in STATUSES:
            rows.append((ts, float(kp), status))
        else:
            bad.append((raw_ts, kp, status))
    if bad:
        log.warning("skipped %d invalid Kp rows, e.g. %s", len(bad), bad[:3])
    return rows


def upsert(conn: psycopg.Connection, rows: list[tuple], seen_at: datetime | None) -> int:
    if not rows:
        return 0
    ts, kp, status = map(list, zip(*rows))
    changed = conn.execute(UPSERT_SQL, {"ts": ts, "kp": kp, "status": status, "seen_at": seen_at}).fetchone()[0]
    conn.commit()
    return changed


def run_once(cfg: dict | None = None) -> int:
    """Live poll: re-fetch the lookback window and record what changed."""
    cfg = (cfg or load_config())["kp"]
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=cfg["live_lookback_days"])).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = parse(fetch(cfg["url"], start, now, cfg["request_timeout_seconds"]))
    with connect() as conn:
        changed = upsert(conn, rows, seen_at=now)
    log.info("kp live: %d intervals fetched (%s .. %s), %d new or changed",
             len(rows), rows[0][0] if rows else None, rows[-1][0] if rows else None, changed)
    return changed


def backfill(first_year: int, last_year: int, cfg: dict | None = None) -> int:
    """Load history year by year (inclusive); one request and one commit per year."""
    cfg = (cfg or load_config())["kp"]
    now = datetime.now(timezone.utc)
    total = 0
    with connect() as conn:
        for year in range(first_year, last_year + 1):
            start = datetime(year, 1, 1, tzinfo=timezone.utc)
            end = min(datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc), now)
            if start > now:
                break
            rows = parse(fetch(cfg["url"], start, end, cfg["request_timeout_seconds"]))
            changed = upsert(conn, rows, seen_at=None)
            total += changed
            log.info("kp backfill %d: %d intervals fetched, %d new or changed", year, len(rows), changed)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backfill", nargs=2, type=int, metavar=("FIRST_YEAR", "LAST_YEAR"),
                        help="load history for these years (inclusive) instead of a live poll")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    with connect() as conn:
        ensure_schema(conn)
    if args.backfill:
        backfill(*args.backfill)
    else:
        run_once()


if __name__ == "__main__":
    main()
