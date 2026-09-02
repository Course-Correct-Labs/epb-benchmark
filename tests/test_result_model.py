"""Tests for the Phase 3A result architecture (`epb.scoring.result`).

Governing design artifact: EPB_PHASE2_EVIDENCE_SEMANTICS.md Sec 8. These
tests cover architecture/plumbing only -- the shape and derivation rules of
`QuantityResult`, not any battery-specific scientific condition (that is
Phase 3B's scope; see tests/test_result_adapter.py for the Phase 3A
control-flow seam that reuses Phase 1's existing conditions unchanged).
"""

import dataclasses

import pytest

from epb.adapters.base import OBSERVATION_SCHEMA_VERSION
from epb.scoring.result import (
    MeasurementState,
    QuantityResult,
    RESULT_SCHEMA_VERSION,
    ValidationStatus,
)


# --- Enum round-trip ---

@pytest.mark.parametrize("state", list(MeasurementState))
def test_measurement_state_round_trips_through_value(state):
    assert MeasurementState(state.value) is state


@pytest.mark.parametrize("status", list(ValidationStatus))
def test_validation_status_round_trips_through_value(status):
    assert ValidationStatus(status.value) is status


def test_measurement_state_exact_vocabulary():
    """Phase 2 Sec 8.1's exact frozen vocabulary -- this phase must not
    rename or add to it."""
    assert {s.value for s in MeasurementState} == {
        "scored",
        "insufficient_evidence",
        "no_applicable_evidence",
        "execution_failure",
        "scoring_error",
    }


def test_validation_status_exact_vocabulary():
    """Phase 2 Sec 8.2's exact frozen vocabulary."""
    assert {s.value for s in ValidationStatus} == {"frozen", "provisional", "unresolved"}


# --- QuantityResult round trip ---

def test_quantity_result_to_dict_from_dict_round_trip():
    qr = QuantityResult(
        quantity="mirror_loop.collapse",
        measurement_state=MeasurementState.SCORED,
        validation_status=ValidationStatus.PROVISIONAL,
        value=87.5,
        planned=10,
        applicable=10,
        usable=10,
        details={"epb_phi": 87.5},
    )
    restored = QuantityResult.from_dict(qr.to_dict())
    assert restored.quantity == qr.quantity
    assert restored.measurement_state == qr.measurement_state
    assert restored.validation_status == qr.validation_status
    assert restored.value == qr.value
    assert restored.planned == qr.planned
    assert restored.applicable == qr.applicable
    assert restored.usable == qr.usable
    assert restored.details == qr.details
    assert restored.canonical_consumption_eligible == qr.canonical_consumption_eligible


def test_quantity_result_blocked_round_trips():
    qr = QuantityResult(
        quantity="mirror_loop.collapse",
        measurement_state=MeasurementState.INSUFFICIENT_EVIDENCE,
        validation_status=ValidationStatus.PROVISIONAL,
        blocked=({"task_id": "ml_001", "reason": "non_valid_text_observation"},),
    )
    restored = QuantityResult.from_dict(qr.to_dict())
    assert restored.blocked == qr.blocked


# --- Derivation exactness (this phase's governing prompt Sec 2) ---

@pytest.mark.parametrize(
    "measurement_state,validation_status,expected",
    [
        (MeasurementState.SCORED, ValidationStatus.FROZEN, True),
        (MeasurementState.SCORED, ValidationStatus.PROVISIONAL, False),
        (MeasurementState.SCORED, ValidationStatus.UNRESOLVED, False),
        (MeasurementState.INSUFFICIENT_EVIDENCE, ValidationStatus.FROZEN, False),
        (MeasurementState.NO_APPLICABLE_EVIDENCE, ValidationStatus.FROZEN, False),
        (MeasurementState.EXECUTION_FAILURE, ValidationStatus.FROZEN, False),
        (MeasurementState.SCORING_ERROR, ValidationStatus.FROZEN, False),
    ],
)
def test_canonical_consumption_eligible_derivation(measurement_state, validation_status, expected):
    qr = QuantityResult(
        quantity="x",
        measurement_state=measurement_state,
        validation_status=validation_status,
        value=1.0 if measurement_state == MeasurementState.SCORED else None,
    )
    assert qr.canonical_consumption_eligible is expected


def test_canonical_flag_cannot_be_forged_through_from_dict():
    """Canonical-consumption adversarial test: a hand-tampered persisted
    dict claiming `canonical_consumption_eligible: true` alongside axes
    that would truthfully derive False must not fool `from_dict` -- the
    flag is re-derived from measurement_state/validation_status only,
    never read back from the persisted value, so `results.json` cannot
    be edited to forge canonical eligibility."""
    tampered = {
        "quantity": "x",
        "measurement_state": "scored",
        "validation_status": "provisional",
        "value": 1.0,
        "canonical_consumption_eligible": True,  # forged -- must be ignored
        "coverage": 1.0,
    }
    restored = QuantityResult.from_dict(tampered)
    assert restored.canonical_consumption_eligible is False


def test_canonical_flag_is_not_a_settable_field():
    """The derived flag has no constructor parameter and no setter -- a
    call site cannot set it directly or set it inconsistently with the two
    axes it depends on (this phase's governing prompt Sec 2)."""
    qr = QuantityResult(
        quantity="x",
        measurement_state=MeasurementState.SCORED,
        validation_status=ValidationStatus.FROZEN,
        value=1.0,
    )
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        qr.canonical_consumption_eligible = False
    with pytest.raises(TypeError):
        QuantityResult(  # noqa: no such constructor parameter
            quantity="x",
            measurement_state=MeasurementState.SCORED,
            validation_status=ValidationStatus.FROZEN,
            canonical_consumption_eligible=True,
        )


def test_measurement_state_is_frozen_and_cannot_be_mutated_after_construction():
    qr = QuantityResult(
        quantity="x",
        measurement_state=MeasurementState.INSUFFICIENT_EVIDENCE,
        validation_status=ValidationStatus.PROVISIONAL,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        qr.measurement_state = MeasurementState.SCORED


# --- Coverage metadata ---

def test_planned_applicable_usable_remain_separate_fields():
    qr = QuantityResult(
        quantity="x",
        measurement_state=MeasurementState.SCORED,
        validation_status=ValidationStatus.PROVISIONAL,
        value=1.0,
        planned=30,
        applicable=12,
        usable=10,
    )
    assert (qr.planned, qr.applicable, qr.usable) == (30, 12, 10)
    assert qr.coverage == 10 / 12


def test_coverage_is_none_not_zero_when_applicable_is_none():
    """Undefined coverage (no applicable count known) must not be
    represented as 0 -- that would be a false zero-pathology claim."""
    qr = QuantityResult(
        quantity="x",
        measurement_state=MeasurementState.SCORING_ERROR,
        validation_status=ValidationStatus.PROVISIONAL,
        error="boom",
    )
    assert qr.applicable is None
    assert qr.coverage is None
    assert qr.to_dict()["coverage"] is None


def test_coverage_is_none_not_zero_when_applicable_is_zero():
    """applicable == 0 (NO_APPLICABLE_EVIDENCE) must not silently produce a
    coverage of 0/0 == error or a false 0.0 -- coverage is undefined."""
    qr = QuantityResult(
        quantity="x",
        measurement_state=MeasurementState.NO_APPLICABLE_EVIDENCE,
        validation_status=ValidationStatus.UNRESOLVED,
        planned=0,
        applicable=0,
    )
    assert qr.coverage is None


# --- No numeric coercion ---

@pytest.mark.parametrize(
    "measurement_state",
    [
        MeasurementState.INSUFFICIENT_EVIDENCE,
        MeasurementState.NO_APPLICABLE_EVIDENCE,
        MeasurementState.EXECUTION_FAILURE,
        MeasurementState.SCORING_ERROR,
    ],
)
def test_non_scored_states_never_default_value_to_a_number(measurement_state):
    qr = QuantityResult(
        quantity="x",
        measurement_state=measurement_state,
        validation_status=ValidationStatus.PROVISIONAL,
    )
    assert qr.value is None


# --- Versioning ---

def test_result_schema_version_is_persisted():
    qr = QuantityResult(
        quantity="x",
        measurement_state=MeasurementState.SCORED,
        validation_status=ValidationStatus.PROVISIONAL,
        value=1.0,
    )
    assert qr.to_dict()["schema_version"] == RESULT_SCHEMA_VERSION


def test_result_schema_version_distinct_from_observation_schema_version():
    """This phase's governing prompt Sec 10: must not silently reuse
    OBSERVATION_SCHEMA_VERSION -- the two must be independently-defined,
    independently-versionable constants in separate modules, each with its
    own name. (Their current integer values may coincide at 1; that is not
    the same claim as being the same constant.)
    """
    from epb.adapters import base as base_module
    from epb.scoring import result as result_module

    assert hasattr(result_module, "RESULT_SCHEMA_VERSION")
    assert hasattr(base_module, "OBSERVATION_SCHEMA_VERSION")
    assert not hasattr(base_module, "RESULT_SCHEMA_VERSION")
    assert not hasattr(result_module, "OBSERVATION_SCHEMA_VERSION")
