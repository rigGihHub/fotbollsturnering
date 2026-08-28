import sqlite3
import html
import base64
import hmac
import json
import os
import random
import re
import io
import time

_APP_RENDER_STARTED = time.perf_counter()
import hashlib
import sys
import importlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def _compute_source_fingerprint():
    """Fingerprint deployed application sources without relying on imported modules."""
    root = Path(__file__).resolve().parent
    candidates = [root / "app.py", root / "requirements.txt", root / "VERSION.txt"]
    core_root = root / "cupnavi_core"
    if core_root.exists():
        candidates.extend(sorted(core_root.rglob("*.py")))
    digest = hashlib.sha256()
    for path in candidates:
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def _refresh_cupnavi_imports_if_sources_changed():
    """Reload CupNavi's own Python package automatically after a deployed source change."""
    current = _compute_source_fingerprint()
    previous = st.session_state.get("_cupnavi_source_fingerprint")
    changed = previous != current

    if changed:
        # The Streamlit process can survive a GitHub redeploy. Remove only our own
        # package modules so subsequent imports in this script load the new files.
        for module_name in list(sys.modules):
            if module_name == "cupnavi_core" or module_name.startswith("cupnavi_core."):
                sys.modules.pop(module_name, None)
        importlib.invalidate_caches()
        st.session_state["_cupnavi_source_fingerprint"] = current
        st.session_state["_cupnavi_source_reload_count"] = int(
            st.session_state.get("_cupnavi_source_reload_count", 0)
        ) + 1
        st.session_state["_cupnavi_source_reloaded_at"] = datetime.now().isoformat(timespec="seconds")
    return current, changed


ACTIVE_SOURCE_FINGERPRINT, SOURCE_PACKAGE_REFRESHED = _refresh_cupnavi_imports_if_sources_changed()

from cupnavi_core.version import APP_VERSION as IMPORTED_CORE_APP_VERSION

from cupnavi_core.product_foundation import organizer_workflow, workflow_summary
from cupnavi_core.observability import safe_error_record, persist_error
from cupnavi_core.schedule_quality import assess_schedule
from cupnavi_core.public_competition import calculate_group_table
from cupnavi_core.rules import validate_match_event_totals
from cupnavi_core.match_event_logic import prepare_changed_event_rows
from cupnavi_core.initial_setup_logic import available_pitch_minutes, estimated_capacity_slots, estimated_match_length_minutes, normalized_priority_order, priority_order_changed
from cupnavi_core.home_away import orientation_balance_score
from cupnavi_core.pdf_export import build_schedule_pdf
from cupnavi_core.migrations import apply_migrations, LATEST_SCHEMA_VERSION, ensure_competition_class_schema_compat, ensure_v16_setup_schema_compat, ensure_v18_pitch_names_schema_compat, ensure_v19_schema_compat, ensure_v20_schema_compat, ensure_v21_schema_compat
from cupnavi_core.health import collect_database_health
from cupnavi_core.backup import build_backup_bytes, validate_backup_bytes, restore_backup_as_new_tournament
from cupnavi_core.rate_limit import consume_rate_limit
from cupnavi_core.config import BACKUP_FILE_SUFFIX, PUBLIC_BASE_URL
from cupnavi_core.schedule_repository import ScheduleRepository
from cupnavi_core.schedule_domain import build_schedule_window, schedule_source_team_id
from cupnavi_core.import_service import (
    TEAM_FIELDS, PLAYER_FIELDS, auto_map_columns,
    build_team_import_plan, build_player_import_plan,
)
from cupnavi_core.team_portal import generate_access_code, generate_short_numeric_code, new_code_hash, verify_access_code, squad_deadline_at, squad_is_locked
from cupnavi_core.experience import (
    SPORT_PROFILES, sport_profile, match_duration_minutes, analyze_schedule_change,
    planned_delay_updates, tournament_quality_score, playoff_preview, cup_summary,
)
from cupnavi_core.sports import sport_definition
from cupnavi_core.match_engine import match_format
from cupnavi_core.schedule_optimizer import optimize_match_order
from cupnavi_core.v137 import candidate_sort_key, normalize_schedule_strategy, travel_minutes
from cupnavi_core.email_service import send_notification_email
from cupnavi_core.notification_service import new_token, token_hash, normalize_email, category_enabled, classify_notification, now_iso
from cupnavi_core.i18n import SUPPORTED_LOCALES, DEFAULT_LOCALE, DEFAULT_TIMEZONE, valid_timezone
from cupnavi_core.lifecycle import normalize_status, status_label, choose_unique_slug
from cupnavi_core.qol import TOURNAMENT_TEMPLATES, template_definition, clone_tournament_payload, checklist_items, admin_mode
from cupnavi_core.fairness import fairness_report
from cupnavi_core.ux2 import workflow_progress, attention_items, schedule_board
from cupnavi_core.about import feature_catalog, about_intro
from cupnavi_core.ui_logic import resolve_tournament_selector_seed
from cupnavi_core.public_view_logic import (
    public_navigation_specs,
    public_section_for_page,
    resolve_public_page,
)
from cupnavi_core.public_info_view import render_public_info_section as render_public_info_section_module
from cupnavi_core.public_statistics_view import render_public_statistics_section as render_public_statistics_section_module
from cupnavi_core.public_match_cards import render_public_match_cards as render_public_match_cards_module
from cupnavi_core.public_match_filter_logic import filter_matches, sort_public_matches
from cupnavi_core.public_match_feed_logic import classify_public_match_feed, public_match_feed_summary
from cupnavi_core.public_match_filters_view import render_public_match_filters as render_public_match_filters_module
from cupnavi_core.match_reporter_logic import build_bulk_result_rows, prepare_bulk_result_update, result_snapshot, select_playable_matches

APP_BUILD_VERSION = "2026.08.28-252-CODE-REGEN-CONFIRM"
APP_VERSION = APP_BUILD_VERSION

def read_core_version_from_disk():
    """Read the deployed version file directly, bypassing Python's import cache."""
    version_path = Path(__file__).resolve().parent / "cupnavi_core" / "version.py"
    try:
        text = version_path.read_text(encoding="utf-8")
        match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', text)
        return match.group(1) if match else IMPORTED_CORE_APP_VERSION
    except (OSError, UnicodeError):
        return IMPORTED_CORE_APP_VERSION

CORE_APP_VERSION = read_core_version_from_disk()
RELEASE_FILES_MISMATCH = CORE_APP_VERSION != APP_BUILD_VERSION
REQUIRED_SCHEMA_VERSION = max(int(LATEST_SCHEMA_VERSION), 5)


def deployment_diagnostics():
    return {
        "release": APP_BUILD_VERSION,
        "core_disk_version": CORE_APP_VERSION,
        "core_imported_version": IMPORTED_CORE_APP_VERSION,
        "fingerprint": ACTIVE_SOURCE_FINGERPRINT,
        "fingerprint_short": ACTIVE_SOURCE_FINGERPRINT[:12],
        "auto_refresh_count": int(st.session_state.get("_cupnavi_source_reload_count", 0)),
        "last_auto_refresh": st.session_state.get("_cupnavi_source_reloaded_at"),
        "package_refreshed_this_run": bool(SOURCE_PACKAGE_REFRESHED),
    }

try:
    from streamlit_sortables import sort_items
except ImportError:
    sort_items = None

try:
    import qrcode
except ImportError:
    qrcode = None



PUBLIC_APP_URL = PUBLIC_BASE_URL.rstrip("/") + "/"


def sport_setup_recommendation(sport):
    """CupNavi defaults and relevant setup concepts for a selected sport."""
    definition=dict(sport_definition(sport))
    fmt=match_format(sport)
    sport_id=str(sport_profile(sport).get("sport_id") or "other")

    profiles={
        "football":{
            "group_sizes":[4,5,3,6],
            "match_note":"Kortare cupmatcher med två halvlekar är vanligast.",
            "rest_note":"Lagvila är en central schemabegränsning.",
            "discipline_label":"Gula/röda kort",
            "relevant_stats":["Mål","Assist","Gula/röda kort"],
            "playoff_note":"Gruppspel följt av A/B-slutspel eller placeringsslutspel fungerar bra.",
            "venue_label":"Planer",
        },
        "floorball":{
            "group_sizes":[4,5,3,6],
            "match_note":"Cupmatcher spelas lämpligen i perioder; CupNavi föreslår sportprofilens periodantal.",
            "rest_note":"Undvik täta matcher och långa väntetider mellan periodintensiva matcher.",
            "discipline_label":"Utvisningar/straffminuter",
            "relevant_stats":["Mål","Assist"],
            "playoff_note":"Gruppspel följt av direkt slutspel är normalt mest lättöverskådligt.",
            "venue_label":"Spelplaner/hallar",
        },
        "handball":{
            "group_sizes":[4,5,3,6],
            "match_note":"Två halvlekar med kort cupmatchtid ger vanligtvis bäst flöde.",
            "rest_note":"Lagvila och hallkapacitet bör prioriteras högt.",
            "discipline_label":"2-minutersutvisningar/kort",
            "relevant_stats":["Mål","Kort/utvisningar"],
            "playoff_note":"Gruppspel och semifinal/final är ett tydligt standardupplägg.",
            "venue_label":"Spelplaner/hallar",
        },
    }
    generic={
        "group_sizes":[4,5,3,6],
        "match_note":"CupNavi använder sportprofilens perioder/set som startvärde.",
        "rest_note":"Vila och kapacitet anpassas efter sportprofilen.",
        "discipline_label":"Disciplinhändelser",
        "relevant_stats":["Resultat"],
        "playoff_note":"CupNavi föreslår ett slutspel som ryms i tillgänglig kapacitet.",
        "venue_label":"Spelytor",
    }
    extra=profiles.get(sport_id,generic)
    return {
        "sport_id":sport_id,
        "display_name":definition.get("sv") or str(sport),
        "participant_type":definition.get("participant_type","team"),
        "period_label":definition.get("period_label",{}).get("sv","perioder"),
        "score_label":definition.get("score_label",{}).get("sv","poäng"),
        "periods":int(definition.get("periods") or 2),
        "minutes_per_period":int(definition.get("minutes_per_period") or 20),
        "break_minutes":int(definition.get("break_minutes") or 5),
        "minimum_rest_minutes":int(definition.get("minimum_rest_minutes") or 45),
        "tracks_assists":bool(fmt.tracks_assists),
        "discipline_mode":fmt.discipline_mode,
        **extra,
    }


def recommend_tournament_format(*, sport, team_count, pitch_count, available_minutes, match_minutes, compactness=50):
    """Return an explainable tournament-format recommendation without mutating data."""
    sport_key=str(sport or "").strip().lower()
    n=max(2,int(team_count or 0))
    pitches=max(1,int(pitch_count or 1))
    minutes=max(0,int(available_minutes or 0))
    match_len=max(1,int(match_minutes or 1))
    compact=max(0,min(100,int(compactness or 50)))

    # Sport-specific defaults come from the same setup profile shown to the organizer.
    preferred_group_sizes=tuple(sport_setup_recommendation(sport)["group_sizes"])

    capacity_matches=(minutes//match_len)*pitches if minutes else 0

    def candidate(group_size):
        group_count=max(1,(n+group_size-1)//group_size)
        sizes=[n//group_count + (1 if i < n%group_count else 0) for i in range(group_count)]
        group_matches=sum(size*(size-1)//2 for size in sizes)

        possible_qualifiers=min(n,group_count*2)
        playoff_size=2
        for clean in (16,8,4,2):
            if clean <= possible_qualifiers:
                playoff_size=clean
                break
        if n >= 4:
            playoff_size=max(4,playoff_size)

        playoff_matches=max(0,playoff_size-1)
        total_matches=group_matches+playoff_matches
        overload=max(0,total_matches-capacity_matches) if capacity_matches else 0
        balance_penalty=(max(sizes)-min(sizes))*4
        density_penalty=(group_matches*compact)/100.0
        preference_penalty=preferred_group_sizes.index(group_size)*2
        score=overload*1000+balance_penalty+density_penalty+preference_penalty
        return {
            "group_size":group_size,
            "group_count":group_count,
            "group_sizes":sizes,
            "group_matches":group_matches,
            "playoff_size":playoff_size,
            "playoff_matches":playoff_matches,
            "total_matches":total_matches,
            "capacity_matches":capacity_matches,
            "fits_capacity": bool(capacity_matches and total_matches <= capacity_matches),
            "score":score,
        }

    options=[candidate(size) for size in preferred_group_sizes if size <= max(n,3)]
    best=min(options,key=lambda item:item["score"])
    label = (
        "Åttondelsfinal → kvartsfinal → semifinal → final" if best["playoff_size"] >= 16 else
        "Kvartsfinal → semifinal → final" if best["playoff_size"] >= 8 else
        "Semifinal → final" if best["playoff_size"] >= 4 else
        "Final"
    )
    return {**best,"playoff_format_label":label,"sport":sport}


def public_cup_url(tournament_id):
    """Permanent public link. Slug is preferred; numeric IDs remain backward compatible."""
    row = one_row("SELECT public_slug FROM tournaments WHERE id=?", (int(tournament_id),))
    public_key = row["public_slug"] if row and row["public_slug"] else str(int(tournament_id))
    return f"{PUBLIC_APP_URL}?cup={quote(str(public_key))}"

def parse_age_classes(value):
    """Bakåtkompatibel parser för tävlingsklasser från JSON eller kommaseparerad text."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        text_value = str(value).strip()
        if not text_value:
            return []
        try:
            parsed = json.loads(text_value)
            raw = parsed if isinstance(parsed, list) else [text_value]
        except (TypeError, ValueError, json.JSONDecodeError):
            raw = re.split(r"[,;\n]+", text_value)
    result = []
    seen = set()
    for item in raw:
        label = str(item).strip()
        if label and label.casefold() not in seen:
            result.append(label)
            seen.add(label.casefold())
    return result


YOUTH_CLASS_CATEGORIES = {"Pojkar": "P", "Flickor": "F"}
YOUTH_CLASS_YEARS = list(range(2008, 2023))

def youth_competition_class_label(category, year):
    prefix = YOUTH_CLASS_CATEGORIES.get(str(category), "P")
    return f"{prefix}{int(year)}"

def add_competition_class(tournament_id, category, year, planned_team_count=0):
    """Lägg till en ungdomsklass med eget planerat antal lag."""
    label = youth_competition_class_label(category, year)
    current = [competition_class_label(row) for row in competition_classes(tournament_id)]
    if label.casefold() in {item.casefold() for item in current}:
        return False, f"{label} finns redan."
    updated = current + [label]
    run("UPDATE tournaments SET age_classes_json=? WHERE id=?", (json.dumps(updated, ensure_ascii=False), tournament_id))
    sync_competition_classes(tournament_id, updated)
    row=one_row("SELECT id FROM competition_classes WHERE tournament_id=? AND name=?",(int(tournament_id),label))
    if row is not None:
        run("UPDATE competition_classes SET planned_team_count=? WHERE id=?",(max(0,int(planned_team_count or 0)),int(row["id"])))
    sync_expected_team_count_from_classes(tournament_id)
    return True, f"{label} tillagd."

def remove_competition_class(tournament_id, class_id):
    """Ta bort en oanvänd tävlingsklass. Använda klasser raderas aldrig blint."""
    row = one_row("SELECT id,name FROM competition_classes WHERE id=? AND tournament_id=?", (class_id, tournament_id))
    if row is None:
        return False, "Tävlingsklassen finns inte längre."
    team_count = int(one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=? AND competition_class_id=?", (tournament_id, class_id))["n"] or 0)
    group_count = int(one_row("SELECT COUNT(*) AS n FROM groups WHERE tournament_id=? AND competition_class_id=?", (tournament_id, class_id))["n"] or 0)
    if team_count or group_count:
        return False, f"{row['name']} används av {team_count} lag och {group_count} grupper. Flytta eller ta bort dessa kopplingar först."
    run("DELETE FROM competition_classes WHERE id=? AND tournament_id=?", (class_id, tournament_id))
    remaining = [competition_class_label(item) for item in competition_classes(tournament_id)]
    run("UPDATE tournaments SET age_classes_json=? WHERE id=?", (json.dumps(remaining, ensure_ascii=False), tournament_id))
    sync_expected_team_count_from_classes(tournament_id)
    return True, f"{row['name']} borttagen."

def competition_classes(tournament_id):
    """Return tournament classes without letting a lagging remote migration crash public pages."""
    sql = "SELECT id,tournament_id,name,sort_order,difficulty,planned_team_count FROM competition_classes WHERE tournament_id=? ORDER BY sort_order,name,id"
    params = (int(tournament_id),)
    try:
        return all_rows(sql, params)
    except Exception:
        # First try to repair the schema. Turso/libSQL deployments can briefly
        # expose new app code before the ALTER has reached the remote database.
        try:
            with db() as con:
                ensure_competition_class_schema_compat(con)
                con.commit()
            _clear_render_query_cache()
            return all_rows(sql, params)
        except Exception:
            # Public rendering must remain available even if ALTER TABLE cannot
            # be completed right now. Fall back to the pre-v176 columns.
            fallback = all_rows(
                "SELECT id,tournament_id,name,sort_order,difficulty FROM competition_classes WHERE tournament_id=? ORDER BY sort_order,name,id",
                params,
            )
            normalized = []
            for row in fallback:
                item = dict(row)
                item["planned_team_count"] = 0
                normalized.append(item)
            return normalized


def sync_competition_classes(tournament_id, labels=None):
    """Synka äldre tävlingsklassdata till den nya klassmodellen utan att radera använda klasser."""
    tournament_id = int(tournament_id)
    if labels is None:
        row = one_row("SELECT age_classes_json FROM tournaments WHERE id=?", (tournament_id,))
        labels = parse_age_classes(_row_value(row, "age_classes_json", "[]") if row else "[]")
    labels = parse_age_classes(labels)
    existing = {str(row["name"]).casefold(): row for row in competition_classes(tournament_id)}
    for order, label in enumerate(labels):
        if label.casefold() not in existing:
            run(
                "INSERT OR IGNORE INTO competition_classes(tournament_id,name,sort_order) VALUES(?,?,?)",
                (tournament_id, label, order),
            )
        else:
            run("UPDATE competition_classes SET sort_order=? WHERE id=?", (order, existing[label.casefold()]["id"]))
    # Koppla äldre textfält till klass-ID när det går. Textfälten behålls tills vidare för bakåtkompatibilitet.
    run(
        """UPDATE teams SET competition_class_id=(SELECT cc.id FROM competition_classes cc WHERE cc.tournament_id=teams.tournament_id AND cc.name=teams.age_class LIMIT 1)
             WHERE tournament_id=? AND competition_class_id IS NULL AND age_class IS NOT NULL AND TRIM(age_class)<>''""",
        (tournament_id,),
    )
    run(
        """UPDATE groups SET competition_class_id=(SELECT cc.id FROM competition_classes cc WHERE cc.tournament_id=groups.tournament_id AND cc.name=groups.age_class LIMIT 1)
             WHERE tournament_id=? AND competition_class_id IS NULL AND age_class IS NOT NULL AND TRIM(age_class)<>''""",
        (tournament_id,),
    )
    return competition_classes(tournament_id)


def competition_class_label(row):
    return str(_row_value(row, "name", "") or "").strip()


def sync_expected_team_count_from_classes(tournament_id):
    """Keep legacy/global team limit equal to the sum of planned teams per class."""
    rows=competition_classes(tournament_id)
    planned=sum(max(0,int(_row_value(row,"planned_team_count",0) or 0)) for row in rows)
    actual=int(one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?",(int(tournament_id),))["n"] or 0)
    total=max(planned,actual)
    run("UPDATE tournaments SET expected_team_count=? WHERE id=?",(total,int(tournament_id)))
    return total


DIFFICULTY_LEVELS = ["Lätt", "Medel", "Svår", "Extra svår"]

def tournament_day_windows(tournament_id):
    return all_rows("SELECT tournament_id,play_date,start_time,end_time,confirmed FROM tournament_day_windows WHERE tournament_id=? ORDER BY play_date", (int(tournament_id),))

def ensure_tournament_day_windows(tournament_id, tournament, default_start="09:00", default_end="18:00"):
    start_date = datetime.fromisoformat(tournament["start_date"] or tournament["tournament_date"]).date()
    end_date = datetime.fromisoformat(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"]).date()
    existing = {str(r["play_date"]): r for r in tournament_day_windows(tournament_id)}
    day = start_date
    while day <= end_date:
        key = day.isoformat()
        if key not in existing:
            run("INSERT OR IGNORE INTO tournament_day_windows(tournament_id,play_date,start_time,end_time,confirmed) VALUES(?,?,?,?,0)", (int(tournament_id), key, default_start, default_end))
        day += timedelta(days=1)
    return tournament_day_windows(tournament_id)

def pitch_day_windows(tournament_id, pitch_count=None):
    params=[int(tournament_id)]
    sql="SELECT tournament_id,pitch_number,play_date,start_time,end_time,confirmed FROM pitch_day_windows WHERE tournament_id=?"
    if pitch_count is not None:
        sql += " AND pitch_number<=?"; params.append(int(pitch_count))
    sql += " ORDER BY play_date,pitch_number"
    return all_rows(sql, tuple(params))

def ensure_pitch_day_windows(tournament_id, tournament, pitch_count, default_start="09:00", default_end="18:00"):
    pitch_count=max(1,int(pitch_count or 1))
    legacy={str(r["play_date"]):r for r in ensure_tournament_day_windows(tournament_id,tournament,default_start,default_end)}
    existing={(str(r["play_date"]),int(r["pitch_number"])) for r in pitch_day_windows(tournament_id)}
    start_date=datetime.fromisoformat(tournament["start_date"] or tournament["tournament_date"]).date()
    end_date=datetime.fromisoformat(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"]).date()
    day=start_date
    while day<=end_date:
        ds=day.isoformat(); base=legacy.get(ds)
        ds_start=base["start_time"] if base else default_start; ds_end=base["end_time"] if base else default_end
        for pitch in range(1,pitch_count+1):
            if (ds,pitch) not in existing:
                run("INSERT OR IGNORE INTO pitch_day_windows(tournament_id,pitch_number,play_date,start_time,end_time,confirmed) VALUES(?,?,?,?,?,0)", (int(tournament_id),pitch,ds,ds_start,ds_end))
        day += timedelta(days=1)
    return pitch_day_windows(tournament_id,pitch_count)

def save_pitch_day_window(tournament_id,pitch_number,play_date,start_time,end_time,confirmed=True):
    if start_time >= end_time:
        raise ValueError("Sluttiden måste vara senare än starttiden.")
    run("""INSERT INTO pitch_day_windows(tournament_id,pitch_number,play_date,start_time,end_time,confirmed) VALUES(?,?,?,?,?,?)
           ON CONFLICT(tournament_id,pitch_number,play_date) DO UPDATE SET start_time=excluded.start_time,end_time=excluded.end_time,confirmed=excluded.confirmed""",
        (int(tournament_id),int(pitch_number),str(play_date),str(start_time),str(end_time),1 if confirmed else 0))
    rows=pitch_day_windows(tournament_id)
    starts=[r["start_time"] for r in rows if r["start_time"]]; ends=[r["end_time"] for r in rows if r["end_time"]]
    if starts and ends:
        run("UPDATE schedule_rules SET first_match_time=?,latest_kickoff_time=? WHERE tournament_id=?",(min(starts),max(ends),int(tournament_id)))


def pitch_definitions(tournament_id, pitch_count=None):
    """Return pitch metadata and repair mixed cloud schemas once if needed.

    v137 introduced pitches.address. A deployment can legitimately have the
    migration marker while the remote table is still missing that column.
    Never let that compatibility state crash Match/Result views.
    """
    params=[int(tournament_id)]
    sql="SELECT tournament_id,pitch_number,name,address FROM pitches WHERE tournament_id=?"
    if pitch_count is not None:
        sql += " AND pitch_number<=?"; params.append(int(pitch_count))
    sql += " ORDER BY pitch_number"
    try:
        return all_rows(sql, tuple(params))
    except Exception as exc:
        message=str(exc).lower()
        if "address" not in message and "column" not in message and "schema" not in message:
            raise
        with db() as con:
            ensure_v18_pitch_names_schema_compat(con)
            ensure_v19_schema_compat(con)
            con.commit()
        _clear_render_query_cache()
        return all_rows(sql, tuple(params))

def ensure_pitch_definitions(tournament_id, pitch_count):
    pitch_count=max(1,int(pitch_count or 1))
    existing={int(r["pitch_number"]):str(r["name"] or "").strip() for r in pitch_definitions(tournament_id)}
    missing=[
        (int(tournament_id), pitch, f"Plan {pitch}")
        for pitch in range(1, pitch_count+1)
        if pitch not in existing
    ]
    if missing:
        run_many(
            "INSERT OR IGNORE INTO pitches(tournament_id,pitch_number,name) VALUES(?,?,?)",
            missing,
        )
    return pitch_definitions(tournament_id,pitch_count)

def save_pitch_name(tournament_id,pitch_number,name):
    clean=str(name or "").strip() or f"Plan {int(pitch_number)}"
    run("""INSERT INTO pitches(tournament_id,pitch_number,name) VALUES(?,?,?)
           ON CONFLICT(tournament_id,pitch_number) DO UPDATE SET name=excluded.name""",
        (int(tournament_id),int(pitch_number),clean))
    return clean

def save_pitch_address(tournament_id,pitch_number,address):
    run("UPDATE pitches SET address=? WHERE tournament_id=? AND pitch_number=?",
        (str(address or "").strip() or None,int(tournament_id),int(pitch_number)))

def pitch_travel_matrix(tournament_id):
    rows=all_rows("SELECT from_pitch_number,to_pitch_number,minutes FROM pitch_travel_times WHERE tournament_id=?",(int(tournament_id),))
    return {(int(r["from_pitch_number"]),int(r["to_pitch_number"])):max(0,int(r["minutes"] or 0)) for r in rows}

def save_pitch_travel_time(tournament_id,from_pitch,to_pitch,minutes):
    a,b=int(from_pitch),int(to_pitch); minutes=max(0,int(minutes or 0))
    run_many(
        """INSERT INTO pitch_travel_times(tournament_id,from_pitch_number,to_pitch_number,minutes) VALUES(?,?,?,?)
           ON CONFLICT(tournament_id,from_pitch_number,to_pitch_number) DO UPDATE SET minutes=excluded.minutes""",
        [
            (int(tournament_id),a,b,minutes),
            (int(tournament_id),b,a,minutes),
        ],
    )

def pitch_name_map(tournament_id,pitch_count=None):
    key=("pitch-name-map", int(tournament_id), int(pitch_count) if pitch_count else None)
    def build():
        rows=ensure_pitch_definitions(tournament_id,pitch_count or 1) if pitch_count else pitch_definitions(tournament_id)
        return {int(r["pitch_number"]):str(r["name"] or f"Plan {int(r['pitch_number'])}") for r in rows}
    return _derived_cache_get(key, build)

def pitch_label(tournament_id,pitch_number,names=None):
    if not pitch_number:
        return "Plan ej satt"
    pitch_number=int(pitch_number)
    names=names or pitch_name_map(tournament_id)
    return names.get(pitch_number,f"Plan {pitch_number}")

REQUEST_TYPE_LABELS = {
    "late_start": "Önskar sen första match",
    "latest_finish": "Önskar vara klar senast",
    "preferred_pitch": "Önskar viss plan",
    "extra_rest": "Önskar extra lagvila",
    "avoid_late_group": "Undvik sen gruppmatch",
}

def schedule_request_label(row):
    label=REQUEST_TYPE_LABELS.get(str(_row_value(row,"request_type","")),str(_row_value(row,"request_type","Önskemål")))
    value=str(_row_value(row,"request_value","") or "").strip()
    return f"{label}: {value}" if value else label

def _team_matches_for_request(tournament_id, team_id):
    team_token=f"team:{int(team_id)}"
    rows=all_rows(
        """SELECT * FROM matches
           WHERE tournament_id=? AND (home_source=? OR away_source=?)
           ORDER BY scheduled_start,id""",
        (int(tournament_id),team_token,team_token),
    )
    return [dict(r) for r in rows]

def evaluate_schedule_request(tournament_id, request_row, rules):
    matches=[m for m in _team_matches_for_request(tournament_id,request_row["team_id"]) if m.get("scheduled_start")]
    if not matches:
        return None,"Inga schemalagda matcher ännu."

    rtype=str(request_row["request_type"])
    value=str(request_row["request_value"] or "").strip()
    strength=str(request_row["strength"] or "Önskemål")
    starts=[datetime.fromisoformat(str(m["scheduled_start"])) for m in matches]
    starts.sort()

    if rtype=="late_start":
        try:
            wanted=datetime.strptime(value,"%H:%M").time()
        except ValueError:
            return None,"Ogiltig tid."
        ok=starts[0].time() >= wanted
        return ok, f"Första match {starts[0].strftime('%H:%M')} · önskat tidigast {value}"

    if rtype=="latest_finish":
        try:
            wanted=datetime.strptime(value,"%H:%M").time()
        except ValueError:
            return None,"Ogiltig tid."
        duration_minutes=max(1,int(rules["halves"] or 1)*int(rules["minutes_per_half"] or 0)+max(0,int(rules["halves"] or 1)-1)*int(rules["halftime_minutes"] or 0))
        last_end=max(starts)+timedelta(minutes=duration_minutes)
        ok=last_end.time() <= wanted
        return ok, f"Sista match slut cirka {last_end.strftime('%H:%M')} · önskat senast {value}"

    if rtype=="preferred_pitch":
        try:
            wanted_pitch=int(value)
        except ValueError:
            return None,"Ogiltigt plannummer."
        pitches=[int(m["pitch_number"]) for m in matches if m.get("pitch_number")]
        if not pitches:
            return None,"Inga planplaceringar ännu."
        share=sum(1 for p in pitches if p==wanted_pitch)/len(pitches)
        threshold=1.0 if strength=="Hårt krav" else 0.5
        return share >= threshold, f"{sum(1 for p in pitches if p==wanted_pitch)}/{len(pitches)} matcher på Plan {wanted_pitch}"

    if rtype=="extra_rest":
        try:
            wanted=max(0,int(value))
        except ValueError:
            return None,"Ogiltigt antal minuter."
        if len(starts)<2:
            return True,"Endast en schemalagd match."
        duration_minutes=max(1,int(rules["halves"] or 1)*int(rules["minutes_per_half"] or 0)+max(0,int(rules["halves"] or 1)-1)*int(rules["halftime_minutes"] or 0))
        gaps=[]
        for a,b in zip(starts,starts[1:]):
            gaps.append(int((b-(a+timedelta(minutes=duration_minutes))).total_seconds()//60))
        minimum=min(gaps) if gaps else 9999
        return minimum >= wanted, f"Minsta faktisk vila {minimum} min · önskat {wanted} min"

    if rtype=="avoid_late_group":
        group_starts=[datetime.fromisoformat(str(m["scheduled_start"])) for m in matches if m.get("stage")=="Gruppspel"]
        if not group_starts:
            return True,"Inga gruppmatcher."
        day_rows=all_rows("SELECT start_time,end_time FROM pitch_day_windows WHERE tournament_id=? AND confirmed=1",(int(tournament_id),))
        latest_boundary=None
        for row in day_rows:
            try:
                s=datetime.strptime(row["start_time"],"%H:%M")
                e=datetime.strptime(row["end_time"],"%H:%M")
                boundary=(s + (e-s)*0.75).time()
                latest_boundary=max(latest_boundary,boundary) if latest_boundary else boundary
            except (TypeError,ValueError):
                pass
        if latest_boundary is None:
            latest_boundary=datetime.strptime("17:00","%H:%M").time()
        late=[dt for dt in group_starts if dt.time() >= latest_boundary]
        return not late, f"{len(late)} sena gruppmatcher enligt sista fjärdedelen av speldagen"

    return None,"Önskemålstypen har ännu ingen automatisk kontroll."

def schedule_score_report(tournament_id, rules):
    matches=[dict(r) for r in all_rows("SELECT * FROM matches WHERE tournament_id=? ORDER BY id",(int(tournament_id),))]
    teams=all_rows("SELECT id,late_first_match,earliest_first_time FROM teams WHERE tournament_id=?",(int(tournament_id),))
    late_preferences={
        int(r["id"]):r["earliest_first_time"]
        for r in teams
        if bool(r["late_first_match"]) and r["earliest_first_time"]
    }
    quality=assess_schedule(
        matches,
        min_rest_minutes=int(_row_value(rules,"minimum_team_rest_minutes",0) or 0),
        late_preferences=late_preferences,
    )
    requests=all_rows(
        "SELECT * FROM schedule_requests WHERE tournament_id=? AND status='Godkänd' ORDER BY priority,id",
        (int(tournament_id),),
    )
    evaluated=[]
    fulfilled=0
    hard_failed=0
    for req in requests:
        ok,detail=evaluate_schedule_request(tournament_id,req,rules)
        evaluated.append((dict(req),ok,detail))
        if ok is True:
            fulfilled += 1
        elif ok is False and str(req["strength"])=="Hårt krav":
            hard_failed += 1

    request_total=sum(1 for _,ok,_ in evaluated if ok is not None)
    request_score=100 if request_total==0 else round(100*fulfilled/request_total)
    score=max(0,min(100,round(quality["score"]*0.7 + request_score*0.3 - hard_failed*15)))
    grade=("Utmärkt" if score>=95 else "Mycket bra" if score>=85 else "Bra" if score>=75 else "Behöver förbättras" if score>=60 else "Svagt")
    return {
        "score":score,
        "grade":grade,
        "quality":quality,
        "requests":evaluated,
        "fulfilled":fulfilled,
        "request_total":request_total,
        "hard_failed":hard_failed,
    }

def schedule_change_impact(tournament_id, change_type):
    rows=all_rows("SELECT id,scheduled_start,home_score,away_score,stage FROM matches WHERE tournament_id=?",(int(tournament_id),))
    played=[r for r in rows if r["home_score"] is not None and r["away_score"] is not None]
    future=[r for r in rows if not (r["home_score"] is not None and r["away_score"] is not None)]
    affects_all={"match_duration","points","group_structure","pitch_windows","priorities","playoff_format"}
    if change_type=="playoff_format":
        affected=[r for r in future if r["stage"]!="Gruppspel"]
    elif change_type=="points":
        affected=[]
    elif change_type in affects_all:
        affected=future
    else:
        affected=future
    return {
        "played":len(played),
        "future":len(future),
        "affected":len(affected),
        "requires_regeneration":change_type in {"match_duration","group_structure","pitch_windows","priorities","playoff_format"},
        "played_protected":True,
    }


def _schedule_recovery_context(tournament_id, tournament, rules, unresolved):
    unresolved=max(0,int(unresolved or 0))
    teams=all_rows("SELECT id,late_first_match,earliest_first_time,avoid_late_group_match FROM teams WHERE tournament_id=?",(int(tournament_id),))
    late_first=sum(1 for r in teams if bool(r["late_first_match"]) and r["earliest_first_time"])
    avoid_late=sum(1 for r in teams if bool(_row_value(r,"avoid_late_group_match",0)))
    windows=ensure_pitch_day_windows(tournament_id,tournament,int(rules["pitch_count"]),rules["first_match_time"],rules["latest_kickoff_time"])
    last_date=max((str(r["play_date"]) for r in windows),default=None)
    last_rows=[r for r in windows if str(r["play_date"])==last_date]
    duration_min=int(rules["halves"] or 1)*int(rules["minutes_per_half"] or 0)+max(0,int(rules["halves"] or 1)-1)*int(rules["halftime_minutes"] or 0)
    slot=max(1,duration_min+int(rules["pitch_break_minutes"] or 0))
    pitches=max(1,len(last_rows) or int(rules["pitch_count"] or 1))
    total_capacity=0
    for row in windows:
        start_dt=datetime.strptime(row["start_time"],"%H:%M")
        end_dt=datetime.strptime(row["end_time"],"%H:%M")
        available=max(0,int((end_dt-start_dt).total_seconds()//60))
        if available>=duration_min:
            total_capacity += 1 + max(0,(available-duration_min)//slot)
    total_matches=int(one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=?",(int(tournament_id),))["n"] or 0)
    physical_shortfall=max(0,total_matches-total_capacity)
    needed_slots=max(unresolved,physical_shortfall)
    extra_slots_per_pitch=(needed_slots+pitches-1)//pitches if needed_slots else 1
    extension=max(5,((extra_slots_per_pitch*slot+4)//5)*5)
    return {
        "unresolved":unresolved,"late_first":late_first,"avoid_late":avoid_late,
        "last_date":last_date,"extension_minutes":extension,
        "capacity":total_capacity,"total_matches":total_matches,"physical_shortfall":physical_shortfall,
        "consecutive_break":int(rules["consecutive_match_break_minutes"] or 0),
        "avoid_consecutive":bool(rules["avoid_consecutive_matches"]),
    }

def _rerun_schedule_after_recovery(tournament_id, tournament, rules, action_label):
    """Kör om schemat direkt efter en föreslagen återställningsåtgärd."""
    fresh_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),)) or rules
    started = time.perf_counter()
    try:
        optimize_group_home_away(tournament_id)
        count, unresolved, warning = generate_schedule(tournament_id, tournament, fresh_rules)
        elapsed = time.perf_counter() - started
        if unresolved:
            st.session_state["schedule_recovery"] = _schedule_recovery_context(tournament_id, tournament, fresh_rules, unresolved)
            detail = f" {warning}" if warning else ""
            st.session_state["schedule_message"] = (
                "warning",
                f"{action_label} genomfördes och schemat genererades om på {elapsed:.1f} s. "
                f"{count} matcher fick tid, men {unresolved} återstår.{detail} Nästa bästa lösning visas nedan.",
            )
        else:
            st.session_state.pop("schedule_recovery", None)
            st.session_state["schedule_message"] = (
                "success",
                f"{action_label} genomfördes. Hela schemat gick nu ihop ({count} matcher) på {elapsed:.1f} s.",
            )
    except Exception as exc:
        st.session_state["schedule_message"] = ("error", f"Åtgärden sparades men omgenereringen misslyckades: {exc}")
    st.rerun()


def render_schedule_recovery_actions(tournament_id,tournament,rules,context):
    if not context or int(context.get("unresolved",0) or 0)<=0:
        return
    unresolved=int(context.get("unresolved",0) or 0)
    st.markdown("#### CupNavi föreslår en lösning")
    st.caption(
        "Förslagen är rangordnade efter minsta praktiska förändring som bedöms ge störst effekt. "
        "Varje knapp genomför ändringen och provar schemat igen direkt. Om det fortfarande inte går ihop visas nästa bästa åtgärd automatiskt."
    )
    if context.get("physical_shortfall",0)>0:
        st.error(
            f"Cupen saknar minst {context.get('physical_shortfall',0)} teoretiska matchplatser med nuvarande plan- och öppettider "
            f"({context.get('capacity',0)} platser för {context.get('total_matches',0)} matcher)."
        )

    solutions=[]
    # Hårda kapacitetsproblem måste lösas med mer faktisk speltid/kapacitet.
    if context.get("last_date"):
        minutes=int(context.get("extension_minutes",30))
        solutions.append({
            "kind":"extend", "title":f"Förläng sista dagens plantider med {minutes} min",
            "effect":f"Skapar ungefär den extra tidskapacitet som behövs för de {unresolved} matcher som saknar tid.",
            "change":f"Endast sluttiden på sista cupdagen ändras (+{minutes} min per tillgänglig plan).",
            "certainty":"Hög" if context.get("physical_shortfall",0)>0 else "Medel–hög",
            "score": 10 if context.get("physical_shortfall",0)>0 else 30,
            "minutes":minutes,
        })
    if context.get("late_first"):
        solutions.append({
            "kind":"late_first", "title":"Släpp önskemål om senare första match",
            "effect":f"Frigör tidiga matchtider för {context['late_first']} lag som idag har en hård startbegränsning.",
            "change":"Plantider och matchregler ändras inte; endast lagens reseönskemål tas bort.",
            "certainty":"Medel–hög", "score":20 if not context.get("physical_shortfall",0) else 45,
        })
    if context.get("avoid_consecutive") and context.get("consecutive_break",0)>0:
        solutions.append({
            "kind":"break", "title":f"Minska extra lagvila ({context['consecutive_break']} min → 0 min)",
            "effect":"Frigör fler möjliga starttider mellan ett lags matcher.",
            "change":"Sportslig återhämtning påverkas, därför rankas detta efter mindre ingripande lösningar.",
            "certainty":"Medel", "score":40,
        })
    # Undvik-sen-match är en preferens/straffterm, inte en hård blockerare. Visa den därför inte som primär lösning.
    solutions.append({
        "kind":"pitch", "title":"Lägg till en extra plan/spelyta",
        "effect":"Ger en stor och robust kapacitetsökning under samtliga öppettider.",
        "change":"Kräver att arrangören faktiskt har ytterligare en spelplan tillgänglig.",
        "certainty":"Mycket hög", "score":90,
    })
    solutions.sort(key=lambda x:x["score"])

    for rank,sol in enumerate(solutions,1):
        with st.container(border=True):
            st.markdown(f"**{rank}. {sol['title']}**")
            a,b=st.columns([3,1])
            a.caption(sol["effect"] + " " + sol["change"])
            b.markdown(f"**Bedömd effekt:** {sol['certainty']}")
            if sol["kind"]=="extend":
                minutes=sol["minutes"]
                label=f"Tillämpa +{minutes} min och generera om"
                if st.button(label,key=f"recover_extend_{tournament_id}_{rank}",use_container_width=True,type="primary" if rank==1 else "secondary"):
                    rows=pitch_day_windows(tournament_id,int(rules["pitch_count"]))
                    changed=0
                    for row in rows:
                        if str(row["play_date"])!=str(context["last_date"]): continue
                        old=datetime.strptime(row["end_time"],"%H:%M")
                        proposed=min(old+timedelta(minutes=minutes),datetime.strptime("23:55","%H:%M"))
                        new=proposed.strftime("%H:%M")
                        if new>row["end_time"]:
                            save_pitch_day_window(tournament_id,int(row["pitch_number"]),row["play_date"],row["start_time"],new,True); changed+=1
                    _rerun_schedule_after_recovery(tournament_id,tournament,rules,f"Plantiderna förlängdes på {changed} plan(er) med upp till {minutes} minuter")
            elif sol["kind"]=="late_first":
                if st.button("Ta bort reservationerna och generera om",key=f"recover_late_{tournament_id}_{rank}",use_container_width=True,type="primary" if rank==1 else "secondary"):
                    run("UPDATE teams SET late_first_match=0,earliest_first_time=NULL WHERE tournament_id=? AND late_first_match=1",(int(tournament_id),))
                    run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",(int(tournament_id),))
                    _rerun_schedule_after_recovery(tournament_id,tournament,rules,"Lagens önskemål om senare första match togs bort")
            elif sol["kind"]=="break":
                if st.button("Sätt extrapusen till 0 min och generera om",key=f"recover_break_{tournament_id}_{rank}",use_container_width=True,type="primary" if rank==1 else "secondary"):
                    run("UPDATE schedule_rules SET consecutive_match_break_minutes=0 WHERE tournament_id=?",(int(tournament_id),))
                    run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",(int(tournament_id),))
                    _rerun_schedule_after_recovery(tournament_id,tournament,rules,"Extra lagvila sattes till 0 minuter")
            elif sol["kind"]=="pitch":
                if st.button("Lägg till 1 plan och generera om",key=f"recover_pitch_{tournament_id}_{rank}",use_container_width=True,type="primary" if rank==1 else "secondary"):
                    new_count=int(rules["pitch_count"] or 1)+1
                    run("UPDATE schedule_rules SET pitch_count=? WHERE tournament_id=?",(new_count,int(tournament_id)))
                    ensure_pitch_definitions(tournament_id,new_count)
                    ensure_pitch_day_windows(tournament_id,tournament,new_count,rules["first_match_time"],rules["latest_kickoff_time"])
                    run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",(int(tournament_id),))
                    _rerun_schedule_after_recovery(tournament_id,tournament,rules,f"Plan {new_count} lades till med standardtider")

    if context.get("avoid_late"):
        st.caption(
            f"Obs: {context['avoid_late']} lag har önskemål om att undvika den senaste gruppspelsmatchen. "
            "Detta är en mjuk prioritering och blockerar inte i sig schemaläggningen, därför visas den inte som en huvudlösning."
        )

def _autosave_tournament_field(tournament_id, column, key, cast=None, dirty=False):
    value = st.session_state.get(key)
    if cast is not None:
        value = cast(value)
    run(f"UPDATE tournaments SET {column}=?{',schedule_dirty=1,is_published=0' if dirty else ''} WHERE id=?", (value, int(tournament_id)))
    if dirty:
        run("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (int(tournament_id),))
    st.session_state[f"autosave_notice_{tournament_id}"] = "✓ Sparat automatiskt"

def _autosave_rule_field(tournament_id, column, key, cast=None):
    value = st.session_state.get(key)
    if cast is not None:
        value = cast(value)
    run(f"UPDATE schedule_rules SET {column}=? WHERE tournament_id=?", (value, int(tournament_id)))
    run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?", (int(tournament_id),))
    run("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (int(tournament_id),))
    st.session_state[f"autosave_notice_{tournament_id}"] = "✓ Sparat automatiskt"


def weekday_short(value):
    if value is None:
        return ""
    names_sv = ["mån", "tis", "ons", "tors", "fre", "lör", "sön"]
    names_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    names = names_en if current_language() == "en" else names_sv
    return names[value.weekday()]


def date_with_weekday(value):
    return f"{weekday_short(value)} {value.isoformat()}" if value else ""


def _visitor_header(name):
    """Läs en HTTP-header om Streamlit exponerar den, annars tom sträng."""
    try:
        headers = st.context.headers
        return str(headers.get(name, "") or headers.get(name.lower(), "") or "").strip()
    except Exception:
        return ""


def _visitor_device_type(user_agent):
    ua = (user_agent or "").lower()
    if any(token in ua for token in ("ipad", "tablet")):
        return "Surfplatta"
    if any(token in ua for token in ("mobi", "iphone", "android")):
        return "Mobil"
    return "Dator"


def _visitor_browser(user_agent):
    ua = (user_agent or "").lower()
    if "edg/" in ua:
        return "Edge"
    if "opr/" in ua or "opera" in ua:
        return "Opera"
    if "chrome/" in ua and "edg/" not in ua:
        return "Chrome"
    if "safari/" in ua and "chrome/" not in ua:
        return "Safari"
    if "firefox/" in ua:
        return "Firefox"
    return "Övrig"


def _visitor_source(referrer):
    ref = (referrer or "").lower()
    if not ref:
        return "Direkt / okänd"
    if "google." in ref:
        return "Google"
    if "facebook." in ref or "messenger." in ref or "l.facebook." in ref:
        return "Facebook / Messenger"
    if "whatsapp." in ref:
        return "WhatsApp"
    if "instagram." in ref:
        return "Instagram"
    return "Annan webbplats"


def track_public_visit(tournament_id):
    """Integritetsvänlig besöksmätning. Ingen IP-adress eller personuppgift lagras."""
    session_key = f"_cupnavi_visitor_session_{tournament_id}"
    token = st.session_state.get(session_key)
    if not token:
        token = hashlib.sha256(os.urandom(32)).hexdigest()
        st.session_state[session_key] = token

    now_dt = datetime.now()
    now_iso = now_dt.isoformat(timespec="seconds")
    throttle_key = f"_cupnavi_visit_last_count_{tournament_id}"
    previous_count_at = st.session_state.get(throttle_key)
    count_view = (
        previous_count_at is None
        or (now_dt - previous_count_at).total_seconds() >= 300
    )
    if not count_view:
        return

    user_agent = _visitor_header("User-Agent")
    referrer = _visitor_header("Referer")
    device_type = _visitor_device_type(user_agent)
    browser = _visitor_browser(user_agent)
    source = _visitor_source(referrer)

    # Ett enda atomiskt UPSERT i stället för SELECT + INSERT/UPDATE. Det sparar
    # ett helt remote DB-varv på första publika sidladdningen och vid 5-minutersräkning.
    run(
        """INSERT INTO visitor_sessions(
               tournament_id,session_token,first_seen,last_seen,view_count,
               device_type,browser,source
           ) VALUES(?,?,?,?,1,?,?,?)
           ON CONFLICT(tournament_id,session_token) DO UPDATE SET
               last_seen=excluded.last_seen,
               view_count=visitor_sessions.view_count+1,
               device_type=excluded.device_type,
               browser=excluded.browser,
               source=excluded.source""",
        (tournament_id, token, now_iso, now_iso, device_type, browser, source),
    )
    st.session_state[throttle_key] = now_dt


@st.cache_data(show_spinner=False)
def qr_png_bytes(value):
    """QR-bilden är deterministisk och behöver inte byggas om vid varje rerun."""
    if qrcode is None:
        return None
    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def normalize_website_url(value):
    """Normalisera en frivillig webbplatsadress och validera utan regex."""
    value = str(value or "").strip()
    if not value:
        return None

    # Gör det enklare för arrangören: example.se blir https://example.se
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlparse(candidate)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "Webbplatsen verkar inte vara giltig. Ange till exempel https://example.se."
        )

    # Undvik blanksteg/control chars i hostnamn.
    if any(ch.isspace() for ch in parsed.netloc):
        raise ValueError(
            "Webbplatsen verkar inte vara giltig. Ange till exempel https://example.se."
        )
    return candidate


def image_data_uri(uploaded_file):
    """Konvertera en liten uppladdad sponsorlogga till en portabel data-URI."""
    if uploaded_file is None:
        return None
    raw = uploaded_file.getvalue()
    if len(raw) > 1_500_000:
        raise ValueError("Logotypen får vara högst 1,5 MB.")
    mime = uploaded_file.type or "image/png"
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError("Logotypen måste vara PNG, JPG eller WEBP.")
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"



TRANSLATIONS = {
    "sv": {},
    "en": {
        "Välj språk": "Choose language", "Turneringar": "Tournaments",
        "Välj läge": "Choose mode", "Turneringsvy": "Tournament view", "Om": "About",
        "Matchrapportör": "Match reporter", "Visningsläge": "Mode",
        "Aktiv turnering": "Active tournament", "Instruktioner": "Instructions",
        "Översikt": "Overview", "Kontroller": "Checks", "Lag": "Teams",
        "Grupper": "Groups", "Trupper": "Squads", "Domare": "Referees",
        "Schema": "Schedule", "Tabeller": "Standings", "Matcher": "Matches",
        "Händelser": "Events", "Slutspel": "Playoffs", "Skytteligor": "Leaderboards",
        "Erbjudanden": "Offers", "Sponsorer": "Sponsors", "Funktionärer": "Staff",
        "Import": "Import", "Besök": "Visitors", "Besöksstatistik": "Visitor analytics",
        "Spelschema": "Schedule", "Resultat": "Results", "Topplistor": "Statistics",
        "Spelschema & resultat": "Schedule & results", "Tabeller gruppspel": "Group-stage tables",
        "Partners": "Partners", "Information": "Information", "Alla matcher": "All matches",
        "En grupp": "A group", "Ett lag": "A team", "En plan": "A pitch",
        "Vad vill du visa?": "What do you want to show?", "Välj grupp": "Choose group",
        "Välj lag": "Choose team", "Alla lag": "All teams", "Visa alla lag": "Show all teams", "Välj plan": "Choose pitch", "Plan": "Pitch",
        "Skytteliga": "Top scorers", "Assistliga": "Assists",
        "Varningar och utvisningar": "Cards", "Praktisk information": "Practical information",
        "Cupens partners": "Tournament partners",
        "Erbjudanden för cupdeltagare": "Offers for tournament participants",
        "Matchhändelser": "Match events", "Arena": "Venue", "Kiosk": "Refreshments",
        "Kontakta arrangören": "Contact the organizer",
        "Frågor eller feedback": "Questions or feedback", "Följ cupen": "Follow the tournament",
        "Lösenord": "Password", "Adminlösenord": "Admin password",
        "Logga in": "Sign in", "Logga ut": "Sign out", "Fel lösenord.": "Incorrect password.",
        "Inloggad som administratör": "Signed in as administrator",
        "Inloggad som matchrapportör": "Signed in as match reporter",
        "Administratörsinloggning": "Administrator sign-in",
        "Administration": "Administration", "Period": "Period",
        "Senaste 7 dagarna": "Last 7 days", "Senaste 30 dagarna": "Last 30 days",
        "Senaste 90 dagarna": "Last 90 days", "All tid": "All time",
        "Unika sessioner": "Unique sessions", "Sidvisningar": "Page views",
        "Besök idag": "Visits today", "Sidvisningar idag": "Page views today",
        "Aktiva senaste 30 min": "Active in last 30 min", "Utveckling över tid": "Trend over time",
        "Enheter": "Devices", "Webbläsare": "Browsers", "Trafikkälla": "Traffic source",
        "Senaste besöken": "Recent visits", "Mobil": "Mobile", "Dator": "Desktop",
        "Surfplatta": "Tablet", "Direkt / okänd": "Direct / unknown",
        "Skapa": "Create", "Spara": "Save", "Avbryt": "Cancel", "Publicera": "Publish",
        "Avpublicera": "Unpublish", "Namn": "Name", "Namn *": "Name *", "Telefon": "Phone",
        "E-post": "Email", "Webbplats": "Website", "Rubrik": "Title", "Rubrik *": "Title *",
        "Beskrivning / villkor": "Description / terms", "Kort beskrivning": "Short description",
        "Visningsordning": "Display order", "Grupp": "Group", "Gruppnamn": "Group name",
        "Lagnamn": "Team name", "Spelare": "Player", "Tröjnummer": "Shirt number",
        "Födelseår": "Birth year", "Position": "Position", "Roll": "Role", "Roll *": "Role *",
        "Datum": "Date", "Avspark": "Kick-off", "Antal planer": "Number of pitches",
        "Första matchstart": "First kick-off", "Spelort": "Location",
        "Turneringens namn": "Tournament name", "Planerat antal lag": "Planned number of teams",
        "Första cupdag": "First tournament day", "Sista cupdag": "Last tournament day",
        "Arenaadress": "Venue address", "Arrangörens telefonnummer": "Organizer phone number",
        "E-post för feedback": "Feedback email", "Övrig information": "Other information",
        "Mål": "Goals", "Assist": "Assists", "Varningar": "Yellow cards",
        "Utvisningar": "Red cards", "Match": "Match", "Fas": "Stage",
        "Hemmalag": "Home team", "Bortalag": "Away team", "Hemmamål": "Home goals",
        "Bortamål": "Away goals", "Publicerad": "Published", "Publicerade": "Published",
        "Ej publicerade": "Unpublished", "Schemalagda": "Scheduled",
        "Schemalagda matcher": "Scheduled matches", "Gruppspelsmatcher": "Group-stage matches",
        "CupNavi Score": "CupNavi Score", "Domarcentral": "Referee centre",
        "Offlineutkast": "Offline draft", "Cupverktyg": "Tournament tools",
        "Cupflöde": "Tournament feed", "Cupkarta": "Tournament map",
        "Kvalitet": "Quality", "Försening": "Delay", "Historik": "History",
        "Summering": "Summary", "Sport": "Sport", "av": "of",
    }
}

EN_PHRASES = {
    "Skapa och publicera schema": "Create and publish schedule",
    "Matcher och resultat": "Matches and results",
    "Registrera resultat och domare": "Enter results and referees",
    "Registrera mål, assist, varningar och utvisningar": "Enter goals, assists, yellow cards and red cards",
    "Dela cupen med QR-kod": "Share tournament with QR code",
    "Lägg till": "Add", "Ta bort": "Delete", "Redigera": "Edit",
    "Spara ändringar": "Save changes", "Spara alla": "Save all", "Ladda ner": "Download",
    "Välj turnering": "Choose tournament", "Välj match": "Choose match",
    "Välj och spara": "Choose and save", "Ange ett": "Enter a", "Ange en": "Enter a",
    "Ange": "Enter", "Det finns ännu inga": "There are no", "Det finns ännu ingen": "There is no",
    "Det finns inga": "There are no", "Det finns ingen": "There is no",
    "Här visas": "This page shows", "Här kan du": "Here you can",
    "Här ställer du in": "Here you configure", "Här granskar du": "Here you review",
    "Klicka på": "Click", "Gå till": "Go to", "under fliken": "under the tab",
    "i den publika turneringsvyn": "in the public tournament view",
    "i turneringsvyn": "in the tournament view", "den publika turneringsvyn": "the public tournament view",
    "spelschemat": "the schedule", "schemat": "the schedule", "turneringen": "the tournament",
    "gruppen": "the group", "laget": "the team", "matchen": "the match", "spelaren": "the player",
    "domaren": "the referee", "publikt": "publicly", "automatiskt": "automatically",
    "manuellt": "manually", "före publicering": "before publishing", "efter publicering": "after publishing",
    "kan inte": "cannot", "måste": "must", "behöver": "needs to", "sparas": "is saved",
    "skapade": "created", "skapats": "been created", "publiceras": "is published",
    "registrerade": "registered", "registreras": "are registered", "uppdateras": "is updated",
    "ändras": "changes", "kontrolleras": "is checked", "visas": "is shown", "saknas": "is missing",
    "resultat": "results", "matchhändelser": "match events", "slutspel": "playoffs",
    "gruppspel": "group stage", "grupper": "groups", "spelare": "players",
    "domare": "referees", "matcher": "matches", "schema": "schedule",
    "turnering": "tournament", "varningar": "warnings", "utvisningar": "red cards",
    "mål": "goals", "assist": "assists", "poäng": "points", "planer": "pitches",
}

EN_WORDS = {
    "och": "and", "eller": "or", "för": "for", "från": "from", "till": "to",
    "med": "with", "utan": "without", "är": "is", "har": "has", "ska": "should",
    "kan": "can", "inte": "not", "alla": "all", "hela": "entire", "vald": "selected",
    "valda": "selected", "aktuell": "current", "aktuella": "current", "ny": "new",
    "nya": "new", "första": "first", "sista": "last", "innan": "before", "efter": "after",
    "ovan": "above", "nedan": "below", "direkt": "directly", "endast": "only",
    "även": "also", "inga": "no", "ingen": "no", "ett": "a", "en": "a",
    "den": "the", "det": "it", "de": "the", "du": "you", "din": "your", "ditt": "your",
}

def current_language():
    return st.session_state.get("language", "sv")

def _translate_english_fallback(value):
    result = str(value)
    for source, target in sorted(EN_PHRASES.items(), key=lambda item: len(item[0]), reverse=True):
        result = re.sub(re.escape(source), target, result, flags=re.IGNORECASE)
    for source, target in EN_WORDS.items():
        result = re.sub(rf"(?<!\w){re.escape(source)}(?!\w)", target, result, flags=re.IGNORECASE)
    return result

def tr(value):
    if value is None or current_language() != "en" or not isinstance(value, str):
        return value
    exact = TRANSLATIONS["en"].get(value)
    if exact is not None:
        return exact
    if value.lstrip().startswith(("http://", "https://", "<style", "<div", "<script")):
        return value
    return _translate_english_fallback(value)

def _translate_dataframe_for_display(dataframe):
    if current_language() != "en" or dataframe is None or not hasattr(dataframe, "rename"):
        return dataframe
    return dataframe.rename(columns={column: tr(column) for column in dataframe.columns})

def _install_streamlit_translation_hooks():
    if getattr(st, "_cupnavi_translation_hooks", False):
        return
    from streamlit.delta_generator import DeltaGenerator

    simple_methods = (
        "title", "header", "subheader", "caption", "info", "warning", "error", "success",
        "button", "download_button", "text_input", "text_area", "checkbox", "number_input",
        "date_input", "time_input", "file_uploader", "form_submit_button", "metric", "expander",
    )
    for method_name in simple_methods:
        original = getattr(DeltaGenerator, method_name, None)
        if original is None:
            continue
        def make_wrapper(original_method):
            def wrapper(self, *args, **kwargs):
                args = list(args)
                if args and isinstance(args[0], str):
                    args[0] = tr(args[0])
                if isinstance(kwargs.get("placeholder"), str):
                    kwargs["placeholder"] = tr(kwargs["placeholder"])
                if isinstance(kwargs.get("help"), str):
                    kwargs["help"] = tr(kwargs["help"])
                return original_method(self, *args, **kwargs)
            return wrapper
        setattr(DeltaGenerator, method_name, make_wrapper(original))

    original_markdown = DeltaGenerator.markdown
    def markdown_wrapper(self, body, *args, **kwargs):
        if isinstance(body, str) and not kwargs.get("unsafe_allow_html"):
            body = tr(body)
        return original_markdown(self, body, *args, **kwargs)
    DeltaGenerator.markdown = markdown_wrapper

    original_tabs = DeltaGenerator.tabs
    def tabs_wrapper(self, tabs, *args, **kwargs):
        if current_language() == "en":
            tabs = [tr(item) if isinstance(item, str) else item for item in tabs]
        return original_tabs(self, tabs, *args, **kwargs)
    DeltaGenerator.tabs = tabs_wrapper

    for method_name in ("selectbox", "radio"):
        original = getattr(DeltaGenerator, method_name)
        def make_option_wrapper(original_method):
            def wrapper(self, label, options, *args, **kwargs):
                label = tr(label) if isinstance(label, str) else label
                existing = kwargs.get("format_func")
                if current_language() == "en":
                    if existing:
                        kwargs["format_func"] = lambda value, f=existing: tr(f(value))
                    else:
                        kwargs["format_func"] = lambda value: tr(value) if isinstance(value, str) else value
                return original_method(self, label, options, *args, **kwargs)
            return wrapper
        setattr(DeltaGenerator, method_name, make_option_wrapper(original))

    original_data_editor = DeltaGenerator.data_editor
    def data_editor_wrapper(self, data, *args, **kwargs):
        if current_language() != "en" or not hasattr(data, "columns"):
            return original_data_editor(self, data, *args, **kwargs)
        rename_map = {column: tr(column) for column in data.columns}
        reverse_map = {value: key for key, value in rename_map.items()}
        display_data = data.rename(columns=rename_map)
        if isinstance(kwargs.get("disabled"), list):
            kwargs["disabled"] = [rename_map.get(x, x) for x in kwargs["disabled"]]
        if isinstance(kwargs.get("column_order"), list):
            kwargs["column_order"] = [rename_map.get(x, x) for x in kwargs["column_order"]]
        if isinstance(kwargs.get("column_config"), dict):
            kwargs["column_config"] = {rename_map.get(k, k): v for k, v in kwargs["column_config"].items()}
        result = original_data_editor(self, display_data, *args, **kwargs)
        return result.rename(columns=reverse_map) if hasattr(result, "rename") else result
    DeltaGenerator.data_editor = data_editor_wrapper

    st._cupnavi_translation_hooks = True


st.set_page_config(page_title="CupNavi", page_icon="🏆", layout="wide")

st.html("""
<style>
/* ===== DIALOGKONTRAST v41 ===== */
div[role="dialog"] {
    background:#0b1220 !important;
    color:#f8fafc !important;
}
div[role="dialog"] h1,
div[role="dialog"] h2,
div[role="dialog"] h3,
div[role="dialog"] p,
div[role="dialog"] span,
div[role="dialog"] label {
    color:#f8fafc !important;
}
div[role="dialog"] [data-testid="stAlert"] {
    background:#3f1d24 !important;
    border:1px solid #fca5a5 !important;
}
div[role="dialog"] [data-testid="stAlert"] *,
div[role="dialog"] [data-testid="stAlert"] p,
div[role="dialog"] [data-testid="stAlert"] span {
    color:#fee2e2 !important;
}
div[role="dialog"] [data-testid="stCaptionContainer"],
div[role="dialog"] .stCaptionContainer {
    color:#cbd5e1 !important;
}
div[role="dialog"] .stButton > button[kind="primary"] {
    background:#15803d !important;
    border-color:#15803d !important;
    color:#ffffff !important;
}
div[role="dialog"] .stButton > button[kind="primary"] * {
    color:#ffffff !important;
}
div[role="dialog"] .stButton > button:not([kind="primary"]) {
    background:#ffffff !important;
    border-color:#cbd5e1 !important;
    color:#0f172a !important;
}
div[role="dialog"] .stButton > button:not([kind="primary"]) * {
    color:#0f172a !important;
}

          /* ===== CUPNAVI DESIGN SYSTEM v46 ===== */
          :root {
            --cn-bg:#F6F8FA;
            --cn-surface:#FFFFFF;
            --cn-ink:#172033;
            --cn-muted:#64748B;
            --cn-border:#D7DEE5;
            --cn-green:#166534;
            --cn-green-soft:#DCFCE7;
            --cn-amber:#B45309;
            --cn-amber-soft:#FEF3C7;
            --cn-red:#B91C1C;
            --cn-blue:#1D4ED8;
            --cn-radius:12px;
          }

          .cn-dashboard-grid {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:12px;
            margin:10px 0 18px;
          }
          .cn-status-card {
            background:var(--cn-surface);
            border:1px solid var(--cn-border);
            border-radius:var(--cn-radius);
            padding:14px 15px;
            min-height:92px;
          }
          .cn-status-card .cn-label {
            color:var(--cn-muted) !important;
            font-size:12px;
            font-weight:750;
            text-transform:uppercase;
            letter-spacing:.03em;
          }
          .cn-status-card .cn-value {
            color:var(--cn-ink) !important;
            font-size:27px;
            line-height:1.1;
            font-weight:850;
            margin-top:6px;
          }
          .cn-status-card .cn-sub {
            color:var(--cn-muted) !important;
            font-size:12px;
            margin-top:7px;
          }

          .cn-workflow {
            display:grid;
            grid-template-columns:repeat(3,minmax(0,1fr));
            gap:10px;
            margin:12px 0 16px;
          }
          .cn-step {
            background:#fff;
            border:1px solid var(--cn-border);
            border-radius:10px;
            padding:11px 13px;
          }
          .cn-step.done {
            background:var(--cn-green-soft);
            border-color:#86EFAC;
          }
          .cn-step.warn {
            background:var(--cn-amber-soft);
            border-color:#FCD34D;
          }
          .cn-step.todo {
            background:#F8FAFC;
          }
          .cn-step .title {
            color:var(--cn-ink) !important;
            font-weight:800;
          }
          .cn-step .meta {
            color:var(--cn-muted) !important;
            margin-top:4px;
            font-size:12px;
          }
          .cn-action-banner {
            background:var(--cn-amber-soft);
            border:1px solid #FCD34D;
            border-radius:12px;
            padding:14px 16px;
            margin:10px 0 14px;
          }
          .cn-action-banner strong { color:#78350F !important; }
          .cn-action-banner span { color:#92400E !important; }

          @media (max-width:900px) {
            .cn-dashboard-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
            .cn-workflow { grid-template-columns:repeat(2,minmax(0,1fr)); }
          }
          @media (max-width:520px) {
            .cn-dashboard-grid,
            .cn-workflow { grid-template-columns:1fr; }
          }


          /* ===== UI/UX FAS 2 v47 ===== */
          .cn-next-match {
            background:linear-gradient(135deg,#0f172a,#1e3a5f);
            border:1px solid #334155;
            border-radius:14px;
            padding:16px;
            margin:12px 0 16px;
            color:#ffffff;
          }
          .cn-next-match * { color:#ffffff !important; }
          .cn-next-match .eyebrow {
            font-size:11px;
            font-weight:850;
            letter-spacing:.08em;
            text-transform:uppercase;
            opacity:.78;
          }
          .cn-next-match .teams {
            margin-top:7px;
            font-size:23px;
            font-weight:900;
            line-height:1.2;
          }
          .cn-next-match .meta {
            margin-top:8px;
            font-size:13px;
            opacity:.88;
          }

          .cn-admin-match {
            display:grid;
            grid-template-columns:74px minmax(0,1fr) minmax(0,1fr) 150px;
            gap:10px;
            align-items:center;
            background:#ffffff;
            border:1px solid #d7dee5;
            border-radius:11px;
            padding:10px 12px;
            margin:7px 0;
          }
          .cn-admin-match.issue {
            border-left:5px solid #b45309;
            background:#fffbeb;
          }
          .cn-admin-match .number {
            font-weight:900;
            color:#166534 !important;
          }
          .cn-admin-match .team {
            font-weight:800;
            color:#172033 !important;
            overflow-wrap:anywhere;
          }
          .cn-admin-match .meta {
            color:#64748b !important;
            font-size:12px;
          }
          .cn-issue-pill {
            display:inline-block;
            margin:3px 4px 0 0;
            padding:3px 7px;
            border-radius:999px;
            background:#fef3c7;
            border:1px solid #fcd34d;
            color:#92400e !important;
            font-size:11px;
            font-weight:800;
          }

          @media (max-width:700px) {
            .cn-admin-match {
              grid-template-columns:62px 1fr;
            }
            .cn-admin-match .ref-col {
              grid-column:1 / -1;
            }
            .cn-next-match .teams { font-size:20px; }
          }


          /* ===== PUBLIKT SCHEMAFILTER v52 ===== */
          div[data-testid="stRadio"] > div {
            gap:8px;
          }
          div[data-testid="stRadio"] label {
            border:1px solid #cbd5e1;
            border-radius:999px;
            padding:7px 12px;
            background:#ffffff;
          }


          /* ===== PUBLIKA MATCHHÄNDELSER v56 ===== */
          .cn-match-events {
            margin-top:10px;
            padding-top:9px;
            border-top:1px solid #e2e8f0;
          }
          .cn-events-title {
            text-align:center;
            color:#64748b !important;
            font-size:11px;
            font-weight:800;
            text-transform:uppercase;
            letter-spacing:.04em;
            margin-bottom:6px;
          }
          .cn-events-list {
            display:flex;
            justify-content:center;
            flex-wrap:wrap;
            gap:6px;
          }
          .cn-event {
            display:inline-block;
            border-radius:999px;
            padding:4px 8px;
            font-size:12px;
            font-weight:750;
            line-height:1.2;
          }
          .cn-event.cn-goal {
            background:#ecfdf5;
            border:1px solid #86efac;
            color:#166534 !important;
          }
          .cn-event.cn-red {
            background:#fef2f2;
            border:1px solid #fca5a5;
            color:#991b1b !important;
          }


          .cn-event-teams {
            display:grid;
            grid-template-columns:repeat(2,minmax(0,1fr));
            gap:8px;
          }
          .cn-event-team {
            background:#f8fafc;
            border:1px solid #e2e8f0;
            border-radius:9px;
            padding:7px;
            min-width:0;
          }
          .cn-event-team-name {
            text-align:center;
            color:#334155 !important;
            font-size:12px;
            font-weight:900;
            margin-bottom:6px;
            overflow-wrap:anywhere;
          }
          .cn-event-team .cn-events-list {
            justify-content:center;
          }
          @media (max-width:480px) {
            .cn-event-teams { grid-template-columns:1fr 1fr; gap:6px; }
            .cn-event { font-size:11px; padding:4px 6px; }
          }


          .cn-organizer-contact {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:12px;
            flex-wrap:wrap;
          }
          .cn-call-button {
            display:inline-block;
            background:#166534;
            color:#ffffff !important;
            text-decoration:none !important;
            font-weight:850;
            border-radius:10px;
            padding:10px 14px;
            white-space:nowrap;
          }
          .cn-call-button:hover { background:#14532d; color:#ffffff !important; }
          @media (max-width:480px) {
            .cn-organizer-contact { align-items:stretch; }
            .cn-call-button { width:100%; text-align:center; box-sizing:border-box; }
          }


          .cn-email-button {
            display:inline-block;
            background:#1e3a8a;
            color:#ffffff !important;
            text-decoration:none !important;
            font-weight:850;
            border-radius:10px;
            padding:10px 14px;
            white-space:nowrap;
          }
          .cn-email-button:hover { background:#172554; color:#ffffff !important; }
          @media (max-width:480px) {
            .cn-email-button { width:100%; text-align:center; box-sizing:border-box; }
          }


          /* v85 import wizard */
          .cn-import-steps {
            display:grid;
            grid-template-columns:repeat(5, minmax(0,1fr));
            gap:8px;
            margin:10px 0 20px 0;
          }
          .cn-import-steps div {
            display:flex;
            align-items:center;
            gap:7px;
            padding:8px 9px;
            border:1px solid #e2e8f0;
            border-radius:10px;
            background:#f8fafc;
            color:#475569;
            font-size:12px;
            min-width:0;
          }
          .cn-import-steps strong {
            display:inline-flex;
            align-items:center;
            justify-content:center;
            min-width:24px;
            height:24px;
            border-radius:999px;
            background:#e0e7ff;
            color:#3730a3;
          }
          @media (max-width:760px) {
            .cn-import-steps { grid-template-columns:1fr; gap:5px; }
            .cn-import-steps div { padding:7px 9px; }
          }

          /* v83 UX polish */
          .cn-admin-nav-group-title {
            margin:14px 0 6px 0;
            font-size:12px;
            font-weight:850;
            letter-spacing:.04em;
            text-transform:uppercase;
            color:#64748b;
          }
          .cn-current-admin-page {
            display:flex;
            align-items:center;
            gap:8px;
            margin:12px 0 2px 0;
            padding:8px 11px;
            border-radius:10px;
            background:#f8fafc;
            border:1px solid #e2e8f0;
            font-size:13px;
            color:#64748b;
          }
          .cn-current-admin-page strong { color:#172033; }
          .cn-admin-status-strip {
            display:flex;
            align-items:center;
            flex-wrap:wrap;
            gap:9px;
            margin:-4px 0 12px 0;
            font-size:13px;
            color:#475569;
          }
          .cn-admin-status-pill {
            display:inline-block;
            padding:4px 9px;
            border-radius:999px;
            background:#ecfdf5;
            border:1px solid #bbf7d0;
            color:#166534;
            font-weight:800;
          }
          div[data-testid="stButton"] > button,
          div[data-testid="stDownloadButton"] > button { min-height:44px; }
          button:focus-visible, a:focus-visible, input:focus-visible,
          textarea:focus-visible, select:focus-visible {
            outline:3px solid rgba(37,99,235,.35) !important;
            outline-offset:2px !important;
          }
          @media (max-width:640px) {
            .cn-current-admin-page { align-items:flex-start; flex-direction:column; gap:2px; }
          }

          .cn-share-card {
            border:1px solid #d7dee5;
            border-radius:14px;
            background:#ffffff;
            padding:14px 16px;
            margin:10px 0 16px 0;
            box-shadow:0 3px 10px rgba(15,23,42,.05);
          }
          .cn-share-title {
            font-size:16px;
            font-weight:850;
            color:#172033;
          }
          .cn-share-subtitle {
            margin-top:2px;
            font-size:13px;
            color:#64748b;
          }
          .cn-share-buttons {
            display:flex;
            flex-wrap:wrap;
            gap:8px;
            margin-top:11px;
          }
          .cn-share-button {
            display:inline-block;
            text-decoration:none !important;
            font-weight:800;
            border-radius:10px;
            padding:9px 13px;
            border:1px solid #cbd5e1;
            color:#172033 !important;
            background:#f8fafc;
          }
          .cn-share-messenger { background:#eef4ff; border-color:#bfdbfe; color:#1d4ed8 !important; }
          .cn-share-whatsapp { background:#f0fdf4; border-color:#bbf7d0; color:#166534 !important; }
          .cn-share-email { background:#eff6ff; border-color:#bfdbfe; color:#1e3a8a !important; }
          .cn-share-sms { background:#f8fafc; border-color:#cbd5e1; color:#334155 !important; }
          .cn-share-url {
            margin-top:10px;
            font-size:11px;
            color:#64748b;
            overflow-wrap:anywhere;
          }
          @media (max-width:480px) {
            .cn-share-buttons { display:grid; grid-template-columns:1fr 1fr; }
            .cn-share-button { text-align:center; box-sizing:border-box; }
          }


          .cn-instagram-button {
            display:inline-block;
            background:#7c3aed;
            color:#ffffff !important;
            text-decoration:none !important;
            font-weight:850;
            border-radius:10px;
            padding:10px 14px;
            white-space:nowrap;
          }
          .cn-instagram-button:hover { background:#6d28d9; color:#ffffff !important; }
          @media (max-width:480px) {
            .cn-instagram-button { width:100%; text-align:center; box-sizing:border-box; }
          }

</style>
""")


# Global arbetsindikator: visas automatiskt medan Streamlit kör om sidan efter interaktion.
st.html("""
<style>
/* Streamlits running-status finns medan Python-skriptet arbetar.
   Förstärk den till en tydlig CupNavi-indikator utan att blockera sidan. */
[data-testid="stStatusWidget"] {
    position: fixed !important;
    top: 12px !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 999999 !important;
    background: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #334155 !important;
    border-radius: 999px !important;
    padding: 8px 14px !important;
    box-shadow: 0 8px 24px rgba(15,23,42,.22) !important;
}
[data-testid="stStatusWidget"]::after {
    content: "  CupNavi arbetar…";
    color: #ffffff;
    font-weight: 800;
    white-space: nowrap;
}
[data-testid="stSpinner"] {
    font-weight: 800 !important;
}
</style>
""")



def inject_custom_css():
    """CupNavis samlade visuella tema: ljust, konsekvent och med hög läsbarhet."""
    st.markdown(
        """
        <style>
          :root {
            --cup-ink:#172033;
            --cup-ink-soft:#334155;
            --cup-muted:#5b6878;
            --cup-bg:#f4f7fa;
            --cup-surface:#ffffff;
            --cup-surface-soft:#eef3f7;
            --cup-border:#cfd8e3;
            --cup-border-strong:#b8c5d3;
            --cup-green:#166534;
            --cup-green-hover:#14532d;
            --cup-blue:#1e3a5f;
            --cup-focus:#2563eb;
            --cup-danger:#991b1b;
            --cup-warning:#92400e;
          }

          /* ---------- Grundyta och typografi ---------- */
          html, body, .stApp {
            background:var(--cup-bg) !important;
            color:var(--cup-ink) !important;
          }
          .stApp { min-height:100vh; min-height:100dvh; }
          [data-testid="stHeader"] { background:rgba(244,247,250,.96) !important; }
          [data-testid="stToolbar"] { color:var(--cup-ink) !important; }
          .block-container {
            padding-top:1.35rem;
            padding-bottom:3rem;
            max-width:1480px;
          }
          .stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6 {
            color:var(--cup-ink) !important;
            letter-spacing:-.015em;
            line-height:1.2;
          }
          .stApp h1 { font-weight:800; }
          .stApp h2,.stApp h3 { font-weight:750; }
          .stApp p,.stApp li,.stApp label,.stApp small,
          .stApp [data-testid="stMarkdownContainer"],
          .stApp [data-testid="stCaptionContainer"],
          .stApp [data-testid="stWidgetLabel"],
          .stApp [data-testid="stMetricLabel"] {
            color:var(--cup-ink-soft) !important;
          }
          .stApp [data-testid="stCaptionContainer"],
          .stApp [data-testid="stCaptionContainer"] p {
            color:var(--cup-muted) !important;
          }
          .stApp a { color:#1d4ed8 !important; text-decoration-color:#93c5fd; }
          .stApp hr { border-color:var(--cup-border) !important; }

          /* ---------- ÅTERÖPPNA DOLD SIDOMENY v70 ---------- */
          [data-testid="collapsedControl"],
          [data-testid="stSidebarCollapsedControl"] {
            display:flex !important;
            visibility:visible !important;
            opacity:1 !important;
            position:fixed !important;
            top:10px !important;
            left:10px !important;
            z-index:1000000 !important;
            width:auto !important;
            height:auto !important;
            pointer-events:auto !important;
          }

          [data-testid="collapsedControl"] button,
          [data-testid="stSidebarCollapsedControl"] button {
            display:flex !important;
            visibility:visible !important;
            opacity:1 !important;
            align-items:center !important;
            justify-content:center !important;
            width:42px !important;
            min-width:42px !important;
            height:42px !important;
            min-height:42px !important;
            padding:0 !important;
            border:1px solid #94a3b8 !important;
            border-radius:11px !important;
            background:#ffffff !important;
            color:#172033 !important;
            box-shadow:0 4px 14px rgba(15,23,42,.18) !important;
            cursor:pointer !important;
            pointer-events:auto !important;
          }

          [data-testid="collapsedControl"] button svg,
          [data-testid="stSidebarCollapsedControl"] button svg {
            color:#172033 !important;
            fill:#172033 !important;
            stroke:#172033 !important;
            width:22px !important;
            height:22px !important;
          }

          [data-testid="collapsedControl"] button:hover,
          [data-testid="stSidebarCollapsedControl"] button:hover {
            background:#f1f5f9 !important;
            border-color:#64748b !important;
          }

          @media (max-width:768px) {
            [data-testid="collapsedControl"],
            [data-testid="stSidebarCollapsedControl"] {
              top:8px !important;
              left:8px !important;
            }

            [data-testid="collapsedControl"] button,
            [data-testid="stSidebarCollapsedControl"] button {
              width:46px !important;
              min-width:46px !important;
              height:46px !important;
              min-height:46px !important;
            }
          }

          /* ---------- Sidomeny: alltid ljus ---------- */
          [data-testid="stSidebar"] {
            background:#eaf0f5 !important;
            border-right:1px solid var(--cup-border) !important;
          }
          [data-testid="stSidebar"] > div { background:#eaf0f5 !important; }
          [data-testid="stSidebar"] h1,
          [data-testid="stSidebar"] h2,
          [data-testid="stSidebar"] h3,
          [data-testid="stSidebar"] p,
          [data-testid="stSidebar"] label,
          [data-testid="stSidebar"] span,
          [data-testid="stSidebar"] small,
          [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color:var(--cup-ink) !important;
          }

          /* ---------- Formulär, containers och expanders ---------- */
          [data-testid="stForm"],
          [data-testid="stVerticalBlockBorderWrapper"] {
            background:var(--cup-surface) !important;
            border-color:var(--cup-border) !important;
            border-radius:14px !important;
          }
          details[data-testid="stExpander"] {
            background:var(--cup-surface) !important;
            border:1px solid var(--cup-border) !important;
            border-radius:12px !important;
            overflow:hidden;
          }
          details[data-testid="stExpander"] summary {
            background:#f7f9fb !important;
            color:var(--cup-ink) !important;
          }
          details[data-testid="stExpander"] summary * { color:var(--cup-ink) !important; }
          [data-testid="stExpander"] details,
          [data-testid="stExpander"] summary,
          div[data-testid="stExpander"] summary,
          div[data-testid="stExpander"] details {
            background:#f7f9fb !important;
            color:var(--cup-ink) !important;
          }
          [data-testid="stExpander"] summary *,
          div[data-testid="stExpander"] summary * { color:var(--cup-ink) !important; }

          /* ---------- Inmatningsfält ---------- */
          [data-baseweb="input"],
          [data-baseweb="textarea"],
          [data-baseweb="select"] > div,
          [data-testid="stNumberInput"] [data-baseweb="input"],
          [data-testid="stDateInput"] [data-baseweb="input"],
          [data-testid="stTimeInput"] [data-baseweb="input"] {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
            border-color:var(--cup-border-strong) !important;
          }
          .stApp input,
          .stApp textarea,
          .stApp [data-baseweb="select"] input,
          .stApp [data-baseweb="select"] span,
          .stApp [data-baseweb="select"] div {
            color:var(--cup-ink) !important;
          }
          .stApp input,
          .stApp textarea {
            background:var(--cup-surface) !important;
            caret-color:var(--cup-ink) !important;
          }
          .stApp input::placeholder,.stApp textarea::placeholder {
            color:#718096 !important;
            opacity:1 !important;
          }
          [data-baseweb="input"]:focus-within,
          [data-baseweb="textarea"]:focus-within,
          [data-baseweb="select"] > div:focus-within {
            border-color:var(--cup-focus) !important;
            box-shadow:0 0 0 1px var(--cup-focus) !important;
          }

          /* Dropdown-menyer renderas ibland utanför .stApp. */
          [role="listbox"], [data-baseweb="popover"] {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
          }
          [role="option"], [role="option"] * {
            color:var(--cup-ink) !important;
          }
          [role="option"]:hover { background:#eef4f8 !important; }
          [aria-selected="true"][role="option"] { background:#e2edf5 !important; }


          /* ---------- Kalender / datumväljare ---------- */
          /* Kalendern ligger i en BaseWeb-popover utanför delar av Streamlits vanliga tema.
             Sätt därför bakgrund och text explicit även för veckodagsraden. */
          [data-baseweb="calendar"],
          [data-baseweb="calendar"] > div,
          [data-baseweb="calendar"] [role="grid"],
          [data-baseweb="calendar"] [role="row"],
          [data-baseweb="calendar"] [role="columnheader"] {
            background:#ffffff !important;
            color:#0f172a !important;
          }
          [data-baseweb="calendar"] [role="columnheader"],
          [data-baseweb="calendar"] [role="columnheader"] *,
          [data-baseweb="calendar"] abbr {
            color:#0f172a !important;
            font-weight:700 !important;
            opacity:1 !important;
            text-decoration:none !important;
          }
          [data-baseweb="calendar"] [role="gridcell"],
          [data-baseweb="calendar"] [role="gridcell"] * {
            color:#0f172a !important;
          }
          [data-baseweb="calendar"] select,
          [data-baseweb="calendar"] [data-baseweb="select"],
          [data-baseweb="calendar"] [data-baseweb="select"] * {
            background:#ffffff !important;
            color:#0f172a !important;
          }
          [data-baseweb="calendar"],
          [data-baseweb="calendar"] > div,
          [data-baseweb="calendar"] table,
          [data-baseweb="calendar"] tbody,
          [data-baseweb="calendar"] thead {
            background:#ffffff !important;
            color:#172033 !important;
          }
          [data-baseweb="calendar"] *,
          [data-baseweb="calendar"] button,
          [data-baseweb="calendar"] th,
          [data-baseweb="calendar"] td,
          [data-baseweb="calendar"] div,
          [data-baseweb="calendar"] span {
            color:#172033 !important;
          }
          [data-baseweb="calendar"] button {
            background:#ffffff !important;
            border-color:transparent !important;
          }
          [data-baseweb="calendar"] button:hover {
            background:#eaf2f7 !important;
          }
          [data-baseweb="calendar"] [aria-selected="true"],
          [data-baseweb="calendar"] [aria-selected="true"] *,
          [data-baseweb="calendar"] button[aria-selected="true"],
          [data-baseweb="calendar"] button[aria-selected="true"] * {
            background:#166534 !important;
            color:#ffffff !important;
            border-radius:8px !important;
          }
          [data-baseweb="calendar"] [aria-disabled="true"],
          [data-baseweb="calendar"] [aria-disabled="true"] * {
            color:#8a98a8 !important;
          }
          [data-baseweb="calendar"] [aria-current="date"] {
            outline:2px solid #2563eb !important;
            outline-offset:-2px !important;
          }

          /* ---------- Checkbox, radio och toggles ---------- */
          [data-testid="stCheckbox"] label,
          [data-testid="stRadio"] label,
          [data-testid="stToggle"] label,
          [data-testid="stCheckbox"] span,
          [data-testid="stRadio"] span,
          [data-testid="stToggle"] span {
            color:var(--cup-ink) !important;
          }

          /* ---------- Segmenterade knappar ----------
             Streamlit kan annars ärva mörka theme-färger här.
             Håll alla segmenterade kontroller ljusa och CupNavi-enhetliga. */
          [data-testid="stSegmentedControl"] button,
          [data-testid="stButtonGroup"] button,
          [data-testid="stSegmentedControl"] [role="button"],
          [data-testid="stButtonGroup"] [role="button"] {
            background:#F8FAFC !important;
            color:#172033 !important;
            border-color:#CBD5E1 !important;
            opacity:1 !important;
            box-shadow:none !important;
          }
          [data-testid="stSegmentedControl"] button *,
          [data-testid="stButtonGroup"] button *,
          [data-testid="stSegmentedControl"] [role="button"] *,
          [data-testid="stButtonGroup"] [role="button"] * {
            color:#172033 !important;
            opacity:1 !important;
          }
          [data-testid="stSegmentedControl"] button:hover,
          [data-testid="stButtonGroup"] button:hover,
          [data-testid="stSegmentedControl"] [role="button"]:hover,
          [data-testid="stButtonGroup"] [role="button"]:hover {
            background:#EEF6F0 !important;
            border-color:#86A995 !important;
          }
          [data-testid="stSegmentedControl"] button[aria-pressed="true"],
          [data-testid="stButtonGroup"] button[aria-pressed="true"],
          [data-testid="stSegmentedControl"] [role="button"][aria-pressed="true"],
          [data-testid="stButtonGroup"] [role="button"][aria-pressed="true"],
          [data-testid="stSegmentedControl"] button[aria-checked="true"],
          [data-testid="stButtonGroup"] button[aria-checked="true"],
          [data-testid="stSegmentedControl"] [data-selected="true"],
          [data-testid="stButtonGroup"] [data-selected="true"] {
            background:#DCFCE7 !important;
            color:#14532D !important;
            border-color:#86A995 !important;
            font-weight:800 !important;
          }
          [data-testid="stSegmentedControl"] button[aria-pressed="true"] *,
          [data-testid="stButtonGroup"] button[aria-pressed="true"] *,
          [data-testid="stSegmentedControl"] [role="button"][aria-pressed="true"] *,
          [data-testid="stButtonGroup"] [role="button"][aria-pressed="true"] *,
          [data-testid="stSegmentedControl"] button[aria-checked="true"] *,
          [data-testid="stButtonGroup"] button[aria-checked="true"] *,
          [data-testid="stSegmentedControl"] [data-selected="true"] *,
          [data-testid="stButtonGroup"] [data-selected="true"] * {
            color:#14532D !important;
            opacity:1 !important;
          }

          /* ---------- Knappar ---------- */
          .stButton > button,
          .stFormSubmitButton > button,
          .stDownloadButton > button {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
            border:1px solid var(--cup-border-strong) !important;
            border-radius:10px !important;
            font-weight:700 !important;
            min-height:2.55rem;
            box-shadow:0 1px 2px rgba(15,23,42,.04);
            transition:background .12s ease,border-color .12s ease,box-shadow .12s ease;
          }
          .stButton > button p,.stButton > button span,
          .stFormSubmitButton > button p,.stFormSubmitButton > button span,
          .stDownloadButton > button p,.stDownloadButton > button span {
            color:var(--cup-ink) !important;
          }
          .stButton > button:hover,
          .stFormSubmitButton > button:hover,
          .stDownloadButton > button:hover {
            background:#f2f6f9 !important;
            border-color:#98a9bb !important;
            box-shadow:0 3px 9px rgba(15,23,42,.08);
          }
          button[kind="primary"],
          .stButton > button[kind="primary"],
          .stFormSubmitButton > button[kind="primary"] {
            background:var(--cup-green) !important;
            border-color:var(--cup-green) !important;
            color:#ffffff !important;
          }
          button[kind="primary"] p,button[kind="primary"] span,
          .stButton > button[kind="primary"] p,.stButton > button[kind="primary"] span,
          .stFormSubmitButton > button[kind="primary"] p,.stFormSubmitButton > button[kind="primary"] span {
            color:#ffffff !important;
          }
          button[kind="primary"]:hover { background:var(--cup-green-hover) !important; }
          button:disabled,button:disabled * {
            color:#7b8794 !important;
            opacity:1 !important;
          }
          button:disabled { background:#edf1f4 !important; border-color:#d7dee6 !important; }

          /* ---------- Metrics ---------- */
          div[data-testid="stMetric"] {
            background:var(--cup-surface) !important;
            border:1px solid var(--cup-border) !important;
            border-radius:12px !important;
            padding:13px 15px !important;
            box-shadow:none !important;
          }
          div[data-testid="stMetricLabel"],div[data-testid="stMetricLabel"] * {
            color:var(--cup-muted) !important;
          }
          div[data-testid="stMetricValue"],div[data-testid="stMetricValue"] * {
            color:var(--cup-ink) !important;
            font-weight:800 !important;
          }

          /* Streamlits generiska Enter-instruktion skapar visuellt brus, särskilt i sidofältet. */
          [data-testid="InputInstructions"] { display:none !important; }

          /* ---------- Informations-, varnings- och felrutor ---------- */
          [data-testid="stAlert"] {
            border-radius:10px !important;
            border:1px solid var(--cup-border) !important;
          }
          [data-testid="stAlert"] p,[data-testid="stAlert"] div,[data-testid="stAlert"] span {
            color:var(--cup-ink) !important;
          }
          [data-testid="stNotification"] * { color:var(--cup-ink) !important; }

          /* ---------- Tabeller och data ---------- */
          .stApp table {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
            border-color:var(--cup-border) !important;
          }
          .stApp table th {
            background:#e9eff4 !important;
            color:var(--cup-ink) !important;
            font-weight:750 !important;
          }
          .stApp table td { color:var(--cup-ink) !important; }
          [data-testid="stDataFrame"] {
            background:var(--cup-surface) !important;
            border:1px solid var(--cup-border) !important;
            border-radius:10px !important;
            overflow:hidden;
          }

          /* ---------- Publik hero och matchkort ---------- */
          /* v91 public navigation + info */
          .cn-rules-grid {
            display:grid;
            grid-template-columns:repeat(2,minmax(0,1fr));
            gap:12px;
            margin:10px 0 20px;
          }
          .cn-rule-card {
            display:flex;
            gap:12px;
            align-items:flex-start;
            padding:16px;
            border:1px solid #dbe3ea;
            border-radius:16px;
            background:linear-gradient(145deg,#ffffff,#f7f9fc);
            box-shadow:0 5px 16px rgba(15,23,42,.06);
          }
          .cn-rule-icon {
            width:38px;height:38px;border-radius:12px;
            display:flex;align-items:center;justify-content:center;
            background:#eef4ff;font-size:20px;flex:0 0 38px;
          }
          .cn-rule-card strong {display:block;color:#172033;font-size:15px;margin-bottom:4px}
          .cn-rule-card span {display:block;color:#334155;line-height:1.45;font-size:14px}
          .cn-rule-card small {display:block;color:#64748b;margin-top:4px}
          .cn-custom-info-card,.cn-practical-info-card {
            border:1px solid #dbe3ea;border-radius:16px;padding:17px 18px;
            background:#fff;box-shadow:0 4px 14px rgba(15,23,42,.05);
            line-height:1.6;color:#172033;margin:8px 0 18px;
          }
          .cn-practical-info-card {display:grid;gap:10px}
          @media (max-width:680px) {
            .cn-rules-grid {grid-template-columns:1fr}
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] button {
              min-height:64px;
              border-radius:15px;
              font-weight:850;
              font-size:14px;
              box-shadow:0 4px 12px rgba(15,23,42,.08);
            }
          }

          .cup-hero {
            background:linear-gradient(135deg,#172033 0%,#1e3a5f 58%,#166534 120%);
            color:#ffffff !important;
            border-radius:16px;
            padding:22px 24px;
            margin:4px 0 18px;
            box-shadow:0 8px 20px rgba(15,23,42,.14);
          }
          .cup-hero,.cup-hero h1,.cup-hero h2,.cup-hero h3,.cup-hero h4,
          .cup-hero p,.cup-hero div,.cup-hero span,.cup-hero b,.cup-hero small {
            color:#ffffff !important;
          }
          .cup-hero .eyebrow { font-size:12px; text-transform:uppercase; letter-spacing:.11em; opacity:.82; font-weight:800; }
          .cup-hero .title { font-size:clamp(26px,4vw,40px); font-weight:850; line-height:1.08; margin:5px 0 8px; }
          .cup-hero .meta { font-size:14px; opacity:.94; }

          .cn-hero-title-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
          .cn-hero-title-row .title{margin-right:auto}
          .cn-hero-status{display:inline-flex;align-items:center;border-radius:999px;padding:5px 9px;font-size:11px;font-weight:850;line-height:1}
          .cn-hero-status.live{background:rgba(34,197,94,.20);border:1px solid rgba(134,239,172,.45);color:#dcfce7!important}
          .cn-hero-status.completed{background:rgba(250,204,21,.18);border:1px solid rgba(253,224,71,.40);color:#fef9c3!important}
          .cn-hero-status.upcoming{background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.22);color:#fff!important}

          .status-pill { display:inline-block; padding:4px 9px; border-radius:999px; font-size:11px; font-weight:800; letter-spacing:.03em; }
          .status-live { background:#dcfce7 !important; color:#14532d !important; }
          .status-upcoming { background:#dbeafe !important; color:#1e40af !important; }
          .status-finished { background:#e2e8f0 !important; color:#334155 !important; }
          .public-match-card {
            background:var(--cup-surface) !important;
            color:var(--cup-ink) !important;
            border-color:var(--cup-border) !important;
            box-shadow:0 2px 8px rgba(15,23,42,.06) !important;
            transition:border-color .15s ease,box-shadow .15s ease;
          }
          .public-match-card,.public-match-card div,.public-match-card p,
          .public-match-card b,.public-match-card small {
            color:var(--cup-ink) !important;
          }
          .public-match-card .match-stage { color:#ffffff !important; }
          .public-match-card .match-meta { color:var(--cup-ink-soft) !important; }
          .public-match-card .match-weather,.public-match-card .match-referee,
          .public-match-card .kit-label { color:var(--cup-muted) !important; }
          .public-match-card:hover {
            box-shadow:0 5px 14px rgba(15,23,42,.10) !important;
            border-color:#aebdca !important;
          }

          /* ---------- Versionsmärke ---------- */
          .cup-version-badge {
            display:inline-block;
            margin:2px 0 12px;
            padding:6px 10px;
            border-radius:7px;
            background:#e4efe8;
            border:1px solid #b9d2c1;
            color:#14532d !important;
            font-size:12px;
            font-weight:800;
            letter-spacing:.02em;
          }

          /* ---------- Publik statistik ---------- */
          .public-metric-grid {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:12px;
            margin:0 0 16px;
          }
          .public-metric {
            background:#ffffff;
            border:1px solid var(--cup-border);
            border-radius:12px;
            padding:13px 15px;
            min-height:82px;
          }
          .public-metric .label { color:var(--cup-muted) !important; font-size:13px; margin-bottom:6px; }
          .public-metric .value { color:var(--cup-ink) !important; font-size:30px; line-height:1; font-weight:850; }


          /* ---------- Mobilkompatibilitet: iOS + Android ---------- */
          html, body {
            -webkit-text-size-adjust:100% !important;
            text-size-adjust:100% !important;
          }

          /* Undvik iOS auto-zoom när användaren trycker i formulärfält. */
          input, textarea, select,
          [data-baseweb="input"] input,
          [data-baseweb="textarea"] textarea,
          [data-baseweb="select"] input {
            font-size:16px !important;
          }


          /* Datumfält: tydlig kontrast även när Safari använder native-kontroll. */
          input[type="date"],
          input[type="time"] {
            background:#ffffff !important;
            color:#172033 !important;
            color-scheme:light !important;
            min-height:44px !important;
          }
          input[type="date"]::-webkit-date-and-time-value,
          input[type="time"]::-webkit-date-and-time-value {
            color:#172033 !important;
            text-align:left;
          }
          input[type="date"]::-webkit-calendar-picker-indicator,
          input[type="time"]::-webkit-calendar-picker-indicator {
            opacity:.85;
          }


          /* Dataframes får inte pressa hela sidan bredare än mobilen. */
          [data-testid="stDataFrame"],
          [data-testid="stDataEditor"] {
            max-width:100% !important;
            overflow-x:auto !important;
            -webkit-overflow-scrolling:touch !important;
          }

          @supports (padding: max(0px)) {
            .stApp .block-container {
              padding-left:max(.65rem, env(safe-area-inset-left)) !important;
              padding-right:max(.65rem, env(safe-area-inset-right)) !important;
              padding-bottom:max(1rem, env(safe-area-inset-bottom)) !important;
            }
          }

          @media (max-width:760px) {
            /* Rubriker får brytas utan att skapa horisontell scroll. */
            h1, h2, h3, h4, .cup-hero .title {
              overflow-wrap:anywhere;
              word-break:normal;
            }


            /* Matchkort ska hålla sig inom viewport. */
            .public-match-card {
              max-width:100% !important;
              overflow:hidden !important;
            }

            /* Formulär i flera kolumner får bli en kolumn på mycket smala telefoner. */
            div[data-testid="stHorizontalBlock"] {
              gap:.55rem !important;
            }
          }

          @media (max-width:430px) {
            .block-container {
              padding-top:.35rem !important;
            }
            .cup-version-badge {
              font-size:11px !important;
              padding:5px 8px !important;
            }
            .cup-hero .title {
              font-size:24px !important;
            }
            .public-metric .value {
              font-size:23px !important;
            }
          }

          /* iOS/Safari-specifikt – påverkar inte Android. */
          @supports (-webkit-touch-callout:none) {
            body {
              -webkit-font-smoothing:antialiased;
            }
            input, textarea, select, button {
              -webkit-appearance:none;
            }
            input[type="checkbox"],
            input[type="radio"] {
              -webkit-appearance:auto;
            }
          }

          /* ---------- Mobil ---------- */
          @media (max-width:760px) {
            .block-container { padding-left:.65rem; padding-right:.65rem; padding-top:.55rem; }
            .cup-hero { padding:15px 14px; border-radius:13px; margin-top:8px; margin-bottom:12px; }
            .cup-hero .title { font-size:27px; }
            .public-metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; margin-bottom:12px; }
            .public-metric { min-height:70px; padding:11px 12px; }
            .public-metric .value { font-size:25px; }
            .public-match-card { padding:11px !important; }
            .public-match-card .public-team-name { font-size:15px !important; }
            .public-match-card .kit-label { display:none !important; }
            .public-match-card .match-meta { font-size:12px !important; line-height:1.35 !important; }
            div[data-baseweb="tab-list"] {
              border-radius:9px !important;
              overflow-x:auto !important;
              flex-wrap:nowrap !important;
              scrollbar-width:none;
            }
            div[data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
            button[data-baseweb="tab"] { min-height:40px; white-space:nowrap !important; padding-left:10px !important; padding-right:10px !important; }
            div[role="radiogroup"] { gap:.25rem !important; }
          }



          /* ===== CENTRAL NAVIGATION v29 =====
             Alla navigationsval använder vanliga Streamlit-knappar.
             Inaktiv = ljus yta + mörk text.
             Aktiv = grön yta + vit text.
          */
          .stButton > button,
          .stFormSubmitButton > button,
          .stDownloadButton > button {
            background:#FFFFFF !important;
            border:1px solid #B8C5D1 !important;
            color:#0F172A !important;
            opacity:1 !important;
          }
          .stButton > button *,
          .stFormSubmitButton > button *,
          .stDownloadButton > button * {
            color:#0F172A !important;
            opacity:1 !important;
          }
          .stButton > button:hover,
          .stFormSubmitButton > button:hover,
          .stDownloadButton > button:hover {
            background:#F1F5F9 !important;
            border-color:#94A3B8 !important;
          }
          [data-testid="stLinkButton"] a {
            background:#FFFFFF !important;
            border:1px solid #B8C5D1 !important;
            color:#0F172A !important;
            opacity:1 !important;
            border-radius:10px !important;
            font-weight:700 !important;
            min-height:2.55rem !important;
            box-shadow:0 1px 2px rgba(15,23,42,.04) !important;
          }
          [data-testid="stLinkButton"] a *,
          [data-testid="stLinkButton"] a p,
          [data-testid="stLinkButton"] a span {
            color:#0F172A !important;
            opacity:1 !important;
          }
          [data-testid="stLinkButton"] a:hover {
            background:#F1F5F9 !important;
            border-color:#94A3B8 !important;
          }

          .stButton > button[kind="primary"],
          .stFormSubmitButton > button[kind="primary"] {
            background:#166534 !important;
            border-color:#166534 !important;
            color:#FFFFFF !important;
            opacity:1 !important;
          }
          .stButton > button[kind="primary"] *,
          .stFormSubmitButton > button[kind="primary"] * {
            color:#FFFFFF !important;
            opacity:1 !important;
          }
          .stButton > button[kind="primary"]:hover,
          .stFormSubmitButton > button[kind="primary"]:hover {
            background:#14532D !important;
            border-color:#14532D !important;
          }

          /* Publika flikar ligger kvar överst när användaren scrollar. */
          div[data-baseweb="tab-list"] {
            position:sticky !important;
            top:0 !important;
            z-index:999 !important;
            box-shadow:0 4px 10px rgba(15,23,42,.10) !important;
          }

          /* Publika st.tabs finns kvar men får ett enda tydligt färgsystem. */
          div[data-baseweb="tab-list"] {
            background:#F1F5F9 !important;
            border:1px solid #CBD5E1 !important;
            isolation:isolate !important;
            border-radius:10px !important;
            padding:4px !important;
            gap:3px !important;
            overflow-x:auto !important;
          }
          button[data-baseweb="tab"],
          button[data-baseweb="tab"] > div {
            background:#FFFFFF !important;
            color:#0F172A !important;
            opacity:1 !important;
          }
          button[data-baseweb="tab"] *,
          button[data-baseweb="tab"] p,
          button[data-baseweb="tab"] span {
            color:#0F172A !important;
            opacity:1 !important;
          }
          button[data-baseweb="tab"][aria-selected="true"],
          button[data-baseweb="tab"][aria-selected="true"] > div {
            background:#DCFCE7 !important;
            color:#14532D !important;
            font-weight:800 !important;
          }
          button[data-baseweb="tab"][aria-selected="true"] * {
            color:#14532D !important;
          }

          @media (max-width:760px) {
            .stButton > button {
              min-height:44px !important;
              font-size:14px !important;
            }
            div[data-baseweb="tab-list"] {
              flex-wrap:nowrap !important;
              overflow-x:auto !important;
              -webkit-overflow-scrolling:touch !important;
              scrollbar-width:none;
            }
            div[data-baseweb="tab-list"]::-webkit-scrollbar { display:none; }
            button[data-baseweb="tab"] {
              flex:0 0 auto !important;
              min-height:44px !important;
              white-space:nowrap !important;
              padding-left:12px !important;
              padding-right:12px !important;
            }
          }


          /* ===== TABELLER v31: centrera rubriker och innehåll ===== */
          table th,
          table td {
            text-align:center !important;
            vertical-align:middle !important;
          }

          /* Streamlit dataframe/data_editor (Glide Data Grid) */
          [data-testid="stDataFrame"] [role="columnheader"],
          [data-testid="stDataFrame"] [role="gridcell"],
          [data-testid="stDataEditor"] [role="columnheader"],
          [data-testid="stDataEditor"] [role="gridcell"] {
            text-align:center !important;
            justify-content:center !important;
            align-items:center !important;
          }

          [data-testid="stDataFrame"] [role="columnheader"] *,
          [data-testid="stDataFrame"] [role="gridcell"] *,
          [data-testid="stDataEditor"] [role="columnheader"] *,
          [data-testid="stDataEditor"] [role="gridcell"] * {
            text-align:center !important;
            justify-content:center !important;
            margin-left:auto !important;
            margin-right:auto !important;
          }

</style>
        """,
        unsafe_allow_html=True,
    )


inject_custom_css()

st.markdown(
    """<style>
      .cn-about-hero { max-width:900px; margin:0 auto 22px; }
      .cn-about-card { min-height:150px; background:#fff; border:1px solid #D8E2EC; border-radius:16px; padding:18px 20px; margin:0 0 14px; box-shadow:0 5px 18px rgba(15,23,42,.05); }
      .cn-about-card .title { color:#0F172A !important; font-weight:850; font-size:18px; margin-bottom:8px; }
      .cn-about-card .body { color:#475569 !important; line-height:1.55; }
      @media (max-width:760px) { .cn-about-card { min-height:auto; padding:16px; } }
    </style>""",
    unsafe_allow_html=True,
)


def inject_ux2_css():
    st.markdown(
        """<style>
        :root{--cn-space-1:4px;--cn-space-2:8px;--cn-space-3:12px;--cn-space-4:16px;--cn-space-5:24px;--cn-radius:14px;--cn-primary:#176b3a;--cn-primary-soft:#eef8f1;--cn-text:#132033;--cn-muted:#64748b;--cn-border:#dbe4ea}
        .cn-recommend-card,.cn-progress-hero,.cn-attention-row{background:#fff;border:1px solid var(--cn-border);border-radius:var(--cn-radius);box-shadow:0 5px 18px rgba(15,23,42,.05)}
        .cn-recommend-card{padding:14px 16px;margin:8px 0 12px;display:flex;flex-direction:column;gap:4px}.cn-recommend-card b{color:var(--cn-primary)}.cn-recommend-card span{font-weight:750;color:var(--cn-text)}.cn-recommend-card small{color:var(--cn-muted)}
        .cn-progress-hero{padding:16px 18px;margin:8px 0 18px}.cn-progress-hero>div:first-child{display:flex;justify-content:space-between;gap:16px;align-items:baseline}.cn-progress-hero span{color:var(--cn-muted);font-weight:700}.cn-progress-hero strong{color:var(--cn-text);font-size:22px}.cn-progress-track{height:9px;background:#edf2f7;border-radius:99px;margin-top:10px;overflow:hidden}.cn-progress-track i{display:block;height:100%;background:var(--cn-primary);border-radius:99px}
        .cn-attention-row{padding:11px 13px;margin:3px 0;color:var(--cn-text)}
        .cn-empty-state{display:flex;gap:13px;align-items:center;padding:18px;border:1px dashed #b9c7d2;border-radius:14px;background:#fbfcfd;margin:10px 0 16px}.cn-empty-state .icon{width:42px;height:42px;border-radius:12px;background:#eef8f1;display:grid;place-items:center;font-size:22px;color:#176b3a}.cn-empty-state b{color:#132033;font-size:16px}.cn-empty-state p{margin:3px 0 0;color:#64748b} 
        .cn-schedule-grid{display:grid;grid-template-columns:72px repeat(var(--cn-pitches,4),minmax(150px,1fr));gap:8px;margin:7px 0;min-width:720px}.cn-schedule-head>div{font-size:12px;font-weight:850;color:var(--cn-muted);text-transform:uppercase;padding:4px 6px}.cn-schedule-time{font-weight:850;color:var(--cn-text);padding:11px 6px}.cn-match-tile{display:grid;grid-template-columns:auto 1fr auto 1fr;gap:5px;align-items:center;padding:10px 11px;border:1px solid var(--cn-border);border-radius:12px;background:#fff;color:var(--cn-text);box-shadow:0 2px 8px rgba(15,23,42,.04)}.cn-match-tile small{color:var(--cn-muted)}.cn-match-tile.empty{display:block;color:#94a3b8;background:#f8fafc;box-shadow:none}.stExpander:has(.cn-schedule-grid){overflow-x:auto}
        .cn-mobile-bottom-nav{display:none}
        [data-testid="stButton"] button{min-height:44px;border-radius:12px;font-weight:720;touch-action:manipulation;-webkit-tap-highlight-color:transparent}
        [data-testid="stDataFrame"],.texttv-table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
        [data-testid="stButton"] button[kind="primary"]{box-shadow:0 4px 12px rgba(23,107,58,.14)}
        .cn-current-admin-page{position:sticky;top:78px;z-index:50;background:rgba(248,250,252,.94);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);border:1px solid var(--cn-border);box-shadow:0 5px 14px rgba(15,23,42,.05)}
        .cn-admin-nav-group-title{margin-top:18px!important;color:#64748b!important;font-size:12px!important;letter-spacing:.06em!important}

        .cn-admin-section-label{font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.07em;color:#64748b;margin:2px 0 5px}

        .cn-mode-nav-safezone{height:0;margin:0;padding:0}
        @media(min-width:901px){
          .cn-mode-nav-safezone{height:24px!important;display:block!important}
          .cn-mode-nav-safezone + div{
            position:relative;z-index:20;
            max-width:430px!important;margin-left:auto!important;
          }
          .cn-mode-nav-safezone + div [data-testid="stButton"] button{
            min-height:38px!important;font-size:.86rem!important;
          }
        }
        @media(max-width:900px){
          .cn-mode-nav-safezone{height:0!important}
        }

        .cn-setup-flow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:#fff;border:1px solid #d7e0ea;border-radius:12px;padding:10px 12px;margin:4px 0 10px}
        .cn-setup-flow b{background:#eef7f0;color:#166534;border:1px solid #bbdfc5;border-radius:999px;padding:5px 9px;font-size:12px}
        .cn-setup-flow span{color:#94a3b8;font-weight:800}
        .cn-rule-type{font-size:11px;font-weight:900;letter-spacing:.05em;text-transform:uppercase}
        .cn-flow-context{background:#fff;border:1px solid var(--cn-border);border-radius:16px;padding:14px 16px;margin:8px 0 12px;box-shadow:0 4px 14px rgba(15,23,42,.045)}
        .cn-flow-kicker{font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.07em;color:#64748b;margin-bottom:3px}
        .cn-flow-title{font-size:17px;font-weight:850;color:#132033;margin-bottom:3px}
        .cn-flow-copy{font-size:13px;line-height:1.45;color:#64748b}
        .cn-flow-status{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}
        .cn-flow-pill{display:inline-flex;align-items:center;gap:5px;border:1px solid #dbe4ea;border-radius:999px;padding:5px 9px;background:#f8fafc;color:#475569;font-size:12px;font-weight:780}
        .cn-flow-pill.good{background:#ecfdf5;border-color:#bbf7d0;color:#166534}
        .cn-flow-pill.warn{background:#fff7ed;border-color:#fed7aa;color:#9a3412}
        .cn-next-action{border-left:4px solid #176b3a;background:#f5fbf7;border-radius:12px;padding:11px 13px;margin:8px 0 12px}
        .cn-next-action b{color:#14532d}.cn-next-action span{color:#475569;font-size:13px}

        @media(max-width:760px){
          .cn-mobile-bottom-nav{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;left:8px;right:8px;bottom:8px;z-index:999996;background:rgba(255,255,255,.97);border:1px solid #dbe4ea;border-radius:18px;box-shadow:0 10px 28px rgba(15,23,42,.16);padding:6px;-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px)}
          .cn-mobile-bottom-nav a{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-height:52px;text-decoration:none!important;color:#475569!important;font-size:17px;border-radius:12px}.cn-mobile-bottom-nav a span{font-size:10px;font-weight:800}.cn-mobile-bottom-nav a.active{background:#eef8f1;color:#14532d!important}
          .stApp .block-container{padding-bottom:5.8rem!important}.cn-schedule-grid{min-width:640px}.cn-current-admin-page{top:70px} [data-testid="stButton"] button{min-height:46px !important}
        }
        </style>""", unsafe_allow_html=True)
    components.html("""<script>document.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();const f=window.parent.document.querySelector('input[aria-label*=\"Sök lag\"],input[placeholder*=\"ÖSK\"]');if(f){f.focus();f.scrollIntoView({block:'center'});}}});</script>""",height=0)

inject_ux2_css()


def inject_v191_design_system():
    """Gemensamt produktlager ovanpå Streamlit utan att ändra affärslogik."""
    st.markdown(
        """<style>
        :root{
          --cn-primary:#176b3a;
          --cn-primary-hover:#12572f;
          --cn-primary-soft:#edf7f0;
          --cn-secondary:#334155;
          --cn-accent:#0f766e;
          --cn-bg:#f6f8f7;
          --cn-surface:#ffffff;
          --cn-surface-subtle:#f8faf9;
          --cn-border:#d9e2dd;
          --cn-border-strong:#c4d1ca;
          --cn-text:#17231d;
          --cn-text-secondary:#5f6f66;
          --cn-success:#18723d;
          --cn-warning:#9a5b0a;
          --cn-error:#b42318;
          --cn-info:#315b7d;
          --cn-disabled:#94a39b;
          --cn-space-1:4px;--cn-space-2:8px;--cn-space-3:12px;--cn-space-4:16px;
          --cn-space-5:24px;--cn-space-6:32px;--cn-space-7:48px;--cn-space-8:64px;
          --cn-radius-sm:8px;--cn-radius-md:12px;--cn-radius-lg:16px;
          --cn-shadow-sm:0 1px 2px rgba(16,24,20,.05);
        }

        html,body,[class*="css"]{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
        .stApp{background:var(--cn-bg);color:var(--cn-text)}
        .stApp .block-container{max-width:1180px;padding-left:clamp(14px,3vw,32px);padding-right:clamp(14px,3vw,32px)}
        [data-testid="stSidebar"]{background:#f1f5f2;border-right:1px solid var(--cn-border)}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.55rem}

        h1{font-size:clamp(1.65rem,2.2vw,2.05rem)!important;line-height:1.15!important;letter-spacing:-.025em!important;font-weight:760!important;margin-bottom:.45rem!important}
        h2{font-size:clamp(1.30rem,1.8vw,1.55rem)!important;line-height:1.2!important;letter-spacing:-.018em!important;font-weight:730!important}
        h3{font-size:1.12rem!important;line-height:1.3!important;font-weight:700!important}
        h4{font-size:1rem!important;line-height:1.35!important;font-weight:690!important}
        p,li,[data-testid="stCaptionContainer"]{line-height:1.52}
        [data-testid="stCaptionContainer"]{color:var(--cn-text-secondary)!important;font-size:.84rem!important}

        [data-testid="stButton"] button,
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stDownloadButton"] button,
        [data-testid="stLinkButton"] a{
          min-height:42px!important;border-radius:var(--cn-radius-sm)!important;
          font-weight:660!important;letter-spacing:0!important;box-shadow:none!important;
          transition:background-color .12s ease,border-color .12s ease,color .12s ease!important;
        }
        [data-testid="stButton"] button[kind="primary"],
        [data-testid="stFormSubmitButton"] button[kind="primary"]{
          background:var(--cn-primary)!important;border-color:var(--cn-primary)!important;color:white!important;
        }
        [data-testid="stButton"] button[kind="primary"]:hover,
        [data-testid="stFormSubmitButton"] button[kind="primary"]:hover{
          background:var(--cn-primary-hover)!important;border-color:var(--cn-primary-hover)!important;
        }
        [data-testid="stButton"] button[kind="secondary"],
        [data-testid="stFormSubmitButton"] button[kind="secondary"],
        [data-testid="stDownloadButton"] button,
        [data-testid="stLinkButton"] a{
          background:var(--cn-surface)!important;border:1px solid var(--cn-border-strong)!important;color:var(--cn-secondary)!important;
        }
        [data-testid="stButton"] button[kind="secondary"]:hover,
        [data-testid="stDownloadButton"] button:hover,
        [data-testid="stLinkButton"] a:hover{background:#f3f6f4!important;border-color:#9fb1a7!important}

        button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,[role="combobox"]:focus-visible{
          outline:3px solid rgba(23,107,58,.28)!important;outline-offset:2px!important;
        }
        button:disabled,[aria-disabled="true"]{opacity:.52!important;cursor:not-allowed!important}

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-baseweb="select"]>div,
        [data-testid="stDateInput"] input{
          border-radius:var(--cn-radius-sm)!important;border-color:var(--cn-border-strong)!important;
          background:var(--cn-surface)!important;box-shadow:none!important;
        }
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus{
          border-color:var(--cn-primary)!important;
        }

        [data-testid="stVerticalBlockBorderWrapper"]{
          border-color:var(--cn-border)!important;border-radius:var(--cn-radius-md)!important;
          box-shadow:none!important;background:var(--cn-surface)!important;
        }
        [data-testid="stExpander"]{
          border:1px solid var(--cn-border)!important;border-radius:var(--cn-radius-md)!important;
          background:var(--cn-surface)!important;box-shadow:none!important;
        }
        [data-testid="stExpander"] summary{font-weight:660!important}

        [data-testid="stAlert"]{
          border-radius:var(--cn-radius-md)!important;box-shadow:none!important;border-width:1px!important;
        }
        [data-testid="stMetric"]{
          background:var(--cn-surface);border:1px solid var(--cn-border);
          border-radius:var(--cn-radius-md);padding:12px 14px;box-shadow:none;
        }

        [data-testid="stDataFrame"]{
          border:1px solid var(--cn-border);border-radius:var(--cn-radius-md);background:var(--cn-surface);
          overflow:hidden;
        }
        [data-testid="stDataFrame"] [role="columnheader"]{font-weight:700!important;background:#f1f5f2!important}
        .texttv-table{border-collapse:separate!important;border-spacing:0!important}
        .texttv-table th{position:sticky;top:0;z-index:2;background:#eef3f0!important;font-size:.78rem!important;letter-spacing:.02em}
        .texttv-table td,.texttv-table th{padding:9px 10px!important;border-bottom:1px solid #e6ece8!important}
        .texttv-table tbody tr:hover td{filter:brightness(.985)}
        .texttv-table td:not(:nth-child(2)){font-variant-numeric:tabular-nums}

        [data-testid="stTabs"] [role="tablist"]{gap:4px;border-bottom:1px solid var(--cn-border)}
        [data-testid="stTabs"] button[role="tab"]{
          border-radius:var(--cn-radius-sm) var(--cn-radius-sm) 0 0!important;font-weight:640!important;padding:.55rem .8rem!important;
        }

        .cn-recommend-card,.cn-progress-hero,.cn-attention-row,.cn-flow-context,.cn-follow-shell,.cn-next-card{
          box-shadow:none!important;border-color:var(--cn-border)!important;border-radius:var(--cn-radius-md)!important;
        }
        .cn-flow-context{padding:12px 14px!important;margin:6px 0 10px!important}
        .cn-flow-kicker,.cn-admin-section-label,.cn-admin-nav-group-title{letter-spacing:.045em!important;font-weight:720!important}
        .cn-flow-pill{border-radius:999px!important;font-weight:650!important}
        .cn-current-admin-page{
          box-shadow:none!important;background:#f6f8f7!important;-webkit-backdrop-filter:none!important;backdrop-filter:none!important;
          border-color:var(--cn-border)!important;
        }

        .cn-empty-state{
          border:1px dashed var(--cn-border-strong)!important;background:var(--cn-surface-subtle)!important;
          border-radius:var(--cn-radius-md)!important;padding:18px!important;box-shadow:none!important;
        }
        .cn-empty-state .icon{background:var(--cn-primary-soft)!important;border-radius:var(--cn-radius-sm)!important}
        .cn-empty-state p{color:var(--cn-text-secondary)!important}

        .cn-public-top-nav + div [data-testid="stButton"] button{min-height:46px!important}
        .cn-public-top-nav + div [data-testid="stButton"] button[kind="primary"]{
          background:var(--cn-primary-soft)!important;color:#14552f!important;border:1px solid #9bc8aa!important;
        }
        .cn-public-top-nav + div [data-testid="stButton"] button[kind="secondary"]{
          background:transparent!important;border-color:transparent!important;color:#53645a!important;
        }
        .cn-public-top-nav + div [data-testid="stButton"] button[kind="secondary"]:hover{
          background:#eef2ef!important;border-color:#dce5df!important;color:#263a2e!important;
        }

        .cn-mobile-bottom-nav{
          border-radius:var(--cn-radius-md)!important;background:#fff!important;border-color:var(--cn-border)!important;
          box-shadow:0 8px 22px rgba(16,24,20,.12)!important;-webkit-backdrop-filter:none!important;backdrop-filter:none!important;
        }
        .cn-mobile-bottom-nav a{border-radius:var(--cn-radius-sm)!important;color:#5c6d63!important}
        .cn-mobile-bottom-nav a.active{background:var(--cn-primary-soft)!important;color:#14552f!important}

        @media(max-width:900px){
          .stApp .block-container{padding-left:12px!important;padding-right:12px!important}
          .cn-mode-nav-safezone + div [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;gap:6px!important}
          .cn-mode-nav-safezone + div [data-testid="column"]{min-width:calc(50% - 4px)!important;flex:1 1 calc(50% - 4px)!important}
          .cn-public-top-nav + div{display:none!important}
        }
        @media(max-width:760px){
          h1{font-size:1.55rem!important} h2{font-size:1.25rem!important}
          .public-metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}
          .public-metric{min-height:auto!important;padding:9px 10px!important}
          .public-metric .value{font-size:22px!important}
          .public-match-card{padding:10px!important;margin:7px 0!important}
          [data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button{min-height:46px!important}
          [data-testid="stVerticalBlockBorderWrapper"]{border-radius:10px!important}
          .cn-mobile-bottom-nav{grid-template-columns:repeat(5,1fr)!important;left:6px!important;right:6px!important;bottom:max(6px,env(safe-area-inset-bottom))!important;padding:5px!important}
          .cn-mobile-bottom-nav a{min-height:50px!important;font-size:15px!important}
          .cn-mobile-bottom-nav a span{font-size:9.5px!important}
          .texttv-table td,.texttv-table th{padding:8px 8px!important}
        }
        @media(min-width:1400px){
          .stApp .block-container{max-width:1220px!important}
        }
        @media(prefers-reduced-motion:reduce){
          *,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important}
        }
        </style>""",
        unsafe_allow_html=True,
    )


inject_v191_design_system()


def inject_v193_product_design_system():
    """Cohesive presentation-only product design layer for v1.193."""
    st.markdown(
        """<style>
        /* CUPNAVI PRODUCT DESIGN SYSTEM v1.193 */
        :root{
          --cn-color-primary:#176b3a;--cn-color-primary-hover:#12572f;--cn-color-primary-pressed:#0d4727;
          --cn-color-primary-soft:#edf7f0;--cn-color-secondary:#334155;--cn-color-accent:#0f766e;
          --cn-color-bg:#f5f7f6;--cn-color-surface:#fff;--cn-color-surface-subtle:#f8faf9;
          --cn-color-border:#d9e2dd;--cn-color-border-strong:#b9c8c0;
          --cn-color-text:#16231c;--cn-color-text-secondary:#5b6b62;--cn-color-text-tertiary:#738078;
          --cn-color-success:#176b3a;--cn-color-warning:#8a5308;--cn-color-error:#b42318;--cn-color-info:#315b7d;
          --cn-space-1:4px;--cn-space-2:8px;--cn-space-3:12px;--cn-space-4:16px;--cn-space-5:24px;--cn-space-6:32px;--cn-space-7:48px;--cn-space-8:64px;
          --cn-radius-xs:6px;--cn-radius-sm:8px;--cn-radius-md:12px;--cn-radius-lg:16px;
          --cn-shadow-xs:0 1px 2px rgba(16,24,20,.035);--cn-shadow-sm:0 3px 12px rgba(16,24,20,.055);
          --cn-control-h:40px;--cn-content-max:1240px;
        }
        html,body,.stApp{background:var(--cn-color-bg)!important;color:var(--cn-color-text)!important}
        html,body,.stApp,button,input,textarea,select{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif!important}
        .stApp .block-container{max-width:var(--cn-content-max)!important;padding-left:clamp(14px,2.4vw,30px)!important;padding-right:clamp(14px,2.4vw,30px)!important;padding-bottom:32px!important}
        h1,h2,h3,h4,h5,h6{color:var(--cn-color-text)!important;text-wrap:balance}
        h1{font-size:clamp(1.55rem,2vw,1.95rem)!important;line-height:1.12!important;letter-spacing:-.025em!important;font-weight:780!important;margin:0 0 12px!important}
        h2{font-size:clamp(1.25rem,1.6vw,1.48rem)!important;line-height:1.2!important;letter-spacing:-.018em!important;font-weight:750!important;margin:24px 0 12px!important}
        h3{font-size:1.08rem!important;line-height:1.28!important;font-weight:720!important;margin:16px 0 8px!important}
        h4{font-size:.98rem!important;font-weight:700!important} p,li{line-height:1.48}
        [data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:var(--cn-color-text-secondary)!important;font-size:.82rem!important;line-height:1.42!important}
        [data-testid="stMarkdownContainer"] a{color:#145a34;text-underline-offset:2px}
        [data-testid="stVerticalBlock"]{gap:.65rem}[data-testid="stHorizontalBlock"]{gap:.75rem}hr{border-color:var(--cn-color-border)!important;margin:24px 0!important}
        [data-testid="stSidebar"]{background:#f0f4f1!important;border-right:1px solid var(--cn-color-border)!important}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.42rem!important}
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{font-size:.76rem!important;color:var(--cn-color-text-secondary)!important;font-weight:700!important}
        [data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] p,label[data-testid="stWidgetLabel"]{color:var(--cn-color-text)!important;font-size:.84rem!important;font-weight:650!important;line-height:1.28!important;opacity:1!important}
        [data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stDateInput"] input,[data-baseweb="select"]>div{min-height:var(--cn-control-h)!important;border:1px solid var(--cn-color-border-strong)!important;border-radius:var(--cn-radius-sm)!important;background:var(--cn-color-surface)!important;color:var(--cn-color-text)!important;box-shadow:none!important}
        [data-testid="stTextInput"] input:focus,[data-testid="stNumberInput"] input:focus,[data-testid="stTextArea"] textarea:focus,[data-testid="stDateInput"] input:focus,[data-baseweb="select"]>div:focus-within{border-color:var(--cn-color-primary)!important;box-shadow:0 0 0 3px rgba(23,107,58,.12)!important;outline:none!important}
        [data-testid="stForm"]{background:var(--cn-color-surface)!important;border-color:var(--cn-color-border)!important;border-radius:var(--cn-radius-md)!important}
        [data-testid="stRadio"]>div{gap:6px!important;flex-wrap:wrap!important}[data-testid="stRadio"] label{padding:6px 10px!important;border:1px solid var(--cn-color-border)!important;border-radius:var(--cn-radius-sm)!important;background:#fff!important;color:var(--cn-color-text)!important;font-size:.84rem!important}
        [data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stLinkButton"] a,[data-testid="stPopover"] button{min-height:var(--cn-control-h)!important;padding:7px 13px!important;border-radius:var(--cn-radius-sm)!important;box-shadow:none!important;font-weight:670!important;font-size:.84rem!important;line-height:1.15!important;transition:background-color .12s ease,border-color .12s ease,color .12s ease,transform .06s ease!important}
        [data-testid="stButton"] button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:var(--cn-color-primary)!important;border:1px solid var(--cn-color-primary)!important;color:#fff!important}
        [data-testid="stButton"] button[kind="primary"] *,[data-testid="stFormSubmitButton"] button[kind="primary"] *{color:#fff!important}
        [data-testid="stButton"] button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover{background:var(--cn-color-primary-hover)!important;border-color:var(--cn-color-primary-hover)!important}
        [data-testid="stButton"] button[kind="secondary"],[data-testid="stFormSubmitButton"] button[kind="secondary"],[data-testid="stDownloadButton"] button,[data-testid="stLinkButton"] a,[data-testid="stPopover"] button{background:#fff!important;border:1px solid var(--cn-color-border-strong)!important;color:var(--cn-color-secondary)!important}
        [data-testid="stButton"] button[kind="secondary"]:hover,[data-testid="stDownloadButton"] button:hover,[data-testid="stLinkButton"] a:hover,[data-testid="stPopover"] button:hover{background:#f0f4f2!important;border-color:#8fa49a!important;color:#183126!important}
        button:disabled,[aria-disabled="true"]{opacity:.48!important;cursor:not-allowed!important;filter:saturate(.65)}
        button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,[role="combobox"]:focus-visible,[role="tab"]:focus-visible,[role="radio"]:focus-visible{outline:3px solid rgba(23,107,58,.28)!important;outline-offset:2px!important}
        [data-testid="stVerticalBlockBorderWrapper"],[data-testid="stExpander"],[data-testid="stMetric"]{background:#fff!important;border:1px solid var(--cn-color-border)!important;border-radius:var(--cn-radius-md)!important;box-shadow:none!important}
        [data-testid="stExpander"] summary{min-height:42px!important;font-size:.86rem!important;font-weight:680!important;color:var(--cn-color-text)!important}
        [data-testid="stMetric"]{padding:11px 13px!important}[data-testid="stMetricLabel"]{color:var(--cn-color-text-secondary)!important}[data-testid="stMetricValue"]{font-weight:770!important;letter-spacing:-.02em!important}
        .cn-status-card,.cn-step,.cn-recommend-card,.cn-progress-hero,.cn-attention-row,.cn-flow-context,.cn-follow-shell,.cn-next-card,.cn-venue-card,.cn-live-card,.public-match-card{box-shadow:none!important;border-color:var(--cn-color-border)!important;border-radius:var(--cn-radius-md)!important}
        [data-testid="stAlert"]{border-radius:var(--cn-radius-md)!important;border-width:1px!important;box-shadow:none!important;padding:10px 12px!important;margin:.25rem 0 .5rem!important}[data-testid="stAlert"] p{font-size:.84rem!important;line-height:1.4!important}
        [data-testid="stTabs"] [role="tablist"]{gap:3px!important;border-bottom:1px solid var(--cn-color-border)!important}[data-testid="stTabs"] button[role="tab"]{min-height:38px!important;padding:6px 10px!important;border-radius:8px 8px 0 0!important;color:var(--cn-color-text-secondary)!important;font-size:.83rem!important;font-weight:650!important}[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{color:var(--cn-color-primary)!important;font-weight:720!important}
        [data-testid="stButtonGroup"] button{min-height:36px!important;background:#fff!important;border-color:var(--cn-color-border)!important;color:var(--cn-color-secondary)!important;font-size:.82rem!important}[data-testid="stButtonGroup"] button[aria-pressed="true"],[data-testid="stButtonGroup"] button[aria-checked="true"],[data-testid="stButtonGroup"] [data-selected="true"]{background:var(--cn-color-primary-soft)!important;color:#14552f!important;border-color:#98bca7!important;font-weight:700!important}
        [data-testid="stDataFrame"],.texttv-table-wrap{border:1px solid var(--cn-color-border)!important;border-radius:var(--cn-radius-md)!important;background:#fff!important;box-shadow:none!important;overflow:auto!important}[data-testid="stDataFrame"] [role="columnheader"]{background:#edf2ef!important;color:var(--cn-color-text)!important;font-size:.78rem!important;font-weight:720!important}[data-testid="stDataFrame"] [role="gridcell"]{color:var(--cn-color-text)!important;font-size:.82rem!important}
        .texttv-table{width:100%!important;border-collapse:separate!important;border-spacing:0!important}.texttv-table th{position:sticky!important;top:0!important;z-index:2!important;background:#edf2ef!important;color:var(--cn-color-text)!important;font-size:.77rem!important;font-weight:720!important}.texttv-table td,.texttv-table th{padding:8px 10px!important;border-bottom:1px solid #e5ebe7!important}.texttv-table tbody tr:hover td{background:#f8faf9!important}
        .cn-empty-state{background:var(--cn-color-surface-subtle)!important;border:1px dashed var(--cn-color-border-strong)!important;border-radius:var(--cn-radius-md)!important;padding:20px!important;box-shadow:none!important}.cn-empty-state .icon{background:var(--cn-color-primary-soft)!important;border-radius:var(--cn-radius-sm)!important}.cn-empty-state p{color:var(--cn-color-text-secondary)!important}
        .cup-hero,.cn-next-match,.cn-live-head,.cn-live-card.is-live{background-image:none!important}.cup-hero{background:#17324d!important;box-shadow:none!important}
        .cn-current-admin-page{background:rgba(245,247,246,.96)!important;border-color:var(--cn-color-border)!important;box-shadow:none!important;backdrop-filter:none!important;-webkit-backdrop-filter:none!important}.cn-admin-nav-group-title,.cn-admin-section-label,.cn-flow-kicker{color:var(--cn-color-text-secondary)!important;font-size:.72rem!important;font-weight:730!important;letter-spacing:.055em!important;text-transform:uppercase!important}.cn-flow-context{padding:10px 12px!important;margin:4px 0 8px!important;background:#fff!important}
        .cn-public-top-nav + div [data-testid="stButton"] button{min-height:38px!important;font-size:.81rem!important}.public-metric{box-shadow:none!important;border-color:var(--cn-color-border)!important}.public-match-card{background:#fff!important}
        @media(max-width:1024px){:root{--cn-content-max:100%}.stApp .block-container{padding-left:16px!important;padding-right:16px!important}}
        @media(max-width:768px){:root{--cn-control-h:44px}html,body,.stApp{max-width:100vw!important;overflow-x:hidden!important}.stApp .block-container{padding-left:10px!important;padding-right:10px!important;padding-bottom:88px!important}[data-testid="stHorizontalBlock"]{gap:8px!important}[data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stLinkButton"] a{min-height:44px!important}h1{font-size:1.46rem!important}h2{font-size:1.22rem!important}h3{font-size:1.02rem!important}[data-testid="stDataFrame"],.texttv-table-wrap{max-width:100%!important;overflow-x:auto!important;-webkit-overflow-scrolling:touch}[data-testid="stPopoverBody"]{max-width:calc(100vw - 20px)!important;max-height:calc(100vh - 24px)!important;overflow:auto!important}}
        @media(max-width:390px){.stApp .block-container{padding-left:8px!important;padding-right:8px!important}[data-testid="stHorizontalBlock"]{gap:6px!important}[data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button{padding-left:9px!important;padding-right:9px!important;font-size:.81rem!important}}
        @media(min-width:1440px){:root{--cn-content-max:1280px}}
        @media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
        </style>""",
        unsafe_allow_html=True,
    )

inject_v193_product_design_system()

# Global CupNavi-identitet. Logotypen ligger lokalt i releasen så den inte kräver
# nätverksanrop. Den renderas som en liten integrerad brand-rad i appskalet och
# ligger kvar i alla vyer under scrollning.
CUPNAVI_LOGO_FILE = Path(__file__).with_name("assets") / "cupnavi_logo.png"


def render_persistent_brand():
    try:
        logo_b64 = base64.b64encode(CUPNAVI_LOGO_FILE.read_bytes()).decode("ascii")
    except OSError:
        return
    st.markdown(
        f"""
        <style>
          .cn-persistent-brand {{
            position:fixed;
            top:10px;
            left:50%;
            transform:translateX(-50%);
            z-index:999997;
            display:flex;
            align-items:center;
            justify-content:center;
            min-width:150px;
            max-width:min(185px, calc(100vw - 28px));
            padding:5px 10px;
            border:1px solid #d9e2dd;
            border-radius:10px;
            background:#ffffff;
            box-shadow:0 2px 8px rgba(16,24,20,.07);
            pointer-events:none;
          }}
          .cn-persistent-brand img {{
            display:block;
            width:min(100%, 155px);
            height:auto;
          }}
          .stApp .block-container {{
            padding-top:3.2rem !important;
          }}
          @media (max-width:760px) {{
            .cn-persistent-brand {{
              top:8px;
              min-width:auto;
              width:auto;
              max-width:170px;
              padding:5px 9px;
              border-radius:9px;
              box-shadow:0 2px 8px rgba(16,24,20,.07);
            }}
            .cn-persistent-brand img {{
              width:min(100%, 145px);
            }}
            .stApp .block-container {{
              padding-top:3.7rem !important;
            }}
          }}
        </style>
        <div class="cn-persistent-brand" aria-label="CupNavi">
          <img src="data:image/png;base64,{logo_b64}" alt="CupNavi logotyp">
        </div>
        """,
        unsafe_allow_html=True,
    )


render_persistent_brand()
# APP_VERSION centraliseras i cupnavi_core/version.py
DB_FILE = Path(os.getenv("CUPNAVI_DB_PATH") or Path(__file__).with_name("turnering.db"))


def setting(name):
    """Hämta en hemlighet från Streamlit Secrets eller en miljövariabel."""
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        value = None
    return str(value).strip() if value else os.getenv(name, "").strip()


TURSO_DATABASE_URL = setting("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = setting("TURSO_AUTH_TOKEN")
CLOUD_DATABASE_ENABLED = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)


def _client_identity_hash(scope):
    """Hashad klientnyckel för rate limiting; rå IP lagras aldrig."""
    forwarded = ""
    user_agent = ""
    try:
        headers = getattr(st.context, "headers", {}) or {}
        forwarded = str(headers.get("X-Forwarded-For") or headers.get("x-forwarded-for") or "")
        user_agent = str(headers.get("User-Agent") or headers.get("user-agent") or "")
    except Exception:
        pass
    if forwarded:
        identity = forwarded.split(",", 1)[0].strip() + "|" + user_agent
    else:
        nonce_key = "_cupnavi_rate_nonce"
        if nonce_key not in st.session_state:
            st.session_state[nonce_key] = uuid.uuid4().hex
        identity = str(st.session_state[nonce_key]) + "|" + user_agent
    return hashlib.sha256(f"{scope}|{identity}".encode("utf-8")).hexdigest()


def _rate_allowed(scope, limit, window_seconds):
    subject = _client_identity_hash(scope)
    with db() as con:
        allowed, retry_after, count = consume_rate_limit(
            con,
            scope=scope,
            subject_hash=subject,
            limit=int(limit),
            window_seconds=int(window_seconds),
        )
        con.commit()
    return allowed, retry_after, count


def require_admin_access():
    """Kräv adminlösenord i webbdrift. Lokalt läge får köras utan lösenord."""
    admin_password = setting("ADMIN_PASSWORD")
    if not admin_password:
        if CLOUD_DATABASE_ENABLED:
            st.sidebar.error("Adminlösenord saknas i Streamlit Secrets.")
            st.error("Administration är låst tills ADMIN_PASSWORD har lagts till i Streamlit Secrets.")
            st.stop()
        st.sidebar.warning("Lokalt läge utan adminlösenord")
        return

    if st.session_state.get("admin_authenticated"):
        st.sidebar.success("Inloggad som administratör")
        if st.sidebar.button("Logga ut", use_container_width=True):
            st.session_state["admin_authenticated"] = False
            st.rerun()
        return

    st.title("Administratörsinloggning")
    st.caption("Turneringsvyn är offentlig. Administrationen kräver lösenord.")
    with st.form("admin_login"):
        entered_password = st.text_input("Adminlösenord", type="password")
        submitted = st.form_submit_button(tr("Logga in"), type="primary", use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered_password, admin_password):
            st.session_state["admin_authenticated"] = True
            st.rerun()
        allowed, retry_after, _ = _rate_allowed("admin-login", 8, 600)
        if not allowed:
            st.error(f"För många misslyckade inloggningsförsök. Försök igen om cirka {max(1, retry_after // 60)} minut(er).")
        else:
            st.error(tr("Fel lösenord."))
    st.stop()


def _verify_tournament_role_code(table_name, tournament_id, entered_code):
    if table_name not in {"match_reporter_credentials", "referee_credentials"}:
        return None
    credential = one_row(
        f"SELECT code_salt,code_hash FROM {table_name} WHERE tournament_id=?",
        (int(tournament_id),),
    )
    if credential and verify_access_code(entered_code, credential["code_salt"], credential["code_hash"]):
        return credential
    return None


def require_match_reporter_access():
    """Matchrapportör loggar normalt in med en turneringsspecifik fyrsiffrig kod."""
    reporter_password = setting("MATCH_REPORTER_PASSWORD")
    test_password = setting("TEST_MATCH_REPORTER_PASSWORD") or "123"

    if st.session_state.get("reporter_authenticated"):
        auth_scope = st.session_state.get("reporter_auth_scope", "production")
        if auth_scope == "tournament":
            authenticated_tid = st.session_state.get("reporter_tournament_id")
            credential_table = (
                "referee_credentials"
                if st.session_state.get("reporter_role") == "referee"
                else "match_reporter_credentials"
            )
            current_credential = one_row(
                f"SELECT code_hash FROM {credential_table} WHERE tournament_id=?",
                (authenticated_tid,),
            )
            # A regenerated code immediately invalidates sessions authenticated with
            # the previous credential.
            if (
                current_credential is None
                or not hmac.compare_digest(
                    str(st.session_state.get("reporter_credential_hash", "")),
                    str(current_credential["code_hash"]),
                )
            ):
                st.session_state["reporter_authenticated"] = False
                st.session_state.pop("reporter_auth_scope", None)
                st.session_state.pop("reporter_tournament_id", None)
                st.session_state.pop("reporter_credential_hash", None)
                st.warning("Matchrapportörskoden har ändrats. Logga in med den nya koden.")
                st.rerun()
            st.sidebar.success(
                "Inloggad som domare"
                if st.session_state.get("reporter_role") == "referee"
                else "Inloggad som matchrapportör"
            )
        else:
            st.sidebar.success(
                "Inloggad som matchrapportör"
                + (" · endast testmiljöer" if auth_scope == "test_only" else "")
            )
        if st.sidebar.button("Logga ut", key="reporter_logout", use_container_width=True):
            st.session_state["reporter_authenticated"] = False
            st.session_state.pop("reporter_auth_scope", None)
            st.session_state.pop("reporter_tournament_id", None)
            st.session_state.pop("reporter_credential_hash", None)
            st.session_state.pop("reporter_role", None)
            st.rerun()
        return

    st.title(tr("Matchrapportör"))
    st.caption("Välj turnering och ange din fyrsiffriga matchrapportörs- eller domarkod.")

    reporter_tournaments = all_rows(
        """SELECT id,name,environment_type FROM tournaments
           WHERE COALESCE(lifecycle_status,'draft')!='trashed'
           ORDER BY CASE COALESCE(lifecycle_status,'draft')
                    WHEN 'live' THEN 0 WHEN 'published' THEN 1
                    WHEN 'draft' THEN 2 WHEN 'completed' THEN 3 ELSE 4 END,
                    COALESCE(start_date,tournament_date) DESC,name"""
    )
    if not reporter_tournaments:
        st.info("Det finns ingen turnering att rapportera ännu.")
        st.stop()

    reporter_ids = [int(row["id"]) for row in reporter_tournaments]
    reporter_names = {int(row["id"]): row["name"] for row in reporter_tournaments}
    with st.form("match_reporter_login"):
        reporter_tid = st.selectbox(
            "Turnering",
            reporter_ids,
            format_func=lambda tournament_id: reporter_names[tournament_id],
            key="reporter_login_tournament",
        )
        entered_password = st.text_input(
            "Kod",
            type="password",
            max_chars=12,
            placeholder="4 siffror",
        )
        submitted = st.form_submit_button("Logga in", type="primary", use_container_width=True)

    if submitted:
        credential = _verify_tournament_role_code(
            "match_reporter_credentials", reporter_tid, entered_password
        )
        referee_credential = _verify_tournament_role_code(
            "referee_credentials", reporter_tid, entered_password
        )
        role_credential = credential or referee_credential
        if role_credential:
            st.session_state["reporter_authenticated"] = True
            st.session_state["reporter_auth_scope"] = "tournament"
            st.session_state["reporter_role"] = "referee" if referee_credential else "reporter"
            st.session_state["reporter_tournament_id"] = int(reporter_tid)
            st.session_state["reporter_credential_hash"] = str(role_credential["code_hash"])
            st.session_state["preferred_tournament_id"] = int(reporter_tid)
            st.session_state["active_tournament_selector"] = int(reporter_tid)
            st.rerun()

        # Backward compatibility for installations that still use Streamlit Secrets.
        if reporter_password and hmac.compare_digest(entered_password, reporter_password):
            st.session_state["reporter_authenticated"] = True
            st.session_state["reporter_auth_scope"] = "production"
            st.rerun()
        if hmac.compare_digest(entered_password, test_password):
            st.session_state["reporter_authenticated"] = True
            st.session_state["reporter_auth_scope"] = "test_only"
            st.rerun()

        allowed, retry_after, _ = _rate_allowed(
            f"reporter-login:{int(reporter_tid)}",
            12,
            600,
        )
        if not allowed:
            st.error(
                f"För många misslyckade försök. Försök igen om cirka "
                f"{max(1, retry_after // 60)} minut(er)."
            )
        else:
            if credential is None:
                st.error("Ingen matchrapportörskod är skapad för den här turneringen ännu.")
            else:
                st.error("Fel kod.")
    st.stop()


class CloudConnection:
    """DB-API-adapter som återanvänder Turso-anslutningen under Streamlit-sessionen."""
    def __init__(self, raw):
        self.raw = raw
        self._dirty = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Turso-anslutningen hålls öppen mellan appens reruns. Att öppna/stänga en
        # nätverksanslutning för varje SELECT var den största prestandaflaskhalsen.
        if exc_type is None:
            if self._dirty:
                self.commit()
        else:
            self.rollback()
        return False

    @staticmethod
    def _is_write(sql):
        first = sql.lstrip().split(None, 1)[0].upper() if sql and sql.strip() else ""
        return first not in {"SELECT", "PRAGMA", "EXPLAIN"}

    def execute(self, sql, params=()):
        is_write = self._is_write(sql)
        if is_write:
            self._dirty = True
        try:
            return self.raw.execute(sql, params)
        except Exception:
            # En tappad/stängd Turso-anslutning ska inte kräva en separat
            # SELECT 1 före varje normal fråga. Läsfrågor får i stället
            # en enda säker återanslutning först när ett verkligt fel uppstår.
            if is_write:
                raise
            fresh = _new_cloud_raw_connection()
            st.session_state["_cupnavi_turso_connection"] = fresh
            self.raw = fresh
            return self.raw.execute(sql, params)

    def executemany(self, sql, params):
        if self._is_write(sql):
            self._dirty = True
        return self.raw.executemany(sql, params)

    def commit(self):
        result = self.raw.commit()
        self._dirty = False
        return result

    def rollback(self):
        rollback = getattr(self.raw, "rollback", None)
        self._dirty = False
        return rollback() if rollback else None

    def close(self):
        # Medvetet no-op i webbdrift. Sessionens anslutning återanvänds för att
        # slippa nätverks-handshake vid varje liten databasfråga.
        return None


def _new_cloud_raw_connection():
    try:
        import libsql
    except ImportError as exc:
        raise RuntimeError(
            "Turso är konfigurerat men Python-paketet libsql saknas. "
            "Installera requirements.txt."
        ) from exc
    return libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)


def _cloud_raw_connection():
    """Återanvänd Turso-anslutningen utan ett extra nätverksanrop före varje fråga."""
    raw = st.session_state.get("_cupnavi_turso_connection")
    if raw is None:
        raw = _new_cloud_raw_connection()
        st.session_state["_cupnavi_turso_connection"] = raw
    return raw


def db():
    """Använd Turso i molnet och lokal SQLite på utvecklingsdatorn."""
    if CLOUD_DATABASE_ENABLED:
        return CloudConnection(_cloud_raw_connection())

    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def update_match_result_if_unchanged(
    con,
    match_id,
    expected,
    *,
    home_score,
    away_score,
    home_penalties=None,
    away_penalties=None,
    decided_winner_id=None,
    referee_id=None,
):
    """Optimistic lock: update only if the row still equals what this UI originally loaded."""
    sql = """UPDATE matches
             SET home_score=?,away_score=?,home_penalties=?,away_penalties=?,
                 decided_winner_id=?,referee_id=?
             WHERE id=?
               AND home_score IS ? AND away_score IS ?
               AND home_penalties IS ? AND away_penalties IS ?
               AND decided_winner_id IS ? AND referee_id IS ?"""
    params = (
        home_score, away_score, home_penalties, away_penalties,
        decided_winner_id, referee_id, int(match_id),
        expected.get("home_score"), expected.get("away_score"),
        expected.get("home_penalties"), expected.get("away_penalties"),
        expected.get("decided_winner_id"), expected.get("referee_id"),
    )
    cursor = con.execute(sql, params)
    rowcount = getattr(cursor, "rowcount", None)
    if rowcount is not None and rowcount >= 0:
        return rowcount == 1

    # Adapter fallback: verify that the requested value is now present. The conditional
    # WHERE above still prevented an overwrite if another session changed the row first.
    verify = con.execute(
        """SELECT home_score,away_score,home_penalties,away_penalties,decided_winner_id,referee_id
           FROM matches WHERE id=?""",
        (int(match_id),),
    ).fetchone()
    if verify is None:
        return False
    values = list(verify) if not isinstance(verify, sqlite3.Row) else [
        verify["home_score"], verify["away_score"], verify["home_penalties"],
        verify["away_penalties"], verify["decided_winner_id"], verify["referee_id"],
    ]
    return values == [home_score, away_score, home_penalties, away_penalties, decided_winner_id, referee_id]


def update_player_match_stats_if_unchanged(
    con,
    match_id,
    player_id,
    expected,
    *,
    goals,
    assists,
    yellow_cards,
    red_cards,
):
    """Optimistic lock for one player's match-event counters.

    INSERT handles a first-time stat row. On conflict, UPDATE is allowed only
    when the stored counters still equal the snapshot originally loaded by the
    editor. A stale browser session therefore cannot silently overwrite newer
    goals/assists/cards.
    """
    sql = """
        INSERT INTO player_match_stats(
            match_id,player_id,goals,assists,yellow_cards,red_cards
        ) VALUES(?,?,?,?,?,?)
        ON CONFLICT(match_id,player_id) DO UPDATE SET
            goals=excluded.goals,
            assists=excluded.assists,
            yellow_cards=excluded.yellow_cards,
            red_cards=excluded.red_cards
        WHERE player_match_stats.goals IS ?
          AND player_match_stats.assists IS ?
          AND player_match_stats.yellow_cards IS ?
          AND player_match_stats.red_cards IS ?
    """
    params = (
        int(match_id),
        int(player_id),
        int(goals),
        int(assists),
        int(yellow_cards),
        int(red_cards),
        int(expected.get("goals", 0) or 0),
        int(expected.get("assists", 0) or 0),
        int(expected.get("yellow_cards", 0) or 0),
        int(expected.get("red_cards", 0) or 0),
    )
    cursor = con.execute(sql, params)
    rowcount = getattr(cursor, "rowcount", None)
    if rowcount is not None and rowcount >= 0:
        return rowcount == 1

    verify = con.execute(
        """SELECT goals,assists,yellow_cards,red_cards
           FROM player_match_stats WHERE match_id=? AND player_id=?""",
        (int(match_id), int(player_id)),
    ).fetchone()
    if verify is None:
        return False
    if isinstance(verify, sqlite3.Row):
        values = [
            verify["goals"], verify["assists"],
            verify["yellow_cards"], verify["red_cards"],
        ]
    else:
        values = list(verify)
    return values == [int(goals), int(assists), int(yellow_cards), int(red_cards)]


def _rows_from_cursor(cursor):
    """Normalisera både sqlite3.Row och libsql-tupler till dictionary-liknande rader."""
    rows = cursor.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], sqlite3.Row):
        return rows
    description = getattr(cursor, "description", None) or []
    names = [column[0] for column in description]
    if names:
        return [dict(zip(names, row)) for row in rows]
    return rows


def _one_from_cursor(cursor):
    row = cursor.fetchone()
    if row is None or isinstance(row, sqlite3.Row):
        return row
    description = getattr(cursor, "description", None) or []
    names = [column[0] for column in description]
    return dict(zip(names, row)) if names else row


def execute_script(con, script):
    """Kör ett SQL-script även när anslutningen saknar sqlite3.executescript."""
    if not CLOUD_DATABASE_ENABLED and hasattr(con, "executescript"):
        return con.executescript(script)
    buffer = ""
    for line in script.splitlines(True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                con.execute(statement)
            buffer = ""
    if buffer.strip():
        con.execute(buffer)


def columns(table):
    with db() as con:
        cursor = con.execute(f"PRAGMA table_info({table})")
        return {row["name"] for row in _rows_from_cursor(cursor)}


def _connection_columns(con, table):
    cursor = con.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in _rows_from_cursor(cursor)}


def ensure_v96_experience_schema_compat(con):
    """
    Självläkande kompatibilitetslager för v96+-data.

    Det här skyddar särskilt mot en ofullständig GitHub-upload där ny app.py
    har publicerats tillsammans med en äldre migrationsmodul. Alla operationer
    är idempotenta och migration 5 markeras först efter att hela minimischemat
    finns på plats.
    """
    con.execute(
        """CREATE TABLE IF NOT EXISTS cupnavi_schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )"""
    )

    tournament_cols = _connection_columns(con, "tournaments")
    team_cols = _connection_columns(con, "teams")
    match_cols = _connection_columns(con, "matches")

    if "sport" not in tournament_cols:
        con.execute("ALTER TABLE tournaments ADD COLUMN sport TEXT NOT NULL DEFAULT 'Fotboll'")
    if "checked_in" not in team_cols:
        con.execute("ALTER TABLE teams ADD COLUMN checked_in INTEGER NOT NULL DEFAULT 0")
    if "checked_in_at" not in team_cols:
        con.execute("ALTER TABLE teams ADD COLUMN checked_in_at TEXT")
    if "original_scheduled_start" not in match_cols:
        con.execute("ALTER TABLE matches ADD COLUMN original_scheduled_start TEXT")

    execute_script(
        con,
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT 'Admin',
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            description TEXT NOT NULL,
            before_json TEXT,
            after_json TEXT,
            reversible INTEGER NOT NULL DEFAULT 0,
            undone_at TEXT
        );
        CREATE TABLE IF NOT EXISTS cup_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Info',
            title TEXT NOT NULL,
            detail TEXT,
            public INTEGER NOT NULL DEFAULT 1,
            related_match_id INTEGER REFERENCES matches(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            event_key TEXT,
            UNIQUE(tournament_id, team_id, event_key)
        );
        CREATE TABLE IF NOT EXISTS venue_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            kind TEXT NOT NULL DEFAULT 'Övrigt',
            label TEXT NOT NULL,
            detail TEXT,
            url TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS referee_acknowledgements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            referee_id INTEGER NOT NULL REFERENCES referees(id) ON DELETE CASCADE,
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            acknowledged_at TEXT NOT NULL,
            UNIQUE(referee_id, match_id)
        );
        CREATE INDEX IF NOT EXISTS idx_audit_tournament_created ON audit_log(tournament_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_feed_tournament_created ON cup_feed(tournament_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_notifications_tournament_team ON notifications(tournament_id, team_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_venue_points_tournament ON venue_points(tournament_id, sort_order);
        CREATE INDEX IF NOT EXISTS idx_ref_ack_tournament_referee ON referee_acknowledgements(tournament_id, referee_id);
        """,
    )
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(5,?,?)",
        ("experience_toolkit_v96", datetime.now().isoformat(timespec="seconds")),
    )


def ensure_v99_team_portal_schema_compat(con):
    """Idempotent skydd för Lagportalens schema även vid blandade releasefiler."""
    tournament_cols = _connection_columns(con, "tournaments")
    team_cols = _connection_columns(con, "teams")
    tournament_additions = {
        "squad_deadline_minutes": "INTEGER NOT NULL DEFAULT 30",
        "max_roster_size": "INTEGER NOT NULL DEFAULT 0",
        "allow_team_public_contact": "INTEGER NOT NULL DEFAULT 0",
    }
    team_additions = {
        "checked_in_by": "TEXT",
        "kit_confirmed_at": "TEXT",
        "public_contact_name": "TEXT",
        "public_contact_phone": "TEXT",
        "public_contact_email": "TEXT",
        "public_contact_enabled": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, ddl in tournament_additions.items():
        if name not in tournament_cols:
            con.execute(f"ALTER TABLE tournaments ADD COLUMN {name} {ddl}")
    for name, ddl in team_additions.items():
        if name not in team_cols:
            con.execute(f"ALTER TABLE teams ADD COLUMN {name} {ddl}")
    execute_script(
        con,
        """
        CREATE TABLE IF NOT EXISTS participant_access_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            code_salt TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            rotated_at TEXT,
            UNIQUE(tournament_id, team_id)
        );
        CREATE TABLE IF NOT EXISTS match_rosters (
            match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
            team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
            selected_at TEXT NOT NULL,
            selected_by TEXT NOT NULL DEFAULT 'Deltagaransvarig',
            PRIMARY KEY(match_id, team_id, player_id)
        );
        CREATE INDEX IF NOT EXISTS idx_participant_access_tournament_team ON participant_access_credentials(tournament_id, team_id);
        CREATE INDEX IF NOT EXISTS idx_match_rosters_match_team ON match_rosters(match_id, team_id);
        """,
    )
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(6,?,?)",
        ("participant_team_portal_v99", datetime.now().isoformat(timespec="seconds")),
    )


def ensure_v106_participant_privacy_schema_compat(con):
    """Idempotent kontakt-, spelarnamn-, integritets- och admin-kodfält för v106."""
    team_cols = _connection_columns(con, "teams")
    player_cols = _connection_columns(con, "players")
    credential_cols = _connection_columns(con, "participant_access_credentials")
    team_additions = {
        "responsible_name": "TEXT",
        "responsible_phone": "TEXT",
        "responsible_email": "TEXT",
        "responsible_contact_protected": "INTEGER NOT NULL DEFAULT 1",
    }
    player_additions = {
        "first_name": "TEXT",
        "last_name": "TEXT",
        "is_protected": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, ddl in team_additions.items():
        if name not in team_cols:
            con.execute(f"ALTER TABLE teams ADD COLUMN {name} {ddl}")
    for name, ddl in player_additions.items():
        if name not in player_cols:
            con.execute(f"ALTER TABLE players ADD COLUMN {name} {ddl}")
    if "admin_code" not in credential_cols:
        con.execute("ALTER TABLE participant_access_credentials ADD COLUMN admin_code TEXT")
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(9,?,?)",
        ("participant_privacy_and_admin_codes_v106", datetime.now().isoformat(timespec="seconds")),
    )


def ensure_v108_team_messages_schema_compat(con):
    """Idempotent intern meddelandefunktion mellan lag och arrangör."""
    execute_script(
        con,
        """
        CREATE TABLE IF NOT EXISTS team_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            sender_type TEXT NOT NULL CHECK(sender_type IN ('team','organizer')),
            sender_team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
            recipient_type TEXT NOT NULL CHECK(recipient_type IN ('team','organizer')),
            recipient_team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            read_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_team_messages_tournament_created ON team_messages(tournament_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_team_messages_recipient_team ON team_messages(tournament_id, recipient_type, recipient_team_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_team_messages_sender_team ON team_messages(tournament_id, sender_type, sender_team_id, created_at);
        """,
    )
    message_cols = _connection_columns(con, "team_messages")
    if "request_token" not in message_cols:
        con.execute("ALTER TABLE team_messages ADD COLUMN request_token TEXT")
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_team_messages_request_token "
        "ON team_messages(tournament_id,request_token)"
    )
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(10,?,?)",
        ("team_messaging_v108", datetime.now().isoformat(timespec="seconds")),
    )


def _message_party_label(row, team_names):
    if row["sender_type"] == "organizer":
        sender = "Arrangören"
    else:
        sender = team_names.get(int(row["sender_team_id"]), "Lag") if row["sender_team_id"] is not None else "Lag"
    if row["recipient_type"] == "organizer":
        recipient = "Arrangören"
    else:
        recipient = team_names.get(int(row["recipient_team_id"]), "Lag") if row["recipient_team_id"] is not None else "Lag"
    return sender, recipient


def _send_team_message(
    tournament_id,
    sender_type,
    subject,
    message,
    *,
    sender_team_id=None,
    recipient_type="organizer",
    recipient_team_id=None,
    request_token=None,
):
    """Persist one internal message with server-side ownership checks.

    ``request_token`` makes a repeated submit idempotent: the same form action
    returns the original message id and does not send a second email.
    """
    tournament_id=int(tournament_id)
    subject=str(subject or "").strip()
    message=str(message or "").strip()
    sender_type=str(sender_type or "").strip()
    recipient_type=str(recipient_type or "").strip()
    request_token=str(request_token or "").strip() or None

    if sender_type not in {"team","organizer"}:
        raise ValueError("Ogiltig avsändare.")
    if recipient_type not in {"team","organizer"}:
        raise ValueError("Ogiltig mottagare.")
    if not subject or not message:
        raise ValueError("Ämne och meddelande krävs.")
    if len(subject) > 200:
        raise ValueError("Ämnet får vara högst 200 tecken.")
    if len(message) > 3000:
        raise ValueError("Meddelandet får vara högst 3000 tecken.")

    sender_team_id=int(sender_team_id) if sender_team_id is not None else None
    recipient_team_id=int(recipient_team_id) if recipient_team_id is not None else None

    if sender_type == "team":
        if sender_team_id is None:
            raise ValueError("Avsändande lag saknas.")
        sender_team=one_row(
            "SELECT id FROM teams WHERE id=? AND tournament_id=?",
            (sender_team_id,tournament_id),
        )
        if sender_team is None:
            raise ValueError("Avsändande lag tillhör inte turneringen.")
    elif sender_team_id is not None:
        raise ValueError("Arrangörsmeddelanden får inte ha avsändande lag.")

    recipient=None
    if recipient_type == "team":
        if recipient_team_id is None:
            raise ValueError("Mottagande lag saknas.")
        recipient=one_row(
            "SELECT id,name,responsible_name,responsible_email FROM teams WHERE id=? AND tournament_id=?",
            (recipient_team_id,tournament_id),
        )
        if recipient is None:
            raise ValueError("Mottagande lag tillhör inte turneringen.")
        if sender_type == "team" and sender_team_id == recipient_team_id:
            raise ValueError("Ett lag kan inte skicka meddelande till sig självt.")
    elif recipient_team_id is not None:
        raise ValueError("Arrangören har inget mottagande lag-id.")

    created_at=datetime.now().isoformat(timespec="microseconds")
    email_status="pending" if recipient_type == "team" else "not_applicable"
    inserted=True

    with db() as con:
        if request_token:
            cursor=con.execute(
                """INSERT OR IGNORE INTO team_messages(
                       tournament_id,sender_type,sender_team_id,recipient_type,recipient_team_id,
                       created_at,subject,message,email_status,request_token)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    tournament_id,sender_type,sender_team_id,recipient_type,recipient_team_id,
                    created_at,subject,message,email_status,request_token,
                ),
            )
            rowcount=getattr(cursor,"rowcount",None)
            row=con.execute(
                "SELECT id,sender_type,sender_team_id,recipient_type,recipient_team_id,subject,message,created_at "
                "FROM team_messages WHERE tournament_id=? AND request_token=?",
                (tournament_id,request_token),
            ).fetchone()
            if row is None:
                raise RuntimeError("Meddelandet kunde inte sparas.")
            message_id=int(row["id"] if isinstance(row,sqlite3.Row) else row[0])
            stored_created_at=(
                row["created_at"] if isinstance(row,sqlite3.Row) else row[7]
            )
            inserted=(
                rowcount == 1
                if rowcount is not None and rowcount >= 0
                else str(stored_created_at) == created_at
            )

            # A token may only ever represent the same logical form action.
            def _msg_value(key,index):
                return row[key] if isinstance(row,sqlite3.Row) else row[index]
            same_payload=(
                str(_msg_value("sender_type",1)) == sender_type
                and _msg_value("sender_team_id",2) == sender_team_id
                and str(_msg_value("recipient_type",3)) == recipient_type
                and _msg_value("recipient_team_id",4) == recipient_team_id
                and str(_msg_value("subject",5)) == subject
                and str(_msg_value("message",6)) == message
            )
            if not same_payload:
                con.rollback()
                raise ValueError("Meddelandeförfrågan är inte längre giltig. Försök igen.")
            con.commit()
        else:
            cursor=con.execute(
                """INSERT INTO team_messages(
                       tournament_id,sender_type,sender_team_id,recipient_type,recipient_team_id,
                       created_at,subject,message,email_status,request_token)
                   VALUES(?,?,?,?,?,?,?,?,?,NULL)""",
                (
                    tournament_id,sender_type,sender_team_id,recipient_type,recipient_team_id,
                    created_at,subject,message,email_status,
                ),
            )
            message_id=int(getattr(cursor,"lastrowid",0) or 0)
            con.commit()

    _clear_render_query_cache()

    # Email is best-effort and only runs for the first insert. Replayed request
    # tokens therefore cannot send duplicate notification email.
    if inserted and recipient_type == "team" and recipient_team_id:
        email=str(_row_value(recipient,"responsible_email","") or "").strip() if recipient else ""
        if email:
            ok,error=send_notification_email(
                email,
                f"Nytt meddelande i CupNavi: {subject}",
                f"Hej {(_row_value(recipient,'responsible_name','') or '').strip() or 'lagansvarig'},\n\n"
                f"{recipient['name']} har fått ett nytt meddelande i CupNavi. "
                f"Logga in i lagportalen för att läsa det.\n\nÄmne: {subject}",
            )
            run(
                "UPDATE team_messages SET email_status=?,email_error=? WHERE id=?",
                ("sent" if ok else "failed",error,int(message_id)),
            )
        else:
            run(
                "UPDATE team_messages SET email_status='skipped',email_error='responsible_email_missing' WHERE id=?",
                (int(message_id),),
            )
    return message_id

def _player_display_name(player_row, public=False):
    """Gemensam namnvisning med stöd för skyddade spelare och legacy-fältet name."""
    if public and bool(_row_value(player_row, "is_protected", 0)):
        return "Skyddad spelare"
    first = str(_row_value(player_row, "first_name", "") or "").strip()
    last = str(_row_value(player_row, "last_name", "") or "").strip()
    full = " ".join(part for part in (first, last) if part).strip()
    return full or str(_row_value(player_row, "name", "") or "").strip() or "Spelare"


def ensure_v100_international_schema_compat(con):
    """Idempotent international/multisport fields for mixed or legacy deployments."""
    tournament_cols = _connection_columns(con, "tournaments")
    additions = {
        "locale": "TEXT NOT NULL DEFAULT 'sv-SE'",
        "timezone_name": "TEXT NOT NULL DEFAULT 'Europe/Stockholm'",
        "participant_type": "TEXT NOT NULL DEFAULT 'team'",
        "country_code": "TEXT",
    }
    for name, ddl in additions.items():
        if name not in tournament_cols:
            con.execute(f"ALTER TABLE tournaments ADD COLUMN {name} {ddl}")
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(7,?,?)",
        ("international_multisport_foundation_v100", datetime.now().isoformat(timespec="seconds")),
    )


def ensure_v102_lifecycle_schema_compat(con):
    """Idempotent cup lifecycle/history fields and permanent public slugs."""
    tournament_cols = _connection_columns(con, "tournaments")
    lifecycle_was_present = "lifecycle_status" in tournament_cols
    additions = {
        "lifecycle_status": "TEXT NOT NULL DEFAULT 'draft'",
        "public_slug": "TEXT",
        "completed_at": "TEXT",
        "trashed_at": "TEXT",
        "environment_type": "TEXT NOT NULL DEFAULT 'production'",
    }
    for name, ddl in additions.items():
        if name not in tournament_cols:
            con.execute(f"ALTER TABLE tournaments ADD COLUMN {name} {ddl}")

    # Preserve legacy publication state when introducing the lifecycle model.
    if not lifecycle_was_present:
        con.execute(
            "UPDATE tournaments SET lifecycle_status=CASE WHEN COALESCE(is_published,0)=1 THEN 'published' ELSE 'draft' END"
        )
    else:
        con.execute(
            "UPDATE tournaments SET lifecycle_status=CASE WHEN COALESCE(is_published,0)=1 THEN 'published' ELSE 'draft' END "
            "WHERE lifecycle_status IS NULL OR lifecycle_status='' OR lifecycle_status NOT IN ('draft','published','live','completed','trashed')"
        )

    rows = con.execute(
        "SELECT id,name,COALESCE(start_date,tournament_date) AS start_date,public_slug FROM tournaments ORDER BY id"
    ).fetchall()
    used = {row[3] for row in rows if row[3]}
    for row in rows:
        if row[3]:
            continue
        slug = choose_unique_slug(row[1], row[2], row[0], used)
        con.execute("UPDATE tournaments SET public_slug=? WHERE id=?", (slug, row[0]))
        used.add(slug)

    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tournaments_public_slug ON tournaments(public_slug)")
    con.execute(
        "UPDATE tournaments SET environment_type='production' "
        "WHERE environment_type IS NULL OR environment_type='' OR environment_type NOT IN ('test','production')"
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_tournaments_lifecycle_status ON tournaments(lifecycle_status)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_tournaments_environment_type ON tournaments(environment_type)")
    con.execute(
        "INSERT OR IGNORE INTO cupnavi_schema_migrations(version,name,applied_at) VALUES(8,?,?)",
        ("tournament_lifecycle_history_v102", datetime.now().isoformat(timespec="seconds")),
    )


@st.cache_resource(show_spinner=False)
def init_db():
    """Initiera schema/migreringar en gång per app-process, inte en gång per besökare."""
    schema_key = f"{APP_VERSION}:{'cloud' if CLOUD_DATABASE_ENABLED else 'local'}"
    with db() as con:
        execute_script(
            con,
            """
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                tournament_date TEXT,
                start_date TEXT,
                end_date TEXT,
                expected_team_count INTEGER NOT NULL DEFAULT 0,
                is_published INTEGER NOT NULL DEFAULT 0,
                points_win INTEGER NOT NULL DEFAULT 3,
                points_draw INTEGER NOT NULL DEFAULT 1,
                points_loss INTEGER NOT NULL DEFAULT 0,
                playoff_format TEXT NOT NULL DEFAULT 'Inget slutspel',
                bronze_match INTEGER NOT NULL DEFAULT 0,
                arena_address TEXT,
                kiosk_available INTEGER NOT NULL DEFAULT 0,
                kiosk_information TEXT,
                public_information TEXT,
                organizer_phone TEXT,
                feedback_email TEXT,
                instagram_url TEXT,
                table_tiebreak TEXT NOT NULL DEFAULT 'Målskillnad först',
                playoff_tie_rule TEXT NOT NULL DEFAULT 'Straffar direkt',
                extra_time_minutes INTEGER NOT NULL DEFAULT 0,
                playoff_model_confirmed INTEGER NOT NULL DEFAULT 0,
                schedule_dirty INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                area TEXT NOT NULL,
                message TEXT NOT NULL,
                contact TEXT
            );
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                business_name TEXT,
                description TEXT,
                discount_code TEXT,
                valid_until TEXT,
                url TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sponsors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                level TEXT,
                description TEXT,
                website_url TEXT,
                logo_data_uri TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS functionaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                pitch_number INTEGER,
                notes TEXT,
                public_contact INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS visitor_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                session_token TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                view_count INTEGER NOT NULL DEFAULT 1,
                device_type TEXT NOT NULL DEFAULT 'Dator',
                browser TEXT NOT NULL DEFAULT 'Övrig',
                source TEXT NOT NULL DEFAULT 'Direkt / okänd',
                UNIQUE(tournament_id, session_token)
            );
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                primary_color TEXT NOT NULL DEFAULT '#111827',
                secondary_color TEXT NOT NULL DEFAULT '#FFFFFF',
                home_pattern TEXT NOT NULL DEFAULT 'Helfärgad',
                home_color_2 TEXT NOT NULL DEFAULT '#FFFFFF',
                away_pattern TEXT NOT NULL DEFAULT 'Helfärgad',
                away_color_2 TEXT NOT NULL DEFAULT '#111827',
                group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
                distance_km INTEGER NOT NULL DEFAULT 0,
                late_first_match INTEGER NOT NULL DEFAULT 0,
                earliest_first_time TEXT,
                travel_note TEXT
            );
            CREATE TABLE IF NOT EXISTS schedule_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                request_type TEXT NOT NULL,
                request_value TEXT,
                strength TEXT NOT NULL DEFAULT 'Önskemål',
                status TEXT NOT NULL DEFAULT 'Godkänd',
                priority INTEGER NOT NULL DEFAULT 100,
                note TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_schedule_requests_tournament
                ON schedule_requests(tournament_id,status,priority);
            CREATE INDEX IF NOT EXISTS idx_schedule_requests_team
                ON schedule_requests(team_id);

            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                player_number INTEGER,
                name TEXT NOT NULL,
                birth_year INTEGER,
                position TEXT
            );
            CREATE TABLE IF NOT EXISTS referees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                referee_level TEXT
            );
            CREATE TABLE IF NOT EXISTS match_reporter_credentials (
                tournament_id INTEGER PRIMARY KEY REFERENCES tournaments(id) ON DELETE CASCADE,
                code_salt TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS referee_credentials (
                tournament_id INTEGER PRIMARY KEY REFERENCES tournaments(id) ON DELETE CASCADE,
                code_salt TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS brackets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                bronze_match INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
                bracket_id INTEGER REFERENCES brackets(id) ON DELETE CASCADE,
                stage TEXT NOT NULL,
                round_no INTEGER NOT NULL DEFAULT 1,
                match_no INTEGER NOT NULL DEFAULT 1,
                home_source TEXT NOT NULL,
                away_source TEXT NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                home_penalties INTEGER,
                away_penalties INTEGER,
                referee_id INTEGER REFERENCES referees(id) ON DELETE SET NULL,
                schedule_published INTEGER NOT NULL DEFAULT 0,
                schedule_locked INTEGER NOT NULL DEFAULT 0,
                decided_winner_id INTEGER REFERENCES teams(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS player_match_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                goals INTEGER NOT NULL DEFAULT 0,
                assists INTEGER NOT NULL DEFAULT 0,
                yellow_cards INTEGER NOT NULL DEFAULT 0,
                red_cards INTEGER NOT NULL DEFAULT 0,
                UNIQUE(match_id, player_id)
            );
            CREATE TABLE IF NOT EXISTS schedule_rules (
                tournament_id INTEGER PRIMARY KEY REFERENCES tournaments(id) ON DELETE CASCADE,
                first_match_time TEXT NOT NULL DEFAULT '09:00',
                halves INTEGER NOT NULL DEFAULT 2,
                minutes_per_half INTEGER NOT NULL DEFAULT 20,
                halftime_minutes INTEGER NOT NULL DEFAULT 5,
                pitch_break_minutes INTEGER NOT NULL DEFAULT 5,
                minimum_team_rest_minutes INTEGER NOT NULL DEFAULT 45,
                avoid_consecutive_matches INTEGER NOT NULL DEFAULT 1,
                consecutive_match_break_minutes INTEGER NOT NULL DEFAULT 15,
                pitch_count INTEGER NOT NULL DEFAULT 2,
                referee_mode TEXT NOT NULL DEFAULT 'Automatisk',
                latest_kickoff_time TEXT NOT NULL DEFAULT '18:00'
            );
            DROP TRIGGER IF EXISTS prevent_team_limit_overflow;
            CREATE TRIGGER prevent_team_limit_overflow
            BEFORE INSERT ON teams
            FOR EACH ROW
            WHEN (
                SELECT COALESCE(expected_team_count, 0)
                FROM tournaments
                WHERE id = NEW.tournament_id
            ) > 0
            AND (
                SELECT COUNT(*)
                FROM teams
                WHERE tournament_id = NEW.tournament_id
            ) >= (
                SELECT expected_team_count
                FROM tournaments
                WHERE id = NEW.tournament_id
            )
            BEGIN
                SELECT RAISE(ABORT, 'TEAM_LIMIT_REACHED');
            END;
            """
        )
    # Uppgradera databasen från den tidigare versionen utan att radera data.
    team_cols = columns("teams")
    tournament_cols = columns("tournaments")
    match_cols = columns("matches")
    stat_cols = columns("player_match_stats")
    with db() as con:
        if "playoff_format" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN playoff_format TEXT NOT NULL DEFAULT 'Inget slutspel'")
        if "start_date" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN start_date TEXT")
        if "end_date" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN end_date TEXT")
        if "expected_team_count" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN expected_team_count INTEGER NOT NULL DEFAULT 0")
        if "is_published" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN is_published INTEGER NOT NULL DEFAULT 0")
        if "bronze_match" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN bronze_match INTEGER NOT NULL DEFAULT 0")
        if "arena_address" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN arena_address TEXT")
        if "kiosk_available" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN kiosk_available INTEGER NOT NULL DEFAULT 0")
        if "kiosk_information" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN kiosk_information TEXT")
        if "public_information" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN public_information TEXT")
        if "organizer_phone" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN organizer_phone TEXT")
        if "feedback_email" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN feedback_email TEXT")
        if "instagram_url" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN instagram_url TEXT")
        if "table_tiebreak" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN table_tiebreak TEXT NOT NULL DEFAULT 'Målskillnad först'")
        if "playoff_tie_rule" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN playoff_tie_rule TEXT NOT NULL DEFAULT 'Straffar direkt'")
        if "extra_time_minutes" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN extra_time_minutes INTEGER NOT NULL DEFAULT 0")
        if "playoff_model_confirmed" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN playoff_model_confirmed INTEGER NOT NULL DEFAULT 0")
        if "schedule_dirty" not in tournament_cols:
            con.execute("ALTER TABLE tournaments ADD COLUMN schedule_dirty INTEGER NOT NULL DEFAULT 1")
        con.execute(
            "UPDATE tournaments SET playoff_format=? WHERE playoff_format=?",
            ("Placeringsslutspel – ettor mot ettor osv.", "Flera egna slutspel"),
        )
        con.execute(
            "UPDATE tournaments SET playoff_format='Inget slutspel' WHERE playoff_format='Ett gemensamt slutspel'"
        )
        if "group_id" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL")
        if "primary_color" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN primary_color TEXT NOT NULL DEFAULT '#111827'")
        if "secondary_color" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN secondary_color TEXT NOT NULL DEFAULT '#FFFFFF'")
        if "home_pattern" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN home_pattern TEXT NOT NULL DEFAULT 'Helfärgad'")
        if "home_color_2" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN home_color_2 TEXT NOT NULL DEFAULT '#FFFFFF'")
        if "away_pattern" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN away_pattern TEXT NOT NULL DEFAULT 'Helfärgad'")
        if "away_color_2" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN away_color_2 TEXT NOT NULL DEFAULT '#111827'")
        if "distance_km" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN distance_km INTEGER NOT NULL DEFAULT 0")
        if "late_first_match" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN late_first_match INTEGER NOT NULL DEFAULT 0")
        if "earliest_first_time" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN earliest_first_time TEXT")
        if "travel_note" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN travel_note TEXT")
        if "scheduled_start" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN scheduled_start TEXT")
        if "pitch_number" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN pitch_number INTEGER")
        if "schedule_published" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN schedule_published INTEGER NOT NULL DEFAULT 0")
        if "schedule_locked" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN schedule_locked INTEGER NOT NULL DEFAULT 0")
        if "decided_winner_id" not in match_cols:
            con.execute("ALTER TABLE matches ADD COLUMN decided_winner_id INTEGER REFERENCES teams(id) ON DELETE SET NULL")
        if "yellow_cards" not in stat_cols:
            con.execute("ALTER TABLE player_match_stats ADD COLUMN yellow_cards INTEGER NOT NULL DEFAULT 0")
        if "red_cards" not in stat_cols:
            con.execute("ALTER TABLE player_match_stats ADD COLUMN red_cards INTEGER NOT NULL DEFAULT 0")
        rule_cols = columns("schedule_rules")
        if "latest_kickoff_time" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN latest_kickoff_time TEXT NOT NULL DEFAULT '18:00'")
        if "avoid_consecutive_matches" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN avoid_consecutive_matches INTEGER NOT NULL DEFAULT 1")
        if "consecutive_match_break_minutes" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN consecutive_match_break_minutes INTEGER NOT NULL DEFAULT 15")
        if "preference_order_json" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN preference_order_json TEXT")
        if "compactness_level" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN compactness_level INTEGER NOT NULL DEFAULT 50")
        if "recommended_group_count" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN recommended_group_count INTEGER NOT NULL DEFAULT 0")
        if "recommended_group_size" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN recommended_group_size INTEGER NOT NULL DEFAULT 0")
        if "recommended_playoff_size" not in rule_cols:
            con.execute("ALTER TABLE schedule_rules ADD COLUMN recommended_playoff_size INTEGER NOT NULL DEFAULT 0")
        if "request_priority" not in team_cols:
            con.execute("ALTER TABLE teams ADD COLUMN request_priority INTEGER NOT NULL DEFAULT 100")
        con.execute("UPDATE tournaments SET start_date=COALESCE(start_date,tournament_date), end_date=COALESCE(end_date,tournament_date)")
        # Ändringar som påverkar schemaförutsättningarna markerar automatiskt schemat som inaktuellt.
        execute_script(con, """
            DROP TRIGGER IF EXISTS cupnavi_dirty_team_insert;
            DROP TRIGGER IF EXISTS cupnavi_dirty_team_update;
            DROP TRIGGER IF EXISTS cupnavi_dirty_team_delete;
            DROP TRIGGER IF EXISTS cupnavi_dirty_group_insert;
            DROP TRIGGER IF EXISTS cupnavi_dirty_group_update;
            DROP TRIGGER IF EXISTS cupnavi_dirty_group_delete;
            DROP TRIGGER IF EXISTS cupnavi_dirty_ref_insert;
            DROP TRIGGER IF EXISTS cupnavi_dirty_ref_update;
            DROP TRIGGER IF EXISTS cupnavi_dirty_ref_delete;
            DROP TRIGGER IF EXISTS cupnavi_dirty_rules_update;
            DROP TRIGGER IF EXISTS cupnavi_dirty_tournament_rules;

            CREATE TRIGGER cupnavi_dirty_team_insert AFTER INSERT ON teams
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_team_update AFTER UPDATE OF group_id,distance_km,late_first_match,earliest_first_time,request_priority ON teams
            WHEN OLD.group_id IS NOT NEW.group_id
              OR OLD.distance_km IS NOT NEW.distance_km
              OR OLD.late_first_match IS NOT NEW.late_first_match
              OR OLD.earliest_first_time IS NOT NEW.earliest_first_time
              OR OLD.request_priority IS NOT NEW.request_priority
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_team_delete AFTER DELETE ON teams
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=OLD.tournament_id; END;

            CREATE TRIGGER cupnavi_dirty_group_insert AFTER INSERT ON groups
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_group_update AFTER UPDATE OF name ON groups
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_group_delete AFTER DELETE ON groups
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=OLD.tournament_id; END;

            CREATE TRIGGER cupnavi_dirty_ref_insert AFTER INSERT ON referees
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;
            CREATE TRIGGER cupnavi_dirty_ref_delete AFTER DELETE ON referees
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=OLD.tournament_id; END;

            CREATE TRIGGER cupnavi_dirty_rules_update AFTER UPDATE ON schedule_rules
            WHEN OLD.first_match_time IS NOT NEW.first_match_time
              OR OLD.halves IS NOT NEW.halves
              OR OLD.minutes_per_half IS NOT NEW.minutes_per_half
              OR OLD.halftime_minutes IS NOT NEW.halftime_minutes
              OR OLD.pitch_break_minutes IS NOT NEW.pitch_break_minutes
              OR OLD.minimum_team_rest_minutes IS NOT NEW.minimum_team_rest_minutes
              OR OLD.avoid_consecutive_matches IS NOT NEW.avoid_consecutive_matches
              OR OLD.consecutive_match_break_minutes IS NOT NEW.consecutive_match_break_minutes
              OR OLD.pitch_count IS NOT NEW.pitch_count
              OR OLD.referee_mode IS NOT NEW.referee_mode
              OR OLD.latest_kickoff_time IS NOT NEW.latest_kickoff_time
              OR OLD.preference_order_json IS NOT NEW.preference_order_json
              OR OLD.compactness_level IS NOT NEW.compactness_level
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.tournament_id; END;

            CREATE TRIGGER cupnavi_dirty_tournament_rules
            AFTER UPDATE OF start_date,end_date,playoff_format,bronze_match,playoff_tie_rule,extra_time_minutes ON tournaments
            WHEN OLD.start_date IS NOT NEW.start_date
              OR OLD.end_date IS NOT NEW.end_date
              OR OLD.playoff_format IS NOT NEW.playoff_format
              OR OLD.bronze_match IS NOT NEW.bronze_match
              OR OLD.playoff_tie_rule IS NOT NEW.playoff_tie_rule
              OR OLD.extra_time_minutes IS NOT NEW.extra_time_minutes
            BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.id; END;
        """)
        # V96+ måste även tåla blandade releasefiler i drift. Säkerställ därför
        # erfarenhets-/multisportschemat innan den versionsstyrda migreringen körs.
        ensure_v96_experience_schema_compat(con)
        ensure_v99_team_portal_schema_compat(con)
        ensure_v106_participant_privacy_schema_compat(con)
        ensure_v108_team_messages_schema_compat(con)
        ensure_v100_international_schema_compat(con)
        ensure_v102_lifecycle_schema_compat(con)

        # Från och med Stabilisering 1.0 registreras schemaändringar versionsstyrt.
        # Den äldre bootstrap-koden ovan behålls tills alla tidigare installationer
        # har migrerats säkert till den nya modellen.
        apply_migrations(con)
        # Defensive repair for mixed/partial cloud deployments. If v14 is
        # already marked but objects are missing, make the schema complete.
        ensure_competition_class_schema_compat(con)
        ensure_v16_setup_schema_compat(con)
        ensure_v18_pitch_names_schema_compat(con)
        # v140: migration markers alone are not enough in mixed Turso deploys.
        # Repair the concrete v19/v20 objects idempotently on startup.
        ensure_v19_schema_compat(con)
        ensure_v20_schema_compat(con)
        ensure_v21_schema_compat(con)
        con.commit()
    return schema_key


# Cache endast under ett enskilt Streamlit-renderingsvarv. Den återställs vid rerun,
# så administratören ser alltid nya data efter en skrivning utan långlivad cache.
_RENDER_QUERY_CACHE = {}
# Härledd data (tabeller, matchnummer, source resolution etc.) är också giltig
# endast under pågående renderingsvarv. Det undviker omräkning utan stale data.
_DERIVED_RENDER_CACHE = {}
_PERF = {"db_calls": 0, "db_ms": 0.0, "cache_hits": 0, "derived_hits": 0, "writes": 0}

def _record_db_call(started, write=False):
    _PERF["db_calls"] += 1
    _PERF["db_ms"] += (time.perf_counter() - started) * 1000
    if write:
        _PERF["writes"] += 1

def _cacheable_query(sql):
    # E2E mutates the same SQLite file from pytest; out-of-process writes cannot
    # invalidate CupNavi's in-process render cache. Force fresh reads only in E2E.
    if os.environ.get("CUPNAVI_E2E") == "1":
        return False
    return sql.lstrip().upper().startswith(("SELECT", "PRAGMA"))

def _query_cache_key(kind, sql, params):
    try:
        frozen_params = tuple(params)
        hash(frozen_params)
    except Exception:
        return None
    return (kind, sql, frozen_params)

def _clear_render_query_cache():
    _RENDER_QUERY_CACHE.clear()
    _DERIVED_RENDER_CACHE.clear()

def _derived_cache_get(key, factory):
    if key in _DERIVED_RENDER_CACHE:
        _PERF["derived_hits"] += 1
        return _DERIVED_RENDER_CACHE[key]
    value = factory()
    _DERIVED_RENDER_CACHE[key] = value
    return value

def all_rows(sql, params=()):
    key = _query_cache_key("all", sql, params) if _cacheable_query(sql) else None
    if key is not None and key in _RENDER_QUERY_CACHE:
        _PERF["cache_hits"] += 1
        return _RENDER_QUERY_CACHE[key]
    started = time.perf_counter()
    with db() as con:
        result = _rows_from_cursor(con.execute(sql, params))
    _record_db_call(started)
    if key is not None:
        _RENDER_QUERY_CACHE[key] = result
    return result


def one_row(sql, params=()):
    key = _query_cache_key("one", sql, params) if _cacheable_query(sql) else None
    if key is not None and key in _RENDER_QUERY_CACHE:
        _PERF["cache_hits"] += 1
        return _RENDER_QUERY_CACHE[key]
    started = time.perf_counter()
    with db() as con:
        result = _one_from_cursor(con.execute(sql, params))
    _record_db_call(started)
    if key is not None:
        _RENDER_QUERY_CACHE[key] = result
    return result


def run(sql, params=()):
    _clear_render_query_cache()
    started = time.perf_counter()
    with db() as con:
        cur = con.execute(sql, params)
        con.commit()
        lastrowid = cur.lastrowid
    _record_db_call(started, write=True)
    return lastrowid




def public_core_snapshot(tournament_id):
    """Load the public page's core rows through one DB connection.

    Results stay fresh on every Streamlit rerun; this only removes repeated
    connection establishment/teardown for matches + teams.
    """
    cache_key=("public-core-snapshot", int(tournament_id))
    if cache_key in _DERIVED_RENDER_CACHE:
        _PERF["derived_hits"] += 1
        return _DERIVED_RENDER_CACHE[cache_key]
    started=time.perf_counter()
    with db() as con:
        matches=_rows_from_cursor(con.execute(
            """SELECT m.*, r.name AS referee_name,
                      COALESCE(p.name, 'Plan ' || CAST(m.pitch_number AS TEXT)) AS pitch_name
               FROM matches m
               LEFT JOIN referees r ON r.id=m.referee_id
               LEFT JOIN pitches p ON p.tournament_id=m.tournament_id AND p.pitch_number=m.pitch_number
               WHERE m.tournament_id=? AND m.scheduled_start IS NOT NULL AND m.schedule_published=1
               ORDER BY m.scheduled_start,m.pitch_number,m.id""",
            (int(tournament_id),),
        ))
        teams=_rows_from_cursor(con.execute(
            "SELECT * FROM teams WHERE tournament_id=? ORDER BY name",
            (int(tournament_id),),
        ))
    _record_db_call(started)
    value={"matches":matches,"teams":teams}
    _DERIVED_RENDER_CACHE[cache_key]=value
    return value

def run_many(sql, params_seq):
    """Batcha flera likadana skrivningar i en enda DB-anslutning/commit."""
    rows = list(params_seq)
    if not rows:
        return 0
    _clear_render_query_cache()
    started = time.perf_counter()
    with db() as con:
        con.executemany(sql, rows)
        con.commit()
    _record_db_call(started, write=True)
    return len(rows)



def insert_tournament_compat(payload):
    """Skapa cup mot det faktiska tournaments-schemat i drift.

    Turso-installationer kan under en deploy kortvarigt ligga efter med en eller
    flera nya kolumner. Skapandet får då inte krascha; befintliga kolumner skrivs
    och nya fält får sina databaskonfigurerade defaults tills migreringen är klar.
    """
    _clear_render_query_cache()
    started = time.perf_counter()
    with db() as con:
        available = _connection_columns(con, "tournaments")
        ordered = [(name, value) for name, value in payload.items() if name in available]
        if not ordered or "name" not in {name for name, _ in ordered}:
            raise RuntimeError("Tournaments-schemat saknar obligatoriska kolumner.")
        names = [name for name, _ in ordered]
        values = tuple(value for _, value in ordered)
        placeholders = ",".join("?" for _ in names)
        sql = f"INSERT INTO tournaments({','.join(names)}) VALUES({placeholders})"
        cur = con.execute(sql, values)
        con.commit()
        lastrowid = cur.lastrowid
    _record_db_call(started, write=True)
    return lastrowid

def _json_snapshot(value):
    try:
        return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    except Exception:
        return None


def record_audit(tournament_id, action_type, entity_type, description, *, entity_id=None,
                 before=None, after=None, reversible=False, actor="Admin"):
    """Spara en kompakt ändringspost för nya CupNavi-verktyg."""
    return run(
        """INSERT INTO audit_log(
               tournament_id,created_at,actor,action_type,entity_type,entity_id,description,
               before_json,after_json,reversible
           ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (tournament_id, datetime.now().isoformat(timespec="seconds"), actor, action_type,
         entity_type, entity_id, description, _json_snapshot(before), _json_snapshot(after),
         1 if reversible else 0),
    )


def add_feed_item(tournament_id, title, detail=None, *, category="Info", related_match_id=None, public=True):
    return run(
        """INSERT INTO cup_feed(tournament_id,created_at,category,title,detail,public,related_match_id)
           VALUES(?,?,?,?,?,?,?)""",
        (tournament_id, datetime.now().isoformat(timespec="seconds"), category, title, detail,
         1 if public else 0, related_match_id),
    )


def _notification_public_url(tournament_id, token, action="confirm"):
    base = public_cup_url(tournament_id)
    separator = "&" if "?" in base else "?"
    key = "notify_confirm" if action == "confirm" else "notify_unsubscribe"
    return f"{base}{separator}{key}={quote(str(token))}"

def create_notification_subscription(tournament_id, team_id, email, *,
                                     notify_schedule=True, notify_results=True, notify_messages=True):
    email = normalize_email(email)
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise ValueError("Ange en giltig e-postadress.")
    verify_token, unsubscribe_token = new_token(), new_token()
    created = now_iso()
    with db() as con:
        con.execute(
            """INSERT INTO notification_subscriptions(
                 tournament_id,team_id,email,verification_token_hash,unsubscribe_token_hash,created_at,
                 verified_at,disabled_at,notify_schedule,notify_results,notify_messages)
               VALUES(?,?,?,?,?,?,NULL,NULL,?,?,?)
               ON CONFLICT(tournament_id,team_id,email) DO UPDATE SET
                 verification_token_hash=excluded.verification_token_hash,
                 unsubscribe_token_hash=excluded.unsubscribe_token_hash,
                 created_at=excluded.created_at,verified_at=NULL,disabled_at=NULL,
                 notify_schedule=excluded.notify_schedule,notify_results=excluded.notify_results,
                 notify_messages=excluded.notify_messages""",
            (int(tournament_id), int(team_id), email, token_hash(verify_token), token_hash(unsubscribe_token), created,
             1 if notify_schedule else 0, 1 if notify_results else 0, 1 if notify_messages else 0),
        )
        con.commit()
    _clear_render_query_cache()
    confirm_url = _notification_public_url(tournament_id, verify_token, "confirm")
    return send_notification_email(
        email,
        "Bekräfta CupNavi-notiser",
        "Du har valt att följa ett lag i CupNavi.\n\n"
        f"Bekräfta prenumerationen här:\n{confirm_url}\n\n"
        "Om du inte gjorde detta kan du ignorera mejlet.",
    )

def confirm_notification_subscription(token):
    hashed = token_hash(token)
    with db() as con:
        cur = con.execute(
            """UPDATE notification_subscriptions SET verified_at=?,disabled_at=NULL
               WHERE verification_token_hash=? AND disabled_at IS NULL""",
            (now_iso(), hashed),
        )
        con.commit()
        changed = cur.rowcount
    _clear_render_query_cache()
    return bool(changed)

def unsubscribe_notification_subscription(token):
    hashed = token_hash(token)
    with db() as con:
        cur = con.execute(
            "UPDATE notification_subscriptions SET disabled_at=? WHERE unsubscribe_token_hash=? AND disabled_at IS NULL",
            (now_iso(), hashed),
        )
        con.commit()
        changed = cur.rowcount
    _clear_render_query_cache()
    return bool(changed)

def _deliver_team_notification_emails(tournament_id, team_id, notification_id, title, message):
    category = classify_notification(title)
    subscriptions = all_rows(
        """SELECT * FROM notification_subscriptions
           WHERE tournament_id=? AND team_id=? AND verified_at IS NOT NULL AND disabled_at IS NULL""",
        (int(tournament_id), int(team_id)),
    )
    for sub in subscriptions:
        if not category_enabled(sub, category):
            continue
        unsubscribe_token = new_token()
        with db() as con:
            con.execute(
                "UPDATE notification_subscriptions SET unsubscribe_token_hash=? WHERE id=?",
                (token_hash(unsubscribe_token), sub["id"]),
            )
            con.commit()
        unsubscribe_url = _notification_public_url(tournament_id, unsubscribe_token, "unsubscribe")
        body = f"{message}\n\nÖppna cupen: {public_cup_url(tournament_id)}\n\nAvsluta notiser: {unsubscribe_url}"
        ok, error = send_notification_email(sub["email"], f"CupNavi · {title}", body)
        run(
            """INSERT OR IGNORE INTO notification_deliveries(
                 subscription_id,notification_id,created_at,category,subject,body,status,attempted_at,error)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (sub["id"], notification_id, now_iso(), category, title, body,
             "sent" if ok else "failed", now_iso(), error),
        )

def add_team_notification(tournament_id, team_id, title, message, event_key=None):
    """Spara notisen först; e-post till verifierade följare därefter."""
    try:
        notification_id = run(
            """INSERT INTO notifications(tournament_id,team_id,created_at,title,message,event_key)
               VALUES(?,?,?,?,?,?)""",
            (tournament_id, team_id, datetime.now().isoformat(timespec="seconds"), title, message, event_key),
        )
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            return None
        raise
    try:
        _deliver_team_notification_emails(tournament_id, team_id, notification_id, title, message)
    except Exception as exc:
        print(f"[notification-email] {type(exc).__name__}: {exc}")
    return notification_id


def _match_team_ids(match_row):
    ids = []
    for source in (match_row["home_source"], match_row["away_source"]):
        resolved = resolve_source(source)
        if resolved:
            ids.append(int(resolved))
    return ids


def schedule_repository():
    """Repository-gräns för all SQL som hör till schemadomänen."""
    return ScheduleRepository(
        fetch_all=all_rows,
        connection_factory=db,
        clear_cache=_clear_render_query_cache,
    )


class TeamLimitReachedError(Exception):
    pass


def insert_team_with_limit(tournament_id, name, primary_color, secondary_color,
                           home_pattern, home_color_2, away_pattern, away_color_2,
                           distance_km, late_first_match, earliest_first_time, travel_note, avoid_late_group_match=False):
    """Lägg till ett lag atomiskt och respektera alltid turneringens sparade maxantal."""
    con = db()
    try:
        # Lokalt låser BEGIN IMMEDIATE bort samtidiga SQLite-skrivningar.
        # I Turso är triggern den slutliga atomiska spärren på serversidan.
        if not CLOUD_DATABASE_ENABLED:
            con.execute("BEGIN IMMEDIATE")
        tournament_row = _one_from_cursor(con.execute(
            "SELECT COALESCE(expected_team_count, 0) AS max_teams FROM tournaments WHERE id=?",
            (tournament_id,),
        ))
        if tournament_row is None:
            raise ValueError("Turneringen finns inte längre.")
        max_teams = int(tournament_row["max_teams"] or 0)
        current_count_row = _one_from_cursor(con.execute(
            "SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tournament_id,)
        ))
        current_count = int(current_count_row["n"])
        if max_teams > 0 and current_count >= max_teams:
            raise TeamLimitReachedError(max_teams)
        cur = con.execute(
            """INSERT INTO teams(
                tournament_id,name,group_id,primary_color,secondary_color,
                home_pattern,home_color_2,away_pattern,away_color_2,
                distance_km,late_first_match,earliest_first_time,travel_note,avoid_late_group_match
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tournament_id, name, None, primary_color, secondary_color,
             home_pattern, home_color_2, away_pattern, away_color_2,
             distance_km, int(late_first_match), earliest_first_time, travel_note, int(bool(avoid_late_group_match))),
        )
        con.commit()
        return cur.lastrowid
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def team(team_id):
    return one_row("SELECT * FROM teams WHERE id=?", (team_id,)) if team_id else None


def calculate_table(group_id, tournament):
    table_key = (
        "group-table", int(group_id),
        int(tournament["points_win"] or 0),
        int(tournament["points_draw"] or 0),
        int(tournament["points_loss"] or 0),
        str(_row_value(tournament, "table_tiebreak", "Målskillnad först") or "Målskillnad först"),
    )
    if table_key in _DERIVED_RENDER_CACHE:
        _PERF["derived_hits"] += 1
        return _DERIVED_RENDER_CACHE[table_key]

    teams = [dict(row) for row in all_rows("SELECT * FROM teams WHERE group_id=? ORDER BY name", (group_id,))]
    matches = [dict(row) for row in all_rows(
        "SELECT * FROM matches WHERE group_id=? AND stage='Gruppspel' AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (group_id,),
    )]
    rows = calculate_group_table(
        teams, matches,
        points_win=int(tournament["points_win"] or 0),
        points_draw=int(tournament["points_draw"] or 0),
        points_loss=int(tournament["points_loss"] or 0),
        table_tiebreak=str(_row_value(tournament, "table_tiebreak", "Målskillnad först") or "Målskillnad först"),
    )
    result = [(row["team_id"], {key:value for key,value in row.items() if key not in {"team_id","position"}}) for row in rows]
    _DERIVED_RENDER_CACHE[table_key] = result
    return result

def calculate_all_group_tables(tournament_id, tournament):
    """Beräkna samtliga grupptabeller med tre queries i stället för 2×N queries."""
    cache_key = (
        "all-group-tables",
        int(tournament_id),
        int(tournament["points_win"] or 0),
        int(tournament["points_draw"] or 0),
        int(tournament["points_loss"] or 0),
        str(_row_value(tournament, "table_tiebreak", "Målskillnad först") or "Målskillnad först"),
    )
    if cache_key in _DERIVED_RENDER_CACHE:
        _PERF["derived_hits"] += 1
        return _DERIVED_RENDER_CACHE[cache_key]

    groups = [dict(row) for row in all_rows(
        "SELECT * FROM groups WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )]
    teams = [dict(row) for row in all_rows(
        "SELECT * FROM teams WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )]
    matches = [dict(row) for row in all_rows(
        """SELECT * FROM matches
           WHERE tournament_id=? AND stage='Gruppspel'
             AND home_score IS NOT NULL AND away_score IS NOT NULL""",
        (int(tournament_id),),
    )]
    teams_by_group = {}
    for row in teams:
        teams_by_group.setdefault(row.get("group_id"), []).append(row)
    matches_by_group = {}
    for row in matches:
        matches_by_group.setdefault(row.get("group_id"), []).append(row)

    result = {}
    for group in groups:
        group_id = int(group["id"])
        rows = calculate_group_table(
            teams_by_group.get(group_id, []),
            matches_by_group.get(group_id, []),
            points_win=int(tournament["points_win"] or 0),
            points_draw=int(tournament["points_draw"] or 0),
            points_loss=int(tournament["points_loss"] or 0),
            table_tiebreak=str(_row_value(tournament, "table_tiebreak", "Målskillnad först") or "Målskillnad först"),
        )
        normalized = [
            (row["team_id"], {key: value for key, value in row.items() if key not in {"team_id", "position"}})
            for row in rows
        ]
        result[group_id] = normalized
        _DERIVED_RENDER_CACHE[(
            "group-table", group_id,
            int(tournament["points_win"] or 0),
            int(tournament["points_draw"] or 0),
            int(tournament["points_loss"] or 0),
            str(_row_value(tournament, "table_tiebreak", "Målskillnad först") or "Målskillnad först"),
        )] = normalized
    _DERIVED_RENDER_CACHE[cache_key] = {"groups": groups, "tables": result}
    return _DERIVED_RENDER_CACHE[cache_key]


def final_ranking_rows(tournament_id, tournament):
    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,))
    if not teams:
        return []
    team_by_id = {int(row["id"]): row for row in teams}
    group_metrics = {}
    _all_tables = calculate_all_group_tables(tournament_id, tournament)
    for group in _all_tables["groups"]:
        for pos, (team_id, stats) in enumerate(_all_tables["tables"].get(int(group["id"]), []), 1):
            group_metrics[int(team_id)] = {
                "pos": pos,
                "P": int(stats["P"] or 0),
                "MS": int(stats["MS"] or 0),
                "GM": int(stats["GM"] or 0),
            }
    depth = {team_id: 0 for team_id in team_by_id}
    stage_depth = {"Kvartsfinal": 1, "Semifinal": 2, "Bronsmatch": 3, "Final": 4}
    playoff = all_rows("SELECT * FROM matches WHERE tournament_id=? AND stage<>'Gruppspel' ORDER BY round_no,match_no,id", (tournament_id,))
    for match_row in playoff:
        for source in (match_row["home_source"], match_row["away_source"]):
            resolved = resolve_source(source)
            if resolved and int(resolved) in depth:
                depth[int(resolved)] = max(depth[int(resolved)], stage_depth.get(match_row["stage"], int(match_row["round_no"] or 0)))
    pinned = []
    for stage in ("Final", "Bronsmatch"):
        completed = [m for m in playoff if m["stage"] == stage and m["home_score"] is not None and m["away_score"] is not None]
        if not completed:
            continue
        m = completed[-1]
        h, a = resolve_source(m["home_source"]), resolve_source(m["away_source"])
        if not h or not a:
            continue
        winner = int(m["decided_winner_id"] or 0)
        if not winner:
            hs, aas = int(m["home_score"]), int(m["away_score"])
            if hs == aas and m["home_penalties"] is not None and m["away_penalties"] is not None:
                winner = int(h if int(m["home_penalties"]) > int(m["away_penalties"]) else a)
            else:
                winner = int(h if hs > aas else a)
        loser = int(a if winner == int(h) else h)
        for team_id in (winner, loser):
            if team_id in team_by_id and team_id not in pinned:
                pinned.append(team_id)
    remaining = [team_id for team_id in team_by_id if team_id not in pinned]
    remaining.sort(key=lambda team_id: (-depth.get(team_id,0), group_metrics.get(team_id,{}).get("pos",999), -group_metrics.get(team_id,{}).get("P",0), -group_metrics.get(team_id,{}).get("MS",0), -group_metrics.get(team_id,{}).get("GM",0), str(team_by_id[team_id]["name"]).casefold()))
    class_map = {row["id"]: row["name"] for row in competition_classes(tournament_id)}
    return [{"Placering": i, "Lag": team_by_id[team_id]["name"], "Tävlingsklass": class_map.get(_row_value(team_by_id[team_id], "competition_class_id", None), "–")} for i, team_id in enumerate(pinned + remaining, 1)]


def result_winner(match_row, want_loser=False):
    home_id = resolve_source(match_row["home_source"])
    away_id = resolve_source(match_row["away_source"])
    if not home_id or not away_id or match_row["home_score"] is None or match_row["away_score"] is None:
        return None
    hs, aas = match_row["home_score"], match_row["away_score"]
    if hs == aas:
        decided = match_row["decided_winner_id"] if "decided_winner_id" in match_row else None
        if decided in (home_id, away_id):
            winner = decided
            loser = away_id if winner == home_id else home_id
        else:
            hp, ap = match_row["home_penalties"], match_row["away_penalties"]
            if hp is None or ap is None or hp == ap:
                return None
            winner, loser = (home_id, away_id) if hp > ap else (away_id, home_id)
    else:
        winner, loser = (home_id, away_id) if hs > aas else (away_id, home_id)
    return loser if want_loser else winner


def group_table_is_final(group_id):
    """En gruppplacering får inte lösas till ett lag förrän hela gruppspelet är klart."""
    team_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group_id,))["n"]
    expected_matches = team_count * (team_count - 1) // 2
    if expected_matches == 0:
        return False
    completed_matches = one_row(
        """SELECT COUNT(*) AS n FROM matches
        WHERE group_id=? AND stage='Gruppspel' AND home_score IS NOT NULL AND away_score IS NOT NULL""",
        (group_id,),
    )["n"]
    return completed_matches >= expected_matches


def resolve_source(source):
    if not source:
        return None
    cache_key=("resolved-source", str(source))
    if cache_key in _DERIVED_RENDER_CACHE:
        _PERF["derived_hits"] += 1
        return _DERIVED_RENDER_CACHE[cache_key]

    parts = source.split(":")
    result = None
    if parts[0] == "team":
        result = int(parts[1])
    elif parts[0] == "group":
        group_id, rank = int(parts[1]), int(parts[2])
        if group_table_is_final(group_id):
            tournament_id = one_row("SELECT tournament_id FROM groups WHERE id=?", (group_id,))["tournament_id"]
            tournament = one_row("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
            table = calculate_table(group_id, tournament)
            result = table[rank - 1][0] if 0 < rank <= len(table) else None
    elif parts[0] in ("winner", "loser"):
        match_row = one_row("SELECT * FROM matches WHERE id=?", (int(parts[1]),))
        result = result_winner(match_row, want_loser=parts[0] == "loser") if match_row else None

    _DERIVED_RENDER_CACHE[cache_key] = result
    return result

def _source_label_uncached(source):
    team_id = resolve_source(source)
    if team_id:
        selected = team(team_id)
        return selected["name"] if selected else "Okänt lag"
    parts = source.split(":") if source else []
    if parts and parts[0] == "group":
        group = one_row("SELECT name FROM groups WHERE id=?", (int(parts[1]),))
        if not group:
            return "Gruppplacering"
        rank = int(parts[2])
        return f"Vinnaren i {group['name']}" if rank == 1 else f"{rank}:an i {group['name']}"
    if parts and parts[0] == "winner":
        source_match = one_row("SELECT * FROM matches WHERE id=?", (int(parts[1]),))
        if source_match:
            schedule_text, _ = match_meta(source_match)
            match_name = schedule_text.split(" · ", 1)[0]
            return f"Vinnare {match_name.lower()}"
        return "Vinnare i match"
    if parts and parts[0] == "loser":
        source_match = one_row("SELECT * FROM matches WHERE id=?", (int(parts[1]),))
        if source_match:
            schedule_text, _ = match_meta(source_match)
            match_name = schedule_text.split(" · ", 1)[0]
            return f"Förlorare {match_name.lower()}"
        return "Förlorare i match"
    return "Ej klart"



def source_label(source):
    cache_key=("source-label", str(source or ""))
    if cache_key in _DERIVED_RENDER_CACHE:
        _PERF["derived_hits"] += 1
        return _DERIVED_RENDER_CACHE[cache_key]
    value=_source_label_uncached(source)
    _DERIVED_RENDER_CACHE[cache_key]=value
    return value

def match_number_map(tournament_id):
    key=("match-number-map", int(tournament_id))
    def build():
        ordered = all_rows(
            "SELECT id FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
            (int(tournament_id),),
        )
        return {int(row["id"]): index for index, row in enumerate(ordered, 1)}
    return _derived_cache_get(key, build)

def referee_name_map(tournament_id):
    key=("referee-name-map", int(tournament_id))
    return _derived_cache_get(
        key,
        lambda: {
            int(row["id"]): row["name"]
            for row in all_rows("SELECT id,name FROM referees WHERE tournament_id=? ORDER BY id", (int(tournament_id),))
        },
    )

def match_meta(match_row):
    match_number = match_number_map(match_row["tournament_id"]).get(int(match_row["id"]))
    referee = None
    if match_row["referee_id"]:
        referee_name = referee_name_map(match_row["tournament_id"]).get(int(match_row["referee_id"]))
        referee = {"name": referee_name} if referee_name else None
    if match_row["scheduled_start"]:
        start = swedish_datetime(match_row["scheduled_start"])
        schedule_text = f"Match {match_number} · {start} · {pitch_label(match_row['tournament_id'],match_row['pitch_number'])}"
    else:
        schedule_text = "Ej schemalagd"
    return schedule_text, referee["name"] if referee else "Ej tillsatt"


def match_result_label(match_row):
    schedule_text, referee = match_meta(match_row)
    return (
        f"{schedule_text} · {match_row['stage']}: "
        f"{source_label(match_row['home_source'])} {match_row['home_score']}–{match_row['away_score']} "
        f"{source_label(match_row['away_source'])} · Domare: {referee}"
    )


SWEDISH_WEEKDAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
SWEDISH_MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]


def swedish_datetime(value):
    moment = datetime.fromisoformat(value) if isinstance(value, str) else value
    return f"{SWEDISH_WEEKDAYS[moment.weekday()]} {moment.day} {SWEDISH_MONTHS[moment.month - 1]} {moment.year} · {moment.strftime('%H:%M')}"


def cup_date_label(tournament):
    start_text = tournament["start_date"] or tournament["tournament_date"]
    end_text = tournament["end_date"] or start_text
    if not start_text:
        return "Cupdatum saknas"
    start = datetime.fromisoformat(start_text)
    end = datetime.fromisoformat(end_text)
    if start.date() == end.date():
        return f"{SWEDISH_WEEKDAYS[start.weekday()]} {start.day} {SWEDISH_MONTHS[start.month - 1]} {start.year}"
    return f"{start.day} {SWEDISH_MONTHS[start.month - 1]} {start.year}–{end.day} {SWEDISH_MONTHS[end.month - 1]} {end.year}"


WEATHER_CODES = {
    0: ("☀️", "Klart"), 1: ("🌤️", "Mestadels klart"), 2: ("⛅", "Växlande molnighet"),
    3: ("☁️", "Mulet"), 45: ("🌫️", "Dimma"), 48: ("🌫️", "Rimfrost och dimma"),
    51: ("🌦️", "Lätt duggregn"), 53: ("🌦️", "Duggregn"), 55: ("🌧️", "Kraftigt duggregn"),
    56: ("🌧️", "Underkylt duggregn"), 57: ("🌧️", "Kraftigt underkylt duggregn"),
    61: ("🌦️", "Lätt regn"), 63: ("🌧️", "Regn"), 65: ("🌧️", "Kraftigt regn"),
    66: ("🌧️", "Underkylt regn"), 67: ("🌧️", "Kraftigt underkylt regn"),
    71: ("🌨️", "Lätt snöfall"), 73: ("🌨️", "Snöfall"), 75: ("❄️", "Kraftigt snöfall"),
    77: ("🌨️", "Snökorn"), 80: ("🌦️", "Lätta regnskurar"), 81: ("🌧️", "Regnskurar"),
    82: ("⛈️", "Kraftiga regnskurar"), 85: ("🌨️", "Lätta snöbyar"), 86: ("❄️", "Kraftiga snöbyar"),
    95: ("⛈️", "Åska"), 96: ("⛈️", "Åska med lätt hagel"), 99: ("⛈️", "Åska med kraftigt hagel"),
}


@st.cache_data(ttl=86400, show_spinner=False)
def _weather_geocode(place):
    """Geokodning ändras sällan; håll den separat från den kortare prognoscachen."""
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode({
        "name": place.strip(), "count": 1, "language": "sv", "format": "json",
    })
    request = Request(geocode_url, headers={"User-Agent": "CupNavi/1.0"})
    with urlopen(request, timeout=4) as response:
        geocode = json.load(response)
    results = geocode.get("results") or []
    return results[0] if results else None


@st.cache_data(ttl=1800, refresh_mode="background", show_spinner=False)
def fetch_weather_forecast(place):
    """Hämta timprognos; utgången cache uppdateras i bakgrunden utan att blockera sidan."""
    if not place or not place.strip():
        return {}, "Spelort saknas"
    try:
        location = _weather_geocode(place)
        if not location:
            return {}, f"Kunde inte hitta spelorten {place}."
        forecast_url = "https://api.open-meteo.com/v1/forecast?" + urlencode({
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "hourly": "temperature_2m,precipitation_probability,weather_code,wind_speed_10m",
            "forecast_days": 16,
            "timezone": "auto",
        })
        request = Request(forecast_url, headers={"User-Agent": "Fotbollsturnering/1.0"})
        with urlopen(request, timeout=8) as response:
            forecast = json.load(response)
        hourly = forecast.get("hourly") or {}
        times = hourly.get("time") or []
        values = {}
        for index, time_value in enumerate(times):
            values[time_value] = {
                "temperature": hourly.get("temperature_2m", [None] * len(times))[index],
                "rain_probability": hourly.get("precipitation_probability", [None] * len(times))[index],
                "weather_code": hourly.get("weather_code", [None] * len(times))[index],
                "wind_speed": hourly.get("wind_speed_10m", [None] * len(times))[index],
            }
        resolved_place = location.get("name", place)
        return {"place": resolved_place, "hours": values}, ""
    except Exception:
        return {}, "Väderprognosen kan inte hämtas just nu."


def weather_for_match(forecast, scheduled_start):
    """Returnera prognos för matchen utan att publikvyn kan krascha på gammal/ofullständig data."""
    if not forecast or not scheduled_start:
        return None
    try:
        moment = datetime.fromisoformat(str(scheduled_start))
    except (TypeError, ValueError):
        return None
    forecast_hour = moment.replace(minute=0, second=0, microsecond=0)
    if moment.minute >= 30:
        forecast_hour += timedelta(hours=1)
    return forecast.get("hours", {}).get(forecast_hour.strftime("%Y-%m-%dT%H:%M"))


def weather_label(weather):
    if not weather:
        return "Prognos tillgänglig närmare matchdagen"
    icon, description = WEATHER_CODES.get(weather.get("weather_code"), ("🌡️", "Väder"))
    temperature = "–" if weather.get("temperature") is None else f"{round(weather['temperature'])} °C"
    rain = "–" if weather.get("rain_probability") is None else f"{round(weather['rain_probability'])} % regnrisk"
    wind = "–" if weather.get("wind_speed") is None else f"{round(weather['wind_speed'])} km/h vind"
    return f"{icon} {description} · {temperature} · {rain} · {wind}"


def _row_value(row, key, default=None):
    """Läs ett fält säkert från sqlite/libsql-rader, dictar och äldre schema."""
    if not row:
        return default
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        value = default
    except Exception:
        value = default
    return default if value is None else value


def _team_value(team_row, key, default=None):
    """Bakåtkompatibel wrapper för lagrader."""
    return _row_value(team_row, key, default)


def is_test_environment(tournament_row):
    return str(_row_value(tournament_row, "environment_type", "production") or "production") == "test"


def played_match_count(tournament_id):
    row = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (int(tournament_id),),
    )
    return int(_row_value(row, "n", 0) or 0)


def production_history_locked(tournament_id, tournament_row):
    """Historikskydd gäller först när en riktig cup har minst ett registrerat resultat."""
    return (not is_test_environment(tournament_row)) and played_match_count(tournament_id) > 0


def team_has_played_result(tournament_id, team_id):
    token = f"team:{int(team_id)}"
    row = one_row(
        """SELECT COUNT(*) AS n FROM matches
           WHERE tournament_id=? AND (home_source=? OR away_source=?)
             AND home_score IS NOT NULL AND away_score IS NOT NULL""",
        (int(tournament_id), token, token),
    )
    return int(_row_value(row, "n", 0) or 0) > 0


KIT_PATTERNS = ["Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad"]


def kit_colors(team_row, kit="home"):
    """Returnera de färger som faktiskt syns i ett hemma- eller bortaställ."""
    if not team_row:
        return ["#9CA3AF"]
    if kit == "away":
        pattern = _team_value(team_row, "away_pattern", "Helfärgad")
        color_1 = _team_value(team_row, "secondary_color", "#FFFFFF")
        color_2 = _team_value(team_row, "away_color_2", "#111827")
    else:
        pattern = _team_value(team_row, "home_pattern", "Helfärgad")
        color_1 = _team_value(team_row, "primary_color", "#111827")
        color_2 = _team_value(team_row, "home_color_2", "#FFFFFF")
    return [color_1] if pattern == "Helfärgad" else [color_1, color_2]


def kit_pattern(team_row, kit="home"):
    if kit == "away":
        return _team_value(team_row, "away_pattern", "Helfärgad")
    return _team_value(team_row, "home_pattern", "Helfärgad")


def kit_background(pattern, color_1, color_2):
    """CSS-bakgrund som visuellt återger valt tröjmönster."""
    if pattern == "Vertikala ränder":
        return f"repeating-linear-gradient(90deg,{color_1} 0 8px,{color_2} 8px 16px)"
    if pattern == "Horisontella ränder":
        return f"repeating-linear-gradient(0deg,{color_1} 0 7px,{color_2} 7px 14px)"
    if pattern == "Rutigt":
        return f"conic-gradient({color_1} 25%,{color_2} 0 50%,{color_1} 0 75%,{color_2} 0) 0 0/16px 16px"
    if pattern == "Delad":
        return f"linear-gradient(90deg,{color_1} 0 50%,{color_2} 50% 100%)"
    return color_1


def kit_background_for_team(team_row, kit="home"):
    colors = kit_colors(team_row, kit)
    color_1 = colors[0]
    color_2 = colors[1] if len(colors) > 1 else color_1
    return kit_background(kit_pattern(team_row, kit), color_1, color_2)


def kit_preview_html(pattern, color_1, color_2, title):
    bg = kit_background(pattern, color_1, color_2)
    return (
        f"<div style='display:flex;align-items:center;gap:10px;margin:4px 0 10px'>"
        f"<span style='width:58px;height:32px;border:1px solid #64748b;border-radius:7px;background:{bg};display:inline-block'></span>"
        f"<span style='color:#334155;font-size:13px'><b>{html.escape(title)}</b><br>{html.escape(pattern)}</span></div>"
    )


def kit_swatch(team_row, kit="home"):
    """SVG-ruta för Streamlit-tabeller som kan visa två färger och mönster."""
    colors = kit_colors(team_row, kit)
    c1 = colors[0]
    c2 = colors[1] if len(colors) > 1 else c1
    pattern = kit_pattern(team_row, kit)
    defs = ""
    fill = c1
    if pattern == "Vertikala ränder":
        defs = f"<pattern id='p' width='12' height='24' patternUnits='userSpaceOnUse'><rect width='6' height='24' fill='{c1}'/><rect x='6' width='6' height='24' fill='{c2}'/></pattern>"
        fill = "url(#p)"
    elif pattern == "Horisontella ränder":
        defs = f"<pattern id='p' width='58' height='12' patternUnits='userSpaceOnUse'><rect width='58' height='6' fill='{c1}'/><rect y='6' width='58' height='6' fill='{c2}'/></pattern>"
        fill = "url(#p)"
    elif pattern == "Rutigt":
        defs = f"<pattern id='p' width='12' height='12' patternUnits='userSpaceOnUse'><rect width='12' height='12' fill='{c1}'/><rect width='6' height='6' fill='{c2}'/><rect x='6' y='6' width='6' height='6' fill='{c2}'/></pattern>"
        fill = "url(#p)"
    elif pattern == "Delad":
        defs = f"<linearGradient id='p' x1='0' x2='1'><stop offset='50%' stop-color='{c1}'/><stop offset='50%' stop-color='{c2}'/></linearGradient>"
        fill = "url(#p)"
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='58' height='24' viewBox='0 0 58 24'><defs>{defs}</defs><rect x='1' y='1' width='56' height='22' rx='4' fill='{fill}' stroke='#475569'/></svg>"
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _hex_rgb(value):
    value = (value or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return None
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def colors_similar(color_a, color_b, threshold=72):
    """Praktisk färgkrock: fånga även tydligt närliggande nyanser, inte bara identiska hexvärden."""
    a, b = _hex_rgb(color_a), _hex_rgb(color_b)
    if not a or not b:
        return str(color_a).casefold() == str(color_b).casefold()
    distance = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
    return distance <= threshold


def kits_conflict(team_a, kit_a, team_b, kit_b):
    return any(colors_similar(a, b) for a in kit_colors(team_a, kit_a) for b in kit_colors(team_b, kit_b))


def match_kit_colors(home_team, away_team):
    """Behåll kompatibel returtyp men välj bortaställ utifrån alla synliga färger."""
    if not home_team or not away_team:
        return "#9CA3AF", "#FFFFFF", False
    use_away_kit = kits_conflict(home_team, "home", away_team, "home")
    home_color = kit_colors(home_team, "home")[0]
    away_color = kit_colors(away_team, "away" if use_away_kit else "home")[0]
    return home_color, away_color, use_away_kit


def kit_color_conflict(home_team, away_team):
    """Kontrollera om bortalagets valda ställ fortfarande krockar med hemmastället."""
    if not home_team or not away_team:
        return False
    use_away_kit = kits_conflict(home_team, "home", away_team, "home")
    selected_away_kit = "away" if use_away_kit else "home"
    return kits_conflict(home_team, "home", away_team, selected_away_kit)


def optimize_group_home_away(tournament_id):
    """
    Optimera hemma/borta i gruppspelet.

    Prioritet 1: välj den riktning som undviker färgkrock när endast en riktning gör det.
    Prioritet 2: bland färgmässigt likvärdiga riktningar, jämna ut hemma/borta per lag.
    Matcher med registrerat resultat lämnas helt orörda men räknas in i balansen.
    """
    teams = {
        row["id"]: row
        for row in all_rows(
            "SELECT * FROM teams WHERE tournament_id=?",
            (tournament_id,),
        )
    }
    groups = all_rows(
        "SELECT id FROM groups WHERE tournament_id=? ORDER BY name,id",
        (tournament_id,),
    )
    changed = 0

    for group in groups:
        matches = all_rows(
            """SELECT * FROM matches
               WHERE group_id=? AND stage='Gruppspel'
               ORDER BY match_no,id""",
            (group["id"],),
        )
        if not matches:
            continue

        home_counts = {}
        away_counts = {}
        editable = []

        # Spelade matcher är låsta, men deras hemma/borta-fördelning påverkar fortsatt balans.
        for match_row in matches:
            try:
                home_id = int(match_row["home_source"].split(":")[1])
                away_id = int(match_row["away_source"].split(":")[1])
            except (AttributeError, IndexError, ValueError):
                continue

            if match_row["home_score"] is not None or match_row["away_score"] is not None:
                home_counts[home_id] = home_counts.get(home_id, 0) + 1
                away_counts[away_id] = away_counts.get(away_id, 0) + 1
            else:
                editable.append((match_row, home_id, away_id))

        forced = []
        flexible = []

        # Färg bedöms i båda riktningarna. Om bara en riktning krockar är valet tvingande.
        for match_row, team_a_id, team_b_id in editable:
            team_a = teams.get(team_a_id)
            team_b = teams.get(team_b_id)
            if not team_a or not team_b:
                flexible.append((match_row, team_a_id, team_b_id))
                continue

            conflict_a_home = kit_color_conflict(team_a, team_b)
            conflict_b_home = kit_color_conflict(team_b, team_a)

            if conflict_a_home != conflict_b_home:
                if not conflict_a_home:
                    forced.append((match_row, team_a_id, team_b_id))
                else:
                    forced.append((match_row, team_b_id, team_a_id))
            else:
                # Båda riktningar är lika bra färgmässigt: använd dem för balans.
                flexible.append((match_row, team_a_id, team_b_id))

        orientations = {}

        # Tvingade färgval går först eftersom färgkrockar har högre prioritet.
        for match_row, home_id, away_id in forced:
            orientations[match_row["id"]] = [home_id, away_id, False]
            home_counts[home_id] = home_counts.get(home_id, 0) + 1
            away_counts[away_id] = away_counts.get(away_id, 0) + 1

        # Därefter balanseras matcher där båda riktningarna är färgmässigt likvärdiga.
        for match_row, team_a_id, team_b_id in flexible:
            score_ab = orientation_balance_score(
                team_a_id, team_b_id, home_counts, away_counts
            )
            score_ba = orientation_balance_score(
                team_b_id, team_a_id, home_counts, away_counts
            )

            if score_ab < score_ba:
                home_id, away_id = team_a_id, team_b_id
            elif score_ba < score_ab:
                home_id, away_id = team_b_id, team_a_id
            else:
                # Stabil tie-break: laget med färre hemmamatcher får hemma.
                a_home = home_counts.get(team_a_id, 0)
                b_home = home_counts.get(team_b_id, 0)
                if a_home < b_home:
                    home_id, away_id = team_a_id, team_b_id
                elif b_home < a_home:
                    home_id, away_id = team_b_id, team_a_id
                else:
                    # Alternera deterministiskt för att undvika ID-bias.
                    if int(match_row["match_no"] or match_row["id"]) % 2:
                        home_id, away_id = team_a_id, team_b_id
                    else:
                        home_id, away_id = team_b_id, team_a_id

            orientations[match_row["id"]] = [home_id, away_id, True]
            home_counts[home_id] = home_counts.get(home_id, 0) + 1
            away_counts[away_id] = away_counts.get(away_id, 0) + 1

        # Lokal förbättring: vänd endast flexibla matcher om den totala obalansen minskar.
        # Färgresultatet kan då inte försämras eftersom dessa matcher var färgmässigt likvärdiga.
        for _ in range(6):
            improved = False
            for match_id, orientation in orientations.items():
                home_id, away_id, is_flexible = orientation
                if not is_flexible:
                    continue

                before = (
                    abs(home_counts.get(home_id, 0) - away_counts.get(home_id, 0))
                    + abs(home_counts.get(away_id, 0) - away_counts.get(away_id, 0))
                )

                after_home_home = home_counts.get(home_id, 0) - 1
                after_home_away = away_counts.get(home_id, 0) + 1
                after_away_home = home_counts.get(away_id, 0) + 1
                after_away_away = away_counts.get(away_id, 0) - 1
                after = (
                    abs(after_home_home - after_home_away)
                    + abs(after_away_home - after_away_away)
                )

                if after < before:
                    home_counts[home_id] -= 1
                    away_counts[home_id] = away_counts.get(home_id, 0) + 1
                    home_counts[away_id] = home_counts.get(away_id, 0) + 1
                    away_counts[away_id] -= 1
                    orientation[0], orientation[1] = away_id, home_id
                    improved = True
            if not improved:
                break

        updates = []
        match_by_id = {m["id"]: m for m in matches}
        for match_id, (home_id, away_id, _is_flexible) in orientations.items():
            original = match_by_id[match_id]
            new_home = f"team:{home_id}"
            new_away = f"team:{away_id}"
            if original["home_source"] != new_home or original["away_source"] != new_away:
                updates.append((new_home, new_away, match_id))

        if updates:
            with db() as con:
                con.executemany(
                    "UPDATE matches SET home_source=?,away_source=? WHERE id=?",
                    updates,
                )
                con.commit()
            changed += len(updates)

    if changed:
        _clear_render_query_cache()
    return changed


def render_centered_table(dataframe, empty_text="Ingen data att visa."):
    """Rendera en responsiv HTML-tabell med centrerade rubriker och celler."""
    if dataframe is None or dataframe.empty:
        st.info(empty_text)
        return

    display_dataframe = _translate_dataframe_for_display(dataframe)
    table_html = display_dataframe.to_html(
        index=False,
        escape=True,
        classes="cup-centered-table",
        border=0,
    )

    html_block = f"""
<style>
.cup-table-scroll {{
    width:100%;
    overflow-x:auto;
    -webkit-overflow-scrolling:touch;
    border:1px solid #cbd5e1;
    border-radius:10px;
    background:#ffffff;
}}
.cup-centered-table {{
    width:100%;
    border-collapse:collapse;
    color:#0f172a;
    background:#ffffff;
}}
.cup-centered-table th,
.cup-centered-table td {{
    text-align:center !important;
    vertical-align:middle !important;
    padding:9px 10px;
    border-bottom:1px solid #e2e8f0;
    border-right:1px solid #e2e8f0;
    white-space:nowrap;
}}
.cup-centered-table th {{
    background:#f1f5f9;
    color:#0f172a;
    font-weight:800;
}}
.cup-centered-table tr:last-child td {{
    border-bottom:none;
}}
.cup-centered-table th:last-child,
.cup-centered-table td:last-child {{
    border-right:none;
}}
</style>
<div class="cup-table-scroll">{table_html}</div>
"""
    st.markdown(html_block, unsafe_allow_html=True)


def brackets_for_display(tournament_id):
    """Visa högst ett A- och ett B-slutspel utan N+1-frågor mot matchtabellen."""
    rows = all_rows("SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tournament_id,))
    stats_rows = all_rows(
        """SELECT bracket_id,
                  COUNT(*) AS total,
                  SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS completed
           FROM matches
           WHERE tournament_id=? AND bracket_id IS NOT NULL
           GROUP BY bracket_id""",
        (tournament_id,),
    )
    stats = {
        row["bracket_id"]: (int(row["completed"] or 0), int(row["total"] or 0))
        for row in stats_rows
    }
    regular = []
    selected = {}
    duplicates = []
    for bracket in rows:
        key = bracket["name"].strip().casefold()
        if key not in {"a-slutspel", "b-slutspel"}:
            regular.append(bracket)
            continue
        completed, total = stats.get(bracket["id"], (0, 0))
        candidate = (completed, total, bracket["id"], bracket)
        if key not in selected or candidate[:3] > selected[key][:3]:
            if key in selected:
                duplicates.append(selected[key][3])
            selected[key] = candidate
        else:
            duplicates.append(bracket)
    visible = regular + [value[3] for value in selected.values()]
    return sorted(visible, key=lambda bracket: bracket["id"]), duplicates


def create_all_group_matches(tournament_id):
    """Skapa alla saknade enkelmöten via schemadomänens repository."""
    repo = schedule_repository()
    groups, all_team_rows, all_existing_rows = repo.group_generation_data(tournament_id)

    teams_by_group = {}
    for row in all_team_rows:
        teams_by_group.setdefault(row["group_id"], []).append(row["id"])

    existing_by_group = {}
    for match_row in all_existing_rows:
        try:
            pair = tuple(sorted((
                int(match_row["home_source"].split(":")[1]),
                int(match_row["away_source"].split(":")[1]),
            )))
        except (ValueError, IndexError, AttributeError):
            continue
        existing_by_group.setdefault(match_row["group_id"], set()).add(pair)

    created = 0
    ready_groups = 0
    skipped_groups = []
    pending = []
    for group in groups:
        team_ids = teams_by_group.get(group["id"], [])
        if len(team_ids) < 2:
            skipped_groups.append(group["name"])
            continue
        ready_groups += 1
        existing = existing_by_group.get(group["id"], set())
        match_no = len(existing) + 1
        for i, home in enumerate(team_ids):
            for away in team_ids[i + 1:]:
                pair = tuple(sorted((home, away)))
                if pair in existing:
                    continue
                pending.append((tournament_id, group["id"], match_no, f"team:{home}", f"team:{away}"))
                existing.add(pair)
                created += 1
                match_no += 1

    if pending:
        repo.insert_group_matches(pending)

    # Optimera även befintliga ospelade gruppmatcher så att regenerering förbättrar
    # färgval och hemma/borta-fördelning, utan att röra spelade matcher.
    optimize_group_home_away(tournament_id)
    return created, ready_groups, skipped_groups


def create_bracket(tournament_id, name, size, bronze, first_sources):
    bracket_id = run("INSERT INTO brackets(tournament_id,name,size,bronze_match) VALUES(?,?,?,?)", (tournament_id, name, size, int(bronze)))
    first_stage = {2: "Final", 4: "Semifinal", 8: "Kvartsfinal"}[size]
    previous_ids = []
    for i in range(size // 2):
        mid = run(
            "INSERT INTO matches(tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source) VALUES(?,?,?,?,?,?,?)",
            (tournament_id, bracket_id, first_stage, 1, i + 1, first_sources[i * 2], first_sources[i * 2 + 1]),
        )
        previous_ids.append(mid)
    semifinal_ids = previous_ids if size == 4 else []
    round_no = 2
    while len(previous_ids) > 1:
        next_ids = []
        stage = "Final" if len(previous_ids) == 2 else "Semifinal"
        for i in range(0, len(previous_ids), 2):
            mid = run(
                "INSERT INTO matches(tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source) VALUES(?,?,?,?,?,?,?)",
                (tournament_id, bracket_id, stage, round_no, i // 2 + 1, f"winner:{previous_ids[i]}", f"winner:{previous_ids[i+1]}"),
            )
            next_ids.append(mid)
        if stage == "Semifinal":
            semifinal_ids = next_ids
        previous_ids = next_ids; round_no += 1
    if bronze and len(semifinal_ids) == 2:
        run(
            "INSERT INTO matches(tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source) VALUES(?,?,?,?,?,?,?)",
            (tournament_id, bracket_id, "Bronsmatch", round_no, 1, f"loser:{semifinal_ids[0]}", f"loser:{semifinal_ids[1]}"),
        )


PLACEMENT_PLAYOFF_FORMAT = "Placeringsslutspel – ettor mot ettor osv."


def placement_playoff_specs(tournament_id):
    """Bygg dynamiska placeringsslutspel för två, fyra eller åtta grupper."""
    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
    team_counts = {
        group["id"]: one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"]
        for group in groups
    }
    if len(groups) not in {2, 4, 8} or any(team_counts[group["id"]] < 2 for group in groups):
        return [], "Placeringsslutspel kräver två, fyra eller åtta grupper med minst två lag i varje grupp."
    max_rank = min(team_counts.values())
    rank_names = {1: "Ettornas slutspel", 2: "Tvåornas slutspel", 3: "Treornas slutspel", 4: "Fyrornas slutspel"}
    specs = []
    for rank in range(1, max_rank + 1):
        name = rank_names.get(rank, f"Placering {rank}-slutspel")
        specs.append((name, len(groups), [f"group:{group['id']}:{rank}" for group in groups]))
    return specs, ""


def playoff_specs_for_tournament(tournament_id, tournament):
    """Returnera önskat slutspel utifrån den modell som valts på Adminöversikten."""
    fmt = tournament["playoff_format"]
    if fmt == "Inget slutspel":
        return [], ""
    if fmt == "A- och B-slutspel":
        groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
        if len(groups) != 2:
            return [], "A- och B-slutspel kräver exakt två grupper."
        count_rows = all_rows(
            """SELECT group_id,COUNT(*) AS n FROM teams
               WHERE tournament_id=? AND group_id IS NOT NULL
               GROUP BY group_id""",
            (tournament_id,),
        )
        counts = {row["group_id"]: int(row["n"] or 0) for row in count_rows}
        if any(counts.get(group["id"], 0) < 4 for group in groups):
            return [], "A- och B-slutspel kräver minst fyra lag i vardera gruppen."
        group_a, group_b = groups
        return [
            ("A-slutspel", 4, [
                f"group:{group_a['id']}:1", f"group:{group_b['id']}:2",
                f"group:{group_b['id']}:1", f"group:{group_a['id']}:2",
            ]),
            ("B-slutspel", 4, [
                f"group:{group_a['id']}:3", f"group:{group_b['id']}:4",
                f"group:{group_b['id']}:3", f"group:{group_a['id']}:4",
            ]),
        ], ""
    if fmt == PLACEMENT_PLAYOFF_FORMAT:
        return placement_playoff_specs(tournament_id)
    return [], "Okänd slutspelsmodell."


def ensure_playoffs_for_schedule(tournament_id, tournament):
    """Skapa/uppdatera slutspel automatiskt när hela schemat genereras."""
    specs, error = playoff_specs_for_tournament(tournament_id, tournament)
    if error:
        return False, error

    existing = all_rows("SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tournament_id,))
    existing_signature = []
    for bracket in existing:
        first_round = all_rows(
            "SELECT home_source,away_source FROM matches WHERE bracket_id=? AND round_no=1 ORDER BY match_no",
            (bracket["id"],),
        )
        sources = [source for row in first_round for source in (row["home_source"], row["away_source"])]
        existing_signature.append((bracket["name"], int(bracket["size"]), sources))
    desired_signature = [(name, int(size), sources) for name, size, sources in specs]

    if existing_signature == desired_signature:
        return True, ""

    played = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL AND home_score IS NOT NULL",
        (tournament_id,),
    )["n"]
    if played:
        return False, "Slutspelsmodellen kan inte byggas om eftersom slutspelsresultat redan är registrerade."

    run("DELETE FROM brackets WHERE tournament_id=?", (tournament_id,))
    for bracket_name, bracket_size, bracket_sources in specs:
        create_bracket(
            tournament_id,
            bracket_name,
            bracket_size,
            bool(tournament["bronze_match"]) and bracket_size >= 4,
            bracket_sources,
        )
    return True, ""


def group_playoff_qualifiers(tournament_id, group_id):
    """Map group position -> playoff label from actual generated bracket sources."""
    rows = all_rows(
        """SELECT b.name,m.home_source,m.away_source
           FROM matches m
           LEFT JOIN brackets b ON b.id=m.bracket_id
           WHERE m.tournament_id=? AND m.stage<>'Gruppspel' AND m.bracket_id IS NOT NULL""",
        (int(tournament_id),),
    )
    mapping = {}
    prefix = f"group:{int(group_id)}:"
    for row in rows:
        bracket_name = str(_row_value(row, "name", "") or "").strip()
        for source in (_row_value(row, "home_source", ""), _row_value(row, "away_source", "")):
            source = str(source or "")
            if not source.startswith(prefix):
                continue
            try:
                rank = int(source.split(":")[-1])
            except (TypeError, ValueError):
                continue
            lower_name = bracket_name.lower()
            if lower_name.startswith("a-"):
                mapping[rank] = ("A", "qual-a")
            elif lower_name.startswith("b-"):
                mapping[rank] = ("B", "qual-b")
            elif "ettornas" in lower_name or "1:ornas" in lower_name or "1ornas" in lower_name:
                mapping[rank] = (bracket_name or "Ettornas slutspel", "qual-rank-1")
            elif "tvåornas" in lower_name or "2:ornas" in lower_name or "2ornas" in lower_name:
                mapping[rank] = (bracket_name or "Tvåornas slutspel", "qual-rank-2")
            elif "treornas" in lower_name or "3:ornas" in lower_name or "3ornas" in lower_name:
                mapping[rank] = (bracket_name or "Treornas slutspel", "qual-rank-3")
            elif "fyrornas" in lower_name or "4:ornas" in lower_name or "4ornas" in lower_name:
                mapping[rank] = (bracket_name or "Fyrornas slutspel", "qual-rank-4")
            else:
                mapping.setdefault(rank, (bracket_name or "Slutspel", "qual-playoff"))
    return mapping


def render_empty_state(title, description, *, symbol="•"):
    st.markdown(
        f"<div class='cn-empty-state' role='status'>"
        f"<div class='icon' aria-hidden='true'>{html.escape(symbol)}</div>"
        f"<div><b>{html.escape(str(title))}</b>"
        f"<p>{html.escape(str(description))}</p></div></div>",
        unsafe_allow_html=True,
    )


def render_group_table(table_rows, tournament, group_id=None):
    """Text-TV-inspirerad grupptabell med tydlig markering av slutspelsplatser."""
    if not table_rows:
        st.info("Ingen tabelldata att visa.")
        return
    rows_html = []
    fmt = tournament["playoff_format"]
    qualifier_map = group_playoff_qualifiers(tournament["id"], group_id) if group_id else {}
    for position, (_, data) in enumerate(table_rows, 1):
        qualifier = ""
        row_class = ""
        if position in qualifier_map:
            qualifier_label, row_class = qualifier_map[position]
            if qualifier_label == "A":
                css_class = "a"
            elif qualifier_label == "B":
                css_class = "b"
            elif row_class.startswith("qual-rank-"):
                css_class = row_class.replace("qual-", "")
            else:
                css_class = "playoff"
            qualifier = f"<span class='qualifier {css_class}'>{html.escape(str(qualifier_label))}</span>"
        elif fmt == "A- och B-slutspel":
            # Fallback before the bracket has been generated.
            if position <= 2:
                qualifier = "<span class='qualifier a'>A</span>"
                row_class = "qual-a"
            elif position <= 4:
                qualifier = "<span class='qualifier b'>B</span>"
                row_class = "qual-b"
        rows_html.append(
            f"<tr class='{row_class}'><td>{position}</td><td class='team'>{html.escape(str(data['Lag']))}</td>"
            f"<td>{data['S']}</td><td>{data['V']}</td><td>{data['O']}</td><td>{data['F']}</td>"
            f"<td>{data['GM']}</td><td>{data['IM']}</td><td>{data['MS']}</td><td><b>{data['P']}</b></td><td>{qualifier}</td></tr>"
        )
    legend = ""
    if fmt == "A- och B-slutspel":
        legend = "<div class='texttv-legend'><span><i class='a'></i>A-slutspel</span><span><i class='b'></i>B-slutspel</span></div>"
    st.markdown(
        f"""
        <style>
        .texttv-wrap{{overflow-x:auto;border:2px solid #172554;border-radius:8px;background:#07111f;padding:6px}}
        .texttv-table{{width:100%;border-collapse:collapse;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;color:#f8fafc}}
        .texttv-table th,.texttv-table td{{text-align:center!important;padding:8px 9px;border-bottom:1px solid #334155}}
        .texttv-table th{{background:#172554;color:#facc15;font-weight:900}}
        .texttv-table td.team{{text-align:left!important;font-weight:800}}
        .texttv-table tr.qual-a td{{background:#dcfce7!important;color:#14532d!important}}
        .texttv-table tr.qual-b td{{background:#dbeafe!important;color:#1e3a8a!important}}
        .texttv-table tr.qual-rank-1 td{{background:#dcfce7!important;color:#14532d!important}}
        .texttv-table tr.qual-rank-2 td{{background:#dbeafe!important;color:#1e3a8a!important}}
        .texttv-table tr.qual-rank-3 td{{background:#fef3c7!important;color:#78350f!important}}
        .texttv-table tr.qual-rank-4 td{{background:#f1f5f9!important;color:#334155!important}}
        .texttv-table tr.qual-playoff td{{background:#fef3c7!important;color:#78350f!important}}
        .qualifier{{display:inline-flex;width:24px;height:24px;align-items:center;justify-content:center;border-radius:4px;color:#fff;font-weight:900}}
        .qualifier.a,.texttv-legend i.a{{background:#16a34a}}
        .qualifier.b,.texttv-legend i.b{{background:#2563eb}}
        .qualifier.rank-1{{background:#15803d;min-width:28px;width:auto;padding:0 6px}}
        .qualifier.rank-2{{background:#2563eb;min-width:28px;width:auto;padding:0 6px}}
        .qualifier.rank-3{{background:#d97706;min-width:28px;width:auto;padding:0 6px}}
        .qualifier.rank-4{{background:#64748b;min-width:28px;width:auto;padding:0 6px}}
        .qualifier.playoff{{background:#d97706;min-width:28px;width:auto;padding:0 6px}}
        .texttv-legend{{display:flex;gap:18px;margin-top:7px;color:#334155;font-size:13px}}
        .texttv-legend span{{display:flex;align-items:center;gap:6px}}
        .texttv-legend i{{width:13px;height:13px;border-radius:2px;display:inline-block}}
        </style>
        <div class="texttv-wrap"><table class="texttv-table">
        <thead><tr><th>Pl</th><th>Lag</th><th>S</th><th>V</th><th>O</th><th>F</th><th>GM</th><th>IM</th><th>MS</th><th>P</th><th>Slutspel</th></tr></thead>
        <tbody>{''.join(rows_html)}</tbody></table></div>{legend}
        """,
        unsafe_allow_html=True,
    )



def generate_schedule(tournament_id, tournament, rules, preserve_existing=False):
    repo = schedule_repository()

    def schedule_source_id(source):
        direct_team_id = schedule_source_team_id(source)
        if direct_team_id is not None:
            return direct_team_id
        return resolve_source(source)

    try:
        schedule_window = build_schedule_window(tournament, rules)
    except (TypeError, ValueError, KeyError):
        return 0, 0, "Turneringen måste ha giltiga cupdatum och tillgängliga tider för planerna."

    start = schedule_window.start
    end_date = schedule_window.end_date
    latest_kickoff = schedule_window.latest_pitch_time
    duration = schedule_window.group_match_duration
    pitch_windows = {(str(r["play_date"]), int(r["pitch_number"])): (datetime.strptime(r["start_time"], "%H:%M").time(), datetime.strptime(r["end_time"], "%H:%M").time()) for r in ensure_pitch_day_windows(tournament_id, tournament, rules["pitch_count"], rules["first_match_time"], rules["latest_kickoff_time"])}

    def pitch_bounds(day,pitch):
        return pitch_windows.get((day.isoformat(),int(pitch)),(start.time(),latest_kickoff))

    def duration_for_match(match_row):
        return schedule_window.duration_for_stage(match_row["stage"])

    def valid_pitch_start_for(candidate, match_duration, pitch):
        while candidate.date() <= end_date:
            day_start_time, day_end_time = pitch_bounds(candidate.date(),pitch)
            day_start = datetime.combine(candidate.date(), day_start_time)
            day_limit = datetime.combine(candidate.date(), day_end_time)
            if candidate < day_start:
                candidate = day_start
            if candidate + match_duration <= day_limit:
                return candidate
            next_day=candidate.date()+timedelta(days=1)
            if next_day>end_date: return None
            candidate=datetime.combine(next_day,pitch_bounds(next_day,pitch)[0])
        return None
    # Databasen ändras först när hela schemaläggningspasset är färdigberäknat.
    # Det minskar risken för ett halvuppdaterat schema om ett oväntat fel inträffar.
    schedule_updates = []
    pitch_gap = timedelta(minutes=rules["pitch_break_minutes"])
    avoid_consecutive = bool(rules["avoid_consecutive_matches"])
    consecutive_break = timedelta(minutes=rules["consecutive_match_break_minutes"] if avoid_consecutive else 0)
    pitch_ready = {pitch: start for pitch in range(1, rules["pitch_count"] + 1)}
    team_ready = {}
    team_last_end = {}
    referees, travel_preference_rows, matches = repo.scheduling_inputs(tournament_id)
    referee_ready = {r["id"]: start for r in referees}
    travel_preferences = {
        row["id"]: row
        for row in travel_preference_rows
    }
    schedule_strategy = normalize_schedule_strategy(_row_value(rules, "schedule_strategy", "earliest_finish"))
    consider_pitch_travel = bool(_row_value(rules, "consider_pitch_travel", 0))
    travel_matrix = pitch_travel_matrix(tournament_id) if consider_pitch_travel else {}
    team_last_pitch = {}
    pitch_loads = {pitch: 0 for pitch in pitch_ready}

    def apply_first_match_preference(candidate, team_id):
        preference = travel_preferences.get(team_id)
        if not preference or not preference["late_first_match"] or not preference["earliest_first_time"]:
            return candidate
        # Önskemålet gäller bara lagets första match i turneringen.
        if team_id in team_last_end:
            return candidate
        try:
            preferred_time = datetime.strptime(preference["earliest_first_time"], "%H:%M").time()
        except (TypeError, ValueError):
            return candidate
        preferred_start = datetime.combine(start.date(), preferred_time)
        return max(candidate, preferred_start)

    locked_events = []
    if preserve_existing:
        for existing_match in matches:
            if not existing_match["scheduled_start"] or not existing_match["pitch_number"]:
                continue
            home_id = schedule_source_id(existing_match["home_source"])
            away_id = schedule_source_id(existing_match["away_source"])
            if not home_id or not away_id:
                continue
            existing_start = datetime.fromisoformat(existing_match["scheduled_start"])
            existing_end = existing_start + duration_for_match(existing_match)
            pitch = existing_match["pitch_number"]
            pitch_ready[pitch] = max(pitch_ready.get(pitch, start), existing_end + pitch_gap)
            team_ready[home_id] = max(team_ready.get(home_id, start), existing_end + consecutive_break)
            team_ready[away_id] = max(team_ready.get(away_id, start), existing_end + consecutive_break)
            team_last_end[home_id] = max(team_last_end.get(home_id, start), existing_end)
            team_last_end[away_id] = max(team_last_end.get(away_id, start), existing_end)
            if existing_match["referee_id"] in referee_ready:
                referee_ready[existing_match["referee_id"]] = max(referee_ready[existing_match["referee_id"]], existing_end + pitch_gap)
    else:
        for locked_match in matches:
            if not locked_match["schedule_locked"] or not locked_match["scheduled_start"] or not locked_match["pitch_number"]:
                continue
            locked_home = schedule_source_id(locked_match["home_source"])
            locked_away = schedule_source_id(locked_match["away_source"])
            locked_start = datetime.fromisoformat(locked_match["scheduled_start"])
            locked_events.append({
                "start": locked_start, "end": locked_start + duration_for_match(locked_match), "pitch": locked_match["pitch_number"],
                "referee": locked_match["referee_id"], "teams": {locked_home, locked_away} - {None},
            })

    def move_past_locked(candidate_start, pitch, referee_id, home_id, away_id, match_duration):
        candidate_teams = {home_id, away_id}
        changed = True
        while changed:
            changed = False
            candidate_end = candidate_start + match_duration
            for locked in locked_events:
                blocked_until = None
                if pitch == locked["pitch"] and candidate_start < locked["end"] + pitch_gap and candidate_end + pitch_gap > locked["start"]:
                    blocked_until = locked["end"] + pitch_gap
                if referee_id and referee_id == locked["referee"] and candidate_start < locked["end"] and candidate_end > locked["start"]:
                    blocked_until = max(blocked_until or locked["end"], locked["end"])
                if candidate_teams & locked["teams"] and candidate_start < locked["end"] + consecutive_break and candidate_end + consecutive_break > locked["start"]:
                    blocked_until = max(blocked_until or locked["end"] + consecutive_break, locked["end"] + consecutive_break)
                if blocked_until and blocked_until > candidate_start:
                    candidate_start = blocked_until
                    changed = True
                    break
        return valid_pitch_start_for(candidate_start,match_duration,pitch)
    scheduled = 0
    unresolved = 0
    remaining = []
    placeholder_matches = []
    for match_row in matches:
        if match_row["scheduled_start"] and (preserve_existing or match_row["schedule_locked"]):
            continue
        home_id = schedule_source_id(match_row["home_source"])
        away_id = schedule_source_id(match_row["away_source"])
        if not home_id or not away_id:
            # Slutspelsmatcher ska ändå få tid, plan och matchnummer redan innan lagen är klara.
            placeholder_matches.append(match_row)
            continue
        remaining.append((match_row, home_id, away_id))
    # Optimera ordningen på konkreta matcher före exakt placering. OR-Tools
    # löser parallella schemavågor när biblioteket finns tillgängligt; den
    # befintliga schemaläggaren ansvarar fortfarande för exakta tider, låsta
    # matcher, domare, reseönskemål och slutspelsberoenden.
    if remaining:
        optimized_order, optimization_engine = optimize_match_order(
            remaining,
            pitch_count=int(rules.get("pitch_count") or 1),
            time_limit_seconds=2.0,
        )
        remaining = [remaining[index] for index in optimized_order]
    else:
        optimization_engine = "trivial"

    last_scheduled_teams = set()
    forced_consecutive = 0

    def late_group_penalty(match_row, candidate_start, pitch, home_id, away_id):
        if match_row["stage"] != "Gruppspel":
            return 0
        requests = any(
            bool(_row_value(travel_preferences.get(team_id), "avoid_late_group_match", 0))
            for team_id in (home_id, away_id)
        )
        if not requests:
            return 0
        p_start,p_end=pitch_bounds(candidate_start.date(),pitch)
        day_start=datetime.combine(candidate_start.date(),p_start)
        day_end=datetime.combine(candidate_start.date(),p_end)
        span_seconds = max(1, (day_end - day_start).total_seconds())
        progress = (candidate_start - day_start).total_seconds() / span_seconds
        return 1 if progress >= 0.75 else 0

    def first_match_request_penalty(candidate_start, team_id):
        pref = travel_preferences.get(team_id)
        if not pref or not pref["late_first_match"] or not pref["earliest_first_time"] or team_id in team_last_end:
            return 0
        try:
            wanted = datetime.strptime(pref["earliest_first_time"], "%H:%M").time()
        except (TypeError, ValueError):
            return 0
        wanted_dt = datetime.combine(candidate_start.date(), wanted)
        if candidate_start >= wanted_dt:
            return 0
        priority = max(1, int(_row_value(pref, "request_priority", 100) or 100))
        minutes_early = max(1, int((wanted_dt-candidate_start).total_seconds()//60))
        return minutes_early * max(1, 101-priority)

    try:
        _pref_order = json.loads(_row_value(rules, "preference_order_json", "") or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        _pref_order = []
    _pref_rank = {name:i for i,name in enumerate(_pref_order)}

    def scheduling_candidate_key(item):
        candidate_start, consecutive_penalty, late_penalty, request_penalty, order, pitch, referee_id = item
        penalties = {
            "Tillgodose lagens startönskemål": request_penalty,
            "Undvik matcher direkt efter varandra": consecutive_penalty,
            "Minimera sena gruppmatcher": late_penalty,
        }
        ordered = tuple(penalties.get(name,0) for name in _pref_order if name in penalties)
        fallback = (request_penalty, consecutive_penalty, late_penalty)
        strategy_key = candidate_sort_key((candidate_start, consecutive_penalty, late_penalty, order, pitch, referee_id), schedule_strategy, pitch_loads)
        return ordered + fallback + tuple(strategy_key)

    while remaining:
        candidates = []
        for order, (match_row, home_id, away_id) in enumerate(remaining):
            for pitch in pitch_ready:
                consecutive_penalty = int(avoid_consecutive and bool({home_id, away_id} & last_scheduled_teams))
                home_ready = team_ready.get(home_id, start)
                away_ready = team_ready.get(away_id, start)
                if consider_pitch_travel:
                    if home_id in team_last_end:
                        home_ready = max(home_ready, team_last_end[home_id] + timedelta(minutes=travel_minutes(travel_matrix, team_last_pitch.get(home_id), pitch)))
                    if away_id in team_last_end:
                        away_ready = max(away_ready, team_last_end[away_id] + timedelta(minutes=travel_minutes(travel_matrix, team_last_pitch.get(away_id), pitch)))
                basic_start = max(pitch_ready[pitch], home_ready, away_ready)
                if consecutive_penalty:
                    basic_start = max(
                        basic_start,
                        team_last_end.get(home_id, start) + consecutive_break,
                        team_last_end.get(away_id, start) + consecutive_break,
                    )
                match_duration = duration_for_match(match_row)
                if rules["referee_mode"] == "Automatisk" and referees:
                    for referee in referees:
                        referee_id = referee["id"]
                        candidate_start = valid_pitch_start_for(max(basic_start, referee_ready[referee_id]), match_duration, pitch)
                        candidate_start = move_past_locked(candidate_start, pitch, referee_id, home_id, away_id, match_duration) if candidate_start else None
                        if candidate_start:
                            candidates.append((candidate_start, consecutive_penalty, late_group_penalty(match_row, candidate_start, pitch, home_id, away_id), first_match_request_penalty(candidate_start,home_id)+first_match_request_penalty(candidate_start,away_id), order, pitch, referee_id))
                else:
                    candidate_start = valid_pitch_start_for(basic_start, match_duration, pitch)
                    candidate_start = move_past_locked(candidate_start, pitch, match_row["referee_id"], home_id, away_id, match_duration) if candidate_start else None
                    if candidate_start:
                        candidates.append((candidate_start, consecutive_penalty, late_group_penalty(match_row, candidate_start, pitch, home_id, away_id), first_match_request_penalty(candidate_start,home_id)+first_match_request_penalty(candidate_start,away_id), order, pitch, match_row["referee_id"]))
        if not candidates:
            unresolved += len(remaining)
            days = (end_date - start.date()).days + 1
            daily_minutes = int((datetime.combine(start.date(), latest_kickoff) - start).total_seconds() // 60)
            slot_minutes = max(1, int(duration.total_seconds() // 60) + rules["pitch_break_minutes"])
            if daily_minutes >= int(duration.total_seconds() // 60):
                starts_per_pitch_day = 1 + max(0, (daily_minutes - int(duration.total_seconds() // 60)) // slot_minutes)
            else:
                starts_per_pitch_day = 0
            theoretical_capacity = starts_per_pitch_day * rules["pitch_count"] * max(days, 0)
            reasons = []
            if len(matches) > theoretical_capacity:
                reasons.append(
                    f"det finns teoretiskt högst {theoretical_capacity} planplatser för {len(matches)} matcher med nuvarande tider"
                )
            if rules["referee_mode"] == "Automatisk" and not referees:
                reasons.append("inga domare är registrerade för automatisk tillsättning")
            late_requests = sum(1 for pref in travel_preferences.values() if pref["late_first_match"] and pref["earliest_first_time"])
            if late_requests:
                reasons.append(f"{late_requests} lag har önskemål om senare första match")
            if avoid_consecutive:
                reasons.append(f"kravet på extra lagvila är {rules['consecutive_match_break_minutes']} minuter")
            reason_text = "; ".join(reasons) if reasons else "kombinationen av plan-, lag-, domar- och tidsbegränsningar"
            warning = (
                "Alla matcher fick inte plats inom cupens datumintervall och planernas tillgängliga tider. "
                f"Möjliga orsaker: {reason_text}."
            )
            break
        match_start, consecutive_penalty, _late_penalty, _request_penalty, order, pitch, referee_id = min(candidates, key=scheduling_candidate_key)
        match_row, home_id, away_id = remaining.pop(order)
        forced_consecutive += consecutive_penalty
        last_scheduled_teams = {home_id, away_id}
        match_end = match_start + duration_for_match(match_row)
        schedule_updates.append(
            (match_start.isoformat(timespec="minutes"), pitch, referee_id, match_row["id"])
        )
        pitch_ready[pitch] = match_end + pitch_gap
        team_ready[home_id] = match_end + consecutive_break
        team_ready[away_id] = match_end + consecutive_break
        team_last_end[home_id] = match_end
        team_last_end[away_id] = match_end
        team_last_pitch[home_id] = pitch
        team_last_pitch[away_id] = pitch
        pitch_loads[pitch] = int(pitch_loads.get(pitch, 0)) + 1
        if referee_id and rules["referee_mode"] == "Automatisk":
            referee_ready[referee_id] = match_end + pitch_gap
        scheduled += 1

    # Schemalägg därefter slutspelsplatshållare. De får riktiga tider och löpnummer
    # även om gruppvinnare/semifinalvinnare ännu inte är kända.
    scheduled_start_by_id = {}
    scheduled_end_by_id = {}
    for existing_match in matches:
        if existing_match["scheduled_start"]:
            existing_start = datetime.fromisoformat(existing_match["scheduled_start"])
            existing_duration = duration_for_match(existing_match)
            scheduled_start_by_id[existing_match["id"]] = existing_start
            scheduled_end_by_id[existing_match["id"]] = existing_start + existing_duration
    match_by_id = {m["id"]: m for m in matches}
    for start_iso, _, _, match_id in schedule_updates:
        scheduled_start = datetime.fromisoformat(start_iso)
        scheduled_start_by_id[match_id] = scheduled_start
        scheduled_end_by_id[match_id] = scheduled_start + duration_for_match(match_by_id[match_id])

    group_match_ids = {}
    for m in matches:
        if m["stage"] == "Gruppspel" and m["group_id"]:
            group_match_ids.setdefault(m["group_id"], []).append(m["id"])

    def source_dependency_ready(source):
        parts = source.split(":") if source else []
        if not parts:
            return start
        if parts[0] == "group":
            group_id = int(parts[1])
            ids = group_match_ids.get(group_id, [])
            if not ids or any(match_id not in scheduled_end_by_id for match_id in ids):
                return None
            return max(scheduled_end_by_id[match_id] for match_id in ids) + consecutive_break
        if parts[0] in ("winner", "loser"):
            feeder_id = int(parts[1])
            if feeder_id not in scheduled_end_by_id:
                return None
            return scheduled_end_by_id[feeder_id] + consecutive_break
        return start

    pending_placeholders = list(placeholder_matches)
    while pending_placeholders:
        progress = False
        for match_row in list(pending_placeholders):
            home_ready = source_dependency_ready(match_row["home_source"])
            away_ready = source_dependency_ready(match_row["away_source"])
            if home_ready is None or away_ready is None:
                continue
            match_duration = duration_for_match(match_row)
            basic_start = max(home_ready, away_ready, start)
            candidates = []
            for pitch in pitch_ready:
                base = max(basic_start, pitch_ready[pitch])
                if rules["referee_mode"] == "Automatisk" and referees:
                    for referee in referees:
                        referee_id = referee["id"]
                        candidate = valid_pitch_start_for(max(base, referee_ready[referee_id]), match_duration, pitch)
                        if candidate:
                            candidates.append((candidate, pitch, referee_id))
                else:
                    candidate = valid_pitch_start_for(base, match_duration, pitch)
                    if candidate:
                        candidates.append((candidate, pitch, match_row["referee_id"]))
            if not candidates:
                continue
            match_start, pitch, referee_id = min(candidates, key=lambda item: (item[0], item[1], item[2] or 0))
            match_end = match_start + match_duration
            schedule_updates.append((match_start.isoformat(timespec="minutes"), pitch, referee_id, match_row["id"]))
            scheduled_start_by_id[match_row["id"]] = match_start
            scheduled_end_by_id[match_row["id"]] = match_end
            pitch_ready[pitch] = match_end + pitch_gap
            if referee_id and rules["referee_mode"] == "Automatisk":
                referee_ready[referee_id] = match_end + pitch_gap
            scheduled += 1
            pending_placeholders.remove(match_row)
            progress = True
        if not progress:
            unresolved += len(pending_placeholders)
            warning = (
                (locals().get("warning", "") + " ").strip()
                + f"{len(pending_placeholders)} slutspelsmatch(er) kunde inte få en tid inom cupens plantider."
            ).strip()
            break

    warning = locals().get("warning", "")
    if rules["referee_mode"] == "Automatisk" and not referees:
        referee_warning = "Schemat skapades utan domare eftersom inga domare är registrerade."
        warning = f"{warning} {referee_warning}".strip()
    if forced_consecutive:
        consecutive_warning = (
            f"Schemat behövde placera {forced_consecutive} match(er) efter en match med samma lag; "
            f"den angivna extrapusen på {rules['consecutive_match_break_minutes']} minuter lades in."
        )
        warning = f"{warning} {consecutive_warning}".strip()

    if optimization_engine == "greedy-fallback":
        warning = f"{warning} OR-Tools var inte tillgängligt; säker standardoptimering användes.".strip()

    # Spara hela schemaläggningspasset atomiskt via repository-lagret.
    try:
        repo.persist_generated_schedule(
            tournament_id=tournament_id,
            schedule_updates=schedule_updates,
            unresolved=unresolved,
            preserve_existing=preserve_existing,
        )
    except Exception as exc:
        return 0, len(schedule_updates) + unresolved, f"Schemat kunde inte sparas och inga schemaändringar genomfördes: {exc}"

    return scheduled, unresolved, warning


def validate_schedule(tournament_id, tournament, rules):
    """Kontrollera schemat och sammanställ väntetid och belastning per lag."""
    rows = schedule_repository().scheduled_matches(tournament_id)
    duration = timedelta(minutes=(rules["halves"] * rules["minutes_per_half"]) + ((rules["halves"] - 1) * rules["halftime_minutes"]))
    playoff_extra = timedelta(
        minutes=int(tournament["extra_time_minutes"] or 0)
        if tournament["playoff_tie_rule"] == "Förlängning + straffar" else 0
    )
    pitch_gap = timedelta(minutes=rules["pitch_break_minutes"])
    avoid_consecutive = bool(rules["avoid_consecutive_matches"])
    consecutive_break_minutes = rules["consecutive_match_break_minutes"] if avoid_consecutive else 0
    cup_start = datetime.fromisoformat(tournament["start_date"] or tournament["tournament_date"]).date()
    cup_end = datetime.fromisoformat(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"]).date()
    first_time = datetime.strptime(rules["first_match_time"], "%H:%M").time()
    latest_time = datetime.strptime(rules["latest_kickoff_time"], "%H:%M").time()
    validation_windows = {(str(r["play_date"]),int(r["pitch_number"])): (datetime.strptime(r["start_time"], "%H:%M").time(), datetime.strptime(r["end_time"], "%H:%M").time()) for r in ensure_pitch_day_windows(tournament_id, tournament, rules["pitch_count"], rules["first_match_time"], rules["latest_kickoff_time"])}
    errors, warnings = [], []
    events = []
    for number, match_row in enumerate(rows, 1):
        start_at = datetime.fromisoformat(match_row["scheduled_start"])
        match_duration = duration + (playoff_extra if match_row["stage"] != "Gruppspel" else timedelta(0))
        home_id, away_id = resolve_source(match_row["home_source"]), resolve_source(match_row["away_source"])
        home_team, away_team = team(home_id), team(away_id)
        events.append({"number": number, "row": match_row, "start": start_at, "end": start_at + match_duration, "teams": {home_id, away_id} - {None}})
        if not cup_start <= start_at.date() <= cup_end:
            errors.append(f"Match {number} ligger utanför cupens datumintervall.")
        pitch_no=int(match_row["pitch_number"] or 0)
        day_first, day_last = validation_windows.get((start_at.date().isoformat(),pitch_no), (first_time, latest_time))
        if start_at.time() < day_first:
            errors.append(f"Match {number} har avspark {start_at.strftime('%H:%M')} före planens tillåtna starttid {day_first.strftime('%H:%M')}.")
        if (start_at + match_duration) > datetime.combine(start_at.date(), day_last):
            errors.append(f"Match {number} slutar {(start_at + match_duration).strftime('%H:%M')}, efter planens sluttid {day_last.strftime('%H:%M')}.")
        if not match_row["pitch_number"] or not 1 <= match_row["pitch_number"] <= rules["pitch_count"]:
            errors.append(f"Match {number} har en ogiltig plan.")
        if rules["referee_mode"] == "Automatisk" and not match_row["referee_id"]:
            warnings.append(f"Match {number} saknar domare.")
        if kit_color_conflict(home_team, away_team):
            warnings.append(
                f"Möjlig färglikhet i match {number}: {away_team['name']}s ordinarie ställ och bortaställ ligger nära hemmalagets färger. "
                f"Ett ytterligare avvikande ställ behöver användas."
            )
    for index, first in enumerate(events):
        for second in events[index + 1:]:
            if second["start"] >= first["end"] + pitch_gap and second["start"] >= first["end"]:
                break
            if first["row"]["pitch_number"] == second["row"]["pitch_number"] and second["start"] < first["end"] + pitch_gap:
                errors.append(f"Plankrock mellan match {first['number']} och {second['number']}.")
            if first["row"]["referee_id"] and first["row"]["referee_id"] == second["row"]["referee_id"] and second["start"] < first["end"]:
                errors.append(f"Domarkrock mellan match {first['number']} och {second['number']}.")
            if first["teams"] & second["teams"] and second["start"] < first["end"]:
                errors.append(f"Ett lag är dubbelbokat i match {first['number']} och {second['number']}.")
    team_events = {}
    for event in events:
        for team_id in event["teams"]:
            team_events.setdefault(team_id, []).append(event)
    day_starts = {}
    for event in events:
        day_starts.setdefault(event["start"].date(), []).append(event["start"])
    quality_rows = []
    for team_id, team_matches in team_events.items():
        team_matches.sort(key=lambda event: event["start"])
        waits = []
        consecutive = 0
        for previous, current in zip(team_matches, team_matches[1:]):
            rest_minutes = int((current["start"] - previous["end"]).total_seconds() // 60)
            waits.append(rest_minutes)
            if avoid_consecutive and rest_minutes < consecutive_break_minutes:
                errors.append(
                    f"{team(team_id)['name']} saknar den obligatoriska extrapusen på {consecutive_break_minutes} minuter "
                    f"mellan match {previous['number']} och {current['number']}."
                )
            if rest_minutes <= rules["pitch_break_minutes"]:
                consecutive += 1
                if avoid_consecutive:
                    warnings.append(f"{team(team_id)['name']} spelar match {previous['number']} och {current['number']} direkt efter varandra.")
        team_row = team(team_id)
        if team_row and team_row["late_first_match"] and team_row["earliest_first_time"] and team_matches:
            try:
                preferred_time = datetime.strptime(team_row["earliest_first_time"], "%H:%M").time()
                first_event = team_matches[0]
                if first_event["start"].date() == cup_start and first_event["start"].time() < preferred_time:
                    warnings.append(
                        f"{team_row['name']} önskar sin första match tidigast {preferred_time.strftime('%H:%M')}, "
                        f"men är schemalagt {first_event['start'].strftime('%H:%M')}."
                    )
            except (TypeError, ValueError):
                pass
        early = sum(1 for event in team_matches if event["start"] == min(day_starts[event["start"].date()]))
        late = sum(1 for event in team_matches if event["start"] == max(day_starts[event["start"].date()]))
        quality_rows.append({
            "Lag": team(team_id)["name"], "Matcher": len(team_matches),
            "Kortaste vila": min(waits) if waits else None,
            "Genomsnittlig vila": round(sum(waits) / len(waits)) if waits else None,
            "Direkt efter": consecutive, "Tidiga matcher": early, "Sena matcher": late,
        })
    unscheduled_groups = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND stage='Gruppspel' AND scheduled_start IS NULL",
        (tournament_id,),
    )["n"]
    if unscheduled_groups:
        errors.append(f"{unscheduled_groups} gruppspelsmatcher saknar schematid.")
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings)), quality_rows


def render_bracket_tree(bracket_id, public=False):
    bracket_matches = all_rows("SELECT * FROM matches WHERE bracket_id=? ORDER BY round_no,match_no", (bracket_id,))
    bracket_team_by_id = {}
    if bracket_matches:
        bracket_tournament_id = int(_row_value(bracket_matches[0], "tournament_id", 0) or 0)
        if bracket_tournament_id:
            bracket_team_rows = all_rows(
                "SELECT * FROM teams WHERE tournament_id=? ORDER BY id",
                (bracket_tournament_id,),
            )
            bracket_team_by_id = {int(row["id"]): row for row in bracket_team_rows}
    main_stages = []
    for stage_name in ["Kvartsfinal", "Semifinal", "Final"]:
        stage_matches = [m for m in bracket_matches if m["stage"] == stage_name]
        if stage_matches:
            main_stages.append((stage_name, stage_matches))
    if not main_stages:
        st.info("Slutspelsträdet saknar matcher.")
        return

    # A final-only bracket should be compact instead of reserving a full tree canvas.
    stage_count = len(main_stages)
    first_count = len(main_stages[0][1])
    compact_final_only = stage_count == 1 and first_count == 1
    card_width = 320 if compact_final_only else 250
    card_height = 108
    column_gap = 92
    column_width = card_width + column_gap
    header_height = 44
    if compact_final_only:
        play_height = card_height + 44
        canvas_width = min(520, card_width + 40)
    else:
        play_height = max(250, first_count * 154)
        canvas_width = stage_count * column_width - column_gap + 40
    canvas_height = header_height + play_height + 16

    stage_centers = []
    first_centers = [(index + 0.5) * play_height / first_count for index in range(first_count)]
    stage_centers.append(first_centers)
    for stage_index in range(1, len(main_stages)):
        previous = stage_centers[-1]
        match_count = len(main_stages[stage_index][1])
        centers = []
        for index in range(match_count):
            feeders = previous[index * 2:index * 2 + 2]
            centers.append(sum(feeders) / len(feeders) if feeders else (index + 0.5) * play_height / match_count)
        stage_centers.append(centers)

    def match_card(match_row, left, center, extra_class=""):
        home_id = resolve_source(match_row["home_source"])
        away_id = resolve_source(match_row["away_source"])
        home = bracket_team_by_id.get(int(home_id)) if home_id else None
        away = bracket_team_by_id.get(int(away_id)) if away_id else None
        home_name = html.escape(home["name"] if home is not None else source_label(match_row["home_source"]))
        away_name = html.escape(away["name"] if away is not None else source_label(match_row["away_source"]))
        home_color = home["primary_color"] if home else "#94a3b8"
        away_color = away["secondary_color"] if away else "#94a3b8"
        home_score = "–" if match_row["home_score"] is None else str(match_row["home_score"])
        away_score = "–" if match_row["away_score"] is None else str(match_row["away_score"])
        home_winner = away_winner = False
        if match_row["home_score"] is not None and match_row["away_score"] is not None:
            if match_row["home_score"] > match_row["away_score"]:
                home_winner = True
            elif match_row["away_score"] > match_row["home_score"]:
                away_winner = True
            elif match_row["decided_winner_id"] in (home_id, away_id):
                home_winner = match_row["decided_winner_id"] == home_id
                away_winner = match_row["decided_winner_id"] == away_id
            elif match_row["home_penalties"] is not None and match_row["away_penalties"] is not None:
                home_winner = match_row["home_penalties"] > match_row["away_penalties"]
                away_winner = match_row["away_penalties"] > match_row["home_penalties"]
        if public and not match_row["schedule_published"]:
            schedule_text, referee = "Tid och plan ej publicerade", "Ej publicerad"
        else:
            schedule_text, referee = match_meta(match_row)
        penalties = ""
        if match_row["decided_winner_id"]:
            penalties = "<div class='bracket-penalties'>Avgjord genom lottning</div>"
        elif match_row["home_penalties"] is not None:
            penalties = f"<div class='bracket-penalties'>Straffar {match_row['home_penalties']}–{match_row['away_penalties']}</div>"
        top = header_height + center - card_height / 2
        return f"""
          <div class="classic-match {extra_class}" style="left:{left}px;top:{top:.1f}px;width:{card_width}px;min-height:{card_height}px">
            <div class="classic-meta">{html.escape(schedule_text)}</div>
            <div class="classic-team{' winner' if home_winner else ''}"><i style="background:{home_color}"></i><span>{home_name}</span><b>{home_score}</b></div>
            <div class="classic-team{' winner' if away_winner else ''}"><i style="background:{away_color}"></i><span>{away_name}</span><b>{away_score}</b></div>
            {penalties}<div class="classic-referee">Domare: {html.escape(referee)}</div>
          </div>
        """

    headers = []
    cards = []
    for stage_index, (stage_name, stage_matches) in enumerate(main_stages):
        left = 20 + stage_index * column_width
        if compact_final_only:
            left = max(20, (canvas_width - card_width) / 2)
        trophy = " 🏆" if stage_name == "Final" else ""
        headers.append(f"<div class='classic-stage-title' style='left:{left}px;width:{card_width}px'>{stage_name}{trophy}</div>")
        for match_index, match_row in enumerate(stage_matches):
            cards.append(match_card(match_row, left, stage_centers[stage_index][match_index], "final-match" if stage_name == "Final" else ""))

    connectors = []
    for stage_index in range(len(main_stages) - 1):
        start_x = 20 + stage_index * column_width + card_width
        end_x = 20 + (stage_index + 1) * column_width
        middle_x = (start_x + end_x) / 2
        previous = stage_centers[stage_index]
        following = stage_centers[stage_index + 1]
        for next_index, next_center in enumerate(following):
            feeders = previous[next_index * 2:next_index * 2 + 2]
            if not feeders:
                continue
            top_y = header_height + min(feeders)
            bottom_y = header_height + max(feeders)
            for feeder in feeders:
                y = header_height + feeder
                connectors.append(f"<span class='line horizontal' style='left:{start_x}px;top:{y:.1f}px;width:{middle_x-start_x}px'></span>")
            connectors.append(f"<span class='line vertical' style='left:{middle_x}px;top:{top_y:.1f}px;height:{bottom_y-top_y:.1f}px'></span>")
            target_y = header_height + next_center
            connectors.append(f"<span class='line horizontal' style='left:{middle_x}px;top:{target_y:.1f}px;width:{end_x-middle_x}px'></span>")

    bronze_matches = [m for m in bracket_matches if m["stage"] == "Bronsmatch"]
    bronze_html = ""
    if bronze_matches:
        bronze = bronze_matches[0]
        bronze_home = "–" if bronze["home_score"] is None else bronze["home_score"]
        bronze_away = "–" if bronze["away_score"] is None else bronze["away_score"]
        bronze_html = f"""
          <div class='classic-bronze'>
            <div><strong>🥉 Bronsmatch</strong><small>Placeringsmatch</small></div>
            <span>{html.escape(source_label(bronze['home_source']))}</span><b>{bronze_home}</b>
            <span>{html.escape(source_label(bronze['away_source']))}</span><b>{bronze_away}</b>
          </div>
        """
    st.markdown(
        f"""
        <style>
          .classic-bracket-scroll {{overflow-x:auto;padding:4px 3px 12px}}
          .classic-bracket {{position:relative;width:{canvas_width}px;min-width:{canvas_width}px;max-width:100%;height:{canvas_height}px;background:#fff;border:1px solid #e2e8f0;border-radius:14px}}
          .classic-stage-title {{position:absolute;top:12px;text-align:center;font-size:14px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;color:#334155}}
          .classic-match {{position:absolute;z-index:2;box-sizing:border-box;background:#fff;border:1px solid #cbd5e1;border-radius:8px;box-shadow:0 3px 10px rgba(15,23,42,.11);overflow:hidden}}
          .classic-match.final-match {{border:2px solid #d4a017;box-shadow:0 4px 14px rgba(180,120,0,.18)}}
          .classic-meta {{padding:5px 9px;background:#0f5132;color:#fff;font-size:10px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
          .classic-team {{display:grid;grid-template-columns:12px 1fr 25px;gap:7px;align-items:center;min-height:29px;padding:2px 8px;border-bottom:1px solid #e5e7eb;font-size:13px;color:#334155}}
          .classic-team i {{width:11px;height:18px;border:1px solid #64748b;border-radius:2px}}
          .classic-team span {{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
          .classic-team b {{font-size:15px;text-align:center;color:#0f172a}}
          .classic-team.winner {{background:#ecfdf5;color:#065f46;font-weight:800}}
          .classic-team.winner b {{color:#047857}}
          .classic-referee {{padding:3px 8px;color:#64748b;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
          .bracket-penalties {{position:absolute;right:34px;bottom:3px;color:#9a3412;font-size:9px;font-weight:700}}
          .line {{position:absolute;z-index:1;display:block;box-sizing:border-box}}
          .line.horizontal {{border-top:2px solid #94a3b8}}
          .line.vertical {{border-left:2px solid #94a3b8}}
          .classic-bronze {{display:grid;grid-template-columns:1fr 32px;gap:4px 10px;max-width:330px;margin-top:12px;padding:12px 14px;background:#fffbeb;border:1px solid #fcd34d;border-left:5px solid #b45309;border-radius:9px}}
          .classic-bronze div {{grid-column:1 / 3;display:flex;justify-content:space-between;margin-bottom:4px;color:#92400e}}
          .classic-bronze small {{color:#a16207}}
          .classic-bronze span {{font-size:13px}}
          .classic-bronze b {{text-align:center}}
        </style>
        <div class="classic-bracket-scroll">
          <div class="classic-bracket">{''.join(connectors)}{''.join(headers)}{''.join(cards)}</div>
          {bronze_html}
        </div>
        """,
        unsafe_allow_html=True,
    )



def public_match_events_html(match_id, match_row=None, rows=None, team_names=None):
    """Publika mål/röda kort. Förhämtad data undviker N+1-frågor."""
    if match_row is None:
        match_row = one_row("SELECT home_source, away_source FROM matches WHERE id=?", (match_id,))
    if not match_row:
        return ""

    home_team_id = resolve_source(match_row["home_source"])
    away_team_id = resolve_source(match_row["away_source"])

    if rows is None:
        rows = all_rows(
            """
            SELECT p.name AS player_name, COALESCE(p.is_protected,0) AS is_protected,
                   t.id AS team_id, t.name AS team_name, s.goals, s.red_cards
            FROM player_match_stats s
            JOIN players p ON p.id=s.player_id
            JOIN teams t ON t.id=p.team_id
            WHERE s.match_id=? AND (s.goals > 0 OR s.red_cards > 0)
            ORDER BY p.name
            """,
            (match_id,),
        )
    if not rows:
        return ""

    team_data = {}
    for row in rows:
        team_id = row["team_id"]
        team_data.setdefault(team_id, {"name": row["team_name"], "events": []})
        goals = int(row["goals"] or 0)
        reds = int(row["red_cards"] or 0)
        public_player_name = "Skyddad spelare" if bool(_row_value(row, "is_protected", 0)) else row["player_name"]
        if goals:
            suffix = f" ×{goals}" if goals > 1 else ""
            team_data[team_id]["events"].append(
                f"<span class='cn-event cn-goal'>⚽ {html.escape(public_player_name)}{suffix}</span>"
            )
        if reds:
            suffix = f" ×{reds}" if reds > 1 else ""
            team_data[team_id]["events"].append(
                f"<span class='cn-event cn-red'>🟥 {html.escape(public_player_name)}{suffix}</span>"
            )

    ordered_team_ids = [home_team_id, away_team_id]
    team_blocks = []
    for team_id in ordered_team_ids:
        data = team_data.get(team_id)
        if data:
            name = data["name"]
            events = "".join(data["events"])
        else:
            name = (team_names or {}).get(team_id, "")
            events = "<span class='cn-no-events'>–</span>"
        team_blocks.append(
            "<div class='cn-event-team'>"
            f"<div class='cn-event-team-name'>{html.escape(name)}</div>"
            f"<div class='cn-events-list'>{events}</div>"
            "</div>"
        )

    return (
        "<div class='cn-match-events'>"
        f"<div class='cn-events-title'>{html.escape(tr('Matchhändelser'))}</div>"
        "<div class='cn-event-teams'>" + "".join(team_blocks) + "</div>"
        "</div>"
    )




def public_rules_html(tournament, rules):
    """Bygg lättlästa publika regler utifrån cupens sparade inställningar."""
    if not rules:
        return ""

    profile = sport_profile(_row_value(tournament, "sport", "Fotboll"))
    period_label = str(profile["period_label"])
    halves = int(rules["halves"] or 1)
    minutes = int(rules["minutes_per_half"] or 0)
    halftime = int(rules["halftime_minutes"] or 0)
    pitch_break = int(rules["pitch_break_minutes"] or 0)
    minimum_rest = int(rules["minimum_team_rest_minutes"] or 0)
    avoid_consecutive = bool(rules["avoid_consecutive_matches"])
    consecutive_break = int(rules["consecutive_match_break_minutes"] or 0)
    pitch_count = int(rules["pitch_count"] or 0)

    match_format = f"{minutes} minuter" if halves == 1 else f"{halves} {period_label} × {minutes} minuter"
    halftime_text = "Ingen periodpaus" if halves == 1 or halftime == 0 else f"Paus mellan {period_label}: {halftime} min"

    if tournament["table_tiebreak"] == "Inbördes möten först":
        table_rule = "Vid lika poäng avgör inbördes möten först, därefter målskillnad och gjorda mål."
    else:
        table_rule = "Vid lika poäng avgör målskillnad först, därefter gjorda mål och lagnamn."

    if avoid_consecutive:
        consecutive_rule = (
            "CupNavi försöker undvika att samma lag spelar direkt efter föregående match. "
            f"Om det inte går läggs {consecutive_break} minuters extra paus in."
        )
    else:
        consecutive_rule = "Följdmatcher för samma lag är tillåtna enligt cupens inställningar."

    playoff_format = tournament["playoff_format"] or "Inget slutspel"
    if playoff_format == "Inget slutspel":
        playoff_rule = "Cupen har inget slutspel."
    else:
        tie_rule = tournament["playoff_tie_rule"] or "Straffar direkt"
        if tie_rule == "Förlängning + straffar":
            extra = int(tournament["extra_time_minutes"] or 0)
            deciding = f"Vid oavgjort spelas {extra} minuters förlängning och därefter straffar vid behov."
        elif tie_rule == "Lottning":
            deciding = "Vid oavgjort avgörs slutspelsmatchen genom lottning."
        else:
            deciding = "Vid oavgjort avgörs slutspelsmatchen med straffar direkt."
        bronze = " Bronsmatch spelas." if tournament["bronze_match"] else " Ingen bronsmatch spelas."
        playoff_rule = f"Slutspelsmodell: {playoff_format}. {deciding}{bronze}"

    return f"""
    <div class="cn-rules-grid">
      <div class="cn-rule-card"><div class="cn-rule-icon">⏱️</div><div>
        <strong>Matchtid</strong><span>{html.escape(match_format)}</span><small>{html.escape(halftime_text)}</small>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">🏅</div><div>
        <strong>Poäng</strong><span>Vinst {int(tournament["points_win"] or 0)} · Oavgjort {int(tournament["points_draw"] or 0)} · Förlust {int(tournament["points_loss"] or 0)}</span>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">📊</div><div>
        <strong>Tabellplacering</strong><span>{html.escape(table_rule)}</span>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">🧘</div><div>
        <strong>Lagvila</strong><span>Minsta lagvila: {minimum_rest} minuter.</span><small>{html.escape(consecutive_rule)}</small>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">🏟️</div><div>
        <strong>Planer och pauser</strong><span>{pitch_count} {'plan' if pitch_count == 1 else 'planer'} används.</span><small>Paus mellan matcher på samma plan: {pitch_break} min.</small>
      </div></div>
      <div class="cn-rule-card"><div class="cn-rule-icon">🏆</div><div>
        <strong>Slutspel</strong><span>{html.escape(playoff_rule)}</span>
      </div></div>
    </div>
    """


def render_about_page():
    """Publik Om-sida driven av CupNavis centrala feature-katalog."""
    language = current_language()
    intro = about_intro(language)
    st.markdown("<div class='cn-about-hero'>", unsafe_allow_html=True)
    st.title(intro["title"])
    st.markdown(f"### {html.escape(intro['lead'])}")
    st.caption(intro["vision"])
    st.markdown("</div>", unsafe_allow_html=True)

    labels = {
        "organizer": "För arrangören" if language == "sv" else "For organizers",
        "teams": "För lag och deltagare" if language == "sv" else "For teams and participants",
        "officials": "För domare och rapportörer" if language == "sv" else "For officials and reporters",
        "audience": "För publik" if language == "sv" else "For spectators",
        "platform": "Plattformen" if language == "sv" else "The platform",
    }
    grouped = {}
    for item in feature_catalog(language):
        grouped.setdefault(item["category"], []).append(item)
    for category in ("organizer", "teams", "officials", "audience", "platform"):
        items = grouped.get(category, [])
        if not items:
            continue
        st.subheader(labels[category])
        cols = st.columns(2)
        for index, item in enumerate(items):
            with cols[index % 2]:
                st.markdown(
                    f"<div class='cn-about-card'><div class='title'>{html.escape(item['title'])}</div>"
                    f"<div class='body'>{html.escape(item['description'])}</div></div>",
                    unsafe_allow_html=True,
                )
    st.markdown("---")
    st.markdown(
        "**CupNavi** · " + (
            "Byggd för att kunna växa från lokala cuper till internationella multisportturneringar." if language == "sv"
            else "Built to grow from local tournaments to international multi-sport events."
        )
    )


@st.fragment
def render_public_statistics_section(tournament_id, tournament, published_matches, played_matches, forced_section=None):
    """Thin application adapter for the extracted public statistics view."""
    return render_public_statistics_section_module(
        tournament_id,
        tournament,
        published_matches,
        played_matches,
        forced_section=forced_section,
        perf=_PERF,
        tr=tr,
        row_value=_row_value,
        all_rows=all_rows,
        calculate_all_group_tables=calculate_all_group_tables,
        render_empty_state=render_empty_state,
        render_group_table=render_group_table,
        final_ranking_rows=final_ranking_rows,
        render_centered_table=render_centered_table,
        playoff_preview=playoff_preview,
        playoff_specs_for_tournament=playoff_specs_for_tournament,
        brackets_for_display=brackets_for_display,
        render_bracket_tree=render_bracket_tree,
    )


@st.fragment
@st.fragment
def render_public_info_section(tournament_id, tournament, published_matches):
    """Thin application adapter for the extracted Cupinfo view."""
    return render_public_info_section_module(
        tournament_id,
        tournament,
        published_matches,
        perf=_PERF,
        tr=tr,
        row_value=_row_value,
        one_row=one_row,
        all_rows=all_rows,
        public_rules_html=public_rules_html,
        cup_summary=cup_summary,
        sport_profile=sport_profile,
        rate_allowed=_rate_allowed,
        run=run,
    )



def render_public_view(tournament_id, tournament):
    # Besöksstatistik registreras sist så den inte ligger före sidans innehåll.
    if hasattr(st, "query_params"):
        _confirm_token = str(st.query_params.get("notify_confirm", "") or "").strip()
        _unsubscribe_token = str(st.query_params.get("notify_unsubscribe", "") or "").strip()
        if _confirm_token:
            st.success("✓ E-postnotiser är aktiverade.") if confirm_notification_subscription(_confirm_token) else st.warning("Bekräftelselänken är ogiltig eller redan använd.")
            try: del st.query_params["notify_confirm"]
            except KeyError: pass
        if _unsubscribe_token:
            st.success("E-postnotiser är avslutade.") if unsubscribe_notification_subscription(_unsubscribe_token) else st.warning("Avregistreringslänken är ogiltig eller redan använd.")
            try: del st.query_params["notify_unsubscribe"]
            except KeyError: pass
    _public_core = public_core_snapshot(tournament_id)
    published_matches = _public_core["matches"]
    played_matches = [m for m in published_matches if m["home_score"] is not None and m["away_score"] is not None]
    public_teams = _public_core["teams"]
    public_team_by_id = {row["id"]: row for row in public_teams}
    public_team_names = {row["id"]: row["name"] for row in public_teams}
    now = datetime.now()

    def _public_pitch_label(match_row):
        return str(_row_value(match_row, "pitch_name", None) or pitch_label(tournament_id, match_row["pitch_number"]))

    def _public_referee_label(match_row):
        return str(_row_value(match_row, "referee_name", "") or "")

    # v147: grupper laddas först när skärm, gruppfilter eller statistik behöver dem.
    # Matcher-sidan gör alltså ingen gruppfråga bara för att rendera grundvyn.
    def _load_public_groups():
        return _derived_cache_get(
            ("public-groups", int(tournament_id)),
            lambda: all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,)),
        )

    def _public_source_team_id(source):
        """Lös vanliga team:<id>-källor lokalt; bara komplexa slutspelskällor behöver DB-resolver."""
        parts = source.split(":") if source else []
        if len(parts) >= 2 and parts[0] == "team":
            try:
                return int(parts[1])
            except (TypeError, ValueError):
                return None
        return resolve_source(source)

    def _public_source_label(source):
        team_id = _public_source_team_id(source)
        if team_id in public_team_names:
            return public_team_names[team_id]
        return source_label(source)

    screen_mode = bool(hasattr(st, "query_params") and str(st.query_params.get("screen", "")) == "1")
    if screen_mode:
        screen_exit_url = public_cup_url(tournament_id)
        st.markdown("""<style>
          [data-testid="stSidebar"], [data-testid="stHeader"] {display:none !important;}
          .stApp .block-container {max-width:1600px !important;padding:1.2rem 2rem 2rem !important;}
          .cn-persistent-brand,.cn-fixed-share {display:none !important;}
          .cn-screen-head{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:18px}
          .cn-screen-title{font-size:34px;font-weight:900;color:#0f172a}.cn-screen-meta{color:#475569;font-size:16px}
          .cn-screen-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.cn-screen-card{background:white;border:1px solid #dbe3ea;border-radius:16px;padding:16px;box-shadow:0 6px 18px rgba(15,23,42,.06)}
          .cn-screen-card h3{margin:0 0 10px;color:#0f172a}.cn-screen-match{padding:10px 0;border-top:1px solid #edf2f7}.cn-screen-match:first-of-type{border-top:0}.cn-screen-score{font-size:26px;font-weight:900;color:#14532d}.cn-screen-time{font-weight:800;color:#0f172a}.cn-screen-muted{color:#64748b}
          @media(max-width:900px){.cn-screen-grid{grid-template-columns:1fr}.cn-screen-title{font-size:27px}}
        </style>""", unsafe_allow_html=True)
        st.markdown(f"<div class='cn-screen-head'><div><div class='cn-screen-title'>🏆 {html.escape(tournament['name'])}</div><div class='cn-screen-meta'>Informationsskärm · uppdateras automatiskt</div></div><a href='{html.escape(screen_exit_url, quote=True)}'>← Till cupsidan</a></div>", unsafe_allow_html=True)
        components.html("<script>setTimeout(function(){window.parent.location.reload();},30000);</script>", height=0)
        live_rows=[]; upcoming_rows=[]; recent_rows=[]
        for m in published_matches:
            start=datetime.fromisoformat(m['scheduled_start'])
            label=f"{_public_source_label(m['home_source'])} – {_public_source_label(m['away_source'])}"
            if m['home_score'] is not None and m['away_score'] is not None:
                recent_rows.append((start,m,label))
            elif start <= now <= start + timedelta(minutes=max(20, match_duration_minutes(tournament))):
                live_rows.append((start,m,label))
            elif start >= now:
                upcoming_rows.append((start,m,label))
        recent_rows=sorted(recent_rows, reverse=True)[:6]
        upcoming_rows=sorted(upcoming_rows)[:8]
        live_rows=sorted(live_rows)[:8]
        def _screen_matches(rows, kind):
            if not rows: return "<div class='cn-screen-muted'>Inga matcher just nu.</div>"
            out=[]
            for start,m,label in rows:
                if kind=='recent':
                    info=f"<span class='cn-screen-score'>{int(m['home_score'])}–{int(m['away_score'])}</span>"
                else:
                    info=f"<span class='cn-screen-time'>{start.strftime('%H:%M')}</span> · {html.escape(_public_pitch_label(m))}"
                out.append(f"<div class='cn-screen-match'><div><b>{html.escape(label)}</b></div><div>{info}</div></div>")
            return ''.join(out)
        st.markdown(f"<div class='cn-screen-grid'><div class='cn-screen-card'><h3>🔴 Pågår / nu</h3>{_screen_matches(live_rows,'live')}</div><div class='cn-screen-card'><h3>⏭ Kommande</h3>{_screen_matches(upcoming_rows,'upcoming')}</div><div class='cn-screen-card'><h3>✅ Senaste resultat</h3>{_screen_matches(recent_rows,'recent')}</div></div>", unsafe_allow_html=True)
        _screen_table_bundle = calculate_all_group_tables(tournament_id, tournament)
        screen_groups = _screen_table_bundle["groups"][:4]
        if screen_groups:
            st.markdown("### Tabeller")
            cols=st.columns(min(2,len(screen_groups)))
            for idx,g in enumerate(screen_groups):
                table=_screen_table_bundle["tables"].get(int(g["id"]), [])
                rows=[data for _team_id,data in table]
                with cols[idx % len(cols)]:
                    st.markdown(f"**{html.escape(g['name'])}**")
                    if rows: st.dataframe(pd.DataFrame(rows)[['Lag','S','MS','P']], hide_index=True, use_container_width=True)
        sponsors=all_rows("SELECT * FROM sponsors WHERE tournament_id=? AND active=1 ORDER BY sort_order,id LIMIT 8", (tournament_id,))
        if sponsors:
            st.caption("Partners: " + " · ".join(s['name'] for s in sponsors))
        return
    filtered_public_matches = published_matches
    next_match = next(
        (
            m for m in filtered_public_matches
            if datetime.fromisoformat(m["scheduled_start"]) >= now and m["home_score"] is None
        ),
        None,
    )
    public_lifecycle = normalize_status(
        _row_value(tournament, "lifecycle_status", None),
        is_published=bool(tournament["is_published"]),
    )
    if public_lifecycle == "completed":
        _hero_status = "<span class='cn-hero-status completed'>🏆 Avslutad</span>"
    elif public_lifecycle == "live":
        _hero_status = "<span class='cn-hero-status live'>● Pågår</span>"
    else:
        _hero_status = "<span class='cn-hero-status upcoming'>Kommande</span>"

    hero_meta = f"{cup_date_label(tournament)} · {html.escape(tournament['location'] or 'Spelort ej angiven')}"
    st.markdown(
        f"""<div class='cup-hero'><div class='eyebrow'>CupNavi · {html.escape(tr("Turneringsöversikt"))}</div>
        <div class='cn-hero-title-row'><div class='title'>{html.escape(tournament['name'])}</div>{_hero_status}</div>
        <div class='meta'>{hero_meta} · {html.escape(str(_row_value(tournament, 'sport', 'Fotboll')))}</div></div>""",
        unsafe_allow_html=True,
    )

    # Min cup: lagvalet ligger även i URL:en så länken kan bokmärkas/delas och
    # fungerar utan konto. Session state gör växlingen snabb under samma besök.
    team_query = st.query_params.get("team") if hasattr(st, "query_params") else None
    pitch_query = st.query_params.get("pitch") if hasattr(st, "query_params") else None
    try:
        requested_team_id = int(team_query) if team_query else None
    except (TypeError, ValueError):
        requested_team_id = None
    try:
        requested_pitch_no = int(pitch_query) if pitch_query else None
    except (TypeError, ValueError):
        requested_pitch_no = None
    if requested_team_id not in public_team_names:
        requested_team_id = None

    # Kompakt delning direkt kopplad till cupheadern. Popovern ersätter den gamla
    # fragment/container-raden som reserverade vertikal höjd även när panelen var stängd.
    share_url = public_cup_url(tournament_id)
    share_text = f"{tr('Följ cupen')}: {tournament['name']} – {share_url}"
    whatsapp_href = "https://wa.me/?text=" + quote(share_text)
    email_href = "mailto:?subject=" + quote(f"CupNavi – {tournament['name']}") + "&body=" + quote(share_text)
    sms_href = "sms:?&body=" + quote(share_text)

    st.markdown(
        """<style>
        .cn-share-inline-anchor{height:0;margin:0;padding:0}
        .cn-share-inline-anchor + div{
          position:relative!important;
          z-index:30!important;
          width:max-content!important;
          margin:-40px 12px 6px auto!important;
        }
        .cn-share-inline-anchor + div button{
          min-height:30px!important;
          padding:3px 9px!important;
          border-radius:8px!important;
          border:1px solid rgba(255,255,255,.42)!important;
          background:rgba(255,255,255,.14)!important;
          color:#ffffff!important;
          font-size:.76rem!important;
          font-weight:800!important;
          box-shadow:none!important;
        }
        .cn-share-inline-anchor + div button:hover{
          background:rgba(255,255,255,.24)!important;
          border-color:rgba(255,255,255,.72)!important;
        }
        @media(max-width:760px){
          .cn-share-inline-anchor + div{
            margin:-38px 8px 5px auto!important;
          }
          .cn-share-inline-anchor + div button{
            min-height:32px!important;
          }
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='cn-share-inline-anchor'></div>", unsafe_allow_html=True)
    with st.popover("Dela", help=tr("Dela cupen")):
        st.markdown("<span class='cn-share-popover-marker'></span>", unsafe_allow_html=True)
        st.markdown(f"### {tr('Dela cupen')}")
        st.caption(tr("Dela länken eller QR-koden till den här cupen."))
        st.code(share_url, language=None)
        share_col1, share_col2, share_col3 = st.columns(3)
        share_col1.link_button("WhatsApp", whatsapp_href, use_container_width=True)
        share_col2.link_button(tr("E-post"), email_href, use_container_width=True)
        share_col3.link_button("SMS", sms_href, use_container_width=True)
        share_qr = qr_png_bytes(share_url)
        if share_qr:
            st.markdown("#### QR-kod")
            qr_col1, qr_col2 = st.columns([1, 2], vertical_alignment="center")
            qr_col1.image(share_qr, width=120)
            with qr_col2:
                st.caption("Skanna koden för att öppna den publika cupsidan.")
                st.download_button(
                    tr("Ladda ner QR-kod"),
                    data=share_qr,
                    file_name=f"cupnavi-{int(tournament_id)}-qr.png",
                    mime="image/png",
                    key=f"cn_share_qr_download_{int(tournament_id)}",
                    use_container_width=True,
                )
        st.caption("Länken går till den publika cupsidan och kräver ingen inloggning.")

    # v143: mobil först – "Följ mitt lag" är en personlig cupyta, inte bara ett filter.
    st.markdown(
        """<style>
        .cn-follow-shell{border:1px solid #dce6e1;border-radius:20px;background:#fff;
          padding:16px 18px;margin:8px 0 14px;box-shadow:0 8px 24px rgba(15,23,42,.05)}
        .cn-follow-kicker{font-size:.78rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#15733c}
        .cn-follow-team{font-size:1.45rem;font-weight:850;color:#142033;margin:2px 0 10px}
        .cn-next-card{border-radius:18px;background:#f5fbf7;border:1px solid #cfe5d7;padding:16px;margin-top:8px}
        .cn-next-meta{font-size:.83rem;font-weight:750;color:#51606d;margin-bottom:8px}
        .cn-next-teams{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px;
          font-size:1.06rem;font-weight:800;color:#152033}
        .cn-next-teams .away{text-align:right}.cn-next-vs{color:#6b7785;font-size:.85rem}
        .cn-follow-mini{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px}
        .cn-follow-mini>div{border:1px solid #e2e8ec;border-radius:14px;padding:10px;background:#fbfcfd}
        .cn-follow-mini span{display:block;color:#73808d;font-size:.75rem}.cn-follow-mini strong{font-size:1rem;color:#172033}
        .cn-live-strip{margin:12px 0 18px}
        .cn-live-head{display:flex;align-items:center;justify-content:space-between;gap:12px;border:1px solid #fecaca;background:linear-gradient(135deg,#fff7f7,#fff);border-radius:16px;padding:13px 15px;margin-bottom:10px}
        .cn-live-head-left{display:flex;align-items:center;gap:10px}
        .cn-live-dot{width:10px;height:10px;border-radius:50%;background:#ef4444;box-shadow:0 0 0 5px rgba(239,68,68,.10)}
        .cn-live-title{font-size:.76rem;font-weight:900;letter-spacing:.08em;color:#b91c1c;text-transform:uppercase}
        .cn-live-subtitle{font-size:.82rem;color:#64748b;margin-top:2px}
        .cn-live-status{font-size:.72rem;font-weight:800;color:#b91c1c;background:#fff;border:1px solid #fecaca;border-radius:999px;padding:5px 8px;white-space:nowrap}
        .cn-live-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
        .cn-live-card{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:13px 14px;box-shadow:0 5px 16px rgba(15,23,42,.055);min-width:0}
        .cn-live-card-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}
        .cn-live-time{font-size:1rem;font-weight:900;color:#166534}
        .cn-live-date{font-size:.72rem;color:#64748b;margin-top:1px}
        .cn-live-pitch{font-size:.75rem;font-weight:800;color:#475569;background:#f8fafc;border:1px solid #e2e8f0;border-radius:999px;padding:5px 8px;white-space:nowrap}
        .cn-live-teams{font-size:.91rem;font-weight:820;color:#172033;line-height:1.35}
        .cn-live-vs{color:#94a3b8;font-weight:750;padding:0 3px}
        .cn-live-card.is-live{border-color:#fecaca;background:linear-gradient(180deg,#fff,#fff7f7)}
        .cn-live-card.is-live .cn-live-time{color:#b91c1c}

                .cn-public-main-nav-note{font-size:12px;color:#64748b;margin:2px 0 6px}
.cn-public-follow-anchor{height:0;margin:0;padding:0}
        @media(min-width:901px){
          .cn-public-follow-anchor + div{margin-top:0!important;margin-bottom:2px!important}
@media(max-width:900px){.cn-live-grid{grid-template-columns:1fr}.cn-live-head{align-items:flex-start}.cn-live-status{display:none}}
        .cn-my-status{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.cn-my-pill{border:1px solid #dbe5df;border-radius:999px;padding:6px 10px;background:#f8fbf9;font-size:.8rem;font-weight:750}
        .cn-venue-card{border:1px solid #e2e8f0;border-radius:14px;padding:11px 12px;margin:7px 0;background:#fff}

        /* v166: tighter desktop rhythm. */
        @media(min-width:901px){
          .stApp .block-container{padding-top:.75rem!important;padding-bottom:1.5rem!important}
          .cn-flow-context{margin-top:0!important;margin-bottom:5px!important;padding:9px 12px!important}
          .cn-next-action{margin:0!important;padding:7px 10px!important}

        @media(min-width:901px){
          .cn-next-action{min-height:44px!important;display:flex;align-items:center;gap:8px}
          .cn-next-action br{display:none}
        }
          hr{margin:.7rem 0!important}
          [data-testid="stAlert"]{margin-top:.3rem!important;margin-bottom:.45rem!important}
          [data-testid="stVerticalBlock"]{gap:.42rem!important}
        }

        /* v162: publika desktopvyn använder bredden bättre och minskar dubblerad höjd. */
        @media(min-width:901px){
          .cup-hero{padding:13px 18px!important;margin:0 0 7px!important;border-radius:14px!important}
          .cup-hero .title{font-size:28px!important;margin:2px 0 3px!important}
          .cup-hero .meta{font-size:13px!important}
          .cn-live-strip{margin:5px 0 7px!important}
          .cn-live-head{padding:10px 13px!important;margin-bottom:8px!important}
          .cn-live-card{padding:10px 12px!important;border-radius:13px!important}
          .cn-live-card-top{margin-bottom:6px!important}
          .public-metric-grid{display:flex!important;gap:8px!important;margin:6px 0 10px!important}
          .public-metric{min-height:auto!important;padding:8px 11px!important;border-radius:10px!important;display:flex!important;align-items:baseline!important;gap:8px!important;flex:0 0 auto!important}
          .public-metric .label{font-size:12px!important;margin:0!important}
          .public-metric .value{font-size:18px!important}
          .cn-public-follow-anchor + div [data-testid="stSelectbox"]{margin-bottom:0!important}
          .cn-public-follow-anchor + div [data-testid="stSelectbox"] label{font-size:12px!important}
          .public-match-card{margin:7px 0!important;padding:10px 12px!important;border-radius:12px!important}
          .public-match-card .public-team-name{font-size:15px!important}
          .public-match-card .match-score{font-size:18px!important}
          .public-match-card .match-meta{font-size:12px!important}
          .public-match-card .kit-label{font-size:10px!important}
          .public-match-card .match-weather,.public-match-card .match-referee{font-size:11px!important;margin-top:6px!important}
          .public-match-card .cn-match-events{margin-top:6px!important;padding-top:6px!important}
          .public-match-card .cn-event-team{padding:5px!important}
          .public-match-card .cn-event{font-size:11px!important;padding:3px 6px!important}
        }

        @media(max-width:760px){
          .cn-follow-shell{padding:14px;margin-top:4px;border-radius:16px}
          .cn-follow-team{font-size:1.22rem}
          .cn-next-card{padding:13px;border-radius:15px}
          .cn-next-teams{grid-template-columns:1fr auto 1fr;font-size:.98rem}
          .cn-follow-mini{grid-template-columns:1fr 1fr 1fr;gap:6px}
          .cn-follow-mini>div{padding:8px}
          [class*="st-key-public_favorite_team_"] label{font-size:.82rem!important}
        }
        </style>""",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='cn-public-follow-anchor'></div>", unsafe_allow_html=True)
    with st.container():
        _all_teams_value = "__all__"
        favorite_options = [_all_teams_value] + [row["id"] for row in public_teams]
        favorite_index = favorite_options.index(requested_team_id) if requested_team_id in favorite_options else 0
        _favorite_selection = st.selectbox(
            "⭐ Följ mitt lag",
            favorite_options,
            index=favorite_index,
            format_func=lambda team_id: tr("Alla lag") if team_id == _all_teams_value else public_team_names.get(team_id, "Lag"),
            key=f"public_favorite_team_{tournament_id}",
            help="Valet sparas i länken så cupen kan öppnas direkt med ditt lag.",
        )
        favorite_team_id = None if _favorite_selection == _all_teams_value else _favorite_selection
        if favorite_team_id is not None and favorite_team_id != requested_team_id:
            if hasattr(st, "query_params"):
                st.query_params["team"] = str(favorite_team_id)
                st.query_params["cup"] = str(tournament_id)
            st.rerun()
        if favorite_team_id is None and requested_team_id is not None:
            if hasattr(st, "query_params"):
                try:
                    del st.query_params["team"]
                except KeyError:
                    pass
                st.query_params["cup"] = str(tournament_id)
            st.rerun()

        if requested_team_id:
            favorite_matches = [
                m for m in published_matches
                if requested_team_id in (_public_source_team_id(m["home_source"]), _public_source_team_id(m["away_source"]))
            ]

            def _public_match_dt(match_row):
                value = _row_value(match_row, "scheduled_start", None)
                if not value:
                    return None
                try:
                    return datetime.fromisoformat(str(value))
                except (TypeError, ValueError):
                    return None

            favorite_matches = sorted(
                favorite_matches,
                key=lambda m: (_public_match_dt(m) is None, _public_match_dt(m) or datetime.max),
            )
            favorite_next = next(
                (
                    m for m in favorite_matches
                    if _row_value(m, "home_score", None) is None
                    and _row_value(m, "away_score", None) is None
                    and _public_match_dt(m) is not None
                    and _public_match_dt(m) >= now
                ),
                None,
            )
            favorite_latest = next(
                (
                    m for m in reversed(favorite_matches)
                    if _row_value(m, "home_score", None) is not None
                    and _row_value(m, "away_score", None) is not None
                ),
                None,
            )
            played_count = sum(
                1 for m in favorite_matches
                if _row_value(m, "home_score", None) is not None and _row_value(m, "away_score", None) is not None
            )
            wins = 0
            for m in favorite_matches:
                hs, aw = _row_value(m, "home_score", None), _row_value(m, "away_score", None)
                if hs is None or aw is None:
                    continue
                home_id = _public_source_team_id(m["home_source"])
                if (home_id == requested_team_id and hs > aw) or (home_id != requested_team_id and aw > hs):
                    wins += 1

            team_name = public_team_names.get(requested_team_id, "Lag")
            hero_html = (
                f"<div class='cn-follow-shell'><div class='cn-follow-kicker'>⭐ Mitt lag</div>"
                f"<div class='cn-follow-team'>{html.escape(team_name)}</div>"
            )
            if favorite_next:
                next_dt = _public_match_dt(favorite_next)
                minutes_until = max(0, int((next_dt-now).total_seconds()//60)) if next_dt else None
                if minutes_until is None:
                    relative_text = ""
                elif minutes_until < 60:
                    relative_text = f" · om {minutes_until} min"
                elif minutes_until < 24*60:
                    relative_text = f" · om {minutes_until//60} h {minutes_until%60:02d} min"
                else:
                    relative_text = ""
                hero_html += (
                    f"<div class='cn-next-card'><div class='cn-next-meta'>Nästa match · "
                    f"{html.escape(swedish_datetime(favorite_next['scheduled_start']))} · "
                    f"{html.escape(_public_pitch_label(favorite_next))}"
                    f"{html.escape(relative_text)}</div>"
                    f"<div class='cn-next-teams'><div>{html.escape(_public_source_label(favorite_next['home_source']))}</div>"
                    f"<div class='cn-next-vs'>VS</div>"
                    f"<div class='away'>{html.escape(_public_source_label(favorite_next['away_source']))}</div></div></div>"
                )
            else:
                hero_html += "<div class='cn-next-card'><div class='cn-next-meta'>Ingen kommande match är schemalagd just nu.</div></div>"

            latest_text = "–"
            if favorite_latest:
                latest_text = f"{favorite_latest['home_score']}–{favorite_latest['away_score']}"

            table_position_text = "–"
            favorite_team_row = next((row for row in public_teams if int(row["id"]) == int(requested_team_id)), None)
            favorite_group_id = _row_value(favorite_team_row, "group_id", None) if favorite_team_row else None
            if favorite_group_id:
                try:
                    favorite_table = calculate_table(int(favorite_group_id), tournament)
                    favorite_position = next((idx for idx, (team_id, _) in enumerate(favorite_table, 1) if int(team_id) == int(requested_team_id)), None)
                    if favorite_position:
                        table_position_text = f"{favorite_position}:a"
                except Exception:
                    pass
            possible_playoff = next(
                (m for m in published_matches
                 if _row_value(m, "stage", "Gruppspel") != "Gruppspel"
                 and requested_team_id in (_public_source_team_id(m["home_source"]), _public_source_team_id(m["away_source"]))
                 and _row_value(m, "home_score", None) is None and _row_value(m, "away_score", None) is None),
                None,
            )
            hero_html += (
                "<div class='cn-follow-mini'>"
                f"<div><span>Matcher</span><strong>{len(favorite_matches)}</strong></div>"
                f"<div><span>Spelade</span><strong>{played_count}</strong></div>"
                f"<div><span>Senaste</span><strong>{html.escape(str(latest_text))}</strong></div>"
                "</div>"
                f"<div class='cn-my-status'><span class='cn-my-pill'>📊 Tabell: {html.escape(table_position_text)}</span>"
                + (
                    f"<span class='cn-my-pill'>🏆 {html.escape(str(_row_value(possible_playoff,'stage','Slutspel')))} · {html.escape(swedish_datetime(possible_playoff['scheduled_start']))}</span>"
                    if possible_playoff and _row_value(possible_playoff, "scheduled_start", None) else
                    "<span class='cn-my-pill'>🏆 Slutspel: inväntar kvalificering</span>"
                )
                + "</div></div>"
            )
            st.markdown(hero_html, unsafe_allow_html=True)

            team_action_1, team_action_2 = st.columns(2)
            if favorite_next:
                favorite_pitch_no = _row_value(favorite_next, "pitch_number", None)
                favorite_pitch_name = pitch_label(tournament_id, favorite_pitch_no) if favorite_pitch_no else None
                venue_direction = one_row(
                    """SELECT url,label FROM venue_points
                       WHERE tournament_id=? AND kind='Plan' AND url IS NOT NULL AND TRIM(url)<>''
                         AND (LOWER(label)=LOWER(?) OR LOWER(label)=LOWER(?))
                       ORDER BY id LIMIT 1""",
                    (tournament_id, str(favorite_pitch_name or ""), f"Plan {favorite_pitch_no}" if favorite_pitch_no else ""),
                )
                if venue_direction:
                    st.link_button(f"📍 Vägbeskrivning till {venue_direction['label']}", venue_direction["url"], use_container_width=True)
            if team_action_1.button("🗓️ Visa mitt lags matcher", key=f"favorite_matches_btn_{tournament_id}", use_container_width=True, type="primary"):
                st.session_state[f"public_force_team_filter_{tournament_id}"] = requested_team_id
                st.session_state[f"public_page_v92_{tournament_id}"] = "Matcher"
                st.rerun()
            if team_action_2.button(tr("Visa alla lag"), key=f"clear_favorite_team_{tournament_id}", use_container_width=True):
                if hasattr(st, "query_params"):
                    try:
                        del st.query_params["team"]
                    except KeyError:
                        pass
                st.rerun()

            with st.expander("🔔 Få viktiga lagnotiser via e-post", expanded=False):
                st.caption("E-postadressen måste verifieras innan några notiser skickas.")
                with st.form(f"public_notification_subscribe_{tournament_id}_{requested_team_id}"):
                    notify_email = st.text_input("E-post", key=f"notify_email_{tournament_id}_{requested_team_id}")
                    nc1, nc2, nc3 = st.columns(3)
                    notify_schedule = nc1.checkbox("Matchtid/plan", value=True)
                    notify_results = nc2.checkbox("Resultat", value=True)
                    notify_messages = nc3.checkbox("Arrangörsinfo", value=True)
                    consent = st.checkbox("Jag vill få CupNavi-notiser för detta lag och kan avsluta dem via länken i varje mejl.")
                    if st.form_submit_button("Skicka verifieringsmejl", type="primary", use_container_width=True):
                        if not consent:
                            st.error("Godkänn prenumerationen först.")
                        else:
                            try:
                                ok, error = create_notification_subscription(
                                    tournament_id, requested_team_id, notify_email,
                                    notify_schedule=notify_schedule, notify_results=notify_results, notify_messages=notify_messages,
                                )
                                if ok:
                                    st.success("Verifieringsmejl skickat. Öppna länken i mejlet för att aktivera notiser.")
                                else:
                                    st.error(f"Prenumerationen sparades men verifieringsmejlet kunde inte skickas: {error}")
                            except ValueError as exc:
                                st.error(str(exc))

            notification_rows = all_rows(
                """SELECT * FROM notifications WHERE tournament_id=? AND (team_id=? OR team_id IS NULL)
                   ORDER BY created_at DESC,id DESC LIMIT 5""",
                (tournament_id, requested_team_id),
            )
            if notification_rows:
                with st.expander(f"🔔 Viktigt för {team_name} ({len(notification_rows)})", expanded=False):
                    for note in notification_rows:
                        st.markdown(f"**{note['title']}**  \n{note['message']}")
                        st.caption(note["created_at"].replace("T", " "))
            st.caption("Bokmärk sidan – lagvalet ligger i länken och följer med nästa gång.")
        else:
            pass

    public_page_key = f"public_page_v167_{tournament_id}"
    requested_section = str(st.query_params.get("section", "")) if hasattr(st, "query_params") else ""
    public_page = resolve_public_page(
        requested_section,
        st.session_state.get(public_page_key),
    )
    st.session_state[public_page_key] = public_page

    st.markdown("<div class='cn-public-top-nav'></div>", unsafe_allow_html=True)
    nav_specs = public_navigation_specs()
    nav_columns = st.columns(len(nav_specs))
    for nav_col, (page_value, _section, desktop_label, _mobile_label) in zip(nav_columns, nav_specs):
        label = tr(desktop_label) if desktop_label != "Cupinfo" else "Cupinfo"
        active = public_page == page_value
        if nav_col.button(
            label,
            key=f"public_nav_v144_{tournament_id}_{page_value}",
            type="primary" if active else "secondary",
            use_container_width=True,
        ):
            st.session_state[public_page_key] = page_value
            if hasattr(st, "query_params"):
                st.query_params["cup"] = str(_row_value(tournament, "public_slug", tournament_id) or tournament_id)
                st.query_params["section"] = public_section_for_page(page_value)
                if requested_team_id:
                    st.query_params["team"] = str(requested_team_id)
            st.rerun()

    # Page-specific UI must only be evaluated after public_page is resolved.
    screen_url = public_cup_url(tournament_id) + ("&" if "?" in public_cup_url(tournament_id) else "?") + "screen=1"
    if public_page == "Info":
        st.markdown(
            f"<div style='text-align:right;margin:-4px 0 8px'><a class='cn-screen-link' href='{html.escape(screen_url, quote=True)}'>🖥 Informationsskärm</a></div>",
            unsafe_allow_html=True,
        )

    cup_key = quote(str(_row_value(tournament, "public_slug", tournament_id) or tournament_id))
    team_query = "&team=" + str(requested_team_id) if requested_team_id else ""
    mobile_links = []
    for page_value, section, _desktop_label, mobile_label in public_navigation_specs():
        active_class = "active" if public_page == page_value else ""
        mobile_links.append(
            f"<a class='{active_class}' href='?cup={cup_key}&section={section}{team_query}'><span>{html.escape(mobile_label)}</span></a>"
        )
    st.markdown(
        "<nav class='cn-mobile-bottom-nav' aria-label='Cup navigation'>"
        + "".join(mobile_links)
        + "</nav>",
        unsafe_allow_html=True,
    )

    def _filter_public_matches(base_matches, key_prefix, heading):
        return render_public_match_filters_module(
            base_matches,
            key_prefix,
            heading,
            tournament_id=tournament_id,
            tr=tr,
            public_teams=public_teams,
            public_team_names=public_team_names,
            load_public_groups=_load_public_groups,
            source_team_id=_public_source_team_id,
            row_value=_row_value,
            filter_matches=filter_matches,
            sort_public_matches=sort_public_matches,
        )


    def _render_public_match_cards(matches, show_results=None, show_weather=False, events_by_match=None):
        return render_public_match_cards_module(
            matches,
            tournament=tournament,
            show_results=show_results,
            show_weather=show_weather,
            events_by_match=events_by_match,
            row_value=_row_value,
            fetch_weather_forecast=fetch_weather_forecast,
            public_team_by_id=public_team_by_id,
            public_team_names=public_team_names,
            public_source_team_id=_public_source_team_id,
            public_source_label=_public_source_label,
            swedish_datetime=swedish_datetime,
            weather_for_match=weather_for_match,
            weather_label=weather_label,
            match_kit_colors=match_kit_colors,
            kit_background_for_team=kit_background_for_team,
            public_match_events_html=public_match_events_html,
            public_pitch_label=_public_pitch_label,
            public_referee_label=_public_referee_label,
            render_empty_state=render_empty_state,
            now=now,
        )


    if public_page == "Matcher":
        @st.fragment
        def render_public_matches_fragment():
            _fragment_started = time.perf_counter()
            _db_calls_before = _PERF["db_calls"]
            _db_ms_before = _PERF["db_ms"]
            # Matcher-specifika summeringar beräknas först när sidan öppnas.
            team_count = len(public_teams)
            total_goals = sum(
                int(m["home_score"] or 0) + int(m["away_score"] or 0)
                for m in played_matches
            )
            public_events_by_match = {}

            _live_now, _next_matches, _recent_results = classify_public_match_feed(
                published_matches,
                now=now,
                match_duration_minutes=match_duration_minutes(tournament),
            )
            _feed_summary = public_match_feed_summary(_live_now, _next_matches)
            if _feed_summary["items"]:
                _live_items = _feed_summary["items"]
                _is_live_mode = _feed_summary["is_live"]
                _head_title = _feed_summary["title"]
                _head_subtitle = _feed_summary["subtitle"]
                _head_status = _feed_summary["status"]
                _live_cards = []
                for _m in _live_items:
                    try:
                        _dt = datetime.fromisoformat(str(_row_value(_m, "scheduled_start", "")))
                        _time_text = _dt.strftime("%H:%M")
                        _date_text = _dt.strftime("%a %d %b").replace("Mon","Mån").replace("Tue","Tis").replace("Wed","Ons").replace("Thu","Tors").replace("Fri","Fre").replace("Sat","Lör").replace("Sun","Sön")
                    except (TypeError, ValueError):
                        _time_text, _date_text = "–", ""
                    _home = html.escape(_public_source_label(_m["home_source"]))
                    _away = html.escape(_public_source_label(_m["away_source"]))
                    _pitch = html.escape(_public_pitch_label(_m))
                    _card_class = "cn-live-card is-live" if _is_live_mode else "cn-live-card"
                    _live_cards.append(
                        f"<div class='{_card_class}'>"
                        f"<div class='cn-live-card-top'><div><div class='cn-live-time'>{html.escape(_time_text)}</div>"
                        f"<div class='cn-live-date'>{html.escape(_date_text)}</div></div>"
                        f"<div class='cn-live-pitch'>📍 {_pitch}</div></div>"
                        f"<div class='cn-live-teams'>{_home}<span class='cn-live-vs'> – </span>{_away}</div>"
                        f"</div>"
                    )
                st.markdown(
                    f"<section class='cn-live-strip'>"
                    f"<div class='cn-live-head'><div class='cn-live-head-left'><span class='cn-live-dot'></span>"
                    f"<div><div class='cn-live-title'>{html.escape(_head_title)}</div>"
                    f"<div class='cn-live-subtitle'>{html.escape(_head_subtitle)}</div></div></div>"
                    f"<div class='cn-live-status'>{html.escape(_head_status)}</div></div>"
                    f"<div class='cn-live-grid'>{''.join(_live_cards)}</div>"
                    f"</section>",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""<div class='public-metric-grid'>
                  <div class='public-metric'><div class='label'>{html.escape(tr("Lag"))}</div><div class='value'>{team_count}</div></div>
                  <div class='public-metric'><div class='label'>{html.escape(tr("Matcher spelade"))}</div><div class='value'>{len(played_matches)} {html.escape(tr("av"))} {len(published_matches)}</div></div>
                  <div class='public-metric'><div class='label'>{html.escape(str(sport_profile(_row_value(tournament, 'sport', 'Fotboll'))['score_label']).capitalize())}</div><div class='value'>{total_goals}</div></div>
                </div>""",
                unsafe_allow_html=True,
            )

            requested_match_view = str(st.query_params.get("matches", "all")) if hasattr(st, "query_params") else "all"
            requested_match_view = requested_match_view if requested_match_view in {"all", "upcoming", "played"} else "all"
            _match_view_labels = {
                "all": tr("Alla"),
                "upcoming": tr("Kommande"),
                "played": tr("Spelade"),
            }
            _match_key_by_label = {value: key for key, value in _match_view_labels.items()}
            match_view = st.segmented_control(
                tr("Visa matcher"),
                [tr("Alla"), tr("Kommande"), tr("Spelade")],
                default=_match_view_labels[requested_match_view],
                key=f"public_match_view_v144_{tournament_id}",
            ) or _match_view_labels[requested_match_view]
            _selected_match_view = _match_key_by_label.get(match_view, "all")

            if _selected_match_view != requested_match_view and hasattr(st, "query_params"):
                st.query_params["matches"] = _selected_match_view
                st.query_params["section"] = "matches"
                st.query_params["cup"] = str(_row_value(tournament, "public_slug", tournament_id) or tournament_id)
                if requested_team_id:
                    st.query_params["team"] = str(requested_team_id)

            if _selected_match_view == "upcoming":
                base_match_list = [m for m in published_matches if m["home_score"] is None or m["away_score"] is None]
            elif _selected_match_view == "played":
                base_match_list = played_matches
            else:
                base_match_list = published_matches

            if _selected_match_view == "played" and not played_matches:
                st.info("Inga publicerade matcher har ett komplett resultat ännu.")

            if requested_team_id:
                base_match_list = [
                    m for m in base_match_list
                    if requested_team_id in (_public_source_team_id(m["home_source"]), _public_source_team_id(m["away_source"]))
                ]
                _follow_info_col, _follow_clear_col = st.columns([3, 1])
                _follow_info_col.info(f"⭐ Min cup visar matcher för {public_team_names[requested_team_id]}.")
                if _follow_clear_col.button("Visa hela cupen", key=f"public_clear_team_filter_v144_{tournament_id}", use_container_width=True):
                    if hasattr(st, "query_params"):
                        try:
                            del st.query_params["team"]
                        except KeyError:
                            pass
                        st.query_params["section"] = "matches"
                    st.rerun()

            if requested_pitch_no:
                base_match_list = [m for m in base_match_list if int(m["pitch_number"] or 0) == requested_pitch_no]
                st.info(f"📍 QR-länken visar Plan {requested_pitch_no}.")

            match_list, match_filter_mode, match_filter_label = _filter_public_matches(
                base_match_list,
                "public_matches",
                tr("Filtrera matcher"),
            )
            st.caption(f"{tr('Visar')} {len(match_list)} {tr('matcher').lower()} · {match_filter_label}")

            # Load match events only for visible played matches. The previous
            # implementation fetched all scoring/red-card rows for the entire
            # tournament even when the user viewed only upcoming fixtures.
            visible_played_match_ids = [
                int(_row_value(match_row, "id", 0) or 0)
                for match_row in match_list
                if (
                    _row_value(match_row, "home_score", None) is not None
                    and _row_value(match_row, "away_score", None) is not None
                    and int(_row_value(match_row, "id", 0) or 0) > 0
                )
            ]
            public_events_by_match = {}
            if visible_played_match_ids:
                event_placeholders = ",".join("?" for _ in visible_played_match_ids)
                public_event_rows = all_rows(
                    f"""
                    SELECT s.match_id, p.name AS player_name, COALESCE(p.is_protected,0) AS is_protected,
                           t.id AS team_id, t.name AS team_name, s.goals, s.red_cards
                    FROM player_match_stats s
                    JOIN players p ON p.id=s.player_id
                    JOIN teams t ON t.id=p.team_id
                    WHERE s.match_id IN ({event_placeholders})
                      AND (s.goals > 0 OR s.red_cards > 0)
                    ORDER BY s.match_id,p.name
                    """,
                    tuple(visible_played_match_ids),
                )
                for event_row in public_event_rows:
                    public_events_by_match.setdefault(event_row["match_id"], []).append(event_row)

            def _safe_public_start(match_row):
                value = _row_value(match_row, "scheduled_start", None)
                if not value:
                    return None
                try:
                    return datetime.fromisoformat(str(value))
                except (TypeError, ValueError):
                    return None

            # v162: Cupen just nu ovan är den enda primära "nästa match"-ytan.
            # Vi undviker ett andra stort hero-kort som duplicerar samma information.
            show_match_weather = st.toggle(
                "🌦️ " + tr("Visa väderprognos"),
                value=True,
                key=f"public_matches_weather_{tournament_id}",
            )
            _render_public_match_cards(
                match_list,
                show_results=None,
                show_weather=show_match_weather,
                events_by_match=public_events_by_match,
            )

            _elapsed_ms = (time.perf_counter() - _fragment_started) * 1000
            st.session_state[f"_public_perf_matches_{tournament_id}"] = {
                "render_ms": round(_elapsed_ms, 1),
                "db_calls": _PERF["db_calls"] - _db_calls_before,
                "db_ms": round(_PERF["db_ms"] - _db_ms_before, 1),
            }

        render_public_matches_fragment()

    if public_page == "Tabeller":
        render_public_statistics_section(
            tournament_id, tournament, published_matches, played_matches,
            forced_section=tr("Tabeller"),
        )

    if public_page == "Slutspel":
        render_public_statistics_section(
            tournament_id, tournament, published_matches, played_matches,
            forced_section=tr("Slutspel"),
        )

    if public_page == "Statistik":
        render_public_statistics_section(
            tournament_id, tournament, published_matches, played_matches,
            forced_section=tr("Topplistor"),
        )

    if public_page == "Info":
        render_public_info_section(tournament_id, tournament, published_matches)

    # Icke-kritisk analytics sist: ett långsamt Turso-write ska inte fördröja
    # hero/navigation/matchinnehåll på den publika sidan.
    track_public_visit(tournament_id)


def render_match_reporter_view(tournament_id, tournament):
    """Begränsad arbetsyta: endast resultat och matchhändelser."""
    st.title(f"📝 Matchrapportör · {tournament['name']}")
    st.caption(
        "Här kan du endast rapportera resultat samt mål, assist, varningar och utvisningar. "
        "Övrig administration är inte tillgänglig."
    )

    result_tab, event_tab, referee_tab, offline_tab = st.tabs([
        tr("CupNavi Score"), tr("Matchhändelser"), tr("Domarcentral"), tr("Offlineutkast")
    ])

    with result_tab:
        matches = all_rows(
            """SELECT * FROM matches
               WHERE tournament_id=? AND scheduled_start IS NOT NULL
               ORDER BY scheduled_start,pitch_number,id""",
            (tournament_id,),
        )
        playable_matches = select_playable_matches(
            matches,
            resolve_source=resolve_source,
        )

        if "reporter_result_message" in st.session_state:
            st.success(st.session_state.pop("reporter_result_message"), icon="✅")
        if "reporter_conflict_message" in st.session_state:
            st.warning(st.session_state.pop("reporter_conflict_message"))

        if not playable_matches:
            st.info("Det finns ännu inga schemalagda matcher med två klara lag.")
        else:
            st.markdown("### ⚡ CupNavi Score")
            quick_match_id = st.selectbox(
                "Välj match för snabbresultat",
                [row["id"] for row in playable_matches],
                format_func=lambda match_id: match_result_label(next(row for row in playable_matches if row["id"] == match_id)),
                key=f"quick_score_match_{tournament_id}",
            )
            quick_match = next(row for row in playable_matches if row["id"] == quick_match_id)
            quick_home_name = source_label(quick_match["home_source"])
            quick_away_name = source_label(quick_match["away_source"])
            draft_key = f"quick_score_draft_{quick_match_id}"
            if draft_key not in st.session_state:
                st.session_state[draft_key] = [int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)]
            quick_home_score, quick_away_score = st.session_state[draft_key]
            qh, qc, qa = st.columns([2, 1, 2])
            qh.markdown(f"**{quick_home_name}**")
            qa.markdown(f"**{quick_away_name}**")
            qh_minus, qh_plus = qh.columns(2)
            qa_minus, qa_plus = qa.columns(2)
            if qh_minus.button("−", key=f"qs_hm_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][0] = max(0, quick_home_score - 1); st.rerun()
            if qh_plus.button("+", key=f"qs_hp_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][0] = quick_home_score + 1; st.rerun()
            if qa_minus.button("−", key=f"qs_am_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][1] = max(0, quick_away_score - 1); st.rerun()
            if qa_plus.button("+", key=f"qs_ap_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key][1] = quick_away_score + 1; st.rerun()
            qc.markdown(
                f"<div style='text-align:center;font-size:30px;font-weight:900;padding-top:8px'>{quick_home_score}–{quick_away_score}</div>",
                unsafe_allow_html=True,
            )
            save_col, reset_col = st.columns(2)
            playoff_tie_needs_detail = quick_match["stage"] != "Gruppspel" and quick_home_score == quick_away_score
            if save_col.button(
                "✅ Spara slutresultat", key=f"qs_save_{quick_match_id}", type="primary", use_container_width=True,
                disabled=playoff_tie_needs_detail,
            ):
                before = result_snapshot(quick_match)
                with db() as con:
                    _quick_saved = update_match_result_if_unchanged(
                        con,
                        quick_match_id,
                        before,
                        home_score=quick_home_score,
                        away_score=quick_away_score,
                        home_penalties=quick_match["home_penalties"],
                        away_penalties=quick_match["away_penalties"],
                        decided_winner_id=quick_match["decided_winner_id"],
                        referee_id=quick_match["referee_id"],
                    )
                    if _quick_saved:
                        con.commit()
                if not _quick_saved:
                    st.error(
                        "Resultatet ändrades av en annan användare innan du hann spara. "
                        "Sidan laddas om så att du ser det senaste resultatet."
                    )
                    st.session_state.pop(draft_key, None)
                    st.rerun()
                description = f"{quick_home_name}–{quick_away_name} {quick_home_score}–{quick_away_score}"
                record_audit(tournament_id, "result", "match", description, entity_id=quick_match_id, before=before,
                             after={"home_score": quick_home_score, "away_score": quick_away_score}, actor="Matchrapportör")
                add_feed_item(tournament_id, f"Slut: {description}", category="Resultat", related_match_id=quick_match_id)
                for team_id in _match_team_ids(quick_match):
                    add_team_notification(tournament_id, team_id, "Nytt resultat", description, event_key=f"result:{quick_match_id}:{quick_home_score}:{quick_away_score}")
                st.session_state["reporter_result_message"] = "Slutresultatet är sparat."
                st.rerun()
            if reset_col.button("Återställ utkast", key=f"qs_reset_{quick_match_id}", use_container_width=True):
                st.session_state[draft_key] = [int(quick_match["home_score"] or 0), int(quick_match["away_score"] or 0)]; st.rerun()
            if playoff_tie_needs_detail:
                st.info("Oavgjord slutspelsmatch behöver avgörande uppgifter. Använd tabellen nedan för straffar/lottning.")
            st.divider()
            st.caption("Tabellen nedan finns kvar för massinmatning och slutspelsavgöranden.")

            team_rows = all_rows(
                "SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name",
                (tournament_id,),
            )
            team_name_by_id = {row["id"]: row["name"] for row in team_rows}
            team_id_by_name = {row["name"]: row["id"] for row in team_rows}
            decision_options = ["–"] + [row["name"] for row in team_rows]

            result_rows = build_bulk_result_rows(
                playable_matches,
                source_label=source_label,
                swedish_datetime=swedish_datetime,
                team_name_by_id=team_name_by_id,
            )

            edited_results = st.data_editor(
                pd.DataFrame(result_rows),
                hide_index=True,
                use_container_width=True,
                disabled=["match_id", "Match", "Plan", "Fas", "Hemmalag", "Bortalag"],
                column_order=[
                    "Match", "Plan", "Fas", "Hemmalag", "Hemmamål",
                    "Bortamål", "Bortalag", "Hemmastraffar",
                    "Bortastraffar", "Avgörande vinnare",
                ],
                column_config={
                    "Hemmamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Bortamål": st.column_config.NumberColumn(min_value=0, max_value=99, step=1),
                    "Hemmastraffar": st.column_config.NumberColumn(
                        "Straffar hemma", min_value=0, max_value=99, step=1
                    ),
                    "Bortastraffar": st.column_config.NumberColumn(
                        "Straffar borta", min_value=0, max_value=99, step=1
                    ),
                    "Avgörande vinnare": st.column_config.SelectboxColumn(options=decision_options),
                },
                key=f"reporter_results_{tournament_id}",
            )

            original_by_id = {int(row["id"]): row for row in playable_matches}
            updates = []
            info_messages = []
            error_messages = []

            for _, row in edited_results.iterrows():
                match_id = int(row["match_id"])
                original = original_by_id[match_id]
                prepared = prepare_bulk_result_update(
                    row,
                    original,
                    team_id_by_name=team_id_by_name,
                    playoff_tie_rule=tournament["playoff_tie_rule"],
                    is_na=pd.isna,
                )
                info_messages.extend(prepared["info"])
                error_messages.extend(prepared["errors"])
                if prepared["update"] is not None:
                    updates.append(prepared["update"])

            for message in error_messages:
                st.error(message)
            for message in info_messages:
                st.info(message)

            if updates:
                _reporter_saved = []
                _reporter_conflicts = []
                with db() as con:
                    for update in updates:
                        saved = update_match_result_if_unchanged(
                            con,
                            update["match_id"],
                            update["expected"],
                            home_score=update["home_score"],
                            away_score=update["away_score"],
                            home_penalties=update["home_penalties"],
                            away_penalties=update["away_penalties"],
                            decided_winner_id=update["decided_winner_id"],
                            referee_id=update["referee_id"],
                        )
                        (_reporter_saved if saved else _reporter_conflicts).append(update)
                    con.commit()
                _clear_render_query_cache()
                for update in _reporter_saved:
                    home_score = update["home_score"]
                    away_score = update["away_score"]
                    home_penalties = update["home_penalties"]
                    away_penalties = update["away_penalties"]
                    changed_match_id = update["match_id"]
                    if home_score is None or away_score is None:
                        continue
                    changed_match = original_by_id[changed_match_id]
                    description = f"{source_label(changed_match['home_source'])}–{source_label(changed_match['away_source'])} {home_score}–{away_score}"
                    if home_penalties is not None and away_penalties is not None:
                        description += f" ({home_penalties}–{away_penalties} str.)"
                    add_feed_item(tournament_id, f"Slut: {description}", category="Resultat", related_match_id=changed_match_id)
                    for team_id in _match_team_ids(changed_match):
                        add_team_notification(tournament_id, team_id, "Nytt resultat", description,
                                              event_key=f"result:{changed_match_id}:{home_score}:{away_score}:{home_penalties}:{away_penalties}")
                st.session_state["_validation_dirty"] = True
                if _reporter_saved:
                    st.session_state["reporter_result_message"] = "Sparat automatiskt"
                if _reporter_conflicts:
                    st.session_state["reporter_conflict_message"] = (
                        f"{len(_reporter_conflicts)} match(er) hade ändrats av en annan rapportör och skrevs inte över. "
                        "De senaste värdena har laddats om."
                    )
                st.rerun()

            st.caption("✓ Kompletta resultat sparas automatiskt.")

    with event_tab:
        played_matches = all_rows(
            """SELECT * FROM matches
               WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL
               ORDER BY scheduled_start DESC,id DESC""",
            (tournament_id,),
        )
        playable_matches = select_playable_matches(
            played_matches,
            resolve_source=resolve_source,
        )

        if not playable_matches:
            st.info("Rapportera först ett matchresultat. Därefter kan matchhändelser registreras.")
        else:
            match_id = st.selectbox(
                "Välj match",
                [row["id"] for row in playable_matches],
                format_func=lambda selected_id: match_result_label(
                    next(row for row in playable_matches if row["id"] == selected_id)
                ),
                key=f"reporter_event_match_{tournament_id}",
            )
            match_row = next(row for row in playable_matches if row["id"] == match_id)
            home_team_id = resolve_source(match_row["home_source"])
            away_team_id = resolve_source(match_row["away_source"])

            for selected_team_id in [home_team_id, away_team_id]:
                selected_team = team(selected_team_id)
                registered_match_roster = all_rows(
                    """SELECT p.* FROM players p
                       JOIN match_rosters mr ON mr.player_id=p.id
                       WHERE mr.match_id=? AND mr.team_id=? AND p.team_id=?
                       ORDER BY p.player_number,p.name""",
                    (match_id, selected_team_id, selected_team_id),
                )
                players = registered_match_roster or all_rows(
                    "SELECT * FROM players WHERE team_id=? ORDER BY player_number,name",
                    (selected_team_id,),
                )
                st.markdown(f"#### {selected_team['name']}")
                if registered_match_roster:
                    st.caption(f"Matchtrupp registrerad · {len(registered_match_roster)} spelare. Endast dessa kan få matchhändelser.")
                elif players:
                    st.warning("Matchtrupp saknas. Alla spelare visas tills en matchtrupp registreras.")
                if not players:
                    st.warning("Laget saknar registrerade spelare.")
                    continue

                existing = {
                    row["player_id"]: row
                    for row in all_rows(
                        """SELECT * FROM player_match_stats
                           WHERE match_id=? AND player_id IN
                           (SELECT id FROM players WHERE team_id=?)""",
                        (match_id, selected_team_id),
                    )
                }

                data = pd.DataFrame([
                    {
                        "player_id": player["id"],
                        "Nr": player["player_number"],
                        "Spelare": player["name"],
                        "Mål": existing[player["id"]]["goals"] if player["id"] in existing else 0,
                        "Assist": existing[player["id"]]["assists"] if player["id"] in existing else 0,
                        "Varningar": existing[player["id"]]["yellow_cards"] if player["id"] in existing else 0,
                        "Utvisningar": existing[player["id"]]["red_cards"] if player["id"] in existing else 0,
                    }
                    for player in players
                ])

                reporter_columns = ["Nr", "Spelare", "Mål"]
                if bool(_row_value(tournament, "enable_assist_leaderboard", 1)):
                    reporter_columns.append("Assist")
                if bool(_row_value(tournament, "enable_card_statistics", 1)):
                    reporter_columns.extend(["Varningar", "Utvisningar"])
                edited = st.data_editor(
                    data,
                    hide_index=True,
                    use_container_width=True,
                    disabled=["player_id", "Nr", "Spelare"],
                    column_order=reporter_columns,
                    column_config={
                        "Mål": st.column_config.NumberColumn(min_value=0, step=1),
                        "Assist": st.column_config.NumberColumn(min_value=0, step=1),
                        "Varningar": st.column_config.NumberColumn(min_value=0, step=1),
                        "Utvisningar": st.column_config.NumberColumn(min_value=0, step=1),
                    },
                    key=f"reporter_stats_{match_id}_{selected_team_id}",
                )

                team_goals = int(
                    match_row["home_score"] if selected_team_id == home_team_id
                    else match_row["away_score"]
                )
                entered_goals = int(edited["Mål"].fillna(0).sum())
                entered_assists = int(edited["Assist"].fillna(0).sum())
                validation = validate_match_event_totals(
                    team_goals, entered_goals, entered_assists
                )
                for message in validation["errors"]:
                    st.error(f"{selected_team['name']}: {message}")

                autosave_key = f"reporter_event_saved_{match_id}_{selected_team_id}"
                if autosave_key in st.session_state:
                    st.success(st.session_state.pop(autosave_key), icon="✅")
                reporter_event_conflict_key = f"reporter_event_conflict_{match_id}_{selected_team_id}"
                if reporter_event_conflict_key in st.session_state:
                    st.warning(st.session_state.pop(reporter_event_conflict_key), icon="⚠️")

                if not validation["errors"]:
                    changed_rows = prepare_changed_event_rows(
                        (edited_row for _, edited_row in edited.iterrows()),
                        existing,
                        match_id=match_id,
                        is_na=pd.isna,
                    )

                    if changed_rows:
                        saved_rows = []
                        conflicted_rows = []
                        with db() as con:
                            for event_update in changed_rows:
                                saved = update_player_match_stats_if_unchanged(
                                    con,
                                    event_update["match_id"],
                                    event_update["player_id"],
                                    event_update["expected"],
                                    goals=event_update["goals"],
                                    assists=event_update["assists"],
                                    yellow_cards=event_update["yellow_cards"],
                                    red_cards=event_update["red_cards"],
                                )
                                (saved_rows if saved else conflicted_rows).append(event_update)
                            con.commit()
                        _clear_render_query_cache()
                        if conflicted_rows:
                            st.session_state[
                                f"reporter_event_conflict_{match_id}_{selected_team_id}"
                            ] = (
                                f"{len(conflicted_rows)} spelarrad(er) hade ändrats av en annan "
                                "rapportör och skrevs inte över. Senaste värden laddas om."
                            )
                        if saved_rows:
                            st.session_state[autosave_key] = "Sparat automatiskt"
                        st.rerun()

                st.caption(
                    f"Matchresultat: {team_goals} mål · registrerade spelarmål: {entered_goals} · "
                    f"registrerade assist: {entered_assists}"
                )

    with referee_tab:
        st.markdown("### 🧑‍⚖️ Domarcentral")
        st.caption("Domare kan se sitt dagsprogram och bekräfta att uppdraget är sett. Ingen adminnavigation visas här.")
        referee_rows = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tournament_id,))
        if not referee_rows:
            render_empty_state("Inga domare ännu", "Lägg till domare för att kunna använda automatisk domartillsättning.", "🧑‍⚖️")
        else:
            referee_id = st.selectbox(
                "Välj domare",
                [row["id"] for row in referee_rows],
                format_func=lambda rid: next(row["name"] for row in referee_rows if row["id"] == rid),
                key=f"reporter_referee_{tournament_id}",
            )
            assignments = all_rows(
                """SELECT * FROM matches WHERE tournament_id=? AND referee_id=? AND scheduled_start IS NOT NULL
                   ORDER BY scheduled_start,pitch_number,id""",
                (tournament_id, referee_id),
            )
            acked = {
                row["match_id"] for row in all_rows(
                    "SELECT match_id FROM referee_acknowledgements WHERE tournament_id=? AND referee_id=?",
                    (tournament_id, referee_id),
                )
            }
            if not assignments:
                st.info("Domaren har inga schemalagda matcher ännu.")
            for assignment in assignments:
                with st.container(border=True):
                    st.markdown(
                        f"**{swedish_datetime(assignment['scheduled_start'])} · Plan {assignment['pitch_number']}**  \n"
                        f"{source_label(assignment['home_source'])} – {source_label(assignment['away_source'])}"
                    )
                    if assignment["id"] in acked:
                        st.success("Uppdraget är bekräftat.", icon="✅")
                    elif st.button("Bekräfta att jag sett matchen", key=f"ref_ack_{referee_id}_{assignment['id']}", use_container_width=True):
                        run(
                            """INSERT INTO referee_acknowledgements(tournament_id,referee_id,match_id,acknowledged_at)
                               VALUES(?,?,?,?) ON CONFLICT(referee_id,match_id) DO NOTHING""",
                            (tournament_id, referee_id, assignment["id"], datetime.now().isoformat(timespec="seconds")),
                        )
                        record_audit(tournament_id, "referee_ack", "match", "Domaruppdrag bekräftat", entity_id=assignment["id"], actor="Domare")
                        st.rerun()

    with offline_tab:
        st.markdown("### 📶 Offlineutkast")
        st.caption(
            "Streamlit kräver serverkontakt för riktig synkronisering. Den här säkerhetsfunktionen sparar därför ett lokalt "
            "resultatutkast i webbläsaren om nätet blir dåligt. Utkastet ligger kvar på enheten och kan föras över till CupNavi Score när nätet återkommer."
        )
        offline_matches = all_rows(
            """SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id""",
            (tournament_id,),
        )
        offline_options = [
            {
                "id": int(row["id"]),
                "label": f"{swedish_datetime(row['scheduled_start'])} · Plan {row['pitch_number']} · {source_label(row['home_source'])} – {source_label(row['away_source'])}",
            }
            for row in offline_matches
        ]
        offline_html = f"""
        <style>body{{font-family:Arial,sans-serif;color:#172033;margin:0}} .box{{border:1px solid #cbd5e1;border-radius:14px;padding:14px;background:#fff}}
        select,input,button{{font-size:16px;padding:9px;border:1px solid #cbd5e1;border-radius:9px}} .scores{{display:flex;gap:8px;margin:12px 0;align-items:center}} input{{width:70px}} button{{cursor:pointer;background:#ecfdf5}} #status{{font-size:12px;color:#475569;margin-top:8px}}</style>
        <div class='box'><b>Lokalt resultatutkast</b><br><small>Data sparas endast i den här webbläsaren.</small><br><br>
        <select id='m'></select><div class='scores'><input id='h' type='number' min='0' value='0'><b>–</b><input id='a' type='number' min='0' value='0'><button id='save'>Spara lokalt</button><button id='copy'>Kopiera</button></div><div id='status'></div></div>
        <script>
        const matches={json.dumps(offline_options, ensure_ascii=False)}; const key='cupnavi-offline-{int(tournament_id)}';
        const select=document.getElementById('m'); const h=document.getElementById('h'); const a=document.getElementById('a'); const status=document.getElementById('status');
        matches.forEach(x=>{{const o=document.createElement('option');o.value=x.id;o.textContent=x.label;select.appendChild(o)}});
        function load(){{const all=JSON.parse(localStorage.getItem(key)||'{{}}');const d=all[select.value];if(d){{h.value=d.h;a.value=d.a;status.textContent='Lokalt utkast hittat: '+d.saved}}else{{h.value=0;a.value=0;status.textContent='Inget lokalt utkast för vald match.'}}}}
        select.addEventListener('change',load); document.getElementById('save').onclick=()=>{{const all=JSON.parse(localStorage.getItem(key)||'{{}}');all[select.value]={{h:+h.value||0,a:+a.value||0,saved:new Date().toLocaleString()}};localStorage.setItem(key,JSON.stringify(all));status.textContent='Sparat lokalt på enheten.'}};
        document.getElementById('copy').onclick=async()=>{{const label=select.options[select.selectedIndex]?.text||'';const txt=label+' | '+h.value+'–'+a.value;try{{await navigator.clipboard.writeText(txt);status.textContent='Utkastet kopierades.'}}catch(e){{status.textContent=txt}}}}; load();
        </script>
        """
        components.html(offline_html, height=210, scrolling=False)


def _participant_role_label(tournament):
    sport = str(_row_value(tournament, "sport", "Fotboll") or "Fotboll")
    return "Spelare/Paransvarig" if sport in {"Tennis", "Padel"} else "Lagledare"


def _portal_match_label(match_row):
    when = swedish_datetime(match_row["scheduled_start"]) if match_row["scheduled_start"] else "Tid ej satt"
    pitch = pitch_label(match_row['tournament_id'],match_row['pitch_number'])
    return f"{when} · {pitch} · {source_label(match_row['home_source'])} – {source_label(match_row['away_source'])}"


def _save_match_roster_if_unchanged(
    match_id,
    team_id,
    player_ids,
    expected_player_ids,
    actor="Deltagaransvarig",
):
    """Save one match roster without silently overwriting a newer browser session.

    The save is transactional and also validates that every submitted player
    still belongs to the team. The caller supplies the roster snapshot that was
    originally rendered; if another user changed the roster meanwhile, this
    write is rejected instead of replacing their newer selection.
    """
    match_id = int(match_id)
    team_id = int(team_id)
    requested_ids = sorted({int(player_id) for player_id in player_ids})
    expected_ids = sorted({int(player_id) for player_id in expected_player_ids})
    selected_at = datetime.now().isoformat(timespec="seconds")

    con = db()
    try:
        # Acquire the transaction before reading the current roster. SQLite uses
        # IMMEDIATE to serialize competing writers; Turso/libSQL supports normal
        # explicit transactions.
        con.execute("BEGIN" if CLOUD_DATABASE_ENABLED else "BEGIN IMMEDIATE")

        current_rows = con.execute(
            "SELECT player_id FROM match_rosters WHERE match_id=? AND team_id=? ORDER BY player_id",
            (match_id, team_id),
        ).fetchall()
        current_ids = sorted(int(row["player_id"] if isinstance(row, sqlite3.Row) else row[0]) for row in current_rows)
        if current_ids != expected_ids:
            con.rollback()
            return False, "conflict"

        if requested_ids:
            placeholders = ",".join("?" for _ in requested_ids)
            valid_rows = con.execute(
                f"SELECT id FROM players WHERE team_id=? AND id IN ({placeholders})",
                (team_id, *requested_ids),
            ).fetchall()
            valid_ids = {
                int(row["id"] if isinstance(row, sqlite3.Row) else row[0])
                for row in valid_rows
            }
            if valid_ids != set(requested_ids):
                con.rollback()
                return False, "invalid_players"

        con.execute(
            "DELETE FROM match_rosters WHERE match_id=? AND team_id=?",
            (match_id, team_id),
        )
        for player_id in requested_ids:
            con.execute(
                "INSERT INTO match_rosters(match_id,team_id,player_id,selected_at,selected_by) VALUES(?,?,?,?,?)",
                (match_id, team_id, player_id, selected_at, actor),
            )
        con.commit()
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            con.close()
        except Exception:
            pass

    _clear_render_query_cache()
    return True, None


def _player_snapshot(player):
    """Fields protected when a team leader edits or deletes a player."""
    return {
        "name": _row_value(player, "name", None),
        "first_name": _row_value(player, "first_name", None),
        "last_name": _row_value(player, "last_name", None),
        "player_number": _row_value(player, "player_number", None),
        "birth_year": _row_value(player, "birth_year", None),
        "position": _row_value(player, "position", None),
        "is_protected": int(_row_value(player, "is_protected", 0) or 0),
    }


def _add_team_player_if_capacity(
    team_id,
    max_roster,
    *,
    player_number,
    name,
    first_name,
    last_name,
    birth_year,
    position,
    is_protected,
):
    """Atomically enforce the team roster limit in the INSERT itself."""
    team_id=int(team_id)
    max_roster=max(0,int(max_roster or 0))
    with db() as con:
        cursor=con.execute(
            """INSERT INTO players(
                   team_id,player_number,name,first_name,last_name,birth_year,position,is_protected
               )
               SELECT ?,?,?,?,?,?,?,?
               WHERE ?=0 OR (
                   SELECT COUNT(*) FROM players WHERE team_id=?
               ) < ?""",
            (
                team_id, int(player_number), name, first_name, last_name,
                int(birth_year), position, int(bool(is_protected)),
                max_roster, team_id, max_roster,
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()

        if rowcount is not None and rowcount >= 0:
            inserted=rowcount == 1
        else:
            count_row=con.execute(
                "SELECT COUNT(*) AS n FROM players WHERE team_id=?",
                (team_id,),
            ).fetchone()
            current_count=int(
                count_row["n"] if isinstance(count_row,sqlite3.Row) else count_row[0]
            )
            # When the adapter lacks rowcount, a full roster means the guarded
            # INSERT did not happen. Otherwise verify the submitted record.
            if max_roster and current_count >= max_roster:
                verify=con.execute(
                    """SELECT id FROM players
                       WHERE team_id=? AND name=? AND player_number IS ?
                       ORDER BY id DESC LIMIT 1""",
                    (team_id,name,int(player_number)),
                ).fetchone()
                inserted=verify is not None
            else:
                verify=con.execute(
                    """SELECT id FROM players
                       WHERE team_id=? AND name=? AND first_name IS ? AND last_name IS ?
                         AND player_number IS ? AND birth_year IS ? AND position IS ?
                         AND COALESCE(is_protected,0)=?
                       ORDER BY id DESC LIMIT 1""",
                    (
                        team_id,name,first_name,last_name,int(player_number),
                        int(birth_year),position,int(bool(is_protected)),
                    ),
                ).fetchone()
                inserted=verify is not None

    if inserted:
        _clear_render_query_cache()
        return True, None
    return False, "roster_full"


def _update_team_player_if_unchanged(
    player_id,
    team_id,
    expected,
    *,
    player_number,
    name,
    first_name,
    last_name,
    birth_year,
    position,
    is_protected,
):
    """Optimistic update for a team-portal player row."""
    with db() as con:
        cursor=con.execute(
            """UPDATE players
               SET name=?,first_name=?,last_name=?,player_number=?,
                   birth_year=?,position=?,is_protected=?
               WHERE id=? AND team_id=?
                 AND name IS ? AND first_name IS ? AND last_name IS ?
                 AND player_number IS ? AND birth_year IS ? AND position IS ?
                 AND COALESCE(is_protected,0)=?""",
            (
                name,first_name,last_name,int(player_number),
                int(birth_year),position,int(bool(is_protected)),
                int(player_id),int(team_id),
                expected.get("name"),expected.get("first_name"),expected.get("last_name"),
                expected.get("player_number"),expected.get("birth_year"),expected.get("position"),
                int(expected.get("is_protected",0) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        if rowcount is not None and rowcount >= 0:
            saved=rowcount == 1
        else:
            verify=con.execute(
                """SELECT name,first_name,last_name,player_number,birth_year,position,
                          COALESCE(is_protected,0) AS is_protected
                   FROM players WHERE id=? AND team_id=?""",
                (int(player_id),int(team_id)),
            ).fetchone()
            saved=bool(verify) and _player_snapshot(verify)=={
                "name":name,
                "first_name":first_name,
                "last_name":last_name,
                "player_number":int(player_number),
                "birth_year":int(birth_year),
                "position":position,
                "is_protected":int(bool(is_protected)),
            }

    if saved:
        _clear_render_query_cache()
        return True, None
    return False, "conflict"


def _delete_team_player_if_unchanged(player_id, team_id, expected):
    """Delete only the player version that the team leader actually saw."""
    with db() as con:
        cursor=con.execute(
            """DELETE FROM players
               WHERE id=? AND team_id=?
                 AND name IS ? AND first_name IS ? AND last_name IS ?
                 AND player_number IS ? AND birth_year IS ? AND position IS ?
                 AND COALESCE(is_protected,0)=?""",
            (
                int(player_id),int(team_id),
                expected.get("name"),expected.get("first_name"),expected.get("last_name"),
                expected.get("player_number"),expected.get("birth_year"),expected.get("position"),
                int(expected.get("is_protected",0) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        if rowcount is not None and rowcount >= 0:
            deleted=rowcount == 1
        else:
            verify=con.execute(
                "SELECT id FROM players WHERE id=? AND team_id=?",
                (int(player_id),int(team_id)),
            ).fetchone()
            deleted=verify is None

    if deleted:
        _clear_render_query_cache()
        return True, None
    return False, "conflict"


def _team_contact_snapshot(team_row):
    return {
        "responsible_name": _team_value(team_row, "responsible_name", "") or "",
        "responsible_phone": _team_value(team_row, "responsible_phone", "") or "",
        "responsible_email": _team_value(team_row, "responsible_email", "") or "",
        "public_contact_name": _team_value(team_row, "public_contact_name", "") or "",
        "public_contact_phone": _team_value(team_row, "public_contact_phone", "") or "",
        "public_contact_email": _team_value(team_row, "public_contact_email", "") or "",
        "public_contact_enabled": int(_team_value(team_row, "public_contact_enabled", 0) or 0),
    }


def _save_team_contact_if_unchanged(
    team_id,
    expected,
    *,
    contact_name,
    contact_phone,
    contact_email,
    public_enabled,
):
    """Optimistic lock for Lagportal contact information."""
    contact_name=str(contact_name or "").strip()
    contact_phone=str(contact_phone or "").strip()
    contact_email=str(contact_email or "").strip()
    if contact_email and ("@" not in contact_email or "." not in contact_email.rsplit("@",1)[-1]):
        return False, "invalid_email"

    with db() as con:
        cursor=con.execute(
            """UPDATE teams SET
                   responsible_name=?,responsible_phone=?,responsible_email=?,
                   public_contact_name=?,public_contact_phone=?,public_contact_email=?,
                   public_contact_enabled=?
               WHERE id=?
                 AND COALESCE(responsible_name,'')=?
                 AND COALESCE(responsible_phone,'')=?
                 AND COALESCE(responsible_email,'')=?
                 AND COALESCE(public_contact_name,'')=?
                 AND COALESCE(public_contact_phone,'')=?
                 AND COALESCE(public_contact_email,'')=?
                 AND COALESCE(public_contact_enabled,0)=?""",
            (
                contact_name,contact_phone,contact_email,
                contact_name,contact_phone,contact_email,int(bool(public_enabled)),
                int(team_id),
                expected.get("responsible_name",""),
                expected.get("responsible_phone",""),
                expected.get("responsible_email",""),
                expected.get("public_contact_name",""),
                expected.get("public_contact_phone",""),
                expected.get("public_contact_email",""),
                int(expected.get("public_contact_enabled",0) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        if rowcount is not None and rowcount >= 0:
            saved=rowcount == 1
        else:
            verify=con.execute(
                """SELECT responsible_name,responsible_phone,responsible_email,
                          public_contact_name,public_contact_phone,public_contact_email,
                          COALESCE(public_contact_enabled,0) AS public_contact_enabled
                   FROM teams WHERE id=?""",
                (int(team_id),),
            ).fetchone()
            saved=bool(verify) and _team_contact_snapshot(verify)=={
                "responsible_name":contact_name,
                "responsible_phone":contact_phone,
                "responsible_email":contact_email,
                "public_contact_name":contact_name,
                "public_contact_phone":contact_phone,
                "public_contact_email":contact_email,
                "public_contact_enabled":int(bool(public_enabled)),
            }

    if saved:
        _clear_render_query_cache()
        return True, None
    return False, "conflict"


def _mark_team_messages_read(message_ids, *, tournament_id, recipient_type, recipient_team_id=None):
    """Mark only messages owned by the current inbox as read.

    The ownership predicate prevents a stale/forged id list from changing
    messages belonging to another team or another tournament.
    """
    ids=sorted({int(message_id) for message_id in message_ids})
    if not ids:
        return 0

    placeholders=",".join("?" for _ in ids)
    now=datetime.now().isoformat(timespec="seconds")
    if recipient_type == "team":
        sql=f"""UPDATE team_messages
                SET read_at=?
                WHERE id IN ({placeholders})
                  AND tournament_id=?
                  AND recipient_type='team'
                  AND recipient_team_id=?
                  AND read_at IS NULL"""
        params=(now,*ids,int(tournament_id),int(recipient_team_id))
    else:
        sql=f"""UPDATE team_messages
                SET read_at=?
                WHERE id IN ({placeholders})
                  AND tournament_id=?
                  AND recipient_type='organizer'
                  AND read_at IS NULL"""
        params=(now,*ids,int(tournament_id))

    with db() as con:
        cursor=con.execute(sql,params)
        con.commit()
        rowcount=getattr(cursor,"rowcount",None)
    _clear_render_query_cache()
    return max(0,int(rowcount or 0)) if rowcount is not None and rowcount >= 0 else len(ids)


def _team_checkin_snapshot(team_row):
    return {
        "checked_in": int(_row_value(team_row,"checked_in",0) or 0),
        "checked_in_at": _row_value(team_row,"checked_in_at",None),
        "checked_in_by": _row_value(team_row,"checked_in_by",None),
    }


def _set_team_checkin_if_unchanged(team_id, expected, *, checked_in, checked_in_by=None):
    """Optimistic check-in transition for the team portal."""
    checked_in=int(bool(checked_in))
    checked_at=datetime.now().isoformat(timespec="seconds") if checked_in else None
    checked_by=(str(checked_in_by or "").strip() or None) if checked_in else None
    with db() as con:
        cursor=con.execute(
            """UPDATE teams
               SET checked_in=?,checked_in_at=?,checked_in_by=?
               WHERE id=?
                 AND COALESCE(checked_in,0)=?
                 AND checked_in_at IS ?
                 AND checked_in_by IS ?""",
            (
                checked_in,checked_at,checked_by,int(team_id),
                int(expected.get("checked_in",0) or 0),
                expected.get("checked_in_at"),
                expected.get("checked_in_by"),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        saved=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if saved:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _team_kit_snapshot(team_row):
    return {
        "kit_confirmed_at": _row_value(team_row,"kit_confirmed_at",None),
        "primary_color": _team_value(team_row,"primary_color","") or "",
        "secondary_color": _team_value(team_row,"secondary_color","") or "",
        "home_pattern": _team_value(team_row,"home_pattern","Helfärgad") or "Helfärgad",
        "home_color_2": _team_value(team_row,"home_color_2","#FFFFFF") or "#FFFFFF",
        "away_pattern": _team_value(team_row,"away_pattern","Helfärgad") or "Helfärgad",
        "away_color_2": _team_value(team_row,"away_color_2","#111827") or "#111827",
    }


def _confirm_team_kit_if_unchanged(team_id, expected):
    """Confirm exactly the kit version that was rendered to the team leader."""
    confirmed_at=datetime.now().isoformat(timespec="seconds")
    with db() as con:
        cursor=con.execute(
            """UPDATE teams SET kit_confirmed_at=?
               WHERE id=?
                 AND kit_confirmed_at IS ?
                 AND COALESCE(primary_color,'')=?
                 AND COALESCE(secondary_color,'')=?
                 AND COALESCE(home_pattern,'Helfärgad')=?
                 AND COALESCE(home_color_2,'#FFFFFF')=?
                 AND COALESCE(away_pattern,'Helfärgad')=?
                 AND COALESCE(away_color_2,'#111827')=?""",
            (
                confirmed_at,int(team_id),
                expected.get("kit_confirmed_at"),
                expected.get("primary_color",""),
                expected.get("secondary_color",""),
                expected.get("home_pattern","Helfärgad"),
                expected.get("home_color_2","#FFFFFF"),
                expected.get("away_pattern","Helfärgad"),
                expected.get("away_color_2","#111827"),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        saved=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if saved:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _admin_team_snapshot(team_row):
    """Fields protected when Admin edits/deletes a team."""
    return {
        "name": _team_value(team_row, "name", "") or "",
        "primary_color": _team_value(team_row, "primary_color", "") or "",
        "secondary_color": _team_value(team_row, "secondary_color", "") or "",
        "home_pattern": _team_value(team_row, "home_pattern", "Helfärgad") or "Helfärgad",
        "home_color_2": _team_value(team_row, "home_color_2", "#FFFFFF") or "#FFFFFF",
        "away_pattern": _team_value(team_row, "away_pattern", "Helfärgad") or "Helfärgad",
        "away_color_2": _team_value(team_row, "away_color_2", "#111827") or "#111827",
        "distance_km": int(_team_value(team_row, "distance_km", 0) or 0),
        "late_first_match": int(_team_value(team_row, "late_first_match", 0) or 0),
        "earliest_first_time": _team_value(team_row, "earliest_first_time", None),
        "travel_note": _team_value(team_row, "travel_note", "") or "",
        "avoid_late_group_match": int(_team_value(team_row, "avoid_late_group_match", 0) or 0),
        "responsible_name": _team_value(team_row, "responsible_name", "") or "",
        "responsible_phone": _team_value(team_row, "responsible_phone", "") or "",
        "responsible_email": _team_value(team_row, "responsible_email", "") or "",
        "age_class": _team_value(team_row, "age_class", None),
        "competition_class_id": _team_value(team_row, "competition_class_id", None),
        "group_id": _team_value(team_row, "group_id", None),
    }


def _admin_update_team_if_unchanged(
    team_id,
    tournament_id,
    expected,
    *,
    name,
    primary_color,
    secondary_color,
    home_pattern,
    home_color_2,
    away_pattern,
    away_color_2,
    distance_km,
    late_first_match,
    earliest_first_time,
    travel_note,
    avoid_late_group_match,
    responsible_name,
    responsible_phone,
    responsible_email,
    age_class,
    competition_class_id,
):
    """Optimistic Admin team update; stale forms cannot overwrite newer edits."""
    if responsible_email and ("@" not in responsible_email or "." not in responsible_email.rsplit("@",1)[-1]):
        return False, "invalid_email"

    with db() as con:
        cursor=con.execute(
            """UPDATE teams SET
                 name=?,primary_color=?,secondary_color=?,home_pattern=?,home_color_2=?,
                 away_pattern=?,away_color_2=?,distance_km=?,late_first_match=?,
                 earliest_first_time=?,travel_note=?,avoid_late_group_match=?,
                 kit_confirmed_at=NULL,responsible_name=?,responsible_phone=?,responsible_email=?,
                 age_class=?,competition_class_id=?,
                 group_id=CASE WHEN COALESCE(competition_class_id,-1)!=COALESCE(?,-1) THEN NULL ELSE group_id END
               WHERE id=? AND tournament_id=?
                 AND COALESCE(name,'')=?
                 AND COALESCE(primary_color,'')=?
                 AND COALESCE(secondary_color,'')=?
                 AND COALESCE(home_pattern,'Helfärgad')=?
                 AND COALESCE(home_color_2,'#FFFFFF')=?
                 AND COALESCE(away_pattern,'Helfärgad')=?
                 AND COALESCE(away_color_2,'#111827')=?
                 AND COALESCE(distance_km,0)=?
                 AND COALESCE(late_first_match,0)=?
                 AND earliest_first_time IS ?
                 AND COALESCE(travel_note,'')=?
                 AND COALESCE(avoid_late_group_match,0)=?
                 AND COALESCE(responsible_name,'')=?
                 AND COALESCE(responsible_phone,'')=?
                 AND COALESCE(responsible_email,'')=?
                 AND age_class IS ?
                 AND competition_class_id IS ?
                 AND group_id IS ?""",
            (
                name,primary_color,secondary_color,home_pattern,home_color_2,
                away_pattern,away_color_2,int(distance_km),int(bool(late_first_match)),
                earliest_first_time,travel_note,int(bool(avoid_late_group_match)),
                responsible_name,responsible_phone,responsible_email,age_class,competition_class_id,
                competition_class_id,int(team_id),int(tournament_id),
                expected.get("name",""),expected.get("primary_color",""),expected.get("secondary_color",""),
                expected.get("home_pattern","Helfärgad"),expected.get("home_color_2","#FFFFFF"),
                expected.get("away_pattern","Helfärgad"),expected.get("away_color_2","#111827"),
                int(expected.get("distance_km",0) or 0),int(expected.get("late_first_match",0) or 0),
                expected.get("earliest_first_time"),expected.get("travel_note",""),
                int(expected.get("avoid_late_group_match",0) or 0),
                expected.get("responsible_name",""),expected.get("responsible_phone",""),
                expected.get("responsible_email",""),expected.get("age_class"),
                expected.get("competition_class_id"),expected.get("group_id"),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        saved=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False

    if saved:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _admin_delete_team_if_unchanged(team_id, tournament_id, expected):
    """Delete a team only if the row still matches the Admin's rendered version."""
    team_id=int(team_id)
    tournament_id=int(tournament_id)
    token=f"team:{team_id}"

    with db() as con:
        current=con.execute(
            "SELECT * FROM teams WHERE id=? AND tournament_id=?",
            (team_id,tournament_id),
        ).fetchone()
        if current is None or _admin_team_snapshot(current) != expected:
            return False,"conflict"

        bracket_rows=con.execute(
            """SELECT DISTINCT bracket_id FROM matches
               WHERE tournament_id=? AND bracket_id IS NOT NULL
                 AND (home_source=? OR away_source=?)""",
            (tournament_id,token,token),
        ).fetchall()
        bracket_ids={
            int(row["bracket_id"] if isinstance(row,sqlite3.Row) else row[0])
            for row in bracket_rows
        }
        group_id=expected.get("group_id")
        if group_id is not None:
            rows=con.execute(
                """SELECT DISTINCT bracket_id FROM matches
                   WHERE tournament_id=? AND bracket_id IS NOT NULL
                     AND (home_source LIKE ? OR away_source LIKE ?)""",
                (tournament_id,f"group:{group_id}:%",f"group:{group_id}:%"),
            ).fetchall()
            bracket_ids.update(
                int(row["bracket_id"] if isinstance(row,sqlite3.Row) else row[0])
                for row in rows
            )

        con.execute(
            "DELETE FROM matches WHERE tournament_id=? AND (home_source=? OR away_source=?)",
            (tournament_id,token,token),
        )
        for bracket_id in bracket_ids:
            con.execute(
                "DELETE FROM brackets WHERE id=? AND tournament_id=?",
                (bracket_id,tournament_id),
            )
        cursor=con.execute(
            "DELETE FROM teams WHERE id=? AND tournament_id=?",
            (team_id,tournament_id),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        deleted=(rowcount == 1) if rowcount is not None and rowcount >= 0 else True

    if deleted:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _admin_group_snapshot(group_row):
    return {
        "name": _row_value(group_row,"name","") or "",
        "age_class": _row_value(group_row,"age_class",None),
        "competition_class_id": _row_value(group_row,"competition_class_id",None),
    }


def _admin_update_group_if_unchanged(
    group_id,
    tournament_id,
    expected,
    *,
    name,
    age_class,
    competition_class_id,
):
    with db() as con:
        cursor=con.execute(
            """UPDATE groups SET name=?,age_class=?,competition_class_id=?
               WHERE id=? AND tournament_id=?
                 AND COALESCE(name,'')=?
                 AND age_class IS ?
                 AND competition_class_id IS ?""",
            (
                name,age_class,competition_class_id,
                int(group_id),int(tournament_id),
                expected.get("name",""),expected.get("age_class"),
                expected.get("competition_class_id"),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        saved=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if saved:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _admin_delete_group_if_unchanged(group_id, tournament_id, expected):
    group_id=int(group_id)
    tournament_id=int(tournament_id)
    with db() as con:
        current=con.execute(
            "SELECT * FROM groups WHERE id=? AND tournament_id=?",
            (group_id,tournament_id),
        ).fetchone()
        if current is None or _admin_group_snapshot(current) != expected:
            return False,"conflict"

        rows=con.execute(
            """SELECT DISTINCT bracket_id FROM matches
               WHERE tournament_id=? AND bracket_id IS NOT NULL
                 AND (home_source LIKE ? OR away_source LIKE ?)""",
            (tournament_id,f"group:{group_id}:%",f"group:{group_id}:%"),
        ).fetchall()
        bracket_ids=[
            int(row["bracket_id"] if isinstance(row,sqlite3.Row) else row[0])
            for row in rows
        ]
        con.execute(
            "UPDATE teams SET group_id=NULL WHERE tournament_id=? AND group_id=?",
            (tournament_id,group_id),
        )
        for bracket_id in bracket_ids:
            con.execute(
                "DELETE FROM brackets WHERE id=? AND tournament_id=?",
                (bracket_id,tournament_id),
            )
        cursor=con.execute(
            "DELETE FROM groups WHERE id=? AND tournament_id=?",
            (group_id,tournament_id),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        deleted=(rowcount == 1) if rowcount is not None and rowcount >= 0 else True
    if deleted:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _set_schedule_request_status_if_current(
    request_id,
    tournament_id,
    expected_status,
    new_status,
):
    """Atomic request-state transition; stale Admin buttons do nothing."""
    if new_status not in {"Godkänd","Nekad"}:
        raise ValueError("Ogiltig önskemålsstatus.")
    with db() as con:
        cursor=con.execute(
            """UPDATE schedule_requests SET status=?
               WHERE id=? AND tournament_id=? AND status=?""",
            (new_status,int(request_id),int(tournament_id),expected_status),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        saved=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if saved:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _sponsor_snapshot(row):
    return {
        "name": _row_value(row,"name","") or "",
        "level": _row_value(row,"level",None),
        "description": _row_value(row,"description",None),
        "website_url": _row_value(row,"website_url",None),
        "logo_data_uri": _row_value(row,"logo_data_uri",None),
        "active": int(_row_value(row,"active",0) or 0),
        "sort_order": int(_row_value(row,"sort_order",0) or 0),
    }


def _admin_update_sponsor_if_unchanged(
    sponsor_id,
    tournament_id,
    expected,
    *,
    name,
    level,
    description,
    website_url,
    logo_data_uri,
    active,
    sort_order,
):
    with db() as con:
        cursor=con.execute(
            """UPDATE sponsors SET
                   name=?,level=?,description=?,website_url=?,logo_data_uri=?,active=?,sort_order=?
               WHERE id=? AND tournament_id=?
                 AND COALESCE(name,'')=?
                 AND level IS ?
                 AND description IS ?
                 AND website_url IS ?
                 AND logo_data_uri IS ?
                 AND COALESCE(active,0)=?
                 AND COALESCE(sort_order,0)=?""",
            (
                name,level,description,website_url,logo_data_uri,int(bool(active)),int(sort_order),
                int(sponsor_id),int(tournament_id),
                expected.get("name",""),expected.get("level"),expected.get("description"),
                expected.get("website_url"),expected.get("logo_data_uri"),
                int(expected.get("active",0) or 0),int(expected.get("sort_order",0) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        saved=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if saved:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _admin_delete_sponsor_if_unchanged(sponsor_id, tournament_id, expected):
    with db() as con:
        cursor=con.execute(
            """DELETE FROM sponsors
               WHERE id=? AND tournament_id=?
                 AND COALESCE(name,'')=?
                 AND level IS ?
                 AND description IS ?
                 AND website_url IS ?
                 AND logo_data_uri IS ?
                 AND COALESCE(active,0)=?
                 AND COALESCE(sort_order,0)=?""",
            (
                int(sponsor_id),int(tournament_id),
                expected.get("name",""),expected.get("level"),expected.get("description"),
                expected.get("website_url"),expected.get("logo_data_uri"),
                int(expected.get("active",0) or 0),int(expected.get("sort_order",0) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        deleted=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if deleted:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _functionary_snapshot(row):
    return {
        "name": _row_value(row,"name","") or "",
        "role": _row_value(row,"role","") or "",
        "phone": _row_value(row,"phone",None),
        "email": _row_value(row,"email",None),
        "pitch_number": _row_value(row,"pitch_number",None),
        "notes": _row_value(row,"notes",None),
        "public_contact": int(_row_value(row,"public_contact",0) or 0),
        "active": int(_row_value(row,"active",1) or 0),
    }


def _admin_update_functionary_if_unchanged(
    functionary_id,
    tournament_id,
    expected,
    *,
    name,
    role,
    phone,
    email,
    pitch_number,
    notes,
    public_contact,
):
    if email and ("@" not in email or "." not in email.rsplit("@",1)[-1]):
        return False,"invalid_email"
    with db() as con:
        cursor=con.execute(
            """UPDATE functionaries SET
                   name=?,role=?,phone=?,email=?,pitch_number=?,notes=?,public_contact=?
               WHERE id=? AND tournament_id=?
                 AND COALESCE(name,'')=?
                 AND COALESCE(role,'')=?
                 AND phone IS ?
                 AND email IS ?
                 AND pitch_number IS ?
                 AND notes IS ?
                 AND COALESCE(public_contact,0)=?
                 AND COALESCE(active,1)=?""",
            (
                name,role,phone,email,pitch_number,notes,int(bool(public_contact)),
                int(functionary_id),int(tournament_id),
                expected.get("name",""),expected.get("role",""),
                expected.get("phone"),expected.get("email"),expected.get("pitch_number"),
                expected.get("notes"),int(expected.get("public_contact",0) or 0),
                int(expected.get("active",1) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        saved=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if saved:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _admin_delete_functionary_if_unchanged(functionary_id, tournament_id, expected):
    with db() as con:
        cursor=con.execute(
            """DELETE FROM functionaries
               WHERE id=? AND tournament_id=?
                 AND COALESCE(name,'')=?
                 AND COALESCE(role,'')=?
                 AND phone IS ?
                 AND email IS ?
                 AND pitch_number IS ?
                 AND notes IS ?
                 AND COALESCE(public_contact,0)=?
                 AND COALESCE(active,1)=?""",
            (
                int(functionary_id),int(tournament_id),
                expected.get("name",""),expected.get("role",""),
                expected.get("phone"),expected.get("email"),expected.get("pitch_number"),
                expected.get("notes"),int(expected.get("public_contact",0) or 0),
                int(expected.get("active",1) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        deleted=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if deleted:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _set_publication_if_current(
    tournament_id,
    *,
    expected_is_published,
    expected_lifecycle,
    publish,
):
    """Apply publish/unpublish only to the tournament state rendered to Admin."""
    tournament_id=int(tournament_id)
    expected_is_published=int(bool(expected_is_published))
    expected_lifecycle=str(expected_lifecycle or "draft")
    with db() as con:
        if publish:
            con.execute(
                """UPDATE matches SET schedule_published=1
                   WHERE tournament_id=? AND scheduled_start IS NOT NULL""",
                (tournament_id,),
            )
            cursor=con.execute(
                """UPDATE tournaments
                   SET is_published=1,
                       lifecycle_status=CASE WHEN lifecycle_status='live' THEN 'live' ELSE 'published' END
                   WHERE id=? AND COALESCE(is_published,0)=?
                     AND COALESCE(lifecycle_status,'draft')=?""",
                (tournament_id,expected_is_published,expected_lifecycle),
            )
        else:
            cursor=con.execute(
                """UPDATE tournaments
                   SET is_published=0,lifecycle_status='draft'
                   WHERE id=? AND COALESCE(is_published,0)=?
                     AND COALESCE(lifecycle_status,'draft')=?""",
                (tournament_id,expected_is_published,expected_lifecycle),
            )
        rowcount=getattr(cursor,"rowcount",None)
        changed=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
        if changed:
            con.commit()
        else:
            con.rollback()
    if changed:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _set_lifecycle_if_current(
    tournament_id,
    expected_lifecycle,
    new_lifecycle,
    *,
    expected_is_published=1,
):
    """Atomic lifecycle transition for live/completed actions."""
    if new_lifecycle not in {"live","completed"}:
        raise ValueError("Ogiltig livscykelstatus.")
    completed_at=datetime.now().isoformat(timespec="seconds") if new_lifecycle=="completed" else None
    with db() as con:
        if new_lifecycle=="completed":
            cursor=con.execute(
                """UPDATE tournaments SET lifecycle_status='completed',completed_at=?,is_published=1
                   WHERE id=? AND COALESCE(lifecycle_status,'draft')=?
                     AND COALESCE(is_published,0)=?""",
                (completed_at,int(tournament_id),expected_lifecycle,int(bool(expected_is_published))),
            )
        else:
            cursor=con.execute(
                """UPDATE tournaments SET lifecycle_status='live'
                   WHERE id=? AND COALESCE(lifecycle_status,'draft')=?
                     AND COALESCE(is_published,0)=?""",
                (int(tournament_id),expected_lifecycle,int(bool(expected_is_published))),
            )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        changed=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if changed:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _undo_audit_entry_if_current(audit_id, tournament_id):
    """Undo one reversible audit entry exactly once, in one transaction."""
    audit_id=int(audit_id)
    tournament_id=int(tournament_id)
    with db() as con:
        audit=con.execute(
            """SELECT * FROM audit_log
               WHERE id=? AND tournament_id=? AND undone_at IS NULL
                 AND reversible=1 AND action_type IN ('schedule_move','delay_shift')""",
            (audit_id,tournament_id),
        ).fetchone()
        if audit is None:
            return False,"conflict",None

        action_type=_row_value(audit,"action_type","")
        entity_id=_row_value(audit,"entity_id",None)
        before_json=_row_value(audit,"before_json",None)
        description=_row_value(audit,"description","") or ""
        entity_type=_row_value(audit,"entity_type","") or ""
        before=json.loads(before_json or "null")

        if action_type=="schedule_move" and isinstance(before,dict):
            cursor=con.execute(
                """UPDATE matches SET scheduled_start=?,pitch_number=?
                   WHERE id=? AND tournament_id=?""",
                (before.get("scheduled_start"),before.get("pitch_number"),entity_id,tournament_id),
            )
            rowcount=getattr(cursor,"rowcount",None)
            if rowcount is not None and rowcount >= 0 and rowcount != 1:
                con.rollback()
                return False,"target_missing",None
        elif action_type=="delay_shift" and isinstance(before,list):
            for item in before:
                cursor=con.execute(
                    """UPDATE matches SET scheduled_start=?
                       WHERE id=? AND tournament_id=?""",
                    (item.get("scheduled_start"),item.get("id"),tournament_id),
                )
                rowcount=getattr(cursor,"rowcount",None)
                if rowcount is not None and rowcount >= 0 and rowcount != 1:
                    con.rollback()
                    return False,"target_missing",None
        else:
            con.rollback()
            return False,"invalid_payload",None

        undone_at=datetime.now().isoformat(timespec="seconds")
        cursor=con.execute(
            """UPDATE audit_log SET undone_at=?
               WHERE id=? AND tournament_id=? AND undone_at IS NULL""",
            (undone_at,audit_id,tournament_id),
        )
        rowcount=getattr(cursor,"rowcount",None)
        if rowcount is not None and rowcount >= 0 and rowcount != 1:
            con.rollback()
            return False,"conflict",None
        con.commit()

    _clear_render_query_cache()
    return True,None,{
        "entity_id":entity_id,
        "entity_type":entity_type,
        "description":description,
    }


def _offer_snapshot(row):
    return {
        "title": _row_value(row,"title","") or "",
        "business_name": _row_value(row,"business_name",None),
        "description": _row_value(row,"description",None),
        "discount_code": _row_value(row,"discount_code",None),
        "valid_until": _row_value(row,"valid_until",None),
        "url": _row_value(row,"url",None),
        "active": int(_row_value(row,"active",0) or 0),
        "sort_order": int(_row_value(row,"sort_order",0) or 0),
    }


def _admin_update_offer_if_unchanged(offer_id,tournament_id,expected,*,title,business_name,description,discount_code,valid_until,url,active,sort_order):
    with db() as con:
        cursor=con.execute(
            """UPDATE offers SET title=?,business_name=?,description=?,discount_code=?,
                   valid_until=?,url=?,active=?,sort_order=?
               WHERE id=? AND tournament_id=?
                 AND COALESCE(title,'')=?
                 AND business_name IS ? AND description IS ? AND discount_code IS ?
                 AND valid_until IS ? AND url IS ?
                 AND COALESCE(active,0)=? AND COALESCE(sort_order,0)=?""",
            (
                title,business_name,description,discount_code,valid_until,url,int(bool(active)),int(sort_order),
                int(offer_id),int(tournament_id),
                expected.get("title",""),expected.get("business_name"),expected.get("description"),
                expected.get("discount_code"),expected.get("valid_until"),expected.get("url"),
                int(expected.get("active",0) or 0),int(expected.get("sort_order",0) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        saved=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if saved:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _admin_delete_offer_if_unchanged(offer_id,tournament_id,expected):
    with db() as con:
        cursor=con.execute(
            """DELETE FROM offers
               WHERE id=? AND tournament_id=?
                 AND COALESCE(title,'')=?
                 AND business_name IS ? AND description IS ? AND discount_code IS ?
                 AND valid_until IS ? AND url IS ?
                 AND COALESCE(active,0)=? AND COALESCE(sort_order,0)=?""",
            (
                int(offer_id),int(tournament_id),expected.get("title",""),
                expected.get("business_name"),expected.get("description"),expected.get("discount_code"),
                expected.get("valid_until"),expected.get("url"),
                int(expected.get("active",0) or 0),int(expected.get("sort_order",0) or 0),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        deleted=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if deleted:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _functionary_shift_snapshot(row):
    return {
        "functionary_id": int(_row_value(row,"functionary_id",0) or 0),
        "shift_start": _row_value(row,"shift_start","") or "",
        "shift_end": _row_value(row,"shift_end","") or "",
        "assignment": _row_value(row,"assignment",None),
        "location": _row_value(row,"location",None),
    }


def _admin_delete_functionary_shift_if_unchanged(shift_id,tournament_id,expected):
    with db() as con:
        cursor=con.execute(
            """DELETE FROM functionary_shifts
               WHERE id=? AND tournament_id=? AND functionary_id=?
                 AND shift_start=? AND shift_end=?
                 AND assignment IS ? AND location IS ?""",
            (
                int(shift_id),int(tournament_id),int(expected.get("functionary_id",0)),
                expected.get("shift_start",""),expected.get("shift_end",""),
                expected.get("assignment"),expected.get("location"),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        deleted=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if deleted:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _credential_snapshot(row):
    if row is None:
        return None
    return {
        "id": int(_row_value(row,"id",0) or 0),
        "admin_code": _row_value(row,"admin_code",None),
        "created_at": _row_value(row,"created_at",None),
        "rotated_at": _row_value(row,"rotated_at",None),
    }


def _rotate_participant_code_if_unchanged(tournament_id,team_id,expected):
    """Rotate portal code only if credential state still matches rendered state."""
    plain_code=generate_access_code()
    salt,code_hash=new_code_hash(plain_code)
    now_iso=datetime.now().isoformat(timespec="microseconds")
    with db() as con:
        if expected is None:
            cursor=con.execute(
                """INSERT OR IGNORE INTO participant_access_credentials(
                       tournament_id,team_id,code_salt,code_hash,created_at,rotated_at,admin_code)
                   VALUES(?,?,?,?,?,NULL,?)""",
                (int(tournament_id),int(team_id),salt,code_hash,now_iso,plain_code),
            )
            rowcount=getattr(cursor,"rowcount",None)
            if rowcount is not None and rowcount >= 0:
                changed=rowcount == 1
            else:
                verify=con.execute(
                    """SELECT created_at,admin_code FROM participant_access_credentials
                       WHERE tournament_id=? AND team_id=?""",
                    (int(tournament_id),int(team_id)),
                ).fetchone()
                changed=bool(verify) and _row_value(verify,"created_at",None)==now_iso and _row_value(verify,"admin_code",None)==plain_code
        else:
            cursor=con.execute(
                """UPDATE participant_access_credentials
                   SET code_salt=?,code_hash=?,rotated_at=?,admin_code=?
                   WHERE id=? AND tournament_id=? AND team_id=?
                     AND admin_code IS ? AND created_at IS ? AND rotated_at IS ?""",
                (
                    salt,code_hash,now_iso,plain_code,
                    int(expected.get("id",0)),int(tournament_id),int(team_id),
                    expected.get("admin_code"),expected.get("created_at"),expected.get("rotated_at"),
                ),
            )
            rowcount=getattr(cursor,"rowcount",None)
            if rowcount is not None and rowcount >= 0:
                changed=rowcount == 1
            else:
                verify=con.execute(
                    """SELECT rotated_at,admin_code FROM participant_access_credentials
                       WHERE id=? AND tournament_id=? AND team_id=?""",
                    (int(expected.get("id",0)),int(tournament_id),int(team_id)),
                ).fetchone()
                changed=bool(verify) and _row_value(verify,"rotated_at",None)==now_iso and _row_value(verify,"admin_code",None)==plain_code
        if changed:
            con.commit()
        else:
            con.rollback()
    if changed:
        _clear_render_query_cache()
        return True,None,plain_code
    return False,"conflict",None


def _rotate_all_participant_codes(tournament_id):
    """Rotate every team portal code for one tournament in a single transaction."""
    team_rows = all_rows(
        "SELECT id FROM teams WHERE tournament_id=? ORDER BY id",
        (int(tournament_id),),
    )
    if not team_rows:
        return [], None

    generated = []
    now_iso = datetime.now().isoformat(timespec="microseconds")
    try:
        with db() as con:
            for team_row in team_rows:
                team_id = int(team_row["id"])
                plain_code = generate_access_code()
                salt, code_hash = new_code_hash(plain_code)
                con.execute(
                    """INSERT INTO participant_access_credentials(
                           tournament_id,team_id,code_salt,code_hash,created_at,rotated_at,admin_code
                       ) VALUES(?,?,?,?,?,NULL,?)
                       ON CONFLICT(tournament_id,team_id) DO UPDATE SET
                           code_salt=excluded.code_salt,
                           code_hash=excluded.code_hash,
                           rotated_at=excluded.created_at,
                           admin_code=excluded.admin_code""",
                    (int(tournament_id), team_id, salt, code_hash, now_iso, plain_code),
                )
                generated.append((team_id, plain_code))
            con.commit()
    except Exception as exc:
        return [], str(exc)

    _clear_render_query_cache()
    return generated, None


def _trash_tournament_if_current(tournament_id,expected_lifecycle,expected_is_published):
    with db() as con:
        cursor=con.execute(
            """UPDATE tournaments SET lifecycle_status='trashed',trashed_at=?,is_published=0
               WHERE id=? AND COALESCE(lifecycle_status,'draft')=?
                 AND COALESCE(is_published,0)=?""",
            (
                datetime.now().isoformat(timespec="seconds"),int(tournament_id),
                str(expected_lifecycle or "draft"),int(bool(expected_is_published)),
            ),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        changed=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if changed:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _restore_trashed_tournament_if_current(tournament_id,expected_trashed_at):
    with db() as con:
        cursor=con.execute(
            """UPDATE tournaments SET lifecycle_status='draft',trashed_at=NULL,is_published=0
               WHERE id=? AND lifecycle_status='trashed' AND trashed_at IS ?""",
            (int(tournament_id),expected_trashed_at),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        changed=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if changed:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def _delete_trashed_tournament_if_current(tournament_id,expected_name,expected_trashed_at):
    with db() as con:
        cursor=con.execute(
            """DELETE FROM tournaments
               WHERE id=? AND name=? AND lifecycle_status='trashed' AND trashed_at IS ?""",
            (int(tournament_id),expected_name,expected_trashed_at),
        )
        rowcount=getattr(cursor,"rowcount",None)
        con.commit()
        deleted=(rowcount == 1) if rowcount is not None and rowcount >= 0 else False
    if deleted:
        _clear_render_query_cache()
        return True,None
    return False,"conflict"


def render_team_portal(tournament_id, tournament):
    """Begränsad portal för ett enda lag/deltagare i en enda cup."""
    role_label = _participant_role_label(tournament)
    st.title(f"👥 {role_label} · {tournament['name']}")
    st.caption("Portalen ger endast åtkomst till det egna laget/deltagaren. Resultat och officiella matchhändelser rapporteras av matchrapportör eller domare.")

    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,))
    if not teams:
        st.info("Det finns ännu inga deltagare/lag i cupen.")
        return

    auth = st.session_state.get("participant_portal_auth") or {}
    authenticated_team_id = auth.get("team_id") if auth.get("tournament_id") == tournament_id else None
    valid_team_ids = {int(row["id"]) for row in teams}
    if authenticated_team_id not in valid_team_ids:
        authenticated_team_id = None

    if not authenticated_team_id:
        with st.form(f"participant_login_{tournament_id}"):
            selected_team_id = st.selectbox(
                "Välj lag/deltagare",
                [row["id"] for row in teams],
                format_func=lambda team_id: next(row["name"] for row in teams if row["id"] == team_id),
            )
            code = st.text_input("Lagkod / deltagarkod", type="password", max_chars=12)
            submitted = st.form_submit_button("Logga in", type="primary", use_container_width=True)
        if submitted:
            credential = one_row(
                "SELECT * FROM participant_access_credentials WHERE tournament_id=? AND team_id=?",
                (tournament_id, selected_team_id),
            )
            if credential and verify_access_code(code, credential["code_salt"], credential["code_hash"]):
                st.session_state["participant_portal_auth"] = {
                    "tournament_id": int(tournament_id), "team_id": int(selected_team_id)
                }
                st.rerun()
            st.error("Fel kod, eller så har laget ännu ingen kod. Kontakta cupadministratören.")
        return

    team_row = next(row for row in teams if int(row["id"]) == int(authenticated_team_id))
    team_id = int(team_row["id"])
    top1, top2 = st.columns([3, 1])
    top1.markdown(f"**{html.escape(team_row['name'])}**")
    top1.caption("Inloggad i lagportalen")
    if top2.button("Logga ut", key=f"participant_logout_{tournament_id}_{team_id}", use_container_width=True):
        st.session_state.pop("participant_portal_auth", None)
        st.rerun()

    received_messages = all_rows(
        """SELECT * FROM team_messages
           WHERE tournament_id=? AND recipient_type='team' AND recipient_team_id=?
           ORDER BY created_at DESC,id DESC LIMIT 200""",
        (tournament_id, team_id),
    )
    unread_team_count = sum(1 for row in received_messages if not row["read_at"])
    message_tab_label = f"🔴 Meddelanden ({unread_team_count})" if unread_team_count else "Meddelanden"
    portal_tabs = st.tabs(["Lag & matcher", "Trupp", "Matchtrupper", message_tab_label])

    with portal_tabs[0]:
        st.caption("Checka in laget, bekräfta matchställ och se kommande matcher.")
        c1, c2 = st.columns(2)
        if bool(_row_value(tournament, "enable_team_checkin", 1)):
            if bool(team_row["checked_in"]):
                c1.success(f"✅ Incheckad {team_row['checked_in_at'] or ''}" + (f" av {team_row['checked_in_by']}" if team_row["checked_in_by"] else ""))
                if c1.button("Ta bort incheckning", key=f"portal_uncheck_{team_id}"):
                    saved, reason = _set_team_checkin_if_unchanged(
                        team_id,
                        _team_checkin_snapshot(team_row),
                        checked_in=False,
                    )
                    if saved:
                        record_audit(tournament_id, "team_checkin", "team", f"{team_row['name']}: incheckning borttagen", entity_id=team_id, actor=role_label)
                    else:
                        st.warning("Lagets incheckningsstatus ändrades av någon annan. Senaste status laddas om.")
                    st.rerun()
            else:
                checkin_name = c1.text_input("Vem checkar in laget?", placeholder="Namn", key=f"checkin_name_{team_id}")
                if c1.button("✅ Vi är på plats", type="primary", key=f"portal_check_{team_id}", use_container_width=True):
                    saved, reason = _set_team_checkin_if_unchanged(
                        team_id,
                        _team_checkin_snapshot(team_row),
                        checked_in=True,
                        checked_in_by=checkin_name.strip() or role_label,
                    )
                    if saved:
                        record_audit(tournament_id, "team_checkin", "team", f"{team_row['name']}: incheckad", entity_id=team_id, actor=role_label)
                    else:
                        st.warning("Lagets incheckningsstatus ändrades av någon annan. Senaste status laddas om.")
                    st.rerun()
        else:
            c1.caption("Lagincheckning används inte i den här turneringen.")

        if team_row["kit_confirmed_at"]:
            c2.success(f"👕 Matchställ bekräftade {team_row['kit_confirmed_at']}")
        else:
            c2.caption("👕 Matchställ är ännu inte bekräftade.")
        c2.markdown(kit_preview_html(_team_value(team_row, "home_pattern", "Helfärgad"), team_row["primary_color"], _team_value(team_row, "home_color_2", "#FFFFFF"), "Hemmaställ"), unsafe_allow_html=True)
        c2.markdown(kit_preview_html(_team_value(team_row, "away_pattern", "Helfärgad"), team_row["secondary_color"], _team_value(team_row, "away_color_2", "#111827"), "Bortaställ"), unsafe_allow_html=True)
        if c2.button(
            "Bekräfta matchställ",
            key=f"confirm_kit_{team_id}",
            use_container_width=True,
            disabled=bool(team_row["kit_confirmed_at"]),
        ):
            saved, reason = _confirm_team_kit_if_unchanged(
                team_id,
                _team_kit_snapshot(team_row),
            )
            if saved:
                record_audit(tournament_id, "kit_confirmed", "team", f"{team_row['name']}: matchställ bekräftade", entity_id=team_id, actor=role_label)
            else:
                st.warning("Matchställen ändrades av någon annan och bekräftades därför inte. Senaste version laddas om.")
            st.rerun()

        st.subheader("Mina matcher")
        direct_team_source = f"team:{team_id}"
        matches = [
            row for row in all_rows(
                """SELECT * FROM matches
                   WHERE tournament_id=? AND scheduled_start IS NOT NULL
                     AND (home_source=? OR away_source=? OR home_source NOT LIKE 'team:%' OR away_source NOT LIKE 'team:%')
                   ORDER BY scheduled_start,pitch_number,id""",
                (tournament_id, direct_team_source, direct_team_source),
            )
            if team_id in _match_team_ids(row)
        ]
        if matches:
            for match_row in matches:
                score = ""
                if match_row["home_score"] is not None and match_row["away_score"] is not None:
                    score = f" · {match_row['home_score']}–{match_row['away_score']}"
                st.markdown(f"**{html.escape(_portal_match_label(match_row))}{score}**")
        else:
            st.caption("Inga schemalagda matcher ännu.")

        st.subheader("Ansvarig kontaktperson")
        contact_notice_key=f"portal_contact_notice_{team_id}"
        if contact_notice_key in st.session_state:
            notice_type, notice_text = st.session_state.pop(contact_notice_key)
            if notice_type == "success":
                st.success(notice_text)
            else:
                st.warning(notice_text)
        with st.form(f"portal_contact_{team_id}"):
            contact_name = st.text_input("Namn", value=_team_value(team_row, "responsible_name", "") or "")
            contact_phone = st.text_input("Telefon", value=_team_value(team_row, "responsible_phone", "") or "")
            contact_email = st.text_input("E-post", value=_team_value(team_row, "responsible_email", "") or "")
            allow_public = bool(_row_value(tournament, "allow_team_public_contact", 0))
            contact_public = st.checkbox(
                "Visa kontaktpersonen publikt",
                value=bool(_team_value(team_row, "public_contact_enabled", 0)) and allow_public,
                disabled=not allow_public,
                help="Kontaktuppgifter är interna som standard. Detta val kan bara aktiveras om arrangören tillåter publika lagkontakter.",
            )
            if st.form_submit_button("Spara kontaktuppgifter"):
                public_enabled = int(bool(contact_public) and allow_public)
                saved, contact_reason = _save_team_contact_if_unchanged(
                    team_id,
                    _team_contact_snapshot(team_row),
                    contact_name=contact_name,
                    contact_phone=contact_phone,
                    contact_email=contact_email,
                    public_enabled=public_enabled,
                )
                if saved:
                    st.session_state[contact_notice_key]=(
                        "success",
                        "Kontaktuppgifterna är sparade.",
                    )
                    st.rerun()
                elif contact_reason == "invalid_email":
                    st.error("Ange en giltig e-postadress eller lämna fältet tomt.")
                else:
                    st.session_state[contact_notice_key]=(
                        "warning",
                        "Kontaktuppgifterna ändrades av någon annan och dina äldre uppgifter skrevs inte över. Senaste uppgifter har laddats.",
                    )
                    st.rerun()

    with portal_tabs[1]:
        st.subheader("Hantera truppen")
        max_roster = int(_row_value(tournament, "max_roster_size", 0) or 0)
        players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (team_id,))
        st.caption(f"{len(players)} registrerade spelare" + (f" · max {max_roster}" if max_roster else " · ingen maxgräns satt"))
        with st.form(f"portal_add_player_{team_id}", clear_on_submit=True):
            pc1, pc2 = st.columns(2)
            pfirst = pc1.text_input("Förnamn")
            plast = pc2.text_input("Efternamn")
            pc3, pc4, pc5 = st.columns(3)
            pnumber = pc3.number_input("Nummer", 0, 999, 0)
            current_year = datetime.now().year
            pbirth = pc4.number_input("Födelseår", 1900, current_year, current_year - 12)
            pposition = pc5.text_input("Position/roll", placeholder="Frivilligt")
            pprotected = st.checkbox("Skyddad spelare – visa inte namn publikt", value=False)
            if st.form_submit_button("Lägg till spelare", type="primary", disabled=bool(max_roster and len(players) >= max_roster)):
                if not pfirst.strip() or not plast.strip():
                    st.error("Ange både förnamn och efternamn.")
                elif max_roster and len(players) >= max_roster:
                    st.error(f"Arrangören har satt max {max_roster} spelare.")
                else:
                    full_name = f"{pfirst.strip()} {plast.strip()}"
                    added, add_reason = _add_team_player_if_capacity(
                        team_id,
                        max_roster,
                        player_number=pnumber,
                        name=full_name,
                        first_name=pfirst.strip(),
                        last_name=plast.strip(),
                        birth_year=int(pbirth),
                        position=pposition.strip(),
                        is_protected=pprotected,
                    )
                    if added:
                        record_audit(tournament_id, "roster_player_added", "team", f"{team_row['name']}: {full_name} tillagd", entity_id=team_id, actor=role_label)
                    elif add_reason == "roster_full":
                        st.warning(f"Truppen har redan nått maxgränsen på {max_roster} spelare. Ingen spelare lades till.")
                    st.rerun()
        for player in players:
            with st.expander(f"#{player['player_number'] if player['player_number'] is not None else '–'} {_player_display_name(player)}"):
                with st.form(f"portal_edit_player_{player['id']}"):
                    ec1, ec2 = st.columns(2)
                    legacy_parts = str(player["name"] or "").strip().split(" ", 1)
                    default_first = _row_value(player, "first_name", "") or (legacy_parts[0] if legacy_parts else "")
                    default_last = _row_value(player, "last_name", "") or (legacy_parts[1] if len(legacy_parts) > 1 else "")
                    efirst = ec1.text_input("Förnamn", value=default_first)
                    elast = ec2.text_input("Efternamn", value=default_last)
                    ec3, ec4, ec5 = st.columns(3)
                    enumber = ec3.number_input("Nummer", 0, 999, int(player["player_number"] or 0))
                    ebirth = ec4.number_input("Födelseår", 1900, datetime.now().year, int(_row_value(player, "birth_year", datetime.now().year - 12) or datetime.now().year - 12))
                    eposition = ec5.text_input("Position/roll", value=player["position"] or "")
                    eprotected = st.checkbox("Skyddad spelare – visa inte namn publikt", value=bool(_row_value(player, "is_protected", 0)))
                    save_player = st.form_submit_button("Spara")
                player_expected = _player_snapshot(player)
                if save_player:
                    if not efirst.strip() or not elast.strip():
                        st.error("Ange både förnamn och efternamn.")
                    else:
                        full_name = f"{efirst.strip()} {elast.strip()}"
                        saved, save_reason = _update_team_player_if_unchanged(
                            player["id"],
                            team_id,
                            player_expected,
                            player_number=enumber,
                            name=full_name,
                            first_name=efirst.strip(),
                            last_name=elast.strip(),
                            birth_year=int(ebirth),
                            position=eposition.strip(),
                            is_protected=eprotected,
                        )
                        if not saved and save_reason == "conflict":
                            st.warning("Spelaren ändrades av någon annan och dina äldre uppgifter skrevs inte över.")
                        st.rerun()
                if st.button("Ta bort spelaren", key=f"portal_delete_player_{player['id']}"):
                    deleted, delete_reason = _delete_team_player_if_unchanged(
                        player["id"],
                        team_id,
                        player_expected,
                    )
                    if deleted:
                        record_audit(tournament_id, "roster_player_deleted", "team", f"{team_row['name']}: spelare borttagen", entity_id=team_id, actor=role_label)
                    elif delete_reason == "conflict":
                        st.warning("Spelaren ändrades av någon annan och raderades därför inte. Senaste uppgifter laddas om.")
                    st.rerun()

    with portal_tabs[2]:
        st.subheader("Matchtrupper")
        deadline_minutes = int(_row_value(tournament, "squad_deadline_minutes", 30) or 0)
        st.caption(f"Matchtruppen låses {deadline_minutes} minuter före matchstart. Admin kan alltid ändra den.")
        direct_team_source = f"team:{team_id}"
        team_matches = [
            row for row in all_rows(
                """SELECT * FROM matches
                   WHERE tournament_id=? AND scheduled_start IS NOT NULL
                     AND (home_source=? OR away_source=? OR home_source NOT LIKE 'team:%' OR away_source NOT LIKE 'team:%')
                   ORDER BY scheduled_start,id""",
                (tournament_id, direct_team_source, direct_team_source),
            ) if team_id in _match_team_ids(row)
        ]
        if not team_matches:
            st.info("Inga matcher att registrera matchtrupp för ännu.")
        else:
            team_match_by_id = {int(row["id"]): row for row in team_matches}
            roster_rows = all_rows(
                """SELECT match_id,player_id
                   FROM match_rosters
                   WHERE team_id=?
                   ORDER BY match_id,player_id""",
                (team_id,),
            )
            roster_ids_by_match = {}
            for roster_row in roster_rows:
                roster_ids_by_match.setdefault(int(roster_row["match_id"]), []).append(int(roster_row["player_id"]))
            rostered_match_ids = set(roster_ids_by_match)

            match_id = st.selectbox(
                "Välj match",
                list(team_match_by_id),
                format_func=lambda mid: _portal_match_label(team_match_by_id[int(mid)]),
                key=f"portal_squad_match_{team_id}",
            )
            match_row = team_match_by_id[int(match_id)]
            locked = squad_is_locked(match_row["scheduled_start"], deadline_minutes)
            deadline = squad_deadline_at(match_row["scheduled_start"], deadline_minutes)
            if locked:
                st.warning(f"Matchtruppen är låst. Deadline var {swedish_datetime(deadline.isoformat(timespec='minutes'))}.")
            else:
                st.info(f"Deadline: {swedish_datetime(deadline.isoformat(timespec='minutes')) if deadline else 'Ingen deadline'}")
            # `players` was already loaded for the Trupp tab earlier in this render.
            existing_ids = set(roster_ids_by_match.get(int(match_id), []))
            options = [int(row["id"]) for row in players]
            player_label_by_id = {
                int(row["id"]): f"#{row['player_number'] if row['player_number'] is not None else '–'} {row['name']}"
                for row in players
            }
            selected_ids = st.multiselect(
                "Spelare i matchtruppen",
                options,
                default=[pid for pid in options if pid in existing_ids],
                format_func=lambda pid: player_label_by_id[int(pid)],
                disabled=locked,
                key=f"portal_match_roster_{match_id}_{team_id}",
            )
            prev_with_roster = next(
                (
                    candidate
                    for candidate in reversed([row for row in team_matches if row["scheduled_start"] < match_row["scheduled_start"]])
                    if int(candidate["id"]) in rostered_match_ids
                ),
                None,
            )
            bc1, bc2 = st.columns(2)
            if bc1.button("Spara matchtrupp", type="primary", disabled=locked, key=f"save_match_roster_{match_id}_{team_id}", use_container_width=True):
                saved, save_reason = _save_match_roster_if_unchanged(
                    match_id,
                    team_id,
                    selected_ids,
                    existing_ids,
                    role_label,
                )
                if saved:
                    record_audit(tournament_id, "match_roster_saved", "match", f"{team_row['name']}: matchtrupp sparad ({len(selected_ids)} spelare)", entity_id=match_id, actor=role_label)
                    st.success("Matchtruppen är sparad.")
                elif save_reason == "conflict":
                    st.warning("Matchtruppen ändrades av någon annan och skrevs inte över. Senaste truppen laddas om.")
                else:
                    st.error("Matchtruppen kunde inte sparas eftersom en vald spelare inte längre tillhör laget.")
                st.rerun()
            if bc2.button("Kopiera föregående matchtrupp", disabled=locked or prev_with_roster is None, key=f"copy_match_roster_{match_id}_{team_id}", use_container_width=True):
                previous_ids = list(roster_ids_by_match.get(int(prev_with_roster["id"]), []))
                valid_ids = {int(row["id"]) for row in players}
                copied_ids = [pid for pid in previous_ids if int(pid) in valid_ids]
                saved, save_reason = _save_match_roster_if_unchanged(
                    match_id,
                    team_id,
                    copied_ids,
                    existing_ids,
                    role_label,
                )
                if saved:
                    st.success("Föregående matchtrupp kopierades.")
                elif save_reason == "conflict":
                    st.warning("Matchtruppen ändrades av någon annan och skrevs inte över. Senaste truppen laddas om.")
                else:
                    st.error("Matchtruppen kunde inte kopieras eftersom spelartruppen ändrades.")
                st.rerun()
            if not existing_ids:
                st.warning("⚠️ Matchtrupp ej registrerad.")

    with portal_tabs[3]:
        st.subheader("Meddelanden")
        st.caption("Skriv internt till arrangören eller till ett annat deltagande lag i samma cup. Meddelanden visas bara för berörda parter och arrangören.")
        team_names = {int(row["id"]): row["name"] for row in teams}
        recipients = [("organizer", None, "Arrangören")] + [
            ("team", int(row["id"]), row["name"]) for row in teams if int(row["id"]) != team_id
        ]
        portal_message_token_key=f"portal_message_request_token_{team_id}"
        if portal_message_token_key not in st.session_state:
            st.session_state[portal_message_token_key]=new_token()
        with st.form(f"portal_send_message_{team_id}", clear_on_submit=True):
            recipient_index = st.selectbox(
                "Till",
                range(len(recipients)),
                format_func=lambda idx: recipients[idx][2],
                key=f"portal_message_recipient_{team_id}",
            )
            msg_subject = st.text_input("Ämne", placeholder="Exempel: Förfrågan om träningsmatch", max_chars=200)
            msg_body = st.text_area(
                "Meddelande",
                placeholder="Exempel: Hej! Vi möts i cupen och skulle gärna spela en träningsmatch mot er senare under säsongen.",
                max_chars=3000,
                height=120,
            )
            send_message = st.form_submit_button("Skicka meddelande", type="primary", use_container_width=True)
        if send_message:
            recipient_type, recipient_team_id, _ = recipients[int(recipient_index)]
            try:
                _send_team_message(
                    tournament_id,
                    "team",
                    msg_subject,
                    msg_body,
                    sender_team_id=team_id,
                    recipient_type=recipient_type,
                    recipient_team_id=recipient_team_id,
                    request_token=st.session_state[portal_message_token_key],
                )
                st.session_state.pop(portal_message_token_key,None)
                record_audit(tournament_id, "team_message_sent", "team", f"{team_row['name']}: meddelande skickat", entity_id=team_id, actor=role_label)
                st.success("Meddelandet är skickat.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        inbox, sent = st.tabs(["Inkorg", "Skickat"])
        with inbox:
            unread_ids = [int(row["id"]) for row in received_messages if not row["read_at"]]
            if unread_ids and st.button(
                f"Markera alla som lästa ({len(unread_ids)})",
                key=f"portal_mark_messages_read_{team_id}",
            ):
                _mark_team_messages_read(
                    unread_ids,
                    tournament_id=tournament_id,
                    recipient_type="team",
                    recipient_team_id=team_id,
                )
                st.rerun()
            if not received_messages:
                st.info("Inga mottagna meddelanden ännu.")
            for msg in received_messages:
                sender, _ = _message_party_label(msg, team_names)
                with st.container(border=True):
                    unread_prefix = "🔴 " if not msg["read_at"] else ""
                    st.markdown(f"**{unread_prefix}{html.escape(msg['subject'])}**")
                    st.caption(f"Från {html.escape(sender)} · {msg['created_at']}")
                    st.write(msg["message"])

        with sent:
            sent_messages = all_rows(
                """SELECT * FROM team_messages
                   WHERE tournament_id=? AND sender_type='team' AND sender_team_id=?
                   ORDER BY created_at DESC,id DESC LIMIT 200""",
                (tournament_id, team_id),
            )
            if not sent_messages:
                st.info("Inga skickade meddelanden ännu.")
            for msg in sent_messages:
                _, recipient = _message_party_label(msg, team_names)
                with st.container(border=True):
                    st.markdown(f"**{html.escape(msg['subject'])}**")
                    st.caption(f"Till {html.escape(recipient)} · {msg['created_at']}")
                    email_status=str(_row_value(msg,"email_status","") or "")
                    if msg["recipient_type"] == "team":
                        email_status_label={
                            "sent":"E-postnotis skickad",
                            "failed":"E-postnotis kunde inte skickas",
                            "skipped":"Ingen e-postadress registrerad",
                            "pending":"E-postnotis behandlas",
                        }.get(email_status,"")
                        if email_status_label:
                            st.caption(email_status_label)
                    st.write(msg["message"])



init_db()


# SIDOMENY OCH TURNERING
st.sidebar.title(f"🏆 {tr('Turneringar')}")
language_options = {"sv": "Svenska", "en": "English"}
selected_language = st.sidebar.selectbox(
    "🌐 " + tr("Välj språk"),
    list(language_options),
    index=0 if current_language() == "sv" else 1,
    format_func=lambda code: language_options[code],
    key="language_selector",
)
if st.session_state.get("language") != selected_language:
    st.session_state["language"] = selected_language
    st.rerun()

_install_streamlit_translation_hooks()
public_app_mode = str(st.query_params.get("public_only", "")).lower() in {"1", "true", "yes"}
_direct_public_cup = bool(str(st.query_params.get("cup", "")).strip()) if hasattr(st, "query_params") else False

mode_options = (
    ["Turneringsvy", "Om"]
    if public_app_mode
    else (["Turneringsvy", "Lagportal", "Matchrapportör", "Admin", "Om"]
          if CLOUD_DATABASE_ENABLED
          else ["Admin", "Lagportal", "Matchrapportör", "Turneringsvy", "Om"])
)
if _direct_public_cup and st.session_state.get("view_mode") is None:
    # A fresh direct cup link is public navigation even in local/CI mode, where
    # Admin is otherwise the first default mode.
    st.session_state["view_mode"] = "Turneringsvy"
elif st.session_state.get("view_mode") not in mode_options:
    st.session_state["view_mode"] = mode_options[0]
st.sidebar.caption("Version v.1.252")

def _set_view_mode(mode):
    st.session_state["view_mode"] = mode
    # Turneringsvyn ska vara så ren som möjligt. Admin öppnar den utökade
    # rollnavigationen och den ligger kvar tills användaren återgår publikt.
    if mode == "Admin":
        st.session_state["role_nav_expanded"] = True
    elif mode == "Turneringsvy":
        st.session_state["role_nav_expanded"] = False
        # En aktiv cup måste följa med explicit till den publika vyn. URL-parametern
        # är den deterministiska sanningskällan och fungerar även i en ny browser/session.
        _active_cup = (
            st.session_state.get("active_tournament_selector")
            or st.session_state.get("preferred_tournament_id")
        )
        if _active_cup and hasattr(st, "query_params"):
            st.query_params["cup"] = str(_active_cup)


# v160: cupens huvudflöde. Specialfunktioner finns kvar i gruppnavigationen.
ADMIN_PRIMARY_FLOW = [
    ("Adminöversikt", "Översikt"),
    ("Lag", "Lag"),
    ("Grupper", "Grupper"),
    ("Skapa och publicera schema", "Schema"),
    ("Matcher och resultat", "Resultat"),
    ("Tabeller", "Tabell"),
    ("Slutspel", "Slutspel"),
]

ADMIN_PAGE_COPY = {
    "Adminöversikt": ("Översikt", "Se status och nästa steg."),
    "Lag": ("Lägg in deltagarna", "Skapa eller importera lag. När lagen är klara går du vidare till gruppindelningen."),
    "Grupper": ("Bygg tävlingsstrukturen", "Fördela lagen i grupper och kontrollera att gruppindelningen är komplett."),
    "Skapa och publicera schema": ("Schema", "Skapa och justera matchschemat."),
    "Matcher och resultat": ("Resultat", "Registrera och följ resultaten."),
    "Matchhändelser": ("Fyll på matchdetaljer", "Registrera mål, assist och kort efter att matchresultatet är sparat."),
    "Tabeller": ("Tabeller", "Följ tävlingsläget."),
    "Slutspel": ("Slutspel", "Följ vägen mot final."),
    "Cupinställningar": ("Cupinställningar", "Se vad som är låst, vad som kan ändras och vilka ändringar som kräver omplanering."),
    "Önskemålscentral": ("Önskemålscentral", "Samla, godkänn och prioritera lagens schemakrav och önskemål på ett ställe."),
    "Problem & lösningar": ("Lös det som blockerar cupen", "CupNavi visar problem och föreslår åtgärder i prioriterad ordning."),
    "Domare": ("Bemanna matcherna", "Lägg till domare och kontrollera att matcherna kan genomföras utan krockar."),
    "Trupper": ("Hantera spelarna", "Registrera spelare och trupper för de lag som behöver det."),
    "Instruktioner": ("Guide genom CupNavi", "Följ cupen steg för steg om du vill ha extra vägledning."),
}

def _primary_flow_index(page):
    return next((i for i,(name,_) in enumerate(ADMIN_PRIMARY_FLOW) if name == page), None)

current_mode = st.session_state["view_mode"]
st.markdown("<div class='cn-mode-nav-safezone'></div>", unsafe_allow_html=True)
if public_app_mode:
    # Public-only-läget behåller sin separata, begränsade navigation.
    mode_col1, mode_col2 = st.columns(2)
    mode_col1.button(tr("Turneringsvy"), key="view_mode_public_button", type="primary" if current_mode == "Turneringsvy" else "secondary", use_container_width=True, on_click=_set_view_mode, args=("Turneringsvy",))
    mode_col2.button(tr("Om"), key="view_mode_about_button", type="primary" if current_mode == "Om" else "secondary", use_container_width=True, on_click=_set_view_mode, args=("Om",))
else:
    role_nav_expanded = bool(
        st.session_state.get("role_nav_expanded", current_mode != "Turneringsvy")
    )
    if current_mode == "Turneringsvy" and not role_nav_expanded:
        # Publik Turneringsvy: endast de två vägar som behövs ska konkurrera om
        # uppmärksamheten. Admin kräver fortfarande vanlig admininloggning.
        mode_col1, mode_col2 = st.columns(2)
        mode_col1.button(tr("Turneringsvy"), key="view_mode_public_button", type="primary", use_container_width=True, on_click=_set_view_mode, args=("Turneringsvy",))
        mode_col2.button(tr("Admin"), key="view_mode_admin_button", type="secondary", use_container_width=True, on_click=_set_view_mode, args=("Admin",))
    else:
        # Efter att Admin öppnats visas rollväxlarna och ligger kvar tills
        # användaren går tillbaka till Turneringsvy.
        mode_col1, mode_col2, mode_col3, mode_col4, mode_col5 = st.columns(5)
        mode_col1.button(tr("Turneringsvy"), key="view_mode_public_button", type="primary" if current_mode == "Turneringsvy" else "secondary", use_container_width=True, on_click=_set_view_mode, args=("Turneringsvy",))
        mode_col2.button("Lagportal", key="view_mode_team_portal_button", type="primary" if current_mode == "Lagportal" else "secondary", use_container_width=True, on_click=_set_view_mode, args=("Lagportal",))
        mode_col3.button(tr("Matchrapportör"), key="view_mode_reporter_button", type="primary" if current_mode == "Matchrapportör" else "secondary", use_container_width=True, on_click=_set_view_mode, args=("Matchrapportör",))
        mode_col4.button(tr("Admin"), key="view_mode_admin_button", type="primary" if current_mode == "Admin" else "secondary", use_container_width=True, on_click=_set_view_mode, args=("Admin",))
        mode_col5.button(tr("Om"), key="view_mode_about_button", type="primary" if current_mode == "Om" else "secondary", use_container_width=True, on_click=_set_view_mode, args=("Om",))
view_mode = st.session_state["view_mode"]
if not public_app_mode:
    st.sidebar.caption(f"{tr('Visningsläge')}: {tr(view_mode)}")
if view_mode == "Om":
    render_about_page()
    st.stop()

if RELEASE_FILES_MISMATCH and view_mode == "Admin":
    st.sidebar.error(
        f"Releasefilerna är inte synkade\n\n"
        f"app.py: {APP_BUILD_VERSION}\n\n"
        f"cupnavi_core/version.py: {CORE_APP_VERSION}\n\n"
        "Kontrollen läser versionsfilen direkt från den deployade disken. "
        "CupNavi laddar automatiskt om egna Pythonmoduler när källkoden ändras. "
        "Om denna varning kvarstår har den deployade filuppsättningen faktiskt olika versioner."
    )

if view_mode == "Matchrapportör":
    require_match_reporter_access()

if view_mode == "Admin":
    require_admin_access()
    st.sidebar.caption("Ny cup skapas här med bara grunduppgifter. Tävlingsklasser och planerat antal lag per klass läggs in i den guidade setupen.")
    with st.sidebar.expander("Skapa ny turnering"):
        template_id = st.selectbox(
            "Startmall",
            list(TOURNAMENT_TEMPLATES),
            format_func=lambda key: TOURNAMENT_TEMPLATES[key]["label_sv"],
            key="new_tournament_template",
            help="Mallen sätter bara bra startvärden. Du kan justera övriga regler efter att cupen skapats.",
        )
        selected_template = template_definition(template_id)
        st.caption(selected_template["description_sv"])
        with st.form("new_tournament", clear_on_submit=True):
            n = st.text_input("Namn")
            place = st.text_input("Spelort")
            sports_list = list(SPORT_PROFILES)
            suggested_sport = selected_template["sport"] if selected_template["sport"] in sports_list else sports_list[0]
            sport = st.selectbox(
                "Sport",
                sports_list,
                index=sports_list.index(suggested_sport),
                key="new_tournament_sport",
                help="Sport väljs när cupen skapas och låses därefter, eftersom den styr matchmodell, terminologi och sportregler.",
            )
            # De flesta arrangörer behöver aldrig ändra dessa grundvärden.
            # Behåll funktionaliteten, men låt normalflödet vara Namn → Spelort → Sport → Datum → Skapa.
            with st.expander("Fler alternativ", expanded=os.environ.get("CUPNAVI_E2E") == "1"):
                st.caption("Internationell grund och testläge. Standardvärdena fungerar för en vanlig svensk cup.")
                environment_type = st.radio(
                    "Miljö",
                    ["production", "test"],
                    index=1 if os.environ.get("CUPNAVI_E2E") == "1" else 0,
                    format_func=lambda value: "Riktig cup" if value == "production" else "Testmiljö",
                    horizontal=True,
                    key="new_tournament_environment",
                    help="Använd Testmiljö endast när du vill skapa demodata eller prova funktioner.",
                )
                create_locale = st.selectbox(
                    "Språk/region",
                    list(SUPPORTED_LOCALES),
                    index=list(SUPPORTED_LOCALES).index(DEFAULT_LOCALE) if DEFAULT_LOCALE in SUPPORTED_LOCALES else 0,
                    key="new_tournament_locale",
                )
                create_timezone = st.text_input(
                    "Tidszon",
                    value=DEFAULT_TIMEZONE,
                    key="new_tournament_timezone",
                    help="IANA-tidszon, exempelvis Europe/Stockholm. Behöver normalt inte ändras.",
                )
                create_country = st.text_input(
                    "Landkod",
                    value="SE",
                    max_chars=2,
                    key="new_tournament_country",
                ).upper().strip()
                if environment_type == "test":
                    st.caption("Testmiljö märks tydligt och kan fyllas med demodata.")
                st.caption("Sport, språk/region, tidszon och land är grundegenskaper och kan inte ändras efter skapandet.")
            # Service-/arrangemangsval görs senare i den guidade setupen.
            create_team_checkin = False
            create_final_ranking = False
            create_changing_rooms = False
            create_show_prices = False
            start_date = st.date_input("Cupdag")
            multi_day = st.checkbox("Cupen pågår flera dagar", value=False, key="new_tournament_multi_day")
            end_date = st.date_input("Sista cupdag", value=start_date) if multi_day else start_date
            st.caption("Efter Skapa guidar CupNavi dig genom tävlingsklasser, kapacitet och regler.")
            expected_teams = 0
            # Antal lag anges per tävlingsklass i den guidade setupen; inget globalt lagantal här.
            if st.form_submit_button("Skapa", type="primary", use_container_width=True):
                normalized_timezone = valid_timezone(create_timezone)
                if not n.strip():
                    st.error("Ange ett namn.")
                elif end_date < start_date:
                    st.error("Sista cupdagen får inte ligga före första cupdagen.")
                elif normalized_timezone != create_timezone.strip():
                    st.error("Ogiltig tidszon. Använd ett IANA-namn, exempelvis Europe/Stockholm.")
                elif create_country and (len(create_country) != 2 or not create_country.isalpha()):
                    st.error("Landkod ska vara två bokstäver enligt ISO-format, exempelvis SE, GB eller US.")
                else:
                    participant_type = str(sport_definition(sport)["participant_type"])
                    # Release-contract compatibility: the creation payload still contains
                    # locale,timezone_name,participant_type,country_code and
                    # age_classes_json,enable_team_checkin even though the INSERT is now
                    # built from the live database schema.
                    new_tournament_id = insert_tournament_compat({
                        "name": n.strip(),
                        "location": place.strip(),
                        "tournament_date": start_date.isoformat(),
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "expected_team_count": expected_teams,
                        "points_win": 3,
                        "points_draw": 1,
                        "points_loss": 0,
                        "sport": sport,
                        "lifecycle_status": "draft",
                        "environment_type": environment_type,
                        "locale": create_locale,
                        "timezone_name": normalized_timezone,
                        "participant_type": participant_type,
                        "country_code": create_country or None,
                        "age_classes_json": json.dumps([], ensure_ascii=False),
                        "enable_team_checkin": 1 if create_team_checkin else 0,
                        "enable_final_ranking": 1 if create_final_ranking else 0,
                        "changing_rooms_available": 1 if create_changing_rooms else 0,
                        "show_price_information": 1 if create_show_prices else 0,
                    })
                    used_slugs = [row["public_slug"] for row in all_rows("SELECT public_slug FROM tournaments WHERE public_slug IS NOT NULL")]
                    public_slug = choose_unique_slug(n.strip(), start_date.isoformat(), new_tournament_id, used_slugs)
                    run("UPDATE tournaments SET public_slug=? WHERE id=?", (public_slug, new_tournament_id))
                    sync_competition_classes(new_tournament_id, [])
                    defaults = sport_profile(sport)
                    run(
                        """INSERT INTO schedule_rules(
                               tournament_id,halves,minutes_per_half,halftime_minutes,minimum_team_rest_minutes
                           ) VALUES(?,?,?,?,?)
                           ON CONFLICT(tournament_id) DO NOTHING""",
                        (new_tournament_id, defaults["halves"], defaults["minutes_per_half"],
                         defaults["halftime_minutes"], defaults["minimum_team_rest_minutes"]),
                    )
                    add_feed_item(new_tournament_id, f"{n.strip()} skapad", f"Sport: {sport}", category="Cup")
                    st.session_state["new_tournament_setup_id"] = int(new_tournament_id)
                    st.session_state["preferred_tournament_id"] = int(new_tournament_id)
                    st.rerun()

if view_mode == "Admin":
    clone_sources = all_rows(
        "SELECT * FROM tournaments WHERE COALESCE(lifecycle_status,'draft')!='trashed' ORDER BY COALESCE(start_date,tournament_date) DESC,name"
    )
    if clone_sources:
        with st.sidebar.expander("Duplicera tidigare cup"):
            source_id = st.selectbox(
                "Kopiera från",
                [row["id"] for row in clone_sources],
                format_func=lambda value: next(row["name"] for row in clone_sources if row["id"] == value),
                key="clone_source_tournament",
            )
            source = next(row for row in clone_sources if row["id"] == source_id)
            default_clone_name = f"{source['name']} – ny upplaga"
            clone_name = st.text_input("Namn på ny cup", value=default_clone_name, key="clone_tournament_name")
            clone_start = st.date_input("Första cupdag", key="clone_tournament_start")
            st.caption(f"📅 {date_with_weekday(clone_start)}")
            clone_end = st.date_input("Sista cupdag", value=clone_start, key="clone_tournament_end")
            st.caption(f"📅 {date_with_weekday(clone_end)}")
            copy_teams = st.checkbox("Kopiera deltagare/lag", value=False, key="clone_copy_teams")
            copy_refs = st.checkbox("Kopiera domare", value=False, key="clone_copy_refs")
            clone_environment = st.radio(
                "Ny miljö",
                ["production", "test"],
                format_func=lambda value: "Riktig cup" if value == "production" else "Testkopia",
                horizontal=True,
                key="clone_environment",
            )
            st.caption("Schema, resultat, grupper, matchtrupper och historik kopieras aldrig. Den nya cupen skapas alltid som utkast.")
            if st.button("Skapa ny upplaga", key="clone_tournament_button", use_container_width=True):
                if not clone_name.strip():
                    st.error("Ange namn på den nya cupen.")
                elif clone_end < clone_start:
                    st.error("Sista cupdagen får inte ligga före första cupdagen.")
                else:
                    payload = clone_tournament_payload(
                        dict(source),
                        name=clone_name,
                        start_date=clone_start.isoformat(),
                        end_date=clone_end.isoformat(),
                    )
                    payload["environment_type"] = clone_environment
                    clone_columns = list(payload)
                    placeholders = ",".join("?" for _ in clone_columns)
                    new_id = run(
                        f"INSERT INTO tournaments({','.join(clone_columns)}) VALUES({placeholders})",
                        tuple(payload[column] for column in clone_columns),
                    )
                    sync_competition_classes(new_id, parse_age_classes(_row_value(source, "age_classes_json", "[]")))
                    source_rule = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (source_id,))
                    if source_rule:
                        rule_columns = [key for key in dict(source_rule) if key != "tournament_id"]
                        run(
                            f"INSERT INTO schedule_rules(tournament_id,{','.join(rule_columns)}) VALUES(?,{','.join('?' for _ in rule_columns)})",
                            (new_id, *(source_rule[column] for column in rule_columns)),
                        )
                    if copy_teams:
                        source_teams = all_rows("SELECT name,primary_color,secondary_color,home_pattern,home_color_2,away_pattern,away_color_2,distance_km,late_first_match,earliest_first_time,travel_note,age_class,avoid_late_group_match FROM teams WHERE tournament_id=? ORDER BY id", (source_id,))
                        for row in source_teams:
                            run(
                                """INSERT INTO teams(tournament_id,name,primary_color,secondary_color,home_pattern,home_color_2,away_pattern,away_color_2,distance_km,late_first_match,earliest_first_time,travel_note,age_class,avoid_late_group_match)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (new_id, row["name"], row["primary_color"], row["secondary_color"], row["home_pattern"], row["home_color_2"], row["away_pattern"], row["away_color_2"], row["distance_km"], row["late_first_match"], row["earliest_first_time"], row["travel_note"], _row_value(row, "age_class", None), _row_value(row, "avoid_late_group_match", 0)),
                            )
                    if copy_teams:
                        sync_competition_classes(new_id)
                    if copy_refs:
                        for row in all_rows("SELECT name,phone,email,referee_level FROM referees WHERE tournament_id=? ORDER BY id", (source_id,)):
                            run("INSERT INTO referees(tournament_id,name,phone,email,referee_level) VALUES(?,?,?,?,?)", (new_id, row["name"], row["phone"], row["email"], row["referee_level"]))
                    used_slugs = [row["public_slug"] for row in all_rows("SELECT public_slug FROM tournaments WHERE public_slug IS NOT NULL")]
                    slug = choose_unique_slug(clone_name.strip(), clone_start.isoformat(), new_id, used_slugs)
                    run("UPDATE tournaments SET public_slug=? WHERE id=?", (slug, new_id))
                    st.success("Ny upplaga skapad som utkast.")
                    st.rerun()

# Explicit cup= must be resolved before generic public discovery. This makes
# direct links deterministic and prevents session state from selecting another cup.
cup_query = st.query_params.get("cup") if hasattr(st, "query_params") else None
cup_query_text = str(cup_query).strip() if cup_query else ""
requested_cup_id = None
_requested_public_row = None

if view_mode in ("Admin", "Matchrapportör", "Lagportal"):
    _tournament_access_sql = "SELECT * FROM tournaments WHERE COALESCE(lifecycle_status,'draft')!='trashed'"
    _tournament_access_params = ()
    if view_mode == "Matchrapportör" and st.session_state.get("reporter_auth_scope") == "test_only":
        _tournament_access_sql += " AND COALESCE(environment_type,'production')='test'"
    if view_mode == "Matchrapportör" and st.session_state.get("reporter_auth_scope") == "tournament":
        _tournament_access_sql += " AND id=?"
        _tournament_access_params = (int(st.session_state["reporter_tournament_id"]),)
    tournaments = all_rows(
        _tournament_access_sql
        + " ORDER BY CASE COALESCE(lifecycle_status,'draft') WHEN 'live' THEN 0 WHEN 'published' THEN 1 WHEN 'draft' THEN 2 WHEN 'completed' THEN 3 ELSE 4 END, "
          "COALESCE(start_date,tournament_date) DESC,name",
        _tournament_access_params,
    )
else:
    if cup_query_text:
        try:
            requested_cup_id = int(cup_query_text)
            _requested_numeric_id = requested_cup_id
        except (TypeError, ValueError):
            _requested_numeric_id = None

        if _requested_numeric_id is not None:
            _requested_public_row = one_row(
                """SELECT * FROM tournaments
                   WHERE id=? AND is_published=1
                     AND COALESCE(lifecycle_status,'published') IN ('published','live','completed')
                     AND COALESCE(lifecycle_status,'published')!='trashed'""",
                (_requested_numeric_id,),
            )
        else:
            _requested_public_row = one_row(
                """SELECT * FROM tournaments
                   WHERE public_slug=? AND is_published=1
                     AND COALESCE(lifecycle_status,'published') IN ('published','live','completed')
                     AND COALESCE(lifecycle_status,'published')!='trashed'""",
                (cup_query_text,),
            )

    if _requested_public_row is not None:
        tournaments = [_requested_public_row]
        requested_cup_id = int(_requested_public_row["id"])
    else:
        tournaments = all_rows(
            "SELECT * FROM tournaments WHERE is_published=1 AND COALESCE(lifecycle_status,'published') IN ('published','live','completed') "
            "ORDER BY CASE COALESCE(lifecycle_status,'published') WHEN 'live' THEN 0 WHEN 'published' THEN 1 WHEN 'completed' THEN 2 ELSE 3 END, "
            "COALESCE(start_date,tournament_date) DESC,name"
        )

if not tournaments:
    st.title("🏆 CupNavi")
    if view_mode == "Admin":
        st.info("Skapa den första turneringen i vänstermenyn.")
    elif view_mode == "Matchrapportör":
        st.info("Det finns ingen turnering att rapportera ännu.")
    elif view_mode == "Lagportal":
        st.info("Det finns ingen turnering med registrerade lag ännu.")
    else:
        st.info("Ingen turnering är publicerad ännu.")
    st.stop()

# Resolve cup= against the actual accessible rows also for Admin/role views.
if cup_query_text and requested_cup_id is None:
    try:
        _candidate_id = int(cup_query_text)
        if any(int(row["id"]) == _candidate_id for row in tournaments):
            requested_cup_id = _candidate_id
    except (TypeError, ValueError):
        slug_match = next(
            (row for row in tournaments if str(_row_value(row, "public_slug", "") or "") == cup_query_text),
            None,
        )
        requested_cup_id = int(slug_match["id"]) if slug_match else None

tournament_ids = [int(t["id"]) for t in tournaments]
preferred_tournament_id = st.session_state.get("preferred_tournament_id")

# Resolve the initial selector seed in pure, regression-tested UI logic.
# URL wins only when the widget has no valid current selection; a deliberate
# user selection must survive subsequent Streamlit reruns.
selector_seed = resolve_tournament_selector_seed(
    tournament_ids,
    current_selection=st.session_state.get("active_tournament_selector"),
    requested_cup_id=requested_cup_id,
    preferred_tournament_id=preferred_tournament_id,
)

def _tournament_selector_label(tournament_id):
    row = next(t for t in tournaments if t["id"] == tournament_id)
    status = normalize_status(row["lifecycle_status"], is_published=bool(row["is_published"]))
    label = row["name"]
    if status == "completed":
        year_source = row["start_date"] or row["tournament_date"] or ""
        year = str(year_source)[:4] if year_source else ""
        return f"🏆 {label}{' · ' + year if year else ''} · {status_label(status, current_language())}"
    if status == "live":
        return f"🔴 {label} · {status_label(status, current_language())}"
    return label

# Seed the widget only when its state is missing/invalid. Do not overwrite it on
# every rerun: doing so made the "Aktiv turnering" selectbox snap back to the
# URL/preferred cup immediately after the user selected another tournament.
if st.session_state.get("active_tournament_selector") not in tournament_ids:
    st.session_state["active_tournament_selector"] = selector_seed

tid = st.sidebar.selectbox(
    tr("Aktiv turnering"),
    tournament_ids,
    format_func=_tournament_selector_label,
    key="active_tournament_selector",
)

# A deliberate selector change becomes the session preference and the URL follows
# it. This keeps Admin, public preview and refreshes on the same selected cup.
if preferred_tournament_id != tid:
    st.session_state["preferred_tournament_id"] = int(tid)
if hasattr(st, "query_params") and str(st.query_params.get("cup", "")).strip():
    selected_row = next(t for t in tournaments if int(t["id"]) == int(tid))
    selected_slug = str(_row_value(selected_row, "public_slug", "") or "").strip()
    canonical_cup_query = selected_slug or str(tid)
    if str(st.query_params.get("cup", "")).strip() != canonical_cup_query:
        st.query_params["cup"] = canonical_cup_query

tournament = next(t for t in tournaments if t["id"] == tid)
# Competition classes are migrated/backfilled by init_db(). Do not perform remote
# write-sync on every Streamlit rerun; explicit create/edit flows call sync as needed.
tournament_lifecycle = normalize_status(tournament["lifecycle_status"], is_published=bool(tournament["is_published"]))

with st.sidebar.expander("♿ Tillgänglighet", expanded=False):
    a11y_high_contrast = st.toggle("Hög kontrast", value=bool(st.session_state.get("a11y_high_contrast", False)), key="a11y_high_contrast")
    a11y_large_text = st.toggle("Större text", value=bool(st.session_state.get("a11y_large_text", False)), key="a11y_large_text")
    st.caption("CupNavi använder text + symboler, stora klickytor och tydliga fokusmarkeringar så färg aldrig är enda informationsbäraren.")

_a11y_css = []
if a11y_high_contrast:
    _a11y_css.append(".stApp{--cup-ink:#000!important;--cup-border:#475569!important;--cup-border-strong:#111827!important;} .stApp a{text-decoration:underline!important;} button{border-width:2px!important;}")
if a11y_large_text:
    _a11y_css.append(".stApp{font-size:1.08rem!important;} .stApp p,.stApp label,.stApp input,.stApp textarea,.stApp button{font-size:1.02rem!important;}")
_a11y_css.append("button,[role='button'],input,select,textarea{min-height:44px;} :focus-visible{outline:3px solid #2563EB!important;outline-offset:2px!important;} .cn-sr-only{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important;}")
if _a11y_css:
    st.markdown("<style>" + "".join(_a11y_css) + "</style><div class='cn-sr-only' role='status' aria-live='polite'>CupNavi är redo. Navigation och formulär kan användas med tangentbord och skärmläsare.</div>", unsafe_allow_html=True)


# Final datepicker contrast override. BaseWeb renders calendars in a portal
# outside the date input subtree, so theme inheritance must be neutralized there.
st.markdown("""
<style>
/* CUPNAVI CALENDAR FINAL OVERRIDE */
/* Streamlit/BaseWeb renders the datepicker in a portal. Keep the entire portal
   explicitly light so neither browser color-scheme nor app theme can create
   dark-on-dark weekday labels or black empty cells. */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="calendar"],
[data-baseweb="calendar"] > div {
  background:#ffffff !important;
  color:#172033 !important;
  color-scheme:light !important;
}

/* Default every calendar descendant to readable dark text. */
[data-baseweb="calendar"] *,
[data-baseweb="popover"] [data-baseweb="calendar"] * {
  color:#172033 !important;
  text-shadow:none !important;
}

/* Header, weekday strip and grid all stay light. */
[data-baseweb="calendar"] [role="banner"],
[data-baseweb="calendar"] [role="columnheader"],
[data-baseweb="calendar"] [role="grid"],
[data-baseweb="calendar"] [role="row"],
[data-baseweb="calendar"] [role="gridcell"],
[data-baseweb="calendar"] [role="gridcell"] > div,
[data-baseweb="calendar"] abbr {
  background:#ffffff !important;
  color:#172033 !important;
  opacity:1 !important;
}

/* Weekday labels must remain visibly distinct. */
[data-baseweb="calendar"] [role="columnheader"],
[data-baseweb="calendar"] abbr {
  font-weight:700 !important;
  color:#334155 !important;
}

/* Month/year controls and arrows. */
[data-baseweb="calendar"] button,
[data-baseweb="calendar"] select,
[data-baseweb="calendar"] [role="combobox"] {
  background:#ffffff !important;
  color:#172033 !important;
  border-color:#cbd5e1 !important;
  opacity:1 !important;
}
[data-baseweb="calendar"] svg,
[data-baseweb="calendar"] button svg {
  fill:#172033 !important;
  color:#172033 !important;
}

/* Every day cell is light by default: no black spacer/overflow blocks. */
[data-baseweb="calendar"] [role="gridcell"] button,
[data-baseweb="calendar"] [role="gridcell"] [role="button"],
[data-baseweb="calendar"] [role="gridcell"] > div {
  background:#ffffff !important;
  color:#172033 !important;
  opacity:1 !important;
  box-shadow:none !important;
}

/* Outside-month / disabled dates are muted, never black. */
[data-baseweb="calendar"] [aria-disabled="true"],
[data-baseweb="calendar"] [aria-disabled="true"] *,
[data-baseweb="calendar"] [data-disabled="true"],
[data-baseweb="calendar"] [data-disabled="true"] * {
  background:#f8fafc !important;
  color:#94a3b8 !important;
  opacity:1 !important;
}

/* Selected date keeps a clear CupNavi accent. */
[data-baseweb="calendar"] [aria-selected="true"],
[data-baseweb="calendar"] [aria-selected="true"] *,
[data-baseweb="calendar"] [data-selected="true"],
[data-baseweb="calendar"] [data-selected="true"] * {
  background:#166534 !important;
  color:#ffffff !important;
  font-weight:700 !important;
}

/* Focus remains visible for keyboard users. */
[data-baseweb="calendar"] :focus-visible {
  outline:3px solid #86efac !important;
  outline-offset:2px !important;
}

/* GLOBAL READABILITY PASS: secondary guidance must not disappear on the light
   CupNavi surface. This intentionally avoids changing buttons or input values. */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
.stCaption,
.stCaption p {
  color:#64748b !important;
  opacity:1 !important;
}
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
label[data-testid="stWidgetLabel"] {
  color:#334155 !important;
  opacity:1 !important;
  font-weight:600 !important;
}

/* PUBLIC VIEW POLISH V192 */
.cn-public-top-nav + div [data-testid="stHorizontalBlock"]{gap:8px!important}
.cn-public-top-nav + div [data-testid="stButton"] button{
  min-height:40px!important;border-radius:10px!important;
  font-size:.84rem!important;font-weight:700!important;box-shadow:none!important;
}
.cn-public-top-nav + div [data-testid="stButton"] button[kind="primary"]{
  background:#176b3a!important;color:#fff!important;border-color:#176b3a!important;
}
.cn-public-top-nav + div [data-testid="stButton"] button[kind="secondary"]{
  background:#fff!important;color:#334155!important;border-color:#d6dee6!important;
}
[data-testid="stExpander"]:has(.cn-public-filter-marker){
  border-color:#dbe4ea!important;background:#fff!important;border-radius:12px!important;
}

/* PUBLIC DENSITY & HIERARCHY V192 */
@media(min-width:901px){
  /* Reduce chrome above tournament content. */
  .stApp .block-container{padding-top:.35rem!important}
  .cn-mode-nav-safezone{height:8px!important}
  .cn-mode-nav-safezone + div{
    max-width:360px!important;
    margin-left:auto!important;
    margin-bottom:4px!important;
  }
  .cn-mode-nav-safezone + div [data-testid="stButton"] button{
    min-height:34px!important;
    font-size:.80rem!important;
    padding:4px 10px!important;
  }

  /* Tournament hero stays primary, but with less vertical padding. */
  .cup-hero{
    padding:10px 16px!important;
    margin:0 0 4px!important;
    border-radius:13px!important;
  }
  .cup-hero .title{font-size:25px!important;margin:1px 0 2px!important}
  .cup-hero .meta{font-size:12px!important}

  /* Follow-team control should read as a compact preference row. */
  .cn-public-follow-anchor + div{
    margin-top:0!important;
    margin-bottom:0!important;
  }
  .cn-public-follow-anchor + div [data-testid="stSelectbox"]{
    margin-bottom:0!important;
  }
  .cn-public-follow-anchor + div [data-testid="stWidgetLabel"]{
    margin-bottom:2px!important;
  }
  .cn-public-follow-anchor + div [data-testid="stWidgetLabel"] p{
    font-size:.78rem!important;
    line-height:1.15!important;
  }
  .cn-public-follow-anchor + div [data-baseweb="select"] > div{
    min-height:36px!important;
  }

  /* Local tournament navigation remains visible but secondary. */
  .cn-public-top-nav + div [data-testid="stButton"] button{
    min-height:36px!important;
    font-size:.80rem!important;
  }

  /* Compact the "now" strip. */
  .cn-live-strip{margin:3px 0 5px!important}
  .cn-live-head{padding:7px 10px!important;margin-bottom:6px!important;border-radius:12px!important}
  .cn-live-title{font-size:.68rem!important}
  .cn-live-subtitle{font-size:.74rem!important}
  .cn-live-card{padding:8px 10px!important;border-radius:11px!important}
  .cn-live-card-top{margin-bottom:4px!important}
  .cn-live-time{font-size:.92rem!important}
  .cn-live-date,.cn-live-pitch{font-size:.67rem!important}
  .cn-live-teams{font-size:.84rem!important}

  /* Summary metrics are utility chips, not cards. */
  .public-metric-grid{margin:4px 0 6px!important}
  .public-metric{padding:5px 8px!important;border-radius:8px!important}
  .public-metric .label{font-size:10px!important}
  .public-metric .value{font-size:15px!important}

  /* Completed match cards: substantially denser on desktop. */
  .public-match-card{
    margin:5px 0!important;
    padding:8px 10px!important;
    border-radius:10px!important;
    box-shadow:0 1px 4px rgba(15,23,42,.045)!important;
  }
  .public-match-card .public-team-name{
    font-size:14px!important;
    line-height:1.12!important;
  }
  .public-match-card .match-score{font-size:17px!important}
  .public-match-card .match-meta{font-size:10.5px!important}
  .public-match-card .kit-label{font-size:9px!important}
  .public-match-card .match-stage{
    font-size:9.5px!important;
    padding:2px 6px!important;
  }
  .public-match-card .status-pill{
    font-size:9px!important;
    padding:2px 6px!important;
  }
  .public-match-card .cn-match-events{
    margin-top:4px!important;
    padding-top:4px!important;
  }
  .public-match-card .cn-event-team{padding:3px 5px!important}
  .public-match-card .cn-event{
    font-size:10px!important;
    padding:2px 5px!important;
  }
  .public-match-secondary{
    margin-top:4px!important;
    gap:9px!important;
    font-size:10px!important;
  }

  /* Compress generic vertical gaps in the public area only. */
  .cn-public-follow-anchor ~ div [data-testid="stVerticalBlock"]{
    gap:.28rem!important;
  }
}

/* PUBLIC HEADER STRUCTURE FIX V192 */
@media(min-width:901px){
  .cn-public-follow-anchor + div{
    margin-top:-2px!important;
    margin-bottom:0!important;
  }
  .cn-public-follow-anchor + div [data-testid="stSelectbox"]{
    margin-top:0!important;
    margin-bottom:0!important;
  }
  .cn-public-follow-anchor + div [data-testid="stWidgetLabel"]{
    margin-bottom:1px!important;
  }
  .cn-public-follow-anchor + div [data-testid="stCaptionContainer"]{
    margin-top:0!important;
    margin-bottom:1px!important;
  }
}

/* SHARE POPOVER POLISH v1.195 */
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker),
[data-baseweb="popover"]:has(.cn-share-popover-marker) > div {
  background:#ffffff!important;
  color:#16231c!important;
  border:1px solid #d9e2dd!important;
  border-radius:14px!important;
  box-shadow:0 14px 36px rgba(16,24,20,.14)!important;
  color-scheme:light!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker){
  width:min(520px,calc(100vw - 24px))!important;
  max-width:min(520px,calc(100vw - 24px))!important;
  padding:16px!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stVerticalBlock"]{
  gap:10px!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) h3,
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) h4,
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) p,
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) span,
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) div{
  color:#16231c!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) h3{
  margin:0!important;
  font-size:1.08rem!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) h4{
  margin:4px 0 0!important;
  font-size:.92rem!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stCaptionContainer"] p{
  color:#5b6b62!important;
  font-size:.79rem!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) pre,
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) code{
  background:#f5f7f6!important;
  color:#17324d!important;
  border-color:#d9e2dd!important;
  font-size:.78rem!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stCode"]{
  background:#f5f7f6!important;
  border:1px solid #d9e2dd!important;
  border-radius:10px!important;
  overflow:hidden!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stLinkButton"] a,
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stDownloadButton"] button{
  background:#ffffff!important;
  color:#174d2f!important;
  border:1px solid #a9c6b5!important;
  min-height:40px!important;
  opacity:1!important;
  font-weight:700!important;
  box-shadow:none!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stLinkButton"] a *,
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stDownloadButton"] button *{
  color:#174d2f!important;
  opacity:1!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stLinkButton"] a:hover,
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stDownloadButton"] button:hover{
  background:#edf7f0!important;
  border-color:#67997a!important;
  color:#0f5a31!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) img{
  background:#ffffff!important;
  border:1px solid #d9e2dd!important;
  border-radius:10px!important;
  padding:6px!important;
}
[data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stHorizontalBlock"]{
  gap:10px!important;
}
@media(max-width:520px){
  [data-testid="stPopoverBody"]:has(.cn-share-popover-marker){
    width:calc(100vw - 16px)!important;
    max-width:calc(100vw - 16px)!important;
    padding:14px!important;
  }
  [data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stHorizontalBlock"]{
    gap:7px!important;
  }
  [data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stLinkButton"] a,
  [data-testid="stPopoverBody"]:has(.cn-share-popover-marker) [data-testid="stDownloadButton"] button{
    min-height:44px!important;
    font-size:.8rem!important;
    padding-left:8px!important;
    padding-right:8px!important;
  }
}
</style>
""", unsafe_allow_html=True)

def render_initial_tournament_setup(tournament_id, tournament):
    """Första konfigurationssidan efter skapande. Vanliga fält autosparas."""
    st.title("Setup av turneringen")
    st.caption("Bygg tävlingen från regler och hårda begränsningar till önskemål och optimering. Inställningarna autosparas.")
    st.info(f"**{tournament['name']}** · {tournament['sport']} · {cup_date_label(tournament)}")
    st.markdown(
        "<div class='cn-setup-flow'><b>1 Grund</b><span>→</span><b>2 Kapacitet</b><span>→</span>"
        "<b>3 Formatförslag</b><span>→</span><b>4 Regler</b><span>→</span>"
        "<b>5 Prioriteringar</b><span>→</span><b>6 Service</b><span>→</span><b>7 Kontroll</b></div>",
        unsafe_allow_html=True,
    )
    st.caption("HÅRT KRAV = får aldrig brytas · ÖNSKEMÅL = försöker uppfyllas · OPTIMERING = avgör vilket av flera giltiga scheman som är bäst.")
    rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
    if rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tournament_id,))
        rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

    _sport_rec=sport_setup_recommendation(_row_value(tournament,"sport","Fotboll"))
    st.markdown("### Sportprofil")
    _sp1,_sp2,_sp3,_sp4=st.columns(4)
    _sp1.metric("Sport",_sport_rec["display_name"])
    _sp2.metric("Format",f'{_sport_rec["periods"]} {_sport_rec["period_label"]}')
    _sp3.metric("Standardtid",f'{_sport_rec["minutes_per_period"]} min/{_sport_rec["period_label"].rstrip("er")}')
    _sp4.metric("Min. lagvila",f'{_sport_rec["minimum_rest_minutes"]} min')
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

    add_c1, add_c2, add_c3, add_c4 = st.columns([1.15, .9, .85, 1])
    setup_category = add_c1.selectbox("Kategori", list(YOUTH_CLASS_CATEGORIES), key=f"setup_class_category_{tournament_id}", disabled=_class_locked)
    setup_year = add_c2.selectbox("Födelseår", YOUTH_CLASS_YEARS, index=YOUTH_CLASS_YEARS.index(2014) if 2014 in YOUTH_CLASS_YEARS else 0, key=f"setup_class_year_{tournament_id}", disabled=_class_locked)
    setup_class_teams = add_c3.number_input("Planerade lag", 2, 200, 8, key=f"setup_class_teams_new_{tournament_id}", disabled=_class_locked)
    if add_c4.button("Lägg till tävlingsklass", key=f"setup_add_class_{tournament_id}", use_container_width=True, disabled=_class_locked):
        ok, message = add_competition_class(tournament_id, setup_category, setup_year, setup_class_teams)
        (st.success if ok else st.info)(message)
        st.rerun()

    class_rows = competition_classes(tournament_id)
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
        c1, c2, c3, c4, c5 = st.columns([1.6, .95, .9, .75, .75])
        c1.markdown(f"**{competition_class_label(row)}**")
        _actual_in_class=int(_team_count_by_class.get(int(row["id"]),0))
        saved_planned=max(_actual_in_class,int(_row_value(row,"planned_team_count",0) or 0))
        planned_key=f"setup_planned_class_teams_{row['id']}"
        planned_value=c2.number_input(
            "Planerade lag",
            min_value=max(2,_actual_in_class),
            max_value=200,
            value=max(2,saved_planned or 8),
            key=planned_key,
            label_visibility="collapsed",
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
        choice = c3.selectbox("Nivå", DIFFICULTY_LEVELS, index=DIFFICULTY_LEVELS.index(saved_diff), key=key, label_visibility="collapsed", disabled=_class_locked)
        if not _class_locked and choice != saved_diff:
            run("UPDATE competition_classes SET difficulty=? WHERE id=?", (choice, row["id"]))
            st.session_state[f"autosave_notice_{tournament_id}"] = "✓ Sparat automatiskt"
        c4.metric("Anmälda",_actual_in_class)
        if c5.button("Ta bort", key=f"setup_remove_class_{row['id']}", use_container_width=True, disabled=_class_locked):
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


def _render_with_friendly_error(renderer, *args):
    try:
        renderer(*args)
    except Exception as exc:
        context = getattr(renderer, "__name__", "page")
        record = safe_error_record(
            exc, context=context, app_version=APP_VERSION,
            tournament_id=int(args[0]) if args and isinstance(args[0], int) else None,
        )
        error_id = record["error_id"]
        try:
            with db() as con:
                persist_error(con, record)
                con.commit()
        except Exception as log_exc:
            print(f"[{error_id}] diagnostic persistence failed: {type(log_exc).__name__}: {log_exc}")
        st.error(f"Något gick fel när sidan skulle visas. Dina sparade uppgifter påverkas inte. Försök igen. Fel-ID: {error_id}")
        st.caption("Tekniska detaljer loggas internt. Ange Fel-ID om du kontaktar support.")
        print(f"[{error_id}] {type(exc).__name__}: {exc}")

if view_mode == "Lagportal":
    _render_with_friendly_error(render_team_portal, tid, tournament)
    st.stop()

if view_mode == "Matchrapportör":
    _render_with_friendly_error(render_match_reporter_view, tid, tournament)
    st.stop()

if view_mode == "Admin" and st.session_state.get("new_tournament_setup_id") == tid:
    render_initial_tournament_setup(tid, tournament)
    st.stop()

if view_mode == "Admin":
    st.title(f"🏆 {tournament['name']}")
    tournament_environment = str(_row_value(tournament, "environment_type", "production") or "production")
    if tournament_environment == "test":
        st.warning("🧪 TESTMILJÖ – denna cup är avsedd för test och kan raderas fritt.")
    admin_status_label = status_label(tournament_lifecycle, current_language())
    schedule_status_label = tr("Schema aktuellt") if not tournament["schedule_dirty"] else tr("Schema behöver uppdateras")
    st.markdown(
        f"<div class='cn-admin-status-strip'>"
        f"<span class='cn-admin-status-pill'>{html.escape(admin_status_label)}</span>"
        f"<span>{html.escape(schedule_status_label)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"{tournament['location'] or 'Spelort saknas'} · {cup_date_label(tournament)} · Planerat antal lag: {tournament['expected_team_count'] or 'Ej angivet'} (summa tävlingsklasser)")
    if tournament_lifecycle == "completed":
        st.success("🏆 Cupen är avslutad och ligger kvar som publik historik. Adminläget är skrivskyddat tills cupen återöppnas.")
        st.caption(f"Permanent publik identifierare: {tournament['public_slug'] or tournament['id']}")
        archive_col1, archive_col2 = st.columns(2)
        if archive_col1.button("↩️ Återöppna cup", type="primary", use_container_width=True, key=f"reopen_completed_{tid}"):
            run("UPDATE tournaments SET lifecycle_status='published',completed_at=NULL,is_published=1 WHERE id=?", (tid,))
            st.rerun()
        trash_confirm = archive_col2.checkbox("Tillåt flytt till papperskorg", key=f"archive_trash_confirm_{tid}")
        if archive_col2.button("🗑️ Flytta till papperskorg", disabled=not trash_confirm, use_container_width=True, key=f"archive_trash_{tid}"):
            run("UPDATE tournaments SET lifecycle_status='trashed',trashed_at=?,is_published=0 WHERE id=?", (datetime.now().isoformat(timespec="seconds"), tid))
            st.rerun()
        st.info("Växla till Turneringsvy för att se den arkiverade cupsidan precis som besökarna gör.")
        st.stop()
if view_mode == "Turneringsvy":
    _render_with_friendly_error(render_public_view, tid, tournament)
    st.stop()

# SNABB ADMINNAVIGERING: visuellt som flikar, men bara vald sida körs.
ADMIN_PAGES = [
    "Instruktioner", "Adminöversikt", "Cupinställningar", "Önskemålscentral", "Kontroller", "Problem & lösningar", "Lag", "Grupper", "Trupper", "Domare",
    "Skapa och publicera schema", "Tabeller", "Matcher och resultat",
    "Matchhändelser", "Slutspel", "Skytteligor", "Erbjudanden",
    "Sponsorer", "Funktionärer", "Import", "Besöksstatistik", "Cupverktyg",
]
ADMIN_NAV_GROUPS = [
    ("Översikt", [("Adminöversikt", tr("Översikt")), ("Cupinställningar", "Inställningar"), ("Kontroller", tr("Kontroller")), ("Problem & lösningar", "Problem"), ("Instruktioner", "Guide")]),
    ("Deltagare", [("Lag", tr("Lag")), ("Önskemålscentral", "Önskemål"), ("Grupper", tr("Grupper")), ("Trupper", tr("Trupper")), ("Import", tr("Import"))]),
    ("Matcher", [("Skapa och publicera schema", tr("Schema")), ("Matcher och resultat", "Resultat"), ("Matchhändelser", tr("Händelser")), ("Tabeller", tr("Tabeller")), ("Slutspel", tr("Slutspel")), ("Skytteligor", tr("Skytteligor"))]),
    ("Organisation", [("Domare", tr("Domare")), ("Funktionärer", tr("Funktionärer")), ("Cupverktyg", "Verktyg")]),
    ("Kommunikation", [("Erbjudanden", tr("Erbjudanden")), ("Sponsorer", tr("Sponsorer")), ("Besöksstatistik", tr("Besök"))]),
]
ADMIN_NAV = [item for _, items in ADMIN_NAV_GROUPS for item in items]
admin_page_key = f"admin_page_{tid}"
if st.session_state.get(admin_page_key) not in ADMIN_PAGES:
    st.session_state[admin_page_key] = "Adminöversikt"

st.markdown(
    f"<div class='cn-admin-section-label'>{html.escape(tr('Administration'))}</div>",
    unsafe_allow_html=True,
)

def _set_admin_page(page):
    st.session_state[admin_page_key] = page

# Två nivåer i adminnavigationen: fem tydliga huvudområden och bara relevanta
# underknappar för valt område. Det minskar knappmängden utan att gömma funktioner.
def _admin_group_for_page(page):
    for group_name, group_items in ADMIN_NAV_GROUPS:
        if any(item_page == page for item_page, _ in group_items):
            return group_name
    return "Översikt"

admin_group_key = f"admin_group_{tid}"
current_group = _admin_group_for_page(st.session_state[admin_page_key])
st.session_state[admin_group_key] = current_group

def _set_admin_group(group_name):
    st.session_state[admin_group_key] = group_name
    first_page = next(items[0][0] for name, items in ADMIN_NAV_GROUPS if name == group_name)
    st.session_state[admin_page_key] = first_page

group_names = [group_name for group_name, _ in ADMIN_NAV_GROUPS]
group_cols = st.columns(len(group_names))
for idx, group_name in enumerate(group_names):
    group_cols[idx].button(
        tr(group_name),
        key=f"admin_group_nav_{tid}_{group_name}",
        type="primary" if st.session_state[admin_group_key] == group_name else "secondary",
        use_container_width=True,
        on_click=_set_admin_group,
        args=(group_name,),
    )

selected_group = st.session_state[admin_group_key]
raw_items = next(items for group_name, items in ADMIN_NAV_GROUPS if group_name == selected_group)
# Logiska sammanslagningar i navigationen. Själva funktionerna ligger kvar som
# separata lätta vyer och växlas inne på den sammanslagna sidan.
if selected_group == "Kommunikation":
    nav_items = [("Sponsorer", "Partners"), ("Besöksstatistik", tr("Besök"))]
elif selected_group == "Matcher":
    nav_items = []
    for page_name, button_label in raw_items:
        if page_name == "Skytteligor":
            continue
        if page_name == "Tabeller":
            nav_items.append(("Tabeller", "Tabeller & statistik"))
        else:
            nav_items.append((page_name, button_label))
else:
    nav_items = raw_items

st.markdown(
    f"<div class='cn-admin-nav-group-title'>{html.escape(tr(selected_group))}</div>",
    unsafe_allow_html=True,
)

# Primära sidor visas direkt. Situationsbundna verktyg finns kvar under Fler verktyg.
# Detta minskar samtidig knappmängd utan att göra någon funktion oåtkomlig.
_ADMIN_PRIMARY_PAGES_BY_GROUP = {
    "Översikt": {"Adminöversikt", "Cupinställningar"},
    "Deltagare": {"Lag", "Grupper"},
    "Matcher": {"Skapa och publicera schema", "Matcher och resultat", "Tabeller", "Slutspel"},
    "Organisation": {"Domare"},
    "Kommunikation": {"Sponsorer"},
}

def _admin_nav_item_is_active(page_name):
    if page_name == "Sponsorer":
        return st.session_state[admin_page_key] in ("Sponsorer", "Erbjudanden")
    if page_name == "Tabeller":
        return st.session_state[admin_page_key] in ("Tabeller", "Skytteligor")
    return st.session_state[admin_page_key] == page_name

_primary_names = _ADMIN_PRIMARY_PAGES_BY_GROUP.get(selected_group, set())
_primary_nav_items = [item for item in nav_items if item[0] in _primary_names]
_more_nav_items = [item for item in nav_items if item[0] not in _primary_names]

if _primary_nav_items:
    nav_cols = st.columns(min(3, len(_primary_nav_items)))
    for nav_index, (page_name, button_label) in enumerate(_primary_nav_items):
        nav_col = nav_cols[nav_index % len(nav_cols)]
        nav_col.button(
            button_label,
            key=f"admin_nav_v194_primary_{tid}_{selected_group}_{page_name}",
            type="primary" if _admin_nav_item_is_active(page_name) else "secondary",
            use_container_width=True,
            on_click=_set_admin_page,
            args=(page_name,),
        )

if _more_nav_items:
    _advanced_active = any(_admin_nav_item_is_active(page_name) for page_name, _ in _more_nav_items)
    with st.expander("Fler verktyg", expanded=_advanced_active):
        _more_cols = st.columns(min(3, len(_more_nav_items)))
        for nav_index, (page_name, button_label) in enumerate(_more_nav_items):
            _more_col = _more_cols[nav_index % len(_more_cols)]
            _more_col.button(
                button_label,
                key=f"admin_nav_v194_more_{tid}_{selected_group}_{page_name}",
                type="primary" if _admin_nav_item_is_active(page_name) else "secondary",
                use_container_width=True,
                on_click=_set_admin_page,
                args=(page_name,),
            )

with st.expander("Sök i cupen", expanded=False):
    global_query = st.text_input(
        "Sök lag/deltagare, spelare, domare eller matchnummer",
        key=f"global_admin_search_{tid}",
        placeholder="Exempel: ÖSK, Andersson eller 12",
    ).strip()
    if len(global_query) >= 2:
        like_query = f"%{global_query}%"
        search_hits = []
        for row in all_rows("SELECT id,name FROM teams WHERE tournament_id=? AND name LIKE ? ORDER BY name LIMIT 8", (tid, like_query)):
            search_hits.append(("Lag", row["name"], "Lag"))
        for row in all_rows("SELECT players.id,players.name,teams.name AS team_name FROM players JOIN teams ON teams.id=players.team_id WHERE teams.tournament_id=? AND players.name LIKE ? ORDER BY players.name LIMIT 8", (tid, like_query)):
            search_hits.append(("Spelare", f"{row['name']} · {row['team_name']}", "Trupper"))
        for row in all_rows("SELECT id,name FROM referees WHERE tournament_id=? AND name LIKE ? ORDER BY name LIMIT 8", (tid, like_query)):
            search_hits.append(("Domare", row["name"], "Domare"))
        if global_query.isdigit():
            for row in all_rows("SELECT id,match_no,stage FROM matches WHERE tournament_id=? AND match_no=? ORDER BY id LIMIT 8", (tid, int(global_query))):
                search_hits.append(("Match", f"Match {row['match_no']} · {row['stage']}", "Matcher och resultat"))
        if search_hits:
            for hit_index, (kind, label, target_page) in enumerate(search_hits[:15]):
                hit_cols = st.columns([4, 1])
                hit_cols[0].markdown(f"**{html.escape(kind)}:** {html.escape(str(label))}")
                hit_cols[1].button(
                    "Öppna", key=f"global_hit_{tid}_{hit_index}", use_container_width=True,
                    on_click=_set_admin_page, args=(target_page,),
                )
        else:
            st.caption("Inga träffar i den aktiva cupen.")


admin_page = st.session_state[admin_page_key]
current_page_label = dict(ADMIN_NAV).get(admin_page, admin_page)

_flow_index = _primary_flow_index(admin_page)
_page_title, _page_copy = ADMIN_PAGE_COPY.get(admin_page, (current_page_label, "Administrera den här delen av cupen."))
_flow_counts = one_row(
    """SELECT
         (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
         (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
         (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n,
         (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL) AS scheduled_n,
         (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL) AS played_n""",
    (tid,tid,tid,tid,tid),
)
_flow_total = int(_flow_counts["matches_n"] or 0)
_flow_played = int(_flow_counts["played_n"] or 0)
_flow_scheduled = int(_flow_counts["scheduled_n"] or 0)

# Sidornas egna rubriker beskriver redan syftet. Globalt visar vi bara flödesläge
# och cupstatus på huvudflödets sidor, så att samma information inte upprepas.
if _flow_index is not None:
    _publish_class = "good" if tournament["is_published"] else "warn"
    _publish_text = "Publicerad" if tournament["is_published"] else "Utkast"
    _schedule_class = "warn" if tournament["schedule_dirty"] else ("good" if _flow_scheduled else "")
    _schedule_text = "Schema behöver uppdateras" if tournament["schedule_dirty"] else ("Schema klart" if _flow_scheduled else "Schema saknas")
    _result_class = "good" if _flow_total and _flow_played == _flow_total else ""
    _result_text = f"Resultat {_flow_played}/{_flow_total}" if _flow_total else "Inga matcher"
    st.markdown(
        f"<div class='cn-flow-context cn-flow-context-compact'>"
        f"<div class='cn-flow-kicker'>Steg {_flow_index + 1} av {len(ADMIN_PRIMARY_FLOW)}</div>"
        f"<div class='cn-flow-status'>"
        f"<span class='cn-flow-pill {_publish_class}'>● {html.escape(_publish_text)}</span>"
        f"<span class='cn-flow-pill {_schedule_class}'>🗓 {html.escape(_schedule_text)}</span>"
        f"<span class='cn-flow-pill {_result_class}'>✓ {html.escape(_result_text)}</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

if int(_flow_counts["teams_n"] or 0) == 0:
    _recommended_page, _recommended_label = "Lag", "Lägg till lag"
elif int(_flow_counts["groups_n"] or 0) == 0:
    _recommended_page, _recommended_label = "Grupper", "Skapa grupper"
elif _flow_scheduled == 0 or bool(tournament["schedule_dirty"]):
    _recommended_page, _recommended_label = "Skapa och publicera schema", "Skapa eller uppdatera schemat"
elif _flow_total and _flow_played < _flow_total:
    _recommended_page, _recommended_label = "Matcher och resultat", "Registrera och följ resultat"
else:
    _recommended_page, _recommended_label = "Tabeller", "Granska tabell och slutspel"

if _flow_index is not None and admin_page != _recommended_page:
    _next_copy_col, _next_button_col = st.columns([3, 2])
    _next_copy_col.markdown(
        f"<div class='cn-next-action'><b>Nästa steg</b><br><span>{html.escape(_recommended_label)}</span></div>",
        unsafe_allow_html=True,
    )
    _next_button_col.button(
        f"Fortsätt → {_recommended_label}",
        key=f"v160_recommended_{tid}_{admin_page}",
        type="primary",
        use_container_width=True,
        on_click=_set_admin_page,
        args=(_recommended_page,),
    )

if _flow_index is not None:
    st.divider()

current_schedule_dirty = bool(_row_value(tournament, "schedule_dirty", 0))
current_schedule_scheduled = _flow_scheduled
if current_schedule_dirty and current_schedule_scheduled:
    st.warning(
        "⚠️ Förutsättningarna för turneringen har ändrats efter att schemat skapades. "
        "Schemat är markerat som inaktuellt och bör regenereras under Schema innan det publiceras på nytt."
    )

# Publicering ska kunna hanteras från samtliga adminflikar.
# Valideringen cachas i sessionen och räknas bara om när något schema-/regelrelaterat ändrats.
sidebar_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
if sidebar_rules is None:
    run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
    sidebar_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))

sidebar_scheduled = _flow_scheduled

validation_cache_key = f"_schedule_validation_{tid}"
if sidebar_scheduled:
    if st.session_state.get("_validation_dirty", True) or validation_cache_key not in st.session_state:
        st.session_state[validation_cache_key] = validate_schedule(tid, tournament, sidebar_rules)
        st.session_state["_validation_dirty"] = False
    sidebar_errors, sidebar_warnings, _sidebar_quality = st.session_state.get(
        validation_cache_key, ([], [], [])
    )
else:
    sidebar_errors, sidebar_warnings, _sidebar_quality = ([], [], [])

st.sidebar.divider()
st.sidebar.subheader("Publicering")
if tournament["is_published"]:
    st.sidebar.success("Publicerad")
else:
    st.sidebar.caption("Turneringsvyn är ett utkast.")


def _is_advisory_schedule_warning(message):
    """Varningar som ska synas men aldrig blockera publicering."""
    lowered = (message or "").lower()
    return any(term in lowered for term in ("färgkrock", "tröjfärg", "färglikhet", "extraställ"))


blocking_sidebar_warnings = [
    warning for warning in sidebar_warnings
    if not _is_advisory_schedule_warning(warning)
]
advisory_sidebar_warnings = [
    warning for warning in sidebar_warnings
    if _is_advisory_schedule_warning(warning)
]

sidebar_warnings_approved = st.sidebar.checkbox(
    "Jag har granskat schemavarningarna",
    disabled=not bool(blocking_sidebar_warnings),
    key=f"sidebar_warning_approval_{tid}",
)
mobile_warnings_approved = bool(st.session_state.get(f"mobile_warning_approval_{tid}", False))
all_warnings_approved = bool(sidebar_warnings_approved or mobile_warnings_approved)

publish_blockers = []
if not tournament["playoff_model_confirmed"]:
    publish_blockers.append("Slutspelsmodell och cupregler måste sparas på Översikt.")
if not sidebar_scheduled:
    publish_blockers.append("Spelschema saknas. Generera schemat under Schema.")
if bool(tournament["schedule_dirty"]) and sidebar_scheduled:
    publish_blockers.append(
        "Schemat är inaktuellt eftersom förutsättningarna har ändrats. Regenerera schemat."
    )
if sidebar_errors:
    publish_blockers.append(
        f"{len(sidebar_errors)} blockerande schemafel måste åtgärdas."
    )
if blocking_sidebar_warnings and not all_warnings_approved:
    publish_blockers.append(
        f"{len(blocking_sidebar_warnings)} schemavarningar måste granskas och godkännas."
    )

sidebar_publish_blocked = bool(publish_blockers)


def _publish_tournament_now():
    """Publish only the tournament version currently rendered to Admin."""
    changed, reason = _set_publication_if_current(
        tid,
        expected_is_published=bool(tournament["is_published"]),
        expected_lifecycle=tournament_lifecycle,
        publish=True,
    )
    if changed:
        st.session_state["_validation_dirty"] = True
    return changed, reason


def _unpublish_tournament_now():
    return _set_publication_if_current(
        tid,
        expected_is_published=bool(tournament["is_published"]),
        expected_lifecycle=tournament_lifecycle,
        publish=False,
    )


if sidebar_publish_blocked:
    st.sidebar.error("Kan inte publicera ännu")
    for reason in publish_blockers:
        st.sidebar.markdown(f"• {reason}")

    if sidebar_errors:
        with st.sidebar.expander(f"Visa schemafel ({len(sidebar_errors)})"):
            for index, error in enumerate(sidebar_errors[:10], 1):
                st.markdown(f"**{index}.** {error}")
            if len(sidebar_errors) > 10:
                st.caption(f"Ytterligare {len(sidebar_errors) - 10} fel visas under Kontroller/Schema.")

    if blocking_sidebar_warnings:
        with st.sidebar.expander(f"Visa schemavarningar ({len(blocking_sidebar_warnings)})"):
            for index, warning in enumerate(blocking_sidebar_warnings[:10], 1):
                st.markdown(f"**{index}.** {warning}")
            if len(blocking_sidebar_warnings) > 10:
                st.caption(
                    f"Ytterligare {len(blocking_sidebar_warnings) - 10} varningar visas under Kontroller/Schema."
                )
else:
    st.sidebar.success("✓ Alla publiceringskrav är uppfyllda.")

if advisory_sidebar_warnings:
    with st.sidebar.expander(f"Notiser – blockerar inte ({len(advisory_sidebar_warnings)})"):
        for index, warning in enumerate(advisory_sidebar_warnings[:10], 1):
            st.markdown(f"**{index}.** {warning}")
        st.caption("Dessa notiser stoppar inte publicering.")

if st.sidebar.button(
    "Publicera",
    type="primary",
    use_container_width=True,
    disabled=sidebar_publish_blocked,
    key=f"publish_from_any_admin_page_{tid}",
):
    changed, publish_reason = _publish_tournament_now()
    if not changed:
        st.sidebar.warning("Publiceringsstatusen ändrades av en annan administratör. Senaste status laddas om.")
    st.rerun()

if st.sidebar.button(
    "Avpublicera",
    use_container_width=True,
    disabled=not tournament["is_published"],
    key=f"unpublish_from_any_admin_page_{tid}",
):
    changed, publish_reason = _unpublish_tournament_now()
    if not changed:
        st.sidebar.warning("Publiceringsstatusen ändrades av en annan administratör. Senaste status laddas om.")
    st.rerun()

# v159: Publicering får inte vara beroende av sidebaren. På mobil ligger denna
# kontroll direkt i huvudinnehållet och använder exakt samma validering.
with st.container(border=True):
    st.markdown("#### 📣 Publicering")
    if tournament["is_published"]:
        st.success("Turneringen är publicerad. Sparade resultat visas automatiskt i turneringsvyn.")
    else:
        st.caption("Turneringsvyn är fortfarande ett utkast tills du publicerar den.")

    if blocking_sidebar_warnings:
        st.checkbox(
            "Jag har granskat schemavarningarna",
            key=f"mobile_warning_approval_{tid}",
        )

    if sidebar_publish_blocked:
        st.warning("Kan inte publicera ännu: " + " ".join(publish_blockers))

    mobile_publish_col, mobile_unpublish_col = st.columns(2)
    if mobile_publish_col.button(
        "📣 Publicera / uppdatera publik vy",
        type="primary",
        use_container_width=True,
        disabled=sidebar_publish_blocked,
        key=f"mobile_publish_from_admin_{tid}",
    ):
        changed, publish_reason = _publish_tournament_now()
        st.session_state["mobile_publish_message"] = (
            "✓ Turneringsvyn är publicerad och synkad."
            if changed
            else "Publiceringsstatusen ändrades av en annan administratör. Senaste status har laddats."
        )
        st.rerun()
    if mobile_unpublish_col.button(
        "Avpublicera",
        use_container_width=True,
        disabled=not tournament["is_published"],
        key=f"mobile_unpublish_from_admin_{tid}",
    ):
        changed, publish_reason = _unpublish_tournament_now()
        if not changed:
            st.session_state["mobile_publish_message"] = "Publiceringsstatusen ändrades av en annan administratör. Senaste status har laddats."
        st.rerun()
    if "mobile_publish_message" in st.session_state:
        st.success(st.session_state.pop("mobile_publish_message"))

# Cupens livscykel: publicerad -> pågår -> avslutad. Avslutad cup blir skrivskyddad
# i admin men ligger kvar publikt tills admin uttryckligen flyttar den till papperskorgen.
if tournament_lifecycle == "published" and tournament["is_published"]:
    if st.sidebar.button("🔴 Markera cupen som pågående", use_container_width=True, key=f"mark_live_{tid}"):
        changed, lifecycle_reason = _set_lifecycle_if_current(
            tid,
            "published",
            "live",
            expected_is_published=1,
        )
        if not changed:
            st.sidebar.warning("Cupstatusen ändrades av en annan administratör. Senaste status laddas om.")
        st.rerun()

lifecycle_counts = one_row(
    "SELECT COUNT(*) AS total, SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS played "
    "FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=1",
    (tid,),
)
life_total = int(lifecycle_counts["total"] or 0) if lifecycle_counts else 0
life_played = int(lifecycle_counts["played"] or 0) if lifecycle_counts else 0
cup_can_complete = life_total > 0 and life_played == life_total and tournament_lifecycle in ("published", "live")
if tournament_lifecycle in ("published", "live"):
    if not cup_can_complete:
        st.sidebar.caption(f"Avsluta cup: {life_played}/{life_total} publicerade matcher färdigrapporterade.")
    if st.sidebar.button("🏁 Avsluta cup", disabled=not cup_can_complete, use_container_width=True, key=f"complete_cup_{tid}"):
        changed, lifecycle_reason = _set_lifecycle_if_current(
            tid,
            tournament_lifecycle,
            "completed",
            expected_is_published=1,
        )
        if changed:
            add_feed_item(tid, "Cupen är avslutad", "Resultat och statistik finns kvar i CupNavi-historiken.", category="Cup")
        else:
            st.sidebar.warning("Cupstatusen ändrades av en annan administratör. Cupen avslutades inte från den här äldre vyn.")
        st.rerun()


def _demo_distribute_count(total, players):
    """Fördela ett heltalsantal slumpmässigt över spelare."""
    if total <= 0 or not players:
        return {}
    counts = {player["id"]: 0 for player in players}
    for _ in range(total):
        chosen = random.choice(players)
        counts[chosen["id"]] += 1
    return {player_id: count for player_id, count in counts.items() if count}


def _demo_write_match_stats(match_id, team_id, goals, con):
    """Skapa fiktiva mål/assist/kort för ett lag i en redan resultatsatt match."""
    players = _rows_from_cursor(
        con.execute(
            "SELECT id,name FROM players WHERE team_id=? ORDER BY player_number,name",
            (team_id,),
        )
    )
    if not players:
        return 0

    goal_map = _demo_distribute_count(goals, players)

    # Alla mål behöver inte ha assist. Antalet assist kan aldrig överstiga antalet mål.
    assist_total = random.randint(0, goals) if goals > 0 else 0
    assist_map = _demo_distribute_count(assist_total, players)

    # Kortdata är separat från mål/assist.
    yellow_total = random.choices([0, 1, 2, 3], weights=[45, 35, 15, 5], k=1)[0]
    red_total = random.choices([0, 1], weights=[92, 8], k=1)[0]
    yellow_map = _demo_distribute_count(yellow_total, players)
    red_map = _demo_distribute_count(red_total, players)

    all_player_ids = set(goal_map) | set(assist_map) | set(yellow_map) | set(red_map)
    for player_id in all_player_ids:
        con.execute(
            """
            INSERT INTO player_match_stats(match_id,player_id,goals,assists,yellow_cards,red_cards)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(match_id,player_id)
            DO UPDATE SET goals=excluded.goals,
                          assists=excluded.assists,
                          yellow_cards=excluded.yellow_cards,
                          red_cards=excluded.red_cards
            """,
            (
                match_id,
                player_id,
                goal_map.get(player_id, 0),
                assist_map.get(player_id, 0),
                yellow_map.get(player_id, 0),
                red_map.get(player_id, 0),
            ),
        )
    return len(all_player_ids)


def _demo_generate_group_results(tournament_id, *, fraction=1.0):
    """Slumpa resultat och matchhändelser för en vald andel gruppspelsmatcher."""
    group_matches = all_rows(
        """SELECT * FROM matches
           WHERE tournament_id=? AND stage='Gruppspel'
           ORDER BY COALESCE(scheduled_start,''),group_id,match_no,id""",
        (tournament_id,),
    )
    if not group_matches:
        return 0, 0, "Inga gruppspelsmatcher finns ännu. Generera spelschemat först."

    fraction = max(0.0, min(1.0, float(fraction)))
    target_count = len(group_matches) if fraction >= 1.0 else max(1, int((len(group_matches) * fraction) + 0.5))
    selected_matches = group_matches[:target_count]
    generated = 0
    stat_rows = 0
    with db() as con:
        for match_row in selected_matches:
            home_id = resolve_source(match_row["home_source"])
            away_id = resolve_source(match_row["away_source"])
            if not home_id or not away_id:
                continue

            # Rimliga testresultat med både målsnåla och målglada matcher.
            home_score = random.choices([0,1,2,3,4,5], weights=[14,25,25,19,11,6], k=1)[0]
            away_score = random.choices([0,1,2,3,4,5], weights=[16,27,24,18,10,5], k=1)[0]

            con.execute(
                """UPDATE matches
                   SET home_score=?,away_score=?,home_penalties=NULL,away_penalties=NULL,decided_winner_id=NULL
                   WHERE id=?""",
                (home_score, away_score, match_row["id"]),
            )
            con.execute("DELETE FROM player_match_stats WHERE match_id=?", (match_row["id"],))
            stat_rows += _demo_write_match_stats(match_row["id"], home_id, home_score, con)
            stat_rows += _demo_write_match_stats(match_row["id"], away_id, away_score, con)
            generated += 1
        con.commit()

    _clear_render_query_cache()
    return generated, stat_rows, None


def _demo_generate_playoff_results(tournament_id, *, fraction=1.0):
    """Slumpa en vald andel slutspelsresultat i spelordning så vinnare går vidare."""
    playoff_matches = all_rows(
        """SELECT * FROM matches
           WHERE tournament_id=? AND stage<>'Gruppspel'
           ORDER BY round_no,match_no,id""",
        (tournament_id,),
    )
    if not playoff_matches:
        return 0, 0, "Inga slutspelsmatcher finns ännu. Generera spelschemat först."

    fraction = max(0.0, min(1.0, float(fraction)))
    target_count = len(playoff_matches) if fraction >= 1.0 else max(1, int((len(playoff_matches) * fraction) + 0.5))
    playoff_matches = playoff_matches[:target_count]

    tournament_row = one_row("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
    tie_rule = tournament_row["playoff_tie_rule"] or "Straffar direkt"
    generated = 0
    stat_rows = 0
    skipped = 0

    # Kör match för match och commit:a varje resultat så winner:<match-id>
    # kan lösas direkt i efterföljande semifinal/final.
    for match_stub in playoff_matches:
        _clear_render_query_cache()
        match_row = one_row("SELECT * FROM matches WHERE id=?", (match_stub["id"],))
        home_id = resolve_source(match_row["home_source"])
        away_id = resolve_source(match_row["away_source"])
        if not home_id or not away_id:
            skipped += 1
            continue

        # Cirka 25 % av matcherna går till oavgjort i ordinarie tid så
        # straff/lottning också får testdata.
        if random.random() < 0.25:
            score = random.choice([0, 1, 2, 3])
            home_score = away_score = score
        else:
            home_score = random.choices([0,1,2,3,4], weights=[15,28,27,20,10], k=1)[0]
            away_score = random.choices([0,1,2,3,4], weights=[15,28,27,20,10], k=1)[0]
            if home_score == away_score:
                if random.random() < 0.5:
                    home_score += 1
                else:
                    away_score += 1

        home_penalties = away_penalties = decided_winner_id = None
        if home_score == away_score:
            if tie_rule == "Lottning":
                decided_winner_id = random.choice([home_id, away_id])
            else:
                winner_home = random.random() < 0.5
                base = random.randint(3, 5)
                if winner_home:
                    home_penalties, away_penalties = base, base - 1
                else:
                    home_penalties, away_penalties = base - 1, base

        with db() as con:
            con.execute(
                """UPDATE matches
                   SET home_score=?,away_score=?,home_penalties=?,away_penalties=?,decided_winner_id=?
                   WHERE id=?""",
                (
                    home_score,
                    away_score,
                    home_penalties,
                    away_penalties,
                    decided_winner_id,
                    match_row["id"],
                ),
            )
            con.execute("DELETE FROM player_match_stats WHERE match_id=?", (match_row["id"],))
            stat_rows += _demo_write_match_stats(match_row["id"], home_id, home_score, con)
            stat_rows += _demo_write_match_stats(match_row["id"], away_id, away_score, con)
            con.commit()

        _clear_render_query_cache()
        generated += 1

    warning = None
    if skipped:
        warning = (
            f"{skipped} slutspelsmatcher kunde inte fyllas eftersom deltagande lag ännu inte kunde avgöras. "
            "Kontrollera att gruppspelet är färdigspelat och kör sedan knappen igen."
        )
    return generated, stat_rows, warning



def _demo_reset_results(tournament_id):
    """Nollställ testresultat/händelser utan att röra schema eller grunddata."""
    with db() as con:
        con.execute(
            """DELETE FROM player_match_stats
               WHERE match_id IN (SELECT id FROM matches WHERE tournament_id=?)""",
            (tournament_id,),
        )
        con.execute(
            """UPDATE matches SET home_score=NULL,away_score=NULL,home_penalties=NULL,away_penalties=NULL,decided_winner_id=NULL
               WHERE tournament_id=?""",
            (tournament_id,),
        )
        con.commit()
    _clear_render_query_cache()


def _demo_apply_safe_schedule_capacity(tournament_id, tournament_row):
    """Ge en Testmiljö reproducerbar kapacitet när democupen annars inte får plats.

    Detta används alltid i CUPNAVI_E2E och som fallback i vanliga Testmiljöer.
    Riktiga cuper påverkas aldrig.
    """
    if not is_test_environment(tournament_row):
        return one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

    run(
        """UPDATE schedule_rules
           SET pitch_count=CASE WHEN pitch_count < 8 THEN 8 ELSE pitch_count END,
               first_match_time='07:00',
               latest_kickoff_time='23:00',
               pitch_break_minutes=0,
               avoid_consecutive_matches=0,
               consecutive_match_break_minutes=0,
               referee_mode='Manuell'
           WHERE tournament_id=?""",
        (tournament_id,),
    )
    # Viktigt: pitch_day_windows ärver tider från tournament_day_windows. Tidigare
    # raderades bara planfönstren, vilket gjorde att de direkt återskapades från
    # gamla 09:00–18:00-fönster och den "säkra" kapaciteten aldrig fick effekt.
    run("DELETE FROM pitch_day_windows WHERE tournament_id=?", (tournament_id,))
    run("DELETE FROM tournament_day_windows WHERE tournament_id=?", (tournament_id,))
    rules_row = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
    ensure_tournament_day_windows(
        tournament_id,
        tournament_row,
        rules_row["first_match_time"],
        rules_row["latest_kickoff_time"],
    )
    ensure_pitch_day_windows(
        tournament_id,
        tournament_row,
        int(rules_row["pitch_count"]),
        rules_row["first_match_time"],
        rules_row["latest_kickoff_time"],
    )
    return one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))


def _demo_prepare_schedule(tournament_id):
    """Säkerställ gruppmöten, slutspel och ett faktiskt genomförbart demoschema."""
    tournament_row = one_row("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
    rules_row = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))
    if rules_row is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tournament_id,))
        rules_row = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tournament_id,))

    # CI måste vara helt deterministiskt. En nyskapad endagscup kan annars skapa
    # gruppmatcherna men fastna före resultat/publicering om plantiderna är för snäva.
    if os.environ.get("CUPNAVI_E2E") == "1" and is_test_environment(tournament_row):
        rules_row = _demo_apply_safe_schedule_capacity(tournament_id, tournament_row)

    create_all_group_matches(tournament_id)
    playoff_ok, playoff_error = ensure_playoffs_for_schedule(tournament_id, tournament_row)
    if not playoff_ok:
        return False, playoff_error

    count, unresolved, warning = generate_schedule(tournament_id, tournament_row, rules_row)

    # Vanliga Testmiljöer ska också vara lätta att experimentera i. Om användarens
    # plantider inte räcker får demomotorn en enda säker fallback i stället för att
    # lämna cupen halvbyggd med matcher men utan resultat.
    if unresolved and is_test_environment(tournament_row):
        rules_row = _demo_apply_safe_schedule_capacity(tournament_id, tournament_row)
        count, unresolved, retry_warning = generate_schedule(
            tournament_id, tournament_row, rules_row
        )
        warning = retry_warning or warning

    if unresolved:
        return False, warning or f"{unresolved} matcher kunde inte schemaläggas."
    return True, warning


def _demo_apply_progress_level(tournament_id, level):
    """Bygg ett reproducerbart testläge från halv grupp till helt avslutad cup."""
    ok, warning = _demo_prepare_schedule(tournament_id)
    if not ok:
        return False, warning

    _demo_reset_results(tournament_id)
    now_iso = datetime.now().isoformat(timespec="seconds")
    run(
        "UPDATE tournaments SET is_published=1,lifecycle_status='live',completed_at=NULL WHERE id=?",
        (tournament_id,),
    )

    if level == "half_group":
        group_generated, _, group_warning = _demo_generate_group_results(tournament_id, fraction=0.5)
        return True, group_warning or f"Halva gruppspelet är testspelat ({group_generated} matcher)."

    group_generated, _, group_warning = _demo_generate_group_results(tournament_id, fraction=1.0)
    if group_warning:
        return False, group_warning

    if level == "full_group":
        return True, f"Hela gruppspelet är testspelat ({group_generated} matcher). Slutspel återstår."

    playoff_fraction = 0.5 if level == "half_playoff" else 1.0
    playoff_generated, _, playoff_warning = _demo_generate_playoff_results(
        tournament_id, fraction=playoff_fraction
    )
    if level == "half_playoff":
        return True, playoff_warning or f"Gruppspelet och halva slutspelet är testspelat ({playoff_generated} slutspelsmatcher)."

    if playoff_warning:
        return False, playoff_warning
    run(
        "UPDATE tournaments SET lifecycle_status='completed',completed_at=? WHERE id=?",
        (now_iso, tournament_id),
    )
    add_feed_item(
        tournament_id,
        "Democupen är färdigspelad",
        "Alla grupp- och slutspelsmatcher har testresultat.",
        category="Resultat",
        public=True,
    )
    return True, f"Hela cupen är färdigspelad i testdata ({group_generated} gruppmatcher, {playoff_generated} slutspelsmatcher)."



def _admin_workflow_counts(tournament_id):
    # Samla dashboardens vanligaste räknare i ett enda Turso-anrop.
    return one_row(
        """SELECT
          (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
          (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
          (SELECT COUNT(*) FROM players p JOIN teams t ON t.id=p.team_id WHERE t.tournament_id=?) AS players_n,
          (SELECT COUNT(*) FROM referees WHERE tournament_id=?) AS refs_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL) AS played_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND referee_id IS NULL) AS missing_refs_n,
          (SELECT COUNT(*) FROM teams WHERE tournament_id=? AND COALESCE(checked_in,0)=0) AS unchecked_n
        """,
        (tournament_id, tournament_id, tournament_id, tournament_id, tournament_id, tournament_id, tournament_id, tournament_id),
    )


def _admin_workflow_step(title, state, meta):
    css_class = "done" if state == "done" else ("warn" if state == "warn" else "todo")
    icon = "✓" if state == "done" else ("⚠" if state == "warn" else "○")
    return (
        f"<div class='cn-step {css_class}'>"
        f"<div class='title'>{icon} {html.escape(title)}</div>"
        f"<div class='meta'>{html.escape(meta)}</div>"
        "</div>"
    )



if admin_page == "Instruktioner":
    st.header("Instruktioner")
    st.caption(
        "En steg-för-steg-guide för dig som administrerar en cup för första gången. "
        "Guiden läser av den valda turneringen och ändrar status och nästa rekommenderade steg automatiskt."
    )

    guide_counts = _admin_workflow_counts(tid)
    guide_expected = int(tournament["expected_team_count"] or 0)
    guide_scheduled = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
        (tid,),
    )["n"]
    guide_published = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND schedule_published=1",
        (tid,),
    )["n"]
    guide_events = one_row(
        """SELECT COUNT(*) AS n
           FROM player_match_stats s
           JOIN matches m ON m.id=s.match_id
           WHERE m.tournament_id=?
             AND (s.goals>0 OR s.assists>0 OR s.yellow_cards>0 OR s.red_cards>0)""",
        (tid,),
    )["n"]

    guide_steps = [
        {
            "title": "1. Grundinställningar",
            "page": "Adminöversikt",
            "done": bool(tournament["name"]) and guide_expected > 0,
            "text": (
                "Börja på Översikt. Ange cupens grunduppgifter, maximalt/planerat antal lag, "
                "datum och plantider. Här bestämmer du också tabellregler, slutspelsmodell och "
                "hur oavgjorda slutspelsmatcher ska avgöras."
            ),
        },
        {
            "title": "2. Registrera lag",
            "page": "Lag",
            "done": guide_counts["teams_n"] > 0 and (guide_expected == 0 or guide_counts["teams_n"] >= guide_expected),
            "text": (
                f"Registrera deltagande lag och deras hemma- och bortaställ. "
                f"Just nu finns {guide_counts['teams_n']} lag registrerade"
                + (f" av {guide_expected} planerade." if guide_expected else ".")
            ),
        },
        {
            "title": "3. Skapa grupper",
            "page": "Grupper",
            "done": guide_counts["groups_n"] > 0,
            "text": (
                f"Skapa grupper och placera lagen i rätt grupp. "
                f"Just nu finns {guide_counts['groups_n']} grupper."
            ),
        },
        {
            "title": "4. Lägg in trupper",
            "page": "Trupper",
            "done": guide_counts["players_n"] > 0,
            "text": (
                f"Lägg in spelarna under respektive lag. Trupper behövs för att kunna registrera "
                f"mål, assist och kort på rätt spelare. {guide_counts['players_n']} spelare är registrerade."
            ),
        },
        {
            "title": "5. Registrera domare",
            "page": "Domare",
            "done": guide_counts["refs_n"] > 0,
            "text": (
                f"Lägg in de domare som ska användas. CupNavi kan sedan tilldela dem i schemat. "
                f"{guide_counts['refs_n']} domare är registrerade."
            ),
        },
        {
            "title": "6. Skapa och kontrollera schemat",
            "page": "Skapa och publicera schema",
            "done": guide_scheduled > 0 and not bool(tournament["schedule_dirty"]),
            "text": (
                f"När lag, grupper och regler är klara skapar du schemat. Slutspelsmatcherna skapas "
                f"samtidigt. Kontrollera därefter tider, planer, vila och domare. "
                f"{guide_scheduled} matcher är schemalagda."
                + (" Schemat behöver regenereras efter en ändring." if tournament["schedule_dirty"] and guide_scheduled else "")
            ),
        },
        {
            "title": "7. Kontrollera innan publicering",
            "page": "Kontroller",
            "done": guide_scheduled > 0 and not bool(tournament["schedule_dirty"]),
            "text": (
                "Öppna Kontroller och gå igenom blockerande fel och varningar. Varningar är sådant "
                "du bör granska; blockerande fel måste rättas innan publicering."
            ),
        },
        {
            "title": "8. Publicera cupen",
            "page": "Skapa och publicera schema",
            "done": bool(tournament["is_published"]) and guide_published > 0,
            "text": (
                "När schemat är godkänt publicerar du cupen. Publiceringsfunktionen finns tillgänglig "
                "i adminläget även när du arbetar på andra flikar. Den publika turneringsvyn visar sedan "
                "spelschema, tabeller, resultat, slutspel och övrig information."
            ),
        },
        {
            "title": "9. Under turneringen – registrera resultat",
            "page": "Matcher och resultat",
            "done": guide_counts["played_n"] > 0,
            "text": (
                f"På Matcher registrerar du slutresultaten. De sparas automatiskt när de matas in. "
                f"{guide_counts['played_n']} av {guide_counts['matches_n']} matcher har resultat."
            ),
        },
        {
            "title": "10. Registrera matchhändelser",
            "page": "Matchhändelser",
            "done": guide_events > 0,
            "text": (
                f"På Händelser registrerar du mål, assist, gula kort och röda kort. Händelserna sparas "
                f"automatiskt och används i den publika resultatvyn och topplistorna. "
                f"{guide_events} spelarhändelser finns registrerade."
            ),
        },
        {
            "title": "11. Följ tabeller, slutspel och topplistor",
            "page": "Tabeller",
            "done": guide_counts["played_n"] > 0,
            "text": (
                "Tabeller räknas från registrerade resultat. Slutspelsplatser och kommande motstånd "
                "uppdateras utifrån cupens regler. Kontrollera även Slutspel och Skytteligor under cupens gång."
            ),
        },
        {
            "title": "12. Lägg in erbjudanden för deltagarna",
            "page": "Erbjudanden",
            "done": one_row("SELECT COUNT(*) AS n FROM offers WHERE tournament_id=? AND active=1", (tid,))["n"] > 0,
            "text": (
                "På Erbjudanden kan du lägga upp lokala förmåner för cupdeltagare, till exempel "
                "restaurangrabatter eller rabattkoder. Aktiva erbjudanden visas i en egen flik i turneringsvyn."
            ),
        },
        {
            "title": "13. Importera lag eller trupper vid behov",
            "page": "Import",
            "done": guide_counts["teams_n"] > 0,
            "text": (
                "På Import kan du läsa in många lag eller spelare från CSV/XLSX. "
                "Använd gärna de nedladdningsbara mallarna och kontrollera förhandsgranskningen innan import."
            ),
        },
        {
            "title": "14. Lägg in sponsorer och funktionärer",
            "page": "Sponsorer",
            "done": one_row("SELECT COUNT(*) AS n FROM sponsors WHERE tournament_id=? AND active=1", (tid,))["n"] > 0
                    or one_row("SELECT COUNT(*) AS n FROM functionaries WHERE tournament_id=? AND active=1", (tid,))["n"] > 0,
            "text": (
                "På Sponsorer administrerar du cupens partners. På Funktionärer registrerar du sekretariat, "
                "planvärdar och andra roller. Publika kontakter kan visas i turneringsvyn."
            ),
        },
        {
            "title": "15. Följ besöksstatistiken",
            "page": "Besöksstatistik",
            "done": one_row("SELECT COUNT(*) AS n FROM visitor_sessions WHERE tournament_id=?", (tid,))["n"] > 0,
            "text": (
                "Under Besök ser du hur många som använder den publika cupsidan, sidvisningar över tid, "
                "enheter, webbläsare och trafikkällor. Ingen IP-adress lagras."
            ),
        },
        {
            "title": "16. Exportera scheman",
            "page": "Skapa och publicera schema",
            "done": guide_scheduled > 0,
            "text": (
                "På Schema kan du skapa ett komplett PDF-paket för utskrift. Det innehåller hela schemat "
                "samt separata grupp-, lag-, plan-, slutspels- och domarscheman."
            ),
        },
    ]

    completed_steps = sum(1 for step in guide_steps if step["done"])
    guide_progress = completed_steps / len(guide_steps)
    st.progress(guide_progress, text=f"{completed_steps} av {len(guide_steps)} steg har påbörjats eller slutförts")

    next_step = next((step for step in guide_steps if not step["done"]), None)
    if next_step:
        st.info(f"**Rekommenderat nästa steg:** {next_step['title']} – {next_step['text']}")
        if st.button(
            f"Gå till {next_step['page'].replace('Skapa och publicera schema', 'Schema').replace('Matcher och resultat', 'Matcher').replace('Matchhändelser', 'Händelser')}",
            type="primary",
            key=f"guide_next_{tid}",
        ):
            st.session_state[admin_page_key] = next_step["page"]
            st.rerun()
    else:
        st.success("Grundflödet är genomfört. Fortsätt administrera resultat, händelser och slutspel under cupen.")

    st.markdown("### Så arbetar du i CupNavi")
    for step_index, step in enumerate(guide_steps, start=1):
        icon = "✓" if step["done"] else "○"
        status = "Klart/aktivt" if step["done"] else "Återstår"
        with st.expander(f"{icon} {step['title']} · {status}", expanded=bool(next_step and step["title"] == next_step["title"])):
            st.write(step["text"])
            if st.button(
                f"Öppna {step['page'].replace('Skapa och publicera schema', 'Schema').replace('Matcher och resultat', 'Matcher').replace('Matchhändelser', 'Händelser')}",
                key=f"guide_open_{tid}_{step_index}_{step['page']}",
            ):
                st.session_state[admin_page_key] = step["page"]
                st.rerun()

    st.markdown("### Viktigt att känna till")
    st.markdown(
        """
        - **Ändrar du lag, grupper, regler eller andra schemaförutsättningar efter att schemat skapats** kan schemat markeras som inaktuellt. Regenerera det då på **Schema**.
        - **Färgkrockar är en varning, inte ett stopp.** CupNavi försöker välja hemma/borta och matchställ så att krockarna blir så få som möjligt.
        - **Resultat och matchhändelser sparas automatiskt.** Den gröna bekräftelsen visar att ändringen är sparad.
        - **Publicering valideras innan den genomförs.** Om något blockerar publiceringen ska CupNavi tala om exakt vad som behöver rättas.
        - **Matcher är samlade på en publik sida.** Kommande och spelade matcher visas i samma flöde, med resultat och registrerade händelser när de finns.
        """
    )
    st.caption(
        "Den här sidan bygger sin status från turneringens aktuella data. "
        "När CupNavi får nya arbetssteg eller funktioner ska motsvarande instruktion uppdateras tillsammans med funktionen."
    )


elif admin_page == "Adminöversikt":
    st.header("Adminöversikt")
    current_admin_mode = admin_mode(tournament["start_date"], tournament["end_date"], tournament_lifecycle)
    mode_labels = {
        "planning": "Planeringsläge",
        "live": "🔴 Cupdagsläge",
        "after": "🏆 Efter cupen",
    }
    st.caption(f"**{mode_labels.get(current_admin_mode, 'Planeringsläge')}** · följ nästa rekommenderade steg och öppna detaljer vid behov.")

    # v139: uppgiftsbaserad Organizer-vy. Den kompletterar navigationen och visar
    # vad arrangören faktiskt behöver göra, inte bara vilka funktioner som finns.
    _v139_counts = _admin_workflow_counts(tid)
    _v139_class_rows = competition_classes(tid)
    _v139_classes = len(_v139_class_rows)
    _v139_pitches = one_row("SELECT COUNT(*) AS n FROM pitches WHERE tournament_id=?", (tid,))
    _v139_rules = sidebar_rules
    _v139_rules_ready = bool(
        _v139_rules
        and int(_row_value(_v139_rules, "halves", 0) or 0) > 0
        and int(_row_value(_v139_rules, "minutes_per_half", 0) or 0) > 0
        and int(_row_value(_v139_rules, "pitch_count", 0) or 0) > 0
        and int(_row_value(_v139_rules, "minimum_team_rest_minutes", 0) or 0) >= 0
    )
    _v139_planned_total = sum(max(0,int(_row_value(row,"planned_team_count",0) or 0)) for row in _v139_class_rows)
    _v139_expected_total = max(_v139_planned_total, int(_v139_counts["teams_n"] or 0))
    _v139_steps = organizer_workflow(
        competition_classes=_v139_classes,
        teams=int(_v139_counts["teams_n"] or 0),
        expected_teams=_v139_expected_total,
        groups=int(_v139_counts["groups_n"] or 0),
        pitches=int(_row_value(_v139_pitches, "n", 0) or 0),
        rules_ready=_v139_rules_ready,
        matches=int(_v139_counts["matches_n"] or 0),
        schedule_dirty=bool(tournament["schedule_dirty"]),
        published=bool(tournament["is_published"]),
    )
    _v139_summary = workflow_summary(_v139_steps)
    with st.expander("Förberedelser i detalj", expanded=False):
        st.caption(f"{_v139_summary['done']}/{_v139_summary['total']} förberedelsesteg klara")

        # Per-class progress replaces the old opaque global "0 av 16" presentation.
        if _v139_class_rows:
            _class_team_count_rows = all_rows(
                """SELECT competition_class_id, COUNT(*) AS n
                   FROM teams
                   WHERE tournament_id=?
                   GROUP BY competition_class_id""",
                (tid,),
            )
            _class_team_counts = {
                int(_row_value(row, "competition_class_id", 0) or 0): int(_row_value(row, "n", 0) or 0)
                for row in _class_team_count_rows
            }
            _class_progress_parts=[]
            for _class in _v139_class_rows:
                _actual=int(_class_team_counts.get(int(_class["id"]),0))
                _planned=max(_actual,int(_row_value(_class,"planned_team_count",0) or 0))
                _class_progress_parts.append(f"{competition_class_label(_class)}: {_actual}/{_planned}" if _planned else f"{competition_class_label(_class)}: {_actual}")
            st.caption("Lag per tävlingsklass · " + " · ".join(_class_progress_parts))

        _v139_cols = st.columns(4)
        for _v139_i, _v139_step in enumerate(_v139_steps):
            _v139_icon = "✓" if _v139_step.done else "•"
            _step_detail = _v139_step.detail
            if _v139_step.key == "teams" and _v139_class_rows:
                _step_detail = f"{int(_v139_counts['teams_n'] or 0)} registrerade · {_v139_expected_total} planerade totalt"
            elif _v139_step.key == "classes":
                _step_detail = f"{_v139_classes} klass" if _v139_classes == 1 else f"{_v139_classes} klasser"
            with _v139_cols[_v139_i % 4]:
                st.markdown(f"**{_v139_icon} {_v139_step.label}**")
                st.caption(_step_detail)
                if not _v139_step.done:
                    st.button(
                        "Öppna",
                        key=f"v139_step_{tid}_{_v139_step.key}",
                        use_container_width=True,
                        on_click=_set_admin_page,
                        args=(_v139_step.target,),
                    )

    # v141 Control Center: operational status for the tournament.
    _cc_matches = [dict(r) for r in all_rows(
        "SELECT scheduled_start,home_score,away_score FROM matches WHERE tournament_id=? ORDER BY scheduled_start",
        (tid,),
    )]
    from cupnavi_core.control_center import control_center_snapshot
    _cc = control_center_snapshot(_cc_matches, schedule_dirty=bool(tournament["schedule_dirty"]))
    with st.expander("Driftstatus", expanded=current_admin_mode == "live"):
        _cc_cols = st.columns(4)
        _cc_cols[0].metric("Kommande matcher", _cc["upcoming"])
        _cc_cols[1].metric("Resultat saknas", _cc["missing_results"])
        _cc_cols[2].metric("Kraftigt försenade", _cc["delayed"])
        _cc_cols[3].metric("Problem", _cc["problems"])
        if _cc["schedule_dirty"]:
            st.warning("Schemat behöver genereras om efter ändrade förutsättningar.")

    ux_counts = _v139_counts
    ux_progress = workflow_progress(
        teams_ready=bool(ux_counts["teams_n"]), groups_ready=bool(ux_counts["groups_n"]),
        schedule_ready=bool(ux_counts["matches_n"]) and not bool(tournament["schedule_dirty"]),
        referees_ready=bool(ux_counts["refs_n"]), published=bool(tournament["is_published"]),
    )
    ux_missing_refs = int(ux_counts["missing_refs_n"] or 0)
    checkin_enabled = bool(_row_value(tournament, "enable_team_checkin", 1))
    ux_unchecked = int(ux_counts["unchecked_n"] or 0) if checkin_enabled else 0
    ux_attention = attention_items(missing_referees=int(ux_missing_refs or 0), unchecked_teams=int(ux_unchecked or 0), schedule_dirty=bool(tournament["schedule_dirty"]), unpublished=not bool(tournament["is_published"]))
    st.markdown(f"<div class='cn-progress-hero'><div><span>Förberedelser</span><strong>{ux_progress['percent']} % klara</strong></div><div class='cn-progress-track'><i style='width:{ux_progress['percent']}%'></i></div></div>", unsafe_allow_html=True)
    if ux_attention:
        st.markdown("#### Kräver din uppmärksamhet")
        for ux_idx, item in enumerate(ux_attention[:4]):
            cols = st.columns([6, 1])
            icon = {"critical":"🔴", "warning":"🟠", "info":"🔵"}.get(item["level"], "🔵")
            cols[0].markdown(f"<div class='cn-attention-row'>{icon} <b>{html.escape(item['text'])}</b></div>", unsafe_allow_html=True)
            cols[1].button(
                "Lös", key=f"ux_attention_{tid}_{ux_idx}", use_container_width=True,
                on_click=_set_admin_page, args=(item["target"],),
            )

    with st.expander("Genvägar & publik vy", expanded=False):
        quick_cols = st.columns(4)
        quick_actions = [
            ("➕ Lag", "Lag"),
            ("🗓️ Schema", "Skapa och publicera schema"),
            ("⚡ Resultat", "Matcher och resultat"),
            ("✅ Kontroller", "Kontroller"),
        ]
        for quick_index, (quick_label, quick_target) in enumerate(quick_actions):
            quick_cols[quick_index].button(
                quick_label, key=f"quick_action_{tid}_{quick_index}", use_container_width=True,
                on_click=_set_admin_page, args=(quick_target,),
            )

        preview_cols = st.columns(2)
        if preview_cols[0].button("👁️ Förhandsgranska publik vy", key=f"preview_public_{tid}", use_container_width=True):
            st.session_state["view_mode"] = "Turneringsvy"
            if hasattr(st, "query_params"):
                st.query_params["cup"] = tournament["public_slug"] or str(tid)
            st.rerun()
        preview_cols[1].link_button("🔗 Öppna publik vy", public_cup_url(tid), use_container_width=True)
    # ux_counts innehåller redan dashboardens samtliga räknare. Undvik två
    # extra Turso-roundtrips för samma information.
    overview_team_count = ux_counts["teams_n"]
    overview_group_count = ux_counts["groups_n"]
    overview_match_count = ux_counts["matches_n"]
    workflow_counts = ux_counts
    cup_checklist = checklist_items(
        teams=int(workflow_counts["teams_n"] or 0),
        groups=int(workflow_counts["groups_n"] or 0),
        matches=int(workflow_counts["matches_n"] or 0),
        referees=int(workflow_counts["refs_n"] or 0),
        published=bool(tournament["is_published"]),
        public_contact=bool((tournament["organizer_phone"] or "").strip() or (tournament["feedback_email"] or "").strip()),
    )
    completed_checks = sum(1 for item in cup_checklist if item["done"])
    with st.expander(f"✅ Checklista inför cupstart · {completed_checks}/{len(cup_checklist)}", expanded=current_admin_mode == "live"):
        for check_index, item in enumerate(cup_checklist):
            check_cols = st.columns([5, 1])
            icon = "✅" if item["done"] else "⚠️"
            check_cols[0].markdown(f"{icon} {html.escape(item['label'])}")
            if not item["done"]:
                check_cols[1].button(
                    "Åtgärda", key=f"check_fix_{tid}_{check_index}", use_container_width=True,
                    on_click=_set_admin_page, args=(item["target"],),
                )

    expected_teams = int(tournament["expected_team_count"] or 0)
    teams_ready = workflow_counts["teams_n"] > 0 and (
        expected_teams == 0 or workflow_counts["teams_n"] == expected_teams
    )
    groups_ready = workflow_counts["groups_n"] > 0
    players_ready = workflow_counts["players_n"] > 0
    refs_ready = workflow_counts["refs_n"] > 0
    schedule_ready = workflow_counts["matches_n"] > 0 and not bool(tournament["schedule_dirty"])
    results_ready = (
        workflow_counts["matches_n"] > 0
        and workflow_counts["played_n"] == workflow_counts["matches_n"]
    )

    st.markdown(
        f"""
        <div class="cn-dashboard-grid">
          <div class="cn-status-card">
            <div class="cn-label">Lag</div>
            <div class="cn-value">{workflow_counts['teams_n']}</div>
            <div class="cn-sub">Planerat: {expected_teams or 'ej satt'}</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Grupper</div>
            <div class="cn-value">{workflow_counts['groups_n']}</div>
            <div class="cn-sub">Gruppindelning</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Matcher</div>
            <div class="cn-value">{workflow_counts['matches_n']}</div>
            <div class="cn-sub">Spelade: {workflow_counts['played_n']}</div>
          </div>
          <div class="cn-status-card">
            <div class="cn-label">Status</div>
            <div class="cn-value">{'Publicerad' if tournament['is_published'] else 'Utkast'}</div>
            <div class="cn-sub">{'Schema aktuellt' if not tournament['schedule_dirty'] else 'Schema behöver uppdateras'}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    workflow_html = "".join([
        _admin_workflow_step(
            "Lag",
            "done" if teams_ready else "todo",
            f"{workflow_counts['teams_n']} registrerade",
        ),
        _admin_workflow_step(
            "Grupper",
            "done" if groups_ready else "todo",
            f"{workflow_counts['groups_n']} skapade",
        ),
        _admin_workflow_step(
            "Trupper",
            "done" if players_ready else "todo",
            f"{workflow_counts['players_n']} spelare",
        ),
        _admin_workflow_step(
            "Domare",
            "done" if refs_ready else "todo",
            f"{workflow_counts['refs_n']} registrerade",
        ),
        _admin_workflow_step(
            "Schema",
            "done" if schedule_ready else ("warn" if workflow_counts["matches_n"] > 0 else "todo"),
            "Aktuellt" if schedule_ready else (
                "Behöver regenereras" if workflow_counts["matches_n"] > 0 else "Ej genererat"
            ),
        ),
        _admin_workflow_step(
            "Resultat",
            "done" if results_ready else "todo",
            f"{workflow_counts['played_n']} av {workflow_counts['matches_n']} matcher",
        ),
    ])
    st.markdown(f"<div class='cn-workflow'>{workflow_html}</div>", unsafe_allow_html=True)

    # Fairness ska aldrig kunna fälla hela Adminöversikten. Hämta hela matchrader
    # via samma beprövade SELECT *-väg som övriga schemavyer (Turso/libSQL har i
    # vissa miljöer gett ValueError för den tidigare smala SELECT-listan).
    try:
        fairness_matches = all_rows(
            "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
            (int(tid),),
        )
        fairness = fairness_report(fairness_matches)
    except Exception as exc:
        fairness = {
            "score": 100,
            "findings": ["Fairnessanalysen kunde inte beräknas just nu. Övrig cupdata påverkas inte."],
            "participants": 0,
        }
        print(f"CupNavi fairness warning for tournament {tid}: {type(exc).__name__}: {exc}")
    with st.expander(f"⚖️ Fairness · {fairness['score']}/100", expanded=False):
        st.progress(int(fairness["score"]) / 100)
        st.caption("Fairness analyserar bland annat skillnader i vila, tidiga/sena matcher och byten av plan/spelplats. Poängen är rådgivande – sportspecifika regler gäller alltid först.")
        for finding in fairness["findings"]:
            st.write(f"• {finding}")

    if bool(_row_value(tournament, "enable_control_center", 0)):
        st.markdown("### 🎛️ Cup Control Center")
        # Fairness hämtade redan samma schemalagda matcher ovan. Återanvänd
        # dem i Control Center i stället för ett nytt Turso-anrop.
        control_matches = fairness_matches
        now_dt = datetime.now()
        missing_refs = sum(1 for m in control_matches if m["referee_id"] is None and m["home_score"] is None)
        unplayed = sum(1 for m in control_matches if m["home_score"] is None or m["away_score"] is None)
        checkin_enabled = bool(_row_value(tournament, "enable_team_checkin", 1))
        unchecked = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=? AND COALESCE(checked_in,0)=0", (tid,))["n"] if checkin_enabled else 0
        open_incidents = all_rows("SELECT * FROM control_incidents WHERE tournament_id=? AND status='open' ORDER BY created_at DESC", (tid,))
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("Matcher kvar", unplayed)
        cc2.metric("Ej incheckade" if checkin_enabled else "Incheckning", unchecked if checkin_enabled else "Avstängd")
        cc3.metric("Domare saknas", missing_refs)
        cc4.metric("Öppna incidenter", len(open_incidents))
        with st.expander("Rapportera incident / avvikelse", expanded=False):
            with st.form(f"control_incident_{tid}", clear_on_submit=True):
                ic1, ic2 = st.columns(2)
                incident_category = ic1.selectbox("Kategori", ["Försening", "Plan/spelplats", "Domare", "Lag/deltagare", "Medicinskt", "Säkerhet", "Övrigt"])
                incident_severity = ic2.selectbox("Prioritet", ["info", "warning", "critical"], format_func=lambda x: {"info":"Info", "warning":"Varning", "critical":"Kritisk"}[x])
                incident_title = st.text_input("Rubrik")
                incident_detail = st.text_area("Beskrivning")
                if st.form_submit_button("Registrera incident", type="primary", use_container_width=True):
                    if not incident_title.strip():
                        st.error("Ange en rubrik.")
                    else:
                        run("INSERT INTO control_incidents(tournament_id,created_at,category,severity,title,detail,status) VALUES(?,?,?,?,?,?,'open')", (tid, datetime.now().isoformat(timespec='seconds'), incident_category, incident_severity, incident_title.strip(), incident_detail.strip() or None))
                        st.rerun()
        if open_incidents:
            for incident in open_incidents:
                icon = {"critical":"🔴", "warning":"🟠", "info":"🔵"}.get(incident["severity"], "🔵")
                with st.container(border=True):
                    st.markdown(f"**{icon} {html.escape(incident['title'])}** · {html.escape(incident['category'])}")
                    if incident["detail"]:
                        st.write(incident["detail"])
                    if st.button("Markera löst", key=f"resolve_incident_{incident['id']}"):
                        run("UPDATE control_incidents SET status='resolved',resolved_at=? WHERE id=? AND tournament_id=?", (datetime.now().isoformat(timespec='seconds'), incident["id"], tid))
                        st.rerun()

    # Tydlig rekommendation om nästa arbetssteg.
    if not teams_ready:
        next_step_title = "Nästa steg: registrera lag"
        next_step_target = "Lag"
        next_step_text = "Lägg in samtliga deltagande lag innan gruppindelning."
    elif not groups_ready:
        next_step_title = "Nästa steg: skapa grupper"
        next_step_target = "Grupper"
        next_step_text = "Skapa grupper och placera lagen innan schemat genereras."
    elif not players_ready:
        next_step_title = "Nästa steg: lägg till trupper"
        next_step_target = "Trupper"
        next_step_text = "Trupper behövs för mål, assist och kortstatistik."
    elif not refs_ready:
        next_step_title = "Nästa steg: lägg till domare"
        next_step_target = "Domare"
        next_step_text = "Lägg till domare innan automatisk domartillsättning används."
    elif not workflow_counts["matches_n"]:
        next_step_title = "Nästa steg: generera schema"
        next_step_target = "Skapa och publicera schema"
        next_step_text = "Grunddata är på plats. Generera gruppspel och slutspel."
    elif bool(tournament["schedule_dirty"]):
        next_step_title = "Nästa steg: regenerera schema"
        next_step_target = "Skapa och publicera schema"
        next_step_text = "Förutsättningarna har ändrats sedan schemat skapades."
    elif not results_ready:
        next_step_title = "Nästa steg: registrera resultat"
        next_step_target = "Matcher och resultat"
        next_step_text = "Schemat är klart. Registrera matchresultaten när turneringen spelas."
    else:
        next_step_title = "Nästa steg: granska och publicera"
        next_step_target = "Kontroller"
        next_step_text = "Grundflödet är klart. Kontrollera varningar och publiceringsstatus."

    st.info(f"**{next_step_title}**\n\n{next_step_text}")
    st.button(
        next_step_title,
        key=f"dashboard_next_step_{tid}",
        use_container_width=True,
        on_click=_set_admin_page,
        args=(next_step_target,),
    )

    if bool(tournament["schedule_dirty"]) and workflow_counts["matches_n"] > 0:
        st.markdown(
            """<div class="cn-action-banner">
            <strong>⚠ Schemat behöver regenereras.</strong><br>
            <span>Något som påverkar schemat har ändrats sedan senaste genereringen.</span>
            </div>""",
            unsafe_allow_html=True,
        )
        st.button(
            "Gå till Schema",
            type="primary",
            use_container_width=True,
            key=f"dashboard_go_schedule_{tid}",
            on_click=_set_admin_page,
            args=("Skapa och publicera schema",),
        )
    with st.expander("Direktredigera cupinställningar", expanded=False):
        st.caption("För avancerad direktredigering. För normal ändring rekommenderas Cupinställningar.")
        saved_start = datetime.fromisoformat(tournament["start_date"] or tournament["tournament_date"]).date()
        saved_end = datetime.fromisoformat(tournament["end_date"] or tournament["start_date"] or tournament["tournament_date"]).date()
        overview_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
        if overview_rules is None:
            run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
            overview_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
        placement_format = PLACEMENT_PLAYOFF_FORMAT
        format_options = ["Inget slutspel", "A- och B-slutspel", placement_format]
        stored_format = placement_format if tournament["playoff_format"] == "Flera egna slutspel" else tournament["playoff_format"]
        saved_format = stored_format if stored_format in format_options else "Inget slutspel"
        if not tournament["playoff_model_confirmed"]:
            st.warning("Välj och spara slutspelsmodell innan spelschemat kan genereras.")
        current_team_count_for_limit = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tid,))["n"]
        _prod_history_locked = production_history_locked(tid, tournament)
        if _prod_history_locked:
            st.warning(
                "🔒 Historikskydd aktivt: cupen är en riktig cup med registrerade resultat. "
                "Poäng-, match- och slutspelsregler är låsta här. Testmiljöer påverkas inte."
            )

        st.markdown("#### Sportprofil och internationell grund")
        saved_sport = _row_value(tournament, "sport", "Fotboll")
        selected_profile = sport_profile(saved_sport)
        selected_match_format = match_format(saved_sport)
        saved_locale = _row_value(tournament, "locale", DEFAULT_LOCALE)
        saved_timezone = _row_value(tournament, "timezone_name", DEFAULT_TIMEZONE)
        saved_country = _row_value(tournament, "country_code", "") or "Ej angivet"
        participant_type = _row_value(tournament, "participant_type", str(sport_definition(saved_sport)["participant_type"]))
        st.info(
            f"**{saved_sport}** · {saved_locale} · {saved_timezone} · {saved_country}  \n"
            "Dessa grundinställningar valdes när turneringen skapades och är låsta för att skydda matchmodell, statistik och regional tolkning."
        )
        st.caption(
            f"Sportstandard: {selected_profile['halves']} {selected_profile['period_label']} × "
            f"{selected_profile['minutes_per_half']} min · vila {selected_profile['minimum_team_rest_minutes']} min · "
            f"resultatmodell: {selected_match_format.scoring_mode} · segmenttyp: {selected_match_format.segment_kind} · "
            f"intern deltagartyp: {participant_type}."
        )
        st.caption(
            "Schemaläggning: OR-Tools CP-SAT används automatiskt när biblioteket är tillgängligt; "
            "annars används CupNavis säkra heuristiska fallback."
        )
        if st.button(
            "Återställ sportens standardregler",
            key=f"apply_sport_defaults_{tid}",
            use_container_width=True,
            disabled=_prod_history_locked,
        ):
            before_rules = dict(overview_rules)
            run(
                """UPDATE schedule_rules SET halves=?,minutes_per_half=?,halftime_minutes=?,minimum_team_rest_minutes=?
                   WHERE tournament_id=?""",
                (selected_profile["halves"], selected_profile["minutes_per_half"], selected_profile["halftime_minutes"],
                 selected_profile["minimum_team_rest_minutes"], tid),
            )
            run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?", (tid,))
            run("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (tid,))
            record_audit(tid, "sport_defaults", "schedule_rules", f"Standardregler för {saved_sport} tillämpades",
                         entity_id=tid, before=before_rules, after=dict(selected_profile), reversible=False)
            st.session_state["overview_saved_message"] = "Sportprofilens standardregler har lagts in. Schemat behöver regenereras."
            st.rerun()

        # Slutspelsvalen ligger utanför formuläret så de reagerar direkt på användarens val.
        # Streamlit-formulär skickar annars inte widgetändringar förrän "Spara" trycks.
        st.markdown("#### Slutspelsmodell och avgörande")
        playoff_col1, playoff_col2 = st.columns(2)
        edited_format = playoff_col1.selectbox(
            "Typ av slutspel",
            format_options,
            index=format_options.index(saved_format),
            key=f"overview_playoff_format_{tid}",
            disabled=_prod_history_locked,
        )
        edited_bronze = playoff_col2.checkbox(
            "Skapa bronsmatch automatiskt när slutspelsträdet har minst fyra lag",
            value=bool(tournament["bronze_match"]),
            disabled=_prod_history_locked or edited_format == "Inget slutspel",
            key=f"overview_bronze_{tid}",
        )

        st.markdown("##### Oavgjort i slutspelsmatch")
        tie1, tie2 = st.columns(2)
        tie_options = ["Förlängning + straffar", "Straffar direkt", "Lottning"]
        saved_tie_rule = tournament["playoff_tie_rule"] or "Straffar direkt"
        edited_tie_rule = tie1.selectbox(
            "Så avgörs slutspelsmatchen",
            tie_options,
            index=tie_options.index(saved_tie_rule) if saved_tie_rule in tie_options else 1,
            disabled=_prod_history_locked or edited_format == "Inget slutspel",
            key=f"overview_tie_rule_{tid}",
        )
        edited_extra_time = tie2.number_input(
            "Förlängning (minuter)",
            min_value=1,
            max_value=60,
            value=max(1, int(tournament["extra_time_minutes"] or 10)),
            disabled=_prod_history_locked or edited_format == "Inget slutspel" or edited_tie_rule != "Förlängning + straffar",
            help=(
                "Aktiveras när 'Förlängning + straffar' väljs. "
                "Tiden reserveras även i schemaläggningen för slutspelsmatcher."
            ),
            key=f"overview_extra_time_{tid}",
        )
        if edited_format != "Inget slutspel":
            st.success("Slutspelsreglerna är aktiva. Du kan justera dem direkt innan du sparar.")
        else:
            st.caption("Välj en slutspelsmodell för att aktivera reglerna för oavgjorda slutspelsmatcher.")

        with st.container():
            st.markdown("#### Cup och deltagande")
            bn1, bn2 = st.columns(2)
            edited_name = bn1.text_input("Turneringens namn", value=tournament["name"])
            edited_location = bn2.text_input("Spelort", value=tournament["location"] or "")
            bc1, bc2, bc3 = st.columns(3)
            edited_start = bc1.date_input("Första cupdag", value=saved_start)
            bc1.caption(f"📅 {date_with_weekday(edited_start)}")
            edited_end = bc2.date_input("Sista cupdag", value=saved_end)
            bc2.caption(f"📅 {date_with_weekday(edited_end)}")
            _class_planned_total=sum(max(0,int(_row_value(row,"planned_team_count",0) or 0)) for row in competition_classes(tid))
            edited_expected=max(_class_planned_total,int(current_team_count_for_limit))
            bc3.metric("Planerat antal lag",edited_expected)
            bc3.caption("Beräknas från planerat antal i varje tävlingsklass. Ändra under Cupinställningar → guidad setup.")

            st.markdown("#### Arena och information till besökare")
            edited_address = st.text_input(
                "Arenaadress", value=tournament["arena_address"] or "",
                placeholder="Exempel: Idrottsvägen 1, 702 00 Örebro",
            )
            edited_kiosk_info = st.text_input(
                "Kiosk och servering (frivillig information)", value=tournament["kiosk_information"] or "",
                placeholder="Exempel: Kiosk finns och är öppen 08.00–17.00 med kaffe, korv och enklare lunch",
            )
            practical1, practical2 = st.columns(2)
            edited_changing_rooms = practical1.checkbox("Tillgång till omklädningsrum", value=bool(_row_value(tournament,"changing_rooms_available",0)))
            edited_show_prices = practical2.checkbox("Visa priser/avgifter publikt", value=bool(_row_value(tournament,"show_price_information",0)))
            edited_changing_room_info = st.text_input("Information om omklädningsrum", value=_row_value(tournament,"changing_room_info","") or "", placeholder="Exempel: 4 omklädningsrum i huvudbyggnaden")
            edited_price_info = st.text_input("Priser/avgifter för cup eller matchcamp", value=_row_value(tournament,"price_information","") or "", placeholder="Exempel: Lagavgift 1 500 SEK · Matchcamp 250 SEK/spelare")
            edited_public_info = st.text_area(
                "Egen information på publika infosidan",
                value=tournament["public_information"] or "",
                placeholder="Exempel: Parkering finns vid skolan. Omklädningsrum öppnar 07.30. Hundar ska hållas kopplade.",
                help="Visas under Info efter de automatiskt skapade cupreglerna.",
            )
            contact_col1, contact_col2 = st.columns(2)
            edited_organizer_phone = contact_col1.text_input(
                "Arrangörens telefonnummer",
                value=tournament["organizer_phone"] or "",
                placeholder="Exempel: 070-123 45 67",
                help="Visas publikt som en klickbar ring-knapp under Information.",
            )
            edited_feedback_email = contact_col2.text_input(
                "E-post för feedback",
                value=tournament["feedback_email"] or "",
                placeholder="Exempel: cup@foreningen.se",
                help="Visas publikt som en klickbar e-postknapp för frågor och feedback.",
            )
            edited_instagram = st.text_input(
                "Instagram för cupen",
                value=tournament["instagram_url"] or "",
                placeholder="Exempel: @cupnavi eller https://www.instagram.com/cupnavi/",
                help="Ange användarnamn eller länk. Visas publikt som en knapp för att följa cupen.",
            )

            st.markdown("#### Valbara funktioner")
            feature_col1, feature_col2 = st.columns(2)
            edited_control_center = feature_col1.checkbox("Cup Control Center", value=bool(_row_value(tournament, "enable_control_center", 0)), help="Visar en operativ cupdagsvy med incidenter, förseningar och snabbstatus.")
            edited_scorers = feature_col1.checkbox("Skytteliga", value=bool(_row_value(tournament, "enable_scorer_leaderboard", 1)))
            edited_assists = feature_col1.checkbox("Assistliga", value=bool(_row_value(tournament, "enable_assist_leaderboard", 1)))
            edited_cards = feature_col1.checkbox("Gula/röda kort och kortstatistik", value=bool(_row_value(tournament, "enable_card_statistics", 1)))
            edited_medical = feature_col2.checkbox("Medicinsk beredskap på infosidan", value=bool(_row_value(tournament, "enable_medical_info", 0)))
            edited_lost_found = feature_col2.checkbox("Lost & found / hittegods på infosidan", value=bool(_row_value(tournament, "enable_lost_found", 0)))
            edited_accessibility_info = feature_col2.checkbox("Tillgänglighetsinfo på infosidan", value=bool(_row_value(tournament, "enable_accessibility_info", 0)))
            # Progressive disclosure: only show the detail field when its public
            # feature is enabled. When disabled we retain the saved value so toggling
            # the feature off never destroys previously entered information.
            if edited_medical:
                edited_medical_info = st.text_area(
                    "Medicinsk beredskap",
                    value=_row_value(tournament, "medical_info", "") or "",
                    placeholder="Exempel: Sjukvårdare finns vid sekretariatet. Hjärtstartare finns i entréhallen.",
                )
            else:
                edited_medical_info = _row_value(tournament, "medical_info", "") or ""

            if edited_lost_found:
                edited_lost_found_info = st.text_area(
                    "Lost & found / hittegods",
                    value=_row_value(tournament, "lost_found_info", "") or "",
                    placeholder="Exempel: Hittegods lämnas och hämtas i sekretariatet.",
                )
            else:
                edited_lost_found_info = _row_value(tournament, "lost_found_info", "") or ""

            if edited_accessibility_info:
                edited_accessibility_text = st.text_area(
                    "Tillgänglighet för besökare",
                    value=_row_value(tournament, "accessibility_info", "") or "",
                    placeholder="Exempel: Tillgänglig entré, RWC och reserverade parkeringsplatser finns vid huvudentrén.",
                )
            else:
                edited_accessibility_text = _row_value(tournament, "accessibility_info", "") or ""

            st.markdown("#### Poängregler och tabell")
            bp1, bp2, bp3 = st.columns(3)
            edited_win = bp1.number_input("Poäng för vinst", 0, 10, int(tournament["points_win"]), disabled=_prod_history_locked)
            edited_draw = bp2.number_input("Poäng för oavgjort", 0, 10, int(tournament["points_draw"]), disabled=_prod_history_locked)
            edited_loss = bp3.number_input("Poäng för förlust", 0, 10, int(tournament["points_loss"]), disabled=_prod_history_locked)

            table_tiebreak_options = ["Målskillnad först", "Inbördes möten först"]
            saved_tiebreak = tournament["table_tiebreak"] or "Målskillnad först"
            edited_tiebreak = st.selectbox(
                "Vid lika poäng avgör i första hand",
                table_tiebreak_options,
                index=table_tiebreak_options.index(saved_tiebreak) if saved_tiebreak in table_tiebreak_options else 0,
                disabled=_prod_history_locked,
            )

            st.markdown("#### Match- och schemaregler")
            br2, br3 = st.columns(2)
            edited_halves = br2.number_input("Antal perioder/halvlekar/set", 1, 4, int(overview_rules["halves"]), disabled=_prod_history_locked)
            edited_minutes_half = br3.number_input("Minuter per period/halvlek/set", 1, 120, int(overview_rules["minutes_per_half"]), disabled=_prod_history_locked)
            br4, br5 = st.columns(2)
            edited_halftime = br4.number_input("Paus mellan perioder/halvlekar (minuter)", 0, 60, int(overview_rules["halftime_minutes"]), disabled=_prod_history_locked)
            edited_pitch_break = br5.number_input("Paus mellan matcher på samma plan", 0, 120, int(overview_rules["pitch_break_minutes"]), disabled=_prod_history_locked)
            st.markdown("##### Följdmatcher för samma lag")
            with st.container(border=True):
                follow1, follow2 = st.columns(2)
                edited_avoid_consecutive = follow1.checkbox(
                    "Försök undvika matcher direkt efter varandra för samma lag",
                    value=bool(overview_rules["avoid_consecutive_matches"]),
                    disabled=_prod_history_locked,
                )
                edited_consecutive_break = follow2.number_input(
                    "Extra paus om följdmatcher inte kan undvikas (minuter)",
                    0, 180, int(overview_rules["consecutive_match_break_minutes"]),
                    disabled=_prod_history_locked or not edited_avoid_consecutive,
                )
            edited_referee_mode = st.selectbox(
                "Domartillsättning",
                ["Automatisk", "Manuell"],
                index=0 if overview_rules["referee_mode"] == "Automatisk" else 1,
                disabled=_prod_history_locked,
            )
            edited_match_minutes = (edited_halves * edited_minutes_half) + ((edited_halves - 1) * edited_halftime)
            st.info(f"Med dessa regler tar en match {edited_match_minutes} minuter från avspark till slutsignal.")
            st.caption("Antal planer och tillgänglig start-/sluttid för varje plan och cupdag anges under Konfigurera turneringen.")

            protected_rules_changed = any([
                int(edited_win) != int(tournament["points_win"]),
                int(edited_draw) != int(tournament["points_draw"]),
                int(edited_loss) != int(tournament["points_loss"]),
                edited_tiebreak != (tournament["table_tiebreak"] or "Målskillnad först"),
                edited_format != saved_format,
                int(edited_bronze) != int(tournament["bronze_match"]),
                edited_tie_rule != (tournament["playoff_tie_rule"] or "Straffar direkt"),
                (edited_extra_time if edited_tie_rule == "Förlängning + straffar" else 0) != int(tournament["extra_time_minutes"] or 0),
                int(edited_halves) != int(overview_rules["halves"]),
                int(edited_minutes_half) != int(overview_rules["minutes_per_half"]),
                int(edited_halftime) != int(overview_rules["halftime_minutes"]),
                int(edited_pitch_break) != int(overview_rules["pitch_break_minutes"]),
                bool(edited_avoid_consecutive) != bool(overview_rules["avoid_consecutive_matches"]),
                int(edited_consecutive_break) != int(overview_rules["consecutive_match_break_minutes"]),
                edited_referee_mode != overview_rules["referee_mode"],
            ])

            overview_autosave_changed = any([
                edited_name.strip() != (tournament["name"] or ""), edited_location.strip() != (tournament["location"] or ""),
                edited_start != saved_start, edited_end != saved_end, int(edited_expected) != int(tournament["expected_team_count"] or 0),
                int(edited_win) != int(tournament["points_win"]), int(edited_draw) != int(tournament["points_draw"]), int(edited_loss) != int(tournament["points_loss"]),
                edited_address.strip() != (tournament["arena_address"] or ""), edited_kiosk_info.strip() != (tournament["kiosk_information"] or ""), bool(edited_changing_rooms) != bool(_row_value(tournament,"changing_rooms_available",0)), bool(edited_show_prices) != bool(_row_value(tournament,"show_price_information",0)), edited_changing_room_info.strip() != (_row_value(tournament,"changing_room_info","") or ""), edited_price_info.strip() != (_row_value(tournament,"price_information","") or ""),
                edited_public_info.strip() != (tournament["public_information"] or ""), edited_organizer_phone.strip() != (tournament["organizer_phone"] or ""),
                edited_feedback_email.strip() != (tournament["feedback_email"] or ""), edited_instagram.strip() != (tournament["instagram_url"] or ""),
                edited_tiebreak != (tournament["table_tiebreak"] or "Målskillnad först"), edited_format != saved_format, int(edited_bronze) != int(tournament["bronze_match"]),
                edited_tie_rule != (tournament["playoff_tie_rule"] or "Straffar direkt"),
                bool(edited_control_center) != bool(_row_value(tournament,"enable_control_center",0)), bool(edited_scorers) != bool(_row_value(tournament,"enable_scorer_leaderboard",1)),
                bool(edited_assists) != bool(_row_value(tournament,"enable_assist_leaderboard",1)), bool(edited_cards) != bool(_row_value(tournament,"enable_card_statistics",1)),
                bool(edited_medical) != bool(_row_value(tournament,"enable_medical_info",0)), edited_medical_info.strip() != (_row_value(tournament,"medical_info","") or ""),
                bool(edited_lost_found) != bool(_row_value(tournament,"enable_lost_found",0)), edited_lost_found_info.strip() != (_row_value(tournament,"lost_found_info","") or ""),
                bool(edited_accessibility_info) != bool(_row_value(tournament,"enable_accessibility_info",0)), edited_accessibility_text.strip() != (_row_value(tournament,"accessibility_info","") or ""),
    int(edited_halves) != int(overview_rules["halves"]),
                int(edited_minutes_half) != int(overview_rules["minutes_per_half"]), int(edited_halftime) != int(overview_rules["halftime_minutes"]),
                int(edited_pitch_break) != int(overview_rules["pitch_break_minutes"]), bool(edited_avoid_consecutive) != bool(overview_rules["avoid_consecutive_matches"]),
                int(edited_consecutive_break) != int(overview_rules["consecutive_match_break_minutes"]), edited_referee_mode != overview_rules["referee_mode"]
            ])
            if overview_autosave_changed:
                if not edited_name.strip():
                    st.error("Turneringens namn får inte vara tomt.")
                elif edited_end < edited_start:
                    st.error("Sista cupdagen får inte ligga före första cupdagen.")
                elif _prod_history_locked and protected_rules_changed:
                    st.error(
                        "Historikskyddet stoppade ändringen. Centrala tävlingsregler kan inte skrivas om "
                        "efter första resultatet i en riktig cup."
                    )
                else:
                    scheduling_changed = any([
                        edited_start != saved_start,
                        edited_end != saved_end,
                        edited_halves != overview_rules["halves"],
                        edited_minutes_half != overview_rules["minutes_per_half"],
                        edited_halftime != overview_rules["halftime_minutes"],
                        edited_pitch_break != overview_rules["pitch_break_minutes"],
                        int(edited_avoid_consecutive) != overview_rules["avoid_consecutive_matches"],
                        edited_consecutive_break != overview_rules["consecutive_match_break_minutes"],
                        edited_referee_mode != overview_rules["referee_mode"],
                        edited_format != saved_format,
                        int(edited_bronze) != int(tournament["bronze_match"]),
                        edited_tie_rule != (tournament["playoff_tie_rule"] or "Straffar direkt"),
                        (edited_extra_time if edited_tie_rule == "Förlängning + straffar" else 0) != int(tournament["extra_time_minutes"] or 0),
                    ])
                    with db() as con:
                        con.execute(
                            """UPDATE tournaments SET name=?,location=?,tournament_date=?,start_date=?,end_date=?,expected_team_count=?,
                            points_win=?,points_draw=?,points_loss=?,playoff_format=?,bronze_match=?,arena_address=?,kiosk_available=?,
                            kiosk_information=?,public_information=?,organizer_phone=?,feedback_email=?,instagram_url=?,table_tiebreak=?,playoff_tie_rule=?,extra_time_minutes=?,playoff_model_confirmed=1,
                            enable_control_center=?,enable_scorer_leaderboard=?,enable_assist_leaderboard=?,enable_card_statistics=?,
                            enable_medical_info=?,medical_info=?,enable_lost_found=?,lost_found_info=?,enable_accessibility_info=?,accessibility_info=?,
                            changing_rooms_available=?,changing_room_info=?,show_price_information=?,price_information=?
                            WHERE id=?""",
                            (edited_name.strip(), edited_location.strip(), edited_start.isoformat(), edited_start.isoformat(), edited_end.isoformat(),
                             edited_expected, edited_win, edited_draw, edited_loss, edited_format, int(edited_bronze), edited_address.strip(),
                             int(bool(edited_kiosk_info.strip())), edited_kiosk_info.strip(), edited_public_info.strip(),
                             edited_organizer_phone.strip(), edited_feedback_email.strip(), edited_instagram.strip(), edited_tiebreak,
                             edited_tie_rule if edited_format != "Inget slutspel" else "Straffar direkt",
                             edited_extra_time if edited_format != "Inget slutspel" and edited_tie_rule == "Förlängning + straffar" else 0,
                             int(edited_control_center), int(edited_scorers), int(edited_assists), int(edited_cards),
                             int(edited_medical), edited_medical_info.strip(), int(edited_lost_found), edited_lost_found_info.strip(),
                             int(edited_accessibility_info), edited_accessibility_text.strip(), int(edited_changing_rooms), edited_changing_room_info.strip(), int(edited_show_prices), edited_price_info.strip(), tid),
                        )
                        con.execute(
                            """UPDATE schedule_rules SET halves=?,minutes_per_half=?,halftime_minutes=?,pitch_break_minutes=?,
                            avoid_consecutive_matches=?,consecutive_match_break_minutes=?,referee_mode=? WHERE tournament_id=?""",
                            (edited_halves, edited_minutes_half, edited_halftime, edited_pitch_break,
                             int(edited_avoid_consecutive), edited_consecutive_break, edited_referee_mode, tid),
                        )
                        if scheduling_changed:
                            con.execute("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (tid,))
                            con.execute("UPDATE tournaments SET is_published=0,schedule_dirty=1 WHERE id=?", (tid,))
                        con.commit()
                    st.session_state["overview_saved_message"] = (
                        "✓ Sparat automatiskt. Ändringarna påverkar schemat, som nu är markerat för regenerering."
                        if scheduling_changed else "✓ Sparat automatiskt."
                    )
        if "overview_saved_message" in st.session_state:
            st.success(st.session_state.pop("overview_saved_message"))
        if tournament["playoff_format"] != "Inget slutspel":
            st.caption("Typen av slutspel väljs här. Vilka placeringar som möts och hur trädet byggs ställs in under fliken Slutspel.")
    with st.expander("Publicering & startkontroll", expanded=False):
        admin_groups = all_rows("SELECT * FROM groups WHERE tournament_id=?", (tid,))
        admin_teams = all_rows("SELECT * FROM teams WHERE tournament_id=?", (tid,))
        admin_matches = all_rows("SELECT * FROM matches WHERE tournament_id=?", (tid,))
        unassigned_teams = [t for t in admin_teams if t["group_id"] is None]
        unscheduled_matches = [m for m in admin_matches if m["scheduled_start"] is None]
        matches_without_referee = [m for m in admin_matches if m["scheduled_start"] is not None and m["referee_id"] is None]
        unpublished_matches = [m for m in admin_matches if m["scheduled_start"] is not None and not m["schedule_published"]]
        scheduled_admin_matches = [m for m in admin_matches if m["scheduled_start"] is not None]
        published_admin_matches = [m for m in scheduled_admin_matches if m["schedule_published"]]
        # Återanvänd den globala publiceringskontrollen som redan är beräknad för
        # den här renderingen. Översikten ska inte göra en andra full schemavalidering.
        overview_schedule_errors = sidebar_errors
        overview_schedule_warnings = sidebar_warnings
        st.subheader("Kontroll före turneringsstart")
        checks = [
            (bool(admin_groups), "Minst en grupp är skapad"),
            (bool(admin_teams), "Minst ett lag är registrerat"),
            (len(admin_teams) == int(tournament["expected_team_count"] or 0), f"Registrerade lag stämmer med planerat antal ({len(admin_teams)}/{tournament['expected_team_count'] or 0})"),
            (not unassigned_teams, "Alla lag är placerade i en grupp"),
            (bool(admin_matches), "Matcher är skapade"),
            (not unscheduled_matches, "Alla matcher som kan planeras har en schematid"),
            (not matches_without_referee, "Alla schemalagda matcher har domare"),
            (not unpublished_matches, "Det aktuella schemat är godkänt och publicerat"),
        ]
        for passed, label in checks:
            st.write(f"{'✅' if passed else '⚠️'} {label}")
        if not scheduled_admin_matches:
            st.caption("Nästa steg: skapa schemat under Schema.")
        elif overview_schedule_errors:
            st.error(f"{len(overview_schedule_errors)} blockerande schemafel behöver åtgärdas under Schema.")
        elif overview_schedule_warnings:
            st.warning(f"{len(overview_schedule_warnings)} schemavarningar behöver granskas före publicering.")
        else:
            st.caption("Publiceringsstatus och publiceringsknapp finns i vänsterspalten.")

    with st.expander("⚠️ Riskzon – Cup och papperskorg", expanded=False):
        current_environment = str(_row_value(tournament, "environment_type", "production") or "production")
        if current_environment == "test":
            st.info("🧪 Testmiljö: cupen kan raderas direkt. Detta påverkar bara den valda testcupen.")
            test_delete_confirm = st.checkbox(
                f"Jag vill radera testcupen {tournament['name']}",
                key=f"delete_test_tournament_confirm_{tid}",
            )
            if st.button(
                "🗑️ Radera testcup permanent",
                disabled=not test_delete_confirm,
                type="primary",
                use_container_width=True,
                key=f"delete_test_tournament_{tid}",
            ):
                with db() as con:
                    con.execute("DELETE FROM tournaments WHERE id=?", (tid,))
                    con.commit()
                _clear_render_query_cache()
                st.session_state.pop("preferred_tournament_id", None)
                st.rerun()
        else:
            st.warning(
                "En riktig cup kan alltid raderas. Admin kan göra det även om cupen är publicerad eller har spelade matcher. "
                "Papperskorgen rekommenderas först så att en felklickning inte tar bort historik."
            )
            trash_selected = st.checkbox(
                f"Jag vill flytta {tournament['name']} till papperskorgen",
                key=f"trash_tournament_selected_{tid}",
            )
            if st.button(
                "🗑️ Flytta cupen till papperskorgen",
                disabled=not trash_selected,
                key=f"trash_tournament_button_{tid}",
                use_container_width=True,
            ):
                changed, trash_reason = _trash_tournament_if_current(
                    tid,
                    tournament_lifecycle,
                    bool(tournament["is_published"]),
                )
                if not changed:
                    st.warning("Cupens status ändrades av en annan administratör och flytten genomfördes inte.")
                st.rerun()

        trashed_tournaments = all_rows(
            "SELECT id,name,trashed_at FROM tournaments WHERE lifecycle_status='trashed' ORDER BY trashed_at DESC,name"
        )
        with st.expander(f"Papperskorg ({len(trashed_tournaments)})", expanded=bool(trashed_tournaments)):
            if not trashed_tournaments:
                st.caption("Papperskorgen är tom.")
            else:
                trashed_ids = [row["id"] for row in trashed_tournaments]
                trash_name_by_id = {row["id"]: row["name"] for row in trashed_tournaments}
                trash_row_by_id = {row["id"]: row for row in trashed_tournaments}
                bin_id = st.selectbox(
                    "Cup i papperskorgen",
                    trashed_ids,
                    format_func=lambda tournament_id: trash_name_by_id[tournament_id],
                    key="trashed_tournament_target",
                )
                bin_name = trash_name_by_id[bin_id]
                trashed_at = trash_row_by_id[bin_id]["trashed_at"] or "Tid saknas"
                st.caption(f"Flyttad till papperskorgen: {trashed_at.replace('T',' ')}")
                restore_col, permanent_col = st.columns(2)
                if restore_col.button("↩️ Återställ cup", use_container_width=True, key=f"restore_trashed_{bin_id}"):
                    changed, restore_reason = _restore_trashed_tournament_if_current(
                        bin_id,
                        trash_row_by_id[bin_id]["trashed_at"],
                    )
                    if not changed:
                        st.warning("Cupen ändrades av en annan administratör och kunde inte återställas från den här äldre vyn.")
                    st.rerun()
                permanent_col.error("Permanent radering går inte att ångra.")
                typed_name = permanent_col.text_input(
                    f"Skriv exakt: {bin_name}",
                    key=f"permanent_delete_name_{bin_id}",
                )
                if permanent_col.button(
                    "Radera permanent",
                    disabled=typed_name != bin_name,
                    type="primary",
                    use_container_width=True,
                    key=f"permanent_delete_{bin_id}",
                ):
                    deleted, delete_reason = _delete_trashed_tournament_if_current(
                        bin_id,
                        bin_name,
                        trash_row_by_id[bin_id]["trashed_at"],
                    )
                    if deleted:
                        st.session_state.pop(f"admin_page_{bin_id}", None)
                        st.session_state.pop(f"_schedule_validation_{bin_id}", None)
                    else:
                        st.warning("Cupen ändrades eller återställdes av en annan administratör och raderades därför inte.")
                    st.rerun()


    with st.expander("Testverktyg", expanded=False):
        _demo_environment_allowed = is_test_environment(tournament)
        st.subheader("Testverktyg" if _demo_environment_allowed else "Testverktyg · endast Testmiljö")
        if _demo_environment_allowed:
            st.caption("Skapa demodata och simulera cupens olika faser utan att påverka en riktig cup.")
        else:
            st.info(
                "Testverktygen är avstängda i riktiga cuper. Duplicera cupen som Testkopia om du vill prova "
                "schema, demodata eller simulerade resultat."
            )
        if _demo_environment_allowed:
            demo_counts = one_row(
                """SELECT
                     (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
                     (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
                     (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n""",
                (tid, tid, tid),
            )
            demo_allowed = (
                _demo_environment_allowed
                and demo_counts["teams_n"] == 0
                and demo_counts["groups_n"] == 0
                and demo_counts["matches_n"] == 0
            )
            if not demo_allowed:
                st.caption("Demodata kan bara skapas i en tom turnering, så befintlig cupdata kan aldrig skrivas över.")
            td1, td2 = st.columns(2)
            demo_team_count = int(td1.number_input("Antal testlag", min_value=4, max_value=24, value=8, step=1, disabled=not demo_allowed, key=f"demo_team_count_{tid}"))
            demo_group_count = int(td2.selectbox("Antal testgrupper", [2, 4, 8], index=0, disabled=not demo_allowed, key=f"demo_group_count_{tid}"))
            demo_shape_valid = demo_team_count >= demo_group_count * 2
            if demo_allowed and not demo_shape_valid:
                st.warning("Varje testgrupp behöver minst två lag. Minska antal grupper eller öka antal lag.")
            if st.button(f"Skapa testdata: {demo_team_count} lag + trupper + {demo_group_count} grupper", disabled=not demo_allowed or not demo_shape_valid, key=f"demo_{tid}"):
                con = db()
                try:
                    # Riktiga klubbnamn används som testlag. Alla spelare nedan är påhittad demo-data.
                    # Varje körning väljer 3 Allsvenskan + 2 Superettan + 3 Premier League.
                    demo_clubs = {
                        "Allsvenskan": [
                            ("AIK", "#111111", "#FDE047"), ("BK Häcken", "#FACC15", "#111111"),
                            ("Djurgårdens IF", "#60A5FA", "#1E3A8A"), ("Hammarby IF", "#16A34A", "#FFFFFF"),
                            ("IF Elfsborg", "#FACC15", "#111111"), ("IFK Göteborg", "#2563EB", "#FFFFFF"),
                            ("IFK Norrköping", "#2563EB", "#FFFFFF"), ("Malmö FF", "#7DD3FC", "#FFFFFF"),
                            ("Mjällby AIF", "#FACC15", "#111111"), ("IK Sirius", "#2563EB", "#111111"),
                        ],
                        "Superettan": [
                            ("Örebro SK", "#111111", "#FFFFFF"), ("Helsingborgs IF", "#DC2626", "#2563EB"),
                            ("Kalmar FF", "#DC2626", "#FFFFFF"), ("Landskrona BoIS", "#111111", "#FFFFFF"),
                            ("GIF Sundsvall", "#2563EB", "#FFFFFF"), ("Örgryte IS", "#DC2626", "#2563EB"),
                            ("IK Brage", "#16A34A", "#FFFFFF"), ("Trelleborgs FF", "#2563EB", "#FFFFFF"),
                        ],
                        "Premier League": [
                            ("Arsenal", "#DC2626", "#FFFFFF"), ("Aston Villa", "#7F1D1D", "#93C5FD"),
                            ("Chelsea", "#1D4ED8", "#FFFFFF"), ("Liverpool", "#DC2626", "#FFFFFF"),
                            ("Manchester City", "#7DD3FC", "#FFFFFF"), ("Manchester United", "#DC2626", "#111111"),
                            ("Newcastle United", "#111111", "#FFFFFF"), ("Tottenham Hotspur", "#FFFFFF", "#172554"),
                            ("West Ham United", "#7F1D1D", "#93C5FD"),
                        ],
                    }
                    club_pool = [(league, *club) for league, clubs in demo_clubs.items() for club in clubs]
                    chosen = random.sample(club_pool, min(demo_team_count, len(club_pool)))
                    while len(chosen) < demo_team_count:
                        index = len(chosen) + 1
                        chosen.append(("Demo", f"Testlag {index}", "#166534", "#FFFFFF"))
                    random.shuffle(chosen)

                    # Fiktiva namn inspirerade av kända fotbollsstjärnors förnamn/klang,
                    # men kombinerade med andra efternamn så de inte påstår sig vara riktiga spelare.
                    star_first_names = [
                        "Lionel", "Cristiano", "Kylian", "Erling", "Jude", "Mohamed", "Kevin", "Harry",
                        "Virgil", "Bukayo", "Cole", "Bruno", "Luka", "Pedri", "Vinícius", "Rodri",
                        "Sonny", "Declan", "Phil", "Antoine", "Zlatan", "Alexander", "Martin", "Victor",
                    ]
                    fun_surnames = [
                        "Svensson", "Bergström", "Karlsson", "Lind", "Holm", "Andersson", "Ekström",
                        "Nyström", "Dahl", "Sandberg", "Rosén", "Strand", "Björk", "Lund", "Forsberg",
                        "Westin", "Hedlund", "Norén", "Engström", "Vik", "Stjärna", "Bollström",
                    ]
                    patterns = ["Helfärgad", "Vertikala ränder", "Horisontella ränder", "Rutigt", "Delad"]
                    away_palette = ["#FFFFFF", "#111827", "#FACC15", "#22C55E", "#F97316", "#E5E7EB", "#7DD3FC"]

                    con.execute(
                        """UPDATE tournaments SET expected_team_count=?,
                               playoff_format='A- och B-slutspel',bronze_match=1,playoff_model_confirmed=1,
                               arena_address='CupNavi Arena, Testvägen 1',kiosk_available=1,
                               kiosk_information='Kiosk öppen hela cupdagen med kaffe, mat och dryck.',
                               public_information='Democup för komplett funktionstest av CupNavi.',
                               organizer_phone='070-000 00 01',feedback_email='demo@cup-navi.com',
                               instagram_url='https://www.instagram.com/cupnavi/',allow_team_public_contact=1,
                               squad_deadline_minutes=30,max_roster_size=18,
                               age_classes_json=?
                           WHERE id=?""",
                        (demo_team_count, json.dumps(["U14"], ensure_ascii=False), tid),
                    )
                    group_names = []
                    for group_index in range(demo_group_count):
                        group_name = f"Grupp {chr(65 + group_index)}"
                        group_names.append(group_name)
                        con.execute("INSERT INTO groups(tournament_id,name,age_class) VALUES(?,?,?)", (tid, group_name, "U14"))
                    created_groups = _rows_from_cursor(con.execute("SELECT id,name FROM groups WHERE tournament_id=? ORDER BY id", (tid,)))
                    group_id_by_name = {row["name"]: row["id"] for row in created_groups}
                    group_ids = [group_id_by_name[name] for name in group_names]

                    # Första passet: skapa alla lag.
                    team_specs = []
                    for index, (league, club_name, home1, home2) in enumerate(chosen):
                        group_id = group_ids[index % demo_group_count]
                        home_pattern = random.choice(patterns)
                        away_pattern = random.choice(patterns)
                        away1 = random.choice(away_palette)
                        away2 = random.choice([color for color in away_palette if color != away1])
                        distance = random.choice([0, 12, 25, 48, 75, 110, 165, 220])
                        late = 1 if distance >= 110 and random.random() < 0.7 else 0
                        earliest = random.choice(["10:00", "10:30", "11:00"]) if late else None
                        note = f"Demodata · {league}" + (" · lång resväg" if late else "")
                        con.execute(
                            """INSERT INTO teams(
                                tournament_id,name,primary_color,secondary_color,home_pattern,home_color_2,
                                away_pattern,away_color_2,group_id,distance_km,late_first_match,
                                earliest_first_time,travel_note,age_class,responsible_name,responsible_phone,
                                responsible_email,public_contact_name,public_contact_phone,public_contact_email,
                                public_contact_enabled
                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (tid, club_name, home1, away1, home_pattern, home2, away_pattern, away2,
                             group_id, distance, late, earliest, note, "U14",
                             f"Kontakt {club_name}", f"070-{100+index:03d} 10 10",
                             f"kontakt{index+1}@demo.cup-navi.com", f"Kontakt {club_name}",
                             f"070-{100+index:03d} 10 10", f"kontakt{index+1}@demo.cup-navi.com", 1),
                        )
                        team_specs.append((club_name, league))

                    # Hämta faktiska Turso-ID:n efter INSERT i stället för att lita på lastrowid.
                    created_teams = _rows_from_cursor(
                        con.execute("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY id", (tid,))
                    )
                    team_id_by_name = {row["name"]: row["id"] for row in created_teams}
                    if len(team_id_by_name) != demo_team_count:
                        raise RuntimeError(f"Förväntade {demo_team_count} demolag men hittade {len(team_id_by_name)}.")

                    # Andra passet: skapa 14 fiktiva spelare per lag.
                    inserted_players = 0
                    for club_name, league in team_specs:
                        team_id = team_id_by_name[club_name]
                        used_names = set()
                        numbers = random.sample(range(1, 100), 14)
                        for player_index in range(14):
                            while True:
                                player_name = f"{random.choice(star_first_names)} {random.choice(fun_surnames)}"
                                if player_name not in used_names:
                                    used_names.add(player_name)
                                    break
                            if player_index == 0:
                                position = "Målvakt"
                            else:
                                position = random.choices(
                                    ["Försvarare", "Mittfältare", "Anfallare"],
                                    weights=[4, 4, 3],
                                    k=1,
                                )[0]
                            birth_year = random.randint(2007, 2014)
                            first_name, last_name = player_name.split(" ", 1)
                            is_protected = 1 if player_index == 13 and club_name == team_specs[0][0] else 0
                            con.execute(
                                """INSERT INTO players(team_id,player_number,name,birth_year,position,first_name,last_name,is_protected)
                                   VALUES(?,?,?,?,?,?,?,?)""",
                                (team_id, numbers[player_index], player_name, birth_year, position,
                                 first_name, last_name, is_protected),
                            )
                            inserted_players += 1

                    # Två fiktiva domare med påhittade kontaktuppgifter och nivåer.
                    referee_first_names = ["Bengt", "Arvid", "Mats", "Sara", "Johan", "Linda", "Oskar", "Emma"]
                    referee_last_names = ["Domarsson", "Pipström", "Visselberg", "Linjeman", "Rättvik", "Matchlund"]
                    referee_levels = ["Distriktsdomare", "Regional domare", "Ungdomsdomare", "Senior domare"]
                    used_ref_names = set()
                    referee_target = max(2, min(8, demo_group_count))
                    for ref_index in range(referee_target):
                        while True:
                            ref_name = f"{random.choice(referee_first_names)} {random.choice(referee_last_names)}"
                            if ref_name not in used_ref_names:
                                used_ref_names.add(ref_name)
                                break
                        phone = f"070-{random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}"
                        email_local = ref_name.lower().replace(" ", ".").replace("å", "a").replace("ä", "a").replace("ö", "o")
                        email = f"{email_local}@demo.cupnavi.se"
                        con.execute(
                            "INSERT INTO referees(tournament_id,name,phone,email,referee_level) VALUES(?,?,?,?,?)",
                            (tid, ref_name, phone, email, random.choice(referee_levels)),
                        )

                    # Kontrollera trupperna innan vi godkänner transaktionen.
                    player_check = _one_from_cursor(
                        con.execute(
                            """SELECT COUNT(*) AS n
                               FROM players p JOIN teams t ON t.id=p.team_id
                               WHERE t.tournament_id=?""",
                            (tid,),
                        )
                    )
                    if int(player_check["n"] or 0) != inserted_players:
                        raise RuntimeError(
                            f"Truppkontrollen misslyckades: skapade {inserted_players}, hittade {player_check['n']}."
                        )

                    referee_check = _one_from_cursor(
                        con.execute("SELECT COUNT(*) AS n FROM referees WHERE tournament_id=?", (tid,))
                    )
                    if int(referee_check["n"] or 0) < referee_target:
                        raise RuntimeError(
                            f"Domarkontrollen misslyckades: förväntade minst {referee_target} domare, hittade {referee_check['n']}."
                        )

                    # Komplett kringdata för att testköra publik vy, lagportal och adminflöden.
                    now_iso = datetime.now().isoformat(timespec="seconds")
                    for team_row in created_teams:
                        plain_code = generate_access_code()
                        salt, code_hash = new_code_hash(plain_code)
                        con.execute(
                            """INSERT INTO participant_access_credentials(
                                   tournament_id,team_id,code_salt,code_hash,created_at,admin_code
                               ) VALUES(?,?,?,?,?,?)
                               ON CONFLICT(tournament_id,team_id) DO UPDATE SET
                                   code_salt=excluded.code_salt,code_hash=excluded.code_hash,
                                   created_at=excluded.created_at,admin_code=excluded.admin_code""",
                            (tid, team_row["id"], salt, code_hash, now_iso, plain_code),
                        )

                    con.execute(
                        """INSERT INTO sponsors(tournament_id,name,level,description,website_url,active,sort_order)
                           VALUES(?,?,?,?,?,?,?)""",
                        (tid, "CupNavi Demo Partner", "Huvudpartner", "Testpartner för sponsorvyn.",
                         "https://cup-navi.com", 1, 1),
                    )
                    con.execute(
                        """INSERT INTO functionaries(tournament_id,name,role,phone,email,pitch_number,notes,public_contact,active)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (tid, "Alex Cupvärd", "Cupvärd", "070-000 00 02", "funktionar@demo.cup-navi.com",
                         1, "Finns vid sekretariatet.", 1, 1),
                    )
                    con.execute(
                        """INSERT INTO offers(tournament_id,title,business_name,description,discount_code,active,sort_order)
                           VALUES(?,?,?,?,?,?,?)""",
                        (tid, "10 % på lunch", "Demo Café", "Visa CupNavi i kassan.", "CUP10", 1, 1),
                    )
                    for sort_order, (kind, label, detail) in enumerate([
                        ("Plan", "Plan 1", "Huvudplan"),
                        ("Plan", "Plan 2", "Plan bredvid kiosken"),
                        ("Kiosk", "Kiosk", "Mat och dryck"),
                        ("Parkering", "Parkering", "Bakom arenan"),
                        ("Sekretariat", "Sekretariat", "Information och tävlingsledning"),
                    ]):
                        con.execute(
                            "INSERT INTO venue_points(tournament_id,kind,label,detail,sort_order) VALUES(?,?,?,?,?)",
                            (tid, kind, label, detail, sort_order),
                        )
                    first_team_id = created_teams[0]["id"]
                    second_team_id = created_teams[1]["id"]
                    con.execute(
                        """INSERT INTO team_messages(tournament_id,sender_type,sender_team_id,recipient_type,recipient_team_id,created_at,subject,message)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (tid, "team", first_team_id, "team", second_team_id, now_iso,
                         "Träningsmatch", "Vi spelar gärna en träningsmatch mot er senare i höst."),
                    )
                    con.execute(
                        """INSERT INTO notifications(tournament_id,team_id,created_at,title,message,event_key)
                           VALUES(?,?,?,?,?,?)""",
                        (tid, first_team_id, now_iso, "Välkommen till democupen", "Detta är ett testmeddelande för laget.",
                         f"demo-welcome-{tid}"),
                    )
                    con.commit()
                    _clear_render_query_cache()
                    sync_competition_classes(tid, ["U14"])
                    st.success(
                        f"Testdata skapad: {demo_team_count} lag, {demo_group_count} grupper, "
                        f"{inserted_players} fiktiva spelare och {referee_target} fiktiva domare."
                    )
                    st.rerun()
                except Exception as exc:
                    try:
                        con.rollback()
                    except Exception:
                        pass
                    st.error(f"Demodata kunde inte skapas: {exc}")


            st.markdown("##### Testläge – välj hur långt cupen har kommit")
            st.caption(
                "Testlägena bygger ett komplett schema och fyller resultat, matchhändelser och status till vald nivå. "
                "Varje körning nollställer tidigare testresultat men behåller lag, trupper, domare, lagkoder och övrig demodata."
            )
            testdata_ready = (
                _demo_environment_allowed
                and int(demo_counts["teams_n"] or 0) > 0
                and int(demo_counts["groups_n"] or 0) > 0
            )
            if not testdata_ready:
                st.info("Skapa testdata i steg 1 innan du väljer hur långt turneringen har pågått.")

            # Browser-E2E does not mutate tournament lifecycle from inside a
            # Streamlit render. Downstream browser states are prepared by the test
            # fixture itself so rerender timing can never change tournament data.
            # Submit selection + action atomically. A normal selectbox rerun can replace
            # the button DOM exactly when it is clicked, which made the real UI flaky.
            with st.form(f"demo_progress_form_{tid}", border=False):
                demo_level = st.selectbox(
                    "Testnivå",
                    [
                        "Halva gruppspelet",
                        "Hela gruppspelet",
                        "Halva slutspelet",
                        "Hela cupen färdig",
                    ],
                    key=f"demo_progress_level_{tid}",
                    disabled=not testdata_ready,
                )
                generate_demo = st.form_submit_button(
                    "🧪 Generera valt testläge",
                    use_container_width=True,
                    type="primary",
                    disabled=not testdata_ready,
                )
            level_key = {
                "Halva gruppspelet": "half_group",
                "Hela gruppspelet": "full_group",
                "Halva slutspelet": "half_playoff",
                "Hela cupen färdig": "complete",
            }[demo_level]
            if generate_demo:
                with st.spinner(f"Bygger testläge: {demo_level}…", show_time=True):
                    ok, message = _demo_apply_progress_level(tid, level_key)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

            progress_counts = one_row(
                """SELECT
                     SUM(CASE WHEN stage='Gruppspel' THEN 1 ELSE 0 END) AS group_total,
                     SUM(CASE WHEN stage='Gruppspel' AND home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS group_played,
                     SUM(CASE WHEN stage<>'Gruppspel' THEN 1 ELSE 0 END) AS playoff_total,
                     SUM(CASE WHEN stage<>'Gruppspel' AND home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS playoff_played
                   FROM matches WHERE tournament_id=?""",
                (tid,),
            )
            st.caption(
                f"Aktuellt testläge: gruppspel {int(progress_counts['group_played'] or 0)}/{int(progress_counts['group_total'] or 0)} · "
                f"slutspel {int(progress_counts['playoff_played'] or 0)}/{int(progress_counts['playoff_total'] or 0)}."
            )


        feedback_rows = all_rows(
            "SELECT created_at,area,message,contact FROM feedback WHERE tournament_id=? ORDER BY id DESC LIMIT 50",
            (tid,),
        )
        with st.expander(f"Feedback från testare ({len(feedback_rows)})"):
            if not feedback_rows:
                st.caption("Ingen feedback har skickats ännu.")
            else:
                for item in feedback_rows:
                    st.markdown(f"**{item['area']}** · {item['created_at']}")
                    st.write(item["message"])
                    if item["contact"]:
                        st.caption(f"Kontakt: {item['contact']}")
                    st.divider()


if admin_page == "Cupinställningar":
    st.subheader("Cupinställningar")
    st.caption("Ändra cupens regler i den guidade setupen. Extra konsekvens- och teknikinfo visas bara vid behov.")
    _played_count = int(one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",(tid,))["n"] or 0)
    _is_started = tournament_lifecycle in ("live","completed") or _played_count > 0
    _is_public = bool(tournament["is_published"])
    _phase = "STARTAD" if _is_started else ("PUBLICERAD" if _is_public else "UTKAST")
    st.caption(f"Fas: **{_phase}** · Spelade matcher: **{_played_count}**")
    if st.button("Ändra cupens inställningar",type="primary",use_container_width=True,key=f"open_setup_{tid}"):
        st.session_state["new_tournament_setup_id"]=int(tid)
        st.session_state["preferred_tournament_id"]=int(tid)
        st.rerun()
    _deploy=deployment_diagnostics()
    with st.expander("Teknisk release-status", expanded=False):
        dc1,dc2,dc3=st.columns(3)
        dc1.metric("Aktiv release",_deploy["release"])
        dc2.metric("Deploy-fingerprint",_deploy["fingerprint_short"])
        dc3.metric("Automatiska kodomladdningar",_deploy["auto_refresh_count"])
        st.caption(
            f'Core på disk: {_deploy["core_disk_version"]} · importerad core: {_deploy["core_imported_version"]}'
        )
        if _deploy["last_auto_refresh"]:
            st.caption(f'Senaste automatiska kodomladdning: {_deploy["last_auto_refresh"]}')
        if _deploy["package_refreshed_this_run"]:
            st.success("Ny deploy upptäcktes och CupNavi-koden laddades om automatiskt i den här körningen.")
        elif not RELEASE_FILES_MISMATCH:
            st.success("App- och corefiler är synkade.")
    _admin_sport_rec=sport_setup_recommendation(_row_value(tournament,"sport","Fotboll"))
    st.caption(
        f'Sportprofil: **{_admin_sport_rec["display_name"]}** · '
        f'{_admin_sport_rec["periods"]} {_admin_sport_rec["period_label"]} × {_admin_sport_rec["minutes_per_period"]} min · '
        f'min. lagvila {_admin_sport_rec["minimum_rest_minutes"]} min.'
    )
    _settings_rules=one_row("SELECT * FROM schedule_rules WHERE tournament_id=?",(tid,))
    _saved_gc=int(_row_value(_settings_rules,"recommended_group_count",0) or 0)
    if _saved_gc:
        with st.expander("CupNavi formatrekommendation",expanded=False):
            st.write(
                f"Sparat förslag: **{_saved_gc} grupper** · cirka **{int(_row_value(_settings_rules,'recommended_group_size',0) or 0)} lag/grupp** · "
                f"**{int(_row_value(_settings_rules,'recommended_playoff_size',0) or 0)} lag i slutspel**."
            )
            st.caption("Det här är beslutsstöd. Det ändrar inte en pågående cup automatiskt.")

    with st.expander("Kontrollera konsekvens före större ändring", expanded=False):
        _phase_rows = [
            ("Namn, kontakt och publik information","Fri","Fri","Fri"),
            ("Domare/funktionärer","Fri","Fri","Framtida matcher"),
            ("Plan/tid för en framtida match","Fri","Fri","Tillåten med konfliktkontroll"),
            ("Plantider och schemaprioriteringar","Fri","Kräver omplanering","Endast framtida matcher"),
            ("Lag och grupper","Fri","Kräver omplanering","Låst"),
            ("Matchtid, poäng och tävlingsformat","Fri","Kräver omplanering","Låst efter första resultat"),
            ("Sport, region och tidszon","Låst grundegenskap","Låst","Låst"),
        ]
        render_centered_table(pd.DataFrame(_phase_rows,columns=["Parameter","Utkast","Publicerad","Startad"]))
        st.warning("CupNavi ska aldrig ändra redan spelade matcher automatiskt. Ändringar efter start får bara påverka framtida, ospelade matcher.")
        st.markdown("### Förhandskontroll före ändring")
        _impact_type=st.selectbox(
            "Vad vill du ändra?",
            ["match_duration","pitch_windows","priorities","group_structure","playoff_format","points"],
            format_func=lambda x:{
                "match_duration":"Matchtid / pauser",
                "pitch_windows":"Planernas öppettider",
                "priorities":"Schemaprioriteringar",
                "group_structure":"Lag eller gruppindelning",
                "playoff_format":"Slutspelsmodell",
                "points":"Poängsystem",
            }[x],
            key=f"impact_change_type_{tid}",
        )
        _impact=schedule_change_impact(tid,_impact_type)
        ic1,ic2,ic3=st.columns(3)
        ic1.metric("Spelade matcher",_impact["played"])
        ic2.metric("Framtida matcher",_impact["future"])
        ic3.metric("Påverkas av ändringen",_impact["affected"])
        if _impact["requires_regeneration"]:
            st.warning(
                f"Den här ändringen påverkar cirka **{_impact['affected']} framtida matcher** och kräver omplanering. "
                f"**{_impact['played']} redan spelade matcher skyddas och ändras inte.**"
            )
        elif _impact_type=="points":
            if _impact["played"]:
                st.error("Poängsystemet bör inte ändras efter registrerade resultat eftersom tabeller och historik då ändrar innebörd.")
            else:
                st.info("Poängsystemet kan ändras utan att schemat behöver regenereras.")
        else:
            st.info("Ändringen kräver ingen full regenerering.")

    st.stop()

if admin_page == "Kontroller":
    st.header("Kontroller")
    st.caption("Åtgärda blockerande fel först. Varningar och detaljer kan granskas därefter.")

    control_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    if control_rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
        control_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    control_errors, control_warnings, control_quality = validate_schedule(tid, tournament, control_rules)
    control_scheduled = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
        (tid,),
    )["n"]
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Blockerande fel", len(control_errors))
    cc2.metric("Varningar", len(control_warnings))
    cc3.metric("Schemalagda matcher", control_scheduled)
    if not control_scheduled:
        st.info("Det finns ännu inget spelschema att kontrollera. Skapa schemat på fliken Skapa och publicera schema.")
    elif control_errors:
        st.error("Publicering är blockerad tills följande fel är åtgärdade:")
        for message in control_errors:
            st.error(message)
    else:
        st.success("Inga blockerande schemafel hittades.")
    if control_warnings:
        st.warning("Följande varningar behöver granskas före publicering:")
        for message in control_warnings:
            st.warning(message)
    with st.expander("Fördjupad kontroll", expanded=False):
        if control_quality:
            st.subheader("Belastning och vila per lag")
            render_centered_table(pd.DataFrame(control_quality))

        unassigned_controls = all_rows("SELECT name FROM teams WHERE tournament_id=? AND group_id IS NULL ORDER BY name", (tid,))
        small_group_controls = []
        group_size_rows = all_rows(
            """SELECT g.id, g.name, COUNT(t.id) AS team_count
               FROM groups g
               LEFT JOIN teams t ON t.group_id=g.id
               WHERE g.tournament_id=?
               GROUP BY g.id, g.name
               ORDER BY g.name""",
            (tid,),
        )
        for group in group_size_rows:
            count = int(group["team_count"] or 0)
            if count < 2:
                small_group_controls.append(f"{group['name']} ({count} lag)")
        st.subheader("Grundkontroller")
        if unassigned_controls:
            st.warning("Lag utan grupp: " + ", ".join(row["name"] for row in unassigned_controls))
        else:
            st.success("Alla registrerade lag är placerade i en grupp.")
        if small_group_controls:
            st.warning("Grupper med färre än två lag: " + ", ".join(small_group_controls))
        else:
            st.success("Alla skapade grupper har minst två lag.")


    st.caption("Tekniska verktyg")
    with st.expander("Teknisk hälsa och backup", expanded=False):
        st.caption(
            "Det här området är till för drift och felsökning. Det påverkar inte själva turneringsreglerna."
        )
        try:
            with db() as con:
                technical_health = collect_database_health(con)
            hc1, hc2 = st.columns(2)
            health_ok = (
                technical_health["schema_version"] >= REQUIRED_SCHEMA_VERSION
                and not technical_health["missing_tables"]
            )
            hc1.metric(
                "Databasschema",
                f"v{technical_health['schema_version']}",
                help=f"CupNavi {APP_BUILD_VERSION} kräver minst schema v{REQUIRED_SCHEMA_VERSION}.",
            )
            hc2.metric(
                "Teknisk status",
                "OK" if health_ok else "Kontroll krävs",
            )
            if health_ok:
                st.success("✓ Databasen har rätt schema och alla kritiska tabeller finns.")
            else:
                if technical_health["schema_version"] < REQUIRED_SCHEMA_VERSION:
                    st.error(
                        f"Databasschema v{technical_health['schema_version']} används, "
                        f"men appen kräver minst v{REQUIRED_SCHEMA_VERSION}."
                    )
                if technical_health["missing_tables"]:
                    st.error(
                        "Kritiska tabeller saknas: "
                        + ", ".join(technical_health["missing_tables"])
                    )
        except Exception as exc:
            st.error(f"Teknisk hälsokontroll kunde inte köras: {exc}")

        st.divider()
        st.markdown("#### Säkerhetskopia av vald turnering")
        st.caption(
            "Backupen är en portabel JSON-fil med turneringens struktur, lag, grupper, spelare, "
            "schema, resultat, slutspel, driftdata och historik. Återställning skapar alltid en ny cup "
            "så att originalet aldrig skrivs över."
        )

        if st.button(
            "Förbered backup",
            key=f"prepare_backup_{tid}",
            use_container_width=True,
        ):
            with st.spinner("CupNavi samlar turneringsdata…"):
                backup_datasets = {
                    "tournaments": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM tournaments WHERE id=?", (tid,)
                        )
                    ],
                    "schedule_rules": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,)
                        )
                    ],
                    "competition_classes": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM competition_classes WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "tournament_day_windows": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM tournament_day_windows WHERE tournament_id=? ORDER BY play_date", (tid,)
                        )
                    ],
                    "pitch_day_windows": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM pitch_day_windows WHERE tournament_id=? ORDER BY play_date,pitch_number", (tid,)
                        )
                    ],
                    "pitches": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM pitches WHERE tournament_id=? ORDER BY pitch_number", (tid,)
                        )
                    ],
                    "pitch_travel_times": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM pitch_travel_times WHERE tournament_id=? ORDER BY from_pitch_number,to_pitch_number", (tid,)
                        )
                    ],
                    "groups": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM groups WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "teams": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM teams WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "players": [
                        dict(row) for row in all_rows(
                            """SELECT p.* FROM players p
                               JOIN teams t ON t.id=p.team_id
                               WHERE t.tournament_id=? ORDER BY p.id""",
                            (tid,),
                        )
                    ],
                    "schedule_requests": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM schedule_requests WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "participant_access_credentials": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM participant_access_credentials WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "team_messages": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM team_messages WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "referees": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM referees WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "brackets": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "matches": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM matches WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "player_match_stats": [
                        dict(row) for row in all_rows(
                            """SELECT s.* FROM player_match_stats s
                               JOIN matches m ON m.id=s.match_id
                               WHERE m.tournament_id=? ORDER BY s.id""",
                            (tid,),
                        )
                    ],
                    "match_rosters": [
                        dict(row) for row in all_rows(
                            """SELECT r.* FROM match_rosters r
                               JOIN matches m ON m.id=r.match_id
                               WHERE m.tournament_id=? ORDER BY r.match_id,r.team_id,r.player_id""",
                            (tid,),
                        )
                    ],
                    "offers": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM offers WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "sponsors": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM sponsors WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "functionaries": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM functionaries WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "functionary_shifts": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM functionary_shifts WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "visitor_sessions": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM visitor_sessions WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "feedback": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM feedback WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "audit_log": [dict(row) for row in all_rows("SELECT * FROM audit_log WHERE tournament_id=? ORDER BY id", (tid,))],
                    "cup_feed": [dict(row) for row in all_rows("SELECT * FROM cup_feed WHERE tournament_id=? ORDER BY id", (tid,))],
                    "notifications": [dict(row) for row in all_rows("SELECT * FROM notifications WHERE tournament_id=? ORDER BY id", (tid,))],
                    "notification_subscriptions": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM notification_subscriptions WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "notification_deliveries": [
                        dict(row) for row in all_rows(
                            """SELECT d.* FROM notification_deliveries d
                               JOIN notification_subscriptions s ON s.id=d.subscription_id
                               WHERE s.tournament_id=? ORDER BY d.id""",
                            (tid,),
                        )
                    ],
                    "control_incidents": [
                        dict(row) for row in all_rows(
                            "SELECT * FROM control_incidents WHERE tournament_id=? ORDER BY id", (tid,)
                        )
                    ],
                    "venue_points": [dict(row) for row in all_rows("SELECT * FROM venue_points WHERE tournament_id=? ORDER BY id", (tid,))],
                    "referee_acknowledgements": [dict(row) for row in all_rows("SELECT * FROM referee_acknowledgements WHERE tournament_id=? ORDER BY id", (tid,))],
                }
                backup_bytes, backup_sha = build_backup_bytes(
                    APP_VERSION,
                    tid,
                    backup_datasets,
                )
                st.session_state[f"backup_bytes_{tid}"] = backup_bytes
                st.session_state[f"backup_sha_{tid}"] = backup_sha

        if f"backup_bytes_{tid}" in st.session_state:
            safe_backup_name = re.sub(
                r"[^A-Za-z0-9_-]+",
                "_",
                tournament["name"] or "CupNavi",
            ).strip("_")
            st.success(
                "✓ Backup klar. SHA-256: "
                + st.session_state[f"backup_sha_{tid}"][:16]
                + "…"
            )
            st.download_button(
                "Ladda ner backup",
                data=st.session_state[f"backup_bytes_{tid}"],
                file_name=f"{safe_backup_name}{BACKUP_FILE_SUFFIX}",
                mime="application/json",
                key=f"download_backup_{tid}",
                use_container_width=True,
            )

        st.divider()
        st.markdown("#### Återställ från backup")
        st.caption(
            "Återställning skriver aldrig över en befintlig cup. CupNavi skapar en ny cup med nya interna ID:n "
            "och återkopplar lag, grupper, matcher, slutspel och relaterad data."
        )
        uploaded_backup = st.file_uploader(
            "Välj CupNavi-backup (.json)",
            type=["json"],
            key=f"restore_backup_upload_{tid}",
        )
        if uploaded_backup is not None:
            try:
                _restore_bytes = uploaded_backup.getvalue()
                _restore_payload = validate_backup_bytes(_restore_bytes)
                _restore_source = _restore_payload["data"]["tournaments"][0]
                st.success(
                    f"Backup verifierad · skapad {_restore_payload.get('created_at','okänd tid')} · "
                    f"källa: {_restore_source.get('name','Okänd cup')}"
                )
                rc1, rc2 = st.columns([2, 1])
                restore_name = rc1.text_input(
                    "Namn på återställd cup",
                    value=f"{_restore_source.get('name','CupNavi')} – återställd",
                    key=f"restore_backup_name_{tid}",
                )
                restore_environment = rc2.selectbox(
                    "Miljö",
                    ["test", "production"],
                    format_func=lambda value: "Testmiljö" if value == "test" else "Riktig cup",
                    key=f"restore_backup_environment_{tid}",
                )
                restore_confirm = st.checkbox(
                    "Jag förstår att återställningen skapar en ny, opublicerad cup och inte ändrar originalet.",
                    key=f"restore_backup_confirm_{tid}",
                )
                if st.button(
                    "↩️ Återställ som ny cup",
                    type="primary",
                    use_container_width=True,
                    disabled=not restore_confirm or not restore_name.strip(),
                    key=f"restore_backup_run_{tid}",
                ):
                    with st.spinner("Återställer backup atomiskt…"):
                        con = db()
                        try:
                            restored_tid = restore_backup_as_new_tournament(
                                con,
                                _restore_bytes,
                                name=restore_name.strip(),
                                environment_type=restore_environment,
                            )
                        finally:
                            con.close()
                    _clear_render_query_cache()
                    st.session_state["preferred_tournament_id"] = int(restored_tid)
                    st.session_state[f"admin_page_{restored_tid}"] = "Adminöversikt"
                    st.success(f"Backup återställd som ny cup (ID {restored_tid}).")
                    st.rerun()
            except Exception as exc:
                st.error(f"Backupen kunde inte återställas: {exc}")

    with st.expander("📱 Mobilkontroll – Android och iPhone"):
        st.caption("Snabb kontroll före publicering. Testa helst minst en Android/Chrome och en iPhone/Safari.")
        st.markdown(
            """
            - Visningsläge och Admin går att nå utan sidomenyn.
            - Publikflikarna går att svepa horisontellt.
            - Datum- och tidsfält är läsbara och öppnar rätt mobilkontroll.
            - Ingen sida zoomar in automatiskt när ett textfält aktiveras.
            - Tabeller och slutspel går att scrolla utan att hela sidan blir bredare än skärmen.
            - Knappar går att trycka på utan att ligga för tätt.
            """
        )

    with st.expander("⚡ Prestandadiagnostik"):
        st.caption("Mäter databasarbete under den aktuella sidladdningen. Använd siffrorna när en sida känns seg.")
        pc1, pc2, pc3, pc4, pc5 = st.columns(5)
        pc1.metric("DB-anrop", _PERF["db_calls"])
        pc2.metric("DB-tid", f"{_PERF['db_ms']:.0f} ms")
        pc3.metric("SQL-cache", _PERF["cache_hits"])
        pc4.metric("Beräkningscache", _PERF["derived_hits"])
        pc5.metric("Skrivningar", _PERF["writes"])
        if _PERF["db_calls"] >= 20:
            st.warning("Många databasfrågor på samma sidladdning. Den här sidan bör optimeras vidare.")
        elif _PERF["db_ms"] >= 1500:
            st.warning("Databasen står för en stor del av väntetiden på den här sidladdningen.")
        else:
            st.success("Ingen tydlig databasflaskhals syns i den här mätningen.")

if admin_page == "Problem & lösningar":
    st.header("Problem & lösningar")
    st.caption("Här samlas schemaproblem och valideringsproblem som går att åtgärda utan tekniska stack traces. Förslag rangordnas efter minsta åtgärd och största sannolika effekt.")
    problem_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    if problem_rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
        problem_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    p_errors, p_warnings, _ = validate_schedule(tid, tournament, problem_rules)
    unresolved = int((one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NULL",(tid,)) or {"n":0})["n"] or 0)

    # v142: transparent Schedule Score based on the actual saved schedule.
    _quality_rows = [dict(r) for r in all_rows(
        "SELECT scheduled_start,home_source,away_source FROM matches WHERE tournament_id=?",
        (tid,),
    )]
    _late_pref_rows = all_rows(
        "SELECT id,earliest_first_time FROM teams WHERE tournament_id=? AND late_first_match=1 AND earliest_first_time IS NOT NULL",
        (tid,),
    )
    _late_prefs = {int(r["id"]): r["earliest_first_time"] for r in _late_pref_rows}
    _min_rest = int(problem_rules["consecutive_match_break_minutes"] or 0) if bool(problem_rules["avoid_consecutive_matches"]) else 0
    _quality = assess_schedule(_quality_rows, min_rest_minutes=_min_rest, late_preferences=_late_prefs)
    st.subheader("Schedule Score")
    _q1,_q2,_q3,_q4 = st.columns(4)
    _q1.metric("Schemakvalitet", f"{_quality['score']}/100")
    _q2.metric("Ej schemalagda", _quality["unscheduled"])
    _q3.metric("Vilokonflikter", _quality["short_rest"])
    _q4.metric("Missade startönskemål", _quality["late_preferences_missed"])
    st.caption(
        f"Bedömning: **{_quality['grade']}**. Poängen är deterministisk och bygger på sparad schemadata – "
        "det är inte en AI-sannolikhet. Kapacitetsproblem väger tyngst."
    )
    if _quality["penalties"]:
        _penalty_text = " · ".join(
            f"{name}: −{value}" for name,value in _quality["penalties"].items() if value
        )
        if _penalty_text:
            st.caption("Poängavdrag: " + _penalty_text)

    if unresolved:
        context = _schedule_recovery_context(tid,tournament,problem_rules,unresolved)
        st.error(f"{unresolved} matcher saknar schematid.")
        if context.get("physical_shortfall", 0) > 0:
            _slot_minutes = max(1, int(context.get("extension_minutes", 0) or 0))
            st.markdown(
                f"**Varför?** Nuvarande planfönster rymmer cirka **{context.get('capacity',0)} matcher** "
                f"men cupen innehåller **{context.get('total_matches',0)} matcher**. "
                f"Det saknas minst **{context.get('physical_shortfall',0)} matchplatser**."
            )
        else:
            st.markdown("**Varför?** Den teoretiska plankapaciteten räcker, men lagvila, domare eller hårda önskemål blockerar återstående placeringar.")
        st.markdown("**Vad påverkas?** Schemat kan inte betraktas som färdigt eller publiceringsklart.")
        render_schedule_recovery_actions(tid,tournament,problem_rules,context)
    if p_errors:
        st.subheader("Blockerande valideringsproblem")
        for i,msg in enumerate(p_errors,1): st.error(f"{i}. {msg}")
    if p_warnings:
        st.subheader("Varningar")
        for i,msg in enumerate(p_warnings,1): st.warning(f"{i}. {msg}")
    if not unresolved and not p_errors and not p_warnings:
        st.success("Inga aktuella schema- eller valideringsproblem hittades.")

if admin_page == "Önskemålscentral":
    st.header("Önskemålscentral")
    st.caption("Här samlas lagens schemakrav och önskemål. Hårda krav får inte brytas; mjuka önskemål prioriteras mot varandra.")
    _wish_rules=one_row("SELECT * FROM schedule_rules WHERE tournament_id=?",(tid,))
    _wish_teams=all_rows("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name",(tid,))
    _wish_rows=all_rows(
        """SELECT r.*,t.name AS team_name
           FROM schedule_requests r
           JOIN teams t ON t.id=r.team_id
           WHERE r.tournament_id=?
           ORDER BY CASE r.status WHEN 'Godkänd' THEN 0 WHEN 'Väntar' THEN 1 ELSE 2 END,
                    r.priority,r.id""",
        (tid,),
    )
    _approved=[r for r in _wish_rows if r["status"]=="Godkänd"]
    _hard=[r for r in _approved if r["strength"]=="Hårt krav"]
    _wish_score=schedule_score_report(tid,_wish_rules)
    wc1,wc2,wc3,wc4=st.columns(4)
    wc1.metric("Önskemål",len(_wish_rows))
    wc2.metric("Godkända",len(_approved))
    wc3.metric("Hårda krav",len(_hard))
    wc4.metric("Uppfyllda",f"{_wish_score['fulfilled']}/{_wish_score['request_total']}")

    if _wish_teams:
        with st.form(f"new_schedule_request_{tid}",clear_on_submit=True):
            wr1,wr2,wr3=st.columns(3)
            _team_id=wr1.selectbox("Lag",[r["id"] for r in _wish_teams],format_func=lambda x: next(r["name"] for r in _wish_teams if r["id"]==x))
            _type=wr2.selectbox("Typ",list(REQUEST_TYPE_LABELS),format_func=lambda x: REQUEST_TYPE_LABELS[x])
            _strength=wr3.selectbox("Klassning",["Önskemål","Hårt krav"])
            _value_label={
                "late_start":"Tid HH:MM",
                "latest_finish":"Tid HH:MM",
                "preferred_pitch":"Plannummer",
                "extra_rest":"Extra vila i minuter",
                "avoid_late_group":"Lämna tomt",
            }[_type]
            _value=st.text_input(_value_label,placeholder="Exempel: 11:00, 2 eller 60")
            _note=st.text_input("Kommentar",placeholder="Exempel: lång resväg")
            if st.form_submit_button("Lägg till",type="primary",use_container_width=True):
                run(
                    """INSERT INTO schedule_requests(
                        tournament_id,team_id,request_type,request_value,strength,status,priority,note,created_at
                    ) VALUES(?,?,?,?,?,'Väntar',100,?,?)""",
                    (tid,_team_id,_type,_value.strip(),_strength,_note.strip(),datetime.now().isoformat(timespec="seconds")),
                )
                st.success("Önskemålet är registrerat och väntar på godkännande.")
                st.rerun()
    else:
        st.info("Lägg till lag innan önskemål kan registreras.")

    if _wish_rows:
        st.markdown("### Inkomna önskemål")
        for req in _wish_rows:
            ok,detail=evaluate_schedule_request(tid,req,_wish_rules)
            state="✓ Uppfyllt" if ok is True else ("⚠ Ej uppfyllt" if ok is False else "Ej bedömt")
            with st.container(border=True):
                c1,c2,c3=st.columns([4,2,2])
                c1.markdown(f"**{html.escape(req['team_name'])}** · {html.escape(schedule_request_label(req))}")
                c1.caption(f"{req['strength']} · {state} · {detail}")
                c2.write(f"Status: **{req['status']}**")
                if req["status"]!="Godkänd" and c3.button("Godkänn",key=f"approve_req_{req['id']}",use_container_width=True):
                    saved, request_reason = _set_schedule_request_status_if_current(
                        req["id"], tid, req["status"], "Godkänd"
                    )
                    if saved:
                        # Mirror legacy supported wishes to team fields used by scheduler.
                        if req["request_type"]=="late_start":
                            run("UPDATE teams SET late_first_match=1,earliest_first_time=? WHERE id=? AND tournament_id=?",(req["request_value"],req["team_id"],tid))
                        elif req["request_type"]=="avoid_late_group":
                            run("UPDATE teams SET avoid_late_group_match=1 WHERE id=? AND tournament_id=?",(req["team_id"],tid))
                    else:
                        st.warning("Önskemålet ändrades av en annan administratör och din äldre åtgärd genomfördes inte.")
                    st.rerun()
                if req["status"]!="Nekad" and c3.button("Neka",key=f"reject_req_{req['id']}",use_container_width=True):
                    saved, request_reason = _set_schedule_request_status_if_current(
                        req["id"], tid, req["status"], "Nekad"
                    )
                    if not saved:
                        st.warning("Önskemålet ändrades av en annan administratör och din äldre åtgärd genomfördes inte.")
                    st.rerun()

        _approved_rows=all_rows(
            """SELECT r.*,t.name AS team_name FROM schedule_requests r
               JOIN teams t ON t.id=r.team_id
               WHERE r.tournament_id=? AND r.status='Godkänd'
               ORDER BY r.priority,r.id""",
            (tid,),
        )
        if _approved_rows:
            st.markdown("### Prioritera godkända önskemål")
            _labels=[f"{r['team_name']} · {schedule_request_label(r)}" for r in _approved_rows]
            if sort_items is not None:
                _sorted=sort_items(
                    _labels,direction="vertical",
                    custom_style=".sortable-item{background:#fff;color:#172033;border:1px solid #cbd5e1;border-radius:10px;padding:9px 11px;margin:4px 0;font-weight:700;}",
                    key=f"request_priority_center_{tid}",
                )
                if _sorted and _sorted!=_labels:
                    _id_by_label={label:int(row["id"]) for label,row in zip(_labels,_approved_rows)}
                    with db() as con:
                        for pos,label in enumerate(_sorted,start=1):
                            con.execute("UPDATE schedule_requests SET priority=? WHERE id=?",(pos,_id_by_label[label]))
                        con.commit()
                    _clear_render_query_cache()
                    st.success("Prioriteringen sparades.")
                    st.rerun()
            else:
                st.caption("Drag-and-drop kräver streamlit-sortables.")
            st.caption("Överst = viktigast om önskemål konkurrerar om samma tider.")
    st.stop()


if admin_page == "Lag":
    st.header("Lag")
    st.caption("Lägg till lagen först. Gruppindelning görs sedan under Grupper.")
    class_rows = sync_competition_classes(tid)
    current_classes = [competition_class_label(row) for row in class_rows]
    with st.expander("Tävlingsklasser", expanded=False):
        if class_rows:
            _class_summary = " · ".join(
                f"**{competition_class_label(row)}** ({_row_value(row, 'difficulty', 'Medel') or 'Medel'})"
                for row in class_rows
            )
            st.markdown(_class_summary)
        else:
            st.warning("Ingen tävlingsklass finns ännu.")
        if st.button(
            "Hantera tävlingsklasser",
            key=f"go_manage_classes_{tid}",
            use_container_width=True,
        ):
            st.session_state[admin_page_key] = "Adminöversikt"
            st.rerun()
    max_teams = int(tournament["expected_team_count"] or 0)
    registered_team_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tid,))["n"]
    team_limit_reached = bool(max_teams and registered_team_count >= max_teams)
    if max_teams:
        status_icon = "✓" if team_limit_reached else "👥"
        st.caption(f"{status_icon} {registered_team_count} av {max_teams} lag/deltagare registrerade." + (" Maxantalet är uppnått." if team_limit_reached else ""))
    if team_limit_reached:
        if st.button("Ändra maxantal lag", key=f"change_team_limit_{tid}", use_container_width=True):
            st.session_state[admin_page_key] = "Adminöversikt"
            st.rerun()
        st.caption("Formuläret för att lägga till lag är dolt eftersom maxantalet är uppnått.")
    else:
      with st.container(border=True):
        team_name = st.text_input("Lagnamn")
        class_rows = competition_classes(tid)
        class_ids = [row["id"] for row in class_rows]
        class_options = class_ids if len(class_ids) == 1 else ([None] + class_ids)
        team_class_id = st.selectbox(
            "Tävlingsklass",
            class_options or [None],
            index=0,
            format_func=lambda value: "Ingen särskild tävlingsklass" if value is None else next(competition_class_label(row) for row in class_rows if row["id"] == value),
            key=f"new_team_competition_class_{tid}",
            disabled=not bool(class_rows),
            help="När cupen bara har en tävlingsklass väljs den automatiskt. Lag i olika klasser hålls sportsligt separerade.",
        )
        team_age_class = next((competition_class_label(row) for row in class_rows if row["id"] == team_class_id), "")
        with st.expander("Fler laguppgifter", expanded=False):
            st.caption("Matchställ, kontaktperson och reseönskemål. Standardvärden fungerar om du vill fylla i detta senare.")
            hc1, hc2, hc3 = st.columns([1.2, 1, 1])
            home_pattern = hc1.selectbox("Mönster hemma", KIT_PATTERNS, key="new_home_pattern")
            primary = hc2.color_picker("Hemma – färg 1", "#111827")
            home_color_2 = hc3.color_picker("Hemma – färg 2", "#FFFFFF", help="Används när stället inte är helfärgat.")
            st.markdown(kit_preview_html(home_pattern, primary, home_color_2, "Förhandsvisning hemmaställ"), unsafe_allow_html=True)

            ac1, ac2, ac3 = st.columns([1.2, 1, 1])
            away_pattern = ac1.selectbox("Mönster borta", KIT_PATTERNS, key="new_away_pattern")
            secondary = ac2.color_picker("Borta – färg 1", "#FFFFFF")
            away_color_2 = ac3.color_picker("Borta – färg 2", "#111827", help="Används när stället inte är helfärgat.")
            st.markdown(kit_preview_html(away_pattern, secondary, away_color_2, "Förhandsvisning bortaställ"), unsafe_allow_html=True)

            rc1, rc2, rc3 = st.columns(3)
            responsible_name = rc1.text_input("Namn", key=f"new_team_responsible_name_{tid}")
            responsible_phone = rc2.text_input("Telefon", key=f"new_team_responsible_phone_{tid}")
            responsible_email = rc3.text_input("E-post", key=f"new_team_responsible_email_{tid}")
            distance = st.number_input("Resväg i kilometer", 0, 5000, 0)
            travel_note = st.text_input("Resekommentar", placeholder="Exempel: Reser samma morgon")
            late_first_match = st.checkbox("Önskar senare första match", help="Använd detta exempelvis för lag med lång resväg.")
            earliest_first_time = st.time_input("Första match tidigast", value=datetime.strptime("10:00", "%H:%M").time(), help="Tiden används bara om Önskar senare första match är markerat.")
            avoid_late_group_match = st.checkbox("Undvik senaste gruppspelsmatchen", help="CupNavi försöker undvika dagens sista gruppspelstid för laget när schemat tillåter det.")
        if st.button("Lägg till lag", type="primary", disabled=team_limit_reached, key=f"add_team_{tid}"):
            current_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tid,))["n"]
            if max_teams and current_count >= max_teams:
                st.error(f"Det går inte att lägga till fler än {max_teams} lag i den här turneringen.")
            elif team_name.strip():
                try:
                    new_team_id = insert_team_with_limit(
                        tid,
                        team_name.strip(),
                        primary,
                        secondary,
                        home_pattern,
                        home_color_2,
                        away_pattern,
                        away_color_2,
                        distance,
                        late_first_match,
                        earliest_first_time.strftime("%H:%M") if late_first_match else None,
                        travel_note.strip(),
                        avoid_late_group_match,
                    )
                    run(
                        "UPDATE teams SET responsible_name=?,responsible_phone=?,responsible_email=?,age_class=?,competition_class_id=? WHERE id=?",
                        (responsible_name.strip(), responsible_phone.strip(), responsible_email.strip(), team_age_class or None, team_class_id, new_team_id),
                    )
                    st.rerun()
                except TeamLimitReachedError as exc:
                    hard_max = int(exc.args[0]) if exc.args else max_teams
                    st.error(f"Det går inte att lägga till fler än {hard_max} lag i den här turneringen.")
                except sqlite3.IntegrityError as exc:
                    if "TEAM_LIMIT_REACHED" in str(exc):
                        fresh_limit = one_row("SELECT expected_team_count FROM tournaments WHERE id=?", (tid,))
                        hard_max = int(fresh_limit["expected_team_count"] or 0) if fresh_limit else max_teams
                        st.error(f"Det går inte att lägga till fler än {hard_max} lag i den här turneringen.")
                    else:
                        raise
            else:
                st.error("Ange ett lagnamn.")

    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    st.divider()
    st.subheader("Skapade lag")
    if teams:
        group_names = {
            row["id"]: row["name"]
            for row in all_rows("SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
        }
        render_centered_table(
            pd.DataFrame([
                {
                    "Lag": team_row["name"],
                    "Tävlingsklass": _team_value(team_row, "age_class", "") or "–",
                    "Grupp": group_names.get(team_row["group_id"], "Ej placerad"),
                    "Ansvarig": _team_value(team_row, "responsible_name", "") or "–",
                    "Telefon": _team_value(team_row, "responsible_phone", "") or "–",
                    "E-post": _team_value(team_row, "responsible_email", "") or "–",
                    "Resväg km": team_row["distance_km"] or 0,
                }
                for team_row in teams
            ])
        )
    else:
        render_empty_state("Inga deltagare ännu", "Lägg till första laget/deltagaren eller använd Import för flera på en gång.", "👥")

    if teams and bool(_row_value(tournament, "enable_team_checkin", 1)):
        with st.expander("Digital lagincheckning", expanded=False):
            st.divider()
            st.subheader("✅ Digital lagincheckning")
            st.caption("Markera vilka lag som är på plats. Statusen sparas med tidsstämpel och syns direkt för tävlingsledningen.")
            checkin_df = pd.DataFrame([
                {"team_id": row["id"], "Lag": row["name"], "På plats": bool(row["checked_in"]), "Incheckad": row["checked_in_at"] or ""}
                for row in teams
            ])
            edited_checkins = st.data_editor(
                checkin_df, hide_index=True, use_container_width=True,
                disabled=["team_id", "Lag", "Incheckad"],
                column_order=["Lag", "På plats", "Incheckad"],
                column_config={"På plats": st.column_config.CheckboxColumn("På plats")},
                key=f"team_checkins_{tid}",
            )
            if st.button("Spara incheckning", key=f"save_checkins_{tid}", type="primary", use_container_width=True):
                changed = 0
                original = {int(row["id"]): row for row in teams}
                now_iso = datetime.now().isoformat(timespec="seconds")
                with db() as con:
                    for _, edited_row in edited_checkins.iterrows():
                        team_id = int(edited_row["team_id"])
                        new_value = 1 if bool(edited_row["På plats"]) else 0
                        old_value = int(original[team_id]["checked_in"] or 0)
                        if new_value == old_value:
                            continue
                        changed += 1
                        con.execute(
                            "UPDATE teams SET checked_in=?,checked_in_at=?,checked_in_by=? WHERE id=?",
                            (new_value, now_iso if new_value else None, "Admin" if new_value else None, team_id),
                        )
                    con.commit()
                if changed:
                    _clear_render_query_cache()
                    for _, edited_row in edited_checkins.iterrows():
                        team_id = int(edited_row["team_id"]); new_value = 1 if bool(edited_row["På plats"]) else 0
                        old_value = int(original[team_id]["checked_in"] or 0)
                        if new_value != old_value:
                            team_name = original[team_id]["name"]
                            record_audit(tid, "team_checkin", "team", f"{team_name}: {'incheckad' if new_value else 'incheckning borttagen'}",
                                         entity_id=team_id, before={"checked_in": old_value}, after={"checked_in": new_value}, reversible=False)
                    st.success(f"Incheckning uppdaterad för {changed} lag.")
                    st.rerun()
                else:
                    st.info("Inga ändringar att spara.")

        with st.expander("Lagportal – koder", expanded=False):
            st.caption("Här ser administratören alla aktuella lagkoder. Inloggningen verifieras fortfarande mot en saltad hash. Skydda tabellen från obehöriga.")
            credentials = {
                int(row["team_id"]): row
                for row in all_rows(
                    "SELECT team_id,admin_code,created_at,rotated_at FROM participant_access_credentials WHERE tournament_id=?",
                    (tid,),
                )
            }
            code_rows = []
            missing_display_codes = []
            for team_row in teams:
                cred = credentials.get(int(team_row["id"]))
                visible_code = (cred["admin_code"] if cred else None) or ""
                if not visible_code:
                    missing_display_codes.append(int(team_row["id"]))
                code_rows.append({
                    "Lag": team_row["name"],
                    "Lagkod": visible_code or ("Äldre kod – skapa ny" if cred else "Saknas"),
                    "Senast ändrad": (cred["rotated_at"] or cred["created_at"]) if cred else "–",
                })
            render_centered_table(pd.DataFrame(code_rows))

            regenerate_all_key = f"confirm_regenerate_all_team_codes_{tid}"
            all_team_codes_notice_key = f"all_team_codes_notice_{tid}"
            if all_team_codes_notice_key in st.session_state:
                notice_type, notice_text = st.session_state.pop(all_team_codes_notice_key)
                getattr(st, notice_type)(notice_text)

            if teams:
                if not st.session_state.get(regenerate_all_key):
                    if st.button(
                        "Regenerera koder för alla lag",
                        key=f"request_regenerate_all_team_codes_{tid}",
                        use_container_width=True,
                    ):
                        st.session_state[regenerate_all_key] = True
                        st.rerun()
                else:
                    st.warning(
                        f"Är du säker? Alla {len(teams)} nuvarande lagkoder slutar fungera direkt "
                        "och måste delas ut på nytt."
                    )
                    bulk_yes, bulk_no = st.columns(2)
                    if bulk_yes.button(
                        "Ja, regenerera alla",
                        key=f"confirm_regenerate_all_team_codes_button_{tid}",
                        type="primary",
                        use_container_width=True,
                    ):
                        generated_codes, bulk_error = _rotate_all_participant_codes(tid)
                        st.session_state.pop(regenerate_all_key, None)
                        if bulk_error:
                            st.session_state[all_team_codes_notice_key] = (
                                "error",
                                f"Lagkoderna kunde inte regenereras: {bulk_error}",
                            )
                        else:
                            for team_id, _plain_code in generated_codes:
                                record_audit(
                                    tid,
                                    "participant_code_rotated",
                                    "team",
                                    "Lagkod regenererad via massåtgärd",
                                    entity_id=team_id,
                                    actor="Admin",
                                )
                            st.session_state[all_team_codes_notice_key] = (
                                "success",
                                f"Nya koder skapades för {len(generated_codes)} lag. "
                                "Alla tidigare lagkoder är nu ogiltiga.",
                            )
                        st.rerun()
                    if bulk_no.button(
                        "Avbryt",
                        key=f"cancel_regenerate_all_team_codes_{tid}",
                        use_container_width=True,
                    ):
                        st.session_state.pop(regenerate_all_key, None)
                        st.rerun()

            if missing_display_codes:
                st.warning(f"{len(missing_display_codes)} lag saknar en visningsbar kod. Äldre hashade koder kan inte återläsas.")
                if st.button("Skapa/ersätt koder för alla som saknar visningsbar kod", key=f"generate_missing_portal_codes_{tid}", type="primary", use_container_width=True):
                    now_iso = datetime.now().isoformat(timespec="seconds")
                    with db() as con:
                        for missing_team_id in missing_display_codes:
                            plain_code = generate_access_code()
                            salt, code_hash = new_code_hash(plain_code)
                            con.execute(
                                """INSERT INTO participant_access_credentials(tournament_id,team_id,code_salt,code_hash,created_at,rotated_at,admin_code)
                                   VALUES(?,?,?,?,?,NULL,?)
                                   ON CONFLICT(tournament_id,team_id) DO UPDATE SET code_salt=excluded.code_salt,code_hash=excluded.code_hash,rotated_at=excluded.created_at,admin_code=excluded.admin_code""",
                                (tid, missing_team_id, salt, code_hash, now_iso, plain_code),
                            )
                        con.commit()
                    _clear_render_query_cache()
                    st.success("Koder skapades. Tidigare koder för berörda lag är nu ogiltiga.")
                    st.rerun()

            access_team_id = st.selectbox(
                "Lag för att skapa/återställa kod",
                [row["id"] for row in teams],
                format_func=lambda selected_id: next(row["name"] for row in teams if row["id"] == selected_id),
                key=f"portal_access_team_{tid}",
            )
            credential = one_row(
                "SELECT id,admin_code,created_at,rotated_at FROM participant_access_credentials WHERE tournament_id=? AND team_id=?",
                (tid, access_team_id),
            )
            portal_code_notice_key=f"portal_code_notice_{tid}_{access_team_id}"
            if portal_code_notice_key in st.session_state:
                notice_type, notice_text = st.session_state.pop(portal_code_notice_key)
                getattr(st, notice_type)(notice_text)
            individual_confirm_key = f"confirm_regenerate_team_code_{tid}_{access_team_id}"
            rotate_individual = False
            if not credential:
                rotate_individual = st.button(
                    "Skapa ny kod",
                    key=f"generate_portal_code_{tid}_{access_team_id}",
                    type="primary",
                )
            elif not st.session_state.get(individual_confirm_key):
                if st.button(
                    "Regenerera lagkod",
                    key=f"request_regenerate_portal_code_{tid}_{access_team_id}",
                ):
                    st.session_state[individual_confirm_key] = True
                    st.rerun()
            else:
                selected_team_name = next(
                    row["name"] for row in teams if row["id"] == access_team_id
                )
                st.warning(
                    f"Är du säker? Den nuvarande lagkoden för {selected_team_name} slutar fungera direkt."
                )
                indiv_yes, indiv_no = st.columns(2)
                if indiv_yes.button(
                    "Ja, regenerera",
                    key=f"confirm_regenerate_portal_code_{tid}_{access_team_id}",
                    type="primary",
                ):
                    rotate_individual = True
                    st.session_state.pop(individual_confirm_key, None)
                if indiv_no.button(
                    "Avbryt",
                    key=f"cancel_regenerate_portal_code_{tid}_{access_team_id}",
                ):
                    st.session_state.pop(individual_confirm_key, None)
                    st.rerun()

            if rotate_individual:
                changed, rotate_reason, plain_code = _rotate_participant_code_if_unchanged(
                    tid,
                    access_team_id,
                    _credential_snapshot(credential),
                )
                if changed:
                    record_audit(
                        tid,
                        "participant_code_rotated",
                        "team",
                        "Ny portal-kod skapad",
                        entity_id=access_team_id,
                        actor="Admin",
                    )
                    st.session_state[portal_code_notice_key]=("success",f"Ny lagkod: **{plain_code}**")
                else:
                    st.session_state[portal_code_notice_key]=(
                        "warning",
                        "Lagkoden ändrades av en annan administratör. Ingen äldre kodrotation skrevs över.",
                    )
                st.rerun()

        with st.expander("Lagmeddelanden", expanded=False):
            st.caption("Meddelanden som skickas till arrangören visas här. Du kan också skriva direkt till valfritt deltagande lag.")
            team_names = {int(row["id"]): row["name"] for row in teams}
            organizer_messages = all_rows(
                """SELECT * FROM team_messages
                   WHERE tournament_id=? AND recipient_type='organizer'
                   ORDER BY created_at DESC,id DESC LIMIT 200""",
                (tid,),
            )
            unread_organizer_ids = [int(row["id"]) for row in organizer_messages if not row["read_at"]]
            organizer_inbox_label = (
                f"🔴 Inkorg ({len(unread_organizer_ids)})"
                if unread_organizer_ids else "Inkorg"
            )
            inbox_tab, compose_tab, history_tab = st.tabs([organizer_inbox_label, "Skriv till lag", "Alla meddelanden"])
            with inbox_tab:
                if unread_organizer_ids and st.button(
                    f"Markera alla som lästa ({len(unread_organizer_ids)})",
                    key=f"admin_mark_messages_read_{tid}",
                ):
                    _mark_team_messages_read(
                        unread_organizer_ids,
                        tournament_id=tid,
                        recipient_type="organizer",
                    )
                    st.rerun()
                if not organizer_messages:
                    st.info("Inga meddelanden till arrangören ännu.")
                for msg in organizer_messages:
                    sender, _ = _message_party_label(msg, team_names)
                    with st.container(border=True):
                        unread_prefix = "🔴 " if not msg["read_at"] else ""
                        st.markdown(f"**{unread_prefix}{html.escape(msg['subject'])}**")
                        st.caption(f"Från {html.escape(sender)} · {msg['created_at']}")
                        st.write(msg["message"])
                        if msg["sender_team_id"] is not None:
                            reply_key = f"admin_reply_{msg['id']}"
                            with st.form(reply_key, clear_on_submit=True):
                                reply_text = st.text_area("Svar", key=f"reply_text_{msg['id']}", max_chars=3000, height=90)
                                reply_send = st.form_submit_button("Skicka svar")
                            if reply_send:
                                try:
                                    reply_token_key=f"admin_reply_request_token_{msg['id']}"
                                    if reply_token_key not in st.session_state:
                                        st.session_state[reply_token_key]=new_token()
                                    _send_team_message(
                                        tid,
                                        "organizer",
                                        f"SV: {msg['subject']}",
                                        reply_text,
                                        recipient_type="team",
                                        recipient_team_id=int(msg["sender_team_id"]),
                                        request_token=st.session_state[reply_token_key],
                                    )
                                    st.session_state.pop(reply_token_key,None)
                                    st.success("Svaret är skickat.")
                                    st.rerun()
                                except ValueError as exc:
                                    st.error(str(exc))

            with compose_tab:
                admin_message_token_key=f"admin_message_request_token_{tid}"
                if admin_message_token_key not in st.session_state:
                    st.session_state[admin_message_token_key]=new_token()
                with st.form(f"admin_message_team_{tid}", clear_on_submit=True):
                    target_team_id = st.selectbox(
                        "Till lag",
                        [int(row["id"]) for row in teams],
                        format_func=lambda team_id: team_names[team_id],
                        key=f"admin_message_target_{tid}",
                    )
                    admin_subject = st.text_input("Ämne", placeholder="Exempel: Information från arrangören", max_chars=200)
                    admin_message = st.text_area("Meddelande", max_chars=3000, height=120)
                    admin_send = st.form_submit_button("Skicka meddelande", type="primary")
                if admin_send:
                    try:
                        _send_team_message(
                            tid,
                            "organizer",
                            admin_subject,
                            admin_message,
                            recipient_type="team",
                            recipient_team_id=int(target_team_id),
                            request_token=st.session_state[admin_message_token_key],
                        )
                        st.session_state.pop(admin_message_token_key,None)
                        st.success("Meddelandet är skickat.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

            with history_tab:
                all_team_messages = all_rows(
                    "SELECT * FROM team_messages WHERE tournament_id=? ORDER BY created_at DESC,id DESC LIMIT 300",
                    (tid,),
                )
                if not all_team_messages:
                    st.info("Ingen meddelandehistorik ännu.")
                else:
                    message_rows = []
                    for msg in all_team_messages:
                        sender, recipient = _message_party_label(msg, team_names)
                        message_rows.append({
                            "Tid": msg["created_at"],
                            "Från": sender,
                            "Till": recipient,
                            "Ämne": msg["subject"],
                            "Meddelande": msg["message"],
                        })
                    render_centered_table(pd.DataFrame(message_rows))

    with st.expander("Redigera eller ta bort lag", expanded=False):
        if teams:
            edit_team_id = st.selectbox("Välj lag", [t["id"] for t in teams], format_func=lambda x: next(t["name"] for t in teams if t["id"] == x), key="edit_team")
            edit_team = next(t for t in teams if t["id"] == edit_team_id)
            with st.container(border=True):
                edited_name = st.text_input("Lagnamn", value=edit_team["name"], key=f"edit_name_{edit_team_id}")
                edit_class_rows = competition_classes(tid)
                edit_class_options = [None] + [row["id"] for row in edit_class_rows]
                saved_class_id = _team_value(edit_team, "competition_class_id", None)
                if saved_class_id not in edit_class_options:
                    saved_class_id = None
                edited_class_id = st.selectbox(
                    "Tävlingsklass", edit_class_options,
                    index=edit_class_options.index(saved_class_id),
                    format_func=lambda value: "Ingen särskild tävlingsklass" if value is None else next(competition_class_label(row) for row in edit_class_rows if row["id"] == value),
                    key=f"edit_competition_class_{edit_team_id}",
                )
                edited_age_class = next((competition_class_label(row) for row in edit_class_rows if row["id"] == edited_class_id), "")
                st.markdown("#### Hemmaställ")
                eh1, eh2, eh3 = st.columns([1.2, 1, 1])
                saved_home_pattern = _team_value(edit_team, "home_pattern", "Helfärgad")
                edited_home_pattern = eh1.selectbox(
                    "Mönster hemma", KIT_PATTERNS,
                    index=KIT_PATTERNS.index(saved_home_pattern) if saved_home_pattern in KIT_PATTERNS else 0,
                    key=f"edit_home_pattern_{edit_team_id}",
                )
                edited_primary = eh2.color_picker("Hemma – färg 1", edit_team["primary_color"], key=f"edit_home_color1_{edit_team_id}")
                edited_home_color_2 = eh3.color_picker("Hemma – färg 2", _team_value(edit_team, "home_color_2", "#FFFFFF"), key=f"edit_home_color2_{edit_team_id}")
                st.markdown(kit_preview_html(edited_home_pattern, edited_primary, edited_home_color_2, "Hemmaställ"), unsafe_allow_html=True)

                st.markdown("#### Bortaställ")
                ea1, ea2, ea3 = st.columns([1.2, 1, 1])
                saved_away_pattern = _team_value(edit_team, "away_pattern", "Helfärgad")
                edited_away_pattern = ea1.selectbox(
                    "Mönster borta", KIT_PATTERNS,
                    index=KIT_PATTERNS.index(saved_away_pattern) if saved_away_pattern in KIT_PATTERNS else 0,
                    key=f"edit_away_pattern_{edit_team_id}",
                )
                edited_secondary = ea2.color_picker("Borta – färg 1", edit_team["secondary_color"], key=f"edit_away_color1_{edit_team_id}")
                edited_away_color_2 = ea3.color_picker("Borta – färg 2", _team_value(edit_team, "away_color_2", "#111827"), key=f"edit_away_color2_{edit_team_id}")
                st.markdown(kit_preview_html(edited_away_pattern, edited_secondary, edited_away_color_2, "Bortaställ"), unsafe_allow_html=True)

                st.markdown("#### Ansvarig kontaktperson")
                erc1, erc2, erc3 = st.columns(3)
                edited_responsible_name = erc1.text_input("Namn", value=_team_value(edit_team, "responsible_name", "") or "", key=f"edit_responsible_name_{edit_team_id}")
                edited_responsible_phone = erc2.text_input("Telefon", value=_team_value(edit_team, "responsible_phone", "") or "", key=f"edit_responsible_phone_{edit_team_id}")
                edited_responsible_email = erc3.text_input("E-post", value=_team_value(edit_team, "responsible_email", "") or "", key=f"edit_responsible_email_{edit_team_id}")
                edited_distance = st.number_input("Resväg i kilometer", 0, 5000, int(edit_team["distance_km"] or 0), key=f"edit_distance_{edit_team_id}")
                edited_travel_note = st.text_input("Resekommentar", value=edit_team["travel_note"] or "", key=f"edit_travel_note_{edit_team_id}")
                edited_late_first = st.checkbox("Önskar senare första match", value=bool(edit_team["late_first_match"]), key=f"edit_late_first_{edit_team_id}")
                edited_avoid_late = st.checkbox("Undvik senaste gruppspelsmatchen", value=bool(_row_value(edit_team, "avoid_late_group_match", 0)), key=f"edit_avoid_late_{edit_team_id}")
                saved_earliest = edit_team["earliest_first_time"] or "10:00"
                edited_earliest = st.time_input(
                    "Första match tidigast",
                    value=datetime.strptime(saved_earliest, "%H:%M").time(),
                    help="Tiden används bara om Önskar senare första match är markerat.",
                    key=f"edit_earliest_{edit_team_id}",
                )
                if st.button("Spara ändringar", type="primary", key=f"save_team_{edit_team_id}"):
                    if edited_name.strip():
                        saved, save_reason = _admin_update_team_if_unchanged(
                            edit_team_id,
                            tid,
                            _admin_team_snapshot(edit_team),
                            name=edited_name.strip(),
                            primary_color=edited_primary,
                            secondary_color=edited_secondary,
                            home_pattern=edited_home_pattern,
                            home_color_2=edited_home_color_2,
                            away_pattern=edited_away_pattern,
                            away_color_2=edited_away_color_2,
                            distance_km=edited_distance,
                            late_first_match=edited_late_first,
                            earliest_first_time=edited_earliest.strftime("%H:%M") if edited_late_first else None,
                            travel_note=edited_travel_note.strip(),
                            avoid_late_group_match=edited_avoid_late,
                            responsible_name=edited_responsible_name.strip(),
                            responsible_phone=edited_responsible_phone.strip(),
                            responsible_email=edited_responsible_email.strip(),
                            age_class=edited_age_class or None,
                            competition_class_id=edited_class_id,
                        )
                        if saved:
                            st.success("Lagets uppgifter är sparade.")
                        elif save_reason == "invalid_email":
                            st.error("Ange en giltig e-postadress eller lämna fältet tomt.")
                        else:
                            st.warning("Laget ändrades av någon annan och dina äldre uppgifter skrevs inte över.")
                        st.rerun()
                    else:
                        st.error("Lagnamnet får inte vara tomt.")
            _team_delete_locked = (
                production_history_locked(tid, tournament)
                and team_has_played_result(tid, edit_team_id)
            )
            if _team_delete_locked:
                st.warning(
                    "🔒 Laget har ett registrerat resultat i en riktig cup och kan därför inte raderas. "
                    "Testmiljöer kan fortfarande radera laget fritt."
                )
            confirm_team_delete = st.checkbox(
                "Jag förstår att lagets trupp, statistik och berörda matcher tas bort",
                key=f"confirm_team_{edit_team_id}",
                disabled=_team_delete_locked,
            )
            if st.button(
                "Ta bort laget",
                disabled=_team_delete_locked or not confirm_team_delete,
                key=f"delete_team_{edit_team_id}",
            ):
                deleted, delete_reason = _admin_delete_team_if_unchanged(
                    edit_team_id,
                    tid,
                    _admin_team_snapshot(edit_team),
                )
                if not deleted and delete_reason == "conflict":
                    st.warning("Laget ändrades av någon annan och raderades därför inte.")
                st.rerun()
        else:
            st.info("Det finns inga lag att redigera.")


if admin_page == "Grupper":
    st.header("Grupper")
    _group_history_locked = production_history_locked(tid, tournament)
    if _group_history_locked:
        st.warning(
            "🔒 Gruppstrukturen är låst efter första resultatet i en riktig cup. "
            "Testmiljöer kan fortfarande ändra grupper fritt."
        )
    st.caption("Skapa grupper och placera lagen. CupNavi visar rekommendation när sådan finns.")
    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    if not teams:
        st.warning("Lägg först till lagen under fliken Lag innan du skapar grupper.")
    class_rows = competition_classes(tid)
    class_ids = [row["id"] for row in class_rows]
    _group_rules=one_row("SELECT * FROM schedule_rules WHERE tournament_id=?",(tid,))
    _recommended_groups=int(_row_value(_group_rules,"recommended_group_count",0) or 0)
    if _recommended_groups > 0:
        st.caption(f"Rekommendation: **{_recommended_groups} grupper** · cirka **{int(_row_value(_group_rules,'recommended_group_size',0) or 0)} lag per grupp**.")
        _existing_groups_count=int(one_row("SELECT COUNT(*) AS n FROM groups WHERE tournament_id=?",(tid,))["n"] or 0)
        if _existing_groups_count == 0 and teams:
            if st.button(f"Skapa {_recommended_groups} rekommenderade grupper",type="primary",use_container_width=True,key=f"create_recommended_groups_{tid}"):
                class_default=class_rows[0] if len(class_rows)==1 else None
                class_id=_row_value(class_default,"id",None) if class_default else None
                class_name=competition_class_label(class_default) if class_default else None
                with db() as con:
                    for idx in range(_recommended_groups):
                        group_name=f"Grupp {chr(65+idx)}" if idx < 26 else f"Grupp {idx+1}"
                        con.execute(
                            "INSERT INTO groups(tournament_id,name,age_class,competition_class_id) VALUES(?,?,?,?)",
                            (tid,group_name,class_name,class_id),
                        )
                    con.commit()
                _clear_render_query_cache()
                st.success("Rekommenderade grupper skapades. Dra nu lagen till rätt grupp.")
                st.rerun()

    with st.form("new_group", clear_on_submit=True):
        group_name = st.text_input("Gruppnamn", placeholder="Grupp A")
        group_class_options = class_ids if len(class_ids) == 1 else ([None] + class_ids)
        group_class_id = st.selectbox(
            "Tävlingsklass",
            group_class_options or [None],
            format_func=lambda value: "Ingen särskild tävlingsklass" if value is None else next(competition_class_label(row) for row in class_rows if row["id"] == value),
            disabled=not bool(class_rows),
            key=f"new_group_competition_class_{tid}",
        )
        group_class_name = next((competition_class_label(row) for row in class_rows if row["id"] == group_class_id), "")
        if st.form_submit_button("Lägg till grupp", type="primary", disabled=_group_history_locked or not bool(teams)):
            if group_name.strip():
                run("INSERT INTO groups(tournament_id,name,age_class,competition_class_id) VALUES(?,?,?,?)", (tid, group_name.strip(), group_class_name or None, group_class_id))
                st.rerun()
            st.error("Ange ett gruppnamn.")

    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    tournament_age_classes = [competition_class_label(row) for row in class_rows]  # compatibility for existing branch conditions

    st.divider()
    st.subheader("Placera lagen i rätt grupp")
    if not teams:
        st.info("Inga lag är registrerade.")
    elif not groups:
        st.info("Skapa minst en grupp ovan för att kunna placera lagen.")
    elif sort_items is not None and not tournament_age_classes:
        st.caption("Dra lagen mellan rutorna och klicka sedan på Spara gruppindelning.")
        sortable_team_labels = {
            t["id"]: t["name"] + "\u2063" + "".join("\u200b" if bit == "0" else "\u200c" for bit in bin(t["id"])[2:])
            for t in teams
        }
        team_id_by_item = {label: team_id for team_id, label in sortable_team_labels.items()}
        containers = [{"header": "Ej placerade", "items": [sortable_team_labels[t["id"]] for t in teams if t["group_id"] is None]}]
        for g in groups:
            containers.append({"header": g["name"], "items": [sortable_team_labels[t["id"]] for t in teams if t["group_id"] == g["id"]]})
        sorted_containers = sort_items(
            containers,
            multi_containers=True,
            key=(
                f"team_group_sort_{tid}_"
                f"g{'_'.join(str(g['id']) for g in groups)}_"
                f"t{'_'.join(str(t['id']) for t in teams)}"
            ),
            custom_style="""
            .sortable-container { border: 1px solid #d1d5db; border-radius: 8px; }
            .sortable-container-header { font-weight: 700; padding: 8px; }
            .sortable-item { background: #f3f4f6; color: #111827; border-radius: 6px; margin: 5px; }
            """,
        )
        if st.button("Spara gruppindelning", type="primary", disabled=_group_history_locked):
            group_by_name = {g["name"]: g["id"] for g in groups}
            with db() as con:
                for container in sorted_containers:
                    target_group = group_by_name.get(container["header"])
                    for item in container["items"]:
                        selected_team_id = team_id_by_item[item]
                        con.execute("UPDATE teams SET group_id=? WHERE id=?", (target_group, selected_team_id))
                con.commit()
            st.success("Gruppindelningen sparades.")
            st.rerun()
    else:
        if tournament_age_classes:
            st.caption("Lag kan bara placeras i grupper inom samma tävlingsklass.")
        else:
            st.warning("Dra-och-släpp kräver tillägget streamlit-sortables. Reservläget används tills det installerats.")
        for t in teams:
            c1, c2, c3 = st.columns([4, 3, 2])
            c1.markdown(f"**{t['name']}**")
            team_class_id = _row_value(t, "competition_class_id", None)
            eligible_groups = [g for g in groups if not class_rows or _row_value(g, "competition_class_id", None) == team_class_id]
            options = [None] + [g["id"] for g in eligible_groups]
            current_index = options.index(t["group_id"]) if t["group_id"] in options else 0
            new_group = c2.selectbox("Grupp", options, index=current_index, key=f"group_{t['id']}", label_visibility="collapsed", format_func=lambda x: "Ingen grupp" if x is None else next(g["name"] for g in eligible_groups if g["id"] == x))
            if c3.button("Spara", key=f"save_group_{t['id']}"):
                if not _group_history_locked:
                    run("UPDATE teams SET group_id=? WHERE id=?", (new_group, t["id"]))
                st.rerun()

    st.divider()
    with st.expander("Redigera eller ta bort grupp"):
        if groups:
            edit_group_id = st.selectbox("Välj grupp", [g["id"] for g in groups], format_func=lambda x: next(g["name"] for g in groups if g["id"] == x), key="edit_group")
            edit_group = next(g for g in groups if g["id"] == edit_group_id)
            with st.form("edit_group_form"):
                edited_group_name = st.text_input("Gruppnamn", value=edit_group["name"], disabled=_group_history_locked)
                group_class_options = [None] + [row["id"] for row in class_rows]
                saved_group_class_id = _row_value(edit_group, "competition_class_id", None)
                if saved_group_class_id not in group_class_options:
                    saved_group_class_id = None
                edited_group_class_id = st.selectbox(
                    "Tävlingsklass", group_class_options,
                    index=group_class_options.index(saved_group_class_id),
                    format_func=lambda value: "Ingen särskild tävlingsklass" if value is None else next(competition_class_label(row) for row in class_rows if row["id"] == value),
                    disabled=_group_history_locked or not bool(class_rows),
                )
                edited_group_class_name = next((competition_class_label(row) for row in class_rows if row["id"] == edited_group_class_id), "")
                if st.form_submit_button("Spara grupp", type="primary", disabled=_group_history_locked):
                    if edited_group_name.strip():
                        assigned_other_class = one_row(
                            "SELECT COUNT(*) AS n FROM teams WHERE group_id=? AND COALESCE(competition_class_id,-1)!=COALESCE(?, -1)",
                            (edit_group_id, edited_group_class_id),
                        )["n"]
                        if assigned_other_class:
                            st.error("Gruppen innehåller lag från en annan tävlingsklass. Flytta lagen först.")
                        else:
                            saved, save_reason = _admin_update_group_if_unchanged(
                                edit_group_id,
                                tid,
                                _admin_group_snapshot(edit_group),
                                name=edited_group_name.strip(),
                                age_class=edited_group_class_name or None,
                                competition_class_id=edited_group_class_id,
                            )
                            if not saved and save_reason == "conflict":
                                st.warning("Gruppen ändrades av någon annan och dina äldre uppgifter skrevs inte över.")
                            st.rerun()
                    else:
                        st.error("Gruppnamnet får inte vara tomt.")
            confirm_group_delete = st.checkbox(
                "Jag förstår att gruppens matcher och slutspel som använder gruppen tas bort, och att lagen blir oplacerade",
                key=f"confirm_group_{edit_group_id}",
                disabled=_group_history_locked,
            )
            if st.button(
                "Ta bort gruppen",
                disabled=_group_history_locked or not confirm_group_delete,
                key=f"delete_group_{edit_group_id}",
            ):
                deleted, delete_reason = _admin_delete_group_if_unchanged(
                    edit_group_id,
                    tid,
                    _admin_group_snapshot(edit_group),
                )
                if not deleted and delete_reason == "conflict":
                    st.warning("Gruppen ändrades av någon annan och raderades därför inte.")
                st.rerun()
        else:
            st.info("Det finns inga grupper att redigera.")


if admin_page == "Trupper":
    st.header("Trupper")
    st.caption("Välj lag och registrera spelare. Matchtrupper och portalregler finns som extra verktyg.")
    with st.expander("⚙️ Regler för Lagportal och matchtrupper", expanded=False):
        rc1, rc2 = st.columns(2)
        portal_max_roster = rc1.number_input("Max spelare i truppen (0 = ingen gräns)", 0, 200, int(_row_value(tournament, "max_roster_size", 0) or 0), key=f"max_roster_{tid}")
        portal_deadline = rc2.number_input("Matchtrupp låses minuter före match", 0, 1440, int(_row_value(tournament, "squad_deadline_minutes", 30) or 30), key=f"squad_deadline_{tid}")
        portal_public_contact = st.checkbox("Tillåt lagledare/deltagaransvarig att ange en publik kontaktperson", value=bool(_row_value(tournament, "allow_team_public_contact", 0)), key=f"allow_public_contact_{tid}")
        if st.button("Spara portalregler", key=f"save_portal_rules_{tid}", type="primary"):
            run("UPDATE tournaments SET max_roster_size=?,squad_deadline_minutes=?,allow_team_public_contact=? WHERE id=?", (portal_max_roster, portal_deadline, int(portal_public_contact), tid))
            st.success("Portalreglerna är sparade.")
            st.rerun()
    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    if not teams:
        st.info("Lägg först till ett lag.")
    else:
        team_id = st.selectbox("Välj lag", [t["id"] for t in teams], format_func=lambda x: next(t["name"] for t in teams if t["id"] == x))
        with st.form("new_player", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            pname = c1.text_input("Spelare")
            number = c2.number_input("Tröjnummer", 0, 99, 0)
            birth = c3.number_input("Födelseår", 1980, 2030, 2014)
            position = c4.selectbox("Position", ["Ej angiven", "Målvakt", "Försvarare", "Mittfältare", "Anfallare"])
            if st.form_submit_button("Lägg till spelare", type="primary"):
                if pname.strip():
                    run("INSERT INTO players(team_id,player_number,name,birth_year,position) VALUES(?,?,?,?,?)", (team_id, number, pname.strip(), birth, position))
                    st.rerun()
                st.error("Ange spelarens namn.")
        players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (team_id,))
        render_centered_table(pd.DataFrame([{"Nr": p["player_number"], "Spelare": p["name"], "Födelseår": p["birth_year"], "Position": p["position"]} for p in players]))

        with st.expander("Matchtrupper – admin", expanded=False):
            admin_team_matches = [
                row for row in all_rows("SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,id", (tid,))
                if team_id in _match_team_ids(row)
            ]
            if not admin_team_matches:
                st.info("Laget har ännu inga schemalagda matcher.")
            elif not players:
                st.info("Lägg till spelare innan matchtrupp kan registreras.")
            else:
                admin_match_id = st.selectbox("Välj match för matchtrupp", [row["id"] for row in admin_team_matches], format_func=lambda mid: _portal_match_label(next(row for row in admin_team_matches if row["id"] == mid)), key=f"admin_squad_match_{team_id}")
                existing_admin_squad = {int(row["player_id"]) for row in all_rows("SELECT player_id FROM match_rosters WHERE match_id=? AND team_id=?", (admin_match_id, team_id))}
                admin_player_ids = [int(row["id"]) for row in players]
                admin_selected = st.multiselect(
                    "Spelare i matchtruppen",
                    admin_player_ids,
                    default=[pid for pid in admin_player_ids if pid in existing_admin_squad],
                    format_func=lambda pid: next(f"#{row['player_number'] if row['player_number'] is not None else '–'} {row['name']}" for row in players if int(row["id"]) == int(pid)),
                    key=f"admin_match_roster_{admin_match_id}_{team_id}",
                )
                if st.button("Spara matchtrupp som admin", key=f"admin_save_squad_{admin_match_id}_{team_id}", type="primary"):
                    saved, save_reason = _save_match_roster_if_unchanged(
                        admin_match_id,
                        team_id,
                        admin_selected,
                        existing_admin_squad,
                        "Admin",
                    )
                    if saved:
                        record_audit(tid, "match_roster_saved", "match", f"Admin sparade matchtrupp för {next(row['name'] for row in teams if row['id'] == team_id)}", entity_id=admin_match_id, actor="Admin")
                        st.success("Matchtruppen är sparad. Admin kan ändra även efter deadline.")
                    elif save_reason == "conflict":
                        st.warning("Matchtruppen ändrades av någon annan och skrevs inte över. Senaste truppen laddas om.")
                    else:
                        st.error("Matchtruppen kunde inte sparas eftersom en vald spelare inte längre tillhör laget.")
                    st.rerun()


if admin_page == "Domare":
    st.header("Domare")
    st.caption("Lägg till domare för automatisk eller manuell matchtilldelning.")

    st.subheader("Åtkomstkoder")
    st.caption("Matchrapportör och domare ligger på samma nivå. Varje roll har en egen fyrsiffrig kod för den aktiva turneringen.")

    def render_role_code_card(label, table_name, session_prefix):
        credential = one_row(
            f"SELECT code_hash,created_at,rotated_at FROM {table_name} WHERE tournament_id=?",
            (tid,),
        )
        with st.container(border=True):
            st.markdown(f"**{label}**")
            if credential:
                st.caption(
                    "Kod aktiv"
                    + (
                        f" · ändrad {str(credential['rotated_at']).replace('T',' ')}"
                        if credential["rotated_at"] else ""
                    )
                )
            else:
                st.caption("Ingen kod skapad ännu.")

            code_key = f"new_{session_prefix}_code_{tid}"
            confirm_key = f"confirm_regenerate_{session_prefix}_code_{tid}"

            # Initial creation is non-destructive. Re-generation invalidates the
            # current code and therefore always requires an explicit confirmation.
            if not credential:
                create_requested = st.button(
                    "Generera 4-siffrig kod",
                    key=f"generate_{session_prefix}_code_{tid}",
                    type="primary",
                    use_container_width=True,
                )
            else:
                create_requested = False
                if not st.session_state.get(confirm_key):
                    if st.button(
                        "Regenerera ny kod",
                        key=f"request_regenerate_{session_prefix}_code_{tid}",
                        use_container_width=True,
                    ):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.warning(
                        f"Är du säker? Den nuvarande koden för {label.lower()} slutar fungera direkt."
                    )
                    yes_col, no_col = st.columns(2)
                    if yes_col.button(
                        "Ja, regenerera",
                        key=f"confirm_regenerate_{session_prefix}_{tid}",
                        type="primary",
                        use_container_width=True,
                    ):
                        create_requested = True
                        st.session_state.pop(confirm_key, None)
                    if no_col.button(
                        "Avbryt",
                        key=f"cancel_regenerate_{session_prefix}_{tid}",
                        use_container_width=True,
                    ):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()

            if create_requested:
                new_code = generate_short_numeric_code(4)
                code_salt, code_hash = new_code_hash(new_code)
                now_text = datetime.now().isoformat(timespec="seconds")
                with db() as con:
                    existing = con.execute(
                        f"SELECT tournament_id FROM {table_name} WHERE tournament_id=?",
                        (tid,),
                    ).fetchone()
                    if existing:
                        con.execute(
                            f"UPDATE {table_name} SET code_salt=?,code_hash=?,rotated_at=? WHERE tournament_id=?",
                            (code_salt, code_hash, now_text, tid),
                        )
                    else:
                        con.execute(
                            f"INSERT INTO {table_name}(tournament_id,code_salt,code_hash,created_at,rotated_at) VALUES(?,?,?,?,NULL)",
                            (tid, code_salt, code_hash, now_text),
                        )
                    con.commit()
                st.session_state[code_key] = new_code
                st.rerun()

            if st.session_state.get(code_key):
                st.markdown(
                    f"<div style='font-size:2rem;font-weight:900;letter-spacing:.22em;"
                    f"text-align:center;padding:12px;border:1px solid #d9e2dd;border-radius:12px;"
                    f"background:#fff'>{html.escape(st.session_state[code_key])}</div>",
                    unsafe_allow_html=True,
                )
                st.caption("Kopiera eller dela koden nu. Den visas bara efter generering.")

    code_col1, code_col2 = st.columns(2)
    with code_col1:
        render_role_code_card("Matchrapportör", "match_reporter_credentials", "reporter")
    with code_col2:
        render_role_code_card("Domare", "referee_credentials", "referee")

    with st.form("new_referee", clear_on_submit=True):
        rname = st.text_input("Namn")
        with st.expander("Kontaktuppgifter", expanded=False):
            phone = st.text_input("Telefon")
            email = st.text_input("E-post")
        if st.form_submit_button("Lägg till domare", type="primary", use_container_width=True):
            if not rname.strip():
                st.error("Ange domarens namn.")
            elif email.strip() and ("@" not in email or "." not in email.rsplit("@",1)[-1]):
                st.error("Ange en giltig e-postadress eller lämna fältet tomt.")
            else:
                run(
                    "INSERT INTO referees(tournament_id,name,phone,email) VALUES(?,?,?,?)",
                    (tid, rname.strip(), phone.strip(), email.strip()),
                )
                st.rerun()
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    if not refs:
        st.caption("Inga domare registrerade ännu.")
    else:
        st.caption(f"{len(refs)} registrerade domare")
        with st.expander("Visa domarlista & kontaktuppgifter", expanded=False):
            render_centered_table(pd.DataFrame([
                {"Namn": r["name"], "Telefon": r["phone"], "E-post": r["email"]}
                for r in refs
            ]))


if admin_page == "Skapa och publicera schema":
    st.header("Schema")
    st.caption("Skapa eller uppdatera hela spelschemat. Detaljer och specialverktyg visas bara när du öppnar dem.")
    if "schedule_message" in st.session_state:
        message_type, message_text = st.session_state.pop("schedule_message")
        getattr(st, message_type)(message_text)

    with st.expander("Regelverk & schemakvalitet", expanded=False):
        st.markdown("#### 1. Sparat regelverk")
        rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
        if rules is None:
            run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
            rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
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
    too_small_groups = [
        group["name"] for group in schedule_groups
        if one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"] < 2
    ]
    group_match_total = one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND stage='Gruppspel'", (tid,))["n"]
    unscheduled_group_total = one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND stage='Gruppspel' AND scheduled_start IS NULL", (tid,))["n"]
    scheduled_total = one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL", (tid,))["n"]
    unpublished_total = one_row("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=0", (tid,))["n"]
    played_result_total = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (tid,),
    )["n"]
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
        _playoff_specs_preview, _playoff_setup_error = playoff_specs_for_tournament(tid, tournament)
        if tournament["playoff_format"] != "Inget slutspel":
            if _playoff_setup_error:
                st.error(f"Slutspel kan inte genereras: {_playoff_setup_error}")
            elif _playoff_specs_preview:
                _playoff_match_estimate = sum(max(0, int(size) - 1) + (1 if bool(tournament["bronze_match"]) and int(size) >= 4 else 0) for _, size, _ in _playoff_specs_preview)
                st.success(f"Slutspel redo att genereras · {len(_playoff_specs_preview)} träd · cirka {_playoff_match_estimate} slutspelsmatcher.")
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

    with st.expander("Exportera schema", expanded=False):
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

    with st.expander("Reseinformation", expanded=False):
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
            with db() as con:
                con.executemany("UPDATE matches SET scheduled_start=?,pitch_number=?,schedule_locked=?,schedule_published=? WHERE id=?", undo_rows)
                con.execute("UPDATE tournaments SET is_published=0,schedule_dirty=0 WHERE id=?", (tid,))
                con.commit()
            _clear_render_query_cache()
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
                    with db() as con:
                        con.executemany(
                            """UPDATE matches
                               SET scheduled_start=?,pitch_number=?,schedule_locked=?,schedule_published=0
                               WHERE id=?""",
                            updates,
                        )
                        con.execute(
                            "UPDATE tournaments SET is_published=0,schedule_dirty=0 WHERE id=?",
                            (tid,),
                        )
                        con.commit()
                    _clear_render_query_cache()
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
                    run(
                        "UPDATE matches SET scheduled_start=?,pitch_number=?,referee_id=?,schedule_locked=?,schedule_published=0 WHERE id=?",
                        (adjusted_start, adjusted_pitch, adjusted_referee, int(adjusted_locked), adjust_id),
                    )
                    run("UPDATE tournaments SET is_published=0 WHERE id=?", (tid,))
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
            with db() as con:
                for _, row in edited_schedule.iterrows():
                    home_score = None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"])
                    away_score = None if pd.isna(row["Bortamål"]) else int(row["Bortamål"])
                    con.execute("UPDATE matches SET home_score=?,away_score=? WHERE id=?", (home_score, away_score, int(row["match_id"])))
                    if tournament["is_published"]:
                        con.execute(
                            "UPDATE matches SET schedule_published=1 WHERE id=? AND scheduled_start IS NOT NULL",
                            (int(row["match_id"]),),
                        )
                con.commit()
            st.success("Resultaten sparades.")
        st.caption("Målskyttar, assist, varningar och utvisningar registreras under fliken Matchhändelser och visas därefter automatiskt här.")


if admin_page == "Matcher och resultat":
    st.header("Resultat")
    st.caption("Registrera resultat. Domare kan justeras direkt i samma tabell.")
    _result_progress = one_row(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS played
           FROM matches WHERE tournament_id=?""",
        (tid,),
    )
    _rp_total = int(_result_progress["total"] or 0)
    _rp_played = int(_result_progress["played"] or 0)
    _rp_pct = int(round((_rp_played / _rp_total) * 100)) if _rp_total else 0
    st.markdown(
        f"<div class='cn-progress-hero'><div><span>Resultatstatus</span><strong>{_rp_played}/{_rp_total}</strong></div>"
        f"<div class='cn-progress-track'><i style='width:{_rp_pct}%'></i></div></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "✓ Publika resultat uppdateras automatiskt."
        if tournament["is_published"]
        else "Cupen är i utkast – resultaten sparas nu och blir publika när cupen publiceras."
    )
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    st.caption("Registrera resultat match för match eller använd massinmatning när det passar.")
    if "bulk_result_message" in st.session_state:
        st.success(st.session_state.pop("bulk_result_message"), icon="✅")
    if "bulk_result_conflict_message" in st.session_state:
        st.warning(st.session_state.pop("bulk_result_conflict_message"))
    matches = all_rows("SELECT * FROM matches WHERE tournament_id=? ORDER BY CASE stage WHEN 'Gruppspel' THEN 0 ELSE 1 END, group_id, bracket_id, round_no, match_no", (tid,))
    if not matches:
        render_empty_state(
            "Inga matcher ännu",
            "Skapa eller generera schemat först. Därefter kan resultat registreras här.",
            symbol="—",
        )
    else:
        with st.expander("Visa hela matchschemat", expanded=False):
            all_match_rows = []
            for m in sorted(
                matches,
                key=lambda row: (
                    row["scheduled_start"] is None,
                    row["scheduled_start"] or "9999-12-31T23:59",
                    row["pitch_number"] or 999,
                    row["id"],
                ),
            ):
                schedule_text, referee_name = match_meta(m)
                all_match_rows.append({
                    "Match": schedule_text.split(" · ", 1)[0] if m["scheduled_start"] else "Ej schemalagd",
                    "Fas": m["stage"],
                    "Tid/plan": schedule_text.replace(schedule_text.split(" · ", 1)[0] + " · ", "", 1) if m["scheduled_start"] else "Ej schemalagd",
                    "Hemmalag": source_label(m["home_source"]),
                    "Bortalag": source_label(m["away_source"]),
                    "Domare": referee_name,
                })
            render_centered_table(pd.DataFrame(all_match_rows))
            st.caption(
                "Slutspelsmatcherna visas även innan lagen är klara. Exempel: Vinnaren i Grupp A eller Vinnare match 17."
            )

        playable_matches = [m for m in matches if resolve_source(m["home_source"]) and resolve_source(m["away_source"])]
        unresolved_count = len(matches) - len(playable_matches)
        if unresolved_count:
            with st.expander(f"Kommande slutspelsmatcher · {unresolved_count} väntar på lag", expanded=False):
                st.caption("Dessa matcher blir möjliga att resultatregistrera automatiskt när föregående matcher eller grupper är avgjorda.")
        if not playable_matches:
            st.info("Det finns ännu inga matcher med två klara lag.")
        else:
            referee_names = {r["id"]: r["name"] for r in refs}
            referee_ids_by_name = {r["name"]: r["id"] for r in refs}
            referee_options = ["Ej tillsatt"] + [r["name"] for r in refs]
            all_result_teams = all_rows("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
            result_team_name_by_id = {row["id"]: row["name"] for row in all_result_teams}
            result_team_id_by_name = {row["name"]: row["id"] for row in all_result_teams}
            decision_options = ["–"] + [row["name"] for row in all_result_teams]
            result_rows = []
            for m in playable_matches:
                schedule_text, _ = match_meta(m)
                result_rows.append({
                    "match_id": m["id"],
                    "Match": schedule_text,
                    "Fas": m["stage"],
                    "Hemmalag": source_label(m["home_source"]),
                    "Hemmamål": m["home_score"],
                    "Bortamål": m["away_score"],
                    "Bortalag": source_label(m["away_source"]),
                    "Hemmastraffar": m["home_penalties"] if m["stage"] != "Gruppspel" else None,
                    "Bortastraffar": m["away_penalties"] if m["stage"] != "Gruppspel" else None,
                    "Avgörande vinnare": result_team_name_by_id.get(m["decided_winner_id"], "–") if m["stage"] != "Gruppspel" else "–",
                    "Domare": referee_names.get(m["referee_id"], "Ej tillsatt"),
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
            if any(m["stage"] != "Gruppspel" for m in playable_matches):
                with st.expander("Regler vid oavgjort i slutspel", expanded=False):
                    if tournament["playoff_tie_rule"] == "Lottning":
                        st.caption("Välj vinnaren i kolumnen Avgörande vinnare enligt tävlingsregeln Lottning.")
                    elif tournament["playoff_tie_rule"] == "Förlängning + straffar":
                        st.caption(f"Vid oavgjort spelas {tournament['extra_time_minutes']} min förlängning och därefter straffar. Registrera straffresultatet vid fortsatt oavgjort.")
                    else:
                        st.caption("Vid oavgjort avgörs slutspelsmatchen med straffar direkt. Registrera straffresultatet.")
            # Resultat sparas automatiskt så snart en komplett ändring finns.
            # Vi jämför editorn mot aktuell databasdata och skriver bara ändrade rader.
            original_match_by_id = {int(match_row["id"]): match_row for match_row in playable_matches}
            auto_updates = []
            auto_messages = []
            auto_errors = []

            for _, row in edited_results.iterrows():
                match_id = int(row["match_id"])
                original_match = original_match_by_id[match_id]

                home_score = None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"])
                away_score = None if pd.isna(row["Bortamål"]) else int(row["Bortamål"])
                home_penalties = None if pd.isna(row["Hemmastraffar"]) else int(row["Hemmastraffar"])
                away_penalties = None if pd.isna(row["Bortastraffar"]) else int(row["Bortastraffar"])
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

                # Ett resultat ska aldrig sparas halvt.
                if (home_score is None) != (away_score is None):
                    auto_messages.append(
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

                    if tournament["playoff_tie_rule"] == "Lottning":
                        selected_winner_id = result_team_id_by_name.get(row["Avgörande vinnare"])
                        home_penalties = None
                        away_penalties = None
                        if selected_winner_id in (home_team_id, away_team_id):
                            decided_winner_id = selected_winner_id
                        else:
                            auto_messages.append(
                                f"{row['Hemmalag']}–{row['Bortalag']}: resultatet sparas, men välj vinnare av lottningen för att avgöra matchen."
                            )
                    else:
                        # Oavgjort resultat får sparas direkt. Straffarna kan fyllas i efteråt.
                        if home_penalties is not None or away_penalties is not None:
                            if (
                                home_penalties is None
                                or away_penalties is None
                                or home_penalties == away_penalties
                            ):
                                auto_errors.append(
                                    f"{row['Hemmalag']}–{row['Bortalag']}: fyll i ett komplett och avgörande straffresultat."
                                )
                                continue
                        else:
                            auto_messages.append(
                                f"{row['Hemmalag']}–{row['Bortalag']}: det oavgjorda resultatet sparas. Ange straffresultat för att avgöra matchen."
                            )
                else:
                    home_penalties = None
                    away_penalties = None

                auto_updates.append(
                    {
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
                    }
                )

            for message in auto_errors:
                st.error(message)
            for message in auto_messages:
                st.info(message)

            if auto_updates:
                _saved_updates = []
                _conflicted_updates = []
                with db() as con:
                    for update in auto_updates:
                        saved = update_match_result_if_unchanged(
                            con,
                            update["match_id"],
                            update["expected"],
                            home_score=update["home_score"],
                            away_score=update["away_score"],
                            home_penalties=update["home_penalties"],
                            away_penalties=update["away_penalties"],
                            decided_winner_id=update["decided_winner_id"],
                            referee_id=update["referee_id"],
                        )
                        (_saved_updates if saved else _conflicted_updates).append(update)
                    if tournament["is_published"] and _saved_updates:
                        con.executemany(
                            "UPDATE matches SET schedule_published=1 WHERE id=? AND scheduled_start IS NOT NULL",
                            [(int(update["match_id"]),) for update in _saved_updates],
                        )
                    con.commit()
                _clear_render_query_cache()
                if _conflicted_updates:
                    st.session_state["bulk_result_conflict_message"] = (
                        f"{len(_conflicted_updates)} match(er) hade ändrats av en annan användare och skrevs inte över. "
                        "CupNavi har laddat om de senaste värdena."
                    )
                for update in _saved_updates:
                    home_score = update["home_score"]
                    away_score = update["away_score"]
                    home_penalties = update["home_penalties"]
                    away_penalties = update["away_penalties"]
                    changed_match_id = update["match_id"]
                    if home_score is None or away_score is None:
                        continue
                    changed_match = original_match_by_id[changed_match_id]
                    description = f"{source_label(changed_match['home_source'])}–{source_label(changed_match['away_source'])} {home_score}–{away_score}"
                    if home_penalties is not None and away_penalties is not None:
                        description += f" ({home_penalties}–{away_penalties} str.)"
                    add_feed_item(tid, f"Slut: {description}", category="Resultat", related_match_id=changed_match_id)
                    for team_id in _match_team_ids(changed_match):
                        add_team_notification(tid, team_id, "Nytt resultat", description,
                                              event_key=f"result:{changed_match_id}:{home_score}:{away_score}:{home_penalties}:{away_penalties}")

                st.session_state["_validation_dirty"] = True
                st.session_state["bulk_result_message"] = (
                    "✓ Sparat automatiskt"
                    if not _conflicted_updates
                    else "✓ Övriga resultat sparades. Konflikter lämnades orörda."
                )
                st.rerun()

            st.caption("✓ Ändringar sparas automatiskt – ingen Spara-knapp behövs.")


if admin_page == "Matchhändelser":
    st.header("Matchhändelser")
    st.caption("Välj en spelad match och registrera spelarnas händelser. Ändringar sparas automatiskt.")
    played_matches = all_rows("SELECT * FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL ORDER BY id DESC", (tid,))
    playable_matches = [m for m in played_matches if resolve_source(m["home_source"]) and resolve_source(m["away_source"])]
    if not playable_matches:
        render_empty_state(
            "Inga spelade matcher ännu",
            "Registrera ett matchresultat först. Därefter kan mål, assist och kort läggas till.",
            symbol="—",
        )
    else:
        stat_match_id = st.selectbox(
            "Välj match",
            [m["id"] for m in playable_matches],
            format_func=lambda x: match_result_label(next(m for m in playable_matches if m["id"] == x)),
        )
        stat_match = next(m for m in playable_matches if m["id"] == stat_match_id)
        home_team_id = resolve_source(stat_match["home_source"])
        away_team_id = resolve_source(stat_match["away_source"])
        st.caption("Fyll bara i de händelser som inträffade.")
        for selected_team_id in [home_team_id, away_team_id]:
            selected_team = team(selected_team_id)
            players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (selected_team_id,))
            st.markdown(f"#### {selected_team['name']}")
            if not players:
                st.warning("Laget saknar registrerade spelare.")
                continue
            existing = {
                r["player_id"]: r
                for r in all_rows("SELECT * FROM player_match_stats WHERE match_id=? AND player_id IN (SELECT id FROM players WHERE team_id=?)", (stat_match_id, selected_team_id))
            }
            data = pd.DataFrame([
                {
                    "player_id": p["id"],
                    "Nr": p["player_number"],
                    "Spelare": p["name"],
                    "Mål": existing[p["id"]]["goals"] if p["id"] in existing else 0,
                    "Assist": existing[p["id"]]["assists"] if p["id"] in existing else 0,
                    "Varningar": existing[p["id"]]["yellow_cards"] if p["id"] in existing else 0,
                    "Utvisningar": existing[p["id"]]["red_cards"] if p["id"] in existing else 0,
                }
                for p in players
            ])
            admin_event_columns = ["Nr", "Spelare", "Mål"]
            if bool(_row_value(tournament, "enable_assist_leaderboard", 1)):
                admin_event_columns.append("Assist")
            if bool(_row_value(tournament, "enable_card_statistics", 1)):
                admin_event_columns.extend(["Varningar", "Utvisningar"])
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

            # Händelser sparas automatiskt när ändringen är giltig.
            # Endast faktiskt ändrade spelarrader skrivs till databasen.
            changed_event_rows = prepare_changed_event_rows(
                (row for _, row in edited.iterrows()),
                existing,
                match_id=stat_match_id,
                is_na=pd.isna,
            )

            if changed_event_rows and event_validation["ok"]:
                saved_event_rows = []
                conflicted_event_rows = []
                with db() as con:
                    for event_update in changed_event_rows:
                        saved = update_player_match_stats_if_unchanged(
                            con,
                            event_update["match_id"],
                            event_update["player_id"],
                            event_update["expected"],
                            goals=event_update["goals"],
                            assists=event_update["assists"],
                            yellow_cards=event_update["yellow_cards"],
                            red_cards=event_update["red_cards"],
                        )
                        (saved_event_rows if saved else conflicted_event_rows).append(event_update)
                    con.commit()

                if saved_event_rows:
                    st.session_state[autosave_message_key] = "✓ Sparat automatiskt"
                if conflicted_event_rows:
                    st.session_state[
                        f"event_autosave_conflict_{stat_match_id}_{selected_team_id}"
                    ] = (
                        f"{len(conflicted_event_rows)} spelarrad(er) hade ändrats av en annan "
                        "användare och skrevs inte över. Senaste värden laddas om."
                    )
                st.rerun()

            if changed_event_rows and not event_validation["ok"]:
                st.caption("Ändringen sparas automatiskt så snart mål/assist stämmer med matchresultatet.")
            else:
                st.caption("✓ Händelser sparas automatiskt – ingen Spara-knapp behövs.")

            registered_goals = int(edited["Mål"].sum())
            expected_goals = stat_match["home_score"] if selected_team_id == home_team_id else stat_match["away_score"]
            if registered_goals != expected_goals and not event_validation["errors"]:
                st.caption(f"ℹ {expected_goals - registered_goals:+d} mål saknar spelarkoppling, exempelvis självmål.")


if admin_page == "Besöksstatistik":
    st.header(tr("Besöksstatistik"))
    st.caption("Besök i den publika turneringsvyn. Inga IP-adresser lagras.")

    period_label = st.selectbox(
        tr("Period"),
        [tr("Senaste 7 dagarna"), tr("Senaste 30 dagarna"), tr("Senaste 90 dagarna"), tr("All tid")],
        index=1,
        key=f"visitor_period_{tid}",
    )
    period_days = {
        tr("Senaste 7 dagarna"): 7,
        tr("Senaste 30 dagarna"): 30,
        tr("Senaste 90 dagarna"): 90,
        tr("All tid"): None,
    }[period_label]

    analytics_rows = all_rows(
        """SELECT first_seen,last_seen,view_count,device_type,browser,source
           FROM visitor_sessions
           WHERE tournament_id=?
           ORDER BY first_seen""",
        (tid,),
    )

    now_stats = datetime.now()
    parsed_rows = []
    for row in analytics_rows:
        try:
            first_seen = datetime.fromisoformat(row["first_seen"])
            last_seen = datetime.fromisoformat(row["last_seen"])
        except Exception:
            continue
        if period_days is not None and first_seen < now_stats - timedelta(days=period_days):
            continue
        parsed_rows.append({
            "first_seen": first_seen,
            "last_seen": last_seen,
            "view_count": int(row["view_count"] or 0),
            "device_type": row["device_type"] or "Övrig",
            "browser": row["browser"] or "Övrig",
            "source": row["source"] or "Direkt / okänd",
        })

    if not parsed_rows:
        st.info("Det finns ännu ingen besöksdata för den valda perioden.")
    else:
        unique_sessions = len(parsed_rows)
        total_views = sum(row["view_count"] for row in parsed_rows)
        today = now_stats.date()
        today_rows = [row for row in parsed_rows if row["first_seen"].date() == today]
        today_sessions = len(today_rows)
        today_views = sum(row["view_count"] for row in today_rows)
        active_30m = sum(
            1 for row in parsed_rows
            if row["last_seen"] >= now_stats - timedelta(minutes=30)
        )
        avg_views = total_views / unique_sessions if unique_sessions else 0

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Unika sessioner", unique_sessions)
        m2.metric("Sidvisningar", total_views)
        m3.metric("Besök idag", today_sessions)
        m4.metric("Sidvisningar idag", today_views)
        m5.metric("Aktiva senaste 30 min", active_30m)
        st.caption(f"Genomsnitt: {avg_views:.1f} sidvisningar per besökssession.")

        with st.expander("Utveckling över tid", expanded=False):
            # Daily development.
            daily = {}
            for row in parsed_rows:
                day = row["first_seen"].date().isoformat()
                daily.setdefault(day, {"Sessioner": 0, "Sidvisningar": 0})
                daily[day]["Sessioner"] += 1
                daily[day]["Sidvisningar"] += row["view_count"]

            daily_df = pd.DataFrame([
                {"Datum": day, **values}
                for day, values in sorted(daily.items())
            ])
            if not daily_df.empty:
                chart_df = daily_df.set_index("Datum")[["Sessioner", "Sidvisningar"]]
                st.line_chart(chart_df, use_container_width=True)
                render_centered_table(daily_df)

        with st.expander("Enheter, webbläsare & trafikkällor", expanded=False):
            breakdown_col1, breakdown_col2, breakdown_col3 = st.columns(3)

            def _breakdown_dataframe(key, label):
                counts = {}
                views = {}
                for row in parsed_rows:
                    value = row[key] or "Övrig"
                    counts[value] = counts.get(value, 0) + 1
                    views[value] = views.get(value, 0) + row["view_count"]
                return pd.DataFrame([
                    {
                        label: value,
                        "Sessioner": counts[value],
                        "Sidvisningar": views[value],
                        "Andel": f"{counts[value] / unique_sessions * 100:.0f} %",
                    }
                    for value in sorted(counts, key=lambda item: (-counts[item], item))
                ])

            with breakdown_col1:
                st.markdown("#### Enheter")
                device_df = _breakdown_dataframe("device_type", "Enhet")
                st.bar_chart(device_df.set_index("Enhet")["Sessioner"], use_container_width=True)
                render_centered_table(device_df)

            with breakdown_col2:
                st.markdown("#### Webbläsare")
                browser_df = _breakdown_dataframe("browser", "Webbläsare")
                st.bar_chart(browser_df.set_index("Webbläsare")["Sessioner"], use_container_width=True)
                render_centered_table(browser_df)

            with breakdown_col3:
                st.markdown("#### Trafikkälla")
                source_df = _breakdown_dataframe("source", "Källa")
                st.bar_chart(source_df.set_index("Källa")["Sessioner"], use_container_width=True)
                render_centered_table(source_df)

        with st.expander("Senaste besök & integritet", expanded=False):
            recent_rows = sorted(parsed_rows, key=lambda row: row["last_seen"], reverse=True)[:50]
            recent_df = pd.DataFrame([
                {
                    "Första besök": row["first_seen"].strftime("%Y-%m-%d %H:%M"),
                    "Senast aktiv": row["last_seen"].strftime("%Y-%m-%d %H:%M"),
                    "Sidvisningar": row["view_count"],
                    "Enhet": row["device_type"],
                    "Webbläsare": row["browser"],
                    "Källa": row["source"],
                }
                for row in recent_rows
            ])
            render_centered_table(recent_df)

            st.info(
                "För att skydda besökarnas integritet lagras ingen IP-adress. "
                "En besökssession identifieras med en slumpmässig sessionsnyckel som endast används för statistik."
            )


if admin_page == "Sponsorer":
    partner_section = st.segmented_control(
        "Partners & erbjudanden",
        ["Sponsorer", "Erbjudanden"],
        default="Sponsorer",
        key=f"partner_offer_switch_{tid}_sponsors",
    )
    if partner_section == "Erbjudanden":
        st.session_state[admin_page_key] = "Erbjudanden"
        st.rerun()
    st.header("Sponsorer")
    st.caption("Lägg till partners som ska kunna visas i den publika cupvyn.")

    with st.form(f"new_sponsor_{tid}", clear_on_submit=True):
        sponsor_name = st.text_input("Namn *", placeholder="Exempel: Lokala Banken")
        sponsor_active = st.checkbox("Visa publikt direkt", value=True)
        with st.expander("Fler sponsoruppgifter", expanded=False):
            sponsor_level = st.selectbox("Nivå", ["", "Huvudsponsor", "Guldsponsor", "Silversponsor", "Partner"])
            sponsor_website = st.text_input("Webbplats", placeholder="example.se", help="Du kan skriva example.se eller en fullständig https://-adress.")
            sponsor_order = st.number_input("Visningsordning", min_value=0, max_value=999, value=0, step=1)
            sponsor_logo = st.file_uploader(
                "Logotyp (PNG/JPG/WEBP, max 1,5 MB)",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"new_sponsor_logo_{tid}",
            )
            sponsor_description = st.text_area("Kort beskrivning", max_chars=1000)
        if st.form_submit_button("Lägg till sponsor", type="primary", use_container_width=True):
            if not sponsor_name.strip():
                st.error("Ange sponsorns namn.")
            else:
                try:
                    normalized_website = normalize_website_url(sponsor_website)
                    logo_uri = image_data_uri(sponsor_logo)
                    run(
                        """INSERT INTO sponsors(
                               tournament_id,name,level,description,website_url,
                               logo_data_uri,active,sort_order
                           ) VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            tid, sponsor_name.strip(), sponsor_level or None,
                            sponsor_description.strip() or None,
                            normalized_website, logo_uri,
                            1 if sponsor_active else 0, int(sponsor_order),
                        ),
                    )
                    st.success("✓ Sponsorn är sparad.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    sponsor_rows = all_rows(
        "SELECT * FROM sponsors WHERE tournament_id=? ORDER BY sort_order,id",
        (tid,),
    )
    st.caption(f"{len(sponsor_rows)} sponsorer registrerade" if sponsor_rows else "Inga sponsorer registrerade ännu")
    if not sponsor_rows:
        render_empty_state("Inga partners ännu", "Lägg till en sponsor eller partner när du vill visa dem publikt och på informationsskärmen.", "🤝")
    else:
        for sponsor in sponsor_rows:
            status = "Publicerad" if sponsor["active"] else "Dold"
            with st.expander(f"{'✓' if sponsor['active'] else '○'} {sponsor['name']} · {status}"):
                with st.form(f"edit_sponsor_{sponsor['id']}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_name = st.text_input("Namn", value=sponsor["name"], key=f"sponsor_name_{sponsor['id']}")
                        levels = ["", "Huvudsponsor", "Guldsponsor", "Silversponsor", "Partner"]
                        current_level = sponsor["level"] or ""
                        edit_level = st.selectbox(
                            "Nivå", levels,
                            index=levels.index(current_level) if current_level in levels else 0,
                            key=f"sponsor_level_{sponsor['id']}",
                        )
                        edit_website = st.text_input("Webbplats", value=sponsor["website_url"] or "", key=f"sponsor_web_{sponsor['id']}")
                    with ec2:
                        edit_order = st.number_input(
                            "Visningsordning", 0, 999, int(sponsor["sort_order"] or 0),
                            key=f"sponsor_order_{sponsor['id']}",
                        )
                        edit_active = st.checkbox(
                            "Visa publikt", value=bool(sponsor["active"]),
                            key=f"sponsor_active_{sponsor['id']}",
                        )
                        replacement_logo = st.file_uploader(
                            "Byt logotyp",
                            type=["png", "jpg", "jpeg", "webp"],
                            key=f"sponsor_logo_{sponsor['id']}",
                        )
                    edit_description = st.text_area(
                        "Kort beskrivning",
                        value=sponsor["description"] or "",
                        max_chars=1000,
                        key=f"sponsor_desc_{sponsor['id']}",
                    )
                    if st.form_submit_button("Spara sponsor", use_container_width=True):
                        if not edit_name.strip():
                            st.error("Namnet får inte vara tomt.")
                        else:
                            try:
                                normalized_website = normalize_website_url(edit_website)
                                edit_logo_uri = sponsor["logo_data_uri"]
                                if replacement_logo is not None:
                                    edit_logo_uri = image_data_uri(replacement_logo)
                                saved, save_reason = _admin_update_sponsor_if_unchanged(
                                    sponsor["id"],
                                    tid,
                                    _sponsor_snapshot(sponsor),
                                    name=edit_name.strip(),
                                    level=edit_level or None,
                                    description=edit_description.strip() or None,
                                    website_url=normalized_website,
                                    logo_data_uri=edit_logo_uri,
                                    active=edit_active,
                                    sort_order=int(edit_order),
                                )
                                if saved:
                                    st.success("✓ Sponsorn är uppdaterad.")
                                else:
                                    st.warning("Sponsorn ändrades av en annan administratör och dina äldre uppgifter skrevs inte över.")
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                if st.button("Ta bort sponsor", key=f"delete_sponsor_{sponsor['id']}"):
                    deleted, delete_reason = _admin_delete_sponsor_if_unchanged(
                        sponsor["id"],
                        tid,
                        _sponsor_snapshot(sponsor),
                    )
                    if not deleted:
                        st.warning("Sponsorn ändrades av en annan administratör och raderades därför inte.")
                    st.rerun()


if admin_page == "Funktionärer":
    st.header("Funktionärer")
    st.caption("Lägg till personer och roller. Kontaktuppgifter och arbetspass är valfria.")

    with st.form(f"new_functionary_{tid}", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        fn_name = fc1.text_input("Namn *")
        fn_role = fc2.selectbox(
            "Roll *",
            ["Sekretariat", "Planvärd", "Tävlingsledning", "Sjukvård", "Kiosk", "Speaker", "Övrigt"],
        )
        with st.expander("Fler funktionärsuppgifter", expanded=False):
            fn_pitch = st.number_input("Plan (0 = ingen särskild)", min_value=0, max_value=100, value=0, step=1)
            fn_phone = st.text_input("Telefon")
            fn_email = st.text_input("E-post")
            fn_public = st.checkbox("Visa kontaktuppgifterna publikt", value=False)
            fn_notes = st.text_area("Anteckning / uppdrag", max_chars=1000)
        if st.form_submit_button("Lägg till funktionär", type="primary", use_container_width=True):
            if not fn_name.strip():
                st.error("Ange ett namn.")
            else:
                run(
                    """INSERT INTO functionaries(
                           tournament_id,name,role,phone,email,pitch_number,notes,public_contact,active
                       ) VALUES(?,?,?,?,?,?,?,?,1)""",
                    (
                        tid, fn_name.strip(), fn_role, fn_phone.strip() or None,
                        fn_email.strip() or None, int(fn_pitch) or None,
                        fn_notes.strip() or None, 1 if fn_public else 0,
                    ),
                )
                st.success("✓ Funktionären är sparad.")
                st.rerun()

    fn_rows = all_rows(
        "SELECT * FROM functionaries WHERE tournament_id=? ORDER BY role,name",
        (tid,),
    )
    if fn_rows:
        st.caption(f"{len(fn_rows)} funktionärer registrerade")
        with st.expander("Visa funktionärslista", expanded=False):
            render_centered_table(pd.DataFrame([
                {
                    "Namn": row["name"],
                    "Roll": row["role"],
                    "Plan": row["pitch_number"] or "–",
                    "Telefon": row["phone"] or "",
                    "E-post": row["email"] or "",
                    "Publik kontakt": "Ja" if row["public_contact"] else "Nej",
                }
                for row in fn_rows
            ]))
        for row in fn_rows:
            with st.expander(f"{row['role']} · {row['name']}"):
                with st.form(f"edit_functionary_{row['id']}"):
                    e1, e2 = st.columns(2)
                    ename = e1.text_input("Namn", value=row["name"], key=f"fn_name_{row['id']}")
                    roles = ["Sekretariat", "Planvärd", "Tävlingsledning", "Sjukvård", "Kiosk", "Speaker", "Övrigt"]
                    erole = e1.selectbox(
                        "Roll", roles,
                        index=roles.index(row["role"]) if row["role"] in roles else len(roles)-1,
                        key=f"fn_role_{row['id']}",
                    )
                    epitch = e1.number_input(
                        "Plan", min_value=0, max_value=100,
                        value=int(row["pitch_number"] or 0),
                        key=f"fn_pitch_{row['id']}",
                    )
                    ephone = e2.text_input("Telefon", value=row["phone"] or "", key=f"fn_phone_{row['id']}")
                    eemail = e2.text_input("E-post", value=row["email"] or "", key=f"fn_email_{row['id']}")
                    epublic = e2.checkbox(
                        "Visa publikt", value=bool(row["public_contact"]),
                        key=f"fn_public_{row['id']}",
                    )
                    enotes = st.text_area("Anteckning / uppdrag", value=row["notes"] or "", key=f"fn_notes_{row['id']}")
                    if st.form_submit_button("Spara funktionär", use_container_width=True):
                        if not ename.strip():
                            st.error("Namnet får inte vara tomt.")
                        else:
                            saved, save_reason = _admin_update_functionary_if_unchanged(
                                row["id"],
                                tid,
                                _functionary_snapshot(row),
                                name=ename.strip(),
                                role=erole,
                                phone=ephone.strip() or None,
                                email=eemail.strip() or None,
                                pitch_number=int(epitch) or None,
                                notes=enotes.strip() or None,
                                public_contact=epublic,
                            )
                            if save_reason == "invalid_email":
                                st.error("Ange en giltig e-postadress eller lämna fältet tomt.")
                            elif not saved:
                                st.warning("Funktionären ändrades av en annan administratör och dina äldre uppgifter skrevs inte över.")
                            else:
                                st.rerun()
                if st.button("Ta bort funktionär", key=f"delete_fn_{row['id']}"):
                    deleted, delete_reason = _admin_delete_functionary_if_unchanged(
                        row["id"],
                        tid,
                        _functionary_snapshot(row),
                    )
                    if not deleted:
                        st.warning("Funktionären ändrades av en annan administratör och raderades därför inte.")
                    st.rerun()
    else:
        render_empty_state("Inga funktionärer ännu", "Lägg till funktionärer för kiosk, sekretariat, planvärd eller andra uppdrag.", "🙋")

    with st.expander("Funktionärsschema & arbetspass", expanded=False):
        if not fn_rows:
            st.caption("Lägg först till minst en funktionär för att skapa arbetspass.")
        else:
            fn_by_id = {row["id"]: row for row in fn_rows}
            with st.form(f"new_functionary_shift_{tid}", clear_on_submit=True):
                sc1, sc2 = st.columns(2)
                shift_functionary = sc1.selectbox("Funktionär", list(fn_by_id), format_func=lambda x: f"{fn_by_id[x]['name']} · {fn_by_id[x]['role']}")
                shift_date = sc2.date_input("Datum", value=saved_start if 'saved_start' in locals() else datetime.now().date())
                st.caption(f"📅 {date_with_weekday(shift_date)}")
                st1, st2 = st.columns(2)
                shift_start_time = st1.time_input("Start", value=datetime.strptime("08:00", "%H:%M").time())
                shift_end_time = st2.time_input("Slut", value=datetime.strptime("12:00", "%H:%M").time())
                shift_assignment = st.text_input("Uppdrag", placeholder="Exempel: Planvärd, sekretariat eller kiosk")
                shift_location = st.text_input("Plats", placeholder="Exempel: Plan 2 eller huvudentrén")
                if st.form_submit_button("Lägg till arbetspass", type="primary", use_container_width=True):
                    start_dt = datetime.combine(shift_date, shift_start_time)
                    end_dt = datetime.combine(shift_date, shift_end_time)
                    if end_dt <= start_dt:
                        st.error("Sluttiden måste ligga efter starttiden.")
                    else:
                        run("INSERT INTO functionary_shifts(tournament_id,functionary_id,shift_start,shift_end,assignment,location) VALUES(?,?,?,?,?,?)", (tid, shift_functionary, start_dt.isoformat(timespec='minutes'), end_dt.isoformat(timespec='minutes'), shift_assignment.strip() or None, shift_location.strip() or None))
                        st.rerun()
            shift_rows = all_rows("SELECT fs.*, f.name, f.role FROM functionary_shifts fs JOIN functionaries f ON f.id=fs.functionary_id WHERE fs.tournament_id=? ORDER BY fs.shift_start,f.name", (tid,))
            if shift_rows:
                render_centered_table(pd.DataFrame([{
                    "Datum": date_with_weekday(datetime.fromisoformat(r["shift_start"]).date()),
                    "Tid": f"{datetime.fromisoformat(r['shift_start']).strftime('%H:%M')}–{datetime.fromisoformat(r['shift_end']).strftime('%H:%M')}",
                    "Funktionär": r["name"], "Roll": r["role"], "Uppdrag": r["assignment"] or "", "Plats": r["location"] or ""
                } for r in shift_rows]))
                shift_delete = st.selectbox("Ta bort arbetspass", [0] + [r["id"] for r in shift_rows], format_func=lambda x: "Välj arbetspass" if x == 0 else next(f"{r['name']} · {r['shift_start'].replace('T',' ')}" for r in shift_rows if r['id']==x), key=f"delete_shift_select_{tid}")
                if st.button("Ta bort valt arbetspass", disabled=not shift_delete, key=f"delete_shift_{tid}"):
                    selected_shift = next((r for r in shift_rows if int(r["id"]) == int(shift_delete)), None)
                    deleted, delete_reason = (
                        _admin_delete_functionary_shift_if_unchanged(
                            shift_delete,
                            tid,
                            _functionary_shift_snapshot(selected_shift),
                        )
                        if selected_shift is not None
                        else (False, "conflict")
                    )
                    if not deleted:
                        st.warning("Arbetspasset ändrades av en annan administratör och raderades därför inte.")
                    st.rerun()


if admin_page == "Erbjudanden":
    partner_section = st.segmented_control(
        "Partners & erbjudanden",
        ["Sponsorer", "Erbjudanden"],
        default="Erbjudanden",
        key=f"partner_offer_switch_{tid}_offers",
    )
    if partner_section == "Sponsorer":
        st.session_state[admin_page_key] = "Sponsorer"
        st.rerun()
    st.header("Erbjudanden")
    st.caption("Lägg till erbjudanden som ska kunna visas för deltagare och besökare.")

    with st.form(f"new_offer_{tid}", clear_on_submit=True):
        offer_title = st.text_input("Rubrik *", placeholder="Exempel: 15 % på hela menyn")
        offer_business = st.text_input("Företag / restaurang", placeholder="Exempel: Restaurang Hörnet")
        offer_active = st.checkbox("Visa publikt direkt", value=True)
        with st.expander("Fler erbjudandeuppgifter", expanded=False):
            offer_code = st.text_input("Rabattkod", placeholder="Exempel: CUPNAVI15")
            offer_valid = st.text_input("Gäller t.o.m.", placeholder="Exempel: 2026-08-23")
            offer_url = st.text_input("Länk till erbjudandet", placeholder="https://...")
            offer_order = st.number_input("Visningsordning", min_value=0, max_value=999, value=0, step=1)
            offer_description = st.text_area(
                "Beskrivning / villkor",
                placeholder="Exempel: Gäller för cupdeltagare vid uppvisande av deltagarband.",
                max_chars=1500,
            )
        if st.form_submit_button("Lägg till erbjudande", type="primary", use_container_width=True):
            if not offer_title.strip():
                st.error("Ange en rubrik för erbjudandet.")
            elif offer_url.strip() and not re.match(r"^https?://", offer_url.strip(), re.I):
                st.error("Länken måste börja med http:// eller https://.")
            else:
                run(
                    """INSERT INTO offers(
                           tournament_id,title,business_name,description,discount_code,
                           valid_until,url,active,sort_order
                       ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        tid,
                        offer_title.strip(),
                        offer_business.strip() or None,
                        offer_description.strip() or None,
                        offer_code.strip() or None,
                        offer_valid.strip() or None,
                        offer_url.strip() or None,
                        1 if offer_active else 0,
                        int(offer_order),
                    ),
                )
                st.success("✓ Erbjudandet är sparat.")
                st.rerun()

    admin_offers = all_rows(
        "SELECT * FROM offers WHERE tournament_id=? ORDER BY sort_order,id",
        (tid,),
    )
    st.caption(f"{len(admin_offers)} erbjudanden registrerade" if admin_offers else "Inga erbjudanden registrerade ännu")
    if not admin_offers:
        render_empty_state(
            "Inga erbjudanden ännu",
            "Skapa ett erbjudande när det finns något relevant att visa för besökarna.",
            symbol="—",
        )
    else:
        for offer in admin_offers:
            status = "Publicerat" if offer["active"] else "Dolt"
            with st.expander(f"{'✓' if offer['active'] else '○'} {offer['title']} · {status}"):
                with st.form(f"edit_offer_{offer['id']}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_title = st.text_input("Rubrik", value=offer["title"], key=f"offer_title_{offer['id']}")
                        edit_business = st.text_input("Företag / restaurang", value=offer["business_name"] or "", key=f"offer_business_{offer['id']}")
                        edit_code = st.text_input("Rabattkod", value=offer["discount_code"] or "", key=f"offer_code_{offer['id']}")
                    with ec2:
                        edit_valid = st.text_input("Gäller t.o.m.", value=offer["valid_until"] or "", key=f"offer_valid_{offer['id']}")
                        edit_url = st.text_input("Länk", value=offer["url"] or "", key=f"offer_url_{offer['id']}")
                        edit_order = st.number_input("Visningsordning", 0, 999, int(offer["sort_order"] or 0), key=f"offer_order_{offer['id']}")
                    edit_description = st.text_area("Beskrivning / villkor", value=offer["description"] or "", max_chars=1500, key=f"offer_desc_{offer['id']}")
                    edit_active = st.checkbox("Visa i turneringsvyn", value=bool(offer["active"]), key=f"offer_active_{offer['id']}")
                    if st.form_submit_button("Spara ändringar", use_container_width=True):
                        if not edit_title.strip():
                            st.error("Rubriken får inte vara tom.")
                        elif edit_url.strip() and not re.match(r"^https?://", edit_url.strip(), re.I):
                            st.error("Länken måste börja med http:// eller https://.")
                        else:
                            saved, save_reason = _admin_update_offer_if_unchanged(
                                offer["id"],
                                tid,
                                _offer_snapshot(offer),
                                title=edit_title.strip(),
                                business_name=edit_business.strip() or None,
                                description=edit_description.strip() or None,
                                discount_code=edit_code.strip() or None,
                                valid_until=edit_valid.strip() or None,
                                url=edit_url.strip() or None,
                                active=edit_active,
                                sort_order=int(edit_order),
                            )
                            if saved:
                                st.success("✓ Ändringarna är sparade.")
                            else:
                                st.warning("Erbjudandet ändrades av en annan administratör och dina äldre uppgifter skrevs inte över.")
                            st.rerun()

                if st.button("Ta bort erbjudande", key=f"delete_offer_{offer['id']}", type="secondary"):
                    st.session_state[f"confirm_delete_offer_{offer['id']}"] = True
                    st.rerun()
                if st.session_state.get(f"confirm_delete_offer_{offer['id']}"):
                    st.warning(f"Ta bort erbjudandet “{offer['title']}”?")
                    dc1, dc2 = st.columns(2)
                    if dc1.button("Ja, ta bort", key=f"confirm_offer_delete_{offer['id']}", type="primary"):
                        deleted, delete_reason = _admin_delete_offer_if_unchanged(
                            offer["id"],
                            tid,
                            _offer_snapshot(offer),
                        )
                        st.session_state.pop(f"confirm_delete_offer_{offer['id']}", None)
                        if not deleted:
                            st.warning("Erbjudandet ändrades av en annan administratör och raderades därför inte.")
                        st.rerun()
                    if dc2.button("Avbryt", key=f"cancel_offer_delete_{offer['id']}"):
                        st.session_state.pop(f"confirm_delete_offer_{offer['id']}", None)
                        st.rerun()


if admin_page == "Import":
    st.header("Import")
    st.caption("Importera många lag eller spelare från CSV/Excel. CupNavi försöker matcha kolumnerna automatiskt.")

    import_kind = st.segmented_control(
        "1. Vad vill du importera?",
        ["Lag", "Trupper"],
        default="Lag",
        key=f"import_kind_{tid}",
    )
    if not import_kind:
        import_kind = "Lag"

    with st.expander("📄 Importmallar och format", expanded=False):
        st.write(
            "Du kan använda **CSV eller Excel (.xlsx)**. Kolumnnamnen behöver inte vara exakt som i mallen – "
            "CupNavi försöker känna igen både svenska och engelska rubriker."
        )
        template_col1, template_col2 = st.columns(2)
        team_template = (
            "Lag,Grupp,Hemmafärg,Bortafärg,Resväg km,Senare första match,Första match tidigast,Kommentar\n"
            "Exempellaget,Grupp A,#111827,#FFFFFF,25,Ja,10:00,Reser samma morgon\n"
        ).encode("utf-8-sig")
        squad_template = (
            "Lag,Spelare,Tröjnummer,Födelseår,Position\n"
            "Exempellaget,Anna Andersson,10,2013,Mittfältare\n"
        ).encode("utf-8-sig")
        template_col1.download_button(
            "Ladda ner mall för lag",
            data=team_template,
            file_name="cupnavi_lag_importmall.csv",
            mime="text/csv",
            use_container_width=True,
        )
        template_col2.download_button(
            "Ladda ner mall för trupper",
            data=squad_template,
            file_name="cupnavi_trupp_importmall.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.subheader("Ladda upp fil")
    import_file = st.file_uploader(
        "Välj CSV eller XLSX",
        type=["csv", "xlsx"],
        key=f"import_file_{tid}_{import_kind}",
        help="CSV-filer kan använda komma, semikolon eller tab som avgränsare.",
    )

    import_df = None
    import_source_name = None

    if import_file is not None:
        try:
            raw_bytes = import_file.getvalue()
            if import_file.name.lower().endswith(".csv"):
                last_error = None
                for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                    try:
                        import_df = pd.read_csv(
                            io.BytesIO(raw_bytes),
                            sep=None,
                            engine="python",
                            encoding=encoding,
                        )
                        break
                    except Exception as exc:
                        last_error = exc
                if import_df is None:
                    raise last_error or ValueError("CSV-filen kunde inte läsas.")
                import_source_name = import_file.name
            else:
                excel_file = pd.ExcelFile(io.BytesIO(raw_bytes))
                sheet_name = st.selectbox(
                    "Välj blad i Excel-filen",
                    excel_file.sheet_names,
                    key=f"import_sheet_{tid}_{import_file.name}",
                )
                import_df = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=sheet_name)
                import_source_name = f"{import_file.name} · {sheet_name}"

            import_df = import_df.dropna(how="all").copy()
            import_df.columns = [str(col).strip() for col in import_df.columns]
            import_df = import_df.loc[:, ~import_df.columns.duplicated()].copy()

            if import_df.empty:
                st.error("Filen innehåller inga datarader.")
                import_df = None
            elif len(import_df) > 5000:
                st.error("Filen innehåller fler än 5 000 rader. Dela upp den i mindre filer.")
                import_df = None
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Fil", import_file.name)
                c2.metric("Rader", len(import_df))
                c3.metric("Kolumner", len(import_df.columns))
                st.caption(f"Läser: {import_source_name}")
        except Exception as exc:
            st.error(f"Filen kunde inte läsas: {exc}")

    if import_df is not None:
        fields = TEAM_FIELDS if import_kind == "Lag" else PLAYER_FIELDS
        auto_mapping = auto_map_columns(import_df.columns, fields)

        required_auto_missing = any(
            spec["required"] and not auto_mapping.get(field_name)
            for field_name, spec in fields.items()
        )
        mapping = {}
        with st.expander("Kolumnmappning", expanded=required_auto_missing):
            st.caption("CupNavi har förvalt kolumner automatiskt. Öppna bara om något behöver ändras.")
            available_options = ["— Använd inte —"] + list(import_df.columns)
            map_cols = st.columns(2)
            for field_index, (field_name, field_spec) in enumerate(fields.items()):
                default_column = auto_mapping.get(field_name)
                default_index = (
                    available_options.index(default_column)
                    if default_column in available_options
                    else 0
                )
                label = f"{field_name}{' *' if field_spec['required'] else ''}"
                selected = map_cols[field_index % 2].selectbox(
                    label,
                    available_options,
                    index=default_index,
                    key=f"import_map_{tid}_{import_kind}_{field_name}",
                )
                mapping[field_name] = None if selected == "— Använd inte —" else selected

        missing_required = [
            field for field, spec in fields.items()
            if spec["required"] and not mapping.get(field)
        ]

        if missing_required:
            st.error(
                "Matcha först de obligatoriska fälten: "
                + ", ".join(missing_required)
                + "."
            )
        else:
            existing_team_rows = all_rows(
                "SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name",
                (tid,),
            )
            existing_names = [row["name"] for row in existing_team_rows]

            if import_kind == "Lag":
                max_teams = int(tournament["expected_team_count"] or 0)
                remaining_slots = (
                    max(0, max_teams - len(existing_team_rows))
                    if max_teams > 0 else None
                )
                records, issues = build_team_import_plan(
                    import_df,
                    mapping,
                    existing_names,
                    max_new_teams=remaining_slots,
                )
            else:
                team_lookup = {
                    row["name"].strip().casefold(): row["id"]
                    for row in existing_team_rows
                }
                existing_player_rows = all_rows(
                    """SELECT p.team_id,p.name
                       FROM players p
                       JOIN teams t ON t.id=p.team_id
                       WHERE t.tournament_id=?""",
                    (tid,),
                )
                existing_players = [
                    (row["team_id"], row["name"])
                    for row in existing_player_rows
                ]
                records, issues = build_player_import_plan(
                    import_df,
                    mapping,
                    team_lookup,
                    existing_players,
                )

            error_count = sum(1 for issue in issues if issue["Nivå"] == "Fel")
            skipped_count = sum(1 for issue in issues if issue["Nivå"] == "Hoppa över")

            st.subheader("Granska import")
            s1, s2, s3 = st.columns(3)
            s1.metric("Redo att importera", len(records))
            s2.metric("Hoppar över", skipped_count)
            s3.metric("Fel att rätta", error_count)

            if import_kind == "Lag" and int(tournament["expected_team_count"] or 0) > 0:
                st.caption(
                    f"Turneringen är planerad för maximalt {int(tournament['expected_team_count'])} lag. "
                    f"Nu finns {len(existing_team_rows)} lag."
                )

            if issues:
                issue_df = pd.DataFrame(issues)
                if error_count:
                    st.error(
                        f"{error_count} fel blockerar importen. Rätta filen eller kolumnmappningen och ladda upp igen."
                    )
                elif skipped_count:
                    st.info(
                        f"{skipped_count} rader kommer att hoppas över eftersom de redan finns."
                    )
                with st.expander("Visa importdetaljer", expanded=bool(error_count)):
                    st.dataframe(
                        issue_df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(360, 42 + 35 * min(len(issue_df), 9)),
                    )
                    issue_csv = issue_df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        "Ladda ner felrapport",
                        data=issue_csv,
                        file_name=f"cupnavi_importkontroll_{import_kind.lower()}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

            if records:
                if import_kind == "Lag":
                    preview_df = pd.DataFrame([
                        {
                            "Lag": row["name"],
                            "Grupp": row["group"] or "–",
                            "Hemmafärg": row["home_color"],
                            "Bortafärg": row["away_color"],
                            "Resväg km": row["distance_km"],
                            "Senare första match": "Ja" if row["late_first_match"] else "Nej",
                            "Första match tidigast": row["earliest_first_time"] or "–",
                        }
                        for row in records[:100]
                    ])
                else:
                    preview_df = pd.DataFrame([
                        {
                            "Lag": row["team_name"],
                            "Spelare": row["player_name"],
                            "Tröjnummer": row["player_number"] if row["player_number"] is not None else "–",
                            "Födelseår": row["birth_year"] if row["birth_year"] is not None else "–",
                            "Position": row["position"] or "–",
                        }
                        for row in records[:100]
                    ])
                with st.expander(
                    f"Förhandsgranska {min(len(records), 100)} av {len(records)} rader",
                    expanded=error_count == 0,
                ):
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

            st.subheader("Importera")
            if error_count:
                st.warning("Importknappen låses tills alla blockerande fel är lösta.")
            elif not records:
                st.info("Det finns inga nya rader att importera.")
            else:
                create_groups = True
                if import_kind == "Lag":
                    create_groups = st.checkbox(
                        "Skapa grupper som finns i filen men inte redan i CupNavi",
                        value=True,
                        key=f"import_create_groups_{tid}",
                    )

                confirmed = st.checkbox(
                    f"Jag har granskat importen och vill lägga till {len(records)} "
                    + ("lag." if import_kind == "Lag" else "spelare."),
                    value=False,
                    key=f"import_confirm_{tid}_{import_kind}_{import_file.name}",
                )

                button_label = "Importera lagen" if import_kind == "Lag" else "Importera trupperna"
                if st.button(
                    button_label,
                    type="primary",
                    use_container_width=True,
                    disabled=not confirmed,
                    key=f"import_execute_{tid}_{import_kind}",
                ):
                    try:
                        con = db()
                        try:
                            if not CLOUD_DATABASE_ENABLED:
                                con.execute("BEGIN IMMEDIATE")

                            if import_kind == "Lag":
                                group_rows = _rows_from_cursor(
                                    con.execute(
                                        "SELECT id,name FROM groups WHERE tournament_id=?",
                                        (tid,),
                                    )
                                )
                                group_map = {
                                    row["name"].strip().casefold(): row["id"]
                                    for row in group_rows
                                }

                                # Re-check max within the write transaction.
                                max_row = _one_from_cursor(
                                    con.execute(
                                        "SELECT COALESCE(expected_team_count,0) AS max_teams FROM tournaments WHERE id=?",
                                        (tid,),
                                    )
                                )
                                count_row = _one_from_cursor(
                                    con.execute(
                                        "SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?",
                                        (tid,),
                                    )
                                )
                                max_teams = int(max_row["max_teams"] or 0)
                                current_count = int(count_row["n"] or 0)
                                if max_teams > 0 and current_count + len(records) > max_teams:
                                    raise TeamLimitReachedError(max_teams)

                                for record in records:
                                    group_id = None
                                    group_name = record["group"]
                                    if group_name:
                                        group_id = group_map.get(group_name.casefold())
                                        if group_id is None and create_groups:
                                            cur = con.execute(
                                                "INSERT INTO groups(tournament_id,name) VALUES(?,?)",
                                                (tid, group_name),
                                            )
                                            group_id = cur.lastrowid
                                            group_map[group_name.casefold()] = group_id

                                    con.execute(
                                        """INSERT INTO teams(
                                               tournament_id,name,group_id,primary_color,secondary_color,
                                               home_pattern,home_color_2,away_pattern,away_color_2,
                                               distance_km,late_first_match,earliest_first_time,travel_note,avoid_late_group_match
                                           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                        (
                                            tid, record["name"], group_id,
                                            record["home_color"], record["away_color"],
                                            "Helfärgad", "#FFFFFF", "Helfärgad", "#111827",
                                            record["distance_km"], int(record["late_first_match"]),
                                            record["earliest_first_time"], record["comment"] or None, int(record.get("avoid_late_group_match", False)),
                                        ),
                                    )
                                con.execute(
                                    "UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",
                                    (tid,),
                                )
                            else:
                                for record in records:
                                    con.execute(
                                        """INSERT INTO players(
                                               team_id,player_number,name,birth_year,position
                                           ) VALUES(?,?,?,?,?)""",
                                        (
                                            record["team_id"], record["player_number"],
                                            record["player_name"], record["birth_year"],
                                            record["position"] or None,
                                        ),
                                    )

                            con.commit()
                        except Exception:
                            con.rollback()
                            raise
                        finally:
                            con.close()

                        _clear_render_query_cache()
                        st.session_state["import_success_message"] = (
                            f"✓ Import klar: {len(records)} "
                            + ("lag lades till." if import_kind == "Lag" else "spelare lades till.")
                        )
                        st.rerun()
                    except TeamLimitReachedError as exc:
                        st.error(
                            f"Importen avbröts utan att något lades till eftersom maxantalet "
                            f"{exc.args[0]} lag skulle överskridas."
                        )
                    except Exception as exc:
                        st.error(
                            "Importen kunde inte genomföras. Inga rader ska ha sparats. "
                            f"Teknisk information: {exc}"
                        )

    if "import_success_message" in st.session_state:
        st.success(st.session_state.pop("import_success_message"))


if admin_page == "Cupverktyg":
    st.header("Cupverktyg")
    st.caption("Extra verktyg för cupdagen och felsituationer. Öppna det verktyg du behöver.")

    tool_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    tool_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    tool_groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    tool_matches = all_rows("SELECT * FROM matches WHERE tournament_id=? ORDER BY scheduled_start,pitch_number,id", (tid,))

    tool_tabs = st.tabs([
        "Status", "Flytta match", "Försening", "Slutspel", "Karta & QR", "Historik", "Summering"
    ])

    with tool_tabs[0]:
        schedule_findings = []
        if any(m["scheduled_start"] for m in tool_matches) and tool_rules:
            errors, warnings, _ = validate_schedule(tid, tournament, tool_rules)
            schedule_findings.extend({"severity": "error", "message": message} for message in errors)
            schedule_findings.extend({"severity": "warning", "message": message} for message in warnings)
        quality_score, quality_findings = tournament_quality_score(
            tournament, tool_teams, tool_groups, tool_matches, tool_rules, schedule_findings
        )
        q1, q2, q3 = st.columns(3)
        q1.metric("CupNavi-kvalitet", f"{quality_score}/100")
        q2.metric("Lag/deltagare", len(tool_teams))
        q3.metric("Matcher", len(tool_matches))
        st.progress(quality_score / 100)
        if quality_score >= 90:
            st.success("Cupen ser väl förberedd ut.")
        elif quality_score >= 70:
            st.warning("Cupen är användbar men det finns förbättringspunkter.")
        else:
            st.error("Cupen har flera saker som bör åtgärdas före eller under genomförandet.")
        if quality_findings:
            with st.expander(f"Förbättringspunkter · {len(quality_findings)}", expanded=False):
                for finding in quality_findings:
                    message = f"−{finding['deduction']} p · {finding['message']}"
                    (st.error if finding["severity"] == "error" else st.warning)(message)
        else:
            st.caption("✓ Inga kvalitetsavdrag hittades.")

    with tool_tabs[1]:
        st.subheader("🔎 Vad händer om jag flyttar en match?")
        scheduled_for_whatif = [m for m in tool_matches if m["scheduled_start"]]
        if not scheduled_for_whatif:
            st.info("Skapa ett schema först.")
        else:
            whatif_match_id = st.selectbox(
                "Match",
                [m["id"] for m in scheduled_for_whatif],
                format_func=lambda mid: match_result_label(next(m for m in scheduled_for_whatif if m["id"] == mid)),
                key=f"whatif_match_{tid}",
            )
            whatif_match = next(m for m in scheduled_for_whatif if m["id"] == whatif_match_id)
            current_start = datetime.fromisoformat(whatif_match["scheduled_start"])
            wi1, wi2, wi3 = st.columns(3)
            new_date = wi1.date_input("Nytt datum", value=current_start.date(), key=f"wi_date_{tid}")
            new_time = wi2.time_input("Ny tid", value=current_start.time().replace(second=0, microsecond=0), key=f"wi_time_{tid}")
            max_pitch = max([int(m["pitch_number"] or 0) for m in scheduled_for_whatif] + [int(tool_rules["pitch_count"] or 1)])
            new_pitch = wi3.number_input("Ny plan", 1, max(1, max_pitch), int(whatif_match["pitch_number"] or 1), key=f"wi_pitch_{tid}")
            proposed_start = datetime.combine(new_date, new_time)
            impact = analyze_schedule_change(
                tool_matches, whatif_match_id, proposed_start, int(new_pitch), tool_rules,
                resolve_team_id=lambda source: resolve_source(source),
            )
            if impact:
                for item in impact:
                    (st.error if item["severity"] == "error" else st.warning)(item["message"])
            else:
                st.success("Ingen plan-, domar- eller lagvilokrock hittades med de aktuella reglerna.")
            has_errors = any(item["severity"] == "error" for item in impact)
            allow_warning_move = st.checkbox("Jag har granskat eventuella varningar", value=not bool(impact), key=f"wi_accept_{tid}")
            if st.button(
                "Genomför schemaändringen",
                type="primary",
                use_container_width=True,
                key=f"wi_apply_{tid}",
                disabled=has_errors or not allow_warning_move,
            ):
                before = {"scheduled_start": whatif_match["scheduled_start"], "pitch_number": whatif_match["pitch_number"]}
                after = {"scheduled_start": proposed_start.isoformat(timespec="minutes"), "pitch_number": int(new_pitch)}
                run(
                    """UPDATE matches SET original_scheduled_start=COALESCE(original_scheduled_start,scheduled_start),scheduled_start=?,pitch_number=? WHERE id=?""",
                    (after["scheduled_start"], after["pitch_number"], whatif_match_id),
                )
                description = (
                    f"{source_label(whatif_match['home_source'])}–{source_label(whatif_match['away_source'])} "
                    f"flyttad till {swedish_datetime(after['scheduled_start'])}, Plan {after['pitch_number']}"
                )
                record_audit(tid, "schedule_move", "match", description, entity_id=whatif_match_id,
                             before=before, after=after, reversible=True)
                add_feed_item(tid, "Match flyttad", description, category="Schema", related_match_id=whatif_match_id)
                for team_id in _match_team_ids(whatif_match):
                    add_team_notification(tid, team_id, "Matchen har flyttats", description,
                                          event_key=f"move:{whatif_match_id}:{after['scheduled_start']}:{after['pitch_number']}")
                st.success("Ändringen är genomförd och berörda lag får en notis i Min cup.")
                st.rerun()

    with tool_tabs[2]:
        st.subheader("⏱️ Automatisk matchförsening")
        pitch_options = sorted({int(m["pitch_number"]) for m in tool_matches if m["pitch_number"] is not None})
        if not pitch_options:
            st.info("Det finns inga schemalagda planer ännu.")
        else:
            d1, d2 = st.columns(2)
            delay_pitch = d1.selectbox("Plan", pitch_options, format_func=lambda pno: f"Plan {pno}", key=f"delay_pitch_{tid}")
            delay_minutes = d2.number_input("Försening i minuter", 1, 180, 10, key=f"delay_minutes_{tid}")
            pitch_unplayed = [m for m in tool_matches if int(m["pitch_number"] or 0) == delay_pitch and m["home_score"] is None]
            if pitch_unplayed:
                start_options = [m["id"] for m in pitch_unplayed]
                from_match_id = st.selectbox(
                    "Flytta från och med match",
                    start_options,
                    format_func=lambda mid: match_result_label(next(m for m in pitch_unplayed if m["id"] == mid)),
                    key=f"delay_from_{tid}",
                )
                from_match = next(m for m in pitch_unplayed if m["id"] == from_match_id)
                delay_updates = planned_delay_updates(tool_matches, delay_pitch, int(delay_minutes), from_match["scheduled_start"])
                st.caption(f"{len(delay_updates)} ospelade matcher flyttas +{delay_minutes} minuter.")
                if delay_updates:
                    preview = []
                    by_id = {m["id"]: m for m in tool_matches}
                    for match_id, new_start in delay_updates[:12]:
                        old = by_id[match_id]
                        preview.append({
                            "Match": f"{source_label(old['home_source'])} – {source_label(old['away_source'])}",
                            "Från": swedish_datetime(old["scheduled_start"]),
                            "Till": swedish_datetime(new_start),
                        })
                    with st.expander("Förhandsvisa ändrade tider", expanded=False):
                        render_centered_table(pd.DataFrame(preview))
                    if st.button("Tillämpa förseningen", type="primary", use_container_width=True, key=f"delay_apply_{tid}"):
                        before_rows, after_rows = [], []
                        with db() as con:
                            for match_id, new_start in delay_updates:
                                old = by_id[match_id]
                                before_rows.append({"id": match_id, "scheduled_start": old["scheduled_start"]})
                                after_rows.append({"id": match_id, "scheduled_start": new_start})
                                con.execute(
                                    """UPDATE matches SET original_scheduled_start=COALESCE(original_scheduled_start,scheduled_start),scheduled_start=? WHERE id=?""",
                                    (new_start, match_id),
                                )
                            con.commit()
                        _clear_render_query_cache()
                        record_audit(tid, "delay_shift", "pitch", f"Plan {delay_pitch} flyttad +{delay_minutes} min",
                                     entity_id=delay_pitch, before=before_rows, after=after_rows, reversible=True)
                        detail = f"Plan {delay_pitch} ligger cirka {delay_minutes} minuter efter. {len(delay_updates)} matcher har fått nya tider."
                        add_feed_item(tid, f"Plan {delay_pitch} försenad", detail, category="Schema")
                        notified = set()
                        for match_id, new_start in delay_updates:
                            match_row = by_id[match_id]
                            for team_id in _match_team_ids(match_row):
                                key = (team_id, match_id)
                                if key in notified:
                                    continue
                                notified.add(key)
                                add_team_notification(
                                    tid, team_id, "Ny matchtid",
                                    f"{source_label(match_row['home_source'])}–{source_label(match_row['away_source'])}: {swedish_datetime(new_start)} · Plan {delay_pitch}",
                                    event_key=f"delay:{match_id}:{new_start}",
                                )
                        st.rerun()
            else:
                st.info("Det finns inga ospelade matcher på planen.")

    with tool_tabs[3]:
        st.subheader("🔮 Slutspelsprognos")
        _tool_table_bundle = calculate_all_group_tables(tid, tournament)
        forecast_tables = {
            group["name"]: _tool_table_bundle["tables"].get(int(group["id"]), [])
            for group in tool_groups
        }
        forecast_lines = playoff_preview(forecast_tables, tournament["playoff_format"])
        if forecast_lines:
            st.caption("Detta är en prognos utifrån tabelläget just nu, inte en låst slutspelsseedning.")
            for line in forecast_lines:
                st.write(f"• {line}")
        else:
            st.info("Slutspelsprognos kan visas när grupper och en slutspelsmodell finns.")

    with tool_tabs[4]:
        st.subheader("🗺️ Cupkarta")
        st.caption("Lägg till praktiska platser för besökare.")
        with st.form(f"venue_point_form_{tid}", clear_on_submit=True):
            vp1, vp2 = st.columns(2)
            venue_kind = vp1.selectbox("Typ", ["Plan", "Kiosk", "Toalett", "Parkering", "Sjukvård", "Sekretariat", "Övrigt"])
            venue_label = vp2.text_input("Namn", placeholder="Exempel: Plan 1 eller Huvudparkering")
            venue_detail = st.text_input("Beskrivning", placeholder="Exempel: bakom sporthallen")
            venue_url = st.text_input("Kartlänk (frivillig)", placeholder="https://...")
            if st.form_submit_button("Lägg till punkt", type="primary"):
                if not venue_label.strip():
                    st.error("Ange ett namn.")
                else:
                    try:
                        normalized_venue_url = normalize_website_url(venue_url) if venue_url.strip() else None
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        run(
                            "INSERT INTO venue_points(tournament_id,kind,label,detail,url,sort_order) VALUES(?,?,?,?,?,?)",
                            (tid, venue_kind, venue_label.strip(), venue_detail.strip() or None, normalized_venue_url, 0),
                        )
                        record_audit(tid, "venue_add", "venue_point", f"Cupkartpunkt tillagd: {venue_label.strip()}")
                        st.rerun()
        venue_points = all_rows("SELECT * FROM venue_points WHERE tournament_id=? ORDER BY sort_order,id", (tid,))
        if venue_points:
            st.caption(f"{len(venue_points)} plats(er) registrerade")
            with st.expander("Visa eller ta bort platser", expanded=False):
                render_centered_table(pd.DataFrame([
                    {"Typ": p["kind"], "Namn": p["label"], "Beskrivning": p["detail"] or "", "Länk": p["url"] or ""}
                    for p in venue_points
                ]))
                remove_point_id = st.selectbox("Ta bort punkt", [p["id"] for p in venue_points], format_func=lambda pid: next(p["label"] for p in venue_points if p["id"] == pid), key=f"remove_point_{tid}")
                if st.button("Ta bort vald punkt", key=f"remove_point_button_{tid}"):
                    run("DELETE FROM venue_points WHERE id=? AND tournament_id=?", (remove_point_id, tid)); st.rerun()

        st.divider()
        st.subheader("▣ QR-koder per plan")
        pitch_numbers = sorted({int(m["pitch_number"]) for m in tool_matches if m["pitch_number"] is not None})
        if not pitch_numbers:
            st.info("QR-koder per plan skapas när schemat har planer.")
        for pitch_no in pitch_numbers:
            pitch_url = public_cup_url(tid) + f"&pitch={pitch_no}"
            qr_bytes = qr_png_bytes(pitch_url)
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                c1.markdown(f"**Plan {pitch_no}**")
                c1.code(pitch_url, language=None)
                if qr_bytes:
                    c2.image(qr_bytes, width=130)
                    c2.download_button(
                        f"Ladda ner QR för Plan {pitch_no}", qr_bytes,
                        file_name=f"cupnavi_plan_{pitch_no}_qr.png", mime="image/png",
                        key=f"pitch_qr_download_{tid}_{pitch_no}",
                    )

    with tool_tabs[5]:
        st.subheader("↩️ Ändringshistorik och ångra")
        audit_rows = all_rows("SELECT * FROM audit_log WHERE tournament_id=? ORDER BY id DESC LIMIT 40", (tid,))
        if not audit_rows:
            st.info("Ingen ny ändringshistorik finns ännu. Historiken registrerar de nya Cupverktygen från och med denna version.")
        if audit_rows:
            st.caption(f"{len(audit_rows)} senaste ändringar")
            with st.expander("Visa historik & ångra", expanded=False):
                for audit in audit_rows:
                    with st.container(border=True):
                        status = " · ÅNGRAD" if audit["undone_at"] else ""
                        st.markdown(f"**{audit['created_at'].replace('T',' ')} · {audit['actor']}**{status}  \\n{audit['description']}")
                        can_undo = bool(audit["reversible"]) and not audit["undone_at"] and audit["action_type"] in {"schedule_move", "delay_shift"}
                        if can_undo and st.button("Ångra denna ändring", key=f"undo_audit_{audit['id']}"):
                            undone, undo_reason, undo_meta = _undo_audit_entry_if_current(audit["id"], tid)
                            if undone:
                                record_audit(
                                    tid,
                                    "undo",
                                    undo_meta["entity_type"],
                                    f"Ångrade: {undo_meta['description']}",
                                    entity_id=undo_meta["entity_id"],
                                    actor="Admin",
                                )
                            else:
                                st.warning("Ändringen kunde inte ångras från den här äldre vyn. Senaste historik laddas om.")
                            st.rerun()

    with tool_tabs[6]:
        st.subheader("🏁 Automatisk cupsummering")
        top_scorer_row = one_row(
            """SELECT players.name AS player_name,teams.name AS team_name,SUM(s.goals) AS goals
               FROM player_match_stats s JOIN players ON players.id=s.player_id
               JOIN teams ON teams.id=players.team_id JOIN matches ON matches.id=s.match_id
               WHERE matches.tournament_id=? GROUP BY players.id,players.name,teams.name
               ORDER BY goals DESC,player_name LIMIT 1""",
            (tid,),
        )
        summary = cup_summary(tournament, tool_teams, tool_matches, top_scorer_row)
        score_word = sport_profile(summary["sport"])["score_label"]
        summary_lines = [
            f"# {summary['name']}",
            f"Sport: {summary['sport']}",
            f"Lag/deltagare: {summary['teams']}",
            f"Matcher: {summary['played_matches']} spelade av {summary['matches']}",
            f"Totalt registrerade {score_word}: {summary['total_score']}",
        ]
        if summary.get("top_scorer") and summary.get("top_scorer_score", 0) > 0:
            summary_lines.append(f"Toppscorer: {summary['top_scorer']} ({summary['top_scorer_team']}) – {summary['top_scorer_score']}")
        summary_text = "\n".join(summary_lines)
        st.markdown(summary_text)
        st.download_button(
            "Ladda ner cupsummering", summary_text.encode("utf-8"),
            file_name=f"cupnavi_summering_{tid}.md", mime="text/markdown", key=f"summary_download_{tid}"
        )


if admin_page == "Tabeller":
    table_stats_section = st.segmented_control(
        "Tabell & statistik",
        ["Tabeller", "Topplistor"],
        default="Tabeller",
        key=f"table_stats_switch_{tid}_tables",
    )
    if table_stats_section == "Topplistor":
        st.session_state[admin_page_key] = "Skytteligor"
        st.rerun()
    st.header("Tabeller")
    st.caption("Tabellerna uppdateras automatiskt när resultat registreras.")
    _admin_tables = calculate_all_group_tables(tid, tournament)
    groups = _admin_tables["groups"]
    if not groups:
        st.info("Skapa minst en grupp.")
    for g in groups:
        st.subheader(g["name"])
        table = _admin_tables["tables"].get(int(g["id"]), [])
        render_group_table(table, tournament, group['id'])
    if groups:
        with st.expander("Så sorteras tabellen", expanded=False):
            if tournament["table_tiebreak"] == "Inbördes möten först":
                st.caption("Poäng → inbördes möten → målskillnad → gjorda mål.")
            else:
                st.caption("Poäng → målskillnad → gjorda mål → lagnamn.")
    if bool(_row_value(tournament, "enable_final_ranking", 0)):
        with st.expander("Slutlig ranking", expanded=False):
            ranking = final_ranking_rows(tid, tournament)
            admin_rank_counts = one_row("SELECT COUNT(*) AS total, SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS played FROM matches WHERE tournament_id=?", (tid,))
            if ranking and int(admin_rank_counts["total"] or 0) > 0 and int(admin_rank_counts["played"] or 0) == int(admin_rank_counts["total"] or 0):
                render_centered_table(pd.DataFrame(ranking))
            else:
                st.caption("Visas när hela cupen är färdigspelad.")


if admin_page == "Skytteligor":
    table_stats_section = st.segmented_control(
        "Tabell & statistik",
        ["Tabeller", "Topplistor"],
        default="Topplistor",
        key=f"table_stats_switch_{tid}_leaders",
    )
    if table_stats_section == "Tabeller":
        st.session_state[admin_page_key] = "Tabeller"
        st.rerun()
    st.header("Topplistor")
    st.caption("Skytteligan visas först. Övrig statistik öppnas vid behov.")
    enabled_scorers = bool(_row_value(tournament, "enable_scorer_leaderboard", 1))
    enabled_assists = bool(_row_value(tournament, "enable_assist_leaderboard", 1))
    enabled_cards = bool(_row_value(tournament, "enable_card_statistics", 1))
    if not any([enabled_scorers, enabled_assists, enabled_cards]):
        st.info("Topplistor och kortstatistik är avstängda för den här turneringen. Aktivera önskade delar på Adminöversikten.")
    else:
        leaders = all_rows(
            """
            SELECT players.name AS player_name, teams.name AS team_name,
                   SUM(player_match_stats.goals) AS goals,
                   SUM(player_match_stats.assists) AS assists,
                   SUM(player_match_stats.yellow_cards) AS yellow_cards,
                   SUM(player_match_stats.red_cards) AS red_cards
            FROM player_match_stats
            JOIN players ON players.id=player_match_stats.player_id
            JOIN teams ON teams.id=players.team_id
            JOIN matches ON matches.id=player_match_stats.match_id
            WHERE matches.tournament_id=?
            GROUP BY players.id, players.name, teams.name
            HAVING goals > 0 OR assists > 0 OR yellow_cards > 0 OR red_cards > 0
            """,
            (tid,),
        )
        if enabled_scorers:
            st.subheader(tr("Skytteliga"))
            goal_rows = [r for r in sorted(leaders, key=lambda r: (-r["goals"], -r["assists"], r["player_name"].lower())) if int(r["goals"] or 0) > 0]
            if goal_rows:
                render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Mål": r["goals"]} for i, r in enumerate(goal_rows, 1)]))
            else:
                st.info("Inga målskyttar har registrerats.")
        if enabled_assists:
            with st.expander(tr("Assistliga"), expanded=False):
                assist_rows = [r for r in sorted(leaders, key=lambda r: (-r["assists"], -r["goals"], r["player_name"].lower())) if int(r["assists"] or 0) > 0]
                if assist_rows:
                    render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Assist": r["assists"]} for i, r in enumerate(assist_rows, 1)]))
                else:
                    st.info("Inga assist har registrerats.")
        if enabled_cards:
            with st.expander("Gula/röda kort", expanded=False):
                card_rows = sorted(leaders, key=lambda r: (-r["red_cards"], -r["yellow_cards"], r["player_name"].lower()))
                card_rows = [r for r in card_rows if r["yellow_cards"] or r["red_cards"]]
                if card_rows:
                    render_centered_table(pd.DataFrame([{"Spelare": r["player_name"], "Lag": r["team_name"], "Gula": r["yellow_cards"], "Röda": r["red_cards"]} for r in card_rows]))
                else:
                    st.info("Inga kort har registrerats.")


if admin_page == "Slutspel":
    st.header("Slutspel")
    st.caption("Följ slutspelsträden. De uppdateras automatiskt från cupens resultat.")

    if not tournament["playoff_model_confirmed"]:
        st.warning("Välj slutspelsmodell innan schemat genereras.")
    elif tournament["playoff_format"] == "Inget slutspel":
        st.caption("Inget slutspel är valt för cupen.")
    else:
        st.caption(f"Modell: **{tournament['playoff_format']}**")

    specs, setup_error = playoff_specs_for_tournament(tid, tournament)
    if setup_error:
        st.error(setup_error)

    brackets, duplicate_brackets = brackets_for_display(tid)
    if duplicate_brackets:
        st.warning("Äldre dubbletter av slutspel finns i databasen. Regenerera hela schemat för att bygga om träden rent.")

    if not brackets:
        if tournament["playoff_format"] != "Inget slutspel":
            st.info("Inga slutspelsmatcher är skapade ännu. Gå till Schema och generera hela spelschemat.")
    else:
        for bracket in brackets:
            st.subheader(bracket["name"])
            render_bracket_tree(bracket["id"], public=False)
            bracket_matches = all_rows(
                "SELECT * FROM matches WHERE bracket_id=? ORDER BY round_no,match_no",
                (bracket["id"],),
            )
            if bracket_matches:
                with st.expander("Matchlista", expanded=False):
                    overview_rows = []
                    for match_row in bracket_matches:
                        schedule_text, _ = match_meta(match_row)
                        match_number = schedule_text.split(" · ", 1)[0] if match_row["scheduled_start"] else "Ej schemalagd"
                        overview_rows.append({
                            "Match": match_number,
                            "Fas": match_row["stage"],
                            "Hemmalag": source_label(match_row["home_source"]),
                            "Bortalag": source_label(match_row["away_source"]),
                        })
                    render_centered_table(pd.DataFrame(overview_rows))



# --- CupNavi performance diagnostics (Admin only) -----------------------------
# Rendered last so the measurements represent almost the whole Streamlit rerun.
if view_mode == "Admin" and admin_page == "Adminöversikt":
    _render_ms = round((time.perf_counter() - _APP_RENDER_STARTED) * 1000, 1)
    _db_ms = round(float(_PERF.get("db_ms", 0.0)), 1)
    _db_calls = int(_PERF.get("db_calls", 0) or 0)
    _writes = int(_PERF.get("writes", 0) or 0)
    _cache_hits = int(_PERF.get("cache_hits", 0) or 0)
    _derived_hits = int(_PERF.get("derived_hits", 0) or 0)
    _db_share = round((_db_ms / _render_ms) * 100, 1) if _render_ms > 0 else 0.0

    _perf_history = list(st.session_state.get("_cupnavi_perf_history", []))
    _perf_history.append(
        {
            "Render ms": _render_ms,
            "DB ms": _db_ms,
            "DB-anrop": _db_calls,
            "Writes": _writes,
            "Query-cache": _cache_hits,
            "Derived-cache": _derived_hits,
            "DB-andel %": _db_share,
        }
    )
    st.session_state["_cupnavi_perf_history"] = _perf_history[-12:]

    with st.expander("Prestandadiagnostik", expanded=False):
        st.caption(
            "Mäter den aktuella Admin-rerenderingen i den här sessionen. "
            "Värdena skickas inte till någon extern analystjänst."
        )
        _perf_cols = st.columns(4)
        _perf_cols[0].metric("Render", f"{_render_ms:.0f} ms")
        _perf_cols[1].metric("Databas", f"{_db_ms:.0f} ms")
        _perf_cols[2].metric("DB-anrop", _db_calls)
        _perf_cols[3].metric("DB-andel", f"{_db_share:.0f} %")

        if _render_ms >= 2500:
            st.warning("Renderingen är långsam (>2,5 s). DB- och nätverksanrop bör granskas.")
        elif _render_ms >= 1200:
            st.info("Renderingen är märkbar (1,2–2,5 s). Det finns sannolikt mer att optimera.")
        else:
            st.success("Renderingen ligger under 1,2 s i den här körningen.")

        _history = st.session_state["_cupnavi_perf_history"]
        if len(_history) >= 2:
            _avg_render = sum(row["Render ms"] for row in _history) / len(_history)
            _avg_db = sum(row["DB ms"] for row in _history) / len(_history)
            st.caption(
                f"Snitt senaste {len(_history)} laddningarna: "
                f"{_avg_render:.0f} ms render · {_avg_db:.0f} ms DB."
            )
            render_centered_table(pd.DataFrame(_history))



def inject_v198_visual_system():
    st.markdown(
        """<style>
        /* ================================================================
           CUPNAVI VISUAL SYSTEM v1.198
           Final visual authority. Presentation only.
           ================================================================ */

        :root{
          --cn98-primary:#176b3a;
          --cn98-primary-hover:#12572f;
          --cn98-primary-soft:#edf7f0;
          --cn98-ink:#17221c;
          --cn98-ink-2:#536159;
          --cn98-ink-3:#768279;
          --cn98-bg:#f5f7f6;
          --cn98-surface:#ffffff;
          --cn98-surface-2:#f9fbfa;
          --cn98-border:#dbe3de;
          --cn98-border-strong:#b9c7bf;
          --cn98-focus:#72a887;
          --cn98-success:#176b3a;
          --cn98-warning:#8a5709;
          --cn98-error:#b42318;
          --cn98-info:#365f7c;

          --cn98-r1:7px;
          --cn98-r2:10px;
          --cn98-r3:14px;
          --cn98-shadow:0 1px 2px rgba(14,31,22,.04),0 5px 18px rgba(14,31,22,.045);

          --cn98-s1:4px;
          --cn98-s2:8px;
          --cn98-s3:12px;
          --cn98-s4:16px;
          --cn98-s5:24px;
          --cn98-s6:32px;
          --cn98-s7:48px;

          --cn98-control:40px;
          --cn98-max:1240px;
        }

        html,body,.stApp{
          background:var(--cn98-bg)!important;
          color:var(--cn98-ink)!important;
        }
        .stApp .block-container{
          max-width:var(--cn98-max)!important;
          padding-left:clamp(12px,2.25vw,28px)!important;
          padding-right:clamp(12px,2.25vw,28px)!important;
          padding-bottom:40px!important;
        }

        /* TYPOGRAPHY — one restrained scale */
        h1,h2,h3,h4,h5,h6{
          font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif!important;
          color:var(--cn98-ink)!important;
          letter-spacing:-.015em!important;
          text-wrap:balance;
        }
        h1{font-size:clamp(1.55rem,2vw,1.9rem)!important;line-height:1.12!important;font-weight:780!important}
        h2{font-size:clamp(1.22rem,1.55vw,1.42rem)!important;line-height:1.2!important;font-weight:750!important}
        h3{font-size:1.05rem!important;line-height:1.25!important;font-weight:720!important}
        h4{font-size:.95rem!important;line-height:1.3!important;font-weight:700!important}
        p,li,label,input,textarea,button{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif!important}
        p,li{line-height:1.48}
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p{
          color:var(--cn98-ink-2)!important;
          font-size:.81rem!important;
          line-height:1.4!important;
        }
        [data-testid="stWidgetLabel"],
        [data-testid="stWidgetLabel"] p{
          color:var(--cn98-ink)!important;
          font-size:.83rem!important;
          font-weight:650!important;
          opacity:1!important;
        }

        /* PAGE RHYTHM */
        [data-testid="stVerticalBlock"]{gap:.62rem!important}
        [data-testid="stHorizontalBlock"]{gap:.72rem!important}
        hr{border-color:var(--cn98-border)!important;margin:20px 0!important}

        /* BUTTONS */
        [data-testid="stButton"] button,
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stDownloadButton"] button,
        [data-testid="stLinkButton"] a,
        [data-testid="stPopover"] > button{
          min-height:var(--cn98-control)!important;
          border-radius:var(--cn98-r1)!important;
          padding:7px 13px!important;
          font-size:.83rem!important;
          font-weight:680!important;
          box-shadow:none!important;
          transition:background-color .13s ease,border-color .13s ease,color .13s ease,transform .06s ease!important;
        }
        [data-testid="stButton"] button[kind="primary"],
        [data-testid="stFormSubmitButton"] button[kind="primary"]{
          background:var(--cn98-primary)!important;
          border:1px solid var(--cn98-primary)!important;
          color:#fff!important;
        }
        [data-testid="stButton"] button[kind="primary"] *,
        [data-testid="stFormSubmitButton"] button[kind="primary"] *{color:#fff!important}
        [data-testid="stButton"] button[kind="primary"]:hover,
        [data-testid="stFormSubmitButton"] button[kind="primary"]:hover{
          background:var(--cn98-primary-hover)!important;
          border-color:var(--cn98-primary-hover)!important;
        }
        [data-testid="stButton"] button[kind="secondary"],
        [data-testid="stDownloadButton"] button,
        [data-testid="stLinkButton"] a,
        [data-testid="stPopover"] > button{
          background:var(--cn98-surface)!important;
          border:1px solid var(--cn98-border-strong)!important;
          color:#24342b!important;
        }
        [data-testid="stButton"] button[kind="secondary"]:hover,
        [data-testid="stDownloadButton"] button:hover,
        [data-testid="stLinkButton"] a:hover,
        [data-testid="stPopover"] > button:hover{
          background:#f0f4f2!important;
          border-color:#8da096!important;
        }
        [data-testid="stButton"] button:active,
        [data-testid="stFormSubmitButton"] button:active{transform:translateY(1px)!important}
        button:disabled,[aria-disabled="true"]{opacity:.5!important;cursor:not-allowed!important}

        /* FORMS */
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stDateInput"] input,
        [data-baseweb="select"] > div{
          min-height:var(--cn98-control)!important;
          border-radius:var(--cn98-r1)!important;
          border:1px solid var(--cn98-border-strong)!important;
          background:var(--cn98-surface)!important;
          color:var(--cn98-ink)!important;
          box-shadow:none!important;
        }
        [data-testid="stTextInput"] input:hover,
        [data-testid="stNumberInput"] input:hover,
        [data-testid="stTextArea"] textarea:hover,
        [data-testid="stDateInput"] input:hover,
        [data-baseweb="select"] > div:hover{border-color:#879b90!important}
        [data-testid="stTextInput"] input:focus,
        [data-testid="stNumberInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus,
        [data-testid="stDateInput"] input:focus,
        [data-baseweb="select"] > div:focus-within{
          border-color:var(--cn98-primary)!important;
          box-shadow:0 0 0 3px rgba(23,107,58,.12)!important;
          outline:none!important;
        }
        [data-testid="stForm"]{
          border:1px solid var(--cn98-border)!important;
          background:var(--cn98-surface)!important;
          border-radius:var(--cn98-r2)!important;
          box-shadow:none!important;
        }

        /* RADIO / CHECKBOX / TOGGLE */
        [data-testid="stRadio"] label,
        [data-testid="stCheckbox"] label{
          color:var(--cn98-ink)!important;
          font-size:.83rem!important;
        }
        [data-testid="stRadio"] > div{gap:6px!important;flex-wrap:wrap!important}
        [data-testid="stRadio"] label{
          padding:5px 9px!important;
          border:1px solid var(--cn98-border)!important;
          border-radius:999px!important;
          background:var(--cn98-surface)!important;
        }

        /* CONTAINERS */
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stExpander"],
        [data-testid="stMetric"]{
          background:var(--cn98-surface)!important;
          border:1px solid var(--cn98-border)!important;
          border-radius:var(--cn98-r2)!important;
          box-shadow:none!important;
        }
        [data-testid="stMetric"]{padding:10px 12px!important}
        [data-testid="stMetricLabel"]{color:var(--cn98-ink-2)!important}
        [data-testid="stMetricValue"]{font-weight:760!important;letter-spacing:-.015em!important}
        [data-testid="stExpander"] summary{
          min-height:40px!important;
          color:var(--cn98-ink)!important;
          font-size:.84rem!important;
          font-weight:680!important;
        }

        /* ALERTS */
        [data-testid="stAlert"]{
          border-radius:var(--cn98-r2)!important;
          border-width:1px!important;
          box-shadow:none!important;
          padding:10px 12px!important;
        }
        [data-testid="stAlert"] p{font-size:.83rem!important;line-height:1.42!important}

        /* NAVIGATION / TABS */
        [data-testid="stTabs"] [role="tablist"]{
          gap:2px!important;
          border-bottom:1px solid var(--cn98-border)!important;
        }
        [data-testid="stTabs"] button[role="tab"]{
          min-height:38px!important;
          padding:6px 10px!important;
          border-radius:var(--cn98-r1) var(--cn98-r1) 0 0!important;
          color:var(--cn98-ink-2)!important;
          font-size:.82rem!important;
          font-weight:650!important;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
          color:var(--cn98-primary)!important;
          font-weight:730!important;
        }
        [data-testid="stButtonGroup"] button{
          min-height:36px!important;
          background:var(--cn98-surface)!important;
          border-color:var(--cn98-border)!important;
          color:var(--cn98-ink-2)!important;
          font-size:.81rem!important;
        }
        [data-testid="stButtonGroup"] button[aria-pressed="true"],
        [data-testid="stButtonGroup"] button[aria-checked="true"],
        [data-testid="stButtonGroup"] [data-selected="true"]{
          background:var(--cn98-primary-soft)!important;
          color:#14552f!important;
          border-color:#9dbdac!important;
          font-weight:700!important;
        }

        /* SIDEBAR */
        [data-testid="stSidebar"]{
          background:#f0f4f1!important;
          border-right:1px solid var(--cn98-border)!important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.42rem!important}
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{
          font-size:.75rem!important;
          color:var(--cn98-ink-2)!important;
          font-weight:700!important;
        }

        /* TABLES */
        [data-testid="stDataFrame"],
        .texttv-table-wrap{
          border:1px solid var(--cn98-border)!important;
          border-radius:var(--cn98-r2)!important;
          background:var(--cn98-surface)!important;
          overflow:auto!important;
          box-shadow:none!important;
        }
        .texttv-table{
          width:100%!important;
          border-collapse:separate!important;
          border-spacing:0!important;
        }
        .texttv-table th{
          position:sticky!important;
          top:0!important;
          z-index:2!important;
          background:#eef3f0!important;
          color:var(--cn98-ink)!important;
          font-size:.76rem!important;
          font-weight:730!important;
        }
        .texttv-table td,.texttv-table th{
          padding:8px 10px!important;
          border:0!important;
          border-bottom:1px solid #e7ece9!important;
        }
        .texttv-table tbody tr:last-child td{border-bottom:0!important}
        .texttv-table tbody tr:hover td{background:#f8faf9!important}

        /* PUBLIC EXPERIENCE */
        .cup-hero{
          background:#17324d!important;
          background-image:none!important;
          border:0!important;
          border-radius:var(--cn98-r3)!important;
          box-shadow:var(--cn98-shadow)!important;
        }
        .public-match-card,.cn-live-card,.public-metric{
          border-color:var(--cn98-border)!important;
          box-shadow:none!important;
          border-radius:var(--cn98-r2)!important;
        }
        .public-match-card{background:var(--cn98-surface)!important}
        .cn-public-top-nav + div [data-testid="stButton"] button{
          min-height:38px!important;
          font-size:.80rem!important;
        }
        .classic-bracket{
          background:#fff!important;
          border-color:var(--cn98-border)!important;
          box-shadow:none!important;
        }
        .classic-match{
          border-color:var(--cn98-border-strong)!important;
          box-shadow:0 2px 8px rgba(18,34,25,.06)!important;
        }

        /* SHARE POPOVER — explicit light surface */
        [data-baseweb="popover"]{
          color:var(--cn98-ink)!important;
        }
        [data-baseweb="popover"] > div{
          background:var(--cn98-surface)!important;
          color:var(--cn98-ink)!important;
          border:1px solid var(--cn98-border)!important;
          border-radius:var(--cn98-r3)!important;
          box-shadow:0 12px 34px rgba(15,23,42,.14)!important;
        }
        [data-baseweb="popover"] p,
        [data-baseweb="popover"] span,
        [data-baseweb="popover"] label{
          color:var(--cn98-ink)!important;
        }

        /* EMPTY STATES */
        .cn-empty-state{
          background:var(--cn98-surface-2)!important;
          border:1px dashed var(--cn98-border-strong)!important;
          border-radius:var(--cn98-r2)!important;
          padding:18px!important;
          box-shadow:none!important;
        }
        .cn-empty-state p{color:var(--cn98-ink-2)!important}

        /* ADMIN */
        .cn-current-admin-page{
          background:rgba(245,247,246,.98)!important;
          border-color:var(--cn98-border)!important;
          box-shadow:none!important;
          backdrop-filter:none!important;
          -webkit-backdrop-filter:none!important;
        }
        .cn-flow-context,.cn-status-card,.cn-step,.cn-recommend-card,.cn-progress-hero,.cn-attention-row{
          border-color:var(--cn98-border)!important;
          box-shadow:none!important;
          border-radius:var(--cn98-r2)!important;
        }

        /* ACCESSIBILITY */
        button:focus-visible,
        a:focus-visible,
        input:focus-visible,
        textarea:focus-visible,
        [role="combobox"]:focus-visible,
        [role="tab"]:focus-visible,
        [role="radio"]:focus-visible{
          outline:3px solid rgba(23,107,58,.28)!important;
          outline-offset:2px!important;
        }

        /* TABLET */
        @media(max-width:1024px){
          :root{--cn98-max:100%}
          .stApp .block-container{
            padding-left:16px!important;
            padding-right:16px!important;
          }
        }

        /* MOBILE */
        @media(max-width:768px){
          :root{--cn98-control:44px}
          html,body,.stApp{max-width:100vw!important;overflow-x:hidden!important}
          .stApp .block-container{
            padding-left:10px!important;
            padding-right:10px!important;
            padding-bottom:88px!important;
          }
          [data-testid="stHorizontalBlock"]{gap:7px!important}
          /* Admin forms/actions must not remain squeezed into desktop columns on phones. */
          [data-testid="stHorizontalBlock"]{
            flex-wrap:wrap!important;
          }
          [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{
            flex:1 1 220px!important;
            min-width:0!important;
            width:auto!important;
          }
          .cn-flow-status{
            display:flex!important;
            flex-wrap:wrap!important;
            gap:5px!important;
          }
          .cn-flow-pill{
            white-space:normal!important;
            line-height:1.25!important;
          }
          .cn-next-action{
            min-height:auto!important;
          }
          [data-testid="stButton"] button,
          [data-testid="stFormSubmitButton"] button,
          [data-testid="stDownloadButton"] button,
          [data-testid="stLinkButton"] a,
          [data-testid="stPopover"] > button{
            min-height:44px!important;
          }
          /* Tabs remain reachable on phones instead of shrinking/cutting off labels. */
          [data-baseweb="tab-list"]{
            overflow-x:auto!important;
            overflow-y:hidden!important;
            flex-wrap:nowrap!important;
            -webkit-overflow-scrolling:touch;
            scrollbar-width:thin;
          }
          [data-baseweb="tab"]{
            flex:0 0 auto!important;
            min-height:44px!important;
            white-space:nowrap!important;
          }
          [data-testid="stDataFrame"],.texttv-table-wrap{
            max-width:100%!important;
            overflow-x:auto!important;
            -webkit-overflow-scrolling:touch;
          }
          .texttv-table td,.texttv-table th{
            padding:7px 8px!important;
            white-space:nowrap!important;
          }
          [data-baseweb="popover"] > div{
            max-width:calc(100vw - 20px)!important;
            max-height:calc(100vh - 24px)!important;
            overflow:auto!important;
          }
        }

        @media(max-width:390px){
          [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{
            flex:1 1 100%!important;
            width:100%!important;
          }
          .stApp .block-container{
            padding-left:8px!important;
            padding-right:8px!important;
          }
          [data-testid="stButton"] button,
          [data-testid="stFormSubmitButton"] button{
            padding-left:9px!important;
            padding-right:9px!important;
          }
        }

        @media(min-width:1440px){
          :root{--cn98-max:1280px}
        }

        @media(prefers-reduced-motion:reduce){
          *,*::before,*::after{
            animation-duration:.01ms!important;
            animation-iteration-count:1!important;
            transition-duration:.01ms!important;
            scroll-behavior:auto!important;
          }
        }
        </style>""",
        unsafe_allow_html=True,
    )

inject_v198_visual_system()
