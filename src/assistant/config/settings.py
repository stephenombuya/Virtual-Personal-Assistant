"""
Application configuration using Pydantic BaseSettings.
All settings are loaded from environment variables or .env file.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[4]


class VoiceGender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SpeechSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPEECH_", extra="ignore")

    rate: int = Field(default=175, ge=50, le=400, description="Words per minute")
    volume: float = Field(default=0.9, ge=0.0, le=1.0, description="TTS volume level")
    voice_gender: VoiceGender = Field(default=VoiceGender.FEMALE)
    energy_threshold: int = Field(default=300, ge=100, le=4000)
    pause_threshold: float = Field(default=0.8, ge=0.3, le=3.0)
    recognition_timeout: int = Field(default=10, ge=3, le=60)
    phrase_time_limit: int = Field(default=15, ge=5, le=120)


class WeatherSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WEATHER_", extra="ignore")

    api_key: str = Field(description="OpenWeatherMap API key")
    base_url: AnyHttpUrl = Field(
        default="https://api.openweathermap.org/data/2.5",
    )
    default_units: str = Field(default="metric", pattern="^(metric|imperial|standard)$")
    default_city: Optional[str] = Field(default=None)
    cache_ttl_seconds: int = Field(default=600, ge=60)


class NewsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEWS_", extra="ignore")

    api_key: str = Field(description="NewsAPI key")
    base_url: AnyHttpUrl = Field(default="https://newsapi.org/v2")
    country: str = Field(default="us", min_length=2, max_length=2)
    page_size: int = Field(default=5, ge=1, le=20)
    cache_ttl_seconds: int = Field(default=300, ge=60)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    path: Path = Field(default=BASE_DIR / "data" / "assistant.db")
    pool_size: int = Field(default=5, ge=1, le=20)
    echo: bool = Field(default=False)

    @field_validator("path", mode="before")
    @classmethod
    def ensure_parent_exists(cls, v: Path) -> Path:
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App identity
    app_name: str = Field(default="VoiceAssistant")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_file: Optional[Path] = Field(default=BASE_DIR / "logs" / "assistant.log")

    # Wake word / greeting
    wake_word: str = Field(default="hey assistant")
    assistant_name: str = Field(default="Assistant")

    # Sub-settings are loaded separately to keep env prefix clean
    speech: SpeechSettings = Field(default_factory=SpeechSettings)
    weather: WeatherSettings = Field(default_factory=lambda: WeatherSettings())  # type: ignore[call-arg]
    news: NewsSettings = Field(default_factory=lambda: NewsSettings())  # type: ignore[call-arg]
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    @field_validator("log_file", mode="before")
    @classmethod
    def ensure_log_dir(cls, v: Optional[Path]) -> Optional[Path]:
        if v:
            path = Path(v)
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        return v


def get_settings() -> AppSettings:
    """Return a cached settings instance."""
    return _settings


_settings = AppSettings()
