import sqlite3
import html
import base64
import hmac
import json
import os
import random
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

from cupnavi_core.version import APP_VERSION
from cupnavi_core.rules import validate_match_event_totals

try:
    from streamlit_sortables import sort_items
except ImportError:
    sort_items = None


st.set_page_config(page_title="Fotbollsturnering", page_icon="⚽", layout="wide")

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
          .stApp { min-height:100vh; }
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

          /* Publika st.tabs finns kvar men får ett enda tydligt färgsystem. */
          div[data-baseweb="tab-list"] {
            background:#F1F5F9 !important;
            border:1px solid #CBD5E1 !important;
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
# APP_VERSION centraliseras i cupnavi_core/version.py
DB_FILE = Path(__file__).with_name("turnering.db")


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
        submitted = st.form_submit_button("Logga in", type="primary", use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered_password, admin_password):
            # Form-submitten har redan startat den aktuella renderingen.
            # Fortsätt direkt till administrationen i samma körning i stället
            # för att tvinga fram ännu en full omladdning mot Turso.
            st.session_state["admin_authenticated"] = True
            return
        st.error("Fel lösenord.")
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


def init_db():
    # Schema/migreringar behöver inte köras om vid varje klick/rerun. Mot en
    # fjärrdatabas sparar detta många nätverksanrop, särskilt efter adminlogin.
    schema_key = f"{APP_VERSION}:{'cloud' if CLOUD_DATABASE_ENABLED else 'local'}"
    if st.session_state.get("_cupnavi_schema_ready") == schema_key:
        return
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
            CREATE TRIGGER cupnavi_dirty_team_update AFTER UPDATE OF group_id,distance_km,late_first_match,earliest_first_time ON teams
            WHEN OLD.group_id IS NOT NEW.group_id
              OR OLD.distance_km IS NOT NEW.distance_km
              OR OLD.late_first_match IS NOT NEW.late_first_match
              OR OLD.earliest_first_time IS NOT NEW.earliest_first_time
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
    st.session_state["_cupnavi_schema_ready"] = schema_key


# Cache endast under ett enskilt Streamlit-renderingsvarv. Den återställs vid rerun,
# så administratören ser alltid nya data efter en skrivning utan långlivad cache.
_RENDER_QUERY_CACHE = {}
_PERF = {"db_calls": 0, "db_ms": 0.0, "cache_hits": 0, "writes": 0}

def _record_db_call(started, write=False):
    _PERF["db_calls"] += 1
    _PERF["db_ms"] += (time.perf_counter() - started) * 1000
    if write:
        _PERF["writes"] += 1

def _cacheable_query(sql):
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


class TeamLimitReachedError(Exception):
    pass


def insert_team_with_limit(tournament_id, name, primary_color, secondary_color,
                           home_pattern, home_color_2, away_pattern, away_color_2,
                           distance_km, late_first_match, earliest_first_time, travel_note):
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
                distance_km,late_first_match,earliest_first_time,travel_note
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tournament_id, name, None, primary_color, secondary_color,
             home_pattern, home_color_2, away_pattern, away_color_2,
             distance_km, int(late_first_match), earliest_first_time, travel_note),
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
    teams = all_rows("SELECT * FROM teams WHERE group_id=? ORDER BY name", (group_id,))
    stats = {
        t["id"]: {"Lag": t["name"], "S": 0, "V": 0, "O": 0, "F": 0, "GM": 0, "IM": 0, "MS": 0, "P": 0}
        for t in teams
    }
    matches = all_rows(
        "SELECT * FROM matches WHERE group_id=? AND stage='Gruppspel' AND home_score IS NOT NULL AND away_score IS NOT NULL",
        (group_id,),
    )
    for m in matches:
        h = int(m["home_source"].split(":")[1])
        a = int(m["away_source"].split(":")[1])
        if h not in stats or a not in stats:
            continue
        hs, aas = int(m["home_score"]), int(m["away_score"])
        stats[h]["S"] += 1; stats[a]["S"] += 1
        stats[h]["GM"] += hs; stats[h]["IM"] += aas
        stats[a]["GM"] += aas; stats[a]["IM"] += hs
        if hs > aas:
            stats[h]["V"] += 1; stats[a]["F"] += 1
            stats[h]["P"] += tournament["points_win"]; stats[a]["P"] += tournament["points_loss"]
        elif hs < aas:
            stats[a]["V"] += 1; stats[h]["F"] += 1
            stats[a]["P"] += tournament["points_win"]; stats[h]["P"] += tournament["points_loss"]
        else:
            stats[h]["O"] += 1; stats[a]["O"] += 1
            stats[h]["P"] += tournament["points_draw"]; stats[a]["P"] += tournament["points_draw"]
    for row in stats.values():
        row["MS"] = row["GM"] - row["IM"]

    tiebreak = tournament.get("table_tiebreak", "Målskillnad först") if hasattr(tournament, "get") else tournament["table_tiebreak"]
    if not tiebreak:
        tiebreak = "Målskillnad först"

    # Grundsortering på poäng. Vid lika poäng kan användaren välja om målskillnad
    # eller inbördes möten ska väga tyngst.
    point_groups = {}
    for team_id, data in stats.items():
        point_groups.setdefault(data["P"], []).append(team_id)

    ordered_ids = []
    for points in sorted(point_groups.keys(), reverse=True):
        tied_ids = point_groups[points]
        if len(tied_ids) == 1:
            ordered_ids.extend(tied_ids)
            continue

        if tiebreak == "Inbördes möten först":
            h2h = {team_id: {"P": 0, "MS": 0, "GM": 0} for team_id in tied_ids}
            tied_set = set(tied_ids)
            for m in matches:
                h = int(m["home_source"].split(":")[1])
                a = int(m["away_source"].split(":")[1])
                if h not in tied_set or a not in tied_set:
                    continue
                hs, aas = int(m["home_score"]), int(m["away_score"])
                h2h[h]["GM"] += hs; h2h[h]["MS"] += hs - aas
                h2h[a]["GM"] += aas; h2h[a]["MS"] += aas - hs
                if hs > aas:
                    h2h[h]["P"] += tournament["points_win"]; h2h[a]["P"] += tournament["points_loss"]
                elif hs < aas:
                    h2h[a]["P"] += tournament["points_win"]; h2h[h]["P"] += tournament["points_loss"]
                else:
                    h2h[h]["P"] += tournament["points_draw"]; h2h[a]["P"] += tournament["points_draw"]
            tied_ids.sort(
                key=lambda team_id: (
                    -h2h[team_id]["P"], -h2h[team_id]["MS"], -h2h[team_id]["GM"],
                    -stats[team_id]["MS"], -stats[team_id]["GM"], stats[team_id]["Lag"].lower()
                )
            )
        else:
            tied_ids.sort(key=lambda team_id: (-stats[team_id]["MS"], -stats[team_id]["GM"], stats[team_id]["Lag"].lower()))
        ordered_ids.extend(tied_ids)

    return [(team_id, stats[team_id]) for team_id in ordered_ids]


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
    parts = source.split(":")
    if parts[0] == "team":
        return int(parts[1])
    if parts[0] == "group":
        group_id, rank = int(parts[1]), int(parts[2])
        if not group_table_is_final(group_id):
            return None
        tournament_id = one_row("SELECT tournament_id FROM groups WHERE id=?", (group_id,))["tournament_id"]
        tournament = one_row("SELECT * FROM tournaments WHERE id=?", (tournament_id,))
        table = calculate_table(group_id, tournament)
        return table[rank - 1][0] if 0 < rank <= len(table) else None
    if parts[0] in ("winner", "loser"):
        match_row = one_row("SELECT * FROM matches WHERE id=?", (int(parts[1]),))
        return result_winner(match_row, want_loser=parts[0] == "loser") if match_row else None
    return None


def source_label(source):
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


def match_meta(match_row):
    ordered = all_rows(
        "SELECT id FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
        (match_row["tournament_id"],),
    )
    match_number = next((index for index, row in enumerate(ordered, 1) if row["id"] == match_row["id"]), None)
    referee = one_row("SELECT name FROM referees WHERE id=?", (match_row["referee_id"],)) if match_row["referee_id"] else None
    if match_row["scheduled_start"]:
        start = swedish_datetime(match_row["scheduled_start"])
        schedule_text = f"Match {match_number} · {start} · Plan {match_row['pitch_number']}"
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


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather_forecast(place):
    """Hämta aktuell timprognos utan API-nyckel. Fel får aldrig stoppa Turneringsvyn."""
    if not place or not place.strip():
        return {}, "Spelort saknas"
    try:
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode({
            "name": place.strip(), "count": 1, "language": "sv", "format": "json",
        })
        request = Request(geocode_url, headers={"User-Agent": "Fotbollsturnering/1.0"})
        with urlopen(request, timeout=6) as response:
            geocode = json.load(response)
        results = geocode.get("results") or []
        if not results:
            return {}, f"Kunde inte hitta spelorten {place}."
        location = results[0]
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
    if not forecast or not scheduled_start:
        return None
    moment = datetime.fromisoformat(scheduled_start)
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


def _team_value(team_row, key, default=None):
    """Läs ett teamfält säkert från sqlite/libsql-rader och äldre data."""
    if not team_row:
        return default
    try:
        value = team_row[key]
    except Exception:
        value = default
    return default if value is None else value


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


def centered_table(dataframe):
    """Bakåtkompatibel hjälpare. Själva visningen görs av render_centered_table."""
    return dataframe


def render_centered_table(dataframe, empty_text="Ingen data att visa."):
    """Rendera en responsiv HTML-tabell med centrerade rubriker och celler."""
    if dataframe is None or dataframe.empty:
        st.info(empty_text)
        return

    table_html = dataframe.to_html(
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
    """Visa högst ett A- och ett B-slutspel även om äldre data innehåller dubbletter."""
    rows = all_rows("SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tournament_id,))
    regular = []
    selected = {}
    duplicates = []
    for bracket in rows:
        key = bracket["name"].strip().casefold()
        if key not in {"a-slutspel", "b-slutspel"}:
            regular.append(bracket)
            continue
        completed = one_row(
            "SELECT COUNT(*) AS n FROM matches WHERE bracket_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL",
            (bracket["id"],),
        )["n"]
        total = one_row("SELECT COUNT(*) AS n FROM matches WHERE bracket_id=?", (bracket["id"],))["n"]
        candidate = (completed, total, bracket["id"], bracket)
        if key not in selected or candidate[:3] > selected[key][:3]:
            if key in selected:
                duplicates.append(selected[key][3])
            selected[key] = candidate
        else:
            duplicates.append(bracket)
    visible = regular + [value[3] for value in selected.values()]
    return sorted(visible, key=lambda bracket: bracket["id"]), duplicates


def create_round_robin(tournament_id, group_id):
    team_ids = [r["id"] for r in all_rows("SELECT id FROM teams WHERE group_id=? ORDER BY id", (group_id,))]
    if len(team_ids) < 2:
        return 0
    existing = {
        tuple(sorted((int(m["home_source"].split(":")[1]), int(m["away_source"].split(":")[1]))))
        for m in all_rows("SELECT home_source, away_source FROM matches WHERE group_id=? AND stage='Gruppspel'", (group_id,))
    }
    created = 0
    match_no = len(existing) + 1
    for i, home in enumerate(team_ids):
        for away in team_ids[i + 1:]:
            if tuple(sorted((home, away))) in existing:
                continue
            run(
                "INSERT INTO matches(tournament_id,group_id,stage,match_no,home_source,away_source) VALUES(?,?,'Gruppspel',?,?,?)",
                (tournament_id, group_id, match_no, f"team:{home}", f"team:{away}"),
            )
            created += 1; match_no += 1
    return created


def create_all_group_matches(tournament_id):
    """Skapa alla saknade enkelmöten atomiskt med batchade databasfrågor."""
    groups = all_rows("SELECT id,name FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
    all_team_rows = all_rows(
        "SELECT id,group_id FROM teams WHERE tournament_id=? ORDER BY group_id,id",
        (tournament_id,),
    )
    all_existing_rows = all_rows(
        """SELECT group_id,home_source,away_source
           FROM matches
           WHERE tournament_id=? AND stage='Gruppspel'""",
        (tournament_id,),
    )

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
        with db() as con:
            con.executemany(
                "INSERT INTO matches(tournament_id,group_id,stage,match_no,home_source,away_source) VALUES(?,?,'Gruppspel',?,?,?)",
                pending,
            )
            con.commit()
        _clear_render_query_cache()
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


def sync_placement_playoffs(tournament_id, bronze_match):
    """Skapa platshållarmatcher automatiskt och behåll redan spelade slutspel orörda."""
    tournament = one_row("SELECT playoff_format FROM tournaments WHERE id=?", (tournament_id,))
    if not tournament or tournament["playoff_format"] != PLACEMENT_PLAYOFF_FORMAT:
        return False
    specs, error = placement_playoff_specs(tournament_id)
    if error:
        return False
    existing = all_rows("SELECT * FROM brackets WHERE tournament_id=? ORDER BY id", (tournament_id,))
    existing_signature = []
    for bracket in existing:
        first_round = all_rows(
            "SELECT home_source,away_source FROM matches WHERE bracket_id=? AND round_no=1 ORDER BY match_no",
            (bracket["id"],),
        )
        sources = [source for match_row in first_round for source in (match_row["home_source"], match_row["away_source"])]
        existing_signature.append((bracket["name"], bracket["size"], sources))
    desired_signature = [(name, size, sources) for name, size, sources in specs]
    if existing_signature == desired_signature:
        return False
    played = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL AND home_score IS NOT NULL",
        (tournament_id,),
    )["n"]
    if played:
        return False
    run("DELETE FROM brackets WHERE tournament_id=?", (tournament_id,))
    for bracket_name, bracket_size, bracket_sources in specs:
        create_bracket(tournament_id, bracket_name, bracket_size, bool(bronze_match) and bracket_size >= 4, bracket_sources)
    return True


def playoff_specs_for_tournament(tournament_id, tournament):
    """Returnera önskat slutspel utifrån den modell som valts på Adminöversikten."""
    fmt = tournament["playoff_format"]
    if fmt == "Inget slutspel":
        return [], ""
    if fmt == "A- och B-slutspel":
        groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
        if len(groups) != 2:
            return [], "A- och B-slutspel kräver exakt två grupper."
        counts = {
            group["id"]: one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?", (group["id"],))["n"]
            for group in groups
        }
        if any(counts[group["id"]] < 4 for group in groups):
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


def render_group_table(table_rows, tournament):
    """Text-TV-inspirerad grupptabell med tydlig markering av A/B-slutspelsplatser."""
    if not table_rows:
        st.info("Ingen tabelldata att visa.")
        return
    rows_html = []
    fmt = tournament["playoff_format"]
    for position, (_, data) in enumerate(table_rows, 1):
        qualifier = ""
        row_class = ""
        if fmt == "A- och B-slutspel":
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
        .texttv-table tr.qual-a{{background:rgba(22,163,74,.20)}}
        .texttv-table tr.qual-b{{background:rgba(37,99,235,.20)}}
        .qualifier{{display:inline-flex;width:24px;height:24px;align-items:center;justify-content:center;border-radius:4px;color:#fff;font-weight:900}}
        .qualifier.a,.texttv-legend i.a{{background:#16a34a}}
        .qualifier.b,.texttv-legend i.b{{background:#2563eb}}
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
    def schedule_source_id(source):
        if not source:
            return None
        if source.startswith("team:"):
            try:
                return int(source.split(":", 1)[1])
            except (TypeError, ValueError):
                return None
        return resolve_source(source)

    try:
        cup_start_date = tournament["start_date"] or tournament["tournament_date"]
        cup_end_date = tournament["end_date"] or cup_start_date
        start = datetime.fromisoformat(f"{cup_start_date}T{rules['first_match_time']}")
        end_date = datetime.fromisoformat(cup_end_date).date()
        latest_kickoff = datetime.strptime(rules["latest_kickoff_time"], "%H:%M").time()
    except (TypeError, ValueError):
        return 0, 0, "Turneringen måste ha giltiga cupdatum, första avspark och sista plantid."

    duration = timedelta(
        minutes=(rules["halves"] * rules["minutes_per_half"])
        + ((rules["halves"] - 1) * rules["halftime_minutes"])
    )
    playoff_extra_minutes = (
        int(tournament["extra_time_minutes"] or 0)
        if tournament.get("playoff_tie_rule", "") == "Förlängning + straffar"
        else 0
    )

    def duration_for_match(match_row):
        return duration + (timedelta(minutes=playoff_extra_minutes) if match_row["stage"] != "Gruppspel" else timedelta(0))

    def valid_daily_start_for(candidate, match_duration):
        candidate_end = candidate + match_duration
        day_limit = datetime.combine(candidate.date(), latest_kickoff)
        if candidate_end > day_limit:
            candidate = datetime.combine(candidate.date() + timedelta(days=1), start.time())
            candidate_end = candidate + match_duration
            day_limit = datetime.combine(candidate.date(), latest_kickoff)
        if candidate.date() > end_date or candidate_end > day_limit:
            return None
        return candidate

    def valid_daily_start(candidate):
        # latest_kickoff_time behålls som databasnamn för kompatibilitet, men värdet betyder sista plantid.
        # Matchen måste vara färdig innan planerna stänger.
        candidate_end = candidate + duration
        day_limit = datetime.combine(candidate.date(), latest_kickoff)
        if candidate_end > day_limit:
            candidate = datetime.combine(candidate.date() + timedelta(days=1), start.time())
            candidate_end = candidate + duration
            day_limit = datetime.combine(candidate.date(), latest_kickoff)
        if candidate.date() > end_date or candidate_end > day_limit:
            return None
        return candidate
    # Databasen ändras först när hela schemaläggningspasset är färdigberäknat.
    # Det minskar risken för ett halvuppdaterat schema om ett oväntat fel inträffar.
    schedule_updates = []
    pitch_gap = timedelta(minutes=rules["pitch_break_minutes"])
    avoid_consecutive = bool(rules["avoid_consecutive_matches"])
    consecutive_break = timedelta(minutes=rules["consecutive_match_break_minutes"] if avoid_consecutive else 0)
    pitch_ready = {pitch: start for pitch in range(1, rules["pitch_count"] + 1)}
    team_ready = {}
    team_last_end = {}
    referees = all_rows("SELECT id FROM referees WHERE tournament_id=? ORDER BY name", (tournament_id,))
    referee_ready = {r["id"]: start for r in referees}
    travel_preferences = {
        row["id"]: row
        for row in all_rows(
            "SELECT id,late_first_match,earliest_first_time FROM teams WHERE tournament_id=?",
            (tournament_id,),
        )
    }

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

    matches = all_rows(
        """
        SELECT * FROM matches WHERE tournament_id=?
        ORDER BY CASE stage
            WHEN 'Gruppspel' THEN 1 WHEN 'Kvartsfinal' THEN 2
            WHEN 'Semifinal' THEN 3 WHEN 'Bronsmatch' THEN 4 WHEN 'Final' THEN 5 ELSE 6 END,
            group_id, bracket_id, round_no, match_no
        """,
        (tournament_id,),
    )
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
        return valid_daily_start(candidate_start)
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
    last_scheduled_teams = set()
    forced_consecutive = 0
    while remaining:
        candidates = []
        for order, (match_row, home_id, away_id) in enumerate(remaining):
            for pitch in pitch_ready:
                consecutive_penalty = int(avoid_consecutive and bool({home_id, away_id} & last_scheduled_teams))
                basic_start = max(pitch_ready[pitch], team_ready.get(home_id, start), team_ready.get(away_id, start))
                basic_start = apply_first_match_preference(basic_start, home_id)
                basic_start = apply_first_match_preference(basic_start, away_id)
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
                        candidate_start = valid_daily_start_for(max(basic_start, referee_ready[referee_id]), match_duration)
                        candidate_start = move_past_locked(candidate_start, pitch, referee_id, home_id, away_id, match_duration) if candidate_start else None
                        if candidate_start:
                            candidates.append((candidate_start, consecutive_penalty, order, pitch, referee_id))
                else:
                    candidate_start = valid_daily_start_for(basic_start, match_duration)
                    candidate_start = move_past_locked(candidate_start, pitch, match_row["referee_id"], home_id, away_id, match_duration) if candidate_start else None
                    if candidate_start:
                        candidates.append((candidate_start, consecutive_penalty, order, pitch, match_row["referee_id"]))
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
                "Alla matcher fick inte plats inom cupens datumintervall och sista plantid. "
                f"Möjliga orsaker: {reason_text}."
            )
            break
        sort_key = (
            (lambda item: (item[1], item[0], item[2], item[3], item[4] or 0))
            if avoid_consecutive else
            (lambda item: (item[0], item[2], item[3], item[4] or 0))
        )
        match_start, consecutive_penalty, order, pitch, referee_id = min(candidates, key=sort_key)
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
                        candidate = valid_daily_start_for(max(base, referee_ready[referee_id]), match_duration)
                        if candidate:
                            candidates.append((candidate, pitch, referee_id))
                else:
                    candidate = valid_daily_start_for(base, match_duration)
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

    # Spara hela schemaläggningspasset i en enda transaktion.
    try:
        with db() as con:
            if not preserve_existing:
                con.execute("UPDATE tournaments SET is_published=0 WHERE id=?", (tournament_id,))
                con.execute("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (tournament_id,))
                con.execute(
                    "UPDATE matches SET scheduled_start=NULL,pitch_number=NULL WHERE tournament_id=? AND schedule_locked=0",
                    (tournament_id,),
                )
            if schedule_updates:
                con.executemany(
                    "UPDATE matches SET scheduled_start=?,pitch_number=?,referee_id=? WHERE id=?",
                    schedule_updates,
                )
            if unresolved == 0:
                con.execute("UPDATE tournaments SET schedule_dirty=0 WHERE id=?", (tournament_id,))
            con.commit()
    except Exception as exc:
        return 0, len(schedule_updates) + unresolved, f"Schemat kunde inte sparas och inga schemaändringar genomfördes: {exc}"

    return scheduled, unresolved, warning


def validate_schedule(tournament_id, tournament, rules):
    """Kontrollera schemat och sammanställ väntetid och belastning per lag."""
    rows = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
        (tournament_id,),
    )
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
        if start_at.time() < first_time:
            errors.append(f"Match {number} har avspark {start_at.strftime('%H:%M')} före första tillåtna avspark.")
        if (start_at + match_duration) > datetime.combine(start_at.date(), latest_time):
            errors.append(
                f"Match {number} slutar {(start_at + match_duration).strftime('%H:%M')}, efter sista plantid {latest_time.strftime('%H:%M')}."
            )
        if not match_row["pitch_number"] or not 1 <= match_row["pitch_number"] <= rules["pitch_count"]:
            errors.append(f"Match {number} har en ogiltig plan.")
        if rules["referee_mode"] == "Automatisk" and not match_row["referee_id"]:
            warnings.append(f"Match {number} saknar domare.")
        if kit_color_conflict(home_team, away_team):
            warnings.append(
                f"Färgkrock i match {number}: {away_team['name']} har fortfarande en färgkrock med hemmalaget även i sitt bortaställ. "
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
    main_stages = []
    for stage_name in ["Kvartsfinal", "Semifinal", "Final"]:
        stage_matches = [m for m in bracket_matches if m["stage"] == stage_name]
        if stage_matches:
            main_stages.append((stage_name, stage_matches))
    if not main_stages:
        st.info("Slutspelsträdet saknar matcher.")
        return

    card_width = 250
    card_height = 108
    column_gap = 92
    column_width = card_width + column_gap
    header_height = 48
    first_count = len(main_stages[0][1])
    play_height = max(330, first_count * 154)
    canvas_width = len(main_stages) * column_width - column_gap + 40
    canvas_height = header_height + play_height + 20

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
        home = team(home_id)
        away = team(away_id)
        home_name = html.escape(source_label(match_row["home_source"]))
        away_name = html.escape(source_label(match_row["away_source"]))
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
          .classic-bracket-scroll {{overflow-x:auto;padding:6px 3px 18px}}
          .classic-bracket {{position:relative;min-width:{canvas_width}px;height:{canvas_height}px;background:linear-gradient(180deg,#f8fafc 0,#fff 100%);border:1px solid #e2e8f0;border-radius:14px}}
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


def render_public_view(tournament_id, tournament):
    published_matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=1 ORDER BY scheduled_start,pitch_number,id",
        (tournament_id,),
    )
    played_matches = [m for m in published_matches if m["home_score"] is not None and m["away_score"] is not None]
    total_goals = sum(int(m["home_score"] or 0) + int(m["away_score"] or 0) for m in played_matches)
    team_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tournament_id,))["n"]
    now = datetime.now()
    next_match = next((m for m in published_matches if datetime.fromisoformat(m["scheduled_start"]) >= now and m["home_score"] is None), None)
    hero_meta = f"{cup_date_label(tournament)} · {html.escape(tournament['location'] or 'Spelort ej angiven')}"
    visitor_rows = []
    if tournament["arena_address"]:
        visitor_rows.append(f"<div><b>📍 Arena:</b> {html.escape(tournament['arena_address'])}</div>")
    if tournament["kiosk_information"]:
        kiosk_text = html.escape(tournament["kiosk_information"])
        visitor_rows.append(f"<div><b>☕ Kiosk:</b> {kiosk_text}</div>")
    else:
        visitor_rows.append("<div><b>☕ Kiosk:</b> Ingen kiosk har angetts.</div>")
    if tournament["public_information"]:
        public_text = html.escape(tournament["public_information"]).replace("\n", "<br>")
        visitor_rows.append(f"<div><b>ℹ️ Information:</b><br>{public_text}</div>")
    schedule, tables, statistics, playoffs, information = st.tabs(
        ["Spelschema", "Tabeller", "Topplistor", "Slutspel", "Information"]
    )
    with schedule:
        st.markdown(
            f"""<div class='cup-hero'><div class='eyebrow'>CupNavi · Turneringsöversikt</div>
            <div class='title'>{html.escape(tournament['name'])}</div><div class='meta'>{hero_meta}</div></div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""<div class='public-metric-grid'>
              <div class='public-metric'><div class='label'>Lag</div><div class='value'>{team_count}</div></div>
              <div class='public-metric'><div class='label'>Matcher</div><div class='value'>{len(published_matches)}</div></div>
              <div class='public-metric'><div class='label'>Spelade</div><div class='value'>{len(played_matches)}</div></div>
              <div class='public-metric'><div class='label'>Gjorda mål</div><div class='value'>{total_goals}</div></div>
            </div>""",
            unsafe_allow_html=True,
        )
        if next_match:
            st.caption(f"Nästa match: {swedish_datetime(next_match['scheduled_start'])} · Plan {next_match['pitch_number']}")
        st.markdown(
            """
            <style>
              .public-match-card,
              .public-match-card div,
              .public-match-card span,
              .public-match-card b { color:#172033 !important; }
              .public-match-card .match-stage { color:#ffffff !important; }
              .public-match-card .match-meta { color:#334155 !important; }
              .public-match-card .kit-label,
              .public-match-card .match-referee,
              .public-match-card .match-weather { color:#475569 !important; }
              .public-match-card .match-score { color:#0f172a !important; }
              .public-match-card .public-team-name { font-size:18px !important;line-height:1.25;font-weight:800; }
              .public-match-card .color-conflict { color:#9a3412 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        matches = published_matches
        referees = {r["id"]: r["name"] for r in all_rows("SELECT * FROM referees WHERE tournament_id=?", (tournament_id,))}
        weather_forecast, weather_status = fetch_weather_forecast(tournament["location"] or "")
        if not matches:
            draft_count = one_row(
                "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=0",
                (tournament_id,),
            )["n"]
            if draft_count:
                st.info(f"Spelschemat är framtaget men väntar på administratörens godkännande ({draft_count} matcher i utkast).")
            else:
                st.info("Inga matcher har schemalagts och publicerats ännu.")
        for number, match_row in enumerate(matches, 1):
            home = team(resolve_source(match_row["home_source"]))
            away = team(resolve_source(match_row["away_source"]))
            home_name = home["name"] if home else source_label(match_row["home_source"])
            away_name = away["name"] if away else source_label(match_row["away_source"])
            start = swedish_datetime(match_row["scheduled_start"])
            match_weather = weather_for_match(weather_forecast, match_row["scheduled_start"])
            weather_text = weather_label(match_weather) if weather_forecast else weather_status
            score = "Ej spelad" if match_row["home_score"] is None else f"{match_row['home_score']}–{match_row['away_score']}"
            if match_row["home_penalties"] is not None:
                score += f" ({match_row['home_penalties']}–{match_row['away_penalties']} str.)"
            home_primary, away_match_color, away_kit_used = match_kit_colors(home, away)
            home_kit_bg = kit_background_for_team(home, "home") if home else "#94a3b8"
            away_selected_kit = "away" if away_kit_used else "home"
            away_kit_bg = kit_background_for_team(away, away_selected_kit) if away else "#94a3b8"
            match_start_dt = datetime.fromisoformat(match_row["scheduled_start"])
            if match_row["home_score"] is not None and match_row["away_score"] is not None:
                status_text, status_class = "SLUT", "status-finished"
            elif match_start_dt <= now <= match_start_dt + timedelta(hours=2):
                status_text, status_class = "PÅGÅR", "status-live"
            else:
                status_text, status_class = "KOMMANDE", "status-upcoming"
            color_conflict_html = ""
            if kit_color_conflict(home, away):
                color_conflict_html = (
                    f"<div style='margin-top:10px;padding:7px 10px;border-radius:7px;background:#fff7ed;border:1px solid #fb923c;"
                    f"color:#9a3412;font-size:12px;font-weight:700'>⚠ Färgkrock: även {html.escape(away_name)}s andra tröjfärg krockar. Ett ytterligare avvikande ställ krävs.</div>"
                )
            elif away_kit_used:
                color_conflict_html = (
                    f"<div style='margin-top:10px;padding:7px 10px;border-radius:7px;background:#eff6ff;border:1px solid #93c5fd;"
                    f"color:#1e3a8a;font-size:12px;font-weight:700'>{html.escape(away_name)} använder sitt bortaställ på grund av färgkrock.</div>"
                )
            st.markdown(
                f"""
                <div class="public-match-card" style="border:1px solid #d1d5db;border-radius:14px;padding:16px;margin:12px 0;background:linear-gradient(135deg,#ffffff,#f3f6fb);color:#172033;box-shadow:0 4px 12px rgba(15,23,42,.08)">
                  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e5e7eb;padding-bottom:9px">
                    <div style="display:flex;gap:7px;align-items:center"><span class="match-stage" style="font-size:12px;font-weight:700;color:#fff;background:#166534;padding:4px 9px;border-radius:999px">{match_row['stage']}</span><span class="status-pill {status_class}">{status_text}</span></div>
                    <span class="match-meta" style="font-size:13px;color:#334155">Match {number} · <b>{start}</b> · Plan {match_row['pitch_number']}</span>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:15px;align-items:center;margin-top:8px;color:#0f172a">
                    <div style="color:#0f172a"><span style="display:inline-block;width:22px;height:15px;background:{home_kit_bg};border:1px solid #444;border-radius:3px"></span>
                    <b class="public-team-name" style="color:#0f172a">{home_name}</b><br><small class="kit-label" style="color:#475569">Hemmalagets hemmaställ</small></div>
                    <div class="match-score" style="font-size:20px;font-weight:700;color:#0f172a">{score}</div>
                    <div style="text-align:right;color:#0f172a"><b class="public-team-name" style="color:#0f172a">{away_name}</b> <span style="display:inline-block;width:22px;height:15px;background:{away_kit_bg};border:1px solid #444;border-radius:3px"></span>
                    <br><small class="kit-label" style="color:#475569">{'Bortalagets bortaställ' if away_kit_used else 'Bortalagets hemmaställ'}</small></div>
                  </div>
                  {color_conflict_html}
                  <div class="match-weather" style="font-size:12px;color:#475569;text-align:center;margin-top:10px">{html.escape(weather_text)}</div>
                  <div class="match-referee" style="font-size:12px;color:#475569;text-align:center;margin-top:10px">Domare: {referees.get(match_row['referee_id'], 'Ej tillsatt')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if matches:
            st.caption("Väderprognos från Open-Meteo. Prognosen uppdateras automatiskt och kan förändras.")
    with tables:
        groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tournament_id,))
        for group in groups:
            st.subheader(group["name"])
            group_table = calculate_table(group["id"], tournament)
            render_group_table(group_table, tournament)
    with statistics:
        rows = all_rows(
            """
            SELECT players.name AS player_name,teams.name AS team_name,
                   SUM(s.goals) AS goals,SUM(s.assists) AS assists,
                   SUM(s.yellow_cards) AS yellow_cards,SUM(s.red_cards) AS red_cards
            FROM player_match_stats s JOIN players ON players.id=s.player_id
            JOIN teams ON teams.id=players.team_id JOIN matches ON matches.id=s.match_id
            WHERE matches.tournament_id=? GROUP BY players.id,players.name,teams.name
            """,
            (tournament_id,),
        )
        st.subheader("Skytteliga")
        goal_rows = sorted(rows, key=lambda r: (-r["goals"], -r["assists"], r["player_name"].lower()))
        render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Mål": r["goals"]} for i, r in enumerate(goal_rows, 1) if r["goals"]]))
        st.subheader("Assistliga")
        assist_rows = sorted(rows, key=lambda r: (-r["assists"], -r["goals"], r["player_name"].lower()))
        render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Assist": r["assists"]} for i, r in enumerate(assist_rows, 1) if r["assists"]]))
    with playoffs:
        brackets = [] if tournament["playoff_format"] == "Inget slutspel" else brackets_for_display(tournament_id)[0]
        if not brackets:
            st.info("Turneringen har inget publicerat slutspel.")
        for bracket in brackets:
            st.subheader(bracket["name"])
            render_bracket_tree(bracket["id"], public=True)
    with information:
        st.subheader("Praktisk information")
        if visitor_rows:
            st.markdown(
                "<div class='public-information-card' style='padding:16px 18px;border:1px solid #cbd5e1;"
                "border-radius:12px;background:#f8fafc;color:#172033;display:grid;gap:12px;line-height:1.5'>"
                "<style>.public-information-card,.public-information-card div,.public-information-card b "
                "{color:#172033 !important}</style>" + "".join(visitor_rows) + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Ingen praktisk information har publicerats ännu.")

        st.divider()
        with st.expander("💬 Rapportera problem eller lämna synpunkt"):
            st.caption("Feedbacken sparas till den här turneringen och kan läsas av administratören.")
            with st.form(f"public_feedback_{tournament_id}", clear_on_submit=True):
                feedback_area = st.selectbox(
                    "Vad gäller det?",
                    ["Spelschema", "Tabeller", "Topplistor", "Slutspel", "Information", "Mobil/utseende", "Annat"],
                )
                feedback_message = st.text_area("Beskriv problemet eller synpunkten", max_chars=2000)
                feedback_contact = st.text_input("Kontaktuppgift (frivilligt)", max_chars=200)
                if st.form_submit_button("Skicka feedback"):
                    if not feedback_message.strip():
                        st.error("Skriv en kort beskrivning först.")
                    else:
                        run(
                            "INSERT INTO feedback(tournament_id,created_at,area,message,contact) VALUES(?,?,?,?,?)",
                            (tournament_id, datetime.now().isoformat(timespec="seconds"), feedback_area,
                             feedback_message.strip(), feedback_contact.strip() or None),
                        )
                        st.success("Tack. Feedbacken är sparad.")


init_db()


# SIDOMENY OCH TURNERING
st.sidebar.title("⚽ Turneringar")
st.sidebar.caption(f"CupNavi version {APP_VERSION}")
st.sidebar.caption("Databas: Turso" if CLOUD_DATABASE_ENABLED else "Databas: Lokal SQLite")
mode_options = ["Turneringsvy", "Admin"] if CLOUD_DATABASE_ENABLED else ["Admin", "Turneringsvy"]
if st.session_state.get("view_mode") not in mode_options:
    st.session_state["view_mode"] = mode_options[0]

# Ett gemensamt lägesval med vanliga Streamlit-knappar.
# on_click uppdaterar state före rerun, så markering och admininloggning
# alltid hänger ihop på första klicket.
def _set_view_mode(mode):
    st.session_state["view_mode"] = mode

st.caption("Välj läge")
mode_col1, mode_col2 = st.columns(2)
current_mode = st.session_state["view_mode"]
mode_col1.button(
    "Turneringsvy",
    key="view_mode_public_button",
    type="primary" if current_mode == "Turneringsvy" else "secondary",
    use_container_width=True,
    on_click=_set_view_mode,
    args=("Turneringsvy",),
)
mode_col2.button(
    "Admin",
    key="view_mode_admin_button",
    type="primary" if current_mode == "Admin" else "secondary",
    use_container_width=True,
    on_click=_set_view_mode,
    args=("Admin",),
)
view_mode = st.session_state["view_mode"]

st.sidebar.caption(f"Visningsläge: {view_mode}")

if view_mode == "Admin":
    require_admin_access()
    with st.sidebar.expander("Skapa ny turnering"):
        with st.form("new_tournament", clear_on_submit=True):
            n = st.text_input("Namn")
            place = st.text_input("Spelort")
            start_date = st.date_input("Första cupdag")
            end_date = st.date_input("Sista cupdag", value=start_date)
            expected_teams = st.number_input("Planerat antal lag", 2, 500, 8)
            st.caption("Poängregler och övriga cupinställningar görs på Adminöversikt efter att turneringen har skapats.")
            if st.form_submit_button("Skapa", type="primary", use_container_width=True):
                if not n.strip():
                    st.error("Ange ett namn.")
                elif end_date < start_date:
                    st.error("Sista cupdagen får inte ligga före första cupdagen.")
                else:
                    run(
                        """INSERT INTO tournaments(name,location,tournament_date,start_date,end_date,expected_team_count,points_win,points_draw,points_loss)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (n.strip(), place.strip(), start_date.isoformat(), start_date.isoformat(), end_date.isoformat(), expected_teams, 3, 1, 0),
                    )
                    st.rerun()

if view_mode == "Admin":
    tournaments = all_rows("SELECT * FROM tournaments ORDER BY COALESCE(start_date,tournament_date) DESC,name")
else:
    tournaments = all_rows("SELECT * FROM tournaments WHERE is_published=1 ORDER BY COALESCE(start_date,tournament_date) DESC,name")

if not tournaments:
    st.title("⚽ Fotbollsturnering")
    st.markdown(
        f"<div class='cup-version-badge'>KÖR VERSION {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )
    if view_mode == "Admin":
        st.info("Skapa den första turneringen i vänstermenyn.")
    else:
        st.info("Ingen turnering är publicerad ännu.")
    st.stop()

tid = st.sidebar.selectbox("Aktiv turnering", [t["id"] for t in tournaments], format_func=lambda x: next(t["name"] for t in tournaments if t["id"] == x))
tournament = next(t for t in tournaments if t["id"] == tid)

if view_mode == "Admin":
    st.title(f"⚽ {tournament['name']}")
    st.markdown(
        f"<div class='cup-version-badge'>KÖR VERSION {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"{tournament['location'] or 'Spelort saknas'} · {cup_date_label(tournament)} · Planerat antal lag: {tournament['expected_team_count'] or 'Ej angivet'}")
else:
    st.markdown(
        f"<div class='cup-version-badge'>KÖR VERSION {APP_VERSION}</div>",
        unsafe_allow_html=True,
    )

if view_mode == "Turneringsvy":
    render_public_view(tid, tournament)
    st.stop()

# SNABB ADMINNAVIGERING: visuellt som flikar, men bara vald sida körs.
ADMIN_PAGES = [
    "Adminöversikt", "Kontroller", "Lag", "Grupper", "Trupper", "Domare",
    "Skapa och publicera schema", "Tabeller", "Matcher och resultat",
    "Matchhändelser", "Slutspel", "Skytteligor",
]
ADMIN_NAV = [
    ("Adminöversikt", "Översikt"),
    ("Kontroller", "Kontroller"),
    ("Lag", "Lag"),
    ("Grupper", "Grupper"),
    ("Trupper", "Trupper"),
    ("Domare", "Domare"),
    ("Skapa och publicera schema", "Schema"),
    ("Tabeller", "Tabeller"),
    ("Matcher och resultat", "Matcher"),
    ("Matchhändelser", "Händelser"),
    ("Slutspel", "Slutspel"),
    ("Skytteligor", "Skytteligor"),
]
admin_page_key = f"admin_page_{tid}"
if st.session_state.get(admin_page_key) not in ADMIN_PAGES:
    st.session_state[admin_page_key] = "Adminöversikt"

st.markdown("### Administration")
st.caption("Välj administrationsdel. Endast den valda delen laddas, för snabbare webbdrift.")

def _set_admin_page(page):
    st.session_state[admin_page_key] = page

# Vanliga Streamlit-knappar används med aktiv/inaktiv typ.
# Två rader à sex val ger tydlig kontrast och fungerar på både desktop och mobil.
for nav_row in (ADMIN_NAV[:6], ADMIN_NAV[6:]):
    nav_cols = st.columns(len(nav_row))
    for nav_col, (page_name, button_label) in zip(nav_cols, nav_row):
        nav_col.button(
            button_label,
            key=f"admin_nav_v29_{tid}_{page_name}",
            type="primary" if st.session_state[admin_page_key] == page_name else "secondary",
            use_container_width=True,
            on_click=_set_admin_page,
            args=(page_name,),
        )

admin_page = st.session_state[admin_page_key]
st.divider()

current_schedule_state = one_row(
    "SELECT schedule_dirty,(SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL) AS scheduled_n "
    "FROM tournaments WHERE id=?",
    (tid, tid),
)
if current_schedule_state and current_schedule_state["schedule_dirty"] and current_schedule_state["scheduled_n"]:
    st.warning(
        "⚠️ Förutsättningarna för turneringen har ändrats efter att schemat skapades. "
        "Schemat är markerat som inaktuellt och bör regenereras under Schema innan det publiceras på nytt."
    )

publication_pages = {"Adminöversikt", "Kontroller", "Skapa och publicera schema"}
sidebar_rules = None
sidebar_scheduled = 0
sidebar_errors, sidebar_warnings, _sidebar_quality = ([], [], [])
if admin_page in publication_pages:
    sidebar_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    if sidebar_rules is None:
        run("INSERT INTO schedule_rules(tournament_id) VALUES(?)", (tid,))
        sidebar_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?", (tid,))
    sidebar_scheduled = one_row(
        "SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL",
        (tid,),
    )["n"]
    validation_cache_key = f"_schedule_validation_{tid}"
    if st.session_state.get("_validation_dirty", True) or validation_cache_key not in st.session_state:
        if admin_page in {"Kontroller", "Skapa och publicera schema"}:
            st.session_state[validation_cache_key] = validate_schedule(tid, tournament, sidebar_rules)
            st.session_state["_validation_dirty"] = False
    sidebar_errors, sidebar_warnings, _sidebar_quality = st.session_state.get(validation_cache_key, ([], [], []))

st.sidebar.divider()
st.sidebar.subheader("Publicering")
if tournament["is_published"]:
    st.sidebar.success("Publicerad")
else:
    st.sidebar.caption("Turneringsvyn är ett utkast.")
if admin_page not in publication_pages:
    st.sidebar.caption("Publicering hanteras under Översikt, Kontroller eller Schema.")
    sidebar_warnings_approved = False
    sidebar_publish_blocked = True
else:
    sidebar_warnings_approved = st.sidebar.checkbox(
        "Jag har granskat schemavarningarna",
        disabled=not sidebar_warnings,
        key=f"sidebar_warning_approval_{tid}",
    )
    sidebar_publish_blocked = (
        not sidebar_scheduled
        or bool(sidebar_errors)
        or bool(tournament["schedule_dirty"])
        or (bool(sidebar_warnings) and not sidebar_warnings_approved)
    )

if admin_page in publication_pages and st.sidebar.button("Publicera", type="primary", use_container_width=True, disabled=sidebar_publish_blocked):
    with db() as con:
        con.execute("UPDATE matches SET schedule_published=1 WHERE tournament_id=? AND scheduled_start IS NOT NULL", (tid,))
        con.execute("UPDATE tournaments SET is_published=1 WHERE id=?", (tid,))
        con.commit()
    st.rerun()
if admin_page in publication_pages and st.sidebar.button("Avpublicera", use_container_width=True, disabled=not tournament["is_published"]):
    run("UPDATE tournaments SET is_published=0 WHERE id=?", (tid,))
    st.rerun()
if admin_page in publication_pages:
    if not sidebar_scheduled:
        st.sidebar.caption("Skapa spelschemat innan publicering.")
    elif tournament["schedule_dirty"]:
        st.sidebar.caption("Schemat är inaktuellt efter ändrade förutsättningar. Regenerera det före publicering.")
    elif sidebar_errors:
        st.sidebar.caption(f"Åtgärda {len(sidebar_errors)} schemafel före publicering.")
    elif sidebar_warnings and not sidebar_warnings_approved:
        st.sidebar.caption("Godkänn varningarna före publicering.")

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


def _demo_generate_group_results(tournament_id):
    """Slumpa resultat och matchhändelser för alla gruppspelsmatcher."""
    group_matches = all_rows(
        """SELECT * FROM matches
           WHERE tournament_id=? AND stage='Gruppspel'
           ORDER BY COALESCE(scheduled_start,''),group_id,match_no,id""",
        (tournament_id,),
    )
    if not group_matches:
        return 0, 0, "Inga gruppspelsmatcher finns ännu. Generera spelschemat först."

    generated = 0
    stat_rows = 0
    with db() as con:
        for match_row in group_matches:
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


def _demo_generate_playoff_results(tournament_id):
    """Slumpa slutspelsresultat i spelordning så vinnare går vidare till nästa match."""
    playoff_matches = all_rows(
        """SELECT * FROM matches
           WHERE tournament_id=? AND stage<>'Gruppspel'
           ORDER BY round_no,match_no,id""",
        (tournament_id,),
    )
    if not playoff_matches:
        return 0, 0, "Inga slutspelsmatcher finns ännu. Generera spelschemat först."

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



if admin_page == "Adminöversikt":
    st.header("Adminöversikt")
    st.caption("Här ställer du in cupens grunduppgifter, poängregler, slutspelsformat och regler för schemaläggningen.")
    overview_counts = one_row(
        """SELECT
             (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
             (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
             (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n""",
        (tid, tid, tid),
    )
    overview_team_count = overview_counts["teams_n"]
    overview_group_count = overview_counts["groups_n"]
    overview_match_count = overview_counts["matches_n"]
    om1, om2, om3, om4 = st.columns(4)
    om1.metric("Registrerade lag", overview_team_count)
    om2.metric("Grupper", overview_group_count)
    om3.metric("Matcher", overview_match_count)
    om4.metric("Status", "Publicerad" if tournament["is_published"] else "Utkast")
    st.subheader("Cupens grunduppgifter")
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

    # Slutspelsvalen ligger utanför formuläret så de reagerar direkt på användarens val.
    # Streamlit-formulär skickar annars inte widgetändringar förrän "Spara" trycks.
    st.markdown("#### Slutspelsmodell och avgörande")
    playoff_col1, playoff_col2 = st.columns(2)
    edited_format = playoff_col1.selectbox(
        "Typ av slutspel",
        format_options,
        index=format_options.index(saved_format),
        key=f"overview_playoff_format_{tid}",
    )
    edited_bronze = playoff_col2.checkbox(
        "Skapa bronsmatch automatiskt när slutspelsträdet har minst fyra lag",
        value=bool(tournament["bronze_match"]),
        disabled=edited_format == "Inget slutspel",
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
        disabled=edited_format == "Inget slutspel",
        key=f"overview_tie_rule_{tid}",
    )
    edited_extra_time = tie2.number_input(
        "Förlängning (minuter)",
        min_value=1,
        max_value=60,
        value=max(1, int(tournament["extra_time_minutes"] or 10)),
        disabled=edited_format == "Inget slutspel" or edited_tie_rule != "Förlängning + straffar",
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

    with st.form("edit_tournament_basics"):
        st.markdown("#### Cup och deltagande")
        bn1, bn2 = st.columns(2)
        edited_name = bn1.text_input("Turneringens namn", value=tournament["name"])
        edited_location = bn2.text_input("Spelort", value=tournament["location"] or "")
        bc1, bc2, bc3 = st.columns(3)
        edited_start = bc1.date_input("Första cupdag", value=saved_start)
        edited_end = bc2.date_input("Sista cupdag", value=saved_end)
        edited_expected = bc3.number_input("Planerat antal lag", max(2, int(current_team_count_for_limit)), 500, max(int(tournament["expected_team_count"] or 8), int(current_team_count_for_limit)), help="Maxantalet kan inte sättas lägre än antalet lag som redan är registrerade.")

        st.markdown("#### Arena och information till besökare")
        edited_address = st.text_input(
            "Arenaadress", value=tournament["arena_address"] or "",
            placeholder="Exempel: Idrottsvägen 1, 702 00 Örebro",
        )
        edited_kiosk_info = st.text_input(
            "Kiosk och servering (frivillig information)", value=tournament["kiosk_information"] or "",
            placeholder="Exempel: Kiosk finns och är öppen 08.00–17.00 med kaffe, korv och enklare lunch",
        )
        edited_public_info = st.text_area(
            "Övrig information", value=tournament["public_information"] or "",
            placeholder="Exempel: Parkering finns vid skolan. Omklädningsrum öppnar 07.30. Hundar ska hållas kopplade.",
        )

        st.markdown("#### Poängregler och tabell")
        bp1, bp2, bp3 = st.columns(3)
        edited_win = bp1.number_input("Poäng för vinst", 0, 10, int(tournament["points_win"]))
        edited_draw = bp2.number_input("Poäng för oavgjort", 0, 10, int(tournament["points_draw"]))
        edited_loss = bp3.number_input("Poäng för förlust", 0, 10, int(tournament["points_loss"]))

        table_tiebreak_options = ["Målskillnad först", "Inbördes möten först"]
        saved_tiebreak = tournament["table_tiebreak"] or "Målskillnad först"
        edited_tiebreak = st.selectbox(
            "Vid lika poäng avgör i första hand",
            table_tiebreak_options,
            index=table_tiebreak_options.index(saved_tiebreak) if saved_tiebreak in table_tiebreak_options else 0,
        )

        st.markdown("#### Match- och schemaregler")
        br1, br2, br3 = st.columns(3)
        edited_first_time = br1.time_input("Första avspark", value=datetime.strptime(overview_rules["first_match_time"], "%H:%M").time())
        edited_halves = br2.number_input("Antal halvlekar", 1, 4, int(overview_rules["halves"]))
        edited_minutes_half = br3.number_input("Minuter per halvlek", 1, 120, int(overview_rules["minutes_per_half"]))
        br4, br5 = st.columns(2)
        edited_halftime = br4.number_input("Halvtidspaus (minuter)", 0, 60, int(overview_rules["halftime_minutes"]))
        edited_pitch_break = br5.number_input("Paus mellan matcher på samma plan", 0, 120, int(overview_rules["pitch_break_minutes"]))
        st.markdown("##### Följdmatcher för samma lag")
        with st.container(border=True):
            follow1, follow2 = st.columns(2)
            edited_avoid_consecutive = follow1.checkbox(
                "Försök undvika matcher direkt efter varandra för samma lag",
                value=bool(overview_rules["avoid_consecutive_matches"]),
            )
            edited_consecutive_break = follow2.number_input(
                "Extra paus om följdmatcher inte kan undvikas (minuter)",
                0, 180, int(overview_rules["consecutive_match_break_minutes"]),
                disabled=not edited_avoid_consecutive,
            )
        br7, br8, br9 = st.columns(3)
        edited_pitch_count = br7.number_input("Antal planer", 1, 30, int(overview_rules["pitch_count"]))
        final_date_label = f"{SWEDISH_WEEKDAYS[edited_end.weekday()]} {edited_end.day} {SWEDISH_MONTHS[edited_end.month - 1]} {edited_end.year}"
        edited_latest = br8.time_input(
            f"Sista plantid – {final_date_label}",
            value=datetime.strptime(overview_rules["latest_kickoff_time"], "%H:%M").time(),
            help="Ingen match får planeras så att den slutar efter denna tid. På sista cupdagen är detta turneringens absoluta sluttid.",
        )
        edited_referee_mode = br9.selectbox("Domartillsättning", ["Automatisk", "Manuell"], index=0 if overview_rules["referee_mode"] == "Automatisk" else 1)
        edited_match_minutes = (edited_halves * edited_minutes_half) + ((edited_halves - 1) * edited_halftime)
        st.info(f"Med dessa regler tar en match {edited_match_minutes} minuter från avspark till slutsignal.")

        if st.form_submit_button("Spara alla grunduppgifter", type="primary", use_container_width=True):
            if not edited_name.strip():
                st.error("Turneringens namn får inte vara tomt.")
            elif edited_end < edited_start:
                st.error("Sista cupdagen får inte ligga före första cupdagen.")
            else:
                scheduling_changed = any([
                    edited_start != saved_start,
                    edited_end != saved_end,
                    edited_first_time.strftime("%H:%M") != overview_rules["first_match_time"],
                    edited_halves != overview_rules["halves"],
                    edited_minutes_half != overview_rules["minutes_per_half"],
                    edited_halftime != overview_rules["halftime_minutes"],
                    edited_pitch_break != overview_rules["pitch_break_minutes"],
                    int(edited_avoid_consecutive) != overview_rules["avoid_consecutive_matches"],
                    edited_consecutive_break != overview_rules["consecutive_match_break_minutes"],
                    edited_pitch_count != overview_rules["pitch_count"],
                    edited_latest.strftime("%H:%M") != overview_rules["latest_kickoff_time"],
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
                        kiosk_information=?,public_information=?,table_tiebreak=?,playoff_tie_rule=?,extra_time_minutes=?,playoff_model_confirmed=1
                        WHERE id=?""",
                        (edited_name.strip(), edited_location.strip(), edited_start.isoformat(), edited_start.isoformat(), edited_end.isoformat(),
                         edited_expected, edited_win, edited_draw, edited_loss, edited_format, int(edited_bronze), edited_address.strip(),
                         int(bool(edited_kiosk_info.strip())), edited_kiosk_info.strip(), edited_public_info.strip(), edited_tiebreak,
                         edited_tie_rule if edited_format != "Inget slutspel" else "Straffar direkt",
                         edited_extra_time if edited_format != "Inget slutspel" and edited_tie_rule == "Förlängning + straffar" else 0,
                         tid),
                    )
                    con.execute(
                        """UPDATE schedule_rules SET first_match_time=?,halves=?,minutes_per_half=?,halftime_minutes=?,pitch_break_minutes=?,
                        avoid_consecutive_matches=?,consecutive_match_break_minutes=?,pitch_count=?,latest_kickoff_time=?,referee_mode=? WHERE tournament_id=?""",
                        (edited_first_time.strftime("%H:%M"), edited_halves, edited_minutes_half, edited_halftime, edited_pitch_break,
                         int(edited_avoid_consecutive), edited_consecutive_break, edited_pitch_count,
                         edited_latest.strftime("%H:%M"), edited_referee_mode, tid),
                    )
                    if scheduling_changed:
                        con.execute("UPDATE matches SET schedule_published=0 WHERE tournament_id=?", (tid,))
                        con.execute("UPDATE tournaments SET is_published=0,schedule_dirty=1 WHERE id=?", (tid,))
                    con.commit()
                st.session_state["overview_saved_message"] = (
                    "Grunduppgifterna sparades. Ändringarna påverkar schemat, som nu är markerat för regenerering."
                    if scheduling_changed else "Grunduppgifterna sparades."
                )
                st.rerun()
    if "overview_saved_message" in st.session_state:
        st.success(st.session_state.pop("overview_saved_message"))
    if tournament["playoff_format"] != "Inget slutspel":
        st.caption("Typen av slutspel väljs här. Vilka placeringar som möts och hur trädet byggs ställs in under fliken Slutspel.")
    admin_groups = all_rows("SELECT * FROM groups WHERE tournament_id=?", (tid,))
    admin_teams = all_rows("SELECT * FROM teams WHERE tournament_id=?", (tid,))
    admin_matches = all_rows("SELECT * FROM matches WHERE tournament_id=?", (tid,))
    unassigned_teams = [t for t in admin_teams if t["group_id"] is None]
    unscheduled_matches = [m for m in admin_matches if m["scheduled_start"] is None]
    matches_without_referee = [m for m in admin_matches if m["scheduled_start"] is not None and m["referee_id"] is None]
    unpublished_matches = [m for m in admin_matches if m["scheduled_start"] is not None and not m["schedule_published"]]
    scheduled_admin_matches = [m for m in admin_matches if m["scheduled_start"] is not None]
    published_admin_matches = [m for m in scheduled_admin_matches if m["schedule_published"]]
    overview_schedule_errors, overview_schedule_warnings, _ = validate_schedule(tid, tournament, overview_rules)
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
    st.subheader("Publicering")
    if tournament["is_published"]:
        st.success("Turneringsvyn är publicerad.")
    else:
        st.warning("Turneringsvyn är ett utkast och kan inte ses publikt ännu.")
    ps1, ps2, ps3 = st.columns(3)
    ps1.metric("Schemalagda", len(scheduled_admin_matches))
    ps2.metric("Publicerade", len(published_admin_matches))
    ps3.metric("Kvar i utkast", len(unpublished_matches))
    if not scheduled_admin_matches:
        st.warning("Turneringsvyn kan inte publiceras ännu. Skapa och generera först matcherna under Skapa och publicera schema.")
    elif overview_schedule_errors:
        st.error(f"Schemat har {len(overview_schedule_errors)} blockerande fel. Åtgärda dem på schemafliken före publicering.")
    elif overview_schedule_warnings:
        st.warning(f"Schemat har {len(overview_schedule_warnings)} varningar som måste granskas före publicering.")
    st.info("Publicera eller avpublicera turneringen med knapparna i vänsterspalten. Den publika sidan nås via Visningsläge → Turneringsvy.")

    st.divider()
    st.subheader("⚠️ Riskzon – Radera turnering")
    st.error(
        "Radering tar permanent bort den valda turneringen inklusive grupper, lag, spelare, domare, matcher, "
        "resultat, matchhändelser, tabeller, slutspel och sparad testfeedback. Åtgärden kan inte ångras i appen."
    )
    delete_tournaments = all_rows("SELECT id,name FROM tournaments ORDER BY name")
    delete_ids = [row["id"] for row in delete_tournaments]
    delete_name_by_id = {row["id"]: row["name"] for row in delete_tournaments}
    default_delete_index = delete_ids.index(tid) if tid in delete_ids else 0

    with st.container(border=True):
        delete_target_id = st.selectbox(
            "Välj turnering som ska raderas",
            delete_ids,
            index=default_delete_index,
            format_func=lambda tournament_id: delete_name_by_id[tournament_id],
            key="delete_tournament_target",
        )
        delete_target_name = delete_name_by_id[delete_target_id]
        st.markdown(f"**Vald turnering:** {delete_target_name}")
        delete_selected = st.checkbox(
            "Jag förstår att hela den valda turneringen och all tillhörande data raderas permanent",
            key=f"delete_tournament_selected_{delete_target_id}",
        )

        @st.dialog("Radera turneringen permanent?")
        def confirm_tournament_deletion():
            st.error(
                f"Du är på väg att permanent radera **{delete_target_name}** och all tillhörande information."
            )
            st.caption("Det här går inte att ångra från CupNavi.")
            confirm_delete, cancel_delete = st.columns(2)
            if confirm_delete.button("Ja, radera turneringen", type="primary", use_container_width=True):
                with db() as con:
                    con.execute("DELETE FROM tournaments WHERE id=?", (delete_target_id,))
                    con.commit()
                st.session_state.pop(f"admin_page_{delete_target_id}", None)
                st.session_state.pop(f"_schedule_validation_{delete_target_id}", None)
                st.session_state.pop("delete_tournament_target", None)
                _clear_render_query_cache()
                st.rerun()
            if cancel_delete.button("Avbryt", use_container_width=True):
                st.rerun()

        if st.button(
            "🗑️ Radera vald turnering",
            disabled=not delete_selected,
            key=f"open_delete_tournament_dialog_{delete_target_id}",
            use_container_width=True,
        ):
            confirm_tournament_deletion()


    st.divider()
    st.subheader("Testverktyg")
    st.caption("Använd detta när en extern testare vill prova arbetsflödet utan att först mata in åtta lag manuellt.")
    demo_counts = one_row(
        """SELECT
             (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
             (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
             (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n""",
        (tid, tid, tid),
    )
    demo_allowed = demo_counts["teams_n"] == 0 and demo_counts["groups_n"] == 0 and demo_counts["matches_n"] == 0
    if not demo_allowed:
        st.caption("Demodata kan bara skapas i en tom turnering, så befintlig cupdata kan aldrig skrivas över.")
    if st.button("Skapa demodata: 8 lag + trupper + 2 grupper", disabled=not demo_allowed, key=f"demo_{tid}"):
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
            chosen = (
                [("Allsvenskan", *club) for club in random.sample(demo_clubs["Allsvenskan"], 3)]
                + [("Superettan", *club) for club in random.sample(demo_clubs["Superettan"], 2)]
                + [("Premier League", *club) for club in random.sample(demo_clubs["Premier League"], 3)]
            )
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

            con.execute("UPDATE tournaments SET expected_team_count=8 WHERE id=?", (tid,))
            g1 = con.execute("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tid, "Grupp A")).lastrowid
            g2 = con.execute("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tid, "Grupp B")).lastrowid

            # Första passet: skapa alla lag.
            team_specs = []
            for index, (league, club_name, home1, home2) in enumerate(chosen):
                group_id = g1 if index < 4 else g2
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
                        earliest_first_time,travel_note
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (tid, club_name, home1, away1, home_pattern, home2, away_pattern, away2,
                     group_id, distance, late, earliest, note),
                )
                team_specs.append((club_name, league))

            # Hämta faktiska Turso-ID:n efter INSERT i stället för att lita på lastrowid.
            created_teams = _rows_from_cursor(
                con.execute("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY id", (tid,))
            )
            team_id_by_name = {row["name"]: row["id"] for row in created_teams}
            if len(team_id_by_name) != 8:
                raise RuntimeError(f"Förväntade 8 demolag men hittade {len(team_id_by_name)}.")

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
                    con.execute(
                        "INSERT INTO players(team_id,player_number,name,birth_year,position) VALUES(?,?,?,?,?)",
                        (team_id, numbers[player_index], player_name, birth_year, position),
                    )
                    inserted_players += 1

            # Två fiktiva domare med påhittade kontaktuppgifter och nivåer.
            referee_first_names = ["Bengt", "Arvid", "Mats", "Sara", "Johan", "Linda", "Oskar", "Emma"]
            referee_last_names = ["Domarsson", "Pipström", "Visselberg", "Linjeman", "Rättvik", "Matchlund"]
            referee_levels = ["Distriktsdomare", "Regional domare", "Ungdomsdomare", "Senior domare"]
            used_ref_names = set()
            for ref_index in range(2):
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
            if int(referee_check["n"] or 0) < 2:
                raise RuntimeError(
                    f"Domarkontrollen misslyckades: förväntade minst 2 domare, hittade {referee_check['n']}."
                )

            con.commit()
            _clear_render_query_cache()
            st.success(
                f"Demodata skapad: 8 riktiga klubbnamn (3 Allsvenskan, 2 Superettan, 3 Premier League), "
                f"2 grupper, {inserted_players} fiktiva stjärninspirerade spelare och 2 fiktiva domare."
            )
            st.rerun()
        except Exception as exc:
            try:
                con.rollback()
            except Exception:
                pass
            st.error(f"Demodata kunde inte skapas: {exc}")


    st.markdown("##### Testresultat och matchhändelser")
    st.caption(
        "Knapparna nedan fyller redan skapade matcher med slumpade testresultat, mål, assist, "
        "gula kort och röda kort. De är endast avsedda för testning."
    )
    test_col1, test_col2 = st.columns(2)

    if test_col1.button(
        "🎲 Generera resultat – gruppspel",
        use_container_width=True,
        key=f"demo_group_results_{tid}",
    ):
        with st.spinner("Skapar gruppspelsresultat och matchhändelser…", show_time=True):
            generated, stat_rows, warning = _demo_generate_group_results(tid)
        if warning:
            st.warning(warning)
        elif generated:
            st.success(
                f"Testdata skapad för {generated} gruppspelsmatcher. "
                "Mål, assist, gula kort och röda kort har fördelats på testspelarna."
            )
            st.rerun()

    if test_col2.button(
        "🏆 Generera resultat – slutspel",
        use_container_width=True,
        key=f"demo_playoff_results_{tid}",
    ):
        with st.spinner("Spelar igenom slutspel och skapar matchhändelser…", show_time=True):
            generated, stat_rows, warning = _demo_generate_playoff_results(tid)
        if generated:
            st.success(
                f"Testdata skapad för {generated} slutspelsmatcher. "
                "Vinnare har förts vidare och matchhändelser har skapats."
            )
        if warning:
            st.warning(warning)
        if generated:
            st.rerun()


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


if admin_page == "Kontroller":
    st.header("Kontroller")
    st.caption("Här granskar du blockerande fel och varningar innan turneringen publiceras.")
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
        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("DB-anrop", _PERF["db_calls"])
        pc2.metric("DB-tid", f"{_PERF['db_ms']:.0f} ms")
        pc3.metric("Cacheträffar", _PERF["cache_hits"])
        pc4.metric("Skrivningar", _PERF["writes"])
        if _PERF["db_calls"] >= 20:
            st.warning("Många databasfrågor på samma sidladdning. Den här sidan bör optimeras vidare.")
        elif _PERF["db_ms"] >= 1500:
            st.warning("Databasen står för en stor del av väntetiden på den här sidladdningen.")
        else:
            st.success("Ingen tydlig databasflaskhals syns i den här mätningen.")
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


if admin_page == "Lag":
    st.header("Lag")
    st.caption("Registrera lagen först. Varje hemma- och bortaställ kan vara helfärgat, randigt, rutigt eller delat och ha upp till två färger. Här anger du även resväg och önskemål om en senare första match. Gruppindelningen görs därefter under fliken Grupper.")
    max_teams = int(tournament["expected_team_count"] or 0)
    registered_team_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tid,))["n"]
    if max_teams:
        st.info(f"Registrerade lag: {registered_team_count} av maximalt {max_teams}.")
    team_limit_reached = bool(max_teams and registered_team_count >= max_teams)
    if team_limit_reached:
        st.info(
            f"Maximalt antal lag ({max_teams}) är registrerade. "
            "Om du vill lägga till fler lag måste du först ändra planerat antal lag under Admin → Översikt."
        )
    if team_limit_reached:
        st.warning(f"Maximalt antal lag ({max_teams}) är registrerade. Ändra planerat antal lag under Admin → Översikt om fler lag ska kunna läggas till.")
    with st.container(border=True):
        team_name = st.text_input("Lagnamn")
        st.markdown("#### Hemmaställ")
        hc1, hc2, hc3 = st.columns([1.2, 1, 1])
        home_pattern = hc1.selectbox("Mönster hemma", KIT_PATTERNS, key="new_home_pattern")
        primary = hc2.color_picker("Hemma – färg 1", "#111827")
        home_color_2 = hc3.color_picker("Hemma – färg 2", "#FFFFFF", help="Används när stället inte är helfärgat.")
        st.markdown(kit_preview_html(home_pattern, primary, home_color_2, "Förhandsvisning hemmaställ"), unsafe_allow_html=True)

        st.markdown("#### Bortaställ")
        ac1, ac2, ac3 = st.columns([1.2, 1, 1])
        away_pattern = ac1.selectbox("Mönster borta", KIT_PATTERNS, key="new_away_pattern")
        secondary = ac2.color_picker("Borta – färg 1", "#FFFFFF")
        away_color_2 = ac3.color_picker("Borta – färg 2", "#111827", help="Används när stället inte är helfärgat.")
        st.markdown(kit_preview_html(away_pattern, secondary, away_color_2, "Förhandsvisning bortaställ"), unsafe_allow_html=True)

        distance = st.number_input("Resväg i kilometer", 0, 5000, 0)
        travel_note = st.text_input("Resekommentar", placeholder="Exempel: Reser samma morgon")
        late_first_match = st.checkbox("Önskar senare första match", help="Använd detta exempelvis för lag med lång resväg.")
        earliest_first_time = st.time_input("Första match tidigast", value=datetime.strptime("10:00", "%H:%M").time(), help="Tiden används bara om Önskar senare första match är markerat.")
        if st.button("Lägg till lag", type="primary", disabled=team_limit_reached, key=f"add_team_{tid}"):
            current_count = one_row("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", (tid,))["n"]
            if max_teams and current_count >= max_teams:
                st.error(f"Det går inte att lägga till fler än {max_teams} lag i den här turneringen.")
            elif team_name.strip():
                try:
                    insert_team_with_limit(
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
                    "Grupp": group_names.get(team_row["group_id"], "Ej placerad"),
                    "Resväg km": team_row["distance_km"] or 0,
                }
                for team_row in teams
            ])
        )
    else:
        st.info("Inga lag är skapade ännu.")

    st.divider()
    st.markdown(
        """
        <div style="
            background:#ffffff;
            border:1px solid #cbd5e1;
            border-left:5px solid #166534;
            border-radius:10px;
            padding:12px 16px;
            margin:6px 0 12px 0;
            color:#0f172a;
            font-size:1.08rem;
            font-weight:800;">
            Redigera eller ta bort lag
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        if teams:
            edit_team_id = st.selectbox("Välj lag", [t["id"] for t in teams], format_func=lambda x: next(t["name"] for t in teams if t["id"] == x), key="edit_team")
            edit_team = next(t for t in teams if t["id"] == edit_team_id)
            with st.container(border=True):
                edited_name = st.text_input("Lagnamn", value=edit_team["name"], key=f"edit_name_{edit_team_id}")
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

                edited_distance = st.number_input("Resväg i kilometer", 0, 5000, int(edit_team["distance_km"] or 0), key=f"edit_distance_{edit_team_id}")
                edited_travel_note = st.text_input("Resekommentar", value=edit_team["travel_note"] or "", key=f"edit_travel_note_{edit_team_id}")
                edited_late_first = st.checkbox("Önskar senare första match", value=bool(edit_team["late_first_match"]), key=f"edit_late_first_{edit_team_id}")
                saved_earliest = edit_team["earliest_first_time"] or "10:00"
                edited_earliest = st.time_input(
                    "Första match tidigast",
                    value=datetime.strptime(saved_earliest, "%H:%M").time(),
                    help="Tiden används bara om Önskar senare första match är markerat.",
                    key=f"edit_earliest_{edit_team_id}",
                )
                if st.button("Spara ändringar", type="primary", key=f"save_team_{edit_team_id}"):
                    if edited_name.strip():
                        run(
                            """UPDATE teams SET
                                name=?,primary_color=?,secondary_color=?,home_pattern=?,home_color_2=?,away_pattern=?,away_color_2=?,
                                distance_km=?,late_first_match=?,earliest_first_time=?,travel_note=? WHERE id=?""",
                            (edited_name.strip(), edited_primary, edited_secondary,
                             edited_home_pattern, edited_home_color_2, edited_away_pattern, edited_away_color_2,
                             edited_distance, int(edited_late_first), edited_earliest.strftime("%H:%M") if edited_late_first else None,
                             edited_travel_note.strip(), edit_team_id),
                        )
                        st.rerun()
                    st.error("Lagnamnet får inte vara tomt.")
            confirm_team_delete = st.checkbox("Jag förstår att lagets trupp, statistik och berörda matcher tas bort", key=f"confirm_team_{edit_team_id}")
            if st.button("Ta bort laget", disabled=not confirm_team_delete, key=f"delete_team_{edit_team_id}"):
                token = f"team:{edit_team_id}"
                bracket_ids = [r["bracket_id"] for r in all_rows("SELECT DISTINCT bracket_id FROM matches WHERE bracket_id IS NOT NULL AND (home_source=? OR away_source=?)", (token, token))]
                if edit_team["group_id"]:
                    group_brackets = all_rows(
                        "SELECT DISTINCT bracket_id FROM matches WHERE bracket_id IS NOT NULL AND (home_source LIKE ? OR away_source LIKE ?)",
                        (f"group:{edit_team['group_id']}:%", f"group:{edit_team['group_id']}:%"),
                    )
                    bracket_ids.extend(r["bracket_id"] for r in group_brackets)
                with db() as con:
                    con.execute("DELETE FROM matches WHERE home_source=? OR away_source=?", (token, token))
                    for bracket_id in set(bracket_ids):
                        con.execute("DELETE FROM brackets WHERE id=?", (bracket_id,))
                    con.execute("DELETE FROM teams WHERE id=?", (edit_team_id,))
                    con.commit()
                st.rerun()
        else:
            st.info("Det finns inga lag att redigera.")


if admin_page == "Grupper":
    st.header("Grupper")
    st.caption("Skapa gruppindelningen efter att lagen är registrerade och placera sedan varje lag i rätt grupp.")
    st.subheader("Grupper")
    teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    if not teams:
        st.warning("Lägg först till lagen under fliken Lag innan du skapar grupper.")
    with st.form("new_group", clear_on_submit=True):
        group_name = st.text_input("Gruppnamn", placeholder="Grupp A")
        if st.form_submit_button("Lägg till grupp", type="primary", disabled=not bool(teams)):
            if group_name.strip():
                run("INSERT INTO groups(tournament_id,name) VALUES(?,?)", (tid, group_name.strip()))
                st.rerun()
            st.error("Ange ett gruppnamn.")

    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    if groups:
        st.caption("Skapade grupper: " + ", ".join(g["name"] for g in groups))

    st.divider()
    st.subheader("Placera lagen i rätt grupp")
    if not teams:
        st.info("Inga lag är registrerade.")
    elif not groups:
        st.info("Skapa minst en grupp ovan för att kunna placera lagen.")
    elif sort_items is not None:
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
        if st.button("Spara gruppindelning", type="primary"):
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
        st.warning("Dra-och-släpp kräver tillägget streamlit-sortables. Reservläget används tills det installerats.")
        for t in teams:
            c1, c2, c3 = st.columns([4, 3, 2])
            c1.markdown(f"**{t['name']}**")
            options = [None] + [g["id"] for g in groups]
            current_index = options.index(t["group_id"]) if t["group_id"] in options else 0
            new_group = c2.selectbox("Grupp", options, index=current_index, key=f"group_{t['id']}", label_visibility="collapsed", format_func=lambda x: "Ingen grupp" if x is None else next(g["name"] for g in groups if g["id"] == x))
            if c3.button("Spara", key=f"save_group_{t['id']}"):
                run("UPDATE teams SET group_id=? WHERE id=?", (new_group, t["id"]))
                st.rerun()

    st.divider()
    with st.expander("Redigera eller ta bort grupp"):
        if groups:
            edit_group_id = st.selectbox("Välj grupp", [g["id"] for g in groups], format_func=lambda x: next(g["name"] for g in groups if g["id"] == x), key="edit_group")
            edit_group = next(g for g in groups if g["id"] == edit_group_id)
            with st.form("edit_group_form"):
                edited_group_name = st.text_input("Gruppnamn", value=edit_group["name"])
                if st.form_submit_button("Spara gruppnamn", type="primary"):
                    if edited_group_name.strip():
                        run("UPDATE groups SET name=? WHERE id=?", (edited_group_name.strip(), edit_group_id))
                        st.rerun()
                    st.error("Gruppnamnet får inte vara tomt.")
            confirm_group_delete = st.checkbox("Jag förstår att gruppens matcher och slutspel som använder gruppen tas bort, och att lagen blir oplacerade", key=f"confirm_group_{edit_group_id}")
            if st.button("Ta bort gruppen", disabled=not confirm_group_delete, key=f"delete_group_{edit_group_id}"):
                affected_brackets = [r["bracket_id"] for r in all_rows("SELECT DISTINCT bracket_id FROM matches WHERE bracket_id IS NOT NULL AND (home_source LIKE ? OR away_source LIKE ?)", (f"group:{edit_group_id}:%", f"group:{edit_group_id}:%"))]
                with db() as con:
                    con.execute("UPDATE teams SET group_id=NULL WHERE group_id=?", (edit_group_id,))
                    for bracket_id in affected_brackets:
                        con.execute("DELETE FROM brackets WHERE id=?", (bracket_id,))
                    con.execute("DELETE FROM groups WHERE id=?", (edit_group_id,))
                    con.commit()
                st.rerun()
        else:
            st.info("Det finns inga grupper att redigera.")


if admin_page == "Trupper":
    st.header("Trupper")
    st.caption("Registrera spelare och truppuppgifter för respektive lag.")
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
            position = c4.selectbox("Position", ["Målvakt", "Försvarare", "Mittfältare", "Anfallare", "Ej angiven"])
            if st.form_submit_button("Lägg till spelare", type="primary"):
                if pname.strip():
                    run("INSERT INTO players(team_id,player_number,name,birth_year,position) VALUES(?,?,?,?,?)", (team_id, number, pname.strip(), birth, position))
                    st.rerun()
                st.error("Ange spelarens namn.")
        players = all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (team_id,))
        render_centered_table(pd.DataFrame([{"Nr": p["player_number"], "Spelare": p["name"], "Födelseår": p["birth_year"], "Position": p["position"]} for p in players]))


if admin_page == "Domare":
    st.header("Domare")
    st.caption("Registrera domare som kan tilldelas matcher automatiskt eller manuellt.")
    with st.form("new_referee", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        rname = c1.text_input("Namn")
        phone = c2.text_input("Telefon")
        email = c3.text_input("E-post")
        if st.form_submit_button("Lägg till domare", type="primary"):
            if rname.strip():
                run("INSERT INTO referees(tournament_id,name,phone,email) VALUES(?,?,?,?)", (tid, rname.strip(), phone.strip(), email.strip()))
                st.rerun()
            st.error("Ange domarens namn.")
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    render_centered_table(pd.DataFrame([{"Namn": r["name"], "Telefon": r["phone"], "E-post": r["email"]} for r in refs]))


if admin_page == "Skapa och publicera schema":
    st.header("Skapa och publicera schema")
    st.caption("En knapp skapar alla gruppmöten och schemalägger dem samtidigt för samtliga grupper. Kontrollresultaten finns på fliken Kontroller.")
    if "schedule_message" in st.session_state:
        message_type, message_text = st.session_state.pop("schedule_message")
        getattr(st, message_type)(message_text)

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
        f"matchtid totalt {match_minutes} min · första avspark {rules['first_match_time']} · sista plantid {rules['latest_kickoff_time']} · "
        f"{rules['pitch_count']} planer · {consecutive_rule_text} · domare: {rules['referee_mode']}."
    )
    st.caption("Regelverket och slutspelsformatet ändras under Adminöversikt → Cupens grunduppgifter.")
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

    st.markdown("#### 2. Skapa och generera hela spelschemat")
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
        schedule_button_label = (
            "Regenerera återstående grupp- och slutspelsmatcher utan att ändra spelade matcher"
            if played_result_total else "Skapa gruppspel + slutspel och generera hela spelschemat"
        )
        if st.button(schedule_button_label, type="primary", use_container_width=True, disabled=create_disabled):
            started_schedule = time.perf_counter()
            try:
                with st.spinner("CupNavi bygger schemat och fördelar planer/domare…"):
                    if played_result_total:
                        created, ready_groups, skipped_groups = 0, len(schedule_groups), []
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
            st.info("Klicka på knappen ovan för att skapa gruppspel, slutspel och generera hela spelschemat i ett steg.")
        elif schedule_errors:
            st.error(f"Schemat har {len(schedule_errors)} fel och kan inte publiceras. Se schemakontrollen nedan.")
        elif schedule_warnings:
            st.warning("Schemat har varningar. Granska dem och godkänn dem i vänsterspalten före publicering.")
        elif unpublished_total:
            st.warning("Schemat är ett utkast. Kontrollera matchlistan och publicera sedan från vänsterspalten.")
        else:
            st.success("Det aktuella spelschemat är publicerat i Turneringsvyn.")

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

    st.info(
        "Blockerande fel, varningar och lagens vilotider granskas på fliken Kontroller. "
        "Slutspelsmatcher får tid och matchnummer direkt; innan lagen är klara visas platshållare som "
        "Vinnaren i Grupp A eller Vinnare match X."
    )

    travel_teams = all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
    st.subheader("Reseinformation för lagen")
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
    adjustable_matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id",
        (tid,),
    )
    if adjustable_matches:
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
                kit_note = f"⚠ {away['name']} behöver ett ytterligare avvikande ställ" if away else "⚠ Färgkrock"
            elif away_kit_used:
                kit_note = f"{away['name']} använder sin andra tröjfärg"
            else:
                kit_note = ""
            schedule_rows.append({
                "match_id": m["id"],
                "Match": index,
                "Fas": m["stage"],
                "Plan": m["pitch_number"],
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
                con.commit()
            st.success("Resultaten sparades.")
        st.caption("Målskyttar, assist, varningar och utvisningar registreras under fliken Matchhändelser och visas därefter automatiskt här.")


if admin_page == "Matcher och resultat":
    st.header("Matcher och resultat")
    st.caption("Registrera och uppdatera matchresultat och domartillsättning.")
    refs = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tid,))
    st.subheader("Registrera resultat och domare")
    st.caption("Matcherna skapas automatiskt från gruppindelningen och den valda slutspelsmodellen.")
    if "bulk_result_message" in st.session_state:
        st.success(st.session_state.pop("bulk_result_message"))
    matches = all_rows("SELECT * FROM matches WHERE tournament_id=? ORDER BY CASE stage WHEN 'Gruppspel' THEN 0 ELSE 1 END, group_id, bracket_id, round_no, match_no", (tid,))
    if not matches:
        st.info("Inga matcher är skapade.")
    else:
        st.subheader("Hela matchschemat")
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
            st.caption(f"{unresolved_count} kommande slutspelsmatch(er) väntar fortfarande på klara lag och kan inte resultatregistreras ännu.")
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
            if tournament["playoff_tie_rule"] == "Lottning":
                st.caption("Vid oavgjord slutspelsmatch väljer du vinnaren i kolumnen Avgörande vinnare enligt tävlingsregeln Lottning.")
            elif tournament["playoff_tie_rule"] == "Förlängning + straffar":
                st.caption(f"Vid oavgjort spelas {tournament['extra_time_minutes']} min förlängning och därefter straffar. Registrera straffresultatet vid fortsatt oavgjort.")
            else:
                st.caption("Vid oavgjord slutspelsmatch avgörs matchen med straffar direkt. Registrera straffresultatet.")
            if st.button("Spara alla resultat", type="primary", use_container_width=True):
                updates = []
                errors = []
                for _, row in edited_results.iterrows():
                    home_score = None if pd.isna(row["Hemmamål"]) else int(row["Hemmamål"])
                    away_score = None if pd.isna(row["Bortamål"]) else int(row["Bortamål"])
                    home_penalties = None if pd.isna(row["Hemmastraffar"]) else int(row["Hemmastraffar"])
                    away_penalties = None if pd.isna(row["Bortastraffar"]) else int(row["Bortastraffar"])
                    if (home_score is None) != (away_score is None):
                        errors.append(f"{row['Hemmalag']}–{row['Bortalag']}: fyll i båda målresultaten eller lämna båda tomma.")
                        continue
                    decided_winner_id = None
                    if row["Fas"] != "Gruppspel" and home_score is not None and home_score == away_score:
                        home_team_id = result_team_id_by_name.get(row["Hemmalag"])
                        away_team_id = result_team_id_by_name.get(row["Bortalag"])
                        if tournament["playoff_tie_rule"] == "Lottning":
                            decided_winner_id = result_team_id_by_name.get(row["Avgörande vinnare"])
                            if decided_winner_id not in (home_team_id, away_team_id):
                                errors.append(f"{row['Hemmalag']}–{row['Bortalag']}: välj vilket av de två lagen som vann lottningen.")
                                continue
                            home_penalties = away_penalties = None
                        else:
                            if home_penalties is None or away_penalties is None or home_penalties == away_penalties:
                                errors.append(f"{row['Hemmalag']}–{row['Bortalag']}: ange ett avgörande straffresultat.")
                                continue
                    else:
                        home_penalties = away_penalties = None
                        decided_winner_id = None
                    referee_id = referee_ids_by_name.get(row["Domare"])
                    updates.append((home_score, away_score, home_penalties, away_penalties, decided_winner_id, referee_id, int(row["match_id"])))
                if errors:
                    st.error("\n".join(f"• {message}" for message in errors))
                else:
                    with db() as con:
                        con.executemany(
                            "UPDATE matches SET home_score=?,away_score=?,home_penalties=?,away_penalties=?,decided_winner_id=?,referee_id=? WHERE id=?",
                            updates,
                        )
                        con.commit()
                    st.session_state["bulk_result_message"] = f"{len(updates)} matchresultat sparades."
                    st.rerun()


if admin_page == "Matchhändelser":
    st.header("Matchhändelser")
    st.caption("Registrera mål, assist, varningar och utvisningar för spelarna i respektive match.")
    st.subheader("Registrera mål, assist, varningar och utvisningar")
    played_matches = all_rows("SELECT * FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL ORDER BY id DESC", (tid,))
    playable_matches = [m for m in played_matches if resolve_source(m["home_source"]) and resolve_source(m["away_source"])]
    if not playable_matches:
        st.info("Spara först ett matchresultat. Därefter kan mål och assist registreras här.")
    else:
        stat_match_id = st.selectbox(
            "Välj match",
            [m["id"] for m in playable_matches],
            format_func=lambda x: match_result_label(next(m for m in playable_matches if m["id"] == x)),
        )
        stat_match = next(m for m in playable_matches if m["id"] == stat_match_id)
        home_team_id = resolve_source(stat_match["home_source"])
        away_team_id = resolve_source(stat_match["away_source"])
        st.caption("Ange spelarens händelser i den valda matchen. Noll innebär ingen notering.")
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
            edited = st.data_editor(
                data,
                hide_index=True,
                use_container_width=True,
                disabled=["player_id", "Nr", "Spelare"],
                column_order=["Nr", "Spelare", "Mål", "Assist", "Varningar", "Utvisningar"],
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
            st.caption(
                f"{selected_team['name']} gjorde {team_goals_in_match} mål i matchen. "
                f"Registrerat just nu: {entered_goals} mål och {entered_assists} assist."
            )
            event_validation = validate_match_event_totals(
                team_goals_in_match, entered_goals, entered_assists
            )
            for message in event_validation["errors"]:
                st.error(f"{selected_team['name']}: {message}")

            if st.button(f"Spara mål och assist för {selected_team['name']}", type="primary", key=f"save_stats_{stat_match_id}_{selected_team_id}"):
                total_goals = int(edited["Mål"].fillna(0).sum())
                total_assists = int(edited["Assist"].fillna(0).sum())
                save_validation = validate_match_event_totals(
                    team_goals_in_match, total_goals, total_assists
                )
                if not save_validation["ok"]:
                    for message in save_validation["errors"]:
                        st.error(f"Kan inte spara – {selected_team['name']}: {message}")
                else:
                    with db() as con:
                        for _, row in edited.iterrows():
                            goals = int(row["Mål"] or 0)
                            assists = int(row["Assist"] or 0)
                            yellow_cards = int(row["Varningar"] or 0)
                            red_cards = int(row["Utvisningar"] or 0)
                            con.execute(
                                """
                                INSERT INTO player_match_stats(match_id,player_id,goals,assists,yellow_cards,red_cards)
                                VALUES(?,?,?,?,?,?)
                                ON CONFLICT(match_id,player_id)
                                DO UPDATE SET goals=excluded.goals, assists=excluded.assists,
                                    yellow_cards=excluded.yellow_cards, red_cards=excluded.red_cards
                                """,
                                (stat_match_id, int(row["player_id"]), goals, assists, yellow_cards, red_cards),
                            )
                        con.commit()
                    st.success("Statistiken sparades.")
            registered_goals = int(edited["Mål"].sum())
            expected_goals = stat_match["home_score"] if selected_team_id == home_team_id else stat_match["away_score"]
            if registered_goals != expected_goals:
                st.warning(f"Registrerade spelarmål: {registered_goals}. Matchresultatet visar {expected_goals} mål. Skillnaden kan exempelvis vara självmål.")


if admin_page == "Tabeller":
    st.header("Tabeller")
    st.caption("Här visas grupptabellerna automatiskt utifrån registrerade matchresultat.")
    groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
    if not groups:
        st.info("Skapa minst en grupp.")
    for g in groups:
        st.subheader(g["name"])
        table = calculate_table(g["id"], tournament)
        render_group_table(table, tournament)
        if tournament["table_tiebreak"] == "Inbördes möten först":
            st.caption("Sortering: poäng, inbördes möten, därefter målskillnad och gjorda mål.")
        else:
            st.caption("Sortering: poäng, målskillnad, gjorda mål, därefter lagnamn.")


if admin_page == "Skytteligor":
    st.header("Skytteligor")
    st.caption("Här visas skytteliga, assistliga och kortstatistik utifrån registrerade matchhändelser.")
    st.subheader("Skytteliga")
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
    goal_rows = sorted(leaders, key=lambda r: (-r["goals"], -r["assists"], r["player_name"].lower()))
    if goal_rows:
        render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Mål": r["goals"]} for i, r in enumerate(goal_rows, 1)]))
    else:
        st.info("Inga målskyttar har registrerats.")
    st.subheader("Assistliga")
    assist_rows = sorted(leaders, key=lambda r: (-r["assists"], -r["goals"], r["player_name"].lower()))
    if assist_rows:
        render_centered_table(pd.DataFrame([{"Pl": i, "Spelare": r["player_name"], "Lag": r["team_name"], "Assist": r["assists"]} for i, r in enumerate(assist_rows, 1)]))
    else:
        st.info("Inga assist har registrerats.")
    st.subheader("Varningar och utvisningar")
    card_rows = sorted(leaders, key=lambda r: (-r["red_cards"], -r["yellow_cards"], r["player_name"].lower()))
    card_rows = [r for r in card_rows if r["yellow_cards"] or r["red_cards"]]
    if card_rows:
        render_centered_table(pd.DataFrame([{"Spelare": r["player_name"], "Lag": r["team_name"], "Varningar": r["yellow_cards"], "Utvisningar": r["red_cards"]} for r in card_rows]))
    else:
        st.info("Inga varningar eller utvisningar har registrerats.")


if admin_page == "Slutspel":
    st.header("Slutspel")
    st.caption("Slutspelet skapas automatiskt när hela spelschemat genereras under Schema.")

    if not tournament["playoff_model_confirmed"]:
        st.warning("Välj och spara först slutspelsmodell på Adminöversikten.")
    elif tournament["playoff_format"] == "Inget slutspel":
        st.info("Den valda modellen är Inget slutspel.")
    else:
        st.info(
            f"Vald modell: **{tournament['playoff_format']}**. "
            "Det finns ingen separat genereringsknapp – ändra modellen på Adminöversikten och regenerera därefter schemat."
        )

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
            bracket_matches = all_rows(
                "SELECT * FROM matches WHERE bracket_id=? ORDER BY round_no,match_no",
                (bracket["id"],),
            )
            if bracket_matches:
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
            render_bracket_tree(bracket["id"], public=False)

