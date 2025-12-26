"""Marketplace service for Telegram Stars trading."""

import logging
from datetime import datetime
from typing import Any

from app import db
from app.models.card import UserCard
from app.models.marketplace import (
    MIN_PRICES,
    MarketListing,
    StarsTransaction,
    UserStarsBalance,
)

logger = logging.getLogger(__name__)

# Platform commission (10%)
COMMISSION_RATE = 0.10

# Cooldown skip price per hour remaining (in Stars)
COOLDOWN_SKIP_RATE = 2  # 2 Stars per hour


class MarketplaceService:
    """Service for managing marketplace listings and transactions."""

    def get_user_balance(self, user_id: int) -> UserStarsBalance:
        """Get or create user's Stars balance."""
        balance = UserStarsBalance.query.filter_by(user_id=user_id).first()
        if not balance:
            balance = UserStarsBalance(user_id=user_id)
            db.session.add(balance)
            db.session.commit()
        return balance

    def list_card(self, user_id: int, card_id: int, price_stars: int) -> dict[str, Any]:
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
        if price_stars < min_price:
            return {
                "error": "price_too_low",
                "min_price": min_price,
                "message": f"Минимальная цена для {card.rarity}: {min_price} ⭐",
            }

        listing = MarketListing(
            seller_id=user_id,
            card_id=card_id,
            price_stars=price_stars,
        )
        db.session.add(listing)
        db.session.commit()

        logger.info(f"Card {card_id} listed by user {user_id} for {price_stars} Stars")
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
    ) -> dict[str, Any]:
        """Browse marketplace listings."""
        query = MarketListing.query.filter_by(status="active")

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

    def create_purchase_invoice(self, buyer_id: int, listing_id: int) -> dict[str, Any]:
        """Create invoice data for Telegram Stars purchase.

        Returns data needed to create a Telegram invoice.
        The actual payment is processed by the bot.
        """
        listing = MarketListing.query.filter_by(id=listing_id, status="active").first()
        if not listing:
            return {"error": "listing_not_found"}

        if listing.seller_id == buyer_id:
            return {"error": "cannot_buy_own"}

        return {
            "success": True,
            "invoice_data": {
                "title": f"Карта: {listing.card.name}",
                "description": (
                    f"Покупка карты {listing.card.name} "
                    f"({listing.card.rarity}) за {listing.price_stars} ⭐"
                ),
                "payload": f"marketplace_purchase_{listing_id}_{buyer_id}",
                "price": listing.price_stars,
                "listing_id": listing_id,
                "card": listing.card.to_dict(),
            },
        }

    def complete_purchase(
        self,
        listing_id: int,
        buyer_id: int,
        telegram_payment_id: str,
    ) -> dict[str, Any]:
        """Complete a purchase after successful Telegram Stars payment.

        Called by bot after receiving successful_payment.
        """
        listing = MarketListing.query.filter_by(id=listing_id, status="active").first()
        if not listing:
            return {"error": "listing_not_found"}

        if listing.seller_id == buyer_id:
            return {"error": "cannot_buy_own"}

        card = listing.card
        seller_id = listing.seller_id
        price = listing.price_stars

        # Calculate seller revenue (after commission)
        commission = int(price * COMMISSION_RATE)
        seller_revenue = price - commission

        # Transfer card ownership
        card.user_id = buyer_id
        card.is_in_deck = False

        # Update listing
        listing.status = "sold"
        listing.buyer_id = buyer_id
        listing.sold_at = datetime.utcnow()

        # Record transactions
        # Buyer transaction (spent)
        buyer_tx = StarsTransaction(
            user_id=buyer_id,
            amount=-price,
            type="card_purchase",
            reference_type="listing",
            reference_id=listing_id,
            telegram_payment_id=telegram_payment_id,
            description=f"Покупка карты: {card.name}",
        )
        db.session.add(buyer_tx)

        # Seller transaction (received)
        seller_tx = StarsTransaction(
            user_id=seller_id,
            amount=seller_revenue,
            type="card_sale",
            reference_type="listing",
            reference_id=listing_id,
            description=f"Продажа карты: {card.name}",
        )
        db.session.add(seller_tx)

        # Update seller balance (pending until withdrawal)
        seller_balance = self.get_user_balance(seller_id)
        seller_balance.pending_balance += seller_revenue
        seller_balance.total_earned += seller_revenue

        # Update buyer stats
        buyer_balance = self.get_user_balance(buyer_id)
        buyer_balance.total_spent += price

        db.session.commit()

        logger.info(
            f"Purchase completed: listing {listing_id}, "
            f"buyer {buyer_id}, seller {seller_id}, "
            f"price {price} Stars"
        )

        return {
            "success": True,
            "card": card.to_dict(),
            "price_paid": price,
            "seller_revenue": seller_revenue,
            "commission": commission,
        }

    def skip_card_cooldown(self, user_id: int, card_id: int) -> dict[str, Any]:
        """Skip card cooldown by paying Stars.

        Price: 2 Stars per hour remaining.
        """
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return {"error": "card_not_found"}

        if not card.is_on_cooldown():
            return {"error": "not_on_cooldown"}

        # Calculate price
        remaining_seconds = card.get_cooldown_remaining()
        remaining_hours = max(1, (remaining_seconds + 3599) // 3600)  # Round up
        price = remaining_hours * COOLDOWN_SKIP_RATE

        return {
            "success": True,
            "invoice_data": {
                "title": "Пропустить перезарядку",
                "description": (f"Восстановить карту {card.name} сейчас за {price} ⭐"),
                "payload": f"skip_cooldown_{card_id}_{user_id}",
                "price": price,
                "card_id": card_id,
                "remaining_hours": remaining_hours,
            },
        }

    def complete_cooldown_skip(
        self,
        card_id: int,
        user_id: int,
        telegram_payment_id: str,
        price: int,
    ) -> dict[str, Any]:
        """Complete cooldown skip after payment."""
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return {"error": "card_not_found"}

        # Clear cooldown and restore HP
        card.clear_cooldown()

        # Record transaction
        tx = StarsTransaction(
            user_id=user_id,
            amount=-price,
            type="skip_cooldown",
            reference_type="card",
            reference_id=card_id,
            telegram_payment_id=telegram_payment_id,
            description=f"Пропуск перезарядки: {card.name}",
        )
        db.session.add(tx)

        # Update balance stats
        balance = self.get_user_balance(user_id)
        balance.total_spent += price

        db.session.commit()

        logger.info(f"Cooldown skipped for card {card_id} by user {user_id}")

        return {"success": True, "card": card.to_dict()}

    def get_transaction_history(
        self, user_id: int, page: int = 1, per_page: int = 20
    ) -> dict[str, Any]:
        """Get user's transaction history."""
        query = StarsTransaction.query.filter_by(user_id=user_id).order_by(
            StarsTransaction.created_at.desc()
        )

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "transactions": [t.to_dict() for t in pagination.items],
            "total": pagination.total,
            "page": page,
            "pages": pagination.pages,
        }
