from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def normalize_db_url(url: str) -> str:
    """Neon/Railway hand out postgres:// or postgresql:// URLs — route them to
    the psycopg3 driver SQLAlchemy should use."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


database_url = normalize_db_url(settings.database_url)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
if database_url.startswith("sqlite:///"):
    # SQLite won't create missing parent directories (data/ is gitignored on fresh clones)
    Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
# pool_pre_ping revives connections severed by Neon's autosuspend (free tier
# sleeps after ~5 min idle); recycle keeps pooled connections younger than that
engine = create_engine(
    database_url, connect_args=connect_args, pool_pre_ping=True, pool_recycle=300
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
