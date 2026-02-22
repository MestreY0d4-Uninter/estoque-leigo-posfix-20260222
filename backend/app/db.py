from __future__ import annotations

import os
from collections.abc import Generator
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class Settings:
    sqlite_path: str


def get_settings() -> Settings:
    return Settings(sqlite_path=os.environ.get("SQLITE_PATH", "/data/app.db"))


def make_engine(settings: Settings) -> Engine:
    # SQLite needs check_same_thread=False for FastAPI threadpool.
    url = f"sqlite+pysqlite:///{settings.sqlite_path}"
    return create_engine(url, connect_args={"check_same_thread": False})


def make_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
