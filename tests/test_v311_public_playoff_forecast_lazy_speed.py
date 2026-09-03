from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "cupnavi_core" / "public_statistics_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_playoff_forecast_is_explicitly_lazy():
    playoff = SRC.index('if stats_section == tr("Slutspel"):')
    gate = SRC.index('show_playoff_forecast = st.toggle(', playoff)
    guarded = SRC.index('if show_playoff_forecast:', gate)
    table_calc = SRC.index('calculate_all_group_tables(tournament_id, tournament)', guarded)
    preview = SRC.index('playoff_preview(forecast_tables, tournament["playoff_format"])', table_calc)
    playoff_mode = SRC.index('if tournament["playoff_format"] == "Inget slutspel":', preview)
    assert playoff < gate < guarded < table_calc < preview < playoff_mode


def test_default_playoff_path_no_longer_uses_forecast_expander():
    playoff = SRC[SRC.index('if stats_section == tr("Slutspel"):'):]
    before_brackets = playoff[:playoff.index('if tournament["playoff_format"] == "Inget slutspel":')]
    assert 'st.expander("🔮 Slutspelsprognos' not in before_brackets
    assert '"🔮 Visa slutspelsprognos"' in before_brackets


def test_forecast_has_empty_state_without_affecting_brackets():
    assert 'Det finns ännu inte tillräckligt med tabellunderlag för en slutspelsprognos.' in SRC
    assert 'brackets_for_display(tournament_id)' in SRC
    assert 'render_bracket_tree(bracket["id"], public=True' in SRC
