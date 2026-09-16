from cupnavi_core.placement_groups import (
    PLACEMENT_GROUP_STAGE,
    build_placement_group_matches,
    build_placement_groups,
    overall_ranking,
)


def test_three_equal_groups_create_one_placement_group_per_position():
    groups = [
        {"id": 10, "team_count": 4},
        {"id": 20, "team_count": 4},
        {"id": 30, "team_count": 4},
    ]
    result = build_placement_groups(groups)
    assert len(result) == 4
    assert result[0] == {
        "placement": 1,
        "name": "Placeringsgrupp 1",
        "sources": ["group:10:1", "group:20:1", "group:30:1"],
        "overall_start": 1,
        "overall_end": 3,
    }
    assert result[3]["overall_start"] == 10
    assert result[3]["overall_end"] == 12


def test_uneven_groups_do_not_invent_missing_qualifiers():
    groups = [
        {"id": 1, "team_count": 4},
        {"id": 2, "team_count": 3},
        {"id": 3, "team_count": 2},
    ]
    result = build_placement_groups(groups)
    assert [item["placement"] for item in result] == [1, 2, 3]
    assert result[2]["sources"] == ["group:1:3", "group:2:3"]
    assert all("group:3:3" not in item["sources"] for item in result)


def test_two_preliminary_groups_become_one_match_per_placement():
    placement_group = build_placement_groups([
        {"id": 1, "team_count": 3},
        {"id": 2, "team_count": 3},
    ])[0]
    matches = build_placement_group_matches(placement_group)
    assert matches == [{
        "stage": PLACEMENT_GROUP_STAGE,
        "placement_group": 1,
        "home_source": "group:1:1",
        "away_source": "group:2:1",
    }]


def test_three_sources_create_round_robin_not_knockout():
    placement_group = build_placement_groups([
        {"id": 1, "team_count": 2},
        {"id": 2, "team_count": 2},
        {"id": 3, "team_count": 2},
    ])[0]
    matches = build_placement_group_matches(placement_group)
    assert len(matches) == 3
    assert all(match["stage"] == "Placeringsgrupp" for match in matches)


def test_overall_ranking_never_crosses_placement_group_boundary():
    groups = build_placement_groups([
        {"id": 1, "team_count": 2},
        {"id": 2, "team_count": 2},
        {"id": 3, "team_count": 2},
    ])
    ranking = overall_ranking(groups, {
        1: ["A1", "B1", "C1"],
        2: ["C2", "A2", "B2"],
    })
    assert [row["team"] for row in ranking] == ["A1", "B1", "C1", "C2", "A2", "B2"]
    assert [row["position"] for row in ranking] == [1, 2, 3, 4, 5, 6]


def test_max_placement_can_limit_second_stage():
    result = build_placement_groups([
        {"id": 1, "team_count": 5},
        {"id": 2, "team_count": 5},
    ], max_placement=3)
    assert [item["placement"] for item in result] == [1, 2, 3]
