from types import SimpleNamespace

from app.ai_engine.rules import (
    build_accessory_rule_dicts,
    resolve_calculation_parameter_overrides,
    resolve_engineering_notes,
)
from app.models.technical_rule import (
    ACTION_TYPE_ADD_ACCESSORY,
    ACTION_TYPE_FLAG_ENGINEERING_NOTE,
    ACTION_TYPE_SET_CALCULATION_PARAMETER,
)


def _catalog_rule(source_product_id, target_tag, per_source_units, quantity):
    return SimpleNamespace(
        source_product_id=source_product_id,
        target_tag=target_tag,
        per_source_units=per_source_units,
        quantity=quantity,
    )


def _technical_rule(
    source_product_id,
    action_type,
    target_tag=None,
    per_source_units=None,
    quantity=1,
    parameter_key=None,
    value=None,
    engineering_note=None,
):
    return SimpleNamespace(
        source_product_id=source_product_id,
        action_type=action_type,
        target_tag=target_tag,
        per_source_units=per_source_units,
        quantity=quantity,
        parameter_key=parameter_key,
        value=value,
        engineering_note=engineering_note,
    )


def test_catalog_rules_and_technical_rules_both_produce_dicts():
    catalog_rules = [_catalog_rule(1, "nvr", None, 1)]
    technical_rules = [_technical_rule(1, ACTION_TYPE_ADD_ACCESSORY, target_tag="poe-switch", per_source_units=8)]

    result = build_accessory_rule_dicts(catalog_rules, technical_rules)

    assert {"source_product_id": 1, "target_tag": "nvr", "per_source_units": None, "quantity": 1.0} in result
    assert {"source_product_id": 1, "target_tag": "poe-switch", "per_source_units": 8, "quantity": 1} in result


def test_technical_rule_with_unimplemented_action_type_is_skipped():
    technical_rules = [_technical_rule(1, "unknown_future_type")]

    result = build_accessory_rule_dicts([], technical_rules)

    assert result == []


def test_resolve_calculation_parameter_overrides_only_when_source_present():
    items = [{"product_id": 1, "description": "Fibra monomodo", "quantity": 100}]
    technical_rules = [
        _technical_rule(
            1, ACTION_TYPE_SET_CALCULATION_PARAMETER, parameter_key="cable_waste_margin_pct", value=0.08
        ),
        _technical_rule(  # producto no presente en items -> no aplica
            99, ACTION_TYPE_SET_CALCULATION_PARAMETER, parameter_key="labor_hourly_rate", value=999
        ),
    ]

    overrides = resolve_calculation_parameter_overrides(items, technical_rules)

    assert overrides == {"cable_waste_margin_pct": 0.08}


def test_resolve_calculation_parameter_overrides_takes_the_highest_value():
    items = [
        {"product_id": 1, "description": "Fibra monomodo", "quantity": 100},
        {"product_id": 2, "description": "Fibra multimodo", "quantity": 50},
    ]
    technical_rules = [
        _technical_rule(1, ACTION_TYPE_SET_CALCULATION_PARAMETER, parameter_key="cable_waste_margin_pct", value=0.08),
        _technical_rule(2, ACTION_TYPE_SET_CALCULATION_PARAMETER, parameter_key="cable_waste_margin_pct", value=0.12),
    ]

    overrides = resolve_calculation_parameter_overrides(items, technical_rules)

    assert overrides == {"cable_waste_margin_pct": 0.12}


def test_resolve_calculation_parameter_overrides_ignores_other_action_types():
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 8}]
    technical_rules = [_technical_rule(1, ACTION_TYPE_ADD_ACCESSORY, target_tag="nvr")]

    overrides = resolve_calculation_parameter_overrides(items, technical_rules)

    assert overrides == {}


def test_resolve_engineering_notes_only_when_source_present():
    items = [{"product_id": 1, "description": "Fibra monomodo", "quantity": 100}]
    technical_rules = [
        _technical_rule(
            1, ACTION_TYPE_FLAG_ENGINEERING_NOTE, engineering_note="Verificar distancia máxima de fibra monomodo."
        ),
        _technical_rule(99, ACTION_TYPE_FLAG_ENGINEERING_NOTE, engineering_note="No debería aparecer."),
    ]

    notes = resolve_engineering_notes(items, technical_rules)

    assert notes == ["Verificar distancia máxima de fibra monomodo."]


def test_resolve_engineering_notes_deduplicates_and_preserves_order():
    items = [
        {"product_id": 1, "description": "Fibra monomodo", "quantity": 1},
        {"product_id": 2, "description": "Otra fibra", "quantity": 1},
    ]
    technical_rules = [
        _technical_rule(1, ACTION_TYPE_FLAG_ENGINEERING_NOTE, engineering_note="Nota A"),
        _technical_rule(2, ACTION_TYPE_FLAG_ENGINEERING_NOTE, engineering_note="Nota A"),  # duplicada
        _technical_rule(2, ACTION_TYPE_FLAG_ENGINEERING_NOTE, engineering_note="Nota B"),
    ]

    notes = resolve_engineering_notes(items, technical_rules)

    assert notes == ["Nota A", "Nota B"]
