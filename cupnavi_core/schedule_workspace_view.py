"""Schedule workspace orchestration for the admin UI.

The schedule engine and persistence-sensitive write operations stay injected from app.py.
"""

from __future__ import annotations

from cupnavi_core.planning_flow_nav import render_clickable_planning_flow, render_problem_actions

from dataclasses import dataclass
from datetime import datetime
import html
import re
import time
from typing import Any, Callable

import pandas as pd

from cupnavi_core.kit_clash_guidance import build_kit_guidance


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
    reset_unused_playoff_downstream_match: Callable[..., Any] | None = None
    setting: Callable[..., Any] | None = None
    db: Callable[..., Any] | None = None
    apply_schedule_improvement: Callable[..., Any] | None = None
    apply_matchcamp_structure_improvement: Callable[..., Any] | None = None
    navigate_admin_page: Callable[[str], Any] | None = None
    rules_snapshot: Any | None = None
    validation_snapshot: tuple[list[Any], list[Any], list[Any]] | None = None



def schedule_next_step(
    *,
    participant_list_complete: bool,
    registered_team_count: int,
    expected_team_count: int,
    has_groups: bool,
    unassigned_count: int,
    too_small_groups: list[str],
    playoff_ready: bool,
    playoff_setup_error: str | None,
    scheduled_total: int,
    schedule_errors: list[Any],
    schedule_warnings: list[Any],
    unpublished_total: int,
) -> dict[str, str]:
    """Return a beginner-facing recommendation without running expensive analysis."""
    if not participant_list_complete:
        detail = (
            f"Registrera återstående lag ({registered_team_count}/{expected_team_count})."
            if expected_team_count
            else "Registrera minst ett lag innan schemat kan byggas."
        )
        return {"title": "Fortsätt med lagen", "detail": detail, "state": "blocked"}
    if not has_groups:
        return {"title": "Skapa grupper", "detail": "Lagen är registrerade men gruppindelningen saknas.", "state": "blocked"}
    if unassigned_count:
        return {
            "title": "Placera alla lag i grupper",
            "detail": f"{unassigned_count} lag saknar fortfarande grupp.",
            "state": "blocked",
        }
    if too_small_groups:
        return {
            "title": "Rätta gruppindelningen",
            "detail": "Minst en grupp har färre än två lag: " + ", ".join(too_small_groups) + ".",
            "state": "blocked",
        }
    if not playoff_ready or playoff_setup_error:
        return {
            "title": "Slutför tävlingsupplägget",
            "detail": playoff_setup_error or "Slutspelsmodellen behöver bekräftas innan schemat skapas.",
            "state": "blocked",
        }
    if scheduled_total == 0:
        return {
            "title": "Skapa spelschemat",
            "detail": "Grundunderlaget är klart. CupNavi kan nu fördela matcher, tider, planer och domare.",
            "state": "ready",
        }
    if schedule_errors:
        return {
            "title": "Rätta schemats blockerande fel",
            "detail": f"{len(schedule_errors)} fel måste lösas innan schemat kan publiceras.",
            "state": "blocked",
        }
    if schedule_warnings:
        return {
            "title": "Granska schemats varningar",
            "detail": f"{len(schedule_warnings)} varningar återstår. De blockerar inte alltid publicering men bör bedömas.",
            "state": "review",
        }
    if unpublished_total:
        return {
            "title": "Kontrollera och publicera",
            "detail": "Schemat klarar snabbkontrollen men är fortfarande ett utkast.",
            "state": "ready",
        }
    return {
        "title": "Schemat är publicerat",
        "detail": "Inga blockerande schemafel eller varningar återstår i snabbkontrollen.",
        "state": "done",
    }




def schedule_issue_match_numbers(issue: Any) -> list[int]:
    """Extract validation match numbers from a human-readable schedule issue."""
    numbers = [int(raw) for raw in re.findall(r"\bmatch\s+(\d+)\b", str(issue or ""), flags=re.IGNORECASE)]
    return list(dict.fromkeys(numbers))


def schedule_issue_guidance(issue: Any) -> str:
    """Return one short beginner-facing action sentence for a validation issue."""
    text = str(issue or "").lower()
    if "plankrock" in text:
        return "Flytta en av matcherna till en annan tid eller plan."
    if "domarkrock" in text:
        return "Byt domare eller flytta en av matcherna."
    if "dubbelbokat" in text:
        return "Flytta en av matcherna så laget inte spelar två matcher samtidigt."
    if "obligatoriska extrapusen" in text or "direkt efter varandra" in text:
        return "Öka tiden mellan de berörda matcherna."
    if "ogiltig plan" in text:
        return "Välj en giltig plan för matchen."
    if "utanför cupens datumintervall" in text:
        return "Flytta matchen till ett datum inom cupen."
    if "före planens tillåtna starttid" in text or "efter planens sluttid" in text:
        return "Justera matchtiden så den ryms inom planens öppettider."
    if "saknar schematid" in text:
        return "Komplettera eller bygg om schemat så alla gruppspelsmatcher får en tid."
    if "saknar domare" in text:
        return "Tilldela en domare eller ändra domarläget."
    if "färglikhet" in text:
        return "Granska lagens matchställ och välj ett tydligt avvikande ställ."
    return "Öppna den berörda matchen och rätta uppgifterna innan publicering."

def schedule_quick_quality(*, scheduled_total: int, schedule_errors: list[Any], schedule_warnings: list[Any]) -> tuple[str, str]:
    """Cheap quality signal; the detailed score remains opt-in/lazy."""
    if scheduled_total <= 0:
        return "Inte bedömt ännu", "Skapa schemat först."
    if schedule_errors:
        return "Blockerat", f"{len(schedule_errors)} fel måste lösas."
    if schedule_warnings:
        return "Behöver granskas", f"{len(schedule_warnings)} varningar finns."
    return "Stabilt", "Inga fel eller varningar i snabbkontrollen."


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
    setting = deps.setting or (lambda _key: None)
    apply_schedule_improvement = deps.apply_schedule_improvement
    apply_matchcamp_structure_improvement = deps.apply_matchcamp_structure_improvement
    navigate_admin_page = deps.navigate_admin_page
    rules_snapshot = deps.rules_snapshot
    validation_snapshot = deps.validation_snapshot

    # Planning flow contract: ["Cupinfo", "Lag", "Grupper", "Planer & tider", "Schema", "Kontroll", "Publicera"]
    # v514: Schema is step five in the single seven-step beginner journey.
    # Keep location and backwards navigation visible instead of reverting to the old
    # isolated "Steg 3 av 5" schedule workspace.
    st.markdown(
        """<div class="cn-workspace-head">
          <div>
            <div class="kicker">Steg 5 av 7</div>
            <div class="title">Schema</div>
            <div class="subtitle">Här använder du ett importerat schema eller skapar ett nytt. CupNavi skriver aldrig över ett befintligt schema automatiskt.</div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )
    if navigate_admin_page is not None:
        render_clickable_planning_flow(
            st, tid=tid, current_step="Schema", navigate_admin_page=navigate_admin_page
        )
    _schedule_flow_back, _schedule_flow_next = st.columns(2)
    if navigate_admin_page is not None:
        _schedule_flow_back.button(
            "← Till Planer & tider",
            use_container_width=True,
            key=f"v514_schedule_back_to_pitches_{tid}",
            on_click=navigate_admin_page,
            args=("Cupinställningar",),
        )
    else:
        _schedule_flow_back.caption("Föregående steg: Planer & tider")
    # v512: Never strand the administrator on Schema. Control is a review step,
    # not a reward for having a perfect setup. It must always be reachable so
    # imported schedules and blockers can be inspected and resolved.
    if navigate_admin_page is not None:
        _schedule_flow_next.button(
            "Fortsätt till Kontroll →",
            use_container_width=True,
            key=f"schedule_flow_next_to_control_{tid}",
            on_click=navigate_admin_page,
            args=("Kontroll",),
        )
    else:
        _schedule_flow_next.caption("Nästa steg: Kontroll")
    if "schedule_message" in st.session_state:
        message_type, message_text = st.session_state.pop("schedule_message")
        getattr(st, message_type)(message_text)

    # v436: Admin shell already fetched the same schedule_rules row for the
    # publication/control snapshot. Reuse it on Schema instead of paying a
    # second remote roundtrip on every rerun.
    rules = rules_snapshot or one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    if rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
        rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))

    # v508: The timing model belongs on the Schema page. Previously it was
    # buried under cup settings, which made a core scheduling choice hard to find.
    with st.expander("⚙️ Schematyp (valfritt)", expanded=False):
        st.caption("De flesta kan lämna detta som det är. Ändra bara om planerna ska följa gemensamma avsparkstider.")
        st.markdown("##### Hur ska planernas tider fungera?")
        _sync_now = bool(rules["synchronized_pitch_times"] or 0)
        _timing_choice = st.radio(
            "Välj schematyp",
            ["Dynamiskt schema", "Samma avsparkstider på alla planer"],
            index=1 if _sync_now else 0,
            key=f"schedule_timing_mode_{tid}",
            help=(
                "Dynamiskt schema låter varje plan starta nästa match så snart vila, matchlängd och plantider tillåter. "
                "Gemensamma avsparkstider använder samma startvågor på alla planer."
            ),
        )
        _sync_new = _timing_choice == "Samma avsparkstider på alla planer"
        if _sync_new:
            st.caption("Alla planer följer gemensamma starttider, till exempel 09:00, 09:45 och 10:30.")
        else:
            st.caption("Dynamiskt: varje plan kan använda nästa möjliga starttid. Det ger större frihet att optimera schemat.")
        if _sync_new != _sync_now:
            if st.button("Spara schematyp", type="primary", key=f"save_schedule_timing_mode_{tid}"):
                _existing_matches = one_row(
                    "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
                    (tid,),
                )
                run(
                    "UPDATE schedule_rules SET synchronized_pitch_times=? WHERE tournament_id=?",
                    (1 if _sync_new else 0, tid),
                )
                if int((_existing_matches["n"] if _existing_matches else 0) or 0) > 0:
                    run("UPDATE tournaments SET schedule_dirty=1 WHERE id=?", (tid,))
                    st.session_state["schedule_message"] = (
                        "warning",
                        "Schematypen är sparad. Ditt befintliga schema har inte ändrats. Granska schemaändringen innan du ersätter något.",
                    )
                else:
                    st.session_state["schedule_message"] = ("success", "Schematypen är sparad.")
                st.session_state["_validation_dirty"] = True
                st.rerun()

    if st.session_state.get("schedule_recovery"):
        render_schedule_recovery_actions(tid,tournament,rules,st.session_state.get("schedule_recovery"))
    schedule_groups = all_rows("SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    schedule_teams = all_rows("SELECT id,group_id FROM teams WHERE tournament_id=?", (tid,))
    expected_team_count = int(tournament["expected_team_count"] or 0)
    registered_team_count = len(schedule_teams)
    participant_list_complete = bool(
        registered_team_count > 0
        and (not expected_team_count or registered_team_count >= expected_team_count)
    )
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
    # v436: validate_schedule is one of the most expensive admin reads (full
    # scheduled-match scan + conflict/rest analysis). The admin shell already
    # computes and invalidates this snapshot when schedule/rules change, so do
    # not run the same analysis a second time merely because Schema rendered.
    if validation_snapshot is not None:
        schedule_errors, schedule_warnings, schedule_quality = validation_snapshot
    elif scheduled_total:
        schedule_errors, schedule_warnings, schedule_quality = validate_schedule(tid, tournament, rules)
    else:
        schedule_errors, schedule_warnings, schedule_quality = ([], [], [])
    playoff_specs, playoff_setup_error = playoff_specs_for_tournament(tid, tournament)
    playoff_model_ready = bool(tournament["playoff_model_confirmed"])

    _next_step = schedule_next_step(
        participant_list_complete=participant_list_complete,
        registered_team_count=registered_team_count,
        expected_team_count=expected_team_count,
        has_groups=bool(schedule_groups),
        unassigned_count=unassigned_count,
        too_small_groups=too_small_groups,
        playoff_ready=playoff_model_ready,
        playoff_setup_error=playoff_setup_error,
        scheduled_total=scheduled_total,
        schedule_errors=schedule_errors,
        schedule_warnings=schedule_warnings,
        unpublished_total=unpublished_total,
    )
    _quick_grade, _quick_detail = schedule_quick_quality(
        scheduled_total=scheduled_total,
        schedule_errors=schedule_errors,
        schedule_warnings=schedule_warnings,
    )
    # v510: A schedule imported from photo/PDF is a real schedule, but it must
    # still be editable by the organizer. Surface that action here instead of
    # hiding it among advanced/detail tools.
    if scheduled_total > 0:
        with st.expander(
            "✏️ Redigera befintligt schema manuellt",
            expanded=bool(st.session_state.get(f"manual_schedule_edit_open_{tid}", False)),
        ):
            st.markdown("#### Redigera befintligt schema manuellt")
            st.caption(
                "Ändra en ospelad match utan att generera om resten av schemat. "
                "Du kan justera tid, plan, domare och – för gruppspelsmatcher – lagen."
            )
            _manual_edit_open = st.toggle(
                "Öppna manuell schemaredigering",
                value=False,
                key=f"manual_schedule_edit_open_{tid}",
            )
            if _manual_edit_open:
                _manual_matches = all_rows(
                    """SELECT * FROM matches
                       WHERE tournament_id=? AND scheduled_start IS NOT NULL
                       ORDER BY scheduled_start,pitch_number,id""",
                    (tid,),
                )
                _manual_ids = [int(row["id"]) for row in _manual_matches]
                _manual_match_id = st.selectbox(
                    "Match att ändra",
                    _manual_ids,
                    format_func=lambda mid: next(
                        f"{swedish_datetime(row['scheduled_start'])} · Plan {row['pitch_number'] or '–'} · "
                        f"{source_label(row['home_source'])} – {source_label(row['away_source'])}"
                        for row in _manual_matches if int(row["id"]) == int(mid)
                    ),
                    key=f"manual_schedule_match_{tid}",
                )
                _manual_match = next(row for row in _manual_matches if int(row["id"]) == int(_manual_match_id))
                _manual_played = _manual_match["home_score"] is not None or _manual_match["away_score"] is not None
                if _manual_played:
                    st.warning("Matchen har redan resultat och är skyddad. Spelade matcher kan inte ändras här.")
                else:
                    _manual_start = datetime.fromisoformat(_manual_match["scheduled_start"])
                    _manual_refs = all_rows("SELECT id,name FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
                    _manual_teams = all_rows("SELECT id,name,group_id FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
                    with st.form(f"manual_schedule_edit_{tid}_{_manual_match_id}"):
                        _me1, _me2, _me3 = st.columns(3)
                        _start_bound = datetime.fromisoformat(str(tournament["start_date"] or tournament["tournament_date"])) .date()
                        _end_bound = datetime.fromisoformat(str(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"])) .date()
                        _new_date = _me1.date_input("Datum", value=_manual_start.date(), min_value=_start_bound, max_value=_end_bound, key=f"manual_schedule_date_{tid}_{_manual_match_id}")
                        _new_time = _me2.time_input("Avspark", value=_manual_start.time(), key=f"manual_schedule_time_{tid}_{_manual_match_id}")
                        _new_pitch = _me3.number_input("Plan", 1, int(rules["pitch_count"]), int(_manual_match["pitch_number"] or 1), key=f"manual_schedule_pitch_{tid}_{_manual_match_id}")

                        _ref_ids = [None] + [int(r["id"]) for r in _manual_refs]
                        _current_ref = int(_manual_match["referee_id"]) if _manual_match["referee_id"] is not None else None
                        _ref_index = _ref_ids.index(_current_ref) if _current_ref in _ref_ids else 0
                        _new_ref = st.selectbox(
                            "Domare",
                            _ref_ids,
                            index=_ref_index,
                            format_func=lambda rid: "Ingen domare" if rid is None else next(r["name"] for r in _manual_refs if int(r["id"]) == int(rid)),
                            key=f"manual_schedule_ref_{tid}_{_manual_match_id}",
                        )

                        _new_home_source = _manual_match["home_source"]
                        _new_away_source = _manual_match["away_source"]
                        if str(_manual_match["stage"] or "") == "Gruppspel" and _manual_match["group_id"] is not None:
                            _group_team_rows = [r for r in _manual_teams if r["group_id"] is not None and int(r["group_id"]) == int(_manual_match["group_id"])]
                            _group_team_ids = [int(r["id"]) for r in _group_team_rows]
                            def _source_team_id(src):
                                try:
                                    kind, raw = str(src).split(":", 1)
                                    return int(raw) if kind == "team" else None
                                except Exception:
                                    return None
                            _home_id = _source_team_id(_manual_match["home_source"])
                            _away_id = _source_team_id(_manual_match["away_source"])
                            if _group_team_ids and _home_id in _group_team_ids and _away_id in _group_team_ids:
                                _th, _ta = st.columns(2)
                                _new_home_id = _th.selectbox(
                                    "Hemma",
                                    _group_team_ids,
                                    index=_group_team_ids.index(_home_id),
                                    format_func=lambda team_id: next(r["name"] for r in _group_team_rows if int(r["id"]) == int(team_id)),
                                    key=f"manual_schedule_home_{tid}_{_manual_match_id}",
                                )
                                _new_away_id = _ta.selectbox(
                                    "Borta",
                                    _group_team_ids,
                                    index=_group_team_ids.index(_away_id),
                                    format_func=lambda team_id: next(r["name"] for r in _group_team_rows if int(r["id"]) == int(team_id)),
                                    key=f"manual_schedule_away_{tid}_{_manual_match_id}",
                                )
                                if int(_new_home_id) == int(_new_away_id):
                                    st.error("Samma lag kan inte möta sig självt.")
                                _new_home_source = f"team:{int(_new_home_id)}"
                                _new_away_source = f"team:{int(_new_away_id)}"

                        _new_locked = st.checkbox(
                            "Lås matchen så automatisk schemaläggning inte flyttar den",
                            value=bool(_manual_match["schedule_locked"]),
                            key=f"manual_schedule_lock_{tid}_{_manual_match_id}",
                        )
                        _save_manual = st.form_submit_button("Spara ändringen", type="primary", use_container_width=True)
                        if _save_manual:
                            if _new_home_source == _new_away_source:
                                st.error("Samma lag kan inte möta sig självt.")
                            else:
                                _new_start = datetime.combine(_new_date, _new_time).isoformat(timespec="minutes")
                                run(
                                    """UPDATE matches
                                       SET scheduled_start=?,pitch_number=?,referee_id=?,home_source=?,away_source=?,schedule_locked=?,schedule_published=0
                                       WHERE id=? AND tournament_id=? AND home_score IS NULL AND away_score IS NULL""",
                                    (_new_start, int(_new_pitch), _new_ref, _new_home_source, _new_away_source, int(_new_locked), int(_manual_match_id), tid),
                                )
                                run("UPDATE tournaments SET is_published=0 WHERE id=?", (tid,))
                                st.session_state["_validation_dirty"] = True
                                st.session_state["schedule_message"] = (
                                    "success",
                                    "Matchen ändrades manuellt. Övriga matcher lämnades orörda. Kontrollera schemat före publicering.",
                                )
                                st.rerun()

    _sync_times = bool(rules["synchronized_pitch_times"])
    _timing_title = "Synkroniserade plantider" if _sync_times else "Dynamiska plantider"
    _timing_detail = (
        "Alla planer använder samma gemensamma avsparksvågor."
        if _sync_times
        else "Varje plan får använda nästa möjliga starttid för bättre kapacitetsutnyttjande."
    )

    # Historical QA anchor: CupNavis rekommendation
    # st.markdown("#### Skapa eller uppdatera schema")
    st.markdown("#### Nästa steg")
    with st.container(border=True):
        _rec_left, _rec_right = st.columns([2, 1])
        _rec_left.markdown(f"### {_next_step['title']}")
        _rec_left.write(_next_step["detail"])
        _rec_right.metric("Snabb schemakvalitet", _quick_grade)
        _rec_right.caption(_quick_detail)
        st.markdown(f"**Aktivt tidsläge: {_timing_title}**")
        st.caption(_timing_detail + " Ändra under ‘Schematyp (valfritt)’ ovan om arrangemanget kräver ett annat upplägg.")
        if _next_step["state"] == "ready" and scheduled_total == 0:
            st.success("CupNavi rekommenderar att du skapar schemat nu.")
        elif _next_step["state"] == "blocked":
            st.warning("CupNavi rekommenderar att du löser punkten ovan innan du försöker skapa eller publicera schemat.")
        elif _next_step["state"] == "review":
            st.info("Schemat finns. Nästa värdefulla steg är granskning, inte ny schemagenerering.")

    st.markdown("#### Schema")
    with st.container(border=True):
        status1, status2, status3 = st.columns(3)
        status1.metric("Gruppspelsmatcher", group_match_total)
        status2.metric("Schemalagda matcher", scheduled_total)
        status3.metric("Ej publicerade", unpublished_total)
        create_disabled = (
            not participant_list_complete
            or not schedule_groups
            or unassigned_count > 0
            or bool(too_small_groups)
            or not playoff_model_ready
            or bool(playoff_setup_error)
        )

        # v509: Existing cups created from the older photo/document flow may have
        # imported teams/groups but no persisted matches. Let the administrator
        # re-read the source directly from Schema and explicitly approve the
        # recovered match programme instead of sending them into the generator.
        if scheduled_total == 0 and setting is not None and deps.db is not None:
            st.info(
                "Om du redan läste in ett matchprogram från foto/PDF men ser 0 schemalagda matcher här, "
                "har själva matcherna inte sparats i cupen. Läs in samma underlag igen nedan och godkänn förhandsgranskningen. "
                "Du kan ändå gå vidare till Kontroll för att se exakt vad som saknas."
            )
            with st.expander("📷 Har du redan ett schema i foto/PDF? Importera matchprogrammet här", expanded=True):
                st.caption("Om du skapade cupen från ett foto i en äldre version kan lag och grupper ha importerats utan själva matcherna. Läs in underlaget igen här. CupNavi visar alltid en förhandsgranskning innan något sparas.")
                _uploads = st.file_uploader(
                    "Foto, PDF eller dokument med matchprogram",
                    type=["pdf", "txt", "png", "jpg", "jpeg", "webp"],
                    accept_multiple_files=True,
                    key=f"schedule_existing_import_upload_{tid}",
                )
                _prefill_key = f"schedule_existing_import_prefill_{tid}"
                if _uploads and st.button("Läs matchprogrammet", key=f"schedule_existing_import_analyze_{tid}", type="primary"):
                    _api_key = setting("OPENAI_API_KEY")
                    if not _api_key:
                        st.error("Dokumenttolkningen är inte aktiverad.")
                    else:
                        try:
                            from cupnavi_core.ai_cup_document_import import extract_cup_setup_from_documents
                            with st.spinner("CupNavi läser matchprogrammet …"):
                                _docs = [(item.getvalue(), item.name, item.type) for item in _uploads]
                                st.session_state[_prefill_key] = extract_cup_setup_from_documents(_docs, _api_key)
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Matchprogrammet kunde inte tolkas: {exc}")
                _import_prefill = st.session_state.get(_prefill_key) or {}
                _import_matches = list(_import_prefill.get("matches") or [])
                if _import_matches:
                    st.success(f"CupNavi hittade {len(_import_matches)} matcher. Kontrollera dem innan du sparar.")
                    _rows = [{
                        "Tid": m.get("time") or "", "Grupp": m.get("group_name") or "",
                        "Hemma": m.get("home_team") or "", "Borta": m.get("away_team") or "",
                        "Plan": m.get("venue") or "",
                    } for m in _import_matches]
                    _edited = st.data_editor(_rows, use_container_width=True, hide_index=True, num_rows="fixed", key=f"schedule_existing_import_editor_{tid}")
                    _confirm = st.checkbox("Jag har granskat matcherna och vill använda detta som cupens befintliga schema", key=f"schedule_existing_import_confirm_{tid}")
                    if st.button("Importera granskat schema", disabled=not _confirm, type="primary", use_container_width=True, key=f"schedule_existing_import_apply_{tid}"):
                        try:
                            from datetime import date as _date
                            from cupnavi_core.cup_document_creator_view import apply_document_matches
                            _import_prefill["matches"] = [{
                                "time": r.get("Tid"), "group_name": r.get("Grupp"),
                                "home_team": r.get("Hemma"), "away_team": r.get("Borta"),
                                "venue": r.get("Plan"), "stage": "Gruppspel",
                            } for r in _edited]
                            _raw_date = tournament["start_date"] or tournament["tournament_date"]
                            _fallback = _date.fromisoformat(str(_raw_date)[:10])
                            _count = apply_document_matches(deps.db, tid, _import_prefill, _fallback)
                            st.session_state["schedule_message"] = ("success", f"{_count} matcher importerades. De behandlas nu som ett befintligt schema och skrivs inte över automatiskt.")
                            st.session_state.pop(_prefill_key, None)
                            st.session_state["_validation_dirty"] = True
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Importen avbröts utan att ändra schemat: {exc}")
                elif _import_prefill:
                    st.warning("CupNavi hittade inga säkra matcher i underlaget. Inget har sparats.")

        # v347: a compact readiness contract before the destructive/expensive
        # schedule action. The generator should never look "ready" while the
        # participant list or group structure is still incomplete.
        readiness_checks = [
            (
                participant_list_complete,
                "Deltagarlista",
                (
                    f"{registered_team_count}/{expected_team_count} lag registrerade"
                    if expected_team_count
                    else f"{registered_team_count} lag registrerade"
                ),
            ),
            (
                bool(schedule_groups),
                "Grupper",
                f"{len(schedule_groups)} grupper skapade" if schedule_groups else "inga grupper skapade",
            ),
            (
                bool(schedule_teams) and unassigned_count == 0,
                "Gruppplacering",
                "alla lag placerade" if schedule_teams and unassigned_count == 0 else f"{unassigned_count} lag saknar grupp",
            ),
            (
                bool(schedule_groups) and not too_small_groups,
                "Gruppstorlek",
                "minst två lag i varje grupp" if schedule_groups and not too_small_groups else "grupp med färre än två lag finns",
            ),
            (
                playoff_model_ready and not playoff_setup_error,
                "Slutspelsmodell",
                "klar" if playoff_model_ready and not playoff_setup_error else "behöver slutföras",
            ),
        ]
        ready_count = sum(1 for ok, _, _ in readiness_checks if ok)
        _missing_readiness = [(label, detail) for ok, label, detail in readiness_checks if not ok]

        # v542: The schedule page should answer three questions immediately:
        # 1) Is the setup ready? 2) What is wrong? 3) What must I choose/do next?
        # Keep completed setup facts compact and surface only unfinished choices.
        with st.container(border=True):
            _status_cols = st.columns(4)
            _status_cols[0].metric("Grunddata", f"{ready_count}/{len(readiness_checks)} klara")
            _status_cols[1].metric("Schema", f"{scheduled_total} matcher" if scheduled_total else "Inte skapat")
            _status_cols[2].metric("Blockerande fel", len(schedule_errors))
            _status_cols[3].metric("Varningar", len(schedule_warnings))
            st.progress(ready_count / len(readiness_checks))

        if _missing_readiness:
            with st.container(border=True):
                st.markdown("### Val som måste göras")
                st.caption("Gör klart dessa punkter innan CupNavi kan bygga eller publicera schemat.")
                for label, detail in _missing_readiness:
                    st.markdown(f"**○ {label}** — {detail}")
        else:
            st.caption("✓ Grunddata klar: lag, grupper, gruppplacering och tävlingsupplägg är redo.")

        _issue_match_rows = []
        if schedule_errors or schedule_warnings:
            # Validation labels matches by chronological position. Fetch only IDs in the
            # same order once so every issue can offer a direct "Rätta match" action.
            _issue_match_rows = all_rows(
                """SELECT id FROM matches
                   WHERE tournament_id=? AND scheduled_start IS NOT NULL
                   ORDER BY scheduled_start,pitch_number,id""",
                (tid,),
            )

        def _open_issue_match(match_number: int) -> None:
            if not 1 <= int(match_number) <= len(_issue_match_rows):
                return
            match_id = int(_issue_match_rows[int(match_number) - 1]["id"])
            st.session_state[f"manual_schedule_edit_open_{tid}"] = True
            st.session_state[f"manual_schedule_match_{tid}"] = match_id

        if schedule_errors:
            with st.container(border=True):
                st.markdown(f"### ⛔ Blockerande schemafel ({len(schedule_errors)})")
                st.caption("Alla fel visas här. Rätta dem innan schemat kan publiceras.")
                for idx, issue in enumerate(schedule_errors, 1):
                    _match_numbers = schedule_issue_match_numbers(issue)
                    with st.container(border=True):
                        st.markdown(f"**Fel {idx}: {issue}**")
                        st.caption(schedule_issue_guidance(issue))
                        if _match_numbers:
                            _action_cols = st.columns(min(3, len(_match_numbers)))
                            for _col_idx, _match_number in enumerate(_match_numbers):
                                _action_cols[_col_idx % len(_action_cols)].button(
                                    f"Rätta match {_match_number} →",
                                    key=f"schedule_error_match_{tid}_{idx}_{_match_number}",
                                    use_container_width=True,
                                    on_click=_open_issue_match,
                                    args=(_match_number,),
                                )
                        elif "saknar schematid" in str(issue).lower():
                            st.caption("Det här felet gäller schemat som helhet. Använd ‘Nästa steg’ nedan för att komplettera eller bygga om schemat.")
        if schedule_warnings:
            with st.expander(f"⚠️ Varningar ({len(schedule_warnings)})", expanded=not bool(schedule_errors)):
                st.caption("Varningar blockerar inte alltid publicering, men bör granskas.")
                for idx, warning in enumerate(schedule_warnings, 1):
                    _match_numbers = schedule_issue_match_numbers(warning)
                    with st.container(border=True):
                        st.markdown(f"**Varning {idx}: {warning}**")
                        st.caption(schedule_issue_guidance(warning))
                        if _match_numbers:
                            _action_cols = st.columns(min(3, len(_match_numbers)))
                            for _col_idx, _match_number in enumerate(_match_numbers):
                                _action_cols[_col_idx % len(_action_cols)].button(
                                    f"Öppna match {_match_number} →",
                                    key=f"schedule_warning_match_{tid}_{idx}_{_match_number}",
                                    use_container_width=True,
                                    on_click=_open_issue_match,
                                    args=(_match_number,),
                                )

        if tournament["playoff_format"] != "Inget slutspel" and playoff_setup_error:
            st.error(f"Slutspel kan inte genereras: {playoff_setup_error}")

        _regenerating_unplayed_schedule = bool(scheduled_total > 0 and not played_result_total)
        _locked_unplayed_total = int(one_row(
            """SELECT COUNT(*) AS n FROM matches
               WHERE tournament_id=? AND schedule_locked=1
                 AND home_score IS NULL AND away_score IS NULL""",
            (tid,),
        )["n"] or 0) if _regenerating_unplayed_schedule else 0
        _repairing_locked_schedule = bool(_regenerating_unplayed_schedule and schedule_errors and _locked_unplayed_total)
        schedule_button_label = (
            "Uppdatera återstående schema"
            if played_result_total
            else "Reparera och bygg om schemat" if _repairing_locked_schedule
            else "Skapa om schemat" if _regenerating_unplayed_schedule
            else "Skapa hela spelschemat"
        )
        # v542: Keep the destructive choice together with the primary action.
        # Do not scatter warnings, confirmations and buttons across the page.
        _confirm_regenerate = True
        _schedule_action_disabled = False

        if not create_disabled:
            with st.container(border=True):
                st.markdown("### Nästa steg")
                if played_result_total:
                    st.markdown(
                        f"**Uppdatera bara det som återstår.** {played_result_total} spelade matcher och deras resultat skyddas. "
                        "CupNavi ändrar inte lagens gruppplacering eller sparade tävlingsregler."
                    )
                elif _repairing_locked_schedule:
                    st.markdown(
                        "**Rekommenderat: reparera det foto/PDF-importerade schemat.** CupNavi låser upp ospelade importerade matcher "
                        "och räknar om tider, planer och domare. Lag, grupper och tävlingsregler behålls."
                    )
                elif _regenerating_unplayed_schedule:
                    st.markdown(
                        "**Du behöver välja:** behåll befintliga tider, eller tillåt CupNavi att skapa om de ospelade schematiderna."
                    )
                elif scheduled_total == 0:
                    st.markdown("**Rekommenderat:** skapa hela spelschemat nu.")
                else:
                    st.markdown(f"**{_next_step['title']}** — {_next_step['detail']}")

                if _regenerating_unplayed_schedule:
                    _confirm_regenerate = st.checkbox(
                        "Ja, CupNavi får ersätta befintliga ospelade schematider",
                        key=f"confirm_regenerate_schedule_{tid}",
                    )
                    _schedule_action_disabled = not _confirm_regenerate
                    if _schedule_action_disabled:
                        st.caption("Välj ovan för att aktivera knappen. Inget ändras innan du trycker på knappen.")

                _run_schedule_action = st.button(
                    schedule_button_label,
                    type="primary",
                    use_container_width=True,
                    disabled=_schedule_action_disabled,
                )
            if _run_schedule_action:
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
                            count, unresolved, warning = generate_schedule(
                                tid, tournament, rules, replace_locked=_repairing_locked_schedule
                            )
                            parts = [
                                f"Alla {ready_groups} grupper kontrollerades och {created} saknade gruppmatcher skapades.",
                                "Slutspelsmatcherna skapades automatiskt utifrån vald slutspelsmodell.",
                                (
                                    f"{_locked_unplayed_total} låsta ospelade matcher låstes upp och byggdes om."
                                    if _repairing_locked_schedule
                                    else None
                                ),
                                f"{count} matcher schemalades totalt.",
                            ]
                            parts = [part for part in parts if part]
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
        if create_disabled:
            problems = []
            if not participant_list_complete:
                if expected_team_count:
                    problems.append(f"registrera alla lag ({registered_team_count}/{expected_team_count})")
                else:
                    problems.append("registrera minst ett lag")
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
            st.caption("Åtgärda valen under ‘Val som måste göras’ ovan. Gå direkt till rätt steg här:")
            if navigate_admin_page is not None:
                render_problem_actions(
                    st,
                    tid=tid,
                    navigate_admin_page=navigate_admin_page,
                    needs_teams=not participant_list_complete or bool(unassigned_count),
                    needs_groups=not bool(schedule_groups) or bool(too_small_groups) or bool(unassigned_count),
                    needs_setup=not playoff_model_ready or bool(playoff_setup_error),
                )
        elif scheduled_total == 0:
            st.caption("Knappen ovan skapar gruppspel, slutspel och spelschema i ett steg.")
        elif schedule_errors:
            st.caption("Publicering är blockerad tills schemafelen ovan är lösta.")
        elif schedule_warnings:
            st.caption("Schemat har varningar som bör granskas före publicering.")
        elif unpublished_total:
            st.warning("Schemat är ett utkast. Kontrollera matchlistan och publicera sedan från vänsterspalten.")
        else:
            st.success("Det aktuella spelschemat är publicerat i Turneringsvyn.")

        # Streamlit expanders still execute their body while collapsed. Keep the
        # per-group aggregate queries truly lazy so the default Schema view stays fast.
        _show_group_details = st.toggle(
            "Visa detaljer per grupp",
            value=False,
            key=f"schedule_group_details_{tid}",
            help="Hämtar extra gruppstatistik först när du behöver den.",
        )
        if _show_group_details:
            with st.container(border=True):
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

    st.divider()
    st.markdown('<div class="cn-section-head">Valfria schemaverktyg</div>', unsafe_allow_html=True)
    st.caption("Behövs bara när ett redan skapat schema ska finjusteras.")

    try:
        _arrangement_type = str(tournament["arrangement_type"] or "tournament")
    except Exception:
        _arrangement_type = "tournament"
    from cupnavi_core.arrangement_type import ARRANGEMENT_MATCHCAMP, normalize_arrangement_type
    _arrangement_type = normalize_arrangement_type(_arrangement_type)
    _optimizer_is_matchcamp = _arrangement_type == ARRANGEMENT_MATCHCAMP

    _show_optimizer = st.toggle(
        "✨ Optimera befintligt schema",
        value=False,
        key=f"show_schedule_optimizer_{tid}",
        help="CupNavi räknar först fram ett förslag. Inget ändras förrän du godkänner det.",
    )
    if _show_optimizer:
        with st.container(border=True):
            st.markdown(
                "#### Optimera matchcampens flyt" if _optimizer_is_matchcamp
                else "#### Optimera turneringsschemat"
            )
            st.caption(
                (
                    "Matchcamp-läget prioriterar jämn vila och färre onödigt långa väntetider. "
                    "Antal matcher och motståndare analyseras också, men ändras inte automatiskt av tidsoptimeringen."
                    if _optimizer_is_matchcamp
                    else
                    "Turneringsläget prioriterar säkra vilotider och ett jämnt flöde utan att ändra gruppmöten eller slutspelslogik."
                )
            )
            st.caption(
                "CupNavi flyttar bara befintliga tider mellan ospelade, olåsta gruppmatcher. "
                "Planernas tider, planutnyttjande och domarnas tidsluckor lämnas oförändrade."
            )
            _opt_key = f"schedule_improvement_{tid}"
            if st.button(
                "Beräkna förbättring",
                key=f"calculate_schedule_improvement_{tid}",
                type="primary",
                use_container_width=True,
            ):
                from cupnavi_core.schedule_improvement import build_schedule_improvement
                _opt_matches = [dict(row) for row in all_rows(
                    """SELECT id,stage,scheduled_start,pitch_number,referee_id,home_source,away_source,
                              home_score,away_score,schedule_locked
                       FROM matches WHERE tournament_id=? ORDER BY scheduled_start,pitch_number,id""",
                    (tid,),
                )]
                _protected_rows = all_rows(
                    """SELECT DISTINCT t.id
                       FROM teams t
                       LEFT JOIN schedule_requests r ON r.team_id=t.id AND r.status='Godkänd'
                       WHERE t.tournament_id=? AND (COALESCE(t.late_first_match,0)=1 OR r.id IS NOT NULL)""",
                    (tid,),
                )
                _protected_ids = {int(row["id"]) for row in _protected_rows}
                _opt_duration = (
                    int(rules["halves"]) * int(rules["minutes_per_half"])
                    + max(0, int(rules["halves"]) - 1) * int(rules["halftime_minutes"])
                )
                _proposal = build_schedule_improvement(
                    _opt_matches,
                    match_duration_minutes=_opt_duration,
                    minimum_rest_minutes=int(rules["minimum_team_rest_minutes"] or 0),
                    protected_team_ids=_protected_ids,
                    arrangement_type=_arrangement_type,
                )
                st.session_state[_opt_key] = _proposal
                st.rerun()

            _proposal = st.session_state.get(_opt_key)
            if _proposal:
                _before = _proposal["before"]
                _after = _proposal["after"]
                st.markdown("##### Före → efter")
                _oc1,_oc2,_oc3,_oc4 = st.columns(4)
                _oc1.metric("Korta vilor", _after["short_rest"], delta=_before["short_rest"] - _after["short_rest"], delta_color="normal")
                _oc2.metric("Långa håltider", _after["long_waits"], delta=_before["long_waits"] - _after["long_waits"], delta_color="normal")
                _oc3.metric("Vilospread", f"{_after['fairness_spread']} min", delta=f"{_before['fairness_spread'] - _after['fairness_spread']} min")
                _min_after = _after["minimum_actual_rest"]
                _min_before = _before["minimum_actual_rest"]
                _oc4.metric(
                    "Kortaste vila",
                    f"{_min_after} min" if _min_after is not None else "–",
                    delta=(f"{_min_after - _min_before} min" if _min_after is not None and _min_before is not None else None),
                )
                if _optimizer_is_matchcamp:
                    st.markdown("##### Matchcamp-balans")
                    _mc1,_mc2,_mc3 = st.columns(3)
                    _mc1.metric("Skillnad matcher/lag", _before["match_count_spread"])
                    _mc2.metric("Skillnad speltid", f"{_before['playtime_spread_minutes']} min")
                    _mc3.metric("Upprepade motstånd", _before["repeated_opponents"])
                    if _before["match_count_spread"] > 0:
                        st.warning(
                            "Lagen har olika många matcher. Tidsoptimeringen kan inte lösa det eftersom den inte lägger till eller tar bort matcher."
                        )
                    if _before["repeated_opponents"] > 0:
                        st.caption(
                            "Upprepade motstånd visas som kvalitetsinformation. CupNavi byter inte motståndare i ett redan skapat schema utan separat kontroll."
                        )

                st.caption(
                    f"{_proposal['eligible_count']} matcher kunde analyseras säkert. "
                    "Lag med godkända schemaönskemål eller sen-startpreferenser lämnas orörda."
                )
                if _proposal["improved"]:
                    st.success(
                        (
                            f"CupNavi hittade ett bättre matchcampflöde genom att flytta {_proposal['updates'].__len__()} matcher mellan befintliga tidsluckor."
                            if _optimizer_is_matchcamp
                            else f"CupNavi hittade ett bättre turneringsflöde genom att flytta {_proposal['updates'].__len__()} matcher mellan befintliga tidsluckor."
                        )
                    )
                    if st.button(
                        "Använd det förbättrade schemat",
                        key=f"apply_schedule_improvement_{tid}",
                        use_container_width=True,
                        type="primary",
                    ):
                        if apply_schedule_improvement is None:
                            st.error("Optimeringen kan inte sparas i den här körningen.")
                        else:
                            try:
                                _home_away_changed = apply_schedule_improvement(
                                    tid, _proposal["updates"], _arrangement_type
                                )
                                st.session_state.pop(_opt_key, None)
                                st.session_state["schedule_message"] = (
                                    "success",
                                    f"Schemat förbättrades. {_proposal['updates'].__len__()} matcher fick bättre tidsfördelning"
                                    + (
                                        f" och {_home_away_changed} hemma/borta-lägen balanserades."
                                        if _home_away_changed and not _optimizer_is_matchcamp
                                        else "."
                                    ),
                                )
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Optimeringen kunde inte sparas: {exc}")
                else:
                    st.info("CupNavi hittade ingen säker förbättring utan att röra låsta matcher, lagönskemål eller befintliga tidsluckor.")


    if _show_optimizer and _optimizer_is_matchcamp:
        with st.container(border=True):
            st.markdown("#### Förbättra matchfördelningen")
            st.caption(
                "CupNavi kan även jämna ut antal matcher per lag och minska onödiga returmöten. "
                "Detta ändrar motståndare i ospelade, olåsta gruppmatcher men behåller samma tider, planer och domare."
            )
            st.caption(
                "Lag med godkända schemaönskemål eller sen-startpreferenser skyddas även här. "
                "CupNavi accepterar aldrig ett förslag som ökar överlapp eller antal för korta vilor."
            )
            _structure_key = f"matchcamp_structure_improvement_{tid}"
            if st.button(
                "Beräkna bättre matchfördelning",
                key=f"calculate_matchcamp_structure_{tid}",
                use_container_width=True,
            ):
                from cupnavi_core.matchcamp_structure import build_matchcamp_structure_improvement
                _structure_matches = [dict(row) for row in all_rows(
                    """SELECT id,group_id,stage,scheduled_start,pitch_number,referee_id,
                              home_source,away_source,home_score,away_score,schedule_locked
                       FROM matches WHERE tournament_id=? ORDER BY group_id,match_no,id""",
                    (tid,),
                )]
                _structure_teams = [dict(row) for row in all_rows(
                    "SELECT id,group_id,name FROM teams WHERE tournament_id=? ORDER BY group_id,name,id",
                    (tid,),
                )]
                _protected_rows = all_rows(
                    """SELECT DISTINCT t.id
                       FROM teams t
                       LEFT JOIN schedule_requests r ON r.team_id=t.id AND r.status='Godkänd'
                       WHERE t.tournament_id=? AND (COALESCE(t.late_first_match,0)=1 OR r.id IS NOT NULL)""",
                    (tid,),
                )
                _protected_ids = {int(row["id"]) for row in _protected_rows}
                _structure_duration = (
                    int(rules["halves"]) * int(rules["minutes_per_half"])
                    + max(0, int(rules["halves"]) - 1) * int(rules["halftime_minutes"])
                )
                st.session_state[_structure_key] = build_matchcamp_structure_improvement(
                    _structure_matches,
                    _structure_teams,
                    match_duration_minutes=_structure_duration,
                    minimum_rest_minutes=int(rules["minimum_team_rest_minutes"] or 0),
                    protected_team_ids=_protected_ids,
                )
                st.rerun()

            _structure_proposal = st.session_state.get(_structure_key)
            if _structure_proposal:
                _sb = _structure_proposal["before"]
                _sa = _structure_proposal["after"]
                _sm1,_sm2,_sm3 = st.columns(3)
                _sm1.metric(
                    "Skillnad matcher/lag",
                    _sa["match_count_spread"],
                    delta=_sb["match_count_spread"] - _sa["match_count_spread"],
                    delta_color="normal",
                )
                _sm2.metric(
                    "Skillnad speltid",
                    f"{_sa['playtime_spread_minutes']} min",
                    delta=f"{_sb['playtime_spread_minutes'] - _sa['playtime_spread_minutes']} min",
                )
                _sm3.metric(
                    "Upprepade motstånd",
                    _sa["repeated_opponents"],
                    delta=_sb["repeated_opponents"] - _sa["repeated_opponents"],
                    delta_color="normal",
                )
                st.caption(
                    f"{_structure_proposal['eligible_count']} matcher kan ändras säkert. "
                    "Antalet matcher totalt och varje grupps antal matcher förblir oförändrat."
                )
                if _structure_proposal["improved"]:
                    _team_name_map = {
                        int(row["id"]): str(row["name"])
                        for row in all_rows(
                            "SELECT id,name FROM teams WHERE tournament_id=?",
                            (tid,),
                        )
                    }
                    st.success(
                        f"CupNavi hittade en bättre matchfördelning genom att ändra "
                        f"{len(_structure_proposal['updates'])} matchkopplingar."
                    )
                    with st.expander("Visa föreslagna ändringar", expanded=False):
                        for _su in _structure_proposal["updates"]:
                            _old_h = int(str(_su["expected_home_source"]).split(":")[1])
                            _old_a = int(str(_su["expected_away_source"]).split(":")[1])
                            _new_h = int(str(_su["home_source"]).split(":")[1])
                            _new_a = int(str(_su["away_source"]).split(":")[1])
                            st.caption(
                                f"Match {_su['id']}: "
                                f"{_team_name_map.get(_old_h, _old_h)} – {_team_name_map.get(_old_a, _old_a)} "
                                f"→ {_team_name_map.get(_new_h, _new_h)} – {_team_name_map.get(_new_a, _new_a)}"
                            )
                    if st.button(
                        "Använd den bättre matchfördelningen",
                        key=f"apply_matchcamp_structure_{tid}",
                        type="primary",
                        use_container_width=True,
                    ):
                        if apply_matchcamp_structure_improvement is None:
                            st.error("Matchfördelningen kan inte sparas i den här körningen.")
                        else:
                            try:
                                apply_matchcamp_structure_improvement(
                                    tid, _structure_proposal["updates"]
                                )
                                st.session_state.pop(_structure_key, None)
                                st.session_state.pop(f"schedule_improvement_{tid}", None)
                                st.session_state["schedule_message"] = (
                                    "success",
                                    "Matchfördelningen förbättrades. Kontrollera nu schemat igen innan publicering.",
                                )
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Matchfördelningen kunde inte sparas: {exc}")
                else:
                    st.info(
                        "CupNavi hittade ingen säkrare matchfördelning som förbättrar balansen "
                        "utan att försämra överlapp eller vilotider."
                    )

    # Historical QA anchor: 📷 Kopiera upplägg från ett tidigare schema
    _show_template_import = st.toggle(
        "📷 Utgå från ett tidigare schema",
        value=False,
        key=f"show_schedule_template_import_{tid}",
        help="Ladda upp ett foto eller en skärmdump. CupNavi försöker läsa strukturen och anpassa den till den här cupen.",
    )
    if _show_template_import:
        with st.container(border=True):
            st.markdown("#### Efterlikna ett tidigare cupupplägg")
            st.caption(
                "CupNavi kopierar inte gamla lag eller resultat. Bilden används för att förstå strukturen: "
                "grupper, plantider, vilomönster, kompakthet och eventuellt slutspel."
            )
            _template_api_key = setting("OPENAI_API_KEY")
            _template_model = setting("CUPNAVI_AI_SCHEDULE_MODEL") or setting("CUPNAVI_AI_ROSTER_MODEL") or "gpt-5.6-luna"
            _template_file = st.file_uploader(
                "Foto eller skärmdump av tidigare schema",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"schedule_template_file_{tid}",
            )
            if not _template_api_key:
                st.info("AI-avläsningen aktiveras när OPENAI_API_KEY finns konfigurerad.")
            if st.button(
                "Analysera upplägget",
                key=f"analyze_schedule_template_{tid}",
                type="primary",
                use_container_width=True,
                disabled=_template_file is None or not bool(_template_api_key),
            ):
                try:
                    from cupnavi_core.schedule_template_import import extract_schedule_template_from_image
                    with st.spinner("CupNavi läser av schemats struktur…"):
                        _analysis = extract_schedule_template_from_image(
                            _template_file.getvalue(),
                            getattr(_template_file, "type", None),
                            _template_api_key,
                            model=_template_model,
                        )
                    st.session_state[f"schedule_template_analysis_{tid}"] = _analysis
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

            _analysis = st.session_state.get(f"schedule_template_analysis_{tid}")
            if _analysis:
                _confidence_label = {"high": "Hög", "medium": "Medel", "low": "Låg"}.get(_analysis["confidence"], "Låg")
                st.markdown(f"**CupNavis tolkning · säkerhet: {_confidence_label}**")
                st.write(_analysis["summary"] or "Ingen sammanfattning kunde läsas ut.")
                _a1, _a2, _a3, _a4 = st.columns(4)
                _a1.metric("Grupper", _analysis["group_count"] or "–")
                _a2.metric("Typisk grupp", f"{_analysis['typical_group_size']} lag" if _analysis["typical_group_size"] else "–")
                _a3.metric("Planer i originalet", _analysis["pitch_count"] or "–")
                _a4.metric("Kompakthet", f"{_analysis['compactness']}/100")
                _timing_mode_text = "Gemensamma avsparkstider" if _analysis["synchronized_pitch_times"] else "Dynamiska plantider"
                st.markdown(f"**Tidsmönster:** {_timing_mode_text}")
                if _analysis["first_match_time"] or _analysis["last_match_time"]:
                    st.caption(
                        f"Observerat tidsspann: {_analysis['first_match_time'] or '–'}–{_analysis['last_match_time'] or '–'} · "
                        f"ungefärligt startintervall {_analysis['estimated_match_interval_minutes'] or '–'} min."
                    )
                if _analysis["caveats"]:
                    with st.expander("Osäkerheter i bildtolkningen", expanded=False):
                        for _caveat in _analysis["caveats"]:
                            st.write(f"• {_caveat}")

                from cupnavi_core.schedule_template_import import adapt_schedule_template
                _current_match_duration = (
                    int(rules["halves"]) * int(rules["minutes_per_half"])
                    + max(0, int(rules["halves"]) - 1) * int(rules["halftime_minutes"])
                )
                _adapted = adapt_schedule_template(
                    _analysis,
                    team_count=max(2, registered_team_count or expected_team_count or 2),
                    pitch_count=max(1, int(rules["pitch_count"] or 1)),
                    current_match_duration_minutes=_current_match_duration,
                    current_min_rest_minutes=int(rules["minimum_team_rest_minutes"] or 0),
                )

                st.markdown("##### Så skulle upplägget se ut i den här cupen")
                _p1, _p2, _p3, _p4 = st.columns(4)
                _p1.metric("Lag", _adapted["team_count"])
                _p2.metric("Grupper", _adapted["group_count"])
                _p3.metric("Planer", _adapted["pitch_count"])
                _p4.metric("Matcher, ca", _adapted["total_matches"])
                _group_text = " + ".join(str(size) for size in _adapted["group_sizes"])
                _hours = _adapted["estimated_day_minutes"] / 60 if _adapted["estimated_day_minutes"] else 0
                st.markdown(
                    f"**Gruppfördelning:** {_group_text} lag · "
                    f"**tidsläge:** {'gemensamma avsparkstider' if _adapted['synchronized_pitch_times'] else 'dynamiska plantider'} · "
                    f"**minsta vila:** cirka {_adapted['minimum_team_rest_minutes']} min."
                )
                if _hours:
                    st.caption(
                        f"Grov uppskattning av schemats aktiva tidsomfång: cirka {_hours:.1f} timmar. "
                        "Detta är inte ett färdigt schema och tar ännu inte hänsyn till alla lagönskemål, domare eller plantidsfönster."
                    )
                st.progress(_adapted["similarity"] / 100)
                st.caption(
                    f"Likhet med originalupplägget: {_adapted['similarity']}% · {_adapted['similarity_label']}. "
                    "CupNavi anpassar hellre upplägget än att tvinga in fel antal lag eller planer."
                )

                st.info(
                    "När du använder upplägget behåller CupNavi den här cupens egna lag och faktiska antal planer. "
                    "Vi kopierar bara schemastilen och den anpassade gruppstrukturen ovan."
                )
                # Legacy QA anchor: Använd upplägget som utgångspunkt
                if st.button(
                    "Använd det anpassade upplägget",
                    key=f"apply_schedule_template_{tid}",
                    use_container_width=True,
                    disabled=_analysis["confidence"] == "low",
                ):
                    _template_rest = max(0, min(300, int(_adapted["minimum_team_rest_minutes"] or 0)))
                    _template_compactness = max(0, min(100, int(_adapted["compactness"] or 50)))
                    _template_strategy = "earliest_finish" if _template_compactness >= 50 else "use_pitch_windows"
                    _recommended_group_size = max(_adapted["group_sizes"]) if _adapted["group_sizes"] else 0
                    run(
                        """UPDATE schedule_rules
                           SET synchronized_pitch_times=?, compactness_level=?, schedule_strategy=?,
                               minimum_team_rest_minutes=?, recommended_group_count=?, recommended_group_size=?
                           WHERE tournament_id=?""",
                        (
                            int(bool(_adapted["synchronized_pitch_times"])),
                            _template_compactness,
                            _template_strategy,
                            _template_rest,
                            int(_adapted["group_count"] or 0),
                            int(_recommended_group_size or 0),
                            int(tid),
                        ),
                    )
                    run("UPDATE tournaments SET schedule_dirty=1 WHERE id=?", (int(tid),))
                    st.session_state["schedule_message"] = (
                        "success",
                        "Det anpassade upplägget används nu som utgångspunkt. CupNavi behåller den här cupens egna lag och planer.",
                    )
                    st.rerun()

    # v1.261: st.expander är inte lazy. Den gamla score-analysen kördes därför
    # vid varje rerun trots att användaren inte öppnat den.
    # Historical QA anchor: "Visa regelverk & schemakvalitet"
    _show_schedule_quality = st.toggle(
        "Analysera schemakvalitet",
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

            # v359: explain the quality score with organizer-facing dimensions.
            _quality_matches = [
                dict(row) for row in all_rows(
                    "SELECT id,home_source,away_source,scheduled_start,pitch_number FROM matches WHERE tournament_id=?",
                    (tid,),
                )
            ]
            from cupnavi_core.schedule_quality import schedule_quality_dimensions
            _match_duration = (
                int(rules["halves"]) * int(rules["minutes_per_half"])
                + max(0, int(rules["halves"]) - 1) * int(rules["halftime_minutes"])
            )
            _dimensions = schedule_quality_dimensions(
                _quality_matches,
                min_rest_minutes=int(rules["minimum_team_rest_minutes"] or 0),
                match_duration_minutes=_match_duration,
            )
            st.markdown("##### Kvalitetsprofil")
            st.caption("Det här förklarar Schema Score. Det är inte ett separat AI-betyg.")
            _dim_cols = st.columns(5)
            _dim_labels = [
                ("completeness", "Fullständighet"),
                ("rest", "Lagvila"),
                ("flow", "Håltider"),
                ("fairness", "Rättvisa"),
                ("pitch_utilization", "Planutnyttjande"),
            ]
            for _col, (_key, _label) in zip(_dim_cols, _dim_labels):
                _dim = _dimensions[_key]
                _col.metric(_label, f"{_dim['score']}/100")
                _col.caption(f"{_dim['grade']} · {_dim['detail']}")

    _show_schedule_export = st.toggle("Exportera schema", value=False, key=f"schedule_export_{tid}", help="Exportunderlaget laddas först när du behöver det.")
    if _show_schedule_export:
        st.markdown("**Cupprogram & PDF**")
        st.caption(
            "Skapa ett professionellt cupprogram för lag, publik och utskrift – med cupöversikt, "
            "grupper, gruppspel, slutspel, tabeller och praktisk information. Det detaljerade "
            "schemapaketet finns kvar som extra export."
        )
        # Legacy export remains available: Skapa komplett schemapaket som PDF
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

            if st.button("Skapa professionellt cupprogram", use_container_width=True, key=f"prepare_pdf_{tid}", type="primary"):
                st.caption("Skapar även komplett schemapaket som PDF för detaljerad administration.")
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

                    _tournament_pdf_keys = (
                        "name", "location", "tournament_date", "start_date", "end_date",
                        "table_tiebreak", "playoff_tie_rule", "extra_time_minutes",
                        "public_information", "organizer_phone", "instagram_url",
                    )
                    tournament_for_pdf = {
                        key: tournament[key]
                        for key in _tournament_pdf_keys
                        if key in tournament.keys()
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
                        {
                            key: team_row[key]
                            for key in ("id", "name", "group_id", "primary_color", "secondary_color")
                            if key in team_row.keys()
                        }
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

                    pdf_rules_row = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
                    pdf_rules = dict(pdf_rules_row) if pdf_rules_row is not None else {}
                    pdf_pitches_rows = all_rows("SELECT * FROM pitches WHERE tournament_id=? ORDER BY pitch_number", (tid,))
                    pdf_pitches = [dict(row) for row in pdf_pitches_rows]

                    from cupnavi_core.pdf_export import build_cup_program_pdf
                    from cupnavi_core.pdf_export import build_schedule_pdf

                    program_key = f"cup_program_pdf_bytes_{tid}"
                    st.session_state[program_key] = build_cup_program_pdf(
                        tournament_for_pdf,
                        matches_for_pdf,
                        teams_for_pdf,
                        groups_for_pdf,
                        refs_for_pdf,
                        source_labels_for_pdf,
                        source_team_ids_for_pdf,
                        rules=pdf_rules,
                        pitches=pdf_pitches,
                    )

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
                st.success("✓ Cupprogrammet är klart.")
                program_key = f"cup_program_pdf_bytes_{tid}"
                if program_key in st.session_state:
                    st.download_button(
                        "Ladda ner cupprogram som PDF",
                        data=st.session_state[program_key],
                        file_name=f"{safe_pdf_name}_cupprogram.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                        key=f"download_cup_program_pdf_{tid}",
                    )
                st.caption("Behöver du ett administrativt detaljunderlag finns hela schemapaketet här också.")
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

    show_schedule_detail_tools = st.toggle(
        "Visa detaljer och redigering",
        value=False,
        key=f"schedule_detail_tools_{tid}",
        help="Laddar visuellt schema, drag-and-drop, matchjustering och resultatredigering först när du behöver dem.",
    )
    if show_schedule_detail_tools:
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
        # v389: the detail workspace already loaded every scheduled match above.
        # Reuse that snapshot instead of issuing the same matches query twice.
        refs = adjustable_refs if "adjustable_refs" in locals() else all_rows(
            "SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,)
        )
        referee_names = {r["id"]: r["name"] for r in refs}
        schedule_pitch_names = pitch_name_map(tid,int(rules["pitch_count"]))
        scheduled_matches = adjustable_matches
        if not scheduled_matches:
            st.info("Klicka på Skapa matcher och generera spelschema ovan.")
        else:
            # v389: player statistics used to be fetched once per match (N+1).
            # Fetch the complete tournament snapshot once and group it in memory.
            event_rows_by_match = {}
            for event_row in all_rows(
                """
                SELECT player_match_stats.match_id, players.name, player_match_stats.*
                FROM player_match_stats
                JOIN players ON players.id=player_match_stats.player_id
                JOIN matches ON matches.id=player_match_stats.match_id
                WHERE matches.tournament_id=?
                ORDER BY player_match_stats.match_id, players.name
                """,
                (tid,),
            ):
                event_rows_by_match.setdefault(int(event_row["match_id"]), []).append(event_row)

            schedule_rows = []
            for index, m in enumerate(scheduled_matches, 1):
                home_id = resolve_source(m["home_source"])
                away_id = resolve_source(m["away_source"])
                home = team(home_id)
                away = team(away_id)
                start_dt = datetime.fromisoformat(m["scheduled_start"])
                event_rows = event_rows_by_match.get(int(m["id"]), [])
                goals_text = ", ".join(f"{e['name']} ({e['goals']})" for e in event_rows if e["goals"]) or "–"
                assists_text = ", ".join(f"{e['name']} ({e['assists']})" for e in event_rows if e["assists"]) or "–"
                yellow_text = ", ".join(f"{e['name']} ({e['yellow_cards']})" for e in event_rows if e["yellow_cards"]) or "–"
                red_text = ", ".join(f"{e['name']} ({e['red_cards']})" for e in event_rows if e["red_cards"]) or "–"
                home_kit_color, away_kit_color, away_kit_used = match_kit_colors(home, away)
                home_home_conflict = bool(home and away and away_kit_used)
                unresolved_kit_conflict = bool(kit_color_conflict(home, away))
                kit_guidance = build_kit_guidance(
                    home_name=home["name"] if home else source_label(m["home_source"]),
                    away_name=away["name"] if away else source_label(m["away_source"]),
                    home_home_conflict=home_home_conflict,
                    away_kit_used=bool(away_kit_used),
                    unresolved_conflict=unresolved_kit_conflict,
                )
                kit_note = str(kit_guidance["short"])
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
                    "Tröjstatus": str(kit_guidance["state"]),
                    "Tröjdetalj": str(kit_guidance["detail"]),
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
            unresolved_kit_total = sum(1 for row in schedule_rows if row.get("Tröjstatus") == "conflict")
            switched_kit_total = sum(1 for row in schedule_rows if row.get("Tröjstatus") == "resolved")
            st.markdown(
                f"""<div class="cn-kit-summary {'attention' if unresolved_kit_total else 'clear'}">
                  <div><span class="value">{unresolved_kit_total}</span><span class="label">färgkrockar kräver åtgärd</span></div>
                  <div><span class="value">{switched_kit_total}</span><span class="label">matcher lösta med bortaställ</span></div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.caption("CupNavi rekommenderar ställ automatiskt. Endast kvarvarande färgkrockar behöver arrangörens åtgärd.")
            for row in schedule_rows:
                issues = []
                if row["Domare"] == "Ej tillsatt":
                    issues.append("Domare saknas")
                if row.get("Tröjstatus") == "conflict":
                    issues.append("Färgkrock")
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
                      <div class="cn-kit-choice {html.escape(str(row.get('Tröjstatus') or 'clear'))}">
                        <span class="label">Matchställ</span><strong>{html.escape(str(row['Tröjval']))}</strong>
                        <small>{html.escape(str(row.get('Tröjdetalj') or ''))}</small>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("Redigera resultat i tabell"):
                edited_schedule = st.data_editor(
                    schedule_df,
                    hide_index=True,
                    use_container_width=True,
                    disabled=["match_id", "Match", "Fas", "Plan", "Datum", "Tid", "Hemmalag", "Hemmafärg", "Bortalag", "Bortafärg", "Tröjval", "Tröjstatus", "Tröjdetalj", "Domare", "Låst", "Målskyttar", "Assister", "Varningar", "Utvisningar"],
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
                    expected_home, expected_away = original_scores.get(match_id, (None, None))
                    if (expected_home, expected_away) != (home_score, away_score):
                        changed_scores.append((home_score, away_score, match_id, expected_home, expected_away))

                if changed_scores:
                    save_result = save_bulk_schedule_results(tid, changed_scores, bool(tournament["is_published"]))
                    saved_count = len(save_result.get("saved", []))
                    conflict_count = len(save_result.get("conflicts", []))
                    integrity_count = len(save_result.get("integrity_blocked", []))
                    dependency_blocked = list(save_result.get("dependency_blocked", []))
                    dependency_count = len(dependency_blocked)
                    if saved_count:
                        st.success(f"Resultat sparade för {saved_count} matcher.")
                    if conflict_count:
                        st.warning(
                            f"{conflict_count} match(er) hade ändrats efter att schemat laddades och skrevs inte över. "
                            "Ladda om och kontrollera det senaste resultatet."
                        )
                    if integrity_count:
                        st.error(
                            f"{integrity_count} match(er) sparades inte eftersom resultatet skulle bli lägre än "
                            "redan registrerade målskyttsmål. Korrigera Matchhändelser först."
                        )
                    if dependency_count:
                        st.error(
                            f"{dependency_count} slutspelsresultat sparades inte eftersom en senare match redan används."
                        )
                        for _blocked in dependency_blocked[:3]:
                            _message = str(_blocked[1] if len(_blocked) > 1 else "").strip()
                            if _message:
                                st.caption(_message)
                            _downstream_ids = tuple(_blocked[3] if len(_blocked) > 3 else ())
                            if (
                                _downstream_ids
                                and deps.reset_unused_playoff_downstream_match is not None
                            ):
                                _downstream_id = int(_downstream_ids[0])
                                if st.button(
                                    f"↩ Återställ oanvänd match {_downstream_id}",
                                    key=f"reset_playoff_downstream_{tid}_{_downstream_id}",
                                    use_container_width=True,
                                ):
                                    _reset = deps.reset_unused_playoff_downstream_match(tid, _downstream_id)
                                    if _reset.get("reset"):
                                        st.success(_reset.get("message", "Matchen återställdes."))
                                    else:
                                        st.error(_reset.get("message", "Matchen kunde inte återställas."))
                    st.rerun()
                else:
                    st.info("Inga resultatändringar att spara.")
            st.caption("Målskyttar, assist, varningar och utvisningar registreras under fliken Matchhändelser och visas därefter automatiskt här.")
