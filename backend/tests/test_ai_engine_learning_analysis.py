from app.ai_engine.learning_analysis import detect_accessory_candidates, detect_stale_rule_candidates
from app.models.ai_feedback_event import (
    ENTITY_TYPE_BUDGET_ITEM,
    ORIGIN_HUMAN_ADDED,
    ORIGIN_HUMAN_REMOVED,
    AIFeedbackEvent,
)
from app.models.budget import Budget, BudgetItem
from app.models.product import Product
from app.models.technical_rule import ACTION_TYPE_ADD_ACCESSORY, TechnicalRule

from tests.conftest import auth_headers, make_project


def _make_product(db_session, code: str, name: str, tags: list[str]) -> Product:
    product = Product(code=code, name=name, unit="unidad", price=0, cost=0, tags=tags, synonyms=[])
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _make_budget_with_items(db_session, project_id: int, code: str, product_ids: list[int]) -> Budget:
    budget = Budget(code=code, project_id=project_id, total=0)
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)
    for product_id in product_ids:
        db_session.add(BudgetItem(budget_id=budget.id, product_id=product_id, description="x", quantity=1))
    db_session.commit()
    return budget


def _project_id(client, admin_token) -> int:
    return make_project(client, auth_headers(admin_token))["id"]


def test_accessory_candidate_detected_when_pattern_repeats(client, db_session, admin_token):
    source = _make_product(db_session, "FIB-001", "Cable de fibra", ["fibra"])
    added = _make_product(db_session, "ORG-001", "Organizador de rack", ["organizador"])

    for i in range(3):
        project_id = _project_id(client, admin_token)
        budget = _make_budget_with_items(db_session, project_id, f"PRE-A{i}", [source.id, added.id])
        db_session.add(
            AIFeedbackEvent(
                project_id=project_id,
                budget_id=budget.id,
                entity_type=ENTITY_TYPE_BUDGET_ITEM,
                origin=ORIGIN_HUMAN_ADDED,
                product_id=added.id,
                new_value="1.0",
            )
        )
    db_session.commit()

    candidates = detect_accessory_candidates(db_session, min_projects=3, min_ratio=0.5)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source_product_id == source.id
    assert candidate.added_product_id == added.id
    assert candidate.suggested_target_tag == "organizador"
    assert candidate.project_count == 3
    assert candidate.ratio == 1.0
    assert len(candidate.example_project_codes) == 3


def test_accessory_candidate_below_threshold_is_not_proposed(client, db_session, admin_token):
    source = _make_product(db_session, "FIB-001", "Cable de fibra", ["fibra"])
    added = _make_product(db_session, "ORG-001", "Organizador de rack", ["organizador"])

    for i in range(2):  # por debajo de min_projects=3
        project_id = _project_id(client, admin_token)
        budget = _make_budget_with_items(db_session, project_id, f"PRE-B{i}", [source.id, added.id])
        db_session.add(
            AIFeedbackEvent(
                project_id=project_id,
                budget_id=budget.id,
                entity_type=ENTITY_TYPE_BUDGET_ITEM,
                origin=ORIGIN_HUMAN_ADDED,
                product_id=added.id,
                new_value="1.0",
            )
        )
    db_session.commit()

    candidates = detect_accessory_candidates(db_session, min_projects=3, min_ratio=0.5)

    assert candidates == []


def test_accessory_candidate_skipped_when_rule_already_covers_it(client, db_session, admin_token):
    source = _make_product(db_session, "FIB-001", "Cable de fibra", ["fibra"])
    added = _make_product(db_session, "ORG-001", "Organizador de rack", ["organizador"])
    db_session.add(
        TechnicalRule(
            source_product_id=source.id,
            action_type=ACTION_TYPE_ADD_ACCESSORY,
            action_params={"target_tag": "organizador", "quantity": 1, "per_source_units": None},
        )
    )
    db_session.commit()

    for i in range(3):
        project_id = _project_id(client, admin_token)
        budget = _make_budget_with_items(db_session, project_id, f"PRE-C{i}", [source.id, added.id])
        db_session.add(
            AIFeedbackEvent(
                project_id=project_id,
                budget_id=budget.id,
                entity_type=ENTITY_TYPE_BUDGET_ITEM,
                origin=ORIGIN_HUMAN_ADDED,
                product_id=added.id,
                new_value="1.0",
            )
        )
    db_session.commit()

    candidates = detect_accessory_candidates(db_session, min_projects=3, min_ratio=0.5)

    assert candidates == []


def test_stale_rule_candidate_detected_when_accessory_consistently_removed(client, db_session, admin_token):
    source = _make_product(db_session, "FIB-002", "Cable de fibra 2", ["fibra2"])
    accessory = _make_product(db_session, "ORG-002", "Organizador de rack 2", ["organizador2"])
    rule = TechnicalRule(
        source_product_id=source.id,
        action_type=ACTION_TYPE_ADD_ACCESSORY,
        action_params={"target_tag": "organizador2", "quantity": 1, "per_source_units": None},
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    for i in range(3):
        project_id = _project_id(client, admin_token)
        # El accesorio se quitó a mano — no queda en los items finales del budget.
        budget = _make_budget_with_items(db_session, project_id, f"PRE-D{i}", [source.id])
        db_session.add(
            AIFeedbackEvent(
                project_id=project_id,
                budget_id=budget.id,
                entity_type=ENTITY_TYPE_BUDGET_ITEM,
                origin=ORIGIN_HUMAN_REMOVED,
                product_id=accessory.id,
                old_value="1.0",
            )
        )
    db_session.commit()

    candidates = detect_stale_rule_candidates(db_session, min_projects=3, min_ratio=0.5)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.rule_id == rule.id
    assert candidate.source_product_id == source.id
    assert candidate.would_add_product_id == accessory.id
    assert candidate.removed_count == 3
    assert candidate.ratio == 1.0


def test_stale_rule_candidate_not_proposed_when_accessory_kept(client, db_session, admin_token):
    source = _make_product(db_session, "FIB-002", "Cable de fibra 2", ["fibra2"])
    accessory = _make_product(db_session, "ORG-002", "Organizador de rack 2", ["organizador2"])
    db_session.add(
        TechnicalRule(
            source_product_id=source.id,
            action_type=ACTION_TYPE_ADD_ACCESSORY,
            action_params={"target_tag": "organizador2", "quantity": 1, "per_source_units": None},
        )
    )
    db_session.commit()

    for i in range(3):
        project_id = _project_id(client, admin_token)
        # El accesorio se mantiene — sin evento human_removed.
        _make_budget_with_items(db_session, project_id, f"PRE-E{i}", [source.id, accessory.id])
    db_session.commit()

    candidates = detect_stale_rule_candidates(db_session, min_projects=3, min_ratio=0.5)

    assert candidates == []
