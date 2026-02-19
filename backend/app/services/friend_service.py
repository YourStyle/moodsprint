"""Friend system service — extracted from card_service.py."""

import logging
from datetime import datetime

from app import db
from app.models.card import Friendship

logger = logging.getLogger(__name__)


class FriendService:
    def send_friend_request(self, user_id: int, friend_id: int) -> dict:
        """Send a friend request."""
        if user_id == friend_id:
            return {"success": False, "error": "cannot_friend_self"}

        existing = Friendship.query.filter(
            ((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id))
            | ((Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
        ).first()

        if existing:
            if existing.status == "accepted":
                return {"success": False, "error": "already_friends"}
            elif existing.status == "pending":
                return {"success": False, "error": "request_pending"}
            elif existing.status == "blocked":
                return {"success": False, "error": "blocked"}

        friendship = Friendship(user_id=user_id, friend_id=friend_id, status="pending")
        db.session.add(friendship)
        db.session.commit()

        return {"success": True, "friendship": friendship.to_dict()}

    def accept_friend_request(self, user_id: int, request_id: int) -> dict:
        """Accept a friend request."""
        friendship = Friendship.query.filter_by(
            id=request_id, friend_id=user_id, status="pending"
        ).first()

        if not friendship:
            return {"success": False, "error": "request_not_found"}

        friendship.status = "accepted"
        friendship.accepted_at = datetime.utcnow()
        db.session.commit()

        return {"success": True, "friendship": friendship.to_dict()}

    def get_friends(self, user_id: int) -> list[dict]:
        """Get user's friends list."""
        friendships = Friendship.query.filter(
            ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id))
            & (Friendship.status == "accepted")
        ).all()

        friends = []
        for f in friendships:
            friend_id = f.friend_id if f.user_id == user_id else f.user_id
            friends.append(
                {
                    "friendship_id": f.id,
                    "friend_id": friend_id,
                    "since": f.accepted_at.isoformat() if f.accepted_at else None,
                }
            )

        return friends

    def get_pending_requests(self, user_id: int) -> list[Friendship]:
        """Get pending friend requests for user."""
        return Friendship.query.filter_by(friend_id=user_id, status="pending").all()

    def remove_friend(self, user_id: int, friend_id: int) -> dict:
        """Remove a friendship between two users."""
        friendship = Friendship.query.filter(
            ((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id))
            | ((Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
        ).first()

        if not friendship:
            return {"error": "friendship_not_found"}

        db.session.delete(friendship)
        db.session.commit()
        return {"success": True}
