"""Authentication API endpoints."""

import logging
from datetime import datetime

from flask import request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app import db
from app.api import api_bp
from app.models import User
from app.models.card import Friendship
from app.utils import (
    parse_telegram_user,
    success_response,
    unauthorized,
    validate_telegram_data,
    validation_error,
)

logger = logging.getLogger(__name__)


@api_bp.route("/auth/telegram", methods=["POST"])
def authenticate_telegram():
    """
    Authenticate user via Telegram WebApp initData.

    Request body:
    {
        "init_data": "query_id=...&user=...&auth_date=...&hash=...",
        "referrer_id": 123  // optional, from invite link
    }
    """
    data = request.get_json()

    if not data or "init_data" not in data:
        return validation_error({"init_data": "init_data is required"})

    init_data = data["init_data"]

    # Validate Telegram data
    if not validate_telegram_data(init_data):
        return unauthorized("Invalid Telegram authentication data")

    # Parse user from initData
    telegram_user = parse_telegram_user(init_data)
    if not telegram_user or not telegram_user.get("id"):
        return validation_error({"user": "Could not parse user data"})

    telegram_id = telegram_user["id"]

    # Find or create user
    user = User.query.filter_by(telegram_id=telegram_id).first()
    is_new_user = user is None
    referrer_id = data.get("referrer_id")
    friendship_created = False
    referral_rewards = {}

    if user:
        # Update user info
        user.username = telegram_user.get("username")
        user.first_name = telegram_user.get("first_name")
        user.last_name = telegram_user.get("last_name")
        user.photo_url = telegram_user.get("photo_url")

        # Handle referral for existing user
        if referrer_id and referrer_id != user.id:
            referrer = User.query.get(referrer_id)
            if referrer:
                # Check if friendship already exists
                existing_friendship = Friendship.query.filter(
                    db.or_(
                        db.and_(
                            Friendship.user_id == referrer_id,
                            Friendship.friend_id == user.id,
                        ),
                        db.and_(
                            Friendship.user_id == user.id,
                            Friendship.friend_id == referrer_id,
                        ),
                    )
                ).first()

                if not existing_friendship:
                    # Create new friendship
                    friendship = Friendship(
                        user_id=referrer_id,
                        friend_id=user.id,
                        status="accepted",
                        accepted_at=datetime.utcnow(),
                    )
                    db.session.add(friendship)
                    friendship_created = True
                    logger.info(
                        f"Created friendship between {referrer_id} and {user.id} via invite link"
                    )

                    # Give rewards to both users
                    try:
                        from app.services.card_service import CardService

                        card_service = CardService()

                        # Give rare+ card to referrer
                        referrer_card = card_service.generate_referral_reward(
                            referrer_id
                        )
                        if referrer_card:
                            referral_rewards["referrer_rewarded"] = True
                            referral_rewards["referrer_card"] = referrer_card.to_dict()
                            logger.info(
                                f"Gave referral reward to user {referrer_id}: "
                                f"{referrer_card.name} ({referrer_card.rarity})"
                            )

                        # Give a card to the invitee as well (uncommon-rare)
                        from app.models.card import CardRarity

                        invitee_card = card_service.generate_card_for_task(
                            user_id=user.id,
                            task_id=None,
                            task_title="Бонус за принятие приглашения",
                            difficulty="medium",
                            max_rarity=CardRarity.RARE,
                        )
                        if invitee_card:
                            referral_rewards["invitee_card"] = invitee_card.to_dict()
                            logger.info(
                                f"Gave invite bonus to user {user.id}: "
                                f"{invitee_card.name} ({invitee_card.rarity})"
                            )
                    except Exception as e:
                        logger.error(f"Failed to give referral rewards: {e}")
    else:
        # Create new user
        # Validate referrer exists
        if referrer_id:
            referrer = User.query.get(referrer_id)
            if not referrer:
                referrer_id = None

        user = User(
            telegram_id=telegram_id,
            username=telegram_user.get("username"),
            first_name=telegram_user.get("first_name"),
            last_name=telegram_user.get("last_name"),
            photo_url=telegram_user.get("photo_url"),
            referred_by=referrer_id,
        )
        db.session.add(user)
        db.session.flush()  # Get user.id before commit

        # Auto-create accepted friendship with referrer
        if referrer_id:
            friendship = Friendship(
                user_id=referrer_id,
                friend_id=user.id,
                status="accepted",
                accepted_at=datetime.utcnow(),
            )
            db.session.add(friendship)
            friendship_created = True

    db.session.commit()

    # Create JWT token (identity must be a string for Flask-JWT-Extended)
    access_token = create_access_token(identity=str(user.id))

    response_data = {
        "user": user.to_dict(),
        "token": access_token,
        "is_new_user": is_new_user,
    }

    if friendship_created:
        response_data["friendship_created"] = True

    if referral_rewards:
        response_data["referral_rewards"] = referral_rewards

    return success_response(response_data)


@api_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current authenticated user."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return unauthorized("User not found")

    return success_response({"user": user.to_dict()})


@api_bp.route("/auth/dev", methods=["POST"])
def dev_authenticate():
    """
    Development-only endpoint for testing without Telegram.
    Creates or gets a test user.

    Request body:
    {
        "telegram_id": 12345,
        "username": "test_user"
    }
    """
    from flask import current_app

    if not current_app.debug:
        return unauthorized("This endpoint is only available in development mode")

    data = request.get_json() or {}

    telegram_id = data.get("telegram_id", 12345)
    username = data.get("username", "test_user")

    user = User.query.filter_by(telegram_id=telegram_id).first()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name="Test",
            last_name="User",
        )
        db.session.add(user)
        db.session.commit()

    access_token = create_access_token(identity=str(user.id))

    return success_response({"user": user.to_dict(), "token": access_token})
