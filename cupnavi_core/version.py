APP_VERSION = "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"


def release_ui_label(version: str) -> str:
    """Return a compact human-facing release label without exposing the build slug."""
    parts = str(version or "").split("-", 2)
    serial = parts[1] if len(parts) >= 2 and parts[1].isdigit() else ""
    return f"Version v1.{serial}" if serial else f"Version {version}"
