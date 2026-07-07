"""Datos semilla del catálogo base (§ catálogo inteligente v2). Un set mínimo de productos
reales de CCTV/redes con los campos que alimentan Motor 2 (tags/synonyms) y Motor 5
(resolution_mp, channel_capacity) ya cargados — no placeholders en 0/null — para que un
entorno nuevo tenga desde el día uno un catálogo utilizable por generate-from-survey en
vez de uno vacío. `category_slug` referencia app/db/taxonomy.py; `seed_products` en
app/db/seed.py resuelve el category_id y genera el code igual que POST /catalog.
"""

PRODUCT_CATALOG_SEED = [
    {
        "name": "Cámara IP 4MP",
        "category_slug": "camaras-ip",
        "unit": "unidad",
        "price": 4500,
        "cost": 2800,
        "resolution_mp": 4,
        "tags": ["camara", "camara ip", "ip", "domo", "cctv", "vigilancia"],
        "synonyms": ["camarita", "camara", "ojo", "camara de seguridad"],
    },
    {
        "name": "Cámara Bullet 5MP",
        "category_slug": "camaras-bullet",
        "unit": "unidad",
        "price": 6500,
        "cost": 4000,
        "resolution_mp": 5,
        "tags": ["camara", "camara ip", "bullet", "ip", "cctv", "vigilancia"],
        "synonyms": ["camarita", "camara", "camara de seguridad", "bullet"],
    },
    {
        "name": "NVR 8 canales PoE",
        "category_slug": "nvr",
        "unit": "unidad",
        "price": 8500,
        "cost": 5500,
        "channel_capacity": 8,
        "tags": ["nvr", "grabador", "grabador de video"],
        "synonyms": ["grabadora", "nvr de 8 canales", "dvr ip"],
    },
    {
        "name": "Switch PoE 8 puertos",
        "category_slug": "switch-poe",
        "unit": "unidad",
        "price": 3200,
        "cost": 1800,
        "channel_capacity": 8,
        "tags": ["poe-switch", "switch", "switch poe"],
        "synonyms": ["switch de red poe", "inyector poe"],
    },
    {
        "name": "Caja de cable UTP (305m)",
        "category_slug": "cableado",
        "unit": "caja",
        "price": 350,
        "cost": 200,
        "tags": ["cable", "utp", "caja de cable", "cableado"],
        "synonyms": ["caja de utp", "caja de red"],
    },
    {
        "name": "Caja de cable coaxial (305m)",
        "category_slug": "cableado",
        "unit": "caja",
        "price": 250,
        "cost": 150,
        "tags": ["cable", "coaxial", "caja de cable", "cableado"],
        "synonyms": ["caja de coaxial"],
    },
    {
        "name": "Caja de cable de fibra óptica (1000m)",
        "category_slug": "cableado",
        "unit": "caja",
        "price": 8000,
        "cost": 5000,
        "tags": ["cable", "fibra", "fibra optica", "caja de cable", "cableado"],
        "synonyms": ["caja de fibra"],
    },
]
