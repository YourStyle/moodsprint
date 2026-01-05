"""Authentication utilities."""

from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models.user import User
from app.utils.response import error_response

# Admin user IDs (telegram_id or user_id)
ADMIN_IDS = [1, 140633872]  # Add your admin telegram IDs here


def admin_required(fn):
    """
    Decorator that requires the user to be an admin.

    Must be used after @jwt_required() or instead of it.
    """

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return error_response("unauthorized", "User not found", 401)

        # Check if user is admin by user_id or telegram_id
        if user_id not in ADMIN_IDS and user.telegram_id not in ADMIN_IDS:
            return error_response("forbidden", "Admin access required", 403)

        return fn(*args, **kwargs)

    return wrapper
