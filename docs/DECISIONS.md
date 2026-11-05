# Decisions

Choices that changed or extended the proposal, newest first. The proposal fixes the target, baseline, data
sources, leakage rules and FTI structure, and allows tools, schedules and the provider to change with
justification.

## 2026-11-05: Freeze targets against the stronger persistence baseline

- **Decision:** the baseline is persistence on the last completed interval. The proposal's recall >= 0.50 at
  precision >= 0.40 stays only as a floor, and the model must also match the baseline. The full rules are in
  the [README](../README.md).
- **Why:** on 1998-2023 this variant scores MAE 0.627 and storm recall and precision of 0.52. "Last published"
  scores MAE 0.806, so 10 % below it would be worse than simply using the last completed interval. The
  proposal's storm target is also weaker than persistence. This follows feedback item A1.
- **Accepted risk:** the baseline ignores the GFZ publication delay, while model features may not. The first
  EDA also shows solar wind barely tracks the change in Kp, so the 10 % target may not be reached.

## 2026-11-05: Infomaniak VM as the host

- **Decision:** an Infomaniak Ubuntu VM on free credits runs TimescaleDB, the backfills and the live polls.
- **Why:** feedback item A4 asked for a decided provider. A negotiated server deal did not work out, and free
  credits were the planned fallback. Docker Compose keeps a later move cheap.
- **Details:** Postgres is not exposed to the internet and is reached through an SSH tunnel. Database files sit
  on an external volume through `TIMESCALE_DATA_PATH`.
- **Backup:** GitHub Actions and Tiger Cloud keep running alongside the VM.

## 2026-11-05: Load history directly into the VM database

- **Decision:** OMNI and historical Kp live on the VM, never on a free hosted tier. OMNI is stored in typed
  columns without the original record, and minutes with no measurements are skipped.
- **Why:** about 13 million rows before 2024 would not fit a 750 MB cap, and the files can be downloaded again
  at any time. Live RTSW keeps its full record because it cannot be fetched again.

## 2026-10-31: Record every Kp revision

- **Decision:** the live Kp poll appends each observed change to `kp_revisions` with the time it was seen.
- **Why:** GFZ's API gives no publication time, and it can publish a preliminary value while an interval is
  still running. The history of changes is what shows which Kp was known at `t` (leakage rule 3).
- **Limitation:** only observed from 2026-10-31. Earlier publication times are lost, and the backfill has
  definitive values only.

## 2026-10-15: Tiger Cloud and GitHub Actions as temporary persistent storage

- **Decision:** poll hourly from GitHub Actions into Tiger Cloud's free TimescaleDB until a VM exists.
- **Why:** feedback item E1 asked for the poller to run now, with persistent storage from the first run. The
  VM was not ready, and the laptop collector stops whenever the laptop is off, while missed RTSW data cannot be
  recovered. Tiger offers full TimescaleDB, the same as the target stack.
- **Rejected:**
  - Neon: reduced TimescaleDB, without compression or continuous aggregates.
  - Supabase: TimescaleDB deprecated on Postgres 17.
  - JSON snapshots as workflow artifacts: kept for at most 90 days and need a later import.
- **Limits:** 750 MB, read-only when full, about 3 months at the measured ~7.7 MiB per day, and free services
  are in beta. Runs are often late, which is harmless because each one fetches the full ~24 h window.

## 2026-10-14: Store all spacecraft, filter later

- **Decision:** RTSW rows from every spacecraft are stored with their `active` flag, and upserts on
  `(time_tag, source)` make repeated polls safe. The feature code will filter to the active spacecraft.
- **Why:** this keeps the record of which spacecraft was active and lets validation change later.

## 2026-10-14: Simpler core stack

- **Decision:** the core is TimescaleDB, a cron scheduler and Streamlit, with MLflow used as a library. Airflow
  and an MLflow server move to stretch.
- **Why:** feedback item A4 named four long-running services as the main risk for a solo project. The pipelines
  are plain Python, so Airflow can still be added later without rewriting them.
- **Status:** the single cron container is not built yet. Today the collector loops by itself and Kp uses the
  VM's crontab. MLflow, Streamlit and the rest of the pipeline are still to come.
