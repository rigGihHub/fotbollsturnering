from cupnavi_core.bracket_validation import validate_bracket_sources


def _team(team_id):
    return {"id": team_id, "name": f"Lag {team_id}"}


def _group(group_id):
    return {"id": group_id, "name": f"Grupp {group_id}"}


def _match(match_id, home, away, bracket_id=1):
    return {"id": match_id, "home_source": home, "away_source": away, "bracket_id": bracket_id}


def test_valid_knockout_chain_is_ready():
    matches = [
        _match(10, "group:1:1", "group:2:2"),
        _match(11, "group:2:1", "group:1:2"),
        _match(12, "winner:10", "winner:11"),
        _match(13, "loser:10", "loser:11"),
    ]
    result = validate_bracket_sources(matches, [_team(1), _team(2)], [_group(1), _group(2)])
    assert result["ready"] is True
    assert result["issue_count"] == 0
    assert result["playoff_match_count"] == 4


def test_missing_entities_and_empty_slots_are_actionable():
    matches = [
        _match(10, "team:999", ""),
        _match(11, "group:88:1", "winner:777"),
    ]
    result = validate_bracket_sources(matches, [_team(1)], [_group(1)])
    codes = {item["code"] for item in result["issues"]}
    assert {"team_missing", "empty_slot", "group_missing", "source_match_missing"}.issubset(codes)
    assert result["ready"] is False


def test_self_dependency_and_transitive_cycles_are_blocked():
    matches = [
        _match(20, "winner:20", "team:1"),
        _match(21, "winner:23", "team:1"),
        _match(22, "winner:21", "team:2"),
        _match(23, "winner:22", "team:3"),
    ]
    result = validate_bracket_sources(matches, [_team(1), _team(2), _team(3)], [])
    codes = [item["code"] for item in result["issues"]]
    assert "self_dependency" in codes
    assert codes.count("dependency_cycle") == 3


def test_legacy_free_text_source_is_not_claimed_safe():
    result = validate_bracket_sources([_match(30, "Vinnare semi 1", "team:1")], [_team(1)], [])
    assert result["ready"] is False
    assert result["issues"][0]["code"] == "legacy_source"


def test_malformed_group_placement_is_blocked():
    result = validate_bracket_sources([_match(40, "group:3:0", "team:1")], [_team(1)], [_group(3)])
    assert any(item["code"] == "unsupported_source" for item in result["issues"])
