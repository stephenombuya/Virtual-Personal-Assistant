# 🎙️ Virtual Personal Assistant

[![CI](https://github.com/stephenombuya/Virtual-Personal-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/stephenombuya/Virtual-Personal-Assistant/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

Production-grade Python virtual assistant with full asynchronous support. Speak naturally to: get weather forecasts, read news headlines, check time and date, set reminders, launch apps, and browse the web — completely hands-free.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Voice Commands](#voice-commands)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Docker](#docker)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

| Category | Details |
|---|---|
| **Speech I/O** | Microphone capture via SpeechRecognition; natural TTS via pyttsx3 on a dedicated background thread |
| **Weather** | Real-time conditions from OpenWeatherMap — temperature, humidity, wind direction, "feels like" |
| **News** | Top headlines from NewsAPI, read aloud and cached to reduce API calls |
| **Date & Time** | Accurate local time and date, spoken naturally |
| **Reminders** | Create reminders by voice (12h, 24h, or relative — "in 30 minutes"); background scheduler fires them on time |
| **App Launcher** | Cross-platform (Linux / macOS / Windows) launch of Chrome, Firefox, Calculator, Terminal, VS Code, and more |
| **Web Search** | Opens Google search results in your default browser by voice |
| **Audit Logging** | Every command and its outcome is persisted to SQLite for observability |
| **Caching** | In-process TTL caches for weather and news to stay within free-tier API limits |
| **Configuration** | All settings via environment variables with strict Pydantic validation; no hard-coded values |
| **Async Core** | Full `asyncio` event loop — blocking I/O (mic capture, TTS) runs in thread pools |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                        main.py                           │
│                   (asyncio entry point)                  │
└────────────────────────┬─────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   VoiceAssistant    │  ← orchestrator
              │  core/assistant.py  │
              └──┬──────────────┬───┘
                 │              │
      ┌──────────▼──┐    ┌──────▼────────────┐
      │ SpeechEngine│    │  CommandRouter     │
      │ (mic + TTS) │    │  core/router.py    │
      └─────────────┘    └──────┬────────────┘
                                │ routes to
              ┌─────────────────▼──────────────────┐
              │            Handlers                 │
              │  DateTimeHandler  WeatherHandler    │
              │  NewsHandler      ReminderHandler   │
              │  SystemHandler    SearchHandler     │
              └──────────────────┬─────────────────┘
                                 │
              ┌──────────────────▼─────────────────┐
              │          DatabaseManager            │
              │   SQLite via SQLAlchemy 2.0 ORM    │
              │  (Reminder + CommandLog tables)    │
              └─────────────────────────────────────┘
```

Each handler is independently testable, implements a common `BaseHandler` contract, and is registered with the router in priority order. Adding new capabilities requires only creating a new handler — no changes to core infrastructure.

---

## Prerequisites

- Python **3.10** or higher
- A working **microphone**
- An active **internet connection**
- Free API keys for:
  - [OpenWeatherMap](https://openweathermap.org/api) (weather)
  - [NewsAPI](https://newsapi.org) (headlines)
- System audio libraries:
  - **Linux/Debian**: `sudo apt install portaudio19-dev python3-pyaudio`
  - **macOS**: `brew install portaudio`
  - **Windows**: PyAudio wheels are included in the pip package

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/stephenombuya/Virtual-Personal-Assistant.git
cd Virtual-Personal-Assistant
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows PowerShell
```

### 3. Install dependencies

```bash
# Runtime only
pip install -r requirements.txt

# Or with dev/test tools (recommended for contributors)
pip install -r requirements-dev.txt
```

> **Alternative:** Use `make install-dev` if you have GNU Make available.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set your API keys:

```env
WEATHER_API_KEY=your_openweathermap_key
NEWS_API_KEY=your_newsapi_key
```

See [Configuration](#configuration) for the full reference.

---

## Configuration

All configuration is driven by environment variables (or a `.env` file). Settings are validated at startup using Pydantic — the assistant will fail fast with a clear error if required values are missing or invalid.

### Full Reference

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `VoiceAssistant` | Display name used in greetings and logs |
| `APP_VERSION` | `1.0.0` | Semantic version string |
| `DEBUG` | `false` | Enable verbose debug logging |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | `logs/assistant.log` | Log file path (comment out for stdout only) |
| `ASSISTANT_NAME` | `Assistant` | Name the assistant introduces itself as |
| `WEATHER_API_KEY` | **required** | OpenWeatherMap API key |
| `WEATHER_DEFAULT_UNITS` | `metric` | `metric` / `imperial` / `standard` |
| `WEATHER_DEFAULT_CITY` | _(none)_ | Fallback city when none is spoken |
| `NEWS_API_KEY` | **required** | NewsAPI key |
| `NEWS_COUNTRY` | `us` | ISO 3166-1 alpha-2 country for headlines |
| `NEWS_PAGE_SIZE` | `5` | Headlines to read aloud (1–20) |
| `SPEECH_RATE` | `175` | TTS words per minute (50–400) |
| `SPEECH_VOLUME` | `0.9` | TTS volume (0.0–1.0) |
| `SPEECH_VOICE_GENDER` | `female` | `female` / `male` |
| `SPEECH_ENERGY_THRESHOLD` | `300` | Microphone sensitivity (100–4000) |
| `SPEECH_PAUSE_THRESHOLD` | `0.8` | Silence duration to end phrase (seconds) |
| `SPEECH_RECOGNITION_TIMEOUT` | `10` | Max seconds to wait for speech |
| `SPEECH_PHRASE_TIME_LIMIT` | `15` | Max seconds per spoken phrase |
| `DB_PATH` | `data/assistant.db` | SQLite database path |
| `DB_ECHO` | `false` | Log SQL queries (debug mode) |

---

## Usage

### Start the assistant

```bash
# Using make
make run

# Or directly
PYTHONPATH=src python main.py
```

The assistant greets you and begins listening. Speak clearly at a normal pace.

### Stop the assistant

Say any of: **"goodbye"**, **"bye"**, **"exit"**, **"quit"**, or **"shut down"** — or press `Ctrl+C`.

---

## Voice Commands

### 🌤️ Weather

```
"weather in London"
"what's the weather like in Paris?"
"temperature in New York"
"how cold is it in Tokyo?"
```

### 📰 News

```
"tell me the news"
"what's happening today?"
"latest headlines"
"what's going on?"
```

### 🕐 Date & Time

```
"what time is it?"
"current time"
"what's the date?"
"what day is it today?"
```

### ⏰ Reminders

```
"remind me at 3 pm to call mom"
"set a reminder for 14:30 to take medicine"
"remind me in 30 minutes to drink water"
"remind me in 2 hours to check email"
"list my reminders"
"show my reminders"
```

### 🖥️ Open Applications

```
"open Chrome"
"launch Calculator"
"open Terminal"
"start VS Code"
"open File Manager"
"open Spotify"
```

### 🔍 Web Search

```
"search for Python tutorials"
"Google machine learning basics"
"look up best restaurants near me"
"find how to make pasta"
```

### 👋 Exit

```
"goodbye"
"bye"
"exit"
"quit"
"shut down"
```

---

## Project Structure

```
virtual-personal-assistant/
├── src/
│   └── assistant/
│       ├── config/
│       │   └── settings.py          # Pydantic-validated settings
│       ├── core/
│       │   ├── assistant.py         # Main orchestrator & lifecycle
│       │   ├── command_router.py    # Pattern-based command dispatcher
│       │   ├── scheduler.py         # Async reminder scheduler
│       │   └── speech.py            # Mic input + TTS output
│       ├── database/
│       │   ├── models.py            # SQLAlchemy ORM models
│       │   └── repository.py        # Repository classes (data layer)
│       ├── handlers/
│       │   ├── base.py              # Abstract BaseHandler contract
│       │   ├── datetime_handler.py
│       │   ├── news.py
│       │   ├── reminder.py
│       │   ├── search.py
│       │   ├── system.py
│       │   └── weather.py
│       └── utils/
│           └── logger.py            # Rotating file + console logging
├── tests/
│   ├── conftest.py                  # Shared pytest fixtures
│   ├── test_core/
│   │   ├── test_database.py
│   │   └── test_router.py
│   └── test_handlers/
│       ├── test_handlers.py
│       └── test_weather.py
├── .github/
│   └── workflows/
│       └── ci.yml                   # GitHub Actions CI pipeline
├── data/                            # SQLite database (git-ignored)
├── logs/                            # Rotating log files (git-ignored)
├── main.py                          # Entry point
├── Dockerfile                       # Multi-stage production Docker build
├── docker-compose.yml
├── Makefile                         # Developer workflow automation
├── pyproject.toml                   # Build config, pytest, ruff, mypy, bandit
├── requirements.txt
├── requirements-dev.txt
└── .env.example                     # Environment variable template
```

---

## Running Tests

```bash
# All tests
make test

# With coverage report (HTML at htmlcov/index.html)
make test-cov

# Skip slow/integration tests
make test-fast

# All quality checks (lint + types + security)
make check
```

The test suite uses **pytest-asyncio** for async handler tests and **pytest-mock** / `unittest.mock` for isolating HTTP calls and database operations. No live APIs or microphone are required to run tests.

---

## Docker

### Build the image

```bash
make docker-build
# or
docker build -t virtual-personal-assistant .
```

### Run with Docker Compose

```bash
# Ensure .env is configured
docker-compose up
```

> **Audio passthrough note:** The Docker Compose file forwards PulseAudio and `/dev/snd` from the host. This works on most Linux desktops. macOS and Windows users may need to use [Soundflower](https://github.com/mattingalls/Soundflower) or a virtual audio device.

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository and create a branch:
   ```bash
   git checkout -b feature/my-new-handler
   ```

2. Install dev dependencies:
   ```bash
   make install-dev
   ```

3. Write your code, following the existing patterns (new handler → subclass `BaseHandler`, add tests).

4. Ensure all checks pass:
   ```bash
   make check
   make test
   ```

5. Commit and push, then open a Pull Request against `main`.

### Adding a New Handler

1. Create `src/assistant/handlers/my_handler.py` subclassing `BaseHandler`
2. Implement `patterns` (list of regex strings) and `handle(command)` (returns `HandlerResponse`)
3. Register it in `src/assistant/core/assistant.py` inside `VoiceAssistant.__init__`
4. Add tests in `tests/test_handlers/`

---

## Troubleshooting

### Microphone not detected
- Run `python -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"` to list available devices.
- Ensure `portaudio19-dev` (Linux) or `portaudio` (macOS) is installed.
- Grant microphone permissions in your OS system settings.
- Increase `SPEECH_ENERGY_THRESHOLD` (e.g., to `500`) in a noisy environment.

### "Could not understand audio"
- Speak at a normal pace and volume.
- Reduce background noise.
- Lower `SPEECH_PAUSE_THRESHOLD` (e.g., to `0.6`) if the assistant cuts off before you finish speaking.

### API errors (weather/news)
- Verify your API keys in `.env`.
- Check your internet connection and confirm the API service status.
- Free-tier keys are usually sufficient; ensure you haven't exceeded rate limits.

### Import errors / ModuleNotFoundError
- Ensure your virtual environment is activated.
- Run with `PYTHONPATH=src python main.py` (or use `make run`).

### Application launcher does nothing
- Verify the application is installed: `which google-chrome` (Linux/macOS).
- Set `DEBUG=true` in `.env` to see the exact command being executed.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- [SpeechRecognition](https://github.com/Uberi/speech_recognition) — cross-platform speech input
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3) — offline text-to-speech
- [OpenWeatherMap API](https://openweathermap.org/api) — weather data
- [NewsAPI](https://newsapi.org) — news headlines
- [SQLAlchemy](https://www.sqlalchemy.org/) — database ORM
- [Pydantic](https://docs.pydantic.dev/) — settings validation
- [httpx](https://www.python-httpx.org/) — async HTTP client
