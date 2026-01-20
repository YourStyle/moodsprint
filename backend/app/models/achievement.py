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


# Predefined achievements - gentle, supportive gamification (with translations)
ACHIEVEMENTS = [
    # === First Steps (Easy to unlock, encouraging) ===
    {
        "code": "first_step",
        "title": "Первый шаг",
        "title_en": "First Step",
        "description": "Выполни свой первый шаг — каждый путь начинается с малого",
        "description_en": "Complete your first step — every journey begins with a single step",
        "xp_reward": 25,
        "icon": "footsteps",
        "category": "beginner",
    },
    {
        "code": "first_task",
        "title": "Задача выполнена",
        "title_en": "Task Completed",
        "description": "Заверши свою первую задачу целиком",
        "description_en": "Complete your first task entirely",
        "xp_reward": 50,
        "icon": "rocket",
        "category": "beginner",
    },
    {
        "code": "first_mood",
        "title": "Познай себя",
        "title_en": "Know Yourself",
        "description": "Отметь своё настроение в первый раз",
        "description_en": "Log your mood for the first time",
        "xp_reward": 15,
        "icon": "sparkle",
        "category": "beginner",
    },
    {
        "code": "first_focus",
        "title": "Сфокусирован",
        "title_en": "Focused",
        "description": "Заверши свою первую фокус-сессию",
        "description_en": "Complete your first focus session",
        "xp_reward": 30,
        "icon": "target",
        "category": "beginner",
    },
    # === Gentle Streaks (Soft, forgiving) ===
    {
        "code": "streak_3",
        "title": "3 дня подряд",
        "title_en": "3 Days in a Row",
        "description": "3 дня подряд с хотя бы одним выполненным шагом",
        "description_en": "3 days in a row with at least one completed step",
        "xp_reward": 40,
        "icon": "fire",
        "category": "streaks",
        "progress_max": 3,
    },
    {
        "code": "streak_7",
        "title": "Неделя прогресса",
        "title_en": "Week of Progress",
        "description": "Целая неделя продуктивности!",
        "description_en": "A whole week of productivity!",
        "xp_reward": 100,
        "icon": "flame",
        "category": "streaks",
        "progress_max": 7,
    },
    {
        "code": "streak_14",
        "title": "Две недели силы",
        "title_en": "Two Weeks Strong",
        "description": "14 дней стабильности",
        "description_en": "14 days of consistency",
        "xp_reward": 200,
        "icon": "zap",
        "category": "streaks",
        "progress_max": 14,
    },
    {
        "code": "streak_30",
        "title": "Чемпион месяца",
        "title_en": "Month Champion",
        "description": "Полный месяц ежедневного прогресса",
        "description_en": "A full month of daily progress",
        "xp_reward": 500,
        "icon": "medal",
        "category": "streaks",
        "progress_max": 30,
    },
    # === Mood Bonuses (Reward honesty) ===
    {
        "code": "mood_tracker_5",
        "title": "Самопознание",
        "title_en": "Self-Awareness",
        "description": "Отметь настроение 5 раз",
        "description_en": "Log your mood 5 times",
        "xp_reward": 30,
        "icon": "heart",
        "category": "mood",
        "progress_max": 5,
    },
    {
        "code": "mood_tracker_20",
        "title": "Мастер настроения",
        "title_en": "Mood Master",
        "description": "Отметь настроение 20 раз",
        "description_en": "Log your mood 20 times",
        "xp_reward": 75,
        "icon": "brain",
        "category": "mood",
        "progress_max": 20,
    },
    {
        "code": "honest_day",
        "title": "Честный день",
        "title_en": "Honest Day",
        "description": "Выполни задачу в день с низкой энергией",
        "description_en": "Complete a task on a low energy day",
        "xp_reward": 50,
        "icon": "shield",
        "category": "mood",
    },
    {
        "code": "low_energy_hero",
        "title": "Герой усталости",
        "title_en": "Low Energy Hero",
        "description": "Выполни 5 задач в дни с низкой энергией",
        "description_en": "Complete 5 tasks on low energy days",
        "xp_reward": 100,
        "icon": "heart-hand",
        "category": "mood",
        "progress_max": 5,
    },
    # === Focus Achievements ===
    {
        "code": "focus_5",
        "title": "Учусь фокусу",
        "title_en": "Learning Focus",
        "description": "Заверши 5 фокус-сессий",
        "description_en": "Complete 5 focus sessions",
        "xp_reward": 50,
        "icon": "bullseye",
        "category": "focus",
        "progress_max": 5,
    },
    {
        "code": "focus_25",
        "title": "Фокус-спринтер",
        "title_en": "Focus Sprinter",
        "description": "Заверши 25 фокус-сессий",
        "description_en": "Complete 25 focus sessions",
        "xp_reward": 150,
        "icon": "timer",
        "category": "focus",
        "progress_max": 25,
    },
    {
        "code": "focus_hour",
        "title": "Час силы",
        "title_en": "Power Hour",
        "description": "60 минут фокуса за один день",
        "description_en": "60 minutes of focus in one day",
        "xp_reward": 75,
        "icon": "clock",
        "category": "focus",
    },
    {
        "code": "deep_focus",
        "title": "Глубокий фокус",
        "title_en": "Deep Focus",
        "description": "Заверши сессию 45+ минут",
        "description_en": "Complete a session of 45+ minutes",
        "xp_reward": 60,
        "icon": "brain",
        "category": "focus",
    },
    # === Task Milestones ===
    {
        "code": "tasks_5",
        "title": "Прогресс идёт",
        "title_en": "Progress Flowing",
        "description": "Заверши 5 задач",
        "description_en": "Complete 5 tasks",
        "xp_reward": 50,
        "icon": "check-circle",
        "category": "tasks",
        "progress_max": 5,
    },
    {
        "code": "tasks_25",
        "title": "Мастер задач",
        "title_en": "Task Master",
        "description": "Заверши 25 задач",
        "description_en": "Complete 25 tasks",
        "xp_reward": 150,
        "icon": "star",
        "category": "tasks",
        "progress_max": 25,
    },
    {
        "code": "tasks_100",
        "title": "Клуб сотни",
        "title_en": "Century Club",
        "description": "Заверши 100 задач",
        "description_en": "Complete 100 tasks",
        "xp_reward": 400,
        "icon": "crown",
        "category": "tasks",
        "progress_max": 100,
    },
    {
        "code": "subtasks_50",
        "title": "Шаг за шагом",
        "title_en": "Step by Step",
        "description": "Заверши 50 шагов",
        "description_en": "Complete 50 steps",
        "xp_reward": 100,
        "icon": "layers",
        "category": "tasks",
        "progress_max": 50,
    },
    # === Levels ===
    {
        "code": "level_3",
        "title": "Новый уровень!",
        "title_en": "Level Up!",
        "description": "Достигни 3 уровня",
        "description_en": "Reach level 3",
        "xp_reward": 50,
        "icon": "trending-up",
        "category": "levels",
        "progress_max": 3,
    },
    {
        "code": "level_5",
        "title": "Восходящая звезда",
        "title_en": "Rising Star",
        "description": "Достигни 5 уровня",
        "description_en": "Reach level 5",
        "xp_reward": 100,
        "icon": "star",
        "category": "levels",
        "progress_max": 5,
    },
    {
        "code": "level_10",
        "title": "Профи продуктивности",
        "title_en": "Productivity Pro",
        "description": "Достигни 10 уровня",
        "description_en": "Reach level 10",
        "xp_reward": 250,
        "icon": "award",
        "category": "levels",
        "progress_max": 10,
    },
    # === Daily/Weekly Quests (Hidden until triggered) ===
    {
        "code": "perfect_day",
        "title": "Идеальный день",
        "title_en": "Perfect Day",
        "description": "Выполни все ежедневные цели",
        "description_en": "Complete all daily goals",
        "xp_reward": 50,
        "icon": "sun",
        "category": "daily",
        "is_hidden": True,
    },
    {
        "code": "weekend_warrior",
        "title": "Воин выходных",
        "title_en": "Weekend Warrior",
        "description": "Выполни задачу на выходных",
        "description_en": "Complete a task on the weekend",
        "xp_reward": 30,
        "icon": "coffee",
        "category": "special",
        "is_hidden": True,
    },
    {
        "code": "early_bird",
        "title": "Ранняя пташка",
        "title_en": "Early Bird",
        "description": "Выполни задачу до 9 утра",
        "description_en": "Complete a task before 9 AM",
        "xp_reward": 30,
        "icon": "sunrise",
        "category": "special",
        "is_hidden": True,
    },
    {
        "code": "night_owl",
        "title": "Ночная сова",
        "title_en": "Night Owl",
        "description": "Выполни задачу после 22:00",
        "description_en": "Complete a task after 10 PM",
        "xp_reward": 30,
        "icon": "moon",
        "category": "special",
        "is_hidden": True,
    },
]


# Level names for display with localization
LEVEL_NAMES = {
    1: {"ru": "Новичок", "en": "Novice"},
    2: {"ru": "Стартер", "en": "Starter"},
    3: {"ru": "Исследователь", "en": "Explorer"},
    4: {"ru": "Достигатор", "en": "Achiever"},
    5: {"ru": "Сфокусированный", "en": "Focused"},
    6: {"ru": "Стабильный", "en": "Steady"},
    7: {"ru": "Преданный", "en": "Dedicated"},
    8: {"ru": "Опытный", "en": "Experienced"},
    9: {"ru": "Эксперт", "en": "Expert"},
    10: {"ru": "Мастер", "en": "Master"},
    11: {"ru": "Чемпион", "en": "Champion"},
    12: {"ru": "Легенда", "en": "Legend"},
    13: {"ru": "Гуру", "en": "Guru"},
    14: {"ru": "Мудрец", "en": "Sage"},
    15: {"ru": "Просветлённый", "en": "Enlightened"},
}


def get_level_name(level: int, lang: str = "ru") -> str:
    """Get display name for a level with localization."""
    if level <= 0:
        return "Apprentice" if lang == "en" else "Ученик"
    if level > 15:
        suffix = level - 15
        return f"Transcendent {suffix}" if lang == "en" else f"Трансцендент {suffix}"
    level_data = LEVEL_NAMES.get(level, {})
    if isinstance(level_data, dict):
        return level_data.get(lang, level_data.get("ru", f"Level {level}"))
    return level_data  # Backward compatibility


def get_achievement_data(achievement: dict, lang: str = "ru") -> dict:
    """Get achievement data with localization."""
    use_en = lang == "en"
    return {
        "code": achievement["code"],
        "title": achievement.get("title_en") if use_en else achievement.get("title"),
        "description": (
            achievement.get("description_en")
            if use_en
            else achievement.get("description")
        ),
        "xp_reward": achievement.get("xp_reward", 0),
        "icon": achievement.get("icon", "trophy"),
        "category": achievement.get("category", "general"),
        "progress_max": achievement.get("progress_max"),
        "is_hidden": achievement.get("is_hidden", False),
    }
