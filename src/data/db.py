from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from data.seed import seed_gl_accounts


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}")


def init_db(db_path: Path):
    engine = get_engine(db_path)
    SQLModel.metadata.create_all(engine)
    seed_gl_accounts(engine)
    return engine


def get_session(db_path: Path) -> Generator[Session, None, None]:
    engine = get_engine(db_path)
    with Session(engine) as session:
        yield session
