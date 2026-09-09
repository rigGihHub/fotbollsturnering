from pathlib import Path

APP=Path("app.py").read_text(encoding="utf-8")
MIG=Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
SETUP=Path("cupnavi_core/initial_setup_view.py").read_text(encoding="utf-8")
RECOVERY=Path("cupnavi_core/schedule_recovery_view.py").read_text(encoding="utf-8")

def test_named_pitches_are_schema_backed_and_autosaved():
    assert "LATEST_SCHEMA_VERSION = " in MIG
    assert "CREATE TABLE IF NOT EXISTS pitches" in MIG
    assert "ensure_v18_pitch_names_schema_compat" in MIG
    assert "def save_pitch_name" in APP
    assert "Namnge planer/spelytor" in SETUP
    assert "Planens nummer behålls bara som internt ID" in SETUP

def test_schedule_failures_offer_ranked_one_click_recovery():
    assert "def render_schedule_recovery_actions" in APP
    assert "CupNavi föreslår en lösning" in RECOVERY
    assert "Släpp önskemål om senare första match" in RECOVERY
    assert "mjuk prioritering och blockerar inte i sig schemaläggningen" in RECOVERY
    assert "Förläng sista dagens plantider" in RECOVERY
    assert "Lägg till en extra plan/spelyta" in RECOVERY
    assert 'st.session_state["schedule_recovery"] = _schedule_recovery_context' in APP

def test_schedule_warning_uses_current_pitch_availability_language():
    assert "planernas tillgängliga tider" in APP
    assert "Alla matcher fick inte plats inom cupens datumintervall och sista plantid" not in APP
