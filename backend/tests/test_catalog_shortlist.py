from types import SimpleNamespace

from app.ai_engine import catalog_matching as cm
from app.ai_engine import ollama_client


def _product(i, name, category="Cámaras", tags=None, synonyms=None):
    return {"id": i, "name": name, "category": category, "unit": "unidad", "tags": tags or [], "synonyms": synonyms or []}


def _big_catalog(n=80):
    catalog = [_product(i, f"Producto genérico {i}", "Varios") for i in range(1, n + 1)]
    catalog.append(_product(1001, "NVR 32 canales", "NVR", ["nvr"], ["grabador 32 canales"]))
    catalog.append(_product(1002, "Cámara IP bala 4MP Hikvision", "Cámaras Bullet", ["camara", "ip"], ["camara exterior 4mp"]))
    catalog.append(_product(1003, "Disco duro 4TB videovigilancia", "Discos Duros", ["disco"], ["disco 4 teras"]))
    return catalog


def test_small_catalog_goes_whole_to_the_model():
    catalog = [_product(i, f"Producto {i}") for i in range(1, 11)]

    assert cm.shortlist_catalog([{"quantity": 1, "description": "algo"}], catalog) == catalog


def test_large_catalog_is_cut_down_to_the_similar_products():
    catalog = _big_catalog()
    entities = [
        {"quantity": 1, "description": "NVR de 32 canales"},
        {"quantity": 16, "description": "Cámaras IP de 4 megapíxeles"},
        {"quantity": 2, "description": "Discos duros de 4 teras"},
    ]

    short = cm.shortlist_catalog(entities, catalog)
    ids = {p["id"] for p in short}

    assert {1001, 1002, 1003} <= ids
    assert len(short) <= cm.MAX_PROMPT_PRODUCTS
    assert len(short) < len(catalog) // 4  # la inmensa mayoría de los "genéricos" no viaja al modelo


def test_synonyms_are_the_strongest_signal():
    catalog = _big_catalog()

    # "grabador de 32 canales" no comparte el nombre exacto, pero sí el sinónimo del producto.
    score_syn = cm._candidate_score("grabador 32 canales", catalog[-3])
    score_other = cm._candidate_score("grabador 32 canales", catalog[0])

    assert score_syn > score_other


def test_plural_and_accents_do_not_hide_a_match():
    product = _product(1, "Cámara domo", "Cámaras", ["camara"])

    assert cm._candidate_score("CÁMARAS domo", product) > 0


def test_nothing_similar_still_returns_a_bounded_slice():
    catalog = _big_catalog()

    short = cm.shortlist_catalog([{"quantity": 1, "description": "zzzz qqqq"}], catalog)

    assert 0 < len(short) <= cm.MAX_PROMPT_PRODUCTS


def _fake_client(monkeypatch, content, calls):
    class FakeClient:
        def chat(self, **kwargs):
            calls.append(kwargs)
            if isinstance(content, Exception):
                raise content
            return SimpleNamespace(message=SimpleNamespace(content=content))

    monkeypatch.setattr(cm, "get_client", lambda: FakeClient())


def test_clear_matches_are_resolved_by_text_without_calling_the_model(monkeypatch):
    """Con un catálogo grande lo que el texto resuelve con claridad no pasa por la IA: en esta
    máquina cada token generado cuesta ~0.4 s y la IA tardaba más de 3 minutos."""
    calls = []
    _fake_client(monkeypatch, '{"product_ids": [999]}', calls)
    entities = [
        {"quantity": 1, "description": "NVR de 32 canales"},
        {"quantity": 2, "description": "Discos duros de 4 teras"},
    ]

    items = cm.match_entities_to_catalog(entities, _big_catalog(200))

    assert calls == []
    assert [i["product_id"] for i in items] == [1001, 1003]


def test_only_ambiguous_entities_reach_the_model_with_a_bounded_prompt(monkeypatch):
    calls = []
    _fake_client(monkeypatch, '{"product_ids": [1002]}', calls)
    catalog = _big_catalog(200)
    # "camara" empata entre dos productos casi iguales: es una decisión para la IA.
    catalog.append(_product(1004, "Cámara IP domo 4MP Hikvision", "Cámaras Domo", ["camara", "ip"], ["camara domo 4mp"]))
    entities = [
        {"quantity": 1, "description": "NVR de 32 canales"},  # claro: por texto
        {"quantity": 16, "description": "cámara ip 4mp hikvision"},  # ambiguo: bala o domo
    ]

    items = cm.match_entities_to_catalog(entities, catalog)

    assert len(calls) == 1
    prompt = calls[0]["messages"][0]["content"]
    assert prompt.count("- id=") <= cm.MAX_PROMPT_PRODUCTS
    assert "id=1002" in prompt and "id=1004" in prompt
    assert "id=150" not in prompt  # los genéricos no viajan
    assert "NVR de 32 canales" not in prompt  # lo ya resuelto tampoco se vuelve a preguntar
    assert calls[0]["options"]["num_predict"] == 40 + 8 * 1  # solo 1 entidad ambigua
    assert [i["product_id"] for i in items] == [1001, 1002]


def test_a_failing_model_degrades_to_text_matching_instead_of_failing_the_quote(monkeypatch):
    calls = []
    _fake_client(monkeypatch, RuntimeError("ollama caído"), calls)
    catalog = _big_catalog(200)
    entities = [
        {"quantity": 1, "description": "NVR de 32 canales"},
        {"quantity": 3, "description": "algo rarísimo sin parecido"},
    ]

    items = cm.match_entities_to_catalog(entities, catalog)

    assert items[0]["product_id"] == 1001  # por texto
    assert items[1]["product_id"] is None  # sin producto, pero la línea se conserva
    assert items[1]["quantity"] == 3


def test_every_ollama_call_gets_a_global_response_cap(monkeypatch):
    seen = {}

    def fake_chat(self, *args, **kwargs):
        seen.update(kwargs)
        return "ok"

    monkeypatch.setattr(ollama_client.ollama.Client, "chat", fake_chat)
    client = ollama_client.get_client()

    client.chat(model="llama3.2", messages=[], options={"num_gpu": 0})
    assert seen["options"]["num_predict"] == ollama_client.MAX_RESPONSE_TOKENS
    assert seen["options"]["num_gpu"] == 0

    # Quien necesita menos (o más) pasa el suyo y se respeta.
    client.chat(model="llama3.2", messages=[], options={"num_predict": 100})
    assert seen["options"]["num_predict"] == 100


def test_numbers_pick_the_right_model_among_near_identical_products():
    catalog = _big_catalog() + [
        _product(2001, "Switch PoE 8 puertos", "Switch PoE", ["poe-switch"]),
        _product(2002, "Switch PoE 16 puertos Gigabit", "Switch PoE", ["poe-switch"]),
        _product(2003, "Switch PoE 24 puertos Gigabit", "Switch PoE", ["poe-switch"]),
    ]

    resolved, ambiguous = cm.resolve_confident_matches([{"quantity": 1, "description": "Switch PoE de 16 puertos"}], catalog)

    assert resolved == {0: 2002}
    assert ambiguous == []


def test_entities_that_resemble_nothing_never_reach_the_model(monkeypatch):
    calls = []
    _fake_client(monkeypatch, '{"product_ids": [1001]}', calls)
    entities = [{"quantity": 1, "description": "servicio de visualización desde el celular"}]

    items = cm.match_entities_to_catalog(entities, _big_catalog(200))

    assert calls == []  # preguntarle solo lo empuja a inventar un producto
    assert items[0]["product_id"] is None
    assert items[0]["quantity"] == 1


def test_measurements_are_not_materials():
    from app.ai_engine.nlu import is_measurement_entity

    for text in ["metros", "40 metros", "Distancia promedio por cámara 40 metros", "Altura de instalación 3.5 metros", "3.5"]:
        assert is_measurement_entity(text), text
    for text in ["200 metros de cable UTP", "metros de cable", "cámaras IP", "NVR de 32 canales"]:
        assert not is_measurement_entity(text), text
