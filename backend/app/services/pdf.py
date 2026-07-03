from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from app.core.config import get_settings
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.quote import Quote

styles = getSampleStyleSheet()
_title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=2)
_meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#555555"))
_label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#888888"))


def _money(value: float) -> str:
    return f"RD$ {value:,.2f}"


def _build_pdf(
    *,
    doc_title: str,
    code: str,
    created_at: datetime,
    client: Client,
    project: Project,
    items: list,
    subtotal: float,
    itbis: float,
    total: float,
    ncf: str | None = None,
    status_label: str | None = None,
    notes: str | None = None,
    show_prices: bool = True,
) -> bytes:
    settings = get_settings()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm
    )
    story = []

    story.append(Paragraph(settings.company_name, _title_style))
    company_lines = [line for line in (settings.company_rnc and f"RNC: {settings.company_rnc}", settings.company_address, settings.company_phone) if line]
    if company_lines:
        story.append(Paragraph(" · ".join(company_lines), _meta_style))
    story.append(Spacer(1, 10 * mm))

    header_data = [
        [Paragraph(f"<b>{doc_title}</b>", styles["Heading2"]), Paragraph(f"<b>{code}</b>", styles["Heading2"])],
        [
            Paragraph(
                f"Cliente: {client.name}"
                + (f" ({client.company})" if client.company else "")
                + (f"<br/>RNC: {client.rnc}" if client.rnc else "")
                + (f"<br/>{client.address}" if client.address else ""),
                _meta_style,
            ),
            Paragraph(
                f"Proyecto: {project.code}<br/>Fecha: {created_at.strftime('%d/%m/%Y')}"
                + (f"<br/>NCF: <b>{ncf}</b>" if ncf else "")
                + (f"<br/>Estado: {status_label}" if status_label else ""),
                _meta_style,
            ),
        ],
    ]
    header_table = Table(header_data, colWidths=[95 * mm, 75 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 8 * mm))

    if show_prices:
        rows = [["Descripción", "Cant.", "Precio unit.", "Subtotal"]]
        for item in items:
            rows.append(
                [item.description, f"{item.quantity:g}", _money(float(item.unit_price)), _money(float(item.subtotal))]
            )
        col_widths = [85 * mm, 20 * mm, 30 * mm, 35 * mm]
    else:
        rows = [["Descripción", "Cant."]]
        for item in items:
            rows.append([item.description, f"{item.quantity:g}"])
        col_widths = [150 * mm, 20 * mm]

    items_table = Table(rows, colWidths=col_widths)
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a63e2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6f8")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    if show_prices:
        totals_rows = [
            ["Subtotal", _money(subtotal)],
            [f"ITBIS ({settings.itbis_rate * 100:.0f}%)", _money(itbis)],
            ["Total", _money(total)],
        ]
        totals_table = Table(totals_rows, colWidths=[140 * mm, 30 * mm])
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                    ("LINEABOVE", (0, 2), (-1, 2), 0.75, colors.black),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(totals_table)

    if notes:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("Notas", _label_style))
        story.append(Paragraph(notes, _meta_style))

    doc.build(story)
    return buf.getvalue()


def build_quote_pdf(quote: Quote) -> bytes:
    return _build_pdf(
        doc_title="Cotización",
        code=quote.code,
        created_at=quote.created_at,
        client=quote.project.client,
        project=quote.project,
        items=quote.items,
        subtotal=float(quote.subtotal),
        itbis=float(quote.itbis),
        total=float(quote.total),
        status_label=quote.status.replace("_", " ").capitalize(),
        notes=quote.notes,
    )


def build_invoice_pdf(invoice: Invoice, variant: str = "detallada") -> bytes:
    show_prices = variant != "global"
    return _build_pdf(
        doc_title="Factura" if show_prices else "Factura — Detalle de trabajo",
        code=invoice.code,
        created_at=invoice.created_at,
        client=invoice.project.client,
        project=invoice.project,
        items=invoice.items,
        subtotal=float(invoice.subtotal),
        itbis=float(invoice.itbis),
        total=float(invoice.total),
        ncf=invoice.ncf if show_prices else None,
        show_prices=show_prices,
    )
