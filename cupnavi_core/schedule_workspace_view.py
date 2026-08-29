"""Schedule workspace orchestration for the admin UI.

The schedule engine and persistence-sensitive write operations stay injected from app.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import re
import time
from typing import Any, Callable

import pandas as pd


@dataclass(frozen=True)
class ScheduleWorkspaceDependencies:
    st: Any
    one_row: Callable[..., Any]
    run: Callable[..., Any]
    all_rows: Callable[..., Any]
    validate_schedule: Callable[..., Any]
    playoff_specs_for_tournament: Callable[..., Any]
    schedule_score_report: Callable[..., Any]
    schedule_request_label: Callable[..., Any]
    render_schedule_recovery_actions: Callable[..., Any]
    optimize_group_home_away: Callable[..., Any]
    ensure_playoffs_for_schedule: Callable[..., Any]
    generate_schedule: Callable[..., Any]
    create_all_group_matches: Callable[..., Any]
    schedule_recovery_context: Callable[..., Any]
    render_centered_table: Callable[..., Any]
    source_label: Callable[..., Any]
    resolve_source: Callable[..., Any]
    undo_schedule_change: Callable[..., Any]
    schedule_board: Callable[..., Any]
    swedish_datetime: Callable[..., Any]
    apply_drag_schedule_updates: Callable[..., Any]
    match_meta: Callable[..., Any]
    save_adjusted_schedule_match: Callable[..., Any]
    pitch_name_map: Callable[..., Any]
    team: Callable[..., Any]
    match_kit_colors: Callable[..., Any]
    kit_color_conflict: Callable[..., Any]
    kit_swatch: Callable[..., Any]
    save_bulk_schedule_results: Callable[..., Any]
    sort_items: Any
    swedish_weekdays: Any


def render_schedule_workspace(tid, tournament, *, deps: ScheduleWorkspaceDependencies):
    st = deps.st
    one_row = deps.one_row
    run = deps.run
    all_rows = deps.all_rows
    validate_schedule = deps.validate_schedule
    playoff_specs_for_tournament = deps.playoff_specs_for_tournament
    schedule_score_report = deps.schedule_score_report
    schedule_request_label = deps.schedule_request_label
    render_schedule_recovery_actions = deps.render_schedule_recovery_actions
    optimize_group_home_away = deps.optimize_group_home_away
    ensure_playoffs_for_schedule = deps.ensure_playoffs_for_schedule
    generate_schedule = deps.generate_schedule
    create_all_group_matches = deps.create_all_group_matches
    _schedule_recovery_context = deps.schedule_recovery_context
    render_centered_table = deps.render_centered_table
    source_label = deps.source_label
    resolve_source = deps.resolve_source
    undo_schedule_change = deps.undo_schedule_change
    schedule_board = deps.schedule_board
    swedish_datetime = deps.swedish_datetime
    apply_drag_schedule_updates = deps.apply_drag_schedule_updates
    match_meta = deps.match_meta
    save_adjusted_schedule_match = deps.save_adjusted_schedule_match
    pitch_name_map = deps.pitch_name_map
    team = deps.team
    match_kit_colors = deps.match_kit_colors
    kit_color_conflict = deps.kit_color_conflict
    kit_swatch = deps.kit_swatch
    save_bulk_schedule_results = deps.save_bulk_schedule_results
    sort_items = deps.sort_items
    SWEDISH_WEEKDAYS = deps.swedish_weekdays

    st.header("Schema")
    st.caption("Skapa eller uppdatera hela spelschemat. Detaljer och specialverktyg visas bara när du öppnar dem.")
    if "schedule_message" in st.session_state:
        message_type, message_text = st.session_state.pop("schedule_message")
        getattr(st, message_type)(message_text)

    rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    if rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
        rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))

    # v1.261: st.expander är inte lazy. Den gamla score-analysen kördes därför
    # vid varje rerun trots att användaren inte öppnat den.
    _show_schedule_quality = st.toggle(
        "Visa regelverk & schemakvalitet",
        value=False,
        key=f"show_schedule_quality_{tid}",
        help="Analysen laddas först när du öppnar den.",
    )
    if _show_schedule_quality:
        with st.container(border=True):
            st.markdown("#### Regelverk & schemakvalitet")
            match_minutes = (rules["halves"] * rules["minutes_per_half"]) + ((rules["halves"] - 1) * rules["halftime_minutes"])
            consecutive_rule_text = (
                f"försök undvika följdmatcher, extra paus {rules['consecutive_match_break_minutes']} min om det inte går"
                if rules["avoid_consecutive_matches"] else "följdmatcher tillåtna"
            )
            st.info(
                f"{rules['halves']} × {rules['minutes_per_half']} minuter · halvtidspaus {rules['halftime_minutes']} min · "
                f"matchtid totalt {match_minutes} min · {rules['pitch_count']} planer/spelytor med individuella öppettider · "
                f"{consecutive_rule_text} · domare: {rules['referee_mode']}."
            )
            st.caption("Regelverket och slutspelsformatet ändras under Adminöversikt → Cupens grunduppgifter.")
            _score_report=schedule_score_report(tid,rules)
            _sc1,_sc2,_sc3,_sc4=st.columns(4)
            _sc1.metric("Schema Score",f"{_score_report['score']}/100")
            _sc2.metric("Bedömning",_score_report["grade"])
            _sc3.metric("Önskemål",f"{_score_report['fulfilled']}/{_score_report['request_total']}")
            _sc4.metric("Hårda krav brutna",_score_report["hard_failed"])
            with st.expander("Varför fick schemat den här poängen?",expanded=False):
                _q=_score_report["quality"]
                st.write(f"• Ej schemalagda matcher: **{_q['unscheduled']}**")
                st.write(f"• För kort lagvila: **{_q['short_rest']}**")
                st.write(f"• Sena-startönskemål missade: **{_q['late_preferences_missed']}**")
                if _score_report["requests"]:
                    st.markdown("**Godkända lagönskemål**")
                    for _req,_ok,_detail in _score_report["requests"]:
                        _icon="✅" if _ok is True else ("⚠️" if _ok is False else "➖")
                        st.write(f"{_icon} {schedule_request_label(_req)} · {_detail}")
                else:
                    st.caption("Inga godkända lagönskemål finns ännu.")

    if st.session_state.get("schedule_recovery"):
        render_schedule_recovery_actions(tid,tournament,rules,st.session_state.get("schedule_recovery"))
    schedule_groups = all_rows("SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    schedule_teams = all_rows("SELECT id,group_id FROM teams WHERE tournament_id=?", (tid,))
    unassigned_count = sum(1 for team_row in schedule_teams if team_row["group_id"] is None)
    _schedule_team_counts = {}
    for _team_row in schedule_teams:
        _gid = _team_row["group_id"]
        if _gid is not None:
            _schedule_team_counts[int(_gid)] = _schedule_team_counts.get(int(_gid), 0) + 1
    too_small_groups = [
        group["name"] for group in schedule_groups
        if _schedule_team_counts.get(int(group["id"]), 0) < 2
    ]
    # v1.261: fem COUNT-frågor blev en enda status-snapshot.
    _schedule_counts = one_row(
        """SELECT
             SUM(CASE WHEN stage='Gruppspel' THEN 1 ELSE 0 END) AS group_match_n,
             SUM(CASE WHEN stage='Gruppspel' AND scheduled_start IS NULL THEN 1 ELSE 0 END) AS unscheduled_group_n,
             SUM(CASE WHEN scheduled_start IS NOT NULL THEN 1 ELSE 0 END) AS scheduled_n,
             SUM(CASE WHEN scheduled_start IS NOT NULL AND schedule_published=0 THEN 1 ELSE 0 END) AS unpublished_n,
             SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS played_n
           FROM matches WHERE tournament_id=?""",
        (tid,),
    )
    group_match_total = int(_schedule_counts["group_match_n"] or 0)
    unscheduled_group_total = int(_schedule_counts["unscheduled_group_n"] or 0)
    scheduled_total = int(_schedule_counts["scheduled_n"] or 0)
    unpublished_total = int(_schedule_counts["unpublished_n"] or 0)
    played_result_total = int(_schedule_counts["played_n"] or 0)
    schedule_errors, schedule_warnings, schedule_quality = validate_schedule(tid, tournament, rules)
    playoff_specs, playoff_setup_error = playoff_specs_for_tournament(tid, tournament)
    playoff_model_ready = bool(tournament["playoff_model_confirmed"])

    st.markdown("#### Skapa eller uppdatera schema")
    with st.container(border=True):
        status1, status2, status3 = st.columns(3)
        status1.metric("Gruppspelsmatcher", group_match_total)
        status2.metric("Schemalagda matcher", scheduled_total)
        status3.metric("Ej publicerade", unpublished_total)
        create_disabled = (
            not schedule_groups
            or unassigned_count > 0
            or bool(too_small_groups)
            or not playoff_model_ready
            or bool(playoff_setup_error)
        )
        if tournament["playoff_format"] != "Inget slutspel":
            if playoff_setup_error:
                st.error(f"Slutspel kan inte genereras: {playoff_setup_error}")
            elif playoff_specs:
                _playoff_match_estimate = sum(max(0, int(size) - 1) + (1 if bool(tournament["bronze_match"]) and int(size) >= 4 else 0) for _, size, _ in playoff_specs)
                st.success(f"Slutspel redo att genereras · {len(playoff_specs)} träd · cirka {_playoff_match_estimate} slutspelsmatcher.")
            else:
                st.warning("Slutspel är valt men CupNavi kunde inte ta fram något slutspelsträd.")

        schedule_button_label = (
            "Uppdatera återstående schema"
            if played_result_total else "Skapa hela spelschemat"
        )
        st.caption(
            "Spelade matcher lämnas oförändrade."
            if played_result_total
            else "CupNavi skapar gruppspel, slutspel och fördelar tider, planer och domare."
        )
        if st.button(schedule_button_label, type="primary", use_container_width=True, disabled=create_disabled):
            started_schedule = time.perf_counter()
            try:
                with st.spinner("CupNavi bygger schemat och fördelar planer/domare…"):
                    if played_result_total:
                        created, ready_groups, skipped_groups = 0, len(schedule_groups), []
                        optimize_group_home_away(tid)
                        playoff_ok, playoff_error = ensure_playoffs_for_schedule(tid, tournament)
                        if not playoff_ok:
                            raise RuntimeError(playoff_error)
                        count, unresolved, warning = generate_schedule(tid, tournament, rules, preserve_existing=True)
                        parts = [
                            f"{played_result_total} färdigspelade matcher skyddades och lämnades oförändrade.",
                            "Slutspelsträdet kontrollerades och uppdaterades automatiskt.",
                            f"{count} återstående matcher schemalades.",
                        ]
                    else:
                        created, ready_groups, skipped_groups = create_all_group_matches(tid)
                        playoff_ok, playoff_error = ensure_playoffs_for_schedule(tid, tournament)
                        if not playoff_ok:
                            raise RuntimeError(playoff_error)
                        count, unresolved, warning = generate_schedule(tid, tournament, rules)
                        parts = [
                            f"Alla {ready_groups} grupper kontrollerades och {created} saknade gruppmatcher skapades.",
                            "Slutspelsmatcherna skapades automatiskt utifrån vald slutspelsmodell.",
                            f"{count} matcher schemalades totalt.",
                        ]
                elapsed = time.perf_counter() - started_schedule
                parts.append(f"Genereringen tog {elapsed:.1f} sekunder.")
                if unresolved:
                    parts.append(f"{unresolved} matcher kunde inte schemaläggas.")
                if warning:
                    parts.append(warning)
                st.session_state["schedule_message"] = (
                    "warning" if unresolved or warning else "success",
                    " ".join(parts),
                )
                if unresolved:
                    st.session_state["schedule_recovery"] = _schedule_recovery_context(tid,tournament,rules,unresolved)
                else:
                    st.session_state.pop("schedule_recovery",None)
            except Exception as exc:
                elapsed = time.perf_counter() - started_schedule
                st.session_state["schedule_message"] = (
                    "error",
                    f"Schemagenereringen avbröts efter {elapsed:.1f} sekunder: {exc}",
                )
            st.rerun()
        if played_result_total:
            st.info(
                f"Det finns {played_result_total} matcher med registrerat resultat. "
                "Därför bevaras befintliga schematider och resultat; endast återstående matcher får nya tider."
            )
        if create_disabled:
            problems = []
            if not schedule_groups:
                problems.append("skapa minst en grupp")
            if unassigned_count:
                problems.append(f"placera {unassigned_count} lag i en grupp")
            if too_small_groups:
                problems.append("lägg minst två lag i: " + ", ".join(too_small_groups))
            if not playoff_model_ready:
                problems.append("välj och spara slutspelsmodell på Adminöversikten")
            if playoff_setup_error:
                problems.append(playoff_setup_error)
            st.warning("Innan hela spelschemat kan skapas måste du " + "; ".join(problems) + ".")
        elif scheduled_total == 0:
            st.caption("Knappen ovan skapar gruppspel, slutspel och spelschema i ett steg.")
        elif schedule_errors:
            st.error(f"Schemat har {len(schedule_errors)} fel och kan inte publiceras. Se schemakontrollen nedan.")
        elif schedule_warnings:
            st.warning("Schemat har varningar. Granska dem och godkänn dem i vänsterspalten före publicering.")
        elif unpublished_total:
            st.warning("Schemat är ett utkast. Kontrollera matchlistan och publicera sedan från vänsterspalten.")
        else:
            st.success("Det aktuella spelschemat är publicerat i Turneringsvyn.")

        with st.expander("Detaljer per grupp", expanded=False):
            st.markdown("**Kontroll per grupp**")
            team_counts = {
                row["group_id"]: row["n"]
                for row in all_rows(
                    "SELECT group_id,COUNT(*) AS n FROM teams WHERE tournament_id=? AND group_id IS NOT NULL GROUP BY group_id",
                    (tid,),
                )
            }
            match_counts = {
                row["group_id"]: row
                for row in all_rows(
                    """SELECT group_id,
                              COUNT(*) AS created_n,
                              SUM(CASE WHEN scheduled_start IS NOT NULL THEN 1 ELSE 0 END) AS scheduled_n,
                              SUM(CASE WHEN schedule_published=1 THEN 1 ELSE 0 END) AS published_n
                       FROM matches
                       WHERE tournament_id=? AND stage='Gruppspel'
                       GROUP BY group_id""",
                    (tid,),
                )
            }
            group_status_rows = []
            for group in schedule_groups:
                team_count = int(team_counts.get(group["id"], 0) or 0)
                counts = match_counts.get(group["id"]) or {}
                expected_matches = team_count * (team_count - 1) // 2
                group_status_rows.append({
                    "Grupp": group["name"],
                    "Lag": team_count,
                    "Förväntade möten": expected_matches,
                    "Skapade": int(counts.get("created_n", 0) or 0),
                    "Schemalagda": int(counts.get("scheduled_n", 0) or 0),
                    "Publicerade": int(counts.get("published_n", 0) or 0),
                })
            if group_status_rows:
                render_centered_table(pd.DataFrame(group_status_rows))

    _show_schedule_export = st.toggle("Exportera schema", value=False, key=f"schedule_export_{tid}", help="Exportunderlaget laddas först när du behöver det.")
    if _show_schedule_export:
        st.markdown("**PDF-export**")
        st.caption(
            "Skapa ett komplett, utskriftsvänligt PDF-paket med hela schemat samt separata "
            "scheman per grupp, lag, plan, slutspel och domare."
        )
        pdf_matches = all_rows(
            "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL "
            "ORDER BY scheduled_start,pitch_number,id",
            (tid,),
        )
        if not pdf_matches:
            st.caption("PDF-export blir tillgänglig när ett schema finns.")
        else:
            pdf_key = f"schedule_pdf_bytes_{tid}"
            pdf_fingerprint_key = f"schedule_pdf_fingerprint_{tid}"
            pdf_fingerprint = "|".join(
                f"{m['id']}:{m['scheduled_start']}:{m['pitch_number']}:{m['home_source']}:{m['away_source']}:"
                f"{m['home_score']}:{m['away_score']}:{m['referee_id']}"
                for m in pdf_matches
            )

            if st.button("Skapa komplett schemapaket som PDF", use_container_width=True, key=f"prepare_pdf_{tid}"):
                with st.spinner("CupNavi skapar PDF-paketet…"):
                    pdf_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
                    pdf_groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
                    pdf_refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))

                    unique_sources = {
                        source
                        for match_row in pdf_matches
                        for source in (match_row["home_source"], match_row["away_source"])
                        if source
                    }
                    source_labels_for_pdf = {source: source_label(source) for source in unique_sources}
                    source_team_ids_for_pdf = {source: resolve_source(source) for source in unique_sources}

                    tournament_for_pdf = {
                        key: tournament[key]
                        for key in ("name", "location", "tournament_date", "start_date", "end_date")
                    }
                    matches_for_pdf = [
                        {
                            key: match_row[key]
                            for key in (
                                "id", "group_id", "stage", "scheduled_start", "pitch_number",
                                "home_source", "away_source", "home_score", "away_score",
                                "home_penalties", "away_penalties", "referee_id",
                            )
                        }
                        for match_row in pdf_matches
                    ]
                    teams_for_pdf = [
                        {key: team_row[key] for key in ("id", "name", "group_id")}
                        for team_row in pdf_teams
                    ]
                    groups_for_pdf = [
                        {key: group_row[key] for key in ("id", "name")}
                        for group_row in pdf_groups
                    ]
                    refs_for_pdf = [
                        {key: ref_row[key] for key in ("id", "name")}
                        for ref_row in pdf_refs
                    ]

                    from cupnavi_core.pdf_export import build_schedule_pdf

                    st.session_state[pdf_key] = build_schedule_pdf(
                        tournament_for_pdf,
                        matches_for_pdf,
                        teams_for_pdf,
                        groups_for_pdf,
                        refs_for_pdf,
                        source_labels_for_pdf,
                        source_team_ids_for_pdf,
                    )
                    st.session_state[pdf_fingerprint_key] = pdf_fingerprint

            if (
                pdf_key in st.session_state
                and st.session_state.get(pdf_fingerprint_key) == pdf_fingerprint
            ):
                safe_pdf_name = re.sub(r"[^A-Za-z0-9_-]+", "_", tournament["name"] or "CupNavi").strip("_")
                st.success("✓ PDF-paketet är klart.")
                st.download_button(
                    "Ladda ner alla scheman som PDF",
                    data=st.session_state[pdf_key],
                    file_name=f"{safe_pdf_name}_alla_scheman.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"download_schedule_pdf_{tid}",
                )
            elif pdf_key in st.session_state:
                st.warning("Schemat har ändrats sedan PDF:en skapades. Skapa PDF-paketet på nytt.")

    _show_schedule_travel = st.toggle("Reseinformation", value=False, key=f"schedule_travel_{tid}", help="Laginformationen laddas först när du öppnar den.")
    if _show_schedule_travel:
        travel_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
        st.markdown("**Reseinformation för lagen**")
        render_centered_table(
            pd.DataFrame([
                {
                    "Lag": t["name"],
                    "Resväg km": t["distance_km"],
                    "Senare första match": "Ja" if t["late_first_match"] else "Nej",
                    "Första match tidigast": t["earliest_first_time"] or "–",
                    "Kommentar": t["travel_note"] or "",
                }
                for t in travel_teams
            ])
        )
    undo_schedule_key = f"ux2_schedule_undo_{tid}"
    if st.session_state.get(undo_schedule_key):
        undo_cols = st.columns([5,1])
        undo_cols[0].success("Schemaändringen sparades.")
        if undo_cols[1].button("↶ Ångra", key=f"undo_schedule_{tid}", use_container_width=True):
            undo_rows = st.session_state.pop(undo_schedule_key)
            undo_schedule_change(tid, undo_rows)
            st.toast("Schemaändringen ångrades.")
            st.rerun()

    adjustable_matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
        (tid,),
    )
    if adjustable_matches:
        board_rows = [dict(row) for row in adjustable_matches]
        board = schedule_board(board_rows, source_label)
        with st.expander("🗓️ Visuellt schema", expanded=True):
            st.caption("Överblick per tid och plan. Drag-and-drop och konfliktkontroll finns direkt under vyn.")
            if board["pitches"]:
                st.caption("Tips: använd ⋯/redigeringsverktygen under schemat för att ändra en match i sitt sammanhang i stället för att leta i andra vyer.")
                header = f"<div class='cn-schedule-grid cn-schedule-head' style='--cn-pitches:{len(board["pitches"])}'><div>Tid</div>" + "".join(f"<div>Plan {p}</div>" for p in board["pitches"]) + "</div>"
                rows_html = []
                for time_label in board["times"]:
                    cells = [f"<div class='cn-schedule-time'>{html.escape(time_label)}</div>"]
                    for pitch in board["pitches"]:
                        cell = board["cells"].get(time_label, {}).get(pitch)
                        if cell:
                            cells.append(f"<div class='cn-match-tile'><small>#{cell['id']}</small><b>{html.escape(str(cell['home']))}</b><span>–</span><b>{html.escape(str(cell['away']))}</b></div>")
                        else:
                            cells.append("<div class='cn-match-tile empty'>Ledigt</div>")
                    rows_html.append(f"<div class='cn-schedule-grid' style='--cn-pitches:{len(board["pitches"])}'>" + "".join(cells) + "</div>")
                st.markdown(header + "".join(rows_html), unsafe_allow_html=True)
        with st.expander("Dra och släpp matcher mellan befintliga tid/plan-platser", expanded=False):
            st.caption(
                "Dra matcherna till önskad ordning. När du tillämpar ordningen får matcherna "
                "de befintliga tid/plan-platserna uppifrån och ned. Exakta tider och planer kan "
                "fortfarande finjusteras i formuläret under. CupNavi validerar schemat efter ändringen."
            )
            if sort_items is None:
                st.warning(
                    "Drag-and-drop-komponenten kunde inte laddas. Kontrollera att streamlit-sortables "
                    "är installerat från requirements.txt."
                )
            else:
                drag_items = [
                    f"#{row['id']} | {swedish_datetime(row['scheduled_start'])} | Plan {row['pitch_number']} | "
                    f"{source_label(row['home_source'])} – {source_label(row['away_source'])}"
                    for row in adjustable_matches
                ]
                dragged_items = sort_items(
                    drag_items,
                    direction="vertical",
                    custom_style="""
                    .sortable-item {
                        background:#ffffff;
                        color:#172033;
                        border:1px solid #cbd5e1;
                        border-radius:10px;
                        padding:10px 12px;
                        margin:5px 0;
                        font-weight:700;
                    }
                    .sortable-item:hover {
                        background:#f0fdf4;
                        border-color:#86efac;
                    }
                    """,
                )
                original_ids = [row["id"] for row in adjustable_matches]
                dragged_items = dragged_items or drag_items
                dragged_ids = [
                    int(item.split("|", 1)[0].strip().lstrip("#"))
                    for item in dragged_items
                ]
                if dragged_ids != original_ids:
                    st.warning(
                        "Du har ändrat ordningen. Klicka på Tillämpa drag-and-drop-ordningen "
                        "för att spara. Schemat avpubliceras tills kontrollerna är granskade igen."
                    )
                else:
                    st.caption("Ordningen är oförändrad.")

                if st.button(
                    "Tillämpa drag-and-drop-ordningen",
                    type="primary",
                    use_container_width=True,
                    disabled=dragged_ids == original_ids,
                    key=f"apply_drag_schedule_{tid}",
                ):
                    slots = [
                        (row["scheduled_start"], row["pitch_number"])
                        for row in adjustable_matches
                    ]
                    original_by_id = {row["id"]: row for row in adjustable_matches}
                    updates = []
                    for match_id, (slot_start, slot_pitch) in zip(dragged_ids, slots):
                        original = original_by_id[match_id]
                        changed = (
                            original["scheduled_start"] != slot_start
                            or int(original["pitch_number"] or 0) != int(slot_pitch or 0)
                        )
                        updates.append(
                            (
                                slot_start,
                                slot_pitch,
                                1 if changed else int(original["schedule_locked"] or 0),
                                match_id,
                            )
                        )
                    st.session_state[undo_schedule_key] = [
                        (row["scheduled_start"], row["pitch_number"], int(row["schedule_locked"] or 0), int(row["schedule_published"] or 0), row["id"])
                        for row in adjustable_matches
                    ]
                    apply_drag_schedule_updates(tid, updates)
                    post_errors, post_warnings, _ = validate_schedule(tid, tournament, rules)
                    if post_errors:
                        st.session_state["schedule_message"] = (
                            "error",
                            f"Drag-and-drop sparades men gav {len(post_errors)} blockerande schemafel. "
                            "Öppna Kontroller och rätta dem innan publicering.",
                        )
                    elif post_warnings:
                        st.session_state["schedule_message"] = (
                            "warning",
                            f"Drag-and-drop sparades. Schemat har {len(post_warnings)} varningar att granska.",
                        )
                    else:
                        st.session_state["schedule_message"] = (
                            "success",
                            "Drag-and-drop-ordningen sparades och schemakontrollen hittade inga fel.",
                        )
                    st.rerun()

        with st.expander("Justera och lås en match"):
            adjustable_refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
            adjustable_ids = [match_row["id"] for match_row in adjustable_matches]
            adjust_id = st.selectbox(
                "Match",
                adjustable_ids,
                format_func=lambda match_id: next(
                    f"{match_meta(row)[0]} · {source_label(row['home_source'])}–{source_label(row['away_source'])}"
                    for row in adjustable_matches if row["id"] == match_id
                ),
                key=f"adjust_match_{tid}",
            )
            adjust_match = next(row for row in adjustable_matches if row["id"] == adjust_id)
            adjust_start = datetime.fromisoformat(adjust_match["scheduled_start"])
            with st.form(f"adjust_schedule_{adjust_id}"):
                ad1, ad2, ad3 = st.columns(3)
                adjusted_date = ad1.date_input(
                    "Datum", value=adjust_start.date(),
                    min_value=datetime.fromisoformat(tournament["start_date"] or tournament["tournament_date"]).date(),
                    max_value=datetime.fromisoformat(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"]).date(),
                )
                adjusted_time = ad2.time_input("Avspark", value=adjust_start.time())
                adjusted_pitch = ad3.number_input("Plan", 1, int(rules["pitch_count"]), int(adjust_match["pitch_number"] or 1))
                referee_options = [None] + [referee["id"] for referee in adjustable_refs]
                referee_index = referee_options.index(adjust_match["referee_id"]) if adjust_match["referee_id"] in referee_options else 0
                adjusted_referee = st.selectbox(
                    "Domare", referee_options, index=referee_index,
                    format_func=lambda referee_id: "Ingen domare" if referee_id is None else next(referee["name"] for referee in adjustable_refs if referee["id"] == referee_id),
                )
                adjusted_locked = st.checkbox(
                    "Lås matchen – automatisk schemaläggning får inte flytta den",
                    value=bool(adjust_match["schedule_locked"]),
                )
                if st.form_submit_button("Spara matchens tid, plan och låsning", type="primary"):
                    adjusted_start = datetime.combine(adjusted_date, adjusted_time).isoformat(timespec="minutes")
                    save_adjusted_schedule_match(
                        tid,
                        adjusted_start,
                        adjusted_pitch,
                        adjusted_referee,
                        int(adjusted_locked),
                        adjust_id,
                    )
                    st.session_state["schedule_message"] = ("success", "Matchen sparades. Kör schemakontrollen och publicera schemat på nytt.")
                    st.rerun()
    st.divider()
    st.subheader("Matchschema")
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    referee_names = {r["id"]: r["name"] for r in refs}
    schedule_pitch_names = pitch_name_map(tid,int(rules["pitch_count"]))
    scheduled_matches = all_rows("SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id", (tid,))
    if not scheduled_matches:
        st.info("Klicka på Skapa matcher och generera spelschema ovan.")
    else:
        schedule_rows = []
        for index, m in enumerate(scheduled_matches, 1):
            home_id = resolve_source(m["home_source"])
            away_id = resolve_source(m["away_source"])
            home = team(home_id)
            away = team(away_id)
            start_dt = datetime.fromisoformat(m["scheduled_start"])
            event_rows = all_rows(
                """
                SELECT players.name, player_match_stats.* FROM player_match_stats
                JOIN players ON players.id=player_match_stats.player_id
                WHERE player_match_stats.match_id=? ORDER BY players.name
                """,
                (m["id"],),
            )
            goals_text = ", ".join(f"{e['name']} ({e['goals']})" for e in event_rows if e["goals"]) or "–"
            assists_text = ", ".join(f"{e['name']} ({e['assists']})" for e in event_rows if e["assists"]) or "–"
            yellow_text = ", ".join(f"{e['name']} ({e['yellow_cards']})" for e in event_rows if e["yellow_cards"]) or "–"
            red_text = ", ".join(f"{e['name']} ({e['red_cards']})" for e in event_rows if e["red_cards"]) or "–"
            home_kit_color, away_kit_color, away_kit_used = match_kit_colors(home, away)
            if kit_color_conflict(home, away):
                kit_note = f"ℹ Om färgerna upplevs som för lika kan {away['name']} behöva ett extraställ" if away else "ℹ Möjlig färglikhet"
            elif away_kit_used:
                kit_note = f"{away['name']} använder sin andra tröjfärg"
            else:
                kit_note = ""
            schedule_rows.append({
                "match_id": m["id"],
                "Match": index,
                "Fas": m["stage"],
                "Plan": schedule_pitch_names.get(int(m["pitch_number"] or 0), f"Plan {m['pitch_number']}") if m["pitch_number"] else "–",
                "Datum": f"{SWEDISH_WEEKDAYS[start_dt.weekday()]} {start_dt.strftime('%Y-%m-%d')}",
                "Tid": start_dt.strftime("%H:%M"),
                "Hemmalag": home["name"] if home else source_label(m["home_source"]),
                "Hemmafärg": kit_swatch(home, "home") if home else None,
                "Bortalag": away["name"] if away else source_label(m["away_source"]),
                "Bortafärg": kit_swatch(away, "away" if away_kit_used else "home") if away else None,
                "Tröjval": kit_note,
                "Domare": referee_names.get(m["referee_id"], "Ej tillsatt"),
                "Låst": "Ja" if m["schedule_locked"] else "Nej",
                "Hemmamål": m["home_score"],
                "Bortamål": m["away_score"],
                "Målskyttar": goals_text,
                "Assister": assists_text,
                "Varningar": yellow_text,
                "Utvisningar": red_text,
            })
        schedule_df = pd.DataFrame(schedule_rows)

        st.markdown("#### Visuell schemaöversikt")
        st.caption("Problem visas direkt på den match där de behöver åtgärdas.")
        for row in schedule_rows:
            issues = []
            if row["Domare"] == "Ej tillsatt":
                issues.append("Domare saknas")
            if row["Tröjval"].startswith("⚠"):
                issues.append("Möjlig färglikhet")
            if row["Hemmalag"].startswith(("Vinnaren i ", "Vinnare match ", "Förlorare match ")):
                issues.append("Hemmalag ej avgjort")
            if row["Bortalag"].startswith(("Vinnaren i ", "Vinnare match ", "Förlorare match ")):
                issues.append("Bortalag ej avgjort")
            issue_html = "".join(
                f"<span class='cn-issue-pill'>{html.escape(issue)}</span>" for issue in issues
            )
            card_class = "cn-admin-match issue" if issues else "cn-admin-match"
            st.markdown(
                f"""
                <div class="{card_class}">
                  <div><div class="number">#{row['Match']}</div><div class="meta">{html.escape(str(row['Fas']))}</div></div>
                  <div><div class="team">{html.escape(str(row['Hemmalag']))}</div><div class="meta">{html.escape(str(row['Datum']))} · {html.escape(str(row['Tid']))}</div></div>
                  <div><div class="team">{html.escape(str(row['Bortalag']))}</div><div class="meta">Plan {html.escape(str(row['Plan']))}</div></div>
                  <div class="ref-col"><div class="meta">Domare</div><div class="team">{html.escape(str(row['Domare']))}</div>{issue_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("Redigera resultat i tabell"):
            edited_schedule = st.data_editor(
                schedule_df,
                hide_index=True,
                use_container_width=True,
                disabled=["match_id", "Match", "Fas", "Plan", "Datum", "Tid", "Hemmalag", "Hemmafärg", "Bortalag", "Bortafärg", "Tröjval", "Domare", "Låst", "Målskyttar", "Assister", "Varningar", "Utvisningar"],
                column_order=["Match", "Fas", "Plan", "Datum", "Tid", "Hemmalag", "Hemmafärg", "Hemmamål", "Bortamål", "Bortafärg", "Bortalag", "Tröjval", "Domare", "Låst", "Målskyttar", "Assister", "Varningar", "Utvisningar"],
                column_config={
                    "Hemmamål": st.column_config.NumberColumn(min_value=0, step=1),
                    "Bortamål": st.column_config.NumberColumn(min_value=0, step=1),
                    "Hemmafärg": st.column_config.ImageColumn("Hemmafärg", width="small"),
                    "Bortafärg": st.column_config.ImageColumn("Bortafärg", width="small"),
                },
                key=f"schedule_editor_{tid}",
            )
        if st.button("Spara alla resultat i schemat"):
            original_scores = {
                int(row["match_id"]): (
                    None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"]),
                    None if pd.isna(row["Bortamål"]) else int(row["Bortamål"]),
                )
                for _, row in schedule_df.iterrows()
            }
            changed_scores = []
            for _, row in edited_schedule.iterrows():
                match_id = int(row["match_id"])
                home_score = None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"])
                away_score = None if pd.isna(row["Bortamål"]) else int(row["Bortamål"])
                if original_scores.get(match_id) != (home_score, away_score):
                    changed_scores.append((home_score, away_score, match_id))

            if changed_scores:
                save_bulk_schedule_results(tid, changed_scores, bool(tournament["is_published"]))
                st.success(f"Resultat sparade för {len(changed_scores)} matcher.")
                st.rerun()
            else:
                st.info("Inga resultatändringar att spara.")
        st.caption("Målskyttar, assist, varningar och utvisningar registreras under fliken Matchhändelser och visas därefter automatiskt här.")
