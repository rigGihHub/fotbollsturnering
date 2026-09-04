from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "cupnavi_core" / "public_statistics_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v318_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_toplists_filter_zero_aggregate_rows_in_sql():
    block = SOURCE[SOURCE.index('if stats_section == tr("Topplistor") and _has_toplists:'):SOURCE.index('if stats_section == tr("Slutspel")')]
    assert "relevant_having" in block
    assert "HAVING {having_sql}" in block
    assert "SUM(COALESCE(s.goals,0)) > 0" in block
    assert "SUM(COALESCE(s.assists,0)) > 0" in block
    assert "SUM(COALESCE(s.yellow_cards,0)) > 0 OR SUM(COALESCE(s.red_cards,0)) > 0" in block


def test_toplists_normalize_aggregates_once_before_sorting():
    block = SOURCE[SOURCE.index('if stats_section == tr("Topplistor") and _has_toplists:'):SOURCE.index('if stats_section == tr("Slutspel")')]
    assert "normalized_rows = [" in block
    assert '"goals": int(r["goals"] or 0)' in block
    assert '"name_sort": str(r["player_name"] or "").lower()' in block
    assert 'int(r["yellow_cards"] or 0) + int(r["red_cards"] or 0)' not in block
