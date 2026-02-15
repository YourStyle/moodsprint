"""Gamification API endpoints."""

from datetime import date, datetime, timedelta

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from app import db
from app.api import api_bp
from app.extensions import cache, limiter
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
from app.models.character import GENRE_THEMES, get_genre_info
from app.models.focus_session import FocusSessionStatus
from app.models.subtask import SubtaskStatus
from app.models.task import TaskStatus
from app.models.user_profile import UserProfile
from app.utils import get_lang, not_found, success_response, validation_error


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

    lang = get_lang()
    return success_response(
        {
            "xp": user.xp,
            "level": user.level,
            "level_name": get_level_name(user.level, lang),
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
@limiter.limit("30 per minute")
@cache.cached(timeout=60, query_string=True)  # Cache for 1 minute
def get_leaderboard():
    """
    Get leaderboard based on killed monsters.
    ---
    tags:
      - Gamification
    security:
      - Bearer: []
    parameters:
      - in: query
        name: type
        type: string
        enum: [weekly, all_time]
        default: weekly
      - in: query
        name: limit
        type: integer
        default: 10
        maximum: 50
    responses:
      200:
        description: Leaderboard data
    """
    from sqlalchemy import func

    from app.models.character import BattleLog

    limit = min(int(request.args.get("limit", 10)), 50)
    leaderboard_type = request.args.get("type", "weekly")

    week_start = None
    if leaderboard_type == "weekly":
        # Weekly - battles from this week (Monday = 0)
        week_start = datetime.combine(
            date.today() - timedelta(days=date.today().weekday()), datetime.min.time()
        )

    # Build the kills count query based on type
    if leaderboard_type == "weekly" and week_start:
        # Weekly kills
        kills_case = func.count(
            db.case(
                (
                    db.and_(
                        BattleLog.won.is_(True),
                        BattleLog.created_at >= week_start,
                    ),
                    BattleLog.id,
                ),
                else_=None,
            )
        )
    else:
        # All time kills
        kills_case = func.count(
            db.case(
                (BattleLog.won.is_(True), BattleLog.id),
                else_=None,
            )
        )

    # Get users who have ever battled, with their kill count for the period
    results = (
        db.session.query(
            User,
            kills_case.label("monsters_killed"),
        )
        .join(BattleLog, User.id == BattleLog.user_id)
        .group_by(User.id)
        .order_by(kills_case.desc(), User.xp.desc())
        .limit(limit)
        .all()
    )

    leaderboard = []
    for rank, (user, monsters_killed) in enumerate(results, 1):
        leaderboard.append(
            {
                "rank": rank,
                "user_id": user.id,
                "username": user.username or f"User {user.id}",
                "first_name": user.first_name,
                "monsters_killed": monsters_killed or 0,
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
    lang = get_lang()
    day_names = (
        [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        if lang == "en"
        else [
            "Понедельник",
            "Вторник",
            "Среда",
            "Четверг",
            "Пятница",
            "Суббота",
            "Воскресенье",
        ]
    )
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
    lang = get_lang()
    genres = [get_genre_info(key, lang) for key in GENRE_THEMES.keys()]
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

    lang = get_lang()
    return success_response(
        {
            "genre": genre,
            "genre_info": get_genre_info(genre, lang),
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

    # Get localized stat names
    lang = get_lang()
    stat_names_key = "stat_names_en" if lang == "en" else "stat_names"
    default_stats = (
        {"strength": "Strength", "agility": "Agility", "intelligence": "Intelligence"}
        if lang == "en"
        else {"strength": "Сила", "agility": "Ловкость", "intelligence": "Интеллект"}
    )

    return success_response(
        {
            "character": character.to_dict(),
            "stat_names": genre_info.get(stat_names_key, default_stats),
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


# ============ Battle Arena (Card-based) ============


@api_bp.route("/arena/monsters", methods=["GET"])
@jwt_required()
def get_arena_monsters():
    """Get available monsters for battle with required card info."""
    user_id = int(get_jwt_identity())

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    monsters = service.get_available_monsters(user_id)

    # Also return user's deck for convenience
    deck = service.get_user_deck(user_id)

    return success_response(
        {
            "monsters": monsters,
            "deck": [c.to_dict() for c in deck],
            "deck_size": len(deck),
        }
    )


@api_bp.route("/arena/battle", methods=["POST"])
@limiter.limit("60 per minute")
@jwt_required()
def start_battle():
    """
    Start a turn-based card battle with a monster.

    Request body:
    {
        "monster_id": 1,
        "card_ids": [1, 2, 3],  // IDs of cards to use in battle
        "campaign_level_id": null  // Optional: for campaign battles
    }

    Returns battle state with player and monster decks.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    monster_id = data.get("monster_id")
    card_ids = data.get("card_ids", [])
    campaign_level_id = data.get("campaign_level_id")

    if not monster_id:
        return validation_error({"monster_id": "Monster ID is required"})

    if not card_ids:
        return validation_error({"card_ids": "Select cards for battle"})

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    result = service.start_battle(user_id, monster_id, card_ids, campaign_level_id)

    if "error" in result:
        return validation_error(result)

    return success_response(result)


@api_bp.route("/arena/battle/active", methods=["GET"])
@jwt_required()
def get_active_battle():
    """Get user's active battle if any."""
    user_id = int(get_jwt_identity())

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    battle = service.get_active_battle(user_id)

    if not battle:
        return success_response({"battle": None})

    lang = get_lang()
    return success_response({"battle": battle.to_dict(lang)})


@api_bp.route("/arena/battle/turn", methods=["POST"])
@jwt_required()
def execute_battle_turn():
    """
    Execute a turn in the active battle.

    Request body:
    {
        "player_card_id": 1,        // ID of player's card to attack/use ability with
        "target_card_id": "m_1_0",  // ID of target card (monster or ally depending on ability)
        "use_ability": false        // If true, use card's ability instead of attack
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    player_card_id = data.get("player_card_id")
    target_card_id = data.get("target_card_id")
    use_ability = data.get("use_ability", False)

    if not player_card_id:
        return validation_error({"player_card_id": "Select a card to attack with"})

    if not target_card_id:
        return validation_error({"target_card_id": "Select a target"})

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    result = service.execute_turn(user_id, player_card_id, target_card_id, use_ability)

    if "error" in result:
        return validation_error(result)

    return success_response(result)


@api_bp.route("/arena/battle/forfeit", methods=["POST"])
@jwt_required()
def forfeit_battle():
    """Forfeit the current battle."""
    user_id = int(get_jwt_identity())

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    result = service.forfeit_battle(user_id)

    if "error" in result:
        return validation_error(result)

    return success_response(result)


@api_bp.route("/arena/history", methods=["GET"])
@jwt_required()
def get_battle_history():
    """Get recent battle history."""
    user_id = int(get_jwt_identity())
    limit = request.args.get("limit", 10, type=int)

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    battles = service.get_battle_history(user_id, min(limit, 50))

    lang = get_lang()
    return success_response(
        {
            "battles": [b.to_dict(lang) for b in battles],
        }
    )


# ============ Monster Image Generation ============


@api_bp.route("/arena/monsters/<int:monster_id>/generate-image", methods=["POST"])
@jwt_required()
def generate_monster_image(monster_id: int):
    """
    Generate image for a monster that doesn't have one yet.
    """
    from app.models.character import Monster

    monster = Monster.query.get(monster_id)
    if not monster:
        return not_found("Monster not found")

    if monster.sprite_url:
        return success_response(
            {
                "success": True,
                "sprite_url": monster.sprite_url,
                "already_exists": True,
            }
        )

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    sprite_url = service._generate_monster_image(monster, monster.genre)

    if sprite_url:
        monster.sprite_url = sprite_url
        db.session.commit()
        return success_response(
            {
                "success": True,
                "sprite_url": sprite_url,
            }
        )

    return success_response({"success": False, "error": "generation_failed"})


@api_bp.route("/arena/monsters/generate-all-images", methods=["POST"])
@jwt_required()
def generate_all_monster_images():
    """
    Generate images for all monsters that don't have images yet.
    This is an admin-like endpoint for batch image generation.
    """
    from app.models.character import Monster

    # Get monsters without images
    monsters = Monster.query.filter(
        (Monster.sprite_url.is_(None)) | (Monster.sprite_url == "")
    ).all()

    if not monsters:
        return success_response(
            {
                "success": True,
                "message": "All monsters already have images",
                "generated": 0,
            }
        )

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    generated = 0
    failed = 0

    for monster in monsters:
        sprite_url = service._generate_monster_image(monster, monster.genre)
        if sprite_url:
            monster.sprite_url = sprite_url
            generated += 1
        else:
            failed += 1

    db.session.commit()

    return success_response(
        {
            "success": True,
            "generated": generated,
            "failed": failed,
            "total": len(monsters),
        }
    )


# ============ Monster Image Generation (Admin) ============


@api_bp.route("/arena/monsters/generate-images-admin", methods=["POST"])
def generate_all_monster_images_admin():
    """
    Generate images for all monsters that don't have images yet.
    Protected by BOT_SECRET header for admin panel use.
    """
    from flask import request

    # Verify bot secret
    bot_secret = request.headers.get("X-Bot-Secret")
    expected_secret = current_app.config.get("BOT_SECRET", "")

    if not expected_secret or bot_secret != expected_secret:
        return validation_error({"error": "unauthorized"})

    from app.models.character import Monster

    # Get monsters without images
    monsters = Monster.query.filter(
        (Monster.sprite_url.is_(None)) | (Monster.sprite_url == "")
    ).all()

    if not monsters:
        return success_response(
            {
                "success": True,
                "message": "All monsters already have images",
                "generated": 0,
                "total": 0,
            }
        )

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    generated = 0
    failed = 0

    for monster in monsters:
        sprite_url = service._generate_monster_image(monster, monster.genre)
        if sprite_url:
            monster.sprite_url = sprite_url
            generated += 1
        else:
            failed += 1

    db.session.commit()

    return success_response(
        {
            "success": True,
            "generated": generated,
            "failed": failed,
            "total": len(monsters),
        }
    )


@api_bp.route("/arena/monsters/<int:monster_id>/generate-image-admin", methods=["POST"])
def generate_single_monster_image_admin(monster_id: int):
    """
    Generate image for a single monster.
    Protected by BOT_SECRET header for admin panel use.
    """
    from flask import request

    # Verify bot secret
    bot_secret = request.headers.get("X-Bot-Secret")
    expected_secret = current_app.config.get("BOT_SECRET", "")

    if not expected_secret or bot_secret != expected_secret:
        return validation_error({"error": "unauthorized"})

    from app.models.character import Monster

    monster = Monster.query.get(monster_id)
    if not monster:
        return validation_error({"error": "monster_not_found"})

    from app.services.card_battle_service import CardBattleService

    service = CardBattleService()
    sprite_url = service._generate_monster_image(monster, monster.genre)

    if sprite_url:
        monster.sprite_url = sprite_url
        db.session.commit()
        return success_response({"success": True, "sprite_url": sprite_url})

    return success_response({"success": False, "error": "generation_failed"})


# ============ Monster Rotation (Cron) ============


@api_bp.route("/arena/monsters/rotate", methods=["POST"])
def rotate_monsters():
    """
    Generate new monsters for current 3-day period.
    Called by cron job from bot every 3 days.
    Protected by BOT_SECRET header.
    """
    from flask import request

    # Verify bot secret
    bot_secret = request.headers.get("X-Bot-Secret")
    expected_secret = current_app.config.get("BOT_SECRET", "")

    if not expected_secret or bot_secret != expected_secret:
        return validation_error({"error": "unauthorized"})

    # Check if we need to generate (only if no monsters exist for current period)
    from app.models.character import DailyMonster

    period_start = DailyMonster.get_current_period_start()

    # Check if any monsters exist for current period (any genre)
    existing_count = DailyMonster.query.filter_by(period_start=period_start).count()

    if existing_count > 0:
        return success_response(
            {
                "success": True,
                "message": f"Monsters already exist for period {period_start}",
                "generated": {},
                "existing_count": existing_count,
            }
        )

    from app.services.monster_generator import MonsterGeneratorService

    service = MonsterGeneratorService()
    # Generate with images so monsters are ready to display
    results = service.generate_daily_monsters(generate_images=True)

    total = sum(results.values())
    return success_response(
        {
            "success": True,
            "message": f"Generated {total} monsters for period {period_start}",
            "generated": results,
            "period_start": str(period_start),
        }
    )


# ============ Boss Tasks ============


# ============ Seasonal Events ============


@api_bp.route("/events/active", methods=["GET"])
@jwt_required(optional=True)
def get_active_event():
    """Get currently active event with user progress."""
    from app.services.event_service import EventService

    service = EventService()
    event = service.get_active_event()

    if not event:
        return success_response({"event": None, "progress": None, "monsters": []})

    # Get user progress if authenticated
    user_identity = get_jwt_identity()
    progress = None
    if user_identity:
        user_id = int(user_identity)
        progress = service.get_user_progress(user_id, event.id)

    # Get event monsters
    monsters = service.get_event_monsters(event.id)

    return success_response(
        {
            "event": event.to_dict(),
            "progress": progress.to_dict() if progress else None,
            "monsters": [m.to_dict() for m in monsters],
        }
    )


@api_bp.route("/events", methods=["GET"])
@jwt_required()
def get_all_events():
    """Get all events (current and upcoming)."""
    include_past = request.args.get("include_past", "false").lower() == "true"

    from app.services.event_service import EventService

    service = EventService()
    events = service.get_all_events(include_past=include_past)

    return success_response(
        {
            "events": [e.to_dict() for e in events],
        }
    )


@api_bp.route("/events/<int:event_id>", methods=["GET"])
@jwt_required()
def get_event_details(event_id: int):
    """Get detailed information about a specific event."""
    user_id = int(get_jwt_identity())

    from app.services.event_service import EventService

    service = EventService()
    event = service.get_event_by_id(event_id)

    if not event:
        return not_found("Event not found")

    progress = service.get_user_progress(user_id, event.id)
    monsters = service.get_event_monsters(event.id)

    return success_response(
        {
            "event": event.to_dict(),
            "progress": progress.to_dict() if progress else None,
            "monsters": [m.to_dict() for m in monsters],
        }
    )


@api_bp.route("/events/<int:event_id>/progress", methods=["GET"])
@jwt_required()
def get_event_progress(event_id: int):
    """Get user's progress in a specific event."""
    user_id = int(get_jwt_identity())

    from app.services.event_service import EventService

    service = EventService()
    event = service.get_event_by_id(event_id)

    if not event:
        return not_found("Event not found")

    progress = service.get_or_create_user_progress(user_id, event.id)

    return success_response(
        {
            "event": event.to_dict(),
            "progress": progress.to_dict(),
        }
    )


# Admin endpoint for creating manual events
@api_bp.route("/admin/events", methods=["POST"])
@jwt_required()
def create_manual_event():
    """
    Create a manual event (admin only).

    Request body:
    {
        "code": "special_event_2024",
        "name": "Special Event",
        "description": "Event description",
        "start_date": "2024-12-20T00:00:00",
        "end_date": "2024-12-27T23:59:59",
        "emoji": "🎉",
        "theme_color": "#FF6B00",
        "xp_multiplier": 1.5
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    # Basic validation (in production, add admin role check)
    required_fields = ["code", "name", "start_date", "end_date"]
    for field in required_fields:
        if not data.get(field):
            return validation_error({field: f"{field} is required"})

    try:
        start_date = datetime.fromisoformat(data["start_date"])
        end_date = datetime.fromisoformat(data["end_date"])
    except ValueError:
        return validation_error({"date": "Invalid date format. Use ISO format."})

    if start_date >= end_date:
        return validation_error({"date": "End date must be after start date"})

    from app.services.event_service import EventService

    service = EventService()

    # Check if code already exists
    existing = service.get_all_events(include_past=True)
    if any(e.code == data["code"] for e in existing):
        return validation_error({"code": "Event code already exists"})

    event = service.create_manual_event(
        code=data["code"],
        name=data["name"],
        description=data.get("description", ""),
        start_date=start_date,
        end_date=end_date,
        created_by=user_id,
        emoji=data.get("emoji", "🎉"),
        theme_color=data.get("theme_color", "#FF6B00"),
        xp_multiplier=data.get("xp_multiplier", 1.0),
    )

    return success_response(
        {
            "event": event.to_dict(),
            "message": "Event created successfully",
        }
    )


# ============ Card Merge System ============


@api_bp.route("/cards/merge/preview", methods=["POST"])
@jwt_required()
def preview_card_merge():
    """
    Preview merge chances for two cards.

    Request body:
    {
        "card1_id": 1,
        "card2_id": 2
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    card1_id = data.get("card1_id")
    card2_id = data.get("card2_id")

    if not card1_id or not card2_id:
        return validation_error({"cards": "Select two cards to merge"})

    from app.models.card import UserCard

    card1 = UserCard.query.filter_by(id=card1_id, user_id=user_id).first()
    card2 = UserCard.query.filter_by(id=card2_id, user_id=user_id).first()

    if not card1 or not card2:
        return not_found("Card not found")

    from app.services.merge_service import MergeService

    service = MergeService()
    result = service.get_merge_chances(card1, card2)

    if "error" in result:
        return validation_error(result)

    lang = get_lang()
    return success_response(
        {
            "card1": card1.to_dict(lang),
            "card2": card2.to_dict(lang),
            **result,
        }
    )


@api_bp.route("/cards/merge", methods=["POST"])
@jwt_required()
def merge_cards():
    """
    Merge two cards into a new random card.

    Request body:
    {
        "card1_id": 1,
        "card2_id": 2
    }

    Note: This will DESTROY both input cards!
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    card1_id = data.get("card1_id")
    card2_id = data.get("card2_id")

    if not card1_id or not card2_id:
        return validation_error({"cards": "Select two cards to merge"})

    from app.services.merge_service import MergeService

    service = MergeService()
    result = service.merge_cards(user_id, card1_id, card2_id)

    if "error" in result:
        return validation_error(result)

    return success_response(result)


@api_bp.route("/cards/merge/history", methods=["GET"])
@jwt_required()
def get_merge_history():
    """Get recent merge history."""
    user_id = int(get_jwt_identity())
    limit = request.args.get("limit", 10, type=int)

    from app.services.merge_service import MergeService

    service = MergeService()
    merges = service.get_merge_history(user_id, min(limit, 50))

    return success_response(
        {
            "merges": [m.to_dict() for m in merges],
        }
    )


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


@api_bp.route("/admin/activity/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user_activity_heatmap(user_id: int):
    """
    Get user activity data for GitHub-style heatmap.

    Returns task completions grouped by date for the last year.
    """
    get_jwt_identity()  # Verify authenticated

    # Get completions for the last 365 days
    start_date = date.today() - timedelta(days=365)

    # Query completed tasks grouped by completion date
    task_completions = (
        db.session.query(
            func.date(Task.completed_at).label("completion_date"),
            func.count(Task.id).label("count"),
        )
        .filter(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at >= start_date,
        )
        .group_by(func.date(Task.completed_at))
        .all()
    )

    # Query completed subtasks grouped by completion date
    subtask_completions = (
        db.session.query(
            func.date(Subtask.completed_at).label("completion_date"),
            func.count(Subtask.id).label("count"),
        )
        .join(Task, Subtask.task_id == Task.id)
        .filter(
            Task.user_id == user_id,
            Subtask.status == SubtaskStatus.COMPLETED,
            Subtask.completed_at >= start_date,
        )
        .group_by(func.date(Subtask.completed_at))
        .all()
    )

    # Combine into a single dict
    activity = {}
    for row in task_completions:
        if row.completion_date:
            date_str = row.completion_date.isoformat()
            activity[date_str] = activity.get(date_str, 0) + row.count

    for row in subtask_completions:
        if row.completion_date:
            date_str = row.completion_date.isoformat()
            activity[date_str] = activity.get(date_str, 0) + row.count

    # Get user info
    user = User.query.get(user_id)
    if not user:
        return not_found("User not found")

    return success_response(
        {
            "user_id": user_id,
            "username": user.username,
            "first_name": user.first_name,
            "activity": activity,
        }
    )


@api_bp.route("/admin/users", methods=["GET"])
@jwt_required()
def get_all_users():
    """
    Get all users for admin panel.
    """
    get_jwt_identity()  # Verify authenticated

    users = User.query.order_by(User.id.desc()).limit(100).all()

    return success_response(
        {
            "users": [
                {
                    "id": u.id,
                    "telegram_id": u.telegram_id,
                    "username": u.username,
                    "first_name": u.first_name,
                    "level": u.level,
                    "xp": u.xp,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ]
        }
    )
