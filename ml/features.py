"""Shared feature engineering. Used by training, live prediction AND analytics,
so the model always sees features built exactly the same way."""
import numpy as np
import pandas as pd

STEP_MIN = 30  # one time-step = 30 minutes
FEATURES = ["hour_float", "day_of_week", "is_weekend", "occupancy_pct",
            "occ_lag_30", "occ_change", "arrivals_30", "departures_30"]
DEMAND_LABELS = ["Low", "Medium", "High"]
LOW_MAX, MEDIUM_MAX = 40.0, 70.0  # occupancy % thresholds for demand level


def demand_from_occupancy(pct: float) -> str:
    """Rule used to create the demand label: <40% Low, 40-70% Medium, >=70% High."""
    return "Low" if pct < LOW_MAX else "Medium" if pct < MEDIUM_MAX else "High"


def _ns(series) -> np.ndarray:
    return np.sort(pd.to_datetime(pd.Series(series)).dropna().values.astype("datetime64[ns]"))


def occupancy_count_at(sessions: pd.DataFrame, times) -> np.ndarray:
    """How many vehicles were parked at each time = entries so far - exits so far."""
    t = pd.DatetimeIndex(times).values.astype("datetime64[ns]")
    entries, exits = _ns(sessions["entry_time"]), _ns(sessions["exit_time"])
    return np.searchsorted(entries, t, side="right") - np.searchsorted(exits, t, side="right")


def count_events(event_times, times, window_min: int = STEP_MIN) -> np.ndarray:
    """Number of events in the `window_min` minutes up to each time."""
    ev = _ns(event_times)
    t = pd.DatetimeIndex(times)
    upper = t.values.astype("datetime64[ns]")
    lower = (t - pd.Timedelta(minutes=window_min)).values.astype("datetime64[ns]")
    return np.searchsorted(ev, upper, side="right") - np.searchsorted(ev, lower, side="right")


def step_features(sessions: pd.DataFrame, times, total_slots: int) -> pd.DataFrame:
    """Build one feature row per timestamp from a sessions table (entry_time, exit_time)."""
    times = pd.DatetimeIndex(times)
    occ = occupancy_count_at(sessions, times)
    lag = occupancy_count_at(sessions, times - pd.Timedelta(minutes=STEP_MIN))
    pct = np.clip(occ / total_slots * 100, 0, 100)
    lag_pct = np.clip(lag / total_slots * 100, 0, 100)
    return pd.DataFrame({
        "timestamp": times,
        "hour_float": times.hour + times.minute / 60,
        "day_of_week": times.dayofweek,
        "is_weekend": (times.dayofweek >= 5).astype(int),
        "occupancy_pct": pct,
        "occ_lag_30": lag_pct,
        "occ_change": pct - lag_pct,
        "arrivals_30": count_events(sessions["entry_time"], times),
        "departures_30": count_events(sessions["exit_time"], times),
    })
