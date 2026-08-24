"""Versionsstyrda databasmigreringar för CupNavi.

Regel:
- En migration får aldrig ändras efter att den släppts.
- Nya schemaändringar läggs till med ett nytt versionsnummer.
- Migreringar ska vara idempotenta där det är rimligt och köras i stigande ordning.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

LATEST_SCHEMA_VERSION = 11


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS = (
    Migration(
        1,
        "baseline_version_tracking",
        (),
    ),
    Migration(
        2,
        "performance_indexes",
        (
            "CREATE INDEX IF NOT EXISTS idx_groups_tournament ON groups(tournament_id)",
            "CREATE INDEX IF NOT EXISTS idx_teams_tournament ON teams(tournament_id)",
            "CREATE INDEX IF NOT EXISTS idx_teams_group ON teams(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_referees_tournament ON referees(tournament_id)",
            "CREATE INDEX IF NOT EXISTS idx_matches_tournament_start ON matches(tournament_id, scheduled_start)",
            "CREATE INDEX IF NOT EXISTS idx_matches_group ON matches(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_matches_bracket ON matches(bracket_id)",
            "CREATE INDEX IF NOT EXISTS idx_match_stats_match ON player_match_stats(match_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_tournament ON feedback(tournament_id)",
            "CREATE INDEX IF NOT EXISTS idx_offers_tournament_active_order ON offers(tournament_id, active, sort_order)",
        ),
    ),
    Migration(
        3,
        "sponsors_and_functionaries",
        (
            """CREATE TABLE IF NOT EXISTS sponsors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                level TEXT,
                description TEXT,
                website_url TEXT,
                logo_data_uri TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS functionaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                pitch_number INTEGER,
                notes TEXT,
                public_contact INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            )""",
            "CREATE INDEX IF NOT EXISTS idx_sponsors_tournament_active_order ON sponsors(tournament_id, active, sort_order)",
            "CREATE INDEX IF NOT EXISTS idx_functionaries_tournament_role ON functionaries(tournament_id, role, active)",
        ),
    ),
    Migration(
        4,
        "visitor_analytics",
        (
            """CREATE TABLE IF NOT EXISTS visitor_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                session_token TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                view_count INTEGER NOT NULL DEFAULT 1,
                device_type TEXT NOT NULL DEFAULT 'Dator',
                browser TEXT NOT NULL DEFAULT 'Övrig',
                source TEXT NOT NULL DEFAULT 'Direkt / okänd',
                UNIQUE(tournament_id, session_token)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_visitor_sessions_tournament_first ON visitor_sessions(tournament_id, first_seen)",
            "CREATE INDEX IF NOT EXISTS idx_visitor_sessions_tournament_last ON visitor_sessions(tournament_id, last_seen)",
        ),
    ),
    Migration(
        5,
        "experience_toolkit_v96",
        (
            "ALTER TABLE tournaments ADD COLUMN sport TEXT NOT NULL DEFAULT 'Fotboll'",
            "ALTER TABLE teams ADD COLUMN checked_in INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE teams ADD COLUMN checked_in_at TEXT",
            "ALTER TABLE matches ADD COLUMN original_scheduled_start TEXT",
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT 'Admin',
                action_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                description TEXT NOT NULL,
                before_json TEXT,
                after_json TEXT,
                reversible INTEGER NOT NULL DEFAULT 0,
                undone_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS cup_feed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Info',
                title TEXT NOT NULL,
                detail TEXT,
                public INTEGER NOT NULL DEFAULT 1,
                related_match_id INTEGER REFERENCES matches(id) ON DELETE SET NULL
            )""",
            """CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                event_key TEXT,
                UNIQUE(tournament_id, team_id, event_key)
            )""",
            """CREATE TABLE IF NOT EXISTS venue_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                kind TEXT NOT NULL DEFAULT 'Övrigt',
                label TEXT NOT NULL,
                detail TEXT,
                url TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS referee_acknowledgements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                referee_id INTEGER NOT NULL REFERENCES referees(id) ON DELETE CASCADE,
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                acknowledged_at TEXT NOT NULL,
                UNIQUE(referee_id, match_id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_audit_tournament_created ON audit_log(tournament_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_feed_tournament_created ON cup_feed(tournament_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_tournament_team ON notifications(tournament_id, team_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_venue_points_tournament ON venue_points(tournament_id, sort_order)",
            "CREATE INDEX IF NOT EXISTS idx_ref_ack_tournament_referee ON referee_acknowledgements(tournament_id, referee_id)",
        ),
    ),
    Migration(
        6,
        "participant_team_portal_v99",
        (
            "ALTER TABLE tournaments ADD COLUMN squad_deadline_minutes INTEGER NOT NULL DEFAULT 30",
            "ALTER TABLE tournaments ADD COLUMN max_roster_size INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE tournaments ADD COLUMN allow_team_public_contact INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE teams ADD COLUMN checked_in_by TEXT",
            "ALTER TABLE teams ADD COLUMN kit_confirmed_at TEXT",
            "ALTER TABLE teams ADD COLUMN public_contact_name TEXT",
            "ALTER TABLE teams ADD COLUMN public_contact_phone TEXT",
            "ALTER TABLE teams ADD COLUMN public_contact_email TEXT",
            "ALTER TABLE teams ADD COLUMN public_contact_enabled INTEGER NOT NULL DEFAULT 0",
            """CREATE TABLE IF NOT EXISTS participant_access_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                code_salt TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT,
                UNIQUE(tournament_id, team_id)
            )""",
            """CREATE TABLE IF NOT EXISTS match_rosters (
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                selected_at TEXT NOT NULL,
                selected_by TEXT NOT NULL DEFAULT 'Deltagaransvarig',
                PRIMARY KEY(match_id, team_id, player_id)
            )""",
            "CREATE INDEX IF NOT EXISTS idx_participant_access_tournament_team ON participant_access_credentials(tournament_id, team_id)",
            "CREATE INDEX IF NOT EXISTS idx_match_rosters_match_team ON match_rosters(match_id, team_id)",
        ),
    ),
    Migration(
        7,
        "international_multisport_foundation_v100",
        (
            "ALTER TABLE tournaments ADD COLUMN locale TEXT NOT NULL DEFAULT 'sv-SE'",
            "ALTER TABLE tournaments ADD COLUMN timezone_name TEXT NOT NULL DEFAULT 'Europe/Stockholm'",
            "ALTER TABLE tournaments ADD COLUMN participant_type TEXT NOT NULL DEFAULT 'team'",
            "ALTER TABLE tournaments ADD COLUMN country_code TEXT",
        ),
    ),
    Migration(
        8,
        "tournament_lifecycle_history_v102",
        (
            "ALTER TABLE tournaments ADD COLUMN lifecycle_status TEXT NOT NULL DEFAULT 'draft'",
            "ALTER TABLE tournaments ADD COLUMN public_slug TEXT",
            "ALTER TABLE tournaments ADD COLUMN completed_at TEXT",
            "ALTER TABLE tournaments ADD COLUMN trashed_at TEXT",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tournaments_public_slug ON tournaments(public_slug)",
            "CREATE INDEX IF NOT EXISTS idx_tournaments_lifecycle_status ON tournaments(lifecycle_status)",
        ),
    ),
    Migration(
        9,
        "participant_privacy_and_admin_codes_v106",
        (
            "ALTER TABLE participant_access_credentials ADD COLUMN admin_code TEXT",
            "ALTER TABLE teams ADD COLUMN responsible_name TEXT",
            "ALTER TABLE teams ADD COLUMN responsible_phone TEXT",
            "ALTER TABLE teams ADD COLUMN responsible_email TEXT",
            "ALTER TABLE teams ADD COLUMN responsible_contact_protected INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE players ADD COLUMN first_name TEXT",
            "ALTER TABLE players ADD COLUMN last_name TEXT",
            "ALTER TABLE players ADD COLUMN is_protected INTEGER NOT NULL DEFAULT 0",
        ),
    ),
    Migration(
        10,
        "team_messaging_v108",
        (
            """CREATE TABLE IF NOT EXISTS team_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                sender_type TEXT NOT NULL CHECK(sender_type IN ('team','organizer')),
                sender_team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
                recipient_type TEXT NOT NULL CHECK(recipient_type IN ('team','organizer')),
                recipient_team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                read_at TEXT
            )""",
            "CREATE INDEX IF NOT EXISTS idx_team_messages_tournament_created ON team_messages(tournament_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_team_messages_recipient_team ON team_messages(tournament_id, recipient_type, recipient_team_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_team_messages_sender_team ON team_messages(tournament_id, sender_type, sender_team_id, created_at)",
        ),
    ),
    Migration(
        11,
        "age_classes_v109",
        (
            "ALTER TABLE tournaments ADD COLUMN age_classes_json TEXT NOT NULL DEFAULT '[]'",
            "ALTER TABLE teams ADD COLUMN age_class TEXT",
            "ALTER TABLE groups ADD COLUMN age_class TEXT",
            "CREATE INDEX IF NOT EXISTS idx_teams_tournament_age_class ON teams(tournament_id, age_class)",
            "CREATE INDEX IF NOT EXISTS idx_groups_tournament_age_class ON groups(tournament_id, age_class)",
        ),
    ),
)


def _execute(con, sql, params=()):
    return con.execute(sql, params)


def ensure_migration_table(con):
    _execute(
        con,
        """
        CREATE TABLE IF NOT EXISTS cupnavi_schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """,
    )


def current_schema_version(con):
    ensure_migration_table(con)
    row = _execute(
        con,
        "SELECT COALESCE(MAX(version), 0) FROM cupnavi_schema_migrations",
    ).fetchone()
    return int(row[0] if row is not None else 0)


def apply_migrations(con):
    """Applicera alla saknade migreringar och returnera nya versionsnummer."""
    ensure_migration_table(con)
    current = current_schema_version(con)
    applied = []

    for migration in MIGRATIONS:
        if migration.version <= current:
            continue
        for statement in migration.statements:
            _execute(con, statement)
        _execute(
            con,
            "INSERT INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(?,?,?)",
            (
                migration.version,
                migration.name,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        applied.append(migration.version)
    return applied
