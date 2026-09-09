"""Internationalization primitives kept independent from Streamlit."""
from __future__ import annotations
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SUPPORTED_LOCALES = {
    "sv-SE": {"language": "sv", "date_order": "YMD", "clock": "24h", "week_start": 1},
    "en-GB": {"language": "en", "date_order": "DMY", "clock": "24h", "week_start": 1},
    "en-US": {"language": "en", "date_order": "MDY", "clock": "12h", "week_start": 7},
}
DEFAULT_LOCALE = "sv-SE"
DEFAULT_TIMEZONE = "Europe/Stockholm"


def normalize_locale(value: str | None) -> str:
    value = str(value or DEFAULT_LOCALE).strip()
    return value if value in SUPPORTED_LOCALES else DEFAULT_LOCALE


def language_for_locale(value: str | None) -> str:
    return str(SUPPORTED_LOCALES[normalize_locale(value)]["language"])


def valid_timezone(value: str | None) -> str:
    candidate = str(value or DEFAULT_TIMEZONE).strip()
    try:
        ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return DEFAULT_TIMEZONE
    return candidate

RTL_LANGUAGES = {"ar", "he", "fa", "ur"}


def text_direction(locale_or_language: str | None) -> str:
    """Return document direction for current/future locales."""
    raw = str(locale_or_language or "").strip()
    language = raw.split("-", 1)[0].lower()
    if raw in SUPPORTED_LOCALES:
        language = str(SUPPORTED_LOCALES[raw]["language"]).lower()
    return "rtl" if language in RTL_LANGUAGES else "ltr"
