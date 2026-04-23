#Branded PDF output with Forest/Scope3/Primer palette, traffic-light emissions colours, ranked table, unmodelled flagging, and separate analyse vs discover layouts.
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Scope3 Brand Colours ──────────────────────────────────────────────────────
FOREST    = colors.HexColor("#0C0E12")   # near-black, primary background
SCOPE3    = colors.HexColor("#DBFC01")   # signature yellow-green
LIME      = colors.HexColor("#82E500")
KELLY     = colors.HexColor("#54C200")
EMERALD   = colors.HexColor("#137300")
PRIMER    = colors.HexColor("#FAFFF0")   # off-white
WHITE     = colors.white
LIGHT_GREY = colors.HexColor("#E8EDE0")

# ── Styles ────────────────────────────────────────────────────────────────────
def make_styles():
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=SCOPE3,
            leading=34,
            spaceAfter=6
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="Helvetica",
            fontSize=13,
            textColor=PRIMER,
            leading=18,
            spaceAfter=4
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=SCOPE3,
            leading=18,
            spaceBefore=14,
            spaceAfter=6
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=FOREST,
            leading=14,
            spaceAfter=4
        ),
        "body_white": ParagraphStyle(
            "body_white",
            fontName="Helvetica",
            fontSize=10,
            textColor=PRIMER,
            leading=14,
            spaceAfter=4
        ),
        "small": ParagraphStyle(
            "small",
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#666666"),
            leading=11
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=FOREST,
        ),
        "flag": ParagraphStyle(
            "flag",
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=colors.HexColor("#888888"),
            leading=12
        ),
    }

# ── Helpers ───────────────────────────────────────────────────────────────────

def _emissions_colour(gco2pm: float) -> colors.Color:
    """Traffic-light colour based on emissions level."""
    if gco2pm < 50:
        return LIME
    elif gco2pm < 150:
        return colors.HexColor("#FFA500")
    else:
        return colors.HexColor("#E53935")


def _percentile_label(p) -> str:
    if p is None:
        return "N/A"
    if p <= 10:
        return f"Top {p}%"
    return f"{p}th pct"


def _rank_medal(rank: int) -> str:
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    return medals.get(rank, str(rank))


# ── Cover Page ────────────────────────────────────────────────────────────────

def _cover_page(story, styles, mode: str, meta: dict):
    # Dark background block via a 1-row table
    title_text = "Inventory Carbon Report" if mode == "analyse" else "Campaign Inventory Recommendations"
    mode_label = "Analysis Mode" if mode == "analyse" else "Discover Mode"
    generated = datetime.now().strftime("%d %B %Y, %H:%M")

    cover_data = [[
        Paragraph(f"<b>Scope3</b>", ParagraphStyle("s3", fontName="Helvetica-Bold", fontSize=11, textColor=SCOPE3)),
        Paragraph(f"{generated}", ParagraphStyle("date", fontName="Helvetica", fontSize=9, textColor=PRIMER, alignment=TA_RIGHT))
    ]]
    header_table = Table(cover_data, colWidths=[100*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), FOREST),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (0,-1), 10),
        ("RIGHTPADDING", (-1,0), (-1,-1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 20*mm))

    story.append(Paragraph(title_text, styles["cover_title"]))
    story.append(Paragraph(mode_label, styles["cover_sub"]))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=SCOPE3))
    story.append(Spacer(1, 6*mm))

    if meta.get("brief"):
        story.append(Paragraph(f"<b>Brief:</b> {meta['brief']}", styles["body"]))
    if meta.get("total_properties"):
        story.append(Paragraph(f"<b>Properties analysed:</b> {meta['total_properties']}", styles["body"]))
    if meta.get("total_modelled") is not None:
        story.append(Paragraph(f"<b>Modelled by Scope3:</b> {meta['total_modelled']}", styles["body"]))
    if meta.get("total_unmodelled"):
        story.append(Paragraph(f"<b>Unmodelled (flagged):</b> {meta['total_unmodelled']}", styles["body"]))

    story.append(Spacer(1, 8*mm))


# ── Ranked Inventory Table ────────────────────────────────────────────────────

def _inventory_table(story, styles, ranked: list, include_category: bool = False):
    story.append(Paragraph("Ranked Inventory", styles["section_heading"]))
    story.append(Paragraph(
        "Properties ranked from lowest to highest carbon emissions (gCO<sub rise='2' size='7'>2</sub>PM).",
        styles["body"]
    ))
    story.append(Spacer(1, 3*mm))

    # Table headers
    headers = ["#", "Property", "gCO2PM", "Percentile", "Channel", "MFA"]
    col_widths = [10*mm, 55*mm, 25*mm, 25*mm, 20*mm, 15*mm]
    if include_category:
        headers.insert(2, "Category")
        col_widths.insert(2, 30*mm)
        col_widths[1] = 40*mm  # shrink property column

    table_data = [[Paragraph(h, styles["table_header"]) for h in headers]]

    for i, prop in enumerate(ranked):
        rank = i + 1
        gco2pm = prop.get("gco2pm", 0)
        mfa = "Yes" if prop.get("is_mfa") else "No"
        row = [
            Paragraph(str(rank), styles["body"]),
            Paragraph(prop.get("inventory_id", ""), styles["body"]),
            Paragraph(f"{gco2pm:.1f}", ParagraphStyle("num", fontName="Helvetica-Bold", fontSize=10, textColor=_emissions_colour(gco2pm))),
            Paragraph(_percentile_label(prop.get("benchmark_percentile")), styles["body"]),
            Paragraph(prop.get("channel", "web"), styles["body"]),
            Paragraph(mfa, ParagraphStyle("mfa", fontName="Helvetica", fontSize=10, textColor=colors.red if mfa == "Yes" else FOREST)),
        ]
        if include_category:
            row.insert(2, Paragraph(prop.get("category", "Unknown"), styles["body"]))
        table_data.append(row)

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FOREST),
        ("TEXTCOLOR", (0, 0), (-1, 0), SCOPE3),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PRIMER, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))


# ── Unmodelled Properties ─────────────────────────────────────────────────────

def _unmodelled_section(story, styles, unmodelled: list):
    if not unmodelled:
        return
    story.append(Paragraph("Unmodelled Properties", styles["section_heading"]))
    story.append(Paragraph(
        "The following properties were not found in Scope3's database and could not be scored. "
        "Recommend excluding or investigating before including in campaign.",
        styles["body"]
    ))
    story.append(Spacer(1, 2*mm))
    for item in unmodelled:
        story.append(Paragraph(f"• {item.get('inventory_id', item)}", styles["flag"]))
    story.append(Spacer(1, 6*mm))


# ── Recommendations Section ───────────────────────────────────────────────────

def _recommendations_section(story, styles, recommendations: list, summary_text: str = None):
    story.append(Paragraph("Recommendations", styles["section_heading"]))
    if summary_text:
        story.append(Paragraph(summary_text, styles["body"]))
        story.append(Spacer(1, 3*mm))

    for i, rec in enumerate(recommendations[:10]):
        rank = i + 1
        gco2pm = rec.get("gco2pm", 0)
        reason = rec.get("reason", "")
        category = rec.get("category", "")
        inv_id = rec.get("inventory_id", "")

        block = [
            Paragraph(
                f"<b>{rank}. {inv_id}</b> &nbsp;&nbsp; "
                f"<font color='#{_emissions_colour(gco2pm).hexval()[2:]}' size='10'>{gco2pm:.1f} gCO2PM</font>"
                f"  |  {category}",
                styles["body"]
            ),
        ]
        if reason:
            block.append(Paragraph(f"<i>{reason}</i>", styles["flag"]))
        block.append(Spacer(1, 2*mm))
        story.extend(block)

    story.append(Spacer(1, 6*mm))


# ── Footer ────────────────────────────────────────────────────────────────────

def _footer(story, styles):
    story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GREY))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        "Generated by Scope3 Inventory Agent  •  Powered by Scope3 Emissions Data  •  scope3.com",
        styles["small"]
    ))


# ── Main PDF builder ──────────────────────────────────────────────────────────

def generate_pdf(
    mode: str,                      # "analyse" or "discover"
    ranked_inventory: list,         # scored + sorted list
    unmodelled_inventory: list = None,
    recommendations: list = None,   # for discover mode
    summary_text: str = None,
    brief: str = None,
    output_path: str = None
) -> str:
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"/mnt/user-data/outputs/scope3_report_{timestamp}.pdf"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=12*mm,
        bottomMargin=15*mm
    )

    styles = make_styles()
    story = []

    meta = {
        "brief": brief,
        "total_properties": len(ranked_inventory) + len(unmodelled_inventory or []),
        "total_modelled": len(ranked_inventory),
        "total_unmodelled": len(unmodelled_inventory or [])
    }

    _cover_page(story, styles, mode, meta)

    if mode == "analyse":
        _inventory_table(story, styles, ranked_inventory, include_category=False)
    else:
        # Discover mode: show recommendations first, then full table with categories
        if recommendations:
            _recommendations_section(story, styles, recommendations, summary_text)
        _inventory_table(story, styles, ranked_inventory, include_category=True)

    _unmodelled_section(story, styles, unmodelled_inventory or [])
    _footer(story, styles)

    doc.build(story)
    return output_path
