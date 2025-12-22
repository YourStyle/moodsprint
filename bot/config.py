"""Bot configuration."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Bot configuration."""

    # Telegram
    BOT_TOKEN: str = field(
        default_factory=lambda: os.environ.get("BOT_TOKEN", "")
        or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    )
    WEBAPP_URL: str = field(
        default_factory=lambda: os.environ.get(
            "WEBAPP_URL", "https://staging.moodsprint.ru"
        )
    )

    # Database
    DATABASE_URL: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://moodsprint:moodsprint@db:5432/moodsprint",
        )
    )

    # Redis for task queue
    REDIS_URL: str = field(
        default_factory=lambda: os.environ.get("REDIS_URL", "redis://redis:6379/0")
    )

    # Backend API
    API_URL: str = field(
        default_factory=lambda: os.environ.get("API_URL", "http://backend:5000/api/v1")
    )
    BOT_SECRET: str = field(default_factory=lambda: os.environ.get("BOT_SECRET", ""))

    # Admin IDs (comma-separated)
    ADMIN_IDS: list[int] = field(default_factory=list)

    def __post_init__(self):
        admin_ids_str = os.environ.get("ADMIN_IDS", "")
        if admin_ids_str:
            self.ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",")]


config = Config()
