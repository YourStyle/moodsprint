"""Marketplace models for Sparks trading."""

from datetime import datetime

from app import db

# Minimum prices by rarity (in Sparks)
MIN_PRICES = {
    "common": 1,
    "uncommon": 5,
    "rare": 15,
    "epic": 50,
    "legendary": 200,
}


class MarketListing(db.Model):
    """Card listing on the marketplace."""

    __tablename__ = "market_listings"

    id = db.Column(db.Integer, primary_key=True)

    # Seller
    seller_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Card being sold
    card_id = db.Column(
        db.Integer,
        db.ForeignKey("user_cards.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Card can only be listed once
    )

    # Price in Sparks (both columns for backward compatibility)
    price_stars = db.Column(db.Integer, nullable=False)
    price_sparks = db.Column(db.Integer, nullable=False)

    # Status: active, sold, cancelled, expired
    status = db.Column(db.String(20), default="active", index=True)

    # Buyer info (filled when sold)
    buyer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sold_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # Optional expiration

    # Relationships
    seller = db.relationship("User", foreign_keys=[seller_id])
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    card = db.relationship("UserCard")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "seller": (
                {
                    "id": self.seller.id,
                    "username": self.seller.username,
                    "first_name": self.seller.first_name,
                }
                if self.seller
                else None
            ),
            "card_id": self.card_id,
            "card": self.card.to_dict() if self.card else None,
            "price": self.price_stars,  # Sparks price
            "price_stars": self.price_stars,  # Legacy field
            "status": self.status,
            "buyer_id": self.buyer_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sold_at": self.sold_at.isoformat() if self.sold_at else None,
        }


class StarsTransaction(db.Model):
    """Transaction log for Telegram Stars."""

    __tablename__ = "stars_transactions"

    id = db.Column(db.Integer, primary_key=True)

    # User
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amount (positive = received, negative = spent)
    amount = db.Column(db.Integer, nullable=False)

    # Transaction type
    # - card_sale: received stars from selling card
    # - card_purchase: spent stars on buying card
    # - skip_cooldown: spent stars to skip card cooldown
    # - gift: received stars as gift
    # - refund: received stars as refund
    type = db.Column(db.String(30), nullable=False)

    # Reference to what this transaction is for
    reference_type = db.Column(db.String(30), nullable=True)  # listing, card, etc
    reference_id = db.Column(db.Integer, nullable=True)

    # Telegram payment info
    telegram_payment_id = db.Column(db.String(100), nullable=True)

    # Description
    description = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "type": self.type,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserStarsBalance(db.Model):
    """User's Telegram Stars balance (cached for quick access)."""

    __tablename__ = "user_stars_balances"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Current balance
    balance = db.Column(db.Integer, default=0)

    # Pending balance (from sales not yet withdrawn)
    pending_balance = db.Column(db.Integer, default=0)

    # Total earned/spent lifetime
    total_earned = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Integer, default=0)

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("stars_balance", uselist=False))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "balance": self.balance,
            "pending_balance": self.pending_balance,
            "total_earned": self.total_earned,
            "total_spent": self.total_spent,
        }
