"""Pytest configuration and fixtures."""

import pytest

from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    """Create and configure a test application instance."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user in the database."""
    with app.app_context():
        user = User(
            telegram_id=12345,
            username="test_user",
            first_name="Test",
            last_name="User",
            photo_url="https://example.com/photo.jpg",
        )
        db.session.add(user)
        db.session.commit()

        # Refresh to get the ID
        db.session.refresh(user)
        return {"id": user.id, "telegram_id": user.telegram_id}


@pytest.fixture
def auth_headers(client, test_user):
    """Get authorization headers with JWT token."""
    response = client.post(
        "/api/v1/auth/dev",
        json={
            "telegram_id": test_user["telegram_id"],
            "username": "test_user",
        },
    )
    assert response.status_code == 200
    token = response.json["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_client(client, auth_headers):
    """Create an authenticated test client wrapper."""

    class AuthenticatedClient:
        def __init__(self, client, headers):
            self._client = client
            self._headers = headers

        def get(self, *args, **kwargs):
            kwargs.setdefault("headers", {}).update(self._headers)
            return self._client.get(*args, **kwargs)

        def post(self, *args, **kwargs):
            kwargs.setdefault("headers", {}).update(self._headers)
            return self._client.post(*args, **kwargs)

        def put(self, *args, **kwargs):
            kwargs.setdefault("headers", {}).update(self._headers)
            return self._client.put(*args, **kwargs)

        def delete(self, *args, **kwargs):
            kwargs.setdefault("headers", {}).update(self._headers)
            return self._client.delete(*args, **kwargs)

        def patch(self, *args, **kwargs):
            kwargs.setdefault("headers", {}).update(self._headers)
            return self._client.patch(*args, **kwargs)

    return AuthenticatedClient(client, auth_headers)
