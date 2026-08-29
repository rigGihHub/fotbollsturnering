"""Admin Matchhändelser workspace orchestration.

Read queries and presentation live here. Persistence-sensitive event writes remain
in app.py and are injected through a narrow callback so the existing optimistic
locking boundary is preserved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from cupnavi_core.admin_match_events_repository import (
    fetch_played_matches,
    fetch_team_match_stats,
    fetch_team_players,
)
from cupnavi_core.match_event_logic import prepare_changed_event_rows
from cupnavi_core.match_reporter_view import build_event_player_rows, build_reporter_columns
from cupnavi_core.rules import validate_match_event_totals


@dataclass(frozen=True)
class AdminMatchEventsDependencies:
    st: Any
    all_rows: Callable[..., Any]
    resolve_source: Callable[[str], Any]
    match_result_label: Callable[[Any], str]
    team: Callable[[int], Any]
    row_value: Callable[..., Any]
    render_empty_state: Callable[..., Any]
    save_event_updates: Callable[..., Any]


def render_admin_match_events_workspace(tid, tournament, *, deps: AdminMatchEventsDependencies):
    st = deps.st
    st.header("Matchhändelser")
    st.caption("Välj en spelad match och registrera spelarnas händelser. Ändringar sparas automatiskt.")

    played_matches = fetch_played_matches(deps.all_rows, tid)
    playable_matches = [
        match_row for match_row in played_matches
        if deps.resolve_source(match_row["home_source"]) and deps.resolve_source(match_row["away_source"])
    ]
    if not playable_matches:
        deps.render_empty_state(
            "Inga spelade matcher ännu",
            "Registrera ett matchresultat först. Därefter kan mål, assist och kort läggas till.",
            symbol="—",
        )
        return

    match_by_id = {int(match_row["id"]): match_row for match_row in playable_matches}
    stat_match_id = st.selectbox(
        "Välj match",
        list(match_by_id),
        format_func=lambda match_id: deps.match_result_label(match_by_id[int(match_id)]),
    )
    stat_match = match_by_id[int(stat_match_id)]
    home_team_id = deps.resolve_source(stat_match["home_source"])
    away_team_id = deps.resolve_source(stat_match["away_source"])
    st.caption("Fyll bara i de händelser som inträffade.")

    assist_enabled = bool(deps.row_value(tournament, "enable_assist_leaderboard", 1))
    card_statistics_enabled = bool(deps.row_value(tournament, "enable_card_statistics", 1))
    admin_event_columns = build_reporter_columns(
        assist_enabled=assist_enabled,
        card_statistics_enabled=card_statistics_enabled,
    )

    for selected_team_id in [home_team_id, away_team_id]:
        selected_team = deps.team(selected_team_id)
        players = fetch_team_players(deps.all_rows, selected_team_id)
        st.markdown(f"#### {selected_team['name']}")
        if not players:
            st.warning("Laget saknar registrerade spelare.")
            continue

        existing = {
            int(row["player_id"]): row
            for row in fetch_team_match_stats(deps.all_rows, stat_match_id, selected_team_id)
        }
        data = pd.DataFrame(build_event_player_rows(players, existing))
        edited = st.data_editor(
            data,
            hide_index=True,
            use_container_width=True,
            disabled=["player_id", "Nr", "Spelare"],
            column_order=admin_event_columns,
            column_config={
                "Mål": st.column_config.NumberColumn(min_value=0, step=1),
                "Assist": st.column_config.NumberColumn(min_value=0, step=1),
                "Varningar": st.column_config.NumberColumn(min_value=0, step=1),
                "Utvisningar": st.column_config.NumberColumn(min_value=0, step=1),
            },
            key=f"stats_editor_{stat_match_id}_{selected_team_id}",
        )

        team_goals_in_match = int(
            stat_match["home_score"] if selected_team_id == home_team_id else stat_match["away_score"]
        )
        entered_goals = int(edited["Mål"].fillna(0).sum())
        entered_assists = int(edited["Assist"].fillna(0).sum())
        event_validation = validate_match_event_totals(
            team_goals_in_match, entered_goals, entered_assists
        )
        if event_validation["errors"] or entered_goals != team_goals_in_match:
            with st.expander("Kontroll av mål & assist", expanded=bool(event_validation["errors"])):
                st.caption(
                    f"Matchresultat: {team_goals_in_match} mål · registrerat: {entered_goals} mål / {entered_assists} assist."
                )
                for message in event_validation["errors"]:
                    st.error(f"{selected_team['name']}: {message}")

        autosave_message_key = f"event_autosave_message_{stat_match_id}_{selected_team_id}"
        if autosave_message_key in st.session_state:
            st.success(st.session_state.pop(autosave_message_key), icon="✅")
        event_conflict_key = f"event_autosave_conflict_{stat_match_id}_{selected_team_id}"
        if event_conflict_key in st.session_state:
            st.warning(st.session_state.pop(event_conflict_key), icon="⚠️")

        changed_event_rows = prepare_changed_event_rows(
            (row for _, row in edited.iterrows()),
            existing,
            match_id=stat_match_id,
            is_na=pd.isna,
        )

        if changed_event_rows and event_validation["ok"]:
            outcome = deps.save_event_updates(
                match_id=int(stat_match_id),
                team_id=int(selected_team_id),
                updates=changed_event_rows,
            )
            saved_count = int(outcome.get("saved_count", 0))
            conflict_count = int(outcome.get("conflict_count", 0))
            if saved_count:
                st.session_state[autosave_message_key] = "✓ Sparat automatiskt"
            if conflict_count:
                st.session_state[event_conflict_key] = (
                    f"{conflict_count} spelarrad(er) hade ändrats av en annan "
                    "användare och skrevs inte över. Senaste värden laddas om."
                )
            st.rerun()

        if changed_event_rows and not event_validation["ok"]:
            st.caption("Ändringen sparas automatiskt så snart mål/assist stämmer med matchresultatet.")
        else:
            st.caption("✓ Händelser sparas automatiskt – ingen Spara-knapp behövs.")

        registered_goals = int(edited["Mål"].fillna(0).sum())
        if registered_goals != team_goals_in_match and not event_validation["errors"]:
            st.caption(
                f"ℹ {team_goals_in_match - registered_goals:+d} mål saknar spelarkoppling, exempelvis självmål."
            )
