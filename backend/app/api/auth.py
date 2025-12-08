"""Authentication API endpoints."""

from flask import request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from app import db
from app.api import api_bp
from app.models import User
from app.utils import (
    success_response,
    validation_error,
    unauthorized,
    validate_telegram_data,
    parse_telegram_user,
)


@api_bp.route("/auth/telegram", methods=["POST"])
def authenticate_telegram():
    """
    Authenticate user via Telegram WebApp initData.

    Request body:
    {
        "init_data": "query_id=...&user=...&auth_date=...&hash=..."
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

    if user:
        # Update user info
        user.username = telegram_user.get("username")
        user.first_name = telegram_user.get("first_name")
        user.last_name = telegram_user.get("last_name")
        user.photo_url = telegram_user.get("photo_url")
    else:
        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=telegram_user.get("username"),
            first_name=telegram_user.get("first_name"),
            last_name=telegram_user.get("last_name"),
            photo_url=telegram_user.get("photo_url"),
        )
        db.session.add(user)

    db.session.commit()

    # Create JWT token
    access_token = create_access_token(identity=user.id)

    return success_response({"user": user.to_dict(), "token": access_token})


@api_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current authenticated user."""
    user_id = get_jwt_identity()
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

    access_token = create_access_token(identity=user.id)

    return success_response({"user": user.to_dict(), "token": access_token})
