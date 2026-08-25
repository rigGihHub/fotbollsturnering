# CupNavi rollback

## Application rollback
1. Identify the last known-good Git commit/release.
2. Revert the faulty commit in GitHub/GitHub Desktop and push.
3. Confirm the sidebar release and deploy fingerprint after Streamlit redeploys.
4. Run CI and the cross-browser smoke matrix.

## Database/data rollback
CupNavi tournament backups are portable JSON snapshots.
- Take a backup before risky live changes.
- Restore creates a NEW, unpublished cup; it never overwrites the source cup.
- Compare the restored cup before publishing it.
- Keep the original cup until the restored copy has been verified.

## Migration safety
Schema migrations must remain forward-compatible and idempotent. A code rollback must not assume that a database migration has been reversed.
