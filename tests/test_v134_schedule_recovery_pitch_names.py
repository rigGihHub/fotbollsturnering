from pathlib import Path

APP=Path("app.py").read_text(encoding="utf-8")
MIG=Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")

def test_named_pitches_are_schema_backed_and_autosaved():
    assert "LATEST_SCHEMA_VERSION = 24" in MIG
    assert "CREATE TABLE IF NOT EXISTS pitches" in MIG
    assert "ensure_v18_pitch_names_schema_compat" in MIG
    assert "def save_pitch_name" in APP
    assert "Namnge planer/spelytor" in APP
    assert "Planens nummer behålls bara som internt ID" in APP

def test_schedule_failures_offer_ranked_one_click_recovery():
    assert "def render_schedule_recovery_actions" in APP
    assert "CupNavi föreslår en lösning" in APP
    assert "Släpp önskemål om senare första match" in APP
    assert "mjuk prioritering och blockerar inte i sig schemaläggningen" in APP
    assert "Förläng sista dagens plantider" in APP
    assert "Lägg till en extra plan/spelyta" in APP
    assert 'st.session_state["schedule_recovery"] = _schedule_recovery_context' in APP

def test_schedule_warning_uses_current_pitch_availability_language():
    assert "planernas tillgängliga tider" in APP
    assert "Alla matcher fick inte plats inom cupens datumintervall och sista plantid" not in APP
