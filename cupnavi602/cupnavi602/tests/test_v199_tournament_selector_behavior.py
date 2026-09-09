from cupnavi_core.ui_logic import resolve_tournament_selector_seed

def test_valid_user_selection_survives_rerun_even_with_url_and_preference():
    assert resolve_tournament_selector_seed([1,2,3], current_selection=3, requested_cup_id=1, preferred_tournament_id=2) == 3

def test_url_seeds_selector_when_widget_state_is_missing():
    assert resolve_tournament_selector_seed([1,2,3], requested_cup_id=2, preferred_tournament_id=3) == 2

def test_preference_is_fallback_when_url_is_not_accessible():
    assert resolve_tournament_selector_seed([1,2,3], requested_cup_id=99, preferred_tournament_id=3) == 3

def test_first_accessible_tournament_is_final_fallback():
    assert resolve_tournament_selector_seed([7,9], requested_cup_id=99) == 7

def test_empty_accessible_list_is_safe():
    assert resolve_tournament_selector_seed([]) is None
