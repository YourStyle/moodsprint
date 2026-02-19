"""Async AI usage tracking for the bot service.

Writes to the same ai_usage_log table as the backend's tracker,
but uses the bot's async SQLAlchemy session.
"""

import logging
import time

from database import get_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (input/output) — keep in sync with backend/app/utils/ai_tracker.py
MODEL_PRICING = {
    "gpt-5-mini": {"input": 0.40, "output": 1.60},
    "gpt-5-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "whisper-1": {"input": 0.006, "output": 0.0},
}


def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 3.0})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


async def track_ai_usage(
    user_id: int | None,
    model: str,
    response,
    latency_ms: int,
    endpoint: str,
):
    """Log an AI API call to the database (async)."""
    try:
        usage = getattr(response, "usage", None)
        if not usage:
            return

        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = prompt_tokens + completion_tokens
        cost = _calculate_cost(model, prompt_tokens, completion_tokens)

        async with get_session() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO ai_usage_log
                        (user_id, service_name, model, prompt_tokens, completion_tokens,
                         total_tokens, estimated_cost_usd, latency_ms, endpoint)
                    VALUES
                        (:user_id, :service_name, :model, :prompt_tokens, :completion_tokens,
                         :total_tokens, :cost, :latency_ms, :endpoint)
                """
                ),
                {
                    "user_id": user_id,
                    "service_name": model,
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost,
                    "latency_ms": latency_ms,
                    "endpoint": endpoint,
                },
            )
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to track AI usage: {e}")


async def tracked_openai_call(client, user_id: int | None, endpoint: str, **kwargs):
    """Wrap an OpenAI chat completion call with usage tracking (async).

    The OpenAI call itself is synchronous, but the DB logging is async.
    """
    model = kwargs.get("model", "unknown")

    start = time.time()
    response = client.chat.completions.create(**kwargs)
    latency_ms = int((time.time() - start) * 1000)

    await track_ai_usage(
        user_id=user_id,
        model=model,
        response=response,
        latency_ms=latency_ms,
        endpoint=endpoint,
    )

    return response
