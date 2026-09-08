from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')


def _render_public_view_block():
    start = APP.index('@st.fragment\ndef render_public_view')
    end = APP.index('\ndef _reporter_save_quick_result', start)
    return APP[start:end]


def test_v536_version_exposed():
    assert '2026.09.08-536-ADAPTIVE-PUBLIC-RERUN-CACHE' in APP


def test_v536_public_cache_epoch_is_adaptive():
    block = _render_public_view_block()
    assert '_cache_epoch_seconds = 3' in block
    assert '_cache_epoch_seconds = 12' in block
    assert '_cache_epoch_seconds = 30' in block
    assert 'public_cache_epoch = int(time.monotonic() // _cache_epoch_seconds)' in block


def test_v536_cupday_keeps_three_second_freshness():
    block = _render_public_view_block()
    assert 'if _start_date <= _today <= _end_date:' in block
    assert '_cache_epoch_seconds = 3' in block
