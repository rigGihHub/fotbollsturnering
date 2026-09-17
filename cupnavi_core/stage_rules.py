"""Shared stage classification for result and table behaviour."""

GROUP_TABLE_STAGES = frozenset({"Gruppspel", "Placeringsgrupp"})


def is_group_table_stage(stage) -> bool:
    """True for stages where draws are valid and no deciding winner is required."""
    return str(stage or "").strip() in GROUP_TABLE_STAGES
