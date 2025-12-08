"""Mood API endpoints."""

from datetime import date, datetime, timedelta

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from app import db
from app.api import api_bp
from app.models import MoodCheck, User
from app.services import AchievementChecker, XPCalculator
from app.utils import success_response, validation_error


@api_bp.route("/mood", methods=["POST"])
@jwt_required()
def create_mood_check():
    """
    Log a mood check.

    Request body:
    {
        "mood": 3,      // 1-5
        "energy": 4,    // 1-5
        "note": "Optional note"
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return validation_error({"body": "Request body is required"})

    # Validate mood
    try:
        mood = int(data.get("mood", 0))
        if not 1 <= mood <= 5:
            raise ValueError()
    except (ValueError, TypeError):
        return validation_error({"mood": "Mood must be an integer between 1 and 5"})

    # Validate energy
    try:
        energy = int(data.get("energy", 0))
        if not 1 <= energy <= 5:
            raise ValueError()
    except (ValueError, TypeError):
        return validation_error({"energy": "Energy must be an integer between 1 and 5"})

    # Create mood check
    mood_check = MoodCheck(
        user_id=user_id,
        mood=mood,
        energy=energy,
        note=data.get("note", "")[:500] if data.get("note") else None,
    )

    db.session.add(mood_check)

    # Award XP
    user = User.query.get(user_id)
    xp_info = user.add_xp(XPCalculator.mood_check())
    user.update_streak()

    # Check achievements
    checker = AchievementChecker(user)
    achievements_unlocked = checker.check_all()

    db.session.commit()

    return success_response(
        {
            "mood_check": mood_check.to_dict(),
            "xp_earned": xp_info["xp_earned"],
            "achievements_unlocked": [a.to_dict() for a in achievements_unlocked],
        },
        status_code=201,
    )


@api_bp.route("/mood/latest", methods=["GET"])
@jwt_required()
def get_latest_mood():
    """Get the latest mood check."""
    user_id = get_jwt_identity()

    mood_check = (
        MoodCheck.query.filter_by(user_id=user_id)
        .order_by(MoodCheck.created_at.desc())
        .first()
    )

    return success_response(
        {"mood_check": mood_check.to_dict() if mood_check else None}
    )


@api_bp.route("/mood/history", methods=["GET"])
@jwt_required()
def get_mood_history():
    """
    Get mood history.

    Query params:
    - days: number of days to include (default 7, max 30)
    """
    user_id = get_jwt_identity()

    days = min(int(request.args.get("days", 7)), 30)
    start_date = datetime.combine(
        date.today() - timedelta(days=days - 1), datetime.min.time()
    )

    # Get all mood checks in range
    mood_checks = (
        MoodCheck.query.filter(
            MoodCheck.user_id == user_id, MoodCheck.created_at >= start_date
        )
        .order_by(MoodCheck.created_at.desc())
        .all()
    )

    # Group by date
    history = {}
    for check in mood_checks:
        check_date = check.created_at.date().isoformat()
        if check_date not in history:
            history[check_date] = {
                "date": check_date,
                "checks": [],
                "mood_sum": 0,
                "energy_sum": 0,
                "count": 0,
            }

        history[check_date]["checks"].append(check.to_dict())
        history[check_date]["mood_sum"] += check.mood
        history[check_date]["energy_sum"] += check.energy
        history[check_date]["count"] += 1

    # Calculate averages
    result = []
    for day_data in history.values():
        count = day_data["count"]
        result.append(
            {
                "date": day_data["date"],
                "checks": day_data["checks"],
                "average_mood": round(day_data["mood_sum"] / count, 1),
                "average_energy": round(day_data["energy_sum"] / count, 1),
            }
        )

    # Sort by date descending
    result.sort(key=lambda x: x["date"], reverse=True)

    return success_response({"history": result})


@api_bp.route("/mood/stats", methods=["GET"])
@jwt_required()
def get_mood_stats():
    """Get mood statistics."""
    user_id = get_jwt_identity()

    # Overall averages
    overall = (
        db.session.query(
            func.avg(MoodCheck.mood).label("avg_mood"),
            func.avg(MoodCheck.energy).label("avg_energy"),
            func.count(MoodCheck.id).label("total_checks"),
        )
        .filter(MoodCheck.user_id == user_id)
        .first()
    )

    # Last 7 days averages
    week_ago = datetime.combine(date.today() - timedelta(days=6), datetime.min.time())

    weekly = (
        db.session.query(
            func.avg(MoodCheck.mood).label("avg_mood"),
            func.avg(MoodCheck.energy).label("avg_energy"),
            func.count(MoodCheck.id).label("total_checks"),
        )
        .filter(MoodCheck.user_id == user_id, MoodCheck.created_at >= week_ago)
        .first()
    )

    return success_response(
        {
            "overall": {
                "average_mood": round(float(overall.avg_mood or 0), 1),
                "average_energy": round(float(overall.avg_energy or 0), 1),
                "total_checks": overall.total_checks or 0,
            },
            "weekly": {
                "average_mood": round(float(weekly.avg_mood or 0), 1),
                "average_energy": round(float(weekly.avg_energy or 0), 1),
                "total_checks": weekly.total_checks or 0,
            },
        }
    )
