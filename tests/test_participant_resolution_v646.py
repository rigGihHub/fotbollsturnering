from cupnavi_core.participant_resolution import (
    ParticipantResolver,
    enrich_match_participants,
    finalized_group_standings,
)


def _team(team_id, name, group_id=None):
    return {"id": team_id, "name": name, "group_id": group_id}


def _match(match_id, home, away, *, stage="Slutspel", group_id=None, home_score=None,
           away_score=None, home_penalties=None, away_penalties=None, decided_winner_id=None):
    return {
        "id": match_id,
        "stage": stage,
        "group_id": group_id,
        "home_source": home,
        "away_source": away,
        "home_score": home_score,
        "away_score": away_score,
        "home_penalties": home_penalties,
        "away_penalties": away_penalties,
        "decided_winner_id": decided_winner_id,
    }


def test_direct_team_source_resolves_without_changing_source():
    resolver = ParticipantResolver(teams=[_team(7, "Örebro SK")], matches=[])
    resolved = resolver.resolve("team:7")
    assert resolved.resolved is True
    assert resolved.team_id == 7
    assert resolved.team_name == "Örebro SK"
    assert resolved.source == "team:7"


def test_group_source_does_not_resolve_from_partial_table():
    teams = [_team(1, "A", 4), _team(2, "B", 4), _team(3, "C", 4)]
    matches = [
        _match(1, "team:1", "team:2", stage="Gruppspel", group_id=4, home_score=2, away_score=0),
        _match(2, "team:1", "team:3", stage="Gruppspel", group_id=4),
    ]
    standings = finalized_group_standings(teams, matches, points_win=3, points_draw=1, points_loss=0)
    assert 4 not in standings
    resolved = ParticipantResolver(teams=teams, matches=matches, standings_by_group=standings).resolve("group:4:1")
    assert resolved.resolved is False
    assert resolved.reason == "group_not_final"


def test_group_source_uses_existing_cup_table_semantics_when_group_is_complete():
    teams = [_team(1, "A", 4), _team(2, "B", 4), _team(3, "C", 4)]
    matches = [
        _match(1, "team:1", "team:2", stage="Gruppspel", group_id=4, home_score=1, away_score=0),
        _match(2, "team:1", "team:3", stage="Gruppspel", group_id=4, home_score=0, away_score=2),
        _match(3, "team:2", "team:3", stage="Gruppspel", group_id=4, home_score=0, away_score=1),
    ]
    standings = finalized_group_standings(teams, matches, points_win=3, points_draw=1, points_loss=0)
    assert [row["team_id"] for row in standings[4]] == [3, 1, 2]
    resolver = ParticipantResolver(teams=teams, matches=matches, standings_by_group=standings)
    assert resolver.resolve("group:4:1").team_id == 3
    assert resolver.resolve("group:4:2").team_id == 1


def test_winner_and_loser_resolve_from_score():
    teams = [_team(1, "A"), _team(2, "B")]
    matches = [_match(10, "team:1", "team:2", home_score=3, away_score=1)]
    resolver = ParticipantResolver(teams=teams, matches=matches)
    assert resolver.resolve("winner:10").team_id == 1
    assert resolver.resolve("loser:10").team_id == 2


def test_penalties_resolve_drawn_playoff_match():
    teams = [_team(1, "A"), _team(2, "B")]
    matches = [_match(10, "team:1", "team:2", home_score=1, away_score=1, home_penalties=4, away_penalties=5)]
    resolver = ParticipantResolver(teams=teams, matches=matches)
    assert resolver.resolve("winner:10").team_id == 2
    assert resolver.resolve("loser:10").team_id == 1


def test_decided_winner_id_has_priority_for_explicit_decision():
    teams = [_team(1, "A"), _team(2, "B")]
    matches = [_match(10, "team:1", "team:2", home_score=1, away_score=1, decided_winner_id=1)]
    resolver = ParticipantResolver(teams=teams, matches=matches)
    assert resolver.resolve("winner:10").team_id == 1
    assert resolver.resolve("loser:10").team_id == 2


def test_multistep_winner_chain_resolves_recursively():
    teams = [_team(1, "A"), _team(2, "B"), _team(3, "C")]
    matches = [
        _match(10, "team:1", "team:2", home_score=2, away_score=0),
        _match(11, "winner:10", "team:3", home_score=0, away_score=1),
    ]
    resolver = ParticipantResolver(teams=teams, matches=matches)
    assert resolver.resolve("winner:11").team_id == 3
    assert resolver.resolve("loser:11").team_id == 1


def test_undecided_match_and_cycle_stay_unresolved():
    teams = [_team(1, "A")]
    undecided = [_match(10, "team:1", "team:99")]
    assert ParticipantResolver(teams=teams, matches=undecided).resolve("winner:10").resolved is False

    cycle = [
        _match(20, "winner:21", "team:1", home_score=1, away_score=0),
        _match(21, "winner:20", "team:1", home_score=1, away_score=0),
    ]
    resolved = ParticipantResolver(teams=teams, matches=cycle).resolve("winner:20")
    assert resolved.resolved is False


def test_enrichment_is_non_destructive_and_adds_names():
    teams = [_team(1, "A"), _team(2, "B")]
    matches = [_match(10, "team:1", "team:2", home_score=2, away_score=0)]
    resolver = ParticipantResolver(teams=teams, matches=matches)
    enriched = enrich_match_participants(matches, resolver)[0]
    assert enriched["home_source"] == "team:1"
    assert enriched["away_source"] == "team:2"
    assert enriched["home_team_name"] == "A"
    assert enriched["away_team_name"] == "B"
    assert enriched["home_participant"]["resolved"] is True
