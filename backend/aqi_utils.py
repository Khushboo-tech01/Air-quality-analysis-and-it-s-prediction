"""AQI Analysis & Prediction — utilities for AQI classification."""
from typing import Dict, List, Tuple


AQI_CATEGORIES: List[Dict] = [
    {"low": 0,   "high": 50,  "label": "Good",                            "color": "#10B981", "advice": "Air quality is satisfactory, and air pollution poses little or no risk."},
    {"low": 51,  "high": 100, "label": "Moderate",                        "color": "#F59E0B", "advice": "Air quality is acceptable. However, there may be a risk for some people, particularly those unusually sensitive to air pollution."},
    {"low": 101, "high": 150, "label": "Unhealthy for Sensitive Groups",  "color": "#F97316", "advice": "Members of sensitive groups may experience health effects. The general public is less likely to be affected."},
    {"low": 151, "high": 200, "label": "Unhealthy",                       "color": "#EF4444", "advice": "Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects."},
    {"low": 201, "high": 300, "label": "Very Unhealthy",                  "color": "#8B5CF6", "advice": "Health alert: The risk of health effects is increased for everyone."},
    {"low": 301, "high": 10_000, "label": "Hazardous",                    "color": "#7F1D1D", "advice": "Health warning of emergency conditions: everyone is more likely to be affected. Avoid all outdoor exertion."},
]


def classify_aqi(aqi: float) -> Dict:
    aqi = max(0.0, float(aqi))
    for cat in AQI_CATEGORIES:
        if cat["low"] <= aqi <= cat["high"]:
            return {"aqi": round(aqi, 1), "category": cat["label"], "color": cat["color"], "advice": cat["advice"]}
    return {"aqi": round(aqi, 1), "category": "Hazardous", "color": "#7F1D1D", "advice": AQI_CATEGORIES[-1]["advice"]}


# EPA breakpoints for computing AQI sub-index from PM2.5 (24-hr avg, µg/m³)
_PM25_BP: List[Tuple[float, float, float, float]] = [
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 500.4, 301, 500),
]


def pm25_to_aqi(pm25: float) -> float:
    if pm25 is None or pm25 < 0:
        return 0.0
    for c_lo, c_hi, i_lo, i_hi in _PM25_BP:
        if c_lo <= pm25 <= c_hi:
            return round((i_hi - i_lo) / (c_hi - c_lo) * (pm25 - c_lo) + i_lo, 1)
    return 500.0


# Common column name aliases (lowercased)
POLLUTANT_ALIASES: Dict[str, List[str]] = {
    "pm25":    ["pm2.5", "pm25", "pm_2_5", "pm2_5", "pm 2.5"],
    "pm10":    ["pm10", "pm_10", "pm 10"],
    "no2":     ["no2", "nitrogen dioxide"],
    "so2":     ["so2", "sulphur dioxide", "sulfur dioxide"],
    "co":      ["co", "carbon monoxide"],
    "o3":      ["o3", "ozone"],
    "temp":    ["temperature", "temp", "t"],
    "humidity":["humidity", "rh", "relative humidity"],
    "wind":    ["wind_speed", "wind speed", "windspeed", "ws", "wind"],
    "pressure":["pressure", "p", "atm_pressure"],
}

TARGET_ALIASES = ["aqi", "air quality index", "aqi_value", "aqi value"]
DATE_ALIASES = ["date", "datetime", "timestamp", "time"]
LOCATION_ALIASES = ["city", "location", "station", "region", "area"]


def detect_column(columns: List[str], aliases: List[str]) -> str | None:
    lowered = {c.lower().strip(): c for c in columns}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    # Fuzzy contains are useful for descriptive names, but short aliases such as
    # "p" and "t" must not match unrelated columns like PM2.5 or Date.
    for c_lower, c_orig in lowered.items():
        for alias in aliases:
            if len(alias) >= 3 and alias in c_lower:
                return c_orig
    return None


def detect_schema(columns: List[str]) -> Dict:
    features: Dict[str, str | None] = {}
    for key, aliases in POLLUTANT_ALIASES.items():
        features[key] = detect_column(columns, aliases)
    return {
        "target": detect_column(columns, TARGET_ALIASES),
        "date": detect_column(columns, DATE_ALIASES),
        "location": detect_column(columns, LOCATION_ALIASES),
        "features": features,
    }
