"""Authentication utilities."""

import os
from functools import wraps

from flask import current_app
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models.user import User
from app.utils.response import error_response


def get_admin_ids():
    """Get admin IDs from app config or environment."""
    # Try app config first (set from ADMIN_IDS env var in config.py)
    if current_app and current_app.config.get("ADMIN_TELEGRAM_IDS"):
        return current_app.config["ADMIN_TELEGRAM_IDS"]
    # Fallback to parsing env var directly
    admin_ids_str = os.environ.get("ADMIN_IDS", "")
    if admin_ids_str:
        return [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    return []


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
        admin_ids = get_admin_ids()
        if user_id not in admin_ids and user.telegram_id not in admin_ids:
            return error_response("forbidden", "Admin access required", 403)

        return fn(*args, **kwargs)

    return wrapper
