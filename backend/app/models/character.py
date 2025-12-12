"""Character stats and battle models for gamification."""

from datetime import datetime

from app import db

# Genre themes for quests
GENRE_THEMES = {
    "magic": {
        "name": "Магия",
        "description": "Волшебный мир как в Гарри Поттере",
        "emoji": "🧙‍♂️",
        "quest_prefix": ["Заклинание", "Зелье", "Магический"],
        "stat_names": {
            "strength": "Сила заклинаний",
            "agility": "Ловкость волшебника",
            "intelligence": "Мудрость",
        },
        "monsters": ["Тёмный маг", "Дементор", "Василиск", "Оборотень", "Горгулья"],
    },
    "fantasy": {
        "name": "Фэнтези",
        "description": "Эпический мир как Властелин Колец",
        "emoji": "⚔️",
        "quest_prefix": ["Поход", "Битва", "Легендарный"],
        "stat_names": {
            "strength": "Сила воина",
            "agility": "Скорость эльфа",
            "intelligence": "Мудрость волшебника",
        },
        "monsters": ["Орк", "Тролль", "Назгул", "Дракон", "Балрог"],
    },
    "scifi": {
        "name": "Научная фантастика",
        "description": "Космические приключения",
        "emoji": "🚀",
        "quest_prefix": ["Миссия", "Операция", "Протокол"],
        "stat_names": {
            "strength": "Мощность",
            "agility": "Рефлексы",
            "intelligence": "Интеллект",
        },
        "monsters": ["Киборг", "Инопланетянин", "Дрон", "Мутант", "Робот-страж"],
    },
    "cyberpunk": {
        "name": "Киберпанк",
        "description": "Мир высоких технологий и хакеров",
        "emoji": "🌆",
        "quest_prefix": ["Взлом", "Операция", "Контракт"],
        "stat_names": {
            "strength": "Кибер-сила",
            "agility": "Нейро-рефлексы",
            "intelligence": "Хакинг",
        },
        "monsters": [
            "Корпоративный дрон",
            "Хакер",
            "Киллер-бот",
            "Мутант",
            "Босс корпорации",
        ],
    },
    "anime": {
        "name": "Аниме",
        "description": "Мир японских приключений",
        "emoji": "🎌",
        "quest_prefix": ["Тренировка", "Испытание", "Путь"],
        "stat_names": {
            "strength": "Сила духа",
            "agility": "Скорость",
            "intelligence": "Чакра",
        },
        "monsters": ["Демон", "Ниндзя", "Каджу", "Тёмный самурай", "Древний дух"],
    },
}


class CharacterStats(db.Model):
    """Character stats for user's avatar."""

    __tablename__ = "character_stats"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Base stats (0-100)
    strength = db.Column(db.Integer, default=10, nullable=False)
    agility = db.Column(db.Integer, default=10, nullable=False)
    intelligence = db.Column(db.Integer, default=10, nullable=False)

    # Battle stats
    max_hp = db.Column(db.Integer, default=100, nullable=False)
    current_hp = db.Column(db.Integer, default=100, nullable=False)
    battles_won = db.Column(db.Integer, default=0, nullable=False)
    battles_lost = db.Column(db.Integer, default=0, nullable=False)

    # Stat points to distribute
    available_stat_points = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    user = db.relationship("User", backref=db.backref("character", uselist=False))

    @property
    def total_stats(self) -> int:
        """Total stat points distributed."""
        return self.strength + self.agility + self.intelligence

    @property
    def attack_power(self) -> int:
        """Calculate attack power based on stats."""
        return self.strength * 2 + self.agility

    @property
    def defense(self) -> int:
        """Calculate defense based on stats."""
        return self.strength + self.intelligence

    @property
    def speed(self) -> int:
        """Calculate speed based on stats."""
        return self.agility * 2 + self.intelligence // 2

    def heal(self, amount: int = None):
        """Heal character. If no amount, full heal."""
        if amount is None:
            self.current_hp = self.max_hp
        else:
            self.current_hp = min(self.max_hp, self.current_hp + amount)

    def take_damage(self, amount: int) -> int:
        """Take damage and return actual damage taken."""
        actual_damage = max(1, amount - self.defense // 10)
        self.current_hp = max(0, self.current_hp - actual_damage)
        return actual_damage

    def add_stat_points(self, points: int):
        """Add stat points from completing tasks."""
        self.available_stat_points += points

    def distribute_stat(self, stat_name: str, points: int) -> bool:
        """Distribute available points to a stat."""
        if points > self.available_stat_points:
            return False
        if stat_name not in ["strength", "agility", "intelligence"]:
            return False

        current_value = getattr(self, stat_name)
        if current_value + points > 100:
            return False

        setattr(self, stat_name, current_value + points)
        self.available_stat_points -= points

        # Update max HP based on new stats
        self.max_hp = 100 + self.strength * 2 + self.intelligence

        return True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "strength": self.strength,
            "agility": self.agility,
            "intelligence": self.intelligence,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "attack_power": self.attack_power,
            "defense": self.defense,
            "speed": self.speed,
            "battles_won": self.battles_won,
            "battles_lost": self.battles_lost,
            "available_stat_points": self.available_stat_points,
            "total_stats": self.total_stats,
        }


class Monster(db.Model):
    """Monsters for battle arena (template monsters)."""

    __tablename__ = "monsters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)  # AI-generated description
    genre = db.Column(db.String(50), nullable=False)  # magic, fantasy, scifi, etc.

    # Base stats (will be scaled for players)
    base_level = db.Column(db.Integer, default=1, nullable=False)
    base_hp = db.Column(db.Integer, default=50, nullable=False)
    base_attack = db.Column(db.Integer, default=10, nullable=False)
    base_defense = db.Column(db.Integer, default=5, nullable=False)
    base_speed = db.Column(db.Integer, default=10, nullable=False)

    # Legacy columns for backwards compatibility
    level = db.Column(db.Integer, default=1, nullable=False)
    hp = db.Column(db.Integer, default=50, nullable=False)
    attack = db.Column(db.Integer, default=10, nullable=False)
    defense = db.Column(db.Integer, default=5, nullable=False)
    speed = db.Column(db.Integer, default=10, nullable=False)

    # Base rewards (scaled for player level)
    base_xp_reward = db.Column(db.Integer, default=20, nullable=False)
    base_stat_points_reward = db.Column(db.Integer, default=1, nullable=False)
    xp_reward = db.Column(db.Integer, default=20, nullable=False)
    stat_points_reward = db.Column(db.Integer, default=1, nullable=False)

    # Visual
    sprite_url = db.Column(db.String(512), nullable=True)
    emoji = db.Column(db.String(10), default="👾")

    is_boss = db.Column(db.Boolean, default=False)

    # Generation tracking
    ai_generated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "level": self.level,
            "hp": self.hp,
            "attack": self.attack,
            "defense": self.defense,
            "speed": self.speed,
            "xp_reward": self.xp_reward,
            "stat_points_reward": self.stat_points_reward,
            "sprite_url": self.sprite_url,
            "emoji": self.emoji,
            "is_boss": self.is_boss,
        }

    def get_scaled_stats(self, player_level: int) -> dict:
        """Get monster stats scaled to player level."""
        # Scale factor: slightly easier than player level
        scale = 0.8 + (player_level * 0.15)

        return {
            "level": max(1, int(self.base_level * scale)),
            "hp": max(20, int(self.base_hp * scale)),
            "attack": max(5, int(self.base_attack * scale)),
            "defense": max(2, int(self.base_defense * scale)),
            "speed": max(5, int(self.base_speed * scale)),
            "xp_reward": max(10, int(self.base_xp_reward * scale)),
            "stat_points_reward": max(
                1, int(self.base_stat_points_reward * (scale * 0.5))
            ),
        }


class DailyMonster(db.Model):
    """Daily monsters shown to players per genre."""

    __tablename__ = "daily_monsters"

    id = db.Column(db.Integer, primary_key=True)
    monster_id = db.Column(
        db.Integer,
        db.ForeignKey("monsters.id", ondelete="CASCADE"),
        nullable=False,
    )
    genre = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    slot_number = db.Column(db.Integer, default=1)  # 1-6 monsters per day

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    monster = db.relationship("Monster")

    __table_args__ = (
        db.UniqueConstraint(
            "genre", "date", "slot_number", name="unique_daily_monster"
        ),
    )


class MonsterCard(db.Model):
    """Cards that belong to a monster's deck."""

    __tablename__ = "monster_cards"

    id = db.Column(db.Integer, primary_key=True)
    monster_id = db.Column(
        db.Integer,
        db.ForeignKey("monsters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Stats
    hp = db.Column(db.Integer, default=50, nullable=False)
    attack = db.Column(db.Integer, default=15, nullable=False)

    # Visual
    emoji = db.Column(db.String(10), default="👾")
    image_url = db.Column(db.String(512), nullable=True)

    # Rarity affects stats scaling
    rarity = db.Column(db.String(20), default="common")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    monster = db.relationship(
        "Monster", backref=db.backref("cards", lazy="dynamic", cascade="all, delete")
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "monster_id": self.monster_id,
            "name": self.name,
            "description": self.description,
            "hp": self.hp,
            "attack": self.attack,
            "emoji": self.emoji,
            "image_url": self.image_url,
            "rarity": self.rarity,
        }


class ActiveBattle(db.Model):
    """Active turn-based battle state."""

    __tablename__ = "active_battles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monster_id = db.Column(
        db.Integer,
        db.ForeignKey("monsters.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Battle state stored as JSON
    # Contains: player_cards, monster_cards, current_turn, battle_log
    state = db.Column(db.JSON, nullable=False, default=dict)

    # Status: active, won, lost
    status = db.Column(db.String(20), default="active")

    current_round = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = db.relationship("User")
    monster = db.relationship("Monster")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "monster_id": self.monster_id,
            "monster": self.monster.to_dict() if self.monster else None,
            "state": self.state,
            "status": self.status,
            "current_round": self.current_round,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BattleLog(db.Model):
    """Log of battles."""

    __tablename__ = "battle_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monster_id = db.Column(
        db.Integer,
        db.ForeignKey("monsters.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Battle result
    won = db.Column(db.Boolean, nullable=False)
    rounds = db.Column(db.Integer, default=0)
    damage_dealt = db.Column(db.Integer, default=0)
    damage_taken = db.Column(db.Integer, default=0)

    # Rewards earned
    xp_earned = db.Column(db.Integer, default=0)
    stat_points_earned = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship("User", backref=db.backref("battles", lazy="dynamic"))
    monster = db.relationship("Monster")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "monster": self.monster.to_dict() if self.monster else None,
            "won": self.won,
            "rounds": self.rounds,
            "damage_dealt": self.damage_dealt,
            "damage_taken": self.damage_taken,
            "xp_earned": self.xp_earned,
            "stat_points_earned": self.stat_points_earned,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
