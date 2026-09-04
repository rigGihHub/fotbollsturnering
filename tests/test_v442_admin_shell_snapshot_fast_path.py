from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
PERF = (ROOT / "scripts" / "check_performance_contract.py").read_text(encoding="utf-8")


def test_release_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_admin_flow_counts_reuse_short_session_snapshots():
    assert '_cupnavi_admin_cache_flow_overview_' in APP
    assert '_cupnavi_admin_cache_flow_primary_' in APP
    assert '5.0,' in APP


def test_sidebar_rules_and_lifecycle_counts_are_cached():
    assert '_cupnavi_admin_cache_sidebar_rules_' in APP
    assert '_cupnavi_admin_cache_lifecycle_counts_' in APP
    assert 'lambda: fetch_lifecycle_match_counts(one_row, tid)' in APP


def test_local_writes_still_invalidate_admin_snapshots():
    run_start = APP.index('def run(sql, params=()):')
    run_block = APP[run_start:APP.index('\n\n\ndef public_core_snapshot', run_start)]
    assert '_clear_session_read_caches()' in run_block


def test_performance_contract_guards_admin_shell_snapshots():
    assert '_cupnavi_admin_cache_sidebar_rules_' in PERF
    assert '_cupnavi_admin_cache_lifecycle_counts_' in PERF
