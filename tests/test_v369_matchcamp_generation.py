from pathlib import Path
import sqlite3
import importlib.util
import sys

from cupnavi_core.matchcamp_pairings import (
    balanced_matchcamp_pairings,
    complete_matchcamp_pairings,
)

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
MIGRATIONS = (ROOT / "cupnavi_core" / "migrations.py").read_text(encoding="utf-8")


def _degree_map(pairs):
    counts = {}
    for a, b in pairs:
        counts[a] = counts.get(a, 0) + 1
        counts[b] = counts.get(b, 0) + 1
    return counts


def test_even_group_gets_exact_target_without_repeats():
    pairs = balanced_matchcamp_pairings([1,2,3,4,5,6], 3)
    counts = _degree_map(pairs)
    assert set(counts.values()) == {3}
    assert len({tuple(sorted(p)) for p in pairs}) == len(pairs)


def test_odd_group_is_as_balanced_as_possible_without_repeats():
    pairs = balanced_matchcamp_pairings([1,2,3,4,5], 3)
    counts = _degree_map(pairs)
    values = [counts.get(team, 0) for team in [1,2,3,4,5]]
    assert max(values) - min(values) <= 1
    assert len({tuple(sorted(p)) for p in pairs}) == len(pairs)


def test_target_is_capped_at_unique_opponents():
    pairs = balanced_matchcamp_pairings([1,2,3,4], 10)
    assert len(pairs) == 6
    assert set(_degree_map(pairs).values()) == {3}


def test_completion_preserves_existing_and_adds_only_unique_pairs():
    existing = {(1,2)}
    added = complete_matchcamp_pairings([1,2,3,4], existing, 2)
    all_pairs = {tuple(sorted(p)) for p in added} | existing
    assert (1,2) in all_pairs
    assert len(all_pairs) == len(added) + 1
    counts = _degree_map(list(all_pairs))
    assert max(counts.values()) <= 2


def test_setup_exposes_matchcamp_target_only_inside_matchcamp_branch():
    assert 'if _is_matchcamp:' in SETUP
    assert '"Mål för matcher per lag"' in SETUP
    assert '"matchcamp_matches_per_team"' in SETUP
    assert "returmöten undviks" in SETUP


def test_app_uses_arrangement_aware_generation_and_preserves_tournament_round_robin():
    block = APP[APP.index("def create_all_group_matches"):APP.index("def create_bracket")]
    assert "complete_matchcamp_pairings" in block
    assert "if is_matchcamp:" in block
    assert "Tournament keeps the established full single round-robin behavior." in block
    assert "if not is_matchcamp:" in block


def test_schema_v29_adds_safe_default():
    assert "LATEST_SCHEMA_VERSION = 31" in MIGRATIONS
    assert "def ensure_v29_schema_compat" in MIGRATIONS
    assert "matchcamp_matches_per_team INTEGER NOT NULL DEFAULT 4" in MIGRATIONS
