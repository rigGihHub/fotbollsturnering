from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
MATCHES = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")


def test_release_version_270():
    assert VERSION == "2026.08.31-342-POST-SIMPLIFICATION-AUDIT"


def test_public_match_paging_helper_batches_without_framework_state():
    from cupnavi_core.public_match_paging import (
        PUBLIC_MATCH_INITIAL_BATCH,
        next_visible_count,
        visible_match_batch,
    )

    rows = list(range(31))
    first, count = visible_match_batch(rows)
    assert PUBLIC_MATCH_INITIAL_BATCH == 12
    assert first == list(range(12))
    assert count == 12
    assert next_visible_count(count, len(rows)) == 24
    final, final_count = visible_match_batch(rows, 99)
    assert final == rows
    assert final_count == 31


def test_public_view_only_queries_events_for_rendered_batch():
    start = MATCHES.index('match_ids_signature = tuple(')
    end = MATCHES.index('stage_timings["events_ms"]', start)
    block = MATCHES[start:end]
    assert 'visible_match_batch(' in block
    assert 'visible_played_match_ids = [' in block
    assert 'for match_row in match_list' in block
    assert 'for match_row in all_filtered_matches' not in block[block.index('visible_played_match_ids = ['):]


def test_public_view_has_incremental_load_more_not_show_all():
    start = MATCHES.index('match_ids_signature = tuple(')
    end = MATCHES.index('stage_timings["cards_weather_ms"]', start)
    block = MATCHES[start:end]
    assert 'Visa {next_batch_size} fler matcher' in block
    assert 'next_visible_count(' in block
    assert 'Visa alla matcher' not in block
    assert 'PUBLIC_MATCH_BATCH_SIZE' in block
