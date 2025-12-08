"""Achievement models."""

from datetime import datetime

from app import db


class Achievement(db.Model):
    """Achievement definition model."""

    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    xp_reward = db.Column(db.Integer, default=50, nullable=False)
    icon = db.Column(db.String(50), default="trophy", nullable=False)
    category = db.Column(db.String(50), default="general", nullable=False)

    # For progress-based achievements
    progress_max = db.Column(db.Integer, nullable=True)

    # Hidden achievements are not shown until unlocked
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    user_achievements = db.relationship(
        "UserAchievement", backref="achievement", lazy="dynamic"
    )

    def to_dict(self) -> dict:
        """Convert achievement to dictionary."""
        return {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "xp_reward": self.xp_reward,
            "icon": self.icon,
            "category": self.category,
            "progress_max": self.progress_max,
            "is_hidden": self.is_hidden,
        }

    def __repr__(self) -> str:
        return f"<Achievement {self.code}>"


class UserAchievement(db.Model):
    """User's unlocked achievements."""

    __tablename__ = "user_achievements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    achievement_id = db.Column(
        db.Integer, db.ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False
    )

    # Progress tracking
    progress = db.Column(db.Integer, default=0, nullable=False)

    # Unlock timestamp
    unlocked_at = db.Column(db.DateTime, nullable=True)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "achievement_id", name="unique_user_achievement"
        ),
    )

    @property
    def is_unlocked(self) -> bool:
        """Check if achievement is unlocked."""
        return self.unlocked_at is not None

    def unlock(self):
        """Unlock the achievement."""
        if not self.is_unlocked:
            self.unlocked_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert user achievement to dictionary."""
        result = self.achievement.to_dict()
        result["progress"] = self.progress
        result["unlocked_at"] = (
            self.unlocked_at.isoformat() if self.unlocked_at else None
        )
        result["is_unlocked"] = self.is_unlocked
        return result

    def __repr__(self) -> str:
        return f"<UserAchievement {self.user_id}:{self.achievement_id}>"


# Predefined achievements - gentle, supportive gamification
ACHIEVEMENTS = [
    # === First Steps (Easy to unlock, encouraging) ===
    {
        "code": "first_step",
        "title": "First Step",
        "description": "Complete your first subtask - every journey starts here",
        "xp_reward": 25,
        "icon": "footsteps",
        "category": "beginner",
    },
    {
        "code": "first_task",
        "title": "Task Complete",
        "description": "Complete your first full task",
        "xp_reward": 50,
        "icon": "rocket",
        "category": "beginner",
    },
    {
        "code": "first_mood",
        "title": "Know Yourself",
        "description": "Log your mood for the first time",
        "xp_reward": 15,
        "icon": "sparkle",
        "category": "beginner",
    },
    {
        "code": "first_focus",
        "title": "Focused",
        "description": "Complete your first focus session",
        "xp_reward": 30,
        "icon": "target",
        "category": "beginner",
    },
    # === Gentle Streaks (Soft, forgiving) ===
    {
        "code": "streak_3",
        "title": "3 Days Strong",
        "description": "3 days in a row with at least one step - keep going!",
        "xp_reward": 40,
        "icon": "fire",
        "category": "streaks",
        "progress_max": 3,
    },
    {
        "code": "streak_7",
        "title": "Week Warrior",
        "description": "A whole week of progress!",
        "xp_reward": 100,
        "icon": "flame",
        "category": "streaks",
        "progress_max": 7,
    },
    {
        "code": "streak_14",
        "title": "Fortnight Force",
        "description": "14 days of consistency",
        "xp_reward": 200,
        "icon": "zap",
        "category": "streaks",
        "progress_max": 14,
    },
    {
        "code": "streak_30",
        "title": "Monthly Champion",
        "description": "A full month of daily progress",
        "xp_reward": 500,
        "icon": "medal",
        "category": "streaks",
        "progress_max": 30,
    },
    # === Mood Bonuses (Reward honesty) ===
    {
        "code": "mood_tracker_5",
        "title": "Self-Aware",
        "description": "Log your mood 5 times",
        "xp_reward": 30,
        "icon": "heart",
        "category": "mood",
        "progress_max": 5,
    },
    {
        "code": "mood_tracker_20",
        "title": "Mood Master",
        "description": "Log your mood 20 times",
        "xp_reward": 75,
        "icon": "brain",
        "category": "mood",
        "progress_max": 20,
    },
    {
        "code": "honest_day",
        "title": "Honest Day",
        "description": "Complete a task on a low-energy day",
        "xp_reward": 50,
        "icon": "shield",
        "category": "mood",
    },
    {
        "code": "low_energy_hero",
        "title": "Low Energy Hero",
        "description": "Complete 5 tasks on low-energy days",
        "xp_reward": 100,
        "icon": "heart-hand",
        "category": "mood",
        "progress_max": 5,
    },
    # === Focus Achievements ===
    {
        "code": "focus_5",
        "title": "Getting Focused",
        "description": "Complete 5 focus sessions",
        "xp_reward": 50,
        "icon": "bullseye",
        "category": "focus",
        "progress_max": 5,
    },
    {
        "code": "focus_25",
        "title": "Focus Sprinter",
        "description": "Complete 25 focus sessions",
        "xp_reward": 150,
        "icon": "timer",
        "category": "focus",
        "progress_max": 25,
    },
    {
        "code": "focus_hour",
        "title": "Hour of Power",
        "description": "60 minutes of focus in one day",
        "xp_reward": 75,
        "icon": "clock",
        "category": "focus",
    },
    {
        "code": "deep_focus",
        "title": "Deep Focus",
        "description": "Complete a 45+ minute session",
        "xp_reward": 60,
        "icon": "brain",
        "category": "focus",
    },
    # === Task Milestones ===
    {
        "code": "tasks_5",
        "title": "Making Progress",
        "description": "Complete 5 tasks",
        "xp_reward": 50,
        "icon": "check-circle",
        "category": "tasks",
        "progress_max": 5,
    },
    {
        "code": "tasks_25",
        "title": "Task Master",
        "description": "Complete 25 tasks",
        "xp_reward": 150,
        "icon": "star",
        "category": "tasks",
        "progress_max": 25,
    },
    {
        "code": "tasks_100",
        "title": "Century Club",
        "description": "Complete 100 tasks",
        "xp_reward": 400,
        "icon": "crown",
        "category": "tasks",
        "progress_max": 100,
    },
    {
        "code": "subtasks_50",
        "title": "Step by Step",
        "description": "Complete 50 subtasks",
        "xp_reward": 100,
        "icon": "layers",
        "category": "tasks",
        "progress_max": 50,
    },
    # === Levels ===
    {
        "code": "level_3",
        "title": "Level Up!",
        "description": "Reach level 3",
        "xp_reward": 50,
        "icon": "trending-up",
        "category": "levels",
        "progress_max": 3,
    },
    {
        "code": "level_5",
        "title": "Rising Star",
        "description": "Reach level 5",
        "xp_reward": 100,
        "icon": "star",
        "category": "levels",
        "progress_max": 5,
    },
    {
        "code": "level_10",
        "title": "Productivity Pro",
        "description": "Reach level 10",
        "xp_reward": 250,
        "icon": "award",
        "category": "levels",
        "progress_max": 10,
    },
    # === Daily/Weekly Quests (Hidden until triggered) ===
    {
        "code": "perfect_day",
        "title": "Perfect Day",
        "description": "Complete all daily goals",
        "xp_reward": 50,
        "icon": "sun",
        "category": "daily",
        "is_hidden": True,
    },
    {
        "code": "weekend_warrior",
        "title": "Weekend Warrior",
        "description": "Complete a task on the weekend",
        "xp_reward": 30,
        "icon": "coffee",
        "category": "special",
        "is_hidden": True,
    },
    {
        "code": "early_bird",
        "title": "Early Bird",
        "description": "Complete a task before 9 AM",
        "xp_reward": 30,
        "icon": "sunrise",
        "category": "special",
        "is_hidden": True,
    },
    {
        "code": "night_owl",
        "title": "Night Owl",
        "description": "Complete a task after 10 PM",
        "xp_reward": 30,
        "icon": "moon",
        "category": "special",
        "is_hidden": True,
    },
]


# Level names for display
LEVEL_NAMES = {
    1: "Beginner",
    2: "Starter",
    3: "Explorer",
    4: "Achiever",
    5: "Focused",
    6: "Consistent",
    7: "Dedicated",
    8: "Skilled",
    9: "Expert",
    10: "Master",
    11: "Champion",
    12: "Legend",
    13: "Guru",
    14: "Sage",
    15: "Enlightened",
}


def get_level_name(level: int) -> str:
    """Get display name for a level."""
    if level <= 0:
        return "Novice"
    if level > 15:
        return f"Transcendent {level - 15}"
    return LEVEL_NAMES.get(level, f"Level {level}")
