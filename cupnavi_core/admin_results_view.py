"""Admin results workspace orchestration.

All persistence-sensitive result writes and optimistic-locking behavior stay injected
from app.py. This module owns presentation and update preparation only.
"""

from __future__ import annotations

from dataclasses import dataclass
import html
from typing import Any, Callable

import pandas as pd

from cupnavi_core.admin_results_repository import fetch_admin_results_data


@dataclass(frozen=True)
class AdminResultsDependencies:
    st: Any
    all_rows: Callable[..., Any]
    match_result_label: Callable[..., str]
    portal_match_label: Callable[..., str]
    match_meta: Callable[..., Any]
    source_label: Callable[..., str]
    resolve_source: Callable[..., Any]
    render_centered_table: Callable[..., Any]
    render_empty_state: Callable[..., Any]
    save_result_updates: Callable[..., Any]
    open_admin_page: Callable[[str], Any] | None = None


def _optional_int(value):
    return None if pd.isna(value) else int(value)


def prepare_admin_result_updates(
    edited_results,
    *,
    playable_matches,
    referee_ids_by_name,
    result_team_id_by_name,
    playoff_tie_rule,
):
    """Build optimistic-locking payloads without writing to storage."""
    original_match_by_id = {int(match_row["id"]): match_row for match_row in playable_matches}
    updates = []
    info_messages = []
    errors = []

    for _, row in edited_results.iterrows():
        match_id = int(row["match_id"])
        original_match = original_match_by_id[match_id]

        home_score = _optional_int(row["Hemmamål"])
        away_score = _optional_int(row["Bortamål"])
        home_penalties = _optional_int(row["Hemmastraffar"])
        away_penalties = _optional_int(row["Bortastraffar"])
        referee_id = referee_ids_by_name.get(row["Domare"])

        original_home = original_match["home_score"]
        original_away = original_match["away_score"]
        original_hp = original_match["home_penalties"]
        original_ap = original_match["away_penalties"]
        original_decided = original_match["decided_winner_id"]
        original_referee = original_match["referee_id"]

        row_changed = any([
            home_score != original_home,
            away_score != original_away,
            home_penalties != original_hp,
            away_penalties != original_ap,
            referee_id != original_referee,
            (
                row["Fas"] != "Gruppspel"
                and result_team_id_by_name.get(row["Avgörande vinnare"]) != original_decided
                and row["Avgörande vinnare"] != "–"
            ),
        ])
        if not row_changed:
            continue

        if (home_score is None) != (away_score is None):
            info_messages.append(
                f"{row['Hemmalag']}–{row['Bortalag']}: fyll i båda målresultaten så sparas det automatiskt."
            )
            continue

        decided_winner_id = None
        if row["Fas"] == "Gruppspel":
            home_penalties = None
            away_penalties = None
        elif home_score is not None and home_score == away_score:
            home_team_id = result_team_id_by_name.get(row["Hemmalag"])
            away_team_id = result_team_id_by_name.get(row["Bortalag"])

            if playoff_tie_rule == "Lottning":
                selected_winner_id = result_team_id_by_name.get(row["Avgörande vinnare"])
                home_penalties = None
                away_penalties = None
                if selected_winner_id in (home_team_id, away_team_id):
                    decided_winner_id = selected_winner_id
                else:
                    info_messages.append(
                        f"{row['Hemmalag']}–{row['Bortalag']}: resultatet sparas, men välj vinnare av lottningen för att avgöra matchen."
                    )
            else:
                if home_penalties is not None or away_penalties is not None:
                    if (
                        home_penalties is None
                        or away_penalties is None
                        or home_penalties == away_penalties
                    ):
                        errors.append(
                            f"{row['Hemmalag']}–{row['Bortalag']}: fyll i ett komplett och avgörande straffresultat."
                        )
                        continue
                else:
                    info_messages.append(
                        f"{row['Hemmalag']}–{row['Bortalag']}: det oavgjorda resultatet sparas. Ange straffresultat för att avgöra matchen."
                    )
        else:
            home_penalties = None
            away_penalties = None

        updates.append({
            "match_id": match_id,
            "home_score": home_score,
            "away_score": away_score,
            "home_penalties": home_penalties,
            "away_penalties": away_penalties,
            "decided_winner_id": decided_winner_id,
            "referee_id": referee_id,
            "expected": {
                "home_score": original_home,
                "away_score": original_away,
                "home_penalties": original_hp,
                "away_penalties": original_ap,
                "decided_winner_id": original_decided,
                "referee_id": original_referee,
            },
        })

    return updates, info_messages, errors, original_match_by_id


def render_admin_results_workspace(tid, tournament, *, deps: AdminResultsDependencies):
    st = deps.st
    matches, refs, all_result_teams = fetch_admin_results_data(deps.all_rows, tid)

    st.header("Resultat")
    st.caption("Registrera resultat. Domare kan justeras direkt i samma tabell.")

    # v339: detailed event editing and statistics are still available, but they
    # are contextual result tools rather than global match destinations.
    if deps.open_admin_page is not None:
        with st.expander("Fler resultatverktyg", expanded=False):
            st.caption("Öppna bara när du behöver detaljredigera händelser eller följa tabeller och topplistor.")
            tool_col1, tool_col2 = st.columns(2)
            tool_col1.button(
                "Detaljerade matchhändelser",
                key=f"v339_result_events_{tid}",
                use_container_width=True,
                on_click=deps.open_admin_page,
                args=("Matchhändelser",),
            )
            tool_col2.button(
                "Tabeller & topplistor",
                key=f"v339_result_stats_{tid}",
                use_container_width=True,
                on_click=deps.open_admin_page,
                args=("Tabeller",),
            )

    match_by_id = {int(row["id"]): row for row in matches}
    focus_kind = st.session_state.get(f"admin_search_focus_kind_{tid}")
    focus_entity = st.session_state.get(f"admin_search_focus_entity_{tid}")
    if focus_kind == "Match" and focus_entity:
        focused_match = match_by_id.get(int(focus_entity))
        if focused_match:
            with st.container(border=True):
                focused_match_label = deps.match_result_label(focused_match) if (
                    focused_match["home_score"] is not None
                    and focused_match["away_score"] is not None
                ) else deps.portal_match_label(focused_match)
                st.markdown(f"### 🔎 {html.escape(focused_match_label)}")
                st.caption("Öppnad från Sök i cupen")

    total = len(matches)
    played = sum(1 for row in matches if row["home_score"] is not None and row["away_score"] is not None)
    pct = int(round((played / total) * 100)) if total else 0
    st.markdown(
        f"<div class='cn-progress-hero'><div><span>Resultatstatus</span><strong>{played}/{total}</strong></div>"
        f"<div class='cn-progress-track'><i style='width:{pct}%'></i></div></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "✓ Publika resultat uppdateras automatiskt."
        if tournament["is_published"]
        else "Cupen är i utkast – resultaten sparas nu och blir publika när cupen publiceras."
    )
    st.caption("Registrera resultat match för match eller använd massinmatning när det passar.")
    if "bulk_result_message" in st.session_state:
        st.success(st.session_state.pop("bulk_result_message"), icon="✅")
    if "bulk_result_conflict_message" in st.session_state:
        st.warning(st.session_state.pop("bulk_result_conflict_message"))

    if not matches:
        deps.render_empty_state(
            "Inga matcher ännu",
            "Skapa eller generera schemat först. Därefter kan resultat registreras här.",
            symbol="—",
        )
        return

    show_full_result_schedule = st.toggle(
        "Visa hela matchschemat", value=False, key=f"show_full_result_schedule_{tid}",
        help="Listan byggs först när du öppnar den."
    )
    if show_full_result_schedule:
        all_match_rows = []
        for match_row in sorted(
            matches,
            key=lambda row: (
                row["scheduled_start"] is None,
                row["scheduled_start"] or "9999-12-31T23:59",
                row["pitch_number"] or 999,
                row["id"],
            ),
        ):
            schedule_text, referee_name = deps.match_meta(match_row)
            all_match_rows.append({
                "Match": schedule_text.split(" · ", 1)[0] if match_row["scheduled_start"] else "Ej schemalagd",
                "Fas": match_row["stage"],
                "Tid/plan": schedule_text.replace(schedule_text.split(" · ", 1)[0] + " · ", "", 1) if match_row["scheduled_start"] else "Ej schemalagd",
                "Hemmalag": deps.source_label(match_row["home_source"]),
                "Bortalag": deps.source_label(match_row["away_source"]),
                "Domare": referee_name,
            })
        deps.render_centered_table(pd.DataFrame(all_match_rows))
        st.caption(
            "Slutspelsmatcherna visas även innan lagen är klara. Exempel: Vinnaren i Grupp A eller Vinnare match 17."
        )

    playable_matches = [
        row for row in matches
        if deps.resolve_source(row["home_source"]) and deps.resolve_source(row["away_source"])
    ]
    unresolved_count = len(matches) - len(playable_matches)
    if unresolved_count:
        with st.expander(f"Kommande slutspelsmatcher · {unresolved_count} väntar på lag", expanded=False):
            st.caption("Dessa matcher blir möjliga att resultatregistrera automatiskt när föregående matcher eller grupper är avgjorda.")
    if not playable_matches:
        st.info("Det finns ännu inga matcher med två klara lag.")
        return

    referee_names = {row["id"]: row["name"] for row in refs}
    referee_ids_by_name = {row["name"]: row["id"] for row in refs}
    referee_options = ["Ej tillsatt"] + [row["name"] for row in refs]
    result_team_name_by_id = {row["id"]: row["name"] for row in all_result_teams}
    result_team_id_by_name = {row["name"]: row["id"] for row in all_result_teams}
    decision_options = ["–"] + [row["name"] for row in all_result_teams]

    result_rows = []
    for match_row in playable_matches:
        schedule_text, _ = deps.match_meta(match_row)
        result_rows.append({
            "match_id": match_row["id"],
            "Match": schedule_text,
            "Fas": match_row["stage"],
            "Hemmalag": deps.source_label(match_row["home_source"]),
            "Hemmamål": match_row["home_score"],
            "Bortamål": match_row["away_score"],
            "Bortalag": deps.source_label(match_row["away_source"]),
            "Hemmastraffar": match_row["home_penalties"] if match_row["stage"] != "Gruppspel" else None,
            "Bortastraffar": match_row["away_penalties"] if match_row["stage"] != "Gruppspel" else None,
            "Avgörande vinnare": result_team_name_by_id.get(match_row["decided_winner_id"], "–") if match_row["stage"] != "Gruppspel" else "–",
            "Domare": referee_names.get(match_row["referee_id"], "Ej tillsatt"),
        })

    edited_results = st.data_editor(
        pd.DataFrame(result_rows),
        hide_index=True,
        use_container_width=True,
        disabled=["match_id", "Match", "Fas", "Hemmalag", "Bortalag"],
        column_order=["Match", "Fas", "Hemmalag", "Hemmamål", "Bortamål", "Bortalag", "Hemmastraffar", "Bortastraffar", "Avgörande vinnare", "Domare"],
        column_config={
            "Hemmamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
            "Bortamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
            "Hemmastraffar": st.column_config.NumberColumn("Straffar hemma", min_value=0, max_value=99, step=1),
            "Bortastraffar": st.column_config.NumberColumn("Straffar borta", min_value=0, max_value=99, step=1),
            "Avgörande vinnare": st.column_config.SelectboxColumn(options=decision_options),
            "Domare": st.column_config.SelectboxColumn(options=referee_options),
        },
        key=f"bulk_results_{tid}",
    )

    if any(match_row["stage"] != "Gruppspel" for match_row in playable_matches):
        with st.expander("Regler vid oavgjort i slutspel", expanded=False):
            if tournament["playoff_tie_rule"] == "Lottning":
                st.caption("Välj vinnaren i kolumnen Avgörande vinnare enligt tävlingsregeln Lottning.")
            elif tournament["playoff_tie_rule"] == "Förlängning + straffar":
                st.caption(f"Vid oavgjort spelas {tournament['extra_time_minutes']} min förlängning och därefter straffar. Registrera straffresultatet vid fortsatt oavgjort.")
            else:
                st.caption("Vid oavgjort avgörs slutspelsmatchen med straffar direkt. Registrera straffresultatet.")

    auto_updates, auto_messages, auto_errors, original_match_by_id = prepare_admin_result_updates(
        edited_results,
        playable_matches=playable_matches,
        referee_ids_by_name=referee_ids_by_name,
        result_team_id_by_name=result_team_id_by_name,
        playoff_tie_rule=tournament["playoff_tie_rule"],
    )
    for message in auto_errors:
        st.error(message)
    for message in auto_messages:
        st.info(message)

    if auto_updates:
        deps.save_result_updates(auto_updates, original_match_by_id)

    st.caption("✓ Ändringar sparas automatiskt – ingen Spara-knapp behövs.")
