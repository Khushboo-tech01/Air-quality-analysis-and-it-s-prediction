"""AQI forecast helpers based on future weather and pollutant projections."""
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import numpy as np

from aqi_utils import classify_aqi
from aqi_utils import health_advice_for_category
from model_loader_service import predict_with_production_model


def _daily_weather(forecast_items: List[Dict]) -> List[Dict]:
    today = datetime.now(timezone.utc).date().isoformat()
    by_date: Dict[str, List[Dict]] = {}
    for item in forecast_items:
        timestamp = item.get("dt")
        if not timestamp:
            continue
        day = datetime.fromtimestamp(timestamp, tz=timezone.utc).date().isoformat()
        if day <= today:
            continue
        by_date.setdefault(day, []).append(item)
    days = []
    for day, rows in sorted(by_date.items()):
        temps = [row.get("main", {}).get("temp") for row in rows if row.get("main", {}).get("temp") is not None]
        humidity = [row.get("main", {}).get("humidity") for row in rows if row.get("main", {}).get("humidity") is not None]
        pressure = [row.get("main", {}).get("pressure") for row in rows if row.get("main", {}).get("pressure") is not None]
        wind = [row.get("wind", {}).get("speed") for row in rows if row.get("wind", {}).get("speed") is not None]
        rain = [row.get("rain", {}).get("3h", 0) for row in rows]
        clouds = [row.get("clouds", {}).get("all", 0) for row in rows]
        descriptions = [row.get("weather", [{}])[0].get("description") for row in rows if row.get("weather")]
        days.append({
            "date": day,
            "temp": float(np.mean(temps)) if temps else None,
            "humidity": float(np.mean(humidity)) if humidity else None,
            "pressure": float(np.mean(pressure)) if pressure else None,
            "wind": float(np.mean(wind)) if wind else None,
            "rain": float(np.sum(rain)) if rain else 0.0,
            "clouds": float(np.mean(clouds)) if clouds else 0.0,
            "summary": descriptions[len(descriptions) // 2] if descriptions else "forecast unavailable",
        })
    return days[:7]


def _project_pollutants(current: Dict[str, float], weather: Dict, day: int) -> Dict[str, float]:
    projected = dict(current)
    wind = float(weather.get("wind") or current.get("wind") or 2.0)
    humidity = float(weather.get("humidity") or current.get("humidity") or 50.0)
    temp = float(weather.get("temp") or current.get("temp") or 25.0)
    rain = float(weather.get("rain") or 0.0)
    pressure = float(weather.get("pressure") or current.get("pressure") or 1013.0)
    clouds = float(weather.get("clouds") or 0.0)

    dispersion = max(0.72, 1 - min(wind, 12) * 0.025)
    rain_washout = max(0.68, 1 - min(rain, 25) * 0.018)
    humidity_factor = 1 + max(0.0, humidity - 60) * 0.002
    temp_ozone_factor = 1 + max(0.0, temp - 25) * 0.012
    stability = 1 + max(0.0, pressure - 1013) * 0.0008 + max(0.0, 45 - wind * 10) * 0.001
    decay = max(0.76, 1 - day * 0.025)

    particulate_factor = decay * dispersion * rain_washout * humidity_factor * stability
    gas_factor = decay * (0.88 + min(clouds, 100) / 1000) * stability
    ozone_factor = decay * temp_ozone_factor * (1 - min(clouds, 100) * 0.0015)

    for key in ("pm25", "pm10"):
        if current.get(key) is not None:
            projected[key] = round(max(0.0, float(current[key]) * particulate_factor), 3)
    for key in ("no2", "so2", "co"):
        if current.get(key) is not None:
            projected[key] = round(max(0.0, float(current[key]) * gas_factor), 3)
    if current.get("o3") is not None:
        projected["o3"] = round(max(0.0, float(current["o3"]) * ozone_factor), 3)

    projected.update({
        "temp": round(temp, 3),
        "humidity": round(humidity, 3),
        "pressure": round(pressure, 3),
        "wind": round(wind, 3),
    })
    return projected


def _explain(day_label: str, info: Dict, current: Dict, projected: Dict) -> str:
    reasons = []
    if projected.get("wind", 0) < float(current.get("wind") or 0):
        reasons.append("wind speed is forecast to decrease")
    if projected.get("pm10", 0) >= float(current.get("pm10") or 0) * 0.9:
        reasons.append("PM10 remains elevated")
    if projected.get("o3", 0) > float(current.get("o3") or 0):
        reasons.append("ozone-forming conditions strengthen")
    if projected.get("humidity", 0) > 70:
        reasons.append("high humidity may slow pollutant dispersion")
    if not reasons:
        reasons.append("weather-driven pollutant dispersion is expected to moderate current levels")
    return f"{day_label}'s AQI is expected to be {info['category']} because " + " while ".join(reasons) + "."


def forecast_next_7_days(measurements: Dict[str, float], weather_forecast: List[Dict] | None = None) -> List[Dict]:
    today = datetime.now(timezone.utc).date()
    weather_days = _daily_weather(weather_forecast or [])
    rows = []
    confidence_schedule = [95, 92, 89, 85, 82, 79, 75]
    for day in range(1, 8):
        weather = weather_days[day - 1] if day - 1 < len(weather_days) else {
            "date": (today + timedelta(days=day)).isoformat(),
            "temp": measurements.get("temp"),
            "humidity": measurements.get("humidity"),
            "pressure": measurements.get("pressure"),
            "wind": measurements.get("wind"),
            "rain": 0,
            "clouds": 0,
            "summary": "forecast unavailable",
        }
        projected = _project_pollutants(measurements, weather, day)
        prediction = predict_with_production_model(projected)
        info = classify_aqi(prediction["prediction"])
        advice = health_advice_for_category(info["category"])
        model_confidence = float(prediction.get("confidence") or confidence_schedule[day - 1])
        confidence = max(75.0, min(float(confidence_schedule[day - 1]), model_confidence))
        day_label = "Tomorrow" if day == 1 else f"Day {day}"
        rows.append({
            "day": day,
            "label": day_label,
            "date": weather.get("date") or (today + timedelta(days=day)).isoformat(),
            "predicted_aqi": info["aqi"],
            "aqi": info["aqi"],
            "category": info["category"],
            "color": info["color"],
            "risk": advice["risk_level"],
            "confidence": round(confidence, 1),
            "health_advice": advice["advice"],
            "explanation": _explain(day_label, info, measurements, projected),
            "weather_summary": weather.get("summary"),
            "weather": weather,
            "features": projected,
        })
    return rows
