"""Poll the NOAA SWPC real-time solar wind (RTSW) feeds and persist them in TimescaleDB.

The feeds only cover the last ~24 h, so anything not stored here is lost for good.
Rows from all spacecraft are kept together with their `active` flag; the feature code
filters to the active spacecraft. Upserts are idempotent, so overlapping polls are harmless.

Usage:
    python -m auroracast.ingest.rtsw          # one poll (what an Airflow task will call)
    python -m auroracast.ingest.rtsw --loop   # poll forever at the configured interval
"""

import argparse
import logging
import time
from datetime import datetime, timezone

import psycopg
import requests
from psycopg.types.json import Jsonb

from auroracast.config import load_config
from auroracast.db import connect, ensure_schema

log = logging.getLogger(__name__)

# feed name -> (table, config key for the URL, typed columns copied out of the record)
FEEDS = {
    "wind": ("raw_rtsw_wind", "wind_url", ["proton_speed", "proton_density", "proton_temperature", "overall_quality"]),
    "mag": ("raw_rtsw_mag", "mag_url", ["bt", "bx_gsm", "by_gsm", "bz_gsm", "overall_quality"]),
}


def parse_time_tag(value: str) -> datetime:
    """NOAA time tags are UTC ISO strings without offset, e.g. '2026-10-02T12:37:04'."""
    ts = datetime.fromisoformat(value)
    return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)


def parse_records(records: list[dict], columns: list[str]) -> list[tuple]:
    """Turn feed records into DB rows; records without time_tag or source are skipped."""
    rows = []
    for rec in records:
        if not rec.get("time_tag") or not rec.get("source"):
            continue
        rows.append(
            (parse_time_tag(rec["time_tag"]), rec["source"], bool(rec.get("active")))
            + tuple(rec.get(c) for c in columns)
            + (Jsonb(rec),)
        )
    skipped = len(records) - len(rows)
    if skipped:
        log.warning("skipped %d records without time_tag/source", skipped)
    return rows


def fetch(url: str, timeout: float) -> list[dict]:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f"unexpected payload from {url}: {type(data).__name__}")
    return data


def upsert(conn: psycopg.Connection, table: str, columns: list[str], rows: list[tuple]) -> None:
    all_cols = ["time_tag", "source", "active", *columns, "payload"]
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in all_cols[2:])
    sql = (
        f"INSERT INTO {table} ({', '.join(all_cols)}) VALUES ({', '.join(['%s'] * len(all_cols))}) "
        f"ON CONFLICT (time_tag, source) DO UPDATE SET {updates}, fetched_at = now()"
    )
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()


def run_once(cfg: dict | None = None) -> dict[str, int]:
    """Fetch both feeds and upsert them. Raises if any feed failed, after trying all of them."""
    cfg = (cfg or load_config())["rtsw"]
    counts, errors = {}, []
    with connect() as conn:
        for name, (table, url_key, columns) in FEEDS.items():
            try:
                rows = parse_records(fetch(cfg[url_key], cfg["request_timeout_seconds"]), columns)
                upsert(conn, table, columns, rows)
                counts[name] = len(rows)
                newest = max((r[0] for r in rows), default=None)
                log.info("%s: upserted %d rows into %s, newest %s", name, len(rows), table, newest)
            except Exception as exc:
                conn.rollback()
                log.exception("%s: ingest failed", name)
                errors.append(f"{name}: {exc}")
    if errors:
        raise RuntimeError("RTSW ingest failed for " + "; ".join(errors))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--loop", action="store_true", help="poll forever at the configured interval")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg = load_config()
    with connect() as conn:
        ensure_schema(conn)

    if not args.loop:
        run_once(cfg)
        return
    interval = cfg["rtsw"]["poll_interval_seconds"]
    while True:
        try:
            run_once(cfg)
        except Exception:
            log.exception("poll failed; retrying in %d s", interval)
        time.sleep(interval)


if __name__ == "__main__":
    main()
