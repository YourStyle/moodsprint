"""Tasks API endpoints."""

from datetime import date, datetime

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.api import api_bp
from app.models import MoodCheck, PostponeLog, Subtask, Task, User, UserProfile
from app.models.subtask import SubtaskStatus
from app.models.task import TaskPriority, TaskStatus
from app.services import AchievementChecker, AIDecomposer, TaskClassifier, XPCalculator
from app.utils import not_found, success_response, validation_error


def get_current_time_slot() -> str:
    """Get current time slot based on hour."""
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def calculate_task_score(
    task: Task,
    current_time_slot: str,
    user_favorite_types: list[str] | None,
    today: date,
) -> int:
    """Calculate sorting score for a task."""
    score = 0

    # Priority weight (HIGH=100, MEDIUM=50, LOW=0)
    priority_weights = {"high": 100, "medium": 50, "low": 0}
    score += priority_weights.get(task.priority, 50)

    # Time match (+30 if preferred time matches current time slot)
    if task.preferred_time and task.preferred_time == current_time_slot:
        score += 30

    # Type match (+20 if task type is in user's favorites)
    if user_favorite_types and task.task_type in user_favorite_types:
        score += 20

    # Postponed count (+15 per postponement)
    score += (task.postponed_count or 0) * 15

    # Overdue bonus (+50 if task is overdue)
    if (
        task.due_date
        and task.due_date < today
        and task.status != TaskStatus.COMPLETED.value
    ):
        score += 50

    return score


@api_bp.route("/tasks", methods=["GET"])
@jwt_required()
def get_tasks():
    """
    Get all tasks for current user with smart sorting.

    Query params:
    - status: filter by status (pending, in_progress, completed)
    - due_date: filter by due date (YYYY-MM-DD format)
    - limit: max results (default 50)
    - offset: pagination offset (default 0)
    - smart_sort: enable smart sorting (default true)
    """
    user_id = int(get_jwt_identity())

    # Build query
    query = Task.query.filter_by(user_id=user_id)

    # Filter by status
    status = request.args.get("status")
    if status and status in [s.value for s in TaskStatus]:
        query = query.filter_by(status=status)

    # Filter by due_date
    due_date_str = request.args.get("due_date")
    if due_date_str:
        try:
            due_date_filter = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            query = query.filter(Task.due_date == due_date_filter)
        except ValueError:
            pass

    # Get total count before pagination
    total = query.count()

    # Pagination
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))

    # Check if smart sorting is enabled (default: true)
    smart_sort = request.args.get("smart_sort", "true").lower() != "false"

    if smart_sort:
        # Get all tasks for smart sorting
        all_tasks = query.all()

        # Get user profile for favorite task types
        user_profile = UserProfile.query.filter_by(user_id=user_id).first()
        favorite_types = user_profile.favorite_task_types if user_profile else None

        # Get current time slot and today's date
        current_time_slot = get_current_time_slot()
        today = date.today()

        # Sort tasks by score (descending), then by due_date (ascending)
        sorted_tasks = sorted(
            all_tasks,
            key=lambda t: (
                -calculate_task_score(t, current_time_slot, favorite_types, today),
                t.due_date or date.max,
            ),
        )

        # Apply pagination
        tasks = sorted_tasks[offset : offset + limit]
    else:
        # Simple ordering by created_at desc
        query = query.order_by(Task.created_at.desc())
        tasks = query.offset(offset).limit(limit).all()

    return success_response({"tasks": [t.to_dict() for t in tasks], "total": total})


@api_bp.route("/tasks", methods=["POST"])
@jwt_required()
def create_task():
    """
    Create a new task.

    Request body:
    {
        "title": "Task title",
        "description": "Optional description",
        "priority": "low|medium|high",
        "due_date": "YYYY-MM-DD"  // optional, defaults to today
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return validation_error({"body": "Request body is required"})

    title = data.get("title", "").strip()
    if not title:
        return validation_error({"title": "Title is required"})

    if len(title) > 500:
        return validation_error({"title": "Title must be less than 500 characters"})

    priority = data.get("priority", TaskPriority.MEDIUM.value)
    if priority not in [p.value for p in TaskPriority]:
        priority = TaskPriority.MEDIUM.value

    # Parse due_date
    due_date_value = date.today()
    due_date_str = data.get("due_date")
    if due_date_str:
        try:
            due_date_value = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    description = data.get("description")

    task = Task(
        user_id=user_id,
        title=title,
        description=description,
        priority=priority,
        due_date=due_date_value,
        original_due_date=due_date_value,
    )

    db.session.add(task)
    db.session.commit()

    # Classify task asynchronously (non-blocking)
    try:
        classifier = TaskClassifier()
        classification = classifier.classify_task(title, description)
        task.task_type = classification.get("task_type")
        task.preferred_time = classification.get("preferred_time")
        db.session.commit()
    except Exception:
        # Classification is optional, don't fail task creation
        pass

    return success_response({"task": task.to_dict()}, status_code=201)


@api_bp.route("/tasks/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id: int):
    """Get a single task with subtasks."""
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    return success_response({"task": task.to_dict(include_subtasks=True)})


@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
@jwt_required()
def update_task(task_id: int):
    """
    Update a task.

    Request body (all optional):
    {
        "title": "New title",
        "description": "New description",
        "priority": "low|medium|high",
        "status": "pending|in_progress|completed",
        "due_date": "YYYY-MM-DD",
        "task_type": "creative|analytical|communication|physical|learning|planning|coding|writing"
    }
    """
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    data = request.get_json() or {}

    if "title" in data:
        title = data["title"].strip()
        if not title:
            return validation_error({"title": "Title cannot be empty"})
        if len(title) > 500:
            return validation_error({"title": "Title must be less than 500 characters"})
        task.title = title

    if "description" in data:
        task.description = data["description"]

    if "priority" in data:
        if data["priority"] in [p.value for p in TaskPriority]:
            task.priority = data["priority"]

    if "status" in data:
        if data["status"] in [s.value for s in TaskStatus]:
            task.status = data["status"]

    if "due_date" in data:
        try:
            task.due_date = datetime.strptime(data["due_date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    # Update task_type if provided
    valid_task_types = [
        "creative",
        "analytical",
        "communication",
        "physical",
        "learning",
        "planning",
        "coding",
        "writing",
    ]
    if "task_type" in data and data["task_type"] in valid_task_types:
        task.task_type = data["task_type"]

    db.session.commit()

    # Check achievements if task completed
    xp_info = None
    achievements_unlocked = []
    if task.status == TaskStatus.COMPLETED.value:
        user = User.query.get(user_id)
        xp_info = user.add_xp(XPCalculator.task_completed())
        user.update_streak()

        checker = AchievementChecker(user)
        achievements_unlocked = checker.check_all()

        db.session.commit()

    response_data = {"task": task.to_dict()}
    if xp_info:
        response_data["xp_earned"] = xp_info["xp_earned"]
        response_data["achievements_unlocked"] = [
            a.to_dict() for a in achievements_unlocked
        ]

    return success_response(response_data)


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id: int):
    """Delete a task and all its subtasks."""
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    db.session.delete(task)
    db.session.commit()

    return success_response(message="Task deleted")


@api_bp.route("/tasks/<int:task_id>/decompose", methods=["POST"])
@jwt_required()
def decompose_task(task_id: int):
    """
    AI-decompose a task into subtasks based on mood.

    Request body:
    {
        "mood_id": 5  // optional, uses latest mood if not provided
    }
    """
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    data = request.get_json() or {}

    # Get mood check
    mood_id = data.get("mood_id")
    if mood_id:
        mood_check = MoodCheck.query.filter_by(id=mood_id, user_id=user_id).first()
    else:
        mood_check = (
            MoodCheck.query.filter_by(user_id=user_id)
            .order_by(MoodCheck.created_at.desc())
            .first()
        )

    if not mood_check:
        # Use default strategy if no mood
        strategy = "standard"
    else:
        strategy = mood_check.decomposition_strategy

    # Clear existing subtasks
    Subtask.query.filter_by(task_id=task.id).delete()

    # Decompose task with type context
    decomposer = AIDecomposer()
    subtask_data = decomposer.decompose_task(
        task.title, task.description, strategy, task.task_type
    )

    # Create subtasks
    subtasks = []
    for data in subtask_data:
        subtask = Subtask(
            task_id=task.id,
            title=data["title"],
            estimated_minutes=data["estimated_minutes"],
            order=data["order"],
        )
        db.session.add(subtask)
        subtasks.append(subtask)

    db.session.commit()

    return success_response(
        {
            "subtasks": [s.to_dict() for s in subtasks],
            "strategy": strategy,
            "message": decomposer.get_strategy_message(strategy),
        }
    )


@api_bp.route("/tasks/postpone-status", methods=["GET"])
@jwt_required()
def get_postpone_status():
    """
    Get the latest postpone log for the current user.

    Returns info about tasks postponed today for display notification.
    """
    user_id = int(get_jwt_identity())
    today = date.today()

    # Get today's postpone log
    log = PostponeLog.query.filter_by(user_id=user_id, date=today).first()

    if not log or log.tasks_postponed == 0:
        return success_response(
            {
                "has_postponed": False,
                "tasks_postponed": 0,
                "priority_changes": [],
                "message": None,
            }
        )

    # Mark as notified
    if not log.notified:
        log.notified = True
        db.session.commit()

    # Build message
    if log.tasks_postponed == 1:
        message = "Перенесена 1 задача с прошлых дней"
    elif log.tasks_postponed < 5:
        message = f"Перенесено {log.tasks_postponed} задачи с прошлых дней"
    else:
        message = f"Перенесено {log.tasks_postponed} задач с прошлых дней"

    return success_response(
        {
            "has_postponed": True,
            "tasks_postponed": log.tasks_postponed,
            "priority_changes": log.priority_changes or [],
            "message": message,
        }
    )


# Subtask endpoints


@api_bp.route("/tasks/<int:task_id>/subtasks", methods=["POST"])
@jwt_required()
def create_subtask(task_id: int):
    """
    Create a new subtask for a task.

    Request body:
    {
        "title": "Subtask title",
        "estimated_minutes": 15  // optional, default 10
    }
    """
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    data = request.get_json()
    if not data:
        return validation_error({"body": "Request body is required"})

    title = data.get("title", "").strip()
    if not title:
        return validation_error({"title": "Title is required"})

    if len(title) > 500:
        return validation_error({"title": "Title must be less than 500 characters"})

    # Get max order
    max_order = (
        db.session.query(db.func.max(Subtask.order)).filter_by(task_id=task_id).scalar()
        or 0
    )

    estimated_minutes = data.get("estimated_minutes", 10)
    try:
        estimated_minutes = max(1, min(120, int(estimated_minutes)))
    except (ValueError, TypeError):
        estimated_minutes = 10

    subtask = Subtask(
        task_id=task.id,
        title=title,
        estimated_minutes=estimated_minutes,
        order=max_order + 1,
    )

    db.session.add(subtask)
    db.session.commit()

    return success_response({"subtask": subtask.to_dict()}, status_code=201)


@api_bp.route("/subtasks/<int:subtask_id>", methods=["PUT"])
@jwt_required()
def update_subtask(subtask_id: int):
    """
    Update a subtask.

    Request body (all optional):
    {
        "title": "New title",
        "status": "pending|in_progress|completed|skipped",
        "estimated_minutes": 15
    }
    """
    user_id = int(get_jwt_identity())

    subtask = (
        Subtask.query.join(Task)
        .filter(Subtask.id == subtask_id, Task.user_id == user_id)
        .first()
    )

    if not subtask:
        return not_found("Subtask not found")

    data = request.get_json() or {}
    old_status = subtask.status

    if "title" in data:
        title = data["title"].strip()
        if title:
            subtask.title = title[:500]

    if "estimated_minutes" in data:
        try:
            minutes = int(data["estimated_minutes"])
            subtask.estimated_minutes = max(1, min(120, minutes))
        except (ValueError, TypeError):
            pass

    if "status" in data:
        if data["status"] in [s.value for s in SubtaskStatus]:
            subtask.status = data["status"]
            if data["status"] == SubtaskStatus.COMPLETED.value:
                subtask.complete()

    # Update parent task status
    subtask.task.update_status_from_subtasks()

    db.session.commit()

    # Calculate XP if completed
    xp_info = None
    achievements_unlocked = []

    was_completed = (
        old_status != SubtaskStatus.COMPLETED.value
        and subtask.status == SubtaskStatus.COMPLETED.value
    )

    if was_completed:
        user = User.query.get(user_id)
        xp_earned = XPCalculator.subtask_completed()

        # Bonus XP if all subtasks completed (task completed)
        if subtask.task.status == TaskStatus.COMPLETED.value:
            xp_earned += XPCalculator.task_completed()

        xp_info = user.add_xp(xp_earned)
        user.update_streak()

        checker = AchievementChecker(user)
        achievements_unlocked = checker.check_all()

        db.session.commit()

    response_data = {"subtask": subtask.to_dict()}
    if xp_info:
        response_data["xp_earned"] = xp_info["xp_earned"]
        response_data["achievements_unlocked"] = [
            a.to_dict() for a in achievements_unlocked
        ]

    return success_response(response_data)


@api_bp.route("/subtasks/reorder", methods=["POST"])
@jwt_required()
def reorder_subtasks():
    """
    Reorder subtasks within a task.

    Request body:
    {
        "task_id": 1,
        "subtask_ids": [3, 1, 2, 4]
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or "task_id" not in data or "subtask_ids" not in data:
        return validation_error({"body": "task_id and subtask_ids are required"})

    task = Task.query.filter_by(id=data["task_id"], user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    subtask_ids = data["subtask_ids"]

    # Update order for each subtask
    for order, subtask_id in enumerate(subtask_ids, 1):
        subtask = Subtask.query.filter_by(id=subtask_id, task_id=task.id).first()
        if subtask:
            subtask.order = order

    db.session.commit()

    return success_response(message="Subtasks reordered")
