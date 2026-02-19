"""Card trading service — extracted from card_service.py."""

import logging
from datetime import datetime

from app import db
from app.models.card import CardTrade, Friendship, UserCard

logger = logging.getLogger(__name__)


class CardTradingService:
    def create_trade_offer(
        self,
        sender_id: int,
        receiver_id: int,
        sender_card_id: int | None = None,
        receiver_card_id: int | None = None,
        message: str | None = None,
        sender_card_ids: list[int] | None = None,
        receiver_card_ids: list[int] | None = None,
    ) -> dict:
        """Create a card trade offer (supports single or multiple cards)."""
        is_friend = Friendship.query.filter(
            (
                (Friendship.user_id == sender_id)
                & (Friendship.friend_id == receiver_id)
                | (Friendship.user_id == receiver_id)
                & (Friendship.friend_id == sender_id)
            )
            & (Friendship.status == "accepted")
        ).first()

        if not is_friend:
            return {"success": False, "error": "not_friends"}

        actual_sender_ids = sender_card_ids or (
            [sender_card_id] if sender_card_id else []
        )
        actual_receiver_ids = receiver_card_ids or (
            [receiver_card_id] if receiver_card_id else []
        )

        if not actual_sender_ids:
            return {"success": False, "error": "no_sender_cards"}

        sender_cards = UserCard.query.filter(
            UserCard.id.in_(actual_sender_ids),
            UserCard.user_id == sender_id,
            UserCard.is_tradeable.is_(True),
            UserCard.is_destroyed.is_(False),
        ).all()

        if len(sender_cards) != len(actual_sender_ids):
            return {"success": False, "error": "sender_card_invalid"}

        if actual_receiver_ids:
            receiver_cards = UserCard.query.filter(
                UserCard.id.in_(actual_receiver_ids),
                UserCard.user_id == receiver_id,
                UserCard.is_tradeable.is_(True),
                UserCard.is_destroyed.is_(False),
            ).all()

            if len(receiver_cards) != len(actual_receiver_ids):
                return {"success": False, "error": "receiver_card_invalid"}

        trade = CardTrade(
            sender_id=sender_id,
            receiver_id=receiver_id,
            sender_card_id=(
                actual_sender_ids[0] if len(actual_sender_ids) == 1 else None
            ),
            receiver_card_id=(
                actual_receiver_ids[0] if len(actual_receiver_ids) == 1 else None
            ),
            sender_card_ids=actual_sender_ids if len(actual_sender_ids) > 1 else None,
            receiver_card_ids=(
                actual_receiver_ids if len(actual_receiver_ids) > 1 else None
            ),
            message=message,
            status="pending",
        )
        db.session.add(trade)
        db.session.commit()

        return {"success": True, "trade": trade.to_dict()}

    def accept_trade(self, user_id: int, trade_id: int) -> dict:
        """Accept a trade offer (supports multi-card trades)."""
        trade = CardTrade.query.filter_by(
            id=trade_id, receiver_id=user_id, status="pending"
        ).first()

        if not trade:
            return {"success": False, "error": "trade_not_found"}

        sender_card_ids = trade.sender_card_ids or (
            [trade.sender_card_id] if trade.sender_card_id else []
        )
        receiver_card_ids = trade.receiver_card_ids or (
            [trade.receiver_card_id] if trade.receiver_card_id else []
        )

        if sender_card_ids:
            sender_cards = UserCard.query.filter(UserCard.id.in_(sender_card_ids)).all()
            for card in sender_cards:
                card.user_id = trade.receiver_id
                card.is_in_deck = False

        if receiver_card_ids:
            receiver_cards = UserCard.query.filter(
                UserCard.id.in_(receiver_card_ids)
            ).all()
            for card in receiver_cards:
                card.user_id = trade.sender_id
                card.is_in_deck = False

        trade.status = "accepted"
        trade.completed_at = datetime.utcnow()
        db.session.commit()

        return {"success": True, "trade": trade.to_dict()}

    def reject_trade(self, user_id: int, trade_id: int) -> dict:
        """Reject a trade offer."""
        trade = CardTrade.query.filter_by(
            id=trade_id, receiver_id=user_id, status="pending"
        ).first()

        if not trade:
            return {"success": False, "error": "trade_not_found"}

        trade.status = "rejected"
        db.session.commit()

        return {"success": True}

    def get_pending_trades(self, user_id: int) -> list[CardTrade]:
        """Get pending trades for user (both sent and received)."""
        return CardTrade.query.filter(
            ((CardTrade.sender_id == user_id) | (CardTrade.receiver_id == user_id))
            & (CardTrade.status == "pending")
        ).all()
