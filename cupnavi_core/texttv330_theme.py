"""Lightweight Text-TV 330 inspired visual theme for CupNavi v488."""

_PUBLIC_CSS = r"""
/* TEXT-TV 330 FUTURE FOUNDATION V488 */
:root{--cn-tt-bg:#07110c;--cn-tt-panel:#0d1a13;--cn-tt-panel-2:#102319;--cn-tt-line:#294234;--cn-tt-text:#f4f7f5;--cn-tt-muted:#a8b7ad;--cn-tt-green:#79ff9b;--cn-tt-cyan:#65e7ff;--cn-tt-yellow:#ffe66d;--cn-tt-red:#ff7878}
.stApp{background:linear-gradient(rgba(255,255,255,.012) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.012) 1px,transparent 1px),var(--cn-tt-bg)!important;background-size:24px 24px!important}
.cup-hero{background:linear-gradient(180deg,var(--cn-tt-panel-2),var(--cn-tt-panel))!important;border:1px solid var(--cn-tt-line)!important;border-radius:4px!important;box-shadow:none!important}
.cup-hero .title{color:var(--cn-tt-text)!important;letter-spacing:.01em!important}.cup-hero .meta{color:var(--cn-tt-cyan)!important}
.cn-section-head{color:var(--cn-tt-yellow)!important;border-bottom:1px solid var(--cn-tt-line)!important;padding-bottom:5px!important;text-transform:uppercase!important;letter-spacing:.08em!important;font-weight:900!important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p,.stCaption,.stCaption p{color:var(--cn-tt-muted)!important;opacity:1!important}
[data-testid="stWidgetLabel"] p,[data-testid="stWidgetLabel"] label,label[data-testid="stWidgetLabel"]{color:#d8e2dc!important;opacity:1!important}
.cn-public-top-nav + div [data-testid="stButton"] button,.cn-mode-nav-safezone + div [data-testid="stButton"] button{border-radius:4px!important;box-shadow:none!important}
.cn-public-top-nav + div [data-testid="stButton"] button[kind="secondary"]{background:var(--cn-tt-panel)!important;color:var(--cn-tt-text)!important;border-color:var(--cn-tt-line)!important}
.cn-public-top-nav + div [data-testid="stButton"] button[kind="primary"]{background:#143a24!important;color:var(--cn-tt-green)!important;border-color:#3d7c52!important}
[data-testid="stExpander"]:has(.cn-public-filter-marker){background:var(--cn-tt-panel)!important;border-color:var(--cn-tt-line)!important;border-radius:4px!important}
.cn-match-events{border-top-color:var(--cn-tt-line)!important}.cn-events-title{color:var(--cn-tt-cyan)!important}.cn-event-team{background:var(--cn-tt-panel)!important;border-color:var(--cn-tt-line)!important;border-radius:4px!important}.cn-event-team-name{color:var(--cn-tt-text)!important}
@media(max-width:760px){.stApp{background-size:18px 18px!important}.cup-hero{padding:9px 11px!important}.cup-hero .title{font-size:22px!important}.cn-section-head{font-size:.82rem!important}.cn-public-top-nav + div [data-testid="stButton"] button{min-height:44px!important}}


/* V489 · MATCH & RESULT SYSTEM
   Pure CSS. Reuses existing public match, live-strip, favorite-team and table DOM. */
.public-match-card{
  background:var(--cn-tt-panel)!important;
  color:var(--cn-tt-text)!important;
  border:1px solid var(--cn-tt-line)!important;
  border-radius:3px!important;
  box-shadow:none!important;
  padding:9px 10px!important;
  margin:5px 0!important;
}
.public-match-card:hover{border-color:#4d6e5a!important;box-shadow:none!important}
.public-match-card,.public-match-card div,.public-match-card p,
.public-match-card b,.public-match-card small,.public-match-card span{
  color:var(--cn-tt-text)!important;
}
.public-match-card .cn-match-card-top{
  grid-template-columns:72px minmax(0,1fr) 78px!important;
  gap:8px!important;
  padding-bottom:6px!important;
  border-bottom:1px solid var(--cn-tt-line)!important;
}
.public-match-card .cn-match-time{
  color:var(--cn-tt-cyan)!important;
  font-size:18px!important;
  font-weight:950!important;
  letter-spacing:.02em!important;
  font-variant-numeric:tabular-nums!important;
}
.public-match-card .cn-match-place{
  color:var(--cn-tt-muted)!important;
  font-size:10px!important;
  text-transform:uppercase!important;
  letter-spacing:.05em!important;
}
.public-match-card .cn-match-context .match-stage{
  color:var(--cn-tt-yellow)!important;
  font-size:10px!important;
  font-weight:950!important;
  letter-spacing:.08em!important;
}
.public-match-card .cn-match-context .match-number{
  color:#789083!important;
  font-size:9px!important;
}
.public-match-card .cn-match-status{text-align:right!important}
.public-match-card .status-pill{
  border-radius:2px!important;
  padding:3px 6px!important;
  font-size:9px!important;
  font-weight:950!important;
  letter-spacing:.07em!important;
  border:1px solid currentColor!important;
  background:transparent!important;
}
.public-match-card .status-live{color:var(--cn-tt-green)!important}
.public-match-card .status-upcoming{color:var(--cn-tt-cyan)!important}
.public-match-card .status-finished{color:var(--cn-tt-muted)!important}
.public-match-card .cn-match-relative{
  color:var(--cn-tt-green)!important;
  font-size:9px!important;
  font-variant-numeric:tabular-nums!important;
}
.public-match-card .cn-match-teams{
  grid-template-columns:minmax(0,1fr) 70px minmax(0,1fr)!important;
  gap:8px!important;
  margin-top:7px!important;
  align-items:center!important;
}
.public-match-card .public-team-name{
  color:var(--cn-tt-text)!important;
  font-size:15px!important;
  line-height:1.08!important;
  font-weight:850!important;
}
.public-match-card .match-score{
  color:var(--cn-tt-yellow)!important;
  font-size:24px!important;
  line-height:1!important;
  font-weight:950!important;
  text-align:center!important;
  font-variant-numeric:tabular-nums!important;
  letter-spacing:.03em!important;
}
.public-match-card.is-live{
  border-color:#3f8354!important;
  box-shadow:inset 3px 0 0 var(--cn-tt-green)!important;
}
.public-match-card.is-live .match-score{color:var(--cn-tt-green)!important}
.public-match-card.is-finished .match-score{color:var(--cn-tt-yellow)!important}
.public-match-card.is-upcoming .match-score{color:#819389!important;font-size:14px!important;letter-spacing:.09em!important}
.public-match-card .cn-match-kit{border-radius:1px!important;border-color:#72867a!important}
.public-match-card .kit-label,.public-match-card .match-referee,
.public-match-card .match-weather,.public-match-secondary{color:var(--cn-tt-muted)!important}
.public-match-card .cn-match-events-compact{border-top-color:var(--cn-tt-line)!important}
.public-match-card .cn-event-team{background:#0a1510!important;border-color:var(--cn-tt-line)!important}

/* Live / next strip becomes a compact scoreboard rail. */
.cn-live-strip{
  background:transparent!important;
  border:0!important;
  margin:4px 0 7px!important;
}
.cn-live-head{
  background:#0a1510!important;
  border:1px solid var(--cn-tt-line)!important;
  border-radius:3px!important;
  padding:6px 8px!important;
  margin-bottom:4px!important;
}
.cn-live-title{color:var(--cn-tt-yellow)!important;letter-spacing:.08em!important;text-transform:uppercase!important}
.cn-live-subtitle{color:var(--cn-tt-muted)!important}
.cn-live-status{color:var(--cn-tt-green)!important;font-weight:950!important;letter-spacing:.06em!important}
.cn-live-dot{background:var(--cn-tt-green)!important;box-shadow:0 0 0 2px rgba(121,255,155,.12)!important}
.cn-live-grid{gap:5px!important}
.cn-live-card{
  background:var(--cn-tt-panel)!important;
  border:1px solid var(--cn-tt-line)!important;
  border-radius:3px!important;
  box-shadow:none!important;
  padding:7px 8px!important;
}
.cn-live-card.is-live{border-color:#3f8354!important;box-shadow:inset 3px 0 0 var(--cn-tt-green)!important}
.cn-live-time{color:var(--cn-tt-cyan)!important;font-variant-numeric:tabular-nums!important;font-weight:950!important}
.cn-live-date,.cn-live-pitch{color:var(--cn-tt-muted)!important}
.cn-live-teams{color:var(--cn-tt-text)!important;font-weight:850!important}
.cn-live-vs{color:#71857a!important}

/* My Team: one dense favorite panel, no decorative card chrome. */
.cn-follow-shell{
  background:var(--cn-tt-panel)!important;
  border:1px solid var(--cn-tt-line)!important;
  border-radius:3px!important;
  box-shadow:none!important;
}
.cn-follow-kicker{
  color:var(--cn-tt-cyan)!important;
  text-transform:uppercase!important;
  letter-spacing:.08em!important;
  font-weight:950!important;
}
.cn-follow-team{color:var(--cn-tt-text)!important;font-weight:950!important}
.cn-next-card{
  background:#0a1510!important;
  border:1px solid var(--cn-tt-line)!important;
  border-radius:2px!important;
  box-shadow:none!important;
}
.cn-next-meta{color:var(--cn-tt-muted)!important}
.cn-next-teams{color:var(--cn-tt-text)!important;font-weight:850!important}
.cn-next-vs{color:var(--cn-tt-yellow)!important;font-weight:950!important}
.cn-follow-mini{
  border-top-color:var(--cn-tt-line)!important;
  border-bottom-color:var(--cn-tt-line)!important;
}
.cn-follow-mini span{color:var(--cn-tt-muted)!important;text-transform:uppercase!important;letter-spacing:.05em!important}
.cn-follow-mini strong{color:var(--cn-tt-yellow)!important;font-variant-numeric:tabular-nums!important}
.cn-follow-latest-result{
  background:#0a1510!important;
  border:1px solid var(--cn-tt-line)!important;
  border-radius:2px!important;
}
.cn-follow-latest-result .label{color:var(--cn-tt-cyan)!important;text-transform:uppercase!important;letter-spacing:.06em!important}
.cn-follow-latest-result .teams{color:var(--cn-tt-text)!important}
.cn-my-pill{
  background:transparent!important;
  border:1px solid var(--cn-tt-line)!important;
  color:var(--cn-tt-muted)!important;
  border-radius:2px!important;
}

/* Tables: classic result-page scanning, modern spacing. */
.texttv-wrap,.texttv-table-wrap{
  background:var(--cn-tt-panel)!important;
  border:1px solid var(--cn-tt-line)!important;
  border-radius:2px!important;
}
.texttv-table{
  width:100%!important;
  border-collapse:collapse!important;
  background:var(--cn-tt-panel)!important;
  color:var(--cn-tt-text)!important;
  font-variant-numeric:tabular-nums!important;
}
.texttv-table th{
  background:#0a1510!important;
  color:var(--cn-tt-cyan)!important;
  border-bottom:1px solid #476253!important;
  font-size:10px!important;
  text-transform:uppercase!important;
  letter-spacing:.06em!important;
}
.texttv-table td{
  background:transparent!important;
  color:var(--cn-tt-text)!important;
  border-bottom:1px solid #1d3126!important;
}
.texttv-table tbody tr:nth-child(even) td{background:rgba(255,255,255,.018)!important}
.texttv-table tbody tr:hover td{background:#11241a!important;filter:none!important}
.texttv-table td:nth-child(1){color:var(--cn-tt-muted)!important;font-weight:850!important}
.texttv-table td:nth-child(2){font-weight:850!important}
.texttv-table td:nth-child(10){color:var(--cn-tt-yellow)!important;font-weight:950!important}
.texttv-legend{color:var(--cn-tt-muted)!important}

@media(max-width:760px){
  .public-match-card{padding:7px 8px!important;margin:4px 0!important}
  .public-match-card .cn-match-card-top{grid-template-columns:56px minmax(0,1fr) 64px!important;gap:5px!important}
  .public-match-card .cn-match-time{font-size:16px!important}
  .public-match-card .cn-match-place{font-size:9px!important}
  .public-match-card .public-team-name{font-size:14px!important}
  .public-match-card .cn-match-teams{grid-template-columns:minmax(0,1fr) 58px minmax(0,1fr)!important;gap:5px!important}
  .public-match-card .match-score{font-size:21px!important}
  .public-match-card.is-upcoming .match-score{font-size:12px!important}
  .cn-live-card{padding:6px 7px!important}
  .cn-follow-shell{padding:10px!important}
  .texttv-table th,.texttv-table td{padding:7px 6px!important}
}

"""

_CUPDAY_CSS = r"""
/* V488 · Text-TV 330 meets future — Cupday control room */
.cn-admin-page-head{background:linear-gradient(180deg,#102319,#0b1710)!important;border:1px solid #294234!important;border-radius:4px!important;padding:12px 14px!important;box-shadow:none!important}
.cn-admin-page-head .cn-kicker{color:#65e7ff!important;text-transform:uppercase!important;letter-spacing:.09em!important;font-weight:900!important}.cn-admin-page-head h1{color:#f4f7f5!important;letter-spacing:.01em!important}.cn-admin-page-head p{color:#a8b7ad!important}
.cn-day-guide{border-radius:4px!important;border:1px solid #294234!important;background:#0d1a13!important;box-shadow:none!important}.cn-day-guide .eyebrow{color:#65e7ff!important;letter-spacing:.08em!important}.cn-day-guide .title{color:#f4f7f5!important}.cn-day-guide .detail{color:#a8b7ad!important}
.cn-day-kpis{gap:6px!important}.cn-day-kpi{border-radius:4px!important;border:1px solid #294234!important;background:#0d1a13!important;box-shadow:none!important}.cn-day-kpi .label{color:#a8b7ad!important;text-transform:uppercase!important;letter-spacing:.07em!important}.cn-day-kpi .value{color:#f4f7f5!important}.cn-day-kpi.is-live .value{color:#79ff9b!important}.cn-day-kpi.is-attention .value{color:#ffe66d!important}
"""


def public_style_tag() -> str:
    return f"<style>{_PUBLIC_CSS}</style>"


def cupday_style_tag() -> str:
    return f"<style>{_CUPDAY_CSS}</style>"
