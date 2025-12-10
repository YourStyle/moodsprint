"""Gamification API endpoints."""

from datetime import date, datetime, timedelta

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
from app.models.character import GENRE_THEMES
from app.models.focus_session import FocusSessionStatus
from app.models.subtask import SubtaskStatus
from app.models.task import TaskStatus
from app.models.user_profile import UserProfile
from app.utils import not_found, success_response, validation_error


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


@api_bp.route("/user/productivity-patterns", methods=["GET"])
@jwt_required()
def get_productivity_patterns():
    """
    Get user productivity patterns based on focus sessions and task completions.

    Analyzes:
    - Best hours of day for focus
    - Best days of week
    - Average session duration
    - Success rate by time slot
    """
    user_id = int(get_jwt_identity())

    # Get completed focus sessions from last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)

    completed_sessions = FocusSession.query.filter(
        FocusSession.user_id == user_id,
        FocusSession.status == FocusSessionStatus.COMPLETED.value,
        FocusSession.started_at >= thirty_days_ago,
    ).all()

    all_sessions = FocusSession.query.filter(
        FocusSession.user_id == user_id,
        FocusSession.started_at >= thirty_days_ago,
    ).all()

    # Analyze hour distribution (0-23)
    hour_stats = {}
    for hour in range(24):
        hour_stats[hour] = {"completed": 0, "total": 0, "total_minutes": 0}

    for session in all_sessions:
        hour = session.started_at.hour
        hour_stats[hour]["total"] += 1
        if session.status == FocusSessionStatus.COMPLETED.value:
            hour_stats[hour]["completed"] += 1
            hour_stats[hour]["total_minutes"] += session.actual_duration_minutes or 0

    # Find best hours (hours with highest completion rate and activity)
    best_hours = []
    for hour, stats in hour_stats.items():
        if stats["total"] >= 2:  # At least 2 sessions to be significant
            success_rate = (
                stats["completed"] / stats["total"] if stats["total"] > 0 else 0
            )
            avg_minutes = (
                stats["total_minutes"] / stats["completed"]
                if stats["completed"] > 0
                else 0
            )
            best_hours.append(
                {
                    "hour": hour,
                    "sessions": stats["total"],
                    "completed": stats["completed"],
                    "success_rate": round(success_rate * 100),
                    "avg_minutes": round(avg_minutes),
                }
            )

    best_hours.sort(key=lambda x: (x["success_rate"], x["sessions"]), reverse=True)

    # Analyze day of week distribution (0=Monday, 6=Sunday)
    day_stats = {}
    day_names = [
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье",
    ]
    for day in range(7):
        day_stats[day] = {"completed": 0, "total": 0, "total_minutes": 0}

    for session in all_sessions:
        day = session.started_at.weekday()
        day_stats[day]["total"] += 1
        if session.status == FocusSessionStatus.COMPLETED.value:
            day_stats[day]["completed"] += 1
            day_stats[day]["total_minutes"] += session.actual_duration_minutes or 0

    day_distribution = []
    for day, stats in day_stats.items():
        success_rate = stats["completed"] / stats["total"] if stats["total"] > 0 else 0
        avg_minutes = (
            stats["total_minutes"] / stats["completed"] if stats["completed"] > 0 else 0
        )
        day_distribution.append(
            {
                "day": day,
                "day_name": day_names[day],
                "sessions": stats["total"],
                "completed": stats["completed"],
                "success_rate": round(success_rate * 100),
                "avg_minutes": round(avg_minutes),
            }
        )

    # Find best day
    best_day = max(
        day_distribution,
        key=lambda x: (x["success_rate"], x["sessions"]),
        default=None,
    )

    # Overall statistics
    total_sessions = len(all_sessions)
    total_completed = len(completed_sessions)
    total_minutes = sum(s.actual_duration_minutes or 0 for s in completed_sessions)
    overall_success_rate = total_completed / total_sessions if total_sessions > 0 else 0
    avg_session_duration = total_minutes / total_completed if total_completed > 0 else 0

    # Determine productivity type based on best hours
    productivity_time = "varies"
    if best_hours:
        top_hour = best_hours[0]["hour"]
        if 5 <= top_hour < 12:
            productivity_time = "morning"
        elif 12 <= top_hour < 17:
            productivity_time = "afternoon"
        elif 17 <= top_hour < 21:
            productivity_time = "evening"
        else:
            productivity_time = "night"

    return success_response(
        {
            "period_days": 30,
            "total_sessions": total_sessions,
            "total_completed": total_completed,
            "total_focus_minutes": total_minutes,
            "overall_success_rate": round(overall_success_rate * 100),
            "avg_session_duration": round(avg_session_duration),
            "productivity_time": productivity_time,
            "best_hours": best_hours[:5],  # Top 5 hours
            "best_day": best_day,
            "day_distribution": day_distribution,
            "hour_distribution": [
                {
                    "hour": h,
                    "sessions": hour_stats[h]["total"],
                    "completed": hour_stats[h]["completed"],
                }
                for h in range(24)
            ],
        }
    )


# ============ Genre Preferences ============


@api_bp.route("/genres", methods=["GET"])
@jwt_required()
def get_genres():
    """Get available genre themes."""
    genres = [
        {
            "id": key,
            "name": value["name"],
            "description": value["description"],
            "emoji": value["emoji"],
        }
        for key, value in GENRE_THEMES.items()
    ]
    return success_response({"genres": genres})


@api_bp.route("/profile/genre", methods=["PUT"])
@jwt_required()
def set_genre():
    """
    Set user's favorite genre.

    Request body:
    {
        "genre": "magic" | "fantasy" | "scifi" | "cyberpunk" | "anime"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    genre = data.get("genre")
    if genre not in GENRE_THEMES:
        return validation_error(
            {"genre": f"Invalid genre. Choose from: {list(GENRE_THEMES.keys())}"}
        )

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)

    profile.favorite_genre = genre
    db.session.commit()

    return success_response(
        {
            "genre": genre,
            "genre_info": {
                "name": GENRE_THEMES[genre]["name"],
                "description": GENRE_THEMES[genre]["description"],
                "emoji": GENRE_THEMES[genre]["emoji"],
            },
        }
    )


# ============ Daily Quests ============


@api_bp.route("/quests", methods=["GET"])
@jwt_required()
def get_daily_quests():
    """Get today's daily quests."""
    user_id = int(get_jwt_identity())

    from app.services.quest_service import QuestService

    service = QuestService()
    quests = service.get_user_quests(user_id)

    return success_response(
        {
            "quests": [q.to_dict() for q in quests],
            "completed_count": sum(1 for q in quests if q.completed),
            "total_count": len(quests),
        }
    )


@api_bp.route("/quests/<int:quest_id>/claim", methods=["POST"])
@jwt_required()
def claim_quest_reward(quest_id: int):
    """Claim reward for completed quest."""
    user_id = int(get_jwt_identity())

    from app.services.quest_service import QuestService

    service = QuestService()
    reward = service.claim_quest_reward(user_id, quest_id)

    if not reward:
        return validation_error(
            {"quest": "Quest not found, not completed, or already claimed"}
        )

    return success_response(
        {
            "reward": reward,
            "message": "Награда получена!",
        }
    )


# ============ Character Stats ============


@api_bp.route("/character", methods=["GET"])
@jwt_required()
def get_character():
    """Get user's character stats."""
    user_id = int(get_jwt_identity())

    from app.services.battle_service import BattleService

    service = BattleService()
    character = service.get_or_create_character(user_id)

    # Get genre-specific stat names
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    genre = profile.favorite_genre if profile else "fantasy"
    if not genre:
        genre = "fantasy"
    genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])

    return success_response(
        {
            "character": character.to_dict(),
            "stat_names": genre_info.get(
                "stat_names",
                {
                    "strength": "Сила",
                    "agility": "Ловкость",
                    "intelligence": "Интеллект",
                },
            ),
            "genre": genre,
        }
    )


@api_bp.route("/character/distribute", methods=["POST"])
@jwt_required()
def distribute_stat_points():
    """
    Distribute available stat points.

    Request body:
    {
        "stat": "strength" | "agility" | "intelligence",
        "points": 1
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    stat = data.get("stat")
    points = data.get("points", 1)

    if stat not in ["strength", "agility", "intelligence"]:
        return validation_error({"stat": "Invalid stat name"})

    try:
        points = int(points)
        if points < 1:
            return validation_error({"points": "Points must be positive"})
    except (ValueError, TypeError):
        return validation_error({"points": "Invalid points value"})

    from app.services.battle_service import BattleService

    service = BattleService()
    result = service.distribute_stat_points(user_id, stat, points)

    if not result["success"]:
        return validation_error(
            {"error": result.get("error", "Failed to distribute points")}
        )

    return success_response(result)


@api_bp.route("/character/heal", methods=["POST"])
@jwt_required()
def heal_character():
    """
    Heal character HP.

    Request body (optional):
    {
        "amount": 50  // if not provided, full heal
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    amount = data.get("amount")
    if amount is not None:
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            amount = None

    from app.services.battle_service import BattleService

    service = BattleService()
    character = service.heal_character(user_id, amount)

    return success_response(
        {
            "character": character.to_dict(),
            "message": "Здоровье восстановлено!",
        }
    )


# ============ Battle Arena ============


@api_bp.route("/arena/monsters", methods=["GET"])
@jwt_required()
def get_arena_monsters():
    """Get available monsters for battle."""
    user_id = int(get_jwt_identity())

    from app.services.battle_service import BattleService

    service = BattleService()
    monsters = service.get_available_monsters(user_id)

    return success_response(
        {
            "monsters": [m.to_dict() for m in monsters],
        }
    )


@api_bp.route("/arena/battle", methods=["POST"])
@jwt_required()
def start_battle():
    """
    Start a battle with a monster.

    Request body:
    {
        "monster_id": 1
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    monster_id = data.get("monster_id")
    if not monster_id:
        return validation_error({"monster_id": "Monster ID is required"})

    from app.services.battle_service import BattleService

    service = BattleService()
    result = service.execute_battle(user_id, monster_id)

    if "error" in result:
        return validation_error(result)

    return success_response(result)


@api_bp.route("/arena/history", methods=["GET"])
@jwt_required()
def get_battle_history():
    """Get recent battle history."""
    user_id = int(get_jwt_identity())
    limit = request.args.get("limit", 10, type=int)

    from app.services.battle_service import BattleService

    service = BattleService()
    battles = service.get_battle_history(user_id, min(limit, 50))

    return success_response(
        {
            "battles": [b.to_dict() for b in battles],
        }
    )


# ============ Boss Tasks ============


@api_bp.route("/tasks/<int:task_id>/boss-info", methods=["GET"])
@jwt_required()
def get_boss_task_info(task_id: int):
    """
    Check if task qualifies as a boss task and get boss info.

    Boss tasks are:
    - Tasks with estimated time > 60 min
    - Tasks with > 5 subtasks
    """
    user_id = int(get_jwt_identity())

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return not_found("Task not found")

    # Calculate total time from subtasks
    total_time = sum(s.estimated_minutes for s in task.subtasks) if task.subtasks else 0
    subtask_count = len(task.subtasks) if task.subtasks else 0

    # Check if boss task
    is_boss = total_time >= 60 or subtask_count >= 5

    # Get genre-specific boss info
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    genre = profile.favorite_genre if profile else "fantasy"
    if not genre:
        genre = "fantasy"

    boss_titles = {
        "magic": "Магическое испытание",
        "fantasy": "Эпический квест",
        "scifi": "Критическая миссия",
        "cyberpunk": "Опасный контракт",
        "anime": "Последний босс",
    }

    return success_response(
        {
            "is_boss": is_boss,
            "total_time": total_time,
            "subtask_count": subtask_count,
            "boss_title": boss_titles.get(genre, "Босс-задача") if is_boss else None,
            "xp_multiplier": 3 if is_boss else 1,
            "stat_points_bonus": 2 if is_boss else 0,
        }
    )
