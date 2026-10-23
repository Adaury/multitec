import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.company_profile import CompanyProfile

FIELDS = (
    "name", "tagline", "representative", "rnc", "cedula", "address", "phone", "email", "website",
    "bank_info", "invoice_notes",
)

# Lo que se acepta como logo y lo que se guarda: un PNG recortado y de tamaño razonable para el PDF.
LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
LOGO_MAX_WIDTH = 900
_WHITE_ENOUGH = 245


@dataclass(frozen=True)
class CompanyInfo:
    name: str = ""
    tagline: str = ""
    representative: str = ""
    rnc: str = ""
    cedula: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    bank_info: str = ""
    invoice_notes: str = ""
    logo_path: str = ""


def company_from_settings() -> CompanyInfo:
    """Membrete sacado solo de COMPANY_* en `.env` (lo que había antes de poder editarlo en la app)."""
    s = get_settings()
    return CompanyInfo(
        name=s.company_name,
        representative=s.company_representative,
        rnc=s.company_rnc,
        cedula=s.company_cedula,
        address=s.company_address,
        phone=s.company_phone,
        bank_info=s.company_bank_info,
        logo_path=s.company_logo_path,
    )


def get_profile(db: Session) -> CompanyProfile | None:
    return db.get(CompanyProfile, 1)


def get_company(db: Session) -> CompanyInfo:
    """Datos vigentes: lo guardado en la app manda y, campo por campo, lo vacío cae a `.env`."""
    base = company_from_settings()
    profile = get_profile(db)
    if profile is None:
        return base
    values = {field: (getattr(profile, field) or getattr(base, field)) for field in FIELDS}
    # NULL = nunca se tocó el logo en la app (cae al de .env); "" = se quitó a propósito (sin logo).
    values["logo_path"] = base.logo_path if profile.logo_path is None else profile.logo_path
    return CompanyInfo(**values)


def load_company() -> CompanyInfo:
    """Igual que `get_company`, abriendo su propia sesión: para quien genera un PDF sin tener `db`."""
    with SessionLocal() as db:
        return get_company(db)


def logo_directory() -> Path:
    directory = Path(get_settings().upload_dir) / "company"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def prepare_logo(contents: bytes) -> bytes:
    """Valida que sea una imagen de verdad, le quita el margen blanco sobrante (los logos suelen venir
    en un cuadro con mucho aire, y en el PDF se vería diminuto) y la devuelve como PNG."""
    try:
        image = Image.open(BytesIO(contents))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida (usa PNG, JPG o WebP).")
    image = image.convert("RGBA")

    # Recorte: lo que no es (casi) blanco ni transparente.
    alpha = image.getchannel("A").point(lambda a: 255 if a > 10 else 0)
    ink = image.convert("L").point(lambda v: 255 if v < _WHITE_ENOUGH else 0)
    mask = Image.composite(ink, Image.new("L", image.size, 0), alpha)
    box = mask.getbbox()
    if box is None:
        raise HTTPException(status_code=400, detail="La imagen está en blanco.")
    pad = max(2, round(max(image.size) * 0.01))
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(image.width, box[2] + pad), min(image.height, box[3] + pad))
    image = image.crop(box)

    if image.width > LOGO_MAX_WIDTH:
        image = image.resize((LOGO_MAX_WIDTH, round(image.height * LOGO_MAX_WIDTH / image.width)), Image.LANCZOS)
    out = BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def save_logo(db: Session, contents: bytes) -> CompanyProfile:
    """Guarda un logo nuevo (con nombre nuevo para que el navegador no muestre el anterior en caché)
    y borra el archivo que reemplaza."""
    png = prepare_logo(contents)
    profile = get_profile(db) or CompanyProfile(id=1)
    destination = logo_directory() / f"logo-{uuid.uuid4().hex}.png"
    destination.write_bytes(png)
    _delete_logo_file(profile.logo_path)
    profile.logo_path = str(destination.as_posix())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def remove_logo(db: Session) -> CompanyProfile | None:
    """Deja la empresa sin logo, también si venía del .env: un logo quitado no debe reaparecer."""
    profile = get_profile(db) or CompanyProfile(id=1)
    _delete_logo_file(profile.logo_path)
    profile.logo_path = ""
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _delete_logo_file(path: str | None) -> None:
    """Solo borra archivos que están dentro de la carpeta de logos de la app, nunca una ruta ajena
    (el logo también puede venir de COMPANY_LOGO_PATH, que apunta a donde el usuario quiera)."""
    if not path:
        return
    try:
        target = Path(path).resolve()
        if logo_directory().resolve() in target.parents and target.is_file():
            target.unlink()
    except OSError:
        pass
