"""Battle arena service for gamification."""

import random
from typing import Any

from app import db
from app.models import BattleLog, CharacterStats, Monster, User
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

    def get_available_monsters(self, user_id: int) -> list[Monster]:
        """
        Get monsters available for battle based on user's genre and level.
        """
        # Get user's genre preference
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        genre = profile.favorite_genre if profile else "fantasy"
        if not genre:
            genre = "fantasy"

        # Get user level for scaling
        user = User.query.get(user_id)
        user_level = user.level if user else 1

        # Get monsters of user's genre, or create if none exist
        monsters = Monster.query.filter_by(genre=genre).all()

        if not monsters:
            # Create default monsters for this genre
            monsters = self._create_default_monsters(genre)

        # Filter by appropriate level range
        max_monster_level = min(user_level + 2, 10)
        available = [m for m in monsters if m.level <= max_monster_level]

        return available or monsters[:3]

    def _create_default_monsters(self, genre: str) -> list[Monster]:
        """Create default monsters for a genre."""
        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])
        monster_names = genre_info.get("monsters", ["Враг", "Монстр", "Босс"])

        monsters = []
        emojis = ["👾", "👹", "🐉", "👻", "🤖"]

        for i, name in enumerate(monster_names[:5]):
            level = i + 1
            monster = Monster(
                name=name,
                genre=genre,
                level=level,
                hp=50 + level * 20,
                attack=10 + level * 5,
                defense=5 + level * 3,
                speed=10 + level * 2,
                xp_reward=20 + level * 15,
                stat_points_reward=1 if level < 3 else 2,
                emoji=emojis[i % len(emojis)],
                is_boss=level >= 4,
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

    def execute_battle(self, user_id: int, monster_id: int) -> dict[str, Any]:
        """
        Execute a full battle and return results.

        Simple turn-based combat simulation.
        """
        character = self.get_or_create_character(user_id)
        monster = Monster.query.get(monster_id)

        if not monster:
            return {"error": "monster_not_found"}

        if character.current_hp <= 0:
            return {"error": "no_hp", "message": "Восстанови здоровье!"}

        # Battle simulation
        char_hp = character.current_hp
        monster_hp = monster.hp
        rounds = 0
        damage_dealt = 0
        damage_taken = 0
        battle_log = []

        # Determine who goes first based on speed
        char_first = character.speed >= monster.speed

        while char_hp > 0 and monster_hp > 0 and rounds < 20:
            rounds += 1

            if char_first:
                # Character attacks
                char_damage = self._calculate_damage(
                    character.attack_power, monster.defense
                )
                monster_hp -= char_damage
                damage_dealt += char_damage
                battle_log.append(
                    {"round": rounds, "actor": "player", "damage": char_damage}
                )

                if monster_hp <= 0:
                    break

                # Monster attacks
                monster_damage = self._calculate_damage(
                    monster.attack, character.defense
                )
                char_hp -= monster_damage
                damage_taken += monster_damage
                battle_log.append(
                    {"round": rounds, "actor": "monster", "damage": monster_damage}
                )
            else:
                # Monster attacks first
                monster_damage = self._calculate_damage(
                    monster.attack, character.defense
                )
                char_hp -= monster_damage
                damage_taken += monster_damage
                battle_log.append(
                    {"round": rounds, "actor": "monster", "damage": monster_damage}
                )

                if char_hp <= 0:
                    break

                # Character attacks
                char_damage = self._calculate_damage(
                    character.attack_power, monster.defense
                )
                monster_hp -= char_damage
                damage_dealt += char_damage
                battle_log.append(
                    {"round": rounds, "actor": "player", "damage": char_damage}
                )

        # Determine winner
        won = monster_hp <= 0

        # Update character HP
        character.current_hp = max(0, char_hp)

        # Apply rewards if won
        xp_earned = 0
        stat_points_earned = 0
        level_up = False

        if won:
            character.battles_won += 1
            xp_earned = monster.xp_reward
            stat_points_earned = monster.stat_points_reward

            user = User.query.get(user_id)
            if user:
                xp_info = user.add_xp(xp_earned)
                level_up = xp_info.get("level_up", False)

            character.add_stat_points(stat_points_earned)
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

        return {
            "won": won,
            "rounds": rounds,
            "damage_dealt": damage_dealt,
            "damage_taken": damage_taken,
            "battle_log": battle_log,
            "xp_earned": xp_earned,
            "stat_points_earned": stat_points_earned,
            "level_up": level_up,
            "character": character.to_dict(),
            "monster": monster.to_dict(),
        }

    def _calculate_damage(self, attack: int, defense: int) -> int:
        """Calculate damage with some randomness."""
        base_damage = max(1, attack - defense // 2)
        variance = random.uniform(0.8, 1.2)
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
