"""OpenAI client factory with proxy support."""

from flask import current_app

try:
    import httpx
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def get_openai_client():
    """
    Create OpenAI client with optional proxy support.

    Returns OpenAI client or None if not available/configured.
    """
    if not OPENAI_AVAILABLE:
        return None

    api_key = current_app.config.get("OPENAI_API_KEY")
    if not api_key:
        return None

    proxy_url = current_app.config.get("OPENAI_PROXY")

    if proxy_url:
        # Create httpx client with proxy
        http_client = httpx.Client(proxy=proxy_url)
        current_app.logger.info("OpenAI client initialized with proxy")
        return OpenAI(api_key=api_key, http_client=http_client)
    else:
        return OpenAI(api_key=api_key)
