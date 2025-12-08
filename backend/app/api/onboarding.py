"""Onboarding API endpoints."""
from datetime import datetime
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.api import api_bp
from app.models import UserActivityLog, ActivityType
from app.models.user_profile import UserProfile
from app.services.profile_analyzer import ProfileAnalyzer
from app.utils import success_response, validation_error, not_found


@api_bp.route('/onboarding/status', methods=['GET'])
@jwt_required()
def get_onboarding_status():
    """Check if user has completed onboarding."""
    user_id = get_jwt_identity()

    profile = UserProfile.query.filter_by(user_id=user_id).first()

    return success_response({
        'completed': profile.onboarding_completed if profile else False,
        'profile': profile.to_dict() if profile else None
    })


@api_bp.route('/onboarding/complete', methods=['POST'])
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
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return validation_error({'body': 'Request body is required'})

    # Get or create profile
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)

    # Analyze with GPT
    analyzer = ProfileAnalyzer()
    analysis = analyzer.analyze_onboarding(data)

    # Update profile
    profile.productivity_type = analysis.get('productivity_type')
    profile.preferred_time = analysis.get('preferred_time', data.get('productive_time'))
    profile.work_style = analysis.get('work_style')
    profile.favorite_task_types = analysis.get('favorite_task_types', data.get('favorite_tasks'))
    profile.main_challenges = analysis.get('main_challenges', data.get('challenges'))
    profile.productivity_goals = data.get('goals')
    profile.gpt_analysis = analysis
    profile.preferred_session_duration = analysis.get('recommended_session_duration', 25)
    profile.onboarding_completed = True
    profile.onboarding_completed_at = datetime.utcnow()

    # Log activity
    UserActivityLog.log(
        user_id=user_id,
        action_type=ActivityType.ONBOARDING_COMPLETE,
        action_details=f"Type: {profile.productivity_type}, Style: {profile.work_style}"
    )

    db.session.commit()

    # Generate personalized message
    welcome_message = analyzer.get_personalized_message(analysis)

    return success_response({
        'profile': profile.to_dict(),
        'analysis': {
            'productivity_type': analysis.get('productivity_type'),
            'work_style': analysis.get('work_style'),
            'personalized_tips': analysis.get('personalized_tips', []),
            'motivation_style': analysis.get('motivation_style', 'gentle'),
            'recommended_session_duration': analysis.get('recommended_session_duration', 25)
        },
        'welcome_message': welcome_message
    })


@api_bp.route('/onboarding/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user's productivity profile."""
    user_id = get_jwt_identity()

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return not_found('Profile not found. Please complete onboarding.')

    return success_response({'profile': profile.to_dict()})


@api_bp.route('/onboarding/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update profile settings.

    Request body:
    {
        "notifications_enabled": true,
        "daily_reminder_time": "09:00",
        "preferred_session_duration": 25
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)

    if 'notifications_enabled' in data:
        profile.notifications_enabled = bool(data['notifications_enabled'])

    if 'daily_reminder_time' in data:
        profile.daily_reminder_time = data['daily_reminder_time']

    if 'preferred_session_duration' in data:
        duration = int(data['preferred_session_duration'])
        profile.preferred_session_duration = max(5, min(120, duration))

    db.session.commit()

    return success_response({'profile': profile.to_dict()})
