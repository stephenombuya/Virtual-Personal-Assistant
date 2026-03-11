"""
Shared pytest fixtures for the virtual assistant test suite.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from assistant.config.settings import AppSettings, DatabaseSettings, NewsSettings, SpeechSettings, WeatherSettings
from assistant.database.repository import DatabaseManager, ReminderRepository, CommandLogRepository


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def app_settings(tmp_db_path: Path) -> AppSettings:
    """Return an AppSettings instance wired for testing (in-memory-ish DB)."""
    settings = AppSettings.model_construct(
        app_name="TestAssistant",
        debug=True,
        log_level="DEBUG",
        log_file=None,
        speech=SpeechSettings.model_construct(
            rate=175,
            volume=0.9,
            energy_threshold=300,
            pause_threshold=0.8,
            recognition_timeout=10,
            phrase_time_limit=15,
        ),
        weather=WeatherSettings.model_construct(
            api_key="test_weather_key",
            base_url="https://api.openweathermap.org/data/2.5",
            default_units="metric",
            cache_ttl_seconds=600,
        ),
        news=NewsSettings.model_construct(
            api_key="test_news_key",
            base_url="https://newsapi.org/v2",
            country="us",
            page_size=5,
            cache_ttl_seconds=300,
        ),
        database=DatabaseSettings.model_construct(
            path=tmp_db_path,
            echo=False,
        ),
    )
    return settings


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


@pytest.fixture
def db_manager(app_settings: AppSettings) -> Generator[DatabaseManager, None, None]:
    manager = DatabaseManager(app_settings)
    yield manager
    manager.dispose()


@pytest.fixture
def reminder_repo(db_manager: DatabaseManager) -> ReminderRepository:
    return ReminderRepository(db_manager)


@pytest.fixture
def log_repo(db_manager: DatabaseManager) -> CommandLogRepository:
    return CommandLogRepository(db_manager)
