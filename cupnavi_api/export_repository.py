"""Authenticated CupNavi document export built on the canonical API repository."""
from __future__ import annotations

import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .admin_repository import _has_tournament_access
from .repository import all_rows, one


def _text(value) -> str:
    return "" if value is None else str(value)


def _safe(value) -> str:
    return escape(_text(value))


def _team_name(source, teams_by_id: dict[int, str]) -> str:
    value = _text(source).strip()
    if value.startswith("team:"):
        try:
            return teams_by_id.get(int(value.split(":", 1)[1]), value)
        except ValueError:
            pass
    return value or "TBD"


def export_snapshot(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    tournament = one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    if not tournament:
        return None
    groups = all_rows("SELECT id,name,age_class FROM groups WHERE tournament_id=? ORDER BY name,id", (int(tournament_id),))
    teams = all_rows("SELECT id,name,group_id,age_class FROM teams WHERE tournament_id=? ORDER BY name,id", (int(tournament_id),))
    matches = all_rows(
        """SELECT id,stage,group_id,round_no,match_no,home_source,away_source,scheduled_start,
                  pitch_number,home_score,away_score,home_penalties,away_penalties
           FROM matches WHERE tournament_id=?
           ORDER BY COALESCE(scheduled_start,''),stage,round_no,match_no,id""",
        (int(tournament_id),),
    )
    pitches = all_rows(
        "SELECT pitch_number,name,address FROM pitches WHERE tournament_id=? ORDER BY pitch_number",
        (int(tournament_id),),
    )
    return {"tournament": tournament, "groups": groups, "teams": teams, "matches": matches, "pitches": pitches}


def build_cup_pdf(account_id: int, tournament_id: int):
    data = export_snapshot(account_id, tournament_id)
    if data is None:
        return None

    tournament = data["tournament"]
    groups = data["groups"]
    teams = data["teams"]
    matches = data["matches"]
    pitches = data["pitches"]
    teams_by_id = {int(t["id"]): _text(t.get("name")) for t in teams}
    groups_by_id = {int(g["id"]): _text(g.get("name")) for g in groups}

    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("CupNaviTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=22, leading=26, spaceAfter=10)
    h2 = ParagraphStyle("CupNaviH2", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=10, spaceAfter=6)
    body = styles["BodyText"]
    story = [Paragraph(_safe(tournament.get("name")) or "CupNavi", title)]

    meta = []
    dates = " – ".join(x for x in (_text(tournament.get("start_date")), _text(tournament.get("end_date"))) if x)
    if dates: meta.append(["Datum", dates])
    if tournament.get("organizer"): meta.append(["Arrangör", _text(tournament.get("organizer"))])
    if tournament.get("arena_address"): meta.append(["Plats", _text(tournament.get("arena_address"))])
    if meta:
        table = Table(meta, colWidths=[32*mm, 135*mm])
        table.setStyle(TableStyle([("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("VALIGN",(0,0),(-1,-1),"TOP"),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        story += [table, Spacer(1, 4*mm)]
    if tournament.get("public_information"):
        story += [Paragraph(_safe(tournament.get("public_information")), body), Spacer(1, 4*mm)]

    story.append(Paragraph("Grupper och lag", h2))
    teams_by_group: dict[int | None, list[dict]] = {}
    for team in teams:
        teams_by_group.setdefault(team.get("group_id"), []).append(team)
    for group in groups:
        gid = int(group["id"])
        story.append(Paragraph(f"<b>{_safe(group.get('name'))}</b>", body))
        names = ", ".join(_text(t.get("name")) for t in teams_by_group.get(gid, [])) or "Inga lag"
        story.append(Paragraph(_safe(names), body))
        story.append(Spacer(1, 2*mm))
    ungrouped = teams_by_group.get(None, [])
    if ungrouped:
        story.append(Paragraph("<b>Ogrupperade lag</b>", body))
        story.append(Paragraph(_safe(", ".join(_text(t.get("name")) for t in ungrouped)), body))

    if pitches:
        story.append(Paragraph("Planer", h2))
        rows = [["Plan", "Namn", "Adress"]] + [[_text(p.get("pitch_number")), _text(p.get("name")), _text(p.get("address"))] for p in pitches]
        table = Table(rows, repeatRows=1, colWidths=[20*mm, 55*mm, 90*mm])
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E5E7EB")),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#9CA3AF")),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),8)]))
        story.append(table)

    story += [PageBreak(), Paragraph("Spelschema och resultat", h2)]
    rows = [["Tid", "Plan", "Fas", "Match", "Resultat"]]
    for match in matches:
        home = _team_name(match.get("home_source"), teams_by_id)
        away = _team_name(match.get("away_source"), teams_by_id)
        score = ""
        if match.get("home_score") is not None and match.get("away_score") is not None:
            score = f"{match['home_score']}–{match['away_score']}"
            if match.get("home_penalties") is not None or match.get("away_penalties") is not None:
                score += f" ({_text(match.get('home_penalties'))}–{_text(match.get('away_penalties'))} str.)"
        stage = _text(match.get("stage"))
        group_id = match.get("group_id")
        if group_id is not None and int(group_id) in groups_by_id:
            stage = f"{stage} · {groups_by_id[int(group_id)]}"
        rows.append([_text(match.get("scheduled_start")), _text(match.get("pitch_number")), stage, f"{home} – {away}", score])
    if len(rows) == 1:
        rows.append(["", "", "", "Inga matcher skapade", ""])
    table = Table(rows, repeatRows=1, colWidths=[35*mm, 14*mm, 38*mm, 62*mm, 24*mm])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#111827")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#D1D5DB")),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),7),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F9FAFB")])]))
    story.append(table)

    doc.build(story)
    raw_name = _text(tournament.get("public_slug")) or _text(tournament.get("name")) or f"cup-{tournament_id}"
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_name.strip()).strip("-.") or f"cup-{tournament_id}"
    return {"filename": safe_name + ".pdf", "content": out.getvalue()}
