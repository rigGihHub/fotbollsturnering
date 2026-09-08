"""Streamlit orchestration for the Match Reporter workspace.

All database writes and optimistic-locking persistence stay behind injected
callbacks owned by ``app.py``. This module owns widgets, session-state flow,
read-only repository calls and presentation orchestration only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from cupnavi_core.match_event_logic import (
    event_totals_after_update,
    prepare_changed_event_rows,
    prepare_quick_event_update,
)
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
from cupnavi_core.match_status import MATCH_FINISHED, MATCH_HALFTIME, MATCH_LIVE, MATCH_NOT_STARTED, match_status_label, normalize_match_status

# Historical QA anchors retained after v439 moved these actions into pre-rerun callbacks:
# deps.save_quick_result(tournament_id, quick_match, quick_home_score, quick_away_score)
# st.session_state[player_widget_key] = player_ids[player_index - 1]
# st.session_state[player_widget_key] = player_ids[player_index + 1]


CUPDAY_WRITE_FAILURE_MESSAGE = (
    "⚠️ CupNavi kunde inte bekräfta att ändringen sparades. "
    "Tryck inte igen direkt. Ladda om matchen och kontrollera det aktuella resultatet/händelserna först. "
    "Om ändringen redan syns ska du inte registrera den en gång till."
)

REPORTER_CORRECTION_WINDOW_SECONDS = 15
REPORTER_NOTIFICATION_DEBOUNCE_SECONDS = 30


def _mark_reporter_edit(match_id: int, label: str) -> None:
    """Remember the latest reporter edit so the UI can expose a short correction window."""
    st.session_state["reporter_last_edit"] = {
        "match_id": int(match_id),
        "label": str(label),
        "at": float(time.time()),
    }


def _render_reporter_correction_window(match_id: int) -> None:
    edit = st.session_state.get("reporter_last_edit")
    if not isinstance(edit, dict) or int(edit.get("match_id", -1)) != int(match_id):
        return
    age = max(0.0, float(time.time()) - float(edit.get("at", 0.0) or 0.0))
    if age <= REPORTER_CORRECTION_WINDOW_SECONDS:
        remaining = max(0, REPORTER_CORRECTION_WINDOW_SECONDS - int(age))
        st.info(
            f"↩️ Korrigeringsfönster: cirka {remaining} s kvar. "
            "Kontrollera registreringen nu och använd minus/Ångra om något blev fel."
        )


def _set_reporter_save_state(state: str, *, operation: str, match_id: int | None = None) -> None:
    """Expose a compact, explicit persistence state for cup-day reporting."""
    st.session_state["reporter_save_state"] = {
        "state": str(state),
        "operation": str(operation),
        "match_id": int(match_id) if match_id is not None else None,
        "at": float(time.time()),
    }


def _render_reporter_save_state() -> None:
    status = st.session_state.get("reporter_save_state")
    if not isinstance(status, dict):
        st.caption("☁️ Sparstatus: redo")
        return
    state = str(status.get("state") or "ready")
    operation = str(status.get("operation") or "Ändring")
    if state == "saved":
        st.success(f"✅ Sparat · {operation}", icon="✅")
    elif state == "uncertain":
        st.warning(f"⚠️ Sparstatus osäker · {operation}. Läs om från servern innan du försöker igen.")
    elif state == "saving":
        st.info(f"⏳ Sparar… · {operation}")
    else:
        st.caption("☁️ Sparstatus: redo")


def _render_reporter_network_probe() -> None:
    """Browser-only online/offline indicator; persistence still remains server-authoritative."""
    components.html(
        """<style>body{font-family:Arial,sans-serif;margin:0;color:#475569;font-size:13px}.ok{color:#166534;font-weight:700}.bad{color:#b91c1c;font-weight:800}</style><div id='cnnet'>Kontrollerar nät…</div><script>const el=document.getElementById('cnnet');function draw(){const on=navigator.onLine;el.textContent=on?'● Online':'● Dåligt nät / offline';el.className=on?'ok':'bad'}window.addEventListener('online',draw);window.addEventListener('offline',draw);draw();</script>""",
        height=26, scrolling=False,
    )


def _set_write_failure_notice(*, operation: str = "Ändring", match_id: int | None = None, intended: dict[str, Any] | None = None) -> None:
    _set_reporter_save_state("uncertain", operation=operation, match_id=match_id)
    st.session_state["reporter_write_failure_message"] = CUPDAY_WRITE_FAILURE_MESSAGE
    st.session_state["reporter_write_failure_context"] = {
        "operation": str(operation),
        "match_id": int(match_id) if match_id is not None else None,
        "intended": dict(intended or {}),
        "refreshed": False,
    }


def _refresh_after_write_failure(deps: "MatchReporterWorkspaceDeps") -> None:
    context = dict(st.session_state.get("reporter_write_failure_context") or {})
    context["refreshed"] = True
    st.session_state["reporter_write_failure_context"] = context
    deps.refresh_server_state()


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
    save_live_goal: Callable[[int, Any, int, int, dict[str, int]], dict[str, Any]]
    undo_live_goal: Callable[[int, Any, int, int, dict[str, int]], dict[str, Any]]
    acknowledge_referee: Callable[[int, int, int], None]
    set_match_status: Callable[[int, Any, str], bool]
    refresh_server_state: Callable[[], None]


def _set_session_value(key: str, value: Any) -> None:
    """Update a widget-backed session value before Streamlit's normal rerun."""
    st.session_state[key] = value


def _adjust_quick_score(draft_key: str, side_index: int, delta: int) -> None:
    """Adjust the local score draft in a callback to avoid a second rerun."""
    draft = list(st.session_state.get(draft_key, [0, 0]))
    draft[side_index] = max(0, int(draft[side_index]) + int(delta))
    st.session_state[draft_key] = draft


def _reset_quick_score(draft_key: str, home_score: int, away_score: int) -> None:
    st.session_state[draft_key] = [int(home_score), int(away_score)]


def _save_quick_result_callback(
    deps: MatchReporterWorkspaceDeps,
    tournament_id: int,
    match_row: Any,
    draft_key: str,
) -> None:
    """Persist the score before Streamlit's normal button rerun.

    This avoids the historical button-rerun + explicit-rerun pair on the
    most frequently used cup-day action.
    """
    home_score, away_score = st.session_state.get(draft_key, [0, 0])
    _set_reporter_save_state("saving", operation="Slutresultat", match_id=int(match_row["id"]))
    try:
        saved = deps.save_quick_result(tournament_id, match_row, int(home_score), int(away_score))
    except Exception:
        _set_write_failure_notice(
            operation="Slutresultat", match_id=int(match_row["id"]),
            intended={"home_score": int(home_score), "away_score": int(away_score)},
        )
        return
    if saved:
        _set_reporter_save_state("saved", operation="Slutresultat", match_id=int(match_row["id"]))
        st.session_state["reporter_result_message"] = "Slutresultatet är sparat."
        _mark_reporter_edit(int(match_row["id"]), "Slutresultat")
    else:
        st.session_state.pop(draft_key, None)
        if "reporter_result_warning" not in st.session_state:
            st.session_state["reporter_result_warning"] = (
                "Resultatet ändrades av en annan användare. Ingen extra ändring sparades. CupNavi visar nu den senaste versionen."
            )


def _set_match_status_callback(
    deps: MatchReporterWorkspaceDeps,
    tournament_id: int,
    match_row: Any,
    status_value: str,
) -> None:
    """Persist match status before the normal widget rerun."""
    _set_reporter_save_state("saving", operation="Matchstatus", match_id=int(match_row["id"]))
    try:
        saved = deps.set_match_status(tournament_id, match_row, status_value)
    except Exception:
        _set_write_failure_notice(
            operation="Matchstatus", match_id=int(match_row["id"]), intended={"match_status": str(status_value)}
        )
        return
    if not saved:
        st.session_state["reporter_result_warning"] = (
            "Matchstatusen ändrades av någon annan. CupNavi visar nu den senaste versionen."
        )
    else:
        _set_reporter_save_state("saved", operation="Matchstatus", match_id=int(match_row["id"]))
        _mark_reporter_edit(int(match_row["id"]), f"Matchstatus: {status_value}")



def _render_match_event_entry(
    tournament_id: int,
    tournament: Any,
    match_id: int,
    match_row: Any,
    deps: MatchReporterWorkspaceDeps,
) -> None:
    home_team_id = deps.resolve_source(match_row["home_source"])
    away_team_id = deps.resolve_source(match_row["away_source"])
    team_ids = [home_team_id, away_team_id]
    team_names = {int(team_id): deps.team(team_id)["name"] for team_id in team_ids}
    selected_team_id = st.segmented_control(
        "Lag",
        team_ids,
        default=team_ids[0],
        format_func=lambda team_id: team_names[int(team_id)],
        key=f"reporter_event_team_{match_id}",
        label_visibility="collapsed",
    ) or team_ids[0]
    selected_team_id = int(selected_team_id)
    selected_team = deps.team(selected_team_id)
    roster_snapshot = fetch_match_team_players(deps.query_all, match_id, selected_team_id)
    registered_match_roster, players = roster_snapshot["registered"], roster_snapshot["players"]
    st.markdown(f"#### {selected_team['name']}")
    if registered_match_roster:
        st.caption(f"Matchtrupp registrerad · {len(registered_match_roster)} spelare. Endast dessa kan få matchhändelser.")
    elif players:
        st.warning("Matchtrupp saknas. Alla spelare visas tills en matchtrupp registreras.")
    if not players:
        st.warning("Laget saknar registrerade spelare.")
    else:
        existing = {int(row["player_id"]): row for row in fetch_player_match_stats(deps.query_all, match_id, selected_team_id)}
        raw_team_goals = match_row["home_score"] if selected_team_id == home_team_id else match_row["away_score"]
        team_goals = int(raw_team_goals or 0)
        match_status = normalize_match_status(deps.row_value(match_row, "match_status", MATCH_NOT_STARTED))
        # v546: reporter event controls must mirror the choices made in setup.
        # Missing/legacy values are treated as disabled in the reporter UI rather than
        # accidentally exposing player-event reporting that the organiser did not choose.
        scorer_enabled = bool(deps.row_value(tournament, "enable_scorer_leaderboard", 0))
        assist_enabled = bool(deps.row_value(tournament, "enable_assist_leaderboard", 0))
        card_statistics_enabled = bool(deps.row_value(tournament, "enable_card_statistics", 0))
        player_by_id = {int(player["id"]): player for player in players}
        player_ids = list(player_by_id)
        player_widget_key = f"reporter_quick_event_player_{match_id}_{selected_team_id}"
        player_id = st.selectbox(
            "Spelare",
            player_ids,
            format_func=lambda pid: f"#{deps.row_value(player_by_id[int(pid)], 'player_number', '–') or '–'} · {deps.row_value(player_by_id[int(pid)], 'name', '')}",
            key=player_widget_key,
        )
        player_id = int(player_id)
        player_index = player_ids.index(player_id)
        prev_col, next_col = st.columns(2)
        prev_col.button(
            "← Föregående spelare",
            key=f"reporter_prev_player_{match_id}_{selected_team_id}_{player_id}",
            use_container_width=True,
            disabled=player_index <= 0,
            on_click=_set_session_value,
            args=(player_widget_key, player_ids[max(0, player_index - 1)]),
        )
        next_col.button(
            "Nästa spelare →",
            key=f"reporter_next_player_{match_id}_{selected_team_id}_{player_id}",
            use_container_width=True,
            disabled=player_index >= len(player_ids) - 1,
            on_click=_set_session_value,
            args=(player_widget_key, player_ids[min(len(player_ids) - 1, player_index + 1)]),
        )
        current = existing.get(player_id)
        current_values = {
            "goals": int(current["goals"] or 0) if current else 0,
            "assists": int(current["assists"] or 0) if current else 0,
            "yellow_cards": int(current["yellow_cards"] or 0) if current else 0,
            "red_cards": int(current["red_cards"] or 0) if current else 0,
        }
        _player_stat_bits = []
        if scorer_enabled:
            _player_stat_bits.append(f"⚽ {current_values['goals']}")
        if assist_enabled:
            _player_stat_bits.append(f"🎯 {current_values['assists']}")
        if card_statistics_enabled:
            _player_stat_bits.extend([f"🟨 {current_values['yellow_cards']}", f"🟥 {current_values['red_cards']}"])
        if _player_stat_bits:
            st.caption("Denna spelare: " + " · ".join(_player_stat_bits))
        quick_message_key = f"reporter_quick_event_message_{match_id}_{selected_team_id}"
        quick_last_event_key = f"reporter_quick_last_event_{match_id}_{selected_team_id}"
        quick_last_event_detail_key = f"reporter_quick_last_event_detail_{match_id}_{selected_team_id}"
        quick_conflict_key = f"reporter_quick_event_conflict_{match_id}_{selected_team_id}"
        if quick_message_key in st.session_state:
            st.success(st.session_state.pop(quick_message_key), icon="✅")
        if quick_last_event_key in st.session_state:
            st.caption(f"Senast registrerat: {st.session_state[quick_last_event_key]}")
            last_detail = st.session_state.get(quick_last_event_detail_key)

            def _undo_latest_quick_event() -> None:
                """Undo inside the button callback so the widget's normal rerun is the only rerun."""
                detail = st.session_state.get(quick_last_event_detail_key)
                if not isinstance(detail, dict):
                    return
                target_player_id = int(detail.get("player_id", 0) or 0)
                target_field = str(detail.get("field", "") or "")
                target_label = str(detail.get("label", "Händelse") or "Händelse")
                if target_player_id not in player_by_id or target_field not in {"goals", "assists", "yellow_cards", "red_cards"}:
                    st.session_state[quick_conflict_key] = "Den senaste händelsen kan inte längre identifieras säkert."
                    return
                if bool(detail.get("atomic_goal")):
                    target_current = existing.get(target_player_id)
                    expected_stats = {
                        "goals": int(target_current["goals"] or 0) if target_current else 0,
                        "assists": int(target_current["assists"] or 0) if target_current else 0,
                        "yellow_cards": int(target_current["yellow_cards"] or 0) if target_current else 0,
                        "red_cards": int(target_current["red_cards"] or 0) if target_current else 0,
                    }
                    try:
                        undo_outcome = deps.undo_live_goal(
                            tournament_id, match_row, selected_team_id, target_player_id, expected_stats
                        )
                    except Exception:
                        _set_write_failure_notice(operation="Ångra mål", match_id=match_id)
                        return
                    if not undo_outcome.get("saved"):
                        st.session_state[quick_conflict_key] = undo_outcome.get(
                            "message", "Målet ändrades av en annan rapportör och kunde inte ångras."
                        )
                    else:
                        st.session_state[quick_message_key] = "Målet och matchresultatet ångrades tillsammans."
                        _mark_reporter_edit(match_id, "Mål ångrat")
                        st.session_state.pop(quick_last_event_key, None)
                        st.session_state.pop(quick_last_event_detail_key, None)
                    return

                undo_update = prepare_quick_event_update(
                    existing, match_id=match_id, player_id=target_player_id, field=target_field, delta=-1
                )
                if undo_update is None:
                    st.session_state[quick_conflict_key] = "Händelsen är redan borttagen eller ändrad."
                    return
                undo_totals = event_totals_after_update(existing, undo_update)
                undo_validation = validate_match_event_totals(
                    team_goals, undo_totals["goals"], undo_totals["assists"]
                )
                if not undo_validation["ok"]:
                    st.session_state[quick_conflict_key] = undo_validation["errors"][0]
                    return
                try:
                    undo_outcome = deps.save_event_rows([undo_update])
                except Exception:
                    _set_write_failure_notice(operation="Ångra matchhändelse", match_id=match_id)
                    return
                if undo_outcome["conflicts"]:
                    st.session_state[quick_conflict_key] = (
                        "Händelsen ändrades av en annan rapportör och kunde inte ångras. Senaste värden laddas om."
                    )
                elif undo_outcome["saved"]:
                    st.session_state[quick_message_key] = f"{target_label} ångrades."
                    _mark_reporter_edit(match_id, f"{target_label} ångrat")
                    st.session_state.pop(quick_last_event_key, None)
                    st.session_state.pop(quick_last_event_detail_key, None)

            if isinstance(last_detail, dict):
                st.button(
                    "↩️ Ångra senaste",
                    key=f"reporter_quick_undo_{match_id}_{selected_team_id}",
                    use_container_width=True,
                    on_click=_undo_latest_quick_event,
                )
        if quick_conflict_key in st.session_state:
            st.warning(st.session_state.pop(quick_conflict_key), icon="⚠️")

        def _apply_quick_event(field: str, delta: int, label: str) -> None:
            """Persist one player event inside the button callback; normal widget rerun is enough."""
            update = prepare_quick_event_update(
                existing, match_id=match_id, player_id=player_id, field=field, delta=delta
            )
            if update is None:
                return
            totals = event_totals_after_update(existing, update)
            validation = validate_match_event_totals(team_goals, totals["goals"], totals["assists"])
            if not validation["ok"]:
                st.session_state[quick_conflict_key] = validation["errors"][0]
                return
            _set_reporter_save_state("saving", operation=label, match_id=match_id)
            try:
                outcome = deps.save_event_rows([update])
            except Exception:
                _set_write_failure_notice(operation=label, match_id=match_id)
                return
            if outcome["conflicts"]:
                st.session_state[quick_conflict_key] = (
                    "Spelarens händelser ändrades av en annan rapportör och skrevs inte över. "
                    "Senaste värden laddas om."
                )
            elif outcome["saved"]:
                _set_reporter_save_state("saved", operation=label, match_id=match_id)
                player = player_by_id[player_id]
                player_number = deps.row_value(player, "player_number", "–") or "–"
                player_name = deps.row_value(player, "name", "")
                direction = "registrerat" if delta > 0 else "korrigerat"
                st.session_state[quick_message_key] = f"{label} {direction}."
                st.session_state[quick_last_event_key] = (
                    f"{label} · #{player_number} {player_name} · {selected_team['name']}"
                )
                st.session_state[quick_last_event_detail_key] = {
                    "player_id": int(player_id),
                    "field": field,
                    "label": label,
                }
                _mark_reporter_edit(match_id, label)

        def _save_live_goal_callback() -> None:
            """Persist score + scorer before the single normal button rerun."""
            _set_reporter_save_state("saving", operation="Mål + målskytt", match_id=match_id)
            try:
                outcome = deps.save_live_goal(
                    tournament_id, match_row, selected_team_id, player_id, current_values
                )
            except Exception:
                _set_write_failure_notice(operation="Mål + målskytt", match_id=match_id)
                return
            if not outcome.get("saved"):
                st.session_state[quick_conflict_key] = outcome.get(
                    "message", "Matchen ändrades redan på servern. Ingen extra måländring sparades. Senaste värden laddas om."
                )
                return
            _set_reporter_save_state("saved", operation="Mål + målskytt", match_id=match_id)
            player = player_by_id[player_id]
            player_number = deps.row_value(player, "player_number", "–") or "–"
            player_name = deps.row_value(player, "name", "")
            st.session_state[quick_message_key] = (
                f"Mål säkert sparat på servern. Resultatet är nu {outcome['home_score']}–{outcome['away_score']}."
            )
            st.session_state[quick_last_event_key] = (
                f"Mål · #{player_number} {player_name} · {selected_team['name']}"
            )
            st.session_state[quick_last_event_detail_key] = {
                "player_id": int(player_id), "field": "goals", "label": "Mål", "atomic_goal": True
            }
            _mark_reporter_edit(match_id, "Mål + målskytt")

        action_specs = []
        if scorer_enabled:
            if match_status != MATCH_FINISHED:
                st.button(
                    "⚽ MÅL · uppdatera resultat",
                    key=f"reporter_live_goal_{match_id}_{selected_team_id}_{player_id}",
                    use_container_width=True,
                    type="primary",
                    on_click=_save_live_goal_callback,
                )
                st.caption("Ett tryck sparar både matchresultat och målskytt i samma transaktion. Vid segt nät: vänta på grön bekräftelse i stället för att trycka igen.")
            else:
                action_specs.append(("goals", "⚽ + Målskytt", "Mål"))
        if assist_enabled:
            action_specs.append(("assists", "🎯 + Assist", "Assist"))
        if card_statistics_enabled:
            action_specs.extend([
                ("yellow_cards", "🟨 + Gult", "Gult kort"),
                ("red_cards", "🟥 + Rött", "Rött kort"),
            ])
        for index in range(0, len(action_specs), 2):
            cols = st.columns(2)
            for offset, spec in enumerate(action_specs[index:index + 2]):
                field, button_label, success_label = spec
                cols[offset].button(
                    button_label,
                    key=f"reporter_quick_add_{field}_{match_id}_{selected_team_id}_{player_id}",
                    use_container_width=True,
                    type="primary" if field == "goals" else "secondary",
                    on_click=_apply_quick_event,
                    args=(field, 1, success_label),
                )

        with st.expander("↩️ Korrigera senaste händelser", expanded=False):
            correction_specs = []
            if scorer_enabled:
                correction_specs.append(("goals", "− Mål", "Mål korrigerat"))
            if assist_enabled:
                correction_specs.append(("assists", "− Assist", "Assist korrigerad"))
            if card_statistics_enabled:
                correction_specs.extend([
                    ("yellow_cards", "− Gult", "Gult kort korrigerat"),
                    ("red_cards", "− Rött", "Rött kort korrigerat"),
                ])
            for field, button_label, success_label in correction_specs:
                st.button(
                    button_label,
                    key=f"reporter_quick_sub_{field}_{match_id}_{selected_team_id}_{player_id}",
                    use_container_width=True,
                    disabled=current_values[field] <= 0,
                    on_click=_apply_quick_event,
                    args=(field, -1, success_label),
                )

        _summary_bits = [f"Matchresultat: {team_goals} mål"]
        if scorer_enabled:
            total_goals = sum(int(row["goals"] or 0) for row in existing.values())
            _summary_bits.append(f"registrerade spelarmål: {total_goals}")
        if assist_enabled:
            total_assists = sum(int(row["assists"] or 0) for row in existing.values())
            _summary_bits.append(f"registrerade assist: {total_assists}")
        st.caption(" · ".join(_summary_bits))

        show_table = False
        if scorer_enabled or assist_enabled or card_statistics_enabled:
            show_table = st.toggle(
                "Visa tabell för massinmatning",
                value=False,
                key=f"reporter_event_table_{match_id}_{selected_team_id}",
            )
        if show_table:
            data = pd.DataFrame(build_event_player_rows(players, existing))
            reporter_columns = build_reporter_columns(
                assist_enabled=assist_enabled,
                card_statistics_enabled=card_statistics_enabled,
            )
            if not scorer_enabled and "Mål" in reporter_columns:
                reporter_columns = [column for column in reporter_columns if column != "Mål"]
            edited = st.data_editor(
                data, hide_index=True, use_container_width=True,
                disabled=["player_id", "Nr", "Spelare"], column_order=reporter_columns,
                column_config={
                    "Mål": st.column_config.NumberColumn(min_value=0, step=1),
                    "Assist": st.column_config.NumberColumn(min_value=0, step=1),
                    "Varningar": st.column_config.NumberColumn(min_value=0, step=1),
                    "Utvisningar": st.column_config.NumberColumn(min_value=0, step=1),
                },
                key=f"reporter_stats_{match_id}_{selected_team_id}",
            )
            entered_goals = int(edited["Mål"].fillna(0).sum()) if scorer_enabled and "Mål" in edited.columns else sum(int(row["goals"] or 0) for row in existing.values())
            entered_assists = int(edited["Assist"].fillna(0).sum()) if assist_enabled and "Assist" in edited.columns else sum(int(row["assists"] or 0) for row in existing.values())
            validation = validate_match_event_totals(team_goals, entered_goals, entered_assists)
            for message in validation["errors"]:
                st.error(f"{selected_team['name']}: {message}")
            autosave_key = f"reporter_event_saved_{match_id}_{selected_team_id}"
            if autosave_key in st.session_state:
                st.success(st.session_state.pop(autosave_key), icon="✅")
            conflict_key = f"reporter_event_conflict_{match_id}_{selected_team_id}"
            if conflict_key in st.session_state:
                st.warning(st.session_state.pop(conflict_key), icon="⚠️")
            if not validation["errors"]:
                changed_rows = prepare_changed_event_rows(
                    (edited_row for _, edited_row in edited.iterrows()), existing,
                    match_id=match_id, is_na=pd.isna,
                )
                if changed_rows:
                    try:
                        outcome = deps.save_event_rows(changed_rows)
                    except Exception:
                        _set_write_failure_notice(operation="Matchhändelser", match_id=match_id)
                        st.rerun()
                    if outcome["conflicts"]:
                        st.session_state[conflict_key] = (
                            f"{outcome['conflicts']} spelarrad(er) hade ändrats av en annan rapportör "
                            "och skrevs inte över. Senaste värden laddas om."
                        )
                    if outcome["saved"]:
                        st.session_state[autosave_key] = "Sparat automatiskt"
                        _mark_reporter_edit(match_id, "Matchhändelser")
                    st.rerun()


def _match_has_saved_result(match_row: Any) -> bool:
    """Return whether both score fields are persisted for a playable match."""
    return match_row["home_score"] is not None and match_row["away_score"] is not None


def _reporter_match_queue(playable_matches: list[Any]) -> list[Any]:
    """Prioritize unreported matches while preserving chronology within each status."""
    unreported = [row for row in playable_matches if not _match_has_saved_result(row)]
    reported = [row for row in playable_matches if _match_has_saved_result(row)]
    return unreported + reported


def _reporter_queue_label(
    match_row: Any,
    *,
    next_unreported_id: int | None,
    match_result_label: Callable[[Any], str],
) -> str:
    """Add a compact work-queue status prefix to the existing match label."""
    match_id = int(match_row["id"])
    if next_unreported_id is not None and match_id == int(next_unreported_id):
        status = "▶ Nästa"
    elif _match_has_saved_result(match_row):
        status = "✓ Rapporterad"
    else:
        status = "○ Orapporterad"
    return f"{status} · {match_result_label(match_row)}"


def _next_unreported_match_id(playable_matches: list[Any], current_match_id: int) -> int | None:
    """Return the next later playable match without a complete saved result."""
    current_index = next(
        (index for index, row in enumerate(playable_matches) if int(row["id"]) == int(current_match_id)),
        None,
    )
    if current_index is None:
        return None
    for row in playable_matches[current_index + 1:]:
        if row["home_score"] is None or row["away_score"] is None:
            return int(row["id"])
    return None


def _select_quick_score_match(widget_key: str, match_id: int) -> None:
    """Widget callback used by the one-tap next-match flow."""
    st.session_state[widget_key] = int(match_id)


def render_match_reporter_workspace(tournament_id: int, tournament: Any, deps: MatchReporterWorkspaceDeps) -> None:
    st.title(f"📝 Matchrapportör · {tournament['name']}")
    _caption_features = ["resultat"]
    if bool(deps.row_value(tournament, "enable_scorer_leaderboard", 0)):
        _caption_features.append("målskytt")
    if bool(deps.row_value(tournament, "enable_assist_leaderboard", 0)):
        _caption_features.append("assist")
    if bool(deps.row_value(tournament, "enable_card_statistics", 0)):
        _caption_features.append("kort")
    st.caption(
        "Rapportören kan registrera " + ", ".join(_caption_features) + ". "
        "Endast funktioner som arrangören valt i setupen visas."
    )
    # Reporterläget används ofta stående på telefon vid plan. Ge knapparna en
    # större touchyta utan att påverka övriga CupNavi-vyer.
    st.markdown(
        """<style>
        div[data-testid="stButton"] > button { min-height: 64px; font-weight: 750; }
        .cn-reporter-score { font-size: 2.15rem; font-weight: 900; text-align:center; padding:.35rem 0; }
        .cn-reporter-score-live { font-size: 3.25rem; line-height:1; padding:.45rem .1rem; letter-spacing:-.06em; }
        .cn-scoreboard-team { font-size:1.08rem; font-weight:850; text-align:center; line-height:1.15; min-height:2.5rem; display:flex; align-items:center; justify-content:center; }
        .cn-scoreboard-help { text-align:center; font-size:.82rem; opacity:.72; margin:.1rem 0 .45rem; }
        [class*="st-key-reporter_quick_score_shell_"] { border:1px solid rgba(128,128,128,.22); border-radius:18px; padding:.65rem .55rem .55rem; }
        [class*="st-key-reporter_quick_score_shell_"] .cn-reporter-score { font-size:3.7rem; line-height:.95; letter-spacing:-.07em; padding:.2rem 0 .45rem; }
        [class*="st-key-reporter_quick_score_shell_"] [data-testid="stButton"] button { min-height:76px; font-size:1.75rem; font-weight:900; border-radius:16px; }
        div[data-testid="stSelectbox"] select { min-height: 52px; font-size: 1rem; }
        @media(max-width:520px){
          .cn-reporter-score-live { font-size:2.8rem; }
          [class*="st-key-reporter_quick_score_shell_"] { padding:.55rem .35rem .45rem; border-radius:16px; }
          [class*="st-key-reporter_quick_score_shell_"] .cn-reporter-score { font-size:3rem; }
          [class*="st-key-reporter_quick_score_shell_"] [data-testid="stButton"] button { min-height:72px; font-size:1.65rem; padding:.25rem; }
        }
        .cn-touch-hint { font-size:.82rem; opacity:.72; margin-top:-.25rem; }
        </style>""",
        unsafe_allow_html=True,
    )
    # v546: the reporter only sees player-event features that the organiser
    # explicitly enabled in setup. Keep result reporting available regardless.
    _setup_scorers = bool(deps.row_value(tournament, "enable_scorer_leaderboard", 0))
    _setup_assists = bool(deps.row_value(tournament, "enable_assist_leaderboard", 0))
    _setup_cards = bool(deps.row_value(tournament, "enable_card_statistics", 0))
    _setup_player_events = _setup_scorers or _setup_assists or _setup_cards

    _score_section = deps.translate("CupNavi Score")
    _events_section = deps.translate("Matchhändelser")
    _referee_section = deps.translate("Domarcentral")
    _offline_section = deps.translate("Offlineutkast")
    reporter_sections = [_score_section]
    if _setup_player_events:
        reporter_sections.append(_events_section)
    reporter_sections.extend([_referee_section, _offline_section])
    reporter_section = st.segmented_control(
        "Arbetsyta",
        reporter_sections,
        default=_score_section,
        key=f"reporter_workspace_section_{tournament_id}",
        label_visibility="collapsed",
    ) or _score_section

    if reporter_section == _score_section:
        _render_reporter_network_probe()
        _render_reporter_save_state()
        matches = fetch_scheduled_matches(deps.query_all, tournament_id)
        playable_matches = select_playable_matches(matches, resolve_source=deps.resolve_source)
        _write_failure_message = st.session_state.get("reporter_write_failure_message")
        _write_failure_context = st.session_state.get("reporter_write_failure_context")
        if _write_failure_message and isinstance(_write_failure_context, dict):
            st.error(_write_failure_message)
            _failure_match_id = _write_failure_context.get("match_id")
            _failure_operation = str(_write_failure_context.get("operation") or "Ändring")
            if not _write_failure_context.get("refreshed"):
                st.button(
                    "🔄 Läs om från servern", key=f"reporter_failure_refresh_{tournament_id}",
                    type="primary", use_container_width=True,
                    on_click=_refresh_after_write_failure, args=(deps,),
                )
                st.caption(f"Osäker åtgärd: {_failure_operation}. CupNavi gör ingen automatisk omskrivning.")
            else:
                _fresh_match = next((row for row in matches if _failure_match_id is not None and int(row["id"]) == int(_failure_match_id)), None)
                _intended = dict(_write_failure_context.get("intended") or {})
                if _fresh_match is not None and {"home_score", "away_score"} <= set(_intended):
                    _already_saved = (
                        _fresh_match["home_score"] == _intended["home_score"]
                        and _fresh_match["away_score"] == _intended["away_score"]
                    )
                    if _already_saved:
                        st.success(
                            f"✅ Servern visar {_intended['home_score']}–{_intended['away_score']}. "
                            "Ditt försök finns redan sparat – registrera det inte igen."
                        )
                    else:
                        st.warning(
                            "Servern visar inte det resultat du försökte spara. Kontrollera matchen visuellt; "
                            "om värdena verkligen saknas kan du registrera dem på nytt."
                        )
                else:
                    st.info("Serverläget är omladdat. Kontrollera den berörda matchen/händelsen innan du gör en ny ändring.")
                def _clear_write_failure_notice() -> None:
                    st.session_state.pop("reporter_write_failure_message", None)
                    st.session_state.pop("reporter_write_failure_context", None)
                    st.session_state["reporter_save_state"] = {"state": "ready", "operation": "Redo", "at": float(time.time())}

                st.button(
                    "✓ Jag har kontrollerat serverläget", key=f"reporter_failure_clear_{tournament_id}",
                    use_container_width=True, on_click=_clear_write_failure_notice,
                )
        elif _write_failure_message:
            st.error(_write_failure_message)
        if "reporter_result_message" in st.session_state:
            st.success(st.session_state.pop("reporter_result_message"), icon="✅")
        if "reporter_result_warning" in st.session_state:
            st.warning(st.session_state.pop("reporter_result_warning"))
        if "reporter_conflict_message" in st.session_state:
            st.warning(st.session_state.pop("reporter_conflict_message"))
        if not playable_matches:
            st.info("Det finns ännu inga schemalagda matcher med två klara lag.")
        else:
            st.markdown("### ⚡ CupNavi Score")
            _reporting_mode = st.segmented_control(
                "Rapporteringsläge",
                ["Enkel", "Avancerad"],
                default="Enkel",
                key=f"reporter_mode_{tournament_id}",
                help=(
                    "Enkel: välj match, ange slutresultat och spara. "
                    "Avancerad: visar matchstatus, valda matchhändelser och slutspelsavgöranden."
                ),
            ) or "Enkel"
            _advanced_reporting = _reporting_mode == "Avancerad"
            st.caption(
                "Snabbast möjligt: välj match → ange resultat → spara."
                if not _advanced_reporting
                else "Avancerat läge: matchstatus, de händelser som valts i setupen och specialfall visas i samma arbetsflöde."
            )
            by_id = {int(row["id"]): row for row in playable_matches}
            match_queue = _reporter_match_queue(playable_matches)
            queue_ids = [int(row["id"]) for row in match_queue]
            unreported_ids = [int(row["id"]) for row in match_queue if not _match_has_saved_result(row)]
            next_unreported_id = unreported_ids[0] if unreported_ids else None
            st.caption(
                f"{len(unreported_ids)} kvar · {len(match_queue) - len(unreported_ids)} klara"
            )
            if not unreported_ids:
                st.success("Alla spelbara matcher har ett sparat resultat.", icon="✅")
            quick_score_widget_key = f"quick_score_match_{tournament_id}"
            if quick_score_widget_key not in st.session_state:
                st.session_state[quick_score_widget_key] = next_unreported_id or queue_ids[0]
            elif int(st.session_state[quick_score_widget_key]) not in by_id:
                st.session_state[quick_score_widget_key] = next_unreported_id or queue_ids[0]
            quick_match_id = st.selectbox(
                "Välj match för snabbresultat",
                queue_ids,
                format_func=lambda match_id: _reporter_queue_label(
                    by_id[int(match_id)],
                    next_unreported_id=next_unreported_id,
                    match_result_label=deps.match_result_label,
                ),
                key=quick_score_widget_key,
            )
            quick_match = by_id[int(quick_match_id)]
            st.markdown(
                f"**Aktuell match · {deps.swedish_datetime(quick_match['scheduled_start'])} · "
                f"Plan {quick_match['pitch_number']}**"
            )
            _current_status = normalize_match_status(
                deps.row_value(quick_match, "match_status", MATCH_NOT_STARTED),
                has_result=(
                    deps.row_value(quick_match, "home_score", None) is not None
                    and deps.row_value(quick_match, "away_score", None) is not None
                ),
            )
            if _advanced_reporting:
                st.markdown(f"**Matchstatus: {match_status_label(_current_status)}**")
                _status_cols = st.columns(4)
                _status_actions = [
                    (MATCH_NOT_STARTED, "Ej startad"),
                    (MATCH_LIVE, "▶ Pågår"),
                    (MATCH_HALFTIME, "⏸ Paus"),
                    (MATCH_FINISHED, "■ Slut"),
                ]
                for _status_col, (_status_value, _status_label) in zip(_status_cols, _status_actions):
                    _status_col.button(
                        _status_label,
                        key=f"reporter_status_{quick_match_id}_{_status_value}",
                        use_container_width=True,
                        type="primary" if _current_status == _status_value else "secondary",
                        disabled=(
                            _current_status == _status_value
                            or (
                                _status_value == MATCH_NOT_STARTED
                                and _current_status == MATCH_FINISHED
                            )
                        ),
                        on_click=_set_match_status_callback,
                        args=(deps, tournament_id, quick_match, _status_value),
                    )
                if _current_status == MATCH_FINISHED and not (
                    deps.row_value(quick_match, "home_score", None) is not None
                    and deps.row_value(quick_match, "away_score", None) is not None
                ):
                    st.caption("Matchen är markerad som slut. Lägg till resultat om resultat används i arrangemanget.")
            elif _current_status in {MATCH_LIVE, MATCH_HALFTIME}:
                st.caption(f"Matchstatus: {match_status_label(_current_status)}")
            quick_home_name = deps.source_label(quick_match["home_source"])
            quick_away_name = deps.source_label(quick_match["away_source"])

            # v545: one-screen mobile match control. Player-bound actions stay beside
            # the selected team/player so a reporter does not have to scroll to a
            # separate event workspace during play.
            _scorer_tracking = bool(deps.row_value(tournament, "enable_scorer_leaderboard", 0))
            _assist_tracking = bool(deps.row_value(tournament, "enable_assist_leaderboard", 0))
            _card_tracking = bool(deps.row_value(tournament, "enable_card_statistics", 0))
            _player_event_tracking = _scorer_tracking or _assist_tracking or _card_tracking
            if _advanced_reporting and _current_status != MATCH_FINISHED and _player_event_tracking:
                _home_team_id = deps.resolve_source(quick_match["home_source"])
                _away_team_id = deps.resolve_source(quick_match["away_source"])
                if _home_team_id and _away_team_id:
                    st.markdown("### 🎛️ Matchkontroll")
                    st.caption("All live-rapportering för vald match ligger här. Välj spelare i rullistan och använd stora +/−-knappar.")
                    _goal_cols = st.columns([1, .48, 1])
                    _score_now_home = int(quick_match["home_score"] or 0)
                    _score_now_away = int(quick_match["away_score"] or 0)
                    _goal_cols[1].markdown(
                        f"<div class='cn-reporter-score cn-reporter-score-live'>{_score_now_home}–{_score_now_away}</div>",
                        unsafe_allow_html=True,
                    )
                    for _side_col, _team_id, _team_name, _side in (
                        (_goal_cols[0], int(_home_team_id), quick_home_name, "home"),
                        (_goal_cols[2], int(_away_team_id), quick_away_name, "away"),
                    ):
                        _side_col.markdown(f"**{_team_name}**")
                        _roster = fetch_match_team_players(deps.query_all, int(quick_match_id), int(_team_id))["players"]
                        if _roster:
                            _player_by_id = {int(r["id"]): r for r in _roster}
                            _player_ids = list(_player_by_id)
                            _selected_player_id = _side_col.selectbox(
                                "Spelare", _player_ids,
                                format_func=lambda pid, pb=_player_by_id: f"#{deps.row_value(pb[int(pid)], 'player_number', '–') or '–'} · {deps.row_value(pb[int(pid)], 'name', '')}",
                                key=f"reporter_inline_player_{quick_match_id}_{_side}",
                                label_visibility="collapsed",
                            )
                            _existing_rows = {
                                int(row["player_id"]): row
                                for row in fetch_player_match_stats(deps.query_all, int(quick_match_id), int(_team_id))
                            }
                            _current_player = _existing_rows.get(int(_selected_player_id))
                            _expected_stats = {
                                "goals": int(_current_player["goals"] or 0) if _current_player else 0,
                                "assists": int(_current_player["assists"] or 0) if _current_player else 0,
                                "yellow_cards": int(_current_player["yellow_cards"] or 0) if _current_player else 0,
                                "red_cards": int(_current_player["red_cards"] or 0) if _current_player else 0,
                            }
                            _team_goals = _score_now_home if _side == "home" else _score_now_away

                            def _inline_goal_change(team_id=_team_id, player_id=int(_selected_player_id), expected_stats=dict(_expected_stats), delta=1):
                                _op = "Mål" if delta > 0 else "Ångra mål"
                                _set_reporter_save_state("saving", operation=_op, match_id=int(quick_match_id))
                                try:
                                    if delta > 0:
                                        outcome = deps.save_live_goal(tournament_id, quick_match, int(team_id), int(player_id), expected_stats)
                                    else:
                                        outcome = deps.undo_live_goal(tournament_id, quick_match, int(team_id), int(player_id), expected_stats)
                                except Exception:
                                    _set_write_failure_notice(operation="Mål", match_id=int(quick_match_id))
                                    return
                                if outcome.get("saved"):
                                    _set_reporter_save_state("saved", operation=_op, match_id=int(quick_match_id))
                                    _mark_reporter_edit(int(quick_match_id), "Mål" if delta > 0 else "Mål ångrat")
                                    st.session_state["reporter_result_message"] = (
                                        f"{'Mål registrerat' if delta > 0 else 'Mål korrigerat'} · "
                                        f"{outcome['home_score']}–{outcome['away_score']}"
                                    )
                                else:
                                    st.session_state["reporter_result_warning"] = outcome.get("message", "Ändringen kunde inte sparas.")

                            def _inline_player_event(field: str, delta: int, label: str,
                                                     player_id=int(_selected_player_id),
                                                     existing_rows=dict(_existing_rows),
                                                     team_goals=int(_team_goals)):
                                update = prepare_quick_event_update(
                                    existing_rows, match_id=int(quick_match_id), player_id=int(player_id), field=field, delta=delta
                                )
                                if update is None:
                                    return
                                totals = event_totals_after_update(existing_rows, update)
                                validation = validate_match_event_totals(team_goals, totals["goals"], totals["assists"])
                                if not validation["ok"]:
                                    st.session_state["reporter_result_warning"] = validation["errors"][0]
                                    return
                                _set_reporter_save_state("saving", operation=label, match_id=int(quick_match_id))
                                try:
                                    outcome = deps.save_event_rows([update])
                                except Exception:
                                    _set_write_failure_notice(operation=label, match_id=int(quick_match_id))
                                    return
                                if outcome.get("conflicts"):
                                    st.session_state["reporter_result_warning"] = "Händelsen ändrades av en annan rapportör. Senaste servervärdet visas nu."
                                elif outcome.get("saved"):
                                    _set_reporter_save_state("saved", operation=label, match_id=int(quick_match_id))
                                    _mark_reporter_edit(int(quick_match_id), label)
                                    st.session_state["reporter_result_message"] = f"{label} {'registrerad' if delta > 0 else 'korrigerad'}."

                            if _scorer_tracking:
                                _side_col.caption(f"⚽ Mål: {_expected_stats['goals']}")
                                _minus, _plus = _side_col.columns(2)
                                _minus.button(
                                    "− MÅL", key=f"inline_goal_minus_{quick_match_id}_{_side}_{_selected_player_id}",
                                    use_container_width=True, disabled=_expected_stats["goals"] <= 0,
                                    on_click=_inline_goal_change, kwargs={"delta": -1},
                                )
                                _plus.button(
                                    "+ MÅL", key=f"inline_goal_plus_{quick_match_id}_{_side}_{_selected_player_id}",
                                    use_container_width=True, type="primary",
                                    on_click=_inline_goal_change, kwargs={"delta": 1},
                                )
                            if _assist_tracking:
                                _side_col.caption(f"🎯 Assist: {_expected_stats['assists']}")
                                _minus, _plus = _side_col.columns(2)
                                _minus.button(
                                    "− ASSIST", key=f"inline_assist_minus_{quick_match_id}_{_side}_{_selected_player_id}",
                                    use_container_width=True, disabled=_expected_stats["assists"] <= 0,
                                    on_click=_inline_player_event, args=("assists", -1, "Assist"),
                                )
                                _plus.button(
                                    "+ ASSIST", key=f"inline_assist_plus_{quick_match_id}_{_side}_{_selected_player_id}",
                                    use_container_width=True,
                                    on_click=_inline_player_event, args=("assists", 1, "Assist"),
                                )
                            if _card_tracking:
                                _side_col.caption(f"🟨 {_expected_stats['yellow_cards']} · 🟥 {_expected_stats['red_cards']}")
                                _yellow_minus, _yellow_plus = _side_col.columns(2)
                                _yellow_minus.button(
                                    "− 🟨", key=f"inline_yellow_minus_{quick_match_id}_{_side}_{_selected_player_id}",
                                    use_container_width=True, disabled=_expected_stats["yellow_cards"] <= 0,
                                    on_click=_inline_player_event, args=("yellow_cards", -1, "Gult kort"),
                                )
                                _yellow_plus.button(
                                    "+ 🟨", key=f"inline_yellow_plus_{quick_match_id}_{_side}_{_selected_player_id}",
                                    use_container_width=True,
                                    on_click=_inline_player_event, args=("yellow_cards", 1, "Gult kort"),
                                )
                                _red_minus, _red_plus = _side_col.columns(2)
                                _red_minus.button(
                                    "− 🟥", key=f"inline_red_minus_{quick_match_id}_{_side}_{_selected_player_id}",
                                    use_container_width=True, disabled=_expected_stats["red_cards"] <= 0,
                                    on_click=_inline_player_event, args=("red_cards", -1, "Rött kort"),
                                )
                                _red_plus.button(
                                    "+ 🟥", key=f"inline_red_plus_{quick_match_id}_{_side}_{_selected_player_id}",
                                    use_container_width=True,
                                    on_click=_inline_player_event, args=("red_cards", 1, "Rött kort"),
                                )
                        else:
                            _side_col.warning("Ingen laglista. Lägg in spelare för att rapportera spelarbundna händelser.")
                    _render_reporter_correction_window(int(quick_match_id))
                    st.caption("15 s korrigeringsfönster efter varje rapportering. Mobilaviseringar väntar minst 30 s från senaste målredigeringen.")

            draft_key = f"quick_score_draft_{quick_match_id}"
            if draft_key not in st.session_state:
                st.session_state[draft_key] = [int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)]
            quick_home_score, quick_away_score = st.session_state[draft_key]
            if _advanced_reporting:
                st.caption("Resultattavla · manuell resultatkorrigering")
            with st.container(key=f"reporter_quick_score_shell_{tournament_id}_{quick_match_id}"):
                st.markdown("<div class='cn-scoreboard-help'>Tryck stort +/− för att ändra. Spara när resultatet är rätt.</div>", unsafe_allow_html=True)
                qh, qc, qa = st.columns([1.35, .9, 1.35])
                qh.markdown(f"<div class='cn-scoreboard-team'>{quick_home_name}</div>", unsafe_allow_html=True)
                qa.markdown(f"<div class='cn-scoreboard-team'>{quick_away_name}</div>", unsafe_allow_html=True)
                qh_minus, qh_plus = qh.columns(2)
                qa_minus, qa_plus = qa.columns(2)
                qh_minus.button(
                    "−", key=f"qs_hm_{quick_match_id}", use_container_width=True,
                    on_click=_adjust_quick_score, args=(draft_key, 0, -1),
                )
                qh_plus.button(
                    "+", key=f"qs_hp_{quick_match_id}", use_container_width=True,
                    on_click=_adjust_quick_score, args=(draft_key, 0, 1),
                )
                qa_minus.button(
                    "−", key=f"qs_am_{quick_match_id}", use_container_width=True,
                    on_click=_adjust_quick_score, args=(draft_key, 1, -1),
                )
                qa_plus.button(
                    "+", key=f"qs_ap_{quick_match_id}", use_container_width=True,
                    on_click=_adjust_quick_score, args=(draft_key, 1, 1),
                )
                qc.markdown(
                    f"<div class='cn-reporter-score'>{quick_home_score}–{quick_away_score}</div>",
                    unsafe_allow_html=True,
                )
                save_col, reset_col = st.columns([3, 1])
                playoff_tie_needs_detail = quick_match["stage"] != "Gruppspel" and quick_home_score == quick_away_score
                save_col.button(
                    "✅ Spara resultat",
                    key=f"qs_save_{quick_match_id}",
                    type="primary",
                    use_container_width=True,
                    disabled=playoff_tie_needs_detail,
                    on_click=_save_quick_result_callback,
                    args=(deps, tournament_id, quick_match, draft_key),
                )
                reset_col.button(
                    "↺",
                    key=f"qs_reset_{quick_match_id}",
                    help="Återställ till senast sparade resultat",
                    use_container_width=True,
                    on_click=_reset_quick_score,
                    args=(draft_key, int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)),
                )
            _render_reporter_correction_window(int(quick_match_id))
            persisted_result = quick_match["home_score"] is not None and quick_match["away_score"] is not None
            if _advanced_reporting and _player_event_tracking:
                with st.expander("Fler matchdetaljer / massinmatning", expanded=False):
                    st.caption(
                        "Visar bara de händelsetyper som arrangören valde i setupen. "
                        "Öppna främst för historiska kompletteringar eller massinmatning."
                    )
                    _render_match_event_entry(
                        tournament_id, tournament, int(quick_match_id), quick_match, deps
                    )
            if persisted_result:
                next_match_id = _next_unreported_match_id(playable_matches, int(quick_match_id))
                if next_match_id is not None:
                    next_match = by_id[next_match_id]
                    st.caption(f"Nästa att rapportera: {deps.match_result_label(next_match)}")
                    st.button(
                        "Nästa orapporterade match →",
                        key=f"reporter_next_match_{quick_match_id}_{next_match_id}",
                        use_container_width=True,
                        on_click=_select_quick_score_match,
                        args=(quick_score_widget_key, next_match_id),
                    )
                else:
                    st.caption("✓ Inga fler orapporterade matcher senare i schemat.")
            if playoff_tie_needs_detail:
                st.info(
                    "Oavgjord slutspelsmatch behöver straffar eller annat avgörande. "
                    "Byt till Avancerad rapportering för att registrera det."
                )

            if not _advanced_reporting and _player_event_tracking:
                _enabled_labels = []
                if _scorer_tracking:
                    _enabled_labels.append("målskytt")
                if _assist_tracking:
                    _enabled_labels.append("assist")
                if _card_tracking:
                    _enabled_labels.append("kort")
                st.caption((", ".join(_enabled_labels)).capitalize() + " finns i Avancerad rapportering.")
            if _advanced_reporting:
                st.divider()
                _show_bulk_results = st.toggle(
                    "Fler resultatfält & massinmatning",
                    value=playoff_tie_needs_detail,
                    key=f"reporter_show_bulk_results_{tournament_id}",
                    help="Öppna bara när du behöver straffar, avgörande vinnare eller flera resultat samtidigt.",
                )
                if _show_bulk_results:
                    st.caption("Använd för straffar, avgörande vinnare eller när flera resultat ska registreras samtidigt.")

                    # v486: truly lazy. Avoid team query, dataframe construction and data_editor
                    # on the hot reporter path until the operator explicitly opens bulk mode.
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
                        try:
                            outcome = deps.save_bulk_results(tournament_id, original_by_id, updates)
                        except Exception:
                            _set_write_failure_notice(operation="Flera resultat")
                            st.rerun()
                        if outcome["saved"]:
                            st.session_state["reporter_result_message"] = "Sparat automatiskt"
                            if updates:
                                _mark_reporter_edit(int(updates[-1]["match_id"]), "Resultat")
                        if outcome["conflicts"]:
                            st.session_state["reporter_conflict_message"] = f"{outcome['conflicts']} match(er) hade ändrats av en annan rapportör och skrevs inte över. De senaste värdena har laddats om."
                    st.caption("✓ Kompletta resultat sparas automatiskt.")

    if reporter_section == _events_section and _setup_player_events:
        played_matches = fetch_completed_matches(deps.query_all, tournament_id)
        playable_matches = select_playable_matches(played_matches, resolve_source=deps.resolve_source)
        if not playable_matches:
            st.info("Rapportera först ett matchresultat. Därefter kan matchhändelser registreras.")
        else:
            by_id = {int(row["id"]): row for row in playable_matches}
            match_id = st.selectbox(
                "Välj match", list(by_id),
                format_func=lambda selected_id: deps.match_result_label(by_id[int(selected_id)]),
                key=f"reporter_event_match_{tournament_id}",
            )
            match_row = by_id[int(match_id)]
            _render_match_event_entry(
                tournament_id, tournament, int(match_id), match_row, deps
            )

    if reporter_section == _referee_section:
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
                    if assignment["id"] in acked:
                        st.success("Uppdraget är bekräftat.", icon="✅")
                    else:
                        st.button(
                            "Bekräfta att jag sett matchen",
                            key=f"ref_ack_{referee_id}_{assignment['id']}",
                            use_container_width=True,
                            on_click=deps.acknowledge_referee,
                            args=(tournament_id, referee_id, int(assignment["id"])),
                        )

    if reporter_section == _offline_section:
        st.markdown("### 📶 Offlineutkast")
        st.caption("Streamlit kräver serverkontakt för riktig synkronisering. Den här säkerhetsfunktionen sparar därför ett lokalt resultatutkast i webbläsaren om nätet blir dåligt. Utkastet ligger kvar på enheten och kan föras över till CupNavi Score när nätet återkommer.")
        offline_matches = fetch_scheduled_matches(deps.query_all, tournament_id)
        offline_options = build_offline_match_options(offline_matches, swedish_datetime=deps.swedish_datetime, source_label=deps.source_label)
        components.html(build_offline_draft_html(offline_options, tournament_id), height=235, scrolling=False)
