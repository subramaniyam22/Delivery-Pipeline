"""
Test configuration and fixtures.
Importing app.main is deferred to the client fixture so tests that only need
db_session/admin_user (e.g. test_autopilot_integration) do not trigger
heavy app imports (e.g. langchain) and avoid pydantic/langsmith compatibility issues.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.models import User, Role, Region
from app.auth import get_password_hash

# Test database URL (in-memory SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override."""
    from fastapi.testclient import TestClient
    from app.main import app

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        email="admin@test.com",
        name="Admin Test",
        password_hash=get_password_hash("admin123"),
        role=Role.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sales_user(db_session):
    """Create a sales user for testing."""
    user = User(
        email="sales@test.com",
        name="Sales Test",
        password_hash=get_password_hash("sales123"),
        role=Role.SALES,
        region=Region.INDIA,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def manager_user(db_session):
    """Create a manager user for testing."""
    user = User(
        email="manager@test.com",
        name="Manager Test",
        password_hash=get_password_hash("manager123"),
        role=Role.MANAGER,
        region=Region.INDIA,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, admin_user):
    """Get authentication headers for admin user."""
    response = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sales_auth_headers(client, sales_user):
    """Get authentication headers for sales user."""
    response = client.post(
        "/auth/login",
        json={"email": "sales@test.com", "password": "sales123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_auth_headers(client, manager_user):
    """Get authentication headers for manager user."""
    response = client.post(
        "/auth/login",
        json={"email": "manager@test.com", "password": "manager123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
