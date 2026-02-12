"""Focus session API endpoints."""

from datetime import date, datetime

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from app import db
from app.api import api_bp
from app.models import FocusSession, Subtask, Task, User
from app.models.card import CardRarity
from app.models.focus_session import FocusSessionStatus
from app.models.subtask import SubtaskStatus
from app.models.task import TaskStatus
from app.services import AchievementChecker, XPCalculator
from app.services.card_service import CardService
from app.utils import conflict, not_found, success_response, validation_error


@api_bp.route("/focus/start", methods=["POST"])
@jwt_required()
def start_focus_session():
    """
    Start a new focus session.

    Request body:
    {
        "subtask_id": 1,  // optional - start focus on a subtask
        "task_id": 1,     // optional - start focus on a task directly
        "planned_duration_minutes": 25
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return validation_error({"body": "Request body is required"})

    # Check if this specific task/subtask already has an active session
    subtask_id = data.get("subtask_id")
    task_id = data.get("task_id")

    if subtask_id:
        existing = FocusSession.query.filter(
            FocusSession.user_id == user_id,
            FocusSession.subtask_id == subtask_id,
            FocusSession.status.in_(
                [FocusSessionStatus.ACTIVE.value, FocusSessionStatus.PAUSED.value]
            ),
        ).first()
        if existing:
            return conflict("This subtask already has an active focus session")
    elif task_id:
        existing = FocusSession.query.filter(
            FocusSession.user_id == user_id,
            FocusSession.task_id == task_id,
            FocusSession.subtask_id.is_(None),
            FocusSession.status.in_(
                [FocusSessionStatus.ACTIVE.value, FocusSessionStatus.PAUSED.value]
            ),
        ).first()
        if existing:
            return conflict("This task already has an active focus session")

    # Validate subtask (optional)
    subtask_id = data.get("subtask_id")
    subtask = None
    if subtask_id:
        subtask = (
            Subtask.query.join(Task)
            .filter(Subtask.id == subtask_id, Task.user_id == user_id)
            .first()
        )

        if not subtask:
            return not_found("Subtask not found")

    # Validate task (optional)
    task_id = data.get("task_id")
    task = None
    if task_id and not subtask_id:
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return not_found("Task not found")

    # Validate duration
    try:
        duration = int(data.get("planned_duration_minutes", 25))
        duration = max(5, min(120, duration))
    except (ValueError, TypeError):
        duration = 25

    # Create session
    session = FocusSession(
        user_id=user_id,
        subtask_id=subtask_id,
        task_id=task_id if task else None,
        planned_duration_minutes=duration,
    )

    # Update subtask status if linked
    if subtask and subtask.status == SubtaskStatus.PENDING.value:
        subtask.status = SubtaskStatus.IN_PROGRESS.value

    # Update task status if linked directly
    if task and task.status == "pending":
        task.status = "in_progress"

    db.session.add(session)
    db.session.commit()

    return success_response({"session": session.to_dict()}, status_code=201)


@api_bp.route("/focus/active", methods=["GET"])
@jwt_required()
def get_active_session():
    """Get all active focus sessions."""
    user_id = int(get_jwt_identity())

    sessions = FocusSession.query.filter(
        FocusSession.user_id == user_id,
        FocusSession.status.in_(
            [FocusSessionStatus.ACTIVE.value, FocusSessionStatus.PAUSED.value]
        ),
    ).all()

    return success_response(
        {
            "sessions": [s.to_dict() for s in sessions],
            # Keep backward compatibility
            "session": sessions[0].to_dict() if sessions else None,
        }
    )


@api_bp.route("/focus/complete", methods=["POST"])
@jwt_required()
def complete_focus_session():
    """
    Complete a focus session.

    Request body:
    {
        "session_id": 1,
        "complete_subtask": true
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    session_id = data.get("session_id")

    # Find session
    if session_id:
        session = FocusSession.query.filter_by(id=session_id, user_id=user_id).first()
    else:
        # Get active session
        session = FocusSession.query.filter(
            FocusSession.user_id == user_id,
            FocusSession.status.in_(
                [FocusSessionStatus.ACTIVE.value, FocusSessionStatus.PAUSED.value]
            ),
        ).first()

    if not session:
        return not_found("No active session found")

    if session.status not in [
        FocusSessionStatus.ACTIVE.value,
        FocusSessionStatus.PAUSED.value,
    ]:
        return conflict("Session is not active")

    complete_subtask = data.get("complete_subtask", False)
    session.complete(complete_subtask=complete_subtask)

    # Calculate XP
    user = User.query.get(user_id)
    xp_earned = XPCalculator.focus_session_completed(
        session.actual_duration_minutes or 0
    )

    # Add XP for subtask completion if applicable
    generated_card = None
    is_quick_completion = False

    if complete_subtask and session.subtask:
        xp_earned += XPCalculator.subtask_completed()

        # Check if task is now complete
        task = session.subtask.task
        old_status = task.status
        task.update_status_from_subtasks()

        if (
            task.status == TaskStatus.COMPLETED.value
            and old_status != TaskStatus.COMPLETED.value
        ):
            xp_earned += XPCalculator.task_completed()

            # Generate card for task completion
            # Check if task was completed too quickly (anti-cheat)
            from app.api.tasks import (
                MIN_TASK_TIME_FOR_CARD,
                should_skip_time_check_for_card,
            )

            task_age_minutes = (
                datetime.utcnow() - task.created_at
            ).total_seconds() / 60
            skip_time_check = should_skip_time_check_for_card(user_id)
            is_quick_completion = (
                not skip_time_check and task_age_minutes < MIN_TASK_TIME_FOR_CARD
            )

            card_service = CardService()
            max_rarity = CardRarity.UNCOMMON if is_quick_completion else None
            generated_card = card_service.generate_card_for_task(
                user_id=user_id,
                task_id=task.id,
                task_title=task.title,
                difficulty=task.difficulty,
                max_rarity=max_rarity,
            )

    xp_info = user.add_xp(xp_earned)
    user.update_streak()

    # Check achievements
    checker = AchievementChecker(user)
    achievements_unlocked = checker.check_all()

    # Award campaign energy for focus sessions 20+ min
    companion_xp_result = None
    try:
        from app.services.card_service import CardService

        card_service = CardService()
        actual_minutes = session.actual_duration_minutes or 0
        if actual_minutes >= 20:
            card_service.add_energy(user_id, 1)
            # Award companion XP
            companion_xp_result = card_service.award_companion_xp(user_id, 10)
    except Exception:
        pass

    db.session.commit()

    response_data = {
        "session": session.to_dict(),
        "xp_earned": xp_info["xp_earned"],
        "achievements_unlocked": [a.to_dict() for a in achievements_unlocked],
    }

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
            from app.services.card_service import CardService

            unlock_info = CardService().check_genre_unlock(user_id)
            if unlock_info:
                response_data["genre_unlock_available"] = unlock_info
        except Exception:
            pass

    if companion_xp_result and companion_xp_result.get("success"):
        response_data["companion_xp"] = companion_xp_result

    if generated_card:
        response_data["card_earned"] = generated_card.to_dict()
        if is_quick_completion:
            response_data["quick_completion"] = True
            response_data["quick_completion_message"] = (
                "Задача выполнена слишком быстро. "
                "Максимальная редкость карты за такую задачу — Необычная."
            )

    return success_response(response_data)


@api_bp.route("/focus/cancel", methods=["POST"])
@jwt_required()
def cancel_focus_session():
    """
    Cancel a focus session.

    Request body:
    {
        "session_id": 1,  // optional, cancels active session if not provided
        "reason": "interrupted"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    session_id = data.get("session_id")

    if session_id:
        session = FocusSession.query.filter_by(id=session_id, user_id=user_id).first()
    else:
        session = FocusSession.query.filter(
            FocusSession.user_id == user_id,
            FocusSession.status.in_(
                [FocusSessionStatus.ACTIVE.value, FocusSessionStatus.PAUSED.value]
            ),
        ).first()

    if not session:
        return not_found("No active session found")

    session.cancel()
    db.session.commit()

    return success_response({"session": session.to_dict()})


@api_bp.route("/focus/pause", methods=["POST"])
@jwt_required()
def pause_focus_session():
    """Pause the active focus session."""
    user_id = int(get_jwt_identity())

    session = FocusSession.query.filter_by(
        user_id=user_id, status=FocusSessionStatus.ACTIVE.value
    ).first()

    if not session:
        return not_found("No active session found")

    session.pause()
    db.session.commit()

    return success_response({"session": session.to_dict()})


@api_bp.route("/focus/resume", methods=["POST"])
@jwt_required()
def resume_focus_session():
    """Resume a paused focus session."""
    user_id = int(get_jwt_identity())

    session = FocusSession.query.filter_by(
        user_id=user_id, status=FocusSessionStatus.PAUSED.value
    ).first()

    if not session:
        return not_found("No paused session found")

    session.resume()
    db.session.commit()

    return success_response({"session": session.to_dict()})


@api_bp.route("/focus/history", methods=["GET"])
@jwt_required()
def get_focus_history():
    """
    Get focus session history.

    Query params:
    - limit: max results (default 20)
    - offset: pagination offset (default 0)
    """
    user_id = int(get_jwt_identity())

    query = FocusSession.query.filter(
        FocusSession.user_id == user_id,
        FocusSession.status.in_(
            [FocusSessionStatus.COMPLETED.value, FocusSessionStatus.CANCELLED.value]
        ),
    ).order_by(FocusSession.started_at.desc())

    total = query.count()

    # Calculate total minutes
    total_minutes = (
        db.session.query(
            func.coalesce(func.sum(FocusSession.actual_duration_minutes), 0)
        )
        .filter(
            FocusSession.user_id == user_id,
            FocusSession.status == FocusSessionStatus.COMPLETED.value,
        )
        .scalar()
    )

    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))

    sessions = query.offset(offset).limit(limit).all()

    return success_response(
        {
            "sessions": [s.to_dict() for s in sessions],
            "total": total,
            "total_minutes": total_minutes or 0,
        }
    )


@api_bp.route("/focus/today", methods=["GET"])
@jwt_required()
def get_today_focus():
    """Get today's focus statistics."""
    user_id = int(get_jwt_identity())

    today_start = datetime.combine(date.today(), datetime.min.time())

    # Today's completed sessions
    today_sessions = FocusSession.query.filter(
        FocusSession.user_id == user_id,
        FocusSession.status == FocusSessionStatus.COMPLETED.value,
        FocusSession.started_at >= today_start,
    ).all()

    total_minutes = sum(s.actual_duration_minutes or 0 for s in today_sessions)

    return success_response(
        {
            "sessions_count": len(today_sessions),
            "total_minutes": total_minutes,
            "sessions": [s.to_dict() for s in today_sessions],
        }
    )


@api_bp.route("/focus/extend", methods=["POST"])
@jwt_required()
def extend_focus_session():
    """
    Extend the active focus session duration.

    Request body:
    {
        "minutes": 10  // minutes to add
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    minutes = data.get("minutes", 10)
    try:
        minutes = int(minutes)
        minutes = max(1, min(60, minutes))  # 1-60 minutes
    except (ValueError, TypeError):
        minutes = 10

    # Find active or paused session
    session = FocusSession.query.filter(
        FocusSession.user_id == user_id,
        FocusSession.status.in_(
            [FocusSessionStatus.ACTIVE.value, FocusSessionStatus.PAUSED.value]
        ),
    ).first()

    if not session:
        return not_found("No active session found")

    # Extend duration
    session.planned_duration_minutes += minutes
    db.session.commit()

    return success_response({"session": session.to_dict()})
