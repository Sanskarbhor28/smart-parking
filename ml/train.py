"""Train, compare and save the ML models.

Run:  python -m ml.train
Trains on SYNTHETIC data (generated automatically if missing). Split is chronological:
70% train / 15% validation (used to CHOOSE the best model) / 15% test (final report).
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.data_generator import SYNTHETIC_NOTE, build_training_table, generate_sessions
from ml.features import DEMAND_LABELS, FEATURES, LOW_MAX, MEDIUM_MAX

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "models"


def _regressors():
    return {"Linear Regression": LinearRegression(),
            "Random Forest": RandomForestRegressor(n_estimators=150, max_depth=12,
                                                   min_samples_leaf=3, random_state=42, n_jobs=-1)}


def _classifiers():
    return {"Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
            "Random Forest": RandomForestClassifier(n_estimators=150, max_depth=10,
                                                    min_samples_leaf=3, random_state=42, n_jobs=-1)}


def _reg_metrics(y, pred) -> dict:
    return {"MAE": round(mean_absolute_error(y, pred), 3),
            "RMSE": round(float(np.sqrt(mean_squared_error(y, pred))), 3),
            "R2": round(r2_score(y, pred), 4)}


def _clf_metrics(y, pred) -> dict:
    kw = dict(average="macro", zero_division=0)
    return {"Accuracy": round(accuracy_score(y, pred), 4),
            "Precision": round(precision_score(y, pred, **kw), 4),
            "Recall": round(recall_score(y, pred, **kw), 4),
            "F1": round(f1_score(y, pred, **kw), 4)}


def train_all(days: int = 60, seed: int = 42, total_slots: int = 30,
              model_dir: Path = DEFAULT_MODEL_DIR, data_dir: Path | None = None) -> dict:
    """Full pipeline: data -> features -> compare models -> pick best -> save. Returns metrics."""
    sessions = generate_sessions(days, seed, total_slots)
    table = build_training_table(sessions, total_slots)
    if data_dir:  # keep a copy of the datasets for inspection
        data_dir.mkdir(exist_ok=True)
        sessions.to_csv(data_dir / "synthetic_sessions.csv", index=False)
        table.to_csv(data_dir / "synthetic_training_data.csv", index=False)

    n = len(table)
    i1, i2 = int(n * 0.70), int(n * 0.85)
    tr, va, te = table.iloc[:i1], table.iloc[i1:i2], table.iloc[i2:]
    X = {k: d[FEATURES] for k, d in (("tr", tr), ("va", va), ("te", te))}

    report: dict = {"data_note": SYNTHETIC_NOTE, "rows": {"train": len(tr), "validation": len(va), "test": len(te)},
                    "features": FEATURES, "regression": {}, "classification": {}}
    chosen: dict = {}

    # ---- regression: occupancy % in 30 and 60 minutes ----
    for horizon in (30, 60):
        col = f"target_occ_{horizon}"
        # baseline: "nothing changes" (predict the current occupancy)
        baseline = {"test": _reg_metrics(te[col], te["occupancy_pct"])}
        results, best_name, best_rmse = {}, None, float("inf")
        for name, model in _regressors().items():
            model.fit(X["tr"], tr[col])
            val_rmse = _reg_metrics(va[col], model.predict(X["va"]))["RMSE"]
            results[name] = {"validation": _reg_metrics(va[col], model.predict(X["va"])),
                             "test": _reg_metrics(te[col], model.predict(X["te"]))}
            if val_rmse < best_rmse:
                best_name, best_rmse = name, val_rmse
        # refit the winner on train+validation before saving
        final = _regressors()[best_name].fit(pd.concat([X["tr"], X["va"]]), pd.concat([tr[col], va[col]]))
        chosen[f"reg{horizon}"] = final
        report["regression"][f"{horizon}min"] = {"models": results, "baseline_no_change": baseline,
                                                 "selected": best_name}

    # ---- classification: demand level ----
    results, best_name, best_f1 = {}, None, -1.0
    for name, model in _classifiers().items():
        model.fit(X["tr"], tr["target_demand"])
        v = _clf_metrics(va["target_demand"], model.predict(X["va"]))
        pred_te = model.predict(X["te"])
        results[name] = {"validation": v, "test": _clf_metrics(te["target_demand"], pred_te),
                         "confusion_matrix": confusion_matrix(te["target_demand"], pred_te,
                                                              labels=DEMAND_LABELS).tolist()}
        if v["F1"] > best_f1:
            best_name, best_f1 = name, v["F1"]
    final = _classifiers()[best_name].fit(pd.concat([X["tr"], X["va"]]),
                                          pd.concat([tr["target_demand"], va["target_demand"]]))
    chosen["clf"] = final
    report["classification"] = {"models": results, "selected": best_name, "labels": DEMAND_LABELS,
                                "rule": f"Low < {LOW_MAX:.0f}% <= Medium < {MEDIUM_MAX:.0f}% <= High (occupancy in 60 min)"}

    version = "v" + datetime.now().strftime("%Y%m%d-%H%M")
    report["model_version"] = version
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({**chosen, "features": FEATURES, "version": version, "labels": DEMAND_LABELS},
                model_dir / "parking_models.joblib")
    (model_dir / "metrics.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Train parking models on synthetic data")
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--slots", type=int, default=30)
    a = ap.parse_args()
    data_dir = Path(__file__).resolve().parent.parent / "data"
    rep = train_all(a.days, a.seed, a.slots, DEFAULT_MODEL_DIR, data_dir)
    print(f"Model version: {rep['model_version']}   ({SYNTHETIC_NOTE})")
    print("Saved to ml/models/. Run `python -m ml.evaluate` to see the full metrics.")


if __name__ == "__main__":
    main()
