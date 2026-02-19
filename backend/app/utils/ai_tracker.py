"""AI usage tracking utility for monitoring OpenAI API costs."""

import logging
import time

from app import db
from app.models.ai_usage_log import AIUsageLog

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (input/output) — update when OpenAI changes prices
MODEL_PRICING = {
    "gpt-5-mini": {"input": 0.40, "output": 1.60},
    "gpt-5-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "whisper-1": {"input": 0.006, "output": 0.0},  # per minute, approximated
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated cost in USD based on model and token counts."""
    pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 3.0})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def track_ai_usage(
    user_id,
    service_name: str,
    model: str,
    response,
    latency_ms: int,
    endpoint: str,
):
    """Log an AI API call to the database."""
    try:
        usage = getattr(response, "usage", None)
        if not usage:
            return

        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = prompt_tokens + completion_tokens

        cost = calculate_cost(model, prompt_tokens, completion_tokens)

        log_entry = AIUsageLog(
            user_id=user_id,
            service_name=service_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
            latency_ms=latency_ms,
            endpoint=endpoint,
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        logger.warning(f"Failed to track AI usage: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def tracked_openai_call(client, user_id, endpoint: str, **kwargs):
    """Wrap an OpenAI chat completion call with usage tracking.

    Usage:
        response = tracked_openai_call(
            client, user_id=123, endpoint="decompose_task",
            model="gpt-5-mini", messages=[...], max_tokens=1000
        )
    """
    model = kwargs.get("model", "unknown")

    start = time.time()
    response = client.chat.completions.create(**kwargs)
    latency_ms = int((time.time() - start) * 1000)

    track_ai_usage(
        user_id=user_id,
        service_name=model,
        model=model,
        response=response,
        latency_ms=latency_ms,
        endpoint=endpoint,
    )

    return response
