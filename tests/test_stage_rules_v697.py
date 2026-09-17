from cupnavi_core.stage_rules import is_group_table_stage


def test_preliminary_and_placement_groups_share_group_result_rules():
    assert is_group_table_stage("Gruppspel") is True
    assert is_group_table_stage("Placeringsgrupp") is True


def test_knockout_remains_decisive():
    assert is_group_table_stage("Slutspel") is False
    assert is_group_table_stage("Final") is False
