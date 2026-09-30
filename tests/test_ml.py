import os
from pathlib import Path

import pandas as pd

from ml.data_generator import generate_sessions
from ml.features import FEATURES, demand_from_occupancy, occupancy_count_at, step_features
from ml.predict import load_metrics, predict


def test_generator_is_reproducible():
    end = pd.Timestamp("2026-01-15 12:00")
    a = generate_sessions(3, seed=5, total_slots=10, end=end)
    b = generate_sessions(3, seed=5, total_slots=10, end=end)
    assert a.equals(b) and len(a) > 0


def test_occupancy_count():
    s = pd.DataFrame({"entry_time": pd.to_datetime(["2026-01-01 10:00", "2026-01-01 10:10"]),
                      "exit_time": pd.to_datetime(["2026-01-01 11:00", None])})
    t = pd.to_datetime(["2026-01-01 09:00", "2026-01-01 10:05", "2026-01-01 10:30", "2026-01-01 12:00"])
    assert occupancy_count_at(s, t).tolist() == [0, 1, 2, 1]


def test_demand_rule():
    assert [demand_from_occupancy(x) for x in (10, 40, 69.9, 70, 100)] == ["Low", "Medium", "Medium", "High", "High"]


def test_model_prediction_and_metrics():
    model_dir = Path(os.environ["MODEL_DIR"])
    sessions = generate_sessions(3, seed=2, total_slots=30)
    feats = step_features(sessions, [pd.Timestamp.now()], 30)
    assert list(FEATURES) == [c for c in FEATURES if c in feats.columns]
    p = predict(model_dir, feats)
    assert 0 <= p["occupancy_30min"] <= 100 and p["demand"] in ("Low", "Medium", "High")
    m = load_metrics(model_dir)
    assert {"MAE", "RMSE", "R2"} <= set(m["regression"]["30min"]["models"]["Random Forest"]["test"])
    assert {"Accuracy", "Precision", "Recall", "F1"} <= set(m["classification"]["models"]["Random Forest"]["test"])
