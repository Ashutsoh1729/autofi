from pathlib import Path

from sqlmodel import Session

from data.db import get_session, init_db
from data.models import AppConfig


def get_setting(db_path: Path, key: str) -> str | None:
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        row = session.get(AppConfig, key)
        if row is not None:
            return row.value
    return None


def set_setting(db_path: Path, key: str, value: str) -> None:
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        existing = session.get(AppConfig, key)
        if existing is not None:
            existing.value = value
            session.add(existing)
        else:
            session.add(AppConfig(key=key, value=value))
        session.commit()


def delete_setting(db_path: Path, key: str) -> None:
    init_db(db_path)
    session: Session
    for session in get_session(db_path):
        row = session.get(AppConfig, key)
        if row is not None:
            session.delete(row)
            session.commit()
