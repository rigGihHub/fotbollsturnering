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
    set_match_status: Callable[[int, Any, str], bool]



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
        team_goals = int(match_row["home_score"] if selected_team_id == home_team_id else match_row["away_score"])
        assist_enabled = bool(deps.row_value(tournament, "enable_assist_leaderboard", 1))
        card_statistics_enabled = bool(deps.row_value(tournament, "enable_card_statistics", 1))
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
        if prev_col.button(
            "← Föregående spelare",
            key=f"reporter_prev_player_{match_id}_{selected_team_id}_{player_id}",
            use_container_width=True,
            disabled=player_index <= 0,
        ):
            st.session_state[player_widget_key] = player_ids[player_index - 1]
            st.rerun()
        if next_col.button(
            "Nästa spelare →",
            key=f"reporter_next_player_{match_id}_{selected_team_id}_{player_id}",
            use_container_width=True,
            disabled=player_index >= len(player_ids) - 1,
        ):
            st.session_state[player_widget_key] = player_ids[player_index + 1]
            st.rerun()
        current = existing.get(player_id)
        current_values = {
            "goals": int(current["goals"] or 0) if current else 0,
            "assists": int(current["assists"] or 0) if current else 0,
            "yellow_cards": int(current["yellow_cards"] or 0) if current else 0,
            "red_cards": int(current["red_cards"] or 0) if current else 0,
        }
        st.caption(
            f"Denna spelare: ⚽ {current_values['goals']} · 🎯 {current_values['assists']} · "
            f"🟨 {current_values['yellow_cards']} · 🟥 {current_values['red_cards']}"
        )
        quick_message_key = f"reporter_quick_event_message_{match_id}_{selected_team_id}"
        quick_last_event_key = f"reporter_quick_last_event_{match_id}_{selected_team_id}"
        quick_last_event_detail_key = f"reporter_quick_last_event_detail_{match_id}_{selected_team_id}"
        quick_conflict_key = f"reporter_quick_event_conflict_{match_id}_{selected_team_id}"
        if quick_message_key in st.session_state:
            st.success(st.session_state.pop(quick_message_key), icon="✅")
        if quick_last_event_key in st.session_state:
            st.caption(f"Senast registrerat: {st.session_state[quick_last_event_key]}")
            last_detail = st.session_state.get(quick_last_event_detail_key)
            if isinstance(last_detail, dict) and st.button(
                "↩️ Ångra senaste",
                key=f"reporter_quick_undo_{match_id}_{selected_team_id}",
                use_container_width=True,
            ):
                target_player_id = int(last_detail.get("player_id", 0) or 0)
                target_field = str(last_detail.get("field", "") or "")
                target_label = str(last_detail.get("label", "Händelse") or "Händelse")
                if target_player_id not in player_by_id or target_field not in {"goals", "assists", "yellow_cards", "red_cards"}:
                    st.session_state[quick_conflict_key] = "Den senaste händelsen kan inte längre identifieras säkert."
                    st.rerun()
                undo_update = prepare_quick_event_update(
                    existing, match_id=match_id, player_id=target_player_id, field=target_field, delta=-1
                )
                if undo_update is None:
                    st.session_state[quick_conflict_key] = "Händelsen är redan borttagen eller ändrad."
                    st.rerun()
                undo_totals = event_totals_after_update(existing, undo_update)
                undo_validation = validate_match_event_totals(
                    team_goals, undo_totals["goals"], undo_totals["assists"]
                )
                if not undo_validation["ok"]:
                    st.session_state[quick_conflict_key] = undo_validation["errors"][0]
                    st.rerun()
                undo_outcome = deps.save_event_rows([undo_update])
                if undo_outcome["conflicts"]:
                    st.session_state[quick_conflict_key] = (
                        "Händelsen ändrades av en annan rapportör och kunde inte ångras. Senaste värden laddas om."
                    )
                elif undo_outcome["saved"]:
                    st.session_state[quick_message_key] = f"{target_label} ångrades."
                    st.session_state.pop(quick_last_event_key, None)
                    st.session_state.pop(quick_last_event_detail_key, None)
                st.rerun()
        if quick_conflict_key in st.session_state:
            st.warning(st.session_state.pop(quick_conflict_key), icon="⚠️")

        def _apply_quick_event(field: str, delta: int, label: str) -> None:
            update = prepare_quick_event_update(
                existing, match_id=match_id, player_id=player_id, field=field, delta=delta
            )
            if update is None:
                return
            totals = event_totals_after_update(existing, update)
            validation = validate_match_event_totals(team_goals, totals["goals"], totals["assists"])
            if not validation["ok"]:
                st.session_state[quick_conflict_key] = validation["errors"][0]
                st.rerun()
            outcome = deps.save_event_rows([update])
            if outcome["conflicts"]:
                st.session_state[quick_conflict_key] = (
                    "Spelarens händelser ändrades av en annan rapportör och skrevs inte över. "
                    "Senaste värden laddas om."
                )
            elif outcome["saved"]:
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
            st.rerun()

        action_specs = [("goals", "⚽ + Mål", "Mål")]
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
                if cols[offset].button(
                    button_label,
                    key=f"reporter_quick_add_{field}_{match_id}_{selected_team_id}_{player_id}",
                    use_container_width=True,
                    type="primary" if field == "goals" else "secondary",
                ):
                    _apply_quick_event(field, 1, success_label)

        with st.expander("↩️ Korrigera senaste händelser", expanded=False):
            correction_specs = [("goals", "− Mål", "Mål korrigerat")]
            if assist_enabled:
                correction_specs.append(("assists", "− Assist", "Assist korrigerad"))
            if card_statistics_enabled:
                correction_specs.extend([
                    ("yellow_cards", "− Gult", "Gult kort korrigerat"),
                    ("red_cards", "− Rött", "Rött kort korrigerat"),
                ])
            for field, button_label, success_label in correction_specs:
                if st.button(
                    button_label,
                    key=f"reporter_quick_sub_{field}_{match_id}_{selected_team_id}_{player_id}",
                    use_container_width=True,
                    disabled=current_values[field] <= 0,
                ):
                    _apply_quick_event(field, -1, success_label)

        total_goals = sum(int(row["goals"] or 0) for row in existing.values())
        total_assists = sum(int(row["assists"] or 0) for row in existing.values())
        st.caption(
            f"Matchresultat: {team_goals} mål · registrerade spelarmål: {total_goals} · "
            f"registrerade assist: {total_assists}"
        )

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
            entered_goals = int(edited["Mål"].fillna(0).sum())
            entered_assists = int(edited["Assist"].fillna(0).sum())
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
                    outcome = deps.save_event_rows(changed_rows)
                    if outcome["conflicts"]:
                        st.session_state[conflict_key] = (
                            f"{outcome['conflicts']} spelarrad(er) hade ändrats av en annan rapportör "
                            "och skrevs inte över. Senaste värden laddas om."
                        )
                    if outcome["saved"]:
                        st.session_state[autosave_key] = "Sparat automatiskt"
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
    st.caption(
        "Här kan du endast rapportera resultat samt mål, assist, varningar och utvisningar. "
        "Övrig administration är inte tillgänglig."
    )
    # Reporterläget används ofta stående på telefon vid plan. Ge knapparna en
    # större touchyta utan att påverka övriga CupNavi-vyer.
    st.markdown(
        """<style>
        div[data-testid="stButton"] > button { min-height: 52px; }
        </style>""",
        unsafe_allow_html=True,
    )
    reporter_sections = [
        deps.translate("CupNavi Score"), deps.translate("Matchhändelser"),
        deps.translate("Domarcentral"), deps.translate("Offlineutkast")
    ]
    reporter_section = st.segmented_control(
        "Arbetsyta",
        reporter_sections,
        default=reporter_sections[0],
        key=f"reporter_workspace_section_{tournament_id}",
        label_visibility="collapsed",
    ) or reporter_sections[0]

    if reporter_section == reporter_sections[0]:
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
            _reporting_mode = st.segmented_control(
                "Rapporteringsläge",
                ["Enkel", "Avancerad"],
                default="Enkel",
                key=f"reporter_mode_{tournament_id}",
                help=(
                    "Enkel: välj match, ange slutresultat och spara. "
                    "Avancerad: lägg även till matchstatus, mål, assist, kort och slutspelsavgöranden."
                ),
            ) or "Enkel"
            _advanced_reporting = _reporting_mode == "Avancerad"
            st.caption(
                "Snabbast möjligt: välj match → ange resultat → spara."
                if not _advanced_reporting
                else "Avancerat läge: matchstatus, matchhändelser och specialfall visas i samma arbetsflöde."
            )
            by_id = {int(row["id"]): row for row in playable_matches}
            match_queue = _reporter_match_queue(playable_matches)
            queue_ids = [int(row["id"]) for row in match_queue]
            unreported_ids = [int(row["id"]) for row in match_queue if not _match_has_saved_result(row)]
            next_unreported_id = unreported_ids[0] if unreported_ids else None
            st.caption(
                f"Matchkö · {len(unreported_ids)} orapporterade · "
                f"{len(match_queue) - len(unreported_ids)} rapporterade"
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
                    if _status_col.button(
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
                    ):
                        if not deps.set_match_status(tournament_id, quick_match, _status_value):
                            st.warning("Matchstatusen ändrades av någon annan. Sidan laddas om.")
                        st.rerun()
                if _current_status == MATCH_FINISHED and not (
                    deps.row_value(quick_match, "home_score", None) is not None
                    and deps.row_value(quick_match, "away_score", None) is not None
                ):
                    st.caption("Matchen är markerad som slut. Lägg till resultat om resultat används i arrangemanget.")
            elif _current_status in {MATCH_LIVE, MATCH_HALFTIME}:
                st.caption(f"Matchstatus: {match_status_label(_current_status)}")
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
            if save_col.button("✅ Spara resultat", key=f"qs_save_{quick_match_id}", type="primary", use_container_width=True, disabled=playoff_tie_needs_detail):
                if not deps.save_quick_result(tournament_id, quick_match, quick_home_score, quick_away_score):
                    st.error("Resultatet ändrades av en annan användare innan du hann spara. Sidan laddas om så att du ser det senaste resultatet.")
                    st.session_state.pop(draft_key, None); st.rerun()
                st.session_state["reporter_result_message"] = "Slutresultatet är sparat."
                st.rerun()
            if reset_col.button("Återställ", key=f"qs_reset_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key] = [int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)]; st.rerun()
            persisted_result = quick_match["home_score"] is not None and quick_match["away_score"] is not None
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
                if _advanced_reporting:
                    st.divider()
                    st.markdown("### ⚽ Livehändelser")
                    st.caption(
                        "Registrera mål, assist och kort för samma match här. Händelserna valideras mot det senast sparade resultatet."
                    )
                    _render_match_event_entry(
                        tournament_id, tournament, int(quick_match_id), quick_match, deps
                    )
            if playoff_tie_needs_detail:
                st.info(
                    "Oavgjord slutspelsmatch behöver straffar eller annat avgörande. "
                    "Byt till Avancerad rapportering för att registrera det."
                )

            if not _advanced_reporting:
                st.caption("Behöver du målskyttar, assist, kort, straffar eller massinmatning? Välj Avancerad ovan.")
            if _advanced_reporting:
                st.divider()
                with st.expander("Fler resultatfält & massinmatning", expanded=playoff_tie_needs_detail):
                    st.caption("Använd för straffar, avgörande vinnare eller när flera resultat ska registreras samtidigt.")

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

    if reporter_section == reporter_sections[1]:
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

    if reporter_section == reporter_sections[2]:
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

    if reporter_section == reporter_sections[3]:
        st.markdown("### 📶 Offlineutkast")
        st.caption("Streamlit kräver serverkontakt för riktig synkronisering. Den här säkerhetsfunktionen sparar därför ett lokalt resultatutkast i webbläsaren om nätet blir dåligt. Utkastet ligger kvar på enheten och kan föras över till CupNavi Score när nätet återkommer.")
        offline_matches = fetch_scheduled_matches(deps.query_all, tournament_id)
        offline_options = build_offline_match_options(offline_matches, swedish_datetime=deps.swedish_datetime, source_label=deps.source_label)
        components.html(build_offline_draft_html(offline_options, tournament_id), height=210, scrolling=False)
