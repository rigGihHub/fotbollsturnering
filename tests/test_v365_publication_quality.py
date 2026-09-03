from pathlib import Path

from cupnavi_core.admin_publication import build_publication_quality_summary

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "admin_publication_view.py").read_text(encoding="utf-8")


def test_only_critical_findings_block_publication():
    summary = build_publication_quality_summary(
        playoff_model_confirmed=True,
        scheduled_matches=12,
        schedule_dirty=False,
        schedule_errors=[],
        schedule_warnings=["Domare saknas", "Färgkrock mellan hemmatröja och bortatröja"],
    )
    assert summary.can_publish
    assert summary.critical == ()
    assert summary.warnings == ("Domare saknas",)
    assert summary.improvements == ("Färgkrock mellan hemmatröja och bortatröja",)


def test_hard_schedule_error_blocks():
    summary = build_publication_quality_summary(
        playoff_model_confirmed=True,
        scheduled_matches=12,
        schedule_dirty=False,
        schedule_errors=["Lag A spelar samtidigt på två planer"],
        schedule_warnings=[],
    )
    assert not summary.can_publish
    assert any("blockerande schemafel" in item for item in summary.critical)


def test_dirty_or_missing_schedule_are_critical():
    missing = build_publication_quality_summary(
        playoff_model_confirmed=True,
        scheduled_matches=0,
        schedule_dirty=False,
        schedule_errors=[],
        schedule_warnings=[],
    )
    dirty = build_publication_quality_summary(
        playoff_model_confirmed=True,
        scheduled_matches=10,
        schedule_dirty=True,
        schedule_errors=[],
        schedule_warnings=[],
    )
    assert not missing.can_publish
    assert not dirty.can_publish


def test_main_control_page_and_publish_widget_share_same_quality_model():
    assert 'st.header("Kontroll före publicering")' in APP
    assert 'build_publication_quality_summary(' in APP
    assert 'st.markdown("#### Publiceringskontroll")' in VIEW
    assert 'build_publication_quality_summary(' in VIEW
    assert '✓ Kontroll klar – cupen är redo att publiceras' in VIEW
    assert "Endast kritiska fel stoppar publicering" in APP


def test_warning_approval_checkbox_is_removed():
    assert "Jag har granskat schemavarningarna" not in VIEW
    assert "Varningar bör granskas men stoppar inte publicering." in VIEW


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.03-423-PUBLIC-INFO-COLD-START"' in APP
