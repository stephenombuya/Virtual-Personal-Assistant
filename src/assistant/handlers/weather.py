"""
Weather command handler.

Handles commands like:
  - "weather in London"
  - "what's the weather in New York?"
  - "temperature in Paris"
"""

from __future__ import annotations

import re
import time
from typing import Dict, List, Optional, Tuple

import httpx

from assistant.config.settings import AppSettings
from assistant.handlers.base import BaseHandler, HandlerResponse
from assistant.utils.logger import get_logger

logger = get_logger(__name__)

_WIND_DIRECTIONS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _degrees_to_cardinal(degrees: float) -> str:
    idx = round(degrees / 22.5) % 16
    return _WIND_DIRECTIONS[idx]


class WeatherCache:
    """Simple in-process TTL cache for weather responses."""

    def __init__(self, ttl: int) -> None:
        self._ttl = ttl
        self._store: Dict[str, Tuple[float, dict]] = {}

    def get(self, key: str) -> Optional[dict]:
        entry = self._store.get(key.lower())
        if entry and (time.monotonic() - entry[0]) < self._ttl:
            return entry[1]
        return None

    def set(self, key: str, data: dict) -> None:
        self._store[key.lower()] = (time.monotonic(), data)


class WeatherHandler(BaseHandler):
    """Fetches and narrates current weather conditions."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings.weather
        self._cache = WeatherCache(ttl=settings.weather.cache_ttl_seconds)
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def patterns(self) -> List[str]:
        return [
            r"\b(weather|temperature|forecast|conditions?)\b.*(in|for|at)\b",
            r"\bwhat.*(weather|temperature).*(in|like)\b",
            r"\bhow.*(hot|cold|warm).*(in|outside)\b",
        ]

    async def handle(self, command: str) -> HandlerResponse:
        city = self._extract_city(command)
        if not city:
            if self._settings.default_city:
                city = self._settings.default_city
            else:
                return HandlerResponse.error(
                    "I couldn't determine which city you want weather for. "
                    "Please say something like 'weather in London'."
                )

        cached = self._cache.get(city)
        if cached:
            logger.debug("Weather cache hit for %s", city)
            return self._format_response(city, cached)

        try:
            data = await self._fetch_weather(city)
        except httpx.TimeoutException:
            logger.warning("Weather API timeout for city=%s", city)
            return HandlerResponse.error(
                f"The weather service timed out. Please try again shortly."
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return HandlerResponse.error(
                    f"I couldn't find weather data for '{city}'. "
                    "Please check the city name and try again."
                )
            logger.error("Weather API HTTP error: %s", exc)
            return HandlerResponse.error("The weather service returned an error.")
        except Exception as exc:
            logger.exception("Unexpected error fetching weather for %s", city)
            return HandlerResponse.error("An unexpected error occurred fetching weather.")

        self._cache.set(city, data)
        return self._format_response(city, data)

    async def _fetch_weather(self, city: str) -> dict:
        url = f"{self._settings.base_url}/weather"
        response = await self._client.get(
            url,
            params={
                "q": city,
                "appid": self._settings.api_key,
                "units": self._settings.default_units,
            },
        )
        response.raise_for_status()
        return response.json()

    def _extract_city(self, command: str) -> Optional[str]:
        """Extract the city name from the command string."""
        patterns = [
            r"(?:weather|temperature|forecast|conditions?)\s+(?:in|for|at)\s+(.+?)(?:\?|$)",
            r"(?:in|for|at)\s+([A-Za-z ]+?)(?:\?|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                city = match.group(1).strip().rstrip("?.,!")
                if city:
                    return city
        return None

    def _format_response(self, city: str, data: dict) -> HandlerResponse:
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"]
        wind_speed = data["wind"]["speed"]
        wind_deg = data["wind"].get("deg", 0)
        wind_dir = _degrees_to_cardinal(wind_deg)
        unit_label = "Celsius" if self._settings.default_units == "metric" else "Fahrenheit"
        unit_symbol = "°C" if self._settings.default_units == "metric" else "°F"

        text = (
            f"The current weather in {city.title()} is {description}. "
            f"Temperature is {temp:.1f}{unit_symbol}, "
            f"feels like {feels_like:.1f}{unit_symbol}. "
            f"Humidity is {humidity}%, "
            f"with {wind_dir} winds at {wind_speed:.1f} metres per second."
        )

        return HandlerResponse(
            text=text,
            data={
                "city": city,
                "temperature": temp,
                "feels_like": feels_like,
                "humidity": humidity,
                "description": description,
                "wind_speed": wind_speed,
                "wind_direction": wind_dir,
                "unit": unit_label,
            },
        )

    async def close(self) -> None:
        await self._client.aclose()
