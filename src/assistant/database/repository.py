"""
Database engine, session factory, and repository classes.
"""

from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Generator, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from assistant.config.settings import AppSettings
from assistant.database.models import Base, CommandLog, Reminder
from assistant.utils.logger import get_logger

logger = get_logger(__name__)


def build_engine(settings: AppSettings):
    """Create and return a SQLAlchemy engine."""
    url = f"sqlite:///{settings.database.path}"
    engine = create_engine(
        url,
        echo=settings.database.echo,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    Base.metadata.create_all(engine)
    logger.info("Database engine initialised at %s", settings.database.path)
    return engine


class DatabaseManager:
    """Manages the engine and provides a context-managed session factory."""

    def __init__(self, settings: AppSettings) -> None:
        self._engine = build_engine(settings)
        self._session_factory = sessionmaker(
            bind=self._engine, autoflush=False, autocommit=False
        )

    @contextlib.contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a transactional session, rolling back on error."""
        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        """Release all database connections."""
        self._engine.dispose()
        logger.info("Database connections disposed")


# ---------------------------------------------------------------------------
# Repository classes
# ---------------------------------------------------------------------------


class ReminderRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def create(self, message: str, remind_at: datetime) -> Reminder:
        reminder = Reminder(message=message, remind_at=remind_at)
        with self._db.session() as session:
            session.add(reminder)
            session.flush()
            session.refresh(reminder)
            # Detach from session so it can be used outside
            session.expunge(reminder)
        logger.debug("Created reminder id=%s at %s", reminder.id, remind_at)
        return reminder

    def get_pending(self, as_of: Optional[datetime] = None) -> List[Reminder]:
        cutoff = as_of or datetime.now()
        with self._db.session() as session:
            stmt = (
                select(Reminder)
                .where(Reminder.remind_at <= cutoff)
                .where(Reminder.is_completed.is_(False))
                .order_by(Reminder.remind_at)
            )
            results = list(session.scalars(stmt))
            for r in results:
                session.expunge(r)
        return results

    def mark_completed(self, reminder_id: int) -> None:
        with self._db.session() as session:
            reminder = session.get(Reminder, reminder_id)
            if reminder:
                reminder.is_completed = True
        logger.debug("Reminder id=%s marked completed", reminder_id)

    def list_upcoming(self, limit: int = 10) -> List[Reminder]:
        now = datetime.now()
        with self._db.session() as session:
            stmt = (
                select(Reminder)
                .where(Reminder.remind_at > now)
                .where(Reminder.is_completed.is_(False))
                .order_by(Reminder.remind_at)
                .limit(limit)
            )
            results = list(session.scalars(stmt))
            for r in results:
                session.expunge(r)
        return results


class CommandLogRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def record(
        self,
        raw_input: str,
        handler: str,
        success: bool,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        entry = CommandLog(
            raw_input=raw_input,
            handler=handler,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        with self._db.session() as session:
            session.add(entry)
