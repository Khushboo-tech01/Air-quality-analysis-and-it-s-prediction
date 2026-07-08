"""Sample dataset generator — synthetic Indian city air quality data."""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


CITIES = ["Delhi", "Mumbai", "Bengaluru", "Kolkata", "Chennai", "Hyderabad", "Ahmedabad", "Pune"]
CITY_BASE = {
    "Delhi":     {"pm25": 130, "pm10": 210, "no2": 55, "so2": 15, "co": 1.4, "o3": 30},
    "Mumbai":    {"pm25": 65,  "pm10": 110, "no2": 40, "so2": 10, "co": 0.9, "o3": 28},
    "Bengaluru": {"pm25": 45,  "pm10": 80,  "no2": 32, "so2": 8,  "co": 0.7, "o3": 25},
    "Kolkata":   {"pm25": 90,  "pm10": 150, "no2": 42, "so2": 12, "co": 1.1, "o3": 26},
    "Chennai":   {"pm25": 50,  "pm10": 95,  "no2": 30, "so2": 9,  "co": 0.8, "o3": 27},
    "Hyderabad": {"pm25": 55,  "pm10": 100, "no2": 35, "so2": 10, "co": 0.9, "o3": 26},
    "Ahmedabad": {"pm25": 75,  "pm10": 130, "no2": 38, "so2": 12, "co": 1.0, "o3": 29},
    "Pune":      {"pm25": 60,  "pm10": 100, "no2": 33, "so2": 9,  "co": 0.8, "o3": 26},
}


def _seasonal_factor(month: int) -> float:
    # Higher pollution in winter (Nov-Feb)
    if month in (11, 12, 1, 2):
        return 1.6
    if month in (3, 4, 10):
        return 1.15
    if month in (5, 6):
        return 0.85
    return 0.7  # monsoon Jul-Sep


def generate_sample_csv(path: Path, days: int = 365) -> Path:
    random.seed(42)
    rows = []
    start = datetime(2024, 1, 1)
    for i in range(days):
        current = start + timedelta(days=i)
        for city in CITIES:
            base = CITY_BASE[city]
            f = _seasonal_factor(current.month)
            pm25 = max(5,  base["pm25"] * f * random.uniform(0.7, 1.3))
            pm10 = max(10, base["pm10"] * f * random.uniform(0.7, 1.3))
            no2  = max(2,  base["no2"]  * f * random.uniform(0.7, 1.3))
            so2  = max(1,  base["so2"]  * f * random.uniform(0.7, 1.3))
            co   = max(0.1,base["co"]   * f * random.uniform(0.7, 1.3))
            o3   = max(2,  base["o3"]   * random.uniform(0.6, 1.4))
            temp = round(random.uniform(18, 36), 1)
            hum  = round(random.uniform(35, 85), 1)
            wind = round(random.uniform(1, 9), 1)
            pres = round(random.uniform(996, 1018), 1)
            # AQI from PM2.5 (EPA formula, simplified)
            aqi  = min(500, pm25 * 1.5 + random.uniform(-5, 5))
            rows.append({
                "date": current.strftime("%Y-%m-%d"),
                "city": city,
                "PM2.5": round(pm25, 2),
                "PM10":  round(pm10, 2),
                "NO2":   round(no2, 2),
                "SO2":   round(so2, 2),
                "CO":    round(co, 3),
                "O3":    round(o3, 2),
                "temperature": temp,
                "humidity": hum,
                "wind_speed": wind,
                "pressure": pres,
                "AQI":   round(aqi, 1),
            })
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path
