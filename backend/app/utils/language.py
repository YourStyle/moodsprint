"""Language/localization utilities."""

from flask import g, request

# Supported languages
SUPPORTED_LANGUAGES = ["ru", "en"]
DEFAULT_LANGUAGE = "ru"


def get_request_language() -> str:
    """Get language preference from current request.

    Priority:
    1. Query parameter `lang` (for testing)
    2. X-Language header (set by frontend)
    3. User's language_code from profile (if authenticated)
    4. Accept-Language header
    5. Default to Russian
    """
    # 1. Check query parameter
    lang = request.args.get("lang")
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # 2. Check X-Language header (preferred method from frontend)
    lang = request.headers.get("X-Language")
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # 3. Check user's language_code if authenticated
    if hasattr(g, "current_user") and g.current_user:
        user_lang = getattr(g.current_user, "language_code", None)
        if user_lang and user_lang in SUPPORTED_LANGUAGES:
            return user_lang

    # 4. Parse Accept-Language header
    accept_lang = request.headers.get("Accept-Language", "")
    for lang_code in accept_lang.split(","):
        # Extract language code (e.g., "en-US;q=0.9" -> "en")
        lang = lang_code.split(";")[0].strip().split("-")[0].lower()
        if lang in SUPPORTED_LANGUAGES:
            return lang

    # 5. Default
    return DEFAULT_LANGUAGE


def get_lang() -> str:
    """Shorthand for get_request_language()."""
    return get_request_language()


def is_english() -> bool:
    """Check if current request language is English."""
    return get_request_language() == "en"


def localize(ru_text: str, en_text: str | None = None) -> str:
    """Return localized text based on current request language.

    Args:
        ru_text: Russian text (default)
        en_text: English text (optional)

    Returns:
        Appropriate text based on language preference
    """
    if get_request_language() == "en" and en_text:
        return en_text
    return ru_text
