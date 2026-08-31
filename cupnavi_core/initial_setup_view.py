from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from urllib.parse import quote_plus
from typing import Any, Callable


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
    _setup_environment = str(_row_value(tournament, "environment_type", "test") or "test")
    _setup_environment_label = "🧪 Testmiljö" if _setup_environment == "test" else "● Riktig cup"
    st.markdown(
        f"""
        <div class="cn-setup-hero">
          <div class="cn-setup-eyebrow">Cup skapad · fortsätt setupen</div>
          <div class="cn-setup-title">Kom igång med {tournament['name']}</div>
          <p class="cn-setup-copy">Lägg bara in det CupNavi behöver för att kunna planera cupen. Avancerade regler kan vänta tills senare.</p>
          <div class="cn-setup-progress-grid">
            <div class="cn-setup-step done"><strong>✓</strong>Grund</div>
            <div class="cn-setup-step active"><strong>2</strong>Tävlingsklasser</div>
            <div class="cn-setup-step"><strong>3</strong>Kapacitet</div>
            <div class="cn-setup-step"><strong>4</strong>Lägg till lag</div>
          </div>
          <div class="cn-setup-meta">{tournament['sport']} · {cup_date_label(tournament)} · {_setup_environment_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Du behöver inte kunna cupregler i förväg. Ange vilka som ska spela och vad ni har för planer/tider – CupNavi föreslår resten.")
    rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
    if rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tournament_id,))
        rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

    _sport_rec=sport_setup_recommendation(_row_value(tournament,"sport","Fotboll"))
    _played_setup=int(one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (tournament_id,),
    )["n"] or 0)

    # Legacy QA anchor: ### 1. Tävlingsklasser och svårighetsgrad
    st.markdown("### 1. Vilka ska spela?")
    st.caption("Välj åldersklass/kategori och ungefär hur många lag du tror kommer delta. Exempel: P2014 betyder pojkar födda 2014.")
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
    with st.expander("➕ Lägg till åldersklass / kategori", expanded=not _existing_class_rows and not _class_locked):
        setup_category = st.selectbox("Vilka spelar?", list(YOUTH_CLASS_CATEGORIES), key=f"setup_class_category_{tournament_id}", disabled=_class_locked)
        setup_year = st.selectbox("Spelarnas födelseår", YOUTH_CLASS_YEARS, index=YOUTH_CLASS_YEARS.index(2014) if 2014 in YOUTH_CLASS_YEARS else 0, key=f"setup_class_year_{tournament_id}", disabled=_class_locked)
        setup_class_teams = st.number_input("Ungefär hur många lag?", 2, 200, 8, key=f"setup_class_teams_new_{tournament_id}", disabled=_class_locked)
        if st.button("Lägg till klassen", key=f"setup_add_class_{tournament_id}", use_container_width=True, disabled=_class_locked):
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
    st.markdown("### 2. Vad har ni tillgång till?")
    st.caption("Ange antal planer/spelytor och när de går att använda. CupNavi använder detta för att räkna ut ett rimligt upplägg.")
    pitch_key=f"setup_pitches_{tournament_id}"
    st.number_input(
        "Hur många planer/spelytor kan användas samtidigt?",
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
        saved_address_verified=bool(_row_value(pr,"address_verified",0))
        ak=f"pitch_address_{tournament_id}_{pitch}"
        address=st.text_input(
            f"Adress – {clean}",
            value=saved_address,
            key=ak,
            placeholder="Exempel: Rudbecksgatan 52, Örebro",
            help="Ange den adress deltagare faktiskt ska navigera till.",
        )
        if address.strip()!=saved_address.strip():
            save_pitch_address(tournament_id,pitch,address)
            saved_address_verified=False
            st.session_state[f"autosave_notice_{tournament_id}"]="✓ Planadress sparad. Kontrollera den nu i Google Maps."
        if address.strip():
            maps_query=quote_plus(address.strip())
            st.link_button(
                f"Öppna {clean} i Google Maps ↗",
                f"https://www.google.com/maps/search/?api=1&query={maps_query}",
                use_container_width=True,
            )
            verified_key=f"pitch_address_verified_{tournament_id}_{pitch}"
            verified=st.checkbox(
                "Jag har kontrollerat att adressen pekar på rätt spelplats i Google Maps",
                value=saved_address_verified,
                key=verified_key,
            )
            if bool(verified)!=saved_address_verified:
                run(
                    "UPDATE pitches SET address_verified=? WHERE tournament_id=? AND pitch_number=?",
                    (1 if verified else 0,int(tournament_id),pitch),
                )
                saved_address_verified=bool(verified)
                st.session_state[f"autosave_notice_{tournament_id}"]="✓ Adresskontrollen sparades."
        else:
            saved_address_verified=False
            st.caption("Lägg in en adress om deltagarna ska kunna navigera till spelplatsen.")
    _pitch_rows_current=ensure_pitch_definitions(tournament_id,current_pitch_count)
    _addresses_to_verify=[
        row for row in _pitch_rows_current
        if str(_row_value(row,"address","") or "").strip()
        and not bool(_row_value(row,"address_verified",0))
    ]
    if _addresses_to_verify:
        st.warning(f"{len(_addresses_to_verify)} planadress(er) behöver fortfarande verifieras i Google Maps.")
    elif any(str(_row_value(row,"address","") or "").strip() for row in _pitch_rows_current):
        st.success("✓ Inlagda planadresser är verifierade i Google Maps.")

    st.caption("Kapacitetssteget anger vad som är möjligt. CupNavi förklarar senare hur prioriteringarna påverkar schemat.")
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

    # v348: Guided Cup Setup turns the existing recommendation engine into a
    # novice-facing assistant. It explains the proposed setup in plain language
    # and applies only safe recommendation/default fields when explicitly accepted.
    _guided_ready = bool(class_rows) and _planned_total > 0 and valid_windows and not _addresses_to_verify
    _guided_format_rec = None
    if _guided_ready:
        _guided_available_minutes = available_pitch_minutes(windows, row_value=_row_value) or 480
        _guided_match_minutes = estimated_match_length_minutes(rules, row_value=_row_value)
        _guided_format_rec = recommend_tournament_format(
            sport=_row_value(tournament, "sport", "Fotboll"),
            team_count=max(2, _planned_total, _actual_team_count),
            pitch_count=current_pitch_count,
            available_minutes=_guided_available_minutes,
            match_minutes=_guided_match_minutes,
            compactness=int(_row_value(rules, "compactness_level", 50) or 50),
        )

    st.markdown("### Hur ska matcherna räknas?")
    _results_counted_saved=bool(_row_value(tournament,"results_counted",1))
    _result_mode=st.radio(
        "Välj tävlingsläge",
        ["Resultat räknas", "Spela utan resultaträkning"],
        index=0 if _results_counted_saved else 1,
        horizontal=True,
        key=f"v350_results_mode_{tournament_id}",
        help="Utan resultaträkning skapas fortfarande matcher och schema, men CupNavi räknar ingen tabell och matchrapporteringen stängs av.",
    )
    _results_counted_now=_result_mode=="Resultat räknas"
    if _results_counted_now!=_results_counted_saved:
        run(
            "UPDATE tournaments SET results_counted=?,playoff_format=?,playoff_model_confirmed=?,schedule_dirty=1 WHERE id=?",
            (
                1 if _results_counted_now else 0,
                _row_value(tournament,"playoff_format","Inget slutspel") if _results_counted_now else "Inget slutspel",
                int(_row_value(tournament,"playoff_model_confirmed",0)) if _results_counted_now else 1,
                tournament_id,
            ),
        )
        st.session_state[f"autosave_notice_{tournament_id}"]="✓ Tävlingsläget sparades."
        st.rerun()
    if not _results_counted_now:
        st.info("Matcherna schemaläggs som vanligt, men inga resultat, tabeller eller slutspelsplaceringar räknas.")

    st.markdown("### CupNavis förslag")
    with st.container(border=True):
        if not _guided_ready:
            st.caption("När du har lagt till minst en klass och giltiga plantider visar CupNavi ett rekommenderat grundupplägg här.")
        else:
            _guided_group_sizes = ", ".join(str(size) for size in _guided_format_rec["group_sizes"])
            _guided_capacity_text = (
                f"Ryms inom den uppskattade kapaciteten på cirka {_guided_format_rec['capacity_matches']} matchslotar."
                if _guided_format_rec["fits_capacity"]
                else f"Behöver cirka {_guided_format_rec['total_matches']} matcher men nuvarande kapacitet uppskattas till cirka {_guided_format_rec['capacity_matches']} matchslotar."
            )
            st.success("Vi har räknat fram ett enkelt startförslag utifrån antal lag, sport, planer och tillgängliga tider.")
            _guided_playoff_label = (
                _guided_format_rec["playoff_format_label"]
                if _results_counted_now
                else "utan tabell eller slutspel"
            )
            _guided_playoff_matches = _guided_format_rec["playoff_matches"] if _results_counted_now else 0
            st.markdown(
                f"**Vi rekommenderar:** {_guided_format_rec['group_count']} grupper · "
                f"{_guided_group_sizes} lag i grupperna · {_guided_playoff_label}."
            )
            st.caption(
                f"Det ger cirka {_guided_format_rec['group_matches']} gruppspelsmatcher och "
                f"{_guided_playoff_matches} slutspelsmatcher. {_guided_capacity_text}"
            )
            st.markdown(
                f"**Matchtid:** {_sport_rec['periods']} {_sport_rec['period_label']} × "
                f"{_sport_rec['minutes_per_period']} min · **rekommenderad lagvila:** minst {_sport_rec['minimum_rest_minutes']} min."
            )
            with st.expander("Varför rekommenderar CupNavi detta?", expanded=False):
                st.write("• Grupperna gör att lagen får flera matcher innan ett eventuellt slutspel.")
                st.write("• Gruppstorleken väljs för att balansera antal matcher mot hur mycket plantid som finns.")
                st.write("• Matchtid och vila kommer från CupNavis standardprofil för den valda sporten.")
                st.write("• Du kan ändra allt senare. CupNavi ändrar inget automatiskt utan ditt godkännande.")
            if not _guided_format_rec["fits_capacity"]:
                st.warning("Förslaget ryms inte bekvämt i nuvarande plantid. Öka plantiden/antalet planer eller finjustera upplägget innan schema skapas.")
            _proposal_col1,_proposal_col2=st.columns(2)
            if _proposal_col1.button(
                "Använd CupNavis förslag",
                type="primary",
                use_container_width=True,
                key=f"v348_accept_guided_setup_{tournament_id}",
            ):
                run(
                    """UPDATE schedule_rules
                       SET halves=?,minutes_per_half=?,halftime_minutes=?,minimum_team_rest_minutes=?,
                           recommended_group_count=?,recommended_group_size=?,recommended_playoff_size=?
                       WHERE tournament_id=?""",
                    (
                        _sport_rec["periods"],
                        _sport_rec["minutes_per_period"],
                        _sport_rec["break_minutes"],
                        _sport_rec["minimum_rest_minutes"],
                        _guided_format_rec["group_count"],
                        _guided_format_rec["group_size"],
                        _guided_format_rec["playoff_size"] if _results_counted_now else 0,
                        tournament_id,
                    ),
                )
                st.session_state[f"autosave_notice_{tournament_id}"] = "✓ CupNavis rekommenderade grundupplägg är sparat."
                st.rerun()
            if _proposal_col2.button(
                "Jag vill ställa in själv",
                use_container_width=True,
                key=f"v350_custom_setup_{tournament_id}",
            ):
                st.session_state[f"show_advanced_initial_setup_{tournament_id}"]=True
                st.session_state[f"v350_scroll_to_custom_{tournament_id}"]=True
                st.rerun()
            st.caption("CupNavis förslag är frivilligt. Du kan alltid öppna alla regler och formatval och göra ett eget upplägg. Den skapar inte grupper, matcher eller schema.")

    # v326/v348: the minimum viable setup ends here. The guided recommendation
    # makes the defaults understandable before the organiser starts adding teams.
    _fast_track_ready = bool(class_rows) and _planned_total > 0 and valid_windows and not _addresses_to_verify
    _setup_ready = _fast_track_ready
    with st.container(border=True):
        st.markdown("#### Redo att lägga till lag")
        if _fast_track_ready:
            st.success("Grunden är klar. Nu kan du lägga till deltagande lag. Regler och specialval kan ändras senare.")
        else:
            st.caption("Lägg till minst en tävlingsklass och kontrollera plantiderna för att aktivera snabbstart.")
        if st.button(
            "Fortsätt → Lägg till lag",
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
        "Visa och ändra alla regler & format",
        value=bool(st.session_state.get(f"v350_scroll_to_custom_{tournament_id}", False)),
        key=f"show_advanced_initial_setup_{tournament_id}",
        help="Här kan du alltid se och ändra CupNavis förslag: gruppformat, matchtid, vila, poäng, schemaprioriteringar och övriga regler.",
    )
    if _show_advanced_setup:
        st.markdown("### Avancerad setup")
        st.caption("Finjustera endast sådant som avviker från CupNavis standardvärden. Alla inställningar autosparas som tidigare.")
        st.caption("HÅRT KRAV = får aldrig brytas · ÖNSKEMÅL = försöker uppfyllas · OPTIMERING = avgör vilket av flera giltiga scheman som är bäst.")

        with st.expander("Sportprofil", expanded=False):
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
                    (_sport_rec["periods"], _sport_rec["minutes_per_period"], _sport_rec["break_minutes"], _sport_rec["minimum_rest_minutes"], tournament_id),
                )
                run(
                    """UPDATE tournaments
                       SET enable_scorer_leaderboard=?, enable_assist_leaderboard=?, enable_card_statistics=?
                       WHERE id=?""",
                    (1 if _sport_rec["score_label"] in ("mål","goals") else 0, 1 if _sport_rec["tracks_assists"] else 0, 1 if _sport_rec["discipline_mode"] in ("cards","two_minute_and_cards") else 0, tournament_id),
                )
                st.session_state[f"autosave_notice_{tournament_id}"]=f'✓ {_sport_rec["display_name"]}-profilen applicerades.'
                st.rerun()

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

        st.markdown("### 5. Vad är viktigast i schemat?")
        st.markdown("**Tider på flera planer**")
        _sync_key=f"setup_sync_pitch_times_{tournament_id}"
        _sync_pitch_times=st.checkbox(
            "Kräv samma avsparkstider på alla planer",
            value=bool(_row_value(rules,"synchronized_pitch_times",0)),
            key=_sync_key,
            help="Påslaget ger gemensamma startvågor på alla planer. Avstängt låter varje plan använda nästa möjliga tid.",
        )
        if _sync_pitch_times:
            st.info("Synkroniserat: enklare för lag, publik och sekretariat att komma ihåg tiderna, men kan lämna viss plantid oanvänd.")
        else:
            st.info("Dynamiskt: CupNavi kan utnyttja planerna friare och få in matcher tidigare när förutsättningarna skiljer sig mellan planerna.")
        if int(_sync_pitch_times)!=int(_row_value(rules,"synchronized_pitch_times",0) or 0):
            run("UPDATE schedule_rules SET synchronized_pitch_times=? WHERE tournament_id=?",(int(_sync_pitch_times),int(tournament_id)))
            rules=one_row("SELECT * FROM schedule_rules WHERE tournament_id=?",(int(tournament_id),))

        st.markdown("**Prioritera schemamålen**")
        st.caption("Rangordna målen. **1 = viktigast.** CupNavi använder ordningen när flera olika scheman klarar alla obligatoriska regler.")
        st.info("Exempel: Om två scheman båda är giltiga väljer CupNavi hellre det som uppfyller prioritet 1 än prioritet 4.")
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
            st.info("Drag-and-drop kräver streamlit-sortables; nuvarande ordning används tills dess.")
            _new_core_items = _core_items
        st.markdown("**Aktuell rangordning**")
        for _rank,_priority_label in enumerate(_new_core_items,start=1):
            st.markdown(f"**{_rank}.** {_priority_label}")
        st.caption("Dra listan ovan för att ändra ordningen. 1 är alltid viktigast.")
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
            "Hur kompakt ska speldagen vara?",
            0,100,int(_row_value(rules,"compactness_level",50) or 50),
            key=_compact_key,
            help="Lägre värde ger mer luft och längre pauser/håltider. Högre värde försöker lägga matcherna tätare så cupen kan sluta tidigare."
        )
        if int(_compactness) < 35:
            _tempo_explanation="Luftigt: större marginaler och mer väntetid kan ge en längre speldag."
        elif int(_compactness) > 65:
            _tempo_explanation="Kompakt: CupNavi försöker minska håltider och få cupen klar tidigare utan att bryta minsta lagvila."
        else:
            _tempo_explanation="Balanserat: CupNavi väger rimlig vila mot att undvika onödigt lång speldag."
        st.caption("0 = mer luft / längre dag · 50 = balanserat · 100 = tätare schema / tidigare slut")
        st.info(_tempo_explanation)
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


        with st.expander("Valfria statistik- och driftfunktioner", expanded=False):
            st.caption("Det här behöver du inte bestämma nu. Funktionerna kan ändras senare.")
            f1,f2,f3,f4=st.columns(4)
            for col,label,column,default in [
                (f1,"Skytteliga","enable_scorer_leaderboard",1),(f2,"Assistliga","enable_assist_leaderboard",1),
                (f3,"Gula/röda kort","enable_card_statistics",1),(f4,"Control Center","enable_control_center",0)]:
                k=f"setup_{column}_{tournament_id}"
                col.checkbox(label,value=bool(_row_value(tournament,column,default)),key=k,on_change=_autosave_tournament_field,args=(tournament_id,column,k,lambda v:1 if v else 0))

        # v351: setup ends with a simple readiness handoff instead of a technical
        # editability matrix. Only minimum blockers are surfaced.
        st.markdown("### 7. Redo att fortsätta")
        st.caption("CupNavi kontrollerar bara det som måste vara klart innan du börjar lägga in deltagande lag.")

        _setup_completion_checks = [
            (
                bool(class_rows) and _planned_total > 0,
                "Åldersklass / kategori",
                "minst en klass med planerat antal lag",
                "Lägg till en klass och ungefärligt antal lag under punkt 1.",
            ),
            (
                bool(valid_windows),
                "Planer och speltider",
                "giltiga tider finns",
                "Kontrollera planernas tillgängliga tider under punkt 2.",
            ),
            (
                not bool(_addresses_to_verify),
                "Planadresser",
                "alla ifyllda adresser är verifierade",
                "Öppna och verifiera återstående planadresser i Google Maps under punkt 2.",
            ),
            (
                bool(_result_mode),
                "Tävlingsläge",
                "resultaträkning är vald" if _results_counted_now else "spel utan resultaträkning är valt",
                "Välj hur matcherna ska räknas.",
            ),
        ]
        _setup_ready = all(item[0] for item in _setup_completion_checks)

        for _check_ok, _check_label, _check_ready_text, _check_fix_text in _setup_completion_checks:
            if _check_ok:
                st.markdown(f"✓ **{_check_label}** · {_check_ready_text}")
            else:
                st.markdown(f"⚠️ **{_check_label}** · {_check_fix_text}")

        if _setup_ready:
            st.success("Grunden är klar. Nästa steg är att lägga till lagen som ska delta.")
            st.markdown(
                "**Efter detta hjälper CupNavi dig vidare:** "
                "Lägg till lag → Grupper → Schema → Kontroll → Publicera."
            )
        else:
            _remaining_setup_checks=sum(1 for item in _setup_completion_checks if not item[0])
            st.warning(
                f"{_remaining_setup_checks} sak{' återstår' if _remaining_setup_checks == 1 else 'er återstår'} "
                "innan du går vidare. Rätta punkterna ovan – resten kan ändras senare."
            )

    notice=st.session_state.pop(f"autosave_notice_{tournament_id}",None)
    if notice: st.success(notice)
    st.caption("Vanliga inställningar autosparas. Du kan komma tillbaka och ändra dem senare.")
    if _show_advanced_setup:
        if st.button(
            "Fortsätt → Lägg till lag",
            type="primary",
            use_container_width=True,
            disabled=not _setup_ready,
            key=f"v351_setup_to_teams_{tournament_id}",
        ):
            st.session_state.pop("new_tournament_setup_id", None)
            st.session_state.pop("preferred_tournament_id", None)
            st.session_state[f"admin_page_{tournament_id}"] = "Lag"
            st.rerun()