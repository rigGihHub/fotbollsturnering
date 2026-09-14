from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
FLOW = (ROOT / "frontend-next/src/components/admin-step-flow.tsx").read_text(encoding="utf-8")
API = (ROOT / "cupnavi_api/main.py").read_text(encoding="utf-8")
REPOSITORY = (ROOT / "cupnavi_api/admin_repository.py").read_text(encoding="utf-8")
PUBLIC_REPOSITORY = (ROOT / "cupnavi_api/repository.py").read_text(encoding="utf-8")
PREVIEW = (ROOT / "frontend-next/src/components/public-cup-preview.tsx").read_text(encoding="utf-8")
MODE_SWITCH = (ROOT / "frontend-next/src/components/ViewModeSwitch.tsx").read_text(encoding="utf-8")


def test_every_admin_step_has_concrete_guidance():
    for step in (
        "overview", "cupinfo", "teams", "groups", "venues", "rules", "schedule",
        "referees", "playoffs", "publish", "reporting", "import", "export",
    ):
        assert f"{step}:{{goal:" in FLOW
    assert "MÅL" in FLOW
    assert "GÖR NU" in FLOW
    assert "KLAR NÄR" in FLOW


def test_next_admin_exposes_evidence_based_kit_search():
    assert '/teams/kit-search' in API
    assert "suggest_team_kit(" in API
    assert "Sök tröjfärger och mönster" in WORKSPACE
    assert "Vilken klubb är rätt?" in WORKSPACE
    assert "Visa källor" in WORKSPACE
    assert "Använd verifierade uppgifter" in WORKSPACE


def test_kit_patterns_and_second_colors_are_persisted():
    for field in ("home_pattern", "home_color_2", "away_pattern", "away_color_2"):
        assert field in REPOSITORY
        assert field in WORKSPACE
    assert "ensure_team_kit_schema" in REPOSITORY


def test_empty_draft_uses_authenticated_preview_instead_of_public_api():
    assert "include_unpublished=True" in API
    assert '/preview' in API
    assert "cup.teams" not in PREVIEW
    assert "data.standings||[]" in PREVIEW
    assert "?preview=1&cup=" in MODE_SWITCH
    assert "include_unpublished=False" in PUBLIC_REPOSITORY
