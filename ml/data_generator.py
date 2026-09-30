"""Generate SYNTHETIC parking data (not real-world data!).

Vehicles arrive following a daily pattern (morning + evening rush on weekdays, a
midday peak on weekends). Each vehicle stays a random time. The result is a table of
parking sessions plus a 30-minute "training table" with features and targets.

Run:  python -m ml.data_generator --days 60
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from ml.features import STEP_MIN, demand_from_occupancy, step_features, occupancy_count_at

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SYNTHETIC_NOTE = "Synthetic data is used for development and demonstration."


def arrival_rate(ts: pd.Timestamp) -> float:
    """Expected number of arrivals in one 30-minute step at this time."""
    h = ts.hour + ts.minute / 60
    if ts.dayofweek < 5:  # weekday: rush hours ~9:00 and ~18:00
        rate = 0.6 + 3.6 * np.exp(-((h - 9) / 1.6) ** 2) + 2.6 * np.exp(-((h - 18) / 1.8) ** 2)
    else:                 # weekend: shopping peak around 13:00
        rate = 0.5 + 2.8 * np.exp(-((h - 13) / 3.0) ** 2)
    if h < 6:
        rate *= 0.15      # very quiet at night
    return float(rate * 2.4)  # scale so the lot gets reasonably busy


def sample_duration(rng: np.random.Generator, ts: pd.Timestamp) -> float:
    """Parking duration in minutes: short visits (shopping) or long stays (office)."""
    long_stay_prob = 0.45 if ts.dayofweek < 5 and ts.hour < 12 else 0.2
    if rng.random() < long_stay_prob:
        d = rng.lognormal(np.log(330), 0.35)
    else:
        d = rng.lognormal(np.log(70), 0.6)
    return float(np.clip(d, 10, 720))


def generate_sessions(days: int = 60, seed: int = 42, total_slots: int = 30,
                      end: pd.Timestamp | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = (end or pd.Timestamp.now()).floor(f"{STEP_MIN}min")
    start = end - pd.Timedelta(days=days)
    plates = [f"MH12{''.join(rng.choice(list('ABCDEFGH'), 2))}{rng.integers(1000, 9999)}" for _ in range(600)]
    plates = list(dict.fromkeys(plates))
    types = rng.choice(["car", "bike", "truck"], size=len(plates), p=[0.65, 0.3, 0.05])
    plate_type = dict(zip(plates, types))

    zone = lambda i: "ABC"[min(i * 3 // total_slots, 2)]  # same formula as backend/config.py
    free = set(range(total_slots))
    active: list[tuple[pd.Timestamp, int, str]] = []  # (exit_time, slot_index, plate)
    rows = []
    for step in pd.date_range(start, end, freq=f"{STEP_MIN}min", inclusive="left"):
        offsets = np.sort(rng.uniform(0, STEP_MIN, rng.poisson(arrival_rate(step))))
        for off in offsets:
            now = (step + pd.Timedelta(minutes=float(off))).round("s")
            still = []
            for ex, slot, plate in active:  # release vehicles that already left
                if ex <= now:
                    free.add(slot)
                else:
                    still.append((ex, slot, plate))
            active = still
            if not free:
                continue  # lot full: this vehicle drives away
            busy = {p for _, _, p in active}
            candidates = [p for p in plates if p not in busy]
            plate = candidates[rng.integers(len(candidates))]
            slot = int(rng.choice(sorted(free)))
            free.remove(slot)
            exit_time = (now + pd.Timedelta(minutes=sample_duration(rng, now))).round("s")
            active.append((exit_time, slot, plate))
            rows.append({"vehicle_number": plate, "vehicle_type": plate_type[plate],
                         "slot_number": f"P{slot + 1:02d}", "zone": zone(slot),
                         "entry_time": now, "exit_time": exit_time})
    df = pd.DataFrame(rows)
    still_parked = df["exit_time"] > end  # they have not left yet at "now"
    df.loc[still_parked, "exit_time"] = pd.NaT
    df["duration_minutes"] = ((df["exit_time"] - df["entry_time"]).dt.total_seconds() / 60).round(2)
    return df


def build_training_table(sessions: pd.DataFrame, total_slots: int) -> pd.DataFrame:
    """Features at every 30-min step + targets (occupancy 30/60 min later, demand level)."""
    lo = sessions["entry_time"].min().ceil(f"{STEP_MIN}min") + pd.Timedelta(days=1)  # skip warm-up day
    hi = (sessions["entry_time"].max().floor(f"{STEP_MIN}min")) - pd.Timedelta(minutes=2 * STEP_MIN)
    times = pd.date_range(lo, hi, freq=f"{STEP_MIN}min")
    table = step_features(sessions, times, total_slots)
    for horizon, name in ((1, "target_occ_30"), (2, "target_occ_60")):
        future = times + pd.Timedelta(minutes=STEP_MIN * horizon)
        table[name] = np.clip(occupancy_count_at(sessions, future) / total_slots * 100, 0, 100)
    table["target_demand"] = table["target_occ_60"].apply(demand_from_occupancy)
    return table


def main() -> None:
    ap = argparse.ArgumentParser(description=SYNTHETIC_NOTE)
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--slots", type=int, default=30)
    args = ap.parse_args()
    DATA_DIR.mkdir(exist_ok=True)
    sessions = generate_sessions(args.days, args.seed, args.slots)
    sessions.to_csv(DATA_DIR / "synthetic_sessions.csv", index=False)
    table = build_training_table(sessions, args.slots)
    table.to_csv(DATA_DIR / "synthetic_training_data.csv", index=False)
    print(SYNTHETIC_NOTE)
    print(f"Sessions: {len(sessions)}  |  Training rows: {len(table)}")
    print(table["target_demand"].value_counts().to_string())
    print(table["occupancy_pct"].describe().round(1).to_string())


if __name__ == "__main__":
    main()
