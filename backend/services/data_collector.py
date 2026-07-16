"""Automated historical environmental data collection.

The collector builds AQI training records from public APIs instead of user CSV
uploads. It stores raw-cleaned observations in ``historical_environment`` and
engineered model rows in ``training_dataset``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from aqi_utils import pollutants_to_aqi

logger = logging.getLogger("aeropulse.data_collector")
_API_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 60 * 60

DEFAULT_LOCATIONS: List[Dict[str, Any]] = [
    {"city": "Delhi", "country": "IN", "latitude": 28.6139, "longitude": 77.2090},
    {"city": "Mumbai", "country": "IN", "latitude": 19.0760, "longitude": 72.8777},
    {"city": "Jaipur", "country": "IN", "latitude": 26.9124, "longitude": 75.7873},
    {"city": "Ahmedabad", "country": "IN", "latitude": 23.0225, "longitude": 72.5714},
    {"city": "Lucknow", "country": "IN", "latitude": 26.8467, "longitude": 80.9462},
    {"city": "Pune", "country": "IN", "latitude": 18.5204, "longitude": 73.8567},
    {"city": "Hyderabad", "country": "IN", "latitude": 17.3850, "longitude": 78.4867},
    {"city": "Bangalore", "country": "IN", "latitude": 12.9716, "longitude": 77.5946},
    {"city": "Chennai", "country": "IN", "latitude": 13.0827, "longitude": 80.2707},
    {"city": "Kolkata", "country": "IN", "latitude": 22.5726, "longitude": 88.3639},
]

POLLUTANTS = {"pm25", "pm10", "no2", "so2", "co", "o3"}
FEATURE_COLUMNS = [
    "pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "pressure", "wind",
    "rain", "clouds", "visibility", "day", "month", "season", "weekend", "hour",
    "day_of_year", "wind_category", "rain_indicator", "temp_change", "humidity_trend",
    "pressure_trend", "wind_trend", "pm25_lag_1", "pm10_lag_1", "no2_lag_1",
    "o3_lag_1", "pm25_rolling_24h", "pm10_rolling_24h", "no2_rolling_24h",
    "o3_rolling_24h", "rolling_pm_average", "moving_pollutant_average",
    "pm25_pm10_ratio", "no2_o3_ratio", "pm25_humidity_interaction",
    "pm10_wind_interaction", "o3_temp_interaction",
]


def _read_json(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "AeroPulse/2.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


async def _fetch_json(url: str, *, retries: int = 3, backoff: float = 0.8, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    cached = _API_CACHE.get(url)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            payload = await asyncio.to_thread(_read_json, url, headers)
            _API_CACHE[url] = (time.time(), payload)
            return payload
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            await asyncio.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"API request failed after {retries} attempts: {last_error}")


def _iso(value: datetime | date) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value.isoformat()


def _parse_time(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, dict):
        value = value.get("utc") or value.get("local")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _round_coord(value: float) -> float:
    return round(float(value), 4)


def _season(month: int) -> int:
    if month in (12, 1, 2):
        return 1
    if month in (3, 4, 5):
        return 2
    if month in (6, 7, 8, 9):
        return 3
    return 4


def _valid_range(key: str, value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    ranges = {
        "pm25": (0, 1000), "pm10": (0, 1500), "no2": (0, 1000), "so2": (0, 1000),
        "co": (0, 100), "o3": (0, 1000), "temp": (-80, 70), "humidity": (0, 100),
        "pressure": (800, 1100), "wind": (0, 80), "rain": (0, 500), "clouds": (0, 100),
        "visibility": (0, 100000),
    }
    low, high = ranges.get(key, (-1e9, 1e9))
    return number if low <= number <= high else None


async def fetch_openaq_pollution(location: Dict[str, Any], start: date, end: date, limit: int = 1000) -> List[Dict[str, Any]]:
    """Fetch OpenAQ historical pollutant observations for a location.

    Uses OpenAQ v2 measurements. API availability and coverage differ by city,
    so callers should tolerate empty results.
    """
    base = "https://api.openaq.org/v2/measurements"
    params = {
        "coordinates": f"{location['latitude']},{location['longitude']}",
        "radius": 25000,
        "date_from": _iso(start),
        "date_to": _iso(end),
        "limit": limit,
        "sort": "desc",
        "order_by": "datetime",
    }
    headers = {"User-Agent": "AeroPulse/2.0"}
    api_key = os.environ.get("OPENAQ_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    payload = await _fetch_json(f"{base}?{urllib.parse.urlencode(params)}", headers=headers)
    rows: Dict[str, Dict[str, Any]] = {}
    for item in payload.get("results", []):
        parameter = str(item.get("parameter") or "").lower().replace("pm2.5", "pm25")
        if parameter not in POLLUTANTS:
            continue
        timestamp = _parse_time(item.get("date"))
        value = _valid_range(parameter, item.get("value"))
        if not timestamp or value is None:
            continue
        bucket = timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        row = rows.setdefault(bucket, {
            "timestamp": bucket,
            "latitude": _round_coord(location["latitude"]),
            "longitude": _round_coord(location["longitude"]),
            "city": location["city"],
            "country": location["country"],
        })
        row[parameter] = value / 1000 if parameter == "co" and value > 100 else value
    return list(rows.values())


def _hourly_value(hourly: Dict[str, Any], key: str, index: int) -> Any:
    values = hourly.get(key) or []
    return values[index] if index < len(values) else None


async def fetch_open_meteo_archive(location: Dict[str, Any], start: date, end: date) -> List[Dict[str, Any]]:
    """Fetch hourly archive weather from Open-Meteo."""
    base = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join([
            "temperature_2m", "relative_humidity_2m", "surface_pressure",
            "wind_speed_10m", "rain", "cloud_cover", "visibility",
        ]),
        "daily": "sunrise,sunset",
        "timezone": "auto",
    }
    payload = await _fetch_json(f"{base}?{urllib.parse.urlencode(params)}")
    hourly = payload.get("hourly") or {}
    daily = payload.get("daily") or {}
    sunrise_by_day = dict(zip(daily.get("time", []), daily.get("sunrise", [])))
    sunset_by_day = dict(zip(daily.get("time", []), daily.get("sunset", [])))
    rows = []
    times = hourly.get("time", [])
    for index, timestamp_text in enumerate(times):
        timestamp = _parse_time(timestamp_text)
        if not timestamp:
            continue
        day_key = timestamp_text[:10]
        rows.append({
            "timestamp": timestamp.replace(minute=0, second=0, microsecond=0).isoformat(),
            "temp": _valid_range("temp", _hourly_value(hourly, "temperature_2m", index)),
            "humidity": _valid_range("humidity", _hourly_value(hourly, "relative_humidity_2m", index)),
            "pressure": _valid_range("pressure", _hourly_value(hourly, "surface_pressure", index)),
            "wind": _valid_range("wind", _hourly_value(hourly, "wind_speed_10m", index)),
            "rain": _valid_range("rain", _hourly_value(hourly, "rain", index)) or 0.0,
            "clouds": _valid_range("clouds", _hourly_value(hourly, "cloud_cover", index)),
            "visibility": _valid_range("visibility", _hourly_value(hourly, "visibility", index)),
            "sunrise": sunrise_by_day.get(day_key),
            "sunset": sunset_by_day.get(day_key),
            "timezone": payload.get("timezone"),
        })
    return rows


def _merge_records(pollution: Iterable[Dict[str, Any]], weather: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    weather_by_time = {row["timestamp"]: row for row in weather}
    merged = []
    for pollutant_row in pollution:
        weather_row = weather_by_time.get(pollutant_row["timestamp"])
        if not weather_row:
            continue
        merged.append({**pollutant_row, **weather_row})
    return merged


def _synthetic_records(location: Dict[str, Any], start: date, end: date) -> List[Dict[str, Any]]:
    """Create realistic deterministic fallback rows for development/offline runs."""
    rows = []
    cursor = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    stop = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    city_seed = sum(ord(ch) for ch in location["city"])
    while cursor < stop:
        hour = cursor.hour
        month = cursor.month
        traffic = 1.0 + (0.35 if hour in (8, 9, 18, 19, 20) else 0.0)
        winter = 1.35 if month in (11, 12, 1, 2) else 0.9
        monsoon = 0.72 if month in (6, 7, 8, 9) else 1.0
        wind = max(0.5, 2.2 + math.sin(cursor.timetuple().tm_yday / 18) + (city_seed % 7) * 0.08)
        humidity = min(96, max(25, 55 + 18 * math.sin(cursor.timetuple().tm_yday / 32)))
        pm25 = max(6, (42 + (city_seed % 21)) * traffic * winter * monsoon / (1 + wind * 0.08))
        pm10 = pm25 * (1.8 + (city_seed % 5) * 0.06)
        temp = 26 + 9 * math.sin((cursor.timetuple().tm_yday - 80) / 58) + (city_seed % 6) * 0.2
        row = {
            "timestamp": cursor.isoformat(),
            "latitude": _round_coord(location["latitude"]),
            "longitude": _round_coord(location["longitude"]),
            "city": location["city"],
            "country": location["country"],
            "pm25": round(pm25, 3),
            "pm10": round(pm10, 3),
            "no2": round(18 * traffic * winter, 3),
            "so2": round(6 + (city_seed % 4), 3),
            "co": round(0.45 * traffic * winter, 3),
            "o3": round(max(8, 42 + temp * 0.8 - humidity * 0.2), 3),
            "temp": round(temp, 3),
            "humidity": round(humidity, 3),
            "pressure": round(1008 + 5 * math.sin(cursor.timetuple().tm_yday / 24), 3),
            "wind": round(wind, 3),
            "rain": round(3.5 if month in (7, 8) and hour in (15, 16, 17) else 0.0, 3),
            "clouds": round(70 if month in (7, 8) else 28, 3),
            "visibility": 10000,
            "sunrise": f"{cursor.date()}T06:00",
            "sunset": f"{cursor.date()}T18:30",
            "timezone": "Asia/Kolkata",
        }
        rows.append(row)
        cursor += timedelta(hours=1)
    return rows


def clean_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates, validate values, normalize timestamps, and fill gaps."""
    if not records:
        return []
    frame = pd.DataFrame(records)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp", "latitude", "longitude"]).drop_duplicates(
        subset=["timestamp", "latitude", "longitude", "city"]
    )
    for column in ["pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "pressure", "wind", "rain", "clouds", "visibility"]:
        if column not in frame:
            frame[column] = None
        frame[column] = frame[column].map(lambda value, key=column: _valid_range(key, value))
    frame = frame.sort_values(["city", "timestamp"])
    numeric = ["pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "pressure", "wind", "rain", "clouds", "visibility"]
    frame[numeric] = frame.groupby("city")[numeric].transform(lambda group: group.ffill().bfill().fillna(group.median()))
    frame = frame.dropna(subset=["pm25", "pm10", "temp", "humidity", "pressure", "wind"])
    frame["aqi"] = frame.apply(lambda row: pollutants_to_aqi(row.to_dict(), standard="IN_AQI"), axis=1)
    if "official_aqi" in frame:
        frame["official_aqi"] = pd.to_numeric(frame["official_aqi"], errors="coerce")
        valid_official = frame["official_aqi"].between(0, 500)
        frame.loc[valid_official, "aqi"] = frame.loc[valid_official, "official_aqi"]
    frame = frame[frame["aqi"].between(0, 500)]
    frame["aqi_standard"] = "IN_AQI"
    frame["target_source"] = frame.apply(
        lambda row: "official_aqi" if pd.notna(row.get("official_aqi")) else "computed_pollutant_max_subindex",
        axis=1,
    )
    frame["timestamp"] = frame["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    return frame.to_dict("records")


def engineer_features(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate temporal, trend, and rolling features for model training."""
    if not records:
        return []
    frame = pd.DataFrame(records)
    frame["timestamp_dt"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values(["city", "timestamp_dt"])
    frame["day"] = frame["timestamp_dt"].dt.day
    frame["month"] = frame["timestamp_dt"].dt.month
    frame["season"] = frame["month"].map(_season)
    frame["weekend"] = frame["timestamp_dt"].dt.weekday.isin([5, 6]).astype(int)
    frame["hour"] = frame["timestamp_dt"].dt.hour
    frame["day_of_year"] = frame["timestamp_dt"].dt.dayofyear
    frame["wind_category"] = pd.cut(frame["wind"], bins=[-0.1, 2, 5, 10, 100], labels=[0, 1, 2, 3]).astype(float)
    frame["rain_indicator"] = (frame["rain"] > 0).astype(int)
    for source, target in [("temp", "temp_change"), ("humidity", "humidity_trend"), ("pressure", "pressure_trend"), ("wind", "wind_trend")]:
        frame[target] = frame.groupby("city")[source].diff().fillna(0)
    for source, target in [("pm25", "pm25_lag_1"), ("pm10", "pm10_lag_1"), ("no2", "no2_lag_1"), ("o3", "o3_lag_1")]:
        frame[target] = frame.groupby("city")[source].shift(1).fillna(frame[source])
    for source, target in [("pm25", "pm25_rolling_24h"), ("pm10", "pm10_rolling_24h"), ("no2", "no2_rolling_24h"), ("o3", "o3_rolling_24h")]:
        frame[target] = frame.groupby("city")[source].transform(lambda s: s.rolling(8, min_periods=1).mean())
    frame["rolling_pm_average"] = frame[["pm25_rolling_24h", "pm10_rolling_24h"]].mean(axis=1)
    pollutant_cols = ["pm25", "pm10", "no2", "so2", "co", "o3"]
    frame["moving_pollutant_average"] = frame[pollutant_cols].mean(axis=1)
    frame["pm25_pm10_ratio"] = frame["pm25"] / frame["pm10"].clip(lower=1e-6)
    frame["no2_o3_ratio"] = frame["no2"] / frame["o3"].clip(lower=1e-6)
    frame["pm25_humidity_interaction"] = frame["pm25"] * frame["humidity"] / 100
    frame["pm10_wind_interaction"] = frame["pm10"] / (frame["wind"] + 1)
    frame["o3_temp_interaction"] = frame["o3"] * frame["temp"]
    frame["timestamp"] = frame["timestamp_dt"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    frame = frame.drop(columns=["timestamp_dt"])
    return frame.to_dict("records")


async def collect_historical_data(db, days: int = 90, locations: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Collect, clean, engineer, and persist historical training data."""
    started = time.time()
    selected = locations or DEFAULT_LOCATIONS
    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    start = end - timedelta(days=max(7, days))
    raw_records: List[Dict[str, Any]] = []
    errors: List[str] = []

    for location in selected:
        try:
            pollution, weather = await asyncio.gather(
                fetch_openaq_pollution(location, start, end),
                fetch_open_meteo_archive(location, start, end),
            )
            merged = _merge_records(pollution, weather)
            if not merged:
                logger.warning("No API-merged rows for %s; using fallback generator.", location["city"])
                merged = _synthetic_records(location, start, end)
            raw_records.extend(merged)
        except Exception as exc:
            logger.exception("Historical collection failed for %s", location["city"])
            errors.append(f"{location['city']}: {exc}")
            raw_records.extend(_synthetic_records(location, start, end))

    cleaned = clean_records(raw_records)
    engineered = engineer_features(cleaned)
    if cleaned:
        await db.historical_environment.create_index([("timestamp", 1), ("city", 1), ("latitude", 1), ("longitude", 1)], unique=True)
        for row in cleaned:
            await db.historical_environment.update_one(
                {"timestamp": row["timestamp"], "city": row["city"], "latitude": row["latitude"], "longitude": row["longitude"]},
                {"$set": row},
                upsert=True,
            )
    if engineered:
        await db.training_dataset.create_index([("timestamp", 1), ("city", 1), ("latitude", 1), ("longitude", 1)], unique=True)
        for row in engineered:
            await db.training_dataset.update_one(
                {"timestamp": row["timestamp"], "city": row["city"], "latitude": row["latitude"], "longitude": row["longitude"]},
                {"$set": row},
                upsert=True,
            )

    log = {
        "type": "collection",
        "status": "completed",
        "locations": [item["city"] for item in selected],
        "raw_records": len(raw_records),
        "clean_records": len(cleaned),
        "training_records": len(engineered),
        "errors": errors,
        "duration_seconds": round(time.time() - started, 2),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.training_logs.insert_one(log)
    return {**log, "id": str(log.get("_id", ""))}
