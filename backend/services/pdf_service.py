import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from models.invoice import InvoiceData


def generate_invoice_pdf(invoice: InvoiceData) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#2563EB")
    light_gray = colors.HexColor("#F3F4F6")
    dark_gray = colors.HexColor("#374151")

    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Title"],
        fontSize=28,
        textColor=primary_color,
        spaceAfter=4,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=1,
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=10,
        textColor=dark_gray,
        spaceAfter=2,
    )
    right_style = ParagraphStyle(
        "Right",
        parent=styles["Normal"],
        fontSize=10,
        textColor=dark_gray,
        alignment=TA_RIGHT,
    )
    bold_right_style = ParagraphStyle(
        "BoldRight",
        parent=styles["Normal"],
        fontSize=12,
        textColor=primary_color,
        alignment=TA_RIGHT,
        fontName="Helvetica-Bold",
    )

    elements = []

    # ── Header: INVOICE title + invoice number / date ──────────────────────
    header_data = [
        [
            Paragraph("INVOICE", title_style),
            Table(
                [
                    [Paragraph("Invoice No.", label_style), Paragraph(invoice.invoice_number, value_style)],
                    [Paragraph("Date", label_style), Paragraph(invoice.date, value_style)],
                    [
                        Paragraph("Due Date", label_style),
                        Paragraph(invoice.due_date or "—", value_style),
                    ],
                ],
                colWidths=[25 * mm, 45 * mm],
                style=TableStyle([("ALIGN", (0, 0), (-1, -1), "LEFT")]),
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[110 * mm, 70 * mm])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(header_table)
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=primary_color))
    elements.append(Spacer(1, 6 * mm))

    # ── From / To ───────────────────────────────────────────────────────────
    def party_block(party, title):
        block = [Paragraph(title, label_style), Paragraph(f"<b>{party.name}</b>", value_style)]
        if party.address:
            block.append(Paragraph(party.address, value_style))
        if party.phone:
            block.append(Paragraph(party.phone, value_style))
        if party.email:
            block.append(Paragraph(party.email, value_style))
        if party.tax_id:
            block.append(Paragraph(f"Tax ID: {party.tax_id}", value_style))
        return block

    parties_data = [[party_block(invoice.issuer, "FROM"), party_block(invoice.client, "BILL TO")]]
    parties_table = Table(parties_data, colWidths=[90 * mm, 90 * mm])
    parties_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(parties_table)
    elements.append(Spacer(1, 8 * mm))

    # ── Items table ─────────────────────────────────────────────────────────
    currency = invoice.currency or "USD"
    col_headers = ["Description", "Qty", "Unit Price", "Total"]
    item_rows = [col_headers]
    for item in invoice.items:
        item_rows.append(
            [
                item.description,
                str(item.quantity),
                f"{currency} {item.unit_price:,.2f}",
                f"{currency} {item.total:,.2f}",
            ]
        )

    items_table = Table(item_rows, colWidths=[95 * mm, 20 * mm, 35 * mm, 30 * mm])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_gray]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(items_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Totals ──────────────────────────────────────────────────────────────
    totals_data = [
        ["", Paragraph("Subtotal", right_style), Paragraph(f"{currency} {invoice.subtotal:,.2f}", right_style)],
    ]
    if invoice.tax_amount:
        tax_label = f"Tax ({invoice.tax_rate:.0f}%)" if invoice.tax_rate else "Tax"
        totals_data.append(
            ["", Paragraph(tax_label, right_style), Paragraph(f"{currency} {invoice.tax_amount:,.2f}", right_style)]
        )
    totals_data.append(
        ["", Paragraph("TOTAL", bold_right_style), Paragraph(f"{currency} {invoice.total:,.2f}", bold_right_style)]
    )

    totals_table = Table(totals_data, colWidths=[100 * mm, 50 * mm, 30 * mm])
    totals_table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (1, -1), (-1, -1), 1.5, primary_color),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(totals_table)

    # ── Notes / Payment terms ───────────────────────────────────────────────
    if invoice.payment_terms or invoice.notes:
        elements.append(Spacer(1, 8 * mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB")))
        elements.append(Spacer(1, 4 * mm))
        if invoice.payment_terms:
            elements.append(Paragraph("Payment Terms", label_style))
            elements.append(Paragraph(invoice.payment_terms, value_style))
            elements.append(Spacer(1, 3 * mm))
        if invoice.notes:
            elements.append(Paragraph("Notes", label_style))
            elements.append(Paragraph(invoice.notes, value_style))

    # ── Footer ──────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 10 * mm))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#9CA3AF"), alignment=TA_CENTER
    )
    elements.append(
        Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} · Receipt to Invoice", footer_style)
    )

    doc.build(elements)
    return buf.getvalue()
