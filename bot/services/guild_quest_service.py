"""Guild weekly quest management — calls backend API."""

import logging

import aiohttp
from config import config

logger = logging.getLogger(__name__)


async def generate_guild_weekly_quests():
    """Generate weekly quests for all guilds via backend API."""
    if not config.BOT_SECRET:
        logger.warning("BOT_SECRET not configured, skipping guild quest generation")
        return

    url = f"{config.API_URL}/guilds/quests/generate"
    headers = {"X-Bot-Secret": config.BOT_SECRET}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    count = data.get("data", {}).get("generated", 0)
                    if count > 0:
                        logger.info(f"Generated weekly quests for {count} guilds")
                else:
                    logger.error(f"Guild quest generation failed: {response.status}")
    except Exception as e:
        logger.error(f"Guild quest generation error: {e}")


async def expire_guild_quests():
    """Expire old guild quests via backend API."""
    if not config.BOT_SECRET:
        logger.warning("BOT_SECRET not configured, skipping guild quest expiration")
        return

    url = f"{config.API_URL}/guilds/quests/expire"
    headers = {"X-Bot-Secret": config.BOT_SECRET}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    count = data.get("data", {}).get("expired", 0)
                    if count > 0:
                        logger.info(f"Expired {count} old guild quests")
                else:
                    logger.error(f"Guild quest expiration failed: {response.status}")
    except Exception as e:
        logger.error(f"Guild quest expiration error: {e}")
