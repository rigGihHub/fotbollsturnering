from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-414-PITCH-TIMING-MODE"


def test_score_flow_has_explicit_simple_and_advanced_modes():
    assert '"Rapporteringsläge"' in VIEW
    assert '["Enkel", "Avancerad"]' in VIEW
    assert 'default="Enkel"' in VIEW
    assert '_advanced_reporting = _reporting_mode == "Avancerad"' in VIEW


def test_simple_mode_keeps_core_result_path_short():
    assert '"Snabbast möjligt: välj match → ange resultat → spara."' in VIEW
    assert '"✅ Spara resultat"' in VIEW
    assert 'deps.save_quick_result(tournament_id, quick_match, quick_home_score, quick_away_score)' in VIEW
    assert 'if not _advanced_reporting:' in VIEW
    assert '"Behöver du målskyttar, assist, kort, straffar eller massinmatning? Välj Avancerad ovan."' in VIEW


def test_advanced_mode_owns_status_events_and_special_fields():
    assert 'if _advanced_reporting:' in VIEW
    assert 'st.markdown(f"**Matchstatus: {match_status_label(_current_status)}**")' in VIEW
    assert 'st.markdown("### ⚽ Livehändelser")' in VIEW
    assert 'with st.expander("Fler resultatfält & massinmatning"' in VIEW
    assert '"Avgörande vinnare"' in VIEW


def test_playoff_tie_directs_user_to_advanced_mode():
    assert "Byt till Avancerad rapportering för att registrera det." in VIEW


def test_existing_separate_match_event_workspace_remains_available():
    assert 'if reporter_section == reporter_sections[1]:' in VIEW
    assert 'key=f"reporter_event_match_{tournament_id}"' in VIEW
