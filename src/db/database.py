"""
Database configuration and session management for EcoTwin.

Supports pluggable persistence:
- Defaults to SQLite ('sqlite:///./ecotwin.db') for zero-friction local development and testing.
- Configurable to PostgreSQL via DATABASE_URL environment variable.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# 1. Resolve Database URL
# Default to SQLite local file in project root if DATABASE_URL is not set
DEFAULT_SQLITE_URL = "sqlite:///./ecotwin.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

# 2. Configure Engine
# SQLite requires 'check_same_thread': False for multithreaded FastAPI access
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

# 3. Session Maker & Declarative Base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy database session and ensures
    it is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_override=None) -> None:
    """
    Creates all database tables defined in SQLAlchemy models.
    Idempotent operation (safe to run on startup).
    """
    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)


def drop_db(engine_override=None) -> None:
    """
    Drops all database tables. Primarily used in isolated test setups.
    """
    target_engine = engine_override or engine
    Base.metadata.drop_all(bind=target_engine)
