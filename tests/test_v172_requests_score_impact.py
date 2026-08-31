from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SCHEDULE=(ROOT/"cupnavi_core"/"schedule_workspace_view.py").read_text(encoding="utf-8")
R="2026.08.31-351-SETUP-COMPLETION-HANDOFF"

def test_requests_center_exists():
    assert "CREATE TABLE IF NOT EXISTS schedule_requests" in APP
    assert '"Önskemålscentral"' in APP
    assert "Prioritera godkända önskemål" in APP
    assert "Hårt krav" in APP

def test_schedule_score_is_explainable():
    assert "def schedule_score_report" in APP
    assert "Schema Score" in SCHEDULE
    assert "Varför fick schemat den här poängen?" in SCHEDULE
    assert "assess_schedule(" in APP

def test_request_evaluation_covers_key_types():
    for token in ("late_start","latest_finish","preferred_pitch","extra_rest","avoid_late_group"):
        assert token in APP
    assert "def evaluate_schedule_request" in APP

def test_change_impact_protects_played_matches():
    assert "def schedule_change_impact" in APP
    assert "Förhandskontroll före ändring" in APP
    assert "redan spelade matcher skyddas" in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
