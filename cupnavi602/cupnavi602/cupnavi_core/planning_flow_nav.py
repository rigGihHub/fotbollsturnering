from __future__ import annotations

FLOW_STEPS = ["Cupinfo", "Lag", "Grupper", "Regler", "Planer & tider", "Domare", "Schema", "Kontroll", "Publicera"]
FLOW_ROUTES = {
    "Cupinfo": "Cupinställningar",
    "Lag": "Lag",
    "Grupper": "Grupper",
    "Regler": "Regler",
    "Planer & tider": "Planer & tider",
    "Domare": "Domare",
    "Schema": "Skapa och publicera schema",
    "Kontroll": "Kontroller",
    # Publicering ligger på kontrollsidan direkt under kvalitetskontrollen.
    "Publicera": "Kontroller",
}


def render_clickable_planning_flow(st, *, tid: int, current_step: str, navigate_admin_page) -> None:
    """Render the nine-step journey only when the global admin shell is absent.

    v587 keeps this helper for isolated workspaces/tests, but the main admin page
    already renders the authoritative journey above every workspace. Rendering it
    again inside Lag/Grupper/Regler/etc created two competing navigators.
    """
    if st.session_state.get(f"_global_admin_flow_rendered_{tid}"):
        return
    current_index = FLOW_STEPS.index(current_step) if current_step in FLOW_STEPS else -1
    for row_start in range(0, len(FLOW_STEPS), 3):
        row_steps = FLOW_STEPS[row_start:row_start + 3]
        cols = st.columns(len(row_steps))
        for offset, (col, label) in enumerate(zip(cols, row_steps)):
            idx = row_start + offset + 1
            is_current = label == current_step
            done = current_index >= 0 and idx - 1 < current_index
            prefix = "✓" if done else str(idx)
            with col:
                def _go(target_label=label, target_page=FLOW_ROUTES[label]):
                    if target_page == "Kontroller":
                        st.session_state[f"planning_control_focus_{tid}"] = target_label
                    navigate_admin_page(target_page)

                st.button(
                    f"{prefix} {label}",
                    key=f"planning_flow_nav_{tid}_{current_step}_{label}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary",
                    disabled=is_current,
                    on_click=_go,
                )

def render_problem_actions(st, *, tid: int, navigate_admin_page, needs_teams: bool = False,
                           needs_groups: bool = False, needs_schedule: bool = False,
                           needs_setup: bool = False, needs_control: bool = False) -> None:
    """Show direct actions beside/under blockers instead of leaving users stranded."""
    actions: list[tuple[str, str]] = []
    if needs_teams:
        actions.append(("Gå till Lag →", "Lag"))
    if needs_groups:
        actions.append(("Gå till Grupper →", "Grupper"))
    if needs_setup:
        actions.append(("Gå till Cupinfo →", "Cupinställningar"))
    if needs_schedule:
        actions.append(("Gå till Schema →", "Skapa och publicera schema"))
    if needs_control:
        actions.append(("Gå till Kontroll →", "Kontroller"))
    if not actions:
        return
    cols = st.columns(min(3, len(actions)))
    for idx, (label, page) in enumerate(actions):
        cols[idx % len(cols)].button(
            label,
            key=f"problem_action_{tid}_{page}_{idx}",
            use_container_width=True,
            on_click=navigate_admin_page,
            args=(page,),
        )
