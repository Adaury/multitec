from app.ai_engine.tagging import find_product_by_text, normalize_text

CATALOG = [
    {"id": 1, "name": "Cámara IP Domo 4MP", "tags": ["camara", "ip"], "synonyms": ["domo", "cctv"]},
    {"id": 2, "name": "Cable UTP Cat6", "tags": ["cable", "utp"], "synonyms": []},
    {"id": 3, "name": "NVR 8 canales", "tags": ["nvr"], "synonyms": []},
]


def test_normalize_lowercases_and_strips_accents():
    assert normalize_text("Cámara IP") == "camara ip"


def test_normalize_collapses_whitespace():
    assert normalize_text("  cable   utp  ") == "cable utp"


def test_finds_product_by_tag():
    assert find_product_by_text("necesitamos 4 camaras para el patio", CATALOG) == 1


def test_finds_product_by_synonym_not_in_name():
    assert find_product_by_text("un domo para la entrada", CATALOG) == 1


def test_finds_product_by_name_substring():
    assert find_product_by_text("nvr 8 canales para grabar", CATALOG) == 3


def test_returns_none_when_nothing_matches():
    assert find_product_by_text("mano de obra de instalación", CATALOG) is None


def test_does_not_match_partial_word_inside_another_word():
    # "cable" no debe matchear dentro de "cableado" — palabras distintas.
    assert find_product_by_text("cableado eléctrico del panel", CATALOG) is None


def test_matching_is_accent_and_case_insensitive():
    assert find_product_by_text("CÁMARAS para el techo", CATALOG) == 1


def test_empty_description_returns_none():
    assert find_product_by_text("", CATALOG) is None
    assert find_product_by_text("   ", CATALOG) is None


def test_returns_first_matching_product_in_catalog_order():
    catalog = [
        {"id": 10, "name": "Producto A", "tags": ["comun"], "synonyms": []},
        {"id": 20, "name": "Producto B", "tags": ["comun"], "synonyms": []},
    ]
    assert find_product_by_text("necesito lo comun", catalog) == 10
