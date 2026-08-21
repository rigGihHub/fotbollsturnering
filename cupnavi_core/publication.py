def publication_blockers(playoff_confirmed, scheduled_count, schedule_dirty, error_count, warning_count, warnings_approved):
    blockers = []
    if not playoff_confirmed:
        blockers.append("Slutspelsmodell och cupregler måste sparas på Översikt.")
    if not scheduled_count:
        blockers.append("Spelschema saknas. Generera schemat under Schema.")
    if schedule_dirty and scheduled_count:
        blockers.append("Schemat är inaktuellt eftersom förutsättningarna har ändrats. Regenerera schemat.")
    if error_count:
        blockers.append(f"{error_count} blockerande schemafel måste åtgärdas.")
    if warning_count and not warnings_approved:
        blockers.append(f"{warning_count} schemavarningar måste granskas och godkännas.")
    return blockers
