from cupnavi_core.publication import publication_blockers

def test_ready_to_publish_has_no_blockers():
    assert publication_blockers(True, 12, False, 0, 0, False) == []

def test_missing_schedule_is_explained():
    blockers = publication_blockers(True, 0, False, 0, 0, False)
    assert any("Spelschema saknas" in item for item in blockers)

def test_dirty_schedule_is_explained():
    blockers = publication_blockers(True, 12, True, 0, 0, False)
    assert any("inaktuellt" in item for item in blockers)

def test_errors_and_unapproved_warnings_are_both_explained():
    blockers = publication_blockers(True, 12, False, 2, 3, False)
    assert any("2 blockerande schemafel" in item for item in blockers)
    assert any("3 schemavarningar" in item for item in blockers)

def test_approved_warnings_do_not_block():
    blockers = publication_blockers(True, 12, False, 0, 3, True)
    assert blockers == []
