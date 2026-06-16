from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import cm
import io
from datetime import datetime

ZONE_COLORS = {
    "Green" : colors.HexColor("#2ECC71"),
    "Yellow": colors.HexColor("#F1C40F"),
    "Red"   : colors.HexColor("#E74C3C"),
}


def generate_report(analyze_result: dict, compare_result: dict = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=18, spaceAfter=6, textColor=colors.HexColor("#1a1a2e"),
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=13, spaceAfter=4, textColor=colors.HexColor("#2C4770"),
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, spaceAfter=4, leading=16,
    )
    alert_style = ParagraphStyle(
        "Alert", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#C0392B"),
        spaceAfter=4, leading=16,
    )

    story = []

    # ── Header ─────────────────────────────────────────────
    story.append(Paragraph("Environmental Livability Assessment Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y  %H:%M')} &nbsp;|&nbsp; "
        f"Model: UNet++ EfficientNet-B4 &nbsp;|&nbsp; Resolution: 10m (Sentinel-2)",
        body_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CCCCCC")))
    story.append(Spacer(1, 0.3*cm))

    # ── Livability Summary ─────────────────────────────────
    liv = analyze_result
    zone  = liv["zone"]
    score = liv["score"]
    zone_color = ZONE_COLORS.get(zone, colors.gray)

    story.append(Paragraph("Livability Assessment", h2_style))

    summary_data = [
        ["Livability Score", "Zone", "Total Area"],
        [
            f"{score:.4f}",
            zone,
            f"{liv['total_km2']:.2f} km²",
        ]
    ]
    summary_table = Table(summary_data, colWidths=[5*cm, 5*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#2C4770")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0), 11),
        ("BACKGROUND",  (1,1), (1,1), zone_color),
        ("FONTNAME",    (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,1), (-1,1), 13),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#F8F8F8")]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Land Cover Breakdown ───────────────────────────────
    story.append(Paragraph("Land Cover Breakdown", h2_style))

    lc_data = [["Class", "Coverage (%)", "Area (km²)"]]
    for cls in ["Water", "Trees", "Buildings", "Open Land"]:
        lc_data.append([
            cls,
            f"{liv['pct'][cls]:.2f}%",
            f"{liv['area_km2'][cls]:.4f} km²",
        ])

    lc_table = Table(lc_data, colWidths=[5*cm, 5*cm, 5*cm])
    row_bg = [
        colors.HexColor("#D6E8FA"),  # Water   — blue
        colors.HexColor("#D6F0D6"),  # Trees   — green
        colors.HexColor("#FAD6D6"),  # Buildings — red
        colors.HexColor("#FAF0D6"),  # Open Land — yellow
    ]
    lc_style = [
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#2C4770")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
    ]
    for i, bg in enumerate(row_bg):
        lc_style.append(("BACKGROUND", (0, i+1), (-1, i+1), bg))
    lc_table.setStyle(TableStyle(lc_style))
    story.append(lc_table)
    story.append(Spacer(1, 0.3*cm))

    # ── Alerts ─────────────────────────────────────────────
    if liv.get("alerts"):
        story.append(Paragraph("Alerts", h2_style))
        for alert in liv["alerts"]:
            story.append(Paragraph(f"⚠ {alert}", alert_style))
        story.append(Spacer(1, 0.3*cm))

    # ── Temporal Change (if provided) ─────────────────────
    if compare_result:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("Temporal Change Analysis (2017 vs 2025)", h2_style))

        chg = compare_result
        ch_data = [["Class", "2017 Area", "2025 Area", "Change (km²)", "Change (%)"]]
        for cls in ["Water", "Trees", "Buildings", "Open Land"]:
            delta = chg["delta_km2"][cls]
            dpct  = chg["delta_pct"][cls]
            sign  = "+" if delta >= 0 else ""
            ch_data.append([
                cls,
                f"{chg['old_area_km2'][cls]:.4f} km²",
                f"{chg['new_area_km2'][cls]:.4f} km²",
                f"{sign}{delta:.4f} km²",
                f"{sign}{dpct:.2f}%",
            ])

        ch_table = Table(ch_data, colWidths=[3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3*cm])
        ch_table.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#2C4770")),
            ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
            ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN",        (0,0), (-1,-1), "CENTER"),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.HexColor("#F8F8F8"), colors.white]),
            ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ]))
        story.append(ch_table)
        story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph(
            f"Total changed area: {chg['change_pct']:.2f}% of region", body_style
        ))

        if chg.get("alerts"):
            story.append(Paragraph("Change Alerts", h2_style))
            for alert in chg["alerts"]:
                story.append(Paragraph(f"⚠ {alert}", alert_style))

    # ── Footer ─────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
    story.append(Paragraph(
        "AI-Based Environmental Livability Assessment — Bangladesh | "
        "Model: UNet++ with EfficientNet-B4 | mIoU: 0.8834",
        ParagraphStyle("footer", parent=styles["Normal"],
                       fontSize=8, textColor=colors.gray)
    ))

    doc.build(story)
    return buf.getvalue()
