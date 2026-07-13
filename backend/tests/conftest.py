import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def db_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def client(db_factory, monkeypatch):
    def override():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    # streaming endpoints persist after the response via SessionLocal — point it at the test DB
    from app.routers import hints as hints_router
    from app.routers import mock as mock_router

    monkeypatch.setattr(hints_router, "SessionLocal", db_factory)
    monkeypatch.setattr(mock_router, "SessionLocal", db_factory)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
