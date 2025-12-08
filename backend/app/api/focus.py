"""Focus session API endpoints."""

from datetime import date, datetime

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from app import db
from app.api import api_bp
from app.models import FocusSession, Subtask, Task, User
from app.models.focus_session import FocusSessionStatus
from app.models.subtask import SubtaskStatus
from app.services import AchievementChecker, XPCalculator
from app.utils import conflict, not_found, success_response, validation_error


@api_bp.route("/focus/start", methods=["POST"])
@jwt_required()
def start_focus_session():
    """
    Start a new focus session.

    Request body:
    {
        "subtask_id": 1,
        "planned_duration_minutes": 25
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return validation_error({"body": "Request body is required"})

    # Check for existing active session
    active_session = FocusSession.query.filter_by(
        user_id=user_id, status=FocusSessionStatus.ACTIVE.value
    ).first()

    if active_session:
        return conflict("You already have an active focus session")

    # Validate subtask (optional)
    subtask_id = data.get("subtask_id")
    if subtask_id:
        subtask = (
            Subtask.query.join(Task)
            .filter(Subtask.id == subtask_id, Task.user_id == user_id)
            .first()
        )

        if not subtask:
            return not_found("Subtask not found")
    else:
        subtask = None

    # Validate duration
    try:
        duration = int(data.get("planned_duration_minutes", 25))
        duration = max(5, min(120, duration))
    except (ValueError, TypeError):
        duration = 25

    # Create session
    session = FocusSession(
        user_id=user_id, subtask_id=subtask_id, planned_duration_minutes=duration
    )

    # Update subtask status if linked
    if subtask and subtask.status == SubtaskStatus.PENDING.value:
        subtask.status = SubtaskStatus.IN_PROGRESS.value

    db.session.add(session)
    db.session.commit()

    return success_response({"session": session.to_dict()}, status_code=201)


@api_bp.route("/focus/active", methods=["GET"])
@jwt_required()
def get_active_session():
    """Get the current active focus session."""
    user_id = int(get_jwt_identity())

    session = FocusSession.query.filter_by(
        user_id=user_id, status=FocusSessionStatus.ACTIVE.value
    ).first()

    # Also check for paused sessions
    if not session:
        session = FocusSession.query.filter_by(
            user_id=user_id, status=FocusSessionStatus.PAUSED.value
        ).first()

    return success_response({"session": session.to_dict() if session else None})


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
    if complete_subtask and session.subtask:
        xp_earned += XPCalculator.subtask_completed()

        # Check if task is now complete
        session.subtask.task.update_status_from_subtasks()
        if session.subtask.task.status == "completed":
            xp_earned += XPCalculator.task_completed()

    xp_info = user.add_xp(xp_earned)
    user.update_streak()

    # Check achievements
    checker = AchievementChecker(user)
    achievements_unlocked = checker.check_all()

    db.session.commit()

    return success_response(
        {
            "session": session.to_dict(),
            "xp_earned": xp_info["xp_earned"],
            "achievements_unlocked": [a.to_dict() for a in achievements_unlocked],
        }
    )


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
