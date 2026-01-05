"""Admin API endpoints for card pool management."""

import logging

from flask import request

from app import db
from app.api import api_bp
from app.models.card import CardRarity, CardTemplate, UserCard
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.card_service import (
    BASE_TEMPLATES_COUNT,
    GENRE_CARD_EMOJIS,
    RARITY_POOL_FACTORS,
    CardService,
)
from app.utils.auth import admin_required
from app.utils.response import error_response, success_response

logger = logging.getLogger(__name__)

# Available genres
GENRES = ["magic", "fantasy", "scifi", "cyberpunk", "anime"]


@api_bp.route("/admin/card-pool", methods=["GET"])
@admin_required
def get_card_pool_status():
    """
    Get card pool status for all genres.

    Returns templates count, required count, and user count per genre.
    """
    result = {}

    for genre in GENRES:
        # Count users in genre
        users_count = (
            db.session.query(db.func.count(UserProfile.id))
            .filter(UserProfile.favorite_genre == genre)
            .scalar()
        ) or 0

        # Count active templates
        active_templates = CardTemplate.query.filter_by(
            genre=genre, is_active=True
        ).count()

        # Count inactive templates
        inactive_templates = CardTemplate.query.filter_by(
            genre=genre, is_active=False
        ).count()

        # Calculate required templates for each rarity
        rarity_status = {}
        for rarity in CardRarity:
            factor = RARITY_POOL_FACTORS.get(rarity)
            if factor is None:
                # Legendary - always unique
                required = "∞"
                needs_more = False
            else:
                required = BASE_TEMPLATES_COUNT + int(users_count * factor)
                needs_more = active_templates < required

            rarity_status[rarity.value] = {
                "factor": factor,
                "required": required,
                "needs_more": needs_more,
            }

        result[genre] = {
            "users_count": users_count,
            "active_templates": active_templates,
            "inactive_templates": inactive_templates,
            "total_templates": active_templates + inactive_templates,
            "rarity_requirements": rarity_status,
        }

    return success_response({"genres": result})


@api_bp.route("/admin/card-pool/<genre>/templates", methods=["GET"])
@admin_required
def get_genre_templates(genre: str):
    """
    Get all templates for a specific genre.
    """
    if genre not in GENRES:
        return error_response("invalid_genre", f"Genre must be one of: {GENRES}", 400)

    templates = (
        CardTemplate.query.filter_by(genre=genre)
        .order_by(CardTemplate.is_active.desc(), CardTemplate.created_at.desc())
        .all()
    )

    return success_response(
        {
            "genre": genre,
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "genre": t.genre,
                    "base_hp": t.base_hp,
                    "base_attack": t.base_attack,
                    "image_url": t.image_url,
                    "emoji": t.emoji,
                    "ai_generated": t.ai_generated,
                    "is_active": t.is_active,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in templates
            ],
            "total": len(templates),
        }
    )


@api_bp.route("/admin/card-pool/template/<int:template_id>/toggle", methods=["POST"])
@admin_required
def toggle_template_active(template_id: int):
    """
    Toggle template active status (enable/disable drops).
    """
    template = CardTemplate.query.get(template_id)

    if not template:
        return error_response("not_found", "Template not found", 404)

    template.is_active = not template.is_active
    db.session.commit()

    logger.info(
        f"Admin toggled template {template_id} ({template.name}) "
        f"is_active={template.is_active}"
    )

    return success_response(
        {
            "template_id": template_id,
            "is_active": template.is_active,
            "name": template.name,
        }
    )


@api_bp.route("/admin/card-pool/<genre>/generate", methods=["POST"])
@admin_required
def generate_template(genre: str):
    """
    Manually generate a new card template for a genre.

    Body:
    - rarity: string (optional, defaults to "common")
    - name: string (optional, will generate via AI if not provided)
    - description: string (optional)
    """
    if genre not in GENRES:
        return error_response("invalid_genre", f"Genre must be one of: {GENRES}", 400)

    data = request.get_json() or {}
    rarity_str = data.get("rarity", "common")
    custom_name = data.get("name")
    custom_description = data.get("description")

    try:
        rarity = CardRarity(rarity_str)
    except ValueError:
        return error_response(
            "invalid_rarity",
            f"Rarity must be one of: {[r.value for r in CardRarity]}",
            400,
        )

    card_service = CardService()

    if custom_name:
        # Create template with custom name
        import random

        emojis = GENRE_CARD_EMOJIS.get(genre, GENRE_CARD_EMOJIS["fantasy"])

        template = CardTemplate(
            name=custom_name,
            description=custom_description or f"Персонаж жанра {genre}",
            genre=genre,
            base_hp=50,
            base_attack=15,
            image_url=None,
            emoji=random.choice(emojis),
            ai_generated=False,
            is_active=True,
        )
    else:
        # Generate via AI
        from app.models.character import GENRE_THEMES

        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])
        name, description = card_service._generate_card_text(
            genre, genre_info, rarity, "Admin generated card"
        )

        import random

        emojis = GENRE_CARD_EMOJIS.get(genre, GENRE_CARD_EMOJIS["fantasy"])

        template = CardTemplate(
            name=name,
            description=description,
            genre=genre,
            base_hp=50,
            base_attack=15,
            image_url=None,
            emoji=random.choice(emojis),
            ai_generated=True,
            is_active=True,
        )

    db.session.add(template)
    db.session.commit()

    logger.info(f"Admin generated template: {template.name} ({genre}, {rarity.value})")

    return success_response(
        {
            "template": {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "genre": template.genre,
                "emoji": template.emoji,
                "is_active": template.is_active,
                "ai_generated": template.ai_generated,
            }
        }
    )


@api_bp.route(
    "/admin/card-pool/template/<int:template_id>/generate-image", methods=["POST"]
)
@admin_required
def generate_template_image(template_id: int):
    """
    Generate image for a template that doesn't have one.
    """
    template = CardTemplate.query.get(template_id)

    if not template:
        return error_response("not_found", "Template not found", 404)

    if template.image_url:
        return success_response(
            {
                "template_id": template_id,
                "image_url": template.image_url,
                "already_exists": True,
            }
        )

    card_service = CardService()

    # Generate image (use rare rarity for decent quality)
    image_url = card_service._generate_card_image(
        template.name, template.genre, CardRarity.RARE
    )

    if image_url:
        template.image_url = image_url
        db.session.commit()

        logger.info(f"Admin generated image for template {template_id}: {image_url}")

        return success_response(
            {
                "template_id": template_id,
                "image_url": image_url,
            }
        )
    else:
        return error_response("generation_failed", "Failed to generate image", 500)


@api_bp.route("/admin/card-pool/generation-schedule", methods=["GET"])
@admin_required
def get_generation_schedule():
    """
    Get when new cards should be generated for each genre/rarity combo.

    Shows:
    - Current template count
    - Required template count
    - How many more users needed before next card generation
    """
    result = {}

    for genre in GENRES:
        # Count users in genre
        users_count = (
            db.session.query(db.func.count(UserProfile.id))
            .filter(UserProfile.favorite_genre == genre)
            .scalar()
        ) or 0

        # Count active templates
        templates_count = CardTemplate.query.filter_by(
            genre=genre, is_active=True
        ).count()

        rarity_schedule = {}
        for rarity in CardRarity:
            factor = RARITY_POOL_FACTORS.get(rarity)

            if factor is None:
                # Legendary - always unique
                rarity_schedule[rarity.value] = {
                    "status": "always_new",
                    "message": "Всегда генерируется новая карта",
                }
                continue

            required = BASE_TEMPLATES_COUNT + int(users_count * factor)

            if templates_count >= required:
                # How many more users needed to trigger new generation?
                # required = BASE + users * factor
                # templates_count < BASE + users * factor
                # users > (templates_count - BASE) / factor
                users_for_next = (
                    int((templates_count - BASE_TEMPLATES_COUNT) / factor) + 1
                )
                users_needed = max(0, users_for_next - users_count)

                rarity_schedule[rarity.value] = {
                    "status": "sufficient",
                    "current": templates_count,
                    "required": required,
                    "users_needed_for_next": users_needed,
                    "message": (
                        f"Достаточно карт. Новая при +{users_needed} юзерах"
                        if users_needed > 0
                        else "Новая карта при след. дропе"
                    ),
                }
            else:
                cards_needed = required - templates_count
                rarity_schedule[rarity.value] = {
                    "status": "needs_generation",
                    "current": templates_count,
                    "required": required,
                    "cards_needed": cards_needed,
                    "message": f"Нужно сгенерировать ещё {cards_needed} карт",
                }

        result[genre] = {
            "users_count": users_count,
            "templates_count": templates_count,
            "schedule": rarity_schedule,
        }

    return success_response({"genres": result})


@api_bp.route("/admin/stats", methods=["GET"])
@admin_required
def get_admin_stats():
    """
    Get general admin statistics.
    """
    total_users = User.query.count()
    total_templates = CardTemplate.query.count()
    active_templates = CardTemplate.query.filter_by(is_active=True).count()
    total_user_cards = UserCard.query.filter_by(is_destroyed=False).count()

    # Cards by rarity
    cards_by_rarity = {}
    for rarity in CardRarity:
        count = UserCard.query.filter_by(
            rarity=rarity.value, is_destroyed=False
        ).count()
        cards_by_rarity[rarity.value] = count

    # Users by genre
    users_by_genre = {}
    for genre in GENRES:
        count = UserProfile.query.filter_by(favorite_genre=genre).count()
        users_by_genre[genre] = count

    return success_response(
        {
            "total_users": total_users,
            "total_templates": total_templates,
            "active_templates": active_templates,
            "total_user_cards": total_user_cards,
            "cards_by_rarity": cards_by_rarity,
            "users_by_genre": users_by_genre,
        }
    )
