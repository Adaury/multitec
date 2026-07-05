from types import SimpleNamespace

from app.ai_engine.rules import build_accessory_rule_dicts
from app.models.technical_rule import ACTION_TYPE_ADD_ACCESSORY


def _catalog_rule(source_product_id, target_tag, per_source_units, quantity):
    return SimpleNamespace(
        source_product_id=source_product_id,
        target_tag=target_tag,
        per_source_units=per_source_units,
        quantity=quantity,
    )


def _technical_rule(source_product_id, action_type, target_tag=None, per_source_units=None, quantity=1):
    return SimpleNamespace(
        source_product_id=source_product_id,
        action_type=action_type,
        target_tag=target_tag,
        per_source_units=per_source_units,
        quantity=quantity,
    )


def test_catalog_rules_and_technical_rules_both_produce_dicts():
    catalog_rules = [_catalog_rule(1, "nvr", None, 1)]
    technical_rules = [_technical_rule(1, ACTION_TYPE_ADD_ACCESSORY, target_tag="poe-switch", per_source_units=8)]

    result = build_accessory_rule_dicts(catalog_rules, technical_rules)

    assert {"source_product_id": 1, "target_tag": "nvr", "per_source_units": None, "quantity": 1.0} in result
    assert {"source_product_id": 1, "target_tag": "poe-switch", "per_source_units": 8, "quantity": 1} in result


def test_technical_rule_with_unimplemented_action_type_is_skipped():
    technical_rules = [_technical_rule(1, "set_calculation_parameter")]

    result = build_accessory_rule_dicts([], technical_rules)

    assert result == []
