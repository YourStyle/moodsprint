"""Marketplace API endpoints for Sparks trading."""

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api import api_bp
from app.models import User
from app.services.marketplace_service import MarketplaceService
from app.utils import not_found, success_response, validation_error

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
    - min_price: minimum price in Sparks
    - max_price: maximum price in Sparks
    - sort_by: "newest" (default), "price_low", "price_high"
    """
    user_id = int(get_jwt_identity())
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
        exclude_seller_id=user_id,  # Don't show user's own listings
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
        "price": 50  # in Sparks
    }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    card_id = data.get("card_id")
    # Support both "price" and legacy "price_stars"
    price = data.get("price") or data.get("price_stars")

    if not card_id:
        return validation_error({"card_id": "ID карты обязателен"})
    if not price or price < 1:
        return validation_error({"price": "Цена должна быть больше 0"})

    service = MarketplaceService()
    result = service.list_card(user_id, card_id, price)

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
def purchase_listing(listing_id: int):
    """
    Purchase a card with Sparks.

    Directly deducts Sparks from buyer and credits to seller.
    """
    user_id = int(get_jwt_identity())

    service = MarketplaceService()
    result = service.purchase_with_sparks(user_id, listing_id)

    if "error" in result:
        error_messages = {
            "listing_not_found": "Объявление не найдено",
            "cannot_buy_own": "Нельзя купить свою карту",
            "buyer_not_found": "Пользователь не найден",
            "seller_not_found": "Продавец не найден",
            "invalid_price": "Неверная цена",
            "insufficient_sparks": result.get("message", "Недостаточно Sparks"),
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Покупка завершена!", **result})


# ============ Cooldown Skip ============


@api_bp.route("/cards/<int:card_id>/skip-cooldown", methods=["POST"])
@jwt_required()
def skip_cooldown(card_id: int):
    """
    Skip card cooldown by paying Sparks.

    Price: 2 Sparks per hour remaining.
    Directly deducts Sparks if user has enough.
    """
    user_id = int(get_jwt_identity())

    service = MarketplaceService()
    result = service.skip_card_cooldown(user_id, card_id)

    if "error" in result:
        error_messages = {
            "card_not_found": "Карта не найдена",
            "user_not_found": "Пользователь не найден",
            "not_on_cooldown": "Карта не на перезарядке",
            "insufficient_sparks": result.get("message", "Недостаточно Sparks"),
        }
        return validation_error(
            {"error": error_messages.get(result["error"], result["error"])}
        )

    return success_response({"message": "Карта восстановлена!", **result})


# ============ Balance & Transactions ============


@api_bp.route("/marketplace/balance", methods=["GET"])
@jwt_required()
def get_marketplace_balance():
    """Get user's Sparks balance."""
    user_id = int(get_jwt_identity())

    user = User.query.get(user_id)
    if not user:
        return not_found("Пользователь не найден")

    return success_response(
        {
            "sparks": user.sparks,
        }
    )


@api_bp.route("/marketplace/transactions", methods=["GET"])
@jwt_required()
def get_marketplace_transactions():
    """
    Get Sparks transaction history.

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
