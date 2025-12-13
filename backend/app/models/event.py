"""Seasonal events models."""

from datetime import datetime
from enum import Enum

from app import db


class EventType(str, Enum):
    """Types of events."""

    SEASONAL = "seasonal"  # Auto-triggered by calendar (New Year, Halloween, etc.)
    MANUAL = "manual"  # Admin-controlled events
    SPECIAL = "special"  # Special occasions (anniversary, etc.)


class SeasonalEvent(db.Model):
    """Seasonal and special events."""

    __tablename__ = "seasonal_events"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)  # e.g., halloween_2024
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    event_type = db.Column(db.String(20), default=EventType.SEASONAL.value)

    # Timing
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)

    # Visual
    banner_url = db.Column(db.String(512), nullable=True)
    theme_color = db.Column(db.String(7), default="#FF6B00")  # Hex color
    emoji = db.Column(db.String(10), default="🎉")

    # Settings
    is_active = db.Column(db.Boolean, default=True)
    xp_multiplier = db.Column(db.Float, default=1.0)  # 1.5 = +50% XP

    # Admin control
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    creator = db.relationship("User", foreign_keys=[created_by])

    @property
    def is_currently_active(self) -> bool:
        """Check if event is currently running."""
        now = datetime.utcnow()
        return self.is_active and self.start_date <= now <= self.end_date

    @property
    def days_remaining(self) -> int:
        """Days remaining until event ends."""
        if not self.is_currently_active:
            return 0
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "banner_url": self.banner_url,
            "theme_color": self.theme_color,
            "emoji": self.emoji,
            "is_active": self.is_active,
            "is_currently_active": self.is_currently_active,
            "xp_multiplier": self.xp_multiplier,
            "days_remaining": self.days_remaining,
        }


class EventMonster(db.Model):
    """Event-specific monsters with exclusive rewards."""

    __tablename__ = "event_monsters"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("seasonal_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monster_id = db.Column(
        db.Integer,
        db.ForeignKey("monsters.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Appearance order (1 = first day of event)
    appear_day = db.Column(db.Integer, default=1)

    # Exclusive rewards
    exclusive_reward_name = db.Column(db.String(100), nullable=True)
    guaranteed_rarity = db.Column(db.String(20), nullable=True)  # Guaranteed rarity

    # Stats
    times_defeated = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    event = db.relationship("SeasonalEvent", backref="event_monsters")
    monster = db.relationship("Monster")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "monster": self.monster.to_dict() if self.monster else None,
            "appear_day": self.appear_day,
            "exclusive_reward_name": self.exclusive_reward_name,
            "guaranteed_rarity": self.guaranteed_rarity,
            "times_defeated": self.times_defeated,
        }


class UserEventProgress(db.Model):
    """Track user progress in events."""

    __tablename__ = "user_event_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("seasonal_events.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Progress
    monsters_defeated = db.Column(db.Integer, default=0)
    bosses_defeated = db.Column(db.Integer, default=0)
    exclusive_cards_earned = db.Column(db.Integer, default=0)

    # Milestones achieved (JSON array of milestone codes)
    milestones = db.Column(db.JSON, default=list)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="unique_user_event"),
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("event_progress", lazy="dynamic"))
    event = db.relationship("SeasonalEvent")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "monsters_defeated": self.monsters_defeated,
            "bosses_defeated": self.bosses_defeated,
            "exclusive_cards_earned": self.exclusive_cards_earned,
            "milestones": self.milestones or [],
        }
