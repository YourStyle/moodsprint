"""Companion system service — extracted from card_service.py."""

import logging

from app import db
from app.models.card import UserCard

logger = logging.getLogger(__name__)


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

        return {"success": True, "card": card.to_dict(lang)}

    def remove_companion(self, user_id: int) -> dict:
        """Remove the current companion."""
        current = UserCard.query.filter_by(user_id=user_id, is_companion=True).first()
        if current:
            current.is_companion = False
            db.session.commit()
        return {"success": True}

    def get_companion(self, user_id: int) -> UserCard | None:
        """Get user's active companion card."""
        return UserCard.query.filter_by(
            user_id=user_id, is_companion=True, is_destroyed=False
        ).first()
