import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

_engine = None
_SessionLocal = None

def init_db(db_url: str | None = None, echo: bool = False):
    global _engine, _SessionLocal
    db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///timetable.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    _engine = create_engine(db_url, echo=echo)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(_engine)

def get_session() -> Session:
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionLocal()

def get_engine():
    return _engine
