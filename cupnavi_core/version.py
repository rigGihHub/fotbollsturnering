import re

APP_VERSION = "2026.09.08-553-REFEREE-MISC-SMART-IMPORT"


def release_ui_label(build_version: str = APP_VERSION) -> str:
    """Return the compact user-facing version label derived from the release serial."""
    match = re.search(r"-(\d+)(?:-|$)", str(build_version or ""))
    serial = match.group(1) if match else str(build_version or "?")
    return f"Version v1.{serial}"
