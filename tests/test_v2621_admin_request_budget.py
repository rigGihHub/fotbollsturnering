from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_release_is_synchronized():
    package = (ROOT / "frontend-next" / "package.json").read_text(encoding="utf-8")
    layout = (ROOT / "frontend-next" / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")
    worker = (ROOT / "frontend-next" / "public" / "sw.js").read_text(encoding="utf-8")
    assert '"version": "2.6.52"' in package
    assert 'APP_VERSION = "2.6.52"' in layout
    assert 'cupnavi-next-v2652' in worker


def test_authenticated_workspace_reuses_authoritative_session():
    shell = (ROOT / "frontend-next" / "src" / "components" / "admin-auth-shell.tsx").read_text(encoding="utf-8")
    workspace = (ROOT / "frontend-next" / "src" / "components" / "admin-workspace.tsx").read_text(encoding="utf-8")
    assert "verifiedSession={verifiedSession}" in shell
    assert "if (verifiedSession)" in workspace


def test_heavy_admin_modules_only_mount_for_active_step():
    workspace = (ROOT / "frontend-next" / "src" / "components" / "admin-workspace.tsx").read_text(encoding="utf-8")
    for step, component in {
        "venues": "VenueAdmin",
        "rules": "RulesAdmin",
        "schedule": "ScheduleAdmin",
        "referees": "RefereeAdmin",
        "playoffs": "PlayoffAdmin",
    }.items():
        assert f'activeStep==="{step}" && token && cupId && <{component}' in workspace


def test_import_recovery_has_no_subsecond_polling():
    guard = (ROOT / "frontend-next" / "src" / "components" / "import-recovery-guard.tsx").read_text(encoding="utf-8")
    assert "setInterval" not in guard
    assert 'window.addEventListener("focus", sync)' in guard


def test_partial_cup_import_is_shown_as_paused_and_resumable():
    launcher = (ROOT / "frontend-next" / "src" / "components" / "cup-create-launcher-v6.tsx").read_text(encoding="utf-8")
    assert 'importFailure ? "is-paused"' in launcher
    assert '"Importen pausades"' in launcher
    assert '"Fortsätt importen"' in launcher
    assert 'onClick={() => goToCup(importFailure.cup)}' in launcher
    assert 'failed to fetch|networkerror|load failed' in launcher
    assert 'setImportFailure({ cup, stage, detail })' in launcher


def test_mutations_are_never_rejected_as_stale_cup_reads():
    coordinator = (ROOT / "frontend-next" / "src" / "lib" / "admin-request-coordinator.ts").read_text(encoding="utf-8")
    assert 'method === "GET" && cupId !== null && selectedCupId !== null' in coordinator
    assert coordinator.index('if (method !== "GET")') < coordinator.index('if (cupId !== null) cancelStaleReads(cupId)')


def test_publish_and_reporting_are_separate_focused_views():
    operations = (ROOT / "frontend-next" / "src" / "components" / "admin-operations.tsx").read_text(encoding="utf-8")
    panel = (ROOT / "frontend-next" / "src" / "components" / "publish-reporting-admin.tsx").read_text(encoding="utf-8")
    assert "mode={step}" in operations
    assert 'if(mode==="publish")setPublication' in panel
    assert 'className="publication-checklist__item is-blocking"' in panel
    assert 'className="admin-team-list"' not in panel
    playoff = (ROOT / "frontend-next" / "src" / "components" / "playoff-admin.tsx").read_text(encoding="utf-8")
    assert "PublishReportingAdmin" not in playoff
    assert "ImportAdmin" not in playoff
    assert "ExportPanel" not in playoff
    css = (ROOT / "frontend-next" / "src" / "app" / "admin-wow-v2622.css").read_text(encoding="utf-8")
    assert 'html[data-admin-step="publish"] .admin-operations-flow>.admin-flow-group' in css
    assert "grid-template-columns:30px minmax(0,1fr) auto!important" in css


def test_public_mobile_navigation_and_match_list_are_complete():
    public_view = (ROOT / "frontend-next" / "src" / "components" / "PublicCupView.tsx").read_text(encoding="utf-8")
    assert "orderedMatches.slice(0,18)" not in public_view
    assert 'type MatchView="upcoming"|"results"|"all"' in public_view
    assert 'openTab("playoff")' not in public_view  # rendered from the typed navigation tuple
    assert '["playoff","Slutspel","◆"]' in public_view
    assert 'openTab("info")' in public_view
    assert 'Cupinfo & karta' in public_view
    assert 'className="mobile-more-menu"' in public_view


def test_admin_navigation_has_work_phases():
    workspace = (ROOT / "frontend-next" / "src" / "components" / "admin-workspace.tsx").read_text(encoding="utf-8")
    for phase in ("SKAPA CUPEN", "VERKTYG & CUPDRIFT"):
        assert phase in workspace
    assert 'className="admin-nav-phase"' in workspace


def test_photo_import_hands_off_to_a_clear_admin_flow():
    launcher = (ROOT / "frontend-next" / "src" / "components" / "cup-create-launcher-v6.tsx").read_text(encoding="utf-8")
    workspace = (ROOT / "frontend-next" / "src" / "components" / "admin-workspace.tsx").read_text(encoding="utf-8")
    assert "IMPORT_WELCOME_KEY" in launcher
    assert "teams:teams.length" in launcher
    assert '>IMPORTEN ÄR KLAR<' in workspace
    assert "Börja med Cupinfo →" in workspace
    assert "Kontrollera schemat" in workspace
    assert "importWelcome" in workspace
