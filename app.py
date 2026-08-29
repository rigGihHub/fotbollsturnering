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
    """Fingerprint deployed sources with metadata instead of rereading every file.

    CupNavi increments VERSION.txt for each release. Combining that small file with
    source path/size/mtime metadata preserves hot-deploy detection while avoiding
    repeatedly reading ~1 MB of Python source on every Streamlit rerun.
    """
    root = Path(__file__).resolve().parent
    candidates = [root / "app.py", root / "requirements.txt", root / "VERSION.txt"]
    core_root = root / "cupnavi_core"
    if core_root.exists():
        candidates.extend(sorted(core_root.rglob("*.py")))
    digest = hashlib.sha256()
    try:
        digest.update((root / "VERSION.txt").read_bytes())
    except OSError:
        pass
    for path in candidates:
        try:
            relative = path.relative_to(root).as_posix()
            stat = path.stat()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b":")
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
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

from cupnavi_core.version import APP_VERSION as IMPORTED_CORE_APP_VERSION, release_ui_label

from cupnavi_core.observability import safe_error_record, persist_error
from cupnavi_core.performance import build_performance_snapshot, performance_log_line
from cupnavi_core.schedule_quality import assess_schedule
from cupnavi_core.public_competition import calculate_group_table
from cupnavi_core.initial_setup_view import InitialSetupDependencies, render_initial_tournament_setup as render_initial_tournament_setup_module
from cupnavi_core.home_away import orientation_balance_score
from cupnavi_core.migrations import apply_migrations, LATEST_SCHEMA_VERSION, ensure_competition_class_schema_compat, ensure_v16_setup_schema_compat, ensure_v18_pitch_names_schema_compat, ensure_v19_schema_compat, ensure_v20_schema_compat, ensure_v21_schema_compat
from cupnavi_core.health import collect_database_health
from cupnavi_core.backup import build_backup_bytes, validate_backup_bytes, restore_backup_as_new_tournament
from cupnavi_core.rate_limit import consume_rate_limit
from cupnavi_core.config import BACKUP_FILE_SUFFIX, PUBLIC_BASE_URL
from cupnavi_core.schedule_repository import ScheduleRepository
from cupnavi_core.schedule_domain import build_schedule_window, schedule_source_team_id
from cupnavi_core.schedule_workspace_view import ScheduleWorkspaceDependencies, render_schedule_workspace
from cupnavi_core.schedule_recovery_view import ScheduleRecoveryDependencies, render_schedule_recovery_actions as render_schedule_recovery_actions_module
from cupnavi_core.admin_results_view import AdminResultsDependencies, render_admin_results_workspace
from cupnavi_core.admin_match_events_view import AdminMatchEventsDependencies, render_admin_match_events_workspace
from cupnavi_core.style_system import (
    inject_custom_css as _inject_custom_css_impl,
    inject_ux2_css as _inject_ux2_css_impl,
    inject_v191_design_system as _inject_v191_design_system_impl,
    inject_v193_product_design_system as _inject_v193_product_design_system_impl,
    inject_v266_public_mobile_css as _inject_v266_public_mobile_css_impl,
    inject_v198_visual_system as _inject_v198_visual_system_impl,
    inject_public_experience_styles,
)
from cupnavi_core.team_portal import generate_access_code, generate_short_numeric_code, new_code_hash, verify_access_code, squad_deadline_at, squad_is_locked
from cupnavi_core.team_portal_view import TeamPortalDependencies, render_team_portal_workspace
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
from cupnavi_core.push_notification_service import enqueue_goal_push_events
from cupnavi_core.i18n import SUPPORTED_LOCALES, DEFAULT_LOCALE, DEFAULT_TIMEZONE, valid_timezone
from cupnavi_core.lifecycle import normalize_status, status_label, choose_unique_slug
from cupnavi_core.qol import TOURNAMENT_TEMPLATES, template_definition, clone_tournament_payload, checklist_items, admin_mode
from cupnavi_core.fairness import fairness_report
from cupnavi_core.ux2 import schedule_board
from cupnavi_core.about import feature_catalog, about_intro
from cupnavi_core.ui_logic import resolve_tournament_selector_seed
from cupnavi_core.public_view_logic import (
    public_navigation_specs,
    public_section_for_page,
    resolve_public_page,
)
from cupnavi_core.public_navigation_view import build_public_navigation_html
from cupnavi_core.public_shell_view import build_public_hero_html, render_public_screen_mode
from cupnavi_core.public_team_follow_view import render_public_team_follow
from cupnavi_core.public_matches_view import render_public_matches_fragment as render_public_matches_fragment_module
from cupnavi_core.public_info_view import render_public_info_section as render_public_info_section_module
from cupnavi_core.public_statistics_view import render_public_statistics_section as render_public_statistics_section_module
from cupnavi_core.public_match_cards import render_public_match_cards as render_public_match_cards_module
from cupnavi_core.public_match_filter_logic import filter_matches, sort_public_matches
from cupnavi_core.public_match_filters_view import render_public_match_filters as render_public_match_filters_module
from cupnavi_core.public_workspace_view import PublicWorkspaceDependencies, render_public_workspace
from cupnavi_core.public_presentation_view import (
    public_match_events_html as _public_match_events_html_impl,
    public_rules_html as _public_rules_html_impl,
    render_bracket_tree as _render_bracket_tree_impl,
    render_group_table as _render_group_table_impl,
)
from cupnavi_core.match_reporter_logic import result_snapshot
from cupnavi_core.match_reporter_workspace_view import (
    MatchReporterWorkspaceDeps,
    render_match_reporter_workspace,
)
from cupnavi_core.admin_overview_repository import fetch_admin_workflow_counts
from cupnavi_core.admin_overview import (
    build_control_status,
    build_organizer_overview,
    build_progress_and_attention,
    build_readiness,
    build_status_cards_html,
    build_workflow_html,
    class_progress_caption,
    recommend_next_step,
)
from cupnavi_core.admin_publication import build_completion_state
from cupnavi_core.admin_publication_repository import fetch_lifecycle_match_counts
from cupnavi_core.admin_publication_view import (
    render_admin_lifecycle_controls,
    render_admin_publication_controls,
)
from cupnavi_core.admin_role_codes_view import render_role_code_card


def inject_custom_css():
    return _inject_custom_css_impl(st)


def inject_ux2_css():
    return _inject_ux2_css_impl(st, components)


def inject_v191_design_system():
    return _inject_v191_design_system_impl(st)


def inject_v193_product_design_system():
    return _inject_v193_product_design_system_impl(st)


def inject_v266_public_mobile_css():
    return _inject_v266_public_mobile_css_impl(st)


def inject_v198_visual_system():
    return _inject_v198_visual_system_impl(st)


APP_BUILD_VERSION = "2026.08.29-303-PUBLIC-MATCH-EVENT-ROW-NORMALIZATION"
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


def _apply_schedule_recovery_extend(tournament_id, tournament, rules, context, minutes):
    rows = pitch_day_windows(tournament_id, int(rules["pitch_count"]))
    changed = 0
    for row in rows:
        if str(row["play_date"]) != str(context["last_date"]):
            continue
        old = datetime.strptime(row["end_time"], "%H:%M")
        proposed = min(old + timedelta(minutes=minutes), datetime.strptime("23:55", "%H:%M"))
        new = proposed.strftime("%H:%M")
        if new > row["end_time"]:
            save_pitch_day_window(tournament_id, int(row["pitch_number"]), row["play_date"], row["start_time"], new, True)
            changed += 1
    _rerun_schedule_after_recovery(tournament_id, tournament, rules, f"Plantiderna förlängdes på {changed} plan(er) med upp till {minutes} minuter")


def _apply_schedule_recovery_late_first(tournament_id, tournament, rules, context):
    run("UPDATE teams SET late_first_match=0,earliest_first_time=NULL WHERE tournament_id=? AND late_first_match=1", (int(tournament_id),))
    run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?", (int(tournament_id),))
    _rerun_schedule_after_recovery(tournament_id, tournament, rules, "Lagens önskemål om senare första match togs bort")


def _apply_schedule_recovery_break(tournament_id, tournament, rules, context):
    run("UPDATE schedule_rules SET consecutive_match_break_minutes=0 WHERE tournament_id=?", (int(tournament_id),))
    run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?", (int(tournament_id),))
    _rerun_schedule_after_recovery(tournament_id, tournament, rules, "Extra lagvila sattes till 0 minuter")


def _apply_schedule_recovery_pitch(tournament_id, tournament, rules, context):
    new_count = int(rules["pitch_count"] or 1) + 1
    run("UPDATE schedule_rules SET pitch_count=? WHERE tournament_id=?", (new_count, int(tournament_id)))
    ensure_pitch_definitions(tournament_id, new_count)
    ensure_pitch_day_windows(tournament_id, tournament, new_count, rules["first_match_time"], rules["latest_kickoff_time"])
    run("UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?", (int(tournament_id),))
    _rerun_schedule_after_recovery(tournament_id, tournament, rules, f"Plan {new_count} lades till med standardtider")


def render_schedule_recovery_actions(tournament_id, tournament, rules, context):
    return render_schedule_recovery_actions_module(
        tournament_id, tournament, rules, context,
        deps=ScheduleRecoveryDependencies(
            st=st,
            apply_extend=_apply_schedule_recovery_extend,
            apply_late_first=_apply_schedule_recovery_late_first,
            apply_break=_apply_schedule_recovery_break,
            apply_pitch=_apply_schedule_recovery_pitch,
        ),
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


def public_match_overview_db_snapshot(tournament_id, *, scorer_enabled=True, assist_enabled=True, active_minutes=5):
    """Load fresh public overview data while keeping Streamlit/session concerns in the UI layer."""
    from cupnavi_core.public_match_repository import fetch_public_match_overview

    session_key = f"_cupnavi_visitor_session_{tournament_id}"
    token = st.session_state.get(session_key)
    if not token:
        token = hashlib.sha256(os.urandom(32)).hexdigest()
        st.session_state[session_key] = token

    cutoff = (datetime.now() - timedelta(minutes=max(1, int(active_minutes)))).isoformat(timespec="seconds")
    started = time.perf_counter()
    with db() as con:
        snapshot = fetch_public_match_overview(
            con, tournament_id=tournament_id, cutoff=cutoff, session_token=token,
            scorer_enabled=scorer_enabled, assist_enabled=assist_enabled,
        )
    _record_db_call(started)
    return {
        "active_visitors": int(snapshot["visitor_count"]) + 1,
        "leader_rows": snapshot["leader_rows"],
    }


def public_match_events_db_snapshot(match_ids):
    """Load visible public match events with DB timing kept in the app service layer."""
    from cupnavi_core.public_match_repository import fetch_public_match_events

    normalized_ids = [int(match_id) for match_id in match_ids if int(match_id) > 0]
    if not normalized_ids:
        return {}
    started = time.perf_counter()
    with db() as con:
        grouped = fetch_public_match_events(con, normalized_ids)
    _record_db_call(started)
    return grouped


def render_public_share_control(tournament_id, tournament):
    """Kompakt delningskontroll placerad under publika nyckeltal."""
    share_url = public_cup_url(tournament_id)
    share_text = f"{tr('Följ cupen')}: {tournament['name']} – {share_url}"
    whatsapp_href = "https://wa.me/?text=" + quote(share_text)
    email_href = "mailto:?subject=" + quote(f"CupNavi – {tournament['name']}") + "&body=" + quote(share_text)
    sms_href = "sms:?&body=" + quote(share_text)

    st.markdown(
        """<style>
        .cn-share-metrics-anchor{height:0;margin:0;padding:0}
        .cn-share-metrics-anchor + div{width:max-content!important;margin:0 0 8px 0!important}
        .cn-share-metrics-anchor + div button{
          min-height:34px!important;padding:4px 12px!important;border-radius:9px!important;
          font-size:.78rem!important;font-weight:800!important;box-shadow:none!important;
        }
        @media(max-width:760px){
          .cn-share-metrics-anchor + div{width:100%!important;margin:0 0 10px!important}
          .cn-share-metrics-anchor + div button{width:100%!important;min-height:40px!important}
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='cn-share-metrics-anchor'></div>", unsafe_allow_html=True)
    with st.popover("Dela", help=tr("Dela cupen")):
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


@st.cache_data(show_spinner=False)
def qr_png_bytes(value):
    """QR-bilden är deterministisk och qrcode laddas först när delning används."""
    try:
        import qrcode
    except ImportError:
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
        "Besök idag": "Visits today", "Sidvisningar idag": "Page views today", "Besökare nu": "Visitors now",
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
        "Poängledare": "Points leader", "Minst insläppta": "Fewest conceded",
        "Skytteligaledare": "Top scorer", "Assistledare": "Assist leader",
        "poäng": "pts", "insläppta": "conceded",
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



inject_ux2_css()




inject_v191_design_system()



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

# v1.266: mobil publikvy – ta bort Streamlit Cloud-chrome som visar bl.a. "Fork",
# fäst cupnavigeringen upptill och säkra responsiviteten i summeringsrutorna.

inject_v266_public_mobile_css()
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
        "published_once": "INTEGER NOT NULL DEFAULT 0",
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
    con.execute(
        "UPDATE tournaments SET published_once=1 WHERE COALESCE(is_published,0)=1 AND COALESCE(published_once,0)=0"
    )
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
                published_once INTEGER NOT NULL DEFAULT 0,
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


def _goal_push_kwargs(tournament_id, match_row, expected, home_score, away_score):
    """Build provider-neutral goal push payload inputs before a write transaction."""
    home_team_id = resolve_source(match_row["home_source"])
    away_team_id = resolve_source(match_row["away_source"])
    return {
        "tournament_id": int(tournament_id),
        "match_id": int(match_row["id"]),
        "home_team_id": int(home_team_id) if home_team_id else None,
        "away_team_id": int(away_team_id) if away_team_id else None,
        "home_team_name": source_label(match_row["home_source"]),
        "away_team_name": source_label(match_row["away_source"]),
        "old_home_score": expected.get("home_score"),
        "old_away_score": expected.get("away_score"),
        "new_home_score": home_score,
        "new_away_score": away_score,
    }


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
    return _render_group_table_impl(
        table_rows, tournament, group_id, st=st,
        group_playoff_qualifiers=group_playoff_qualifiers,
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
    # v1.260: validering läser lag i en batch. team() per unikt lag var särskilt
    # dyrt mot Turso även om render-cachen förhindrade exakt dubbla queries.
    validation_teams = {int(r["id"]): r for r in all_rows("SELECT * FROM teams WHERE tournament_id=?", (tournament_id,))}
    def validation_team(team_id):
        return validation_teams.get(int(team_id)) if team_id else None
    errors, warnings = [], []
    events = []
    for number, match_row in enumerate(rows, 1):
        start_at = datetime.fromisoformat(match_row["scheduled_start"])
        match_duration = duration + (playoff_extra if match_row["stage"] != "Gruppspel" else timedelta(0))
        home_id, away_id = resolve_source(match_row["home_source"]), resolve_source(match_row["away_source"])
        home_team, away_team = validation_team(home_id), validation_team(away_id)
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
                    f"{validation_team(team_id)['name']} saknar den obligatoriska extrapusen på {consecutive_break_minutes} minuter "
                    f"mellan match {previous['number']} och {current['number']}."
                )
            if rest_minutes <= rules["pitch_break_minutes"]:
                consecutive += 1
                if avoid_consecutive:
                    warnings.append(f"{validation_team(team_id)['name']} spelar match {previous['number']} och {current['number']} direkt efter varandra.")
        team_row = validation_team(team_id)
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
            "Lag": validation_team(team_id)["name"], "Matcher": len(team_matches),
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
    return _render_bracket_tree_impl(
        bracket_id, public, st=st, all_rows=all_rows, row_value=_row_value,
        resolve_source=resolve_source, source_label=source_label, match_meta=match_meta,
    )



def public_match_events_html(match_id, match_row=None, rows=None, team_names=None):
    return _public_match_events_html_impl(
        match_id, match_row, rows, team_names, all_rows=all_rows, one_row=one_row,
        row_value=_row_value, resolve_source=resolve_source, tr=tr,
    )




def public_rules_html(tournament, rules):
    return _public_rules_html_impl(
        tournament, rules, row_value=_row_value, sport_profile=sport_profile,
    )


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
    """Thin application adapter for the extracted public tournament workspace."""
    return render_public_workspace(
        tournament_id,
        tournament,
        PublicWorkspaceDependencies(
            st=st,
            perf=_PERF,
            derived_cache_get=_derived_cache_get,
            row_value=_row_value,
            all_rows=all_rows,
            build_public_hero_html=build_public_hero_html,
            build_public_navigation_html=build_public_navigation_html,
            calculate_all_group_tables=calculate_all_group_tables,
            calculate_table=calculate_table,
            confirm_notification_subscription=confirm_notification_subscription,
            create_notification_subscription=create_notification_subscription,
            cup_date_label=cup_date_label,
            fetch_weather_forecast=fetch_weather_forecast,
            filter_matches=filter_matches,
            inject_public_experience_styles=inject_public_experience_styles,
            kit_background_for_team=kit_background_for_team,
            match_duration_minutes=match_duration_minutes,
            match_kit_colors=match_kit_colors,
            normalize_status=normalize_status,
            one_row=one_row,
            pitch_label=pitch_label,
            public_core_snapshot=public_core_snapshot,
            public_cup_url=public_cup_url,
            public_match_events_db_snapshot=public_match_events_db_snapshot,
            public_match_events_html=public_match_events_html,
            public_match_overview_db_snapshot=public_match_overview_db_snapshot,
            public_navigation_specs=public_navigation_specs,
            render_empty_state=render_empty_state,
            render_public_info_section=render_public_info_section,
            render_public_match_cards_module=render_public_match_cards_module,
            render_public_match_filters_module=render_public_match_filters_module,
            render_public_matches_fragment_module=render_public_matches_fragment_module,
            render_public_screen_mode=render_public_screen_mode,
            render_public_share_control=render_public_share_control,
            render_public_statistics_section=render_public_statistics_section,
            render_public_team_follow=render_public_team_follow,
            resolve_public_page=resolve_public_page,
            resolve_source=resolve_source,
            sort_public_matches=sort_public_matches,
            source_label=source_label,
            sport_profile=sport_profile,
            swedish_datetime=swedish_datetime,
            tr=tr,
            track_public_visit=track_public_visit,
            unsubscribe_notification_subscription=unsubscribe_notification_subscription,
            weather_for_match=weather_for_match,
            weather_label=weather_label,
        ),
    )

def _reporter_save_quick_result(tournament_id, quick_match, home_score, away_score):
    """Persist one quick result with the existing optimistic-locking boundary."""
    quick_match_id = int(quick_match["id"])
    before = result_snapshot(quick_match)
    goal_push = _goal_push_kwargs(tournament_id, quick_match, before, home_score, away_score)
    with db() as con:
        saved = update_match_result_if_unchanged(
            con,
            quick_match_id,
            before,
            home_score=home_score,
            away_score=away_score,
            home_penalties=quick_match["home_penalties"],
            away_penalties=quick_match["away_penalties"],
            decided_winner_id=quick_match["decided_winner_id"],
            referee_id=quick_match["referee_id"],
        )
        if saved:
            enqueue_goal_push_events(con, **goal_push)
            con.commit()
    if not saved:
        return False
    quick_home_name = source_label(quick_match["home_source"])
    quick_away_name = source_label(quick_match["away_source"])
    description = f"{quick_home_name}–{quick_away_name} {home_score}–{away_score}"
    record_audit(
        tournament_id, "result", "match", description, entity_id=quick_match_id,
        before=before, after={"home_score": home_score, "away_score": away_score}, actor="Matchrapportör"
    )
    add_feed_item(tournament_id, f"Slut: {description}", category="Resultat", related_match_id=quick_match_id)
    for team_id in _match_team_ids(quick_match):
        add_team_notification(
            tournament_id, team_id, "Nytt resultat", description,
            event_key=f"result:{quick_match_id}:{home_score}:{away_score}",
        )
    return True


def _reporter_save_bulk_results(tournament_id, original_by_id, updates):
    """Persist bulk results without moving concurrency/write logic into the view."""
    for update in updates:
        match_for_push = original_by_id[update["match_id"]]
        update["_goal_push"] = _goal_push_kwargs(
            tournament_id, match_for_push, update["expected"], update["home_score"], update["away_score"]
        )
    saved_updates = []
    conflicts = []
    with db() as con:
        for update in updates:
            saved = update_match_result_if_unchanged(
                con, update["match_id"], update["expected"],
                home_score=update["home_score"], away_score=update["away_score"],
                home_penalties=update["home_penalties"], away_penalties=update["away_penalties"],
                decided_winner_id=update["decided_winner_id"], referee_id=update["referee_id"],
            )
            (saved_updates if saved else conflicts).append(update)
            if saved:
                enqueue_goal_push_events(con, **update["_goal_push"])
        con.commit()
    _clear_render_query_cache()
    for update in saved_updates:
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
            add_team_notification(
                tournament_id, team_id, "Nytt resultat", description,
                event_key=f"result:{changed_match_id}:{home_score}:{away_score}:{home_penalties}:{away_penalties}",
            )
    st.session_state["_validation_dirty"] = True
    return {"saved": len(saved_updates), "conflicts": len(conflicts)}


def _reporter_save_event_rows(changed_rows):
    """Persist player-event edits with the existing optimistic-locking helper."""
    saved_rows = []
    conflicted_rows = []
    with db() as con:
        for event_update in changed_rows:
            saved = update_player_match_stats_if_unchanged(
                con, event_update["match_id"], event_update["player_id"], event_update["expected"],
                goals=event_update["goals"], assists=event_update["assists"],
                yellow_cards=event_update["yellow_cards"], red_cards=event_update["red_cards"],
            )
            (saved_rows if saved else conflicted_rows).append(event_update)
        con.commit()
    _clear_render_query_cache()
    return {"saved": len(saved_rows), "conflicts": len(conflicted_rows)}


def _reporter_acknowledge_referee(tournament_id, referee_id, match_id):
    run(
        """INSERT INTO referee_acknowledgements(tournament_id,referee_id,match_id,acknowledged_at)
           VALUES(?,?,?,?) ON CONFLICT(referee_id,match_id) DO NOTHING""",
        (tournament_id, referee_id, match_id, datetime.now().isoformat(timespec="seconds")),
    )
    record_audit(
        tournament_id, "referee_ack", "match", "Domaruppdrag bekräftat",
        entity_id=match_id, actor="Domare",
    )


def render_match_reporter_view(tournament_id, tournament):
    """Thin app boundary: inject reads, labels and protected persistence callbacks."""
    render_match_reporter_workspace(
        tournament_id,
        tournament,
        MatchReporterWorkspaceDeps(
            query_all=all_rows,
            resolve_source=resolve_source,
            source_label=source_label,
            swedish_datetime=swedish_datetime,
            match_result_label=match_result_label,
            team=team,
            row_value=_row_value,
            translate=tr,
            render_empty_state=render_empty_state,
            save_quick_result=_reporter_save_quick_result,
            save_bulk_results=_reporter_save_bulk_results,
            save_event_rows=_reporter_save_event_rows,
            acknowledge_referee=_reporter_acknowledge_referee,
        ),
    )

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
                       published_once=1,
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
    deps = TeamPortalDependencies(
        all_rows=all_rows,
        one_row=one_row,
        participant_role_label=_participant_role_label,
        row_value=_row_value,
        team_value=_team_value,
        match_team_ids=_match_team_ids,
        portal_match_label=_portal_match_label,
        team_checkin_snapshot=_team_checkin_snapshot,
        set_team_checkin_if_unchanged=_set_team_checkin_if_unchanged,
        team_kit_snapshot=_team_kit_snapshot,
        confirm_team_kit_if_unchanged=_confirm_team_kit_if_unchanged,
        team_contact_snapshot=_team_contact_snapshot,
        save_team_contact_if_unchanged=_save_team_contact_if_unchanged,
        add_team_player_if_capacity=_add_team_player_if_capacity,
        player_display_name=_player_display_name,
        player_snapshot=_player_snapshot,
        update_team_player_if_unchanged=_update_team_player_if_unchanged,
        delete_team_player_if_unchanged=_delete_team_player_if_unchanged,
        save_match_roster_if_unchanged=_save_match_roster_if_unchanged,
        send_team_message=_send_team_message,
        mark_team_messages_read=_mark_team_messages_read,
        message_party_label=_message_party_label,
        record_audit=record_audit,
        kit_preview_html=kit_preview_html,
        swedish_datetime=swedish_datetime,
    )
    return render_team_portal_workspace(tournament_id, tournament, deps)



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
st.sidebar.caption(release_ui_label(APP_BUILD_VERSION))

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
        render_empty_state(
            "Skapa din första cup",
            "Öppna sidomenyn (☰ på mobil) och välj Skapa ny turnering. Du behöver bara namn, spelort, sport och cupdag för att komma igång.",
            symbol="🏆",
        )
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

# A direct public cup URL is authoritative in the public view. This prevents a
# stale session selection from silently rewriting ?cup= to another tournament.
# Admin/role views keep the deliberate selector behavior below.
if view_mode == "Turneringsvy" and requested_cup_id in tournament_ids:
    st.session_state["active_tournament_selector"] = int(requested_cup_id)
elif st.session_state.get("active_tournament_selector") not in tournament_ids:
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
    """Render the guided setup via the extracted presentation/orchestration layer."""
    return render_initial_tournament_setup_module(
        tournament_id,
        tournament,
        deps=InitialSetupDependencies(
            st=st,
            one_row=one_row,
            run=run,
            sport_setup_recommendation=sport_setup_recommendation,
            row_value=_row_value,
            cup_date_label=cup_date_label,
            add_competition_class=add_competition_class,
            competition_classes=competition_classes,
            all_rows=all_rows,
            competition_class_label=competition_class_label,
            sync_expected_team_count_from_classes=sync_expected_team_count_from_classes,
            remove_competition_class=remove_competition_class,
            autosave_rule_field=_autosave_rule_field,
            ensure_pitch_definitions=ensure_pitch_definitions,
            save_pitch_name=save_pitch_name,
            save_pitch_address=save_pitch_address,
            ensure_pitch_day_windows=ensure_pitch_day_windows,
            save_pitch_day_window=save_pitch_day_window,
            pitch_travel_matrix=pitch_travel_matrix,
            save_pitch_travel_time=save_pitch_travel_time,
            recommend_tournament_format=recommend_tournament_format,
            autosave_tournament_field=_autosave_tournament_field,
            render_centered_table=render_centered_table,
            db=db,
            clear_render_query_cache=_clear_render_query_cache,
            sort_items=sort_items,
            youth_class_categories=YOUTH_CLASS_CATEGORIES,
            youth_class_years=YOUTH_CLASS_YEARS,
            difficulty_levels=DIFFICULTY_LEVELS,
            date_with_weekday=date_with_weekday,
        ),
    )


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
    ("Deltagare", [("Lag", tr("Lag")), ("Önskemålscentral", "Önskemål"), ("Grupper", tr("Grupper")), ("Trupper", "Spelare & trupper"), ("Import", tr("Import"))]),
    ("Matcher", [("Skapa och publicera schema", tr("Schema")), ("Matcher och resultat", "Resultat"), ("Matchhändelser", tr("Händelser")), ("Tabeller", tr("Tabeller")), ("Slutspel", tr("Slutspel")), ("Skytteligor", tr("Skytteligor"))]),
    ("Organisation", [("Domare", tr("Domare")), ("Funktionärer", tr("Funktionärer")), ("Cupverktyg", "Verktyg")]),
    ("Kommunikation", [("Erbjudanden", tr("Erbjudanden")), ("Sponsorer", tr("Sponsorer")), ("Besöksstatistik", tr("Besök"))]),
]
ADMIN_NAV = [item for _, items in ADMIN_NAV_GROUPS for item in items]
admin_page_key = f"admin_page_{tid}"
if st.session_state.get(admin_page_key) not in ADMIN_PAGES:
    st.session_state[admin_page_key] = "Adminöversikt"

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

def _open_admin_search_hit(target_page, kind, entity_id, team_id=None):
    """Navigate from global search and carry the selected entity into its target view."""
    st.session_state[admin_page_key] = target_page
    st.session_state[admin_group_key] = _admin_group_for_page(target_page)
    st.session_state[f"admin_search_focus_kind_{tid}"] = kind
    st.session_state[f"admin_search_focus_entity_{tid}"] = int(entity_id)
    if team_id is not None:
        st.session_state[f"admin_search_focus_team_{tid}"] = int(team_id)
    else:
        st.session_state.pop(f"admin_search_focus_team_{tid}", None)
    # Clear the search field in the callback (before widgets are rebuilt) so the
    # user sees the destination rather than an apparently unchanged search panel.
    st.session_state[f"global_admin_search_{tid}"] = ""


with st.expander("Sök i cupen", expanded=False):
    global_query = st.text_input(
        "Sök lag/deltagare, spelare, domare eller matchnummer",
        key=f"global_admin_search_{tid}",
        placeholder="Exempel: ÖSK, Andersson eller 12",
    ).strip()
    if len(global_query) >= 2:
        like_query = f"%{global_query}%"
        _numeric_match = 1 if global_query.isdigit() else 0
        _match_no = int(global_query) if global_query.isdigit() else -1
        # v1.259: one search round-trip instead of 3–4 sequential queries on
        # every keystroke. Each category still has the same per-type ceiling.
        _search_rows = all_rows(
            """WITH
               team_hits AS (
                 SELECT 'Lag' AS kind, name AS label, 'Lag' AS target_page,
                        id AS entity_id, id AS team_id
                 FROM teams WHERE tournament_id=? AND name LIKE ? ORDER BY name LIMIT 8
               ),
               player_hits AS (
                 SELECT 'Spelare' AS kind, players.name || ' · ' || teams.name AS label,
                        'Trupper' AS target_page, players.id AS entity_id, players.team_id AS team_id
                 FROM players JOIN teams ON teams.id=players.team_id
                 WHERE teams.tournament_id=? AND players.name LIKE ?
                 ORDER BY players.name LIMIT 8
               ),
               referee_hits AS (
                 SELECT 'Domare' AS kind, name AS label, 'Domare' AS target_page,
                        id AS entity_id, NULL AS team_id
                 FROM referees WHERE tournament_id=? AND name LIKE ? ORDER BY name LIMIT 8
               ),
               match_hits AS (
                 SELECT 'Match' AS kind, 'Match ' || match_no || ' · ' || stage AS label,
                        'Matcher och resultat' AS target_page, id AS entity_id, NULL AS team_id
                 FROM matches
                 WHERE tournament_id=? AND ?=1 AND match_no=? ORDER BY id LIMIT 8
               )
               SELECT * FROM team_hits
               UNION ALL SELECT * FROM player_hits
               UNION ALL SELECT * FROM referee_hits
               UNION ALL SELECT * FROM match_hits
               LIMIT 24""",
            (tid, like_query, tid, like_query, tid, like_query, tid, _numeric_match, _match_no),
        )
        search_hits = [dict(row) for row in _search_rows]
        if search_hits:
            for hit_index, hit in enumerate(search_hits[:15]):
                hit_cols = st.columns([4, 1])
                hit_cols[0].markdown(
                    f"**{html.escape(hit['kind'])}:** {html.escape(str(hit['label']))}"
                )
                hit_cols[1].button(
                    "Öppna",
                    key=f"global_hit_{tid}_{hit_index}",
                    use_container_width=True,
                    on_click=_open_admin_search_hit,
                    args=(
                        hit["target_page"],
                        hit["kind"],
                        hit["entity_id"],
                        hit["team_id"],
                    ),
                )
        else:
            st.caption("Inga träffar i den aktiva cupen.")



admin_page = st.session_state[admin_page_key]
current_page_label = dict(ADMIN_NAV).get(admin_page, admin_page)

_flow_index = _primary_flow_index(admin_page)
_page_title, _page_copy = ADMIN_PAGE_COPY.get(admin_page, (current_page_label, "Administrera den här delen av cupen."))
# Flödesräknarna används bara på de sju primära cupstegen. Tidigare kördes
# den här femdelade COUNT-frågan även på sekundära adminsidor vid varje
# knapptryckning/navigation, vilket gav ett onödigt remote DB-varv.
_flow_counts = None
_flow_total = _flow_played = _flow_scheduled = 0
if _flow_index is not None:
    if admin_page == "Adminöversikt":
        # v1.260: Adminöversikten behöver fler räknare än flödeslisten. Hämta dem
        # i samma remote DB-roundtrip och återanvänd snapshoten längre ned.
        _now_iso = datetime.now().isoformat(timespec="seconds")
        _delayed_cutoff_iso = (datetime.now() - timedelta(minutes=90)).isoformat(timespec="seconds")
        _flow_counts = one_row(
            """SELECT
                 (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
                 (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
                 (SELECT COUNT(*) FROM players p JOIN teams t ON t.id=p.team_id WHERE t.tournament_id=?) AS players_n,
                 (SELECT COUNT(*) FROM referees WHERE tournament_id=?) AS refs_n,
                 (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n,
                 (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL) AS scheduled_n,
                 (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL) AS played_n,
                 (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND referee_id IS NULL) AS missing_refs_n,
                 (SELECT COUNT(*) FROM teams WHERE tournament_id=? AND COALESCE(checked_in,0)=0) AS unchecked_n,
                 (SELECT COUNT(*) FROM pitches WHERE tournament_id=?) AS pitches_n,
                 (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND schedule_published=1) AS published_n,
                 (SELECT COUNT(*) FROM player_match_stats s JOIN matches m ON m.id=s.match_id
                    WHERE m.tournament_id=? AND (s.goals>0 OR s.assists>0 OR s.yellow_cards>0 OR s.red_cards>0)) AS events_n,
                 (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start>?) AS upcoming_n,
                 (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND scheduled_start<=?
                    AND (home_score IS NULL OR away_score IS NULL)) AS missing_results_n,
                 (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND scheduled_start<?
                    AND (home_score IS NULL OR away_score IS NULL)) AS delayed_n""",
            (tid,tid,tid,tid,tid,tid,tid,tid,tid,tid,tid,tid,tid,_now_iso,tid,_now_iso,tid,_delayed_cutoff_iso),
        )
        _DERIVED_RENDER_CACHE[("admin-workflow-counts", int(tid))] = _flow_counts
    else:
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

if _flow_index is not None:
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
else:
    _recommended_page = _recommended_label = None

if _flow_index is not None and admin_page not in (_recommended_page, "Adminöversikt"):
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
sidebar_rules = one_row(
    """SELECT sr.*,
              (SELECT COUNT(*) FROM matches m WHERE m.tournament_id=sr.tournament_id AND m.scheduled_start IS NOT NULL) AS scheduled_n
       FROM schedule_rules sr WHERE sr.tournament_id=?""",
    (tid,),
)
if sidebar_rules is None:
    run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
    sidebar_rules = one_row(
        """SELECT sr.*,
                  (SELECT COUNT(*) FROM matches m WHERE m.tournament_id=sr.tournament_id AND m.scheduled_start IS NOT NULL) AS scheduled_n
           FROM schedule_rules sr WHERE sr.tournament_id=?""",
        (tid,),
    )

# Primärflödet har redan räknat schemalagda matcher. På sekundära sidor kommer
# samma värde från rules-snapshoten, utan ett extra DB-anrop.
sidebar_scheduled = _flow_scheduled if _flow_index is not None else int(_row_value(sidebar_rules, "scheduled_n", 0) or 0)

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


render_admin_publication_controls(
    tournament_id=tid,
    is_published=bool(tournament["is_published"]),
    published_once=bool(_row_value(tournament, "published_once", 0)),
    playoff_model_confirmed=bool(tournament["playoff_model_confirmed"]),
    scheduled_matches=sidebar_scheduled,
    schedule_dirty=bool(tournament["schedule_dirty"]),
    schedule_errors=sidebar_errors,
    schedule_warnings=sidebar_warnings,
    publish_now=_publish_tournament_now,
    unpublish_now=_unpublish_tournament_now,
)

# Cupens livscykel: publicerad -> pågår -> avslutad. Avslutad cup blir skrivskyddad
# i admin men ligger kvar publikt tills admin uttryckligen flyttar den till papperskorgen.
lifecycle_counts = fetch_lifecycle_match_counts(one_row, tid)
completion_state = build_completion_state(
    total=int(lifecycle_counts["total"] or 0) if lifecycle_counts else 0,
    played=int(lifecycle_counts["played"] or 0) if lifecycle_counts else 0,
    lifecycle=tournament_lifecycle,
)


def _admin_set_public_lifecycle(expected_lifecycle, new_lifecycle):
    return _set_lifecycle_if_current(
        tid,
        expected_lifecycle,
        new_lifecycle,
        expected_is_published=1,
    )


def _add_completed_cup_feed_item():
    add_feed_item(
        tid,
        "Cupen är avslutad",
        "Resultat och statistik finns kvar i CupNavi-historiken.",
        category="Cup",
    )


render_admin_lifecycle_controls(
    tournament_id=tid,
    lifecycle=tournament_lifecycle,
    is_published=bool(tournament["is_published"]),
    completion_state=completion_state,
    set_lifecycle=_admin_set_public_lifecycle,
    add_completion_feed_item=_add_completed_cup_feed_item,
)

def _demo_data_service():
    from cupnavi_core.demo_data_service import DemoDataDeps, DemoDataService

    return DemoDataService(
        DemoDataDeps(
            all_rows=all_rows,
            one_row=one_row,
            run=run,
            db=db,
            resolve_source=resolve_source,
            clear_render_query_cache=_clear_render_query_cache,
            is_test_environment=is_test_environment,
            ensure_tournament_day_windows=ensure_tournament_day_windows,
            ensure_pitch_day_windows=ensure_pitch_day_windows,
            create_all_group_matches=create_all_group_matches,
            ensure_playoffs_for_schedule=ensure_playoffs_for_schedule,
            generate_schedule=generate_schedule,
            add_feed_item=add_feed_item,
            rows_from_cursor=_rows_from_cursor,
        )
    )


def _demo_distribute_count(total, players):
    return _demo_data_service().distribute_count(total, players)


def _demo_write_match_stats(match_id, team_id, goals, con):
    return _demo_data_service().write_match_stats(match_id, team_id, goals, con)


def _demo_generate_group_results(tournament_id, *, fraction=1.0):
    return _demo_data_service().generate_group_results(tournament_id, fraction=fraction)


def _demo_generate_playoff_results(tournament_id, *, fraction=1.0):
    return _demo_data_service().generate_playoff_results(tournament_id, fraction=fraction)


def _demo_reset_results(tournament_id):
    return _demo_data_service().reset_results(tournament_id)


def _demo_apply_safe_schedule_capacity(tournament_id, tournament_row):
    return _demo_data_service().apply_safe_schedule_capacity(tournament_id, tournament_row)


def _demo_prepare_schedule(tournament_id):
    return _demo_data_service().prepare_schedule(tournament_id)


def _demo_apply_progress_level(tournament_id, level):
    return _demo_data_service().apply_progress_level(tournament_id, level)


def _admin_workflow_counts(tournament_id):
    # v1.279: query ownership lives in the repository module; app.py keeps only
    # the render-cache/performance boundary used by the current Streamlit run.
    cache_key = ("admin-workflow-counts", int(tournament_id))
    if cache_key in _DERIVED_RENDER_CACHE:
        _PERF["derived_hits"] += 1
        return _DERIVED_RENDER_CACHE[cache_key]
    result = fetch_admin_workflow_counts(one_row, int(tournament_id))
    _DERIVED_RENDER_CACHE[cache_key] = result
    return result



if admin_page == "Instruktioner":
    st.header("Instruktioner")
    st.caption("Följ cupen steg för steg. Guiden anpassas automatiskt efter turneringens aktuella status.")

    guide_counts = _admin_workflow_counts(tid)
    guide_expected = int(tournament["expected_team_count"] or 0)
    guide_scheduled = guide_counts["scheduled_n"]
    guide_published = guide_counts["published_n"]
    guide_events = guide_counts["events_n"]

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
    _v139_model = build_organizer_overview(
        _v139_counts,
        class_rows=_v139_class_rows,
        sidebar_rules=sidebar_rules,
        schedule_dirty=bool(tournament["schedule_dirty"]),
        published=bool(tournament["is_published"]),
    )
    _v139_classes = _v139_model["classes_n"]
    _v139_expected_total = _v139_model["expected_total"]
    _v139_steps = _v139_model["steps"]
    _v139_summary = _v139_model["summary"]
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
            st.caption(class_progress_caption(_v139_class_rows, _class_team_counts, competition_class_label))

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
    # v1.260: driftstatusen ingår i dashboard-snapshoten. Tidigare hämtades varje
    # matchrad över nätet och räknades i Python på varje Adminöversikt-rendering.
    _cc = build_control_status(_v139_counts, schedule_dirty=bool(tournament["schedule_dirty"]))
    with st.expander("Driftstatus", expanded=current_admin_mode == "live"):
        _cc_cols = st.columns(4)
        _cc_cols[0].metric("Kommande matcher", _cc["upcoming"])
        _cc_cols[1].metric("Resultat saknas", _cc["missing_results"])
        _cc_cols[2].metric("Kraftigt försenade", _cc["delayed"])
        _cc_cols[3].metric("Problem", _cc["problems"])
        if _cc["schedule_dirty"]:
            st.warning("Schemat behöver genereras om efter ändrade förutsättningar.")

    ux_counts = _v139_counts
    checkin_enabled = bool(_row_value(tournament, "enable_team_checkin", 1))
    ux_progress, ux_attention = build_progress_and_attention(
        ux_counts,
        schedule_dirty=bool(tournament["schedule_dirty"]),
        published=bool(tournament["is_published"]),
        checkin_enabled=checkin_enabled,
    )
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
    readiness = build_readiness(
        workflow_counts,
        expected_teams=expected_teams,
        schedule_dirty=bool(tournament["schedule_dirty"]),
    )
    teams_ready = readiness.teams_ready
    groups_ready = readiness.groups_ready
    players_ready = readiness.players_ready
    refs_ready = readiness.referees_ready
    schedule_ready = readiness.schedule_ready
    results_ready = readiness.results_ready

    st.markdown(
        build_status_cards_html(
            workflow_counts,
            expected_teams=expected_teams,
            published=bool(tournament["is_published"]),
            schedule_dirty=bool(tournament["schedule_dirty"]),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(build_workflow_html(workflow_counts, readiness), unsafe_allow_html=True)

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
        st.caption("Rådgivande analys av vila, matchtider och planbyten. Sportspecifika regler gäller alltid först.")
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
    next_step = recommend_next_step(
        readiness,
        workflow_counts,
        schedule_dirty=bool(tournament["schedule_dirty"]),
    )
    st.info(f"**{next_step.title}**\n\n{next_step.text}")
    st.button(
        next_step.title,
        key=f"dashboard_next_step_{tid}",
        use_container_width=True,
        on_click=_set_admin_page,
        args=(next_step.target,),
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
    st.caption("Ändra regler och planeringsförutsättningar i den guidade setupen.")
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
    _settings_rules=one_row("SELECT * FROM schedule_rules WHERE tournament_id=?",(tid,))
    _saved_gc=int(_row_value(_settings_rules,"recommended_group_count",0) or 0)
    with st.expander("Tävlingsprofil och rekommendation", expanded=False):
        st.write(
            f'**{_admin_sport_rec["display_name"]}** · '
            f'{_admin_sport_rec["periods"]} {_admin_sport_rec["period_label"]} × {_admin_sport_rec["minutes_per_period"]} min · '
            f'min. lagvila {_admin_sport_rec["minimum_rest_minutes"]} min.'
        )
        if _saved_gc:
            st.write(
                f"Rekommenderat format: **{_saved_gc} grupper** · cirka **{int(_row_value(_settings_rules,'recommended_group_size',0) or 0)} lag/grupp** · "
                f"**{int(_row_value(_settings_rules,'recommended_playoff_size',0) or 0)} lag i slutspel**."
            )
            st.caption("Rekommendationen är beslutsstöd och ändrar inte cupen automatiskt.")
        else:
            st.caption("Formatrekommendation visas när CupNavi har tillräckliga planeringsuppgifter.")

    _show_change_impact = st.toggle("Kontrollera konsekvens före större ändring", value=False, key=f"show_change_impact_{tid}")
    if _show_change_impact:
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
    _show_deep_controls = st.toggle("Fördjupad kontroll", value=False, key=f"show_deep_controls_{tid}")
    if _show_deep_controls:
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


    _show_technical_health = st.toggle("Visa teknisk hälsa och backup", value=False, key=f"show_technical_health_{tid}")
    if _show_technical_health:
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
    st.caption("Se vad som blockerar schemat och få förslag på minsta möjliga åtgärd.")
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

    _search_focus_kind = st.session_state.get(f"admin_search_focus_kind_{tid}")
    _search_focus_entity = st.session_state.get(f"admin_search_focus_entity_{tid}")
    if _search_focus_kind == "Lag" and _search_focus_entity:
        _focused_team = one_row(
            "SELECT * FROM teams WHERE tournament_id=? AND id=?",
            (tid, int(_search_focus_entity)),
        )
        if _focused_team:
            _focused_group = (
                one_row("SELECT name FROM groups WHERE id=? AND tournament_id=?", (_focused_team["group_id"], tid))
                if _focused_team["group_id"] is not None else None
            )
            with st.container(border=True):
                st.markdown(f"### 🔎 {html.escape(_focused_team['name'])}")
                st.caption("Öppnad från Sök i cupen")
                focus_cols = st.columns(3)
                focus_cols[0].metric("Tävlingsklass", _team_value(_focused_team, "age_class", "") or "–")
                focus_cols[1].metric("Grupp", _focused_group["name"] if _focused_group else "Ej placerad")
                focus_cols[2].metric("Spelare", one_row("SELECT COUNT(*) AS n FROM players WHERE team_id=?", (_focused_team["id"],))["n"])
                if st.button(
                    "Öppna lagets trupp",
                    key=f"search_focus_team_roster_{tid}_{_focused_team['id']}",
                    type="primary",
                ):
                    st.session_state[f"admin_search_focus_kind_{tid}"] = "Lag"
                    st.session_state[f"admin_search_focus_team_{tid}"] = int(_focused_team["id"])
                    st.session_state[admin_page_key] = "Trupper"
                    st.session_state[admin_group_key] = _admin_group_for_page("Trupper")
                    st.rerun()
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
    if registered_team_count:
        st.caption("Spelare registreras under **Deltagare → Spelare & trupper**.")
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

            st.markdown("#### Lagansvarig kontaktperson")
            st.caption("Ange den person som CupNavi/arrangören i första hand ska kontakta för laget, till exempel lagledare eller tränare. Uppgifterna är interna om du inte uttryckligen väljer att visa kontaktpersonen publikt.")
            rc1, rc2, rc3 = st.columns(3)
            responsible_name = rc1.text_input("Namn på lagansvarig", key=f"new_team_responsible_name_{tid}")
            responsible_phone = rc2.text_input("Telefon till lagansvarig", key=f"new_team_responsible_phone_{tid}")
            responsible_email = rc3.text_input("E-post till lagansvarig", key=f"new_team_responsible_email_{tid}")
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
        render_empty_state(
            "Inga deltagare ännu",
            "Lägg till första laget/deltagaren eller använd Import för flera på en gång.",
            symbol="👥",
        )

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
                original = {int(row["id"]): row for row in teams}
                now_iso = datetime.now().isoformat(timespec="seconds")
                changes = []
                for _, edited_row in edited_checkins.iterrows():
                    team_id = int(edited_row["team_id"])
                    new_value = 1 if bool(edited_row["På plats"]) else 0
                    old_value = int(original[team_id]["checked_in"] or 0)
                    if new_value != old_value:
                        changes.append((team_id, old_value, new_value, original[team_id]["name"]))

                if changes:
                    # Teamuppdateringar och audit skrivs i samma transaktion. Tidigare
                    # öppnade record_audit en ny anslutning + commit per ändrat lag, vilket
                    # gav tydlig väntetid mot Turso när flera lag checkades in samtidigt.
                    with db() as con:
                        for team_id, old_value, new_value, team_name in changes:
                            con.execute(
                                "UPDATE teams SET checked_in=?,checked_in_at=?,checked_in_by=? WHERE id=?",
                                (new_value, now_iso if new_value else None, "Admin" if new_value else None, team_id),
                            )
                            con.execute(
                                """INSERT INTO audit_log(
                                       tournament_id,created_at,actor,action_type,entity_type,entity_id,description,
                                       before_json,after_json,reversible
                                   ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                                (tid, now_iso, "Admin", "team_checkin", "team", team_id,
                                 f"{team_name}: {'incheckad' if new_value else 'incheckning borttagen'}",
                                 _json_snapshot({"checked_in": old_value}),
                                 _json_snapshot({"checked_in": new_value}), 0),
                            )
                        con.commit()
                    _clear_render_query_cache()
                    st.success(f"Incheckning uppdaterad för {len(changes)} lag.")
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

                st.markdown("#### Lagansvarig kontaktperson")
                st.caption("Personen som CupNavi/arrangören i första hand kontaktar för laget, till exempel lagledare eller tränare.")
                erc1, erc2, erc3 = st.columns(3)
                edited_responsible_name = erc1.text_input("Namn på lagansvarig", value=_team_value(edit_team, "responsible_name", "") or "", key=f"edit_responsible_name_{edit_team_id}")
                edited_responsible_phone = erc2.text_input("Telefon till lagansvarig", value=_team_value(edit_team, "responsible_phone", "") or "", key=f"edit_responsible_phone_{edit_team_id}")
                edited_responsible_email = erc3.text_input("E-post till lagansvarig", value=_team_value(edit_team, "responsible_email", "") or "", key=f"edit_responsible_email_{edit_team_id}")
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
            current_group_by_team = {int(t["id"]): t["group_id"] for t in teams}
            group_changes = []
            for container in sorted_containers:
                target_group = group_by_name.get(container["header"])
                for item in container["items"]:
                    selected_team_id = int(team_id_by_item[item])
                    if current_group_by_team.get(selected_team_id) != target_group:
                        group_changes.append((target_group, selected_team_id))

            if group_changes:
                with db() as con:
                    con.executemany("UPDATE teams SET group_id=? WHERE id=?", group_changes)
                    con.commit()
                _clear_render_query_cache()
                st.success(f"Gruppindelningen sparades för {len(group_changes)} lag.")
                st.rerun()
            else:
                st.info("Inga ändringar i gruppindelningen att spara.")
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
    st.header("Spelare & trupper")
    st.caption("Välj lag och hantera spelare manuellt eller via AI-import.")
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
        _roster_team_ids = [int(t["id"]) for t in teams]
        _focus_team_id = st.session_state.get(f"admin_search_focus_team_{tid}")
        _roster_selector_key = f"admin_roster_team_{tid}"
        if _focus_team_id in _roster_team_ids:
            st.session_state[_roster_selector_key] = int(_focus_team_id)
        elif st.session_state.get(_roster_selector_key) not in _roster_team_ids:
            st.session_state[_roster_selector_key] = _roster_team_ids[0]

        _team_name_by_id = {int(row["id"]): row["name"] for row in teams}
        team_id = st.selectbox(
            "Välj lag",
            _roster_team_ids,
            format_func=lambda x: _team_name_by_id.get(int(x), "Okänt lag"),
            key=_roster_selector_key,
        )

        # v1.259: AI-assisted roster import from old team sheets/screenshots.
        # Nothing is written until the admin has reviewed the extracted rows.
        with st.expander("✨ AI-import från foto eller skärmdump", expanded=False):
            st.caption(
                "Dra in en bild av en tidigare laglista eller laguppställning. "
                "CupNavi läser av spelarna med AI och låter dig granska allt innan import."
            )
            _ai_roster_key = f"ai_roster_rows_{tid}_{team_id}"
            _ai_model = setting("CUPNAVI_AI_ROSTER_MODEL") or "gpt-5.6-luna"
            _ai_api_key = setting("OPENAI_API_KEY")
            _ai_files = st.file_uploader(
                "Dra hit foto/skärmdump",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key=f"ai_roster_upload_{tid}_{team_id}",
                help="Du kan dra in flera bilder om laglistan finns på flera sidor.",
            )
            st.caption(
                "När du väljer Läs av med AI skickas bilden till den konfigurerade AI-tjänsten. "
                "Kontrollera alltid namn och nummer innan du importerar."
            )
            if not _ai_api_key:
                st.info(
                    "AI-importen är förberedd men inte aktiverad. Lägg OPENAI_API_KEY i Streamlit Secrets "
                    "för att slå på bildavläsningen."
                )
            if st.button(
                "Läs av med AI",
                key=f"ai_roster_analyse_{tid}_{team_id}",
                type="primary",
                disabled=not bool(_ai_files) or not bool(_ai_api_key),
                use_container_width=True,
            ):
                _combined_ai_rows = []
                _seen_ai_names = set()
                try:
                    with st.spinner("Läser laglistan…"):
                        for _uploaded in _ai_files:
                            _mime = str(getattr(_uploaded, "type", None) or "image/png")
                            from cupnavi_core.ai_roster_import import extract_roster_from_image

                            _rows = extract_roster_from_image(
                                _uploaded.getvalue(),
                                _mime,
                                _ai_api_key,
                                model=_ai_model,
                            )
                            for _row in _rows:
                                _folded = str(_row.get("name") or "").strip().casefold()
                                if not _folded or _folded in _seen_ai_names:
                                    continue
                                _seen_ai_names.add(_folded)
                                _combined_ai_rows.append(_row)
                    st.session_state[_ai_roster_key] = _combined_ai_rows
                    if _combined_ai_rows:
                        st.success(f"Hittade {len(_combined_ai_rows)} spelare. Granska listan nedan.")
                    else:
                        st.warning("AI:n hittade inga säkra spelarrader i bilden.")
                except Exception as exc:
                    st.error(str(exc))

            _ai_rows = st.session_state.get(_ai_roster_key, [])
            if _ai_rows:
                from cupnavi_core.ai_roster_import import ALLOWED_POSITIONS

                _existing_names = {
                    str(row["name"]).strip().casefold()
                    for row in all_rows("SELECT name FROM players WHERE team_id=?", (team_id,))
                }
                _editor_source = pd.DataFrame([
                    {
                        "Importera": str(row.get("name") or "").strip().casefold() not in _existing_names,
                        "Spelare": row.get("name") or "",
                        "Tröjnummer": row.get("player_number"),
                        "Födelseår": row.get("birth_year"),
                        "Position": row.get("position") or "Ej angiven",
                    }
                    for row in _ai_rows
                ])
                _edited_ai = st.data_editor(
                    _editor_source,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="dynamic",
                    key=f"ai_roster_editor_{tid}_{team_id}",
                    column_config={
                        "Importera": st.column_config.CheckboxColumn("Importera"),
                        "Spelare": st.column_config.TextColumn("Spelare", required=True),
                        "Tröjnummer": st.column_config.NumberColumn("Tröjnummer", min_value=0, max_value=999, step=1),
                        "Födelseår": st.column_config.NumberColumn("Födelseår", min_value=1900, max_value=2100, step=1),
                        "Position": st.column_config.SelectboxColumn("Position", options=ALLOWED_POSITIONS),
                    },
                )
                _selected_ai = []
                _seen_selected = set(_existing_names)
                for _row in _edited_ai.to_dict("records"):
                    if not bool(_row.get("Importera")):
                        continue
                    _name = " ".join(str(_row.get("Spelare") or "").strip().split())
                    _folded = _name.casefold()
                    if not _name or _folded in _seen_selected:
                        continue
                    _seen_selected.add(_folded)
                    def _editor_int(value, minimum, maximum):
                        if value is None or pd.isna(value):
                            return None
                        try:
                            number = int(value)
                        except (TypeError, ValueError):
                            return None
                        return number if minimum <= number <= maximum else None
                    _selected_ai.append((
                        int(team_id),
                        _editor_int(_row.get("Tröjnummer"), 0, 999),
                        _name,
                        _editor_int(_row.get("Födelseår"), 1900, 2100),
                        _row.get("Position") if _row.get("Position") in ALLOWED_POSITIONS else "Ej angiven",
                    ))

                if _existing_names:
                    _duplicate_count = sum(
                        1 for row in _editor_source.to_dict("records")
                        if str(row.get("Spelare") or "").strip().casefold() in _existing_names
                    )
                    if _duplicate_count:
                        st.caption(f"{_duplicate_count} redan registrerade spelare är avmarkerade automatiskt.")

                if st.button(
                    f"Importera {len(_selected_ai)} spelare till {_team_name_by_id[int(team_id)]}",
                    key=f"ai_roster_import_{tid}_{team_id}",
                    type="primary",
                    disabled=not bool(_selected_ai),
                    use_container_width=True,
                ):
                    run_many(
                        "INSERT INTO players(team_id,player_number,name,birth_year,position) VALUES(?,?,?,?,?)",
                        _selected_ai,
                    )
                    record_audit(
                        tid,
                        "ai_roster_imported",
                        "team",
                        f"AI-importerade {len(_selected_ai)} spelare till {_team_name_by_id[int(team_id)]}",
                        entity_id=int(team_id),
                        actor="Admin",
                    )
                    st.session_state.pop(_ai_roster_key, None)
                    st.success(f"{len(_selected_ai)} spelare importerades.")
                    st.rerun()

        _focus_kind = st.session_state.get(f"admin_search_focus_kind_{tid}")
        _focus_entity = st.session_state.get(f"admin_search_focus_entity_{tid}")
        if _focus_kind == "Spelare" and _focus_entity:
            _focused_player = one_row(
                "SELECT id,name,player_number FROM players WHERE id=? AND team_id=?",
                (int(_focus_entity), int(team_id)),
            )
            if _focused_player:
                number_text = (
                    f"#{_focused_player['player_number']} · "
                    if _focused_player["player_number"] is not None else ""
                )
                st.success(
                    f"🔎 Öppnad från sökningen: {number_text}{_focused_player['name']}"
                )
        elif _focus_team_id == team_id:
            st.caption("🔎 Laget öppnades från Sök i cupen.")

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
        _player_by_id = {int(row["id"]): row for row in players}
        render_centered_table(pd.DataFrame([{"Nr": p["player_number"], "Spelare": p["name"], "Födelseår": p["birth_year"], "Position": p["position"]} for p in players]))

        _show_admin_match_rosters = st.toggle(
            "Visa matchtrupper – admin",
            value=False,
            key=f"show_admin_match_rosters_{tid}_{team_id}",
            help="Laddas först när verktyget öppnas för att hålla Trupper-sidan snabb.",
        )
        if _show_admin_match_rosters:
            _team_token = f"team:{int(team_id)}"
            admin_team_matches = all_rows(
                """SELECT * FROM matches
                   WHERE tournament_id=? AND scheduled_start IS NOT NULL
                     AND (home_source=? OR away_source=?)
                   ORDER BY scheduled_start,id""",
                (tid, _team_token, _team_token),
            )
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
                    format_func=lambda pid: (
                        f"#{_player_by_id[int(pid)]['player_number'] if _player_by_id[int(pid)]['player_number'] is not None else '–'} "
                        f"{_player_by_id[int(pid)]['name']}"
                    ) if int(pid) in _player_by_id else "Okänd spelare",
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

    _focus_kind = st.session_state.get(f"admin_search_focus_kind_{tid}")
    _focus_entity = st.session_state.get(f"admin_search_focus_entity_{tid}")
    if _focus_kind == "Domare" and _focus_entity:
        _focused_referee = one_row(
            "SELECT * FROM referees WHERE tournament_id=? AND id=?",
            (tid, int(_focus_entity)),
        )
        if _focused_referee:
            with st.container(border=True):
                st.markdown(f"### 🔎 {html.escape(_focused_referee['name'])}")
                st.caption("Öppnad från Sök i cupen")
                if _focused_referee["phone"]:
                    st.write(f"Telefon: {_focused_referee['phone']}")
                if _focused_referee["email"]:
                    st.write(f"E-post: {_focused_referee['email']}")

    st.subheader("Åtkomstkoder")
    st.caption("Matchrapportör och domare har varsin fyrsiffrig kod för den aktiva cupen.")

    def _load_role_code_credential(table_name):
        return one_row(
            f"SELECT code_hash,created_at,rotated_at FROM {table_name} WHERE tournament_id=?",
            (tid,),
        )

    def _rotate_admin_role_code(table_name):
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
        return new_code

    code_col1, code_col2 = st.columns(2)
    with code_col1:
        render_role_code_card(
            st,
            "Matchrapportör",
            "match_reporter_credentials",
            "reporter",
            tid,
            _load_role_code_credential("match_reporter_credentials"),
            _rotate_admin_role_code,
        )
    with code_col2:
        render_role_code_card(
            st,
            "Domare",
            "referee_credentials",
            "referee",
            tid,
            _load_role_code_credential("referee_credentials"),
            _rotate_admin_role_code,
        )

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


def _undo_schedule_change(tournament_id, undo_rows):
    """Restore the exact pre-edit schedule snapshot used by the admin undo action."""
    with db() as con:
        con.executemany(
            "UPDATE matches SET scheduled_start=?,pitch_number=?,schedule_locked=?,schedule_published=? WHERE id=?",
            undo_rows,
        )
        con.execute(
            "UPDATE tournaments SET is_published=0,schedule_dirty=0 WHERE id=?",
            (tournament_id,),
        )
        con.commit()
    _clear_render_query_cache()


def _apply_drag_schedule_updates(tournament_id, updates):
    """Persist a drag-and-drop slot reassignment without changing schedule validation rules."""
    with db() as con:
        con.executemany(
            """UPDATE matches
               SET scheduled_start=?,pitch_number=?,schedule_locked=?,schedule_published=0
               WHERE id=?""",
            updates,
        )
        con.execute(
            "UPDATE tournaments SET is_published=0,schedule_dirty=0 WHERE id=?",
            (tournament_id,),
        )
        con.commit()
    _clear_render_query_cache()


def _save_adjusted_schedule_match(
    tournament_id,
    scheduled_start,
    pitch_number,
    referee_id,
    schedule_locked,
    match_id,
):
    """Persist one manual schedule adjustment and force republication."""
    run(
        "UPDATE matches SET scheduled_start=?,pitch_number=?,referee_id=?,schedule_locked=?,schedule_published=0 WHERE id=?",
        (
            scheduled_start,
            pitch_number,
            referee_id,
            int(schedule_locked),
            match_id,
        ),
    )
    run("UPDATE tournaments SET is_published=0 WHERE id=?", (tournament_id,))
    _clear_render_query_cache()


def _save_bulk_schedule_results(tournament_id, changed_scores, tournament_is_published):
    """Persist only changed schedule-table scores while preserving current publication semantics."""
    with db() as con:
        if tournament_is_published:
            for home_score, away_score, match_id in changed_scores:
                con.execute(
                    """UPDATE matches
                       SET home_score=?,away_score=?,
                           schedule_published=CASE WHEN scheduled_start IS NOT NULL THEN 1 ELSE schedule_published END
                       WHERE id=?""",
                    (home_score, away_score, match_id),
                )
        else:
            con.executemany(
                "UPDATE matches SET home_score=?,away_score=? WHERE id=?",
                changed_scores,
            )
        con.commit()
    _clear_render_query_cache()


if admin_page == "Skapa och publicera schema":
    render_schedule_workspace(
        tid,
        tournament,
        deps=ScheduleWorkspaceDependencies(
            st=st,
            one_row=one_row,
            run=run,
            all_rows=all_rows,
            validate_schedule=validate_schedule,
            playoff_specs_for_tournament=playoff_specs_for_tournament,
            schedule_score_report=schedule_score_report,
            schedule_request_label=schedule_request_label,
            render_schedule_recovery_actions=render_schedule_recovery_actions,
            optimize_group_home_away=optimize_group_home_away,
            ensure_playoffs_for_schedule=ensure_playoffs_for_schedule,
            generate_schedule=generate_schedule,
            create_all_group_matches=create_all_group_matches,
            schedule_recovery_context=_schedule_recovery_context,
            render_centered_table=render_centered_table,
            source_label=source_label,
            resolve_source=resolve_source,
            undo_schedule_change=_undo_schedule_change,
            schedule_board=schedule_board,
            swedish_datetime=swedish_datetime,
            apply_drag_schedule_updates=_apply_drag_schedule_updates,
            match_meta=match_meta,
            save_adjusted_schedule_match=_save_adjusted_schedule_match,
            pitch_name_map=pitch_name_map,
            team=team,
            match_kit_colors=match_kit_colors,
            kit_color_conflict=kit_color_conflict,
            kit_swatch=kit_swatch,
            save_bulk_schedule_results=_save_bulk_schedule_results,
            sort_items=sort_items,
            swedish_weekdays=SWEDISH_WEEKDAYS,
        ),
    )


if admin_page == "Matcher och resultat":
    def _save_admin_result_updates(auto_updates, original_match_by_id):
        for update in auto_updates:
            match_for_push = original_match_by_id[update["match_id"]]
            update["_goal_push"] = _goal_push_kwargs(
                tid, match_for_push, update["expected"],
                update["home_score"], update["away_score"],
            )

        saved_updates = []
        conflicted_updates = []
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
                (saved_updates if saved else conflicted_updates).append(update)
                if saved:
                    enqueue_goal_push_events(con, **update["_goal_push"])
            if tournament["is_published"] and saved_updates:
                con.executemany(
                    "UPDATE matches SET schedule_published=1 WHERE id=? AND scheduled_start IS NOT NULL",
                    [(int(update["match_id"]),) for update in saved_updates],
                )
            con.commit()

        _clear_render_query_cache()
        if conflicted_updates:
            st.session_state["bulk_result_conflict_message"] = (
                f"{len(conflicted_updates)} match(er) hade ändrats av en annan användare och skrevs inte över. "
                "CupNavi har laddat om de senaste värdena."
            )

        for update in saved_updates:
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
                add_team_notification(
                    tid, team_id, "Nytt resultat", description,
                    event_key=f"result:{changed_match_id}:{home_score}:{away_score}:{home_penalties}:{away_penalties}",
                )

        st.session_state["_validation_dirty"] = True
        st.session_state["bulk_result_message"] = (
            "✓ Sparat automatiskt"
            if not conflicted_updates
            else "✓ Övriga resultat sparades. Konflikter lämnades orörda."
        )
        st.rerun()

    render_admin_results_workspace(
        tid,
        tournament,
        deps=AdminResultsDependencies(
            st=st,
            all_rows=all_rows,
            match_result_label=match_result_label,
            portal_match_label=_portal_match_label,
            match_meta=match_meta,
            source_label=source_label,
            resolve_source=resolve_source,
            render_centered_table=render_centered_table,
            render_empty_state=render_empty_state,
            save_result_updates=_save_admin_result_updates,
        ),
    )


if admin_page == "Matchhändelser":
    def _save_admin_match_event_updates(*, match_id, team_id, updates):
        saved_event_rows = []
        conflicted_event_rows = []
        with db() as con:
            for event_update in updates:
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
        return {
            "saved_count": len(saved_event_rows),
            "conflict_count": len(conflicted_event_rows),
        }

    render_admin_match_events_workspace(
        tid,
        tournament,
        deps=AdminMatchEventsDependencies(
            st=st,
            all_rows=all_rows,
            resolve_source=resolve_source,
            match_result_label=match_result_label,
            team=team,
            row_value=_row_value,
            render_empty_state=render_empty_state,
            save_event_updates=_save_admin_match_event_updates,
        ),
    )


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
    st.caption("Importera lag eller spelare från CSV/Excel med automatisk kolumnmatchning.")

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
        from cupnavi_core.import_service import (
            TEAM_FIELDS, PLAYER_FIELDS, auto_map_columns,
            build_team_import_plan, build_player_import_plan,
        )

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
    st.caption("Verktyg för cupdagen, schemajusteringar och felsituationer.")

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



# --- CupNavi performance diagnostics ------------------------------------------
# One compact snapshot is recorded for every rerun. This gives us route-specific
# measurements instead of continuing to optimize from subjective impressions.
_cupnavi_run_seq = int(st.session_state.get("_cupnavi_run_seq", 0) or 0) + 1
st.session_state["_cupnavi_run_seq"] = _cupnavi_run_seq
_render_ms = round((time.perf_counter() - _APP_RENDER_STARTED) * 1000, 1)
_perf_snapshot = build_performance_snapshot(
    render_ms=_render_ms,
    perf=_PERF,
    view_mode=view_mode,
    admin_page=admin_page if view_mode == "Admin" else None,
    public_page=st.session_state.get("_cupnavi_current_public_page") if view_mode == "Turneringsvy" else None,
    run_seq=_cupnavi_run_seq,
    source_refreshed=SOURCE_PACKAGE_REFRESHED,
)
_perf_route_history = list(st.session_state.get("_cupnavi_perf_route_history", []))
_perf_route_history.append(_perf_snapshot)
st.session_state["_cupnavi_perf_route_history"] = _perf_route_history[-24:]
if os.environ.get("CUPNAVI_PERF_LOG") == "1":
    print(performance_log_line(_perf_snapshot), flush=True)

if view_mode == "Admin" and admin_page == "Adminöversikt":
    _db_ms = _perf_snapshot["db_ms"]
    _db_calls = _perf_snapshot["db_calls"]
    _writes = _perf_snapshot["writes"]
    _cache_hits = _perf_snapshot["query_cache_hits"]
    _derived_hits = _perf_snapshot["derived_cache_hits"]
    _db_share = _perf_snapshot["db_share_pct"]

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
            "Mäter aktuell rerendering och sparar de senaste rutterna i den här browser-sessionen. "
            "Inget skickas till en extern analystjänst."
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

        _route_history = list(st.session_state.get("_cupnavi_perf_route_history", []))
        if _route_history:
            st.markdown("**Senaste rutter**")
            _route_rows = [{
                "Vy": row["route"],
                "Render ms": row["render_ms"],
                "DB ms": row["db_ms"],
                "DB-anrop": row["db_calls"],
                "Fas": row["session_phase"],
            } for row in _route_history[-8:]]
            render_centered_table(pd.DataFrame(_route_rows))

        _public_matches_history = list(st.session_state.get("_cupnavi_public_matches_perf_history", []))
        if _public_matches_history:
            st.markdown("**Turneringsvy / Matcher – delsteg**")
            st.caption(
                "Visar vad som faktiskt tog tid i de senaste matchvyerna på samma browser-session. "
                "Det gör det möjligt att skilja DB/visitor/highlights/filter från själva matchkortsrenderingen."
            )
            _public_stage_rows = [{
                "Total ms": row.get("render_ms", 0),
                "Liveflöde": row.get("live_feed_ms", 0),
                "Översikt DB": row.get("overview_db_ms", 0),
                "Highlights": row.get("highlights_ms", 0),
                "Besökare": row.get("visitors_ms", 0),
                "Summering/dela": row.get("summary_share_ms", 0),
                "Filter": row.get("filters_ms", 0),
                "Händelser": row.get("events_ms", 0),
                "Matchkort/väder": row.get("cards_weather_ms", 0),
                "DB ms": row.get("db_ms", 0),
                "Matcher": row.get("visible_matches", 0),
            } for row in _public_matches_history[-6:]]
            render_centered_table(pd.DataFrame(_public_stage_rows))




inject_v198_visual_system()
