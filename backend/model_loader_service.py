"""Production model loading and prediction helpers."""
import logging
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

from aqi_utils import pollutants_to_aqi

MODELS_DIR = Path(__file__).resolve().parent / "models"
PRODUCTION_MODEL_PATH = MODELS_DIR / "final_model.pkl"
BEST_MODEL_PATH = MODELS_DIR / "best_model.pkl"
AUTOML_BEST_MODEL_PATH = Path(__file__).resolve().parent / "ml" / "models" / "best_model.pkl"
AUTOML_METRICS_PATH = Path(__file__).resolve().parent / "ml" / "metadata" / "metrics.json"

_MODEL_ARTIFACT: Optional[Dict] = None
_MODEL_PATH: Optional[Path] = None
logger = logging.getLogger("aeropulse.model_loader")


def _automl_metrics() -> Dict:
    if not AUTOML_METRICS_PATH.exists():
        return {}
    try:
        return json.loads(AUTOML_METRICS_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Unable to read AutoML metrics metadata.")
        return {}


def load_production_model() -> Optional[Dict]:
    global _MODEL_ARTIFACT, _MODEL_PATH
    candidates = [AUTOML_BEST_MODEL_PATH, BEST_MODEL_PATH, PRODUCTION_MODEL_PATH]
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
    metrics_doc = _automl_metrics() if _MODEL_PATH == AUTOML_BEST_MODEL_PATH else {}
    artifact_metrics = _MODEL_ARTIFACT.get("best_metrics") or _MODEL_ARTIFACT.get("metrics", {})
    return {
        "loaded": True,
        "model_path": str(_MODEL_PATH),
        "model_name": metrics_doc.get("algorithm") or _MODEL_ARTIFACT.get("algorithm") or _MODEL_ARTIFACT.get("best_name", "Production AQI Model"),
        "algorithm": metrics_doc.get("algorithm") or _MODEL_ARTIFACT.get("algorithm") or _MODEL_ARTIFACT.get("best_name", "Production AQI Model"),
        "model_version": metrics_doc.get("version") or _MODEL_ARTIFACT.get("model_version") or (_MODEL_PATH.stem if _MODEL_PATH else "production"),
        "trained_at": metrics_doc.get("timestamp") or _MODEL_ARTIFACT.get("trained_at"),
        "metrics": metrics_doc.get("metrics") or artifact_metrics,
        "dataset_rows": metrics_doc.get("dataset_size") or _MODEL_ARTIFACT.get("dataset_rows"),
        "feature_importance": metrics_doc.get("feature_importance") or _MODEL_ARTIFACT.get("feature_importance", []),
        "git_commit": metrics_doc.get("git_commit") or _MODEL_ARTIFACT.get("git_commit"),
        "model_size_mb": metrics_doc.get("model_size_mb"),
        "feature_count": metrics_doc.get("feature_count") or len(_MODEL_ARTIFACT.get("feature_keys", [])),
        "training_duration_seconds": metrics_doc.get("training_duration_seconds"),
        "leaderboard": metrics_doc.get("leaderboard", []),
        "target_scale": _MODEL_ARTIFACT.get("target_scale", "0-500"),
        "aqi_standard": _MODEL_ARTIFACT.get("aqi_standard", "IN_AQI"),
    }


def _season(month: int) -> int:
    if month in (12, 1, 2):
        return 1
    if month in (3, 4, 5):
        return 2
    if month in (6, 7, 8, 9):
        return 3
    return 4


def _prepare_inference_features(features: Dict[str, float], means: Dict[str, float]) -> Dict[str, float]:
    now = datetime.now(timezone.utc)
    prepared = dict(features)
    prepared.setdefault("day", now.day)
    prepared.setdefault("month", now.month)
    prepared.setdefault("season", _season(now.month))
    prepared.setdefault("weekend", 1 if now.weekday() >= 5 else 0)
    prepared.setdefault("hour", now.hour)
    prepared.setdefault("day_of_year", now.timetuple().tm_yday)
    prepared.setdefault("rain", 0.0)
    prepared.setdefault("clouds", means.get("clouds", 0.0))
    prepared.setdefault("visibility", means.get("visibility", 10000.0))
    prepared.setdefault("wind_category", 0 if float(prepared.get("wind") or means.get("wind", 0) or 0) <= 2 else 1)
    prepared.setdefault("rain_indicator", 1 if float(prepared.get("rain") or 0) > 0 else 0)
    for key in ("temp", "humidity", "pressure", "wind"):
        prepared.setdefault(f"{key}_change" if key == "temp" else f"{key}_trend", 0.0)
    pm25 = float(prepared.get("pm25") or means.get("pm25", 0.0) or 0.0)
    pm10 = float(prepared.get("pm10") or means.get("pm10", 0.0) or 0.0)
    no2 = float(prepared.get("no2") or means.get("no2", 0.0) or 0.0)
    o3 = float(prepared.get("o3") or means.get("o3", 0.0) or 0.0)
    humidity = float(prepared.get("humidity") or means.get("humidity", 0.0) or 0.0)
    temp = float(prepared.get("temp") or means.get("temp", 0.0) or 0.0)
    wind = float(prepared.get("wind") or means.get("wind", 0.0) or 0.0)
    for key, value in {"pm25_lag_1": pm25, "pm10_lag_1": pm10, "no2_lag_1": no2, "o3_lag_1": o3}.items():
        prepared.setdefault(key, value)
    for key, value in {"pm25_rolling_24h": pm25, "pm10_rolling_24h": pm10, "no2_rolling_24h": no2, "o3_rolling_24h": o3}.items():
        prepared.setdefault(key, value)
    prepared.setdefault("rolling_pm_average", np.mean([pm25, pm10]))
    prepared.setdefault("moving_pollutant_average", np.mean([
        float(prepared.get(key) or means.get(key, 0.0) or 0.0)
        for key in ("pm25", "pm10", "no2", "so2", "co", "o3")
    ]))
    prepared.setdefault("pm25_pm10_ratio", pm25 / max(pm10, 1e-6))
    prepared.setdefault("no2_o3_ratio", no2 / max(o3, 1e-6))
    prepared.setdefault("pm25_humidity_interaction", pm25 * humidity / 100)
    prepared.setdefault("pm10_wind_interaction", pm10 / (wind + 1))
    prepared.setdefault("o3_temp_interaction", o3 * temp)
    prepared["pm25"] = pm25
    prepared["pm10"] = pm10
    return prepared


def _sanity_floor(features: Dict[str, float]) -> float:
    # A pollutant-max AQI is not a replacement for the ML model, but it is a
    # physical guardrail against returning impossible 0-15 AQI under high PM.
    estimate = pollutants_to_aqi(features, standard="IN_AQI")
    return max(0.0, estimate * 0.65)


def predict_with_production_model(features: Dict[str, float]) -> Dict:
    if _MODEL_ARTIFACT is None:
        load_production_model()
    if _MODEL_ARTIFACT is None:
        return _fallback_prediction(features)

    keys = _MODEL_ARTIFACT["feature_keys"]
    means = _MODEL_ARTIFACT.get("means", {})
    stds = _MODEL_ARTIFACT.get("stds", {})
    processed = _prepare_inference_features(features, means)
    row = [float(processed.get(key, means.get(key, 0.0)) or 0.0) for key in keys]
    frame = pd.DataFrame([row], columns=keys)
    raw_output = max(0.0, min(500.0, float(_MODEL_ARTIFACT["model"].predict(frame)[0])))
    calibrator = _MODEL_ARTIFACT.get("calibrator")
    calibrated = float(calibrator.predict([raw_output])[0]) if calibrator is not None else raw_output
    floor = _sanity_floor(processed)
    warnings = []
    if calibrated < floor:
        warnings.append(f"Model output {calibrated:.1f} AQI was below pollutant sanity floor {floor:.1f}; raised final AQI.")
    prediction = max(0.0, min(500.0, max(calibrated, floor)))
    logger.info(
        "AQI prediction debug | input=%s processed=%s raw_model_output=%.3f calibrated=%.3f final_aqi=%.3f expected_range=0-500 warnings=%s",
        features,
        {key: processed.get(key) for key in keys},
        raw_output,
        calibrated,
        prediction,
        warnings,
    )
    metrics = _MODEL_ARTIFACT.get("best_metrics") or _MODEL_ARTIFACT.get("metrics", {})
    r2_confidence = max(0.0, min(1.0, float(metrics.get("r2", 0.0))))
    z_scores = [
        abs(float(frame.iloc[0][key]) - float(means.get(key, 0.0))) / max(float(stds.get(key, 1.0)), 1e-6)
        for key in keys
    ]
    drift_penalty = min(0.35, float(np.mean(z_scores)) * 0.08) if z_scores else 0.0
    confidence = max(0.0, min(0.99, r2_confidence - drift_penalty))
    return {
        "prediction": prediction,
        "raw_model_output": round(raw_output, 3),
        "calibrated_output": round(calibrated, 3),
        "final_aqi": round(prediction, 3),
        "expected_aqi_range": "0-500",
        "warnings": warnings,
        "model": _MODEL_ARTIFACT.get("algorithm") or _MODEL_ARTIFACT.get("best_name", "Production AQI Model"),
        "features_used": keys,
        "processed_features": {key: processed.get(key) for key in keys},
        "confidence": round(confidence * 100, 1),
        "metrics": metrics,
        "model_version": model_status().get("model_version"),
        "trained_at": model_status().get("trained_at") or _MODEL_ARTIFACT.get("trained_at"),
        "dataset_rows": _MODEL_ARTIFACT.get("dataset_rows"),
        "feature_importance": model_status().get("feature_importance") or _MODEL_ARTIFACT.get("feature_importance", []),
        "feature_contributions": _feature_contributions(processed, keys, means),
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
        "feature_importance": _fallback_importance(),
        "feature_contributions": _fallback_contributions(features),
    }


def _feature_contributions(features: Dict[str, float], keys, means: Dict[str, float]) -> list[Dict]:
    contributions = []
    for key in keys:
        current = float(features.get(key) or 0.0)
        baseline = float(means.get(key, 0.0) or 0.0)
        if key in {"pm25", "pm10", "no2", "so2", "co", "o3"}:
            direction = 1
            weight = {"pm25": 1.8, "pm10": 0.75, "no2": 0.5, "o3": 0.45, "so2": 0.35, "co": 12}.get(key, 0.2)
        elif key in {"wind", "rain"}:
            direction = -1
            weight = {"wind": 3.0, "rain": 1.2}.get(key, 1.0)
        elif key == "humidity":
            direction = 1 if current > 65 else -1
            weight = 0.25
        else:
            direction = 1 if current > baseline else -1
            weight = 0.08
        contribution = direction * (current - baseline) * weight
        if abs(contribution) >= 0.25:
            contributions.append({"feature": key, "contribution": round(float(contribution), 2)})
    return sorted(contributions, key=lambda item: abs(item["contribution"]), reverse=True)[:8]


def _fallback_importance() -> list[Dict]:
    weights = {"pm25": 0.32, "pm10": 0.24, "no2": 0.12, "o3": 0.1, "co": 0.08, "wind": 0.07, "humidity": 0.04, "so2": 0.03}
    return [{"feature": key, "importance": value} for key, value in weights.items()]


def _fallback_contributions(features: Dict[str, float]) -> list[Dict]:
    baseline = {"pm25": 35, "pm10": 80, "no2": 25, "o3": 45, "co": 0.7, "wind": 3, "humidity": 60, "so2": 8}
    return _feature_contributions(features, baseline.keys(), baseline)
