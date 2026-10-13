-- Raw NOAA RTSW 1-min data, all spacecraft. Filtering to the active spacecraft
-- happens in the feature code, so the history of which one was active is kept.
-- `payload` holds the full original record; typed columns are the ones features use.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS raw_rtsw_wind (
    time_tag           TIMESTAMPTZ      NOT NULL,
    source             TEXT             NOT NULL,
    active             BOOLEAN          NOT NULL,
    proton_speed       DOUBLE PRECISION,
    proton_density     DOUBLE PRECISION,
    proton_temperature DOUBLE PRECISION,
    overall_quality    INTEGER,
    payload            JSONB            NOT NULL,
    fetched_at         TIMESTAMPTZ      NOT NULL DEFAULT now(),
    PRIMARY KEY (time_tag, source)
);
SELECT create_hypertable('raw_rtsw_wind', by_range('time_tag', INTERVAL '7 days'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS raw_rtsw_mag (
    time_tag        TIMESTAMPTZ      NOT NULL,
    source          TEXT             NOT NULL,
    active          BOOLEAN          NOT NULL,
    bt              DOUBLE PRECISION,
    bx_gsm          DOUBLE PRECISION,
    by_gsm          DOUBLE PRECISION,
    bz_gsm          DOUBLE PRECISION,
    overall_quality INTEGER,
    payload         JSONB            NOT NULL,
    fetched_at      TIMESTAMPTZ      NOT NULL DEFAULT now(),
    PRIMARY KEY (time_tag, source)
);
SELECT create_hypertable('raw_rtsw_mag', by_range('time_tag', INTERVAL '7 days'), if_not_exists => TRUE);
