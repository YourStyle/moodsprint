"""Tests for onboarding API endpoints."""


class TestOnboardingAPI:
    """Test cases for onboarding endpoints."""

    def test_get_profile(self, auth_client, test_user):
        """Test getting user profile."""
        response = auth_client.get("/api/v1/profile")
        assert response.status_code == 200
        data = response.json["data"]
        assert "profile" in data
        assert "user" in data

    def test_update_profile(self, auth_client, test_user):
        """Test updating user profile."""
        response = auth_client.put(
            "/api/v1/profile",
            json={
                "work_start_time": "09:00",
                "work_end_time": "18:00",
                "work_days": [1, 2, 3, 4, 5],
                "preferred_session_duration": 25,
            },
        )
        assert response.status_code == 200
        profile = response.json["data"]["profile"]
        assert profile["work_start_time"] == "09:00"
        assert profile["work_end_time"] == "18:00"
        assert profile["work_days"] == [1, 2, 3, 4, 5]

    def test_update_profile_notifications(self, auth_client, test_user):
        """Test updating notification settings."""
        response = auth_client.put(
            "/api/v1/profile",
            json={
                "notifications_enabled": True,
                "daily_reminder_time": "08:00",
            },
        )
        assert response.status_code == 200
        profile = response.json["data"]["profile"]
        assert profile["notifications_enabled"] is True
        assert profile["daily_reminder_time"] == "08:00"

    def test_complete_onboarding(self, auth_client, test_user, app):
        """Test completing onboarding."""
        # First set profile data
        auth_client.put(
            "/api/v1/profile",
            json={
                "work_start_time": "09:00",
                "work_end_time": "18:00",
            },
        )

        response = auth_client.post("/api/v1/profile/complete-onboarding")
        assert response.status_code == 200
        assert response.json["data"]["completed"] is True


class TestMoodAPI:
    """Test cases for mood endpoints."""

    def test_submit_mood(self, auth_client, test_user):
        """Test submitting a mood check."""
        response = auth_client.post(
            "/api/v1/mood",
            json={
                "mood_level": 4,
                "energy_level": 3,
                "note": "Feeling good today",
            },
        )
        assert response.status_code == 200
        data = response.json["data"]
        assert "mood_check" in data
        assert data["mood_check"]["mood_level"] == 4
        assert data["mood_check"]["energy_level"] == 3

    def test_submit_mood_without_note(self, auth_client, test_user):
        """Test submitting mood without note."""
        response = auth_client.post(
            "/api/v1/mood",
            json={
                "mood_level": 5,
                "energy_level": 5,
            },
        )
        assert response.status_code == 200
        assert response.json["data"]["mood_check"]["mood_level"] == 5

    def test_submit_mood_invalid_level(self, auth_client, test_user):
        """Test submitting invalid mood level."""
        response = auth_client.post(
            "/api/v1/mood",
            json={
                "mood_level": 10,  # Invalid - should be 1-5
                "energy_level": 3,
            },
        )
        assert response.status_code == 400

    def test_get_mood_history(self, auth_client, test_user):
        """Test getting mood history."""
        # Submit some moods first
        for level in [3, 4, 5]:
            auth_client.post(
                "/api/v1/mood",
                json={"mood_level": level, "energy_level": level},
            )

        response = auth_client.get("/api/v1/mood/history")
        assert response.status_code == 200
        assert len(response.json["data"]["moods"]) >= 3

    def test_get_latest_mood(self, auth_client, test_user):
        """Test getting latest mood."""
        # Submit a mood first
        auth_client.post(
            "/api/v1/mood",
            json={"mood_level": 4, "energy_level": 4},
        )

        response = auth_client.get("/api/v1/mood/latest")
        assert response.status_code == 200
        assert response.json["data"]["mood"]["mood_level"] == 4

    def test_get_mood_stats(self, auth_client, test_user):
        """Test getting mood statistics."""
        response = auth_client.get("/api/v1/mood/stats")
        assert response.status_code == 200
        data = response.json["data"]
        assert "average_mood" in data or "stats" in data
