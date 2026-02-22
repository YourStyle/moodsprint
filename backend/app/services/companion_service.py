"""Companion system service — extracted from card_service.py."""

import json
import logging

from app import db
from app.models.card import UserCard

logger = logging.getLogger(__name__)

COMPANION_CACHE_TTL = 300  # 5 minutes
COMPANION_CACHE_PREFIX = "companion:"


def _companion_cache_key(user_id: int) -> str:
    return f"{COMPANION_CACHE_PREFIX}{user_id}"


def _invalidate_companion_cache(user_id: int) -> None:
    """Remove companion from Redis cache."""
    try:
        from app.extensions import get_redis_client

        r = get_redis_client()
        r.delete(_companion_cache_key(user_id))
    except Exception as e:
        logger.warning(f"Failed to invalidate companion cache: {e}")


class CompanionService:
    def set_companion(self, user_id: int, card_id: int, lang: str = "en") -> dict:
        """Set a card as the user's companion."""
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return {"success": False, "error": "card_not_found"}

        if card.is_destroyed:
            return {"success": False, "error": "card_destroyed"}

        current_companion = UserCard.query.filter_by(
            user_id=user_id, is_companion=True
        ).first()
        if current_companion:
            current_companion.is_companion = False

        card.is_companion = True
        db.session.commit()

        _invalidate_companion_cache(user_id)

        return {"success": True, "card": card.to_dict(lang)}

    def remove_companion(self, user_id: int) -> dict:
        """Remove the current companion."""
        current = UserCard.query.filter_by(user_id=user_id, is_companion=True).first()
        if current:
            current.is_companion = False
            db.session.commit()

        _invalidate_companion_cache(user_id)

        return {"success": True}

    def get_companion(self, user_id: int) -> UserCard | None:
        """Get user's active companion card (with Redis caching)."""
        # Try Redis cache first
        try:
            from app.extensions import get_redis_client

            r = get_redis_client()
            cached = r.get(_companion_cache_key(user_id))
            if cached is not None:
                data = json.loads(cached)
                if data is None:
                    # Cached "no companion" result
                    return None
                # Load from DB by ID (avoids serialization issues)
                return UserCard.query.get(data["id"])
        except Exception as e:
            logger.warning(f"Companion cache read error: {e}")

        # Cache miss — query DB
        companion = UserCard.query.filter_by(
            user_id=user_id, is_companion=True, is_destroyed=False
        ).first()

        # Store in cache
        try:
            from app.extensions import get_redis_client

            r = get_redis_client()
            cache_val = json.dumps({"id": companion.id} if companion else None)
            r.set(_companion_cache_key(user_id), cache_val, ex=COMPANION_CACHE_TTL)
        except Exception as e:
            logger.warning(f"Companion cache write error: {e}")

        return companion
