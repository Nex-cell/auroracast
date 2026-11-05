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
