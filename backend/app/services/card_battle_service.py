"""Card-based battle arena service."""

import random
from datetime import date
from typing import Any

from app import db
from app.models import BattleLog, DailyMonster, Monster, User
from app.models.card import UserCard
from app.models.character import GENRE_THEMES
from app.models.user_profile import UserProfile


class CardBattleService:
    """Service for managing card-based battles in the arena."""

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
        """
        Get monsters available for battle based on user's genre and deck power.
        """
        genre = self.get_user_genre(user_id)

        # Get user deck to calculate power level
        deck = self.get_user_deck(user_id)
        deck_power = sum(card.attack + card.hp for card in deck) if deck else 0

        # Try to get today's daily monsters first
        today = date.today()
        daily_monsters = (
            DailyMonster.query.filter_by(genre=genre, date=today)
            .order_by(DailyMonster.slot_number)
            .all()
        )

        if daily_monsters:
            result = []
            for dm in daily_monsters:
                if dm.monster:
                    monster_dict = dm.monster.to_dict()
                    # Scale monster based on deck power
                    scaled = self._scale_monster_for_deck(dm.monster, deck_power)
                    monster_dict.update(scaled)
                    # Add required card count based on monster type
                    monster_dict["required_cards"] = self._get_required_cards(
                        dm.monster
                    )
                    result.append(monster_dict)
            if result:
                return result

        # Fallback to regular monsters
        monsters = Monster.query.filter_by(genre=genre).all()

        if not monsters:
            monsters = self._create_default_monsters(genre)

        result = []
        for monster in monsters[:6]:
            monster_dict = monster.to_dict()
            scaled = self._scale_monster_for_deck(monster, deck_power)
            monster_dict.update(scaled)
            monster_dict["required_cards"] = self._get_required_cards(monster)
            result.append(monster_dict)

        return result

    def _scale_monster_for_deck(self, monster: Monster, deck_power: int) -> dict:
        """Scale monster stats based on deck power."""
        # Base scaling factor - increases difficulty as deck gets stronger
        if deck_power > 0:
            scale_factor = 1 + (deck_power / 500)  # Every 500 power = +100% stats
            scale_factor = min(scale_factor, 3.0)  # Cap at 3x
        else:
            scale_factor = 0.5  # Easier for empty decks

        # Apply scaling to monster base stats
        hp = int(monster.base_hp * scale_factor)
        attack = int(monster.base_attack * scale_factor)
        defense = int(monster.base_defense * scale_factor)
        xp_reward = int(monster.base_xp_reward * scale_factor)
        stat_points = monster.base_stat_points_reward

        # Boss monsters get extra scaling
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

    def _get_required_cards(self, monster: Monster) -> dict:
        """Get required cards for battle based on monster type."""
        if monster.is_boss:
            return {
                "min_cards": 3,
                "max_cards": 5,
                "min_genres": 2,  # Boss requires cards from at least 2 different genres
                "same_genre_bonus": True,
                "description": "Босс требует минимум 3 карты из 2+ жанров",
            }
        else:
            return {
                "min_cards": 1,
                "max_cards": 5,
                "min_genres": 1,
                "same_genre_bonus": True,
                "description": "Выберите карты для боя",
            }

    def _create_default_monsters(self, genre: str) -> list[Monster]:
        """Create default monsters for a genre."""
        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])
        monster_names = genre_info.get("monsters", ["Враг", "Монстр", "Босс"])

        monsters = []
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
                name=name,
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
            monsters.append(monster)

        db.session.commit()
        return monsters

    def validate_battle_cards(
        self, user_id: int, card_ids: list[int], monster: Monster
    ) -> dict:
        """Validate that selected cards can be used for battle."""
        if not card_ids:
            return {"valid": False, "error": "no_cards", "message": "Выберите карты"}

        # Get user's cards
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

        # Check minimum card requirement
        required = self._get_required_cards(monster)
        if len(cards) < required["min_cards"]:
            return {
                "valid": False,
                "error": "not_enough_cards",
                "message": f"Нужно минимум {required['min_cards']} карт",
            }

        # Check if cards have HP
        low_hp_cards = [c for c in cards if c.current_hp <= 0]
        if low_hp_cards:
            return {
                "valid": False,
                "error": "cards_no_hp",
                "message": "Некоторые карты без здоровья",
            }

        # Check genre diversity for bosses
        min_genres = required.get("min_genres", 1)
        if min_genres > 1:
            unique_genres = set(c.genre for c in cards)
            if len(unique_genres) < min_genres:
                return {
                    "valid": False,
                    "error": "not_enough_genres",
                    "message": f"Для босса нужны карты из {min_genres}+ жанров",
                }

        return {"valid": True, "cards": cards}

    def execute_card_battle(
        self,
        user_id: int,
        monster_id: int,
        card_ids: list[int],
        scaled_stats: dict | None = None,
    ) -> dict[str, Any]:
        """
        Execute a card-based battle.

        Cards take turns attacking the monster.
        Monster attacks random cards.
        Cards with 0 HP are destroyed at end of battle.
        """
        monster = Monster.query.get(monster_id)
        if not monster:
            return {"error": "monster_not_found", "message": "Монстр не найден"}

        # Validate cards
        validation = self.validate_battle_cards(user_id, card_ids, monster)
        if not validation["valid"]:
            return validation

        cards = validation["cards"]
        user = User.query.get(user_id)

        # Get or calculate monster stats
        if scaled_stats:
            m_hp = scaled_stats.get("hp", monster.hp)
            m_attack = scaled_stats.get("attack", monster.attack)
            m_defense = scaled_stats.get("defense", monster.defense)
            m_xp_reward = scaled_stats.get("xp_reward", monster.xp_reward)
            m_stat_points = scaled_stats.get(
                "stat_points_reward", monster.stat_points_reward
            )
        else:
            deck = self.get_user_deck(user_id)
            deck_power = sum(card.attack + card.hp for card in deck) if deck else 0
            scaled = self._scale_monster_for_deck(monster, deck_power)
            m_hp = scaled["hp"]
            m_attack = scaled["attack"]
            m_defense = scaled["defense"]
            m_xp_reward = scaled["xp_reward"]
            m_stat_points = scaled["stat_points_reward"]

        # Battle simulation
        monster_hp = m_hp
        rounds = 0
        damage_dealt = 0
        damage_taken = 0
        battle_log = []
        cards_lost = []

        # Track card states
        card_states = {
            card.id: {
                "card": card,
                "hp": card.current_hp,
                "max_hp": card.hp,
                "alive": True,
            }
            for card in cards
        }

        # Calculate genre bonus
        user_genre = self.get_user_genre(user_id)
        genre_bonus_cards = [c for c in cards if c.genre == user_genre]
        has_genre_bonus = len(genre_bonus_cards) >= len(cards) // 2

        while monster_hp > 0 and any(s["alive"] for s in card_states.values()):
            rounds += 1
            if rounds > 20:  # Max rounds safety
                break

            # Each alive card attacks
            alive_cards = [s for s in card_states.values() if s["alive"]]

            for card_state in alive_cards:
                card = card_state["card"]

                # Calculate card attack
                base_attack = card.attack
                is_critical = False
                attack_type = "attack"
                message = ""

                # Critical hit chance (10%)
                if random.random() < 0.1:
                    is_critical = True
                    base_attack = int(base_attack * 1.8)
                    attack_type = "critical"
                    message = "Критический удар!"

                # Genre bonus (same genre as user preference = +20% damage)
                if card.genre == user_genre:
                    base_attack = int(base_attack * 1.2)
                    if not message:
                        message = "Бонус жанра!"

                # Calculate damage with defense
                card_damage = max(1, base_attack - m_defense // 3)
                variance = random.uniform(0.9, 1.1)
                card_damage = int(card_damage * variance)

                monster_hp -= card_damage
                damage_dealt += card_damage

                battle_log.append(
                    {
                        "round": rounds,
                        "actor": "card",
                        "card_id": card.id,
                        "card_name": card.name,
                        "card_emoji": card.emoji,
                        "action": attack_type,
                        "damage": card_damage,
                        "is_critical": is_critical,
                        "message": message,
                        "target": "monster",
                    }
                )

                if monster_hp <= 0:
                    break

            if monster_hp <= 0:
                break

            # Monster attacks random cards
            alive_cards = [s for s in card_states.values() if s["alive"]]
            if not alive_cards:
                break

            # Number of attacks (bosses attack more)
            num_attacks = 2 if monster.is_boss else 1

            for _ in range(num_attacks):
                if not alive_cards:
                    break

                target_state = random.choice(alive_cards)
                target_card = target_state["card"]

                # Calculate monster damage
                monster_damage = m_attack
                is_critical = False
                attack_type = "attack"
                message = ""

                # Boss special attack (25% chance)
                if monster.is_boss and random.random() < 0.25:
                    monster_damage = int(monster_damage * 1.5)
                    attack_type = "special"
                    message = "Мощный удар!"

                # Critical (10% chance)
                if random.random() < 0.1:
                    is_critical = True
                    monster_damage = int(monster_damage * 1.5)
                    attack_type = "critical"
                    message = "Критический удар!" if not message else f"{message} Крит!"

                # Apply damage to card
                variance = random.uniform(0.85, 1.15)
                monster_damage = int(monster_damage * variance)

                target_state["hp"] -= monster_damage
                damage_taken += monster_damage

                battle_log.append(
                    {
                        "round": rounds,
                        "actor": "monster",
                        "action": attack_type,
                        "damage": monster_damage,
                        "is_critical": is_critical,
                        "message": message,
                        "target_card_id": target_card.id,
                        "target_card_name": target_card.name,
                    }
                )

                # Check if card died
                if target_state["hp"] <= 0:
                    target_state["alive"] = False
                    cards_lost.append(target_card.id)
                    battle_log.append(
                        {
                            "round": rounds,
                            "actor": "system",
                            "action": "card_destroyed",
                            "card_id": target_card.id,
                            "card_name": target_card.name,
                            "message": f"{target_card.name} уничтожена!",
                        }
                    )
                    alive_cards = [s for s in card_states.values() if s["alive"]]

        # Determine winner
        won = monster_hp <= 0

        # Update card states in database
        for card_state in card_states.values():
            card = card_state["card"]
            card.current_hp = max(0, card_state["hp"])

            # Destroy cards that died
            if card.id in cards_lost:
                card.is_destroyed = True
                card.is_in_deck = False

        # Apply rewards if won
        xp_earned = 0
        stat_points_earned = 0
        level_up = False
        new_card = None

        if won:
            xp_earned = m_xp_reward
            stat_points_earned = m_stat_points

            # Bonus for no cards lost
            if not cards_lost:
                xp_earned = int(xp_earned * 1.5)

            # Bonus for genre synergy
            if has_genre_bonus:
                xp_earned = int(xp_earned * 1.2)

            if user:
                xp_info = user.add_xp(xp_earned)
                level_up = xp_info.get("level_up", False)

            # Generate reward card for boss kills
            if monster.is_boss:
                from app.services.card_service import CardService

                card_service = CardService()
                new_card = card_service.generate_card_for_task(
                    user_id=user_id,
                    task_id=None,
                    task_title=f"Победа над {monster.name}",
                    difficulty="very_hard",
                )
                if new_card:
                    new_card = new_card.to_dict()

        # Log battle
        battle_record = BattleLog(
            user_id=user_id,
            monster_id=monster_id,
            won=won,
            rounds=rounds,
            damage_dealt=damage_dealt,
            damage_taken=damage_taken,
            xp_earned=xp_earned,
            stat_points_earned=stat_points_earned,
        )
        db.session.add(battle_record)
        db.session.commit()

        # Build monster dict for response
        monster_dict = monster.to_dict()
        monster_dict.update(
            {
                "hp": m_hp,
                "attack": m_attack,
                "defense": m_defense,
                "xp_reward": m_xp_reward,
                "stat_points_reward": m_stat_points,
            }
        )

        return {
            "won": won,
            "rounds": rounds,
            "damage_dealt": damage_dealt,
            "damage_taken": damage_taken,
            "battle_log": battle_log,
            "xp_earned": xp_earned,
            "stat_points_earned": stat_points_earned,
            "level_up": level_up,
            "cards_used": [c.to_dict() for c in cards],
            "cards_lost": cards_lost,
            "cards_remaining": [
                {
                    "id": s["card"].id,
                    "name": s["card"].name,
                    "hp": s["hp"],
                    "max_hp": s["max_hp"],
                }
                for s in card_states.values()
            ],
            "monster": monster_dict,
            "reward_card": new_card,
        }

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
