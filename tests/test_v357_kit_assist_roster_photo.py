from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
AI = (ROOT / "cupnavi_core" / "ai_kit_suggestion.py").read_text(encoding="utf-8")


def test_beginner_color_selector_uses_presets_and_custom_fallback():
    assert "KIT_COLOR_PRESETS" in APP
    assert "🎨 Egen färg…" in APP
    assert "def kit_color_selector(" in APP
    assert 'kit_color_selector("Hemma – färg 1"' in APP
    assert 'kit_color_selector("Borta – färg 1"' in APP


def test_team_name_can_trigger_cautious_ai_kit_suggestion():
    assert "Föreslå hemma- och bortaställ från lagnamnet" in APP
    assert "suggest_team_kit" in APP
    assert '"found": found' in AI
    assert 'confidence in {"medium", "high"}' in AI
    assert "Gissa inte" in AI


def test_photo_roster_import_is_discoverable_from_team_registration():
    assert "📷 Importera laguppställning från foto" in APP
    assert "Öppna fotoimport för valt lag" in APP
    assert 'st.session_state[admin_page_key] = "Trupper"' in APP
    assert "AI-import från foto eller skärmdump" in APP


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"' in APP
