"""Public Cupinfo rendering extracted from the Streamlit monolith.

Presentation stays here. Database/domain/rate-limit helpers are injected by
app.py so behavior and persistence rules remain unchanged.
"""
import html
import re
import time
from datetime import datetime

import streamlit as st


def render_public_info_section(
    tournament_id,
    tournament,
    published_matches,
    *,
    match_completion=None,
    load_published_matches=None,
    perf,
    tr,
    row_value,
    one_row,
    all_rows,
    public_rules_html,
    cup_summary,
    sport_profile,
    rate_allowed,
    run,
):
    """Render public information/feedback independently from matches/statistics."""
    _fragment_started = time.perf_counter()
    _db_calls_before = perf["db_calls"]
    _db_ms_before = perf["db_ms"]
    info_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
    st.markdown(
        """<div class="cn-info-guide-head">
          <div class="kicker">Cupguide</div>
          <div class="title">Allt praktiskt på ett ställe</div>
          <div class="copy">Hitta planer, kontaktuppgifter, kiosk, regler och annan viktig information inför och under cupdagen.</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='cn-info-section-title'>📘 {tr('Cupens regler')}</div>", unsafe_allow_html=True)
    rules_html = public_rules_html(tournament, info_rules)
    if rules_html:
        st.markdown(rules_html, unsafe_allow_html=True)

    if tournament["public_information"]:
        st.markdown(f"<div class='cn-info-section-title'>✍️ {tr('Information från arrangören')}</div>", unsafe_allow_html=True)
        public_text = html.escape(tournament["public_information"]).replace("\n", "<br>")
        st.markdown(f"<div class='cn-custom-info-card'>{public_text}</div>", unsafe_allow_html=True)

    venue_points_public = all_rows(
        """SELECT * FROM venue_points WHERE tournament_id=? ORDER BY
           CASE kind WHEN 'Plan' THEN 1 WHEN 'Parkering' THEN 2 WHEN 'Sekretariat' THEN 3
                     WHEN 'Sjukvård' THEN 4 WHEN 'Toalett' THEN 5 WHEN 'Kiosk' THEN 6 ELSE 7 END,
           label,id""",
        (tournament_id,),
    )
    if venue_points_public:
        st.markdown("<div class='cn-info-section-title'>🗺️ Hitta på cupområdet</div>", unsafe_allow_html=True)
        st.caption("Planer och praktiska platser från arrangören.")
        for point in venue_points_public:
            icon = {"Plan":"⚽","Parkering":"🅿️","Sekretariat":"ℹ️","Sjukvård":"➕","Toalett":"🚻","Kiosk":"☕"}.get(point["kind"],"📍")
            point_kind = str(point["kind"] or "Plats").lower().replace("å","a").replace("ä","a").replace("ö","o")
            st.markdown(
                f"<div class='cn-venue-card kind-{html.escape(point_kind)}'>"
                f"<div class='cn-venue-icon'>{icon}</div><div class='cn-venue-copy'>"
                f"<strong>{html.escape(point['label'])}</strong>"
                f"<small>{html.escape(point['kind'] or 'Plats')}</small>"
                f"<span>{html.escape(point['detail'] or '')}</span></div></div>",
                unsafe_allow_html=True,
            )
            if point["url"]:
                st.link_button(f"Vägbeskrivning · {point['label']}", point["url"], use_container_width=True)

    st.markdown(f"<div class='cn-info-section-title'>📍 {tr('Praktisk information')}</div>", unsafe_allow_html=True)
    practical_rows = []
    pitch_size_format = str(row_value(info_rules, "pitch_size_format", "") or "").strip() if info_rules else ""
    if pitch_size_format:
        practical_rows.append(
            f"<div class='cn-practical-item'><span class='icon'>⚽</span><div><small>Planstorlek</small><strong>{html.escape(pitch_size_format)}</strong></div></div>"
        )
    if tournament["arena_address"]:
        practical_rows.append(f"<div class='cn-practical-item'><span class='icon'>📍</span><div><small>{html.escape(tr('Arena'))}</small><strong>{html.escape(tournament['arena_address'])}</strong></div></div>")
    if tournament["kiosk_information"]:
        practical_rows.append(f"<div class='cn-practical-item'><span class='icon'>☕</span><div><small>{html.escape(tr('Kiosk'))}</small><strong>{html.escape(tournament['kiosk_information'])}</strong></div></div>")
    if bool(row_value(tournament, "changing_rooms_available", 0)):
        room_info = (row_value(tournament, "changing_room_info", "") or "").strip() or "Omklädningsrum finns tillgängliga."
        practical_rows.append(f"<div class='cn-practical-item'><span class='icon'>🚿</span><div><small>Omklädningsrum</small><strong>{html.escape(room_info)}</strong></div></div>")
    if bool(row_value(tournament, "show_price_information", 0)) and (row_value(tournament, "price_information", "") or "").strip():
        practical_rows.append(f"<div class='cn-practical-item'><span class='icon'>💳</span><div><small>Priser/avgifter</small><strong>{html.escape(row_value(tournament, 'price_information', ''))}</strong></div></div>")
    if tournament["organizer_phone"]:
        phone_display = html.escape(tournament["organizer_phone"])
        phone_href = re.sub(r"[^0-9+]", "", tournament["organizer_phone"])
        practical_rows.append(f"<div class='cn-practical-item'><span class='icon'>📞</span><div><small>{html.escape(tr('Kontakt'))}</small><strong><a href='tel:{html.escape(phone_href)}'>{phone_display}</a></strong></div></div>")
    if tournament["feedback_email"]:
        email_display = html.escape(tournament["feedback_email"])
        email_href = html.escape(tournament["feedback_email"], quote=True)
        practical_rows.append(f"<div class='cn-practical-item'><span class='icon'>✉️</span><div><small>E-post</small><strong><a href='mailto:{email_href}'>{email_display}</a></strong></div></div>")
    if tournament["instagram_url"]:
        instagram_raw = tournament["instagram_url"].strip()
        if instagram_raw.startswith("@"):
            instagram_handle = instagram_raw[1:]
            instagram_href = f"https://www.instagram.com/{instagram_handle}/"
            instagram_label = f"@{instagram_handle}"
        elif instagram_raw.startswith("http://") or instagram_raw.startswith("https://"):
            instagram_href = instagram_raw
            instagram_handle = instagram_raw.rstrip("/").split("/")[-1]
            instagram_label = f"@{instagram_handle}" if instagram_handle else "Instagram"
        else:
            instagram_handle = instagram_raw.strip("/")
            instagram_href = f"https://www.instagram.com/{instagram_handle}/"
            instagram_label = f"@{instagram_handle}"
        practical_rows.append(
            f"<div class='cn-practical-item'><span class='icon'>📷</span><div><small>{html.escape(tr('Instagram'))}</small><strong>"
            f"<a href='{html.escape(instagram_href, quote=True)}' target='_blank' rel='noopener noreferrer'>"
            f"{html.escape(instagram_label)}</a></strong></div></div>"
        )

    if practical_rows:
        st.markdown("<div class='cn-practical-info-card'>" + "".join(practical_rows) + "</div>", unsafe_allow_html=True)
    else:
        st.info(tr("Ingen praktisk information har publicerats ännu."))

    if bool(row_value(tournament, "enable_medical_info", 0)) and (row_value(tournament, "medical_info", "") or "").strip():
        st.markdown("<div class='cn-info-section-title'>🩹 Medicinsk beredskap</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='cn-custom-info-card'>{html.escape(row_value(tournament, 'medical_info', '')).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
    if bool(row_value(tournament, "enable_lost_found", 0)) and (row_value(tournament, "lost_found_info", "") or "").strip():
        st.markdown("<div class='cn-info-section-title'>🧳 Lost & found / hittegods</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='cn-custom-info-card'>{html.escape(row_value(tournament, 'lost_found_info', '')).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
    if bool(row_value(tournament, "enable_accessibility_info", 0)) and (row_value(tournament, "accessibility_info", "") or "").strip():
        st.markdown("<div class='cn-info-section-title'>♿ Tillgänglighet</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='cn-custom-info-card'>{html.escape(row_value(tournament, 'accessibility_info', '')).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    # v382: venue_points_public is already presented once above with directions.
    # Do not repeat the same places as a second "Cupkarta" list on the same page.
    # The already loaded snapshot remains available without an extra DB roundtrip.

    all_public_matches = published_matches
    total_public_matches = int((match_completion or {}).get("total_matches", len(all_public_matches or [])) or 0)
    open_public_matches = int((match_completion or {}).get("open_matches", 0) or 0)
    cup_is_complete = total_public_matches > 0 and open_public_matches == 0
    if cup_is_complete:
        # v1.309: a collapsed Streamlit expander still executes its body. The old
        # Cupsummering therefore fetched teams and top-scorer data on every Cupinfo
        # rerun after the cup was finished. Keep the feature, but make the expensive
        # summary opt-in.
        show_cup_summary = st.toggle(
            "🏁 Visa cupsummering",
            value=False,
            key=f"public_cup_summary_{int(tournament_id)}",
            help="Laddar slutlig cupsummering och toppscorer först när du vill se den.",
        )
        if show_cup_summary:
            if not all_public_matches and load_published_matches is not None:
                all_public_matches = load_published_matches()
            top_scorer_row = one_row(
                """SELECT CASE WHEN COALESCE(players.is_protected,0)=1 THEN 'Skyddad spelare' ELSE players.name END AS player_name,
                          teams.name AS team_name,SUM(s.goals) AS goals
                   FROM player_match_stats s JOIN players ON players.id=s.player_id
                   JOIN teams ON teams.id=players.team_id JOIN matches ON matches.id=s.match_id
                   WHERE matches.tournament_id=? GROUP BY players.id,players.name,players.is_protected,teams.name
                   ORDER BY goals DESC,player_name LIMIT 1""",
                (tournament_id,),
            )
            summary_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,))
            summary = cup_summary(tournament, summary_teams, all_public_matches, top_scorer_row)
            with st.container(border=True):
                st.markdown(
                    f"**{html.escape(summary['name'])}** · {summary['sport']}  \n"
                    f"{summary['teams']} deltagare/lag · {summary['played_matches']} spelade matcher · "
                    f"{summary['total_score']} registrerade {sport_profile(summary['sport'])['score_label']}"
                )
                if summary.get("top_scorer") and summary.get("top_scorer_score", 0) > 0:
                    st.caption(f"Toppscorer: {summary['top_scorer']} ({summary['top_scorer_team']}) – {summary['top_scorer_score']}")

    # v1.310: secondary Cupinfo content is intentionally lazy. Streamlit expanders
    # execute their bodies even while collapsed, so the old page performed up to
    # four DB reads for contacts, functionaries, offers and sponsors on every
    # Cupinfo rerun. One explicit gate keeps the default journey lightweight.
    show_more_cup_details = st.toggle(
        "Visa fler cupdetaljer",
        value=False,
        key=f"public_more_cup_details_{int(tournament_id)}",
        help="Laddar lagkontakter, funktionärer, erbjudanden och partners först när du vill se dem.",
    )
    if show_more_cup_details:
        public_team_contacts = []
        if bool(row_value(tournament, "allow_team_public_contact", 0)):
            public_team_contacts = all_rows(
                """SELECT name,public_contact_name,public_contact_phone,public_contact_email
                   FROM teams WHERE tournament_id=? AND public_contact_enabled=1
                   AND (COALESCE(public_contact_name,'')<>'' OR COALESCE(public_contact_phone,'')<>'' OR COALESCE(public_contact_email,'')<>'')
                   ORDER BY name""",
                (tournament_id,),
            )
        if public_team_contacts:
            with st.expander("📞 Lagkontakter"):
                for contact in public_team_contacts:
                    bits = [x for x in (contact["public_contact_name"], contact["public_contact_phone"], contact["public_contact_email"]) if x]
                    st.markdown(f"**{html.escape(contact['name'])}** · " + " · ".join(html.escape(str(x)) for x in bits))

        public_functionaries = all_rows(
            """SELECT * FROM functionaries
               WHERE tournament_id=? AND active=1 AND public_contact=1
               ORDER BY role,name""",
            (tournament_id,),
        )
        if public_functionaries:
            with st.expander("👥 " + tr("Funktionärer")):
                for person in public_functionaries:
                    contact_bits = [bit for bit in (person["phone"], person["email"]) if bit]
                    pitch_text = f" · {tr('Plan')} {person['pitch_number']}" if person["pitch_number"] else ""
                    st.markdown(
                        f"**{html.escape(person['role'])}: {html.escape(person['name'])}**"
                        f"{pitch_text}"
                        + (f" · {' · '.join(html.escape(x) for x in contact_bits)}" if contact_bits else "")
                    )

        public_offers = all_rows(
            """SELECT * FROM offers WHERE tournament_id=? AND active=1 ORDER BY sort_order,id""",
            (tournament_id,),
        )
        if public_offers:
            with st.expander("🎁 " + tr("Erbjudanden")):
                for offer in public_offers:
                    business = f" · {offer['business_name']}" if offer["business_name"] else ""
                    st.markdown(f"**{html.escape(offer['title'])}**{html.escape(business)}")
                    if offer["description"]:
                        st.write(offer["description"])
                    if offer["discount_code"]:
                        st.caption(tr("Rabattkod"))
                        st.code(offer["discount_code"], language=None)
                    if offer["valid_until"]:
                        st.caption(f"{tr('Gäller t.o.m.')} {offer['valid_until']}")
                    if offer["url"]:
                        st.markdown(
                            f"<a href='{html.escape(offer['url'], quote=True)}' target='_blank' "
                            f"rel='noopener noreferrer'><b>{html.escape(tr('Öppna erbjudandet'))} ↗</b></a>",
                            unsafe_allow_html=True,
                        )

        public_sponsors = all_rows(
            """SELECT * FROM sponsors WHERE tournament_id=? AND active=1 ORDER BY sort_order,id""",
            (tournament_id,),
        )
        if public_sponsors:
            with st.expander("🤝 " + tr("Partners")):
                for sponsor in public_sponsors:
                    logo_html = (
                        f"<img src='{sponsor['logo_data_uri']}' alt='' style='max-width:140px;max-height:70px;object-fit:contain;margin:4px 0 8px'>"
                        if sponsor["logo_data_uri"] else ""
                    )
                    level_html = f"<div style='font-size:12px;font-weight:800;color:#166534'>{html.escape(sponsor['level'])}</div>" if sponsor["level"] else ""
                    website_html = (
                        f"<div style='margin-top:7px'><a href='{html.escape(sponsor['website_url'], quote=True)}' target='_blank' rel='noopener noreferrer'>"
                        f"{html.escape(tr('Besök partnern'))} ↗</a></div>"
                        if sponsor["website_url"] else ""
                    )
                    description_html = f"<div style='margin-top:6px'>{html.escape(sponsor['description'])}</div>" if sponsor["description"] else ""
                    st.markdown(
                        f"<div style='padding:10px 0'>{logo_html}{level_html}<b>{html.escape(sponsor['name'])}</b>{description_html}{website_html}</div>",
                        unsafe_allow_html=True,
                    )

    with st.expander("💬 " + tr("Rapportera problem eller lämna synpunkt")):
        st.caption(tr("Feedbacken sparas till den här turneringen och kan läsas av administratören."))
        with st.form(f"public_feedback_{tournament_id}", clear_on_submit=True):
            feedback_area = st.selectbox(
                tr("Vad gäller det?"),
                [tr("Matcher"), tr("Tabeller"), tr("Topplistor"), tr("Slutspel"), tr("Info"), tr("Mobil/utseende"), tr("Annat")],
            )
            feedback_message = st.text_area(tr("Beskriv problemet eller synpunkten"), max_chars=2000)
            feedback_contact = st.text_input(tr("Kontaktuppgift (frivilligt)"), max_chars=200)
            if st.form_submit_button(tr("Skicka feedback")):
                if not feedback_message.strip():
                    st.error(tr("Skriv en kort beskrivning först."))
                else:
                    allowed, retry_after, _ = rate_allowed(f"feedback:{int(tournament_id)}", 5, 600)
                    if not allowed:
                        st.error(
                            f"För många meddelanden på kort tid. Försök igen om cirka "
                            f"{max(1, retry_after // 60)} minut(er)."
                        )
                    else:
                        run(
                            "INSERT INTO feedback(tournament_id,created_at,area,message,contact) VALUES(?,?,?,?,?)",
                            (tournament_id, datetime.now().isoformat(timespec="seconds"), feedback_area,
                             feedback_message.strip(), feedback_contact.strip() or None),
                        )
                        st.success(tr("Tack. Feedbacken är sparad."))




    st.session_state[f"_public_perf_info_{tournament_id}"] = {
        "render_ms": round((time.perf_counter() - _fragment_started) * 1000, 1),
        "db_calls": perf["db_calls"] - _db_calls_before,
        "db_ms": round(perf["db_ms"] - _db_ms_before, 1),
    }
