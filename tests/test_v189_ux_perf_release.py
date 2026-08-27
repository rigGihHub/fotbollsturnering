from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
REPO=(ROOT/"cupnavi_api/repository.py").read_text(encoding="utf-8")
MAIN=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")
R="2026.08.27-232-E2E-PERSISTENCE-FRESH-READ"

def test_test_tools_are_gated_to_test_environment():
    assert "_demo_environment_allowed = is_test_environment(tournament)" in APP
    assert "Testverktygen är avstängda i riktiga cuper." in APP
    assert "demo_allowed = (" in APP and "_demo_environment_allowed" in APP

def test_only_short_user_version_is_visible():
    assert "Version v.1.232" in APP
    assert 'st.sidebar.caption(f"CupNavi version {APP_VERSION}")' not in APP
    assert "KÖR VERSION" not in APP

def test_group_tables_have_batch_path():
    assert "def calculate_all_group_tables" in APP
    assert "tre queries i stället för 2×N queries" in APP

def test_public_api_removes_n_plus_one():
    assert "def standings_inputs" in REPO
    assert "Load every bracket and its matches in two queries" in REPO
    bracket_block=REPO[REPO.index("def public_brackets"):REPO.index("def public_snapshot")]
    assert 'WHERE bracket_id=?' not in bracket_block

def test_health_endpoint_checks_database():
    assert "database_probe()" in MAIN
    assert '"database_latency_ms"' in MAIN
    assert "response.status_code=503" in MAIN

def test_production_ui_does_not_render_test_controls():
    assert "if _demo_environment_allowed:" in APP
    assert "Duplicera cupen som Testkopia" in APP

def test_release_integrity_and_security_ci_exist():
    assert (ROOT/"scripts/generate_release_manifest.py").exists()
    security=(ROOT/".github/workflows/security.yml").read_text(encoding="utf-8")
    assert "pip-audit" in security
    assert "generate_release_manifest.py --check" in security
    assert (ROOT/".gitignore").exists()

def test_version():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
