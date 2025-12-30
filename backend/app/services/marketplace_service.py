"""Marketplace service for Sparks trading."""

import logging
from datetime import datetime
from typing import Any

from app import db
from app.models.card import UserCard
from app.models.marketplace import MIN_PRICES, MarketListing
from app.models.sparks import SparksTransaction
from app.models.user import User

logger = logging.getLogger(__name__)

# Platform commission (10%)
COMMISSION_RATE = 0.10

# Cooldown skip price per hour remaining (in Sparks)
COOLDOWN_SKIP_RATE = 2  # 2 Sparks per hour


class MarketplaceService:
    """Service for managing marketplace listings and transactions."""

    def get_user_sparks(self, user_id: int) -> int:
        """Get user's Sparks balance."""
        user = User.query.get(user_id)
        return user.sparks if user else 0

    def list_card(self, user_id: int, card_id: int, price: int) -> dict[str, Any]:
        """List a card for sale on the marketplace."""
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return {"error": "card_not_found"}

        if card.is_destroyed:
            return {"error": "card_destroyed"}

        if card.is_in_deck:
            return {
                "error": "card_in_deck",
                "message": "Сначала уберите карту из колоды",
            }

        if card.is_on_cooldown():
            return {"error": "card_on_cooldown"}

        if not card.is_tradeable:
            return {"error": "card_not_tradeable"}

        # Check if already listed
        existing = MarketListing.query.filter_by(
            card_id=card_id, status="active"
        ).first()
        if existing:
            return {"error": "already_listed"}

        # Check minimum price
        min_price = MIN_PRICES.get(card.rarity, 1)
        if price < min_price:
            return {
                "error": "price_too_low",
                "min_price": min_price,
                "message": f"Минимальная цена для {card.rarity}: {min_price} ✨",
            }

        listing = MarketListing(
            seller_id=user_id,
            card_id=card_id,
            price_stars=price,  # Keep for backwards compatibility
            price_sparks=price,
        )
        db.session.add(listing)
        db.session.commit()

        logger.info(f"Card {card_id} listed by user {user_id} for {price} Sparks")
        return {"success": True, "listing": listing.to_dict()}

    def cancel_listing(self, user_id: int, listing_id: int) -> dict[str, Any]:
        """Cancel a marketplace listing."""
        listing = MarketListing.query.filter_by(
            id=listing_id, seller_id=user_id, status="active"
        ).first()
        if not listing:
            return {"error": "listing_not_found"}

        listing.status = "cancelled"
        db.session.commit()

        logger.info(f"Listing {listing_id} cancelled by user {user_id}")
        return {"success": True}

    def browse_listings(
        self,
        page: int = 1,
        per_page: int = 20,
        rarity: str | None = None,
        genre: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        sort_by: str = "newest",
        exclude_seller_id: int | None = None,
    ) -> dict[str, Any]:
        """Browse marketplace listings."""
        query = MarketListing.query.filter_by(status="active")

        # Exclude user's own listings
        if exclude_seller_id:
            query = query.filter(MarketListing.seller_id != exclude_seller_id)

        if rarity:
            query = query.join(UserCard).filter(UserCard.rarity == rarity)
        elif genre:
            query = query.join(UserCard).filter(UserCard.genre == genre)

        if min_price:
            query = query.filter(MarketListing.price_stars >= min_price)
        if max_price:
            query = query.filter(MarketListing.price_stars <= max_price)

        # Sorting
        if sort_by == "price_low":
            query = query.order_by(MarketListing.price_stars.asc())
        elif sort_by == "price_high":
            query = query.order_by(MarketListing.price_stars.desc())
        else:  # newest
            query = query.order_by(MarketListing.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "listings": [listing.to_dict() for listing in pagination.items],
            "total": pagination.total,
            "page": page,
            "pages": pagination.pages,
        }

    def get_listing(self, listing_id: int) -> MarketListing | None:
        """Get a specific listing."""
        return MarketListing.query.get(listing_id)

    def get_user_listings(self, user_id: int) -> list[dict]:
        """Get user's active listings."""
        listings = MarketListing.query.filter_by(
            seller_id=user_id, status="active"
        ).all()
        return [listing.to_dict() for listing in listings]

    def purchase_with_sparks(self, buyer_id: int, listing_id: int) -> dict[str, Any]:
        """Purchase a listing directly with Sparks."""
        listing = MarketListing.query.filter_by(id=listing_id, status="active").first()
        if not listing:
            return {"error": "listing_not_found"}

        if listing.seller_id == buyer_id:
            return {"error": "cannot_buy_own"}

        buyer = User.query.get(buyer_id)
        if not buyer:
            return {"error": "buyer_not_found"}

        seller = User.query.get(listing.seller_id)
        if not seller:
            return {"error": "seller_not_found"}

        # Use price_sparks if available, fall back to price_stars
        price = listing.price_sparks or listing.price_stars
        if not price:
            return {"error": "invalid_price"}

        # Check buyer has enough Sparks
        if buyer.sparks < price:
            return {
                "error": "insufficient_sparks",
                "required": price,
                "available": buyer.sparks,
                "message": f"Недостаточно Sparks. Нужно: {price}, у вас: {buyer.sparks}",
            }

        card = listing.card
        seller_id = listing.seller_id

        # Calculate seller revenue (after commission)
        commission = int(price * COMMISSION_RATE)
        seller_revenue = price - commission

        # Deduct from buyer
        buyer.spend_sparks(price)

        # Add to seller
        seller.add_sparks(seller_revenue)

        # Transfer card ownership
        card.user_id = buyer_id
        card.is_in_deck = False

        # Update listing
        listing.status = "sold"
        listing.buyer_id = buyer_id
        listing.sold_at = datetime.utcnow()

        # Record transactions
        buyer_tx = SparksTransaction(
            user_id=buyer_id,
            amount=-price,
            type="card_purchase",
            reference_type="listing",
            reference_id=listing_id,
            description=f"Покупка карты: {card.name}",
        )
        db.session.add(buyer_tx)

        seller_tx = SparksTransaction(
            user_id=seller_id,
            amount=seller_revenue,
            type="card_sale",
            reference_type="listing",
            reference_id=listing_id,
            description=f"Продажа карты: {card.name}",
        )
        db.session.add(seller_tx)

        db.session.commit()

        logger.info(
            f"Purchase completed: listing {listing_id}, "
            f"buyer {buyer_id}, seller {seller_id}, "
            f"price {price} Sparks"
        )

        return {
            "success": True,
            "card": card.to_dict(),
            "price_paid": price,
            "seller_revenue": seller_revenue,
            "commission": commission,
            "buyer_balance": buyer.sparks,
        }

    def skip_card_cooldown(self, user_id: int, card_id: int) -> dict[str, Any]:
        """Skip card cooldown by paying Sparks.

        Price: 2 Sparks per hour remaining.
        """
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return {"error": "card_not_found"}

        if not card.is_on_cooldown():
            return {"error": "not_on_cooldown"}

        user = User.query.get(user_id)
        if not user:
            return {"error": "user_not_found"}

        # Calculate price
        remaining_seconds = card.get_cooldown_remaining()
        remaining_hours = max(1, (remaining_seconds + 3599) // 3600)  # Round up
        price = remaining_hours * COOLDOWN_SKIP_RATE

        # Check if user has enough Sparks
        if user.sparks < price:
            return {
                "error": "insufficient_sparks",
                "required": price,
                "available": user.sparks,
                "message": f"Недостаточно Sparks. Нужно: {price}, у вас: {user.sparks}",
            }

        # Deduct Sparks and clear cooldown
        user.spend_sparks(price)
        card.clear_cooldown()

        # Record transaction
        tx = SparksTransaction(
            user_id=user_id,
            amount=-price,
            type="skip_cooldown",
            reference_type="card",
            reference_id=card_id,
            description=f"Пропуск перезарядки: {card.name}",
        )
        db.session.add(tx)
        db.session.commit()

        logger.info(f"Cooldown skipped for card {card_id} by user {user_id}")

        return {
            "success": True,
            "card": card.to_dict(),
            "price_paid": price,
            "remaining_sparks": user.sparks,
        }

    def get_transaction_history(
        self, user_id: int, page: int = 1, per_page: int = 20
    ) -> dict[str, Any]:
        """Get user's Sparks transaction history."""
        query = SparksTransaction.query.filter_by(user_id=user_id).order_by(
            SparksTransaction.created_at.desc()
        )

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "transactions": [t.to_dict() for t in pagination.items],
            "total": pagination.total,
            "page": page,
            "pages": pagination.pages,
        }
