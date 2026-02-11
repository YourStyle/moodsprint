"""Battle arena service for gamification."""

import random
from datetime import date
from typing import Any

from app import db
from app.models import BattleLog, CharacterStats, DailyMonster, Monster, User
from app.models.character import GENRE_THEMES
from app.models.user_profile import UserProfile


class BattleService:
    """Service for managing battles in the arena."""

    def get_or_create_character(self, user_id: int) -> CharacterStats:
        """Get or create character stats for user."""
        character = CharacterStats.query.filter_by(user_id=user_id).first()
        if not character:
            character = CharacterStats(user_id=user_id)
            db.session.add(character)
            db.session.commit()
        return character

    def get_available_monsters(self, user_id: int) -> list[dict]:
        """
        Get monsters available for battle based on user's genre and level.
        Returns monsters with scaled stats for player level.
        """
        # Get user's genre preference
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        genre = profile.favorite_genre if profile else "fantasy"
        if not genre:
            genre = "fantasy"

        # Get user level for scaling
        user = User.query.get(user_id)
        user_level = user.level if user else 1

        # Try to get today's daily monsters first
        today = date.today()
        daily_monsters = (
            DailyMonster.query.filter_by(genre=genre, date=today)
            .order_by(DailyMonster.slot_number)
            .all()
        )

        if daily_monsters:
            # Return scaled daily monsters
            result = []
            for dm in daily_monsters:
                if dm.monster:
                    monster_dict = dm.monster.to_dict()
                    scaled = dm.monster.get_scaled_stats(user_level)
                    monster_dict.update(scaled)
                    result.append(monster_dict)
            if result:
                return result

        # Fallback to regular monsters
        monsters = Monster.query.filter_by(genre=genre).all()

        if not monsters:
            # Create default monsters for this genre
            monsters = self._create_default_monsters(genre)

        # Return scaled monsters
        result = []
        for monster in monsters[:6]:
            monster_dict = monster.to_dict()
            scaled = monster.get_scaled_stats(user_level)
            monster_dict.update(scaled)
            result.append(monster_dict)

        return result

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
                # Base stats for scaling
                base_level=base_stats["level"],
                base_hp=base_stats["hp"],
                base_attack=base_stats["attack"],
                base_defense=base_stats["defense"],
                base_speed=base_stats["speed"],
                base_xp_reward=base_stats["xp_reward"],
                base_stat_points_reward=base_stats["stat_points_reward"],
                # Legacy columns
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

    def start_battle(self, user_id: int, monster_id: int) -> dict[str, Any] | None:
        """
        Start a battle with a monster.

        Returns battle state or None if cannot battle.
        """
        character = self.get_or_create_character(user_id)
        monster = Monster.query.get(monster_id)

        if not monster:
            return None

        # Check if character has HP
        if character.current_hp <= 0:
            return {"error": "no_hp", "message": "Восстанови здоровье перед боем!"}

        return {
            "character": character.to_dict(),
            "monster": monster.to_dict(),
            "battle_started": True,
        }

    def execute_battle(
        self, user_id: int, monster_id: int, scaled_stats: dict | None = None
    ) -> dict[str, Any]:
        """
        Execute a full dynamic battle and return results.

        Features: critical hits, dodges, special attacks, combo system.
        """
        character = self.get_or_create_character(user_id)
        monster = Monster.query.get(monster_id)

        if not monster:
            return {"error": "monster_not_found"}

        if character.current_hp <= 0:
            return {"error": "no_hp", "message": "Восстанови здоровье!"}

        # Get user level for scaling
        user = User.query.get(user_id)
        user_level = user.level if user else 1

        # Use scaled stats if provided, otherwise get them
        if scaled_stats:
            m_hp = scaled_stats.get("hp", monster.hp)
            m_attack = scaled_stats.get("attack", monster.attack)
            m_defense = scaled_stats.get("defense", monster.defense)
            m_speed = scaled_stats.get("speed", monster.speed)
            m_xp_reward = scaled_stats.get("xp_reward", monster.xp_reward)
            m_stat_points = scaled_stats.get(
                "stat_points_reward", monster.stat_points_reward
            )
        else:
            scaled = monster.get_scaled_stats(user_level)
            m_hp = scaled["hp"]
            m_attack = scaled["attack"]
            m_defense = scaled["defense"]
            m_speed = scaled["speed"]
            m_xp_reward = scaled["xp_reward"]
            m_stat_points = scaled["stat_points_reward"]

        # Battle simulation with dynamic mechanics
        char_hp = character.current_hp
        monster_hp = m_hp
        rounds = 0
        damage_dealt = 0
        damage_taken = 0
        battle_log = []

        # Combo and special mechanics
        player_combo = 0
        monster_combo = 0

        # Determine turn order based on speed with some randomness
        speed_diff = character.speed - m_speed
        char_first = speed_diff >= 0 or random.random() < 0.3

        while char_hp > 0 and monster_hp > 0 and rounds < 15:
            rounds += 1

            # Player's turn
            if char_first or rounds > 1:
                action = self._player_action(
                    character, m_defense, player_combo, monster.is_boss
                )
                player_combo = action["new_combo"]

                if action["type"] == "dodge":
                    battle_log.append(
                        {
                            "round": rounds,
                            "actor": "player",
                            "action": "prepare",
                            "damage": 0,
                            "message": "Готовится к контратаке",
                        }
                    )
                else:
                    monster_hp -= action["damage"]
                    damage_dealt += action["damage"]
                    battle_log.append(
                        {
                            "round": rounds,
                            "actor": "player",
                            "action": action["type"],
                            "damage": action["damage"],
                            "is_critical": action.get("is_critical", False),
                            "is_combo": action.get("is_combo", False),
                            "message": action.get("message", ""),
                        }
                    )

                if monster_hp <= 0:
                    break

            # Monster's turn
            action = self._monster_action(
                m_attack, character.defense, monster_combo, monster.is_boss
            )
            monster_combo = action["new_combo"]

            # Check for player dodge
            dodge_chance = min(0.25, character.agility / 200)
            if random.random() < dodge_chance:
                battle_log.append(
                    {
                        "round": rounds,
                        "actor": "monster",
                        "action": "miss",
                        "damage": 0,
                        "message": "Промахнулся!",
                    }
                )
                player_combo += 1  # Bonus combo for dodging
            else:
                char_hp -= action["damage"]
                damage_taken += action["damage"]
                battle_log.append(
                    {
                        "round": rounds,
                        "actor": "monster",
                        "action": action["type"],
                        "damage": action["damage"],
                        "is_critical": action.get("is_critical", False),
                        "message": action.get("message", ""),
                    }
                )
                player_combo = 0  # Reset combo when hit

            if char_hp <= 0:
                break

            char_first = True  # After first round, normal turn order

        # Determine winner
        won = monster_hp <= 0

        # Update character HP
        character.current_hp = max(0, char_hp)

        # Apply rewards if won
        xp_earned = 0
        stat_points_earned = 0
        level_up = False

        card_xp_results = []

        if won:
            character.battles_won += 1
            xp_earned = m_xp_reward
            stat_points_earned = m_stat_points

            # Bonus XP for fast victory
            if rounds <= 5:
                xp_earned = int(xp_earned * 1.2)

            if user:
                xp_info = user.add_xp(xp_earned)
                level_up = xp_info.get("level_up", False)

            character.add_stat_points(stat_points_earned)

            # Award card XP to deck cards that participated (+20 per win)
            try:
                from app.models.card import UserCard
                from app.services.card_service import CardService

                card_service = CardService()
                deck_cards = UserCard.query.filter_by(
                    user_id=user_id, is_in_deck=True, is_destroyed=False
                ).all()
                for card in deck_cards:
                    result = card_service.add_card_xp(card.id, user_id, 20)
                    if result.get("success") and result.get("level_up"):
                        card_xp_results.append(result)
            except Exception:
                pass
        else:
            character.battles_lost += 1

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

        # Build scaled monster dict for response
        monster_dict = monster.to_dict()
        monster_dict.update(
            {
                "hp": m_hp,
                "attack": m_attack,
                "defense": m_defense,
                "speed": m_speed,
                "xp_reward": m_xp_reward,
                "stat_points_reward": m_stat_points,
            }
        )

        result = {
            "won": won,
            "rounds": rounds,
            "damage_dealt": damage_dealt,
            "damage_taken": damage_taken,
            "battle_log": battle_log,
            "xp_earned": xp_earned,
            "stat_points_earned": stat_points_earned,
            "level_up": level_up,
            "character": character.to_dict(),
            "monster": monster_dict,
        }

        if card_xp_results:
            result["card_level_ups"] = card_xp_results

        return result

    def _player_action(
        self, character: CharacterStats, monster_defense: int, combo: int, is_boss: bool
    ) -> dict:
        """Calculate player's action with dynamic mechanics."""
        base_attack = character.attack_power
        action_type = "attack"
        is_critical = False
        is_combo = False
        message = ""

        # Critical hit chance based on agility
        crit_chance = min(0.3, character.agility / 150)
        if random.random() < crit_chance:
            is_critical = True
            base_attack = int(base_attack * 1.8)
            message = "Критический удар!"
            action_type = "critical"

        # Combo bonus (builds up when dodging or landing hits)
        if combo >= 3:
            is_combo = True
            base_attack = int(base_attack * (1 + combo * 0.15))
            message = (
                f"Комбо x{combo}!" if not is_critical else f"Крит + Комбо x{combo}!"
            )
            action_type = "combo" if not is_critical else "critical_combo"

        # Special attack chance (higher intelligence = more special attacks)
        special_chance = min(0.15, character.intelligence / 200)
        if random.random() < special_chance and not is_critical:
            base_attack = int(base_attack * 1.5)
            message = "Особая атака!"
            action_type = "special"

        damage = self._calculate_damage(base_attack, monster_defense)

        # New combo value
        new_combo = combo + 1 if damage > 0 else 0

        return {
            "type": action_type,
            "damage": damage,
            "is_critical": is_critical,
            "is_combo": is_combo,
            "message": message,
            "new_combo": min(new_combo, 5),  # Cap combo at 5
        }

    def _monster_action(
        self, monster_attack: int, player_defense: int, combo: int, is_boss: bool
    ) -> dict:
        """Calculate monster's action."""
        base_attack = monster_attack
        action_type = "attack"
        is_critical = False
        message = ""

        # Bosses have special attacks
        if is_boss and random.random() < 0.25:
            base_attack = int(base_attack * 1.6)
            message = "Мощный удар!"
            action_type = "special"

        # Monster critical (lower chance than player)
        if random.random() < 0.1:
            is_critical = True
            base_attack = int(base_attack * 1.5)
            message = "Критический удар!" if not message else message + " Крит!"
            action_type = "critical"

        damage = self._calculate_damage(base_attack, player_defense)

        return {
            "type": action_type,
            "damage": damage,
            "is_critical": is_critical,
            "message": message,
            "new_combo": combo + 1 if damage > 0 else 0,
        }

    def _calculate_damage(self, attack: int, defense: int) -> int:
        """Calculate damage with randomness."""
        base_damage = max(1, attack - defense // 2)
        variance = random.uniform(0.85, 1.15)
        return max(1, int(base_damage * variance))

    def heal_character(self, user_id: int, amount: int | None = None) -> CharacterStats:
        """
        Heal character.

        If amount is None, full heal (costs more).
        """
        character = self.get_or_create_character(user_id)
        character.heal(amount)
        db.session.commit()
        return character

    def distribute_stat_points(
        self, user_id: int, stat_name: str, points: int
    ) -> dict[str, Any]:
        """Distribute available stat points to a stat."""
        character = self.get_or_create_character(user_id)

        if character.available_stat_points < points:
            return {
                "success": False,
                "error": "not_enough_points",
                "available": character.available_stat_points,
            }

        success = character.distribute_stat(stat_name, points)
        if success:
            db.session.commit()
            return {"success": True, "character": character.to_dict()}

        return {"success": False, "error": "invalid_stat_or_max_reached"}

    def get_battle_history(self, user_id: int, limit: int = 10) -> list[BattleLog]:
        """Get recent battle history."""
        return (
            BattleLog.query.filter_by(user_id=user_id)
            .order_by(BattleLog.created_at.desc())
            .limit(limit)
            .all()
        )
