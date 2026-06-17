"""Shared pytest fixtures.

Environment is configured BEFORE importing the app so the engine binds to a
throwaway SQLite database and startup seeding is disabled.
"""
import os
import tempfile

os.environ.setdefault("SEED_ON_STARTUP", "0")
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401  (register mappers)
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.enums import Role  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Recreate all tables before each test for full isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class UserFactory:
    """Insert a user directly and mint a valid JWT for them."""

    def __init__(self, session):
        self.session = session
        self._n = 0

    def __call__(self, role: Role = Role.CITIZEN, *, ward: str | None = None,
                 organization: str | None = None, name: str | None = None,
                 password: str = "Passw0rd!", is_active: bool = True):
        self._n += 1
        phone = f"90000{self._n:05d}"
        user = User(
            name=name or f"{role.value}-{self._n}",
            phone=phone,
            email=f"{role.value}{self._n}@example.com",
            password=hash_password(password),
            role=role.value,
            ward=ward,
            organization=organization,
            is_active=is_active,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        token = create_access_token(subject=user.id, role=user.role)
        return {
            "id": user.id,
            "phone": phone,
            "password": password,
            "token": token,
            "headers": auth_headers(token),
            "role": role.value,
        }


@pytest.fixture
def make_user(db):
    return UserFactory(db)


@pytest.fixture
def citizen(make_user):
    return make_user(Role.CITIZEN, ward="Ward 45 - Koh-e-Fiza")


@pytest.fixture
def officer(make_user):
    return make_user(Role.NODAL_OFFICER, ward="Ward 45 - Koh-e-Fiza")


@pytest.fixture
def worker(make_user):
    return make_user(Role.WORKER, ward="Ward 45 - Koh-e-Fiza")


@pytest.fixture
def ngo(make_user):
    return make_user(Role.NGO, ward="Ward 45 - Koh-e-Fiza", organization="Helping Hands")


@pytest.fixture
def authority(make_user):
    return make_user(Role.HIGHER_AUTHORITY)


@pytest.fixture
def admin(make_user):
    return make_user(Role.SUPER_ADMIN)


def make_complaint(client, citizen, **overrides) -> dict:
    payload = {
        "category": "Garbage / Waste Management",
        "description": "Garbage not collected for a week near the market.",
        "image_url": "/media/test.jpg",
        "address": "10 No Market",
        "ward": "Ward 45 - Koh-e-Fiza",
        "latitude": 23.25,
        "longitude": 77.41,
    }
    payload.update(overrides)
    resp = client.post("/complaints", json=payload, headers=citizen["headers"])
    assert resp.status_code == 201, resp.text
    return resp.json()
