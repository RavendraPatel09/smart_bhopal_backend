"""Database engine, session factory and declarative base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def init_db() -> None:
    """Create all tables. Import models for side effects before calling."""
    import app.models  # noqa: F401  (registers mappers)

    Base.metadata.create_all(bind=engine)
