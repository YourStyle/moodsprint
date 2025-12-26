"""Card system models for RPG mechanics."""

from datetime import datetime, timedelta
from enum import Enum

from app import db


class CardRarity(str, Enum):
    """Card rarity levels based on task difficulty."""

    COMMON = "common"  # Easy tasks
    UNCOMMON = "uncommon"  # Medium tasks
    RARE = "rare"  # Hard tasks
    EPIC = "epic"  # Very hard tasks
    LEGENDARY = "legendary"  # Boss tasks / special achievements


class CardAbility(str, Enum):
    """Card abilities available for Uncommon+ cards."""

    HEAL = "heal"  # Restore 30% HP to an ally
    DOUBLE_STRIKE = "double_strike"  # Attack twice at 60% damage each
    SHIELD = "shield"  # Block next attack
    POISON = "poison"  # Deal 10% damage over 3 turns


# Ability configuration
ABILITY_CONFIG = {
    CardAbility.HEAL: {
        "name": "Исцеление",
        "description": "Восстанавливает 30% HP союзной карте",
        "emoji": "💚",
        "cooldown": 3,
        "target": "ally",  # ally, enemy, self
        "effect_value": 0.3,  # 30% HP
    },
    CardAbility.DOUBLE_STRIKE: {
        "name": "Двойной удар",
        "description": "Атакует дважды за ход (60% урона каждый удар)",
        "emoji": "⚔️",
        "cooldown": 2,
        "target": "enemy",
        "effect_value": 0.6,  # 60% of base attack
    },
    CardAbility.SHIELD: {
        "name": "Щит",
        "description": "Блокирует следующую атаку",
        "emoji": "🛡️",
        "cooldown": 4,
        "target": "self",
        "effect_value": 1,  # Full block
    },
    CardAbility.POISON: {
        "name": "Яд",
        "description": "Отравляет врага: 10% урона каждый ход 3 хода",
        "emoji": "☠️",
        "cooldown": 3,
        "target": "enemy",
        "effect_value": 0.1,  # 10% of max HP
        "duration": 3,
    },
}

# Chance of getting an ability by rarity
ABILITY_CHANCE_BY_RARITY = {
    CardRarity.COMMON: 0,  # Common cards don't get abilities
    CardRarity.UNCOMMON: 0.3,  # 30% chance
    CardRarity.RARE: 0.5,  # 50% chance
    CardRarity.EPIC: 0.75,  # 75% chance
    CardRarity.LEGENDARY: 1.0,  # 100% chance
}


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

    # Ability (for Uncommon+ cards)
    ability = db.Column(db.String(30), nullable=True)  # CardAbility value
    ability_cooldown = db.Column(db.Integer, default=0)  # Current cooldown in turns

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
    is_destroyed = db.Column(db.Boolean, default=False)  # Lost in battle (legacy)

    # Cooldown system (replaces permanent death)
    cooldown_until = db.Column(
        db.DateTime, nullable=True
    )  # When card becomes available

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

    def is_on_cooldown(self) -> bool:
        """Check if card is on cooldown."""
        if not self.cooldown_until:
            return False
        return datetime.utcnow() < self.cooldown_until

    def start_cooldown(self, hours: int = 1):
        """Put card on cooldown after battle defeat."""
        self.cooldown_until = datetime.utcnow() + timedelta(hours=hours)
        self.current_hp = 0
        self.is_in_deck = False

    def clear_cooldown(self):
        """Clear cooldown and restore HP (after cooldown expires or skip)."""
        self.cooldown_until = None
        self.current_hp = self.hp

    def get_cooldown_remaining(self) -> int | None:
        """Get remaining cooldown time in seconds, or None if not on cooldown."""
        if not self.cooldown_until:
            return None
        remaining = (self.cooldown_until - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))

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

    @property
    def ability_info(self) -> dict | None:
        """Get ability configuration info."""
        if not self.ability:
            return None
        try:
            ability_enum = CardAbility(self.ability)
            config = ABILITY_CONFIG.get(ability_enum, {})
            return {
                "type": self.ability,
                "name": config.get("name", self.ability),
                "description": config.get("description", ""),
                "emoji": config.get("emoji", "✨"),
                "cooldown": config.get("cooldown", 0),
                "current_cooldown": self.ability_cooldown or 0,
            }
        except ValueError:
            return None

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
            "ability": self.ability,
            "ability_info": self.ability_info,
            "image_url": self.image_url,
            "emoji": self.emoji,
            "is_in_deck": self.is_in_deck,
            "is_tradeable": self.is_tradeable,
            "is_alive": self.is_alive,
            "is_on_cooldown": self.is_on_cooldown(),
            "cooldown_remaining": self.get_cooldown_remaining(),
            "cooldown_until": (
                self.cooldown_until.isoformat() if self.cooldown_until else None
            ),
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
    # For multi-card trades
    sender_card_ids = db.Column(db.JSON, nullable=True)

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
    # For multi-card exchanges
    receiver_card_ids = db.Column(db.JSON, nullable=True)

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

    def get_sender_cards(self) -> list:
        """Get all sender cards (supports both single and multi-card)."""
        # Check for multi-card (with safety for pre-migration)
        card_ids = getattr(self, "sender_card_ids", None)
        if card_ids:
            cards = UserCard.query.filter(UserCard.id.in_(card_ids)).all()
            return [c.to_dict() for c in cards]
        elif self.sender_card:
            return [self.sender_card.to_dict()]
        return []

    def get_receiver_cards(self) -> list:
        """Get all receiver cards (supports both single and multi-card)."""
        # Check for multi-card (with safety for pre-migration)
        card_ids = getattr(self, "receiver_card_ids", None)
        if card_ids:
            cards = UserCard.query.filter(UserCard.id.in_(card_ids)).all()
            return [c.to_dict() for c in cards]
        elif self.receiver_card:
            return [self.receiver_card.to_dict()]
        return []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        sender_cards = self.get_sender_cards()
        receiver_cards = self.get_receiver_cards()

        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            # Single card (backward compatibility)
            "sender_card": sender_cards[0] if sender_cards else None,
            "receiver_card": receiver_cards[0] if receiver_cards else None,
            # Multi-card support
            "sender_cards": sender_cards,
            "receiver_cards": receiver_cards,
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


class MergeLog(db.Model):
    """History of card merges."""

    __tablename__ = "merge_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source cards info (saved because cards will be destroyed)
    card1_name = db.Column(db.String(100), nullable=False)
    card1_rarity = db.Column(db.String(20), nullable=False)
    card2_name = db.Column(db.String(100), nullable=False)
    card2_rarity = db.Column(db.String(20), nullable=False)

    # Result
    result_card_id = db.Column(
        db.Integer,
        db.ForeignKey("user_cards.id", ondelete="SET NULL"),
        nullable=True,
    )
    result_rarity = db.Column(db.String(20), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", backref=db.backref("merges", lazy="dynamic"))
    result_card = db.relationship("UserCard")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "card1_name": self.card1_name,
            "card1_rarity": self.card1_rarity,
            "card2_name": self.card2_name,
            "card2_rarity": self.card2_rarity,
            "result_card": self.result_card.to_dict() if self.result_card else None,
            "result_rarity": self.result_rarity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PendingReferralReward(db.Model):
    """Store pending referral rewards to show when user logs in."""

    __tablename__ = "pending_referral_rewards"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    friend_name = db.Column(db.String(255), nullable=True)
    card_id = db.Column(db.Integer, db.ForeignKey("user_cards.id"), nullable=False)
    is_referrer = db.Column(
        db.Boolean, default=True
    )  # True = you invited, False = you were invited
    is_claimed = db.Column(db.Boolean, default=False)
    notified_at = db.Column(
        db.DateTime, nullable=True
    )  # When bot notification was sent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id])
    friend = db.relationship("User", foreign_keys=[friend_id])
    card = db.relationship("UserCard")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "friend_id": self.friend_id,
            "friend_name": self.friend_name,
            "card": self.card.to_dict() if self.card else None,
            "is_referrer": self.is_referrer,
            "is_claimed": self.is_claimed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
