from types import SimpleNamespace

from app.ai_engine.learning import record_budget_edit_feedback, record_engineering_edit_feedback
from app.models.ai_feedback_event import AIFeedbackEvent


class _FakeSession:
    """No hace falta una base de datos real para probar la lógica de diffing — solo
    verificar qué AIFeedbackEvent se hubieran agregado."""

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


def _budget_item(product_id, description, quantity):
    return SimpleNamespace(product_id=product_id, description=description, quantity=quantity)


def _budget(ai_generated, items, id=1):
    return SimpleNamespace(id=id, ai_generated=ai_generated, items=items)


def test_untouched_budget_produces_no_events_and_flips_flag():
    db = _FakeSession()
    budget = _budget(True, [_budget_item(1, "Cámara IP", 8)])

    record_budget_edit_feedback(db, project_id=1, budget=budget, new_items=[(1, "Cámara IP", 8)])

    assert db.added == []
    assert budget.ai_generated is False


def test_removed_item_is_recorded():
    db = _FakeSession()
    budget = _budget(True, [_budget_item(1, "Cámara IP", 8), _budget_item(2, "NVR", 1)])

    record_budget_edit_feedback(db, project_id=1, budget=budget, new_items=[(1, "Cámara IP", 8)])

    assert len(db.added) == 1
    event = db.added[0]
    assert event.origin == "human_removed"
    assert event.product_id == 2
    assert event.old_value == "1.0"
    assert event.budget_id == 1


def test_added_item_is_recorded():
    db = _FakeSession()
    budget = _budget(True, [_budget_item(1, "Cámara IP", 8)])

    record_budget_edit_feedback(
        db, project_id=1, budget=budget, new_items=[(1, "Cámara IP", 8), (3, "Switch PoE", 1)]
    )

    assert len(db.added) == 1
    event = db.added[0]
    assert event.origin == "human_added"
    assert event.product_id == 3
    assert event.new_value == "1.0"
    assert event.budget_id == 1


def test_quantity_change_is_recorded_as_modified():
    db = _FakeSession()
    budget = _budget(True, [_budget_item(1, "Cámara IP", 8)])

    record_budget_edit_feedback(db, project_id=1, budget=budget, new_items=[(1, "Cámara IP", 12)])

    assert len(db.added) == 1
    event = db.added[0]
    assert event.origin == "human_modified"
    assert event.field_changed == "quantity"
    assert event.old_value == "8.0"
    assert event.new_value == "12.0"
    assert event.budget_id == 1


def test_already_edited_budget_does_not_record_again():
    db = _FakeSession()
    budget = _budget(False, [_budget_item(1, "Cámara IP", 8)])  # ya no es la sugerencia original de la IA

    record_budget_edit_feedback(db, project_id=1, budget=budget, new_items=[(1, "Cámara IP", 999)])

    assert db.added == []


def test_manually_created_budget_never_records_feedback():
    db = _FakeSession()
    budget = _budget(False, [_budget_item(1, "Cámara IP", 8)])  # nunca vino de la IA

    record_budget_edit_feedback(db, project_id=1, budget=budget, new_items=[(1, "Cámara IP", 1)])

    assert db.added == []


def _engineering(ai_generated, **fields):
    base = {
        "recommended_equipment": None,
        "distribution": None,
        "conduits": None,
        "wiring": None,
        "technical_design": None,
        "observations": None,
    }
    base.update(fields)
    return SimpleNamespace(ai_generated=ai_generated, **base)


def test_engineering_field_change_is_recorded():
    db = _FakeSession()
    engineering = _engineering(True, recommended_equipment="8 cámaras IP", distribution="Perímetro")

    record_engineering_edit_feedback(
        db, project_id=1, engineering=engineering,
        new_values={"recommended_equipment": "8 cámaras IP + 1 NVR", "distribution": "Perímetro"},
    )

    assert len(db.added) == 1
    event = db.added[0]
    assert isinstance(event, AIFeedbackEvent)
    assert event.entity_type == "engineering"
    assert event.field_changed == "recommended_equipment"
    assert event.old_value == "8 cámaras IP"
    assert event.new_value == "8 cámaras IP + 1 NVR"
    assert engineering.ai_generated is False


def test_engineering_untouched_fields_produce_no_events():
    db = _FakeSession()
    engineering = _engineering(True, recommended_equipment="8 cámaras IP")

    record_engineering_edit_feedback(
        db, project_id=1, engineering=engineering, new_values={"recommended_equipment": "8 cámaras IP"}
    )

    assert db.added == []
    assert engineering.ai_generated is False  # igual se marca: ya hubo una edición humana


def test_manually_written_engineering_never_records_feedback():
    db = _FakeSession()
    engineering = _engineering(False, recommended_equipment="Escrito a mano")

    record_engineering_edit_feedback(
        db, project_id=1, engineering=engineering, new_values={"recommended_equipment": "Otra cosa"}
    )

    assert db.added == []
