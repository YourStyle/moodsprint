"""Telegram WebApp authentication utilities."""

import hashlib
import hmac
import json
from urllib.parse import parse_qs
from typing import Any
from flask import current_app


def validate_telegram_data(init_data: str) -> bool:
    """
    Validate Telegram WebApp initData.

    The validation process:
    1. Parse the init_data query string
    2. Extract the hash
    3. Create data-check-string from remaining params (sorted alphabetically)
    4. Create HMAC-SHA256 of data-check-string using secret key
    5. Compare with provided hash
    """
    try:
        # Parse init_data as query string
        parsed = parse_qs(init_data)

        # Extract hash
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return False

        # Build data-check-string (all params except hash, sorted)
        data_check_parts = []
        for key in sorted(parsed.keys()):
            if key != "hash":
                value = parsed[key][0]
                data_check_parts.append(f"{key}={value}")

        data_check_string = "\n".join(data_check_parts)

        # Get bot token
        bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            # In development, allow bypass if no token configured
            current_app.logger.warning(
                "No TELEGRAM_BOT_TOKEN configured, skipping validation"
            )
            return True

        # Create secret key: HMAC-SHA256 of bot token with "WebAppData" as key
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_hash, received_hash)

    except Exception as e:
        current_app.logger.error(f"Telegram validation error: {e}")
        return False


def parse_telegram_user(init_data: str) -> dict[str, Any] | None:
    """
    Extract user data from Telegram initData.

    Returns user dict with fields:
    - id (telegram user id)
    - first_name
    - last_name (optional)
    - username (optional)
    - photo_url (optional)
    """
    try:
        parsed = parse_qs(init_data)
        user_json = parsed.get("user", [None])[0]

        if not user_json:
            return None

        user_data = json.loads(user_json)

        return {
            "id": user_data.get("id"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "username": user_data.get("username"),
            "photo_url": user_data.get("photo_url"),
        }

    except (json.JSONDecodeError, KeyError) as e:
        current_app.logger.error(f"Error parsing Telegram user: {e}")
        return None


def get_auth_date(init_data: str) -> int | None:
    """Extract auth_date from initData."""
    try:
        parsed = parse_qs(init_data)
        auth_date = parsed.get("auth_date", [None])[0]
        return int(auth_date) if auth_date else None
    except (ValueError, TypeError):
        return None
