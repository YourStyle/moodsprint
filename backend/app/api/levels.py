"""Level rewards API endpoints."""

from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api import api_bp
from app.models.user import User
from app.services.level_service import LevelService
from app.utils.response import success_response


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

    return success_response(response_data)
