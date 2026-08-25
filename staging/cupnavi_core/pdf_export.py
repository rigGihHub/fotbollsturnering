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
