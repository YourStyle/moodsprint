"""Service for seasonal events."""

import logging
from datetime import date, datetime
from typing import Any

from app import db
from app.models.event import EventMonster, EventType, SeasonalEvent, UserEventProgress

logger = logging.getLogger(__name__)


# Predefined seasonal events (auto-triggered by calendar)
PREDEFINED_EVENTS = {
    "new_year": {
        "name": "Новогодний марафон",
        "description": "Победи зимних монстров и получи праздничные карты! Бонус XP x1.5",
        "start_month": 12,
        "start_day": 25,
        "end_month": 1,
        "end_day": 7,
        "emoji": "🎄",
        "theme_color": "#00A86B",
        "xp_multiplier": 1.5,
        "monsters": ["Снежный голем", "Ледяной дракон", "Дед Мороз"],
    },
    "halloween": {
        "name": "Ночь ужасов",
        "description": "Тёмные силы пробудились. Сразись с ними за эксклюзивные награды!",
        "start_month": 10,
        "start_day": 25,
        "end_month": 11,
        "end_day": 2,
        "emoji": "🎃",
        "theme_color": "#FF6600",
        "xp_multiplier": 1.3,
        "monsters": ["Призрак", "Вампир", "Тыквенный король"],
    },
    "spring": {
        "name": "Весеннее пробуждение",
        "description": "Природа просыпается... вместе с древними существами.",
        "start_month": 3,
        "start_day": 20,
        "end_month": 3,
        "end_day": 27,
        "emoji": "🌸",
        "theme_color": "#FFB7C5",
        "xp_multiplier": 1.2,
        "monsters": ["Лесной дух", "Цветочный голем", "Весенний дракон"],
    },
    "summer": {
        "name": "Жаркое лето",
        "description": "Солнце в зените. Огненные существа вышли на охоту!",
        "start_month": 6,
        "start_day": 21,
        "end_month": 6,
        "end_day": 28,
        "emoji": "☀️",
        "theme_color": "#FFD700",
        "xp_multiplier": 1.2,
        "monsters": ["Огненный элементаль", "Песчаный червь", "Солнечный феникс"],
    },
}


class EventService:
    """Service for managing seasonal events."""

    def get_active_event(self) -> SeasonalEvent | None:
        """Get currently active event if any."""
        now = datetime.utcnow()
        return SeasonalEvent.query.filter(
            SeasonalEvent.is_active.is_(True),
            SeasonalEvent.start_date <= now,
            SeasonalEvent.end_date >= now,
        ).first()

    def get_all_events(self, include_past: bool = False) -> list[SeasonalEvent]:
        """Get all events, optionally including past ones."""
        query = SeasonalEvent.query
        if not include_past:
            query = query.filter(SeasonalEvent.end_date >= datetime.utcnow())
        return query.order_by(SeasonalEvent.start_date.desc()).all()

    def get_event_by_id(self, event_id: int) -> SeasonalEvent | None:
        """Get event by ID."""
        return SeasonalEvent.query.get(event_id)

    def get_event_monsters(self, event_id: int) -> list[EventMonster]:
        """Get monsters for a specific event."""
        return EventMonster.query.filter_by(event_id=event_id).all()

    def get_user_progress(
        self, user_id: int, event_id: int
    ) -> UserEventProgress | None:
        """Get user's progress in an event."""
        return UserEventProgress.query.filter_by(
            user_id=user_id, event_id=event_id
        ).first()

    def get_or_create_user_progress(
        self, user_id: int, event_id: int
    ) -> UserEventProgress:
        """Get or create user's progress in an event."""
        progress = self.get_user_progress(user_id, event_id)
        if not progress:
            progress = UserEventProgress(
                user_id=user_id,
                event_id=event_id,
                monsters_defeated=0,
                bosses_defeated=0,
                exclusive_cards_earned=0,
                milestones=[],
            )
            db.session.add(progress)
            db.session.commit()
        return progress

    def update_progress_on_monster_defeat(
        self, user_id: int, monster_id: int, is_boss: bool
    ) -> dict[str, Any] | None:
        """Update user's event progress when they defeat a monster."""
        event = self.get_active_event()
        if not event:
            return None

        # Check if this monster is part of the event
        event_monster = EventMonster.query.filter_by(
            event_id=event.id, monster_id=monster_id
        ).first()
        if not event_monster:
            return None

        # Update progress
        progress = self.get_or_create_user_progress(user_id, event.id)
        progress.monsters_defeated += 1
        if is_boss:
            progress.bosses_defeated += 1

        # Update event monster stats
        event_monster.times_defeated += 1

        # Check for milestones
        new_milestones = self._check_milestones(progress, event)

        db.session.commit()

        return {
            "event": event.to_dict(),
            "progress": progress.to_dict(),
            "new_milestones": new_milestones,
        }

    def create_manual_event(
        self,
        code: str,
        name: str,
        description: str,
        start_date: datetime,
        end_date: datetime,
        created_by: int | None = None,
        emoji: str = "🎉",
        theme_color: str = "#FF6B00",
        xp_multiplier: float = 1.0,
    ) -> SeasonalEvent:
        """Create a manual (admin-controlled) event."""
        event = SeasonalEvent(
            code=code,
            name=name,
            description=description,
            event_type=EventType.MANUAL.value,
            start_date=start_date,
            end_date=end_date,
            emoji=emoji,
            theme_color=theme_color,
            xp_multiplier=xp_multiplier,
            is_active=True,
            created_by=created_by,
        )
        db.session.add(event)
        db.session.commit()
        return event

    def add_monster_to_event(
        self,
        event_id: int,
        monster_id: int,
        appear_day: int = 1,
        exclusive_reward_name: str | None = None,
        guaranteed_rarity: str | None = None,
    ) -> EventMonster:
        """Add a monster to an event."""
        event_monster = EventMonster(
            event_id=event_id,
            monster_id=monster_id,
            appear_day=appear_day,
            exclusive_reward_name=exclusive_reward_name,
            guaranteed_rarity=guaranteed_rarity,
        )
        db.session.add(event_monster)
        db.session.commit()
        return event_monster

    def check_and_create_seasonal_events(self) -> SeasonalEvent | None:
        """
        Check if any predefined seasonal events should start today.
        Called by scheduler.
        """
        today = date.today()

        for code, config in PREDEFINED_EVENTS.items():
            # Check if this event should start today
            if (
                today.month == config["start_month"]
                and today.day == config["start_day"]
            ):
                year = today.year
                # Handle year transition for new_year event
                if code == "new_year" and config["end_month"] < config["start_month"]:
                    end_year = year + 1
                else:
                    end_year = year

                full_code = f"{code}_{year}"

                # Check if already exists
                existing = SeasonalEvent.query.filter_by(code=full_code).first()
                if existing:
                    continue

                # Create event
                event = self._create_seasonal_event(full_code, config, year, end_year)
                logger.info(f"Created seasonal event: {full_code}")
                return event

        return None

    def _create_seasonal_event(
        self, code: str, config: dict, year: int, end_year: int
    ) -> SeasonalEvent:
        """Create a predefined seasonal event."""
        start_date = datetime(year, config["start_month"], config["start_day"], 0, 0, 0)
        end_date = datetime(
            end_year, config["end_month"], config["end_day"], 23, 59, 59
        )

        event = SeasonalEvent(
            code=code,
            name=config["name"],
            description=config["description"],
            event_type=EventType.SEASONAL.value,
            start_date=start_date,
            end_date=end_date,
            emoji=config["emoji"],
            theme_color=config["theme_color"],
            xp_multiplier=config.get("xp_multiplier", 1.0),
            is_active=True,
        )
        db.session.add(event)
        db.session.commit()

        # TODO: Create event monsters from config["monsters"]
        # This would require generating/finding monster templates

        return event

    def _check_milestones(
        self, progress: UserEventProgress, event: SeasonalEvent
    ) -> list[dict]:
        """Check and award milestones based on progress."""
        new_milestones = []
        current_milestones = progress.milestones or []

        # Define milestone thresholds
        monster_milestones = [
            {"code": "monsters_5", "count": 5, "title": "Охотник", "xp": 50},
            {"code": "monsters_10", "count": 10, "title": "Истребитель", "xp": 100},
            {"code": "monsters_25", "count": 25, "title": "Легенда арены", "xp": 250},
        ]

        boss_milestones = [
            {"code": "bosses_1", "count": 1, "title": "Убийца боссов", "xp": 75},
            {"code": "bosses_3", "count": 3, "title": "Грозный воин", "xp": 150},
        ]

        # Check monster milestones
        for milestone in monster_milestones:
            if (
                milestone["code"] not in current_milestones
                and progress.monsters_defeated >= milestone["count"]
            ):
                current_milestones.append(milestone["code"])
                new_milestones.append(
                    {
                        "code": milestone["code"],
                        "title": milestone["title"],
                        "xp_reward": milestone["xp"],
                    }
                )

        # Check boss milestones
        for milestone in boss_milestones:
            if (
                milestone["code"] not in current_milestones
                and progress.bosses_defeated >= milestone["count"]
            ):
                current_milestones.append(milestone["code"])
                new_milestones.append(
                    {
                        "code": milestone["code"],
                        "title": milestone["title"],
                        "xp_reward": milestone["xp"],
                    }
                )

        progress.milestones = current_milestones
        return new_milestones

    def deactivate_event(self, event_id: int) -> bool:
        """Deactivate an event."""
        event = SeasonalEvent.query.get(event_id)
        if not event:
            return False
        event.is_active = False
        db.session.commit()
        return True
