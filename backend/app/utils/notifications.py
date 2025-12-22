"""Telegram notification utilities for the backend."""

import logging
from typing import Optional

import requests
from flask import current_app

logger = logging.getLogger(__name__)


def send_telegram_message(
    telegram_id: int,
    text: str,
    parse_mode: str = "HTML",
    webapp_url: Optional[str] = None,
) -> bool:
    """
    Send a Telegram message to a user.

    Args:
        telegram_id: Telegram user ID
        text: Message text (supports HTML formatting)
        parse_mode: Parse mode for message formatting (HTML or Markdown)
        webapp_url: Optional URL for inline webapp button

    Returns:
        True if message was sent successfully, False otherwise
    """
    bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("No TELEGRAM_BOT_TOKEN configured, skipping notification")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    # Add webapp button if URL provided
    if webapp_url:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {
                        "text": "Открыть MoodSprint",
                        "web_app": {"url": webapp_url},
                    }
                ]
            ]
        }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            # User might have blocked the bot or chat doesn't exist
            error_data = response.json()
            logger.warning(
                f"Failed to send Telegram message to {telegram_id}: {error_data}"
            )
            return False
    except requests.RequestException as e:
        logger.error(f"Error sending Telegram message to {telegram_id}: {e}")
        return False


def notify_trade_received(
    receiver_telegram_id: int,
    sender_name: str,
    cards_count: int,
    is_gift: bool,
    webapp_url: Optional[str] = None,
) -> bool:
    """
    Notify user about received trade offer or gift.

    Args:
        receiver_telegram_id: Telegram ID of the receiver
        sender_name: Name of the sender
        cards_count: Number of cards being offered
        is_gift: True if it's a gift (no cards requested in return)
        webapp_url: URL to the webapp

    Returns:
        True if notification was sent successfully
    """
    if is_gift:
        emoji = "🎁"
        title = "Вам отправили подарок!"
        description = f"<b>{sender_name}</b> хочет подарить вам "
        if cards_count == 1:
            description += "карту"
        elif cards_count < 5:
            description += f"{cards_count} карты"
        else:
            description += f"{cards_count} карт"
    else:
        emoji = "🔄"
        title = "Новое предложение обмена!"
        description = f"<b>{sender_name}</b> предлагает обмен"
        if cards_count > 1:
            description += f" ({cards_count} карт)"

    text = f"{emoji} <b>{title}</b>\n\n{description}\n\nОткройте приложение, чтобы посмотреть"

    return send_telegram_message(
        telegram_id=receiver_telegram_id,
        text=text,
        webapp_url=webapp_url,
    )
