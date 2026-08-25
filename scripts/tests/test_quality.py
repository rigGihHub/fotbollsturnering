from cupnavi_core.quality import is_advisory_warning, next_admin_step

def test_color_conflict_is_advisory():
    assert is_advisory_warning("Färgkrock i match 4")

def test_other_warning_is_not_advisory():
    assert not is_advisory_warning("Domare saknas i match 4")

def test_next_step_starts_with_teams():
    assert next_admin_step(False, False, False, False, 0, True, False) == "Lag"

def test_next_step_moves_to_schedule_when_prerequisites_ready():
    assert next_admin_step(True, True, True, True, 0, True, False) == "Skapa och publicera schema"

def test_next_step_moves_to_results_after_clean_schedule():
    assert next_admin_step(True, True, True, True, 20, False, False) == "Matcher och resultat"

def test_next_step_moves_to_controls_when_everything_done():
    assert next_admin_step(True, True, True, True, 20, False, True) == "Kontroller"

def test_possible_color_similarity_is_advisory():
    assert is_advisory_warning("Möjlig färglikhet – extraställ kan behövas")
