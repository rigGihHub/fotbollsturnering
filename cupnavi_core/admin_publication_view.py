"""Streamlit presentation for publication and lifecycle controls."""

from __future__ import annotations

from typing import Callable, Sequence

from cupnavi_core.admin_publication import (
    build_publish_blockers,
    publication_action_label,
    split_schedule_warnings,
)


def render_admin_publication_controls(
    *,
    tournament_id: int,
    is_published: bool,
    published_once: bool,
    playoff_model_confirmed: bool,
    scheduled_matches: int,
    schedule_dirty: bool,
    schedule_errors: Sequence[str],
    schedule_warnings: Sequence[str],
    publish_now: Callable[[], tuple[bool, str]],
    unpublish_now: Callable[[], tuple[bool, str]],
) -> None:
    """Render equivalent sidebar + mobile publication controls from one state model."""
    import streamlit as st

    blocking_warnings, advisory_warnings = split_schedule_warnings(schedule_warnings)

    st.sidebar.divider()
    st.sidebar.subheader("Publicering")
    if is_published:
        st.sidebar.success("Publicerad")
    else:
        st.sidebar.caption("Turneringsvyn är ett utkast.")

    sidebar_warnings_approved = st.sidebar.checkbox(
        "Jag har granskat schemavarningarna",
        disabled=not bool(blocking_warnings),
        key=f"sidebar_warning_approval_{tournament_id}",
    )
    mobile_warnings_approved = bool(st.session_state.get(f"mobile_warning_approval_{tournament_id}", False))
    all_warnings_approved = bool(sidebar_warnings_approved or mobile_warnings_approved)

    publish_blockers = build_publish_blockers(
        playoff_model_confirmed=playoff_model_confirmed,
        scheduled_matches=scheduled_matches,
        schedule_dirty=schedule_dirty,
        schedule_errors=schedule_errors,
        blocking_warnings=blocking_warnings,
        warnings_approved=all_warnings_approved,
    )
    publish_blocked = bool(publish_blockers)

    if publish_blocked:
        st.sidebar.error("Kan inte publicera ännu")
        for reason in publish_blockers:
            st.sidebar.markdown(f"• {reason}")

        if schedule_errors:
            with st.sidebar.expander(f"Visa schemafel ({len(schedule_errors)})"):
                for index, error in enumerate(schedule_errors[:10], 1):
                    st.markdown(f"**{index}.** {error}")
                if len(schedule_errors) > 10:
                    st.caption(f"Ytterligare {len(schedule_errors) - 10} fel visas under Kontroller/Schema.")

        if blocking_warnings:
            with st.sidebar.expander(f"Visa schemavarningar ({len(blocking_warnings)})"):
                for index, warning in enumerate(blocking_warnings[:10], 1):
                    st.markdown(f"**{index}.** {warning}")
                if len(blocking_warnings) > 10:
                    st.caption(
                        f"Ytterligare {len(blocking_warnings) - 10} varningar visas under Kontroller/Schema."
                    )
    else:
        st.sidebar.success("✓ Alla publiceringskrav är uppfyllda.")

    if advisory_warnings:
        with st.sidebar.expander(f"Notiser – blockerar inte ({len(advisory_warnings)})"):
            for index, warning in enumerate(advisory_warnings[:10], 1):
                st.markdown(f"**{index}.** {warning}")
            st.caption("Dessa notiser stoppar inte publicering.")

    action_label = publication_action_label(published_once=published_once)
    if st.sidebar.button(
        action_label,
        type="primary",
        use_container_width=True,
        disabled=publish_blocked,
        key=f"publish_from_any_admin_page_{tournament_id}",
    ):
        changed, _reason = publish_now()
        if not changed:
            st.sidebar.warning("Publiceringsstatusen ändrades av en annan administratör. Senaste status laddas om.")
        st.rerun()

    if st.sidebar.button(
        "Avpublicera",
        use_container_width=True,
        disabled=not is_published,
        key=f"unpublish_from_any_admin_page_{tournament_id}",
    ):
        changed, _reason = unpublish_now()
        if not changed:
            st.sidebar.warning("Publiceringsstatusen ändrades av en annan administratör. Senaste status laddas om.")
        st.rerun()

    # v159: Publicering får inte vara beroende av sidebaren. På mobil ligger denna
    # kontroll direkt i huvudinnehållet och använder exakt samma validering.
    with st.container(border=True):
        st.markdown("#### 📣 Publicering")
        if is_published:
            st.success("Turneringen är publicerad. Sparade resultat visas automatiskt i turneringsvyn.")
        else:
            st.caption("Turneringsvyn är fortfarande ett utkast tills du publicerar den.")

        if blocking_warnings:
            st.checkbox(
                "Jag har granskat schemavarningarna",
                key=f"mobile_warning_approval_{tournament_id}",
            )

        if publish_blocked:
            st.warning("Kan inte publicera ännu: " + " ".join(publish_blockers))

        mobile_publish_col, _publish_spacer = st.columns([1, 1])
        if mobile_publish_col.button(
            f"📣 {action_label}",
            type="primary",
            use_container_width=True,
            disabled=publish_blocked,
            key=f"mobile_publish_from_admin_{tournament_id}",
        ):
            changed, _reason = publish_now()
            st.session_state["mobile_publish_message"] = (
                "✓ Turneringsvyn är publicerad och synkad."
                if changed
                else "Publiceringsstatusen ändrades av en annan administratör. Senaste status har laddats."
            )
            st.rerun()

        if is_published:
            with st.expander("Fler publiceringsval", expanded=False):
                if st.button("Avpublicera", key=f"mobile_unpublish_from_admin_{tournament_id}"):
                    changed, _reason = unpublish_now()
                    if not changed:
                        st.session_state["mobile_publish_message"] = (
                            "Publiceringsstatusen ändrades av en annan administratör. "
                            "Senaste status har laddats."
                        )
                    st.rerun()
        if "mobile_publish_message" in st.session_state:
            st.success(st.session_state.pop("mobile_publish_message"))


def render_admin_lifecycle_controls(
    *,
    tournament_id: int,
    lifecycle: str,
    is_published: bool,
    completion_state,
    set_lifecycle: Callable[[str, str], tuple[bool, str]],
    add_completion_feed_item: Callable[[], None],
) -> None:
    """Render guarded published -> live -> completed lifecycle actions."""
    import streamlit as st

    if lifecycle == "published" and is_published:
        if st.sidebar.button("🔴 Markera cupen som pågående", use_container_width=True, key=f"mark_live_{tournament_id}"):
            changed, _reason = set_lifecycle("published", "live")
            if not changed:
                st.sidebar.warning("Cupstatusen ändrades av en annan administratör. Senaste status laddas om.")
            st.rerun()

    if lifecycle in ("published", "live"):
        if not completion_state.can_complete:
            st.sidebar.caption(
                f"Avsluta cup: {completion_state.played}/{completion_state.total} publicerade matcher färdigrapporterade."
            )
        if st.sidebar.button(
            "🏁 Avsluta cup",
            disabled=not completion_state.can_complete,
            use_container_width=True,
            key=f"complete_cup_{tournament_id}",
        ):
            changed, _reason = set_lifecycle(lifecycle, "completed")
            if changed:
                add_completion_feed_item()
            else:
                st.sidebar.warning(
                    "Cupstatusen ändrades av en annan administratör. Cupen avslutades inte från den här äldre vyn."
                )
            st.rerun()
