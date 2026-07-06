from app.ai_engine.catalog_matching import _apply_tag_fallback, _merge_entities_with_matches


def test_matched_entity_gets_product_id_from_match():
    entities = [{"description": "cámaras IP", "quantity": 8}]
    matches = [{"index": 0, "product_id": 5}]

    result = _merge_entities_with_matches(entities, matches)

    assert result == [{"product_id": 5, "description": "cámaras IP", "quantity": 8}]


def test_product_id_zero_means_no_catalog_match():
    entities = [{"description": "instalación", "quantity": 1}]
    matches = [{"index": 0, "product_id": 0}]

    result = _merge_entities_with_matches(entities, matches)

    assert result[0]["product_id"] is None


def test_missing_index_in_matches_is_treated_as_no_match_not_dropped():
    # El modelo puede omitir un índice en la respuesta; la entidad no debe desaparecer.
    entities = [
        {"description": "cámaras IP", "quantity": 8},
        {"description": "cable UTP cat6", "quantity": 200},
    ]
    matches = [{"index": 0, "product_id": 5}]  # índice 1 ausente

    result = _merge_entities_with_matches(entities, matches)

    assert len(result) == 2
    assert result[1]["product_id"] is None
    assert result[1]["description"] == "cable UTP cat6"
    assert result[1]["quantity"] == 200


def test_description_and_quantity_come_from_entities_not_matches():
    # Motor 2 nunca debe poder alterar lo que Motor 1 detectó, solo decidir el product_id.
    entities = [{"description": "doscientos metros de cable", "quantity": 200}]
    matches = [{"index": 0, "product_id": 9}]

    result = _merge_entities_with_matches(entities, matches)

    assert result[0]["description"] == "doscientos metros de cable"
    assert result[0]["quantity"] == 200


CATALOG = [{"id": 1, "name": "Cámara IP", "tags": ["camara"], "synonyms": ["domo"]}]


def test_tag_fallback_resolves_an_item_the_model_could_not():
    items = [{"product_id": None, "description": "8 domo para el perímetro", "quantity": 8}]

    result = _apply_tag_fallback(items, CATALOG)

    assert result[0]["product_id"] == 1


def test_tag_fallback_never_overrides_a_match_the_model_already_found():
    items = [{"product_id": 2, "description": "domo", "quantity": 1}]

    result = _apply_tag_fallback(items, CATALOG)

    assert result[0]["product_id"] == 2  # no se pisa aunque "domo" matchee otro producto


def test_tag_fallback_leaves_truly_unmatched_items_alone():
    items = [{"product_id": None, "description": "mano de obra de instalación", "quantity": 1}]

    result = _apply_tag_fallback(items, CATALOG)

    assert result[0]["product_id"] is None
