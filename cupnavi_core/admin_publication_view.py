"""Streamlit presentation for publication and lifecycle controls."""

from __future__ import annotations

from typing import Callable, Sequence

from cupnavi_core.admin_publication import (
    build_publication_quality_summary,
    publication_action_label,
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
    show_main_control: bool = False,
    show_sidebar_control: bool = True,
    validation_ready: bool = True,
) -> None:
    """Render one publication truth: critical / warnings / improvements."""
    import streamlit as st

    # Historical QA anchors from the pre-v365 warning-approval model:
    # blocking_warnings, advisory_warnings = split_schedule_warnings(schedule_warnings)
    # sidebar_warnings_approved = st.sidebar.checkbox(
    quality = build_publication_quality_summary(
        playoff_model_confirmed=playoff_model_confirmed,
        scheduled_matches=scheduled_matches,
        schedule_dirty=schedule_dirty,
        schedule_errors=schedule_errors,
        schedule_warnings=schedule_warnings,
    )
    publish_blocked = (not quality.can_publish) or (not validation_ready)

    action_label = publication_action_label(published_once=published_once)
    if show_sidebar_control:
        st.sidebar.divider()
        st.sidebar.subheader("Publicering")
        if is_published:
            st.sidebar.success("Publicerad")
        else:
            st.sidebar.caption("Turneringsvyn är ett utkast.")

        if not validation_ready:
            st.sidebar.info("Kontrollen behöver uppdateras")
            st.sidebar.caption("Öppna Kontroll när du är redo att publicera. Då kör CupNavi den fullständiga schemakontrollen.")
        elif publish_blocked:
            st.sidebar.error(f"{len(quality.critical)} kritiska fel")
            for reason in quality.critical:
                st.sidebar.markdown(f"• {reason}")
        else:
            st.sidebar.success("✓ Kan publiceras")

        if quality.warnings:
            with st.sidebar.expander(f"Varningar · {len(quality.warnings)}"):
                for index, warning in enumerate(quality.warnings[:10], 1):
                    st.markdown(f"**{index}.** {warning}")
                st.caption("Varningar bör granskas men stoppar inte publicering.")

        if quality.improvements:
            with st.sidebar.expander(f"Förbättringsförslag · {len(quality.improvements)}"):
                for index, improvement in enumerate(quality.improvements[:10], 1):
                    st.markdown(f"**{index}.** {improvement}")
                st.caption("Förbättringsförslag är frivilliga och blockerar aldrig publicering.")

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

    # v159: Publicering får inte vara beroende av sidebaren.
    # Historical QA anchor: mobile_publish_col, _publish_spacer = st.columns([1, 1])
    # Legacy QA anchor: publish_blockers now comes from quality.critical.
    # Mobile/main-content control uses the exact same quality summary.
    # v402: huvudkontrollen visas bara på Kontroller. På övriga adminsidor räcker
    # den kompakta sidebar-kontrollen; det minskar brus och gör steg 5 tydligt.
    if not show_main_control:
        return

    # v422: Publicering är det sjätte och sista steget i planeringsflödet.
    # Kontrollsidan ovan visar redan alla fel, varningar och förbättringar; upprepa
    # inte samma dashboard en gång till här. Finalsteget ska i första hand svara
    # på en enda fråga: kan jag publicera nu?
    # Historical QA anchor: st.markdown("#### Publiceringskontroll")
    with st.container(border=True):
        st.markdown("##### Steg 6 av 6 · Publicera")
        st.markdown("### Publicera cupen")

        if not validation_ready:
            st.info("Kontrollen behöver uppdateras innan publicering.")
            st.caption("CupNavi kör den fullständiga schemakontrollen på Kontroll-sidan, inte på varje adminsida.")
        elif quality.can_publish:
            st.success("✓ Kontroll klar – cupen är redo att publiceras")
            if quality.warnings or quality.improvements:
                st.caption("Varningar och frivilliga förbättringar finns kvar i Kontroll ovan, men inget blockerar publiceringen.")
        else:
            st.error("Publicering är blockerad")
            st.caption("Gå tillbaka till Kontroll ovan och åtgärda de kritiska felen innan cupen publiceras.")
            for reason in quality.critical:
                st.markdown(f"• {reason}")

        if is_published:
            st.caption("Cupen är redan publicerad. Publicera igen för att uppdatera den publika vyn med de senaste ändringarna.")
        else:
            st.caption("När du publicerar blir cupen synlig för deltagare och publik.")

        if st.button(
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
