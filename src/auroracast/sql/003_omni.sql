-- NASA OMNI high-resolution 1-min solar wind (history for training). Values are already
-- time-shifted to the bow shock nose; timeshift_s is the applied shift, so the L1 observation
-- time is roughly time_tag - timeshift_s. Fill values are stored as NULL.
-- Minutes without any IMF or plasma measurement are not stored.

CREATE TABLE IF NOT EXISTS omni_1min (
    time_tag      TIMESTAMPTZ      NOT NULL PRIMARY KEY,
    imf_source    SMALLINT,
    plasma_source SMALLINT,
    timeshift_s   INTEGER,
    bt            DOUBLE PRECISION,
    bx_gsm        DOUBLE PRECISION,
    by_gsm        DOUBLE PRECISION,
    bz_gsm        DOUBLE PRECISION,
    flow_speed    DOUBLE PRECISION,
    density       DOUBLE PRECISION,
    temperature   DOUBLE PRECISION,
    flow_pressure DOUBLE PRECISION,
    ey            DOUBLE PRECISION
);
SELECT create_hypertable('omni_1min', by_range('time_tag', INTERVAL '365 days'), if_not_exists => TRUE);
