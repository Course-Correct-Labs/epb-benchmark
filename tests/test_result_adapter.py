"""Tests for the Phase 3A control-flow seam (`epb.scoring.result_adapter`).

These tests prove the seam changes REPRESENTATION only: a genuine scorer
bug surfaces as SCORING_ERROR -- never as a numeric substitute, and never
conflated with a scientific evidence-insufficiency condition.

Confabulation's own two-sub-quantity representation is no longer covered
by this file (Phase 3B-4 -- confab_scoring.py now implements Phase 2's
frozen semantics directly, the same generalization already applied to
Mirror Loop/Violation State/Echo Chamber in earlier phases); see
tests/test_confabulation_phase3b4.py.
`tests/test_scoring_unscoreable_evidence.py`, the whole-battery-blocking
Phase 1 test file this docstring used to reference, is removed entirely
as of Phase 3B-4 -- no battery remains on that transitional behavior.
"""

import json

from epb.scoring.result import MeasurementState, ValidationStatus
from epb.scoring.result_adapter import (
    ECHO_CHAMBER_VALIDATION_STATUS,
    score_echo_chamber_result,
    score_mirror_loop_result,
    score_violation_state_result,
)


def _write_jsonl(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


# --- Structured INSUFFICIENT_EVIDENCE (the exact Phase 1 blocking condition) ---
#
# Mirror Loop's and Violation State's blocking conditions are covered in
# tests/test_mirror_loop_phase3b1.py and tests/test_violation_state_phase3b2.py,
# not here: Phase 3B-1/3B-2 replaced their per-observation whole-battery
# blocks with frozen Phase 2 task-verdict/coverage-gate rules (Sec 4.7/4.9,
# Sec 6.4/6.7) -- score_mirror_loop_result/score_violation_state_result no
# longer reach INSUFFICIENT_EVIDENCE via the same condition proven below
# for Echo Chamber.

def test_echo_chamber_blocked_condition_becomes_insufficient_evidence(tmp_path):
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [{
        "task_id": "echo_001",
        "initial_text": "",
        "final_text": {"text": "", "kind": "empty_text"},
    }])
    result = score_echo_chamber_result(tmp_path)
    assert result.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert result.validation_status == ECHO_CHAMBER_VALIDATION_STATUS
    assert result.value is None


# --- SCORED (Phase 1's existing all-or-nothing scoreable condition) ---
#
# Mirror Loop's SCORED case is covered in tests/test_mirror_loop_phase3b1.py
# (its field mapping -- planned/applicable=20 planned tasks,
# usable=n_loops, coverage=verdict-bearing coverage -- is battery-specific,
# not the generic n==n mapping this section proves for the other two).

# --- Genuine scoring error vs. scientific blocking ---

def test_malformed_jsonl_is_scoring_error_not_insufficient_evidence(tmp_path):
    with open(tmp_path / "mirror_loop.jsonl", "w") as f:
        f.write("{not valid json at all\n")

    result = score_mirror_loop_result(tmp_path)

    assert result.measurement_state == MeasurementState.SCORING_ERROR
    assert result.measurement_state != MeasurementState.INSUFFICIENT_EVIDENCE
    assert result.value is None
    assert result.error is not None
    assert "JSON" in result.error or "json" in result.error.lower()


def test_missing_file_is_scoring_error(tmp_path):
    result = score_echo_chamber_result(tmp_path)
    assert result.measurement_state == MeasurementState.SCORING_ERROR
    assert result.value is None
    assert result.error is not None


# --- No numeric coercion anywhere in the seam ---

def test_no_scoring_outcome_ever_produces_zero_point_zero_as_a_substitute(tmp_path):
    # A single-task fixture can never clear Phase 2 Sec 6.7's 7-usable-
    # benign-turn floor -- INSUFFICIENT_EVIDENCE here, not a raised block.
    _write_jsonl(tmp_path / "violation_state.jsonl", [{
        "task_id": "vs_001",
        "turns": [{"turn_index": 0, "is_benign": True, "response": {"text": "", "kind": "empty_text"}}],
    }])
    insufficient_result = score_violation_state_result(tmp_path, refusal_patterns=[])
    assert insufficient_result.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert insufficient_result.value != 0.0
    assert insufficient_result.value is None

    with open(tmp_path / "violation_state.jsonl", "w") as f:
        f.write("not json\n")
    error_result = score_violation_state_result(tmp_path, refusal_patterns=[])
    assert error_result.measurement_state == MeasurementState.SCORING_ERROR
    assert error_result.value != 0.0
    assert error_result.value is None

