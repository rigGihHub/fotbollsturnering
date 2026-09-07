from pathlib import Path

VERSION = "2026.09.07-519-BEGINNER-E2E-REGRESSION"
APP = Path("app.py").read_text(encoding="utf-8")
TEAM = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")
SHELL = Path("cupnavi_core/public_shell_view.py").read_text(encoding="utf-8")
STATS = Path("cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
PWA = Path("public_pwa/app.js").read_text(encoding="utf-8")
PWA_HTML = Path("public_pwa/index.html").read_text(encoding="utf-8")


def test_version_consistency():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in Path("cupnavi_core/version.py").read_text()


def test_my_teams_desktop_cards_and_latest_result_are_clean():
    assert "grid-template-columns:minmax(150px,.8fr)" in STYLE
    assert 'html.escape(source_label(_last[\'home_source\']))' in TEAM
    assert 'f"{row_value(_last' not in TEAM


def test_slogan_is_public_and_short():
    assert "Mer cup. Mindre kaos." in SHELL
    assert "cn-hero-slogan" in STYLE


def test_toplists_are_only_selectable_when_admin_enabled_them():
    assert '[tr("Tabeller")] + ([tr("Topplistor")] if _has_toplists else [])' in STATS
    assert 'stats_section == tr("Topplistor") and not _has_toplists' in STATS
    assert '["Tabeller"] + (["Topplistor"] if _admin_has_toplists else [])' in APP


def test_mobile_notification_beta_is_real_pwa_notification_flow():
    assert 'id="mobileNotify"' in PWA_HTML
    assert 'Notification.requestPermission()' in PWA
    assert 'registration.showNotification' in PWA
    assert '/notifications`' in PWA
    assert 'setInterval(()=>pollTeamNotifications(),45000)' in PWA
    assert 'Lagnotiser i mobilen · beta' in TEAM
