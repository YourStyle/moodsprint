"""Shared task API endpoints."""

import logging
from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.models import Friendship, SharedTask, SharedTaskStatus, Task, User
from app.models.task import TaskStatus
from app.utils import not_found, success_response, validation_error
from app.utils.notifications import send_telegram_message

logger = logging.getLogger(__name__)

shared_tasks_bp = Blueprint("shared_tasks", __name__, url_prefix="/api/v1/tasks")


# --- Task Sharing Endpoints ---


@shared_tasks_bp.route("/<int:task_id>/share", methods=["POST"])
@jwt_required()
def share_task(task_id: int):
    """
    Share a task with a friend.

    Request body:
    {
        "friend_id": 123,
        "message": "Optional message"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    friend_id = data.get("friend_id")
    if not friend_id:
        return validation_error({"friend_id": "Friend ID is required"})

    # Verify task ownership
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    # Verify friendship exists (accepted)
    friendship = Friendship.query.filter(
        db.or_(
            db.and_(
                Friendship.user_id == user_id,
                Friendship.friend_id == friend_id,
            ),
            db.and_(
                Friendship.user_id == friend_id,
                Friendship.friend_id == user_id,
            ),
        ),
        Friendship.status == "accepted",
    ).first()
    if not friendship:
        return validation_error({"friend_id": "Not friends with this user"})

    # Check if already shared
    existing = SharedTask.query.filter_by(
        task_id=task_id, assignee_id=friend_id
    ).first()
    if existing:
        return validation_error({"friend_id": "Task already shared with this user"})

    shared = SharedTask(
        task_id=task_id,
        owner_id=user_id,
        assignee_id=friend_id,
        message=data.get("message", "").strip() or None,
    )
    db.session.add(shared)
    db.session.commit()

    # Send Telegram notification
    try:
        owner = User.query.get(user_id)
        friend = User.query.get(friend_id)
        if friend and friend.telegram_id:
            owner_name = owner.first_name or "Друг"
            text = (
                f"📋 <b>{owner_name}</b> поделился задачей с тобой!\n\n"
                f"<b>{task.title}</b>"
            )
            if shared.message:
                text += f"\n\n💬 {shared.message}"
            send_telegram_message(friend.telegram_id, text)
    except Exception:
        pass

    return success_response({"shared_task": shared.to_dict()}, status_code=201)


@shared_tasks_bp.route("/shared", methods=["GET"])
@jwt_required()
def get_shared_with_me():
    """
    Get tasks shared with the current user.

    Query params:
    - status: filter by status (pending, accepted, declined, completed)
    """
    user_id = int(get_jwt_identity())
    status = request.args.get("status")

    query = SharedTask.query.filter_by(assignee_id=user_id)
    if status and status in [s.value for s in SharedTaskStatus]:
        query = query.filter_by(status=status)
    else:
        # Exclude declined by default
        query = query.filter(SharedTask.status != SharedTaskStatus.DECLINED.value)
        # Exclude fully done shared tasks (assignee pinged + owner completed the task)
        query = query.filter(
            ~db.and_(
                SharedTask.status == SharedTaskStatus.COMPLETED.value,
                SharedTask.task.has(Task.status == TaskStatus.COMPLETED.value),
            )
        )

    shared_tasks = query.order_by(SharedTask.created_at.desc()).all()
    return success_response(
        {"shared_tasks": [s.to_dict(include_task=True) for s in shared_tasks]}
    )


@shared_tasks_bp.route("/<int:task_id>/shared", methods=["GET"])
@jwt_required()
def get_task_shares(task_id: int):
    """Get who a task has been shared with (for the owner)."""
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    shares = SharedTask.query.filter_by(task_id=task_id).all()
    return success_response({"shares": [s.to_dict() for s in shares]})


@shared_tasks_bp.route("/shared/<int:shared_id>/accept", methods=["POST"])
@jwt_required()
def accept_shared_task(shared_id: int):
    """Accept a shared task."""
    user_id = int(get_jwt_identity())

    shared = SharedTask.query.filter_by(
        id=shared_id,
        assignee_id=user_id,
        status=SharedTaskStatus.PENDING.value,
    ).first()
    if not shared:
        return not_found("Shared task not found")

    shared.status = SharedTaskStatus.ACCEPTED.value
    shared.accepted_at = datetime.utcnow()
    db.session.commit()

    return success_response({"shared_task": shared.to_dict()})


@shared_tasks_bp.route("/shared/<int:shared_id>/decline", methods=["POST"])
@jwt_required()
def decline_shared_task(shared_id: int):
    """Decline a shared task."""
    user_id = int(get_jwt_identity())

    shared = SharedTask.query.filter_by(
        id=shared_id,
        assignee_id=user_id,
        status=SharedTaskStatus.PENDING.value,
    ).first()
    if not shared:
        return not_found("Shared task not found")

    shared.status = SharedTaskStatus.DECLINED.value
    db.session.commit()

    # Notify owner
    try:
        assignee = User.query.get(user_id)
        owner = User.query.get(shared.owner_id)
        if owner and owner.telegram_id:
            name = assignee.first_name or "Друг"
            send_telegram_message(
                owner.telegram_id,
                f"😔 <b>{name}</b> отклонил задачу «{shared.task.title}»",
            )
    except Exception:
        pass

    return success_response({"shared_task": shared.to_dict()})


@shared_tasks_bp.route("/shared/<int:shared_id>/ping", methods=["POST"])
@jwt_required()
def ping_shared_task(shared_id: int):
    """Notify the task owner that the assignee has finished."""
    user_id = int(get_jwt_identity())

    shared = SharedTask.query.filter_by(
        id=shared_id,
        assignee_id=user_id,
        status=SharedTaskStatus.ACCEPTED.value,
    ).first()
    if not shared:
        return not_found("Shared task not found")

    shared.status = SharedTaskStatus.COMPLETED.value
    shared.completed_at = datetime.utcnow()
    db.session.commit()

    # Notify owner via Telegram
    try:
        assignee = User.query.get(user_id)
        owner = User.query.get(shared.owner_id)
        if owner and owner.telegram_id:
            name = assignee.first_name or "Друг"
            send_telegram_message(
                owner.telegram_id,
                f"✅ <b>{name}</b> выполнил задачу «{shared.task.title}»!",
            )
    except Exception:
        pass

    return success_response({"shared_task": shared.to_dict()})


@shared_tasks_bp.route("/shared/rewards", methods=["GET"])
@jwt_required()
def get_shared_task_rewards():
    """Get unshown card rewards from completed shared tasks."""
    user_id = int(get_jwt_identity())

    pending = (
        SharedTask.query.filter_by(
            assignee_id=user_id,
            reward_shown=False,
        )
        .filter(SharedTask.reward_card_id.isnot(None))
        .all()
    )

    rewards = []
    for s in pending:
        if s.reward_card:
            rewards.append(
                {
                    "shared_id": s.id,
                    "card": s.reward_card.to_dict(),
                    "task_title": s.task.title if s.task else None,
                    "owner_name": s.owner.first_name if s.owner else None,
                }
            )

    return success_response({"rewards": rewards})


@shared_tasks_bp.route("/shared/<int:shared_id>/reward-shown", methods=["POST"])
@jwt_required()
def mark_shared_reward_shown(shared_id: int):
    """Mark a shared task reward as shown."""
    user_id = int(get_jwt_identity())
    shared = SharedTask.query.filter_by(id=shared_id, assignee_id=user_id).first()
    if shared:
        shared.reward_shown = True
        db.session.commit()
    return success_response({})
