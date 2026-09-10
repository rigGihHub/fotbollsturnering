APP_VERSION = "2026.09.10-621-CI-MIGRATION-GATE"


def release_ui_label(version: str | None = None) -> str:
    """Return the UI-safe release label used by Streamlit and the public API."""
    return version or APP_VERSION
