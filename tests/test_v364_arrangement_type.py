from pathlib import Path
import importlib.util
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
MIGRATIONS = (ROOT / "cupnavi_core" / "migrations.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _load_arrangement():
    spec = importlib.util.spec_from_file_location("arrangement_type_v364", ROOT / "cupnavi_core" / "arrangement_type.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_migrations():
    spec = importlib.util.spec_from_file_location("migrations_v364", ROOT / "cupnavi_core" / "migrations.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_arrangement_type_defaults_safely_to_tournament():
    mod = _load_arrangement()
    assert mod.normalize_arrangement_type(None) == "tournament"
    assert mod.normalize_arrangement_type("unknown") == "tournament"
    assert mod.arrangement_label("matchcamp") == "Matchcamp"
    assert mod.arrangement_label("tournament") == "Turnering"


def test_v28_compat_adds_column_without_changing_existing_rows():
    mod = _load_migrations()
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY, name TEXT)")
    con.execute("INSERT INTO tournaments(id,name) VALUES(1,'Historisk cup')")
    mod.ensure_v28_schema_compat(con)
    cols = {row[1] for row in con.execute("PRAGMA table_info(tournaments)").fetchall()}
    row = con.execute("SELECT arrangement_type FROM tournaments WHERE id=1").fetchone()
    assert "arrangement_type" in cols
    assert row[0] == "tournament"


def test_setup_asks_matchcamp_or_tournament_before_other_configuration():
    assert "### Vad arrangerar ni?" in SETUP
    assert "[ARRANGEMENT_MATCHCAMP, ARRANGEMENT_TOURNAMENT]" in SETUP
    assert SETUP.index("### Vad arrangerar ni?") < SETUP.index("### 1. Vilka ska spela?")


def test_matchcamp_switch_disables_tournament_only_defaults_safely():
    section = SETUP[SETUP.index('if _arrangement_choice == ARRANGEMENT_MATCHCAMP:'):SETUP.index('_sport_rec=')]
    assert "results_counted=0" in section
    assert "playoff_format='Inget slutspel'" in section
    assert "playoff_model_confirmed=1" in section
    assert "schedule_dirty=1" in section


def test_matchcamp_can_opt_in_to_results_without_enabling_playoffs():
    assert "Utan resultat · rekommenderas för matchcamp" in SETUP
    assert "Registrera resultat" in SETUP
    results_section = SETUP[SETUP.index("if _results_counted_now!=_results_counted_saved:"):SETUP.index("st.rerun()", SETUP.index("if _results_counted_now!=_results_counted_saved:"))]
    assert '"Inget slutspel"' in results_section
    assert "if _is_matchcamp" in results_section


def test_schema_and_version():
    assert "LATEST_SCHEMA_VERSION = 32" in MIGRATIONS
    assert 'APP_BUILD_VERSION = "2026.09.03-427-TRAVEL-RULES-FLOW"' in APP
