"""Showcase system service — extracted from card_service.py."""

import logging

from app import db
from app.models.card import UserCard

logger = logging.getLogger(__name__)


class ShowcaseService:
    def set_showcase(
        self, user_id: int, card_id: int, slot: int, lang: str = "en"
    ) -> dict:
        """Set a card in a showcase slot (1-3)."""
        if slot not in (1, 2, 3):
            return {"success": False, "error": "invalid_slot"}

        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return {"success": False, "error": "card_not_found"}

        if card.is_destroyed:
            return {"success": False, "error": "card_destroyed"}

        current_in_slot = UserCard.query.filter_by(
            user_id=user_id, is_showcase=True, showcase_slot=slot
        ).first()
        if current_in_slot:
            current_in_slot.is_showcase = False
            current_in_slot.showcase_slot = None

        if card.is_showcase:
            card.is_showcase = False
            card.showcase_slot = None

        card.is_showcase = True
        card.showcase_slot = slot
        db.session.commit()

        return {"success": True, "card": card.to_dict(lang)}

    def remove_showcase(self, user_id: int, slot: int) -> dict:
        """Remove a card from a showcase slot."""
        if slot not in (1, 2, 3):
            return {"success": False, "error": "invalid_slot"}

        card = UserCard.query.filter_by(
            user_id=user_id, is_showcase=True, showcase_slot=slot
        ).first()
        if card:
            card.is_showcase = False
            card.showcase_slot = None
            db.session.commit()

        return {"success": True}

    def get_showcase_cards(self, user_id: int, lang: str = "en") -> list[dict]:
        """Get user's 3 showcase card slots."""
        cards = (
            UserCard.query.filter_by(
                user_id=user_id, is_showcase=True, is_destroyed=False
            )
            .order_by(UserCard.showcase_slot)
            .all()
        )

        slots = {1: None, 2: None, 3: None}
        for card in cards:
            if card.showcase_slot in slots:
                slots[card.showcase_slot] = card.to_dict(lang)

        return [slots[1], slots[2], slots[3]]
