"""Card-based turn-by-turn battle arena service."""

import logging
import os
import random
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import requests

from app import db
from app.models import (
    ActiveBattle,
    BattleLog,
    DailyMonster,
    DefeatedMonster,
    Monster,
    MonsterCard,
    User,
)
from app.models.card import CardRarity, UserCard
from app.models.character import GENRE_THEMES
from app.models.user_profile import UserProfile
from app.utils import get_lang

logger = logging.getLogger(__name__)

# Monster reward configuration by type
MONSTER_REWARD_CONFIG = {
    "normal": {
        "card_chance": 1.0,  # 100% chance to get a card
        "rarity_weights": {
            CardRarity.COMMON: 1.0,  # 100% Common
            CardRarity.UNCOMMON: 0,
            CardRarity.RARE: 0,
            CardRarity.EPIC: 0,
            CardRarity.LEGENDARY: 0,
        },
    },
    "elite": {
        "card_chance": 1.0,
        "rarity_weights": {
            CardRarity.COMMON: 0,
            CardRarity.UNCOMMON: 0.70,  # 70% Uncommon
            CardRarity.RARE: 0.30,  # 30% Rare
            CardRarity.EPIC: 0,
            CardRarity.LEGENDARY: 0,
        },
    },
    "boss": {
        "card_chance": 1.0,
        "rarity_weights": {
            CardRarity.COMMON: 0,
            CardRarity.UNCOMMON: 0,
            CardRarity.RARE: 0.55,  # 55% Rare
            CardRarity.EPIC: 0.40,  # 40% Epic
            CardRarity.LEGENDARY: 0.05,  # 5% Legendary (reduced from 10%)
        },
    },
}

# Monster card templates per genre
MONSTER_CARD_TEMPLATES = {
    "magic": [
        {"name": "Тёмное заклинание", "emoji": "🌑", "attack": 18, "hp": 35},
        {"name": "Огненный шар", "emoji": "🔥", "attack": 22, "hp": 28},
        {"name": "Ледяная стрела", "emoji": "❄️", "attack": 20, "hp": 30},
        {"name": "Молния", "emoji": "⚡", "attack": 25, "hp": 25},
        {"name": "Теневой удар", "emoji": "👤", "attack": 16, "hp": 40},
        {"name": "Проклятие", "emoji": "💀", "attack": 19, "hp": 33},
        {"name": "Магический щит", "emoji": "🛡️", "attack": 12, "hp": 50},
    ],
    "fantasy": [
        {"name": "Орк-берсерк", "emoji": "👹", "attack": 24, "hp": 45},
        {"name": "Гоблин-вор", "emoji": "👺", "attack": 18, "hp": 30},
        {"name": "Тролль", "emoji": "🧌", "attack": 20, "hp": 55},
        {"name": "Скелет-воин", "emoji": "💀", "attack": 15, "hp": 35},
        {"name": "Тёмный эльф", "emoji": "🧝", "attack": 22, "hp": 32},
        {"name": "Огр", "emoji": "👾", "attack": 26, "hp": 48},
        {"name": "Призрачный рыцарь", "emoji": "⚔️", "attack": 21, "hp": 38},
    ],
    "scifi": [
        {"name": "Боевой дрон", "emoji": "🤖", "attack": 20, "hp": 35},
        {"name": "Кибер-солдат", "emoji": "🦾", "attack": 22, "hp": 40},
        {"name": "Инопланетянин", "emoji": "👽", "attack": 18, "hp": 45},
        {"name": "Лазерная турель", "emoji": "🔫", "attack": 25, "hp": 25},
        {"name": "Мутант", "emoji": "🧟", "attack": 16, "hp": 50},
        {"name": "Нанобот", "emoji": "🔬", "attack": 14, "hp": 32},
        {"name": "Плазменный страж", "emoji": "⚡", "attack": 23, "hp": 36},
    ],
    "cyberpunk": [
        {"name": "Хакер", "emoji": "💻", "attack": 18, "hp": 32},
        {"name": "Корпо-охранник", "emoji": "🕴️", "attack": 20, "hp": 42},
        {"name": "Киборг", "emoji": "🦿", "attack": 24, "hp": 38},
        {"name": "Нетраннер", "emoji": "🌐", "attack": 22, "hp": 30},
        {"name": "Уличный самурай", "emoji": "⚔️", "attack": 26, "hp": 35},
        {"name": "Боевой дрон", "emoji": "🤖", "attack": 19, "hp": 33},
        {"name": "Наёмник", "emoji": "🎯", "attack": 21, "hp": 40},
    ],
    "anime": [
        {"name": "Демон", "emoji": "👿", "attack": 22, "hp": 40},
        {"name": "Тёмный ниндзя", "emoji": "🥷", "attack": 20, "hp": 35},
        {"name": "Призрак", "emoji": "👻", "attack": 18, "hp": 45},
        {"name": "Огненный дух", "emoji": "🔥", "attack": 24, "hp": 30},
        {"name": "Ледяной воин", "emoji": "🧊", "attack": 20, "hp": 42},
        {"name": "Теневой клон", "emoji": "👤", "attack": 17, "hp": 38},
        {"name": "Древний ёкай", "emoji": "🎭", "attack": 23, "hp": 44},
    ],
}


# Monster character types for image generation per genre
MONSTER_CHARACTERS = {
    "magic": [
        "dark wizard with glowing evil eyes",
        "shadowy demon with horns",
        "cursed ghost with chains",
        "corrupted golem with purple crystals",
        "nightmare wraith floating",
    ],
    "fantasy": [
        "orc warlord with battle scars",
        "troll with massive club",
        "dark elf assassin",
        "undead knight in rusted armor",
        "fire dragon breathing flames",
    ],
    "scifi": [
        "alien creature with tentacles",
        "corrupted combat robot",
        "mutant monster with extra limbs",
        "space parasite creature",
        "rogue AI android with red eyes",
    ],
    "cyberpunk": [
        "cyber-enhanced gang leader",
        "rogue combat drone",
        "mutant street monster",
        "corporate killer robot",
        "netrunner gone insane with implants",
    ],
    "anime": [
        "demon lord with horns and dark aura",
        "evil ninja master",
        "corrupted samurai with glowing katana",
        "yokai spirit monster",
        "kaiju giant beast",
    ],
}

MONSTER_ART_STYLES = {
    "magic": (
        "art deco dark magic, steampunk evil wizard, brass clockwork curse, "
        "geometric sinister patterns, gold and black"
    ),
    "fantasy": (
        "art deco villain, steampunk monster armor, brass and copper menace, "
        "geometric dark ornaments, vintage evil poster"
    ),
    "scifi": (
        "art deco retro alien, steampunk robot enemy, brass machinery threat, "
        "geometric danger patterns, vintage sci-fi menace"
    ),
    "cyberpunk": (
        "art deco noir villain, steampunk cyber threat, brass implant horror, "
        "geometric neon evil, industrial nightmare"
    ),
    "anime": (
        "art deco anime villain, steampunk dark lord, brass accessories, "
        "geometric shadow patterns, vintage Japanese evil poster"
    ),
}


class CardBattleService:
    """Service for managing turn-based card battles."""

    # Stability AI config
    STABILITY_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

    def __init__(self):
        self.stability_api_key = os.getenv("STABILITY_API_KEY")

        # Store monster images in media volume (shared with nginx)
        self.images_dir = Path("/app/media/monster_images")
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def get_user_deck(self, user_id: int) -> list[UserCard]:
        """Get user's active battle deck."""
        return UserCard.query.filter_by(
            user_id=user_id, is_in_deck=True, is_destroyed=False
        ).all()

    def get_user_genre(self, user_id: int) -> str:
        """Get user's preferred genre."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile and profile.favorite_genre:
            return profile.favorite_genre
        return "fantasy"

    def get_available_monsters(self, user_id: int) -> list[dict]:
        """Get monsters available for battle (excluding defeated ones).

        Includes both regular period monsters and event monsters if an event is active.
        """
        from datetime import datetime

        from app.models.event import EventMonster, SeasonalEvent

        genre = self.get_user_genre(user_id)
        deck = self.get_user_deck(user_id)
        deck_power = sum(card.attack + card.hp for card in deck) if deck else 0

        # Get current period
        period_start = DailyMonster.get_current_period_start()

        # Get defeated monsters for this user in current period
        defeated_ids = {
            dm.monster_id
            for dm in DefeatedMonster.query.filter_by(
                user_id=user_id, period_start=period_start
            ).all()
        }

        result = []

        # Check for active event and include event monsters
        now = datetime.utcnow()
        active_event = SeasonalEvent.query.filter(
            SeasonalEvent.is_active.is_(True),
            SeasonalEvent.start_date <= now,
            SeasonalEvent.end_date >= now,
        ).first()

        lang = get_lang()

        if active_event:
            event_monsters = EventMonster.query.filter_by(
                event_id=active_event.id
            ).all()
            for em in event_monsters:
                if em.monster and em.monster.id not in defeated_ids:
                    monster_dict = em.monster.to_dict(lang)
                    scaled = self._scale_monster_for_deck(em.monster, deck_power)
                    monster_dict.update(scaled)
                    monster_dict["deck_size"] = self._get_monster_deck_size(em.monster)
                    monster_dict["cards_count"] = em.monster.cards.count()
                    monster_dict["is_event_monster"] = True
                    monster_dict["event_id"] = active_event.id
                    monster_dict["event_name"] = active_event.name
                    monster_dict["event_emoji"] = active_event.emoji
                    if em.guaranteed_rarity:
                        monster_dict["guaranteed_rarity"] = em.guaranteed_rarity
                    result.append(monster_dict)

        # Try to get period monsters
        period_monsters = (
            DailyMonster.query.filter_by(genre=genre, period_start=period_start)
            .order_by(DailyMonster.slot_number)
            .all()
        )

        if period_monsters:
            for dm in period_monsters:
                if dm.monster and dm.monster.id not in defeated_ids:
                    monster_dict = dm.monster.to_dict(lang)
                    scaled = self._scale_monster_for_deck(dm.monster, deck_power)
                    monster_dict.update(scaled)
                    monster_dict["deck_size"] = self._get_monster_deck_size(dm.monster)
                    monster_dict["cards_count"] = dm.monster.cards.count()
                    monster_dict["is_event_monster"] = False
                    result.append(monster_dict)
            if result:
                return result

        # Fallback: create monsters for this period if none exist
        self._create_period_monsters(genre, period_start)

        # Re-fetch
        period_monsters = (
            DailyMonster.query.filter_by(genre=genre, period_start=period_start)
            .order_by(DailyMonster.slot_number)
            .all()
        )

        for dm in period_monsters:
            if dm.monster and dm.monster.id not in defeated_ids:
                monster_dict = dm.monster.to_dict(lang)
                scaled = self._scale_monster_for_deck(dm.monster, deck_power)
                monster_dict.update(scaled)
                monster_dict["deck_size"] = self._get_monster_deck_size(dm.monster)
                monster_dict["cards_count"] = dm.monster.cards.count()
                monster_dict["is_event_monster"] = False
                result.append(monster_dict)

        return result

    def _generate_monster_image(self, monster: Monster, genre: str) -> str | None:
        """Generate monster image using Stability AI."""
        if not self.stability_api_key:
            logger.warning(
                "Stability API key not configured, skipping monster image generation"
            )
            return None

        try:
            # Get random character type for variety
            characters = MONSTER_CHARACTERS.get(genre, MONSTER_CHARACTERS["fantasy"])
            character_type = random.choice(characters)

            # Build prompt from genre
            art_style = MONSTER_ART_STYLES.get(genre, MONSTER_ART_STYLES["fantasy"])

            # Boss monsters get special treatment
            boss_modifier = ""
            if monster.is_boss:
                boss_modifier = (
                    "powerful boss enemy, epic scale, intimidating presence, "
                )

            prompt = (
                f"Art deco steampunk monster portrait, {boss_modifier}{character_type}, "
                f"{art_style}, "
                f"brass and copper machinery, geometric dark patterns, "
                f"vintage villain poster style, ornate evil design, highly detailed"
            )

            logger.info(
                f"Generating monster image for {monster.name}: {prompt[:80]}..."
            )

            response = requests.post(
                self.STABILITY_API_URL,
                headers={
                    "authorization": f"Bearer {self.stability_api_key}",
                    "accept": "image/*",
                },
                files={"none": ""},
                data={
                    "prompt": prompt,
                    "model": "sd3.5-large-turbo",
                    "output_format": "png",
                    "aspect_ratio": "1:1",
                },
                timeout=60,
            )

            if response.status_code == 200:
                filename = f"monster_{uuid.uuid4()}.png"
                filepath = self.images_dir / filename
                filepath.write_bytes(response.content)

                image_url = f"/media/monster_images/{filename}"
                logger.info(f"Monster image generated: {image_url}")
                return image_url
            else:
                error_text = (
                    response.text[:500] if response.text else "No response body"
                )
                logger.error(
                    f"Stability AI API error for monster: status={response.status_code}, "
                    f"response={error_text}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to generate monster image: {e}", exc_info=True)
            return None

    def _create_period_monsters(self, genre: str, period_start: date) -> None:
        """Create/reuse monsters with pre-generated decks for a weekly period.

        Creates 1 boss + 1-2 normal monsters per week.
        Reuses existing monsters from the database when possible,
        only generating new decks for each period.
        """
        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])
        monster_names = genre_info.get("monsters", ["Враг", "Монстр", "Босс"])

        emojis = ["👾", "👹", "🐉", "👻", "🤖"]
        # 1 boss + 2 normal monsters per week
        types = ["normal", "normal", "boss"]

        # Try to find existing monsters for this genre that we can reuse
        existing_monsters = (
            Monster.query.filter_by(genre=genre).order_by(Monster.id).all()
        )

        # Separate by type
        existing_normal = [m for m in existing_monsters if not m.is_boss]
        existing_bosses = [m for m in existing_monsters if m.is_boss]

        for i, name in enumerate(monster_names[:3]):
            monster_type = types[i] if i < len(types) else "normal"
            monster = None

            # Try to reuse existing monster
            if monster_type == "boss" and existing_bosses:
                # Reuse random boss
                monster = random.choice(existing_bosses)
                existing_bosses.remove(monster)
            elif monster_type != "boss" and existing_normal:
                # Reuse random normal monster
                monster = random.choice(existing_normal)
                existing_normal.remove(monster)

            if monster:
                # Reuse existing monster - regenerate its deck
                logger.info(
                    f"Reusing monster {monster.name} (id={monster.id}) for period {period_start}"
                )

                # Delete old deck cards
                MonsterCard.query.filter_by(monster_id=monster.id).delete()

                # Create new deck
                self._create_monster_deck(monster, genre)
            else:
                # Create new monster
                if monster_type == "boss":
                    base_stats = {
                        "level": 5,
                        "hp": 200,
                        "attack": 35,
                        "defense": 20,
                        "speed": 25,
                        "xp_reward": 100,
                        "stat_points_reward": 3,
                    }
                elif monster_type == "elite":
                    base_stats = {
                        "level": 3,
                        "hp": 120,
                        "attack": 25,
                        "defense": 15,
                        "speed": 20,
                        "xp_reward": 60,
                        "stat_points_reward": 2,
                    }
                else:
                    base_stats = {
                        "level": i + 1,
                        "hp": 50 + i * 15,
                        "attack": 12 + i * 4,
                        "defense": 6 + i * 3,
                        "speed": 12 + i * 3,
                        "xp_reward": 25 + i * 10,
                        "stat_points_reward": 1,
                    }

                monster = Monster(
                    name=name,  # No date suffix - reusable monster
                    genre=genre,
                    base_level=base_stats["level"],
                    base_hp=base_stats["hp"],
                    base_attack=base_stats["attack"],
                    base_defense=base_stats["defense"],
                    base_speed=base_stats["speed"],
                    base_xp_reward=base_stats["xp_reward"],
                    base_stat_points_reward=base_stats["stat_points_reward"],
                    level=base_stats["level"],
                    hp=base_stats["hp"],
                    attack=base_stats["attack"],
                    defense=base_stats["defense"],
                    speed=base_stats["speed"],
                    xp_reward=base_stats["xp_reward"],
                    stat_points_reward=base_stats["stat_points_reward"],
                    emoji=emojis[i % len(emojis)],
                    is_boss=monster_type == "boss",
                )
                db.session.add(monster)
                db.session.flush()  # Get monster ID

                # Generate image for new monster
                sprite_url = self._generate_monster_image(monster, genre)
                if sprite_url:
                    monster.sprite_url = sprite_url

                # Create pre-generated deck for this monster
                self._create_monster_deck(monster, genre)

                logger.info(f"Created new monster {monster.name} (id={monster.id})")

            # Link to period
            daily_monster = DailyMonster(
                monster_id=monster.id,
                genre=genre,
                period_start=period_start,
                slot_number=i + 1,
            )
            db.session.add(daily_monster)

        db.session.commit()

    def _create_monster_deck(self, monster: Monster, genre: str) -> None:
        """Create pre-generated deck of cards for a monster (stored in DB)."""
        templates = MONSTER_CARD_TEMPLATES.get(genre, MONSTER_CARD_TEMPLATES["fantasy"])
        deck_size = self._get_monster_deck_size(monster)

        # Select random cards for this monster's deck
        selected = random.sample(templates, min(deck_size, len(templates)))

        for template in selected:
            card = MonsterCard(
                monster_id=monster.id,
                name=template["name"],
                emoji=template["emoji"],
                hp=template["hp"],
                attack=template["attack"],
                rarity="common",
            )
            db.session.add(card)

    def _get_monster_deck_size(self, monster: Monster) -> int:
        """Get the number of cards in monster's deck."""
        if monster.is_boss:
            return 5
        return 3

    def _scale_monster_for_deck(self, monster: Monster, deck_power: int) -> dict:
        """Scale monster stats based on deck power."""
        if deck_power > 0:
            scale_factor = 1 + (deck_power / 500)
            scale_factor = min(scale_factor, 3.0)
        else:
            scale_factor = 0.5

        hp = int(monster.base_hp * scale_factor)
        attack = int(monster.base_attack * scale_factor)
        defense = int(monster.base_defense * scale_factor)
        xp_reward = int(monster.base_xp_reward * scale_factor)
        stat_points = monster.base_stat_points_reward

        if monster.is_boss:
            hp = int(hp * 1.5)
            attack = int(attack * 1.3)
            xp_reward = int(xp_reward * 2)
            stat_points = stat_points * 2

        return {
            "hp": hp,
            "attack": attack,
            "defense": defense,
            "xp_reward": xp_reward,
            "stat_points_reward": stat_points,
        }

    def get_active_battle(self, user_id: int) -> ActiveBattle | None:
        """Get user's active battle if any."""
        return ActiveBattle.query.filter_by(user_id=user_id, status="active").first()

    def start_battle(
        self,
        user_id: int,
        monster_id: int,
        card_ids: list[int],
        campaign_level_id: int | None = None,
    ) -> dict[str, Any]:
        """Start a new turn-based battle.

        Args:
            user_id: User ID
            monster_id: Monster ID
            card_ids: List of user card IDs to use in battle
            campaign_level_id: Optional campaign level ID (skips defeated check)
        """
        # Check for existing active battle
        existing = self.get_active_battle(user_id)
        if existing:
            lang = get_lang()
            return {"error": "battle_in_progress", "battle": existing.to_dict(lang)}

        monster = Monster.query.get(monster_id)
        if not monster:
            return {"error": "monster_not_found"}

        # Check if monster was already defeated in this period
        # Skip this check for campaign battles (levels can be replayed)
        if not campaign_level_id:
            period_start = DailyMonster.get_current_period_start()
            already_defeated = DefeatedMonster.query.filter_by(
                user_id=user_id, monster_id=monster_id, period_start=period_start
            ).first()
            if already_defeated:
                return {"error": "monster_already_defeated"}

        # Validate player cards
        cards = UserCard.query.filter(
            UserCard.id.in_(card_ids),
            UserCard.user_id == user_id,
            UserCard.is_destroyed.is_(False),
        ).all()

        # Filter out cards with no HP or on cooldown (silently skip them)
        cards = [c for c in cards if c.current_hp > 0 and not c.is_on_cooldown()]

        if not cards:
            return {"error": "no_valid_cards", "message": "Нет доступных карт для боя"}

        # Get deck power for scaling
        deck = self.get_user_deck(user_id)
        deck_power = sum(card.attack + card.hp for card in deck) if deck else 0
        scaled = self._scale_monster_for_deck(monster, deck_power)

        # Get monster's pre-generated deck from DB and scale it
        monster_cards = self._get_monster_battle_deck(monster, deck_power)

        if not monster_cards:
            # Fallback: generate on the fly if no cards in DB
            genre = monster.genre or self.get_user_genre(user_id)
            monster_cards = self._generate_monster_deck_fallback(
                monster, genre, deck_power
            )

        # Create player cards state
        player_cards = [
            {
                "id": c.id,
                "name": c.name,
                "emoji": c.emoji,
                "image_url": c.image_url,
                "hp": c.current_hp,
                "max_hp": c.hp,
                "attack": c.attack,
                "rarity": c.rarity,
                "genre": c.genre,
                "alive": True,
                "ability": c.ability,
                "ability_info": c.ability_info,
                "ability_cooldown": 0,  # Fresh cooldown at battle start
                "has_shield": False,  # Shield status
                "status_effects": [],  # Active status effects (poison, etc.)
            }
            for c in cards
        ]

        # Create battle state
        state = {
            "player_cards": player_cards,
            "monster_cards": monster_cards,
            "current_turn": "player",  # Player always goes first
            "battle_log": [],
            "damage_dealt": 0,
            "damage_taken": 0,
            "scaled_stats": scaled,
            "campaign_level_id": campaign_level_id,  # Track if this is campaign battle
        }

        battle = ActiveBattle(
            user_id=user_id,
            monster_id=monster_id,
            state=state,
            status="active",
            current_round=1,
        )
        db.session.add(battle)
        db.session.commit()

        lang = get_lang()
        return {
            "success": True,
            "battle": battle.to_dict(lang),
            "message": "Бой начался! Выбери карту для атаки.",
        }

    def _get_monster_battle_deck(self, monster: Monster, deck_power: int) -> list[dict]:
        """Get monster's pre-generated deck from DB with scaling."""
        db_cards = monster.cards.all()
        if not db_cards:
            return []

        # Scale factor based on deck power
        if deck_power > 0:
            scale = 0.8 + (deck_power / 600)
            scale = min(scale, 2.5)
        else:
            scale = 0.6

        # Boss gets stronger cards
        if monster.is_boss:
            scale *= 1.3

        cards = []
        for i, db_card in enumerate(db_cards):
            hp = int(db_card.hp * scale)
            attack = int(db_card.attack * scale)
            card = {
                "id": f"m_{monster.id}_{db_card.id}",
                "db_id": db_card.id,
                "name": db_card.name,
                "emoji": db_card.emoji,
                "hp": hp,
                "max_hp": hp,
                "attack": attack,
                "alive": True,
                "has_shield": False,
                "status_effects": [],
            }
            cards.append(card)

        return cards

    def _generate_monster_deck_fallback(
        self, monster: Monster, genre: str, deck_power: int
    ) -> list[dict]:
        """Fallback: generate monster deck on the fly if not in DB."""
        templates = MONSTER_CARD_TEMPLATES.get(genre, MONSTER_CARD_TEMPLATES["fantasy"])
        deck_size = self._get_monster_deck_size(monster)

        # Scale factor based on deck power
        if deck_power > 0:
            scale = 0.8 + (deck_power / 600)
            scale = min(scale, 2.5)
        else:
            scale = 0.6

        # Boss gets stronger cards
        if monster.is_boss:
            scale *= 1.3

        cards = []
        selected = random.sample(templates, min(deck_size, len(templates)))

        for i, template in enumerate(selected):
            card = {
                "id": f"m_{monster.id}_{i}",
                "name": template["name"],
                "emoji": template["emoji"],
                "hp": int(template["hp"] * scale),
                "max_hp": int(template["hp"] * scale),
                "attack": int(template["attack"] * scale),
                "alive": True,
                "has_shield": False,
                "status_effects": [],
            }
            cards.append(card)

        return cards

    def execute_turn(
        self,
        user_id: int,
        player_card_id: int,
        target_card_id: str,
        use_ability: bool = False,
    ) -> dict[str, Any]:
        """Execute a turn in the battle."""
        battle = self.get_active_battle(user_id)
        if not battle:
            return {"error": "no_active_battle"}

        state = battle.state.copy()

        if state["current_turn"] != "player":
            return {"error": "not_player_turn"}

        # Find player's card
        player_card = None
        for c in state["player_cards"]:
            if c["id"] == player_card_id and c["alive"]:
                player_card = c
                break

        if not player_card:
            return {"error": "invalid_player_card"}

        turn_log = []

        # Process poison damage at start of turn
        poison_log = self._process_poison_damage(state)
        turn_log.extend(poison_log)

        # Check if battle ended from poison
        alive_monster_cards = [c for c in state["monster_cards"] if c["alive"]]
        if not alive_monster_cards:
            state["battle_log"].extend(turn_log)
            battle.state = state
            return self._end_battle(battle, won=True, turn_log=turn_log)

        # Use ability or attack
        if use_ability:
            ability_result = self._execute_ability(
                state, player_card, target_card_id, turn_log
            )
            if "error" in ability_result:
                return ability_result
            # Track ability usage for quests
            try:
                from app.services.quest_service import QuestService

                QuestService().check_ability_used_quests(battle.user_id)
            except Exception:
                pass
        else:
            # Find target monster card for attack
            monster_card = None
            for c in state["monster_cards"]:
                if c["id"] == target_card_id and c["alive"]:
                    monster_card = c
                    break

            if not monster_card:
                return {"error": "invalid_monster_card"}

            # Player attacks monster card
            damage = self._calculate_damage(player_card["attack"], is_critical=False)
            is_critical = random.random() < 0.15
            if is_critical:
                damage = int(damage * 1.5)

            # Check if target has shield
            if monster_card.get("has_shield"):
                monster_card["has_shield"] = False
                turn_log.append(
                    {
                        "actor": "system",
                        "action": "shield_blocked",
                        "message": f"Щит {monster_card['name']} поглотил удар!",
                    }
                )
                damage = 0
            else:
                monster_card["hp"] -= damage
                state["damage_dealt"] = state.get("damage_dealt", 0) + damage

            turn_log.append(
                {
                    "actor": "player",
                    "card_id": player_card["id"],
                    "card_name": player_card["name"],
                    "card_emoji": player_card["emoji"],
                    "action": "critical" if is_critical else "attack",
                    "damage": damage,
                    "target_id": monster_card["id"],
                    "target_name": monster_card["name"],
                    "target_emoji": monster_card.get("emoji", "👾"),
                    "is_critical": is_critical,
                }
            )

        # Check if monster card died (only if we attacked, not used ability)
        if not use_ability and monster_card["hp"] <= 0:
            monster_card["alive"] = False
            monster_card["hp"] = 0
            turn_log.append(
                {
                    "actor": "system",
                    "action": "card_destroyed",
                    "card_name": monster_card["name"],
                    "message": f"{monster_card['name']} побеждена!",
                }
            )

        # Check if all monster cards are dead
        alive_monster_cards = [c for c in state["monster_cards"] if c["alive"]]
        if not alive_monster_cards:
            # Player wins!
            state["battle_log"].extend(turn_log)
            battle.state = state
            return self._end_battle(battle, won=True, turn_log=turn_log)

        # Monster's turn - attack a random alive player card
        alive_player_cards = [c for c in state["player_cards"] if c["alive"]]
        if alive_player_cards:
            # Monster chooses random alive card to attack with
            attacking_monster_card = random.choice(alive_monster_cards)
            target_player_card = random.choice(alive_player_cards)

            monster_damage = self._calculate_damage(
                attacking_monster_card["attack"], is_critical=False
            )
            monster_crit = random.random() < 0.1
            if monster_crit:
                monster_damage = int(monster_damage * 1.5)

            # Check if target has shield
            if target_player_card.get("has_shield"):
                target_player_card["has_shield"] = False
                turn_log.append(
                    {
                        "actor": "system",
                        "action": "shield_blocked",
                        "message": f"Щит {target_player_card['name']} поглотил удар!",
                    }
                )
                monster_damage = 0
            else:
                target_player_card["hp"] -= monster_damage
                state["damage_taken"] = state.get("damage_taken", 0) + monster_damage

            turn_log.append(
                {
                    "actor": "monster",
                    "card_id": attacking_monster_card["id"],
                    "card_name": attacking_monster_card["name"],
                    "card_emoji": attacking_monster_card.get("emoji", "👾"),
                    "action": "critical" if monster_crit else "attack",
                    "damage": monster_damage,
                    "target_id": target_player_card["id"],
                    "target_name": target_player_card["name"],
                    "target_emoji": target_player_card.get("emoji", "🃏"),
                    "is_critical": monster_crit,
                }
            )

            # Check if player card died
            if target_player_card["hp"] <= 0:
                target_player_card["alive"] = False
                target_player_card["hp"] = 0
                turn_log.append(
                    {
                        "actor": "system",
                        "action": "card_destroyed",
                        "card_name": target_player_card["name"],
                        "message": f"{target_player_card['name']} уничтожена!",
                    }
                )

        # Check if all player cards are dead
        alive_player_cards = [c for c in state["player_cards"] if c["alive"]]
        if not alive_player_cards:
            # Player loses!
            state["battle_log"].extend(turn_log)
            battle.state = state
            return self._end_battle(battle, won=False, turn_log=turn_log)

        # Decrease cooldowns at end of turn
        for card in state["player_cards"]:
            if card.get("ability_cooldown", 0) > 0:
                card["ability_cooldown"] -= 1

        # Continue battle
        state["current_turn"] = "player"
        state["battle_log"].extend(turn_log)
        battle.current_round += 1
        battle.state = state
        db.session.commit()

        lang = get_lang()
        return {
            "success": True,
            "battle": battle.to_dict(lang),
            "turn_log": turn_log,
            "status": "continue",
        }

    def _calculate_damage(self, attack: int, is_critical: bool = False) -> int:
        """Calculate damage with variance."""
        variance = random.uniform(0.85, 1.15)
        damage = int(attack * variance)
        if is_critical:
            damage = int(damage * 1.5)
        return max(1, damage)

    def _execute_ability(
        self, state: dict, player_card: dict, target_id: str, turn_log: list
    ) -> dict:
        """Execute a card's ability."""
        from app.models.card import ABILITY_CONFIG, CardAbility

        ability = player_card.get("ability")
        if not ability:
            return {"error": "no_ability"}

        cooldown = player_card.get("ability_cooldown", 0)
        if cooldown > 0:
            return {"error": "ability_on_cooldown", "cooldown": cooldown}

        try:
            ability_enum = CardAbility(ability)
            config = ABILITY_CONFIG.get(ability_enum, {})
        except ValueError:
            return {"error": "invalid_ability"}

        ability_name = config.get("name", ability)
        ability_emoji = config.get("emoji", "✨")
        ability_cooldown = config.get("cooldown", 3)

        if ability == "heal":
            # Find target ally card
            target_card = None
            for c in state["player_cards"]:
                if c["id"] == int(target_id) and c["alive"]:
                    target_card = c
                    break
            if not target_card:
                return {"error": "invalid_target"}

            # Heal 30% of max HP
            heal_amount = int(target_card["max_hp"] * config.get("effect_value", 0.3))
            old_hp = target_card["hp"]
            target_card["hp"] = min(
                target_card["max_hp"], target_card["hp"] + heal_amount
            )
            actual_heal = target_card["hp"] - old_hp

            turn_log.append(
                {
                    "actor": "player",
                    "card_name": player_card["name"],
                    "action": "ability",
                    "ability": ability,
                    "ability_name": ability_name,
                    "ability_emoji": ability_emoji,
                    "heal_amount": actual_heal,
                    "target_name": target_card["name"],
                    "message": f"{player_card['name']} исцеляет "
                    f"{target_card['name']} на {actual_heal} HP!",
                }
            )

        elif ability == "double_strike":
            # Find target enemy card
            target_card = None
            for c in state["monster_cards"]:
                if c["id"] == target_id and c["alive"]:
                    target_card = c
                    break
            if not target_card:
                return {"error": "invalid_target"}

            # Two attacks at 60% damage each
            effect_value = config.get("effect_value", 0.6)
            damage1 = int(self._calculate_damage(player_card["attack"]) * effect_value)
            damage2 = int(self._calculate_damage(player_card["attack"]) * effect_value)

            # First strike
            if target_card.get("has_shield"):
                target_card["has_shield"] = False
                damage1 = 0
            else:
                target_card["hp"] -= damage1

            # Check if first hit killed the target — retarget if needed
            second_target = target_card
            if target_card["hp"] <= 0:
                target_card["alive"] = False
                target_card["hp"] = 0
                turn_log.append(
                    {
                        "actor": "system",
                        "action": "card_destroyed",
                        "card_name": target_card["name"],
                        "message": f"{target_card['name']} побеждена!",
                    }
                )
                # Find next alive enemy for second strike
                new_target = None
                for c in state["monster_cards"]:
                    if c["alive"] and c["id"] != target_card["id"]:
                        new_target = c
                        break
                if new_target:
                    second_target = new_target
                else:
                    damage2 = 0  # No more targets

            # Second strike (can't be blocked by shield)
            if damage2 > 0:
                second_target["hp"] -= damage2

            total_damage = damage1 + damage2
            state["damage_dealt"] = state.get("damage_dealt", 0) + total_damage

            turn_log.append(
                {
                    "actor": "player",
                    "card_id": player_card["id"],
                    "card_name": player_card["name"],
                    "action": "ability",
                    "ability": ability,
                    "ability_name": ability_name,
                    "ability_emoji": ability_emoji,
                    "damage": total_damage,
                    "damage1": damage1,
                    "damage2": damage2,
                    "target_id": second_target["id"],
                    "target_name": second_target["name"],
                    "message": f"{player_card['name']} наносит двойной удар: "
                    f"{damage1} + {damage2} урона!",
                }
            )

            # Check if second target died
            if second_target["hp"] <= 0:
                second_target["alive"] = False
                second_target["hp"] = 0
                if second_target["id"] != target_card["id"]:
                    turn_log.append(
                        {
                            "actor": "system",
                            "action": "card_destroyed",
                            "card_name": second_target["name"],
                            "message": f"{second_target['name']} побеждена!",
                        }
                    )

        elif ability == "shield":
            # Find target ally card (can be self or another ally)
            target_card = None
            for c in state["player_cards"]:
                if c["id"] == int(target_id) and c["alive"]:
                    target_card = c
                    break
            if not target_card:
                return {"error": "invalid_target"}

            # Apply shield to target ally
            target_card["has_shield"] = True

            if target_card["id"] == player_card["id"]:
                message = f"{player_card['name']} активирует щит!"
            else:
                message = (
                    f"{player_card['name']} накладывает щит на {target_card['name']}!"
                )

            turn_log.append(
                {
                    "actor": "player",
                    "card_id": player_card["id"],
                    "card_name": player_card["name"],
                    "action": "ability",
                    "ability": ability,
                    "ability_name": ability_name,
                    "ability_emoji": ability_emoji,
                    "target_id": target_card["id"],
                    "target_name": target_card["name"],
                    "message": message,
                }
            )

        elif ability == "poison":
            # Find target enemy card
            target_card = None
            for c in state["monster_cards"]:
                if c["id"] == target_id and c["alive"]:
                    target_card = c
                    break
            if not target_card:
                return {"error": "invalid_target"}

            # Apply poison effect
            duration = config.get("duration", 3)
            poison_damage = int(target_card["max_hp"] * config.get("effect_value", 0.1))

            # Initialize status_effects if not present
            if "status_effects" not in target_card:
                target_card["status_effects"] = []

            target_card["status_effects"].append(
                {
                    "type": "poison",
                    "damage": poison_damage,
                    "turns_left": duration,
                    "source": player_card["name"],
                }
            )

            turn_log.append(
                {
                    "actor": "player",
                    "card_name": player_card["name"],
                    "action": "ability",
                    "ability": ability,
                    "ability_name": ability_name,
                    "ability_emoji": ability_emoji,
                    "target_name": target_card["name"],
                    "message": f"{player_card['name']} отравляет "
                    f"{target_card['name']}! ({poison_damage} урона/{duration} ходов)",
                }
            )

        # Set cooldown
        player_card["ability_cooldown"] = ability_cooldown

        return {"success": True}

    def _process_poison_damage(self, state: dict) -> list:
        """Process poison damage on all affected cards at start of turn."""
        turn_log = []

        # Process poison on monster cards
        for card in state["monster_cards"]:
            if not card.get("alive"):
                continue
            if "status_effects" not in card:
                continue

            new_effects = []
            for effect in card["status_effects"]:
                if effect["type"] == "poison" and effect["turns_left"] > 0:
                    damage = effect["damage"]
                    card["hp"] -= damage
                    effect["turns_left"] -= 1
                    state["damage_dealt"] = state.get("damage_dealt", 0) + damage

                    turn_log.append(
                        {
                            "actor": "system",
                            "action": "poison_damage",
                            "damage": damage,
                            "target_name": card["name"],
                            "message": f"☠️ Яд наносит {damage} урона {card['name']}!",
                        }
                    )

                    # Check if card died from poison
                    if card["hp"] <= 0:
                        card["alive"] = False
                        card["hp"] = 0
                        turn_log.append(
                            {
                                "actor": "system",
                                "action": "card_destroyed",
                                "card_name": card["name"],
                                "message": f"{card['name']} погибла от яда!",
                            }
                        )

                    # Keep effect if turns remain
                    if effect["turns_left"] > 0:
                        new_effects.append(effect)

            card["status_effects"] = new_effects

        return turn_log

    def _get_monster_type(self, monster: Monster) -> str:
        """Determine monster type: normal, elite, or boss."""
        if monster.is_boss:
            return "boss"
        # Elite monsters have higher base stats
        if monster.base_hp >= 100 or monster.base_attack >= 20:
            return "elite"
        return "normal"

    def _roll_rarity_from_weights(self, weights: dict) -> CardRarity:
        """Roll a rarity based on weight distribution."""
        total = sum(weights.values())
        if total == 0:
            return CardRarity.COMMON

        roll = random.random() * total
        cumulative = 0
        for rarity, weight in weights.items():
            cumulative += weight
            if roll <= cumulative:
                return rarity
        return CardRarity.COMMON

    def _generate_reward_card(
        self, user_id: int, monster: Monster, monster_type: str
    ) -> UserCard | None:
        """Generate a reward card based on monster type."""
        from app.services.card_service import CardService

        config = MONSTER_REWARD_CONFIG.get(
            monster_type, MONSTER_REWARD_CONFIG["normal"]
        )

        # Check if we should generate a card
        if random.random() > config["card_chance"]:
            return None

        # Roll rarity based on weights
        rarity = self._roll_rarity_from_weights(config["rarity_weights"])

        # Generate card using CardService
        card_service = CardService()
        card = card_service.generate_card_for_task(
            user_id=user_id,
            task_id=None,
            task_title=f"Победа над {monster.name}",
            difficulty=monster_type,
            forced_rarity=rarity,
        )

        return card

    def _end_battle(
        self, battle: ActiveBattle, won: bool, turn_log: list
    ) -> dict[str, Any]:
        """End the battle and process rewards."""
        state = battle.state
        user = User.query.get(battle.user_id)

        # Update battle status
        battle.status = "won" if won else "lost"

        # Calculate rewards
        xp_earned = 0
        stat_points_earned = 0
        level_up = False
        new_card = None
        cards_lost = []

        if won:
            scaled = state.get("scaled_stats", {})
            xp_earned = scaled.get("xp_reward", 50)
            stat_points_earned = scaled.get("stat_points_reward", 1)

            # Bonus for no cards lost
            lost_cards = [c for c in state["player_cards"] if not c["alive"]]
            if not lost_cards:
                xp_earned = int(xp_earned * 1.5)

            if user:
                xp_info = user.add_xp(xp_earned)
                level_up = xp_info.get("level_up", False)

            # Mark monster as defeated for this period (skip for campaign battles)
            campaign_level_id = state.get("campaign_level_id")
            if not campaign_level_id:
                period_start = DailyMonster.get_current_period_start()
                # Check if already defeated to avoid unique constraint violation
                existing = DefeatedMonster.query.filter_by(
                    user_id=battle.user_id,
                    monster_id=battle.monster_id,
                    period_start=period_start,
                ).first()
                if not existing:
                    defeated = DefeatedMonster(
                        user_id=battle.user_id,
                        monster_id=battle.monster_id,
                        period_start=period_start,
                    )
                    db.session.add(defeated)

            # Generate reward card based on monster type
            monster = battle.monster
            if monster:
                monster_type = self._get_monster_type(monster)
                reward_card = self._generate_reward_card(
                    user_id=battle.user_id,
                    monster=monster,
                    monster_type=monster_type,
                )
                if reward_card:
                    lang = get_lang()
                    new_card = reward_card.to_dict(lang)

        # Update actual player cards in database
        for card_state in state["player_cards"]:
            card = UserCard.query.get(card_state["id"])
            if card:
                card.current_hp = max(0, card_state["hp"])
                if not card_state["alive"]:
                    # Put card on cooldown instead of destroying it
                    card.start_cooldown(hours=1)
                    cards_lost.append(card_state["id"])

        # Check quests for battle win
        if won:
            try:
                from app.services.quest_service import QuestService

                quest_service = QuestService()
                quest_service.check_battle_win_quests(battle.user_id)
                # Check card rarity quest if a new card was earned
                if new_card and new_card.get("rarity"):
                    quest_service.check_card_received_quests(
                        battle.user_id, new_card["rarity"]
                    )
            except Exception:
                pass  # Don't fail battle on quest errors

        # Log battle
        battle_record = BattleLog(
            user_id=battle.user_id,
            monster_id=battle.monster_id,
            won=won,
            rounds=battle.current_round,
            damage_dealt=state.get("damage_dealt", 0),
            damage_taken=state.get("damage_taken", 0),
            xp_earned=xp_earned,
            stat_points_earned=stat_points_earned,
        )
        db.session.add(battle_record)
        db.session.commit()

        lang = get_lang()
        return {
            "success": True,
            "status": "won" if won else "lost",
            "battle": battle.to_dict(lang),
            "turn_log": turn_log,
            "campaign_level_id": state.get("campaign_level_id"),
            "result": {
                "won": won,
                "rounds": battle.current_round,
                "damage_dealt": state.get("damage_dealt", 0),
                "damage_taken": state.get("damage_taken", 0),
                "xp_earned": xp_earned,
                "stat_points_earned": stat_points_earned,
                "level_up": level_up,
                "cards_lost": cards_lost,
                "reward_card": new_card,
            },
        }

    def forfeit_battle(self, user_id: int) -> dict[str, Any]:
        """Forfeit the current battle. All cards go to knockout and need healing."""
        battle = self.get_active_battle(user_id)
        if not battle:
            return {"error": "no_active_battle"}

        # Mark all player cards as dead (knockout) - they will need healing
        state = battle.state
        for card in state["player_cards"]:
            card["hp"] = 0
            card["alive"] = False
        battle.state = state

        return self._end_battle(battle, won=False, turn_log=[])

    def heal_all_cards(self, user_id: int) -> int:
        """Heal all user's cards to full HP."""
        cards = UserCard.query.filter_by(user_id=user_id, is_destroyed=False).all()
        healed = 0

        for card in cards:
            if card.current_hp < card.hp:
                card.heal()
                healed += 1

        db.session.commit()
        return healed

    def get_battle_history(self, user_id: int, limit: int = 10) -> list[BattleLog]:
        """Get recent battle history."""
        return (
            BattleLog.query.filter_by(user_id=user_id)
            .order_by(BattleLog.created_at.desc())
            .limit(limit)
            .all()
        )

    # Keep old method for backwards compatibility but redirect to new system
    def execute_card_battle(
        self,
        user_id: int,
        monster_id: int,
        card_ids: list[int],
        scaled_stats: dict | None = None,
    ) -> dict[str, Any]:
        """Legacy method - redirects to start_battle for new turn-based system."""
        return self.start_battle(user_id, monster_id, card_ids)

    def validate_battle_cards(
        self, user_id: int, card_ids: list[int], monster: Monster
    ) -> dict:
        """Validate that selected cards can be used for battle."""
        if not card_ids:
            return {"valid": False, "error": "no_cards", "message": "Выберите карты"}

        cards = UserCard.query.filter(
            UserCard.id.in_(card_ids),
            UserCard.user_id == user_id,
            UserCard.is_destroyed.is_(False),
        ).all()

        if len(cards) != len(card_ids):
            return {
                "valid": False,
                "error": "invalid_cards",
                "message": "Некоторые карты недоступны",
            }

        # Check if cards have HP
        low_hp_cards = [c for c in cards if c.current_hp <= 0]
        if low_hp_cards:
            return {
                "valid": False,
                "error": "cards_no_hp",
                "message": "Некоторые карты без здоровья",
            }

        return {"valid": True, "cards": cards}
