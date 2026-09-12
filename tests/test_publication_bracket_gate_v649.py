from pathlib import Path

from cupnavi_core.admin_publication import build_publish_blockers, publication_problem_destination

ROOT = Path(__file__).resolve().parents[1]


def test_bracket_errors_are_real_publication_blockers():
    blockers = build_publish_blockers(
        playoff_model_confirmed=True,
        scheduled_matches=12,
        schedule_dirty=False,
        schedule_errors=(),
        bracket_errors=("Finalen saknar en giltig deltagare", "Cykel i semifinalerna"),
    )
    assert blockers == ["2 fel i slutspelsträdet måste åtgärdas."]
    assert publication_problem_destination(blockers[0]) == ("Slutspel", "Öppna Slutspel")


def test_playoff_admin_surfaces_structural_readiness():
    repo = (ROOT / "cupnavi_api/playoff_admin_repository.py").read_text(encoding="utf-8")
    ui = (ROOT / "frontend-next/src/components/playoff-admin.tsx").read_text(encoding="utf-8")
    assert '"bracket_validation": validation' in repo
    assert '"bracket_ready": bool(validation.get("ready", True))' in repo
    assert "TRÄDET ÄR KONTROLLERAT" in ui
    assert "Slutspelsträdet måste rättas före publicering" in ui


def test_publication_payload_reuses_same_bracket_validator():
    source = (ROOT / "cupnavi_api/publish_reporting_repository.py").read_text(encoding="utf-8")
    assert "validate_bracket_sources" in source
    assert '"bracket_validation": bracket_analysis' in source
    assert "bracket_errors=bracket_errors" in source
