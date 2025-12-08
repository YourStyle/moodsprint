"""Bot configuration."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Bot configuration."""

    # Telegram
    BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    WEBAPP_URL: str = os.environ.get("WEBAPP_URL", "https://your-domain.com")

    # Database
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://moodsprint:moodsprint@db:5432/moodsprint"
    )

    # Redis for task queue
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    # Admin IDs (comma-separated)
    ADMIN_IDS: list[int] = []

    def __post_init__(self):
        admin_ids_str = os.environ.get("ADMIN_IDS", "")
        if admin_ids_str:
            self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",")]


config = Config()
