"""Level rewards API endpoints."""

import logging

from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.api import api_bp
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.level_service import LevelService
from app.utils.response import success_response

logger = logging.getLogger(__name__)


@api_bp.route("/level-rewards", methods=["GET"])
@jwt_required()
def get_all_level_rewards():
    """Get all level rewards grouped by level (for upcoming rewards preview)."""
    service = LevelService()
    grouped = service.get_all_level_rewards()
    return success_response({"level_rewards": grouped})


@api_bp.route("/level-rewards/<int:level>", methods=["GET"])
@jwt_required()
def get_level_rewards(level: int):
    """Get rewards for a specific level."""
    service = LevelService()
    rewards = service.get_rewards_for_level(level)
    return success_response({"level": level, "rewards": rewards})


@api_bp.route("/level-rewards/catch-up", methods=["POST"])
@jwt_required()
def catch_up_level_rewards():
    """Grant retroactive level rewards for existing users.

    Users who were already above level 1 when the reward system launched
    will receive all rewards they missed in a single batch.
    Also handles retroactive energy limit increases.
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return success_response({"has_rewards": False, "rewards": [], "new_level": 1})

    current_level = user.level
    service = LevelService()
    result = service.grant_level_rewards(user_id, current_level)

    response_data = {
        "has_rewards": result["granted"],
        "rewards": result["rewards"],
        "new_level": current_level,
    }

    # Include genre unlock info if any genre_unlock rewards were granted
    if result["granted"]:
        try:
            from app.services.card_service import CardService

            unlock_info = CardService().check_genre_unlock(user_id)
            if unlock_info:
                response_data["genre_unlock_available"] = unlock_info
        except Exception:
            pass

    # Check if user needs retroactive energy limit increase
    try:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile:
            db.session.refresh(profile)  # Get fresh data after grant_level_rewards
        if profile and (profile.energy_limit_updated_to_level or 0) < current_level:
            # Calculate expected max energy
            # Auto +1 every 3 levels (3, 6, 9, 12, 15, ...)
            auto_increase = current_level // 3

            # Configured max_energy rewards for levels 2..current_level
            from app.models.level_reward import LevelReward

            configured = (
                db.session.query(
                    db.func.coalesce(
                        db.func.sum(LevelReward.reward_value["amount"].as_integer()),
                        0,
                    )
                )
                .filter(
                    LevelReward.reward_type == "max_energy",
                    LevelReward.level <= current_level,
                    LevelReward.level >= 2,
                    LevelReward.is_active.is_(True),
                )
                .scalar()
                or 0
            )

            expected_max = 5 + auto_increase + configured
            old_max = profile.max_campaign_energy or 5

            if expected_max > old_max:
                profile.max_campaign_energy = expected_max
                profile.campaign_energy = expected_max  # fill up
                profile.energy_limit_updated_to_level = current_level
                db.session.commit()

                response_data["energy_limit_increased"] = {
                    "old_max": old_max,
                    "new_max": expected_max,
                    "increase": expected_max - old_max,
                }
            else:
                profile.energy_limit_updated_to_level = current_level
                db.session.commit()
    except Exception as e:
        logger.warning(f"Failed to check energy limit catch-up: {e}")

    return success_response(response_data)
