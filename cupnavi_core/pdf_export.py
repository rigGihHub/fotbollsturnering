"""PDF-export för CupNavi-scheman."""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Line, Rect, String


NAVY = colors.HexColor("#172033")
GREEN = colors.HexColor("#166534")
LIGHT_GREEN = colors.HexColor("#DCFCE7")
LIGHT_BG = colors.HexColor("#F6F8FA")
BORDER = colors.HexColor("#D7DEE5")
MUTED = colors.HexColor("#64748B")
WHITE = colors.white


def _safe(value, fallback="-"):
    if value is None or value == "":
        return fallback
    return str(value)


def _dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _result_text(match):
    hs = match.get("home_score")
    aas = match.get("away_score")
    if hs is None or aas is None:
        return "-"
    result = f"{hs}-{aas}"
    hp = match.get("home_penalties")
    ap = match.get("away_penalties")
    if hp is not None and ap is not None:
        result += f" ({hp}-{ap} str)"
    return result


def _section_title(story, text, styles):
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(text, styles["SectionTitle"]))
    story.append(Spacer(1, 2.5 * mm))


def _table(data, widths, header=True):
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 0), (3, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ])
    for row_index in range(1 if header else 0, len(data)):
        if row_index % 2 == 0:
            style.append(("BACKGROUND", (0, row_index), (-1, row_index), LIGHT_BG))
    table.setStyle(TableStyle(style))
    return table


def _page_header_footer(canvas, doc, tournament_name):
    canvas.saveState()
    width, height = landscape(A4)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawString(12 * mm, height - 8 * mm, f"CupNavi - {tournament_name}")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 12 * mm, 7 * mm, f"Sida {doc.page}")
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(12 * mm, 11 * mm, width - 12 * mm, 11 * mm)
    canvas.restoreState()


def build_schedule_pdf(
    tournament,
    matches,
    teams,
    groups,
    referees,
    source_labels,
    source_team_ids,
):
    """Returnera ett komplett PDF-paket som bytes."""
    tournament_name = _safe(tournament.get("name"), "Turnering")
    location = _safe(tournament.get("location"), "Spelort ej angiven")
    date_from = tournament.get("start_date") or tournament.get("tournament_date")
    date_to = tournament.get("end_date") or date_from

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"{tournament_name} - scheman",
        author="CupNavi",
    )

    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "Title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=24, leading=28, textColor=NAVY, alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "SubTitle": ParagraphStyle(
            "SubTitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, leading=15, textColor=MUTED, alignment=TA_CENTER,
        ),
        "SectionTitle": ParagraphStyle(
            "SectionTitle", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=15, leading=18, textColor=GREEN, alignment=TA_LEFT,
            keepWithNext=True,
        ),
        "Small": ParagraphStyle(
            "Small", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=11, textColor=MUTED,
        ),
    }

    team_map = {int(t["id"]): t for t in teams}
    group_map = {int(g["id"]): g for g in groups}
    ref_map = {int(r["id"]): r for r in referees if r.get("id") is not None}
    sorted_matches = sorted(
        matches,
        key=lambda m: (
            m.get("scheduled_start") or "",
            m.get("pitch_number") or 0,
            m.get("id") or 0,
        ),
    )
    display_no = {int(m["id"]): i for i, m in enumerate(sorted_matches, 1)}

    def label(source):
        return _safe(source_labels.get(source), source or "Ej avgjort")

    def match_row(m, number=None):
        start = _dt(m.get("scheduled_start"))
        return [
            number if number is not None else display_no.get(int(m["id"]), "-"),
            start.strftime("%Y-%m-%d") if start else "-",
            start.strftime("%H:%M") if start else "-",
            _safe(m.get("pitch_number")),
            label(m.get("home_source")),
            label(m.get("away_source")),
            _result_text(m),
            _safe(ref_map.get(m.get("referee_id"), {}).get("name") if m.get("referee_id") else None),
            _safe(m.get("stage")),
        ]

    # Cover
    story = [
        Spacer(1, 18 * mm),
        Paragraph(tournament_name, styles["Title"]),
        Paragraph("Komplett schemapaket", styles["SubTitle"]),
        Spacer(1, 5 * mm),
        Paragraph(
            f"{location} | {date_from or '-'}"
            + (f" - {date_to}" if date_to and date_to != date_from else ""),
            styles["SubTitle"],
        ),
        Spacer(1, 10 * mm),
    ]
    summary = [
        ["Matcher", "Lag", "Grupper", "Planer"],
        [
            len(sorted_matches),
            len(teams),
            len(groups),
            len({m.get("pitch_number") for m in sorted_matches if m.get("pitch_number") is not None}),
        ],
    ]
    summary_table = _table(summary, [42 * mm] * 4)
    summary_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 1), (-1, 1), GREEN),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_GREEN),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 7 * mm))
    story.append(Paragraph(
        "PDF:en innehåller hela spelschemat samt separata scheman per grupp, lag, plan, slutspel och domare.",
        styles["Small"],
    ))
    story.append(PageBreak())

    # Overall
    _section_title(story, "Hela spelschemat - datum och tid", styles)
    overall = [["Match", "Datum", "Tid", "Plan", "Hemma", "Borta", "Resultat", "Domare", "Fas"]]
    overall.extend(match_row(m) for m in sorted_matches)
    story.append(_table(
        overall,
        [13*mm, 25*mm, 14*mm, 13*mm, 43*mm, 43*mm, 22*mm, 34*mm, 27*mm],
    ))

    # Groups
    group_matches_exist = any(m.get("stage") == "Gruppspel" for m in sorted_matches)
    if groups and group_matches_exist:
        story.append(PageBreak())
        story.append(Paragraph("Gruppscheman", styles["Title"]))
        for group in groups:
            group_matches = [
                m for m in sorted_matches
                if m.get("stage") == "Gruppspel" and m.get("group_id") == group.get("id")
            ]
            if not group_matches:
                continue
            _section_title(story, _safe(group.get("name"), "Grupp"), styles)
            data = [["Match", "Datum", "Tid", "Plan", "Hemmalag", "Bortalag", "Resultat"]]
            data.extend([
                match_row(m)[:7] for m in group_matches
            ])
            story.append(_table(
                data,
                [15*mm, 28*mm, 15*mm, 15*mm, 55*mm, 55*mm, 24*mm],
            ))

    # Team schedules
    if teams:
        story.append(PageBreak())
        story.append(Paragraph("Lagscheman", styles["Title"]))
        for team in sorted(teams, key=lambda t: str(t.get("name", "")).casefold()):
            team_id = int(team["id"])
            team_matches = [
                m for m in sorted_matches
                if source_team_ids.get(m.get("home_source")) == team_id
                or source_team_ids.get(m.get("away_source")) == team_id
            ]
            if not team_matches:
                continue
            _section_title(story, _safe(team.get("name")), styles)
            data = [["Datum", "Tid", "Plan", "H/B", "Motståndare", "Fas", "Resultat", "Domare"]]
            for m in team_matches:
                start = _dt(m.get("scheduled_start"))
                is_home = source_team_ids.get(m.get("home_source")) == team_id
                opponent = label(m.get("away_source") if is_home else m.get("home_source"))
                referee = ref_map.get(m.get("referee_id"), {}).get("name") if m.get("referee_id") else None
                data.append([
                    start.strftime("%Y-%m-%d") if start else "-",
                    start.strftime("%H:%M") if start else "-",
                    _safe(m.get("pitch_number")),
                    "Hemma" if is_home else "Borta",
                    opponent,
                    _safe(m.get("stage")),
                    _result_text(m),
                    _safe(referee),
                ])
            story.append(_table(
                data,
                [28*mm, 15*mm, 15*mm, 22*mm, 52*mm, 30*mm, 24*mm, 42*mm],
            ))

    # Pitch schedules
    pitches = sorted({
        int(m["pitch_number"])
        for m in sorted_matches
        if m.get("pitch_number") is not None
    })
    if pitches:
        story.append(PageBreak())
        story.append(Paragraph("Planscheman", styles["Title"]))
        for pitch in pitches:
            pitch_matches = [m for m in sorted_matches if int(m.get("pitch_number") or 0) == pitch]
            _section_title(story, f"Plan {pitch}", styles)
            data = [["Datum", "Tid", "Match", "Hemmalag", "Bortalag", "Fas", "Resultat"]]
            for m in pitch_matches:
                row = match_row(m)
                data.append([row[1], row[2], row[0], row[4], row[5], row[8], row[6]])
            story.append(_table(
                data,
                [28*mm, 15*mm, 15*mm, 55*mm, 55*mm, 32*mm, 25*mm],
            ))

    # Playoffs
    playoff_matches = [m for m in sorted_matches if m.get("stage") != "Gruppspel"]
    if playoff_matches:
        story.append(PageBreak())
        story.append(Paragraph("Slutspelsschema", styles["Title"]))
        data = [["Match", "Datum", "Tid", "Plan", "Hemmalag", "Bortalag", "Fas", "Resultat"]]
        for m in playoff_matches:
            row = match_row(m)
            data.append([row[0], row[1], row[2], row[3], row[4], row[5], row[8], row[6]])
        story.append(_table(
            data,
            [15*mm, 28*mm, 15*mm, 15*mm, 52*mm, 52*mm, 32*mm, 25*mm],
        ))

    # Referee schedules
    refs_with_matches = []
    for ref in referees:
        ref_matches = [m for m in sorted_matches if m.get("referee_id") == ref.get("id")]
        if ref_matches:
            refs_with_matches.append((ref, ref_matches))
    if refs_with_matches:
        story.append(PageBreak())
        story.append(Paragraph("Domarschema", styles["Title"]))
        for ref, ref_matches in sorted(refs_with_matches, key=lambda item: str(item[0].get("name", "")).casefold()):
            _section_title(story, _safe(ref.get("name")), styles)
            data = [["Datum", "Tid", "Plan", "Match", "Hemmalag", "Bortalag", "Fas"]]
            for m in ref_matches:
                row = match_row(m)
                data.append([row[1], row[2], row[3], row[0], row[4], row[5], row[8]])
            story.append(_table(
                data,
                [28*mm, 15*mm, 15*mm, 15*mm, 55*mm, 55*mm, 32*mm],
            ))

    doc.build(
        story,
        onFirstPage=lambda c, d: _page_header_footer(c, d, tournament_name),
        onLaterPages=lambda c, d: _page_header_footer(c, d, tournament_name),
    )
    return buffer.getvalue()


# --- Premium cup program ---------------------------------------------------
GOLD = colors.HexColor("#B08A2E")
PALE_GOLD = colors.HexColor("#F8F2E6")
PALE_BLUE = colors.HexColor("#EEF4F8")
INK = colors.HexColor("#0F172A")


def _program_styles():
    base = getSampleStyleSheet()
    return {
        "HeroEyebrow": ParagraphStyle(
            "HeroEyebrow", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=colors.HexColor("#D8C48D"), spaceAfter=4,
        ),
        "HeroTitle": ParagraphStyle(
            "HeroTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=27, leading=29, textColor=WHITE, alignment=TA_LEFT, spaceAfter=6,
        ),
        "HeroMeta": ParagraphStyle(
            "HeroMeta", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=WHITE,
        ),
        "Section": ParagraphStyle(
            "ProgramSection", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=14, leading=17, textColor=NAVY, spaceBefore=5, spaceAfter=5,
        ),
        "Body": ParagraphStyle(
            "ProgramBody", parent=base["Normal"], fontName="Helvetica",
            fontSize=8.5, leading=11.5, textColor=INK,
        ),
        "Small": ParagraphStyle(
            "ProgramSmall", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.5, leading=10, textColor=MUTED,
        ),
        "CardLabel": ParagraphStyle(
            "ProgramCardLabel", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=6.5, leading=8, textColor=GOLD,
        ),
        "CardValue": ParagraphStyle(
            "ProgramCardValue", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=10, leading=12, textColor=INK,
        ),
    }


def _program_header_footer(canvas, doc, tournament_name, date_label):
    canvas.saveState()
    width, _height = A4
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(14 * mm, 10 * mm, width - 14 * mm, 10 * mm)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(14 * mm, 6.5 * mm, f"{tournament_name}  ·  {date_label}")
    canvas.drawRightString(width - 14 * mm, 6.5 * mm, f"CupNavi  ·  Sida {doc.page}")
    canvas.restoreState()


def _program_table(data, widths, *, accent=NAVY, font_size=7.4, first_col_bold=False):
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row in range(1, len(data)):
        if row % 2 == 0:
            style.append(("BACKGROUND", (0, row), (-1, row), PALE_BLUE))
    if first_col_bold:
        style.append(("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table


def _team_chip(team, styles):
    name = _safe(team.get("name"), "Lag")
    color = team.get("primary_color") or "#D7DEE5"
    try:
        swatch = colors.HexColor(str(color))
    except Exception:
        swatch = BORDER
    d = Drawing(8 * mm, 5 * mm)
    d.add(Rect(0, 0.8 * mm, 3.2 * mm, 3.2 * mm, rx=1, ry=1, fillColor=swatch, strokeColor=BORDER, strokeWidth=.4))
    return Table([[d, Paragraph(name, styles["Body"])]], colWidths=[8*mm, 62*mm], style=TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 2), ("TOPPADDING", (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
    ]))


def _bracket_drawing(playoff_matches, label_fn):
    """Compact visual bracket for the first two semifinals + final when available."""
    semis = [m for m in playoff_matches if "semi" in str(m.get("stage", "")).casefold()]
    final = next((m for m in playoff_matches if str(m.get("stage", "")).casefold() == "final"), None)
    if len(semis) < 2 or final is None:
        return None
    width, height = 178 * mm, 42 * mm
    d = Drawing(width, height)
    left_x, mid_x, right_x = 2*mm, 77*mm, 132*mm
    box_w, box_h = 58*mm, 11*mm
    ys = [27*mm, 6*mm]
    for i, m in enumerate(semis[:2]):
        y = ys[i]
        d.add(Rect(left_x, y, box_w, box_h, fillColor=PALE_BLUE, strokeColor=NAVY, strokeWidth=.6))
        d.add(String(left_x+2*mm, y+6.7*mm, label_fn(m.get("home_source"))[:33], fontName="Helvetica-Bold", fontSize=6.5, fillColor=INK))
        d.add(String(left_x+2*mm, y+2.2*mm, label_fn(m.get("away_source"))[:33], fontName="Helvetica", fontSize=6.3, fillColor=INK))
        center_y = y + box_h/2
        target_y = height/2
        d.add(Line(left_x+box_w, center_y, mid_x, center_y, strokeColor=GOLD, strokeWidth=.8))
        d.add(Line(mid_x, center_y, mid_x, target_y, strokeColor=GOLD, strokeWidth=.8))
        d.add(Line(mid_x, target_y, right_x, target_y, strokeColor=GOLD, strokeWidth=.8))
    d.add(Rect(right_x, height/2-box_h/2, 42*mm, box_h, fillColor=PALE_GOLD, strokeColor=GOLD, strokeWidth=.8))
    final_start = _dt(final.get("scheduled_start"))
    final_text = "FINAL" + (f"  {final_start.strftime('%H:%M')}" if final_start else "")
    d.add(String(right_x+21*mm, height/2+1.4*mm, final_text, textAnchor="middle", fontName="Helvetica-Bold", fontSize=7.2, fillColor=INK))
    return d


def build_cup_program_pdf(
    tournament,
    matches,
    teams,
    groups,
    referees,
    source_labels,
    source_team_ids,
    *,
    rules=None,
    pitches=None,
):
    """Create a polished portrait A4 cup program from live CupNavi data.

    The layout intentionally behaves like an official tournament programme rather than
    a database export: overview -> participants -> group schedule -> playoffs -> tables/rules.
    """
    rules = rules or {}
    pitches = pitches or []
    styles = _program_styles()
    tournament_name = _safe(tournament.get("name"), "CupNavi Cup")
    location = _safe(tournament.get("location"), "Spelort")
    start_date = tournament.get("start_date") or tournament.get("tournament_date") or ""
    end_date = tournament.get("end_date") or start_date
    date_label = str(start_date or "") + (f" – {end_date}" if end_date and end_date != start_date else "")

    sorted_matches = sorted(matches, key=lambda m: (m.get("scheduled_start") or "", m.get("pitch_number") or 0, m.get("id") or 0))
    group_matches = [m for m in sorted_matches if str(m.get("stage")) == "Gruppspel"]
    playoff_matches = [m for m in sorted_matches if str(m.get("stage")) != "Gruppspel"]
    team_map = {int(t["id"]): t for t in teams if t.get("id") is not None}
    group_map = {int(g["id"]): g for g in groups if g.get("id") is not None}
    pitch_map = {int(p.get("pitch_number")): _safe(p.get("name"), f"Plan {p.get('pitch_number')}") for p in pitches if p.get("pitch_number") is not None}

    def label(source):
        return _safe(source_labels.get(source), source or "Ej avgjort")

    def pitch_name(no):
        if no is None:
            return "–"
        return pitch_map.get(int(no), f"Plan {no}")

    def kick(m):
        value = _dt(m.get("scheduled_start"))
        return value.strftime("%H:%M") if value else "–"

    first_kick = kick(sorted_matches[0]) if sorted_matches else "–"
    last_kick = kick(sorted_matches[-1]) if sorted_matches else "–"
    pitch_count = len({m.get("pitch_number") for m in sorted_matches if m.get("pitch_number") is not None}) or len(pitches)
    halves = int(rules.get("halves") or 2)
    mins = int(rules.get("minutes_per_half") or 0)
    match_time = f"{halves}×{mins} min" if mins else "–"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=14*mm, rightMargin=14*mm,
        topMargin=13*mm, bottomMargin=14*mm,
        title=f"{tournament_name} – cupprogram", author="CupNavi",
    )
    story = []

    # Hero / identity block
    hero = Table([[Paragraph("OFFICIELLT CUPPROGRAM", styles["HeroEyebrow"])],
                  [Paragraph(tournament_name.upper(), styles["HeroTitle"])],
                  [Paragraph(f"{location}  ·  {date_label or 'Datum ej angivet'}", styles["HeroMeta"])]],
                 colWidths=[182*mm], rowHeights=[8*mm, 17*mm, 9*mm])
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("BOX", (0,0), (-1,-1), 0, NAVY),
        ("LEFTPADDING", (0,0), (-1,-1), 7*mm),
        ("RIGHTPADDING", (0,0), (-1,-1), 7*mm),
        ("TOPPADDING", (0,0), (-1,-1), 2*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1*mm),
        ("LINEBELOW", (0,-1), (-1,-1), 2.2, GOLD),
    ]))
    story += [hero, Spacer(1, 5*mm)]

    cards = [
        ("FÖRSTA AVSPARK", first_kick),
        ("GRUPPSPEL", match_time),
        ("LAG / GRUPPER", f"{len(teams)} / {len(groups)}"),
        ("PLANER", str(pitch_count or "–")),
        ("SISTA AVSPARK", last_kick),
    ]
    card_cells = []
    for title, value in cards:
        card_cells.append([Paragraph(title, styles["CardLabel"]), Paragraph(str(value), styles["CardValue"])])
    card_table = Table([card_cells], colWidths=[36.4*mm]*5)
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), PALE_GOLD),
        ("BOX", (0,0), (-1,-1), .4, colors.HexColor("#DACBA5")),
        ("INNERGRID", (0,0), (-1,-1), .35, colors.HexColor("#DACBA5")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 3*mm), ("RIGHTPADDING", (0,0), (-1,-1), 2*mm),
        ("TOPPADDING", (0,0), (-1,-1), 2.5*mm), ("BOTTOMPADDING", (0,0), (-1,-1), 2.5*mm),
    ]))
    story += [card_table, Spacer(1, 5*mm)]

    # Pitch/location strip
    if pitches:
        pitch_rows = []
        for p in pitches:
            details = _safe(p.get("address"), "Adress ej angiven")
            pitch_rows.append([Paragraph(f"<b>{_safe(p.get('name'), 'Plan')}</b>", styles["Body"]), Paragraph(details, styles["Small"])])
        pitch_table = Table(pitch_rows, colWidths=[55*mm, 127*mm])
        pitch_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FAFBFC")),
            ("BOX", (0,0), (-1,-1), .4, BORDER), ("INNERGRID", (0,0), (-1,-1), .3, BORDER),
            ("LEFTPADDING", (0,0), (-1,-1), 3*mm), ("RIGHTPADDING", (0,0), (-1,-1), 3*mm),
            ("TOPPADDING", (0,0), (-1,-1), 2*mm), ("BOTTOMPADDING", (0,0), (-1,-1), 2*mm),
        ]))
        story += [pitch_table, Spacer(1, 4*mm)]

    # Groups / participants
    if groups:
        story.append(Paragraph("GRUPPER", styles["Section"]))
        group_blocks = []
        for group in groups:
            gid = int(group["id"])
            members = [t for t in teams if t.get("group_id") == gid]
            rows = [[Paragraph(f"<b>{_safe(group.get('name'), 'Grupp')}</b>", styles["Body"])]]
            for t in members:
                rows.append([_team_chip(t, styles)])
            tbl = Table(rows, colWidths=[86*mm])
            accent = NAVY if len(group_blocks) % 2 == 0 else GOLD
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), accent), ("TEXTCOLOR", (0,0), (-1,0), WHITE),
                ("BOX", (0,0), (-1,-1), .4, BORDER), ("INNERGRID", (0,0), (-1,-1), .3, BORDER),
                ("LEFTPADDING", (0,0), (-1,-1), 3*mm), ("RIGHTPADDING", (0,0), (-1,-1), 3*mm),
                ("TOPPADDING", (0,0), (-1,-1), 2*mm), ("BOTTOMPADDING", (0,0), (-1,-1), 2*mm),
            ]))
            group_blocks.append(tbl)
        paired = []
        for i in range(0, len(group_blocks), 2):
            paired.append([group_blocks[i], group_blocks[i+1] if i+1 < len(group_blocks) else ""])
        story += [Table(paired, colWidths=[89*mm, 89*mm], hAlign="LEFT", style=TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 3*mm), ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3*mm),
        ])), Spacer(1, 2*mm)]

    # Group schedule
    if group_matches:
        story.append(Paragraph("GRUPPSPEL", styles["Section"]))
        data = [["TID", "GRP", "HEMMA", "BORTA", "PLAN", "RESULTAT"]]
        for m in group_matches:
            group_name = _safe(group_map.get(int(m.get("group_id") or 0), {}).get("name"), "")
            group_short = group_name.replace("Grupp", "").strip() or group_name
            data.append([kick(m), group_short, label(m.get("home_source")), label(m.get("away_source")), pitch_name(m.get("pitch_number")), _result_text(m)])
        story.append(_program_table(data, [15*mm, 13*mm, 51*mm, 51*mm, 30*mm, 22*mm], accent=NAVY, font_size=7.2, first_col_bold=True))

    if playoff_matches:
        story += [PageBreak(), Paragraph("SLUTSPEL", styles["Section"])]
        pdata = [["TID", "PLAN", "MATCH", "HEMMA", "BORTA", "RESULTAT"]]
        for m in playoff_matches:
            pdata.append([kick(m), pitch_name(m.get("pitch_number")), _safe(m.get("stage")), label(m.get("home_source")), label(m.get("away_source")), _result_text(m)])
        story.append(_program_table(pdata, [15*mm, 29*mm, 32*mm, 43*mm, 43*mm, 20*mm], accent=NAVY, font_size=7.0, first_col_bold=True))
        bracket = _bracket_drawing(playoff_matches, label)
        if bracket is not None:
            story += [Spacer(1, 5*mm), Paragraph("VÄGEN TILL FINALEN", styles["Section"]), bracket]

    # Blank/printable tables are useful before kickoff, while completed scores remain visible in schedule.
    if groups:
        story += [Spacer(1, 5*mm), Paragraph("TABELLER", styles["Section"])]
        tables = []
        for idx, group in enumerate(groups):
            gid = int(group["id"])
            members = [t for t in teams if t.get("group_id") == gid]
            rows = [["LAG", "S", "V", "O", "F", "MÅL", "P"]]
            rows.extend([[_safe(t.get("name")), "", "", "", "", "", ""] for t in members])
            tables.append(_program_table(rows, [35*mm, 7*mm, 7*mm, 7*mm, 7*mm, 15*mm, 8*mm], accent=NAVY if idx % 2 == 0 else GOLD, font_size=6.8))
        paired = []
        for i in range(0, len(tables), 2):
            paired.append([tables[i], tables[i+1] if i+1 < len(tables) else ""])
        story.append(Table(paired, colWidths=[89*mm,89*mm], style=TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 3*mm), ("TOPPADDING", (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3*mm),
        ])))

    practical = []
    min_rest = int(rules.get("minimum_team_rest_minutes") or 0)
    if min_rest:
        practical.append(f"<b>Vila.</b> CupNavi planerar minst {min_rest} minuters lagvila enligt tävlingsinställningarna.")
    if rules.get("synchronized_pitch_times"):
        practical.append("<b>Avsparkstider.</b> Planerna använder synkroniserade avsparkstider.")
    if rules.get("consider_pitch_travel"):
        buffer_minutes = int(rules.get("pitch_travel_buffer_minutes") or 0)
        practical.append(f"<b>Resor mellan planer.</b> Restid tas med i schemat, inklusive {buffer_minutes} minuters extra marginal.")
    tiebreak = tournament.get("table_tiebreak")
    if tiebreak:
        practical.append(f"<b>Skiljeregler.</b> {_safe(tiebreak)}.")
    playoff_rule = tournament.get("playoff_tie_rule")
    if playoff_matches and playoff_rule:
        practical.append(f"<b>Oavgjort i slutspel.</b> {_safe(playoff_rule)}.")
    if tournament.get("public_information"):
        practical.append(f"<b>Arrangörsinformation.</b> {_safe(tournament.get('public_information'))}")
    if practical:
        story += [Spacer(1, 4*mm), Paragraph("ATT TÄNKA PÅ", styles["Section"])]
        for text in practical:
            story.append(Paragraph(f"• {text}", styles["Body"]))
            story.append(Spacer(1, 1.3*mm))

    doc.build(
        story,
        onFirstPage=lambda c, d: _program_header_footer(c, d, tournament_name, date_label),
        onLaterPages=lambda c, d: _program_header_footer(c, d, tournament_name, date_label),
    )
    return buffer.getvalue()
