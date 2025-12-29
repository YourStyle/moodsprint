"""Marketplace API endpoints for Telegram Stars trading."""

import os

import httpx
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api import api_bp
from app.services.marketplace_service import MarketplaceService
from app.utils import not_found, success_response, validation_error

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ============ Listings ============


@api_bp.route("/marketplace", methods=["GET"])
@jwt_required()
def browse_marketplace():
    """
    Browse marketplace listings.

    Query params:
    - page: page number (default 1)
    - per_page: items per page (default 20)
    - rarity: filter by card rarity
    - genre: filter by card genre
    - min_price: minimum price in Stars
    - max_price: maximum price in Stars
    - sort_by: "newest" (default), "price_low", "price_high"
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    rarity = request.args.get("rarity")
    genre = request.args.get("genre")
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    sort_by = request.args.get("sort_by", "newest")

    service = MarketplaceService()
    result = service.browse_listings(
        page=page,
        per_page=per_page,
        rarity=rarity,
        genre=genre,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
    )

    return success_response(result)


@api_bp.route("/marketplace/<int:listing_id>", methods=["GET"])
@jwt_required()
def get_listing(listing_id: int):
    """Get listing details."""
    service = MarketplaceService()
    listing = service.get_listing(listing_id)

    if not listing:
        return not_found("Объявление не найдено")

    return success_response({"listing": listing.to_dict()})


@api_bp.route("/marketplace", methods=["POST"])
@jwt_required()
def create_listing():
    """
    List a card for sale.

    Request body:
    {
        "card_id": 1,
        "price_stars": 50
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    card_id = data.get("card_id")
    price_stars = data.get("price_stars")

    if not card_id:
        return validation_error({"card_id": "ID карты обязателен"})
    if not price_stars or price_stars < 1:
        return validation_error({"price_stars": "Цена должна быть больше 0"})

    service = MarketplaceService()
    result = service.list_card(user_id, card_id, price_stars)

    if "error" in result:
        error_messages = {
            "card_not_found": "Карта не найдена",
            "card_destroyed": "Карта уничтожена",
            "card_in_deck": "Сначала уберите карту из колоды",
            "card_on_cooldown": "Карта на перезарядке",
            "card_not_tradeable": "Эта карта не может быть продана",
            "already_listed": "Карта уже выставлена на продажу",
            "price_too_low": result.get("message", "Цена слишком низкая"),
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Карта выставлена на продажу!", **result})


@api_bp.route("/marketplace/<int:listing_id>", methods=["DELETE"])
@jwt_required()
def cancel_listing(listing_id: int):
    """Cancel a listing (seller only)."""
    user_id = int(get_jwt_identity())

    service = MarketplaceService()
    result = service.cancel_listing(user_id, listing_id)

    if "error" in result:
        return not_found("Объявление не найдено")

    return success_response({"message": "Объявление отменено"})


@api_bp.route("/marketplace/my-listings", methods=["GET"])
@jwt_required()
def get_my_listings():
    """Get current user's active listings."""
    user_id = int(get_jwt_identity())

    service = MarketplaceService()
    listings = service.get_user_listings(user_id)

    return success_response({"listings": listings, "total": len(listings)})


# ============ Purchases ============


@api_bp.route("/marketplace/<int:listing_id>/buy", methods=["POST"])
@jwt_required()
def create_purchase_invoice(listing_id: int):
    """
    Create invoice link for purchasing a card.

    Returns invoice_url to open via WebApp.openInvoice().
    """
    user_id = int(get_jwt_identity())

    service = MarketplaceService()
    result = service.create_purchase_invoice(user_id, listing_id)

    if "error" in result:
        error_messages = {
            "listing_not_found": "Объявление не найдено",
            "cannot_buy_own": "Нельзя купить свою карту",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    # Create invoice link via Telegram Bot API
    invoice_data = result["invoice_data"]

    try:
        with httpx.Client() as client:
            response = client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink",
                json={
                    "title": invoice_data["title"],
                    "description": invoice_data["description"],
                    "payload": invoice_data["payload"],
                    "currency": "XTR",  # Telegram Stars
                    "prices": [{"label": "Карта", "amount": invoice_data["price"]}],
                },
                timeout=10,
            )
            data = response.json()

            if not data.get("ok"):
                return validation_error({"error": "Не удалось создать платёж"})

            return success_response(
                {
                    "invoice_url": data["result"],
                    "listing_id": listing_id,
                    "price": invoice_data["price"],
                    "card": invoice_data["card"],
                }
            )
    except Exception as e:
        return validation_error({"error": f"Ошибка создания платежа: {str(e)}"})


@api_bp.route("/marketplace/complete-purchase", methods=["POST"])
@jwt_required()
def complete_purchase():
    """
    Complete a purchase after successful Telegram Stars payment.

    Called by the bot after receiving successful_payment.

    Request body:
    {
        "listing_id": 1,
        "telegram_payment_id": "xxx"
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    listing_id = data.get("listing_id")
    telegram_payment_id = data.get("telegram_payment_id")

    if not listing_id or not telegram_payment_id:
        return validation_error(
            {"error": "listing_id and telegram_payment_id are required"}
        )

    service = MarketplaceService()
    result = service.complete_purchase(listing_id, user_id, telegram_payment_id)

    if "error" in result:
        error_messages = {
            "listing_not_found": "Объявление не найдено или уже продано",
            "cannot_buy_own": "Нельзя купить свою карту",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Покупка завершена!", **result})


# ============ Cooldown Skip ============


@api_bp.route("/cards/<int:card_id>/skip-cooldown", methods=["POST"])
@jwt_required()
def create_cooldown_skip_invoice(card_id: int):
    """
    Create invoice link for skipping card cooldown.

    Price: 2 Stars per hour remaining.
    """
    user_id = int(get_jwt_identity())

    service = MarketplaceService()
    result = service.skip_card_cooldown(user_id, card_id)

    if "error" in result:
        error_messages = {
            "card_not_found": "Карта не найдена",
            "not_on_cooldown": "Карта не на перезарядке",
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    # Create invoice link via Telegram Bot API
    invoice_data = result["invoice_data"]

    try:
        with httpx.Client() as client:
            response = client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink",
                json={
                    "title": invoice_data["title"],
                    "description": invoice_data["description"],
                    "payload": invoice_data["payload"],
                    "currency": "XTR",  # Telegram Stars
                    "prices": [
                        {"label": "Восстановление", "amount": invoice_data["price"]}
                    ],
                },
                timeout=10,
            )
            data = response.json()

            if not data.get("ok"):
                return validation_error({"error": "Не удалось создать платёж"})

            return success_response(
                {
                    "invoice_url": data["result"],
                    "card_id": card_id,
                    "price": invoice_data["price"],
                }
            )
    except Exception as e:
        return validation_error({"error": f"Ошибка создания платежа: {str(e)}"})


@api_bp.route("/cards/complete-cooldown-skip", methods=["POST"])
@jwt_required()
def complete_cooldown_skip():
    """
    Complete cooldown skip after successful payment.

    Request body:
    {
        "card_id": 1,
        "telegram_payment_id": "xxx",
        "price": 10
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    card_id = data.get("card_id")
    telegram_payment_id = data.get("telegram_payment_id")
    price = data.get("price")

    if not card_id or not telegram_payment_id or not price:
        return validation_error(
            {"error": "card_id, telegram_payment_id, and price are required"}
        )

    service = MarketplaceService()
    result = service.complete_cooldown_skip(
        card_id, user_id, telegram_payment_id, price
    )

    if "error" in result:
        return validation_error({"error": result["error"]})

    return success_response({"message": "Карта восстановлена!", **result})


# ============ Balance & Transactions ============


@api_bp.route("/marketplace/balance", methods=["GET"])
@jwt_required()
def get_stars_balance():
    """Get user's Stars balance and stats."""
    user_id = int(get_jwt_identity())

    service = MarketplaceService()
    balance = service.get_user_balance(user_id)

    return success_response(
        {
            "balance": balance.balance,
            "pending_balance": balance.pending_balance,
            "total_earned": balance.total_earned,
            "total_spent": balance.total_spent,
        }
    )


@api_bp.route("/marketplace/transactions", methods=["GET"])
@jwt_required()
def get_transactions():
    """
    Get transaction history.

    Query params:
    - page: page number (default 1)
    - per_page: items per page (default 20)
    """
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    service = MarketplaceService()
    result = service.get_transaction_history(user_id, page=page, per_page=per_page)

    return success_response(result)
