"""Card system models for RPG mechanics."""

from datetime import datetime
from enum import Enum

from app import db


class CardRarity(str, Enum):
    """Card rarity levels based on task difficulty."""

    COMMON = "common"  # Easy tasks
    UNCOMMON = "uncommon"  # Medium tasks
    RARE = "rare"  # Hard tasks
    EPIC = "epic"  # Very hard tasks
    LEGENDARY = "legendary"  # Boss tasks / special achievements


# Rarity stats multipliers
RARITY_MULTIPLIERS = {
    CardRarity.COMMON: {"hp": 1.0, "attack": 1.0},
    CardRarity.UNCOMMON: {"hp": 1.3, "attack": 1.2},
    CardRarity.RARE: {"hp": 1.6, "attack": 1.5},
    CardRarity.EPIC: {"hp": 2.0, "attack": 1.8},
    CardRarity.LEGENDARY: {"hp": 2.5, "attack": 2.2},
}

# Rarity colors for UI
RARITY_COLORS = {
    CardRarity.COMMON: "#9CA3AF",  # Gray
    CardRarity.UNCOMMON: "#22C55E",  # Green
    CardRarity.RARE: "#3B82F6",  # Blue
    CardRarity.EPIC: "#A855F7",  # Purple
    CardRarity.LEGENDARY: "#F59E0B",  # Orange/Gold
}


class CardTemplate(db.Model):
    """
    Base card templates - predefined cards with images.
    We start with 10 per genre and add more over time.
    """

    __tablename__ = "card_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    genre = db.Column(db.String(50), nullable=False)

    # Base stats (will be modified by rarity when card is generated)
    base_hp = db.Column(db.Integer, default=50, nullable=False)
    base_attack = db.Column(db.Integer, default=15, nullable=False)

    # Visual
    image_url = db.Column(db.String(512), nullable=True)
    emoji = db.Column(db.String(10), default="🃏")

    # Generation control
    ai_generated = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "base_hp": self.base_hp,
            "base_attack": self.base_attack,
            "image_url": self.image_url,
            "emoji": self.emoji,
        }


class UserCard(db.Model):
    """
    User's card collection - cards earned from completing tasks.
    Each card is a specific instance with rarity-modified stats.
    """

    __tablename__ = "user_cards"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id = db.Column(
        db.Integer,
        db.ForeignKey("card_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Card details (copied from template + modifications)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    genre = db.Column(db.String(50), nullable=False)
    rarity = db.Column(db.String(20), default=CardRarity.COMMON.value, nullable=False)

    # Final stats (after rarity multiplier)
    hp = db.Column(db.Integer, default=50, nullable=False)
    attack = db.Column(db.Integer, default=15, nullable=False)
    current_hp = db.Column(db.Integer, default=50, nullable=False)  # For battles

    # Visual
    image_url = db.Column(db.String(512), nullable=True)
    emoji = db.Column(db.String(10), default="🃏")

    # Source tracking
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )  # Which task gave this card

    # Status
    is_in_deck = db.Column(db.Boolean, default=False)  # In active battle deck
    is_tradeable = db.Column(db.Boolean, default=True)
    is_destroyed = db.Column(db.Boolean, default=False)  # Lost in battle

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("cards", lazy="dynamic"))
    template = db.relationship("CardTemplate")

    def heal(self):
        """Restore card HP to full."""
        self.current_hp = self.hp

    def take_damage(self, damage: int) -> int:
        """Take damage and return actual damage taken."""
        actual_damage = min(damage, self.current_hp)
        self.current_hp = max(0, self.current_hp - actual_damage)
        return actual_damage

    @property
    def is_alive(self) -> bool:
        """Check if card has HP remaining."""
        return self.current_hp > 0

    @property
    def rarity_color(self) -> str:
        """Get color for this rarity."""
        return RARITY_COLORS.get(
            CardRarity(self.rarity), RARITY_COLORS[CardRarity.COMMON]
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "rarity": self.rarity,
            "hp": self.hp,
            "attack": self.attack,
            "current_hp": self.current_hp,
            "image_url": self.image_url,
            "emoji": self.emoji,
            "is_in_deck": self.is_in_deck,
            "is_tradeable": self.is_tradeable,
            "is_alive": self.is_alive,
            "rarity_color": self.rarity_color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Friendship(db.Model):
    """Friend relationships between users."""

    __tablename__ = "friendships"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    friend_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # pending, accepted, blocked

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime, nullable=True)

    # Unique constraint: one friendship record per pair
    __table_args__ = (
        db.UniqueConstraint("user_id", "friend_id", name="unique_friendship"),
    )

    # Relationships
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref("sent_requests", lazy="dynamic"),
    )
    friend = db.relationship(
        "User",
        foreign_keys=[friend_id],
        backref=db.backref("received_requests", lazy="dynamic"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "friend_id": self.friend_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
        }


class CardTrade(db.Model):
    """Card trading between friends."""

    __tablename__ = "card_trades"

    id = db.Column(db.Integer, primary_key=True)

    # Sender
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_card_id = db.Column(
        db.Integer,
        db.ForeignKey("user_cards.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Receiver
    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receiver_card_id = db.Column(
        db.Integer,
        db.ForeignKey("user_cards.id", ondelete="SET NULL"),
        nullable=True,
    )  # Card offered in exchange (optional for gifts)

    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # pending, accepted, rejected, cancelled

    message = db.Column(db.String(500), nullable=True)  # Optional trade message

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])
    sender_card = db.relationship("UserCard", foreign_keys=[sender_card_id])
    receiver_card = db.relationship("UserCard", foreign_keys=[receiver_card_id])

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "sender_card": self.sender_card.to_dict() if self.sender_card else None,
            "receiver_card": (
                self.receiver_card.to_dict() if self.receiver_card else None
            ),
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CoopBattle(db.Model):
    """Cooperative battles against bosses."""

    __tablename__ = "coop_battles"

    id = db.Column(db.Integer, primary_key=True)
    monster_id = db.Column(
        db.Integer,
        db.ForeignKey("monsters.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Battle initiator
    initiator_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = db.Column(
        db.String(20), default="waiting", nullable=False
    )  # waiting, in_progress, won, lost

    # Required genres for this battle (JSON array)
    required_genres = db.Column(db.JSON, default=list)
    min_cards_required = db.Column(db.Integer, default=3)
    max_players = db.Column(db.Integer, default=4)

    # Battle result
    total_damage_dealt = db.Column(db.Integer, default=0)
    rounds_played = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    initiator = db.relationship("User", foreign_keys=[initiator_id])
    monster = db.relationship("Monster")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "monster_id": self.monster_id,
            "monster": self.monster.to_dict() if self.monster else None,
            "initiator_id": self.initiator_id,
            "status": self.status,
            "required_genres": self.required_genres,
            "min_cards_required": self.min_cards_required,
            "max_players": self.max_players,
            "total_damage_dealt": self.total_damage_dealt,
            "rounds_played": self.rounds_played,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CoopBattleParticipant(db.Model):
    """Participants in a cooperative battle."""

    __tablename__ = "coop_battle_participants"

    id = db.Column(db.Integer, primary_key=True)
    battle_id = db.Column(
        db.Integer,
        db.ForeignKey("coop_battles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Cards used in this battle (JSON array of card IDs)
    card_ids = db.Column(db.JSON, default=list)

    # Contribution
    damage_dealt = db.Column(db.Integer, default=0)
    cards_lost = db.Column(db.Integer, default=0)

    # Rewards
    xp_earned = db.Column(db.Integer, default=0)

    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint("battle_id", "user_id", name="unique_battle_participant"),
    )

    # Relationships
    battle = db.relationship(
        "CoopBattle", backref=db.backref("participants", lazy="dynamic")
    )
    user = db.relationship("User")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "battle_id": self.battle_id,
            "user_id": self.user_id,
            "card_ids": self.card_ids,
            "damage_dealt": self.damage_dealt,
            "cards_lost": self.cards_lost,
            "xp_earned": self.xp_earned,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }
