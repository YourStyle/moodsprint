"""Tests for admin broadcast routes."""

import pytest
from admin.app import app as admin_app


@pytest.fixture
def admin_client():
    """Create admin test client."""
    admin_app.config["TESTING"] = True
    admin_app.config["WTF_CSRF_ENABLED"] = False
    with admin_app.test_client() as client:
        # Login
        with client.session_transaction() as sess:
            sess["logged_in"] = True
        yield client


class TestBroadcastPage:
    """Test broadcast form page."""

    def test_broadcast_page_requires_login(self):
        """Should redirect to login when not authenticated."""
        admin_app.config["TESTING"] = True
        with admin_app.test_client() as client:
            response = client.get("/broadcast")
            assert response.status_code == 302
            assert "/login" in response.location

    def test_broadcast_page_loads(self, admin_client):
        """Should load the broadcast form page."""
        response = admin_client.get("/broadcast")
        assert response.status_code == 200
        assert b"Broadcast" in response.data or b"broadcast" in response.data


class TestBroadcastSend:
    """Test broadcast send endpoint."""

    def test_send_requires_login(self):
        """Should redirect to login when not authenticated."""
        admin_app.config["TESTING"] = True
        with admin_app.test_client() as client:
            response = client.post("/broadcast/send", data={"message": "test"})
            assert response.status_code == 302

    def test_send_empty_message(self, admin_client):
        """Should reject empty message."""
        response = admin_client.post(
            "/broadcast/send",
            data={"message": "", "filter_type": "all"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "empty" in data["error"].lower()

    def test_send_no_bot_token(self, admin_client):
        """Should fail when BOT_TOKEN is not set."""
        import admin.app as admin_module

        original_token = admin_module.BOT_TOKEN
        admin_module.BOT_TOKEN = ""
        try:
            response = admin_client.post(
                "/broadcast/send",
                data={"message": "Hello!", "filter_type": "all"},
            )
            assert response.status_code == 500
            data = response.get_json()
            assert "BOT_TOKEN" in data["error"]
        finally:
            admin_module.BOT_TOKEN = original_token
