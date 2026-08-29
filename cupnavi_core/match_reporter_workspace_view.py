"""Streamlit orchestration for the Match Reporter workspace.

All database writes and optimistic-locking persistence stay behind injected
callbacks owned by ``app.py``. This module owns widgets, session-state flow,
read-only repository calls and presentation orchestration only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from cupnavi_core.match_event_logic import prepare_changed_event_rows
from cupnavi_core.match_reporter_logic import (
    build_bulk_result_rows,
    prepare_bulk_result_update,
    select_playable_matches,
)
from cupnavi_core.match_reporter_repository import (
    fetch_completed_matches,
    fetch_match_team_players,
    fetch_player_match_stats,
    fetch_referee_acknowledged_match_ids,
    fetch_referee_assignments,
    fetch_referees,
    fetch_scheduled_matches,
    fetch_teams,
)
from cupnavi_core.match_reporter_view import (
    build_event_player_rows,
    build_offline_draft_html,
    build_offline_match_options,
    build_reporter_columns,
    referee_assignment_markdown,
)
from cupnavi_core.rules import validate_match_event_totals


@dataclass(frozen=True)
class MatchReporterWorkspaceDeps:
    query_all: Callable[..., list[Any]]
    resolve_source: Callable[[str], int | None]
    source_label: Callable[[str], str]
    swedish_datetime: Callable[[Any], str]
    match_result_label: Callable[[Any], str]
    team: Callable[[int], Any]
    row_value: Callable[[Any, str, Any], Any]
    translate: Callable[[str], str]
    render_empty_state: Callable[[str, str, str], None]
    save_quick_result: Callable[[int, Any, int, int], bool]
    save_bulk_results: Callable[[int, dict[int, Any], list[dict[str, Any]]], dict[str, Any]]
    save_event_rows: Callable[[list[dict[str, Any]]], dict[str, int]]
    acknowledge_referee: Callable[[int, int, int], None]


def render_match_reporter_workspace(tournament_id: int, tournament: Any, deps: MatchReporterWorkspaceDeps) -> None:
    st.title(f"📝 Matchrapportör · {tournament['name']}")
    st.caption(
        "Här kan du endast rapportera resultat samt mål, assist, varningar och utvisningar. "
        "Övrig administration är inte tillgänglig."
    )
    result_tab, event_tab, referee_tab, offline_tab = st.tabs([
        deps.translate("CupNavi Score"), deps.translate("Matchhändelser"),
        deps.translate("Domarcentral"), deps.translate("Offlineutkast")
    ])

    with result_tab:
        matches = fetch_scheduled_matches(deps.query_all, tournament_id)
        playable_matches = select_playable_matches(matches, resolve_source=deps.resolve_source)
        if "reporter_result_message" in st.session_state:
            st.success(st.session_state.pop("reporter_result_message"), icon="✅")
        if "reporter_conflict_message" in st.session_state:
            st.warning(st.session_state.pop("reporter_conflict_message"))
        if not playable_matches:
            st.info("Det finns ännu inga schemalagda matcher med två klara lag.")
        else:
            st.markdown("### ⚡ CupNavi Score")
            by_id = {int(row["id"]): row for row in playable_matches}
            quick_match_id = st.selectbox(
                "Välj match för snabbresultat", list(by_id),
                format_func=lambda match_id: deps.match_result_label(by_id[int(match_id)]),
                key=f"quick_score_match_{tournament_id}",
            )
            quick_match = by_id[int(quick_match_id)]
            quick_home_name = deps.source_label(quick_match["home_source"])
            quick_away_name = deps.source_label(quick_match["away_source"])
            draft_key = f"quick_score_draft_{quick_match_id}"
            if draft_key not in st.session_state:
                st.session_state[draft_key] = [int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)]
            quick_home_score, quick_away_score = st.session_state[draft_key]
            qh, qc, qa = st.columns([2, 1, 2])
            qh.markdown(f"**{quick_home_name}**"); qa.markdown(f"**{quick_away_name}**")
            qh_minus, qh_plus = qh.columns(2); qa_minus, qa_plus = qa.columns(2)
            if qh_minus.button("−", key=f"qs_hm_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][0] = max(0, quick_home_score - 1); st.rerun()
            if qh_plus.button("+", key=f"qs_hp_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][0] = quick_home_score + 1; st.rerun()
            if qa_minus.button("−", key=f"qs_am_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][1] = max(0, quick_away_score - 1); st.rerun()
            if qa_plus.button("+", key=f"qs_ap_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][1] = quick_away_score + 1; st.rerun()
            qc.markdown(f"<div style='text-align:center;font-size:30px;font-weight:900;padding-top:8px'>{quick_home_score}–{quick_away_score}</div>", unsafe_allow_html=True)
            save_col, reset_col = st.columns(2)
            playoff_tie_needs_detail = quick_match["stage"] != "Gruppspel" and quick_home_score == quick_away_score
            if save_col.button("✅ Spara slutresultat", key=f"qs_save_{quick_match_id}", type="primary", use_container_width=True, disabled=playoff_tie_needs_detail):
                if not deps.save_quick_result(tournament_id, quick_match, quick_home_score, quick_away_score):
                    st.error("Resultatet ändrades av en annan användare innan du hann spara. Sidan laddas om så att du ser det senaste resultatet.")
                    st.session_state.pop(draft_key, None); st.rerun()
                st.session_state["reporter_result_message"] = "Slutresultatet är sparat."; st.rerun()
            if reset_col.button("Återställ utkast", key=f"qs_reset_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key] = [int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)]; st.rerun()
            if playoff_tie_needs_detail:
                st.info("Oavgjord slutspelsmatch behöver avgörande uppgifter. Använd tabellen nedan för straffar/lottning.")
            st.divider(); st.caption("Tabellen nedan finns kvar för massinmatning och slutspelsavgöranden.")

            team_rows = fetch_teams(deps.query_all, tournament_id)
            team_name_by_id = {row["id"]: row["name"] for row in team_rows}
            team_id_by_name = {row["name"]: row["id"] for row in team_rows}
            decision_options = ["–"] + [row["name"] for row in team_rows]
            result_rows = build_bulk_result_rows(playable_matches, source_label=deps.source_label, swedish_datetime=deps.swedish_datetime, team_name_by_id=team_name_by_id)
            edited_results = st.data_editor(
                pd.DataFrame(result_rows), hide_index=True, use_container_width=True,
                disabled=["match_id", "Match", "Plan", "Fas", "Hemmalag", "Bortalag"],
                column_order=["Match", "Plan", "Fas", "Hemmalag", "Hemmamål", "Bortamål", "Bortalag", "Hemmastraffar", "Bortastraffar", "Avgörande vinnare"],
                column_config={
                    "Hemmamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Bortamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Hemmastraffar": st.column_config.NumberColumn("Straffar hemma", min_value=0, max_value=99, step=1),
                    "Bortastraffar": st.column_config.NumberColumn("Straffar borta", min_value=0, max_value=99, step=1),
                    "Avgörande vinnare": st.column_config.SelectboxColumn(options=decision_options),
                }, key=f"reporter_results_{tournament_id}",
            )
            original_by_id = {int(row["id"]): row for row in playable_matches}
            updates, info_messages, error_messages = [], [], []
            for _, row in edited_results.iterrows():
                match_id = int(row["match_id"]); original = original_by_id[match_id]
                prepared = prepare_bulk_result_update(row, original, team_id_by_name=team_id_by_name, playoff_tie_rule=tournament["playoff_tie_rule"], is_na=pd.isna)
                info_messages.extend(prepared["info"]); error_messages.extend(prepared["errors"])
                if prepared["update"] is not None: updates.append(prepared["update"])
            for message in error_messages: st.error(message)
            for message in info_messages: st.info(message)
            if updates:
                outcome = deps.save_bulk_results(tournament_id, original_by_id, updates)
                if outcome["saved"]: st.session_state["reporter_result_message"] = "Sparat automatiskt"
                if outcome["conflicts"]:
                    st.session_state["reporter_conflict_message"] = f"{outcome['conflicts']} match(er) hade ändrats av en annan rapportör och skrevs inte över. De senaste värdena har laddats om."
                st.rerun()
            st.caption("✓ Kompletta resultat sparas automatiskt.")

    with event_tab:
        played_matches = fetch_completed_matches(deps.query_all, tournament_id)
        playable_matches = select_playable_matches(played_matches, resolve_source=deps.resolve_source)
        if not playable_matches:
            st.info("Rapportera först ett matchresultat. Därefter kan matchhändelser registreras.")
        else:
            by_id = {int(row["id"]): row for row in playable_matches}
            match_id = st.selectbox("Välj match", list(by_id), format_func=lambda selected_id: deps.match_result_label(by_id[int(selected_id)]), key=f"reporter_event_match_{tournament_id}")
            match_row = by_id[int(match_id)]
            home_team_id = deps.resolve_source(match_row["home_source"]); away_team_id = deps.resolve_source(match_row["away_source"])
            for selected_team_id in [home_team_id, away_team_id]:
                selected_team = deps.team(selected_team_id)
                roster_snapshot = fetch_match_team_players(deps.query_all, match_id, selected_team_id)
                registered_match_roster, players = roster_snapshot["registered"], roster_snapshot["players"]
                st.markdown(f"#### {selected_team['name']}")
                if registered_match_roster: st.caption(f"Matchtrupp registrerad · {len(registered_match_roster)} spelare. Endast dessa kan få matchhändelser.")
                elif players: st.warning("Matchtrupp saknas. Alla spelare visas tills en matchtrupp registreras.")
                if not players: st.warning("Laget saknar registrerade spelare."); continue
                existing = {row["player_id"]: row for row in fetch_player_match_stats(deps.query_all, match_id, selected_team_id)}
                data = pd.DataFrame(build_event_player_rows(players, existing))
                reporter_columns = build_reporter_columns(
                    assist_enabled=bool(deps.row_value(tournament, "enable_assist_leaderboard", 1)),
                    card_statistics_enabled=bool(deps.row_value(tournament, "enable_card_statistics", 1)),
                )
                edited = st.data_editor(data, hide_index=True, use_container_width=True, disabled=["player_id", "Nr", "Spelare"], column_order=reporter_columns,
                    column_config={"Mål": st.column_config.NumberColumn(min_value=0, step=1), "Assist": st.column_config.NumberColumn(min_value=0, step=1), "Varningar": st.column_config.NumberColumn(min_value=0, step=1), "Utvisningar": st.column_config.NumberColumn(min_value=0, step=1)},
                    key=f"reporter_stats_{match_id}_{selected_team_id}")
                team_goals = int(match_row["home_score"] if selected_team_id == home_team_id else match_row["away_score"])
                entered_goals = int(edited["Mål"].fillna(0).sum()); entered_assists = int(edited["Assist"].fillna(0).sum())
                validation = validate_match_event_totals(team_goals, entered_goals, entered_assists)
                for message in validation["errors"]: st.error(f"{selected_team['name']}: {message}")
                autosave_key = f"reporter_event_saved_{match_id}_{selected_team_id}"
                if autosave_key in st.session_state: st.success(st.session_state.pop(autosave_key), icon="✅")
                conflict_key = f"reporter_event_conflict_{match_id}_{selected_team_id}"
                if conflict_key in st.session_state: st.warning(st.session_state.pop(conflict_key), icon="⚠️")
                if not validation["errors"]:
                    changed_rows = prepare_changed_event_rows((edited_row for _, edited_row in edited.iterrows()), existing, match_id=match_id, is_na=pd.isna)
                    if changed_rows:
                        outcome = deps.save_event_rows(changed_rows)
                        if outcome["conflicts"]: st.session_state[conflict_key] = f"{outcome['conflicts']} spelarrad(er) hade ändrats av en annan rapportör och skrevs inte över. Senaste värden laddas om."
                        if outcome["saved"]: st.session_state[autosave_key] = "Sparat automatiskt"
                        st.rerun()
                st.caption(f"Matchresultat: {team_goals} mål · registrerade spelarmål: {entered_goals} · registrerade assist: {entered_assists}")

    with referee_tab:
        st.markdown("### 🧑‍⚖️ Domarcentral")
        st.caption("Domare kan se sitt dagsprogram och bekräfta att uppdraget är sett. Ingen adminnavigation visas här.")
        referee_rows = fetch_referees(deps.query_all, tournament_id)
        if not referee_rows:
            deps.render_empty_state("Inga domare ännu", "Lägg till domare för att kunna använda automatisk domartillsättning.", "🧑‍⚖️")
        else:
            names = {int(row["id"]): row["name"] for row in referee_rows}
            referee_id = st.selectbox("Välj domare", list(names), format_func=lambda rid: names[int(rid)], key=f"reporter_referee_{tournament_id}")
            assignments = fetch_referee_assignments(deps.query_all, tournament_id, referee_id)
            acked = fetch_referee_acknowledged_match_ids(deps.query_all, tournament_id, referee_id)
            if not assignments: st.info("Domaren har inga schemalagda matcher ännu.")
            for assignment in assignments:
                with st.container(border=True):
                    st.markdown(referee_assignment_markdown(assignment, swedish_datetime=deps.swedish_datetime, source_label=deps.source_label))
                    if assignment["id"] in acked: st.success("Uppdraget är bekräftat.", icon="✅")
                    elif st.button("Bekräfta att jag sett matchen", key=f"ref_ack_{referee_id}_{assignment['id']}", use_container_width=True):
                        deps.acknowledge_referee(tournament_id, referee_id, int(assignment["id"])); st.rerun()

    with offline_tab:
        st.markdown("### 📶 Offlineutkast")
        st.caption("Streamlit kräver serverkontakt för riktig synkronisering. Den här säkerhetsfunktionen sparar därför ett lokalt resultatutkast i webbläsaren om nätet blir dåligt. Utkastet ligger kvar på enheten och kan föras över till CupNavi Score när nätet återkommer.")
        offline_matches = fetch_scheduled_matches(deps.query_all, tournament_id)
        offline_options = build_offline_match_options(offline_matches, swedish_datetime=deps.swedish_datetime, source_label=deps.source_label)
        components.html(build_offline_draft_html(offline_options, tournament_id), height=210, scrolling=False)
