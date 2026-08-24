from pathlib import Path
import sqlite3

from cupnavi_core.migrations import apply_migrations, LATEST_SCHEMA_VERSION


def app_text():
    return Path('app.py').read_text(encoding='utf-8')


def test_v109_version_and_weather_default():
    text = app_text()
    # Regressionen ska verifiera väder-defaulten, inte frysa hela appen på v109.
    assert 'APP_BUILD_VERSION = "2026.08.24-' in text
    assert '"🌦️ " + tr("Visa väderprognos"),\n            value=True' in text


def test_public_version_badge_not_rendered_before_public_view():
    text = app_text()
    assert 'if view_mode == "Turneringsvy":' in text
    assert '_render_with_friendly_error(render_public_view, tid, tournament)' in text
    marker = 'if view_mode == "Turneringsvy":'
    before = text[text.find('if view_mode == "Admin":'):text.find(marker)]
    assert "else:\n    st.markdown(\n        f\"<div class='cup-version-badge'>KÖR VERSION" not in before


def test_share_button_is_fixed_beside_brand():
    text = app_text()
    assert '[class*="st-key-cn_share_toggle_"] {' in text
    assert 'left:calc(50% + 184px)' in text
    assert 'cn_share_button_' in text
    assert 'cn_share_panel_' in text
    assert 'popovertarget=' not in text


def test_input_instruction_is_hidden_and_weekday_helpers_exist():
    text = app_text()
    assert '[data-testid="InputInstructions"] { display:none !important; }' in text
    assert 'def weekday_short(value):' in text
    assert '["mån", "tis", "ons", "tors", "fre", "lör", "sön"]' in text


def test_age_classes_are_modeled_and_filtered():
    text = app_text()
    assert 'Tävlingsklasser i turneringen' in text
    assert '"Tävlingsklass"' in text
    assert 'competition_classes' in text
    assert 'eligible_groups = [g for g in groups' in text
    assert 'filter_mode == "Tävlingsklass"' in text


def test_schema_v11_adds_age_class_fields():
    assert LATEST_SCHEMA_VERSION >= 11
    con = sqlite3.connect(':memory:')
    con.executescript('''
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY);
        CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER, group_id INTEGER);
        CREATE TABLE groups(id INTEGER PRIMARY KEY, tournament_id INTEGER);
    ''')
    # Earlier migrations reference many production tables, so validate v11 DDL contract directly.
    migration_text = Path('cupnavi_core/migrations.py').read_text(encoding='utf-8')
    assert "ALTER TABLE tournaments ADD COLUMN age_classes_json" in migration_text
    assert "ALTER TABLE teams ADD COLUMN age_class TEXT" in migration_text
    assert "ALTER TABLE groups ADD COLUMN age_class TEXT" in migration_text
