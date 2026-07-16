"""World Air Quality Index (WAQI) live AQI integration."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("aeropulse.waqi")

WAQI_BASE_URL = "https://api.waqi.info/feed"
_CACHE: Dict[str, Dict[str, Any]] = {}
_TTL_SECONDS = 5 * 60
_TIMEOUT_SECONDS = 12


def _token() -> str:
    token = os.environ.get("WAQI_API_TOKEN")
    if not token:
        raise RuntimeError("WAQI_API_TOKEN is not configured.")
    return token


def _read_json(url: str) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "AeroPulse/2.0"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


async def _cached_json(key: str, url: str, retries: int = 3) -> Dict[str, Any]:
    cached = _CACHE.get(key)
    if cached and time.time() - cached["at"] < _TTL_SECONDS:
        return cached["data"]

    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            data = await asyncio.to_thread(_read_json, url)
            _CACHE[key] = {"at": time.time(), "data": data}
            return data
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"WAQI request failed after {retries} attempts: {last_error}")


def _number(value: Any) -> Optional[float]:
    if isinstance(value, dict):
        value = value.get("v")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _aqi(value: Any) -> Optional[float]:
    if value in (None, "-", ""):
        return None
    number = _number(value)
    return round(number, 1) if number is not None else None


def _parse_timestamp(data: Dict[str, Any]) -> Any:
    time_info = data.get("time") or {}
    iso = time_info.get("iso")
    if iso:
        try:
            return int(datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
        except ValueError:
            return iso
    return time_info.get("v") or int(datetime.now(timezone.utc).timestamp())


def _normalize(payload: Dict[str, Any], *, source_query: str) -> Dict[str, Any]:
    if payload.get("status") != "ok":
        raise RuntimeError(f"WAQI returned status={payload.get('status')}: {payload.get('data')}")

    data = payload.get("data") or {}
    iaqi = data.get("iaqi") or {}
    city = data.get("city") or {}
    station_name = city.get("name") or source_query
    dominant_pollutant = data.get("dominentpol") or data.get("dominantpol")
    timestamp = _parse_timestamp(data)

    measurements = {
        "temp": _number(iaqi.get("t")),
        "humidity": _number(iaqi.get("h")),
        "pressure": _number(iaqi.get("p")),
        "wind": _number(iaqi.get("w")),
        "visibility": None,
        "pm25": _number(iaqi.get("pm25")),
        "pm10": _number(iaqi.get("pm10")),
        "no2": _number(iaqi.get("no2")),
        "so2": _number(iaqi.get("so2")),
        "co": _number(iaqi.get("co")),
        "o3": _number(iaqi.get("o3")),
    }

    return {
        "timestamp": timestamp,
        "timezone": data.get("time", {}).get("tz"),
        "sunrise": None,
        "sunset": None,
        "weather_condition": None,
        "source": "WAQI",
        "official_aqi": _aqi(data.get("aqi")),
        "dominant_pollutant": dominant_pollutant,
        "station_name": station_name,
        "measurements": measurements,
        "weather_forecast": [],
        "waqi": {
            "station": station_name,
            "dominant_pollutant": dominant_pollutant,
            "attributions": data.get("attributions", []),
            "source_query": source_query,
        },
    }


def _city_url(city: str, token: str) -> str:
    return f"{WAQI_BASE_URL}/{urllib.parse.quote(city.strip())}/?token={urllib.parse.quote(token)}"


def _geo_url(latitude: float, longitude: float, token: str) -> str:
    return f"{WAQI_BASE_URL}/geo:{latitude};{longitude}/?token={urllib.parse.quote(token)}"


async def fetch_waqi_environment(city: Optional[str] = None, latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict[str, Any]:
    """Fetch live WAQI observations normalized to the OpenWeather environment shape."""
    token = _token()
    errors = []

    if city:
        try:
            url = _city_url(city, token)
            payload = await _cached_json(f"waqi:city:{city.lower()}", url)
            return _normalize(payload, source_query=city)
        except Exception as exc:
            errors.append(f"city lookup failed: {exc}")

    if latitude is not None and longitude is not None:
        try:
            url = _geo_url(latitude, longitude, token)
            payload = await _cached_json(f"waqi:geo:{latitude:.4f}:{longitude:.4f}", url)
            return _normalize(payload, source_query=f"geo:{latitude},{longitude}")
        except Exception as exc:
            errors.append(f"geo lookup failed: {exc}")

    raise RuntimeError("; ".join(errors) or "No WAQI city or coordinates were provided.")
