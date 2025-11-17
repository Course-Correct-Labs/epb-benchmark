"""Database utilities for EPB leaderboard."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from leaderboard.backend.models import Base

# Database path
DB_PATH = Path("leaderboard/data/epb_leaderboard.db")


def get_engine(db_path: Path = DB_PATH):
    """Get SQLAlchemy engine."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    return engine


def get_session_maker(db_path: Path = DB_PATH):
    """Get SQLAlchemy session maker."""
    engine = get_engine(db_path)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(db_path: Path = DB_PATH):
    """Initialize the database."""
    engine = get_engine(db_path)
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session (for FastAPI dependency injection)."""
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
