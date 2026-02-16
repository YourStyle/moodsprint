"""User model."""

from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(db.Model):
    """User model for storing user data."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True, index=True)
    username = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    photo_url = db.Column(db.String(512), nullable=True)

    # Email/password authentication
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)

    def set_password(self, password: str) -> None:
        """Set password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check password against hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # Gamification
    xp = db.Column(db.Integer, default=0, nullable=False)
    streak_days = db.Column(db.Integer, default=0, nullable=False)
    longest_streak = db.Column(db.Integer, default=0, nullable=False)
    last_activity_date = db.Column(db.Date, nullable=True)
    last_daily_bonus_date = db.Column(db.Date, nullable=True)
    last_streak_milestone_claimed = db.Column(db.Integer, default=0, nullable=False)
    comeback_card_pending = db.Column(db.Boolean, default=False, nullable=False)

    # Sparks - internal currency
    sparks = db.Column(db.Integer, default=0, nullable=False)

    # TON wallet integration
    ton_wallet_address = db.Column(db.String(48), nullable=True, index=True)

    # Referral system
    referred_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    referral_reward_given = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tasks = db.relationship(
        "Task", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    mood_checks = db.relationship(
        "MoodCheck", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    focus_sessions = db.relationship(
        "FocusSession", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    achievements = db.relationship(
        "UserAchievement", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def level(self) -> int:
        """Calculate user level based on XP."""
        import math

        if self.xp < 100:
            return 1
        return int(math.floor(math.sqrt(self.xp / 100))) + 1

    @property
    def xp_for_current_level(self) -> int:
        """XP required for current level."""
        if self.level == 1:
            return 0
        return ((self.level - 1) ** 2) * 100

    @property
    def xp_for_next_level(self) -> int:
        """XP required for next level."""
        return (self.level**2) * 100

    @property
    def xp_progress_percent(self) -> int:
        """Progress percentage to next level."""
        current_level_xp = self.xp_for_current_level
        next_level_xp = self.xp_for_next_level
        if next_level_xp == current_level_xp:
            return 100
        progress = (self.xp - current_level_xp) / (next_level_xp - current_level_xp)
        return int(progress * 100)

    def add_xp(self, amount: int) -> dict:
        """Add XP to user and return level up info."""
        old_level = self.level
        self.xp += amount
        new_level = self.level

        return {
            "xp_earned": amount,
            "total_xp": self.xp,
            "level_up": new_level > old_level,
            "old_level": old_level,
            "new_level": new_level,
        }

    def add_sparks(self, amount: int) -> int:
        """Add sparks to user. Returns new balance."""
        self.sparks += amount
        return self.sparks

    def spend_sparks(self, amount: int) -> bool:
        """Spend sparks. Returns True if successful, False if insufficient."""
        if self.sparks >= amount:
            self.sparks -= amount
            return True
        return False

    def update_streak(self) -> bool:
        """Update streak based on activity. Returns True if streak increased."""
        today = date.today()

        if self.last_activity_date is None:
            self.streak_days = 1
            self.last_activity_date = today
            return True

        days_diff = (today - self.last_activity_date).days

        if days_diff == 0:
            # Same day, no change
            return False
        elif days_diff == 1:
            # Consecutive day
            self.streak_days += 1
            if self.streak_days > self.longest_streak:
                self.longest_streak = self.streak_days
        else:
            # Streak broken
            self.streak_days = 1

        self.last_activity_date = today
        return True

    def to_dict(self) -> dict:
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "photo_url": self.photo_url,
            "xp": self.xp,
            "level": self.level,
            "xp_for_next_level": self.xp_for_next_level,
            "xp_progress_percent": self.xp_progress_percent,
            "streak_days": self.streak_days,
            "longest_streak": self.longest_streak,
            "sparks": self.sparks,
            "ton_wallet_address": self.ton_wallet_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.telegram_id}>"
