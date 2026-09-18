from cupnavi_core.placement_groups import build_placement_groups


def second_stage_for(format_key, groups):
    """Test contract: placement groups are opt-in, never implied by group play."""
    if format_key == "placement_groups":
        return build_placement_groups(groups)
    return []


def test_group_only_never_creates_a_second_stage():
    groups = [{"id": 1, "team_count": 4}, {"id": 2, "team_count": 4}]
    assert second_stage_for("group_only", groups) == []


def test_knockout_choice_does_not_create_placement_groups():
    groups = [{"id": 1, "team_count": 4}, {"id": 2, "team_count": 4}]
    assert second_stage_for("knockout", groups) == []


def test_placement_group_choice_creates_second_group_stage():
    groups = [{"id": 1, "team_count": 4}, {"id": 2, "team_count": 4}]
    second_stage = second_stage_for("placement_groups", groups)
    assert len(second_stage) == 4
    assert second_stage[0]["sources"] == ["group:1:1", "group:2:1"]
