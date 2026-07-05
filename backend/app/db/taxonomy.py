"""Árbol de clasificaciones del catálogo (§ catálogo inteligente v2).

Fuente única de verdad para las categorías/subcategorías iniciales — la usan tanto la
migración (siembra + backfill de productos existentes) como `db/seed.py` (top-up
idempotente en bases nuevas y en tests). Cada nodo puede llevar `code_prefix`; si no lo
lleva, el producto hereda el de su ancestro más cercano que sí lo tenga (ver
`Product.resolve_code_prefix`), con "OTR" como último recurso.

La sección "Herramientas" del documento original llegó cortada a mitad de lista — se
completó con un set razonable de herramientas comunes en instalaciones de seguridad
electrónica; se puede ajustar libremente desde la pantalla de Clasificaciones.
"""

TAXONOMY = [
    {
        "name": "CCTV",
        "slug": "cctv",
        "children": [
            {"name": "Cámaras IP", "slug": "camaras-ip", "code_prefix": "CAM"},
            {"name": "Cámaras Analógicas", "slug": "camaras-analogicas", "code_prefix": "CAM"},
            {"name": "Cámaras PTZ", "slug": "camaras-ptz", "code_prefix": "CAM"},
            {"name": "Cámaras Bullet", "slug": "camaras-bullet", "code_prefix": "CAM"},
            {"name": "Cámaras Domo", "slug": "camaras-domo", "code_prefix": "CAM"},
            {"name": "Cámaras Térmicas", "slug": "camaras-termicas", "code_prefix": "CAM"},
            {"name": "NVR", "slug": "nvr", "code_prefix": "NVR"},
            {"name": "DVR", "slug": "dvr", "code_prefix": "DVR"},
            {"name": "Discos Duros", "slug": "discos-duros-cctv", "code_prefix": "DD"},
            {"name": "Monitores", "slug": "monitores-cctv", "code_prefix": "MON"},
            {"name": "Fuentes de Alimentación", "slug": "fuentes-alimentacion-cctv", "code_prefix": "FTE"},
            {"name": "Accesorios", "slug": "accesorios-cctv"},
        ],
    },
    {
        "name": "Cableado",
        "slug": "cableado",
        "code_prefix": "CAB",
        "children": [
            {"name": "UTP Categoría 5e", "slug": "utp-cat5e"},
            {"name": "UTP Categoría 6", "slug": "utp-cat6"},
            {"name": "UTP Categoría 6A", "slug": "utp-cat6a"},
            {"name": "UTP Categoría 7", "slug": "utp-cat7"},
            {"name": "FTP", "slug": "ftp"},
            {"name": "STP", "slug": "stp"},
            {"name": "Cable Coaxial RG59", "slug": "coaxial-rg59"},
            {"name": "Cable Coaxial RG6", "slug": "coaxial-rg6"},
            {"name": "Cable Siamés", "slug": "cable-siames"},
            {"name": "Cable para Alimentación", "slug": "cable-alimentacion"},
            {"name": "Cable Eléctrico", "slug": "cable-electrico"},
            {"name": "Cable de Fibra Óptica Monomodo", "slug": "cable-fibra-optica-monomodo"},
            {"name": "Cable de Fibra Óptica Multimodo", "slug": "cable-fibra-optica-multimodo"},
            {"name": "Patch Cord", "slug": "patch-cord-cableado"},
            {"name": "Cable HDMI", "slug": "cable-hdmi"},
            {"name": "Cable VGA", "slug": "cable-vga"},
            {"name": "Cable USB", "slug": "cable-usb"},
            {"name": "Cable de Audio", "slug": "cable-audio"},
            {"name": "Otros", "slug": "otros-cableado"},
        ],
    },
    {
        "name": "Canalizaciones",
        "slug": "canalizaciones",
        "code_prefix": "CND",
        "children": [
            {"name": "Tubería EMT", "slug": "tuberia-emt"},
            {"name": "PVC Eléctrico", "slug": "pvc-electrico"},
            {"name": "PVC Pesado", "slug": "pvc-pesado"},
            {"name": "Tubería Flexible", "slug": "tuberia-flexible"},
            {"name": "Conduit Galvanizado", "slug": "conduit-galvanizado"},
            {"name": "Canaleta Plástica", "slug": "canaleta-plastica"},
            {"name": "Canaleta Metálica", "slug": "canaleta-metalica"},
            {"name": "Bandeja Portacables", "slug": "bandeja-portacables"},
            {"name": "Escalerilla", "slug": "escalerilla"},
            {"name": "Ductos", "slug": "ductos"},
            {"name": "Registros", "slug": "registros"},
            {"name": "Cajas de Paso", "slug": "cajas-de-paso"},
        ],
    },
    {
        "name": "Conectores",
        "slug": "conectores",
        "code_prefix": "CNX",
        "children": [
            {"name": "RJ45 Cat5e", "slug": "rj45-cat5e"},
            {"name": "RJ45 Cat6", "slug": "rj45-cat6"},
            {"name": "RJ45 Blindado", "slug": "rj45-blindado"},
            {"name": "Keystone RJ45", "slug": "keystone-rj45"},
            {"name": "BNC", "slug": "bnc"},
            {"name": "Conector DC", "slug": "conector-dc"},
            {"name": "Jack DC", "slug": "jack-dc"},
            {"name": "Adaptadores BNC", "slug": "adaptadores-bnc"},
            {"name": "Conectores de Fibra SC", "slug": "conector-fibra-sc"},
            {"name": "Conectores de Fibra LC", "slug": "conector-fibra-lc"},
            {"name": "Conectores de Fibra ST", "slug": "conector-fibra-st"},
            {"name": "Conectores de Fibra FC", "slug": "conector-fibra-fc"},
            {"name": "Conectores APC", "slug": "conectores-apc"},
            {"name": "Conectores UPC", "slug": "conectores-upc"},
            {"name": "Empalmes", "slug": "empalmes-conectores"},
            {"name": "Adaptadores", "slug": "adaptadores-conectores"},
        ],
    },
    {
        "name": "Redes",
        "slug": "redes",
        "code_prefix": "RED",
        "children": [
            {"name": "Switch PoE", "slug": "switch-poe", "code_prefix": "SW"},
            {"name": "Switch Administrable", "slug": "switch-administrable", "code_prefix": "SW"},
            {"name": "Router", "slug": "router"},
            {"name": "Firewall", "slug": "firewall"},
            {"name": "Access Point", "slug": "access-point"},
            {"name": "Patch Panel", "slug": "patch-panel"},
            {"name": "Rack", "slug": "rack"},
            {"name": "Organizadores", "slug": "organizadores-redes"},
            {"name": "UPS", "slug": "ups"},
            {"name": "Inyectores PoE", "slug": "inyectores-poe"},
        ],
    },
    {
        "name": "Fibra Óptica",
        "slug": "fibra-optica",
        "code_prefix": "FO",
        "children": [
            {"name": "ODF", "slug": "odf"},
            {"name": "CTO", "slug": "cto"},
            {"name": "NAP", "slug": "nap"},
            {"name": "Splitters", "slug": "splitters"},
            {"name": "Pigtails", "slug": "pigtails"},
            {"name": "Patch Cord", "slug": "patch-cord-fibra"},
            {"name": "Empalmadoras", "slug": "empalmadoras"},
            {"name": "Bandejas", "slug": "bandejas-fibra"},
            {"name": "Protectores de Empalme", "slug": "protectores-empalme"},
        ],
    },
    {
        "name": "Control de Acceso",
        "slug": "control-de-acceso",
        "code_prefix": "ACC",
        "children": [
            {"name": "Lectores Biométricos", "slug": "lectores-biometricos"},
            {"name": "Lectores RFID", "slug": "lectores-rfid"},
            {"name": "Tarjetas", "slug": "tarjetas-acceso"},
            {"name": "Cerraduras Magnéticas", "slug": "cerraduras-magneticas"},
            {"name": "Cerraduras Eléctricas", "slug": "cerraduras-electricas"},
            {"name": "Botones de Salida", "slug": "botones-salida"},
            {"name": "Fuentes", "slug": "fuentes-acceso"},
            {"name": "Controladoras", "slug": "controladoras-acceso"},
        ],
    },
    {
        "name": "Videoporteros",
        "slug": "videoporteros",
        "code_prefix": "VP",
        "children": [
            {"name": "Monitores", "slug": "monitores-videoportero"},
            {"name": "Estaciones Exteriores", "slug": "estaciones-exteriores"},
            {"name": "Fuentes", "slug": "fuentes-videoportero"},
            {"name": "Módulos de Expansión", "slug": "modulos-expansion"},
            {"name": "Accesorios", "slug": "accesorios-videoportero"},
        ],
    },
    {
        "name": "Automatización",
        "slug": "automatizacion",
        "code_prefix": "AUT",
        "children": [
            {"name": "Barreras Vehiculares", "slug": "barreras-vehiculares", "code_prefix": "BAR"},
            {"name": "Motores para Portones", "slug": "motores-portones"},
            {"name": "Sensores", "slug": "sensores-automatizacion"},
            {"name": "Fotoceldas", "slug": "fotoceldas"},
            {"name": "Controles Remotos", "slug": "controles-remotos"},
            {"name": "Receptores", "slug": "receptores-automatizacion"},
            {"name": "Relés", "slug": "reles"},
            {"name": "Contactores", "slug": "contactores"},
        ],
    },
    {
        "name": "Herramientas",
        "slug": "herramientas",
        "code_prefix": "HER",
        "children": [
            {"name": "Crimpadoras", "slug": "crimpadoras"},
            {"name": "Ponchadoras", "slug": "ponchadoras"},
            {"name": "Certificador de Cable", "slug": "certificador-cable"},
            {"name": "Multímetro", "slug": "multimetro"},
            {"name": "Probador de Cable", "slug": "probador-cable"},
            {"name": "Peladora de Cable", "slug": "peladora-cable"},
        ],
    },
    {
        # No forma parte del documento original — cajón de sastre para lo que no
        # encaje en ninguna clasificación, equivalente al "otro" del sistema anterior.
        "name": "Otros",
        "slug": "otros",
        "code_prefix": "OTR",
        "children": [],
    },
]

# Backfill: mapea el `Product.category` (string libre) del sistema anterior a un slug de
# hoja de este árbol. "camara" y "cableado" no alcanzan para elegir subcategoría solos —
# la migración además revisa el nombre del producto (ver
# ai_engine.catalog_matching._format_catalog_line para el mismo tipo de heurística por
# texto) antes de caer en el default de esta tabla.
LEGACY_SLUG_MAP = {
    "camara": "camaras-ip",
    "nvr": "nvr",
    "cableado": "otros-cableado",
    "switch": "switch-poe",
    "control_acceso": "control-de-acceso",
    "videoportero": "videoporteros",
    "barrera": "barreras-vehiculares",
    "automatizacion": "automatizacion",
    "otro": "otros",
}
