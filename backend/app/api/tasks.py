"""Tasks API endpoints."""

import logging
from datetime import date, datetime

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.api import api_bp
from app.models import (
    FriendActivityLog,
    MoodCheck,
    PostponeLog,
    SharedTask,
    SharedTaskStatus,
    Subtask,
    Task,
    User,
    UserActivityLog,
    UserProfile,
)
from app.models.card import CardRarity
from app.models.subtask import SubtaskStatus
from app.models.task import TaskPriority, TaskStatus
from app.services import AchievementChecker, AIDecomposer, TaskClassifier, XPCalculator
from app.services.card_service import (
    COMPANION_XP_BY_DIFFICULTY,
    CardService,
    get_rarity_odds,
)
from app.services.streak_service import StreakService
from app.services.task_service import (
    MIN_TASK_TIME_FOR_CARD,
    auto_postpone_overdue_tasks,
    calculate_task_score,
    get_current_time_slot,
    should_skip_time_check_for_card,
)
from app.utils import not_found, success_response, validation_error

logger = logging.getLogger(__name__)


@api_bp.route("/tasks", methods=["GET"])
@jwt_required()
def get_tasks():
    """
    Get all tasks for current user with smart sorting.

    Query params:
    - status: filter by status (pending, in_progress, completed)
    - due_date: filter by exact due date (YYYY-MM-DD format)
    - due_date_from: filter by due date >= (YYYY-MM-DD format)
    - due_date_to: filter by due date <= (YYYY-MM-DD format)
    - limit: max results (default 50)
    - offset: pagination offset (default 0)
    - smart_sort: enable smart sorting (default true)
    """
    user_id = int(get_jwt_identity())

    # Auto-postpone any overdue tasks (fallback if bot cron didn't run)
    auto_postpone_overdue_tasks(user_id)

    # Build query
    query = Task.query.filter_by(user_id=user_id)

    # Filter by status
    status = request.args.get("status")
    if status and status in [s.value for s in TaskStatus]:
        query = query.filter_by(status=status)
    else:
        # Exclude archived tasks by default
        query = query.filter(Task.status != TaskStatus.ARCHIVED.value)

    # Filter by due_date (exact match)
    due_date_str = request.args.get("due_date")
    if due_date_str:
        try:
            due_date_filter = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            query = query.filter(Task.due_date == due_date_filter)
        except ValueError:
            pass

    # Filter by date range
    due_date_from = request.args.get("due_date_from")
    if due_date_from:
        try:
            date_from = datetime.strptime(due_date_from, "%Y-%m-%d").date()
            query = query.filter(Task.due_date >= date_from)
        except ValueError:
            pass

    due_date_to = request.args.get("due_date_to")
    if due_date_to:
        try:
            date_to = datetime.strptime(due_date_to, "%Y-%m-%d").date()
            query = query.filter(Task.due_date <= date_to)
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

        # Sort by score (desc), due_date (asc), created_at (desc - newer first)
        sorted_tasks = sorted(
            all_tasks,
            key=lambda t: (
                -calculate_task_score(t, current_time_slot, favorite_types, today),
                t.due_date or date.max,
                -t.created_at.timestamp() if t.created_at else 0,
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
        "priority": "low|medium|high",  // optional, AI will determine if not provided
        "due_date": "YYYY-MM-DD"  // optional, defaults to today
    }

    Note: If priority is not provided, AI will analyze the task and set difficulty automatically.
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

    description = data.get("description")

    # Combined AI call: classify task type, preferred time, AND difficulty
    priority = data.get("priority")
    ai_difficulty = None
    ai_task_type = None
    ai_preferred_time = None

    try:
        classifier = TaskClassifier()
        classification = classifier.classify_and_rate_task(
            title, description, user_id=user_id
        )
        ai_difficulty = classification["difficulty"]
        ai_task_type = classification.get("task_type")
        ai_preferred_time = classification.get("preferred_time")
    except Exception:
        ai_difficulty = "medium"

    if not priority or priority not in [p.value for p in TaskPriority]:
        # Map AI difficulty to priority
        difficulty_to_priority = {
            "easy": TaskPriority.LOW.value,
            "medium": TaskPriority.MEDIUM.value,
            "hard": TaskPriority.HIGH.value,
            "very_hard": TaskPriority.HIGH.value,
        }
        priority = difficulty_to_priority.get(ai_difficulty, TaskPriority.MEDIUM.value)
    else:
        # Map user-provided priority to difficulty for card generation
        priority_to_difficulty = {
            TaskPriority.LOW.value: "easy",
            TaskPriority.MEDIUM.value: "medium",
            TaskPriority.HIGH.value: "hard",
        }
        ai_difficulty = priority_to_difficulty.get(priority, "medium")

    # Parse due_date
    due_date_value = date.today()
    due_date_str = data.get("due_date")
    if due_date_str:
        try:
            due_date_value = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    preferred_time = data.get("preferred_time")

    # Validate preferred_time if provided
    valid_times = ["morning", "afternoon", "evening", "night"]
    if preferred_time and preferred_time not in valid_times:
        preferred_time = None

    # Parse scheduled_at for reminders
    scheduled_at = None
    scheduled_at_str = data.get("scheduled_at")
    if scheduled_at_str:
        try:
            scheduled_at = datetime.fromisoformat(
                scheduled_at_str.replace("Z", "+00:00")
            )
        except ValueError:
            pass

    # Use AI-classified preferred_time if user didn't provide one
    if not preferred_time and ai_preferred_time:
        preferred_time = ai_preferred_time

    task = Task(
        user_id=user_id,
        title=title,
        description=description,
        priority=priority,
        due_date=due_date_value,
        original_due_date=due_date_value,
        preferred_time=preferred_time,
        scheduled_at=scheduled_at,
        difficulty=ai_difficulty,
        task_type=ai_task_type,
    )

    db.session.add(task)
    db.session.commit()

    try:
        UserActivityLog.log(
            user_id=user_id,
            action_type="task_create",
            action_details=f"Created task: {title[:100]}",
            entity_type="task",
            entity_id=task.id,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    return success_response(
        {
            "task": task.to_dict(),
            "ai_difficulty": ai_difficulty,
        },
        status_code=201,
    )


@api_bp.route("/tasks/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id: int):
    """Get a single task with subtasks. Also accessible by shared assignees."""
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    is_shared_assignee = False

    # If not owner, check if shared with this user (accepted)
    if not task:
        task = Task.query.get(task_id)
        if task:
            shared = SharedTask.query.filter_by(
                task_id=task_id,
                assignee_id=user_id,
                status=SharedTaskStatus.ACCEPTED.value,
            ).first()
            if shared:
                is_shared_assignee = True
            else:
                return not_found("Task not found")
        else:
            return not_found("Task not found")

    task_data = task.to_dict(include_subtasks=True)
    task_data["is_shared_assignee"] = is_shared_assignee

    # Include rarity odds for uncompleted tasks (owner only)
    if not is_shared_assignee and task.status != "completed" and task.difficulty:
        task_data["rarity_odds"] = get_rarity_odds(task.difficulty)

    return success_response({"task": task_data})


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
    old_status = task.status  # Save old status to check for completion transition

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

            # Reset counters when restoring from archive
            if (
                old_status == TaskStatus.ARCHIVED.value
                and data["status"] == TaskStatus.PENDING.value
            ):
                task.due_date = date.today()
                task.postponed_count = 0
                task.original_due_date = None

    if "due_date" in data:
        if data["due_date"] is None:
            task.due_date = None
        else:
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

    # Update scheduled_at for reminders
    if "scheduled_at" in data:
        if data["scheduled_at"] is None:
            task.scheduled_at = None
            task.reminder_sent = False
        else:
            try:
                task.scheduled_at = datetime.fromisoformat(
                    data["scheduled_at"].replace("Z", "+00:00")
                )
                task.reminder_sent = False  # Reset so new reminder will be sent
            except (ValueError, AttributeError):
                pass

    db.session.commit()

    # Check achievements if task just completed (transition from non-completed to completed)
    xp_info = None
    achievements_unlocked = []
    generated_card = None
    is_quick_completion = False

    task_just_completed = (
        old_status != TaskStatus.COMPLETED.value
        and task.status == TaskStatus.COMPLETED.value
    )

    if task_just_completed:
        user = User.query.get(user_id)
        xp_info = user.add_xp(XPCalculator.task_completed())
        user.update_streak()

        checker = AchievementChecker(user)
        achievements_unlocked = checker.check_all()

        # Generate card for completing task
        # For quick completions, limit max rarity to uncommon
        task_age_minutes = (datetime.utcnow() - task.created_at).total_seconds() / 60
        skip_time_check = should_skip_time_check_for_card(user_id)
        is_quick_completion = (
            not skip_time_check and task_age_minutes < MIN_TASK_TIME_FOR_CARD
        )

        try:
            card_service = CardService()
            difficulty = task.difficulty or "medium"
            # Quick completions get max_rarity=UNCOMMON
            max_rarity = CardRarity.UNCOMMON if is_quick_completion else None
            generated_card = card_service.generate_card_for_task(
                user_id, task.id, task.title, difficulty, max_rarity=max_rarity
            )

            # Award campaign energy for task completion
            card_service.add_energy(user_id, 1)
            # Award companion XP for task completion
            companion_xp_result = card_service.award_companion_xp(user_id, 5)
        except Exception:
            # Card generation is optional, don't fail task completion
            companion_xp_result = None
            pass

        db.session.commit()

        # Award cards to shared assignees who completed the task
        try:
            completed_shares = (
                SharedTask.query.filter_by(
                    task_id=task.id,
                    status=SharedTaskStatus.COMPLETED.value,
                )
                .filter(SharedTask.reward_card_id.is_(None))
                .all()
            )

            for share in completed_shares:
                try:
                    card_service = CardService()
                    difficulty = task.difficulty or "medium"
                    reward_card = card_service.generate_card_for_task(
                        share.assignee_id, task.id, task.title, difficulty
                    )
                    if reward_card:
                        share.reward_card_id = reward_card.id
                except Exception:
                    pass

            if completed_shares:
                db.session.commit()
        except Exception:
            pass

    response_data = {"task": task.to_dict()}
    if xp_info:
        response_data["xp_earned"] = xp_info["xp_earned"]
        response_data["achievements_unlocked"] = [
            a.to_dict() for a in achievements_unlocked
        ]
        # Grant level-up rewards
        if xp_info.get("level_up"):
            response_data["level_up"] = True
            response_data["new_level"] = xp_info["new_level"]
            try:
                from app.services.level_service import LevelService

                reward_summary = LevelService().grant_level_rewards(
                    user_id, xp_info["new_level"]
                )
                if reward_summary.get("granted"):
                    response_data["level_rewards"] = reward_summary["rewards"]
            except Exception:
                pass
            try:
                unlock_info = CardService().check_genre_unlock(user_id)
                if unlock_info:
                    response_data["genre_unlock_available"] = unlock_info
            except Exception:
                pass
    if generated_card:
        response_data["card_earned"] = generated_card.to_dict()
        # Add quick completion flag and message
        if is_quick_completion:
            response_data["quick_completion"] = True
            response_data["quick_completion_message"] = (
                "Задача выполнена слишком быстро. "
                "Максимальная редкость карты за такую задачу — Необычная."
            )
    if (
        task_just_completed
        and companion_xp_result
        and companion_xp_result.get("success")
    ):
        response_data["companion_xp"] = {
            "xp_earned": companion_xp_result.get("xp_earned", 5),
            "card_name": companion_xp_result.get("card_name"),
            "card_emoji": companion_xp_result.get("card_emoji"),
            "level_up": companion_xp_result.get("level_up", False),
            "new_level": companion_xp_result.get("new_level"),
        }

    # Increment guild quest progress for task completion
    if task_just_completed:
        try:
            from app.models.guild import GuildMember
            from app.services.guild_service import GuildService as GS

            membership = GuildMember.query.filter_by(user_id=user_id).first()
            if membership:
                gs = GS()
                gs.increment_quest_progress(
                    membership.guild_id, "tasks_completed", user_id=user_id
                )
                if generated_card:
                    gs.increment_quest_progress(
                        membership.guild_id, "cards_earned", user_id=user_id
                    )
        except Exception:
            pass

    return success_response(response_data)


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id: int):
    """Delete a task and all its subtasks."""
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    # Delete related shared_tasks first (ORM doesn't cascade automatically)
    from app.models.shared_task import SharedTask

    SharedTask.query.filter_by(task_id=task_id).delete()

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
        mood_value = None
        energy_value = None
    else:
        strategy = mood_check.decomposition_strategy
        mood_value = mood_check.mood
        energy_value = mood_check.energy

    # Count existing subtasks
    existing_subtasks = Subtask.query.filter_by(task_id=task.id).all()
    existing_count = len(existing_subtasks)

    # Decompose task with type context and user state
    decomposer = AIDecomposer()
    result = decomposer.decompose_task(
        task.title,
        task.description,
        strategy,
        task.task_type,
        mood=mood_value,
        energy=energy_value,
        existing_subtasks_count=existing_count,
        user_id=user_id,
    )

    # Handle no_new_steps response
    if result.get("no_new_steps"):
        return success_response(
            {
                "subtasks": [s.to_dict() for s in existing_subtasks],
                "strategy": strategy,
                "no_new_steps": True,
                "message": result.get(
                    "reason", "Задача уже разбита на достаточное количество шагов"
                ),
            }
        )

    # Clear existing subtasks and create new ones
    Subtask.query.filter_by(task_id=task.id).delete()

    # Create subtasks
    subtasks = []
    for subtask_info in result["subtasks"]:
        subtask = Subtask(
            task_id=task.id,
            title=subtask_info["title"],
            estimated_minutes=subtask_info["estimated_minutes"],
            order=subtask_info["order"],
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

    # If already notified, don't show again
    if log.notified:
        return success_response(
            {
                "has_postponed": False,
                "tasks_postponed": 0,
                "priority_changes": [],
                "message": None,
            }
        )

    # Mark as notified (will only show once)
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

    is_shared_assignee = False
    if not subtask:
        # Check if user is a shared assignee for this subtask's task
        subtask = Subtask.query.filter_by(id=subtask_id).first()
        if subtask:
            shared = SharedTask.query.filter_by(
                task_id=subtask.task_id,
                assignee_id=user_id,
                status=SharedTaskStatus.ACCEPTED.value,
            ).first()
            if shared:
                is_shared_assignee = True
            else:
                subtask = None

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

    # Update parent task status (skip auto-completion for shared assignees)
    if not is_shared_assignee:
        subtask.task.update_status_from_subtasks()

    db.session.commit()

    # Shared assignees don't earn XP or cards
    if is_shared_assignee:
        return success_response({"subtask": subtask.to_dict()})

    # Calculate XP if completed
    xp_info = None
    achievements_unlocked = []
    generated_card = None

    was_completed = (
        old_status != SubtaskStatus.COMPLETED.value
        and subtask.status == SubtaskStatus.COMPLETED.value
    )

    if was_completed:
        user = User.query.get(user_id)
        xp_earned = XPCalculator.subtask_completed()
        task = subtask.task

        # Bonus XP if all subtasks completed (task completed)
        task_just_completed = task.status == TaskStatus.COMPLETED.value
        is_quick_completion = False
        if task_just_completed:
            xp_earned += XPCalculator.task_completed()

            # Generate card for completing task
            # For quick completions, limit max rarity to uncommon
            task_age_minutes = (
                datetime.utcnow() - task.created_at
            ).total_seconds() / 60
            skip_time_check = should_skip_time_check_for_card(user_id)
            is_quick_completion = (
                not skip_time_check and task_age_minutes < MIN_TASK_TIME_FOR_CARD
            )

            try:
                card_service = CardService()
                difficulty = task.difficulty or "medium"
                # Quick completions get max_rarity=UNCOMMON
                max_rarity = CardRarity.UNCOMMON if is_quick_completion else None
                generated_card = card_service.generate_card_for_task(
                    user_id, task.id, task.title, difficulty, max_rarity=max_rarity
                )
                # Award companion XP based on difficulty
                companion_xp_amount = COMPANION_XP_BY_DIFFICULTY.get(difficulty, 5)
                companion_xp_result = card_service.award_companion_xp(
                    user_id, companion_xp_amount
                )
            except Exception:
                # Card generation is optional, don't fail task completion
                companion_xp_result = None
                pass

        xp_info = user.add_xp(xp_earned)
        user.update_streak()

        # Check streak milestones
        streak_milestone = None
        try:
            streak_milestone = StreakService().check_and_grant_milestone(user)
        except Exception:
            pass

        checker = AchievementChecker(user)
        achievements_unlocked = checker.check_all()

        try:
            UserActivityLog.log(
                user_id=user_id,
                action_type="subtask_complete",
                entity_type="subtask",
                entity_id=subtask.id,
            )
            if task_just_completed:
                UserActivityLog.log(
                    user_id=user_id,
                    action_type="task_complete",
                    action_details=f"Completed task: {task.title[:100]}",
                    entity_type="task",
                    entity_id=task.id,
                )
        except Exception:
            pass

        # Log friend activities for notifications
        try:
            if xp_info and xp_info.get("level_up"):
                FriendActivityLog.create(
                    user_id, "level_up", {"level": xp_info["new_level"]}
                )
            if streak_milestone:
                FriendActivityLog.create(
                    user_id,
                    "streak_milestone",
                    {"streak_days": streak_milestone["milestone_days"]},
                )
        except Exception:
            pass

        db.session.commit()

        # Award cards to shared assignees who completed the task
        if task_just_completed:
            try:
                completed_shares = (
                    SharedTask.query.filter_by(
                        task_id=task.id,
                        status=SharedTaskStatus.COMPLETED.value,
                    )
                    .filter(SharedTask.reward_card_id.is_(None))
                    .all()
                )

                for share in completed_shares:
                    try:
                        cs = CardService()
                        diff = task.difficulty or "medium"
                        reward_card = cs.generate_card_for_task(
                            share.assignee_id, task.id, task.title, diff
                        )
                        if reward_card:
                            share.reward_card_id = reward_card.id
                    except Exception:
                        pass

                if completed_shares:
                    db.session.commit()
            except Exception:
                pass

    response_data = {"subtask": subtask.to_dict()}
    if xp_info:
        response_data["xp_earned"] = xp_info["xp_earned"]
        response_data["achievements_unlocked"] = [
            a.to_dict() for a in achievements_unlocked
        ]
    if generated_card:
        response_data["card_earned"] = generated_card.to_dict()
        # Add quick completion flag and message
        if is_quick_completion:
            response_data["quick_completion"] = True
            response_data["quick_completion_message"] = (
                "Задача выполнена слишком быстро. "
                "Максимальная редкость карты за такую задачу — Необычная."
            )
    if was_completed and task_just_completed:
        try:
            if companion_xp_result and companion_xp_result.get("success"):
                response_data["companion_xp"] = {
                    "xp_earned": companion_xp_result.get("xp_earned", 5),
                    "card_name": companion_xp_result.get("card_name"),
                    "card_emoji": companion_xp_result.get("card_emoji"),
                    "level_up": companion_xp_result.get("level_up", False),
                    "new_level": companion_xp_result.get("new_level"),
                }
        except NameError:
            pass

    if streak_milestone:
        response_data["streak_milestone"] = streak_milestone

    # Increment guild quest progress for subtask → task completion
    if task_just_completed:
        try:
            from app.models.guild import GuildMember
            from app.services.guild_service import GuildService as GS

            membership = GuildMember.query.filter_by(user_id=user_id).first()
            if membership:
                gs = GS()
                gs.increment_quest_progress(
                    membership.guild_id, "tasks_completed", user_id=user_id
                )
                if generated_card:
                    gs.increment_quest_progress(
                        membership.guild_id, "cards_earned", user_id=user_id
                    )
        except Exception:
            pass

    return success_response(response_data)


@api_bp.route("/tasks/suggestions", methods=["GET"])
@jwt_required()
def get_task_suggestions():
    """
    Get task suggestions based on available time.

    Query params:
    - available_minutes: how much time the user has (required)
    - include_subtasks: whether to include individual subtasks (default: true)

    Returns tasks/subtasks that fit within the available time,
    sorted by priority and best fit.
    """
    user_id = int(get_jwt_identity())

    available_minutes = request.args.get("available_minutes", type=int)
    if not available_minutes or available_minutes < 5:
        return validation_error({"available_minutes": "Must be at least 5 minutes"})

    include_subtasks = request.args.get("include_subtasks", "true").lower() != "false"

    # Get user profile for preferences
    user_profile = UserProfile.query.filter_by(user_id=user_id).first()
    favorite_types = user_profile.favorite_task_types if user_profile else None
    current_time_slot = get_current_time_slot()
    today = date.today()

    suggestions = []

    # Get incomplete tasks with subtasks
    # Only tasks with preferred_time set (marked for "free time" suggestions)
    tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.status != TaskStatus.COMPLETED.value,
        Task.preferred_time.isnot(None),
    ).all()

    for task in tasks:
        task_score = calculate_task_score(
            task, current_time_slot, favorite_types, today
        )

        # Check if task has incomplete subtasks
        incomplete_subtasks = [
            s for s in task.subtasks if s.status != SubtaskStatus.COMPLETED.value
        ]

        if incomplete_subtasks and include_subtasks:
            # Calculate total remaining time for this task
            total_remaining = sum(s.estimated_minutes for s in incomplete_subtasks)

            # If all subtasks fit, suggest the whole task
            if total_remaining <= available_minutes:
                suggestions.append(
                    {
                        "type": "task",
                        "task_id": task.id,
                        "task_title": task.title,
                        "priority": task.priority,
                        "estimated_minutes": total_remaining,
                        "subtasks_count": len(incomplete_subtasks),
                        "score": task_score + 50,  # Bonus for completing full task
                        "fit_quality": (
                            "perfect"
                            if total_remaining >= available_minutes * 0.8
                            else "good"
                        ),
                    }
                )
            else:
                # Find subtasks that fit
                fitting_subtasks = []
                remaining_time = available_minutes

                # Sort subtasks by order
                sorted_subtasks = sorted(incomplete_subtasks, key=lambda s: s.order)

                for subtask in sorted_subtasks:
                    if subtask.estimated_minutes <= remaining_time:
                        fitting_subtasks.append(
                            {
                                "subtask_id": subtask.id,
                                "title": subtask.title,
                                "estimated_minutes": subtask.estimated_minutes,
                            }
                        )
                        remaining_time -= subtask.estimated_minutes

                if fitting_subtasks:
                    total_fitting_time = sum(
                        s["estimated_minutes"] for s in fitting_subtasks
                    )
                    suggestions.append(
                        {
                            "type": "subtasks",
                            "task_id": task.id,
                            "task_title": task.title,
                            "priority": task.priority,
                            "subtasks": fitting_subtasks,
                            "estimated_minutes": total_fitting_time,
                            "score": task_score + len(fitting_subtasks) * 5,
                            "fit_quality": (
                                "perfect"
                                if total_fitting_time >= available_minutes * 0.8
                                else "partial"
                            ),
                        }
                    )

        elif not task.subtasks:
            # Task without subtasks - estimate based on priority
            estimated = (
                30
                if task.priority == "high"
                else 20 if task.priority == "medium" else 15
            )

            if estimated <= available_minutes:
                suggestions.append(
                    {
                        "type": "task",
                        "task_id": task.id,
                        "task_title": task.title,
                        "priority": task.priority,
                        "estimated_minutes": estimated,
                        "subtasks_count": 0,
                        "score": task_score,
                        "fit_quality": "estimated",
                    }
                )

    # Sort by score (highest first)
    suggestions.sort(key=lambda x: (-x["score"], x["estimated_minutes"]))

    # Limit to top 5 suggestions
    suggestions = suggestions[:5]

    return success_response(
        {
            "suggestions": suggestions,
            "available_minutes": available_minutes,
            "suggestions_count": len(suggestions),
        }
    )


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
