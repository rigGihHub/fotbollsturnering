from __future__ import annotations

from datetime import datetime
from urllib.parse import quote_plus

from cupnavi_core.arrangement_type import (
    ARRANGEMENT_MATCHCAMP, ARRANGEMENT_TOURNAMENT, arrangement_label, arrangement_setup_copy, normalize_arrangement_type,
)
from cupnavi_core.initial_setup_logic import available_pitch_minutes, estimated_match_length_minutes, setup_consequence_preview
from cupnavi_core.setup_recommendation import recommend_matchcamp_matches_per_team

def render_new_tournament_wizard(tournament_id, tournament, *, deps):
    """Focused first-run wizard: one decision area at a time, then handoff to teams."""
    st = deps.st
    one_row = deps.one_row
    run = deps.run
    _row_value = deps.row_value
    add_competition_class = deps.add_competition_class
    competition_classes = deps.competition_classes
    competition_class_label = deps.competition_class_label
    sync_expected_team_count_from_classes = deps.sync_expected_team_count_from_classes
    remove_competition_class = deps.remove_competition_class
    _autosave_rule_field = deps.autosave_rule_field
    ensure_pitch_definitions = deps.ensure_pitch_definitions
    save_pitch_name = deps.save_pitch_name
    save_pitch_address = deps.save_pitch_address
    ensure_pitch_day_windows = deps.ensure_pitch_day_windows
    save_pitch_day_window = deps.save_pitch_day_window
    recommend_tournament_format = deps.recommend_tournament_format
    all_rows = deps.all_rows
    calculate_pitch_travel_times = deps.calculate_pitch_travel_times
    date_with_weekday = deps.date_with_weekday
    YOUTH_CLASS_CATEGORIES = deps.youth_class_categories
    YOUTH_CLASS_YEARS = deps.youth_class_years
    DIFFICULTY_LEVELS = deps.difficulty_levels

    rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
    if rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tournament_id,))
        rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

    step_key = f"new_tournament_wizard_step_{tournament_id}"
    step = int(st.session_state.get(step_key, 1) or 1)
    step = max(1, min(5, step))
    st.session_state[step_key] = step

    labels = ["Typ", "Deltagare", "Planer & tider", "Upplägg", "Klart"]
    progress_html = "".join(
        f'<div class="cn-setup-step {"done" if i < step else "active" if i == step else ""}"><strong>{"✓" if i < step else i}</strong>{label}</div>'
        for i, label in enumerate(labels, start=1)
    )
    st.markdown(
        f"""
        <div class="cn-setup-hero">
          <div class="cn-setup-eyebrow">Ny turnering · interaktiv guide</div>
          <div class="cn-setup-title">{tournament['name']}</div>
          <p class="cn-setup-copy">En sak i taget. CupNavi sparar dina val och visar nästa steg först när det behövs.</p>
          <div class="cn-setup-progress-grid">{progress_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(step / 5, text=f"Steg {step} av 5 · {labels[step-1]}")

    def _set_wizard_step(target_step: int) -> None:
        # v441: callbacks run before Streamlit's normal widget rerun, so pure
        # navigation needs one render instead of button render + explicit rerun.
        st.session_state[step_key] = max(1, min(5, int(target_step)))

    def nav(*, can_next=True, next_label="Fortsätt", back=True):
        left, right = st.columns(2)
        if back:
            left.button(
                "← Föregående",
                use_container_width=True,
                key=f"wizard_back_{tournament_id}_{step}",
                on_click=_set_wizard_step,
                args=(step - 1,),
            )
        right.button(
            next_label,
            type="primary",
            use_container_width=True,
            disabled=not can_next,
            key=f"wizard_next_{tournament_id}_{step}",
            on_click=_set_wizard_step,
            args=(step + 1,),
        )

    arrangement_type = normalize_arrangement_type(_row_value(tournament, "arrangement_type", "tournament"))

    if step == 1:
        st.markdown("### Vad ska ni arrangera?")
        st.caption("Det här styr vilka funktioner CupNavi använder. Du behöver inte kunna regler eller format i förväg.")
        choice = st.radio(
            "Arrangemangstyp",
            [ARRANGEMENT_MATCHCAMP, ARRANGEMENT_TOURNAMENT],
            index=0 if arrangement_type == ARRANGEMENT_MATCHCAMP else 1,
            horizontal=True,
            format_func=arrangement_label,
            key=f"wizard_arrangement_{tournament_id}",
        )
        copy = arrangement_setup_copy(choice)
        st.info(copy["goal"])
        if choice != arrangement_type:
            if choice == ARRANGEMENT_MATCHCAMP:
                run("UPDATE tournaments SET arrangement_type='matchcamp',results_counted=0,playoff_format='Inget slutspel',playoff_model_confirmed=1,schedule_dirty=1 WHERE id=?", (tournament_id,))
            else:
                run("UPDATE tournaments SET arrangement_type='tournament',schedule_dirty=1 WHERE id=?", (tournament_id,))
            arrangement_type = choice
        is_matchcamp = choice == ARRANGEMENT_MATCHCAMP
        saved_results = bool(_row_value(tournament, "results_counted", 1))
        saved_playoff = str(_row_value(tournament, "playoff_format", "Inget slutspel") or "Inget slutspel")
        result_options = (
            ["Utan resultat", "Registrera resultat"]
            if is_matchcamp
            else [
                "Resultat, tabell och placeringar",
                "Spela utan resultaträkning",
                "Spela utan resultat · skapa slutspel manuellt",
            ]
        )
        if is_matchcamp:
            current_index = 1 if saved_results else 0
        elif saved_results:
            current_index = 0
        elif saved_playoff == "Manuellt slutspel":
            current_index = 2
        else:
            current_index = 1
        mode = st.radio("Ska resultat registreras?", result_options, index=current_index, key=f"wizard_results_{tournament_id}")
        results_now = mode == "Registrera resultat" if is_matchcamp else mode == "Resultat, tabell och placeringar"
        manual_playoff_now = (not is_matchcamp) and mode == "Spela utan resultat · skapa slutspel manuellt"
        desired_playoff = (
            "Inget slutspel"
            if is_matchcamp or (not results_now and not manual_playoff_now)
            else ("Manuellt slutspel" if manual_playoff_now else saved_playoff)
        )
        desired_confirmed = 1 if (is_matchcamp or not results_now) else int(_row_value(tournament,"playoff_model_confirmed",0))
        if results_now != saved_results or desired_playoff != saved_playoff:
            run("UPDATE tournaments SET results_counted=?,playoff_format=?,playoff_model_confirmed=?,schedule_dirty=1 WHERE id=?",
                (1 if results_now else 0, desired_playoff, desired_confirmed, tournament_id))
        nav(back=False)
        return

    class_rows = competition_classes(tournament_id)
    team_count_rows = all_rows("SELECT competition_class_id,COUNT(*) AS n FROM teams WHERE tournament_id=? GROUP BY competition_class_id", (tournament_id,))
    team_count_by_class = {_row_value(r,"competition_class_id",None): int(_row_value(r,"n",0) or 0) for r in team_count_rows}

    if step == 2:
        st.markdown("### Vilka ska spela?")
        st.caption("Lägg in en eller flera klasser. CupNavi använder planerat antal lag för att föreslå ett rimligt upplägg.")
        with st.container(border=True):
            category = st.selectbox("Vilka spelar?", list(YOUTH_CLASS_CATEGORIES), key=f"wizard_category_{tournament_id}")
            year = st.selectbox("Födelseår", YOUTH_CLASS_YEARS, index=YOUTH_CLASS_YEARS.index(2014) if 2014 in YOUTH_CLASS_YEARS else 0, key=f"wizard_year_{tournament_id}")
            difficulty = st.selectbox("Nivå", DIFFICULTY_LEVELS, index=DIFFICULTY_LEVELS.index("Medel") if "Medel" in DIFFICULTY_LEVELS else 0, key=f"wizard_diff_{tournament_id}")
            planned = st.number_input("Ungefär hur många lag?", 2, 200, 8, key=f"wizard_planned_{tournament_id}")
            if st.button("Lägg till klassen", use_container_width=True, key=f"wizard_add_class_{tournament_id}"):
                ok, message = add_competition_class(tournament_id, category, year, planned, difficulty)
                (st.success if ok else st.info)(message)
                st.rerun()
        class_rows = competition_classes(tournament_id)
        planned_total = 0
        for row in class_rows:
            actual = int(team_count_by_class.get(int(row["id"]), 0))
            saved = max(actual, int(_row_value(row,"planned_team_count",0) or 0), 2)
            planned_total += int(saved)
            with st.container(border=True):
                st.markdown(f"**{competition_class_label(row)}** · {saved} planerade lag")
                st.caption(f"{actual} lag är registrerade hittills." if actual else "Lagantalet sparades när klassen lades till.")
                _edit_key = f"wizard_edit_class_count_{row['id']}"
                if st.button("Ändra lagantal", key=f"wizard_toggle_class_count_{row['id']}"):
                    st.session_state[_edit_key] = not bool(st.session_state.get(_edit_key, False))
                if st.session_state.get(_edit_key, False):
                    n = st.number_input(
                        "Nytt planerat lagantal",
                        min_value=max(2,actual),
                        max_value=200,
                        value=int(saved),
                        key=f"wizard_class_count_{row['id']}",
                    )
                    if int(n) != int(_row_value(row,"planned_team_count",0) or 0):
                        run("UPDATE competition_classes SET planned_team_count=? WHERE id=?", (int(n), int(row["id"])))
                        sync_expected_team_count_from_classes(tournament_id)
                        st.rerun()
                if st.button("Ta bort", key=f"wizard_remove_class_{row['id']}"):
                    ok, message = remove_competition_class(tournament_id, int(row["id"]))
                    (st.success if ok else st.error)(message)
                    if ok: st.rerun()
        if class_rows:
            st.caption(f"Planerat totalt: **{planned_total} lag**")
        else:
            st.warning("Lägg till minst en klass för att fortsätta.")
        nav(can_next=bool(class_rows))
        return

    planned_total = sum(max(2, int(_row_value(r,"planned_team_count",0) or 0)) for r in class_rows)

    if step == 3:
        st.markdown("### Vilka planer och tider har ni?")
        st.caption("Ange bara det som faktiskt begränsar schemat: antal planer och när de kan användas.")
        pitch_key = f"wizard_pitch_count_{tournament_id}"
        st.number_input("Antal planer/spelytor", 1, 50, int(rules["pitch_count"]), key=pitch_key,
                        on_change=_autosave_rule_field, args=(tournament_id,"pitch_count",pitch_key,int))
        pitch_count = int(st.session_state.get(pitch_key, rules["pitch_count"]))

        # v416: planstorlek/spelform är grundläggande cupinformation, inte en
        # avancerad schemaregel. Fråga efter den tillsammans med planer och tider.
        _pitch_size_saved = str(_row_value(rules, "pitch_size_format", "") or "").strip()
        _pitch_size_options = ["Välj planstorlek", "5-manna", "7-manna", "9-manna", "11-manna"]
        _pitch_size_index = _pitch_size_options.index(_pitch_size_saved) if _pitch_size_saved in _pitch_size_options else 0
        _pitch_size = st.selectbox(
            "Planstorlek / spelform",
            _pitch_size_options,
            index=_pitch_size_index,
            key=f"wizard_pitch_size_{tournament_id}",
            help="Visas i cupinformationen så att lag och besökare direkt ser vilken spelform som gäller.",
        )
        if _pitch_size != "Välj planstorlek" and _pitch_size != _pitch_size_saved:
            run(
                "UPDATE schedule_rules SET pitch_size_format=? WHERE tournament_id=?",
                (_pitch_size, int(tournament_id)),
            )
            rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),))

        if pitch_count > 1:
            st.markdown("**Hur ska matchtiderna fördelas mellan planerna?**")
            _current_sync = bool(_row_value(rules, "synchronized_pitch_times", 0))
            _timing_options = [
                "Dynamiskt – varje plan använder nästa möjliga tid",
                "Synkroniserat – samma avsparkstider på alla planer",
            ]
            _timing_mode = st.radio(
                "Tidsupplägg för flera planer",
                _timing_options,
                index=1 if _current_sync else 0,
                key=f"wizard_pitch_timing_mode_{tournament_id}",
                label_visibility="collapsed",
                help="Dynamiskt ger CupNavi större frihet att utnyttja plantiden. Synkroniserat skapar gemensamma startvågor på alla planer.",
            )
            _new_sync = _timing_mode.startswith("Synkroniserat")
            if _new_sync != _current_sync:
                run(
                    "UPDATE schedule_rules SET synchronized_pitch_times=? WHERE tournament_id=?",
                    (int(_new_sync), int(tournament_id)),
                )
                rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),))
            if _new_sync:
                st.caption("Alla planer följer gemensamma startvågor, exempelvis 09:00, 09:45 och 10:30. Enklare att kommunicera, men kan lämna viss plantid oanvänd.")
            else:
                st.caption("Varje plan kan starta nästa match så snart regler, vila och plantid tillåter. Ger normalt bättre kapacitetsutnyttjande.")

        pitches = ensure_pitch_definitions(tournament_id, pitch_count)
        unverified = 0
        for pr in pitches:
            pitch = int(pr["pitch_number"])
            saved_name = str(pr["name"] or f"Plan {pitch}")
            name = st.text_input(f"Namn på plan {pitch}", value=saved_name, key=f"wizard_pitch_name_{tournament_id}_{pitch}")
            clean = (name or "").strip() or f"Plan {pitch}"
            if clean != saved_name:
                save_pitch_name(tournament_id, pitch, clean)
            saved_address = str(_row_value(pr,"address","") or "")
            address = st.text_input(f"Adress – {clean}", value=saved_address, key=f"wizard_pitch_address_{tournament_id}_{pitch}", placeholder="Exempel: Rudbecksgatan 52, Örebro")
            if address.strip() != saved_address.strip():
                save_pitch_address(tournament_id, pitch, address)
                run("UPDATE pitches SET address_verified=0 WHERE tournament_id=? AND pitch_number=?", (tournament_id,pitch))
            verified = bool(_row_value(pr,"address_verified",0)) and address.strip() == saved_address.strip()
            if address.strip():
                st.link_button("Kontrollera adress i Google Maps ↗", f"https://www.google.com/maps/search/?api=1&query={quote_plus(address.strip())}", use_container_width=True)
                checked = st.checkbox("Adressen pekar på rätt spelplats", value=verified, key=f"wizard_verified_{tournament_id}_{pitch}")
                if checked != verified:
                    run("UPDATE pitches SET address_verified=? WHERE tournament_id=? AND pitch_number=?", (1 if checked else 0,tournament_id,pitch))
                if not checked: unverified += 1
        if pitch_count > 1:
            st.markdown("**Restid mellan planer**")
            _travel_saved=bool(_row_value(rules,"consider_pitch_travel",0))
            _travel_on=st.checkbox("Ta hänsyn till restid mellan planerna",value=_travel_saved,key=f"wizard_consider_travel_{tournament_id}",help="CupNavi beräknar faktisk körtid från verifierade planadresser och lägger på din marginal.")
            if _travel_on != _travel_saved:
                run("UPDATE schedule_rules SET consider_pitch_travel=? WHERE tournament_id=?",(1 if _travel_on else 0,int(tournament_id)))
            if _travel_on:
                _saved_buffer=int(_row_value(rules,"pitch_travel_buffer_minutes",10) or 0)
                _buffer=st.number_input("Extra tid utöver den faktiska restiden",0,60,_saved_buffer,key=f"wizard_travel_buffer_{tournament_id}",help="Exempel: 12 min körtid + 8 min marginal = minst 20 min mellan planerna.")
                if int(_buffer)!=_saved_buffer:
                    run("UPDATE schedule_rules SET pitch_travel_buffer_minutes=? WHERE tournament_id=?",(int(_buffer),int(tournament_id)))
                st.caption("Du anger bara marginalen. CupNavi räknar själva körtiden mellan de verifierade adresserna.")
                if st.button("Beräkna restider med CupNavi",use_container_width=True,key=f"wizard_calc_travel_{tournament_id}"):
                    _ok,_message,_rows=calculate_pitch_travel_times(tournament_id,int(_buffer))
                    (st.success if _ok else st.warning)(_message)
                    for _row in _rows:
                        st.caption(f"{_row['from']} → {_row['to']}: {_row['route_minutes']} min + {_row['buffer_minutes']} min marginal = {_row['total_minutes']} min")

        st.markdown("**När är planerna tillgängliga?**")
        st.caption("Ange tidsfönstret då CupNavi får lägga matcher på varje plan. Starttiden är den första möjliga matchstarten. Sluttiden är när planen slutar vara tillgänglig – CupNavi lägger därför ingen match som pågår efter den tiden.")
        windows = ensure_pitch_day_windows(tournament_id, tournament, pitch_count, rules["first_match_time"], rules["latest_kickoff_time"])
        valid = True
        by_day = {}
        for row in windows: by_day.setdefault(str(row["play_date"]), []).append(row)
        for play_date, rows in by_day.items():
            d = datetime.fromisoformat(play_date).date()
            st.markdown(f"**{date_with_weekday(d)}**")
            for w in rows:
                pitch = int(w["pitch_number"])
                c1,c2 = st.columns(2)
                sv = c1.time_input(f"Första möjliga matchstart · plan {pitch}", value=datetime.strptime(w["start_time"],"%H:%M").time(), key=f"wizard_start_{tournament_id}_{pitch}_{play_date}")
                ev = c2.time_input(f"Planen tillgänglig till · plan {pitch}", value=datetime.strptime(w["end_time"],"%H:%M").time(), key=f"wizard_end_{tournament_id}_{pitch}_{play_date}")
                if sv >= ev:
                    valid = False
                    st.error("Sluttiden måste vara senare än starttiden.")
                elif sv.strftime("%H:%M") != w["start_time"] or ev.strftime("%H:%M") != w["end_time"] or not bool(_row_value(w,"confirmed",0)):
                    save_pitch_day_window(tournament_id,pitch,play_date,sv.strftime("%H:%M"),ev.strftime("%H:%M"),True)
        if unverified:
            st.warning(f"{unverified} adress(er) behöver verifieras innan du fortsätter.")
        nav(can_next=valid and unverified == 0 and _pitch_size != "Välj planstorlek")
        return

    pitch_count = int(_row_value(rules,"pitch_count",1) or 1)
    windows = ensure_pitch_day_windows(tournament_id, tournament, pitch_count, rules["first_match_time"], rules["latest_kickoff_time"])

    if step == 4:
        st.markdown("### Bestäm upplägget")
        st.caption("Du väljer hur cupen ska spelas. CupNavi kan ge ett snabbförslag, men det är alltid frivilligt.")

        if arrangement_type != ARRANGEMENT_MATCHCAMP:
            manual_col, assist_col = st.columns(2)
            with manual_col:
                st.markdown("**Ställ in själv**")
                st.caption("För dig som vill bestämma gruppformat, poäng, matchtid, pauser, vila, slutspel och schemaprioriteringar själv.")
                if st.button(
                    "Ställ in regler och upplägg själv",
                    type="primary",
                    use_container_width=True,
                    key=f"wizard_manual_setup_{tournament_id}",
                ):
                    st.session_state["new_tournament_setup_mode"] = "rules"
                    st.session_state["new_tournament_setup_id"] = int(tournament_id)
                    st.session_state["preferred_tournament_id"] = int(tournament_id)
                    st.rerun()
            with assist_col:
                st.markdown("**Låt CupNavi föreslå**")
                st.caption("Ett snabbspår om du vill få ett rimligt grundupplägg utifrån lag, planer och tillgänglig tid.")
                if st.button("Visa CupNavis förslag",use_container_width=True,key=f"wizard_show_rec_{tournament_id}"):
                    st.session_state[f"wizard_rec_visible_{tournament_id}"]=True
                    st.rerun()

        available = available_pitch_minutes(windows, row_value=_row_value) or 480
        match_minutes = estimated_match_length_minutes(rules, row_value=_row_value)

        if arrangement_type == ARRANGEMENT_MATCHCAMP:
            st.caption("För en matchcamp fokuserar CupNavi på jämnt antal matcher, rimlig vila och att plantiden räcker. Grupper och slutspel behövs inte.")
            recommendation = recommend_matchcamp_matches_per_team(
                team_count=max(2, planned_total), available_minutes=available, match_minutes=match_minutes
            )
            match_key = f"wizard_matchcamp_target_{tournament_id}"
            saved_target = int(_row_value(rules,"matchcamp_matches_per_team",4) or 4)
            if st.button(f"Sätt {recommendation['matches_per_team']} matcher per lag", type="primary", use_container_width=True, key=f"wizard_matchcamp_accept_{tournament_id}"):
                run("UPDATE schedule_rules SET matchcamp_matches_per_team=? WHERE tournament_id=?", (int(recommendation["matches_per_team"]), tournament_id))
                st.session_state[match_key] = int(recommendation["matches_per_team"])
                st.rerun()
            matches_per_team = st.number_input(
                "Hur många matcher ska varje lag få?", 1, 12, saved_target,
                key=match_key, on_change=_autosave_rule_field,
                args=(tournament_id,"matchcamp_matches_per_team",match_key,int),
                help="Du kan ändra CupNavis förslag om ni vill prioritera fler matcher framför större tidsmarginal.",
            )
            estimated_matches = max(1, (max(2, planned_total) * int(matches_per_team) + 1) // 2)
            required_minutes = estimated_matches * match_minutes
            capacity_percent = int(round((required_minutes / available) * 100)) if available else 999
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Lag", planned_total)
            c2.metric("Matcher/lag", int(matches_per_team))
            c3.metric("Cirka matcher", estimated_matches)
            c4.metric("Plantid används", f"{capacity_percent}%")
            if required_minutes <= available:
                spare = available - required_minutes
                st.success(f"✓ Upplägget ryms i plantiden. Ungefär {spare} planminuter finns kvar som marginal för vila, luckor och justeringar.")
            else:
                shortage = required_minutes - available
                st.warning(f"Upplägget behöver ungefär {shortage} fler planminuter. Minska matcher per lag, lägg till plantid eller använd fler planer.")
            st.info("CupNavi skapar senare själva matchcamp-schemat och försöker ge lagen jämnt motstånd, jämn speltid och bra vila.")
        else:
            if not st.session_state.get(f"wizard_rec_visible_{tournament_id}",False):
                st.info("Välj **Ställ in regler och upplägg själv** eller **Visa CupNavis förslag** ovan.")
                nav(next_label="Kontrollera setupen")
                return
            st.caption("CupNavis frivilliga snabbförslag")
            rec = recommend_tournament_format(
                sport=_row_value(tournament,"sport","Fotboll"), team_count=max(2,planned_total), pitch_count=pitch_count,
                available_minutes=available, match_minutes=match_minutes, compactness=int(_row_value(rules,"compactness_level",50) or 50),
            )
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Grupper", rec["group_count"])
            c2.metric("Lag/grupp", rec["group_size"])
            c3.metric("Matcher", rec["total_matches"])
            c4.metric("Slutspelslag", rec["playoff_size"])
            st.markdown(f"**CupNavi rekommenderar:** {rec['group_count']} grupper · cirka {rec['group_size']} lag per grupp · {rec['playoff_format_label']}.")
            if rec.get("fits_capacity"):
                st.success("✓ Förslaget ryms inom den plantid du har angett.")
            else:
                st.warning("Förslaget ser trångt ut med nuvarande plantid. Du kan ändå fortsätta och justera efter att lagen är inlagda.")
            if st.button("Använd CupNavis snabbförslag", use_container_width=True, key=f"wizard_accept_rec_{tournament_id}"):
                run("UPDATE schedule_rules SET recommended_group_count=?,recommended_group_size=?,recommended_playoff_size=? WHERE tournament_id=?",
                    (rec["group_count"],rec["group_size"],rec["playoff_size"],tournament_id))
                st.session_state[f"wizard_rec_accepted_{tournament_id}"] = True
                st.success("Förslaget är sparat.")
            st.caption("Vill du styra detaljerna själv använder du den fullständiga setupen ovan. CupNavi ändrar inget förrän du väljer att använda snabbförslaget.")

        nav(next_label="Kontrollera setupen")
        return

    # Step 5
    st.markdown("### Klart att lägga till lag")
    st.caption("Här ser du vad du har valt innan du går vidare. CupNavi kontrollerar bara sådant som faktiskt behövs för nästa steg.")
    summary_type = arrangement_label(arrangement_type)
    _summary_playoff = str(_row_value(tournament, "playoff_format", "Inget slutspel") or "Inget slutspel")
    summary_results = (
        "Resultat registreras"
        if bool(_row_value(tournament, "results_counted", 1))
        else ("Utan gruppresultat · manuellt slutspel" if _summary_playoff == "Manuellt slutspel" else "Utan resultaträkning")
    )
    _timing_summary = "synkroniserade avsparkstider" if bool(_row_value(rules, "synchronized_pitch_times", 0)) else "dynamiska plantider"
    _pitch_size_summary = str(_row_value(rules, "pitch_size_format", "") or "").strip()
    _pitch_size_part = f" · **{_pitch_size_summary}**" if _pitch_size_summary else ""
    st.markdown(f"**{summary_type}** · {summary_results} · cirka **{planned_total} lag** · **{pitch_count} plan(er)**{_pitch_size_part} · **{_timing_summary}**")

    # v396: the consequence preview now lives in the actual first-run wizard,
    # not only in the later full setup editor. Reuse the already loaded rules
    # and pitch windows so the final check stays lightweight.
    available = available_pitch_minutes(windows, row_value=_row_value) or 0
    match_minutes = estimated_match_length_minutes(rules, row_value=_row_value)
    if arrangement_type == ARRANGEMENT_MATCHCAMP:
        matches_per_team = int(_row_value(rules, "matchcamp_matches_per_team", 4) or 4)
        unique_target = max(1, min(matches_per_team, max(1, planned_total - 1)))
        total_matches = (max(2, planned_total) * unique_target + 1) // 2
    else:
        rec = recommend_tournament_format(
            sport=_row_value(tournament, "sport", "Fotboll"),
            team_count=max(2, planned_total),
            pitch_count=pitch_count,
            available_minutes=available or 480,
            match_minutes=match_minutes,
            compactness=int(_row_value(rules, "compactness_level", 50) or 50),
        )
        total_matches = int(rec.get("total_matches", 0) or 0)

    preview = setup_consequence_preview(
        team_count=planned_total,
        total_matches=total_matches,
        match_minutes=match_minutes,
        available_minutes=available,
    )
    preview_hours, preview_mins = divmod(preview["pitch_time_minutes"], 60)
    preview_time = (
        f"{preview_hours} h {preview_mins} min" if preview_hours and preview_mins
        else f"{preview_hours} h" if preview_hours
        else f"{preview_mins} min"
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lag", preview["team_count"])
    m2.metric("Planer", pitch_count)
    m3.metric("Cirka matcher", preview["total_matches"] or "–")
    m4.metric("Matchtid på plan", preview_time if preview["total_matches"] else "–")
    if preview["utilization_percent"] is not None and preview["total_matches"]:
        margin_text = f"{preview['margin_label']} · cirka {preview['utilization_percent']} % av plantiden används av matcherna."
        if preview["margin_tone"] == "over":
            st.error(margin_text + " Gå tillbaka till Planer & tider eller Upplägg innan du fortsätter.")
        elif preview["margin_tone"] == "tight":
            st.warning(margin_text + " Det finns liten marginal för vila, förseningar och schemajusteringar.")
        else:
            st.success(margin_text)
    st.caption("Detta är en kapacitetskontroll, inte det färdiga schemat. Exakta tider bestäms när CupNavi bygger schemat.")

    pitch_rows = ensure_pitch_definitions(tournament_id, pitch_count)
    address_ok = all(not str(_row_value(r,"address","") or "").strip() or bool(_row_value(r,"address_verified",0)) for r in pitch_rows)
    checks = [
        (bool(class_rows), "Deltagare", f"{len(class_rows)} klass(er) planerade"),
        (planned_total > 0, "Lagantal", f"cirka {planned_total} lag totalt"),
        (bool(windows), "Planer och tider", f"{pitch_count} plan(er) med speltider"),
        (address_ok, "Planadresser", "ifyllda adresser är verifierade"),
    ]
    for ok, label, text in checks:
        st.markdown(f"{'✓' if ok else '⚠️'} **{label}** · {text}")
    capacity_ok = preview["margin_tone"] != "over"
    if not capacity_ok:
        checks.append((False, "Kapacitet", "upplägget behöver mer plantid eller färre matcher"))
    ready = all(ok for ok,_,_ in checks)
    if ready:
        st.success("Grundsetupen är klar. Nästa steg är att lägga till lagen.")
    else:
        st.warning("Något behöver kompletteras. Gå tillbaka till steget som är markerat ovan.")
    left,right = st.columns(2)
    if left.button("← Föregående", use_container_width=True, key=f"wizard_back_{tournament_id}_5"):
        st.session_state[step_key] = 4
        st.rerun()
    if right.button("Fortsätt → Lägg till lag", type="primary", use_container_width=True, disabled=not ready, key=f"wizard_finish_{tournament_id}"):
        st.session_state.pop("new_tournament_setup_id", None)
        st.session_state.pop("preferred_tournament_id", None)
        st.session_state.pop("new_tournament_setup_mode", None)
        st.session_state[f"admin_page_{tournament_id}"] = "Lag"
        st.rerun()
    st.caption("Efter Lag hjälper CupNavi dig vidare till grupper, schema, kontroll och publicering.")


