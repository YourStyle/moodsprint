"""Daily quests model for gamification."""

from datetime import date, datetime

from app import db


class DailyQuest(db.Model):
    """Daily quest assigned to user."""

    __tablename__ = "daily_quests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Quest info
    quest_type = db.Column(
        db.String(50), nullable=False
    )  # task_before_noon, streak_tasks, high_priority, etc.
    title = db.Column(db.String(200), nullable=False)  # AI-generated themed title
    description = db.Column(db.String(500), nullable=True)  # Original description
    themed_description = db.Column(
        db.String(500), nullable=True
    )  # AI-generated themed description

    # Requirements
    target_count = db.Column(db.Integer, default=1, nullable=False)
    current_count = db.Column(db.Integer, default=0, nullable=False)

    # Rewards
    xp_reward = db.Column(db.Integer, default=50, nullable=False)
    stat_points_reward = db.Column(db.Integer, default=1, nullable=False)

    # Status
    date = db.Column(db.Date, default=date.today, nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    claimed = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship("User", backref=db.backref("daily_quests", lazy="dynamic"))

    # Unique constraint: one quest type per user per day
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "quest_type", "date", name="unique_user_quest_date"
        ),
    )

    @property
    def progress_percent(self) -> int:
        """Progress percentage."""
        if self.target_count == 0:
            return 100 if self.completed else 0
        return min(100, int(self.current_count / self.target_count * 100))

    def increment_progress(self, amount: int = 1) -> bool:
        """Increment progress and check completion. Returns True if just completed."""
        if self.completed:
            return False

        self.current_count += amount
        if self.current_count >= self.target_count:
            self.completed = True
            self.completed_at = datetime.utcnow()
            return True
        return False

    def claim_reward(self) -> dict | None:
        """Claim reward if completed and not yet claimed."""
        if not self.completed or self.claimed:
            return None

        self.claimed = True
        return {
            "xp": self.xp_reward,
            "stat_points": self.stat_points_reward,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "quest_type": self.quest_type,
            "title": self.title,
            "description": self.description,
            "themed_description": self.themed_description,
            "target_count": self.target_count,
            "current_count": self.current_count,
            "progress_percent": self.progress_percent,
            "xp_reward": self.xp_reward,
            "stat_points_reward": self.stat_points_reward,
            "date": self.date.isoformat() if self.date else None,
            "completed": self.completed,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "claimed": self.claimed,
        }


# Quest templates
QUEST_TEMPLATES = {
    "early_bird": {
        "description": "Выполни задачу до 10:00",
        "target_count": 1,
        "xp_reward": 50,
        "stat_points_reward": 1,
    },
    "task_before_noon": {
        "description": "Выполни задачу до обеда",
        "target_count": 1,
        "xp_reward": 40,
        "stat_points_reward": 1,
    },
    "streak_tasks": {
        "description": "Выполни 3 задачи подряд",
        "target_count": 3,
        "xp_reward": 60,
        "stat_points_reward": 2,
    },
    "high_priority_first": {
        "description": "Начни день с высокоприоритетной задачи",
        "target_count": 1,
        "xp_reward": 50,
        "stat_points_reward": 1,
    },
    "focus_master": {
        "description": "Проведи 2 фокус-сессии",
        "target_count": 2,
        "xp_reward": 70,
        "stat_points_reward": 2,
    },
    "subtask_warrior": {
        "description": "Выполни 5 подзадач",
        "target_count": 5,
        "xp_reward": 50,
        "stat_points_reward": 1,
    },
    "mood_tracker": {
        "description": "Отметь настроение 2 раза за день",
        "target_count": 2,
        "xp_reward": 30,
        "stat_points_reward": 1,
    },
    "complete_all": {
        "description": "Выполни все задачи на сегодня",
        "target_count": 1,  # Will be updated based on user's tasks
        "xp_reward": 100,
        "stat_points_reward": 3,
    },
    "arena_battles": {
        "description": "Победи в 2 боях на арене",
        "target_count": 2,
        "xp_reward": 60,
        "stat_points_reward": 2,
    },
    "merge_cards": {
        "description": "Выполни слияние карт",
        "target_count": 1,
        "xp_reward": 50,
        "stat_points_reward": 1,
    },
    "collect_rarity": {
        "description": "Получи редкую карту или выше",
        "target_count": 1,
        "xp_reward": 70,
        "stat_points_reward": 2,
    },
    "campaign_stars": {
        "description": "Заработай 3 звезды в кампании",
        "target_count": 3,
        "xp_reward": 80,
        "stat_points_reward": 2,
    },
    "use_abilities": {
        "description": "Используй 3 способности карт в боях",
        "target_count": 3,
        "xp_reward": 50,
        "stat_points_reward": 1,
    },
}


# Genre-themed quest name templates for AI generation
QUEST_NAME_PROMPTS = {
    "magic": {
        "early_bird": "ранний магический ритуал",
        "task_before_noon": "утреннее заклинание",
        "streak_tasks": "магическая цепочка заклинаний",
        "high_priority_first": "мощное первое заклинание",
        "focus_master": "сеансы медитации волшебника",
        "subtask_warrior": "малые заклинания",
        "mood_tracker": "чтение ауры",
        "complete_all": "завершение магического ритуала",
        "arena_battles": "дуэли магов",
        "merge_cards": "слияние артефактов",
        "collect_rarity": "поиск редкого артефакта",
        "campaign_stars": "покорение звёздных башен",
        "use_abilities": "применение заклинаний",
    },
    "fantasy": {
        "early_bird": "рассветный поход",
        "task_before_noon": "утренняя вылазка",
        "streak_tasks": "цепь побед",
        "high_priority_first": "битва с главным врагом",
        "focus_master": "тренировка воина",
        "subtask_warrior": "малые подвиги",
        "mood_tracker": "совет с мудрецом",
        "complete_all": "завершение эпического квеста",
        "arena_battles": "поединки на арене",
        "merge_cards": "ковка легендарного оружия",
        "collect_rarity": "обнаружение реликвии",
        "campaign_stars": "завоевание звёзд подземелья",
        "use_abilities": "применение боевых умений",
    },
    "scifi": {
        "early_bird": "утренний протокол",
        "task_before_noon": "операция 'Рассвет'",
        "streak_tasks": "последовательность миссий",
        "high_priority_first": "приоритетная миссия",
        "focus_master": "калибровка систем",
        "subtask_warrior": "выполнение подпротоколов",
        "mood_tracker": "сканирование биометрии",
        "complete_all": "выполнение директивы",
        "arena_battles": "космические сражения",
        "merge_cards": "синтез компонентов",
        "collect_rarity": "обнаружение артефакта предтеч",
        "campaign_stars": "колонизация секторов",
        "use_abilities": "активация спецсистем",
    },
    "cyberpunk": {
        "early_bird": "ранний взлом",
        "task_before_noon": "утренний контракт",
        "streak_tasks": "серия хаков",
        "high_priority_first": "взлом корпорации",
        "focus_master": "нейро-калибровка",
        "subtask_warrior": "обход файрволов",
        "mood_tracker": "нейросканирование",
        "complete_all": "завершение операции",
        "arena_battles": "уличные перестрелки",
        "merge_cards": "апгрейд импланта",
        "collect_rarity": "добыча прототипа",
        "campaign_stars": "зачистка районов",
        "use_abilities": "активация аугментаций",
    },
    "anime": {
        "early_bird": "утренняя тренировка",
        "task_before_noon": "испытание до полудня",
        "streak_tasks": "комбо атак",
        "high_priority_first": "сражение с сильнейшим",
        "focus_master": "медитация воина",
        "subtask_warrior": "отработка техник",
        "mood_tracker": "чтение чакры",
        "complete_all": "путь ниндзя",
        "arena_battles": "турнирные бои",
        "merge_cards": "слияние духов",
        "collect_rarity": "призыв легендарного духа",
        "campaign_stars": "прохождение испытаний",
        "use_abilities": "использование ультимативных техник",
    },
}
