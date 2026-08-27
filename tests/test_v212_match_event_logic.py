
import math
from cupnavi_core.match_event_logic import (
    event_values_from_editor,
    prepare_changed_event_rows,
)


def _is_na(value):
    return value is None or (isinstance(value,float) and math.isnan(value))


def test_nan_editor_values_are_normalized_to_zero():
    row={"Mål":float("nan"),"Assist":None,"Varningar":0,"Utvisningar":0}
    assert event_values_from_editor(row,is_na=_is_na)=={
        "goals":0,"assists":0,"yellow_cards":0,"red_cards":0,
    }


def test_unchanged_player_is_not_written():
    rows=[{"player_id":4,"Mål":1,"Assist":1,"Varningar":0,"Utvisningar":0}]
    existing={4:{"goals":1,"assists":1,"yellow_cards":0,"red_cards":0}}
    assert prepare_changed_event_rows(rows,existing,match_id=9,is_na=_is_na)==[]


def test_changed_player_carries_expected_snapshot():
    rows=[{"player_id":4,"Mål":2,"Assist":1,"Varningar":1,"Utvisningar":0}]
    existing={4:{"goals":1,"assists":1,"yellow_cards":0,"red_cards":0}}
    changed=prepare_changed_event_rows(rows,existing,match_id=9,is_na=_is_na)
    assert changed==[{
        "match_id":9,
        "player_id":4,
        "goals":2,
        "assists":1,
        "yellow_cards":1,
        "red_cards":0,
        "expected":{"goals":1,"assists":1,"yellow_cards":0,"red_cards":0},
    }]


def test_new_player_stat_row_has_zero_expected_snapshot():
    rows=[{"player_id":5,"Mål":1,"Assist":0,"Varningar":0,"Utvisningar":0}]
    changed=prepare_changed_event_rows(rows,{},match_id=10,is_na=_is_na)
    assert changed[0]["expected"]=={
        "goals":0,"assists":0,"yellow_cards":0,"red_cards":0,
    }
