"""
Integration tests for ReminderRepository and CommandLogRepository.
Uses a real SQLite in-memory-like database via the tmp_path fixture.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from assistant.database.repository import DatabaseManager, ReminderRepository, CommandLogRepository


class TestReminderRepository:
    def test_create_and_retrieve(self, reminder_repo):
        future = datetime.now() + timedelta(hours=1)
        reminder = reminder_repo.create(message="call mom", remind_at=future)
        assert reminder.id is not None
        assert reminder.message == "call mom"
        assert reminder.is_completed is False

    def test_get_pending_returns_due_reminders(self, reminder_repo):
        past = datetime.now() - timedelta(minutes=1)
        reminder_repo.create(message="overdue task", remind_at=past)
        pending = reminder_repo.get_pending()
        assert len(pending) >= 1
        assert any(r.message == "overdue task" for r in pending)

    def test_get_pending_excludes_future_reminders(self, reminder_repo):
        future = datetime.now() + timedelta(hours=2)
        reminder_repo.create(message="future task", remind_at=future)
        pending = reminder_repo.get_pending()
        assert not any(r.message == "future task" for r in pending)

    def test_get_pending_excludes_completed(self, reminder_repo):
        past = datetime.now() - timedelta(minutes=1)
        reminder = reminder_repo.create(message="done task", remind_at=past)
        reminder_repo.mark_completed(reminder.id)
        pending = reminder_repo.get_pending()
        assert not any(r.message == "done task" for r in pending)

    def test_mark_completed(self, reminder_repo):
        future = datetime.now() + timedelta(hours=1)
        reminder = reminder_repo.create(message="test", remind_at=future)
        reminder_repo.mark_completed(reminder.id)
        # Should no longer appear in upcoming
        upcoming = reminder_repo.list_upcoming()
        assert not any(r.id == reminder.id for r in upcoming)

    def test_list_upcoming_respects_limit(self, reminder_repo):
        future_base = datetime.now() + timedelta(hours=1)
        for i in range(10):
            reminder_repo.create(
                message=f"task {i}", remind_at=future_base + timedelta(minutes=i)
            )
        upcoming = reminder_repo.list_upcoming(limit=5)
        assert len(upcoming) <= 5

    def test_list_upcoming_ordered_by_time(self, reminder_repo):
        now = datetime.now()
        reminder_repo.create("third", now + timedelta(hours=3))
        reminder_repo.create("first", now + timedelta(hours=1))
        reminder_repo.create("second", now + timedelta(hours=2))
        upcoming = reminder_repo.list_upcoming(limit=3)
        times = [r.remind_at for r in upcoming[-3:]]
        assert times == sorted(times)


class TestCommandLogRepository:
    def test_record_success(self, log_repo):
        # Should not raise
        log_repo.record(
            raw_input="what time is it?",
            handler="DateTimeHandler",
            success=True,
            duration_ms=12,
        )

    def test_record_failure(self, log_repo):
        log_repo.record(
            raw_input="gibberish command",
            handler="FallbackHandler",
            success=False,
            error_message="No handler matched",
            duration_ms=2,
        )
