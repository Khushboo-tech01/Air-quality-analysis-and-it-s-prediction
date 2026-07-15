"""OpenWeather data fetching with a short in-memory cache."""
import asyncio
import json
import time
import urllib.request
from typing import Dict


_CACHE: Dict[str, Dict] = {}
_TTL_SECONDS = 600


def _read_json(url: str) -> Dict:
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


async def _cached_json(key: str, url: str) -> Dict:
    cached = _CACHE.get(key)
    if cached and time.time() - cached["at"] < _TTL_SECONDS:
        return cached["data"]
    data = await asyncio.to_thread(_read_json, url)
    _CACHE[key] = {"at": time.time(), "data": data}
    return data


async def fetch_environment(api_key: str, latitude: float, longitude: float) -> Dict:
    weather_url = (
        "https://api.openweathermap.org/data/2.5/weather?"
        f"lat={latitude}&lon={longitude}&units=metric&appid={api_key}"
    )
    air_url = (
        "https://api.openweathermap.org/data/2.5/air_pollution?"
        f"lat={latitude}&lon={longitude}&appid={api_key}"
    )
    weather, air = await asyncio.gather(
        _cached_json(f"weather:{latitude:.4f}:{longitude:.4f}", weather_url),
        _cached_json(f"air:{latitude:.4f}:{longitude:.4f}", air_url),
    )
    air_entry = (air.get("list") or [{}])[0]
    components = air_entry.get("components") or {}
    timestamp = air_entry.get("dt") or weather.get("dt")
    return {
        "timestamp": timestamp,
        "timezone": weather.get("timezone"),
        "sunrise": weather.get("sys", {}).get("sunrise"),
        "sunset": weather.get("sys", {}).get("sunset"),
        "weather_condition": (weather.get("weather") or [{}])[0].get("description"),
        "source": "OpenWeather APIs",
        "official_aqi": air_entry.get("main", {}).get("aqi"),
        "measurements": {
            "temp": weather.get("main", {}).get("temp"),
            "humidity": weather.get("main", {}).get("humidity"),
            "pressure": weather.get("main", {}).get("pressure"),
            "wind": weather.get("wind", {}).get("speed"),
            "pm25": components.get("pm2_5"),
            "pm10": components.get("pm10"),
            "no2": components.get("no2"),
            "so2": components.get("so2"),
            "co": components.get("co") / 1000 if components.get("co") is not None else None,
            "o3": components.get("o3"),
        },
    }
