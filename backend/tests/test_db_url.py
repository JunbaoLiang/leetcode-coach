from app.db import normalize_db_url


def test_heroku_style_postgres_scheme() -> None:
    assert normalize_db_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_plain_postgresql_scheme() -> None:
    assert normalize_db_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"


def test_explicit_driver_and_sqlite_untouched() -> None:
    assert normalize_db_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"
    assert normalize_db_url("sqlite:///./data/app.db") == "sqlite:///./data/app.db"
