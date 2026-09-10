APP_VERSION = "2026.09.10-615-NEXT-VISUAL-RUNTIME-HARDENING"


def release_ui_label(version: str | None = None) -> str:
    value = version or APP_VERSION
    return value
