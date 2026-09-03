from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text()
VERSION = (ROOT / 'VERSION.txt').read_text().strip()


def test_v323_version():
    assert VERSION == '2026.09.03-427-TRAVEL-RULES-FLOW'


def test_schema_fast_path_is_one_execute_statement():
    block = APP[APP.index('def _schema_fast_path_ready'):APP.index('@st.cache_resource', APP.index('def _schema_fast_path_ready'))]
    assert block.count('con.execute(') == 1
    assert "pragma_table_info('tournaments')" in block
    assert "pragma_table_info('teams')" in block
    assert "pragma_table_info('notification_subscriptions')" in block
    assert "pragma_table_info('competition_classes')" in block
    assert 'LATEST_SCHEMA_VERSION' in block


def test_source_fingerprint_does_not_scan_core_tree():
    block = APP[APP.index('def _compute_source_fingerprint'):APP.index('def _refresh_cupnavi_imports_if_sources_changed')]
    assert 'rglob(' not in block
    assert 'VERSION.txt' in block
    assert '(root / "app.py").stat()' in block


def test_public_fragment_has_bounded_three_second_cache_epoch():
    block = APP[APP.index('@st.fragment\ndef render_public_view'):APP.index('def _reporter_save_quick_result')]
    assert 'time.monotonic() // 3' in block
    assert '_clear_render_query_cache()' in block
    assert '_cupnavi_public_cache_epoch_' in block
