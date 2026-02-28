"""Cosmetics service for card frames and profile frames.

All cosmetic items are defined as code constants. Users buy them
with Sparks and equip one card frame + one profile frame at a time.
"""

import logging

from sqlalchemy.orm.attributes import flag_modified

from app import db
from app.models.user import User
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)


# Card frame definitions (CSS gradient/border styles applied on frontend)
CARD_FRAMES = {
    "card_frame_golden": {
        "id": "card_frame_golden",
        "type": "card_frame",
        "name_ru": "Золотая рамка",
        "name_en": "Golden Frame",
        "description_ru": "Сияющая золотая рамка для твоих карт",
        "description_en": "Shining golden frame for your cards",
        "price_sparks": 500,
        "css": "border-2 border-yellow-400 shadow-[0_0_12px_rgba(250,204,21,0.4)]",
        "preview_gradient": "linear-gradient(135deg, #f59e0b, #fbbf24, #f59e0b)",
        "min_level": 1,
    },
    "card_frame_neon": {
        "id": "card_frame_neon",
        "type": "card_frame",
        "name_ru": "Неоновая рамка",
        "name_en": "Neon Frame",
        "description_ru": "Яркий неон для твоей колоды",
        "description_en": "Bright neon for your deck",
        "price_sparks": 800,
        "css": "border-2 border-cyan-400 shadow-[0_0_16px_rgba(34,211,238,0.5)]",
        "preview_gradient": "linear-gradient(135deg, #06b6d4, #22d3ee, #06b6d4)",
        "min_level": 5,
    },
    "card_frame_fire": {
        "id": "card_frame_fire",
        "type": "card_frame",
        "name_ru": "Огненная рамка",
        "name_en": "Fire Frame",
        "description_ru": "Пылающая рамка для настоящих бойцов",
        "description_en": "Blazing frame for true warriors",
        "price_sparks": 1200,
        "css": "border-2 border-orange-500 shadow-[0_0_20px_rgba(249,115,22,0.5)]",
        "preview_gradient": "linear-gradient(135deg, #ef4444, #f97316, #ef4444)",
        "min_level": 10,
    },
    "card_frame_cosmic": {
        "id": "card_frame_cosmic",
        "type": "card_frame",
        "name_ru": "Космическая рамка",
        "name_en": "Cosmic Frame",
        "description_ru": "Из глубин космоса — для самых преданных",
        "description_en": "From the depths of space — for the devoted",
        "price_sparks": 2000,
        "css": "border-2 border-purple-400 shadow-[0_0_24px_rgba(192,132,252,0.5)]",
        "preview_gradient": "linear-gradient(135deg, #7c3aed, #c084fc, #7c3aed)",
        "min_level": 15,
    },
}

# Profile frame definitions
PROFILE_FRAMES = {
    "profile_frame_silver": {
        "id": "profile_frame_silver",
        "type": "profile_frame",
        "name_ru": "Серебряная рамка",
        "name_en": "Silver Frame",
        "description_ru": "Элегантная серебряная рамка профиля",
        "description_en": "Elegant silver profile frame",
        "price_sparks": 300,
        "css": "ring-2 ring-gray-300 ring-offset-2 ring-offset-gray-900",
        "preview_gradient": "linear-gradient(135deg, #9ca3af, #d1d5db, #9ca3af)",
        "min_level": 1,
    },
    "profile_frame_emerald": {
        "id": "profile_frame_emerald",
        "type": "profile_frame",
        "name_ru": "Изумрудная рамка",
        "name_en": "Emerald Frame",
        "description_ru": "Зелёный блеск для твоего профиля",
        "description_en": "Green sparkle for your profile",
        "price_sparks": 600,
        "css": "ring-2 ring-emerald-400 ring-offset-2 ring-offset-gray-900",
        "preview_gradient": "linear-gradient(135deg, #059669, #34d399, #059669)",
        "min_level": 5,
    },
    "profile_frame_ruby": {
        "id": "profile_frame_ruby",
        "type": "profile_frame",
        "name_ru": "Рубиновая рамка",
        "name_en": "Ruby Frame",
        "description_ru": "Драгоценная рамка для ценителей",
        "description_en": "Precious frame for connoisseurs",
        "price_sparks": 1000,
        "css": "ring-2 ring-rose-400 ring-offset-2 ring-offset-gray-900",
        "preview_gradient": "linear-gradient(135deg, #e11d48, #fb7185, #e11d48)",
        "min_level": 10,
    },
    "profile_frame_diamond": {
        "id": "profile_frame_diamond",
        "type": "profile_frame",
        "name_ru": "Бриллиантовая рамка",
        "name_en": "Diamond Frame",
        "description_ru": "Сверкающая рамка для легенд",
        "description_en": "Sparkling frame for legends",
        "price_sparks": 1500,
        "css": (
            "ring-2 ring-sky-300 ring-offset-2 ring-offset-gray-900 "
            "shadow-[0_0_12px_rgba(125,211,252,0.4)]"
        ),
        "preview_gradient": "linear-gradient(135deg, #0ea5e9, #7dd3fc, #0ea5e9)",
        "min_level": 15,
    },
}

ALL_COSMETICS = {**CARD_FRAMES, **PROFILE_FRAMES}


class CosmeticsService:
    """Service for managing cosmetic items."""

    def get_all_cosmetics(self, lang: str = "ru") -> list[dict]:
        """Get all available cosmetics with localized names."""
        result = []
        for item in ALL_COSMETICS.values():
            result.append(self._localize(item, lang))
        return result

    def get_user_cosmetics(self, user_id: int, lang: str = "ru") -> dict:
        """Get user's owned cosmetics and equipped items."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        owned = profile.owned_cosmetics if profile else []
        equipped_card_frame = profile.equipped_card_frame if profile else None
        equipped_profile_frame = profile.equipped_profile_frame if profile else None

        items = []
        for cosmetic_id in owned:
            cosmetic = ALL_COSMETICS.get(cosmetic_id)
            if cosmetic:
                item = self._localize(cosmetic, lang)
                item["is_equipped"] = (
                    cosmetic_id == equipped_card_frame
                    or cosmetic_id == equipped_profile_frame
                )
                items.append(item)

        return {
            "owned": items,
            "equipped_card_frame": equipped_card_frame,
            "equipped_profile_frame": equipped_profile_frame,
        }

    def buy_cosmetic(self, user_id: int, cosmetic_id: str) -> dict:
        """Buy a cosmetic item with Sparks."""
        cosmetic = ALL_COSMETICS.get(cosmetic_id)
        if not cosmetic:
            return {"error": "cosmetic_not_found"}

        user = User.query.get(user_id)
        if not user:
            return {"error": "user_not_found"}

        # Check level requirement
        if user.level < cosmetic["min_level"]:
            return {"error": "level_too_low", "required_level": cosmetic["min_level"]}

        # Check if already owned
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"error": "profile_not_found"}

        owned = profile.owned_cosmetics or []
        if cosmetic_id in owned:
            return {"error": "already_owned"}

        # Check Sparks balance
        price = cosmetic["price_sparks"]
        if (user.sparks or 0) < price:
            return {"error": "not_enough_sparks", "needed": price}

        # Deduct Sparks
        user.spend_sparks(price)

        # Add to owned
        owned.append(cosmetic_id)
        profile.owned_cosmetics = owned
        flag_modified(profile, "owned_cosmetics")

        # Record transaction
        from app.models.sparks import SparksTransaction

        txn = SparksTransaction(
            user_id=user_id,
            amount=-price,
            type="cosmetic_purchase",
            description=f"Покупка: {cosmetic.get('name_ru', cosmetic_id)}",
        )
        db.session.add(txn)
        db.session.commit()

        return {"success": True, "cosmetic_id": cosmetic_id}

    def equip_cosmetic(self, user_id: int, cosmetic_id: str | None) -> dict:
        """Equip a cosmetic (or unequip if cosmetic_id is None)."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"error": "profile_not_found"}

        if cosmetic_id is None:
            # Unequip — need to know which type
            return {"error": "specify_cosmetic_or_type"}

        cosmetic = ALL_COSMETICS.get(cosmetic_id)
        if not cosmetic:
            return {"error": "cosmetic_not_found"}

        # Check if owned
        owned = profile.owned_cosmetics or []
        if cosmetic_id not in owned:
            return {"error": "not_owned"}

        # Equip based on type
        if cosmetic["type"] == "card_frame":
            profile.equipped_card_frame = cosmetic_id
        elif cosmetic["type"] == "profile_frame":
            profile.equipped_profile_frame = cosmetic_id

        db.session.commit()
        return {"success": True, "cosmetic_id": cosmetic_id}

    def unequip_cosmetic(self, user_id: int, cosmetic_type: str) -> dict:
        """Unequip a cosmetic by type (card_frame or profile_frame)."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            return {"error": "profile_not_found"}

        if cosmetic_type == "card_frame":
            profile.equipped_card_frame = None
        elif cosmetic_type == "profile_frame":
            profile.equipped_profile_frame = None
        else:
            return {"error": "invalid_type"}

        db.session.commit()
        return {"success": True}

    @staticmethod
    def _localize(item: dict, lang: str) -> dict:
        """Create a localized copy of a cosmetic item."""
        result = {
            "id": item["id"],
            "type": item["type"],
            "name": item.get(f"name_{lang}", item.get("name_ru", "")),
            "description": item.get(
                f"description_{lang}", item.get("description_ru", "")
            ),
            "price_sparks": item["price_sparks"],
            "css": item["css"],
            "preview_gradient": item["preview_gradient"],
            "min_level": item["min_level"],
        }
        return result
