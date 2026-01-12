"""Tests for tasks API endpoints."""

from app import db
from app.models import Subtask, Task
from app.models.subtask import SubtaskStatus
from app.models.task import TaskStatus


class TestTasksAPI:
    """Test cases for tasks endpoints."""

    def test_create_task(self, auth_client, test_user):
        """Test creating a new task."""
        response = auth_client.post(
            "/api/v1/tasks",
            json={
                "title": "Test Task",
                "description": "Test description",
                "priority": "high",
            },
        )
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["data"]["task"]["title"] == "Test Task"
        assert response.json["data"]["task"]["priority"] == "high"

    def test_create_task_minimal(self, auth_client):
        """Test creating a task with only required fields."""
        response = auth_client.post(
            "/api/v1/tasks",
            json={"title": "Minimal Task"},
        )
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["data"]["task"]["title"] == "Minimal Task"

    def test_create_task_empty_title(self, auth_client):
        """Test creating a task without title fails."""
        response = auth_client.post(
            "/api/v1/tasks",
            json={"description": "No title"},
        )
        assert response.status_code == 400
        assert response.json["success"] is False

    def test_get_tasks(self, auth_client, test_user, app):
        """Test getting user's tasks."""
        # Create a task first
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Existing Task",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.commit()

        response = auth_client.get("/api/v1/tasks")
        assert response.status_code == 200
        assert response.json["success"] is True
        assert len(response.json["data"]["tasks"]) >= 1

    def test_get_tasks_filter_by_status(self, auth_client, test_user, app):
        """Test filtering tasks by status."""
        with app.app_context():
            task1 = Task(
                user_id=test_user["id"],
                title="In Progress Task",
                status=TaskStatus.IN_PROGRESS.value,
            )
            task2 = Task(
                user_id=test_user["id"],
                title="Completed Task",
                status=TaskStatus.COMPLETED.value,
            )
            db.session.add_all([task1, task2])
            db.session.commit()

        response = auth_client.get("/api/v1/tasks?status=in_progress")
        assert response.status_code == 200
        tasks = response.json["data"]["tasks"]
        assert all(t["status"] == "in_progress" for t in tasks)

    def test_get_single_task(self, auth_client, test_user, app):
        """Test getting a single task by ID."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Single Task",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = auth_client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json["data"]["task"]["title"] == "Single Task"

    def test_get_nonexistent_task(self, auth_client):
        """Test getting a task that doesn't exist."""
        response = auth_client.get("/api/v1/tasks/99999")
        assert response.status_code == 404

    def test_update_task(self, auth_client, test_user, app):
        """Test updating a task."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Original Title",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = auth_client.put(
            f"/api/v1/tasks/{task_id}",
            json={"title": "Updated Title", "priority": "low"},
        )
        assert response.status_code == 200
        assert response.json["data"]["task"]["title"] == "Updated Title"
        assert response.json["data"]["task"]["priority"] == "low"

    def test_complete_task(self, auth_client, test_user, app):
        """Test completing a task."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Task to Complete",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = auth_client.post(f"/api/v1/tasks/{task_id}/complete")
        assert response.status_code == 200
        assert response.json["data"]["task"]["status"] == "completed"

    def test_delete_task(self, auth_client, test_user, app):
        """Test deleting a task."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Task to Delete",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = auth_client.delete(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json["success"] is True


class TestSubtasksAPI:
    """Test cases for subtasks endpoints."""

    def test_create_subtask(self, auth_client, test_user, app):
        """Test creating a subtask."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Parent Task",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id

        response = auth_client.post(
            f"/api/v1/tasks/{task_id}/subtasks",
            json={
                "title": "New Subtask",
                "estimated_minutes": 30,
            },
        )
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["data"]["subtask"]["title"] == "New Subtask"

    def test_complete_subtask(self, auth_client, test_user, app):
        """Test completing a subtask."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Parent Task",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.flush()

            subtask = Subtask(
                task_id=task.id,
                title="Subtask to Complete",
                status=SubtaskStatus.PENDING.value,
            )
            db.session.add(subtask)
            db.session.commit()
            subtask_id = subtask.id

        response = auth_client.post(f"/api/v1/subtasks/{subtask_id}/complete")
        assert response.status_code == 200
        assert response.json["data"]["subtask"]["status"] == "completed"

    def test_update_subtask(self, auth_client, test_user, app):
        """Test updating a subtask."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Parent Task",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.flush()

            subtask = Subtask(
                task_id=task.id,
                title="Original Subtask",
                status=SubtaskStatus.PENDING.value,
            )
            db.session.add(subtask)
            db.session.commit()
            subtask_id = subtask.id

        response = auth_client.put(
            f"/api/v1/subtasks/{subtask_id}",
            json={"title": "Updated Subtask", "estimated_minutes": 45},
        )
        assert response.status_code == 200
        assert response.json["data"]["subtask"]["title"] == "Updated Subtask"

    def test_delete_subtask(self, auth_client, test_user, app):
        """Test deleting a subtask."""
        with app.app_context():
            task = Task(
                user_id=test_user["id"],
                title="Parent Task",
                status=TaskStatus.IN_PROGRESS.value,
            )
            db.session.add(task)
            db.session.flush()

            subtask = Subtask(
                task_id=task.id,
                title="Subtask to Delete",
                status=SubtaskStatus.PENDING.value,
            )
            db.session.add(subtask)
            db.session.commit()
            subtask_id = subtask.id

        response = auth_client.delete(f"/api/v1/subtasks/{subtask_id}")
        assert response.status_code == 200
        assert response.json["success"] is True
