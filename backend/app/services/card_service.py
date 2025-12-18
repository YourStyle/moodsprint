"""Card generation and management service."""

import logging
import os
import random
import uuid
from pathlib import Path

import requests
from openai import OpenAI

from app import db
from app.models.card import (
    ABILITY_CHANCE_BY_RARITY,
    RARITY_MULTIPLIERS,
    CardAbility,
    CardRarity,
    CardTemplate,
    CardTrade,
    Friendship,
    UserCard,
)
from app.models.character import GENRE_THEMES
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

# Probability-based rarity distribution (independent of task difficulty)
# Each tuple is (rarity, cumulative_probability)
# Common: 50%, Uncommon: 30%, Rare: 15%, Epic: 4%, Legendary: 1%
RARITY_PROBABILITIES = [
    (CardRarity.COMMON, 0.50),
    (CardRarity.UNCOMMON, 0.80),
    (CardRarity.RARE, 0.95),
    (CardRarity.EPIC, 0.99),
    (CardRarity.LEGENDARY, 1.00),
]

# Card pool thresholds - how many templates per user in genre before we reuse
# Lower number = generate more new cards, higher = reuse more
# Legendary always generates new (unique feel)
CARD_POOL_MULTIPLIERS = {
    CardRarity.COMMON: 0.5,  # 1 template per 2 users
    CardRarity.UNCOMMON: 0.3,  # 1 template per ~3 users
    CardRarity.RARE: 0.2,  # 1 template per 5 users
    CardRarity.EPIC: 0.1,  # 1 template per 10 users
    CardRarity.LEGENDARY: 0.0,  # Always generate new (always unique)
}

# Minimum templates in pool before we start reusing
MIN_TEMPLATES_PER_GENRE = {
    CardRarity.COMMON: 10,
    CardRarity.UNCOMMON: 7,
    CardRarity.RARE: 5,
    CardRarity.EPIC: 3,
    CardRarity.LEGENDARY: 0,  # Never reuse
}


def get_random_rarity() -> CardRarity:
    """Get a random rarity based on probability distribution."""
    roll = random.random()
    for rarity, cumulative_prob in RARITY_PROBABILITIES:
        if roll <= cumulative_prob:
            return rarity
    return CardRarity.COMMON


def get_random_ability(rarity: CardRarity) -> CardAbility | None:
    """Get a random ability based on rarity chance, or None if no ability."""
    chance = ABILITY_CHANCE_BY_RARITY.get(rarity, 0)
    if random.random() > chance:
        return None
    # Pick a random ability
    abilities = list(CardAbility)
    return random.choice(abilities)


# Genre-specific card name prefixes for variety
GENRE_CARD_PREFIXES = {
    "magic": ["Маг", "Волшебник", "Чародей", "Алхимик", "Заклинатель"],
    "fantasy": ["Рыцарь", "Воин", "Паладин", "Следопыт", "Страж"],
    "scifi": ["Пилот", "Инженер", "Киборг", "Агент", "Исследователь"],
    "cyberpunk": ["Хакер", "Бегун", "Нетраннер", "Техник", "Наёмник"],
    "anime": ["Герой", "Самурай", "Ниндзя", "Маг", "Боец"],
}

# Genre emojis for cards
GENRE_CARD_EMOJIS = {
    "magic": ["🧙", "✨", "🔮", "⚡", "🌟", "📚", "🦉", "🌙"],
    "fantasy": ["⚔️", "🛡️", "🐉", "👑", "🏰", "🗡️", "🦅", "🐺"],
    "scifi": ["🚀", "🤖", "👽", "🔬", "💫", "🛸", "⚡", "🔭"],
    "cyberpunk": ["💻", "🎮", "🌆", "⚡", "🔧", "🎯", "💾", "🕶️"],
    "anime": ["🎌", "⚔️", "🔥", "💫", "🌸", "👊", "✨", "🎭"],
}


class CardService:
    """Service for card generation and management."""

    # Stability AI API config
    STABILITY_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

    # Genre-specific character types for variety
    GENRE_CHARACTERS = {
        "magic": [
            "ancient wizard with long beard and staff",
            "young sorceress with glowing hands",
            "mystical alchemist with potions",
            "elemental mage summoning fire",
            "dark warlock with shadow magic",
            "enchanted owl familiar",
            "magical golem made of crystals",
            "phoenix spirit bird",
        ],
        "fantasy": [
            "orc warrior with battle axe",
            "elf archer with bow",
            "dwarf blacksmith with hammer",
            "dragon breathing fire",
            "goblin rogue with daggers",
            "troll berserker",
            "giant with club",
            "unicorn with glowing horn",
            "griffin hybrid creature",
            "knight paladin in shining armor",
        ],
        "scifi": [
            "cyborg soldier with mechanical arm",
            "alien creature with tentacles",
            "robot android with glowing eyes",
            "space marine in power armor",
            "mutant with extra limbs",
            "AI hologram entity",
            "insectoid alien warrior",
            "mech pilot in exosuit",
            "genetically enhanced supersoldier",
        ],
        "cyberpunk": [
            "hacker with cybernetic implants",
            "street samurai with katana",
            "android assassin",
            "netrunner with neural interface",
            "corpo bodyguard in suit",
            "cyber-enhanced mercenary",
            "drone operator with robots",
            "biohacked mutant",
            "synth human replica",
        ],
        "anime": [
            "samurai warrior with katana",
            "ninja with shuriken",
            "mecha robot pilot",
            "magical girl with wand",
            "demon lord with horns",
            "spirit fox yokai",
            "martial artist fighter",
            "school hero with special powers",
            "dragon slayer knight",
        ],
    }

    # Genre-specific art style prompts - Art Deco & Steampunk fusion
    GENRE_ART_STYLES = {
        "magic": (
            "art deco style, geometric patterns, gold accents, "
            "mystical steampunk, brass gears, magical clockwork, ornate frames"
        ),
        "fantasy": (
            "art deco fantasy, steampunk armor, brass and copper details, "
            "geometric ornaments, vintage poster style, elegant machinery"
        ),
        "scifi": (
            "art deco retro-futurism, steampunk technology, brass machinery, "
            "geometric shapes, vintage sci-fi poster, ornate metalwork"
        ),
        "cyberpunk": (
            "art deco noir, steampunk cybernetics, brass implants, "
            "neon and gold, geometric patterns, industrial elegance"
        ),
        "anime": (
            "art deco anime fusion, steampunk aesthetic, brass accessories, "
            "geometric backgrounds, vintage Japanese poster style"
        ),
    }

    # Rarity visual modifiers
    RARITY_MODIFIERS = {
        "common": "simple design, clean lines",
        "uncommon": "detailed design, subtle magical glow",
        "rare": "intricate design, blue energy aura, impressive equipment",
        "epic": "epic majestic design, purple magical aura, legendary gear, dramatic lighting",
        "legendary": "divine godlike design, golden celestial aura, ultimate power, heavenly light",
    }

    def __init__(self):
        self.openai_client = None
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)

        self.stability_api_key = os.getenv("STABILITY_API_KEY")

        # Get static folder from Flask config or use default
        from flask import current_app

        try:
            static_folder = current_app.static_folder or "/app/static"
        except RuntimeError:
            static_folder = "/app/static"

        # Ensure images directory exists
        self.images_dir = Path(static_folder) / "card_images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def get_user_genre(self, user_id: int) -> str:
        """Get user's preferred genre."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile and profile.favorite_genre:
            return profile.favorite_genre
        return "fantasy"

    def _count_users_in_genre(self, genre: str) -> int:
        """Count how many users have this genre as their favorite."""
        count = (
            db.session.query(db.func.count(UserProfile.id))
            .filter(UserProfile.favorite_genre == genre)
            .scalar()
        )
        return count or 1  # At least 1 to avoid division issues

    def _count_templates_in_genre(self, genre: str) -> int:
        """Count active templates for a genre."""
        return CardTemplate.query.filter_by(genre=genre, is_active=True).count()

    def _should_generate_new_card(self, genre: str, rarity: CardRarity) -> bool:
        """
        Determine if we should generate a new card or use existing template.

        Logic:
        - Legendary: always generate new (unique feel)
        - Other rarities: generate if pool is too small for user count
        """
        # Legendary always generates new cards
        if rarity == CardRarity.LEGENDARY:
            return True

        users_count = self._count_users_in_genre(genre)
        templates_count = self._count_templates_in_genre(genre)
        min_templates = MIN_TEMPLATES_PER_GENRE.get(rarity, 5)
        multiplier = CARD_POOL_MULTIPLIERS.get(rarity, 0.3)

        # Required templates = max(minimum, users * multiplier)
        required_templates = max(min_templates, int(users_count * multiplier))

        # Generate new if we don't have enough templates
        should_generate = templates_count < required_templates

        logger.debug(
            f"Card pool check: genre={genre}, rarity={rarity.value}, "
            f"users={users_count}, templates={templates_count}, "
            f"required={required_templates}, generate_new={should_generate}"
        )

        return should_generate

    def determine_task_difficulty(
        self, task_title: str, task_description: str = ""
    ) -> str:
        """
        Use AI to determine task difficulty based on title and description.

        Returns: 'easy', 'medium', 'hard', or 'very_hard'
        """
        if not self.openai_client:
            # Fallback: simple heuristic based on text length
            text = f"{task_title} {task_description or ''}"
            if len(text) < 20:
                return "easy"
            elif len(text) < 50:
                return "medium"
            else:
                return "hard"

        try:
            prompt = f"""Определи сложность задачи для таск-менеджера.

Название задачи: {task_title}
Описание: {task_description or 'Нет описания'}

Оцени сложность по следующим критериям:
- easy: быстрые простые задачи (5-15 минут), рутина
- medium: задачи средней сложности (30-60 минут), требующие концентрации
- hard: сложные задачи (1-3 часа), требующие глубокой работы
- very_hard: очень сложные задачи (3+ часов), комплексные проекты

Ответь ТОЛЬКО одним словом: easy, medium, hard или very_hard"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Определяй сложность задач. Отвечай одним словом.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=10,
            )

            difficulty = response.choices[0].message.content.strip().lower()
            if difficulty in ["easy", "medium", "hard", "very_hard"]:
                return difficulty
            return "medium"

        except Exception as e:
            logger.error(f"Failed to determine difficulty via AI: {e}")
            return "medium"

    def generate_card_for_task(
        self,
        user_id: int,
        task_id: int | None,
        task_title: str,
        difficulty: str = "medium",
        forced_rarity: CardRarity | None = None,
    ) -> UserCard | None:
        """
        Generate a card for completing a task.

        Uses a card pool system:
        - Checks if we have enough templates for the user count in this genre
        - If pool is sufficient, picks a random existing template
        - If pool needs more variety, generates a new card and saves as template

        Rarity is determined by random probability, unless forced_rarity is specified.
        """
        genre = self.get_user_genre(user_id)
        rarity = forced_rarity if forced_rarity else get_random_rarity()

        # Check if we should generate new or use existing pool
        should_generate = self._should_generate_new_card(genre, rarity)

        if should_generate:
            # Generate new card with AI and save as template
            card = self._generate_card_with_ai(
                user_id, task_id, genre, rarity, task_title
            )
            if card:
                # Save as template for future reuse (except legendary - unique)
                if rarity != CardRarity.LEGENDARY:
                    self._save_as_template(card, genre)
        else:
            # Use existing template from pool
            template = self._get_random_template(genre)
            if template:
                card = self._create_card_from_template(
                    user_id, task_id, template, rarity
                )
            else:
                # Fallback: generate if no templates exist
                card = self._generate_card_with_ai(
                    user_id, task_id, genre, rarity, task_title
                )
                if card:
                    self._save_as_template(card, genre)

        if card:
            db.session.add(card)
            db.session.commit()
            logger.info(
                f"Generated {rarity.value} card for user {user_id}: {card.name} "
                f"(new={should_generate})"
            )

        return card

    def _save_as_template(self, card: UserCard, genre: str) -> CardTemplate | None:
        """Save a generated card as a template for future reuse."""
        try:
            template = CardTemplate(
                name=card.name,
                description=card.description,
                genre=genre,
                base_hp=50,  # Base stats, will be modified by rarity
                base_attack=15,
                image_url=card.image_url,
                emoji=card.emoji,
                ai_generated=True,
                is_active=True,
            )
            db.session.add(template)
            # Don't commit here, let the caller handle transaction
            logger.info(f"Saved new template: {card.name} for genre {genre}")
            return template
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
            return None

    def _get_random_template(self, genre: str) -> CardTemplate | None:
        """Get a random active template for the genre."""
        templates = CardTemplate.query.filter_by(genre=genre, is_active=True).all()
        if templates:
            return random.choice(templates)
        return None

    def _create_card_from_template(
        self, user_id: int, task_id: int, template: CardTemplate, rarity: CardRarity
    ) -> UserCard:
        """Create a user card from a template with rarity modifiers."""
        multipliers = RARITY_MULTIPLIERS[rarity]

        hp = int(template.base_hp * multipliers["hp"])
        attack = int(template.base_attack * multipliers["attack"])

        # Roll for ability based on rarity
        ability = get_random_ability(rarity)

        return UserCard(
            user_id=user_id,
            template_id=template.id,
            task_id=task_id,
            name=template.name,
            description=template.description,
            genre=template.genre,
            rarity=rarity.value,
            hp=hp,
            attack=attack,
            current_hp=hp,
            image_url=template.image_url,
            emoji=template.emoji,
            ability=ability.value if ability else None,
        )

    def _generate_card_with_ai(
        self,
        user_id: int,
        task_id: int,
        genre: str,
        rarity: CardRarity,
        task_title: str,
    ) -> UserCard:
        """Generate a card using AI for name and description."""
        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])

        # Generate name and description
        name, description = self._generate_card_text(
            genre, genre_info, rarity, task_title
        )

        # Calculate stats based on rarity
        multipliers = RARITY_MULTIPLIERS[rarity]
        base_hp = random.randint(40, 60)
        base_attack = random.randint(12, 20)

        hp = int(base_hp * multipliers["hp"])
        attack = int(base_attack * multipliers["attack"])

        # Select emoji
        emojis = GENRE_CARD_EMOJIS.get(genre, GENRE_CARD_EMOJIS["fantasy"])
        emoji = random.choice(emojis)

        # Roll for ability based on rarity
        ability = get_random_ability(rarity)

        # Card created without image - image will be generated async
        return UserCard(
            user_id=user_id,
            template_id=None,  # AI generated, no template
            task_id=task_id,
            name=name,
            description=description,
            genre=genre,
            rarity=rarity.value,
            hp=hp,
            attack=attack,
            current_hp=hp,
            image_url=None,  # Will be generated async
            emoji=emoji,
            ability=ability.value if ability else None,
        )

    def _generate_card_image(
        self, name: str, genre: str, rarity: CardRarity
    ) -> str | None:
        """Generate card image using Stability AI."""
        if not self.stability_api_key:
            logger.warning(
                "Stability API key not configured, skipping image generation"
            )
            return None

        try:
            # Get random character type for variety
            characters = self.GENRE_CHARACTERS.get(
                genre, self.GENRE_CHARACTERS["fantasy"]
            )
            character_type = random.choice(characters)

            # Build prompt from genre and rarity
            art_style = self.GENRE_ART_STYLES.get(
                genre, self.GENRE_ART_STYLES["fantasy"]
            )
            rarity_modifier = self.RARITY_MODIFIERS.get(
                rarity.value, self.RARITY_MODIFIERS["common"]
            )

            prompt = (
                f"Art deco steampunk trading card portrait, {character_type}, "
                f"{art_style}, {rarity_modifier}, "
                f"brass and gold ornaments, geometric art deco frame, "
                f"vintage poster illustration, highly detailed, elegant composition"
            )

            logger.info(f"Generating card image with prompt: {prompt[:100]}...")

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
                # Save image to file
                filename = f"{uuid.uuid4()}.png"
                filepath = self.images_dir / filename
                filepath.write_bytes(response.content)

                # Return URL path for the image
                image_url = f"/static/card_images/{filename}"
                logger.info(f"Card image generated successfully: {image_url}")
                return image_url
            else:
                error_text = (
                    response.text[:500] if response.text else "No response body"
                )
                logger.error(
                    f"Stability AI API error: status={response.status_code}, "
                    f"response={error_text}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to generate card image: {e}", exc_info=True)
            return None

    def generate_card_image_async(self, card_id: int, user_id: int) -> dict:
        """Generate image for an existing card (called async after card creation)."""
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()

        if not card:
            return {"success": False, "error": "card_not_found"}

        if card.image_url:
            return {
                "success": True,
                "image_url": card.image_url,
                "already_exists": True,
            }

        # Generate image
        rarity = CardRarity(card.rarity)
        image_url = self._generate_card_image(card.name, card.genre, rarity)

        if image_url:
            card.image_url = image_url
            db.session.commit()
            logger.info(f"Generated image for card {card_id}: {image_url}")
            return {"success": True, "image_url": image_url}
        else:
            logger.warning(
                f"Image generation failed for card {card_id}. "
                f"API key configured: {bool(self.stability_api_key)}"
            )
            return {"success": False, "error": "generation_failed"}

    def _generate_card_text(
        self, genre: str, genre_info: dict, rarity: CardRarity, task_title: str
    ) -> tuple[str, str]:
        """Generate card name and description using AI or fallback."""
        if not self.openai_client:
            return self._generate_fallback_text(genre, rarity)

        try:
            rarity_names = {
                CardRarity.COMMON: "обычный",
                CardRarity.UNCOMMON: "необычный",
                CardRarity.RARE: "редкий",
                CardRarity.EPIC: "эпический",
                CardRarity.LEGENDARY: "легендарный",
            }

            prompt = f"""Создай карточку персонажа для игры в жанре {genre_info['name']}.
Редкость карты: {rarity_names[rarity]}
Задача, за которую получена карта: {task_title}

Создай:
1. Уникальное имя персонажа (на русском, 1-3 слова)
2. Короткое описание персонажа (на русском, 1 предложение, до 100 символов)

Персонаж должен тематически соответствовать жанру {genre_info['name']}.
Чем выше редкость, тем эпичнее должно быть имя.

Ответ в формате:
ИМЯ: [имя]
ОПИСАНИЕ: [описание]"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Создавай карточки для RPG. Отвечай в заданном формате.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=150,
            )

            content = response.choices[0].message.content.strip()

            # Parse response
            name = "Герой"
            description = "Отважный воин"

            for line in content.split("\n"):
                if line.startswith("ИМЯ:"):
                    name = line.replace("ИМЯ:", "").strip()
                elif line.startswith("ОПИСАНИЕ:"):
                    description = line.replace("ОПИСАНИЕ:", "").strip()

            return name, description

        except Exception as e:
            logger.error(f"Failed to generate card text via AI: {e}")
            return self._generate_fallback_text(genre, rarity)

    def _generate_fallback_text(
        self, genre: str, rarity: CardRarity
    ) -> tuple[str, str]:
        """Generate fallback card name and description."""
        prefixes = GENRE_CARD_PREFIXES.get(genre, GENRE_CARD_PREFIXES["fantasy"])
        prefix = random.choice(prefixes)

        rarity_suffixes = {
            CardRarity.COMMON: ["Начинающий", "Юный", "Простой"],
            CardRarity.UNCOMMON: ["Опытный", "Умелый", "Способный"],
            CardRarity.RARE: ["Мастер", "Знаменитый", "Искусный"],
            CardRarity.EPIC: ["Великий", "Легендарный", "Могучий"],
            CardRarity.LEGENDARY: ["Божественный", "Непобедимый", "Всемогущий"],
        }

        suffix = random.choice(rarity_suffixes[rarity])
        name = f"{suffix} {prefix}"

        descriptions = {
            CardRarity.COMMON: "Только начинает свой путь героя.",
            CardRarity.UNCOMMON: "Прошёл множество испытаний.",
            CardRarity.RARE: "Известен своими подвигами.",
            CardRarity.EPIC: "Легенды слагают о его силе.",
            CardRarity.LEGENDARY: "Превзошёл всех смертных.",
        }

        return name, descriptions[rarity]

    def get_user_cards(
        self, user_id: int, genre: str | None = None, include_destroyed: bool = False
    ) -> list[UserCard]:
        """Get user's card collection."""
        query = UserCard.query.filter_by(user_id=user_id)

        if not include_destroyed:
            query = query.filter_by(is_destroyed=False)

        if genre:
            query = query.filter_by(genre=genre)

        return query.order_by(UserCard.created_at.desc()).all()

    def get_user_deck(self, user_id: int) -> list[UserCard]:
        """Get user's active battle deck."""
        return UserCard.query.filter_by(
            user_id=user_id, is_in_deck=True, is_destroyed=False
        ).all()

    def add_to_deck(self, user_id: int, card_id: int, max_deck_size: int = 5) -> dict:
        """Add a card to user's battle deck."""
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()

        if not card:
            return {"success": False, "error": "card_not_found"}

        if card.is_destroyed:
            return {"success": False, "error": "card_destroyed"}

        if card.is_in_deck:
            return {"success": False, "error": "already_in_deck"}

        # Check deck size
        current_deck = self.get_user_deck(user_id)
        if len(current_deck) >= max_deck_size:
            return {"success": False, "error": "deck_full", "max_size": max_deck_size}

        card.is_in_deck = True
        db.session.commit()

        return {"success": True, "card": card.to_dict()}

    def remove_from_deck(self, user_id: int, card_id: int) -> dict:
        """Remove a card from user's battle deck."""
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()

        if not card:
            return {"success": False, "error": "card_not_found"}

        if not card.is_in_deck:
            return {"success": False, "error": "not_in_deck"}

        card.is_in_deck = False
        db.session.commit()

        return {"success": True}

    def heal_card(self, card_id: int, user_id: int) -> dict:
        """Heal a card to full HP."""
        card = UserCard.query.filter_by(id=card_id, user_id=user_id).first()

        if not card:
            return {"success": False, "error": "card_not_found"}

        if card.is_destroyed:
            return {"success": False, "error": "card_destroyed"}

        card.heal()
        db.session.commit()

        return {"success": True, "card": card.to_dict()}

    def heal_all_cards(self, user_id: int) -> int:
        """Heal all user's cards. Returns number of cards healed."""
        cards = UserCard.query.filter_by(user_id=user_id, is_destroyed=False).all()
        healed = 0

        for card in cards:
            if card.current_hp < card.hp:
                card.heal()
                healed += 1

        db.session.commit()
        return healed

    # Friend system methods
    def send_friend_request(self, user_id: int, friend_id: int) -> dict:
        """Send a friend request."""
        if user_id == friend_id:
            return {"success": False, "error": "cannot_friend_self"}

        # Check if friendship already exists
        existing = Friendship.query.filter(
            ((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id))
            | ((Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
        ).first()

        if existing:
            if existing.status == "accepted":
                return {"success": False, "error": "already_friends"}
            elif existing.status == "pending":
                return {"success": False, "error": "request_pending"}
            elif existing.status == "blocked":
                return {"success": False, "error": "blocked"}

        friendship = Friendship(user_id=user_id, friend_id=friend_id, status="pending")
        db.session.add(friendship)
        db.session.commit()

        return {"success": True, "friendship": friendship.to_dict()}

    def accept_friend_request(self, user_id: int, request_id: int) -> dict:
        """Accept a friend request."""
        from datetime import datetime

        friendship = Friendship.query.filter_by(
            id=request_id, friend_id=user_id, status="pending"
        ).first()

        if not friendship:
            return {"success": False, "error": "request_not_found"}

        friendship.status = "accepted"
        friendship.accepted_at = datetime.utcnow()
        db.session.commit()

        return {"success": True, "friendship": friendship.to_dict()}

    def get_friends(self, user_id: int) -> list[dict]:
        """Get user's friends list."""
        friendships = Friendship.query.filter(
            ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id))
            & (Friendship.status == "accepted")
        ).all()

        friends = []
        for f in friendships:
            friend_id = f.friend_id if f.user_id == user_id else f.user_id
            friends.append(
                {
                    "friendship_id": f.id,
                    "friend_id": friend_id,
                    "since": f.accepted_at.isoformat() if f.accepted_at else None,
                }
            )

        return friends

    def get_pending_requests(self, user_id: int) -> list[Friendship]:
        """Get pending friend requests for user."""
        return Friendship.query.filter_by(friend_id=user_id, status="pending").all()

    # Card trading methods
    def create_trade_offer(
        self,
        sender_id: int,
        receiver_id: int,
        sender_card_id: int,
        receiver_card_id: int | None = None,
        message: str | None = None,
    ) -> dict:
        """Create a card trade offer."""
        # Verify friendship
        is_friend = Friendship.query.filter(
            (
                (Friendship.user_id == sender_id)
                & (Friendship.friend_id == receiver_id)
                | (Friendship.user_id == receiver_id)
                & (Friendship.friend_id == sender_id)
            )
            & (Friendship.status == "accepted")
        ).first()

        if not is_friend:
            return {"success": False, "error": "not_friends"}

        # Verify sender's card
        sender_card = UserCard.query.filter_by(
            id=sender_card_id, user_id=sender_id, is_tradeable=True, is_destroyed=False
        ).first()

        if not sender_card:
            return {"success": False, "error": "sender_card_invalid"}

        # Verify receiver's card if exchange
        if receiver_card_id:
            receiver_card = UserCard.query.filter_by(
                id=receiver_card_id,
                user_id=receiver_id,
                is_tradeable=True,
                is_destroyed=False,
            ).first()

            if not receiver_card:
                return {"success": False, "error": "receiver_card_invalid"}

        trade = CardTrade(
            sender_id=sender_id,
            receiver_id=receiver_id,
            sender_card_id=sender_card_id,
            receiver_card_id=receiver_card_id,
            message=message,
            status="pending",
        )
        db.session.add(trade)
        db.session.commit()

        return {"success": True, "trade": trade.to_dict()}

    def accept_trade(self, user_id: int, trade_id: int) -> dict:
        """Accept a trade offer."""
        from datetime import datetime

        trade = CardTrade.query.filter_by(
            id=trade_id, receiver_id=user_id, status="pending"
        ).first()

        if not trade:
            return {"success": False, "error": "trade_not_found"}

        # Transfer cards
        sender_card = trade.sender_card
        if sender_card:
            sender_card.user_id = trade.receiver_id
            sender_card.is_in_deck = False

        receiver_card = trade.receiver_card
        if receiver_card:
            receiver_card.user_id = trade.sender_id
            receiver_card.is_in_deck = False

        trade.status = "accepted"
        trade.completed_at = datetime.utcnow()
        db.session.commit()

        return {"success": True, "trade": trade.to_dict()}

    def reject_trade(self, user_id: int, trade_id: int) -> dict:
        """Reject a trade offer."""
        trade = CardTrade.query.filter_by(
            id=trade_id, receiver_id=user_id, status="pending"
        ).first()

        if not trade:
            return {"success": False, "error": "trade_not_found"}

        trade.status = "rejected"
        db.session.commit()

        return {"success": True}

    def get_pending_trades(self, user_id: int) -> list[CardTrade]:
        """Get pending trades for user (both sent and received)."""
        return CardTrade.query.filter(
            ((CardTrade.sender_id == user_id) | (CardTrade.receiver_id == user_id))
            & (CardTrade.status == "pending")
        ).all()

    def merge_cards(self, user_id: int, card1: UserCard, card2: UserCard) -> dict:
        """
        Merge two cards of the same rarity to create one card of higher rarity.

        Args:
            user_id: The user's ID
            card1: First card to merge
            card2: Second card to merge

        Returns:
            dict with success status and new card or error
        """
        # Rarity upgrade order
        rarity_order = ["common", "uncommon", "rare", "epic", "legendary"]
        current_rarity_idx = rarity_order.index(card1.rarity)

        if current_rarity_idx >= len(rarity_order) - 1:
            return {"success": False, "error": "Cannot upgrade legendary cards"}

        new_rarity = rarity_order[current_rarity_idx + 1]
        new_rarity_enum = CardRarity(new_rarity)

        # Get genre from one of the cards (prefer card1, or pick randomly)
        genre = card1.genre or card2.genre or "fantasy"

        # Generate new card name and description
        name, description = self._generate_card_text(
            genre,
            GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"]),
            new_rarity_enum,
            f"Merged from {card1.name} and {card2.name}",
        )

        # Calculate stats - take best of both cards and apply new rarity multiplier
        multipliers = RARITY_MULTIPLIERS[new_rarity_enum]
        base_hp = max(card1.hp, card2.hp)
        base_attack = max(card1.attack, card2.attack)

        # Apply upgrade bonus (10-20% on top of the best card)
        hp = int(
            base_hp
            * multipliers["hp"]
            / RARITY_MULTIPLIERS[CardRarity(card1.rarity)]["hp"]
            * random.uniform(1.1, 1.2)
        )
        attack = int(
            base_attack
            * multipliers["attack"]
            / RARITY_MULTIPLIERS[CardRarity(card1.rarity)]["attack"]
            * random.uniform(1.1, 1.2)
        )

        # Select emoji
        emojis = GENRE_CARD_EMOJIS.get(genre, GENRE_CARD_EMOJIS["fantasy"])
        emoji = random.choice(emojis)

        # Higher chance for ability on merged card
        ability = get_random_ability(new_rarity_enum)

        # Create new card
        new_card = UserCard(
            user_id=user_id,
            template_id=None,
            task_id=None,  # Merged card, no task
            name=name,
            description=description,
            genre=genre,
            rarity=new_rarity,
            hp=hp,
            attack=attack,
            current_hp=hp,
            image_url=None,  # Will be generated async
            emoji=emoji,
            ability=ability.value if ability else None,
        )

        # Mark old cards as destroyed
        card1.is_destroyed = True
        card1.is_in_deck = False
        card2.is_destroyed = True
        card2.is_in_deck = False

        db.session.add(new_card)
        db.session.commit()

        # Get rarity name for message
        rarity_names = {
            "common": "Обычную",
            "uncommon": "Необычную",
            "rare": "Редкую",
            "epic": "Эпическую",
            "legendary": "Легендарную",
        }

        rarity_label = rarity_names.get(new_rarity, new_rarity)
        return {
            "success": True,
            "card": new_card.to_dict(),
            "message": f"Карты объединены! Получена {rarity_label} карта!",
        }
