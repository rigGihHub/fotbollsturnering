import cupnavi_api.matchcamp_builder_repository as builder


def _teams(count):
    return [{"id": index, "name": f"Lag {index}"} for index in range(1, count + 1)]


def test_even_matchcamp_is_balanced_and_unique(monkeypatch):
    monkeypatch.setattr(builder, "_source", lambda *_: (_teams(8), 0, "matchcamp"))
    proposal = builder.matchcamp_pairing_proposal(1, 9, 3)
    assert proposal["match_count"] == 12
    assert proposal["minimum_matches"] == proposal["maximum_matches"] == 3
    pairs = [{row["home_team_id"], row["away_team_id"]} for row in proposal["pairs"]]
    assert len({frozenset(pair) for pair in pairs}) == len(pairs)


def test_odd_matchcamp_explains_unavoidable_bye(monkeypatch):
    monkeypatch.setattr(builder, "_source", lambda *_: (_teams(7), 0, "matchcamp"))
    proposal = builder.matchcamp_pairing_proposal(1, 9, 3)
    assert proposal["balanced"] is False
    assert proposal["minimum_matches"] == 2
    assert proposal["maximum_matches"] == 3


def test_builder_refuses_existing_matches(monkeypatch):
    monkeypatch.setattr(builder, "_source", lambda *_: (_teams(8), 1, "matchcamp"))
    try:
        builder.matchcamp_pairing_proposal(1, 9, 3)
    except ValueError as exc:
        assert "skriver aldrig över" in str(exc)
    else:
        raise AssertionError("Existing matches must be protected")


def test_single_match_requires_exactly_two_teams_and_one_meeting(monkeypatch):
    monkeypatch.setattr(builder, "_source", lambda *_: (_teams(2), 0, "single_match"))
    proposal = builder.matchcamp_pairing_proposal(1, 9, 1)
    assert proposal["match_count"] == 1
    assert {proposal["pairs"][0]["home_team_id"], proposal["pairs"][0]["away_team_id"]} == {1, 2}
    for target in (2, 0):
        try:
            builder.matchcamp_pairing_proposal(1, 9, target)
        except ValueError as exc:
            assert "exakt två lag och en match" in str(exc)
        else:
            raise AssertionError("Single match must refuse other match counts")
    monkeypatch.setattr(builder, "_source", lambda *_: (_teams(3), 0, "single_match"))
    try:
        builder.matchcamp_pairing_proposal(1, 9, 1)
    except ValueError as exc:
        assert "exakt två lag" in str(exc)
    else:
        raise AssertionError("Single match must refuse three teams")
