APP_VERSION = "2026.09.10-611-SIGNATURE-PUBLIC-STAGE"


def release_ui_label(version: str) -> str:
    """Return the human-readable release label used in the CupNavi UI."""
    return f"CupNavi {version}"
