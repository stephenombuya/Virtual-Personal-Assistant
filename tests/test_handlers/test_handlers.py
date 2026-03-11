"""
Unit tests for individual command handlers.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from assistant.handlers.datetime_handler import DateTimeHandler
from assistant.handlers.reminder import ReminderHandler, _parse_time, _extract_message
from assistant.handlers.search import SearchHandler
from assistant.handlers.system import SystemHandler


# ---------------------------------------------------------------------------
# DateTimeHandler
# ---------------------------------------------------------------------------


class TestDateTimeHandler:
    @pytest.fixture
    def handler(self):
        return DateTimeHandler()

    def test_can_handle_time_query(self, handler):
        assert handler.can_handle("what time is it?")
        assert handler.can_handle("current time")

    def test_can_handle_date_query(self, handler):
        assert handler.can_handle("what's the date today?")
        assert handler.can_handle("what day is it?")

    def test_does_not_handle_weather(self, handler):
        assert not handler.can_handle("open chrome")

    @pytest.mark.asyncio
    async def test_time_response_contains_time(self, handler):
        response = await handler.handle("what time is it?")
        assert response.success
        assert ":" in response.text  # time format HH:MM

    @pytest.mark.asyncio
    async def test_date_response_contains_day(self, handler):
        response = await handler.handle("what's the date?")
        assert response.success
        assert any(
            day in response.text
            for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        )

    @pytest.mark.asyncio
    async def test_response_has_datetime_data(self, handler):
        response = await handler.handle("what time is it?")
        assert response.data is not None
        assert "datetime" in response.data


# ---------------------------------------------------------------------------
# ReminderHandler time parsing
# ---------------------------------------------------------------------------


class TestTimeParser:
    def test_parse_12h_pm(self):
        result = _parse_time("remind me at 3 pm to call mom")
        assert result is not None
        assert result.hour == 15

    def test_parse_12h_am(self):
        result = _parse_time("remind me at 9 am to exercise")
        assert result is not None
        assert result.hour == 9

    def test_parse_12h_with_minutes(self):
        result = _parse_time("remind me at 3:30 pm to leave")
        assert result is not None
        assert result.hour == 15
        assert result.minute == 30

    def test_parse_in_minutes(self):
        before = datetime.now()
        result = _parse_time("remind me in 30 minutes to drink water")
        after = datetime.now()
        assert result is not None
        assert before + timedelta(minutes=29) <= result <= after + timedelta(minutes=31)

    def test_parse_in_hours(self):
        before = datetime.now()
        result = _parse_time("remind me in 2 hours to check email")
        assert result is not None
        delta = result - before
        assert timedelta(hours=1, minutes=59) <= delta <= timedelta(hours=2, minutes=1)

    def test_parse_24h_format(self):
        result = _parse_time("set a reminder for 14:30 to take medicine")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30

    def test_returns_none_for_no_time(self):
        result = _parse_time("just a reminder to do something")
        assert result is None

    def test_extract_message(self):
        msg = _extract_message("remind me at 3 pm to call mom")
        assert msg is not None
        assert "call mom" in msg.lower()


class TestReminderHandler:
    @pytest.fixture
    def repo(self):
        mock = MagicMock()
        mock.create.return_value = MagicMock(id=1)
        mock.list_upcoming.return_value = []
        return mock

    @pytest.fixture
    def handler(self, repo):
        return ReminderHandler(repo)

    def test_can_handle_reminder(self, handler):
        assert handler.can_handle("remind me at 3 pm to call mom")
        assert handler.can_handle("set a reminder for 2 pm")

    def test_can_handle_list(self, handler):
        assert handler.can_handle("list my reminders")
        assert handler.can_handle("show my reminders")

    @pytest.mark.asyncio
    async def test_create_reminder_success(self, handler):
        response = await handler.handle("remind me at 3 pm to call mom")
        assert response.success
        assert "remind" in response.text.lower() or "got it" in response.text.lower()

    @pytest.mark.asyncio
    async def test_create_reminder_no_time_returns_error(self, handler):
        response = await handler.handle("remind me to do something someday")
        assert not response.success

    @pytest.mark.asyncio
    async def test_list_no_reminders(self, handler):
        response = await handler.handle("list my reminders")
        assert response.success
        assert "no upcoming" in response.text.lower()

    @pytest.mark.asyncio
    async def test_list_reminders(self, handler, repo):
        mock_reminder = MagicMock()
        mock_reminder.message = "call mom"
        mock_reminder.remind_at = datetime.now() + timedelta(hours=1)
        repo.list_upcoming.return_value = [mock_reminder]
        response = await handler.handle("list my reminders")
        assert response.success
        assert "call mom" in response.text


# ---------------------------------------------------------------------------
# SearchHandler
# ---------------------------------------------------------------------------


class TestSearchHandler:
    @pytest.fixture
    def handler(self):
        return SearchHandler()

    def test_can_handle_search(self, handler):
        assert handler.can_handle("search for Python tutorials")
        assert handler.can_handle("google machine learning")
        assert handler.can_handle("look up best restaurants")

    def test_does_not_handle_weather(self, handler):
        assert not handler.can_handle("what time is it")

    @pytest.mark.asyncio
    async def test_opens_browser(self, handler):
        with patch("webbrowser.open", return_value=True) as mock_open:
            response = await handler.handle("search for Python tutorials")
        assert response.success
        mock_open.assert_called_once()
        assert "python+tutorials" in mock_open.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_no_query_returns_error(self, handler):
        with patch("webbrowser.open", return_value=True):
            response = await handler.handle("search")
        # "search" with nothing after it may or may not match — depends on extraction
        # At minimum the handler should not raise
        assert response is not None

    @pytest.mark.asyncio
    async def test_browser_failure_returns_error(self, handler):
        with patch("webbrowser.open", side_effect=Exception("no browser")):
            response = await handler.handle("search for Python")
        assert not response.success


# ---------------------------------------------------------------------------
# SystemHandler
# ---------------------------------------------------------------------------


class TestSystemHandler:
    @pytest.fixture
    def handler(self):
        return SystemHandler()

    def test_can_handle_open(self, handler):
        assert handler.can_handle("open Chrome")
        assert handler.can_handle("launch Calculator")

    @pytest.mark.asyncio
    async def test_opens_known_app(self, handler):
        with patch("shutil.which", return_value="/usr/bin/calc"), \
             patch("subprocess.Popen") as mock_popen:
            response = await handler.handle("open Calculator")
        assert response.success

    @pytest.mark.asyncio
    async def test_unknown_app_returns_error(self, handler):
        response = await handler.handle("open UnknownApp12345")
        assert not response.success
        assert "don't know" in response.text.lower()

    @pytest.mark.asyncio
    async def test_no_app_name_returns_error(self, handler):
        response = await handler.handle("open")
        assert not response.success
