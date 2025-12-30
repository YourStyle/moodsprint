"""Sparks currency and TON wallet models."""

from datetime import datetime

from app import db


class SparksTransaction(db.Model):
    """Transaction log for Sparks currency."""

    __tablename__ = "sparks_transactions"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Amount (positive = received, negative = spent)
    amount = db.Column(db.Integer, nullable=False)

    # Transaction types:
    # - card_sale: received sparks from selling card
    # - card_purchase: spent sparks on buying card
    # - campaign_reward: received for completing campaign level
    # - ton_deposit: received from TON deposit
    # - stars_purchase: received from Telegram Stars purchase
    # - referral_bonus: received for referring a user
    type = db.Column(db.String(30), nullable=False)

    # Reference to what this transaction is for
    reference_type = db.Column(db.String(30), nullable=True)  # listing, level, etc
    reference_id = db.Column(db.Integer, nullable=True)

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


class TonDeposit(db.Model):
    """TON blockchain deposit tracking."""

    __tablename__ = "ton_deposits"

    id = db.Column(db.Integer, primary_key=True)

    # User who sent the deposit (null if can't identify)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Transaction hash (unique identifier)
    tx_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)

    # Sender wallet address
    sender_address = db.Column(db.String(48), nullable=False)

    # Amount in nanoTON (1 TON = 10^9 nanoTON)
    amount_nano = db.Column(db.BigInteger, nullable=False)

    # Amount in TON (for display)
    amount_ton = db.Column(db.Numeric(20, 9), nullable=False)

    # Memo/comment from transaction (used to identify user)
    memo = db.Column(db.String(200), nullable=True)

    # Status: pending, processed, failed, refunded
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    # Sparks credited to user (null if not processed)
    sparks_credited = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship("User")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tx_hash": self.tx_hash,
            "sender_address": self.sender_address,
            "amount_nano": self.amount_nano,
            "amount_ton": float(self.amount_ton) if self.amount_ton else None,
            "memo": self.memo,
            "status": self.status,
            "sparks_credited": self.sparks_credited,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": (
                self.processed_at.isoformat() if self.processed_at else None
            ),
        }


# Sparks pack definitions for purchase
SPARKS_PACKS = {
    "starter": {"sparks": 100, "price_stars": 10, "price_ton": 0.1},
    "basic": {"sparks": 500, "price_stars": 45, "price_ton": 0.45},
    "standard": {"sparks": 1000, "price_stars": 80, "price_ton": 0.8},
    "premium": {"sparks": 2500, "price_stars": 175, "price_ton": 1.75},
    "elite": {"sparks": 5000, "price_stars": 300, "price_ton": 3.0},
    "ultimate": {"sparks": 10000, "price_stars": 500, "price_ton": 5.0},
}


def get_sparks_for_ton(ton_amount: float) -> int:
    """Calculate sparks to credit for TON deposit amount."""
    # Find the best matching pack (highest that fits the amount)
    selected_pack = None
    for pack in sorted(SPARKS_PACKS.values(), key=lambda x: x["price_ton"]):
        if pack["price_ton"] <= ton_amount:
            selected_pack = pack
        else:
            break

    if selected_pack:
        return selected_pack["sparks"]

    # If less than minimum pack, give proportional amount
    # Base rate: 1000 sparks per 0.8 TON = 1250 sparks per TON
    return int(ton_amount * 1250)
