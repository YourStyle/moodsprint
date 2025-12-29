"""Campaign/Story mode API endpoints."""

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api import api_bp
from app.services.campaign_service import CampaignService
from app.utils import not_found, success_response, validation_error

# ============ Campaign Overview ============


@api_bp.route("/campaign", methods=["GET"])
@jwt_required()
def get_campaign_overview():
    """Get campaign overview with user's progress."""
    user_id = int(get_jwt_identity())

    service = CampaignService()
    result = service.get_campaign_overview(user_id)

    return success_response(result)


@api_bp.route("/campaign/progress", methods=["GET"])
@jwt_required()
def get_campaign_progress():
    """Get user's campaign progress only."""
    user_id = int(get_jwt_identity())

    service = CampaignService()
    progress = service.get_user_progress(user_id)

    return success_response({"progress": progress.to_dict()})


# ============ Chapters ============


@api_bp.route("/campaign/chapters/<int:chapter_number>", methods=["GET"])
@jwt_required()
def get_chapter_details(chapter_number: int):
    """Get chapter details with levels."""
    user_id = int(get_jwt_identity())

    service = CampaignService()
    result = service.get_chapter_details(user_id, chapter_number)

    if "error" in result:
        error_messages = {
            "chapter_not_found": "Глава не найдена",
            "chapter_locked": "Глава ещё не открыта",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


# ============ Levels ============


@api_bp.route("/campaign/levels/<int:level_id>/start", methods=["POST"])
@jwt_required()
def start_campaign_level(level_id: int):
    """
    Start a campaign level.

    Returns level data for initiating battle.
    """
    user_id = int(get_jwt_identity())

    service = CampaignService()
    result = service.start_level(user_id, level_id)

    if "error" in result:
        error_messages = {
            "level_not_found": "Уровень не найден",
            "chapter_locked": "Глава ещё не открыта",
            "previous_level_not_completed": "Сначала пройдите предыдущий уровень",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


@api_bp.route("/campaign/levels/<int:level_id>/dialogue-choice", methods=["POST"])
@jwt_required()
def process_dialogue_choice(level_id: int):
    """
    Process a dialogue choice with an event.

    Request body:
    {
        "action": "skip_battle" | "buff_player" | "debuff_monster" | "bonus_xp" | "heal_cards"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    action = data.get("action")
    if not action:
        return validation_error({"error": "Действие не указано"})

    service = CampaignService()
    result = service.process_dialogue_choice(
        user_id=user_id,
        level_id=level_id,
        choice_action=action,
    )

    if "error" in result:
        return not_found("Уровень не найден")

    return success_response(result)


@api_bp.route("/campaign/levels/<int:level_id>/complete", methods=["POST"])
@jwt_required()
def complete_campaign_level(level_id: int):
    """
    Complete a campaign level after battle.

    Request body:
    {
        "won": true,
        "rounds": 5,
        "hp_remaining": 50,
        "cards_lost": 0
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    won = data.get("won", False)
    rounds = data.get("rounds", 10)
    hp_remaining = data.get("hp_remaining", 0)
    cards_lost = data.get("cards_lost", 0)

    service = CampaignService()
    result = service.complete_level(
        user_id=user_id,
        level_id=level_id,
        won=won,
        rounds=rounds,
        hp_remaining=hp_remaining,
        cards_lost=cards_lost,
    )

    if "error" in result:
        return not_found("Уровень не найден")

    return success_response(result)


@api_bp.route("/campaign/levels/<int:level_id>/battle-config", methods=["GET"])
@jwt_required()
def get_level_battle_config(level_id: int):
    """Get battle configuration for a campaign level."""
    service = CampaignService()
    result = service.get_level_battle_config(level_id)

    if "error" in result:
        error_messages = {
            "level_not_found": "Уровень не найден",
            "monster_not_configured": "Монстр для уровня не настроен",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response(result)


# ============ Admin/Seed ============


@api_bp.route("/campaign/seed", methods=["POST"])
@jwt_required()
def seed_campaign():
    """
    Seed campaign data (admin only, for testing).

    Creates initial chapters and levels if not exist.
    """
    from app.services.campaign_service import seed_campaign_data

    try:
        seed_campaign_data()
        return success_response({"message": "Campaign data seeded successfully"})
    except Exception as e:
        return validation_error({"error": str(e)})
