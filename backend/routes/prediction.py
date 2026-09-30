from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend import analytics, config, crud
from backend.database import get_db
from backend.models import ParkingSession, Prediction
from ml import predict as ml_predict
from ml.features import step_features

router = APIRouter(prefix="/prediction", tags=["Prediction"])


def _run_model(db: Session) -> dict:
    """Build features for 'right now' from the database and ask the saved model."""
    now = datetime.now()
    cutoff = now - timedelta(hours=3)
    rows = db.execute(select(ParkingSession.entry_time, ParkingSession.exit_time).where(
        or_(ParkingSession.exit_time.is_(None), ParkingSession.exit_time >= cutoff))).all()
    sessions = pd.DataFrame(rows, columns=["entry_time", "exit_time"])
    feats = step_features(sessions, [pd.Timestamp(now)], analytics.total_slots(db))
    try:
        result = ml_predict.predict(config.MODEL_DIR, feats)
    except ml_predict.ModelNotFound as e:
        raise HTTPException(status_code=503, detail=str(e))
    result["current_occupancy"] = round(float(feats["occupancy_pct"].iloc[0]), 1)
    result["generated_at"] = now
    _save(db, result, now)
    return result


def _save(db: Session, r: dict, now: datetime) -> None:
    """Store the prediction (at most once every 5 minutes so the table doesn't explode)."""
    last = db.scalar(select(Prediction.prediction_time).order_by(Prediction.prediction_time.desc()).limit(1))
    if last and now - last < timedelta(minutes=5):
        return
    for horizon, key in ((30, "occupancy_30min"), (60, "occupancy_60min")):
        db.add(Prediction(prediction_time=now, horizon_minutes=horizon, predicted_occupancy=r[key],
                          predicted_demand=r["demand"], model_version=r["model_version"]))
    db.commit()


@router.get("/occupancy")
def occupancy(db: Session = Depends(get_db)):
    """Predicted occupancy % in 30 and 60 minutes."""
    r = _run_model(db)
    return {"current_occupancy": r["current_occupancy"], "next_30_min": r["occupancy_30min"],
            "next_60_min": r["occupancy_60min"], "model_version": r["model_version"],
            "generated_at": r["generated_at"]}


@router.get("/demand")
def demand(db: Session = Depends(get_db)):
    """Predicted demand level (Low / Medium / High) for the next hour."""
    r = _run_model(db)
    return {"demand": r["demand"], "probabilities": r["demand_probabilities"],
            "model_version": r["model_version"], "generated_at": r["generated_at"]}


@router.get("/model-info")
def model_info():
    """Evaluation metrics saved during training (real results, computed on the test set)."""
    try:
        return ml_predict.load_metrics(config.MODEL_DIR)
    except ml_predict.ModelNotFound as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/history")
def prediction_history(limit: int = 50, db: Session = Depends(get_db)):
    """Predictions that were stored earlier."""
    rows = db.scalars(select(Prediction).order_by(Prediction.prediction_time.desc()).limit(min(limit, 500)))
    return [{"prediction_time": p.prediction_time, "horizon_minutes": p.horizon_minutes,
             "predicted_occupancy": p.predicted_occupancy, "predicted_demand": p.predicted_demand,
             "model_version": p.model_version} for p in rows]
