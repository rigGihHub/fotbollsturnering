"""Public match-filter UI extracted from render_public_view.

This module owns the Streamlit filter panel only. Pure filtering and sorting
remain in public_match_filter_logic.py and are injected by app.py.
"""
import streamlit as st

def render_public_match_filters(
    base_matches,
    key_prefix,
    heading,
    *,
    tournament_id,
    tr,
    public_teams,
    public_team_names,
    load_public_groups,
    source_team_id,
    row_value,
    filter_matches,
    sort_public_matches,
):
    """Gemensamt filter för den sammanslagna matchsidan."""
    filtered = list(base_matches)
    filter_label = "Alla matcher"
    forced_team_id = st.session_state.pop(f"public_force_team_filter_{tournament_id}", None)

    if forced_team_id:
        filtered = [
            match_row for match_row in base_matches
            if forced_team_id in (
                source_team_id(match_row["home_source"]),
                source_team_id(match_row["away_source"]),
            )
        ]
        filter_label = public_team_names.get(forced_team_id, "Mitt lag")
        st.info(f"Visar matcher för **{filter_label}**.")

    with st.expander("Fler filter", expanded=False):
        st.markdown("<span class='cn-public-filter-marker'></span>", unsafe_allow_html=True)
        st.caption("Avgränsa matchlistan efter tävlingsklass, grupp, lag eller plan.")
        filter_mode = st.radio(
            tr("Vad vill du visa?"),
            [tr("Alla matcher"), "Tävlingsklass", tr("En grupp"), tr("Ett lag"), tr("En plan")],
            horizontal=True,
            key=f"{key_prefix}_mode_{tournament_id}",
            label_visibility="collapsed",
        )

        if forced_team_id and filter_mode == tr("Alla matcher"):
            pass
        elif filter_mode == "Tävlingsklass":
            age_options = sorted({
                str(row_value(team, "age_class", "") or "").strip()
                for team in public_teams
                if str(row_value(team, "age_class", "") or "").strip()
            })
            if age_options:
                selected_age = st.selectbox("Välj tävlingsklass", age_options, key=f"{key_prefix}_age_{tournament_id}")
                filter_label = selected_age
                allowed_team_ids = {
                    int(team["id"]) for team in public_teams
                    if row_value(team, "age_class", None) == selected_age
                }
                filtered = filter_matches(
                    base_matches,
                    mode="age",
                    selected=selected_age,
                    team_rows=public_teams,
                    source_team_id=source_team_id,
                )
            else:
                filtered = []
                st.info("Det finns inga tävlingsklasser att filtrera på.")

        elif filter_mode == tr("En grupp"):
            groups = load_public_groups()
            if groups:
                selected_group = st.selectbox(
                    tr("Välj grupp"),
                    [row["id"] for row in groups],
                    format_func=lambda group_id: next(row["name"] for row in groups if row["id"] == group_id),
                    key=f"{key_prefix}_group_{tournament_id}",
                )
                filter_label = next(row["name"] for row in groups if row["id"] == selected_group)
                filtered = filter_matches(
                    base_matches,
                    mode="group",
                    selected=selected_group,
                    source_team_id=source_team_id,
                )
            else:
                filtered = []
                st.info("Det finns inga grupper att filtrera på.")

        elif filter_mode == tr("Ett lag"):
            if public_teams:
                selected_team = st.selectbox(
                    tr("Välj lag"),
                    [row["id"] for row in public_teams],
                    format_func=lambda team_id: next(row["name"] for row in public_teams if row["id"] == team_id),
                    key=f"{key_prefix}_team_{tournament_id}",
                )
                filter_label = next(row["name"] for row in public_teams if row["id"] == selected_team)
                filtered = filter_matches(
                    base_matches,
                    mode="team",
                    selected=selected_team,
                    source_team_id=source_team_id,
                )
            else:
                filtered = []
                st.info("Det finns inga lag att filtrera på.")

        elif filter_mode == tr("En plan"):
            pitch_options = sorted({
                int(match_row["pitch_number"])
                for match_row in base_matches
                if match_row["pitch_number"] is not None
            })
            if pitch_options:
                selected_pitch = st.selectbox(
                    tr("Välj plan"), pitch_options,
                    format_func=lambda pitch_no: f"Plan {pitch_no}",
                    key=f"{key_prefix}_pitch_{tournament_id}",
                )
                filter_label = f"Plan {selected_pitch}"
                filtered = filter_matches(
                    base_matches,
                    mode="pitch",
                    selected=selected_pitch,
                    source_team_id=source_team_id,
                )
            else:
                filtered = []
                st.info("Det finns inga planer att filtrera på.")
        elif not forced_team_id:
            filtered = list(base_matches)
            filter_label = "Alla matcher"

    return (
        sort_public_matches(filtered),
        filter_mode,
        filter_label,
    )
