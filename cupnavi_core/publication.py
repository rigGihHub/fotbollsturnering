from cupnavi_core.admin_publication import build_publish_blockers


def publication_blockers(playoff_confirmed, scheduled_count, schedule_dirty, error_count, warning_count, warnings_approved):
    """Compatibility wrapper around the single publication blocker model.

    warning_count/warnings_approved remain in the signature for older callers,
    but warnings no longer block publication in v365.
    """
    errors = ["schemafel"] * max(0, int(error_count or 0))
    return build_publish_blockers(
        playoff_model_confirmed=bool(playoff_confirmed),
        scheduled_matches=int(scheduled_count or 0),
        schedule_dirty=bool(schedule_dirty),
        schedule_errors=errors,
    )
