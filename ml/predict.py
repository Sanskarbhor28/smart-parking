"""Load the saved models once and make predictions."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.features import FEATURES

_cache: dict = {}


class ModelNotFound(Exception):
    pass


def load_bundle(model_dir: Path):
    path = Path(model_dir) / "parking_models.joblib"
    if not path.exists():
        raise ModelNotFound("Model not trained yet. Run:  python -m ml.train")
    mtime = path.stat().st_mtime
    if _cache.get("path") != str(path) or _cache.get("mtime") != mtime:  # reload if retrained
        _cache.update(path=str(path), mtime=mtime, bundle=joblib.load(path))
    return _cache["bundle"]


def load_metrics(model_dir: Path) -> dict:
    path = Path(model_dir) / "metrics.json"
    if not path.exists():
        raise ModelNotFound("metrics.json not found. Run:  python -m ml.train")
    return json.loads(path.read_text())


def predict(model_dir: Path, features: pd.DataFrame) -> dict:
    """`features` = one row built by ml.features.step_features."""
    b = load_bundle(model_dir)
    X = features[FEATURES]
    o30 = float(np.clip(b["reg30"].predict(X)[0], 0, 100))
    o60 = float(np.clip(b["reg60"].predict(X)[0], 0, 100))
    probs = b["clf"].predict_proba(X)[0]
    classes = list(b["clf"].classes_)
    return {"occupancy_30min": round(o30, 1), "occupancy_60min": round(o60, 1),
            "demand": str(b["clf"].predict(X)[0]),
            "demand_probabilities": {c: round(float(p), 3) for c, p in zip(classes, probs)},
            "model_version": b["version"]}
