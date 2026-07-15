"""AQI forecast helpers based on weather-shaped pollutant projections."""
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import numpy as np

from aqi_utils import classify_aqi
from model_loader_service import predict_with_production_model


def forecast_next_7_days(measurements: Dict[str, float]) -> List[Dict]:
    rng = np.random.default_rng(17)
    today = datetime.now(timezone.utc).date()
    rows = []
    for day in range(1, 8):
        projected = {}
        for key, value in measurements.items():
            if value is None:
                continue
            trend = 1 + (day * 0.018)
            weather_cycle = 1 + np.sin(day / 7 * np.pi) * 0.035
            noise = rng.normal(0, 0.018)
            projected[key] = round(max(0.0, float(value) * trend * weather_cycle * (1 + noise)), 3)
        prediction = predict_with_production_model(projected)
        info = classify_aqi(prediction["prediction"])
        rows.append({
            "day": day,
            "date": (today + timedelta(days=day)).isoformat(),
            "aqi": info["aqi"],
            "category": info["category"],
            "color": info["color"],
            "features": projected,
        })
    return rows
