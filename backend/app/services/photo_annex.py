"""Anexo fotográfico de la cotización: las fotos del levantamiento con las cámaras/puntos
numerados encima (marcadores) y una leyenda debajo. Es lo que más ayuda al cliente a entender
dónde va cada equipo."""

import logging
import os
from dataclasses import dataclass
from io import BytesIO

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

logger = logging.getLogger("multitec.pdf")

MAX_PHOTOS = 8
MAX_SIDE_PX = 1100
CONTENT_WIDTH = 175 * mm
MAX_IMAGE_HEIGHT = 105 * mm
PIN_COLOR = (10, 99, 226)  # --color-brand-blue

_styles = getSampleStyleSheet()
_heading = ParagraphStyle("AnnexHeading", parent=_styles["Heading2"], fontSize=13, spaceAfter=4)
_caption = ParagraphStyle("AnnexCaption", parent=_styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#6b7280"))


@dataclass
class AnnexMarker:
    number: int
    label: str
    x: float  # 0..1 sobre el ancho de la foto
    y: float  # 0..1 sobre el alto


@dataclass
class AnnexPhoto:
    file_path: str
    description: str | None
    markers: list[AnnexMarker]


def collect_photos(survey, mode: str) -> list[AnnexPhoto]:
    """Fotos del levantamiento para el anexo. `marked`: solo las que tienen marcadores
    (lo que ve el cliente); `all`: todas las fotos. `none` (o sin levantamiento): nada."""
    if survey is None or mode not in ("marked", "all"):
        return []
    photos: list[AnnexPhoto] = []
    for asset in sorted(survey.assets, key=lambda a: a.id):
        if asset.kind != "photo":
            continue
        markers = sorted(asset.markers, key=lambda m: m.number)
        if mode == "marked" and not markers:
            continue
        photos.append(
            AnnexPhoto(
                file_path=asset.file_path,
                description=asset.description,
                markers=[AnnexMarker(m.number, m.label or "", m.x, m.y) for m in markers],
            )
        )
    return photos[:MAX_PHOTOS]


def render_marked_photo(photo: AnnexPhoto) -> tuple[bytes, float] | None:
    """JPEG con los marcadores dibujados y su relación alto/ancho; None si la foto no se
    puede abrir (archivo borrado, HEIC que Pillow no lee)."""
    if not os.path.isfile(photo.file_path):
        return None
    try:
        with PILImage.open(photo.file_path) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
    except Exception:  # noqa: BLE001 - un archivo ilegible no debe tumbar toda la cotización
        logger.warning("Foto ilegible para el anexo: %s", photo.file_path)
        return None

    image.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
    width, height = image.size
    draw = ImageDraw.Draw(image)
    radius = max(12, round(width * 0.022))
    try:
        font = ImageFont.load_default(size=round(radius * 1.15))
    except TypeError:  # Pillow viejo sin tamaño variable
        font = ImageFont.load_default()
    for marker in photo.markers:
        cx, cy = marker.x * width, marker.y * height
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius), fill=PIN_COLOR, outline=(255, 255, 255), width=3
        )
        draw.text((cx, cy), str(marker.number), fill=(255, 255, 255), font=font, anchor="mm")

    out = BytesIO()
    image.save(out, format="JPEG", quality=82)
    return out.getvalue(), height / width


def build_annex_flowables(photos: list[AnnexPhoto]) -> list:
    flowables: list = []
    rendered = []
    for photo in photos:
        result = render_marked_photo(photo)
        if result is not None:
            rendered.append((photo, result))
    if not rendered:
        return flowables

    flowables.append(PageBreak())
    flowables.append(Paragraph("Anexo: ubicación de los equipos", _heading))
    flowables.append(Paragraph("Fotos del levantamiento con los puntos numerados.", _caption))
    flowables.append(Spacer(1, 4 * mm))

    for index, (photo, (jpeg, ratio)) in enumerate(rendered, start=1):
        draw_width = CONTENT_WIDTH
        draw_height = draw_width * ratio
        if draw_height > MAX_IMAGE_HEIGHT:
            draw_height = MAX_IMAGE_HEIGHT
            draw_width = draw_height / ratio
        block = [Image(BytesIO(jpeg), width=draw_width, height=draw_height)]
        title = photo.description or f"Foto {index}"
        block.append(Paragraph(title, _caption))
        if photo.markers:
            rows = [[str(m.number), m.label or "Punto sin nombre"] for m in photo.markers]
            legend = Table(rows, colWidths=[10 * mm, CONTENT_WIDTH - 10 * mm])
            legend.setStyle(
                TableStyle(
                    [
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0a63e2")),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ]
                )
            )
            block.append(Spacer(1, 1.5 * mm))
            block.append(legend)
        block.append(Spacer(1, 8 * mm))
        flowables.append(KeepTogether(block))
    return flowables
