# auroracast

## Live RTSW collector

NOAA's real-time solar-wind feeds only keep the last ~24 h, so a collector polls them hourly
and stores every row in TimescaleDB (`raw_rtsw_wind`, `raw_rtsw_mag`).

```bash
cp env.sample .env                    # then set real values
docker compose up -d --build          # starts TimescaleDB + the collector
docker compose logs -f rtsw-collector # one "upserted N rows" line per feed per hour
```

Data lives in the Docker volume `auroracast_timescale_data`. `docker compose down` keeps it;
`docker compose down -v` deletes it.

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```
