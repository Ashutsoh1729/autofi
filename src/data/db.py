from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine


def get_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}")


def init_db(db_path: Path):
    engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)
    return engine


def get_session(db_path: Path) -> Generator[Session, None, None]:
    engine = get_engine(db_path)
    with Session(engine) as session:
        yield session
