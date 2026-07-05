from app.ai_engine.catalog_matching import _merge_entities_with_matches


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
