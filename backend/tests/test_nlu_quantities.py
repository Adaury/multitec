from app.ai_engine.nlu import _spec_number_is_not_quantity as fix


def test_spec_number_taken_as_quantity_becomes_one_unit():
    assert fix({"description": "un NVR de 16 canales", "quantity": 16})["quantity"] == 1
    assert fix({"description": "switch PoE de 8 puertos", "quantity": 8})["quantity"] == 1
    assert fix({"description": "disco de 2TB", "quantity": 2})["quantity"] == 1


def test_real_quantities_are_kept():
    assert fix({"description": "8 cámaras de 4 megapíxeles", "quantity": 8})["quantity"] == 8
    assert fix({"description": "2 NVR de 16 canales", "quantity": 2})["quantity"] == 2
    assert fix({"description": "cable UTP de 200 metros", "quantity": 200})["quantity"] == 200
    assert fix({"description": "4 cámaras exteriores", "quantity": 4})["quantity"] == 4


def test_places_and_client_belongings_are_not_for_sale():
    from app.ai_engine.nlu import is_not_for_sale_entity as not_for_sale

    assert not_for_sale("el celular")
    assert not_for_sale("internet")
    assert not_for_sale("la casa")
    assert not_for_sale("Computadora")
    # Un producto real que menciona esas palabras se conserva.
    assert not not_for_sale("router wifi")
    assert not not_for_sale("cable de internet")
    assert not not_for_sale("rack")
    assert not not_for_sale("cámaras exteriores")
    assert not not_for_sale("")
