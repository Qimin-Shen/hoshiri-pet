"""Explicitly opted-in local time and coarse, city-based weather context."""
from __future__ import annotations

from datetime import datetime
import threading
import time

import httpx

WEATHER_TTL = 30 * 60
WEATHER_TIMEOUT = httpx.Timeout(connect=4.0, read=5.0, write=4.0, pool=4.0)
WEATHER_CODES = {
    0: "晴", 1: "大致晴朗", 2: "局部多云", 3: "阴", 45: "有雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪", 80: "阵雨", 81: "阵雨", 82: "强阵雨",
    95: "雷暴", 96: "雷暴冰雹", 99: "强雷暴冰雹",
}
_lock = threading.Lock()
_weather_cache: dict[str, tuple[float, str]] = {}


def local_time_context(now: datetime | None = None) -> str:
    """Return coarse local time and timezone only; never read location."""
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.astimezone()
    return f"设备本地时间：{current:%Y-%m-%d %H:%M}（{current.tzname() or 'local timezone'}）"


def weather_context(city: str, *, now: float | None = None) -> str:
    """Fetch a city-level forecast from Open-Meteo, or return empty on failure."""
    city = city.strip()[:100]
    if not city:
        return ""
    stamp = time.monotonic() if now is None else now
    with _lock:
        cached = _weather_cache.get(city.casefold())
        if cached and stamp - cached[0] < WEATHER_TTL:
            return cached[1]
    try:
        # Only the manually configured city is sent to the geocoder; no device location is accessed.
        with httpx.Client(timeout=WEATHER_TIMEOUT, follow_redirects=False) as client:
            geo = client.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1, "language": "zh", "format": "json"})
            geo.raise_for_status()
            results = geo.json().get("results") or []
            if not results:
                return ""
            place = results[0]
            lat, lon = float(place["latitude"]), float(place["longitude"])
            label = ", ".join(str(x) for x in (place.get("name"), place.get("admin1"), place.get("country")) if x)
            response = client.get("https://api.open-meteo.com/v1/forecast", params={"latitude": lat, "longitude": lon, "current": "temperature_2m,apparent_temperature,weather_code", "timezone": "auto", "forecast_days": 1})
            response.raise_for_status()
            current = response.json().get("current") or {}
            temp = current.get("temperature_2m")
            if temp is None:
                return ""
            condition = WEATHER_CODES.get(int(current.get("weather_code", -1)), "天气情况未知")
            text = f"用户设置的城市当前天气（Open-Meteo，{label}）：{condition}，气温 {temp}°C"
            apparent = current.get("apparent_temperature")
            if apparent is not None:
                text += f"，体感 {apparent}°C"
            text += "。天气可能有延迟，仅供闲聊参考。"
            with _lock:
                _weather_cache[city.casefold()] = (stamp, text)
            return text
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return ""  # Optional context must never block normal chat.


def build_context(*, use_local_time: bool, use_weather: bool, city: str, now: datetime | None = None) -> str:
    parts = []
    if use_local_time:
        parts.append(local_time_context(now))
    if use_weather:
        weather = weather_context(city)
        if weather:
            parts.append(weather)
    return "\n".join(parts)
