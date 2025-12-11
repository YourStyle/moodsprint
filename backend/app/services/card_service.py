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
    RARITY_MULTIPLIERS,
    CardRarity,
    CardTemplate,
    CardTrade,
    Friendship,
    UserCard,
)
from app.models.character import GENRE_THEMES
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

# Mapping task difficulty to card rarity
DIFFICULTY_TO_RARITY = {
    "easy": CardRarity.COMMON,
    "medium": CardRarity.UNCOMMON,
    "hard": CardRarity.RARE,
    "very_hard": CardRarity.EPIC,
    "boss": CardRarity.LEGENDARY,
}

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

    # Genre-specific art style prompts
    GENRE_ART_STYLES = {
        "magic": "mystical wizard, magical aura, glowing runes, fantasy art style",
        "fantasy": "medieval knight warrior, epic armor, fantasy art style",
        "scifi": "futuristic space pilot, sci-fi armor, cybernetic enhancements",
        "cyberpunk": "neon cyberpunk hacker, futuristic city, digital aesthetic",
        "anime": "anime hero character, dynamic pose, vibrant colors, anime art style",
    }

    # Rarity visual modifiers
    RARITY_MODIFIERS = {
        "common": "simple design, basic colors",
        "uncommon": "detailed design, subtle glow",
        "rare": "intricate design, blue magical aura, detailed armor",
        "epic": "epic design, purple magical aura, legendary equipment, dramatic lighting",
        "legendary": "divine design, golden aura, celestial light, ultimate power",
    }

    def __init__(self):
        self.openai_client = None
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)

        self.stability_api_key = os.getenv("STABILITY_API_KEY")

        # Ensure images directory exists
        self.images_dir = Path("/app/static/card_images")
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def get_user_genre(self, user_id: int) -> str:
        """Get user's preferred genre."""
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile and profile.favorite_genre:
            return profile.favorite_genre
        return "fantasy"

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
        self, user_id: int, task_id: int, task_title: str, difficulty: str
    ) -> UserCard | None:
        """
        Generate a card for completing a task.

        First tries to use an existing template, then falls back to AI generation.
        """
        genre = self.get_user_genre(user_id)
        rarity = DIFFICULTY_TO_RARITY.get(difficulty, CardRarity.COMMON)

        # Try to find an unused template for this genre
        template = self._get_random_template(genre)

        if template:
            card = self._create_card_from_template(user_id, task_id, template, rarity)
        else:
            # Generate card with AI
            card = self._generate_card_with_ai(
                user_id, task_id, genre, rarity, task_title
            )

        if card:
            db.session.add(card)
            db.session.commit()
            logger.info(
                f"Generated {rarity.value} card for user {user_id}: {card.name}"
            )

        return card

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
            # Build prompt from genre and rarity
            art_style = self.GENRE_ART_STYLES.get(
                genre, self.GENRE_ART_STYLES["fantasy"]
            )
            rarity_modifier = self.RARITY_MODIFIERS.get(
                rarity.value, self.RARITY_MODIFIERS["common"]
            )

            prompt = (
                f"Trading card game character portrait, {name}, {art_style}, "
                f"{rarity_modifier}, high quality digital art, centered composition"
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
                logger.error(
                    f"Stability AI API error: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to generate card image: {e}")
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
