"""CupNavi presentation/style injection extracted from app.py in v288.

The functions accept Streamlit/component modules explicitly so this module stays free
of application state and persistence dependencies.
"""

def inject_custom_css(st):
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

          /* v349: Streamlit/BaseWeb kan rendera månads-/årsnavigering och
             filler/header-rader utanför själva gridrollen. De får inte ärva
             appens mörka button/popover-bakgrund. */
          [data-baseweb="calendar"] header,
          [data-baseweb="calendar"] header *,
          [data-baseweb="calendar"] [role="presentation"],
          [data-baseweb="calendar"] [role="presentation"] *,
          [data-baseweb="calendar"] [data-baseweb="button"],
          [data-baseweb="calendar"] [data-baseweb="button"] *,
          [data-baseweb="calendar"] [role="button"],
          [data-baseweb="calendar"] [role="button"] * {
            color:#0f172a !important;
          }
          [data-baseweb="calendar"] header,
          [data-baseweb="calendar"] [role="presentation"] {
            background:#ffffff !important;
          }
          [data-baseweb="calendar"] [data-baseweb="button"],
          [data-baseweb="calendar"] [role="button"] {
            background:#ffffff !important;
            border-color:#cbd5e1 !important;
          }
          [data-baseweb="calendar"] [data-baseweb="button"]:hover,
          [data-baseweb="calendar"] [role="button"]:hover {
            background:#f1f5f9 !important;
          }
          /* v350: isolate every calendar surface, including BaseWeb's blank
             leading/trailing week fillers which otherwise inherit dark theme
             backgrounds and appear as black rectangles. */
          [data-baseweb="calendar"] div,
          [data-baseweb="calendar"] span,
          [data-baseweb="calendar"] table,
          [data-baseweb="calendar"] tbody,
          [data-baseweb="calendar"] thead,
          [data-baseweb="calendar"] tr,
          [data-baseweb="calendar"] th,
          [data-baseweb="calendar"] td {
            background-color:#ffffff !important;
          }
          [data-baseweb="calendar"] [aria-selected="true"],
          [data-baseweb="calendar"] [aria-selected="true"] *,
          [data-baseweb="calendar"] [aria-selected="true"][role="gridcell"],
          [data-baseweb="calendar"] [aria-selected="true"][role="gridcell"] * {
            background-color:#166534 !important;
            color:#ffffff !important;
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
          .cn-public-summary-row {
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:14px;
            margin:0 0 12px;
          }
          .cn-public-summary-row .public-metric-grid { margin-bottom:0; }
          .cn-public-highlights {
            display:grid;
            grid-template-columns:repeat(2,minmax(155px,1fr));
            gap:8px;
            flex:1 1 460px;
            max-width:680px;
          }
          .cn-public-highlight {
            background:#f8fafc;
            border:1px solid var(--cup-border);
            border-radius:10px;
            padding:8px 10px;
            min-width:0;
          }
          .cn-public-highlight .label { color:var(--cup-muted) !important; font-size:11px; font-weight:750; margin-bottom:2px; }
          .cn-public-highlight .value { color:var(--cup-ink) !important; font-size:14px; line-height:1.25; font-weight:850; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
          .cn-public-highlight .sub { color:var(--cup-muted) !important; font-size:11px; line-height:1.2; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }


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


def inject_ux2_css(st, components):
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
        .cn-setup-hero{background:linear-gradient(135deg,#ffffff 0%,#f6fbf7 100%);border:1px solid #dfe8e2;border-radius:18px;padding:20px 22px;margin:4px 0 14px;box-shadow:0 8px 24px rgba(15,23,42,.045)}
        .cn-setup-eyebrow{font-size:.76rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#178342;margin-bottom:5px}
        .cn-setup-title{font-size:1.42rem;font-weight:850;color:#142019;line-height:1.2;margin-bottom:6px}
        .cn-setup-copy{font-size:.93rem;line-height:1.5;color:#59665e;margin:0 0 14px}
        .cn-setup-progress-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}
        .cn-setup-step{border:1px solid #e1e7e3;border-radius:12px;padding:9px 10px;background:#fff;color:#69746d;font-size:.78rem;font-weight:700}
        .cn-setup-step strong{display:inline-flex;width:21px;height:21px;align-items:center;justify-content:center;border-radius:999px;background:#eef2ef;color:#667169;margin-right:5px}
        .cn-setup-step.done{background:#f3faf5;border-color:#b9dec5;color:#28613c}.cn-setup-step.done strong{background:#dff3e5;color:#176b38}
        .cn-setup-step.active{background:#edf8f0;border-color:#8ecba1;color:#154f2d;box-shadow:inset 0 0 0 1px rgba(23,131,66,.08)}.cn-setup-step.active strong{background:#178342;color:#fff}
        .cn-setup-meta{margin-top:10px;color:#738078;font-size:.8rem;font-weight:650}
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
          .cn-setup-hero{padding:14px 14px 12px;margin-bottom:9px}.cn-setup-title{font-size:1.16rem}.cn-setup-copy{font-size:.86rem;line-height:1.4;margin-bottom:10px}.cn-setup-progress-grid{grid-template-columns:1fr 1fr}
          /* v400: keep all five wizard steps visible in one compact mobile row.
             Only the current step keeps its text label, which removes a large
             progress block without hiding where the user is in the flow. */
          .cn-setup-progress-grid{display:flex!important;gap:5px!important;overflow:hidden!important}
          .cn-setup-step{flex:1 1 0!important;min-width:0!important;padding:6px 3px!important;text-align:center!important;font-size:0!important;border-radius:10px!important;white-space:nowrap!important}
          .cn-setup-step strong{width:22px!important;height:22px!important;margin:0!important;font-size:.72rem!important}
          .cn-setup-step.active{flex:2.45 1 0!important;font-size:.7rem!important;padding-left:6px!important;padding-right:6px!important}
          .cn-setup-step.active strong{margin-right:4px!important}
          .cn-mobile-bottom-nav{display:grid;grid-template-columns:repeat(4,1fr);position:fixed;left:8px;right:8px;bottom:8px;z-index:999996;background:rgba(255,255,255,.97);border:1px solid #dbe4ea;border-radius:18px;box-shadow:0 10px 28px rgba(15,23,42,.16);padding:6px;-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px)}
          .cn-mobile-bottom-nav a{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-height:52px;text-decoration:none!important;color:#475569!important;font-size:17px;border-radius:12px}.cn-mobile-bottom-nav a span{font-size:10px;font-weight:800}.cn-mobile-bottom-nav a.active{background:#eef8f1;color:#14532d!important}
          .stApp .block-container{padding-bottom:5.8rem!important}.cn-schedule-grid{min-width:640px}.cn-current-admin-page{top:70px} [data-testid="stButton"] button{min-height:46px !important}
        }
        </style>""", unsafe_allow_html=True)
    components.html("""<script>document.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();const f=window.parent.document.querySelector('input[aria-label*=\"Sök lag\"],input[placeholder*=\"ÖSK\"]');if(f){f.focus();f.scrollIntoView({block:'center'});}}});</script>""",height=0)


def inject_v191_design_system(st):
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
          /* v1.289: rows with four or more Streamlit columns were the main
             recurring mobile-density problem across admin, setup and metrics.
             Wrap only wide rows; ordinary one/two/three-column forms are untouched. */
          [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)){
            flex-wrap:wrap!important;
          }
          [data-testid="stHorizontalBlock"]:has(> [data-testid="column"]:nth-child(4)) > [data-testid="column"]{
            min-width:calc(50% - 5px)!important;
            flex:1 1 calc(50% - 5px)!important;
            width:calc(50% - 5px)!important;
          }
          [data-testid="stMetric"]{min-width:0!important}
          [data-testid="stMetricLabel"]{white-space:normal!important;line-height:1.2!important}
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


def inject_v193_product_design_system(st):
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


def inject_v266_public_mobile_css(st):
    st.markdown(
        """<style>
        /* Behåll Streamlits header (sidebar-kontroll behövs i admin) men dölj
           hostingverktyg/deploy-toolbar i den publika produktupplevelsen. */
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        .stAppDeployButton { display:none !important; }

        /* Summeringen får aldrig pressa metric-korten till bokstavssmala kolumner. */
        .cn-public-summary-row,
        .cn-public-summary-row > * { min-width:0 !important; }
        .public-metric-grid { min-width:0 !important; }
        .public-metric { min-width:0 !important; overflow:hidden !important; }
        .public-metric .label, .public-metric .value {
          word-break:normal !important; overflow-wrap:normal !important; hyphens:none !important;
        }

        /* The public section navigation must remain visible throughout the whole
           page. Making only the <nav> sticky is not sufficient in Streamlit: the
           nav lives inside a short markdown element, so sticky positioning stops
           when that element leaves the viewport. Make the Streamlit element
           itself sticky and keep the nav in normal flow inside it. */
        [data-testid="stElementContainer"]:has(.cn-public-section-nav),
        .element-container:has(.cn-public-section-nav){
          position:sticky !important;top:0 !important;z-index:999995 !important;
        }
        .cn-public-section-nav{
          display:grid !important;grid-template-columns:repeat(5,minmax(0,1fr)) !important;
          position:relative !important;top:auto !important;z-index:1 !important;
          width:100% !important;margin:4px 0 12px !important;padding:6px !important;
          background:#1f6f4a !important;border:1px solid #195d3e !important;
          border-radius:12px !important;box-shadow:0 5px 16px rgba(15,23,42,.14) !important;
        }
        .cn-public-section-nav a{
          display:flex !important;align-items:center !important;justify-content:center !important;
          min-width:0 !important;min-height:42px !important;padding:6px 7px !important;
          border-radius:8px !important;text-decoration:none !important;color:#f8fffb !important;
          font-size:13px !important;font-weight:800 !important;text-align:center !important;
          transition:background-color .15s ease,color .15s ease !important;
        }
        .cn-public-section-nav a:hover{background:rgba(255,255,255,.12) !important;color:#fff !important}
        .cn-public-section-nav a.active{background:#ffffff !important;color:#14552f !important;box-shadow:0 1px 4px rgba(15,23,42,.16) !important}
        .cn-public-section-nav .cn-nav-mobile{display:none}

        /* v315: native primary tournament navigation. A Streamlit widget keeps
           clicks inside the active session instead of doing a full href page
           navigation. The keyed container retains the same sticky green shell. */
        [class*="st-key-cn_public_primary_nav_shell_"]{
          position:sticky !important;top:0 !important;z-index:999995 !important;
          width:100% !important;margin:4px 0 12px !important;padding:6px !important;
          background:#1f6f4a !important;border:1px solid #195d3e !important;
          border-radius:12px !important;box-shadow:0 5px 16px rgba(15,23,42,.14) !important;
        }
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"],
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"]{width:100% !important}
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] > div,
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] > div{
          display:grid !important;grid-template-columns:repeat(5,minmax(0,1fr)) !important;width:100% !important;gap:0 !important;
        }
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] button,
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] button{
          min-width:0 !important;min-height:42px !important;padding:6px 7px !important;border-radius:8px !important;
          background:transparent !important;color:#f8fffb !important;border-color:transparent !important;
          font-size:13px !important;font-weight:800 !important;box-shadow:none !important;
        }
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] button *,
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] button *{color:#f8fffb !important}
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] button[aria-pressed="true"],
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] button[aria-pressed="true"],
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] button[aria-checked="true"],
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] button[aria-checked="true"]{
          background:#fff !important;color:#14552f !important;border-color:#fff !important;box-shadow:0 1px 4px rgba(15,23,42,.16) !important;
        }
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] button[aria-pressed="true"] *,
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] button[aria-pressed="true"] *,
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] button[aria-checked="true"] *,
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] button[aria-checked="true"] *{color:#14552f !important}

        @media(max-width:900px){
          /* Samma breakpoint som mobilnavigationen – tidigare gällde layoutfixen först
             under 760px, vilket gav sönderpressade rutor på vissa Android-viewports. */
          .cn-public-summary-row{display:block !important;margin-bottom:10px !important;width:100% !important}
          .cn-public-summary-row .public-metric-grid{
            display:grid !important;grid-template-columns:repeat(2,minmax(0,1fr)) !important;
            width:100% !important;gap:8px !important;margin:5px 0 8px !important;
          }
          .cn-public-summary-row .public-metric{
            width:auto !important;min-width:0 !important;min-height:68px !important;
            padding:10px 11px !important;display:block !important;
          }
          .cn-public-summary-row .public-metric .label{
            display:block !important;font-size:12px !important;line-height:1.2 !important;
            white-space:normal !important;margin-bottom:5px !important;
          }
          .cn-public-summary-row .public-metric .value{
            display:block !important;font-size:23px !important;line-height:1.05 !important;
            white-space:normal !important;
          }
          .cn-public-highlights{
            display:grid !important;grid-template-columns:repeat(2,minmax(0,1fr)) !important;
            width:100% !important;max-width:none !important;gap:8px !important;
          }
          .cn-public-highlight{min-width:0 !important;padding:10px !important}
          .cn-public-highlight .value,.cn-public-highlight .sub{white-space:normal !important}

          /* Mobilens cupnavigation ligger i dokumentflödet och fastnar i överkant.
             Den ersätter den tidigare bottenbaren som skymde innehåll. */
          .cn-public-section-nav{left:auto !important;right:auto !important;bottom:auto !important}
          .cn-public-section-nav .cn-nav-desktop{display:none !important}
          .cn-public-section-nav .cn-nav-mobile{display:inline !important}
          .cn-public-section-nav a{min-width:0 !important;min-height:46px !important;padding:4px 2px !important}
          .cn-public-section-nav a span{font-size:10px !important;white-space:nowrap !important}
          .stApp .block-container{padding-bottom:1.5rem !important}
        }

        @media(max-width:430px){
          .cn-public-summary-row .public-metric-grid{gap:7px !important}
          .cn-public-summary-row .public-metric{padding:9px !important;min-height:64px !important}
          .cn-public-summary-row .public-metric .value{font-size:21px !important}
          .cn-public-highlights{grid-template-columns:1fr !important}
          .cn-public-section-nav a span{font-size:9px !important}
        }
        </style>""",
        unsafe_allow_html=True,
    )


def inject_v198_visual_system(st):
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

        /* v376 — Admin operational UI */
        .cn-admin-page-head{
          display:flex;align-items:flex-end;justify-content:space-between;gap:18px;
          padding:4px 2px 14px;margin:0 0 10px;border-bottom:1px solid var(--cn98-border);
        }
        .cn-admin-page-head .cn-kicker{
          display:inline-flex;align-items:center;gap:6px;margin-bottom:5px;
          font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;
          color:var(--cn98-primary);
        }
        .cn-admin-page-head h1{
          margin:0!important;font-size:2rem!important;line-height:1.05!important;letter-spacing:-.035em!important;
        }
        .cn-admin-page-head p{
          margin:6px 0 0!important;max-width:720px;color:var(--cn98-ink-2)!important;font-size:.9rem!important;
        }
        .cn-day-guide{
          position:relative;overflow:hidden;background:var(--cn98-surface);
          border:1px solid var(--cn98-border);border-radius:16px;padding:17px 18px 16px;
          box-shadow:var(--cn98-shadow);margin:4px 0 8px;
        }
        .cn-day-guide::before{
          content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--cn98-primary);
        }
        .cn-day-guide.is-action::before{background:var(--cn98-error)}
        .cn-day-guide.is-live::before{background:#d33b31}
        .cn-day-guide.is-next::before{background:#2d6f96}
        .cn-day-guide.is-done::before{background:var(--cn98-success)}
        .cn-day-guide .eyebrow{
          font-size:.7rem;font-weight:850;letter-spacing:.09em;text-transform:uppercase;color:var(--cn98-ink-3);
        }
        .cn-day-guide .title{
          margin:4px 0 3px;font-size:1.22rem;font-weight:820;letter-spacing:-.02em;color:var(--cn98-ink);
        }
        .cn-day-guide .detail{font-size:.86rem;color:var(--cn98-ink-2)}
        .cn-day-kpis{
          display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:10px 0 8px;
        }
        .cn-day-kpi{
          background:var(--cn98-surface);border:1px solid var(--cn98-border);border-radius:12px;
          padding:11px 13px;min-width:0;
        }
        .cn-day-kpi .label{
          display:block;font-size:.72rem;font-weight:690;color:var(--cn98-ink-3);margin-bottom:2px;
        }
        .cn-day-kpi .value{
          display:block;font-size:1.45rem;line-height:1.1;font-weight:830;letter-spacing:-.035em;color:var(--cn98-ink);
        }
        .cn-day-kpi.is-live .value{color:#b42318}
        .cn-day-kpi.is-attention .value{color:var(--cn98-warning)}
        .cn-pitch-focus-grid{
          display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin:0 0 8px;
        }
        .cn-pitch-focus{
          min-width:0;background:var(--cn98-surface);border:1px solid var(--cn98-border);
          border-radius:11px;padding:9px 10px;position:relative;overflow:hidden;
        }
        .cn-pitch-focus::before{
          content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#8aa79a;
        }
        .cn-pitch-focus.is-live::before{background:#d33b31}
        .cn-pitch-focus.is-attention::before{background:var(--cn98-warning)}
        .cn-pitch-focus .pitch{font-size:.66rem;font-weight:820;color:var(--cn98-ink-3);text-transform:uppercase;letter-spacing:.06em}
        .cn-pitch-focus .when{font-size:1rem;font-weight:830;color:var(--cn98-ink);margin-top:2px}
        .cn-pitch-focus .teams{font-size:.76rem;font-weight:690;color:var(--cn98-ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .cn-pitch-focus .status{font-size:.67rem;color:var(--cn98-ink-3);margin-top:2px}
        .cn-pitch-focus-head{margin-top:13px}
        .cn-section-head{
          display:flex;align-items:center;gap:8px;margin:18px 0 7px;
          font-size:.74rem;font-weight:820;letter-spacing:.065em;text-transform:uppercase;color:var(--cn98-ink-2);
        }
        .cn-section-head::after{content:"";height:1px;flex:1;background:var(--cn98-border)}
        .cn-autopilot-head{
          display:flex;align-items:center;justify-content:space-between;gap:12px;margin:16px 0 6px;
        }
        .cn-autopilot-title{font-weight:820;font-size:.94rem;color:var(--cn98-ink)}
        .cn-autopilot-badge{
          border:1px solid #bcd5c5;background:#f0f8f3;color:#176b3a;border-radius:999px;
          padding:4px 8px;font-size:.67rem;font-weight:820;letter-spacing:.05em;text-transform:uppercase;
        }

        /* Better admin controls: less generic Streamlit, clearer action hierarchy. */
        [data-testid="stButton"] button{
          border-radius:9px!important;font-weight:690!important;letter-spacing:-.005em!important;
          transition:background-color .14s ease,border-color .14s ease,transform .14s ease!important;
        }
        [data-testid="stButton"] button:not(:disabled):active{transform:translateY(1px)}
        [data-testid="stButton"] button[kind="primary"]{
          box-shadow:0 1px 2px rgba(17,80,43,.12)!important;
        }
        [data-testid="stForm"]{
          padding:14px!important;
          box-shadow:none!important;
        }

        @media(max-width:768px){
          .cn-admin-page-head{padding:2px 0 11px;margin-bottom:7px}
          .cn-admin-page-head h1{font-size:1.7rem!important}
          .cn-admin-page-head p{font-size:.82rem!important}
          .cn-day-guide{padding:14px 14px 13px;border-radius:13px}
          .cn-day-guide .title{font-size:1.08rem}
          .cn-day-kpis{gap:6px}
          .cn-day-kpi{padding:9px 10px;border-radius:10px}
          .cn-day-kpi .label{font-size:.66rem}
          .cn-day-kpi .value{font-size:1.25rem}
          .cn-pitch-focus-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
          .cn-pitch-focus{padding:8px 9px}
          .cn-section-head{margin-top:15px}
        }
        @media(max-width:390px){
          .cn-day-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}
          .cn-day-kpi{padding:8px}
          .cn-day-kpi .label{font-size:.62rem}
          .cn-pitch-focus-grid{grid-template-columns:1fr}
          .cn-pitch-focus .teams{white-space:normal}
        }

        /* v377 — Shared admin workspace language */
        .cn-workspace-head{
          display:flex;align-items:flex-end;justify-content:space-between;gap:16px;
          padding:3px 1px 12px;margin:0 0 9px;border-bottom:1px solid var(--cn98-border);
        }
        .cn-workspace-head .kicker{
          font-size:.69rem;font-weight:830;letter-spacing:.085em;text-transform:uppercase;
          color:var(--cn98-primary);margin-bottom:4px;
        }
        .cn-workspace-head .title{
          font-size:1.72rem;font-weight:830;letter-spacing:-.035em;line-height:1.08;color:var(--cn98-ink);
        }
        .cn-workspace-head .subtitle{
          margin-top:5px;max-width:760px;font-size:.84rem;line-height:1.42;color:var(--cn98-ink-2);
        }
        .cn-step-trail{
          display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin:0 0 11px;
          color:var(--cn98-ink-3);font-size:.72rem;font-weight:680;
        }
        .cn-step-trail .step{
          display:inline-flex;align-items:center;gap:5px;padding:4px 7px;border:1px solid var(--cn98-border);
          border-radius:999px;background:var(--cn98-surface);
        }
        .cn-step-trail .step.active{
          border-color:#a8c6b3;background:var(--cn98-primary-soft);color:var(--cn98-primary);font-weight:780;
        }
        .cn-step-trail .arrow{color:#9aa69f}
        .cn-workspace-card{
          border:1px solid var(--cn98-border);border-radius:13px;background:var(--cn98-surface);
          padding:13px 14px;margin:7px 0 10px;box-shadow:none;
        }
        .cn-workspace-card .label{
          font-size:.7rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--cn98-ink-3);
        }
        .cn-workspace-card .headline{
          margin-top:3px;font-size:1rem;font-weight:790;letter-spacing:-.015em;color:var(--cn98-ink);
        }
        .cn-workspace-card .copy{
          margin-top:3px;font-size:.81rem;line-height:1.4;color:var(--cn98-ink-2);
        }
        .cn-result-progress{
          display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;
          border:1px solid var(--cn98-border);border-radius:12px;background:var(--cn98-surface);
          padding:11px 13px;margin:7px 0 5px;
        }
        .cn-result-progress .label{font-size:.74rem;font-weight:720;color:var(--cn98-ink-2)}
        .cn-result-progress .track{height:7px;background:#edf1ee;border-radius:999px;overflow:hidden}
        .cn-result-progress .track i{display:block;height:100%;background:var(--cn98-primary);border-radius:999px}
        .cn-result-progress .value{font-size:.85rem;font-weight:800;color:var(--cn98-ink)}
        .cn-mini-status{
          display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:4px 8px;
          font-size:.69rem;font-weight:760;border:1px solid var(--cn98-border);background:#fff;color:var(--cn98-ink-2);
        }

        @media(max-width:768px){
          .cn-workspace-head{padding-bottom:10px}
          .cn-workspace-head .title{font-size:1.5rem}
          .cn-workspace-head .subtitle{font-size:.79rem}
          .cn-step-trail{gap:4px;margin-bottom:9px}
          .cn-step-trail .step{padding:4px 6px;font-size:.68rem}
          .cn-result-progress{grid-template-columns:1fr auto;gap:7px}
          .cn-result-progress .label{grid-column:1/-1}
        }

        /* v378 — Admin navigation + overview */
        .cn-admin-nav-shell{
          display:flex;align-items:center;justify-content:space-between;gap:12px;
          margin:4px 0 6px;padding:0 1px;
        }
        .cn-admin-nav-shell .label{
          font-size:.7rem;font-weight:820;letter-spacing:.08em;text-transform:uppercase;color:var(--cn98-ink-3);
        }
        .cn-admin-nav-shell .hint{
          font-size:.72rem;color:var(--cn98-ink-3);
        }
        .cn-admin-overview-head{
          display:flex;align-items:flex-end;justify-content:space-between;gap:18px;
          padding:3px 1px 12px;margin:0 0 8px;border-bottom:1px solid var(--cn98-border);
        }
        .cn-admin-overview-head .kicker{
          font-size:.69rem;font-weight:830;letter-spacing:.085em;text-transform:uppercase;color:var(--cn98-primary);
        }
        .cn-admin-overview-head .title{
          margin-top:3px;font-size:1.72rem;font-weight:835;letter-spacing:-.035em;color:var(--cn98-ink);
        }
        .cn-admin-overview-head .meta{
          margin-top:5px;font-size:.8rem;color:var(--cn98-ink-2);
        }
        .cn-overview-next{
          position:relative;overflow:hidden;border:1px solid var(--cn98-border);border-radius:15px;
          background:var(--cn98-surface);padding:15px 16px 14px;margin:7px 0 6px;box-shadow:var(--cn98-shadow);
        }
        .cn-overview-next::before{
          content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--cn98-primary);
        }
        .cn-overview-next .eyebrow{
          font-size:.68rem;font-weight:840;letter-spacing:.08em;text-transform:uppercase;color:var(--cn98-primary);
        }
        .cn-overview-next .title{
          margin:4px 0 3px;font-size:1.08rem;font-weight:815;letter-spacing:-.018em;color:var(--cn98-ink);
        }
        .cn-overview-next .copy{
          font-size:.82rem;line-height:1.42;color:var(--cn98-ink-2);
        }
        .cn-overview-attention{
          display:grid;grid-template-columns:1fr;gap:7px;margin:7px 0 12px;
        }
        .cn-overview-attention-row{
          display:flex;align-items:flex-start;gap:9px;border:1px solid var(--cn98-border);
          border-radius:11px;background:var(--cn98-surface);padding:10px 11px;
        }
        .cn-overview-attention-row .dot{
          width:8px;height:8px;border-radius:50%;margin-top:5px;flex:0 0 8px;background:var(--cn98-info);
        }
        .cn-overview-attention-row.warning .dot{background:#c07a12}
        .cn-overview-attention-row.critical .dot{background:var(--cn98-error)}
        .cn-overview-attention-row .text{
          font-size:.8rem;line-height:1.35;font-weight:680;color:var(--cn98-ink);
        }
        .cn-overview-journey{
          display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin:7px 0 12px;
        }
        .cn-overview-journey .item{
          position:relative;min-width:0;border:1px solid var(--cn98-border);border-radius:10px;
          background:var(--cn98-surface);padding:9px 8px;
        }
        .cn-overview-journey .item.done{
          border-color:#b7d3c0;background:#f4faf6;
        }
        .cn-overview-journey .symbol{
          display:block;font-size:.7rem;font-weight:850;color:var(--cn98-ink-3);margin-bottom:2px;
        }
        .cn-overview-journey .done .symbol{color:var(--cn98-primary)}
        .cn-overview-journey .name{
          display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
          font-size:.72rem;font-weight:720;color:var(--cn98-ink-2);
        }
        .cn-first-run-hero{
          border:1px solid #bdd4c5;border-radius:16px;background:linear-gradient(145deg,#f6fbf7,#fff);
          padding:18px 18px 16px;margin:5px 0 9px;
        }
        .cn-first-run-hero .kicker{
          font-size:.68rem;font-weight:850;letter-spacing:.08em;text-transform:uppercase;color:var(--cn98-primary);
        }
        .cn-first-run-hero .title{
          margin:4px 0;font-size:1.35rem;font-weight:835;letter-spacing:-.025em;color:var(--cn98-ink);
        }
        .cn-first-run-hero .copy{font-size:.84rem;line-height:1.45;color:var(--cn98-ink-2)}
        .cn-first-run-steps{
          display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin:10px 0 8px;
        }
        .cn-first-run-steps .step{
          border:1px solid var(--cn98-border);border-radius:10px;background:#fff;padding:8px;
          font-size:.7rem;font-weight:690;line-height:1.25;color:var(--cn98-ink-2);
        }
        .cn-first-run-steps .step.active{
          border-color:#9fc2aa;background:var(--cn98-primary-soft);color:var(--cn98-primary);
        }

        /* Final sidebar authority: quieter app chrome, clearer controls. */
        [data-testid="stSidebar"]{
          background:#f1f5f2!important;border-right:1px solid var(--cn98-border)!important;
        }
        [data-testid="stSidebar"] > div{background:#f1f5f2!important}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.38rem!important}
        [data-testid="stSidebar"] h1{
          font-size:1.05rem!important;letter-spacing:-.02em!important;margin-bottom:.15rem!important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"]{
          margin-bottom:.1rem!important;
        }
        [data-testid="stSidebar"] hr{margin:.5rem 0!important}

        @media(max-width:768px){
          .cn-admin-nav-shell .hint{display:none}
          .cn-admin-overview-head .title{font-size:1.5rem}
          .cn-overview-next{padding:13px 14px 12px}
          .cn-overview-journey{grid-template-columns:repeat(5,minmax(72px,1fr));overflow-x:auto;padding-bottom:3px}
          .cn-first-run-steps{grid-template-columns:repeat(5,minmax(100px,1fr));overflow-x:auto;padding-bottom:3px}
          .cn-overview-journey .item,.cn-first-run-steps .step{min-width:0}
        }

        /* v379 — Public mobile workspace */
        [class*="st-key-cn_public_primary_nav_shell_"]{
          position:sticky;top:0;z-index:40;background:rgba(255,255,255,.96);
          border-bottom:1px solid var(--cn98-border);padding:7px 0 8px;margin:0 0 9px;
          -webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);
        }
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"],
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"]{
          width:100%;
        }
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] > div,
        [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] > div{
          width:100%;
        }
        [class*="st-key-cn_public_primary_nav_shell_"] button{
          min-height:42px!important;font-size:.76rem!important;font-weight:740!important;
          border-radius:9px!important;box-shadow:none!important;
        }
        .cn-public-follow-anchor{
          display:flex;align-items:flex-end;justify-content:space-between;gap:12px;
          margin:10px 0 4px;padding:0 1px;
        }
        .cn-public-follow-label{
          font-size:.82rem;font-weight:820;letter-spacing:-.01em;color:var(--cn98-ink);
        }
        .cn-public-follow-hint{
          max-width:520px;text-align:right;font-size:.7rem;line-height:1.3;color:var(--cn98-ink-3);
        }
        .cn-follow-shell{
          border:1px solid var(--cn98-border)!important;border-radius:15px!important;
          background:var(--cn98-surface)!important;box-shadow:var(--cn98-shadow)!important;
          padding:15px!important;margin:8px 0 12px!important;
        }
        .cn-follow-kicker{
          font-size:.67rem!important;font-weight:840!important;letter-spacing:.08em!important;
          text-transform:uppercase!important;color:var(--cn98-primary)!important;
        }
        .cn-follow-team{
          font-size:1.25rem!important;font-weight:835!important;letter-spacing:-.025em!important;
          color:var(--cn98-ink)!important;margin:2px 0 9px!important;
        }
        .cn-next-card{
          border:1px solid #bfd5c6!important;border-radius:12px!important;
          background:#f5faf6!important;padding:12px!important;margin:7px 0 9px!important;
        }
        .cn-next-teams{font-size:1rem!important;font-weight:790!important}
        .cn-follow-mini{
          display:grid!important;grid-template-columns:repeat(3,1fr)!important;gap:6px!important;margin-top:7px!important;
        }
        .cn-follow-mini > div{
          border:1px solid var(--cn98-border)!important;border-radius:9px!important;
          background:var(--cn98-surface-muted)!important;padding:8px!important;
        }
        .cn-my-status{display:flex!important;gap:6px!important;flex-wrap:wrap!important;margin-top:8px!important}
        .cn-my-pill{
          border:1px solid var(--cn98-border)!important;border-radius:999px!important;
          background:#fff!important;color:var(--cn98-ink-2)!important;font-size:.7rem!important;
          font-weight:680!important;padding:5px 8px!important;
        }

        @media(max-width:680px){
          .cup-hero{
            padding:15px 16px!important;margin:2px 0 7px!important;border-radius:13px!important;box-shadow:none!important;
          }
          .cup-hero .title{font-size:1.45rem!important}
          .cup-hero .meta{font-size:.75rem!important}
          [class*="st-key-cn_public_primary_nav_shell_"]{
            top:0;padding:5px 0 6px;margin-bottom:7px;overflow-x:auto;
          }
          [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] > div,
          [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] > div{
            min-width:440px;
          }
          [class*="st-key-cn_public_primary_nav_shell_"] button{
            min-height:39px!important;padding:.4rem .5rem!important;font-size:.72rem!important;
          }
          .cn-public-follow-anchor{align-items:flex-start;flex-direction:column;gap:1px;margin-top:7px}
          .cn-public-follow-hint{text-align:left;font-size:.68rem}
          .cn-follow-shell{padding:12px!important;margin-top:6px!important}
          .cn-follow-team{font-size:1.15rem!important}
          .cn-next-card{padding:10px!important}
          .cn-follow-mini > div{padding:7px!important}
          .cn-my-pill{font-size:.67rem!important}
        }

        /* v380 — Public match-card hierarchy */
        .public-match-card{
          position:relative!important;overflow:hidden!important;box-shadow:none!important;
          border-color:var(--cn98-border)!important;
        }
        .public-match-card.is-live{
          border-color:#e6aaa5!important;background:#fffafa!important;
        }
        .public-match-card.is-live::before{
          content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:#d33b31;
        }
        .public-match-card.is-upcoming::before{
          content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#b9d0c0;
        }
        .public-match-card.is-finished{
          background:#fbfcfb!important;
        }
        .public-match-card.is-finished .cn-match-time,
        .public-match-card.is-finished .cn-match-place{
          color:var(--cn98-ink-3)!important;
        }
        .public-match-card .status-pill{
          border-radius:999px!important;padding:4px 7px!important;font-size:10px!important;
          letter-spacing:.04em!important;
        }
        @media(max-width:680px){
          .public-match-card{padding:11px 10px 10px 13px!important;margin:7px 0!important;border-radius:12px!important}
          .public-match-card .match-score{font-size:19px!important}
          .public-match-card .public-team-name{overflow-wrap:anywhere}
          .public-match-card .public-match-secondary{margin-top:6px!important;font-size:10px!important}
          .public-match-card .match-referee{display:inline-block!important;margin-top:2px}
        }

        /* v382 — Public cup guide */
        .cn-info-guide-head{
          border:1px solid var(--cn98-border);border-radius:16px;background:var(--cn98-surface);
          padding:17px 18px 15px;margin:8px 0 14px;box-shadow:var(--cn98-shadow);
        }
        .cn-info-guide-head .kicker{
          font-size:.68rem;font-weight:840;letter-spacing:.08em;text-transform:uppercase;color:var(--cn98-primary);
        }
        .cn-info-guide-head .title{
          margin-top:3px;font-size:1.28rem;font-weight:835;letter-spacing:-.025em;color:var(--cn98-ink);
        }
        .cn-info-guide-head .copy{
          margin-top:4px;max-width:720px;font-size:.82rem;line-height:1.45;color:var(--cn98-ink-2);
        }
        .cn-info-section-title{
          display:flex;align-items:center;gap:8px;margin:18px 0 7px;
          font-size:.78rem;font-weight:825;letter-spacing:.03em;color:var(--cn98-ink);
        }
        .cn-info-section-title::after{
          content:"";height:1px;flex:1;background:var(--cn98-border);
        }
        .cn-custom-info-card{
          border:1px solid var(--cn98-border)!important;border-radius:12px!important;
          padding:13px 14px!important;background:var(--cn98-surface)!important;
          box-shadow:none!important;line-height:1.5!important;margin:6px 0 12px!important;
        }
        .cn-venue-card{
          display:grid!important;grid-template-columns:38px 1fr!important;gap:10px!important;
          align-items:start!important;border:1px solid var(--cn98-border)!important;border-radius:12px!important;
          background:var(--cn98-surface)!important;padding:11px 12px!important;margin:6px 0 5px!important;
          box-shadow:none!important;
        }
        .cn-venue-icon{
          width:36px;height:36px;border-radius:10px;background:var(--cn98-surface-muted);
          display:flex;align-items:center;justify-content:center;font-size:18px;
        }
        .cn-venue-copy strong{display:block;font-size:.86rem;color:var(--cn98-ink);line-height:1.25}
        .cn-venue-copy small{
          display:block;margin-top:1px;font-size:.64rem;font-weight:760;letter-spacing:.05em;
          text-transform:uppercase;color:var(--cn98-primary);
        }
        .cn-venue-copy span{display:block;margin-top:3px;font-size:.76rem;line-height:1.35;color:var(--cn98-ink-2)}
        .cn-practical-info-card{
          display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important;
          border:0!important;padding:0!important;background:transparent!important;box-shadow:none!important;margin:6px 0 13px!important;
        }
        .cn-practical-item{
          display:grid;grid-template-columns:34px 1fr;gap:8px;align-items:start;
          border:1px solid var(--cn98-border);border-radius:11px;background:var(--cn98-surface);padding:10px 11px;
          min-width:0;
        }
        .cn-practical-item .icon{
          width:32px;height:32px;border-radius:9px;background:var(--cn98-surface-muted);
          display:flex;align-items:center;justify-content:center;font-size:16px;
        }
        .cn-practical-item small{
          display:block;font-size:.63rem;font-weight:760;letter-spacing:.04em;text-transform:uppercase;color:var(--cn98-ink-3);
        }
        .cn-practical-item strong{
          display:block;margin-top:2px;font-size:.78rem;line-height:1.35;color:var(--cn98-ink);overflow-wrap:anywhere;
        }
        .cn-practical-item a{color:var(--cn98-primary)!important;text-decoration:none;font-weight:760}
        @media(max-width:680px){
          .cn-info-guide-head{padding:14px 14px 13px;margin-top:5px;border-radius:13px}
          .cn-info-guide-head .title{font-size:1.12rem}
          .cn-info-guide-head .copy{font-size:.77rem}
          .cn-info-section-title{margin-top:15px}
          .cn-practical-info-card{grid-template-columns:1fr!important}
          .cn-practical-item{padding:9px 10px}
          .cn-venue-card{grid-template-columns:34px 1fr!important;padding:10px!important}
          .cn-venue-icon{width:32px;height:32px;font-size:16px}
          [data-testid="stLinkButton"] a{min-height:2.35rem!important}
        }

        /* v383 — Global polish authority */
        .stApp h1,.stApp h2,.stApp h3,.stApp h4{
          color:var(--cn98-ink)!important;letter-spacing:-.025em!important;
          line-height:1.16!important;
        }
        .stApp h1{font-size:1.78rem!important;margin:.15rem 0 .55rem!important}
        .stApp h2{font-size:1.42rem!important;margin:.2rem 0 .5rem!important}
        .stApp h3{font-size:1.12rem!important;margin:.3rem 0 .4rem!important}
        .stApp h4{font-size:.96rem!important;margin:.3rem 0 .35rem!important}
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p{
          color:var(--cn98-ink-3)!important;font-size:.76rem!important;line-height:1.4!important;
        }

        /* One button rhythm across admin/public instead of page-specific oversized controls. */
        [data-testid="stButton"] button,
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stDownloadButton"] button,
        [data-testid="stLinkButton"] a{
          min-height:44px!important;border-radius:9px!important;
          font-size:.82rem!important;font-weight:740!important;
          padding:.48rem .78rem!important;box-shadow:none!important;
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover,
        [data-testid="stLinkButton"] a:hover{
          box-shadow:0 2px 7px rgba(18,35,27,.07)!important;
        }

        /* Forms and expanders read as lightweight work areas, not floating cards. */
        [data-testid="stForm"]{
          border:1px solid var(--cn98-border)!important;border-radius:12px!important;
          padding:13px 14px!important;background:var(--cn98-surface)!important;box-shadow:none!important;
        }
        [data-testid="stExpander"]{
          border:1px solid var(--cn98-border)!important;border-radius:10px!important;
          background:var(--cn98-surface)!important;box-shadow:none!important;
        }
        [data-testid="stExpander"] summary{
          min-height:42px!important;font-size:.81rem!important;font-weight:720!important;
          color:var(--cn98-ink)!important;
        }

        /* Alerts should signal state without dominating the whole page. */
        [data-testid="stAlert"]{
          border-radius:10px!important;box-shadow:none!important;padding:.7rem .8rem!important;
        }
        [data-testid="stAlert"] p{
          font-size:.79rem!important;line-height:1.4!important;
        }

        /* Empty states are intentionally quiet and action-oriented. */
        .cn-empty-state{
          display:grid!important;grid-template-columns:36px 1fr!important;gap:10px!important;align-items:start!important;
          border:1px dashed #cbd7cf!important;border-radius:12px!important;background:#f9fbfa!important;
          padding:13px 14px!important;margin:8px 0 11px!important;box-shadow:none!important;
        }
        .cn-empty-state .icon{
          width:34px!important;height:34px!important;border-radius:9px!important;
          display:flex!important;align-items:center!important;justify-content:center!important;
          background:#eef4f0!important;color:var(--cn98-primary)!important;font-size:1rem!important;font-weight:820!important;
        }
        .cn-empty-state b{
          display:block!important;color:var(--cn98-ink)!important;font-size:.84rem!important;line-height:1.25!important;
        }
        .cn-empty-state p{
          margin:3px 0 0!important;color:var(--cn98-ink-2)!important;font-size:.76rem!important;line-height:1.4!important;
        }

        /* Common section headers stay secondary to page titles. */
        .cn-section-head,.cn-info-section-title{
          font-size:.74rem!important;font-weight:820!important;letter-spacing:.045em!important;
          text-transform:uppercase!important;color:var(--cn98-ink-2)!important;
        }

        /* Data containers: restrained border/radius, no accidental double-card look. */
        [data-testid="stDataFrame"],[data-testid="stDataEditor"]{
          border:1px solid var(--cn98-border)!important;border-radius:10px!important;
          box-shadow:none!important;background:var(--cn98-surface)!important;
        }

        /* Widgets line up visually and keep labels readable. */
        [data-testid="stWidgetLabel"] p{
          font-size:.76rem!important;font-weight:680!important;color:var(--cn98-ink-2)!important;
        }
        [data-baseweb="select"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea{
          border-radius:9px!important;
        }

        @media(max-width:768px){
          .stApp h1{font-size:1.52rem!important;margin-bottom:.45rem!important}
          .stApp h2{font-size:1.28rem!important}
          .stApp h3{font-size:1.04rem!important}
          [data-testid="stButton"] button,
          [data-testid="stFormSubmitButton"] button,
          [data-testid="stDownloadButton"] button,
          [data-testid="stLinkButton"] a{
            min-height:44px!important;font-size:.79rem!important;padding:.45rem .62rem!important;
          }
          /* Override older broad mobile rules that made every column button 64px tall. */
          div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] button{
            min-height:44px!important;border-radius:9px!important;font-size:.79rem!important;
          }
          [data-testid="stForm"]{padding:11px 11px!important;border-radius:10px!important}
          [data-testid="stExpander"] summary{min-height:40px!important}
          .cn-empty-state{grid-template-columns:32px 1fr!important;padding:11px 12px!important}
          .cn-empty-state .icon{width:30px!important;height:30px!important}
          [data-testid="stAlert"]{padding:.62rem .7rem!important}
          .cn-workspace-head,.cn-admin-overview-head,.cn-info-guide-head{
            box-shadow:none!important;
          }
        }

        @media(max-width:390px){
          [data-testid="stButton"] button,
          [data-testid="stFormSubmitButton"] button,
          [data-testid="stDownloadButton"] button,
          [data-testid="stLinkButton"] a{
            width:100%!important;
          }
          .cn-section-head,.cn-info-section-title{font-size:.7rem!important}
        }

        /* v384 — Kit clash guidance */
        .cn-kit-summary{
          display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;
          border:1px solid var(--cn98-border);border-radius:12px;background:var(--cn98-surface);
          padding:9px 10px;margin:7px 0 6px;
        }
        .cn-kit-summary > div{display:flex;align-items:baseline;gap:6px;min-width:0}
        .cn-kit-summary .value{font-size:1.05rem;font-weight:860;color:var(--cn98-ink)}
        .cn-kit-summary .label{font-size:.69rem;color:var(--cn98-ink-3);line-height:1.25}
        .cn-kit-summary.attention{border-color:#e7c9a4;background:#fffaf4}
        .cn-admin-match .cn-kit-choice{
          grid-column:1 / -1;display:grid;grid-template-columns:auto 1fr;gap:2px 8px;
          border-top:1px solid var(--cn98-border);padding-top:8px;margin-top:3px;
        }
        .cn-admin-match .cn-kit-choice .label{
          font-size:.63rem;font-weight:800;text-transform:uppercase;letter-spacing:.045em;color:var(--cn98-ink-3)
        }
        .cn-admin-match .cn-kit-choice strong{
          font-size:.75rem;color:var(--cn98-ink);line-height:1.25
        }
        .cn-admin-match .cn-kit-choice small{
          grid-column:2;font-size:.67rem;line-height:1.3;color:var(--cn98-ink-3)
        }
        .cn-admin-match .cn-kit-choice.resolved strong{color:var(--cn98-primary)}
        .cn-admin-match .cn-kit-choice.conflict strong{color:#9a3412}
        @media(max-width:768px){
          .cn-kit-summary{grid-template-columns:1fr;gap:5px}
          .cn-admin-match .cn-kit-choice{grid-template-columns:1fr;gap:1px}
          .cn-admin-match .cn-kit-choice small{grid-column:1}
        }

        /* v385 — Logical flow + no-scroll public primary navigation */
        @media(max-width:680px){
          [class*="st-key-cn_public_primary_nav_shell_"]{
            overflow-x:visible!important;
          }
          [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stSegmentedControl"] > div,
          [class*="st-key-cn_public_primary_nav_shell_"] [data-testid="stButtonGroup"] > div{
            min-width:0!important;
            width:100%!important;
            display:flex!important;
            flex-wrap:wrap!important;
            gap:4px!important;
          }
          [class*="st-key-cn_public_primary_nav_shell_"] button{
            flex:1 1 calc(33.333% - 4px)!important;
            min-width:0!important;
            min-height:38px!important;
            padding:.35rem .35rem!important;
            font-size:.69rem!important;
          }
        }

        /* Keep guidance hierarchy simple: page kicker says the step, content says what to do next. */
        .cn-workspace-head{margin-bottom:11px!important}
        .cn-overview-next{box-shadow:none!important}
        .cn-overview-attention-row{box-shadow:none!important}
        @media(max-width:768px){
          .cn-workspace-head{margin-bottom:9px!important}
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


def inject_public_experience_styles(st):
    """Public follow/live/layout styles with valid, non-nested media queries.

    Extracted from ``render_public_view`` in v294. Keeping the public experience
    rules here avoids growing the application orchestrator and makes responsive
    CSS independently regression-testable.
    """
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
        .cn-my-status{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
        .cn-my-pill{border:1px solid #dbe5df;border-radius:999px;padding:6px 10px;background:#f8fbf9;font-size:.8rem;font-weight:750}
        .cn-venue-card{border:1px solid #e2e8f0;border-radius:14px;padding:11px 12px;margin:7px 0;background:#fff}

        @media(max-width:900px){
          .cn-live-grid{grid-template-columns:1fr}
          .cn-live-head{align-items:flex-start}
          .cn-live-status{display:none}
        }

        /* Tighter desktop rhythm. */
        @media(min-width:901px){
          .cn-public-follow-anchor + div{margin-top:0!important;margin-bottom:2px!important}
          .stApp .block-container{padding-top:.75rem!important;padding-bottom:1.5rem!important}
          .cn-flow-context{margin-top:0!important;margin-bottom:5px!important;padding:9px 12px!important}
          .cn-next-action{margin:0!important;padding:7px 10px!important;min-height:44px!important;display:flex;align-items:center;gap:8px}
          .cn-next-action br{display:none}
          hr{margin:.7rem 0!important}
          [data-testid="stAlert"]{margin-top:.3rem!important;margin-bottom:.45rem!important}
          [data-testid="stVerticalBlock"]{gap:.42rem!important}

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
          .cn-public-summary-row{display:block!important;margin-bottom:10px!important}
          .cn-public-summary-row .public-metric-grid{margin-bottom:8px!important}
          .cn-public-highlights{grid-template-columns:repeat(2,minmax(0,1fr))!important;max-width:none!important;gap:7px!important}
          .cn-public-highlight{padding:8px 9px!important}
          .cn-public-highlight .value{font-size:13px!important}
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
