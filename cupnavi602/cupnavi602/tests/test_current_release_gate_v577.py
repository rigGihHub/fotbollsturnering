from pathlib import Path
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VIEW = (ROOT / 'cupnavi_core' / 'cup_document_creator_view.py').read_text(encoding='utf-8')
MIG = (ROOT / 'cupnavi_core' / 'migrations.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')


def test_v577_version_and_persistent_initial_import_schema():
    assert '2026.09.09-577-INITIAL-IMPORT-CARRIES-GROUPS' in VERSION
    assert '2026.09.09-577-INITIAL-IMPORT-CARRIES-GROUPS' in APP
    assert 'LATEST_SCHEMA_VERSION = 35' in MIG
    assert 'CREATE TABLE IF NOT EXISTS tournament_setup_imports' in MIG
    assert 'payload_json TEXT NOT NULL' in MIG


def test_initial_scan_explicitly_carries_groups_forward_to_step_three():
    assert 'Gruppindelningen följer med från den här första importen' in VIEW
    assert 'Du behöver inte läsa in samma foto en gång till.' in VIEW
    assert 'save_setup_import_snapshot' in APP
    assert 'load_setup_import_snapshot' in APP
    assert '📦 Från första importen' in APP
    assert '✓ Använd grupperna från första importen' in APP


def test_initial_team_import_defers_group_assignment_unless_imported_schedule_needs_it():
    assert 'def apply_document_teams(connection_factory, tournament_id, prefill, *, assign_groups=False)' in VIEW
    assert 'assign_groups=_use_doc_matches' in APP
    assert 'Gruppindelning från första scanningen ska normalt granskas i Steg 3' in APP


def test_later_group_apply_is_review_first_and_never_overwrites_existing_groups():
    assert 'def apply_document_groups' in VIEW
    assert 'Cupen har redan grupper.' in VIEW
    assert 'skriver inte över något' in VIEW
    assert 'Gruppindelningen finns redan i cupen.' in APP
    assert 'skriver aldrig över befintliga grupper' in APP


def test_snapshot_helpers_roundtrip_and_group_apply(tmp_path):
    from cupnavi_core.cup_document_creator_view import (
        save_setup_import_snapshot,
        load_setup_import_snapshot,
        apply_document_groups,
    )

    db_path = tmp_path / "v577.sqlite"
    con = sqlite3.connect(db_path)
    con.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY, schedule_dirty INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE teams(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,name TEXT NOT NULL,group_id INTEGER);
        CREATE TABLE groups(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,name TEXT NOT NULL);
        CREATE TABLE tournament_setup_imports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,import_kind TEXT NOT NULL DEFAULT 'initial_setup',
            source_name TEXT,payload_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO tournaments(id) VALUES(1);
        INSERT INTO teams(tournament_id,name) VALUES(1,'ÖSK P2014 Svart'),(1,'Karlslund P2014');
    ''')
    con.commit(); con.close()

    def factory():
        return sqlite3.connect(db_path)

    payload = {
        'source_name': 'foto1.jpg',
        'teams': [
            {'name': 'ÖSK P2014 Svart', 'group_name': 'Grupp A'},
            {'name': 'Karlslund P2014', 'group_name': 'Grupp A'},
        ],
    }
    save_setup_import_snapshot(factory, 1, payload)
    loaded = load_setup_import_snapshot(factory, 1)
    assert loaded['source_name'] == 'foto1.jpg'
    result = apply_document_groups(factory, 1, loaded)
    assert result == {'groups': 1, 'assigned': 2, 'unmatched': []}
    con = factory()
    assert con.execute('SELECT COUNT(*) FROM groups').fetchone()[0] == 1
    assert con.execute('SELECT COUNT(*) FROM teams WHERE group_id IS NOT NULL').fetchone()[0] == 2
    con.close()
