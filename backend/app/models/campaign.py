"""Campaign/Story mode models."""

from datetime import datetime

from app import db


class CampaignChapter(db.Model):
    """Story chapter (tied to a genre)."""

    __tablename__ = "campaign_chapters"
    __table_args__ = (
        db.UniqueConstraint("number", "genre", name="uq_chapter_number_genre"),
    )

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)  # Chapter number per genre
    name = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)  # fantasy, magic, scifi, etc

    # Story text
    description = db.Column(db.Text, nullable=True)
    story_intro = db.Column(db.Text, nullable=True)  # Shown at chapter start
    story_outro = db.Column(db.Text, nullable=True)  # Shown after boss defeat

    # Visual
    emoji = db.Column(db.String(10), default="📖")
    image_url = db.Column(db.String(500), nullable=True)  # Chapter cover image
    background_color = db.Column(db.String(20), default="#1a1a2e")

    # Requirements
    required_power = db.Column(db.Integer, default=0)  # Min deck power to enter

    # Rewards for completing chapter
    xp_reward = db.Column(db.Integer, default=500)
    guaranteed_card_rarity = db.Column(db.String(20), default="rare")

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    levels = db.relationship(
        "CampaignLevel",
        backref="chapter",
        lazy="dynamic",
        order_by="CampaignLevel.number",
        cascade="all, delete-orphan",
    )
    rewards = db.relationship(
        "CampaignReward",
        backref="chapter",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "genre": self.genre,
            "description": self.description,
            "story_intro": self.story_intro,
            "story_outro": self.story_outro,
            "emoji": self.emoji,
            "image_url": self.image_url,
            "background_color": self.background_color,
            "required_power": self.required_power,
            "xp_reward": self.xp_reward,
            "guaranteed_card_rarity": self.guaranteed_card_rarity,
            "levels_count": self.levels.count(),
        }


class CampaignLevel(db.Model):
    """Individual level within a chapter."""

    __tablename__ = "campaign_levels"

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(
        db.Integer,
        db.ForeignKey("campaign_chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number = db.Column(db.Integer, nullable=False)  # 1-6 within chapter

    # Monster for this level
    monster_id = db.Column(
        db.Integer,
        db.ForeignKey("monsters.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Level type
    is_boss = db.Column(db.Boolean, default=False)  # Boss level (last in chapter)

    # Story elements
    title = db.Column(db.String(100), nullable=True)
    dialogue_before = db.Column(db.JSON, nullable=True)
    # Format: [{"speaker": "Boss", "text": "...", "emoji": "👹"}, ...]
    dialogue_after = db.Column(db.JSON, nullable=True)

    # Difficulty scaling
    difficulty_multiplier = db.Column(db.Float, default=1.0)
    required_power = db.Column(db.Integer, default=0)

    # Rewards
    xp_reward = db.Column(db.Integer, default=50)
    stars_max = db.Column(db.Integer, default=3)  # 1-3 stars based on performance

    is_active = db.Column(db.Boolean, default=True)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint("chapter_id", "number", name="unique_chapter_level"),
    )

    # Relationships
    monster = db.relationship("Monster")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "chapter_id": self.chapter_id,
            "number": self.number,
            "monster_id": self.monster_id,
            "monster": self.monster.to_dict() if self.monster else None,
            "is_boss": self.is_boss,
            "title": self.title,
            "dialogue_before": self.dialogue_before,
            "dialogue_after": self.dialogue_after,
            "difficulty_multiplier": self.difficulty_multiplier,
            "required_power": self.required_power,
            "xp_reward": self.xp_reward,
            "stars_max": self.stars_max,
        }


class UserCampaignProgress(db.Model):
    """User's progress through the campaign."""

    __tablename__ = "user_campaign_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Current position
    current_chapter = db.Column(db.Integer, default=1)
    current_level = db.Column(db.Integer, default=1)

    # Completed chapters (JSON array of chapter IDs)
    chapters_completed = db.Column(db.JSON, default=list)

    # Total stats
    total_stars_earned = db.Column(db.Integer, default=0)
    bosses_defeated = db.Column(db.Integer, default=0)

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = db.relationship(
        "User", backref=db.backref("campaign_progress", uselist=False)
    )
    level_completions = db.relationship(
        "CampaignLevelCompletion",
        backref="progress",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "current_chapter": self.current_chapter,
            "current_level": self.current_level,
            "chapters_completed": self.chapters_completed or [],
            "total_stars_earned": self.total_stars_earned,
            "bosses_defeated": self.bosses_defeated,
        }


class CampaignLevelCompletion(db.Model):
    """Record of a level completion."""

    __tablename__ = "campaign_level_completions"

    id = db.Column(db.Integer, primary_key=True)
    progress_id = db.Column(
        db.Integer,
        db.ForeignKey("user_campaign_progress.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level_id = db.Column(
        db.Integer,
        db.ForeignKey("campaign_levels.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Best result
    stars_earned = db.Column(db.Integer, default=1)  # 1-3 stars
    best_rounds = db.Column(db.Integer, nullable=True)  # Fewest rounds
    best_hp_remaining = db.Column(db.Integer, nullable=True)  # Most HP remaining

    # Attempts
    attempts = db.Column(db.Integer, default=1)

    first_completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_completed_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint("progress_id", "level_id", name="unique_level_completion"),
    )

    # Relationships
    level = db.relationship("CampaignLevel")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "level_id": self.level_id,
            "stars_earned": self.stars_earned,
            "best_rounds": self.best_rounds,
            "attempts": self.attempts,
            "first_completed_at": (
                self.first_completed_at.isoformat() if self.first_completed_at else None
            ),
        }


class CampaignReward(db.Model):
    """Reward for completing a chapter."""

    __tablename__ = "campaign_rewards"

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(
        db.Integer,
        db.ForeignKey("campaign_chapters.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Reward type: card, xp, title, stars, special
    reward_type = db.Column(db.String(30), nullable=False)

    # Reward data (JSON)
    # For card: {"rarity": "legendary", "genre": "fantasy"}
    # For xp: {"amount": 1000}
    # For title: {"title": "Dragon Slayer"}
    reward_data = db.Column(db.JSON, nullable=False)

    # Visual
    name = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(200), nullable=True)
    emoji = db.Column(db.String(10), default="🎁")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "chapter_id": self.chapter_id,
            "reward_type": self.reward_type,
            "reward_data": self.reward_data,
            "name": self.name,
            "description": self.description,
            "emoji": self.emoji,
        }
