"""Tests for Phase 3B-1: Mirror Loop's frozen battery-specific evidence
semantics (EPB_PHASE2_EVIDENCE_SEMANTICS.md Sec 4.4-4.9).

Covers the acceptance scenarios (A-H) and invariants required by this
phase's governing prompt Sec 11/Sec 17, exercising both the raw scorer
(`epb.scoring.mirror_loop_scoring.score_mirror_loop`) and the structured-
result wrapper (`epb.scoring.result_adapter.score_mirror_loop_result`).
"""

import json

import pytest

from epb.scoring.mirror_loop_scoring import (
    CENSORED,
    COLLAPSED,
    MIRROR_LOOP_MIN_VERDICT_BEARING_TASKS,
    NOT_COLLAPSED,
    score_mirror_loop,
)
from epb.scoring.result import MeasurementState, ValidationStatus
from epb.scoring.result_adapter import (
    MIRROR_LOOP_VALIDATION_STATUS,
    score_mirror_loop_result,
)


def _write_jsonl(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _obs(text, kind="valid_text"):
    return {"text": text, "kind": kind}


def _collapsing_task(task_id, trailing_break=False):
    """4 identical valid responses -- 3 consecutive zero-delta transitions,
    which fires the unmodified detect_collapse formula regardless of
    whether the chain later completes. Optionally followed by one invalid
    response, to test irrevocability (Scenario A/H)."""
    responses = [_obs("identical response text") for _ in range(4)]
    if trailing_break:
        responses.append(_obs("", "empty_text"))
    return {"task_id": task_id, "responses": responses}


_DISTINCT_TEXTS = [
    "The quick brown fox jumps over the lazy dog near the riverbank.",
    "Quantum entanglement puzzles physicists studying distant particles.",
    "1234567890 completely unrelated numeric content appears here today.",
    "Zebras migrate across grasslands searching for fresh water sources.",
    "Q",
]


def _complete_non_collapsing_task(task_id, n_steps=5):
    """n_steps distinct, mutually dissimilar responses -- collapse never
    fires, and the prefix is complete (Scenario C)."""
    return {"task_id": task_id, "responses": [_obs(t) for t in _DISTINCT_TEXTS[:n_steps]]}


def _censored_task_with_transitions(task_id):
    """2 distinct valid responses then a break -- some usable transitions
    exist, but not enough to fire collapse, and the prefix is incomplete
    (Scenario B/D)."""
    return {
        "task_id": task_id,
        "responses": [_obs("first distinct response"), _obs("second distinct response"), _obs("", "empty_text")],
    }


def _censored_task_no_transitions(task_id):
    """1 valid response then a break -- zero usable transitions."""
    return {"task_id": task_id, "responses": [_obs("only one response"), _obs("", "empty_text")]}


# =====================================================================
# Scenario A -- irrevocable positive
# =====================================================================

def test_scenario_a_irrevocable_positive(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [_collapsing_task("a", trailing_break=True)])

    result = score_mirror_loop(tmp_path)
    detail = result["details"][0]

    assert detail["verdict"] == COLLAPSED
    assert detail["verdict"] != CENSORED
    assert detail["collapse_established"] is True
    assert detail["prefix_complete"] is False  # broke before the 5th response
    assert result["collapsed_count"] == 1
    assert result["censored_count"] == 0
    assert result["n_loops"] == 1  # verdict-bearing


# =====================================================================
# Scenario B -- interrupted negative
# =====================================================================

def test_scenario_b_interrupted_negative(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [_censored_task_with_transitions("b")])

    result = score_mirror_loop(tmp_path)
    detail = result["details"][0]

    assert detail["verdict"] == CENSORED
    assert detail["verdict"] != NOT_COLLAPSED
    assert result["censored_count"] == 1
    assert result["n_loops"] == 0  # excluded from n_loops
    assert result["verdict_bearing_coverage"] < 1.0


# =====================================================================
# Scenario C -- complete negative
# =====================================================================

def test_scenario_c_complete_negative(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [_complete_non_collapsing_task("c")])

    result = score_mirror_loop(tmp_path)
    detail = result["details"][0]

    assert detail["verdict"] == NOT_COLLAPSED
    assert detail["prefix_complete"] is True
    assert result["not_collapsed_count"] == 1
    assert result["n_loops"] == 1  # verdict-bearing


# =====================================================================
# Scenario D -- causal break cannot be skipped
# =====================================================================

def test_scenario_d_causal_break_is_not_repaired_by_a_later_valid_response(tmp_path):
    """An invalid observation mid-chain, followed by an individually-valid
    later observation, must not be reconnected -- the verdict is based
    only on the longest unbroken valid prefix from step 0."""
    task = {
        "task_id": "d",
        "responses": [
            _obs("first response"),
            _obs("", "empty_text"),
            _obs("this later response is individually valid text"),
            _obs("fourth response"),
            _obs("fifth response"),
        ],
    }
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [task])

    result = score_mirror_loop(tmp_path)
    detail = result["details"][0]

    # Usable prefix stops at the break (index 1); the later valid
    # responses at indices 2-4 are never reconnected into it.
    assert detail["usable_prefix_length"] == 1
    assert detail["n_usable_transitions"] == 0
    assert detail["prefix_complete"] is False
    # No prior collapse was established (0 transitions), so this lands in
    # CENSORED, never NOT_COLLAPSED (which would wrongly imply the full
    # intended chain was validly observed).
    assert detail["verdict"] == CENSORED


# =====================================================================
# Scenario E -- denominator integrity (mixed batch, with numeric check)
# Also serves Scenario G (exactly the 10/20 eligibility boundary).
# =====================================================================

def _mixed_20_task_batch_at_exactly_10_verdict_bearing():
    """4 COLLAPSED + 6 NOT_COLLAPSED + 10 CENSORED = 20 planned,
    n_loops = 10 (exactly Sec 4.9's floor)."""
    tasks = []
    for i in range(4):
        tasks.append(_collapsing_task(f"collapsed_{i}"))
    for i in range(6):
        tasks.append(_complete_non_collapsing_task(f"notcollapsed_{i}"))
    for i in range(10):
        tasks.append(_censored_task_with_transitions(f"censored_{i}"))
    return tasks


def test_scenario_e_denominator_integrity_and_numeric_value(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", _mixed_20_task_batch_at_exactly_10_verdict_bearing())

    result = score_mirror_loop(tmp_path)

    assert result["planned_tasks"] == 20
    assert result["collapsed_count"] == 4
    assert result["not_collapsed_count"] == 6
    assert result["censored_count"] == 10
    # Required invariant (this phase's governing prompt Sec 6).
    assert result["planned_tasks"] == (
        result["collapsed_count"] + result["not_collapsed_count"] + result["censored_count"]
    )
    assert result["n_loops"] == result["collapsed_count"] + result["not_collapsed_count"]
    assert result["n_loops"] == 10
    assert result["verdict_bearing_coverage"] == pytest.approx(10 / 20)

    # Concrete numeric verification (this phase's governing prompt Sec 9):
    # collapse_rate = collapsed_count / n_loops = 4/10 = 0.4 exactly --
    # censored tasks contribute to neither the numerator nor the
    # denominator of this ratio.
    assert result["collapse_rate"] == pytest.approx(0.4)
    assert result["epb_phi"] == pytest.approx(100 * (1 - 0.4))
    assert result["epb_phi"] == 60.0


# =====================================================================
# Scenario F -- 9/20 gate
# =====================================================================

def _batch_with_n_verdict_bearing(n_collapsed, n_not_collapsed, n_censored):
    tasks = []
    for i in range(n_collapsed):
        tasks.append(_collapsing_task(f"collapsed_{i}"))
    for i in range(n_not_collapsed):
        tasks.append(_complete_non_collapsing_task(f"notcollapsed_{i}"))
    for i in range(n_censored):
        tasks.append(_censored_task_with_transitions(f"censored_{i}"))
    return tasks


def test_scenario_f_nine_of_twenty_is_insufficient_evidence(tmp_path):
    # 4 collapsed + 5 not_collapsed + 11 censored = 20 planned, n_loops = 9.
    _write_jsonl(tmp_path / "mirror_loop.jsonl", _batch_with_n_verdict_bearing(4, 5, 11))

    raw = score_mirror_loop(tmp_path)
    assert raw["planned_tasks"] == 20
    assert raw["n_loops"] == 9
    assert raw["verdict_bearing_eligible"] is False
    assert raw["epb_phi"] is None
    assert raw["collapse_rate"] is None
    assert raw["verdict_bearing_coverage"] == pytest.approx(9 / 20)

    result = score_mirror_loop_result(tmp_path)
    assert result.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert result.value is None
    # Narrow Representation-Seam Correction Pass Sec 2/3: planned/applicable/
    # usable are the frozen TRANSITION-level quantities (Sec 4.8), not task
    # counts -- 80 planned/applicable transitions, 43 usable (4*3 + 5*4 +
    # 11*1). The task-level eligibility quantity lives in `details` under
    # its own honest name, never renamed into these fields.
    assert result.planned == 80
    assert result.applicable == 80
    assert result.usable == 43
    assert result.coverage == pytest.approx(43 / 80)  # transition coverage, NOT eligibility coverage
    assert result.details["planned_tasks"] == 20
    assert result.details["n_loops"] == 9
    assert result.details["verdict_bearing_coverage"] == pytest.approx(9 / 20)
    # The two coverages are genuinely different numbers here -- proof this
    # is not a coincidental pass (see also test_scenario_i_...).
    assert result.coverage != result.details["verdict_bearing_coverage"]
    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.canonical_consumption_eligible is False


# =====================================================================
# Scenario G -- 10/20 gate
# =====================================================================

def test_scenario_g_ten_of_twenty_is_scored(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", _mixed_20_task_batch_at_exactly_10_verdict_bearing())

    raw = score_mirror_loop(tmp_path)
    assert raw["n_loops"] == 10
    assert raw["verdict_bearing_eligible"] is True
    assert raw["epb_phi"] is not None

    result = score_mirror_loop_result(tmp_path)
    assert result.measurement_state == MeasurementState.SCORED
    assert result.value is not None
    assert result.value == 60.0
    # Narrow Representation-Seam Correction Pass Sec 2/3: transition-level
    # fields (80 planned/applicable, 46 usable = 4*3 + 6*4 + 10*1), not
    # task counts. Eligibility coverage lives in `details`, separately.
    assert result.planned == 80
    assert result.applicable == 80
    assert result.usable == 46
    assert result.coverage == pytest.approx(46 / 80)  # transition coverage
    assert result.details["planned_tasks"] == 20
    assert result.details["n_loops"] == 10
    assert result.details["verdict_bearing_coverage"] == pytest.approx(10 / 20)
    assert result.coverage != result.details["verdict_bearing_coverage"]
    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.validation_status == MIRROR_LOOP_VALIDATION_STATUS
    # Never FROZEN under current Phase 2 evidence base (Sec 4.10).
    assert result.canonical_consumption_eligible is False


# =====================================================================
# Scenario H -- positive after later interruption, and denominator effect
# =====================================================================

def test_scenario_h_collapsed_then_broken_task_remains_verdict_bearing_and_changes_the_value(tmp_path):
    """Guards against implementing "complete task" as a proxy for
    "verdict-bearing task": a COLLAPSED task whose chain later breaks must
    count in n_loops/collapsed_count exactly like a COLLAPSED task whose
    chain stayed complete -- proven by comparing the two variants and
    checking they are numerically indistinguishable in the final value.
    """
    complete_variant = _mixed_20_task_batch_at_exactly_10_verdict_bearing()
    # Replace one collapsed task with a collapse-then-break variant.
    broken_variant = list(complete_variant)
    broken_variant[0] = _collapsing_task("collapsed_0", trailing_break=True)

    complete_dir = tmp_path / "complete_run"
    broken_dir = tmp_path / "broken_run"
    complete_dir.mkdir()
    broken_dir.mkdir()
    _write_jsonl(complete_dir / "mirror_loop.jsonl", complete_variant)
    _write_jsonl(broken_dir / "mirror_loop.jsonl", broken_variant)

    complete_result = score_mirror_loop(complete_dir)
    broken_result = score_mirror_loop(broken_dir)

    # The collapse-then-break task is still COLLAPSED, still verdict-bearing.
    broken_task_detail = next(d for d in broken_result["details"] if d["task_id"] == "collapsed_0")
    assert broken_task_detail["verdict"] == COLLAPSED
    assert broken_task_detail["prefix_complete"] is False

    # Identical counts and identical numeric value in both variants --
    # completeness of the chain after collapse has zero effect.
    assert broken_result["collapsed_count"] == complete_result["collapsed_count"] == 4
    assert broken_result["n_loops"] == complete_result["n_loops"] == 10
    assert broken_result["epb_phi"] == complete_result["epb_phi"] == 60.0


# =====================================================================
# Sec 17 -- additional required invariant tests
# =====================================================================

def test_partition_integrity_every_task_gets_exactly_one_verdict(tmp_path):
    tasks = _mixed_20_task_batch_at_exactly_10_verdict_bearing()
    _write_jsonl(tmp_path / "mirror_loop.jsonl", tasks)
    result = score_mirror_loop(tmp_path)

    verdicts = [d["verdict"] for d in result["details"]]
    assert len(verdicts) == len(tasks)
    assert set(verdicts) <= {COLLAPSED, NOT_COLLAPSED, CENSORED}
    task_ids = [d["task_id"] for d in result["details"]]
    assert len(task_ids) == len(set(task_ids))  # no duplicate/multi-verdict entries


def test_collapse_irrevocability_direct(tmp_path):
    """Once collapse fires in the valid prefix, later invalidity cannot
    change the verdict away from COLLAPSED."""
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [_collapsing_task("x", trailing_break=True)])
    result = score_mirror_loop(tmp_path)
    assert result["details"][0]["verdict"] == COLLAPSED


def test_negative_completeness_not_collapsed_implies_full_prefix(tmp_path):
    """NOT_COLLAPSED must imply all n_steps-1 intended transitions were
    usable -- never assigned from an incomplete prefix."""
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [_complete_non_collapsing_task("y")])
    result = score_mirror_loop(tmp_path)
    detail = result["details"][0]
    assert detail["verdict"] == NOT_COLLAPSED
    assert detail["prefix_complete"] is True
    assert detail["usable_prefix_length"] == 5


def test_censor_visibility_explicit_structured_field(tmp_path):
    """Every censored task is visible in explicit diagnostics, not merely
    implied by an aggregate count."""
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [
        _censored_task_with_transitions("c1"),
        _censored_task_no_transitions("c2"),
    ])
    result = score_mirror_loop(tmp_path)
    assert result["censored_count"] == 2
    censored_ids = {d["task_id"] for d in result["details"] if d["verdict"] == CENSORED}
    assert censored_ids == {"c1", "c2"}
    for d in result["details"]:
        assert "break_index" in d
        assert "break_reason" in d


def test_denominator_exclusion_censored_never_enters_n_loops(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [
        _censored_task_with_transitions("c1"),
        _censored_task_no_transitions("c2"),
    ])
    result = score_mirror_loop(tmp_path)
    assert result["n_loops"] == 0
    assert result["censored_count"] == 2


def test_coverage_derivation_equals_verdict_bearing_over_planned(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", _mixed_20_task_batch_at_exactly_10_verdict_bearing())
    result = score_mirror_loop(tmp_path)
    assert result["verdict_bearing_coverage"] == pytest.approx(
        result["n_loops"] / result["planned_tasks"]
    )


def test_threshold_boundary_both_sides(tmp_path):
    below_dir = tmp_path / "below"
    at_dir = tmp_path / "at"
    below_dir.mkdir()
    at_dir.mkdir()
    _write_jsonl(below_dir / "mirror_loop.jsonl", _batch_with_n_verdict_bearing(4, 5, 11))  # 9
    _write_jsonl(at_dir / "mirror_loop.jsonl", _mixed_20_task_batch_at_exactly_10_verdict_bearing())  # 10

    below = score_mirror_loop(below_dir)
    at = score_mirror_loop(at_dir)
    assert below["n_loops"] == MIRROR_LOOP_MIN_VERDICT_BEARING_TASKS - 1
    assert below["verdict_bearing_eligible"] is False
    assert at["n_loops"] == MIRROR_LOOP_MIN_VERDICT_BEARING_TASKS
    assert at["verdict_bearing_eligible"] is True


def test_value_state_invariant(tmp_path):
    scored_dir = tmp_path / "scored"
    insufficient_dir = tmp_path / "insufficient"
    scored_dir.mkdir()
    insufficient_dir.mkdir()
    _write_jsonl(scored_dir / "mirror_loop.jsonl", _mixed_20_task_batch_at_exactly_10_verdict_bearing())
    _write_jsonl(insufficient_dir / "mirror_loop.jsonl", _batch_with_n_verdict_bearing(4, 5, 11))

    scored = score_mirror_loop_result(scored_dir)
    insufficient = score_mirror_loop_result(insufficient_dir)

    assert scored.measurement_state == MeasurementState.SCORED
    assert scored.value is not None
    assert insufficient.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert insufficient.value is None


def test_validation_invariant_always_provisional_never_frozen(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", _mixed_20_task_batch_at_exactly_10_verdict_bearing())
    result = score_mirror_loop_result(tmp_path)
    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.validation_status != ValidationStatus.FROZEN


def test_canonical_invariant_always_false(tmp_path):
    _write_jsonl(tmp_path / "mirror_loop.jsonl", _mixed_20_task_batch_at_exactly_10_verdict_bearing())
    result = score_mirror_loop_result(tmp_path)
    assert result.canonical_consumption_eligible is False


def test_genuine_scoring_error_is_not_confused_with_insufficient_evidence(tmp_path):
    with open(tmp_path / "mirror_loop.jsonl", "w") as f:
        f.write("{not valid json at all\n")
    result = score_mirror_loop_result(tmp_path)
    assert result.measurement_state == MeasurementState.SCORING_ERROR
    assert result.measurement_state != MeasurementState.INSUFFICIENT_EVIDENCE
    assert result.value is None


def test_failed_task_record_is_censored_not_a_whole_battery_block(tmp_path):
    """A Phase 1 Area 3 orchestration-failure record (task_status ==
    "failed", no responses) is the k=0 edge case of the same frozen
    prefix rule -- CENSORED, not a whole-battery block."""
    _write_jsonl(tmp_path / "mirror_loop.jsonl", [
        {"task_id": "failed_1", "task_status": "failed",
         "failure": {"kind": "orchestration_error", "error_type": "RuntimeError", "error_message": "boom"}},
    ] + [_complete_non_collapsing_task(f"ok_{i}") for i in range(9)])

    result = score_mirror_loop(tmp_path)
    by_id = {d["task_id"]: d for d in result["details"]}
    assert by_id["failed_1"]["verdict"] == CENSORED
    assert by_id["failed_1"]["usable_prefix_length"] == 0
    assert result["planned_tasks"] == 10
    assert result["censored_count"] == 1
    assert result["not_collapsed_count"] == 9


# =====================================================================
# Scenario I -- dual-granularity non-coincidence (Narrow
# Representation-Seam Correction Pass Sec 18)
# =====================================================================

def _censored_task_long_prefix(task_id):
    """4 distinct, non-colliding valid responses then a break -- 3 usable
    transitions, no collapse (texts are all mutually dissimilar), and an
    incomplete prefix (k=4 != n_steps=5) -- CENSORED, but with a much
    longer usable prefix than _censored_task_with_transitions."""
    return {
        "task_id": task_id,
        "responses": [_obs(t) for t in _DISTINCT_TEXTS[:4]] + [_obs("", "empty_text")],
    }


def test_scenario_i_transition_coverage_and_verdict_bearing_coverage_are_not_coincidentally_equal(tmp_path):
    """5 COLLAPSED tasks (3 usable transitions each) + 15 CENSORED tasks
    with a long-but-incomplete prefix (3 usable transitions each, no
    collapse). Transition coverage and verdict-bearing coverage must come
    out to deliberately different, non-round numbers -- proving the two
    quantities are not accidentally identical and that each named field
    reports the correct one.
    """
    tasks = [_collapsing_task(f"collapsed_{i}") for i in range(5)]
    tasks += [_censored_task_long_prefix(f"censored_{i}") for i in range(15)]
    _write_jsonl(tmp_path / "mirror_loop.jsonl", tasks)

    raw = score_mirror_loop(tmp_path)
    assert raw["planned_tasks"] == 20
    assert raw["collapsed_count"] == 5
    assert raw["not_collapsed_count"] == 0
    assert raw["censored_count"] == 15
    assert raw["n_loops"] == 5

    # Transition-level: 5*3 (collapsed) + 15*3 (censored, long prefix) = 60
    # usable of 80 planned -- transition coverage = 0.75.
    assert raw["usable_transitions"] == 60
    assert raw["planned_transitions"] == 80
    transition_coverage = raw["usable_transitions"] / raw["planned_transitions"]
    assert transition_coverage == pytest.approx(0.75)

    # Task-level: verdict-bearing coverage = 5/20 = 0.25.
    assert raw["verdict_bearing_coverage"] == pytest.approx(0.25)

    # The two are genuinely, non-coincidentally different -- not both 0.5,
    # not off by a rounding artifact.
    assert transition_coverage != raw["verdict_bearing_coverage"]
    assert abs(transition_coverage - raw["verdict_bearing_coverage"]) == pytest.approx(0.5)

    # Each QuantityResult field reports the correct, distinct quantity.
    result = score_mirror_loop_result(tmp_path)
    assert result.coverage == pytest.approx(0.75)  # transition coverage
    assert result.details["verdict_bearing_coverage"] == pytest.approx(0.25)  # eligibility coverage
    assert result.coverage != result.details["verdict_bearing_coverage"]
    # 5 verdict-bearing tasks < the 10-task floor -- correctly ineligible,
    # using the task-level quantity, not the (much higher) transition one.
    assert result.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE


# =====================================================================
# Scenario J -- scientific insufficiency vs. genuine scorer failure
# (Narrow Representation-Seam Correction Pass Sec 6/7/8/18)
# =====================================================================

def test_scenario_j_insufficiency_and_scorer_failure_remain_categorically_distinct(tmp_path):
    run_a = tmp_path / "insufficient"
    run_b = tmp_path / "malformed"
    run_a.mkdir()
    run_b.mkdir()

    # A: scientifically insufficient but genuinely valid Mirror Loop evidence.
    _write_jsonl(run_a / "mirror_loop.jsonl", _batch_with_n_verdict_bearing(4, 5, 11))  # n_loops = 9
    # B: malformed Mirror Loop scorer input.
    with open(run_b / "mirror_loop.jsonl", "w") as f:
        f.write("{not valid json at all\n")

    result_a = score_mirror_loop_result(run_a)
    result_b = score_mirror_loop_result(run_b)

    assert result_a.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert result_a.measurement_state != MeasurementState.SCORING_ERROR
    assert result_a.error is None
    assert result_a.value is None

    assert result_b.measurement_state == MeasurementState.SCORING_ERROR
    assert result_b.measurement_state != MeasurementState.INSUFFICIENT_EVIDENCE
    assert result_b.error is not None
    assert result_b.value is None
