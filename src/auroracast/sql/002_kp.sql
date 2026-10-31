-- Planetary Kp index from GFZ Potsdam: latest known value per 3-hour interval.
-- status 'pre' = preliminary nowcast (published and revised while the interval is still running),
--        'def' = definitive (published monthly).
-- first_seen_at is when the live poller first saw the interval; NULL for backfilled history.

CREATE TABLE IF NOT EXISTS kp (
    interval_start TIMESTAMPTZ      PRIMARY KEY,
    kp             DOUBLE PRECISION NOT NULL,
    status         TEXT             NOT NULL CHECK (status IN ('pre', 'def')),
    first_seen_at  TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- Every value/status change observed by the live poller, with the time it was seen.
-- "Kp known at time t" = per interval, the latest revision with seen_at < t (leakage rule 3).
CREATE TABLE IF NOT EXISTS kp_revisions (
    interval_start TIMESTAMPTZ      NOT NULL,
    seen_at        TIMESTAMPTZ      NOT NULL,
    kp             DOUBLE PRECISION NOT NULL,
    status         TEXT             NOT NULL,
    PRIMARY KEY (interval_start, seen_at)
);
