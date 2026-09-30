from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import analytics
from backend.database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    """Headline numbers: sessions, average duration, busiest/quietest hour..."""
    return analytics.summary(db)


@router.get("/peak-hours")
def peak_hours(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Average occupancy for each hour of the day + peak and least-busy hours."""
    return analytics.peak_hours(db, days)


@router.get("/occupancy-trend")
def occupancy_trend(days: int = Query(7, ge=1, le=60), db: Session = Depends(get_db)):
    """Occupancy % every 30 minutes."""
    df = analytics.occupancy_series(db, days)
    df["timestamp"] = df["timestamp"].astype(str)
    return df.to_dict("records")


@router.get("/daily")
def daily(days: int = Query(14, ge=1, le=90), db: Session = Depends(get_db)):
    """Average and maximum occupancy per day."""
    return analytics.daily_occupancy(db, days)


@router.get("/weekly")
def weekly(days: int = Query(28, ge=7, le=180), db: Session = Depends(get_db)):
    """Average occupancy for each day-of-week and hour (0=Monday)."""
    return analytics.weekly_pattern(db, days)


@router.get("/entries-exits")
def entries_exits(days: int = Query(7, ge=1, le=60), db: Session = Depends(get_db)):
    """Vehicle entries and exits per day."""
    return analytics.entries_exits(db, days)
