"""Pytest fixtures — in-memory SQLite database for fast, isolated tests."""
import uuid
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app

# Import all models so they register with Base.metadata
from app.models.user import User                     # noqa: F401
from app.models.group import Group, GroupMember       # noqa: F401
from app.models.event import Event                    # noqa: F401
from app.models.attendee import EventAttendee         # noqa: F401
from app.models.change_request import ChangeRequest   # noqa: F401
from app.models.event_mutation import EventMutation   # noqa: F401

SQLITE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh SQLite engine for each test."""
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

    # Enable WAL mode for better concurrency
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db(db_engine):
    """Yield a database session, rolled back after the test."""
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_engine):
    """FastAPI TestClient with the database dependency overridden to use SQLite."""
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def _override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: create a user via the API, returns the JSON response dict
# ---------------------------------------------------------------------------
def create_test_user(client: TestClient, name: str = "Test User", tz: str = "America/New_York") -> dict:
    """Helper — POST /api/users and return response JSON."""
    resp = client.post("/api/users/", json={
        "display_name": name,
        "default_timezone": tz,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_test_group(client: TestClient, creator_id: str, name: str = "Test Group") -> dict:
    """Helper — POST /api/groups and return response JSON."""
    resp = client.post("/api/groups/", json={
        "name": name,
        "created_by": creator_id,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()
