"""Monster generation service using AI and Stable Diffusion."""

import logging
import os
import random
import uuid
from datetime import date
from pathlib import Path

import requests
from flask import current_app
from openai import OpenAI

from app import db
from app.models import DailyMonster, Monster
from app.models.character import GENRE_THEMES

logger = logging.getLogger(__name__)

# Genre-specific prompts for image generation
GENRE_IMAGE_STYLES = {
    "magic": (
        "magical creature, wizarding world style, mystical, "
        "glowing magical effects, dark fantasy art"
    ),
    "fantasy": (
        "epic fantasy monster, medieval fantasy, detailed armor and weapons, "
        "dramatic lighting, fantasy art"
    ),
    "scifi": (
        "sci-fi alien creature, futuristic, neon lights, "
        "cybernetic implants, space opera style"
    ),
    "cyberpunk": (
        "cyberpunk enemy, neon noir, rain-soaked streets, "
        "holographic effects, dystopian future"
    ),
    "anime": (
        "anime monster, japanese animation style, vibrant colors, "
        "dynamic pose, cel shaded"
    ),
}

# Genre-specific emoji pools
GENRE_EMOJIS = {
    "magic": ["🧙", "🔮", "⚡", "🌙", "🦇", "👻", "🐍", "🦉"],
    "fantasy": ["🐉", "👹", "⚔️", "🛡️", "🧝", "🦅", "🐺", "🦁"],
    "scifi": ["🤖", "👽", "🛸", "🦾", "🔬", "💀", "🌌", "⚡"],
    "cyberpunk": ["🤖", "💀", "⚡", "🌆", "💻", "🔫", "🎮", "🕶️"],
    "anime": ["👹", "🎌", "⚔️", "🔥", "💫", "🌸", "🐲", "👊"],
}


class MonsterGeneratorService:
    """Service for generating monsters using AI."""

    def __init__(self):
        self.openai_client = None
        self.stability_api_key = os.getenv("STABILITY_API_KEY")

        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)

        # Get static folder from Flask app context
        try:
            static_folder = current_app.static_folder or "/app/static"
        except RuntimeError:
            static_folder = "/app/static"

        # Ensure monster images directory exists
        self.images_dir = Path(static_folder) / "monster_images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def generate_monsters_for_genre(self, genre: str, count: int = 6) -> list[dict]:
        """
        Generate monster descriptions for a genre using AI.

        Returns list of monster data dicts.
        """
        if not self.openai_client:
            logger.warning("OpenAI client not initialized, using fallback monsters")
            return self._generate_fallback_monsters(genre, count)

        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])

        prompt = f"""Generate {count} unique monsters for a {genre_info['name']} themed game.
Genre description: {genre_info['description']}

For each monster, provide:
1. A creative, evocative name (in Russian)
2. A short description (1-2 sentences in Russian)
3. Monster type: "normal" for regular enemies, "elite" for stronger ones, "boss" for the strongest
4. A visual description for image generation (in English, 10-15 words, focus on appearance)

Return as JSON array with format:
[
  {{
    "name": "Название монстра",
    "description": "Описание монстра на русском",
    "type": "normal|elite|boss",
    "visual": "English visual description for image generation"
  }}
]

Make monsters thematic to {genre_info['name']}. Include 3-4 normal, 2 elite, and 1 boss monster.
Be creative with names - avoid generic names. Each monster should feel unique and memorable."""

        try:
            system_msg = (
                "You are a creative game designer specializing in monster design. "
                "Always respond with valid JSON only."
            )
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
                max_tokens=1500,
            )

            content = response.choices[0].message.content.strip()
            # Clean up markdown if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            import json

            monsters_data = json.loads(content)
            return monsters_data

        except Exception as e:
            logger.error(f"Failed to generate monsters via AI: {e}")
            return self._generate_fallback_monsters(genre, count)

    def _generate_fallback_monsters(self, genre: str, count: int) -> list[dict]:
        """Generate fallback monsters without AI."""
        genre_info = GENRE_THEMES.get(genre, GENRE_THEMES["fantasy"])
        monster_names = genre_info.get("monsters", ["Враг", "Противник", "Монстр"])

        monsters = []
        types = ["normal"] * 3 + ["elite"] * 2 + ["boss"]

        for i in range(min(count, len(monster_names))):
            monsters.append(
                {
                    "name": monster_names[i],
                    "description": f"Опасный противник из мира {genre_info['name']}",
                    "type": types[i] if i < len(types) else "normal",
                    "visual": f"{genre} creature, menacing appearance",
                }
            )

        return monsters

    def generate_monster_image(
        self, monster_name: str, visual_desc: str, genre: str
    ) -> str | None:
        """
        Generate monster image using Stable Diffusion.

        Returns URL of generated image or None if failed.
        """
        if not self.stability_api_key:
            logger.warning("Stability API key not set, skipping image generation")
            return None

        genre_style = GENRE_IMAGE_STYLES.get(genre, GENRE_IMAGE_STYLES["fantasy"])

        # Build prompt for image generation
        prompt = (
            f"{visual_desc}, {genre_style}, portrait, dark background, "
            "high quality, detailed, game art, character design"
        )

        try:
            response = requests.post(
                "https://api.stability.ai/v2beta/stable-image/generate/sd3",
                headers={
                    "authorization": f"Bearer {self.stability_api_key}",
                    "accept": "image/*",
                },
                files={"none": ""},
                data={
                    "prompt": prompt,
                    "model": "sd3.5-large-turbo",
                    "output_format": "jpeg",
                    "aspect_ratio": "1:1",
                },
                timeout=60,
            )

            if response.status_code == 200:
                # Save image and return URL
                image_filename = f"monster_{uuid.uuid4().hex[:8]}.jpg"
                image_path = self.images_dir / image_filename

                image_path.write_bytes(response.content)

                # Return relative URL
                image_url = f"/static/monster_images/{image_filename}"
                logger.info(f"Monster image generated: {image_url}")
                return image_url

            else:
                logger.error(
                    f"Stability API error: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to generate monster image: {e}")
            return None

    def create_monster_from_data(
        self, data: dict, genre: str, generate_image: bool = True
    ) -> Monster:
        """Create a Monster record from generated data."""
        monster_type = data.get("type", "normal")

        # Base stats based on type
        if monster_type == "boss":
            base_stats = {
                "level": 5,
                "hp": 200,
                "attack": 35,
                "defense": 20,
                "speed": 25,
                "xp_reward": 100,
                "stat_points_reward": 3,
                "is_boss": True,
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
                "is_boss": False,
            }
        else:  # normal
            base_stats = {
                "level": random.randint(1, 2),
                "hp": random.randint(50, 80),
                "attack": random.randint(10, 18),
                "defense": random.randint(5, 12),
                "speed": random.randint(10, 18),
                "xp_reward": random.randint(20, 40),
                "stat_points_reward": 1,
                "is_boss": False,
            }

        # Generate image if requested
        sprite_url = None
        if generate_image:
            sprite_url = self.generate_monster_image(
                data["name"], data.get("visual", ""), genre
            )

        # Select emoji
        emojis = GENRE_EMOJIS.get(genre, GENRE_EMOJIS["fantasy"])
        emoji = random.choice(emojis)

        monster = Monster(
            name=data["name"],
            description=data.get("description"),
            genre=genre,
            # Base stats
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
            # Visual
            sprite_url=sprite_url,
            emoji=emoji,
            is_boss=base_stats["is_boss"],
            ai_generated=True,
        )

        return monster

    def generate_daily_monsters(self, generate_images: bool = True) -> dict[str, int]:
        """
        Generate daily monsters for all genres.

        Called by cron job each night.

        Returns dict of genre -> count of monsters generated.
        """
        today = date.today()
        results = {}

        for genre in GENRE_THEMES.keys():
            try:
                # Check if monsters already generated for today
                existing = DailyMonster.query.filter_by(genre=genre, date=today).first()
                if existing:
                    logger.info(f"Monsters for {genre} already exist for {today}")
                    results[genre] = 0
                    continue

                # Generate monster descriptions
                monsters_data = self.generate_monsters_for_genre(genre, count=6)

                # Create monsters
                created_count = 0
                for i, monster_data in enumerate(monsters_data):
                    # Create monster
                    monster = self.create_monster_from_data(
                        monster_data, genre, generate_image=generate_images
                    )
                    db.session.add(monster)
                    db.session.flush()  # Get monster ID

                    # Create daily monster entry
                    daily = DailyMonster(
                        monster_id=monster.id,
                        genre=genre,
                        date=today,
                        slot_number=i + 1,
                    )
                    db.session.add(daily)
                    created_count += 1

                db.session.commit()
                results[genre] = created_count
                logger.info(f"Generated {created_count} monsters for {genre}")

            except Exception as e:
                logger.error(f"Failed to generate monsters for {genre}: {e}")
                db.session.rollback()
                results[genre] = 0

        return results

    def get_daily_monsters_for_user(
        self, user_id: int, genre: str, player_level: int
    ) -> list[dict]:
        """
        Get today's monsters for a user, scaled to their level.

        Returns list of monster dicts with scaled stats.
        """
        today = date.today()

        # Get daily monsters for genre
        daily_monsters = (
            DailyMonster.query.filter_by(genre=genre, date=today)
            .order_by(DailyMonster.slot_number)
            .all()
        )

        if not daily_monsters:
            # Fallback to any monsters of this genre
            monsters = Monster.query.filter_by(genre=genre).limit(6).all()
        else:
            monsters = [dm.monster for dm in daily_monsters]

        # Scale monsters for player level
        result = []
        for monster in monsters:
            if not monster:
                continue

            scaled = monster.get_scaled_stats(player_level)
            monster_dict = monster.to_dict()
            monster_dict.update(scaled)
            result.append(monster_dict)

        return result
