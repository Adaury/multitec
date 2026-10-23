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
