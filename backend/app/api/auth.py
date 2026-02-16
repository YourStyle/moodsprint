"""Authentication API endpoints."""

from datetime import datetime

import structlog
from flask import request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app import db
from app.api import api_bp
from app.extensions import limiter
from app.models import User, UserActivityLog
from app.models.card import Friendship, PendingReferralReward
from app.utils import (
    parse_telegram_user,
    success_response,
    unauthorized,
    validate_telegram_data,
    validation_error,
)

logger = structlog.get_logger()


@api_bp.route("/auth/telegram", methods=["POST"])
@limiter.limit("10 per minute")
def authenticate_telegram():
    """
    Authenticate user via Telegram WebApp initData.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - init_data
          properties:
            init_data:
              type: string
              description: Telegram WebApp initData string
            referrer_id:
              type: integer
              description: Optional referrer user ID from invite link
    responses:
      200:
        description: Authentication successful
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: object
              properties:
                user:
                  type: object
                token:
                  type: string
                is_new_user:
                  type: boolean
      400:
        description: Invalid request data
      401:
        description: Invalid Telegram authentication
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

                            # Store pending reward for referrer to show on next login
                            invitee_name = user.first_name or user.username or "друг"
                            pending_reward = PendingReferralReward(
                                user_id=referrer_id,
                                friend_id=user.id,
                                friend_name=invitee_name,
                                card_id=referrer_card.id,
                                is_referrer=True,
                            )
                            db.session.add(pending_reward)

                            logger.info(
                                f"Gave referral reward to user {referrer_id}: "
                                f"{referrer_card.name} ({referrer_card.rarity})"
                            )

                        # Give starter deck to invitee (3 cards, max rare)
                        starter_deck = card_service.generate_starter_deck(user.id)
                        if starter_deck:
                            referral_rewards["invitee_starter_deck"] = [
                                c.to_dict() for c in starter_deck
                            ]
                            # Store friend name for invitee modal
                            referral_rewards["referrer_name"] = (
                                referrer.first_name or referrer.username or "друг"
                            )
                            logger.info(
                                f"Gave starter deck to user {user.id}: "
                                f"{len(starter_deck)} cards"
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

    try:
        UserActivityLog.log(
            user_id=user.id,
            action_type="login",
            action_details="New user registration" if is_new_user else "Login",
        )
    except Exception:
        pass

    # F5: Grant comeback card if pending
    comeback_card = None
    if user and not is_new_user and user.comeback_card_pending:
        try:
            from app.models.card import CardRarity
            from app.services.card_service import CardService

            comeback_card = CardService().generate_card_for_task(
                user.id, None, "Welcome back!", forced_rarity=CardRarity.UNCOMMON
            )
            user.comeback_card_pending = False
        except Exception as e:
            logger.error(f"Failed to generate comeback card: {e}")

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

    if comeback_card:
        response_data["comeback_card"] = comeback_card.to_dict()

    return success_response(response_data)


@api_bp.route("/auth/me", methods=["GET"])
@jwt_required()
@limiter.limit("60 per minute")
def get_current_user():
    """
    Get current authenticated user.
    ---
    tags:
      - Authentication
    security:
      - Bearer: []
    responses:
      200:
        description: Current user data
        schema:
          type: object
          properties:
            success:
              type: boolean
            data:
              type: object
              properties:
                user:
                  type: object
      401:
        description: Unauthorized
    """
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return unauthorized("User not found")

    return success_response({"user": user.to_dict()})


@api_bp.route("/auth/register", methods=["POST"])
@limiter.limit("5 per minute")
def register_with_email():
    """
    Register a new user with email and password.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
            - first_name
          properties:
            email:
              type: string
              description: User email address
            password:
              type: string
              description: User password (min 6 characters)
            first_name:
              type: string
              description: User's first name
    responses:
      200:
        description: Registration successful
      400:
        description: Invalid request data
      409:
        description: Email already exists
    """
    data = request.get_json()

    if not data:
        return validation_error({"request": "Request body is required"})

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    first_name = data.get("first_name", "").strip()

    # Validate email
    if not email or "@" not in email:
        return validation_error({"email": "Valid email is required"})

    # Validate password
    if len(password) < 6:
        return validation_error({"password": "Password must be at least 6 characters"})

    # Validate first_name
    if not first_name:
        return validation_error({"first_name": "First name is required"})

    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return validation_error({"email": "Email already registered"})

    # Create new user
    user = User(
        email=email,
        first_name=first_name,
        username=email.split("@")[0],  # Use email prefix as username
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Create JWT token
    access_token = create_access_token(identity=str(user.id))

    logger.info(f"New user registered with email: {email}")

    return success_response(
        {
            "user": user.to_dict(),
            "token": access_token,
            "is_new_user": True,
        }
    )


@api_bp.route("/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
def login_with_email():
    """
    Login with email and password.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              description: User email address
            password:
              type: string
              description: User password
    responses:
      200:
        description: Login successful
      400:
        description: Invalid request data
      401:
        description: Invalid credentials
    """
    data = request.get_json()

    if not data:
        return validation_error({"request": "Request body is required"})

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return validation_error({"credentials": "Email and password are required"})

    # Find user by email
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return unauthorized("Invalid email or password")

    # Create JWT token
    access_token = create_access_token(identity=str(user.id))

    logger.info(f"User logged in with email: {email}")

    return success_response(
        {
            "user": user.to_dict(),
            "token": access_token,
        }
    )


@api_bp.route("/auth/dev", methods=["POST"])
def dev_authenticate():
    """
    Development/testing endpoint for authentication without Telegram.
    Creates or gets a test user.

    In production, requires dev_secret to match BOT_SECRET config.

    Request body:
    {
        "telegram_id": 12345,
        "username": "test_user",
        "dev_secret": "optional_secret_for_production"
    }
    """
    from flask import current_app

    data = request.get_json() or {}

    # Allow in debug mode OR with valid dev_secret
    if not current_app.debug:
        dev_secret = data.get("dev_secret", "")
        bot_secret = current_app.config.get("BOT_SECRET", "")
        if not bot_secret or dev_secret != bot_secret:
            return unauthorized("This endpoint is only available in development mode")

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
