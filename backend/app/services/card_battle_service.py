"""Card-based turn-by-turn battle arena service."""

import random
from datetime import date
from typing import Any

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
from app.models.card import UserCard
from app.models.character import GENRE_THEMES
from app.models.user_profile import UserProfile

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


class CardBattleService:
    """Service for managing turn-based card battles."""

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
        """Get monsters available for battle (excluding defeated ones)."""
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

        # Try to get period monsters first
        period_monsters = (
            DailyMonster.query.filter_by(genre=genre, period_start=period_start)
            .order_by(DailyMonster.slot_number)
            .all()
        )

        if period_monsters:
            result = []
            for dm in period_monsters:
                if dm.monster and dm.monster.id not in defeated_ids:
                    monster_dict = dm.monster.to_dict()
                    scaled = self._scale_monster_for_deck(dm.monster, deck_power)
                    monster_dict.update(scaled)
                    monster_dict["deck_size"] = self._get_monster_deck_size(dm.monster)
                    # Include pre-generated cards count
                    monster_dict["cards_count"] = dm.monster.cards.count()
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

        result = []
        for dm in period_monsters:
            if dm.monster and dm.monster.id not in defeated_ids:
                monster_dict = dm.monster.to_dict()
                scaled = self._scale_monster_for_deck(dm.monster, deck_power)
                monster_dict.update(scaled)
                monster_dict["deck_size"] = self._get_monster_deck_size(dm.monster)
                monster_dict["cards_count"] = dm.monster.cards.count()
                result.append(monster_dict)

        return result

    def _create_period_monsters(self, genre: str, period_start: date) -> None:
        """Create monsters with pre-generated decks for a 3-day period."""
        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])
        monster_names = genre_info.get("monsters", ["Враг", "Монстр", "Босс"])

        emojis = ["👾", "👹", "🐉", "👻", "🤖"]
        types = ["normal", "normal", "normal", "elite", "boss"]

        for i, name in enumerate(monster_names[:5]):
            monster_type = types[i] if i < len(types) else "normal"

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
                name=f"{name} ({period_start.strftime('%d.%m')})",
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

            # Create pre-generated deck for this monster
            self._create_monster_deck(monster, genre)

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
        self, user_id: int, monster_id: int, card_ids: list[int]
    ) -> dict[str, Any]:
        """Start a new turn-based battle."""
        # Check for existing active battle
        existing = self.get_active_battle(user_id)
        if existing:
            return {"error": "battle_in_progress", "battle": existing.to_dict()}

        monster = Monster.query.get(monster_id)
        if not monster:
            return {"error": "monster_not_found"}

        # Check if monster was already defeated in this period
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

        if not cards:
            return {"error": "no_valid_cards"}

        # Check cards have HP
        low_hp_cards = [c for c in cards if c.current_hp <= 0]
        if low_hp_cards:
            return {"error": "cards_no_hp", "message": "Некоторые карты без здоровья"}

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

        return {
            "success": True,
            "battle": battle.to_dict(),
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
            }
            cards.append(card)

        return cards

    def execute_turn(
        self, user_id: int, player_card_id: int, target_monster_card_id: str
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

        # Find target monster card
        monster_card = None
        for c in state["monster_cards"]:
            if c["id"] == target_monster_card_id and c["alive"]:
                monster_card = c
                break

        if not monster_card:
            return {"error": "invalid_monster_card"}

        turn_log = []

        # Player attacks monster card
        damage = self._calculate_damage(player_card["attack"], is_critical=False)
        is_critical = random.random() < 0.15
        if is_critical:
            damage = int(damage * 1.5)

        monster_card["hp"] -= damage
        state["damage_dealt"] = state.get("damage_dealt", 0) + damage

        turn_log.append(
            {
                "actor": "player",
                "card_name": player_card["name"],
                "card_emoji": player_card["emoji"],
                "action": "critical" if is_critical else "attack",
                "damage": damage,
                "target_name": monster_card["name"],
                "target_emoji": monster_card["emoji"],
                "is_critical": is_critical,
            }
        )

        # Check if monster card died
        if monster_card["hp"] <= 0:
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

            target_player_card["hp"] -= monster_damage
            state["damage_taken"] = state.get("damage_taken", 0) + monster_damage

            turn_log.append(
                {
                    "actor": "monster",
                    "card_name": attacking_monster_card["name"],
                    "card_emoji": attacking_monster_card["emoji"],
                    "action": "critical" if monster_crit else "attack",
                    "damage": monster_damage,
                    "target_name": target_player_card["name"],
                    "target_emoji": target_player_card["emoji"],
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

        # Continue battle
        state["current_turn"] = "player"
        state["battle_log"].extend(turn_log)
        battle.current_round += 1
        battle.state = state
        db.session.commit()

        return {
            "success": True,
            "battle": battle.to_dict(),
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

            # Mark monster as defeated for this period
            period_start = DailyMonster.get_current_period_start()
            defeated = DefeatedMonster(
                user_id=battle.user_id,
                monster_id=battle.monster_id,
                period_start=period_start,
            )
            db.session.add(defeated)

            # Generate reward card for boss kills
            monster = battle.monster
            if monster and monster.is_boss:
                from app.services.card_service import CardService

                card_service = CardService()
                new_card = card_service.generate_card_for_task(
                    user_id=battle.user_id,
                    task_id=None,
                    task_title=f"Победа над {monster.name}",
                    difficulty="very_hard",
                )
                if new_card:
                    new_card = new_card.to_dict()

        # Update actual player cards in database
        for card_state in state["player_cards"]:
            card = UserCard.query.get(card_state["id"])
            if card:
                card.current_hp = max(0, card_state["hp"])
                if not card_state["alive"]:
                    card.is_destroyed = True
                    card.is_in_deck = False
                    cards_lost.append(card_state["id"])

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

        return {
            "success": True,
            "status": "won" if won else "lost",
            "battle": battle.to_dict(),
            "turn_log": turn_log,
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
        """Forfeit the current battle."""
        battle = self.get_active_battle(user_id)
        if not battle:
            return {"error": "no_active_battle"}

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
