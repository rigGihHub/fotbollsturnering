import cupnavi_api.matchcamp_builder_repository as builder


def _teams(count):
    return [{"id": index, "name": f"Lag {index}"} for index in range(1, count + 1)]


def test_even_matchcamp_is_balanced_and_unique(monkeypatch):
    monkeypatch.setattr(builder, "_source", lambda *_: (_teams(8), 0))
    proposal = builder.matchcamp_pairing_proposal(1, 9, 3)
    assert proposal["match_count"] == 12
    assert proposal["minimum_matches"] == proposal["maximum_matches"] == 3
    pairs = [{row["home_team_id"], row["away_team_id"]} for row in proposal["pairs"]]
    assert len({frozenset(pair) for pair in pairs}) == len(pairs)


def test_odd_matchcamp_explains_unavoidable_bye(monkeypatch):
    monkeypatch.setattr(builder, "_source", lambda *_: (_teams(7), 0))
    proposal = builder.matchcamp_pairing_proposal(1, 9, 3)
    assert proposal["balanced"] is False
    assert proposal["minimum_matches"] == 2
    assert proposal["maximum_matches"] == 3


def test_builder_refuses_existing_matches(monkeypatch):
    monkeypatch.setattr(builder, "_source", lambda *_: (_teams(8), 1))
    try:
        builder.matchcamp_pairing_proposal(1, 9, 3)
    except ValueError as exc:
        assert "skriver aldrig över" in str(exc)
    else:
        raise AssertionError("Existing matches must be protected")
