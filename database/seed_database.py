"""Load the SYNTHETIC history (data/synthetic_sessions.csv) into the database.

Run:  python -m database.seed_database --reset
After this the dashboard has weeks of demo history to analyse.
Synthetic data is used for development and demonstration.
"""
import argparse

import pandas as pd
from sqlalchemy import delete, select

from backend import config
from backend.database import SessionLocal, init_db
from backend.models import ParkingSession, ParkingSlot, Prediction, SensorData, Vehicle
from ml.data_generator import generate_sessions


def seed(days: int = 60, seed_value: int = 42, reset: bool = False) -> int:
    init_db()
    csv = config.DATA_DIR / "synthetic_sessions.csv"
    if csv.exists() and not reset:
        df = pd.read_csv(csv, parse_dates=["entry_time", "exit_time"])
    else:
        df = generate_sessions(days, seed_value, config.TOTAL_SLOTS)
        df.to_csv(csv, index=False)
    with SessionLocal() as db:
        if reset:
            for table in (SensorData, ParkingSession, Prediction, Vehicle):
                db.execute(delete(table))
            for s in db.scalars(select(ParkingSlot)):
                s.status = "available"
            db.commit()
        elif db.scalar(select(ParkingSession.id).limit(1)):
            print("Database already has sessions. Use --reset to replace them.")
            return 0

        slots = {s.slot_number: s.id for s in db.scalars(select(ParkingSlot))}
        vehicles = {}
        for plate, vtype in df[["vehicle_number", "vehicle_type"]].drop_duplicates("vehicle_number").values:
            v = Vehicle(vehicle_number=plate, vehicle_type=vtype)
            db.add(v)
            vehicles[plate] = v
        db.flush()

        sessions, sensors, still_parked = [], [], set()
        for r in df.itertuples(index=False):
            exit_time = None if pd.isna(r.exit_time) else r.exit_time.to_pydatetime()
            sid = slots[r.slot_number]
            sessions.append({"vehicle_id": vehicles[r.vehicle_number].id, "slot_id": sid,
                             "entry_time": r.entry_time.to_pydatetime(), "exit_time": exit_time,
                             "duration_minutes": None if pd.isna(r.duration_minutes) else float(r.duration_minutes)})
            sensors.append({"slot_id": sid, "timestamp": r.entry_time.to_pydatetime(), "occupancy_status": "occupied"})
            if exit_time:
                sensors.append({"slot_id": sid, "timestamp": exit_time, "occupancy_status": "available"})
            else:
                still_parked.add(r.slot_number)
        db.bulk_insert_mappings(ParkingSession, sessions)
        db.bulk_insert_mappings(SensorData, sensors)
        for s in db.scalars(select(ParkingSlot)):
            s.status = "occupied" if s.slot_number in still_parked else "available"
        db.commit()
    print(f"Loaded {len(sessions)} synthetic sessions ({len(still_parked)} vehicles currently parked).")
    return len(sessions)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--reset", action="store_true", help="wipe existing parking data first")
    a = ap.parse_args()
    seed(a.days, a.seed, a.reset)
