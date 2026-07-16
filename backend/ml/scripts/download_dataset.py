"""Create or refresh raw datasets for AutoML training.

The pipeline automatically consumes CSV files placed in ``backend/ml/datasets/raw``.
When no CSV is present, this script creates a deterministic multi-city baseline
dataset so the full training command remains runnable offline.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pandas as pd

from utils import RAW_DIR, configure_logging, ensure_dirs

LOCATIONS = [
    {"city": "Delhi", "state": "Delhi", "country": "IN", "latitude": 28.6139, "longitude": 77.2090},
    {"city": "Mumbai", "state": "Maharashtra", "country": "IN", "latitude": 19.0760, "longitude": 72.8777},
    {"city": "Jaipur", "state": "Rajasthan", "country": "IN", "latitude": 26.9124, "longitude": 75.7873},
    {"city": "Ahmedabad", "state": "Gujarat", "country": "IN", "latitude": 23.0225, "longitude": 72.5714},
    {"city": "Lucknow", "state": "Uttar Pradesh", "country": "IN", "latitude": 26.8467, "longitude": 80.9462},
    {"city": "Pune", "state": "Maharashtra", "country": "IN", "latitude": 18.5204, "longitude": 73.8567},
    {"city": "Hyderabad", "state": "Telangana", "country": "IN", "latitude": 17.3850, "longitude": 78.4867},
    {"city": "Bangalore", "state": "Karnataka", "country": "IN", "latitude": 12.9716, "longitude": 77.5946},
    {"city": "Chennai", "state": "Tamil Nadu", "country": "IN", "latitude": 13.0827, "longitude": 80.2707},
    {"city": "Kolkata", "state": "West Bengal", "country": "IN", "latitude": 22.5726, "longitude": 88.3639},
]


def _aqi(row: Dict[str, float]) -> float:
    return min(500.0, max(row["pm25"] * 1.9, row["pm10"] * 0.72, row["no2"] * 0.9, row["o3"] * 0.8, row["co"] * 35))


def generate_baseline(days: int = 730) -> pd.DataFrame:
    rows: List[Dict] = []
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(days=1)
    start = end - timedelta(days=days)
    for location in LOCATIONS:
        seed = sum(ord(char) for char in location["city"])
        cursor = start
        while cursor <= end:
            hour = cursor.hour
            day = cursor.timetuple().tm_yday
            month = cursor.month
            traffic = 1.0 + (0.35 if hour in (8, 9, 18, 19, 20) else 0.0)
            winter = 1.4 if month in (11, 12, 1, 2) else 0.9
            monsoon = 0.72 if month in (6, 7, 8, 9) else 1.0
            wind = max(0.4, 2.2 + math.sin(day / 18) + (seed % 7) * 0.08)
            humidity = min(96, max(25, 55 + 18 * math.sin(day / 32)))
            temp = 26 + 9 * math.sin((day - 80) / 58) + (seed % 6) * 0.2
            pm25 = max(6, (42 + (seed % 21)) * traffic * winter * monsoon / (1 + wind * 0.08))
            row = {
                **location,
                "date": cursor.isoformat(),
                "pm25": round(pm25, 3),
                "pm10": round(pm25 * (1.8 + (seed % 5) * 0.06), 3),
                "no2": round(18 * traffic * winter, 3),
                "so2": round(6 + (seed % 4), 3),
                "co": round(0.45 * traffic * winter, 3),
                "o3": round(max(8, 42 + temp * 0.8 - humidity * 0.2), 3),
                "temp": round(temp, 3),
                "humidity": round(humidity, 3),
                "pressure": round(1008 + 5 * math.sin(day / 24), 3),
                "wind": round(wind, 3),
                "rain": round(3.5 if month in (7, 8) and hour in (15, 16, 17) else 0.0, 3),
                "clouds": round(70 if month in (7, 8) else 28, 3),
                "visibility": 10000,
            }
            row["aqi"] = round(_aqi(row), 1)
            rows.append(row)
            cursor += timedelta(hours=1)
    return pd.DataFrame(rows)


def main() -> Dict:
    logger = configure_logging()
    ensure_dirs()
    existing = list(RAW_DIR.glob("*.csv"))
    if existing:
        logger.info("Using %s raw CSV dataset(s).", len(existing))
        return {"raw_files": [path.name for path in existing], "generated": False}
    frame = generate_baseline()
    path = RAW_DIR / "generated_multi_city_aqi.csv"
    frame.to_csv(path, index=False)
    logger.info("Generated offline baseline dataset: %s rows at %s", len(frame), path)
    return {"raw_files": [path.name], "generated": True, "rows": len(frame)}


if __name__ == "__main__":
    main()
