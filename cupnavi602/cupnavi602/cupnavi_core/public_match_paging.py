"""Small, framework-free helpers for incremental public match rendering."""

PUBLIC_MATCH_INITIAL_BATCH = 12
PUBLIC_MATCH_BATCH_SIZE = 12


def visible_match_batch(matches, requested_count=None):
    """Return a bounded first slice and the effective visible count.

    The helper deliberately does not know about Streamlit/session state so the
    public view can evolve without coupling paging policy to the UI framework.
    """
    rows = list(matches or [])
    try:
        count = int(requested_count or PUBLIC_MATCH_INITIAL_BATCH)
    except (TypeError, ValueError):
        count = PUBLIC_MATCH_INITIAL_BATCH
    count = max(PUBLIC_MATCH_INITIAL_BATCH, count)
    count = min(count, len(rows))
    return rows[:count], count


def next_visible_count(current_count, total_count):
    """Advance one batch without ever exceeding the filtered match count."""
    try:
        current = int(current_count or PUBLIC_MATCH_INITIAL_BATCH)
    except (TypeError, ValueError):
        current = PUBLIC_MATCH_INITIAL_BATCH
    try:
        total = max(0, int(total_count or 0))
    except (TypeError, ValueError):
        total = 0
    return min(total, max(PUBLIC_MATCH_INITIAL_BATCH, current) + PUBLIC_MATCH_BATCH_SIZE)
