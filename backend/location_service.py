"""Location lookup helpers backed by OpenWeather geocoding."""
import asyncio
import json
import urllib.parse
import urllib.request
from typing import Dict, Optional


def _read_json(url: str) -> Dict:
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


async def geocode_location(api_key: str, country: str, city: str, state: Optional[str] = None) -> Dict:
    query = ",".join(part for part in [city, state, country] if part)
    url = (
        "https://api.openweathermap.org/geo/1.0/direct?"
        f"q={urllib.parse.quote(query)}&limit=1&appid={api_key}"
    )
    data = await asyncio.to_thread(_read_json, url)
    if not data:
        raise ValueError("Location not found. Check country, state, and city.")
    place = data[0]
    return {
        "name": ", ".join(part for part in [place.get("name"), place.get("state"), place.get("country")] if part),
        "country": place.get("country"),
        "state": place.get("state"),
        "city": place.get("name"),
        "latitude": float(place["lat"]),
        "longitude": float(place["lon"]),
    }


async def reverse_geocode(api_key: str, latitude: float, longitude: float) -> Dict:
    url = (
        "https://api.openweathermap.org/geo/1.0/reverse?"
        f"lat={latitude}&lon={longitude}&limit=1&appid={api_key}"
    )
    data = await asyncio.to_thread(_read_json, url)
    place = data[0] if data else {}
    return {
        "name": ", ".join(part for part in [place.get("name"), place.get("state"), place.get("country")] if part) or f"{latitude:.4f}, {longitude:.4f}",
        "country": place.get("country"),
        "state": place.get("state"),
        "city": place.get("name"),
        "latitude": float(latitude),
        "longitude": float(longitude),
    }
