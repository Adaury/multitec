import os
from datetime import datetime, timedelta
from io import BytesIO
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from app.core.config import get_settings
from app.models.budget import Budget
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.quote import Quote
from app.services.company import CompanyInfo, load_company
from app.services.photo_annex import AnnexPhoto, build_annex_flowables

# Paleta alineada a frontend/src/index.css (--color-brand-*) para que los PDF se vean
# consistentes con el resto de la app en vez de usar grises genéricos de reportlab. El
# azul de marca es el acento; el tono oscuro de las cabeceras sale del logo de Multitec.
BRAND_BLUE = colors.HexColor("#0a63e2")
BRAND_BLUE_DARK = colors.HexColor("#0850b8")
BRAND_GRAY = colors.HexColor("#f4f5f7")
INK = colors.HexColor("#111827")
TEXT_DARK = colors.HexColor("#1c1e21")
TEXT_MUTED = colors.HexColor("#6b7280")  # ~ tailwind gray-500, igual que text-gray-500 en la UI
TEXT_FAINT = colors.HexColor("#9ca3af")  # ~ tailwind gray-400, igual que text-gray-400 en la UI
BORDER_GRAY = colors.HexColor("#e5e7eb")  # ~ tailwind gray-200, igual que border-gray-200 en la UI

# Ancho utilizable de una página Letter con 20mm de margen a cada lado.
CONTENT_WIDTH = 175 * mm

# Tamaño máximo del logo en el membrete: alto fijo, ancho proporcional con tope, para que un logo
# panorámico o cuadrado no se deforme ni se desborde.
LOGO_MAX_HEIGHT = 22 * mm
LOGO_MAX_WIDTH = 60 * mm

styles = getSampleStyleSheet()
_title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=2, textColor=TEXT_DARK)
_meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=TEXT_MUTED)
_item_desc_style = ParagraphStyle("ItemDesc", parent=styles["Normal"], fontSize=9, leading=12, textColor=TEXT_DARK)
_company_style = ParagraphStyle("CompanyMeta", parent=_meta_style, fontSize=8.5, leading=11.5)
_doc_title_style = ParagraphStyle(
    "DocHeading", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=22, leading=24,
    textColor=INK, alignment=TA_RIGHT,
)
_doc_subtitle_style = ParagraphStyle(
    "DocSubtitle", parent=styles["Normal"], fontSize=9, leading=11, textColor=TEXT_MUTED, alignment=TA_RIGHT
)
_doc_code_style = ParagraphStyle(
    "DocCode", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=13, leading=16,
    textColor=BRAND_BLUE, alignment=TA_RIGHT,
)
_box_label_style = ParagraphStyle(
    "BoxLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=TEXT_FAINT
)
_box_name_style = ParagraphStyle(
    "BoxName", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK
)
_box_text_style = ParagraphStyle("BoxText", parent=styles["Normal"], fontSize=9, leading=12, textColor=TEXT_MUTED)
_detail_label_style = ParagraphStyle(
    "DetailLabel", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=TEXT_FAINT
)
_detail_value_style = ParagraphStyle(
    "DetailValue", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12,
    textColor=TEXT_DARK, alignment=TA_RIGHT,
)
_section_label_style = ParagraphStyle(
    "SectionLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10,
    textColor=TEXT_FAINT, spaceAfter=3,
)
_closing_style = ParagraphStyle("Closing", parent=_meta_style, alignment=1)


def _money(value: float) -> str:
    return f"RD$ {value:,.2f}"


def _e(text) -> str:
    """Texto de usuario listo para ir dentro de un Paragraph (un '&' o '<' en un nombre rompería el PDF)."""
    return _xml_escape(str(text))


def _description_cell(description: str, note: str | None):
    """Celda de descripción de una línea: texto plano si no hay nota, o un Paragraph de
    dos renglones (descripción + nota en gris/cursiva) si el usuario le puso una en el
    editor de ítems."""
    if not note:
        return description
    return Paragraph(
        f"{_xml_escape(description)}<br/><font size=7.5 color='#9ca3af'><i>{_xml_escape(note)}</i></font>",
        _item_desc_style,
    )


def _logo_flowable(logo_path: str):
    """El logo de la empresa ajustado a su caja, o None si no hay archivo o no se puede leer."""
    if not logo_path or not os.path.isfile(logo_path):
        return None
    try:
        logo = Image(logo_path, mask="auto")
    except Exception:  # archivo dañado o formato que reportlab no abre: el PDF sale sin logo
        return None
    scale = min(LOGO_MAX_HEIGHT / logo.imageHeight, LOGO_MAX_WIDTH / logo.imageWidth)
    logo.drawHeight = logo.imageHeight * scale
    logo.drawWidth = logo.imageWidth * scale
    logo.hAlign = "LEFT"
    return logo


def _letterhead(company: CompanyInfo, doc_title: str, code: str) -> list:
    """Membrete: logo (o nombre) y datos de la empresa a la izquierda; tipo de documento y número
    a la derecha; una línea de acento debajo."""
    left: list = []
    logo = _logo_flowable(company.logo_path)
    if logo is not None:
        left.append(logo)
        left.append(Spacer(1, 2 * mm))
    else:
        left.append(Paragraph(_e(company.name), _title_style))
        if company.tagline:
            left.append(Paragraph(_e(company.tagline), _company_style))
    if company.representative:
        left.append(Paragraph(_e(company.representative), _company_style))
    id_line = " · ".join(
        part for part in (company.rnc and f"RNC: {company.rnc}", company.cedula and f"Cédula: {company.cedula}") if part
    )
    contact_line = " · ".join(part for part in (company.phone, company.email, company.website) if part)
    for line in (id_line, company.address, contact_line):
        if line:
            left.append(Paragraph(_e(line), _company_style))

    main_title, _, subtitle = doc_title.partition(" — ")
    right: list = [Paragraph(_e(main_title.upper()), _doc_title_style)]
    if subtitle:
        right.append(Paragraph(_e(subtitle), _doc_subtitle_style))
    right.append(Spacer(1, 1.5 * mm))
    right.append(Paragraph(_e(code), _doc_code_style))

    table = Table([[left, right]], colWidths=[0.58 * CONTENT_WIDTH, 0.42 * CONTENT_WIDTH])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [table, Spacer(1, 4 * mm), HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=5 * mm)]


def _info_boxes(
    *,
    client: Client,
    project: Project,
    created_at: datetime,
    due_date: datetime | None,
    ncf: str | None,
    status_label: str | None,
    client_label: str,
) -> Table:
    """Dos cuadros lado a lado: a quién va dirigido el documento y sus datos (fecha, NCF, proyecto…)."""
    client_cells = [Paragraph(client_label, _box_label_style), Paragraph(_e(client.name), _box_name_style)]
    for line in (
        client.company,
        client.rnc and f"RNC: {client.rnc}",
        client.address,
        getattr(client, "phone", None),
    ):
        if line:
            client_cells.append(Paragraph(_e(line), _box_text_style))

    details = [("Fecha", created_at.strftime("%d/%m/%Y"))]
    if due_date:
        details.append(("Vencimiento", due_date.strftime("%d/%m/%Y")))
    if ncf:
        details.append(("NCF", ncf))
    details.append(("Proyecto", project.code))
    if status_label:
        details.append(("Estado", status_label))
    details_table = Table(
        [[Paragraph(label, _detail_label_style), Paragraph(_e(value), _detail_value_style)] for label, value in details],
        colWidths=[0.14 * CONTENT_WIDTH, 0.26 * CONTENT_WIDTH],
    )
    details_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )

    boxes = Table([[client_cells, details_table]], colWidths=[0.55 * CONTENT_WIDTH, 0.45 * CONTENT_WIDTH])
    boxes.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LINEBEFORE", (0, 0), (0, 0), 2.5, BRAND_BLUE),
            ]
        )
    )
    return boxes


def _page_footer(company: CompanyInfo):
    """Pie de cada página: una línea fina, el contacto de la empresa y el número de página."""
    contact = " · ".join(part for part in (company.name, company.phone, company.email, company.website) if part)

    def draw(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(BORDER_GRAY)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 14 * mm, doc.leftMargin + CONTENT_WIDTH, 14 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(TEXT_FAINT)
        canvas.drawString(doc.leftMargin, 10 * mm, contact)
        canvas.drawRightString(doc.leftMargin + CONTENT_WIDTH, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    return draw


def _boxed_section(label: str, lines: list[str]) -> Table:
    """Recuadro gris con barra azul a la izquierda (notas, datos para depósito)."""
    content = [Paragraph(label, _section_label_style)] + [Paragraph(_e(line), _meta_style) for line in lines]
    box = Table([[content]], colWidths=[CONTENT_WIDTH])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_GRAY),
                ("LINEBEFORE", (0, 0), (0, 0), 2.5, BRAND_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return box


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
    due_date: datetime | None = None,
    status_label: str | None = None,
    notes: str | None = None,
    show_line_prices: bool = True,
    show_breakdown: bool = True,
    show_quantities: bool = True,
    quantity_first: bool = False,
    integer_quantities: bool = False,
    category_totals: list[tuple[str, float]] | None = None,
    photo_annex: list[AnnexPhoto] | None = None,
    company: CompanyInfo | None = None,
    client_label: str = "CLIENTE",
    closing_note: str | None = None,
) -> bytes:
    settings = get_settings()
    company = company or load_company(project.company_id)  # el membrete es el de la empresa DUEÑA del documento
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, topMargin=18 * mm, bottomMargin=22 * mm, leftMargin=20 * mm, rightMargin=20 * mm
    )
    story: list = []

    story.extend(_letterhead(company, doc_title, code))
    story.append(
        _info_boxes(
            client=client,
            project=project,
            created_at=created_at,
            due_date=due_date,
            ncf=ncf,
            status_label=status_label,
            client_label=client_label,
        )
    )
    story.append(Spacer(1, 7 * mm))

    desc_col = 0  # columna que va alineada a la izquierda (todas las demás, a la derecha)
    number_col = False  # la tabla detallada lleva columna "#"

    if category_totals is not None:
        # Resumen ejecutivo (§ Motor 6): totales por categoría, sin línea por línea — no
        # es un registro financiero aparte, solo otra vista del mismo Quote.
        rows = [["Categoría", "Subtotal"]]
        for category_name, amount in category_totals:
            rows.append([category_name, _money(amount)])
        col_widths = [0.77 * CONTENT_WIDTH, 0.23 * CONTENT_WIDTH]
    elif show_line_prices:
        number_col = True
        rows = [["#", "Descripción", "Cant.", "Precio unit.", "Importe"]]
        for index, item in enumerate(items, start=1):
            rows.append(
                [
                    str(index),
                    _description_cell(item.description, getattr(item, "note", None)),
                    f"{float(item.quantity):g}",
                    _money(float(item.unit_price)),
                    _money(float(item.subtotal)),
                ]
            )
        col_widths = [
            0.06 * CONTENT_WIDTH, 0.45 * CONTENT_WIDTH, 0.10 * CONTENT_WIDTH, 0.18 * CONTENT_WIDTH, 0.21 * CONTENT_WIDTH,
        ]
        desc_col = 1
    elif show_quantities:

        def _qty(item) -> str:
            # § presupuesto: cantidades enteras, sin decimales, para el resumen que ve el
            # cliente — el valor exacto (con el margen de desperdicio de cable, etc.) sigue
            # viviendo en la Cotización.
            return str(round(float(item.quantity))) if integer_quantities else f"{float(item.quantity):g}"

        if quantity_first:
            rows = [["Cant.", "Descripción"]]
            for item in items:
                rows.append([_qty(item), _description_cell(item.description, getattr(item, "note", None))])
            col_widths = [0.12 * CONTENT_WIDTH, 0.88 * CONTENT_WIDTH]
            desc_col = 1
        else:
            rows = [["Descripción", "Cant."]]
            for item in items:
                rows.append([_description_cell(item.description, getattr(item, "note", None)), _qty(item)])
            col_widths = [0.88 * CONTENT_WIDTH, 0.12 * CONTENT_WIDTH]
    else:
        # Resumen mínimo: solo nombres, sin cantidades ni precios por línea — para
        # compartir con el cliente un vistazo del alcance sin el desglose comercial.
        rows = [["Descripción"]]
        for item in items:
            rows.append([_description_cell(item.description, getattr(item, "note", None))])
        col_widths = [CONTENT_WIDTH]

    items_table = Table(rows, colWidths=col_widths, repeatRows=1)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_DARK),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (desc_col, 0), (desc_col, -1), "LEFT"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafb")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if number_col:
        table_style += [("ALIGN", (0, 0), (0, -1), "CENTER"), ("TEXTCOLOR", (0, 1), (0, -1), TEXT_FAINT)]
    items_table.setStyle(TableStyle(table_style))
    story.append(items_table)
    story.append(Spacer(1, 5 * mm))

    if show_breakdown:
        if show_line_prices or category_totals is not None:
            totals_rows = [
                ["Subtotal", _money(subtotal)],
                [f"ITBIS ({settings.itbis_rate * 100:.0f}%)", _money(itbis)],
                ["TOTAL", _money(total)],
            ]
        else:
            # Sin desglose por línea ni por categoría: solo el precio global del servicio.
            totals_rows = [["TOTAL DEL SERVICIO", _money(total)]]
        last = len(totals_rows) - 1
        # La etiqueta más larga ("TOTAL DEL SERVICIO", en negrita 11 pt) tiene que caber sin cortarse.
        totals_table = Table(totals_rows, colWidths=[0.31 * CONTENT_WIDTH, 0.23 * CONTENT_WIDTH], hAlign="RIGHT")
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_MUTED),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("BACKGROUND", (0, last), (-1, last), INK),
                    ("TEXTCOLOR", (0, last), (-1, last), colors.white),
                    ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
                    ("FONTSIZE", (0, last), (-1, last), 11),
                    ("TOPPADDING", (0, last), (-1, last), 7),
                    ("BOTTOMPADDING", (0, last), (-1, last), 7),
                ]
            )
        )
        story.append(totals_table)

    if notes:
        story.append(Spacer(1, 8 * mm))
        story.append(_boxed_section("NOTAS", [notes]))

    bank_lines = [line.strip() for line in (company.bank_info or "").splitlines() if line.strip()]
    if bank_lines:
        story.append(Spacer(1, 6 * mm))
        story.append(_boxed_section("DATOS PARA DEPÓSITO O TRANSFERENCIA", bank_lines))

    if closing_note:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph(_e(closing_note), _closing_style))

    if photo_annex:
        story.extend(build_annex_flowables(photo_annex))

    footer = _page_footer(company)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


FALLBACK_CATEGORY_LABEL = "Mano de obra y servicios"


def _category_totals(items: list, category_by_product_id: dict[int, str | None]) -> list[tuple[str, float]]:
    """Agrupa las líneas de una cotización por categoría de catálogo (o el fallback, para
    líneas sin producto — ej. mano de obra) para el resumen ejecutivo. `category_by_product_id`
    lo arma el caller (no se consulta la base de datos aquí — este módulo solo renderiza)."""
    totals: dict[str, float] = {}
    order: list[str] = []
    for item in items:
        category_name = category_by_product_id.get(item.product_id) or FALLBACK_CATEGORY_LABEL
        if category_name not in totals:
            totals[category_name] = 0.0
            order.append(category_name)
        totals[category_name] += float(item.subtotal)
    return [(name, totals[name]) for name in order]


def build_quote_pdf(
    quote: Quote,
    variant: str = "detallada",
    category_by_product_id: dict[int, str | None] | None = None,
    photo_annex: list[AnnexPhoto] | None = None,
    company: CompanyInfo | None = None,
) -> bytes:
    is_executive = variant == "ejecutiva"
    return _build_pdf(
        doc_title="Cotización — Resumen ejecutivo" if is_executive else "Cotización",
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
        category_totals=_category_totals(quote.items, category_by_product_id or {}) if is_executive else None,
        photo_annex=photo_annex,
        company=company,
    )


def build_invoice_pdf(invoice: Invoice, variant: str = "detallada", company: CompanyInfo | None = None) -> bytes:
    settings = get_settings()
    company = company or load_company(invoice.company_id)
    show_line_prices = variant != "global"
    return _build_pdf(
        doc_title="Factura" if show_line_prices else "Factura — Detalle de trabajo",
        code=invoice.code,
        created_at=invoice.created_at,
        client=invoice.project.client,
        project=invoice.project,
        items=invoice.items,
        subtotal=float(invoice.subtotal),
        itbis=float(invoice.itbis),
        total=float(invoice.total),
        ncf=invoice.ncf if show_line_prices else None,
        due_date=invoice.created_at + timedelta(days=settings.invoice_due_days),
        show_line_prices=show_line_prices,
        show_breakdown=True,
        company=company,
        client_label="FACTURADO A",
        closing_note=company.invoice_notes or None,
    )


def build_budget_summary_pdf(budget: Budget, company: CompanyInfo | None = None) -> bytes:
    """Resumen para compartir con el cliente: nombres y cantidad de lo incluido, y el
    total final — sin precios unitarios ni desglose de ITBIS (eso vive en la Cotización,
    un documento aparte)."""
    return _build_pdf(
        doc_title="Presupuesto — Resumen",
        code=budget.code,
        created_at=budget.created_at,
        client=budget.project.client,
        project=budget.project,
        items=budget.items,
        subtotal=0,
        itbis=0,
        total=float(budget.total),
        notes=budget.notes,
        show_line_prices=False,
        show_breakdown=True,
        show_quantities=True,
        quantity_first=True,
        integer_quantities=True,
        company=company,
    )
