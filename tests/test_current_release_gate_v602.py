from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def _base_payload(**overrides):
    payload = {
        "found": True,
        "confidence": "high",
        "reason": "Belagd klubb och tröja.",
        "home_pattern": "Helfärgad",
        "home_color_1": "#112233",
        "home_color_2": "#FFFFFF",
        "away_pattern": "Helfärgad",
        "away_color_1": "#FFFFFF",
        "away_color_2": "#111827",
        "home_sources": ["https://club.example/home"],
        "away_sources": ["https://club.example/away"],
        "home_evidence": "Hemmastället visas.",
        "away_evidence": "Bortastället visas.",
        "sources": [],
        "home_verified": True,
        "away_verified": True,
        "club_match": "Heming IL, Oslo",
        "identity_status": "exact",
        "candidate_matches": [],
    }
    payload.update(overrides)
    return payload


def test_v602_version_is_synchronized():
    expected = "2026.09.09-602-KIT-IDENTITY-DISAMBIGUATION"
    assert expected in VERSION
    assert expected in APP
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == expected


def test_ambiguous_club_identity_never_exposes_mixed_kit_colors():
    from cupnavi_core.ai_kit_suggestion import normalize_kit_suggestion

    result = normalize_kit_suggestion(_base_payload(
        identity_status="ambiguous",
        candidate_matches=[
            {
                "name": "Heming IL",
                "location": "Oslo",
                "country": "Norge",
                "source_url": "https://heming.no/",
                "reason": "Officiell klubbkälla.",
                "confidence": "high",
            },
            {
                "name": "Heming Fotball",
                "location": "Oslo",
                "country": "Norge",
                "source_url": "https://example.org/heming-football",
                "reason": "Möjlig ungdomssektion.",
                "confidence": "medium",
            },
        ],
    ))
    assert result["identity_status"] == "ambiguous"
    assert len(result["candidate_matches"]) == 2
    assert result["found"] is False
    assert result["home_verified"] is False
    assert result["away_verified"] is False


def test_candidate_list_requires_real_source_urls_and_is_bounded():
    from cupnavi_core.ai_kit_suggestion import normalize_kit_suggestion

    candidates = [
        {"name": f"Club {i}", "location": "Ort", "country": "SE", "source_url": f"https://example.org/{i}", "reason": "x", "confidence": "medium"}
        for i in range(6)
    ]
    candidates.insert(0, {"name": "Bad", "location": "", "country": "", "source_url": "not-a-url", "reason": "", "confidence": "high"})
    result = normalize_kit_suggestion(_base_payload(identity_status="ambiguous", candidate_matches=candidates))
    assert len(result["candidate_matches"]) == 4
    assert all(c["source_url"].startswith("https://") for c in result["candidate_matches"])
    assert all(c["name"] != "Bad" for c in result["candidate_matches"])


def test_resolved_identity_is_part_of_search_context_and_cache_key():
    from cupnavi_core.ai_kit_suggestion import _context_text, _cache_key

    context = _context_text("Örebro", "SE", "P2013", "", "Heming IL · Oslo · Norge", "https://heming.no/")
    assert "arrangören har valt klubbidentitet" in context
    assert "Heming IL" in context
    assert "https://heming.no/" in context
    a = _cache_key("Heming P2013", "Örebro", "SE", "P2013", "", "gpt", "Heming IL", "https://heming.no/")
    b = _cache_key("Heming P2013", "Örebro", "SE", "P2013", "", "gpt", "Annan klubb", "https://other.example/")
    assert a != b


def test_ui_forces_identity_choice_before_retrying_kit_search():
    block = APP[APP.index('if admin_page == "Tröj setup"'):APP.index('if admin_page == "Grupper"')]
    assert "CupNavi hittade flera möjliga klubbar" in block
    assert "Vilken klubb är rätt?" in block
    assert "✓ Använd denna klubb och sök tröjor" in block
    assert "resolved_club=" in block
    assert "resolved_source_url=" in block
    assert "use_cache=False" in block
