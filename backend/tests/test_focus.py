"""Tests for focus sessions API endpoints."""

from datetime import datetime, timedelta

from app import db
from app.models import FocusSession, Subtask, Task
from app.models.focus_session import FocusSessionStatus
from app.models.subtask import SubtaskStatus
from app.models.task import TaskStatus


class TestFocusSessionsAPI:
    """Test cases for focus session endpoints."""

    def test_start_focus_session(self, auth_client, test_user):
        """Test starting a focus session without a subtask."""
        response = auth_client.post(
            "/api/v1/focus/start",
            json={"planned_duration_minutes": 25},
        )
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["data"]["session"]["status"] == "active"
        assert response.json["data"]["session"]["planned_duration_minutes"] == 25

    def test_start_focus_session_with_subtask(self, auth_client, test_user, app):
        """Test starting a focus session with a subtask."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Test Task",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.flush()

            subtask = Subtask(
                task_id=task.id,
                title="Test Subtask",
                status=SubtaskStatus.PENDING.value,
            )
            db.session.add(subtask)
            db.session.commit()
            subtask_id = subtask.id

        response = auth_client.post(
            "/api/v1/focus/start",
            json={
                "subtask_id": subtask_id,
                "planned_duration_minutes": 45,
            },
        )
        assert response.status_code == 200
        assert response.json["data"]["session"]["subtask_id"] == subtask_id

    def test_start_session_already_active(self, auth_client, test_user, app):
        """Test that starting a session when one is active fails."""
        # Start first session
        response1 = auth_client.post(
            "/api/v1/focus/start",
            json={"planned_duration_minutes": 25},
        )
        assert response1.status_code == 200

        # Try to start another
        response2 = auth_client.post(
            "/api/v1/focus/start",
            json={"planned_duration_minutes": 25},
        )
        assert response2.status_code == 400

    def test_get_active_session(self, auth_client, test_user, app):
        """Test getting the active focus session."""
        # Start a session
        auth_client.post(
            "/api/v1/focus/start",
            json={"planned_duration_minutes": 25},
        )

        response = auth_client.get("/api/v1/focus/active")
        assert response.status_code == 200
        assert response.json["data"]["session"] is not None
        assert response.json["data"]["session"]["status"] == "active"

    def test_get_active_session_none(self, auth_client):
        """Test getting active session when none exists."""
        response = auth_client.get("/api/v1/focus/active")
        assert response.status_code == 200
        assert response.json["data"]["session"] is None

    def test_complete_session(self, auth_client, test_user):
        """Test completing a focus session."""
        # Start a session
        auth_client.post(
            "/api/v1/focus/start",
            json={"planned_duration_minutes": 25},
        )

        response = auth_client.post(
            "/api/v1/focus/complete",
            json={"complete_subtask": False},
        )
        assert response.status_code == 200
        assert response.json["data"]["session"]["status"] == "completed"

    def test_cancel_session(self, auth_client, test_user):
        """Test canceling a focus session."""
        # Start a session
        auth_client.post(
            "/api/v1/focus/start",
            json={"planned_duration_minutes": 25},
        )

        response = auth_client.post("/api/v1/focus/cancel")
        assert response.status_code == 200
        assert response.json["data"]["session"]["status"] == "cancelled"

    def test_pause_session(self, auth_client, test_user):
        """Test pausing a focus session."""
        # Start a session
        auth_client.post(
            "/api/v1/focus/start",
            json={"planned_duration_minutes": 25},
        )

        response = auth_client.post("/api/v1/focus/pause")
        assert response.status_code == 200
        assert response.json["data"]["session"]["status"] == "paused"

    def test_resume_session(self, auth_client, test_user):
        """Test resuming a paused focus session."""
        # Start and pause a session
        auth_client.post(
            "/api/v1/focus/start",
            json={"planned_duration_minutes": 25},
        )
        auth_client.post("/api/v1/focus/pause")

        response = auth_client.post("/api/v1/focus/resume")
        assert response.status_code == 200
        assert response.json["data"]["session"]["status"] == "active"

    def test_get_focus_history(self, auth_client, test_user, app):
        """Test getting focus session history."""
        with app.app_context():
            # Create some completed sessions
            for i in range(3):
                session = FocusSession(
                    user_id=test_user["id"],
                    status=FocusSessionStatus.COMPLETED.value,
                    planned_duration_minutes=25,
                    actual_duration_minutes=25,
                    started_at=datetime.utcnow() - timedelta(hours=i),
                    completed_at=datetime.utcnow()
                    - timedelta(hours=i)
                    + timedelta(minutes=25),
                )
                db.session.add(session)
            db.session.commit()

        response = auth_client.get("/api/v1/focus/history")
        assert response.status_code == 200
        assert len(response.json["data"]["sessions"]) == 3

    def test_get_focus_history_with_limit(self, auth_client, test_user, app):
        """Test getting focus history with limit."""
        with app.app_context():
            for i in range(5):
                session = FocusSession(
                    user_id=test_user["id"],
                    status=FocusSessionStatus.COMPLETED.value,
                    planned_duration_minutes=25,
                    actual_duration_minutes=25,
                    started_at=datetime.utcnow() - timedelta(hours=i),
                    completed_at=datetime.utcnow()
                    - timedelta(hours=i)
                    + timedelta(minutes=25),
                )
                db.session.add(session)
            db.session.commit()

        response = auth_client.get("/api/v1/focus/history?limit=2")
        assert response.status_code == 200
        assert len(response.json["data"]["sessions"]) == 2
