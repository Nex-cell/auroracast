import pandas as pd
import pytest

from auroracast.baseline import LAST_COMPLETED, LAST_PUBLISHED, count_storm_events, score_persistence


def series(values, start="2020-01-01"):
    index = pd.date_range(start, periods=len(values), freq="3h", tz="UTC")
    return pd.Series(values, index=index, dtype=float)


def test_last_completed_uses_previous_interval():
    s = score_persistence(series([1, 2, 4]), LAST_COMPLETED)
    assert s["intervals"] == 2
    assert s["mae"] == pytest.approx(1.5)  # |2-1|, |4-2|


def test_last_published_uses_interval_before_that():
    s = score_persistence(series([1, 2, 4]), LAST_PUBLISHED)
    assert s["intervals"] == 1
    assert s["mae"] == pytest.approx(3)  # |4-1|


def test_lag_respects_time_not_row_position():
    kp = series([1, 2, 4]).drop(series([1, 2, 4]).index[1])  # middle interval missing
    assert score_persistence(kp, LAST_COMPLETED)["intervals"] == 0


def test_storm_recall_and_precision():
    s = score_persistence(series([1, 5, 6, 1, 5]), LAST_COMPLETED)
    # actual storms at positions 1, 2, 4; predicted storms at 2, 3 -> one hit
    assert s["storm_intervals"] == 3
    assert s["recall"] == pytest.approx(1 / 3)
    assert s["precision"] == pytest.approx(1 / 2)


def test_year_filter():
    kp = pd.concat([series([1, 2], "2019-12-31 21:00"), series([4], "2020-01-01 03:00")])
    assert score_persistence(kp, LAST_COMPLETED, years=[2020])["intervals"] == 2


def test_storm_events_merge_close_intervals():
    kp = series([5] + [0] * 3 + [5] + [0] * 8 + [6, 6])  # 12 h apart merges, then 27 h apart splits
    assert count_storm_events(kp) == 2
    assert count_storm_events(series([0, 1])) == 0
