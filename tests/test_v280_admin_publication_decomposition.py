from pathlib import Path

from cupnavi_core.admin_publication import (
    build_completion_state,
    build_publish_blockers,
    publication_action_label,
    split_schedule_warnings,
)

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "admin_publication_view.py").read_text(encoding="utf-8")
REPO = (ROOT / "cupnavi_core" / "admin_publication_repository.py").read_text(encoding="utf-8")


def test_warning_split_keeps_kit_clashes_advisory_only():
    blocking, advisory = split_schedule_warnings([
        "Domare saknas",
        "Färgkrock mellan hemmatröja och bortatröja",
        "Extraställ kan behövas",
    ])
    assert blocking == ["Domare saknas"]
    assert advisory == [
        "Färgkrock mellan hemmatröja och bortatröja",
        "Extraställ kan behövas",
    ]


def test_publish_blockers_preserve_existing_admin_rules():
    blockers = build_publish_blockers(
        playoff_model_confirmed=False,
        scheduled_matches=4,
        schedule_dirty=True,
        schedule_errors=["fel"],
        blocking_warnings=["varning"],
        warnings_approved=False,
    )
    assert blockers == [
        "Slutspelsmodell och cupregler måste sparas på Översikt.",
        "Schemat är inaktuellt eftersom förutsättningarna har ändrats. Regenerera schemat.",
        "1 blockerande schemafel måste åtgärdas.",
    ]


def test_publish_action_label_preserves_first_publish_history_semantics():
    assert publication_action_label(published_once=False) == "Publicera"
    assert publication_action_label(published_once=True) == "Uppdatera"


def test_completion_requires_all_published_scheduled_matches_and_public_lifecycle():
    assert build_completion_state(total=3, played=3, lifecycle="live").can_complete
    assert not build_completion_state(total=3, played=2, lifecycle="live").can_complete
    assert not build_completion_state(total=0, played=0, lifecycle="published").can_complete
    assert not build_completion_state(total=3, played=3, lifecycle="draft").can_complete


def test_app_delegates_publication_and_lifecycle_rendering():
    assert "render_admin_publication_controls(" in APP
    assert "render_admin_lifecycle_controls(" in APP
    assert "fetch_lifecycle_match_counts(one_row, tid)" in APP
    assert 'st.sidebar.subheader("Publicering")' not in APP
    assert 'st.sidebar.subheader("Publicering")' in VIEW


def test_publication_mutation_compare_and_set_remains_in_app():
    assert "def _set_publication_if_current(" in APP
    assert "def _set_lifecycle_if_current(" in APP
    assert "expected_lifecycle=tournament_lifecycle" in APP
    assert "publish_now=_publish_tournament_now" in APP
    assert "unpublish_now=_unpublish_tournament_now" in APP


def test_lifecycle_count_sql_is_read_only_repository_code():
    assert "schedule_published=1" in REPO
    assert "UPDATE " not in REPO
    assert "INSERT " not in REPO
    assert "DELETE " not in REPO
