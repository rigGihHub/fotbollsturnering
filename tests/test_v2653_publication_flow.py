from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "frontend-next/src/components/admin-auth-shell.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
OPERATIONS = (ROOT / "frontend-next/src/components/admin-operations.tsx").read_text(encoding="utf-8")
PUBLISH = (ROOT / "frontend-next/src/components/publish-reporting-admin.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend-next/src/app/publication-flow-v2653.css").read_text(encoding="utf-8")


def test_heavy_operations_render_inside_the_workspace_grid():
    assert "<AdminWorkspace" in SHELL and "<AdminOperations/>" in SHELL
    assert "{children}" in WORKSPACE
    assert '.admin-workspace>#overview' in CSS
    assert "grid-column:2" in CSS


def test_publication_step_is_not_hidden_by_legacy_nth_child_rules():
    assert 'html[data-admin-step="publish"] .admin-operations-flow>.admin-flow-group' in CSS
    assert "display:block!important" in CSS


def test_final_step_explains_the_three_actions():
    assert "Kontrollera sammanfattningen" in PUBLISH
    assert "Förhandsgranska cupvyn" in PUBLISH
    assert "Publicera cupen" in PUBLISH
    assert "publication-console--loading" in PUBLISH


def test_preview_uses_the_active_cups_public_slug():
    assert "publicSlug={activeCup?.public_slug}" in OPERATIONS
    assert 'target="_blank"' in PUBLISH
