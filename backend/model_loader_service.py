"""Production model loading and prediction helpers."""
import pickle
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

MODELS_DIR = Path(__file__).resolve().parent / "models"
PRODUCTION_MODEL_PATH = MODELS_DIR / "final_model.pkl"

_MODEL_ARTIFACT: Optional[Dict] = None
_MODEL_PATH: Optional[Path] = None


def load_production_model() -> Optional[Dict]:
    global _MODEL_ARTIFACT, _MODEL_PATH
    candidates = [PRODUCTION_MODEL_PATH]
    candidates.extend(sorted(MODELS_DIR.glob("*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True))
    for path in candidates:
        if path.exists():
            with open(path, "rb") as file:
                _MODEL_ARTIFACT = pickle.load(file)
            _MODEL_PATH = path
            return _MODEL_ARTIFACT
    _MODEL_ARTIFACT = None
    _MODEL_PATH = None
    return None


def model_status() -> Dict:
    if _MODEL_ARTIFACT is None:
        return {"loaded": False, "model_path": None}
    return {
        "loaded": True,
        "model_path": str(_MODEL_PATH),
        "model_name": _MODEL_ARTIFACT.get("best_name", "Production AQI Model"),
        "model_version": _MODEL_ARTIFACT.get("model_version") or (_MODEL_PATH.stem if _MODEL_PATH else "production"),
        "trained_at": _MODEL_ARTIFACT.get("trained_at"),
        "metrics": _MODEL_ARTIFACT.get("best_metrics", {}),
        "dataset_rows": _MODEL_ARTIFACT.get("dataset_rows"),
    }


def predict_with_production_model(features: Dict[str, float]) -> Dict:
    if _MODEL_ARTIFACT is None:
        load_production_model()
    if _MODEL_ARTIFACT is None:
        return _fallback_prediction(features)

    keys = _MODEL_ARTIFACT["feature_keys"]
    means = _MODEL_ARTIFACT.get("means", {})
    stds = _MODEL_ARTIFACT.get("stds", {})
    row = [float(features.get(key, means.get(key, 0.0)) or 0.0) for key in keys]
    frame = pd.DataFrame([row], columns=keys)
    prediction = max(0.0, min(500.0, float(_MODEL_ARTIFACT["model"].predict(frame)[0])))
    metrics = _MODEL_ARTIFACT.get("best_metrics", {})
    r2_confidence = max(0.0, min(1.0, float(metrics.get("r2", 0.0))))
    z_scores = [
        abs(float(frame.iloc[0][key]) - float(means.get(key, 0.0))) / max(float(stds.get(key, 1.0)), 1e-6)
        for key in keys
    ]
    drift_penalty = min(0.35, float(np.mean(z_scores)) * 0.08) if z_scores else 0.0
    confidence = max(0.0, min(0.99, r2_confidence - drift_penalty))
    return {
        "prediction": prediction,
        "model": _MODEL_ARTIFACT.get("best_name", "Production AQI Model"),
        "features_used": keys,
        "confidence": round(confidence * 100, 1),
        "metrics": metrics,
        "model_version": model_status().get("model_version"),
        "trained_at": _MODEL_ARTIFACT.get("trained_at"),
        "dataset_rows": _MODEL_ARTIFACT.get("dataset_rows"),
    }


def _fallback_prediction(features: Dict[str, float]) -> Dict:
    pollutant_score = (
        float(features.get("pm25") or 0) * 1.8
        + float(features.get("pm10") or 0) * 0.75
        + float(features.get("no2") or 0) * 0.5
        + float(features.get("o3") or 0) * 0.45
        + float(features.get("so2") or 0) * 0.35
        + float(features.get("co") or 0) * 12
    )
    return {
        "prediction": max(0.0, min(500.0, pollutant_score)),
        "model": "Fallback AQI Estimator",
        "features_used": [key for key, value in features.items() if value is not None],
        "confidence": 55.0,
        "metrics": {},
        "model_version": "fallback",
        "trained_at": None,
        "dataset_rows": None,
    }
