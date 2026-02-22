"""Guild system models for social features, raids, and weekly quests."""

from datetime import datetime

from app import db


class Guild(db.Model):
    """Guild/Clan for social features."""

    __tablename__ = "guilds"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    emoji = db.Column(db.String(10), default="⚔️")

    # Leader
    leader_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Guild progression
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)

    # Settings
    is_public = db.Column(db.Boolean, default=True)  # Anyone can join
    max_members = db.Column(db.Integer, default=30)

    # Quest preferences (JSON array of quest_type strings)
    preferred_quest_types = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    leader = db.relationship("User", foreign_keys=[leader_id])
    members = db.relationship(
        "GuildMember", backref="guild", lazy="dynamic", cascade="all, delete-orphan"
    )
    raids = db.relationship(
        "GuildRaid", backref="guild", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def member_count(self) -> int:
        """Get current member count."""
        return self.members.count()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "emoji": self.emoji,
            "leader_id": self.leader_id,
            "level": self.level,
            "xp": self.xp,
            "is_public": self.is_public,
            "max_members": self.max_members,
            "members_count": self.member_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GuildMember(db.Model):
    """Guild membership."""

    __tablename__ = "guild_members"

    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(
        db.Integer,
        db.ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role: leader, officer, member
    role = db.Column(db.String(20), default="member")

    # Contribution tracking
    contribution_xp = db.Column(db.Integer, default=0)
    raids_participated = db.Column(db.Integer, default=0)
    total_damage_dealt = db.Column(db.Integer, default=0)

    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint("guild_id", "user_id", name="unique_guild_member"),
    )

    # Relationships
    user = db.relationship(
        "User", backref=db.backref("guild_membership", uselist=False)
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "role": self.role,
            "contribution_xp": self.contribution_xp,
            "raids_participated": self.raids_participated,
            "total_damage_dealt": self.total_damage_dealt,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "user": self.user.to_dict() if self.user else None,
        }


class GuildRaid(db.Model):
    """Guild raid against a powerful boss."""

    __tablename__ = "guild_raids"

    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(
        db.Integer,
        db.ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monster_id = db.Column(
        db.Integer,
        db.ForeignKey("monsters.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Boss stats (scaled for guild size)
    boss_name = db.Column(db.String(100), nullable=False)
    boss_emoji = db.Column(db.String(10), default="👹")
    total_hp = db.Column(db.Integer, nullable=False)  # Total HP to defeat
    current_hp = db.Column(db.Integer, nullable=False)  # Remaining HP

    # Status: active, won, expired, cancelled
    status = db.Column(db.String(20), default="active")

    # Rewards
    xp_reward = db.Column(db.Integer, default=500)
    card_reward_rarity = db.Column(db.String(20), default="rare")  # Minimum rarity

    # Timing
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)  # 24-48 hours from start
    completed_at = db.Column(db.DateTime, nullable=True)

    # Stats
    total_damage_dealt = db.Column(db.Integer, default=0)
    participants_count = db.Column(db.Integer, default=0)

    # Relationships
    monster = db.relationship("Monster")
    contributions = db.relationship(
        "GuildRaidContribution",
        backref="raid",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "monster_id": self.monster_id,
            "boss_name": self.boss_name,
            "boss_emoji": self.boss_emoji,
            "total_hp": self.total_hp,
            "current_hp": self.current_hp,
            "hp_percentage": (
                int((self.current_hp / self.total_hp) * 100) if self.total_hp > 0 else 0
            ),
            "status": self.status,
            "xp_reward": self.xp_reward,
            "card_reward_rarity": self.card_reward_rarity,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "total_damage_dealt": self.total_damage_dealt,
            "participants_count": self.participants_count,
        }


class GuildRaidContribution(db.Model):
    """Individual contribution to a guild raid."""

    __tablename__ = "guild_raid_contributions"

    id = db.Column(db.Integer, primary_key=True)
    raid_id = db.Column(
        db.Integer,
        db.ForeignKey("guild_raids.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Contribution stats
    damage_dealt = db.Column(db.Integer, default=0)
    attacks_count = db.Column(db.Integer, default=0)
    last_attack_at = db.Column(db.DateTime, nullable=True)

    # Daily limit tracking (3 attacks per day)
    attacks_today = db.Column(db.Integer, default=0)
    attacks_reset_date = db.Column(db.Date, nullable=True)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint("raid_id", "user_id", name="unique_raid_contribution"),
    )

    # Relationships
    user = db.relationship("User")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "raid_id": self.raid_id,
            "user_id": self.user_id,
            "damage_dealt": self.damage_dealt,
            "attacks_count": self.attacks_count,
            "attacks_today": self.attacks_today,
            "last_attack_at": (
                self.last_attack_at.isoformat() if self.last_attack_at else None
            ),
        }


class GuildInvite(db.Model):
    """Invite to join a guild."""

    __tablename__ = "guild_invites"

    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(
        db.Integer,
        db.ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status: pending, accepted, rejected, expired
    status = db.Column(db.String(20), default="pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    guild = db.relationship("Guild")
    user = db.relationship("User", foreign_keys=[user_id])
    invited_by = db.relationship("User", foreign_keys=[invited_by_id])

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "guild": self.guild.to_dict() if self.guild else None,
            "user_id": self.user_id,
            "invited_by_id": self.invited_by_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GuildQuest(db.Model):
    """Weekly quest for a guild."""

    __tablename__ = "guild_quests"

    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(
        db.Integer,
        db.ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Quest definition
    quest_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    emoji = db.Column(db.String(10), default="📋")
    target = db.Column(db.Integer, nullable=False)
    progress = db.Column(db.Integer, default=0)

    # Time window
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)

    # Status: active, completed, expired
    status = db.Column(db.String(20), default="active")

    # Rewards
    xp_reward = db.Column(db.Integer, default=200)
    sparks_reward = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    contributions = db.relationship(
        "GuildQuestContribution",
        backref="quest",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        # Get top 5 contributors
        top_contributors = []
        try:
            contribs = (
                self.contributions.order_by(GuildQuestContribution.amount.desc())
                .limit(5)
                .all()
            )
            for c in contribs:
                user = c.user
                top_contributors.append(
                    {
                        "user_id": c.user_id,
                        "username": user.username if user else None,
                        "first_name": user.first_name if user else None,
                        "amount": c.amount,
                    }
                )
        except Exception:
            pass

        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "quest_type": self.quest_type,
            "title": self.title,
            "emoji": self.emoji,
            "target": self.target,
            "progress": min(self.progress, self.target),
            "percentage": (
                min(100, int(self.progress / self.target * 100))
                if self.target > 0
                else 0
            ),
            "week_start": str(self.week_start),
            "week_end": str(self.week_end),
            "status": self.status,
            "xp_reward": self.xp_reward,
            "sparks_reward": self.sparks_reward,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "top_contributors": top_contributors,
        }


class GuildQuestContribution(db.Model):
    """Per-member contribution to a guild quest."""

    __tablename__ = "guild_quest_contributions"

    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(
        db.Integer,
        db.ForeignKey("guild_quests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = db.Column(db.Integer, default=0, nullable=False)
    last_contributed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("quest_id", "user_id", name="unique_quest_contribution"),
    )

    # Relationships
    user = db.relationship("User")
