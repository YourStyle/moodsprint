"""Onboarding API endpoints."""

import logging
from datetime import datetime

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.api import api_bp
from app.models import ActivityType, User, UserActivityLog
from app.models.user_profile import UserProfile
from app.services.card_service import CardService
from app.services.profile_analyzer import ProfileAnalyzer
from app.utils import not_found, success_response, validation_error

logger = logging.getLogger(__name__)


@api_bp.route("/onboarding/status", methods=["GET"])
@jwt_required()
def get_onboarding_status():
    """Check if user has completed onboarding."""
    user_id = int(get_jwt_identity())

    profile = UserProfile.query.filter_by(user_id=user_id).first()

    return success_response(
        {
            "completed": profile.onboarding_completed if profile else False,
            "profile": profile.to_dict() if profile else None,
        }
    )


@api_bp.route("/onboarding/complete", methods=["POST"])
@jwt_required()
def complete_onboarding():
    """
    Complete onboarding with user responses.

    Request body:
    {
        "productive_time": "morning",
        "favorite_tasks": ["creative", "analytical"],
        "challenges": ["focus", "procrastination"],
        "work_description": "I work best in quiet environments...",
        "goals": "I want to be more consistent with my tasks"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return validation_error({"body": "Request body is required"})

    # Get or create profile
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)

    # Analyze with GPT
    analyzer = ProfileAnalyzer()
    analysis = analyzer.analyze_onboarding(data)

    # Update profile
    profile.productivity_type = analysis.get("productivity_type")
    profile.preferred_time = analysis.get("preferred_time", data.get("productive_time"))
    profile.work_style = analysis.get("work_style")
    profile.favorite_task_types = analysis.get(
        "favorite_task_types", data.get("favorite_tasks")
    )
    profile.main_challenges = analysis.get("main_challenges", data.get("challenges"))
    profile.productivity_goals = data.get("goals")
    profile.gpt_analysis = analysis
    profile.preferred_session_duration = analysis.get(
        "recommended_session_duration", 25
    )
    profile.onboarding_completed = True
    profile.onboarding_completed_at = datetime.utcnow()

    # Log activity
    UserActivityLog.log(
        user_id=user_id,
        action_type=ActivityType.ONBOARDING_COMPLETE,
        action_details=f"Type: {profile.productivity_type}, Style: {profile.work_style}",
    )

    db.session.commit()

    # Handle referral rewards
    referral_rewards = {}
    user = User.query.get(user_id)

    if user and user.referred_by and not user.referral_reward_given:
        try:
            card_service = CardService()

            # Give starter deck to new user (3 cards, max rare)
            starter_deck = card_service.generate_starter_deck(user_id)
            if starter_deck:
                referral_rewards["starter_deck"] = [c.to_dict() for c in starter_deck]
                logger.info(
                    f"Gave starter deck to user {user_id}: {len(starter_deck)} cards"
                )

            # Give rare+ card to referrer
            referrer_card = card_service.generate_referral_reward(user.referred_by)
            if referrer_card:
                referral_rewards["referrer_rewarded"] = True
                referral_rewards["referrer_card_rarity"] = referrer_card.rarity
                logger.info(
                    f"Gave referral reward to user {user.referred_by}: "
                    f"{referrer_card.name} ({referrer_card.rarity})"
                )

            # Mark reward as given
            user.referral_reward_given = True
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to give referral rewards: {e}")

    # Generate personalized message
    welcome_message = analyzer.get_personalized_message(analysis)

    response_data = {
        "profile": profile.to_dict(),
        "analysis": {
            "productivity_type": analysis.get("productivity_type"),
            "work_style": analysis.get("work_style"),
            "personalized_tips": analysis.get("personalized_tips", []),
            "motivation_style": analysis.get("motivation_style", "gentle"),
            "recommended_session_duration": analysis.get(
                "recommended_session_duration", 25
            ),
        },
        "welcome_message": welcome_message,
    }

    if referral_rewards:
        response_data["referral_rewards"] = referral_rewards

    return success_response(response_data)


@api_bp.route("/onboarding/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """Get user's productivity profile."""
    user_id = int(get_jwt_identity())

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return not_found("Profile not found. Please complete onboarding.")

    return success_response({"profile": profile.to_dict()})


@api_bp.route("/onboarding/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """
    Update profile settings.

    Request body:
    {
        "notifications_enabled": true,
        "daily_reminder_time": "09:00",
        "preferred_session_duration": 25,
        "work_start_time": "09:00",
        "work_end_time": "18:00",
        "work_days": [1, 2, 3, 4, 5],
        "timezone": "Europe/Moscow"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)

    if "notifications_enabled" in data:
        profile.notifications_enabled = bool(data["notifications_enabled"])

    if "daily_reminder_time" in data:
        profile.daily_reminder_time = data["daily_reminder_time"]

    if "preferred_session_duration" in data:
        duration = int(data["preferred_session_duration"])
        profile.preferred_session_duration = max(5, min(120, duration))

    # Work schedule settings
    if "work_start_time" in data:
        profile.work_start_time = data["work_start_time"]

    if "work_end_time" in data:
        profile.work_end_time = data["work_end_time"]

    if "work_days" in data:
        work_days = data["work_days"]
        if isinstance(work_days, list):
            # Validate days are 1-7
            profile.work_days = [d for d in work_days if 1 <= d <= 7]

    if "timezone" in data:
        profile.timezone = data["timezone"]

    db.session.commit()

    return success_response({"profile": profile.to_dict()})
