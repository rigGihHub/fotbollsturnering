
from cupnavi_core.initial_setup_logic import normalized_priority_order, priority_order_changed


def test_normalized_priority_order_preserves_saved_and_adds_new_defaults():
    defaults=["A","B","C"]
    assert normalized_priority_order(["B","A"],defaults)==["B","A","C"]


def test_invalid_or_removed_priority_is_not_reintroduced():
    defaults=["A","B"]
    assert normalized_priority_order(["OLD","B"],defaults)==["B","A"]


def test_priority_write_guard_only_flags_real_change():
    assert priority_order_changed(["A","B"],["A","B"]) is False
    assert priority_order_changed(["B","A"],["A","B"]) is True
