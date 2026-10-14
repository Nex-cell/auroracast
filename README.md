# auroracast

## Updates / Info for lecturers

> This section is where I post updates and notes for you ahead of each milestone (MS).
> Newest entry first; everything below it documents the project itself.

### 2026-10-14
- Live solar-wind collection (NOAA RTSW, wind + magnetic field) has been running since 14 Oct 2026.
  The feed only keeps ~24 h, so it is persisted hourly into TimescaleDB. For now it runs on my laptop
  and will move to the cloud VM once that is set up.

  Progress has been slowed due to me being sick from early to mid oktober.

  Also I am negotiating a deal on a cloud VM for running this and other services. Wich is why data collection is still only local.
  If the deal doesnt workout there is free credit as a fallback.
  
## Live RTSW collector

NOAA's real-time solar-wind feeds only keep the last ~24 h, so a collector polls them hourly
and stores every row in TimescaleDB (`raw_rtsw_wind`, `raw_rtsw_mag`).

```bash
cp .env.sample .env                   # then set real values
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
