"""Analytics computed with pandas from the parking_sessions table."""
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import ParkingSession, ParkingSlot
from ml.features import STEP_MIN, occupancy_count_at


def load_sessions(db: Session, since: datetime) -> pd.DataFrame:
    """Sessions that overlap the period [since, now]."""
    q = select(ParkingSession.entry_time, ParkingSession.exit_time, ParkingSession.duration_minutes).where(
        or_(ParkingSession.exit_time.is_(None), ParkingSession.exit_time >= since))
    df = pd.DataFrame(db.execute(q).all(), columns=["entry_time", "exit_time", "duration_minutes"])
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    return df


def total_slots(db: Session) -> int:
    return db.scalar(select(func.count(ParkingSlot.id))) or 1


def occupancy_series(db: Session, days: int) -> pd.DataFrame:
    """Occupancy % every 30 minutes for the last `days` days."""
    now = datetime.now()
    since = (pd.Timestamp(now) - pd.Timedelta(days=days)).ceil(f"{STEP_MIN}min")
    sessions = load_sessions(db, since.to_pydatetime())
    times = pd.date_range(since, pd.Timestamp(now).floor(f"{STEP_MIN}min"), freq=f"{STEP_MIN}min")
    occ = occupancy_count_at(sessions, times)
    return pd.DataFrame({"timestamp": times, "occupancy_pct": (occ / total_slots(db) * 100).clip(0, 100).round(1)})


def hourly_profile(db: Session, days: int = 30) -> pd.DataFrame:
    """Average occupancy % and average arrivals for each hour of the day."""
    s = occupancy_series(db, days)
    s["hour"] = s["timestamp"].dt.hour
    occ = s.groupby("hour")["occupancy_pct"].mean().reindex(range(24), fill_value=0).round(1)
    sessions = load_sessions(db, datetime.now() - timedelta(days=days))
    sessions = sessions[sessions["entry_time"] >= datetime.now() - timedelta(days=days)]
    n_days = max(days, 1)
    arrivals = sessions.groupby(sessions["entry_time"].dt.hour).size().reindex(range(24), fill_value=0) / n_days
    return pd.DataFrame({"hour": range(24), "avg_occupancy_pct": occ.values,
                         "avg_arrivals": arrivals.round(2).values})


def summary(db: Session) -> dict:
    now = datetime.now()
    today = datetime.combine(now.date(), datetime.min.time())
    completed = db.scalar(select(func.count(ParkingSession.id)).where(ParkingSession.exit_time.is_not(None))) or 0
    parked = db.scalar(select(func.count(ParkingSession.id)).where(ParkingSession.exit_time.is_(None))) or 0
    avg_dur = db.scalar(select(func.avg(ParkingSession.duration_minutes)))
    entries_today = db.scalar(select(func.count(ParkingSession.id)).where(ParkingSession.entry_time >= today)) or 0
    exits_today = db.scalar(select(func.count(ParkingSession.id)).where(ParkingSession.exit_time >= today)) or 0
    prof = hourly_profile(db, 30)
    has_data = prof["avg_occupancy_pct"].sum() > 0
    s7 = occupancy_series(db, 7)
    return {
        "total_sessions": completed + parked,
        "completed_sessions": completed,
        "currently_parked": parked,
        "avg_duration_minutes": round(float(avg_dur), 1) if avg_dur is not None else None,
        "entries_today": entries_today,
        "exits_today": exits_today,
        "avg_occupancy_7d_pct": round(float(s7["occupancy_pct"].mean()), 1) if len(s7) else 0.0,
        "busiest_hour": int(prof.loc[prof["avg_occupancy_pct"].idxmax(), "hour"]) if has_data else None,
        "quietest_hour": int(prof.loc[prof["avg_occupancy_pct"].idxmin(), "hour"]) if has_data else None,
    }


def peak_hours(db: Session, days: int = 30, top: int = 3) -> dict:
    prof = hourly_profile(db, days)
    ranked = prof.sort_values("avg_occupancy_pct", ascending=False)
    return {"window_days": days,
            "peak_hours": ranked.head(top)["hour"].tolist(),
            "least_busy_hours": ranked.tail(top).sort_values("avg_occupancy_pct")["hour"].tolist(),
            "hourly": prof.to_dict("records")}


def daily_occupancy(db: Session, days: int = 14) -> list[dict]:
    s = occupancy_series(db, days)
    s["date"] = s["timestamp"].dt.date.astype(str)
    g = s.groupby("date")["occupancy_pct"].agg(avg="mean", max="max").round(1).reset_index()
    return g.to_dict("records")


def weekly_pattern(db: Session, days: int = 28) -> list[dict]:
    s = occupancy_series(db, days)
    s["day_of_week"] = s["timestamp"].dt.dayofweek
    s["hour"] = s["timestamp"].dt.hour
    g = s.groupby(["day_of_week", "hour"])["occupancy_pct"].mean().round(1).reset_index()
    return g.rename(columns={"occupancy_pct": "avg_occupancy_pct"}).to_dict("records")


def entries_exits(db: Session, days: int = 7) -> list[dict]:
    """Entries and exits per day."""
    since = datetime.combine((datetime.now() - timedelta(days=days - 1)).date(), datetime.min.time())
    sessions = load_sessions(db, since)
    days_idx = pd.date_range(since, periods=days, freq="D")
    e = sessions[sessions["entry_time"] >= since].groupby(sessions["entry_time"].dt.normalize()).size()
    x = sessions[sessions["exit_time"] >= since].groupby(sessions["exit_time"].dt.normalize()).size()
    return [{"date": str(d.date()), "entries": int(e.get(d, 0)), "exits": int(x.get(d, 0))} for d in days_idx]
