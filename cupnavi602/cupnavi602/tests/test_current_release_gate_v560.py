from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = "2026.09.08-560-MARKETING-HOME"


def test_release_files_are_current():
    assert VERSION in APP
    assert (ROOT / "VERSION.txt").read_text().strip() == VERSION
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text()


def test_bare_public_root_is_marketing_home():
    assert "def render_cupnavi_marketing_landing():" in APP
    assert 'if view_mode == "Turneringsvy" and not cup_query_text:' in APP
    assert "render_cupnavi_marketing_landing()" in APP
    assert "Cupen ska vara rolig." in APP
    assert "Skapa eller administrera en cup" in APP


def test_direct_cup_link_bypasses_marketing_home():
    marker = 'if view_mode == "Turneringsvy" and not cup_query_text:'
    assert marker in APP
    assert 'cup_query = st.query_params.get("cup")' in APP
    assert "Direct ?cup= links bypass this page completely" in APP
    assert "public_cup_url(int(row[\"id\"]))" in APP


def test_marketing_home_can_surface_live_and_upcoming_cups():
    assert "public_rows = public_tournament_list_snapshot()" in APP
    assert 'in {"live", "published"}' in APP
    assert "Pågående och kommande cuper" in APP
    assert 'status_text = "🔴 Pågår nu" if status == "live" else "🗓️ Kommande"' in APP


def test_v559_environment_and_public_safety_is_retained():
    assert '"Arbetsmiljö"' in APP
    assert '"🧪 Testmiljö" if value == "test" else "🟢 Skarp miljö"' in APP
    assert "AND COALESCE(t.environment_type,'production')=?" in APP
    assert "is_published=1 AND COALESCE(environment_type,'production')='production'" in APP
