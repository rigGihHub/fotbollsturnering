from cupnavi_core.migrations import LATEST_SCHEMA_VERSION, MIGRATIONS


def test_v129_schema_fields_exist_in_migration():
    assert LATEST_SCHEMA_VERSION >= 15
    migration = next(m for m in MIGRATIONS if m.version == 15)
    statements = "\n".join(migration.statements)
    assert "enable_final_ranking" in statements
    assert "avoid_late_group_match" in statements
