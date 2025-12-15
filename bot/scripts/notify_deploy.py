#!/usr/bin/env python3
"""
Deploy notification script.

Sends deployment status to admin users via Telegram bot.
Run this script after docker compose up completes.

Usage:
    python scripts/notify_deploy.py [--server prod|stage]
"""

import argparse
import asyncio
import os
import subprocess
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot  # noqa: E402


def get_git_version() -> str:
    """Get current git version/tag."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def get_container_status() -> list[dict]:
    """Get status of docker containers."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--format",
                "{{.Names}}\t{{.Status}}\t{{.Health}}",
                "--filter",
                "name=moodsprint",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        containers = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            name = parts[0] if len(parts) > 0 else "unknown"
            status = parts[1] if len(parts) > 1 else "unknown"
            health = parts[2] if len(parts) > 2 else ""

            # Determine if healthy
            is_healthy = "Up" in status and (not health or "healthy" in health.lower())

            containers.append(
                {
                    "name": name.replace("moodsprint-", ""),
                    "status": status,
                    "healthy": is_healthy,
                }
            )
        return containers
    except Exception as e:
        return [{"name": "error", "status": str(e), "healthy": False}]


def format_containers(containers: list[dict]) -> str:
    """Format container status for message."""
    lines = []
    for c in sorted(containers, key=lambda x: x["name"]):
        icon = "✅" if c["healthy"] else "❌"
        lines.append(f"{icon} {c['name']}")
    return "\n".join(lines)


async def send_deploy_notification(
    bot_token: str, admin_ids: list[int], server: str = "prod"
) -> None:
    """Send deploy notification to admins."""
    bot = Bot(token=bot_token)

    version = get_git_version()
    containers = get_container_status()
    timestamp = datetime.now().strftime("%H:%M:%S")

    # Count healthy containers
    healthy_count = sum(1 for c in containers if c["healthy"])
    total_count = len(containers)
    all_healthy = healthy_count == total_count

    # Format message
    status_emoji = "✅" if all_healthy else "⚠️"
    server_emoji = "🚀" if server == "prod" else "🧪"

    message = f"""
{server_emoji} *Деплой завершён* ({server.upper()})

📦 Версия: `{version}`
🕐 Время: {timestamp}
{status_emoji} Статус: {healthy_count}/{total_count} контейнеров

*Контейнеры:*
{format_containers(containers)}
"""

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id, text=message.strip(), parse_mode="Markdown"
            )
            print(f"Sent notification to admin {admin_id}")
        except Exception as e:
            print(f"Failed to send to {admin_id}: {e}")

    await bot.session.close()


def main():
    parser = argparse.ArgumentParser(description="Send deploy notification to admins")
    parser.add_argument(
        "--server",
        choices=["prod", "stage"],
        default="prod",
        help="Server type (prod or stage)",
    )
    args = parser.parse_args()

    # Get bot token from environment
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    # Get admin IDs from environment
    admin_ids_str = os.environ.get("ADMIN_IDS", "")
    if not admin_ids_str:
        print("Error: ADMIN_IDS not set")
        sys.exit(1)

    admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]

    if not admin_ids:
        print("Error: No valid admin IDs found")
        sys.exit(1)

    print(
        f"Sending deploy notification for {args.server} to {len(admin_ids)} admins..."
    )
    asyncio.run(send_deploy_notification(bot_token, admin_ids, args.server))
    print("Done!")


if __name__ == "__main__":
    main()
