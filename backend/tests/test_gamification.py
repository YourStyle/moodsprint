"""Tests for gamification API endpoints."""

from datetime import datetime, timedelta

from app import db
from app.models import Achievement, FocusSession, Task
from app.models.focus_session import FocusSessionStatus
from app.models.task import TaskStatus


class TestUserStatsAPI:
    """Test cases for user stats endpoint."""

    def test_get_user_stats(self, auth_client, test_user):
        """Test getting user statistics."""
        response = auth_client.get("/api/v1/user/stats")
        assert response.status_code == 200
        assert response.json["success"] is True
        assert "xp" in response.json["data"]
        assert "level" in response.json["data"]
        assert "streak_days" in response.json["data"]
        assert "today" in response.json["data"]

    def test_user_stats_with_activity(self, auth_client, test_user, app):
        """Test user stats with some activity."""
        with app.app_context():
            # Create completed task
            task = Task(
                user_id=test_user["id"],
                title="Completed Task",
                status=TaskStatus.COMPLETED.value,
                completed_at=datetime.utcnow(),
            )
            db.session.add(task)

            # Create focus session
            session = FocusSession(
                user_id=test_user["id"],
                status=FocusSessionStatus.COMPLETED.value,
                planned_duration_minutes=25,
                actual_duration_minutes=25,
                started_at=datetime.utcnow() - timedelta(minutes=25),
                completed_at=datetime.utcnow(),
            )
            db.session.add(session)
            db.session.commit()

        response = auth_client.get("/api/v1/user/stats")
        assert response.status_code == 200
        data = response.json["data"]
        assert data["total_tasks_completed"] >= 1
        assert data["total_focus_minutes"] >= 25


class TestDailyGoalsAPI:
    """Test cases for daily goals endpoint."""

    def test_get_daily_goals(self, auth_client, test_user):
        """Test getting daily goals."""
        response = auth_client.get("/api/v1/user/daily-goals")
        assert response.status_code == 200
        data = response.json["data"]
        assert "goals" in data
        assert "all_completed" in data
        assert len(data["goals"]) == 3  # focus, subtasks, mood check


class TestDailyBonusAPI:
    """Test cases for daily bonus endpoints."""

    def test_get_daily_bonus_status(self, auth_client, test_user):
        """Test getting daily bonus status."""
        response = auth_client.get("/api/v1/daily-bonus/status")
        assert response.status_code == 200
        data = response.json["data"]
        assert "can_claim" in data
        assert "potential_xp" in data
        assert "streak_days" in data

    def test_claim_daily_bonus(self, auth_client, test_user):
        """Test claiming daily bonus."""
        response = auth_client.post("/api/v1/daily-bonus")
        assert response.status_code == 200
        data = response.json["data"]
        assert data["claimed"] is True
        assert "xp_earned" in data

    def test_claim_daily_bonus_twice(self, auth_client, test_user):
        """Test that claiming daily bonus twice fails."""
        # First claim
        auth_client.post("/api/v1/daily-bonus")

        # Second claim should fail
        response = auth_client.post("/api/v1/daily-bonus")
        assert response.status_code == 200
        assert response.json["data"]["claimed"] is False


class TestLeaderboardAPI:
    """Test cases for leaderboard endpoint."""

    def test_get_leaderboard_weekly(self, auth_client, test_user):
        """Test getting weekly leaderboard."""
        response = auth_client.get("/api/v1/leaderboard?type=weekly")
        assert response.status_code == 200
        data = response.json["data"]
        assert data["type"] == "weekly"
        assert "leaderboard" in data

    def test_get_leaderboard_all_time(self, auth_client, test_user):
        """Test getting all-time leaderboard."""
        response = auth_client.get("/api/v1/leaderboard?type=all_time")
        assert response.status_code == 200
        data = response.json["data"]
        assert data["type"] == "all_time"

    def test_get_leaderboard_with_limit(self, auth_client, test_user):
        """Test getting leaderboard with custom limit."""
        response = auth_client.get("/api/v1/leaderboard?limit=5")
        assert response.status_code == 200


class TestAchievementsAPI:
    """Test cases for achievements endpoints."""

    def test_get_all_achievements(self, auth_client, test_user, app):
        """Test getting all achievements."""
        with app.app_context():
            achievement = Achievement(
                code="test_achievement",
                name="Test Achievement",
                description="A test achievement",
                xp_reward=100,
                category="tasks",
                target_value=1,
            )
            db.session.add(achievement)
            db.session.commit()

        response = auth_client.get("/api/v1/achievements")
        assert response.status_code == 200
        assert len(response.json["data"]["achievements"]) >= 1

    def test_get_user_achievements(self, auth_client, test_user, app):
        """Test getting user's achievement progress."""
        with app.app_context():
            achievement = Achievement(
                code="user_test_achievement",
                name="User Test Achievement",
                description="A test achievement",
                xp_reward=100,
                category="tasks",
                target_value=1,
            )
            db.session.add(achievement)
            db.session.commit()

        response = auth_client.get("/api/v1/user/achievements")
        assert response.status_code == 200
        data = response.json["data"]
        assert "unlocked" in data
        assert "in_progress" in data


class TestGenresAPI:
    """Test cases for genre endpoints."""

    def test_get_genres(self, auth_client):
        """Test getting available genres."""
        response = auth_client.get("/api/v1/genres")
        assert response.status_code == 200
        genres = response.json["data"]["genres"]
        assert len(genres) > 0
        assert all("id" in g and "name" in g for g in genres)

    def test_set_genre(self, auth_client, test_user):
        """Test setting user's genre preference."""
        response = auth_client.put(
            "/api/v1/profile/genre",
            json={"genre": "fantasy"},
        )
        assert response.status_code == 200
        assert response.json["data"]["genre"] == "fantasy"

    def test_set_invalid_genre(self, auth_client, test_user):
        """Test setting an invalid genre fails."""
        response = auth_client.put(
            "/api/v1/profile/genre",
            json={"genre": "invalid_genre"},
        )
        assert response.status_code == 400


class TestQuestsAPI:
    """Test cases for daily quests endpoints."""

    def test_get_daily_quests(self, auth_client, test_user):
        """Test getting daily quests."""
        response = auth_client.get("/api/v1/quests")
        assert response.status_code == 200
        data = response.json["data"]
        assert "quests" in data
        assert "completed_count" in data
        assert "total_count" in data


class TestCharacterAPI:
    """Test cases for character endpoints."""

    def test_get_character(self, auth_client, test_user):
        """Test getting user's character."""
        response = auth_client.get("/api/v1/character")
        assert response.status_code == 200
        data = response.json["data"]
        assert "character" in data
        assert "stat_names" in data
        assert "genre" in data

    def test_heal_character(self, auth_client, test_user):
        """Test healing character."""
        response = auth_client.post("/api/v1/character/heal")
        assert response.status_code == 200
        assert "character" in response.json["data"]


class TestProductivityPatternsAPI:
    """Test cases for productivity patterns endpoint."""

    def test_get_productivity_patterns(self, auth_client, test_user):
        """Test getting productivity patterns."""
        response = auth_client.get("/api/v1/user/productivity-patterns")
        assert response.status_code == 200
        data = response.json["data"]
        assert "period_days" in data
        assert "total_sessions" in data
        assert "productivity_time" in data
        assert "day_distribution" in data
