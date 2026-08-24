from pathlib import Path

def test_schema_contains_sponsors_and_functionaries():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS sponsors" in text
    assert "CREATE TABLE IF NOT EXISTS functionaries" in text

def test_migration_version_is_at_least_three():
    text = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = 5" in text
    assert '"sponsors_and_functionaries"' in text

def test_runtime_dependencies_cover_new_features():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()
    assert "streamlit-sortables" in requirements
    assert "qrcode[pil]" in requirements
    assert "openpyxl" in requirements
