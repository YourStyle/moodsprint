"""Voice message processing service using OpenAI Whisper and GPT."""

import json
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta

import httpx
from config import config
from openai import OpenAI


@dataclass
class TaskFromVoice:
    """Parsed task from voice message."""

    title: str
    due_date: str  # YYYY-MM-DD format
    scheduled_at: str | None = None  # ISO format with time
    has_explicit_date: bool = False


def _get_openai_client() -> OpenAI:
    """Get OpenAI client with optional proxy."""
    proxy_url = config.OPENAI_PROXY

    if proxy_url:
        http_client = httpx.Client(
            mounts={
                "https://": httpx.HTTPTransport(proxy=proxy_url),
                "http://": httpx.HTTPTransport(proxy=proxy_url),
            },
            timeout=60.0,
        )
        return OpenAI(api_key=config.OPENAI_API_KEY, http_client=http_client)

    return OpenAI(api_key=config.OPENAI_API_KEY)


async def transcribe_voice(voice_file_path: str) -> str | None:
    """
    Transcribe voice message using OpenAI Whisper.

    Args:
        voice_file_path: Path to the voice file (ogg/oga format)

    Returns:
        Transcribed text or None if failed
    """
    try:
        client = _get_openai_client()

        with open(voice_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru",  # Will auto-detect if wrong
            )

        return response.text.strip() if response.text else None
    except Exception as e:
        print(f"Error transcribing voice: {e}")
        return None


async def extract_task_from_text(
    text: str, lang: str = "ru", user_id: int | None = None
) -> TaskFromVoice | None:
    """
    Extract task information from transcribed text using GPT.

    Args:
        text: Transcribed text
        lang: User's language

    Returns:
        TaskFromVoice with extracted info or None if failed
    """
    try:
        client = _get_openai_client()

        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        weekday = today.weekday()  # 0 = Monday

        # Map weekdays for Russian
        weekday_names_ru = [
            "понедельник",
            "вторник",
            "среда",
            "четверг",
            "пятница",
            "суббота",
            "воскресенье",
        ]
        weekday_names_en = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (today + timedelta(days=2)).strftime("%Y-%m-%d")
        week_later = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        weekday_ru = weekday_names_ru[weekday]
        weekday_en = weekday_names_en[weekday]

        system_prompt = (
            "You are a task extraction assistant. "
            "Extract task information from voice message text.\n\n"
            f"Current date: {today_str} ({weekday_ru}/{weekday_en})\n\n"
            "Rules for date extraction:\n"
            f'- "сегодня" / "today" = {today_str}\n'
            f'- "завтра" / "tomorrow" = {tomorrow_str}\n'
            f'- "послезавтра" / "day after tomorrow" = {day_after}\n'
            f'- "через неделю" / "in a week" = {week_later}\n'
            "- Weekday names = next occurrence of that day\n"
            '- "в 15:00" / "at 3pm" = scheduled time on that date\n'
            "- If no date mentioned, set has_explicit_date to false "
            "and use today's date\n\n"
            "Return JSON with:\n"
            "- title: string - the task title (clean, no date/time)\n"
            "- due_date: string - date in YYYY-MM-DD format\n"
            "- scheduled_at: string | null - ISO datetime if specific "
            'time mentioned (e.g. "2024-01-15T15:00:00")\n'
            "- has_explicit_date: boolean - true if date/time was "
            "explicitly mentioned\n\n"
            "Examples:\n"
            '- "Позвонить маме завтра" -> title: "Позвонить маме", '
            "due_date: tomorrow, has_explicit_date: true\n"
            '- "Купить молоко" -> title: "Купить молоко", '
            "due_date: today, has_explicit_date: false\n"
            '- "Встреча с клиентом в среду в 14:00" -> '
            'title: "Встреча с клиентом", '
            "due_date: next Wednesday, has_explicit_date: true\n"
            '- "Отправить отчёт в пятницу" -> '
            'title: "Отправить отчёт", '
            "due_date: next Friday, has_explicit_date: true\n\n"
            "Return ONLY valid JSON, no markdown or explanations."
        )

        from services.ai_tracker import tracked_openai_call

        response = await tracked_openai_call(
            client,
            user_id=user_id,
            endpoint="extract_task_from_voice",
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
        )

        result_text = response.choices[0].message.content.strip()

        # Clean JSON if wrapped in markdown
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            result_text = result_text.rsplit("```", 1)[0]

        data = json.loads(result_text)

        return TaskFromVoice(
            title=data.get("title", text),
            due_date=data.get("due_date", today_str),
            scheduled_at=data.get("scheduled_at"),
            has_explicit_date=data.get("has_explicit_date", False),
        )

    except Exception as e:
        print(f"Error extracting task from text: {e}")
        # Fallback: return the text as-is with today's date
        return TaskFromVoice(
            title=text,
            due_date=date.today().strftime("%Y-%m-%d"),
            scheduled_at=None,
            has_explicit_date=False,
        )


async def download_voice_file(bot, file_id: str) -> str | None:
    """
    Download voice file from Telegram.

    Args:
        bot: Telegram bot instance
        file_id: Telegram file ID

    Returns:
        Path to downloaded file or None if failed
    """
    try:
        file = await bot.get_file(file_id)
        file_path = file.file_path

        # Create temp file with correct extension
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await bot.download_file(file_path, tmp.name)
            return tmp.name

    except Exception as e:
        print(f"Error downloading voice file: {e}")
        return None


async def process_voice_message(
    bot, file_id: str, lang: str = "ru"
) -> tuple[str | None, TaskFromVoice | None]:
    """
    Full pipeline: download, transcribe, extract task.

    Args:
        bot: Telegram bot instance
        file_id: Voice message file ID
        lang: User's language

    Returns:
        Tuple of (transcribed_text, parsed_task) - either can be None on failure
    """
    # Download voice file
    voice_path = await download_voice_file(bot, file_id)
    if not voice_path:
        return None, None

    try:
        # Transcribe
        transcribed_text = await transcribe_voice(voice_path)
        if not transcribed_text:
            return None, None

        # Extract task info
        task_info = await extract_task_from_text(transcribed_text, lang)

        return transcribed_text, task_info

    finally:
        # Clean up temp file
        import os

        try:
            os.unlink(voice_path)
        except Exception:
            pass
