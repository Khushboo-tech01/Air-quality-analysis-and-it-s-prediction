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


def health_advice_for_category(category: str) -> Dict:
    normalized = (category or "").lower()
    if normalized == "good":
        return {"risk_level": "Low", "advice": "Enjoy outdoor activities."}
    if normalized == "moderate":
        return {"risk_level": "Moderate", "advice": "Sensitive people should reduce prolonged outdoor exposure."}
    if "sensitive" in normalized or normalized == "unhealthy":
        return {"risk_level": "Poor", "advice": "Wear masks and limit outdoor exercise."}
    if "very" in normalized:
        return {"risk_level": "Very Poor", "advice": "Avoid outdoor activity."}
    return {"risk_level": "Hazardous", "advice": "Stay indoors and use air purifiers."}


# India CPCB-style pollutant breakpoints. PM/NO2/SO2/O3 are ug/m3; CO is mg/m3.
_INDIA_BP: Dict[str, List[Tuple[float, float, float, float]]] = {
    "pm25": [(0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200), (91, 120, 201, 300), (121, 250, 301, 400), (251, 500, 401, 500)],
    "pm10": [(0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200), (251, 350, 201, 300), (351, 430, 301, 400), (431, 600, 401, 500)],
    "no2": [(0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200), (181, 280, 201, 300), (281, 400, 301, 400), (401, 1000, 401, 500)],
    "so2": [(0, 40, 0, 50), (41, 80, 51, 100), (81, 380, 101, 200), (381, 800, 201, 300), (801, 1600, 301, 400), (1601, 2000, 401, 500)],
    "co": [(0, 1, 0, 50), (1.1, 2, 51, 100), (2.1, 10, 101, 200), (10.1, 17, 201, 300), (17.1, 34, 301, 400), (34.1, 50, 401, 500)],
    "o3": [(0, 50, 0, 50), (51, 100, 51, 100), (101, 168, 101, 200), (169, 208, 201, 300), (209, 748, 301, 400), (749, 1000, 401, 500)],
}


def pollutant_subindex(pollutant: str, value: float | None, standard: str = "IN_AQI") -> float | None:
    if value is None or value < 0:
        return None
    breakpoints = _INDIA_BP.get(pollutant.lower())
    if not breakpoints:
        return None
    for c_lo, c_hi, i_lo, i_hi in breakpoints:
        if c_lo <= value <= c_hi:
            return round((i_hi - i_lo) / (c_hi - c_lo) * (value - c_lo) + i_lo, 1)
    return 500.0


def pollutants_to_aqi(values: Dict[str, float | None], standard: str = "IN_AQI") -> float:
    subindices = [
        pollutant_subindex(key, values.get(key), standard)
        for key in ("pm25", "pm10", "no2", "so2", "co", "o3")
    ]
    valid = [value for value in subindices if value is not None]
    return round(max(valid), 1) if valid else 0.0


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
