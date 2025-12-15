"""Authentication API tests."""


class TestDevAuth:
    """Tests for development authentication endpoint."""

    def test_dev_auth_creates_user(self, client):
        """Dev endpoint should create a new user."""
        response = client.post(
            "/api/v1/auth/dev",
            json={"telegram_id": 99999, "username": "new_test_user"},
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "token" in data["data"]
        assert data["data"]["user"]["telegram_id"] == 99999
        assert data["data"]["user"]["username"] == "new_test_user"

    def test_dev_auth_returns_existing_user(self, client, test_user):
        """Dev endpoint should return existing user."""
        response = client.post(
            "/api/v1/auth/dev",
            json={"telegram_id": test_user["telegram_id"]},
        )

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["user"]["id"] == test_user["id"]

    def test_dev_auth_default_values(self, client):
        """Dev endpoint should use default values if not provided."""
        response = client.post("/api/v1/auth/dev", json={})

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert data["data"]["user"]["telegram_id"] == 12345


class TestGetCurrentUser:
    """Tests for getting current user."""

    def test_get_me_authenticated(self, auth_client):
        """Should return current user when authenticated."""
        response = auth_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json
        assert data["success"] is True
        assert "user" in data["data"]
        assert data["data"]["user"]["username"] == "test_user"

    def test_get_me_unauthenticated(self, client):
        """Should return 401 when not authenticated."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestTelegramAuth:
    """Tests for Telegram WebApp authentication."""

    def test_telegram_auth_missing_init_data(self, client):
        """Should return error when init_data is missing."""
        response = client.post("/api/v1/auth/telegram", json={})

        assert response.status_code == 400
        data = response.json
        assert data["success"] is False

    def test_telegram_auth_invalid_data(self, client):
        """Should return 401 for invalid Telegram data."""
        response = client.post(
            "/api/v1/auth/telegram",
            json={"init_data": "invalid_data"},
        )

        # Should be unauthorized due to invalid hash
        assert response.status_code == 401
