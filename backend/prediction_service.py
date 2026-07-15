"""Prediction response helpers for transparent ML AQI outputs."""
from datetime import datetime, timezone
from typing import Dict, Iterable

from aqi_utils import health_advice_for_category


POLLUTANT_LABELS = {
    "pm25": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "so2": "SO2",
    "co": "CO",
    "o3": "O3",
    "temp": "temperature",
    "humidity": "humidity",
    "wind": "wind speed",
    "pressure": "pressure",
}


def build_prediction_explanation(category: str, features: Dict[str, float], used_keys: Iterable[str]) -> str:
    pollutant_keys = [k for k in used_keys if k in {"pm25", "pm10", "no2", "so2", "co", "o3"}]
    ranked = sorted(
        ((k, float(features.get(k, 0.0))) for k in pollutant_keys if features.get(k) is not None),
        key=lambda item: item[1],
        reverse=True,
    )
    elevated = [POLLUTANT_LABELS[k] for k, _ in ranked[:2]]
    lower = [POLLUTANT_LABELS[k] for k, _ in ranked[-2:]]
    if elevated:
        return (
            f"The model predicts {category} AQI because {', '.join(elevated)} are the strongest pollutant signals "
            f"while {', '.join(lower)} remain comparatively lower."
        )
    return f"The model predicts {category} AQI from the supplied weather and pollutant measurements."


def build_ai_prediction(prediction: Dict, aqi_info: Dict, features: Dict[str, float]) -> Dict:
    advice = health_advice_for_category(aqi_info["category"])
    now = datetime.now(timezone.utc).isoformat()
    return {
        "predicted_aqi": aqi_info["aqi"],
        "aqi": aqi_info["aqi"],
        "category": aqi_info["category"],
        "color": aqi_info["color"],
        "confidence": prediction.get("confidence"),
        "model": prediction.get("model"),
        "model_name": prediction.get("model"),
        "model_version": prediction.get("model_version"),
        "generated_at": now,
        "prediction_timestamp": now,
        "health_advice": advice["advice"],
        "advice": advice["advice"],
        "risk_level": advice["risk_level"],
        "explanation": build_prediction_explanation(aqi_info["category"], features, prediction.get("features_used", [])),
        "prediction_interval": prediction.get("prediction_interval"),
        "features_used": prediction.get("features_used", []),
    }


def build_model_performance(dataset: Dict, prediction: Dict) -> Dict:
    metrics = prediction.get("metrics") or {}
    return {
        "algorithm": prediction.get("model"),
        "training_accuracy": round(max(0.0, float(metrics.get("r2", 0.0))) * 100, 1),
        "validation_accuracy": round(max(0.0, float(metrics.get("cv_r2", 0.0))) * 100, 1),
        "rmse": metrics.get("rmse"),
        "mae": metrics.get("mae"),
        "r2_score": metrics.get("r2"),
        "dataset_used": dataset.get("name"),
        "training_date": prediction.get("trained_at") or dataset.get("trained_at"),
        "model_version": prediction.get("model_version"),
        "rows_used": prediction.get("dataset_rows"),
    }
