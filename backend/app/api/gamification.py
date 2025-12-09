"""Gamification API endpoints."""

from datetime import date, datetime

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from app import db
from app.api import api_bp
from app.models import (
    Achievement,
    FocusSession,
    MoodCheck,
    Subtask,
    Task,
    User,
    UserAchievement,
)
from app.models.achievement import get_level_name
from app.models.focus_session import FocusSessionStatus
from app.models.subtask import SubtaskStatus
from app.models.task import TaskStatus
from app.utils import success_response


@api_bp.route("/user/stats", methods=["GET"])
@jwt_required()
def get_user_stats():
    """Get user statistics and progress."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    # Total completed tasks
    total_tasks = Task.query.filter_by(
        user_id=user_id, status=TaskStatus.COMPLETED.value
    ).count()

    # Total completed subtasks
    total_subtasks = (
        db.session.query(func.count(Subtask.id))
        .join(Task)
        .filter(
            Task.user_id == user_id, Subtask.status == SubtaskStatus.COMPLETED.value
        )
        .scalar()
    )

    # Total focus minutes
    total_focus_minutes = (
        db.session.query(
            func.coalesce(func.sum(FocusSession.actual_duration_minutes), 0)
        )
        .filter(
            FocusSession.user_id == user_id,
            FocusSession.status == FocusSessionStatus.COMPLETED.value,
        )
        .scalar()
    )

    # Today's stats
    today_start = datetime.combine(date.today(), datetime.min.time())

    today_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.status == TaskStatus.COMPLETED.value,
        Task.completed_at >= today_start,
    ).count()

    today_subtasks = (
        db.session.query(func.count(Subtask.id))
        .join(Task)
        .filter(
            Task.user_id == user_id,
            Subtask.status == SubtaskStatus.COMPLETED.value,
            Subtask.completed_at >= today_start,
        )
        .scalar()
    )

    today_focus_minutes = (
        db.session.query(
            func.coalesce(func.sum(FocusSession.actual_duration_minutes), 0)
        )
        .filter(
            FocusSession.user_id == user_id,
            FocusSession.status == FocusSessionStatus.COMPLETED.value,
            FocusSession.started_at >= today_start,
        )
        .scalar()
    )

    today_mood_checks = MoodCheck.query.filter(
        MoodCheck.user_id == user_id, MoodCheck.created_at >= today_start
    ).count()

    return success_response(
        {
            "xp": user.xp,
            "level": user.level,
            "level_name": get_level_name(user.level),
            "xp_for_next_level": user.xp_for_next_level,
            "xp_progress_percent": user.xp_progress_percent,
            "streak_days": user.streak_days,
            "longest_streak": user.longest_streak,
            "total_tasks_completed": total_tasks,
            "total_subtasks_completed": total_subtasks or 0,
            "total_focus_minutes": total_focus_minutes or 0,
            "today": {
                "tasks_completed": today_tasks,
                "subtasks_completed": today_subtasks or 0,
                "focus_minutes": today_focus_minutes or 0,
                "mood_checks": today_mood_checks,
            },
        }
    )


@api_bp.route("/achievements", methods=["GET"])
@jwt_required()
def get_all_achievements():
    """Get all available achievements."""
    achievements = Achievement.query.filter_by(is_hidden=False).all()

    return success_response({"achievements": [a.to_dict() for a in achievements]})


@api_bp.route("/user/achievements", methods=["GET"])
@jwt_required()
def get_user_achievements():
    """Get user's achievements with progress."""
    user_id = int(get_jwt_identity())

    # Get all achievements
    all_achievements = Achievement.query.filter_by(is_hidden=False).all()

    # Get user achievements
    user_achievements = {
        ua.achievement_id: ua
        for ua in UserAchievement.query.filter_by(user_id=user_id).all()
    }

    unlocked = []
    in_progress = []

    for achievement in all_achievements:
        user_ach = user_achievements.get(achievement.id)

        if user_ach and user_ach.is_unlocked:
            result = achievement.to_dict()
            result["unlocked_at"] = user_ach.unlocked_at.isoformat()
            result["is_unlocked"] = True
            result["progress"] = user_ach.progress
            unlocked.append(result)
        else:
            result = achievement.to_dict()
            result["progress"] = user_ach.progress if user_ach else 0
            result["is_unlocked"] = False
            in_progress.append(result)

    return success_response({"unlocked": unlocked, "in_progress": in_progress})


@api_bp.route("/user/daily-goals", methods=["GET"])
@jwt_required()
def get_daily_goals():
    """Get daily goals progress."""
    user_id = int(get_jwt_identity())

    today_start = datetime.combine(date.today(), datetime.min.time())

    # Focus minutes goal (60 min)
    focus_minutes = (
        db.session.query(
            func.coalesce(func.sum(FocusSession.actual_duration_minutes), 0)
        )
        .filter(
            FocusSession.user_id == user_id,
            FocusSession.status == FocusSessionStatus.COMPLETED.value,
            FocusSession.started_at >= today_start,
        )
        .scalar()
        or 0
    )

    # Subtasks goal (5 subtasks)
    subtasks_completed = (
        db.session.query(func.count(Subtask.id))
        .join(Task)
        .filter(
            Task.user_id == user_id,
            Subtask.status == SubtaskStatus.COMPLETED.value,
            Subtask.completed_at >= today_start,
        )
        .scalar()
        or 0
    )

    # Mood check goal (1 check)
    mood_checks = MoodCheck.query.filter(
        MoodCheck.user_id == user_id, MoodCheck.created_at >= today_start
    ).count()

    goals = [
        {
            "type": "focus_minutes",
            "title": "Время фокуса",
            "target": 60,
            "current": min(focus_minutes, 60),
            "completed": focus_minutes >= 60,
        },
        {
            "type": "subtasks",
            "title": "Выполнить шаги",
            "target": 5,
            "current": min(subtasks_completed, 5),
            "completed": subtasks_completed >= 5,
        },
        {
            "type": "mood_check",
            "title": "Отметить настроение",
            "target": 1,
            "current": min(mood_checks, 1),
            "completed": mood_checks >= 1,
        },
    ]

    all_completed = all(g["completed"] for g in goals)

    return success_response(
        {
            "goals": goals,
            "all_completed": all_completed,
            "bonus_xp_available": 30 if not all_completed else 0,
        }
    )


@api_bp.route("/daily-bonus", methods=["POST"])
@jwt_required()
def claim_daily_bonus():
    """Claim daily login bonus."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    today = date.today()

    # Check if already claimed today
    if user.last_daily_bonus_date == today:
        return success_response(
            {
                "claimed": False,
                "message": "Бонус уже получен сегодня",
                "next_bonus_at": (
                    datetime.combine(today, datetime.min.time())
                    + __import__("datetime").timedelta(days=1)
                ).isoformat(),
            }
        )

    # Calculate bonus based on streak
    base_bonus = 10
    streak_multiplier = min(user.streak_days, 7)  # Max 7x multiplier
    bonus_xp = base_bonus + (streak_multiplier * 5)  # 10 + (streak * 5)

    # Award bonus
    xp_result = user.add_xp(bonus_xp)
    user.last_daily_bonus_date = today

    db.session.commit()

    return success_response(
        {
            "claimed": True,
            "xp_earned": bonus_xp,
            "streak_bonus": streak_multiplier * 5,
            "streak_days": user.streak_days,
            "total_xp": user.xp,
            "level_up": xp_result["level_up"],
            "new_level": xp_result["new_level"] if xp_result["level_up"] else None,
        }
    )


@api_bp.route("/daily-bonus/status", methods=["GET"])
@jwt_required()
def get_daily_bonus_status():
    """Check if daily bonus is available."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    today = date.today()
    can_claim = user.last_daily_bonus_date != today

    # Calculate potential bonus
    base_bonus = 10
    streak_multiplier = min(user.streak_days, 7)
    potential_bonus = base_bonus + (streak_multiplier * 5)

    return success_response(
        {
            "can_claim": can_claim,
            "potential_xp": potential_bonus if can_claim else 0,
            "streak_days": user.streak_days,
            "streak_multiplier": streak_multiplier,
            "last_claimed": (
                user.last_daily_bonus_date.isoformat()
                if user.last_daily_bonus_date
                else None
            ),
        }
    )


@api_bp.route("/leaderboard", methods=["GET"])
@jwt_required()
def get_leaderboard():
    """
    Get leaderboard.

    Query params:
    - type: weekly or all_time (default: weekly)
    - limit: max results (default 10)
    """
    limit = min(int(request.args.get("limit", 10)), 50)
    leaderboard_type = request.args.get("type", "weekly")

    if leaderboard_type == "weekly":
        # Weekly leaderboard based on XP earned this week
        # TODO: In production, track weekly XP separately using week_start filter
        # week_start = datetime.combine(
        #     date.today() - timedelta(days=date.today().weekday()),
        #     datetime.min.time()
        # )
        users = User.query.order_by(User.xp.desc()).limit(limit).all()
    else:
        # All-time leaderboard
        users = User.query.order_by(User.xp.desc()).limit(limit).all()

    leaderboard = []
    for rank, user in enumerate(users, 1):
        leaderboard.append(
            {
                "rank": rank,
                "user_id": user.id,
                "username": user.username or f"User {user.id}",
                "first_name": user.first_name,
                "xp": user.xp,
                "level": user.level,
                "streak_days": user.streak_days,
            }
        )

    return success_response({"type": leaderboard_type, "leaderboard": leaderboard})
