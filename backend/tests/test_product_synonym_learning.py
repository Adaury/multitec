from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.ai_engine.catalog_matching import match_entities_to_catalog
from app.ai_engine.learning import MIN_CONFIRMATIONS, get_learned_matches
from app.models.product_match_correction import ProductMatchCorrection
from tests.conftest import auth_headers, make_category, make_project


def _product(client, headers, name, **extra):
    category_id = make_category(client, headers, name=f"Cat {name}", code_prefix=None)["id"]
    payload = {"category_id": category_id, "name": name, "unit": "unidad", "price": 100, **extra}
    resp = client.post("/api/catalog", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _generate_ai_budget(client, headers, project_id, items):
    """Presupuesto generado por la IA (ai_generated=True) con las líneas dadas."""
    with (
        patch("app.ai_engine.documents.suggest_budget_items", return_value=items),
        patch("app.ai_engine.documents.draft_engineering", side_effect=HTTPException(status_code=400, detail="x")),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project_id}/generate-from-survey", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["budget"]


def _edit_budget(client, headers, budget_id, lines):
    items = [{"product_id": pid, "description": desc, "quantity": qty, "unit_price": 100} for pid, desc, qty in lines]
    resp = client.put(f"/api/budgets/{budget_id}", json={"items": items}, headers=headers)
    assert resp.status_code == 200, resp.text


def _corrections(db_session):
    db_session.expire_all()
    return db_session.query(ProductMatchCorrection).order_by(ProductMatchCorrection.id).all()


def test_replacing_wrong_product_records_spoken_phrase(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    wrong = _product(client, headers, "Cámara bullet")
    right = _product(client, headers, "Cámara domo 4MP")
    budget = _generate_ai_budget(
        client, headers, project["id"], [{"product_id": wrong["id"], "description": "domo", "quantity": 4}]
    )

    _edit_budget(client, headers, budget["id"], [(right["id"], right["name"], 4)])

    rows = _corrections(db_session)
    assert len(rows) == 1
    assert rows[0].spoken_text == "domo"
    assert rows[0].ai_product_id == wrong["id"]
    assert rows[0].human_product_id == right["id"]
    assert rows[0].project_id == project["id"]


def test_unmatched_line_picked_by_human_records_correction(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _product(client, headers, "Cable UTP Cat6")
    budget = _generate_ai_budget(
        client, headers, project["id"], [{"product_id": None, "description": "cable de red", "quantity": 100}]
    )

    _edit_budget(client, headers, budget["id"], [(product["id"], product["name"], 100)])

    rows = _corrections(db_session)
    assert [(r.spoken_text, r.ai_product_id, r.human_product_id) for r in rows] == [("cable de red", None, product["id"])]


def test_ambiguous_replacements_are_not_learned(client, admin_token, db_session):
    """Dos líneas quitadas y dos agregadas con la misma cantidad: no se sabe cuál reemplaza a cuál."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    a, b = _product(client, headers, "Producto A"), _product(client, headers, "Producto B")
    new1, new2 = _product(client, headers, "Nuevo 1"), _product(client, headers, "Nuevo 2")
    budget = _generate_ai_budget(
        client,
        headers,
        project["id"],
        [
            {"product_id": a["id"], "description": "cosa uno", "quantity": 2},
            {"product_id": b["id"], "description": "cosa dos", "quantity": 2},
        ],
    )
    _edit_budget(client, headers, budget["id"], [(new1["id"], new1["name"], 2), (new2["id"], new2["name"], 2)])
    assert _corrections(db_session) == []


def test_lines_named_after_their_own_product_are_not_learned(client, admin_token, db_session):
    """Un accesorio agregado por reglas se llama como su producto: nadie lo dijo en voz alta."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    accessory = _product(client, headers, "Conector RJ45")
    other = _product(client, headers, "Conector RJ45 blindado")
    budget = _generate_ai_budget(
        client, headers, project["id"], [{"product_id": accessory["id"], "description": "Conector RJ45", "quantity": 8}]
    )
    _edit_budget(client, headers, budget["id"], [(other["id"], other["name"], 8)])
    assert _corrections(db_session) == []


def test_editing_a_human_budget_does_not_record_corrections(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    a, b = _product(client, headers, "Uno"), _product(client, headers, "Dos")
    budget = _generate_ai_budget(
        client, headers, project["id"], [{"product_id": a["id"], "description": "algo", "quantity": 1}]
    )
    _edit_budget(client, headers, budget["id"], [(a["id"], a["name"], 1)])  # primera edición: ya no es de la IA
    _edit_budget(client, headers, budget["id"], [(b["id"], b["name"], 1)])
    assert _corrections(db_session) == []


# --- umbrales de lo aprendido --------------------------------------------------------------


def _add_corrections(db_session, project_id, phrase, product_id, times):
    for _ in range(times):
        db_session.add(ProductMatchCorrection(project_id=project_id, spoken_text=phrase, human_product_id=product_id))
    db_session.commit()


def test_single_correction_is_only_a_hint_but_repeated_one_overrides(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _product(client, headers, "Cámara domo 4MP")

    _add_corrections(db_session, project["id"], "Domo", product["id"], 1)
    learned = get_learned_matches(db_session)
    assert learned.overrides == {}
    assert learned.hints == [("domo", product["id"])]

    _add_corrections(db_session, project["id"], "domo ", product["id"], MIN_CONFIRMATIONS - 1)
    learned = get_learned_matches(db_session)
    assert learned.overrides == {"domo": product["id"]}
    assert learned.hints == []  # ya no es solo una pista


def test_conflicting_corrections_do_not_override(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    a, b = _product(client, headers, "Cámara A"), _product(client, headers, "Cámara B")
    _add_corrections(db_session, project["id"], "domo", a["id"], 2)
    _add_corrections(db_session, project["id"], "domo", b["id"], 2)
    assert get_learned_matches(db_session).overrides == {}


# --- uso en el emparejamiento ---------------------------------------------------------------


CATALOG = [
    {"id": 1, "name": "Cámara bullet", "category": "CCTV", "unit": "unidad", "tags": [], "synonyms": []},
    {"id": 2, "name": "Cámara domo 4MP", "category": "CCTV", "unit": "unidad", "tags": [], "synonyms": []},
]


def _fake_ollama(matches, seen=None):
    class Client:
        def chat(self, **kwargs):
            if seen is not None:
                seen["prompt"] = kwargs["messages"][0]["content"]
            return SimpleNamespace(message=SimpleNamespace(content=f'{{"matches": {matches}}}'))

    return Client()


def test_confirmed_phrase_overrides_the_model_match():
    from app.ai_engine.learning import LearnedMatches

    entities = [{"description": "3 domos en el patio", "quantity": 3}, {"description": "cámara bullet", "quantity": 1}]
    model_says = '[{"index": 0, "product_id": 1}, {"index": 1, "product_id": 1}]'  # se equivoca en el domo
    with patch("app.ai_engine.catalog_matching.get_client", return_value=_fake_ollama(model_says)):
        items = match_entities_to_catalog(entities, CATALOG, LearnedMatches(overrides={"domos": 2}))
    assert [i["product_id"] for i in items] == [2, 1]  # solo cambia la línea que dice "domos"


def test_override_for_a_product_no_longer_in_catalog_is_ignored():
    from app.ai_engine.learning import LearnedMatches

    entities = [{"description": "domo", "quantity": 1}]
    with patch("app.ai_engine.catalog_matching.get_client", return_value=_fake_ollama('[{"index": 0, "product_id": 1}]')):
        items = match_entities_to_catalog(entities, CATALOG, LearnedMatches(overrides={"domo": 999}))
    assert items[0]["product_id"] == 1


def test_hints_reach_the_prompt_only_when_relevant():
    from app.ai_engine.learning import LearnedMatches

    seen = {}
    learned = LearnedMatches(hints=[("domo exterior", 2), ("cable coaxial", 1)])
    entities = [{"description": "dos domo en la entrada", "quantity": 2}]
    with patch("app.ai_engine.catalog_matching.get_client", return_value=_fake_ollama('[{"index": 0, "product_id": 2}]', seen)):
        match_entities_to_catalog(entities, CATALOG, learned)
    assert '"domo exterior" → id=2: Cámara domo 4MP' in seen["prompt"]
    assert "cable coaxial" not in seen["prompt"]  # no comparte palabras con lo detectado

    with patch("app.ai_engine.catalog_matching.get_client", return_value=_fake_ollama('[{"index": 0, "product_id": 2}]', seen)):
        match_entities_to_catalog(entities, CATALOG, None)
    assert "Correcciones anteriores" not in seen["prompt"]


# --- propuesta de sinónimos al admin ---------------------------------------------------------


def test_synonym_candidate_appears_after_repeated_corrections_and_disappears_once_added(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _product(client, headers, "Cámara domo 4MP")

    _add_corrections(db_session, project["id"], "domo", product["id"], 1)
    body = client.post("/api/ai-feedback-events/analyze", headers=headers).json()
    assert body["synonym_candidates"] == []  # una sola corrección no alcanza

    _add_corrections(db_session, project["id"], "domo", product["id"], 1)
    body = client.post("/api/ai-feedback-events/analyze", headers=headers).json()
    assert len(body["synonym_candidates"]) == 1
    candidate = body["synonym_candidates"][0]
    assert (candidate["phrase"], candidate["product_id"], candidate["confirmations"]) == ("domo", product["id"], 2)
    assert candidate["example_project_codes"] == [project["code"]]

    update = client.put(f"/api/catalog/{product['id']}", json={"synonyms": ["domo"]}, headers=headers)
    assert update.status_code == 200, update.text
    body = client.post("/api/ai-feedback-events/analyze", headers=headers).json()
    assert body["synonym_candidates"] == []  # el catálogo ya lo reconoce


def test_tied_phrases_produce_no_synonym_candidate(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    a, b = _product(client, headers, "Cámara A"), _product(client, headers, "Cámara B")
    _add_corrections(db_session, project["id"], "domo", a["id"], 2)
    _add_corrections(db_session, project["id"], "domo", b["id"], 2)
    body = client.post("/api/ai-feedback-events/analyze", headers=headers).json()
    assert body["synonym_candidates"] == []
