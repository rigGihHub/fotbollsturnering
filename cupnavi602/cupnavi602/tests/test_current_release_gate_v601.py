from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
KIT = (ROOT / "cupnavi_core" / "ai_kit_suggestion.py").read_text(encoding="utf-8")
VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v601_version_is_synchronized():
    expected = "2026.09.09-601-KIT-SEARCH-ACCURACY-SPEED"
    assert expected in VERSION
    assert expected in APP
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == expected


def test_v601_uses_fast_two_pass_search_and_cache():
    assert "MAX_SEARCH_ATTEMPTS = 2" in KIT
    assert "Snabb multikällesökning" in KIT
    assert "Riktad lucksökning" in KIT
    assert "CACHE_TTL_SECONDS" in KIT
    assert 'cached["cache_hit"] = True' in KIT


def test_v601_requires_kit_specific_sources_for_verification():
    from cupnavi_core.ai_kit_suggestion import normalize_kit_suggestion

    unsafe = normalize_kit_suggestion({
        "found": True,
        "confidence": "high",
        "home_verified": True,
        "away_verified": False,
        "home_pattern": "Helfärgad",
        "home_color_1": "#112233",
        "home_color_2": "#FFFFFF",
        "away_pattern": "Helfärgad",
        "away_color_1": "#FFFFFF",
        "away_color_2": "#111827",
        "home_sources": [],
        "away_sources": [],
        "sources": [],
    })
    assert unsafe["found"] is False
    assert unsafe["home_verified"] is False

    grounded = normalize_kit_suggestion({
        "found": True,
        "confidence": "high",
        "home_verified": True,
        "away_verified": False,
        "home_pattern": "Helfärgad",
        "home_color_1": "#112233",
        "home_color_2": "#FFFFFF",
        "away_pattern": "Helfärgad",
        "away_color_1": "#FFFFFF",
        "away_color_2": "#111827",
        "home_sources": ["https://club.example/kit"],
        "away_sources": [],
        "sources": [],
    })
    assert grounded["found"] is True
    assert grounded["home_verified"] is True
    assert grounded["confidence"] == "medium"


def test_v601_parallelises_whole_tournament_scan():
    block = APP[APP.index('if admin_page == "Tröj setup"'):APP.index('if admin_page == "Grupper"')]
    assert "ThreadPoolExecutor" in block
    assert "as_completed" in block
    assert "max_workers=workers" in block
    assert "min(4" in block
    assert "⚡ Snabbsök tröjor för alla lag" in block


def test_v601_exposes_per_kit_evidence_and_keeps_manual_approval():
    block = APP[APP.index('if admin_page == "Tröj setup"'):APP.index('if admin_page == "Grupper"')]
    assert "Källor & bevis som CupNavi använde" in block
    assert "home_evidence" in block and "away_evidence" in block
    assert 'if approve_col.button("✓ Godkänn och spara"' in block
    assert block.index('if approve_col.button("✓ Godkänn och spara"') < block.index('UPDATE teams SET primary_color=')
