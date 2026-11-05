"""Persistence baselines and storm-event counting, shared by the EDA and later evaluation."""

import pandas as pd

STORM_KP = 5.0
INTERVAL = pd.Timedelta(hours=3)

# Lag in Kp intervals between the persisted value and the interval being forecast.
LAST_COMPLETED = 1  # Kp of [t-3h, t): stronger, but ignores the GFZ publication delay
LAST_PUBLISHED = 2  # Kp of [t-6h, t-3h): assumed complete and published before t (see EDA section 3)


def score_persistence(kp: pd.Series, lag: int, years: range | list[int] | None = None) -> dict:
    """Score "Kp(next interval) = Kp `lag` intervals earlier"; kp is indexed by interval start."""
    frame = pd.DataFrame({"actual": kp, "predicted": kp.shift(freq=lag * INTERVAL)}).dropna()
    if years is not None:
        frame = frame[frame.index.year.isin(list(years))]
    actual_storm = frame["actual"] >= STORM_KP
    predicted_storm = frame["predicted"] >= STORM_KP
    hits = int((actual_storm & predicted_storm).sum())
    return {
        "intervals": len(frame),
        "mae": (frame["actual"] - frame["predicted"]).abs().mean(),
        "storm_intervals": int(actual_storm.sum()),
        "storm_rate": actual_storm.mean(),
        "recall": hits / actual_storm.sum() if actual_storm.any() else float("nan"),
        "precision": hits / predicted_storm.sum() if predicted_storm.any() else float("nan"),
    }


def count_storm_events(kp: pd.Series, gap: pd.Timedelta = pd.Timedelta(hours=24)) -> int:
    """Independent storms: storm intervals (Kp >= 5) less than `gap` apart count as one event."""
    storm_times = kp.index[kp >= STORM_KP].sort_values()
    if len(storm_times) == 0:
        return 0
    return int((pd.Series(storm_times).diff() >= gap).sum()) + 1
