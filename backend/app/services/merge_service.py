"""Service for card merging mechanics."""

import logging
import random
from typing import Any

from app import db
from app.models.card import CardRarity, MergeLog, UserCard
from app.services.card_service import CardService

logger = logging.getLogger(__name__)


# Base chances for merge results based on input rarities
# Key is tuple of sorted rarities, value is dict of result rarity: probability
MERGE_RESULT_CHANCES = {
    # Common + Common
    (CardRarity.COMMON, CardRarity.COMMON): {
        CardRarity.COMMON: 0.60,
        CardRarity.UNCOMMON: 0.30,
        CardRarity.RARE: 0.08,
        CardRarity.EPIC: 0.02,
    },
    # Common + Uncommon
    (CardRarity.COMMON, CardRarity.UNCOMMON): {
        CardRarity.COMMON: 0.40,
        CardRarity.UNCOMMON: 0.40,
        CardRarity.RARE: 0.15,
        CardRarity.EPIC: 0.05,
    },
    # Uncommon + Uncommon
    (CardRarity.UNCOMMON, CardRarity.UNCOMMON): {
        CardRarity.UNCOMMON: 0.50,
        CardRarity.RARE: 0.35,
        CardRarity.EPIC: 0.12,
        CardRarity.LEGENDARY: 0.03,
    },
    # Common + Rare
    (CardRarity.COMMON, CardRarity.RARE): {
        CardRarity.UNCOMMON: 0.50,
        CardRarity.RARE: 0.40,
        CardRarity.EPIC: 0.10,
    },
    # Uncommon + Rare
    (CardRarity.UNCOMMON, CardRarity.RARE): {
        CardRarity.UNCOMMON: 0.30,
        CardRarity.RARE: 0.45,
        CardRarity.EPIC: 0.20,
        CardRarity.LEGENDARY: 0.05,
    },
    # Rare + Rare
    (CardRarity.RARE, CardRarity.RARE): {
        CardRarity.RARE: 0.40,
        CardRarity.EPIC: 0.40,
        CardRarity.LEGENDARY: 0.20,
    },
    # Common + Epic
    (CardRarity.COMMON, CardRarity.EPIC): {
        CardRarity.RARE: 0.60,
        CardRarity.EPIC: 0.35,
        CardRarity.LEGENDARY: 0.05,
    },
    # Uncommon + Epic
    (CardRarity.UNCOMMON, CardRarity.EPIC): {
        CardRarity.RARE: 0.40,
        CardRarity.EPIC: 0.45,
        CardRarity.LEGENDARY: 0.15,
    },
    # Rare + Epic
    (CardRarity.RARE, CardRarity.EPIC): {
        CardRarity.RARE: 0.20,
        CardRarity.EPIC: 0.50,
        CardRarity.LEGENDARY: 0.30,
    },
    # Epic + Epic
    (CardRarity.EPIC, CardRarity.EPIC): {
        CardRarity.EPIC: 0.40,
        CardRarity.LEGENDARY: 0.60,
    },
}

# Rarity order for sorting
RARITY_ORDER = {
    CardRarity.COMMON: 0,
    CardRarity.UNCOMMON: 1,
    CardRarity.RARE: 2,
    CardRarity.EPIC: 3,
    CardRarity.LEGENDARY: 4,
}


class MergeService:
    """Service for card merging mechanics."""

    def get_merge_chances(
        self, card1: UserCard, card2: UserCard
    ) -> dict[str, Any] | None:
        """
        Calculate merge result chances with bonuses.

        Returns None if merge is not allowed.
        """
        # Validate cards can be merged
        error = self._validate_merge(card1, card2)
        if error:
            return {"error": error}

        # Get base chances
        r1 = CardRarity(card1.rarity)
        r2 = CardRarity(card2.rarity)
        sorted_rarities = tuple(sorted([r1, r2], key=lambda x: RARITY_ORDER[x]))

        base_chances = MERGE_RESULT_CHANCES.get(sorted_rarities)
        if not base_chances:
            return {"error": "invalid_rarity_combination"}

        # Apply bonuses
        chances = dict(base_chances)
        bonuses = []

        # Bonus for same genre (+5% to higher rarities)
        if card1.genre == card2.genre:
            chances = self._shift_chances_up(chances, 0.05)
            bonuses.append({"type": "same_genre", "value": "+5%"})

        # Bonus for both having abilities (+3%)
        if card1.ability and card2.ability:
            chances = self._shift_chances_up(chances, 0.03)
            bonuses.append({"type": "both_abilities", "value": "+3%"})

        # Bonus for high combined attack (+2% if > 60)
        combined_attack = card1.attack + card2.attack
        if combined_attack > 60:
            chances = self._shift_chances_up(chances, 0.02)
            bonuses.append({"type": "high_attack", "value": "+2%"})

        # Format chances for response
        formatted_chances = {
            rarity.value: round(prob * 100, 1)
            for rarity, prob in chances.items()
            if prob > 0
        }

        return {
            "chances": formatted_chances,
            "bonuses": bonuses,
            "can_merge": True,
        }

    def merge_cards(self, user_id: int, card1_id: int, card2_id: int) -> dict[str, Any]:
        """
        Merge two cards into a new random card.

        Returns the new card or error.
        """
        card1 = UserCard.query.filter_by(id=card1_id, user_id=user_id).first()
        card2 = UserCard.query.filter_by(id=card2_id, user_id=user_id).first()

        if not card1 or not card2:
            return {"error": "card_not_found"}

        # Validate merge
        error = self._validate_merge(card1, card2)
        if error:
            return {"error": error}

        # Get base chances
        r1 = CardRarity(card1.rarity)
        r2 = CardRarity(card2.rarity)
        sorted_rarities = tuple(sorted([r1, r2], key=lambda x: RARITY_ORDER[x]))

        base_chances = MERGE_RESULT_CHANCES.get(sorted_rarities)
        if not base_chances:
            return {"error": "invalid_rarity_combination"}

        # Apply bonuses
        chances = dict(base_chances)

        if card1.genre == card2.genre:
            chances = self._shift_chances_up(chances, 0.05)

        if card1.ability and card2.ability:
            chances = self._shift_chances_up(chances, 0.03)

        if card1.attack + card2.attack > 60:
            chances = self._shift_chances_up(chances, 0.02)

        # Roll for result rarity
        result_rarity = self._roll_rarity(chances)

        # Determine genre (50/50 if different, same if same)
        if card1.genre == card2.genre:
            result_genre = card1.genre
        else:
            result_genre = random.choice([card1.genre, card2.genre])

        # Generate new card
        card_service = CardService()
        new_card = card_service.generate_card_for_task(
            user_id=user_id,
            task_id=None,
            task_title=f"Слияние: {card1.name} + {card2.name}",
            difficulty="merge",
            forced_rarity=result_rarity,
        )

        if not new_card:
            return {"error": "card_generation_failed"}

        # Override genre to match merge result
        new_card.genre = result_genre

        # Create merge log
        merge_log = MergeLog(
            user_id=user_id,
            card1_name=card1.name,
            card1_rarity=card1.rarity,
            card2_name=card2.name,
            card2_rarity=card2.rarity,
            result_card_id=new_card.id,
            result_rarity=result_rarity.value,
        )
        db.session.add(merge_log)

        # Mark source cards as destroyed
        card1.is_destroyed = True
        card2.is_destroyed = True

        # Remove from deck if in deck
        card1.is_in_deck = False
        card2.is_in_deck = False

        db.session.commit()

        # Check if rarity improved
        max_input_rarity = max(RARITY_ORDER[r1], RARITY_ORDER[r2])
        result_rarity_order = RARITY_ORDER[result_rarity]
        rarity_upgrade = result_rarity_order > max_input_rarity

        return {
            "success": True,
            "new_card": new_card.to_dict(),
            "merged_cards": [card1.name, card2.name],
            "rarity_upgrade": rarity_upgrade,
            "message": self._get_merge_message(rarity_upgrade, result_rarity),
        }

    def get_merge_history(self, user_id: int, limit: int = 10) -> list[MergeLog]:
        """Get recent merge history for user."""
        return (
            MergeLog.query.filter_by(user_id=user_id)
            .order_by(MergeLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def _validate_merge(self, card1: UserCard, card2: UserCard) -> str | None:
        """Validate if two cards can be merged. Returns error message or None."""
        if card1.id == card2.id:
            return "same_card"

        if card1.is_destroyed or card2.is_destroyed:
            return "card_destroyed"

        if card1.rarity == CardRarity.LEGENDARY.value:
            return "cannot_merge_legendary"

        if card2.rarity == CardRarity.LEGENDARY.value:
            return "cannot_merge_legendary"

        if card1.is_in_deck or card2.is_in_deck:
            return "card_in_deck"

        return None

    def _shift_chances_up(
        self, chances: dict[CardRarity, float], shift: float
    ) -> dict[CardRarity, float]:
        """Shift probability distribution towards higher rarities."""
        result = dict(chances)
        rarities = sorted(result.keys(), key=lambda x: RARITY_ORDER[x])

        if len(rarities) < 2:
            return result

        # Take from lowest rarity, give to others proportionally
        lowest = rarities[0]
        take_amount = min(result[lowest], shift)
        result[lowest] -= take_amount

        # Distribute to higher rarities
        higher_rarities = rarities[1:]
        if higher_rarities:
            per_rarity = take_amount / len(higher_rarities)
            for r in higher_rarities:
                result[r] += per_rarity

        return result

    def _roll_rarity(self, chances: dict[CardRarity, float]) -> CardRarity:
        """Roll for a rarity based on probability distribution."""
        roll = random.random()
        cumulative = 0

        for rarity in sorted(chances.keys(), key=lambda x: RARITY_ORDER[x]):
            cumulative += chances[rarity]
            if roll <= cumulative:
                return rarity

        # Fallback to lowest available
        return min(chances.keys(), key=lambda x: RARITY_ORDER[x])

    def _get_merge_message(self, upgrade: bool, rarity: CardRarity) -> str:
        """Get a message for merge result."""
        if upgrade:
            messages = {
                CardRarity.UNCOMMON: "Неплохо! Редкость повысилась!",
                CardRarity.RARE: "Отлично! Получилась редкая карта!",
                CardRarity.EPIC: "Потрясающе! Эпическая карта!",
                CardRarity.LEGENDARY: "ЛЕГЕНДАРНАЯ! Невероятная удача!",
            }
            return messages.get(rarity, "Редкость повысилась!")
        else:
            return "Слияние завершено"
