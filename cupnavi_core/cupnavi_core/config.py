"""Gemensamma tekniska konstanter för CupNavi."""

import os

APP_NAME = "CupNavi"
OFFICIAL_PUBLIC_BASE_URL = "https://cup-navi.com"
LEGACY_STREAMLIT_BASE_URL = "https://cupnavi.streamlit.app"
PUBLIC_BASE_URL = os.getenv("CUPNAVI_PUBLIC_URL", OFFICIAL_PUBLIC_BASE_URL).rstrip("/")
BACKUP_FILE_SUFFIX = "_cupnavi_backup.json"
MAX_BACKUP_ROWS_PER_TABLE = 250_000
