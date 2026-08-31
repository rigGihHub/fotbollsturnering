from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any, Callable

import pandas as pd

from cupnavi_core.initial_setup_logic import (
    available_pitch_minutes,
    estimated_capacity_slots,
    estimated_match_length_minutes,
    normalized_priority_order,
    priority_order_changed,
)


@dataclass(frozen=True)
class InitialSetupDependencies:
    st: Any
    one_row: Callable[..., Any]
    run: Callable[..., Any]
    sport_setup_recommendation: Callable[..., Any]
    row_value: Callable[..., Any]
    cup_date_label: Callable[..., Any]
    add_competition_class: Callable[..., Any]
    competition_classes: Callable[..., Any]
    all_rows: Callable[..., Any]
    competition_class_label: Callable[..., Any]
    sync_expected_team_count_from_classes: Callable[..., Any]
    remove_competition_class: Callable[..., Any]
    autosave_rule_field: Callable[..., Any]
    ensure_pitch_definitions: Callable[..., Any]
    save_pitch_name: Callable[..., Any]
    save_pitch_address: Callable[..., Any]
    ensure_pitch_day_windows: Callable[..., Any]
    save_pitch_day_window: Callable[..., Any]
    pitch_travel_matrix: Callable[..., Any]
    save_pitch_travel_time: Callable[..., Any]
    recommend_tournament_format: Callable[..., Any]
    autosave_tournament_field: Callable[..., Any]
    render_centered_table: Callable[..., Any]
    db: Callable[..., Any]
    clear_render_query_cache: Callable[..., Any]
    sort_items: Any
    youth_class_categories: Any
    youth_class_years: Any
    difficulty_levels: Any
    date_with_weekday: Callable[..., Any]


def render_initial_tournament_setup(tournament_id, tournament, *, deps: InitialSetupDependencies):
    st = deps.st
    one_row = deps.one_row
    run = deps.run
    sport_setup_recommendation = deps.sport_setup_recommendation
    _row_value = deps.row_value
    cup_date_label = deps.cup_date_label
    add_competition_class = deps.add_competition_class
    competition_classes = deps.competition_classes
    all_rows = deps.all_rows
    competition_class_label = deps.competition_class_label
    sync_expected_team_count_from_classes = deps.sync_expected_team_count_from_classes
    remove_competition_class = deps.remove_competition_class
    _autosave_rule_field = deps.autosave_rule_field
    ensure_pitch_definitions = deps.ensure_pitch_definitions
    save_pitch_name = deps.save_pitch_name
    save_pitch_address = deps.save_pitch_address
    ensure_pitch_day_windows = deps.ensure_pitch_day_windows
    save_pitch_day_window = deps.save_pitch_day_window
    pitch_travel_matrix = deps.pitch_travel_matrix
    save_pitch_travel_time = deps.save_pitch_travel_time
    recommend_tournament_format = deps.recommend_tournament_format
    _autosave_tournament_field = deps.autosave_tournament_field
    render_centered_table = deps.render_centered_table
    db = deps.db
    _clear_render_query_cache = deps.clear_render_query_cache
    sort_items = deps.sort_items
    YOUTH_CLASS_CATEGORIES = deps.youth_class_categories
    YOUTH_CLASS_YEARS = deps.youth_class_years
    DIFFICULTY_LEVELS = deps.difficulty_levels
    date_with_weekday = deps.date_with_weekday
    """Första konfigurationssidan efter skapande. Vanliga fält autosparas."""
    st.title("Kom igång med turneringen")
    st.caption("Börja med det som krävs för att lägga in lag och skapa schema. Övriga inställningar kan finjusteras senare.")
    st.info(f"**{tournament['name']}** · {tournament['sport']} · {cup_date_label(tournament)}")
    st.markdown(
        "<div class='cn-setup-flow'><b>1 Grund</b><span>→</span><b>2 Kapacitet</b><span>→</span><b>3 Lägg till lag</b></div>",
        unsafe_allow_html=True,
    )
    st.caption("Det räcker normalt att ange tävlingsklasser, planerat lagantal och när planerna är tillgängliga. CupNavi har standardvärden för resten.")
    rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
    if rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tournament_id,))
        rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

    _sport_rec=sport_setup_recommendation(_row_value(tournament,"sport","Fotboll"))
    st.markdown("### Sportprofil")
    # v325: keep the recommendation useful without four narrow metric cards on mobile.
    st.markdown(
        f'**{_sport_rec["display_name"]}** · {_sport_rec["periods"]} {_sport_rec["period_label"]} · '
        f'{_sport_rec["minutes_per_period"]} min/{_sport_rec["period_label"].rstrip("er")} · '
        f'min. lagvila {_sport_rec["minimum_rest_minutes"]} min'
    )
    st.caption(
        f'{_sport_rec["match_note"]} {_sport_rec["rest_note"]} '
        f'Relevant statistik: {", ".join(_sport_rec["relevant_stats"])}. '
        f'Slutspel: {_sport_rec["playoff_note"]}'
    )

    _played_setup=int(one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (tournament_id,),
    )["n"] or 0)
    if _played_setup:
        st.info("Sportprofilens standardvärden visas som referens. De kan inte appliceras efter att resultat har registrerats.")
    elif st.button(
        f'Använd rekommenderade {_sport_rec["display_name"].lower()}-värden',
        key=f"apply_sport_defaults_{tournament_id}",
        use_container_width=True,
    ):
        run(
            """UPDATE schedule_rules
               SET halves=?,minutes_per_half=?,halftime_minutes=?,minimum_team_rest_minutes=?
               WHERE tournament_id=?""",
            (
                _sport_rec["periods"],
                _sport_rec["minutes_per_period"],
                _sport_rec["break_minutes"],
                _sport_rec["minimum_rest_minutes"],
                tournament_id,
            ),
        )
        # Public stat defaults follow what the sport actually tracks.
        run(
            """UPDATE tournaments
               SET enable_scorer_leaderboard=?,
                   enable_assist_leaderboard=?,
                   enable_card_statistics=?
               WHERE id=?""",
            (
                1 if _sport_rec["score_label"] in ("mål","goals") else 0,
                1 if _sport_rec["tracks_assists"] else 0,
                1 if _sport_rec["discipline_mode"] in ("cards","two_minute_and_cards") else 0,
                tournament_id,
            ),
        )
        st.session_state[f"autosave_notice_{tournament_id}"]=f'✓ {_sport_rec["display_name"]}-profilen applicerades.'
        st.rerun()

    # Legacy QA anchor: ### 1. Tävlingsklasser och svårighetsgrad
    st.markdown("### 1. Grunduppgifter")
    st.caption("Definiera varje tävlingsklass och hur många lag du planerar i just den klassen. Summan används som cupens totala planeringsantal.")
    _class_played_count=_played_setup
    _class_locked=_class_played_count > 0
    if _class_locked:
        st.warning("Tävlingsklasser och planerat lagantal är låsta efter att första resultatet har registrerats. Befintliga lag och spelade matcher skyddas.")
    elif bool(_row_value(tournament,"is_published",0)):
        st.info("Du kan fortfarande lägga till en klass före första spelade matchen. Det kan kräva ny gruppindelning och omplanering av framtida matcher.")

    # v325: class creation is progressive and vertical. The old four-column row
    # compressed labels and touch targets on phones before the organiser had
    # even added a first class. Keep it open only while the setup still needs one.
    _existing_class_rows = competition_classes(tournament_id)
    with st.expander("➕ Lägg till tävlingsklass", expanded=not _existing_class_rows and not _class_locked):
        setup_category = st.selectbox("Kategori", list(YOUTH_CLASS_CATEGORIES), key=f"setup_class_category_{tournament_id}", disabled=_class_locked)
        setup_year = st.selectbox("Födelseår", YOUTH_CLASS_YEARS, index=YOUTH_CLASS_YEARS.index(2014) if 2014 in YOUTH_CLASS_YEARS else 0, key=f"setup_class_year_{tournament_id}", disabled=_class_locked)
        setup_class_teams = st.number_input("Planerade lag", 2, 200, 8, key=f"setup_class_teams_new_{tournament_id}", disabled=_class_locked)
        if st.button("Lägg till tävlingsklass", key=f"setup_add_class_{tournament_id}", use_container_width=True, disabled=_class_locked):
            ok, message = add_competition_class(tournament_id, setup_category, setup_year, setup_class_teams)
            (st.success if ok else st.info)(message)
            st.rerun()

    class_rows = _existing_class_rows
    _team_count_rows = all_rows(
        """SELECT competition_class_id, COUNT(*) AS n
           FROM teams
           WHERE tournament_id=?
           GROUP BY competition_class_id""",
        (tournament_id,),
    )
    _team_count_by_class = {
        _row_value(count_row, "competition_class_id", None): int(_row_value(count_row, "n", 0) or 0)
        for count_row in _team_count_rows
    }
    _actual_team_count = sum(_team_count_by_class.values())

    if not class_rows:
        st.warning("Lägg till minst en tävlingsklass och ange planerat antal lag innan du går vidare.")
    _planned_total=0
    for row in class_rows:
        _actual_in_class=int(_team_count_by_class.get(int(row["id"]),0))
        saved_planned=max(_actual_in_class,int(_row_value(row,"planned_team_count",0) or 0))
        with st.container(border=True):
            st.markdown(f"**{competition_class_label(row)}** · {_actual_in_class} anmälda")
            planned_key=f"setup_planned_class_teams_{row['id']}"
            planned_value=st.number_input(
                "Planerade lag",
                min_value=max(2,_actual_in_class),
                max_value=200,
                value=max(2,saved_planned or 8),
                key=planned_key,
                disabled=_class_locked,
                help=f"Registrerade lag i klassen: {_actual_in_class}. Planerat antal kan inte understiga detta.",
            )
            _planned_total += int(planned_value)
            if not _class_locked and int(planned_value)!=int(_row_value(row,"planned_team_count",0) or 0):
                run("UPDATE competition_classes SET planned_team_count=? WHERE id=?",(int(planned_value),int(row["id"])))
                sync_expected_team_count_from_classes(tournament_id)
                st.session_state[f"autosave_notice_{tournament_id}"]="✓ Planerat lagantal sparat"

            saved_diff = _row_value(row, "difficulty", "Medel") or "Medel"
            if saved_diff not in DIFFICULTY_LEVELS:
                saved_diff = "Medel"
            key = f"setup_diff_{row['id']}"
            choice = st.selectbox("Nivå", DIFFICULTY_LEVELS, index=DIFFICULTY_LEVELS.index(saved_diff), key=key, disabled=_class_locked)
            if not _class_locked and choice != saved_diff:
                run("UPDATE competition_classes SET difficulty=? WHERE id=?", (choice, row["id"]))
                st.session_state[f"autosave_notice_{tournament_id}"] = "✓ Sparat automatiskt"
            if st.button("Ta bort klass", key=f"setup_remove_class_{row['id']}", use_container_width=True, disabled=_class_locked):
                ok, message = remove_competition_class(tournament_id, int(row["id"]))
                (st.success if ok else st.error)(message)
                if ok:
                    st.rerun()
    if class_rows:
        st.caption(f"Planerat totalt antal lag: **{_planned_total}** · detta är summan av klasserna och kan ändras fram till första registrerade resultat.")

    # Legacy QA anchor: ### 2. Planer och öppettider per dag
    st.markdown("### 2. Kapacitet & speltider")
    st.caption("Detta kommer före tävlingsformatet eftersom antal planer och tillgängliga timmar avgör hur många matcher och vilket slutspel som faktiskt ryms.")
    pitch_key=f"setup_pitches_{tournament_id}"
    st.number_input(
        "Antal tillgängliga planer/spelytor",
        1, 50, int(rules["pitch_count"]),
        key=pitch_key,
        on_change=_autosave_rule_field,
        args=(tournament_id,"pitch_count",pitch_key,int),
        help="Detta är cupens samtidiga plankapacitet och används tillsammans med start- och sluttiderna för varje dag när schemat byggs.",
    )
    current_pitch_count=int(st.session_state.get(pitch_key,rules["pitch_count"]))
    pitch_rows=ensure_pitch_definitions(tournament_id,current_pitch_count)
    st.markdown("**Namnge planer/spelytor**")
    st.caption("Ge varje plan ett eget namn, exempelvis Huvudplan, Hall A eller Arena 2. Planens nummer behålls bara som internt ID.")
    pitch_names={}
    for pr in pitch_rows:
        pitch=int(pr["pitch_number"]); saved_name=str(pr["name"] or f"Plan {pitch}")
        nk=f"pitch_name_{tournament_id}_{pitch}"
        name=st.text_input(f"Plan {pitch}",value=saved_name,key=nk,placeholder=f"Exempel: A-plan, Hall 1 eller Arena {pitch}")
        clean=(name or "").strip() or f"Plan {pitch}"
        pitch_names[pitch]=clean
        if clean!=saved_name:
            save_pitch_name(tournament_id,pitch,clean)
            st.session_state[f"autosave_notice_{tournament_id}"]="✓ Plannamn sparade automatiskt"
        saved_address=str(_row_value(pr,"address","") or "")
        ak=f"pitch_address_{tournament_id}_{pitch}"
        address=st.text_input(f"Adress – {clean}",value=saved_address,key=ak,placeholder="Exempel: Rudbecksgatan 52, Örebro")
        if address.strip()!=saved_address.strip():
            save_pitch_address(tournament_id,pitch,address)
            st.session_state[f"autosave_notice_{tournament_id}"]="✓ Planadress sparad automatiskt"
    st.caption("Kapacitetssteget anger vad som är möjligt. Hur CupNavi ska prioritera mellan flera möjliga scheman väljer du i steg 5.")
    travel_key=f"setup_consider_pitch_travel_{tournament_id}"
    consider_travel=st.checkbox("Ta hänsyn till restid mellan planer",value=bool(_row_value(rules,"consider_pitch_travel",0)),key=travel_key,help="CupNavi använder de restider du anger nedan. Ingen extern karttjänst anropas.")
    if consider_travel!=bool(_row_value(rules,"consider_pitch_travel",0)):
        run("UPDATE schedule_rules SET consider_pitch_travel=? WHERE tournament_id=?",(1 if consider_travel else 0,int(tournament_id)))
    if consider_travel and current_pitch_count>1:
        st.caption("Ange faktisk förflyttningstid mellan spelytor. Värdet används som minsta extra tid när ett lag byter plan.")
        matrix=pitch_travel_matrix(tournament_id)
        for a in range(1,current_pitch_count+1):
            for b in range(a+1,current_pitch_count+1):
                tk=f"travel_{tournament_id}_{a}_{b}"
                minutes=st.number_input(f"Restid {pitch_names.get(a,f'Plan {a}')} → {pitch_names.get(b,f'Plan {b}')} (min)",0,180,int(matrix.get((a,b),0)),key=tk)
                if int(minutes)!=int(matrix.get((a,b),0)):
                    save_pitch_travel_time(tournament_id,a,b,int(minutes))
    windows=ensure_pitch_day_windows(tournament_id,tournament,current_pitch_count,rules["first_match_time"],rules["latest_kickoff_time"])
    valid_windows=True
    by_day={}
    for row in windows: by_day.setdefault(str(row["play_date"]),[]).append(row)
    for play_date,rows in by_day.items():
        d=datetime.fromisoformat(play_date).date()
        st.markdown(f"**{date_with_weekday(d)}**")
        for w in rows:
            pitch=int(w["pitch_number"]); c0,c1,c2=st.columns([0.7,1.15,1.15])
            c0.markdown(f"**{pitch_names.get(pitch, f'Plan {pitch}')}**")
            sk=f"pitch_start_{tournament_id}_{pitch}_{play_date}"; ek=f"pitch_end_{tournament_id}_{pitch}_{play_date}"
            sv=c1.time_input("Starttid",value=datetime.strptime(w["start_time"],"%H:%M").time(),key=sk,label_visibility="collapsed")
            ev=c2.time_input("Sluttid",value=datetime.strptime(w["end_time"],"%H:%M").time(),key=ek,label_visibility="collapsed")
            if sv>=ev:
                valid_windows=False; st.error(f"{date_with_weekday(d)}, {pitch_names.get(pitch, f'Plan {pitch}')}: sluttiden måste vara senare än starttiden.")
            elif sv.strftime("%H:%M")!=w["start_time"] or ev.strftime("%H:%M")!=w["end_time"] or not bool(_row_value(w,"confirmed",0)):
                save_pitch_day_window(tournament_id,pitch,play_date,sv.strftime("%H:%M"),ev.strftime("%H:%M"),True)
                st.session_state[f"autosave_notice_{tournament_id}"]="✓ Plantider sparade automatiskt"

    _capacity_windows=windows
    _capacity_minutes,_capacity_slots=estimated_capacity_slots(
        _capacity_windows,
        rules,
        row_value=_row_value,
    )
    cap1,cap2,cap3=st.columns(3)
    cap1.metric("Spelytor",current_pitch_count)
    cap2.metric("Tillgängliga plantimmar",f"{_capacity_minutes/60:.1f}" if _capacity_minutes else "–")
    cap3.metric("Uppskattade matchslotar",_capacity_slots or "–")

    # v326: the minimum viable setup ends here. Sport-specific defaults already
    # exist for format, rules and priorities, so a new organiser should not be
    # forced through every advanced setup section before registering teams.
    _fast_track_ready = bool(class_rows) and _planned_total > 0 and valid_windows
    with st.container(border=True):
        st.markdown("#### ⚡ Snabbstart")
        if _fast_track_ready:
            st.success("Grunden är klar. Du kan börja lägga in lag nu och finjustera format, regler och prioriteringar senare under Admin → Inställningar.")
        else:
            st.caption("Lägg till minst en tävlingsklass och kontrollera plantiderna för att aktivera snabbstart.")
        if st.button(
            "Fortsätt snabbstart → Lägg till lag",
            type="primary",
            use_container_width=True,
            disabled=not _fast_track_ready,
            key=f"setup_fast_track_to_teams_{tournament_id}",
        ):
            st.session_state.pop("new_tournament_setup_id", None)
            st.session_state.pop("preferred_tournament_id", None)
            st.session_state[f"admin_page_{tournament_id}"] = "Lag"
            st.rerun()
        st.caption("Format, poäng, pauser, prioriteringar och publik statistik kan finjusteras senare under Inställningar.")

    _show_advanced_setup = st.toggle(
        "Visa avancerade inställningar",
        value=False,
        key=f"show_advanced_initial_setup_{tournament_id}",
        help="Öppnar tävlingsformat, matchregler, schemaprioriteringar, service och publik statistik. Detta behövs normalt inte för att komma igång.",
    )
    if _show_advanced_setup:
        st.markdown("### Avancerad setup")
        st.caption("Finjustera endast sådant som avviker från CupNavis standardvärden. Alla inställningar autosparas som tidigare.")
        st.caption("HÅRT KRAV = får aldrig brytas · ÖNSKEMÅL = försöker uppfyllas · OPTIMERING = avgör vilket av flera giltiga scheman som är bäst.")

        st.markdown("### 3. Rekommenderat tävlingsformat")
        st.caption("Nu känner CupNavi till sport, antal lag och faktisk plankapacitet. Därför kan formatförslaget bedömas mot vad som verkligen ryms. Inget ändras förrän du accepterar.")

        # _planned_total reflects the current widget values in this rerun, including
        # any autosaved edits made above. Re-querying competition_classes here would
        # add another DB read without giving fresher UI state.
        _planned_by_class=_planned_total
        _rec_team_count=max(2,_planned_by_class,_actual_team_count)
        _rec_pitch_count=current_pitch_count
        _rec_match_minutes=estimated_match_length_minutes(rules,row_value=_row_value)
        _rec_windows=windows
        _rec_available_minutes=available_pitch_minutes(_rec_windows,row_value=_row_value)
        if not _rec_available_minutes:
            _rec_available_minutes=480

        _format_rec=recommend_tournament_format(
            sport=_row_value(tournament,"sport","Fotboll"),
            team_count=_rec_team_count,
            pitch_count=_rec_pitch_count,
            available_minutes=_rec_available_minutes,
            match_minutes=_rec_match_minutes,
            compactness=int(_row_value(rules,"compactness_level",50) or 50),
        )

        _fmt1,_fmt2,_fmt3,_fmt4=st.columns(4)
        _fmt1.metric("Grupper",_format_rec["group_count"])
        _fmt2.metric("Lag/grupp",_format_rec["group_size"])
        _fmt3.metric("Matcher",_format_rec["total_matches"])
        _fmt4.metric("Slutspelslag",_format_rec["playoff_size"])
        st.markdown(
            f"**Förslag:** {_format_rec['group_count']} grupper · cirka {_format_rec['group_size']} lag per grupp · "
            f"{_format_rec['playoff_format_label']} · cirka {_format_rec['total_matches']} matcher."
        )
        if _format_rec["capacity_matches"]:
            if _format_rec["fits_capacity"]:
                st.success(f"✓ Förslaget ryms inom uppskattad kapacitet: cirka {_format_rec['capacity_matches']} matchslotar.")
            else:
                st.warning(f"Nuvarande kapacitet är cirka {_format_rec['capacity_matches']} matchslotar medan förslaget behöver cirka {_format_rec['total_matches']} matcher. CupNavi rekommenderar mer plantid, fler planer eller ett kompaktare format.")
        if st.button("Använd rekommenderat format",type="primary",use_container_width=True,key=f"accept_format_rec_{tournament_id}"):
            run(
                "UPDATE schedule_rules SET recommended_group_count=?,recommended_group_size=?,recommended_playoff_size=? WHERE tournament_id=?",
                (_format_rec["group_count"],_format_rec["group_size"],_format_rec["playoff_size"],tournament_id),
            )
            st.success("Rekommendationen är sparad och används som hjälp i gruppindelningen. Inga lag eller grupper ändrades automatiskt.")
            rules=one_row("SELECT * FROM schedule_rules WHERE tournament_id=?",(tournament_id,))


        st.markdown("### 4. Tävlingsregler")
        fields=[
            ("Poäng vinst","points_win",int(tournament["points_win"])),
            ("Poäng oavgjort","points_draw",int(tournament["points_draw"])),
            ("Poäng förlust","points_loss",int(tournament["points_loss"])),
        ]
        cols=st.columns(3)
        for col,(label,column,val) in zip(cols,fields):
            k=f"setup_{column}_{tournament_id}"
            col.number_input(label,0,10,val,key=k,on_change=_autosave_tournament_field,args=(tournament_id,column,k,int))
        # Legacy QA anchor: ### 5. Match- och schemaregler
        st.markdown("### 4. Matchregler och hårda begränsningar")
        st.caption(
            f'För {_sport_rec["display_name"]}: {_sport_rec["periods"]} {_sport_rec["period_label"]} är standardprofilen. '
            f'Disciplin: {_sport_rec["discipline_label"]}. Poäng/resultat mäts som {_sport_rec["score_label"]}.'
        )
        r1,r2=st.columns(2)
        hk=f"setup_halves_{tournament_id}"; mk=f"setup_minutes_{tournament_id}"
        r1.number_input("Perioder/halvlekar/set",1,7,int(rules["halves"]),key=hk,on_change=_autosave_rule_field,args=(tournament_id,"halves",hk,int))
        r2.number_input("Minuter per period/halvlek/set",1,120,int(rules["minutes_per_half"]),key=mk,on_change=_autosave_rule_field,args=(tournament_id,"minutes_per_half",mk,int))
        r4,r5,r6=st.columns(3)
        htk=f"setup_halftime_{tournament_id}"; pbk=f"setup_pitchbreak_{tournament_id}"; restk=f"setup_rest_{tournament_id}"
        r4.number_input("Paus mellan perioder",0,60,int(rules["halftime_minutes"]),key=htk,on_change=_autosave_rule_field,args=(tournament_id,"halftime_minutes",htk,int))
        r5.number_input("Paus mellan matcher på plan",0,120,int(rules["pitch_break_minutes"]),key=pbk,on_change=_autosave_rule_field,args=(tournament_id,"pitch_break_minutes",pbk,int))
        r6.number_input("Minsta lagvila",0,300,int(rules["minimum_team_rest_minutes"]),key=restk,on_change=_autosave_rule_field,args=(tournament_id,"minimum_team_rest_minutes",restk,int))

        st.markdown("### 5. Schemaprioriteringar")
        st.caption("Dra målen i den ordning CupNavi ska prioritera dem. Ordningen används bara mellan lösningar som redan uppfyller alla hårda krav.")
        _core_priorities = [
            "Tillgodose lagens startönskemål",
            "Undvik matcher direkt efter varandra",
            "Jämna ut lagens vilotider",
            "Minimera långa håltider",
        ]
        _advanced_priorities = [
            "Jämn belastning mellan planer",
            "Minimera sena gruppmatcher",
        ]
        _default_priorities = _core_priorities + _advanced_priorities
        try:
            _saved_priorities = json.loads(_row_value(rules, "preference_order_json", "") or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            _saved_priorities = []
        _priority_items = normalized_priority_order(_saved_priorities, _default_priorities)
        _core_items=[x for x in _priority_items if x in _core_priorities]
        _advanced_items=[x for x in _priority_items if x in _advanced_priorities]
        st.markdown("**Grundprioriteringar**")
        st.caption("Det här är de fyra val som normalt har störst påverkan på lagens upplevelse.")
        if sort_items is not None:
            _new_core_items = sort_items(
                _core_items,
                direction="vertical",
                custom_style=".sortable-item{background:#fff;color:#172033;border:1px solid #cbd5e1;border-radius:10px;padding:9px 11px;margin:4px 0;font-weight:750;}",
                key=f"setup_priority_core_sort_{tournament_id}",
            )
        else:
            st.info("Drag-and-drop kräver streamlit-sortables. Prioriteringen visas i nuvarande ordning.")
            _new_core_items = _core_items
        with st.expander("Avancerade schemamål", expanded=False):
            st.caption("Dessa mål är relevanta, men behöver normalt inte styra setupen för en vanlig cup.")
            if sort_items is not None:
                _new_advanced_items = sort_items(
                    _advanced_items,
                    direction="vertical",
                    custom_style=".sortable-item{background:#fff;color:#172033;border:1px solid #cbd5e1;border-radius:10px;padding:9px 11px;margin:4px 0;font-weight:750;}",
                    key=f"setup_priority_advanced_sort_{tournament_id}",
                )
            else:
                _new_advanced_items = _advanced_items
        _new_priority_items = list(_new_core_items) + list(_new_advanced_items)
        if priority_order_changed(_new_priority_items, _saved_priorities):
            run(
                "UPDATE schedule_rules SET preference_order_json=? WHERE tournament_id=?",
                (json.dumps(_new_priority_items, ensure_ascii=False), int(tournament_id)),
            )
            rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),))

        _compact_key=f"setup_compactness_{tournament_id}"
        _compactness=st.slider(
            "Turneringens tempo",
            0,100,int(_row_value(rules,"compactness_level",50) or 50),
            key=_compact_key,
            help="0 = luftigare schema och mer marginal. 100 = komprimera cupen och bli klar så tidigt som möjligt."
        )
        st.caption("Luftigt schema ←  turneringens tempo  → Kompakt / tidigt avslut")
        if int(_compactness)!=int(_row_value(rules,"compactness_level",50) or 50):
            run("UPDATE schedule_rules SET compactness_level=?,schedule_strategy=? WHERE tournament_id=?",
                (int(_compactness), "earliest_finish" if int(_compactness)>=50 else "use_pitch_windows", int(tournament_id)))
            rules=one_row("SELECT * FROM schedule_rules WHERE tournament_id=?",(int(tournament_id),))

        st.markdown("**Prioritera inkomna lagönskemål**")
        _request_teams = all_rows(
            "SELECT id,name,late_first_match,earliest_first_time,avoid_late_group_match,request_priority FROM teams "
            "WHERE tournament_id=? AND (late_first_match=1 OR avoid_late_group_match=1) ORDER BY request_priority,name",
            (int(tournament_id),),
        )
        if not _request_teams:
            st.caption("Inga lagönskemål finns ännu. De kan registreras under Admin → Lag eller av laget via Lagportalen.")
        else:
            _request_labels = [
                f"{row['name']} · " +
                (f"helst första match efter {row['earliest_first_time']}" if row['late_first_match'] and row['earliest_first_time'] else "undvik sen gruppmatch")
                for row in _request_teams
            ]
            if sort_items is not None:
                _sorted_requests = sort_items(
                    _request_labels, direction="vertical",
                    custom_style=".sortable-item{background:#fff;color:#172033;border:1px solid #cbd5e1;border-radius:10px;padding:9px 11px;margin:4px 0;}",
                    key=f"setup_request_sort_{tournament_id}",
                )
                if _sorted_requests:
                    _label_to_row={label:row for label,row in zip(_request_labels,_request_teams)}
                    _request_priority_updates=[]
                    for pos,label in enumerate(_sorted_requests, start=1):
                        row=_label_to_row[label]
                        if int(_row_value(row,"request_priority",0) or 0) != pos:
                            _request_priority_updates.append((pos,int(row["id"])))
                    if _request_priority_updates:
                        with db() as con:
                            con.executemany(
                                "UPDATE teams SET request_priority=? WHERE id=?",
                                _request_priority_updates,
                            )
                            con.commit()
                        _clear_render_query_cache()
            st.caption("Överst = viktigast om flera önskemål konkurrerar om samma tider.")

        # Service-/arrangemangsval påverkar inte formatmotorn och kommer därför sent i setupen.
        st.markdown("### 6. Arrangemang & deltagarservice")
        st.caption("Dessa val påverkar deltagarupplevelsen och publik information, men inte hur CupNavi räknar ut tävlingsformatet.")
        svc1,svc2=st.columns(2)
        checkin_key=f"setup_team_checkin_{tournament_id}"
        svc1.checkbox(
            "Använd lagincheckning",
            value=bool(_row_value(tournament,"enable_team_checkin",0)),
            key=checkin_key,
            on_change=_autosave_tournament_field,
            args=(tournament_id,"enable_team_checkin",checkin_key,lambda v:1 if v else 0),
            help="Lagledare/Admin kan markera laget på plats. Detta är en driftfunktion, inte en schemaregel.",
        )
        ranking_key=f"setup_final_ranking_{tournament_id}"
        svc2.checkbox(
            "Skapa slutlig ranking av alla lag",
            value=bool(_row_value(tournament,"enable_final_ranking",0)),
            key=ranking_key,
            on_change=_autosave_tournament_field,
            args=(tournament_id,"enable_final_ranking",ranking_key,lambda v:1 if v else 0),
        )
        cr_toggle=f"setup_changing_rooms_{tournament_id}"
        changing_rooms_enabled=st.checkbox(
            "Tillgång till omklädningsrum",
            value=bool(_row_value(tournament,"changing_rooms_available",0)),
            key=cr_toggle,
            on_change=_autosave_tournament_field,
            args=(tournament_id,"changing_rooms_available",cr_toggle,lambda v:1 if v else 0),
        )
        if changing_rooms_enabled:
            cr_key=f"setup_changing_info_{tournament_id}"
            st.text_area(
                "Information om omklädningsrum",
                value=_row_value(tournament,"changing_room_info","") or "",
                key=cr_key,
                placeholder="Exempel: 4 omklädningsrum i huvudbyggnaden. Nycklar hämtas i sekretariatet.",
                on_change=_autosave_tournament_field,
                args=(tournament_id,"changing_room_info",cr_key),
            )

        pshow=f"setup_show_prices_{tournament_id}"
        show_prices_enabled=st.checkbox(
            "Visa priser/avgifter publikt",
            value=bool(_row_value(tournament,"show_price_information",0)),
            key=pshow,
            on_change=_autosave_tournament_field,
            args=(tournament_id,"show_price_information",pshow,lambda v:1 if v else 0),
        )
        if show_prices_enabled:
            pkey=f"setup_price_info_{tournament_id}"
            st.text_area(
                "Priser/avgifter",
                value=_row_value(tournament,"price_information","") or "",
                key=pkey,
                placeholder="Exempel: Lagavgift 1 500 SEK. Matchcamp 250 SEK/spelare.",
                on_change=_autosave_tournament_field,
                args=(tournament_id,"price_information",pkey),
            )


        st.markdown("### 7. Kontroll & skapa")
        st.caption("Kontrollera kapacitet, regler och ändringsbarhet innan du lämnar setupen. CupNavi visar vad som kan ändras senare och vad som låses efter start.")
        _editability = pd.DataFrame([
            {"Parameter":"Namn, kontakt, publik information","Utkast":"✓","Publicerad":"✓","Startad":"✓"},
            {"Parameter":"Domare och funktionärer","Utkast":"✓","Publicerad":"✓","Startad":"✓ framtida matcher"},
            {"Parameter":"Plan/tid för framtida match","Utkast":"✓","Publicerad":"✓","Startad":"⚠ kontroll"},
            {"Parameter":"Plantider och schemaprioriteringar","Utkast":"✓","Publicerad":"⚠ omplanering","Startad":"⚠ endast framtida"},
            {"Parameter":"Lag och gruppindelning","Utkast":"✓","Publicerad":"⚠ omplanering","Startad":"🔒"},
            {"Parameter":"Matchtid, poängsystem, tävlingsformat","Utkast":"✓","Publicerad":"⚠ omplanering","Startad":"🔒 efter första resultat"},
            {"Parameter":"Sport, region, tidszon","Utkast":"🔒 grundval","Publicerad":"🔒","Startad":"🔒"},
        ])
        render_centered_table(_editability)

        st.markdown("### Publik statistik och drift")
        f1,f2,f3,f4=st.columns(4)
        for col,label,column,default in [
            (f1,"Skytteliga","enable_scorer_leaderboard",1),(f2,"Assistliga","enable_assist_leaderboard",1),
            (f3,"Gula/röda kort","enable_card_statistics",1),(f4,"Control Center","enable_control_center",0)]:
            k=f"setup_{column}_{tournament_id}"
            col.checkbox(label,value=bool(_row_value(tournament,column,default)),key=k,on_change=_autosave_tournament_field,args=(tournament_id,column,k,lambda v:1 if v else 0))
    notice=st.session_state.pop(f"autosave_notice_{tournament_id}",None)
    if notice: st.success(notice)
    st.caption("Vanliga inställningar autosparas. Endast åtgärder som publicering, schemagenerering och radering kräver fortfarande ett aktivt knapptryck.")
    if st.button("Fortsätt till Admin", type="primary", use_container_width=True, disabled=not valid_windows):
        st.session_state.pop("new_tournament_setup_id", None)
        st.session_state.pop("preferred_tournament_id", None)
        st.session_state[f"admin_page_{tournament_id}"] = "Adminöversikt"
        st.rerun()