from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "2026.09.08-550-OPTIONAL-REFEREE-FLOW"


def test_current_release_version_is_synchronized():
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    core = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert version == EXPECTED
    assert f'APP_BUILD_VERSION = "{EXPECTED}"' in app
    assert f'APP_VERSION = "{EXPECTED}"' in core


def test_referee_page_belongs_to_planning_step_not_publish_step():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"Domare": "Planer & tider"' in app
    assert 'Steg 4 · Planer & tider  /  Domare (valfritt)' in app
    assert 'Fortsätt till Schema →' in app


def test_missing_referees_do_not_enter_schedule_validation_warning_list():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    validation_start = app.index('def validate_schedule(')
    validation_end = app.index('def ', validation_start + 20)
    validation = app[validation_start:validation_end]
    assert 'warnings.append(f"Match {number} saknar domare.")' not in validation


def test_referee_readiness_is_informational_not_blocking():
    ux = (ROOT / "cupnavi_core" / "ux2.py").read_text(encoding="utf-8")
    assert '"level": "info"' in ux
    assert 'matcher saknar domare · valfritt före publicering' in ux
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'Det stoppar inte publicering; domare kan tillsättas senare.' in app
    assert '(missing_refs_n == 0, "Alla schemalagda matcher har domare")' not in app


def test_current_reporter_safety_contracts_remain_present():
    reporter = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
    for token in ("Sparar", "Sparat", "Dåligt nät", "_setup_scorers", "_setup_assists", "_setup_cards"):
        assert token in reporter
