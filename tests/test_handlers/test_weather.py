"""
Tests for WeatherHandler using httpx mock transport.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from assistant.handlers.weather import WeatherHandler


SAMPLE_WEATHER = {
    "main": {
        "temp": 22.5,
        "feels_like": 21.0,
        "humidity": 60,
    },
    "weather": [{"description": "clear sky", "icon": "01d"}],
    "wind": {"speed": 3.5, "deg": 180},
    "name": "London",
}


@pytest.fixture
def mock_response():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = SAMPLE_WEATHER
    return resp


@pytest.fixture
def handler(app_settings):
    return WeatherHandler(app_settings)


class TestWeatherHandler:
    def test_patterns_match_weather_queries(self, handler):
        assert handler.can_handle("weather in London")
        assert handler.can_handle("what's the weather like in Paris?")
        assert handler.can_handle("temperature in New York")

    def test_patterns_do_not_match_unrelated(self, handler):
        assert not handler.can_handle("what time is it?")
        assert not handler.can_handle("open chrome")

    @pytest.mark.asyncio
    async def test_successful_weather_fetch(self, handler, mock_response):
        with patch.object(handler._client, "get", new_callable=AsyncMock, return_value=mock_response):
            response = await handler.handle("weather in London")

        assert response.success
        assert "22.5" in response.text
        assert "London" in response.text.lower() or "london" in response.text.lower()
        assert response.data is not None
        assert response.data["temperature"] == 22.5
        assert response.data["humidity"] == 60

    @pytest.mark.asyncio
    async def test_city_extracted_correctly(self, handler, mock_response):
        with patch.object(handler._client, "get", new_callable=AsyncMock, return_value=mock_response):
            response = await handler.handle("what's the weather in New York?")

        assert response.success

    @pytest.mark.asyncio
    async def test_cache_hit_does_not_call_api(self, handler, mock_response):
        with patch.object(handler._client, "get", new_callable=AsyncMock, return_value=mock_response) as mock_get:
            await handler.handle("weather in London")
            await handler.handle("weather in London")

        # Second call should hit cache
        assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_city_not_found_returns_error(self, handler):
        error_resp = MagicMock(spec=httpx.Response)
        error_resp.status_code = 404
        error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=error_resp
        )

        with patch.object(handler._client, "get", new_callable=AsyncMock, return_value=error_resp):
            response = await handler.handle("weather in FakeCity12345")

        assert not response.success
        assert "fakecity" in response.text.lower() or "couldn't find" in response.text.lower()

    @pytest.mark.asyncio
    async def test_timeout_returns_graceful_error(self, handler):
        with patch.object(handler._client, "get", new_callable=AsyncMock,
                          side_effect=httpx.TimeoutException("timeout")):
            response = await handler.handle("weather in London")

        assert not response.success
        assert "timed out" in response.text.lower()

    @pytest.mark.asyncio
    async def test_no_city_without_default_returns_error(self, handler):
        handler._settings.default_city = None
        response = await handler.handle("what is the weather?")
        # No city extractable AND no default
        assert not response.success

    @pytest.mark.asyncio
    async def test_uses_default_city_when_no_city_in_command(self, handler, mock_response):
        handler._settings.default_city = "Nairobi"
        with patch.object(handler._client, "get", new_callable=AsyncMock, return_value=mock_response):
            response = await handler.handle("what is the temperature?")
        assert response.success
