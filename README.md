# auroracast

## Updates / Info for lecturers

> This section is where I post updates and notes for you ahead of each milestone (MS).
> Newest entry first; everything below it documents the project itself.

### 2026-11-05 (MS2)

- Host decided: Infomaniak Ubuntu VM on free credits, as the server deal did not work out. TimescaleDB and the
  OMNI (1998-2026) and Kp backfills run there.
- The server polls RTSW and Kp hourly itself, with data from 14 Oct, later than the requested early
  October because I was sick. GitHub Actions into a temporary Tiger Cloud database keeps running as a backup.
- EDA with both persistence variants and the frozen targets: see "Frozen targets" and notebooks/01_eda.ipynb.
- Not done yet: the shared feature module, nowcast vs definitive (no data yet), a full OMNI vs RTSW
  comparison (only 33 overlapping hours), NOAA forecast logging.

### 2026-10-14
- Live solar-wind collection (NOAA RTSW, wind + magnetic field) has been running since 14 Oct 2026.
  The feed only keeps ~24 h, so it is persisted hourly into TimescaleDB. For now it runs on my laptop
  and will move to the cloud VM once that is set up.

  Progress has been slowed due to me being sick from early to mid oktober.

  Also I am negotiating a deal on a cloud VM for running this and other services. Wich is why data collection is still only local.
  If the deal doesnt workout there is free credit as a fallback.

## Frozen targets and decision thresholds

Frozen on 2026-11-05 from 1998-2023 data only, before any model or baseline was scored on the test
set (2024-2025). The analysis is in [notebooks/01_eda.ipynb](notebooks/01_eda.ipynb).

**Persistence measured both ways** (Kp units; a storm is Kp >= 5):

| Variant | Period | MAE | Storm recall | Storm precision |
|---|---|---|---|---|
| Last completed interval, `[t-3h, t)` | 1998-2023 | 0.627 | 0.522 | 0.522 |
| Last completed interval, `[t-3h, t)` | 2020-2023 | 0.631 | 0.415 | 0.415 |
| Last published, `[t-6h, t-3h)` | 1998-2023 | 0.806 | 0.383 | 0.383 |
| Last published, `[t-6h, t-3h)` | 2020-2023 | 0.812 | 0.250 | 0.250 |

Storm base rate: 2.64 % of intervals in 1998-2023, 1.40 % in 2020-2023.

Independent storm events (storm intervals under 24 h apart count as one): 533 in training, 77 in
validation, 61 in the test years. Only this count was taken from the test years, and final results
will state the per-event hit rate out of those 61 events.

**Frozen rules**, evaluated once on the test set:

| Item | Rule |
|---|---|
| Baseline | Last completed interval, the stronger variant, scored on the test set |
| Storm | Kp >= 5.0 (`5-` = 4.67 does not count) |
| Minimum | Lower MAE than the baseline, and higher storm recall at equal or better precision |
| Target | MAE at least 10 % below the baseline, and storm recall >= max(0.50, baseline recall) at precision >= max(0.40, baseline precision) |
| Stretch | MAE at least 15 % below the baseline |
| Decision threshold | Set on validation (2020-2023) only: the highest recall with precision >= 0.50, then applied unchanged to the test set |
| Live | Rolling 30-day MAE below persistence, and storm recall at equal precision compared with NOAA's Kp forecast, shown on the dashboard |

The proposal's target of recall >= 0.50 at precision >= 0.40 is weaker than persistence on 1998-2023,
so those values remain only as floors and the model must also match the baseline. Logging of NOAA's
forecast for the live comparison is not built yet.

## What runs where

| Part | Where | How |
|---|---|---|
| TimescaleDB with all data | Infomaniak Ubuntu VM | Docker Compose |
| RTSW solar wind, hourly | VM | `rtsw-collector` container, which loops by itself |
| GFZ Kp, hourly | VM | crontab entry |
| Backup of both polls | GitHub Actions into Tiger Cloud | `.github/workflows/rtsw-poller.yml` |

The reasons for this setup and how it evolved are in [DECISIONS.md](DECISIONS.md). No forecasting model or
feature pipeline exists yet.

## Setup from a fresh clone

You need Docker with Compose, and Python 3.12 or newer for the tests and the notebook.

### 1. Configure and start

```bash
cp .env.sample .env                    # then set real values; the variables are explained in that file
docker compose up -d --build           # starts TimescaleDB and the RTSW collector
docker compose logs -f rtsw-collector  # expect one "upserted N rows" line per feed per hour
```

The collector creates all database tables when it starts. NOAA's real-time feed only keeps the last ~24 h,
so polls must not be more than about 20 hours apart, or that data is lost for good.

By default the database lives in the Docker volume `auroracast_timescale_data`. To use another location, set
`TIMESCALE_DATA_PATH` to an absolute path before the first start. `docker compose down` keeps the data;
`docker compose down -v` deletes the Docker volume.

### 2. Load history

```bash
docker compose run --rm rtsw-collector python -m auroracast.ingest.kp --backfill 1998 2026
docker compose run -d --name omni-backfill rtsw-collector python -m auroracast.ingest.omni --years 1998 2026
docker logs -f omni-backfill
```

The Kp backfill takes about a minute. OMNI downloads one ~160 MB file per year and uses about 3 GB in the
database. It keeps running if your SSH session drops. Both are safe to rerun; for OMNI, remove the old
container first with `docker rm omni-backfill`.

### 3. Poll Kp hourly

The Kp ingest runs once and exits, so schedule it with `crontab -e`, using your project path:

```
17 * * * * cd /path/to/auroracast && docker compose run --rm rtsw-collector python -m auroracast.ingest.kp >> /tmp/kp.log 2>&1
```

### 4. Connect to the database

Postgres only listens on `127.0.0.1`, so from another machine use an SSH tunnel and leave it running:

```bash
ssh -N -L 15432:localhost:5432 <user>@<server-ip>
```

The database is then at `localhost:15432`. Use the port from `docker compose port timescaledb 5432` if you
changed `POSTGRES_HOST_PORT`. On WSL, a tunnel opened in PowerShell is not reachable from WSL.

### 5. Reproduce the EDA

Needs the backfills from step 2. With the tunnel open, run this from the project folder. `read` waits
silently for the database password.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-eda.txt
read -rs PW && PYTHONPATH="$PWD/src" DATABASE_URL= POSTGRES_HOST=localhost POSTGRES_PORT=15432 \
  POSTGRES_DB=<db> POSTGRES_USER=<user> POSTGRES_PASSWORD="$PW" \
  .venv/bin/python -m nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb
```

### 6. Optional: the GitHub Actions backup

Add the repository secret `DATABASE_URL` with the connection URL of a hosted TimescaleDB. The workflow then
polls RTSW and Kp into it hourly. Scheduled runs can be late, which is harmless because each run fetches the
full ~24 h window. GitHub disables scheduled workflows after about 60 days without repository activity.

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```
