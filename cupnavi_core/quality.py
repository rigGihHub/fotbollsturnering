def is_advisory_warning(message):
    lowered = (message or "").lower()
    return "färgkrock" in lowered or "tröjfärg" in lowered

def next_admin_step(teams_ready, groups_ready, players_ready, refs_ready, match_count, schedule_dirty, results_ready):
    if not teams_ready:
        return "Lag"
    if not groups_ready:
        return "Grupper"
    if not players_ready:
        return "Trupper"
    if not refs_ready:
        return "Domare"
    if not match_count or schedule_dirty:
        return "Skapa och publicera schema"
    if not results_ready:
        return "Matcher och resultat"
    return "Kontroller"
