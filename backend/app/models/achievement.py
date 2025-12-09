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
        "title": "Первый шаг",
        "description": "Выполни свой первый шаг — каждый путь начинается с малого",
        "xp_reward": 25,
        "icon": "footsteps",
        "category": "beginner",
    },
    {
        "code": "first_task",
        "title": "Задача выполнена",
        "description": "Заверши свою первую задачу целиком",
        "xp_reward": 50,
        "icon": "rocket",
        "category": "beginner",
    },
    {
        "code": "first_mood",
        "title": "Познай себя",
        "description": "Отметь своё настроение в первый раз",
        "xp_reward": 15,
        "icon": "sparkle",
        "category": "beginner",
    },
    {
        "code": "first_focus",
        "title": "Сфокусирован",
        "description": "Заверши свою первую фокус-сессию",
        "xp_reward": 30,
        "icon": "target",
        "category": "beginner",
    },
    # === Gentle Streaks (Soft, forgiving) ===
    {
        "code": "streak_3",
        "title": "3 дня подряд",
        "description": "3 дня подряд с хотя бы одним выполненным шагом",
        "xp_reward": 40,
        "icon": "fire",
        "category": "streaks",
        "progress_max": 3,
    },
    {
        "code": "streak_7",
        "title": "Неделя прогресса",
        "description": "Целая неделя продуктивности!",
        "xp_reward": 100,
        "icon": "flame",
        "category": "streaks",
        "progress_max": 7,
    },
    {
        "code": "streak_14",
        "title": "Две недели силы",
        "description": "14 дней стабильности",
        "xp_reward": 200,
        "icon": "zap",
        "category": "streaks",
        "progress_max": 14,
    },
    {
        "code": "streak_30",
        "title": "Чемпион месяца",
        "description": "Полный месяц ежедневного прогресса",
        "xp_reward": 500,
        "icon": "medal",
        "category": "streaks",
        "progress_max": 30,
    },
    # === Mood Bonuses (Reward honesty) ===
    {
        "code": "mood_tracker_5",
        "title": "Самопознание",
        "description": "Отметь настроение 5 раз",
        "xp_reward": 30,
        "icon": "heart",
        "category": "mood",
        "progress_max": 5,
    },
    {
        "code": "mood_tracker_20",
        "title": "Мастер настроения",
        "description": "Отметь настроение 20 раз",
        "xp_reward": 75,
        "icon": "brain",
        "category": "mood",
        "progress_max": 20,
    },
    {
        "code": "honest_day",
        "title": "Честный день",
        "description": "Выполни задачу в день с низкой энергией",
        "xp_reward": 50,
        "icon": "shield",
        "category": "mood",
    },
    {
        "code": "low_energy_hero",
        "title": "Герой усталости",
        "description": "Выполни 5 задач в дни с низкой энергией",
        "xp_reward": 100,
        "icon": "heart-hand",
        "category": "mood",
        "progress_max": 5,
    },
    # === Focus Achievements ===
    {
        "code": "focus_5",
        "title": "Учусь фокусу",
        "description": "Заверши 5 фокус-сессий",
        "xp_reward": 50,
        "icon": "bullseye",
        "category": "focus",
        "progress_max": 5,
    },
    {
        "code": "focus_25",
        "title": "Фокус-спринтер",
        "description": "Заверши 25 фокус-сессий",
        "xp_reward": 150,
        "icon": "timer",
        "category": "focus",
        "progress_max": 25,
    },
    {
        "code": "focus_hour",
        "title": "Час силы",
        "description": "60 минут фокуса за один день",
        "xp_reward": 75,
        "icon": "clock",
        "category": "focus",
    },
    {
        "code": "deep_focus",
        "title": "Глубокий фокус",
        "description": "Заверши сессию 45+ минут",
        "xp_reward": 60,
        "icon": "brain",
        "category": "focus",
    },
    # === Task Milestones ===
    {
        "code": "tasks_5",
        "title": "Прогресс идёт",
        "description": "Заверши 5 задач",
        "xp_reward": 50,
        "icon": "check-circle",
        "category": "tasks",
        "progress_max": 5,
    },
    {
        "code": "tasks_25",
        "title": "Мастер задач",
        "description": "Заверши 25 задач",
        "xp_reward": 150,
        "icon": "star",
        "category": "tasks",
        "progress_max": 25,
    },
    {
        "code": "tasks_100",
        "title": "Клуб сотни",
        "description": "Заверши 100 задач",
        "xp_reward": 400,
        "icon": "crown",
        "category": "tasks",
        "progress_max": 100,
    },
    {
        "code": "subtasks_50",
        "title": "Шаг за шагом",
        "description": "Заверши 50 шагов",
        "xp_reward": 100,
        "icon": "layers",
        "category": "tasks",
        "progress_max": 50,
    },
    # === Levels ===
    {
        "code": "level_3",
        "title": "Новый уровень!",
        "description": "Достигни 3 уровня",
        "xp_reward": 50,
        "icon": "trending-up",
        "category": "levels",
        "progress_max": 3,
    },
    {
        "code": "level_5",
        "title": "Восходящая звезда",
        "description": "Достигни 5 уровня",
        "xp_reward": 100,
        "icon": "star",
        "category": "levels",
        "progress_max": 5,
    },
    {
        "code": "level_10",
        "title": "Профи продуктивности",
        "description": "Достигни 10 уровня",
        "xp_reward": 250,
        "icon": "award",
        "category": "levels",
        "progress_max": 10,
    },
    # === Daily/Weekly Quests (Hidden until triggered) ===
    {
        "code": "perfect_day",
        "title": "Идеальный день",
        "description": "Выполни все ежедневные цели",
        "xp_reward": 50,
        "icon": "sun",
        "category": "daily",
        "is_hidden": True,
    },
    {
        "code": "weekend_warrior",
        "title": "Воин выходных",
        "description": "Выполни задачу на выходных",
        "xp_reward": 30,
        "icon": "coffee",
        "category": "special",
        "is_hidden": True,
    },
    {
        "code": "early_bird",
        "title": "Ранняя пташка",
        "description": "Выполни задачу до 9 утра",
        "xp_reward": 30,
        "icon": "sunrise",
        "category": "special",
        "is_hidden": True,
    },
    {
        "code": "night_owl",
        "title": "Ночная сова",
        "description": "Выполни задачу после 22:00",
        "xp_reward": 30,
        "icon": "moon",
        "category": "special",
        "is_hidden": True,
    },
]


# Level names for display (Russian)
LEVEL_NAMES = {
    1: "Новичок",
    2: "Стартер",
    3: "Исследователь",
    4: "Достигатор",
    5: "Сфокусированный",
    6: "Стабильный",
    7: "Преданный",
    8: "Опытный",
    9: "Эксперт",
    10: "Мастер",
    11: "Чемпион",
    12: "Легенда",
    13: "Гуру",
    14: "Мудрец",
    15: "Просветлённый",
}


def get_level_name(level: int) -> str:
    """Get display name for a level."""
    if level <= 0:
        return "Ученик"
    if level > 15:
        return f"Трансцендент {level - 15}"
    return LEVEL_NAMES.get(level, f"Уровень {level}")
