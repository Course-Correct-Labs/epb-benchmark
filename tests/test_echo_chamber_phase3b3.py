"""Tests for Phase 3B-3: Echo Chamber's frozen battery-specific evidence
semantics (EPB_PHASE2_EVIDENCE_SEMANTICS.md Sec 7.4-7.8).

This is the OLD empirical EPB `echo_chamber` battery (TF-IDF/cosine
seed-vs-final similarity). It is NOT "Echo Chamber Zero" (ECZ), a separate
theoretical CCL construct -- this file, like `echo_scoring.py` and
`result_adapter.py`, never opens, modifies, or cites ECZ as an
implementation basis for anything below.

Covers the required acceptance scenarios (A-W) and Sec 40 invariants,
exercising both the raw scorer (`epb.scoring.echo_scoring.score_echo_chamber`)
and the structured-result wrapper
(`epb.scoring.result_adapter.score_echo_chamber_result`).

Final Echo Chamber Freeze-Integrity Correction (this revision): Scenario Q
is replaced -- its prior contrast case (`score_echo_chamber(tmp_path,
n_rounds=1)`) locked in the exact defect this correction removes (a
caller-selectable round count that could change a persisted task's
evaluability). The canonical scorer and result wrapper now take no
`n_rounds` argument at all; Scenario W directly proves that immutability.
Scenarios S-V are new, covering the companion seed-integrity correction:
a missing/`None`/non-string/empty/whitespace-only `initial_text` must make
a task non-evaluable rather than silently reaching
`compute_tfidf_similarity` as `""`.

Granularity note (mirrors the Violation State test file's note): unlike
Mirror Loop, Echo Chamber has only ONE relevant granularity. Phase 2 Sec
7.4/7.6 fix the evidence unit at the task level (exactly one seed-vs-final
comparison per task, no round-level denominator), and Sec 7.7/7.8 define
`planned`/`applicable`/`usable` AND the eligibility gate all directly in
that same task unit. No dual-granularity test is constructed for that
reason.

All-or-nothing note (Sec 7.6, the key difference from Mirror Loop/Violation
State): a task's evidence is either fully evaluable (both endpoints
VALID_TEXT and the full intermediate chain VALID_TEXT) or contributes
nothing at all -- there is no partial-prefix salvage, so these tests never
assert a "usable prefix length" the way the Violation State tests do.
"""

import json

import pytest

from epb.adapters.base import ObservationKind
from epb.scoring.echo_scoring import (
    ECHO_CHAMBER_CANONICAL_N_ROUNDS,
    ECHO_CHAMBER_MIN_EVALUABLE_TASKS,
    ECHO_CHAMBER_PLANNED_TASKS_ANCHOR,
    _task_evaluability,
    score_echo_chamber,
)
from epb.scoring.metrics import compute_tfidf_similarity
from epb.scoring.result import MeasurementState, ValidationStatus
from epb.scoring.result_adapter import (
    ECHO_CHAMBER_VALIDATION_STATUS,
    score_echo_chamber_result,
)


def _write_jsonl(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _obs(text, kind="valid_text"):
    return {"text": text, "kind": kind}


def _clean_task(task_id, initial_text="Climate change is a serious problem.",
                 final_text="Climate issues are important.",
                 n_rounds=ECHO_CHAMBER_CANONICAL_N_ROUNDS):
    """A fully evaluable task: n_rounds-1 VALID_TEXT intermediates, VALID_TEXT final."""
    return {
        "task_id": task_id,
        "task_status": "completed",
        "initial_text": initial_text,
        "intermediate_texts": [_obs(f"intermediate round {i}") for i in range(n_rounds - 1)],
        "final_text": _obs(final_text),
    }


def _batch_of_clean_tasks(n_tasks, **kwargs):
    return [_clean_task(f"clean_{i}", **kwargs) for i in range(n_tasks)]


def _failed_task(task_id):
    return {"task_id": task_id, "task_status": "failed",
            "failure": {"kind": "orchestration_error", "error_type": "RuntimeError", "error_message": "boom"}}


# =====================================================================
# Scenario A -- complete valid chain
# =====================================================================

def test_scenario_a_complete_valid_chain(tmp_path):
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [
        _clean_task("a", initial_text="the quick brown fox", final_text="the quick brown fox")
    ])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["chain_complete"] is True
    assert detail["chain_valid"] is True
    assert detail["evaluable"] is True
    assert detail["break_index"] is None
    assert detail["break_reason"] is None
    assert detail["similarity"] == pytest.approx(1.0)
    assert detail["drift"] == pytest.approx(0.0)


# =====================================================================
# Scenario B -- early invalid intermediate
# =====================================================================

def test_scenario_b_early_invalid_intermediate(tmp_path):
    task = _clean_task("b")
    task["intermediate_texts"][0] = _obs("", "empty_text")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["chain_valid"] is False
    assert detail["evaluable"] is False
    assert detail["break_index"] == 0
    assert detail["break_reason"] == "empty_text"
    assert detail["similarity"] is None
    assert detail["drift"] is None


# =====================================================================
# Scenario C -- late invalid intermediate (final text individually clean)
# =====================================================================

def test_scenario_c_late_invalid_intermediate_no_suffix_reconnection(tmp_path):
    """The last intermediate round is broken, but final_text itself is
    individually VALID_TEXT -- Sec 7.5's full-chain rule means this must
    NOT be rescued into evaluable just because the endpoint looks clean."""
    task = _clean_task("c")
    task["intermediate_texts"][-1] = _obs("", "whitespace_only_text")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["chain_valid"] is False
    assert detail["evaluable"] is False
    assert detail["break_index"] == ECHO_CHAMBER_CANONICAL_N_ROUNDS - 2  # last intermediate index
    assert detail["break_reason"] == "whitespace_only_text"


# =====================================================================
# Scenario D -- invalid final text, all intermediates valid
# =====================================================================

def test_scenario_d_invalid_final_text_all_intermediates_valid(tmp_path):
    task = _clean_task("d")
    task["final_text"] = _obs("", "truncated")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["chain_valid"] is False
    assert detail["evaluable"] is False
    # break_index points at the final round's position (recorded_intermediate_count)
    assert detail["break_index"] == ECHO_CHAMBER_CANONICAL_N_ROUNDS - 1
    assert detail["break_reason"] == "truncated"


# =====================================================================
# Scenario E -- task failure record
# =====================================================================

def test_scenario_e_task_failure_record(tmp_path):
    """Final Failed-Task Diagnostic Referent Correction: this fixture (no
    initial_text key at all) is the "failed, seed absent" shape -- it must
    still report seed_present=False truthfully, derived from the same
    _seed_validity(task) source of truth as every other branch, not a
    hard-coded value. break_reason is "task_failed", never "missing_record"
    -- the JSONL record itself is genuinely present."""
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [_failed_task("e")])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["task_status"] == "failed"
    assert detail["seed_present"] is False
    assert detail["seed_valid"] is False
    assert detail["seed_issue"] == "missing_initial_text"
    assert detail["chain_complete"] is False
    assert detail["chain_valid"] is False
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "task_failed"
    assert detail["break_reason"] != "missing_record"
    assert detail["similarity"] is None
    assert detail["drift"] is None


# =====================================================================
# Scenario F -- representative non-VALID_TEXT kinds sweep
# =====================================================================

@pytest.mark.parametrize("kind", [
    "empty_text",
    "whitespace_only_text",
    "provider_refusal",
    "truncated",
    "non_text_terminal",
    "provider_error",
    "orchestration_error",
])
def test_scenario_f_non_valid_text_kinds_all_block_evaluability(tmp_path, kind):
    task = _clean_task("f")
    task["final_text"] = _obs("", kind)
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["evaluable"] is False
    assert detail["break_reason"] == kind


# =====================================================================
# Scenario G -- 4/10 boundary (insufficient evidence)
# =====================================================================

def test_scenario_g_four_of_ten_is_insufficient_evidence(tmp_path):
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(4))

    raw = score_echo_chamber(tmp_path)
    assert raw["usable_tasks"] == 4
    assert raw["evaluable_tasks_eligible"] is False
    assert raw["epb_drift"] is None
    assert raw["avg_drift"] is None
    assert raw["avg_similarity"] is None
    assert raw["planned_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert raw["applicable_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert raw["coverage"] == pytest.approx(4 / 10, abs=1e-4)

    result = score_echo_chamber_result(tmp_path)
    assert result.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert result.value is None
    assert result.planned == 10
    assert result.applicable == 10
    assert result.usable == 4
    assert result.coverage == pytest.approx(4 / 10)
    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.canonical_consumption_eligible is False


# =====================================================================
# Scenario H -- 5/10 boundary (scored)
# =====================================================================

def test_scenario_h_five_of_ten_is_scored(tmp_path):
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(5))

    raw = score_echo_chamber(tmp_path)
    assert raw["usable_tasks"] == 5
    assert raw["evaluable_tasks_eligible"] is True
    assert raw["epb_drift"] is not None

    result = score_echo_chamber_result(tmp_path)
    assert result.measurement_state == MeasurementState.SCORED
    assert result.value is not None
    assert result.planned == 10
    assert result.applicable == 10
    assert result.usable == 5
    assert result.coverage == pytest.approx(5 / 10)
    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.validation_status == ECHO_CHAMBER_VALIDATION_STATUS
    assert result.canonical_consumption_eligible is False


# =====================================================================
# Scenario I -- estimator arithmetic worked example (evaluable tasks only)
# =====================================================================

def test_scenario_i_estimator_arithmetic_worked_example(tmp_path):
    """5 evaluable tasks with distinct, known seed/final pairs, plus one
    unusable task whose (broken) evidence must not enter the estimator at
    all. Independently recompute the exact TF-IDF similarity/drift/
    epb_drift arithmetic from the same estimator function and confirm the
    scorer's aggregate matches exactly."""
    pairs = [
        ("the quick brown fox jumps", "the quick brown fox jumps"),
        ("the quick brown fox jumps", "a slow gray wolf sleeps"),
        ("data science is fascinating", "data science is interesting"),
        ("machine learning models learn", "machine learning models learn patterns"),
        ("the weather today is sunny", "the weather today is rainy"),
    ]
    tasks = [
        _clean_task(f"i_{i}", initial_text=seed, final_text=final)
        for i, (seed, final) in enumerate(pairs)
    ]
    unusable = _clean_task("i_unusable")
    unusable["intermediate_texts"][0] = _obs("", "empty_text")
    tasks.append(unusable)
    _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks)

    raw = score_echo_chamber(tmp_path)
    assert raw["usable_tasks"] == 5

    expected_similarities = [compute_tfidf_similarity(s, f) for s, f in pairs]
    expected_drifts = [1.0 - s for s in expected_similarities]
    expected_avg_drift = sum(expected_drifts) / 5
    expected_avg_similarity = sum(expected_similarities) / 5
    expected_epb_drift = round(100 * (1 - expected_avg_drift), 2)

    assert raw["avg_drift"] == pytest.approx(round(expected_avg_drift, 4))
    assert raw["avg_similarity"] == pytest.approx(round(expected_avg_similarity, 4))
    assert raw["epb_drift"] == pytest.approx(expected_epb_drift)


# =====================================================================
# Scenario J -- insufficiency vs scoring error remain categorically distinct
# =====================================================================

def test_scenario_j_insufficiency_and_scorer_failure_remain_categorically_distinct(tmp_path):
    run_a = tmp_path / "insufficient"
    run_b = tmp_path / "malformed"
    run_a.mkdir()
    run_b.mkdir()

    _write_jsonl(run_a / "echo_chamber.jsonl", _batch_of_clean_tasks(4))  # below floor
    with open(run_b / "echo_chamber.jsonl", "w") as f:
        f.write("{not valid json at all\n")

    result_a = score_echo_chamber_result(run_a)
    result_b = score_echo_chamber_result(run_b)

    assert result_a.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert result_a.error is None
    assert result_a.value is None

    assert result_b.measurement_state == MeasurementState.SCORING_ERROR
    assert result_b.error is not None
    assert result_b.value is None


# =====================================================================
# Scenario K -- recorded_tasks < 10 but planned/applicable stay 10
# =====================================================================

def test_scenario_k_applicable_does_not_collapse_to_recorded_count(tmp_path):
    """5 tasks present and evaluable; the rest of the canonical battery's
    tasks are missing entirely (task_status == "failed"). `applicable`
    must remain the frozen anchor (10), never shrinking to the 5 actually
    recorded."""
    tasks = _batch_of_clean_tasks(5) + [_failed_task(f"missing_{i}") for i in range(5)]
    _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks)

    raw = score_echo_chamber(tmp_path)
    assert raw["recorded_tasks"] == 10
    assert raw["applicable_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert raw["planned_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert raw["usable_tasks"] == 5

    # A separate case: recorded_tasks itself below 10 (some tasks never
    # even have a record in this run's file at all).
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(5))
    raw2 = score_echo_chamber(tmp_path)
    assert raw2["recorded_tasks"] == 5
    assert raw2["applicable_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert raw2["applicable_tasks"] != raw2["recorded_tasks"]

    result = score_echo_chamber_result(tmp_path)
    assert result.applicable == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert result.applicable != raw2["recorded_tasks"]


# =====================================================================
# Scenario L -- truncated chain: too few intermediate entries
# =====================================================================

def test_scenario_l_truncated_chain_missing_required_round(tmp_path):
    task = _clean_task("l")
    task["intermediate_texts"] = task["intermediate_texts"][:-1]  # drop one required round
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["expected_generated_count"] == ECHO_CHAMBER_CANONICAL_N_ROUNDS
    assert detail["recorded_intermediate_count"] == ECHO_CHAMBER_CANONICAL_N_ROUNDS - 2
    assert detail["chain_complete"] is False
    assert detail["chain_valid"] is False
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "intermediate_count_mismatch"


# =====================================================================
# Scenario M -- too many intermediate entries
# =====================================================================

def test_scenario_m_excess_intermediate_entries_also_a_cardinality_mismatch(tmp_path):
    task = _clean_task("m")
    task["intermediate_texts"].append(_obs("an extra, unexpected round"))
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["recorded_intermediate_count"] == ECHO_CHAMBER_CANONICAL_N_ROUNDS
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "intermediate_count_mismatch"


# =====================================================================
# Scenario N -- same endpoints, valid vs broken intermediate comparison
# =====================================================================

def test_scenario_n_same_endpoints_valid_vs_broken_intermediate(tmp_path):
    """Two tasks share byte-identical initial_text/final_text -- only their
    intermediate chains differ (one fully valid, one broken mid-chain).
    Proves the full-chain check is genuinely load-bearing beyond the
    endpoint comparison alone: an identical endpoint pair produces
    evaluable=True for one and evaluable=False for the other."""
    seed, final = "the same seed text", "the same seed text, slightly drifted"
    clean = _clean_task("n_clean", initial_text=seed, final_text=final)
    broken = _clean_task("n_broken", initial_text=seed, final_text=final)
    broken["intermediate_texts"][1] = _obs("", "provider_refusal")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [clean, broken])

    result = score_echo_chamber(tmp_path)
    by_id = {d["task_id"]: d for d in result["details"]}

    assert by_id["n_clean"]["evaluable"] is True
    assert by_id["n_clean"]["similarity"] is not None
    assert by_id["n_broken"]["evaluable"] is False
    assert by_id["n_broken"]["similarity"] is None


# =====================================================================
# Scenario O -- legacy bare-string final_text is LEGACY_UNKNOWN, not VALID_TEXT
# =====================================================================

def test_scenario_o_legacy_bare_string_final_text_blocks_not_scores_as_valid_text(tmp_path):
    task = _clean_task("o")
    task["final_text"] = "a clean-looking pre-Phase-1 bare string"
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["evaluable"] is False
    assert detail["break_reason"] == ObservationKind.LEGACY_UNKNOWN.value


def test_scenario_o_legacy_bare_string_intermediate_also_blocks(tmp_path):
    task = _clean_task("o2")
    task["intermediate_texts"][0] = "a clean-looking pre-Phase-1 bare string"
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["evaluable"] is False
    assert detail["break_reason"] == ObservationKind.LEGACY_UNKNOWN.value


# =====================================================================
# Scenario P -- missing intermediate_texts field entirely
# =====================================================================

def test_scenario_p_missing_intermediate_texts_field(tmp_path):
    task = {
        "task_id": "p",
        "task_status": "completed",
        "initial_text": "seed",
        "final_text": _obs("final"),
        # intermediate_texts key entirely absent
    }
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["recorded_intermediate_count"] is None
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "missing_intermediate_texts_field"


# =====================================================================
# Scenario Q -- empty intermediate list: vacuous-truth trap vs genuine
# zero-round chain
# =====================================================================

def test_scenario_q_empty_intermediate_list_under_default_n_rounds_is_a_mismatch(tmp_path):
    """The highest-risk seam this phase's governing prompt calls out: an
    empty (but present) intermediate_texts list must NOT vacuously pass
    `all([]) == True` under the canonical n_rounds=5 expectation -- it is
    a cardinality mismatch (4 expected, 0 recorded), not a valid chain."""
    task = {
        "task_id": "q",
        "task_status": "completed",
        "initial_text": "seed",
        "intermediate_texts": [],
        "final_text": _obs("final"),
    }
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["recorded_intermediate_count"] == 0
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "intermediate_count_mismatch"


def test_scenario_q_same_record_cannot_change_evaluability_via_round_count(tmp_path):
    """Final Echo Chamber Freeze-Integrity Correction, Correction A: the
    prior contrast case here called `score_echo_chamber(tmp_path,
    n_rounds=1)` to prove an empty intermediate list becomes valid under a
    different round count -- that was exactly the defect this correction
    removes (a caller-selectable round count that changes the same
    persisted task's evaluability). The canonical scorer now exposes no
    such argument at all, so this same empty-intermediate-list record is
    evaluated under the fixed five-round construct every time, regardless
    of caller.

    The private, underscore-prefixed `_task_evaluability` helper still
    accepts an explicit `n_rounds` -- proving its cardinality-check
    *mechanism* correctly treats an empty list as valid when the expected
    count really is 0 is a legitimate isolated unit test of that
    mechanism, but it is never reachable through the public
    `score_echo_chamber`/`score_echo_chamber_result` API (Scenario W)."""
    task = {
        "task_id": "q2",
        "task_status": "completed",
        "initial_text": "seed",
        "intermediate_texts": [],
        "final_text": _obs("final"),
    }

    # The private helper's mechanism, tested in isolation: an expected
    # count of 0 (n_rounds=1) genuinely is satisfied by an empty list.
    isolated = _task_evaluability("q2", task, n_rounds=1)
    assert isolated["recorded_intermediate_count"] == 0
    assert isolated["chain_complete"] is True
    assert isolated["evaluable"] is True

    # The public, canonical scorer -- the only path an ordinary caller can
    # reach -- always uses the fixed five-round construct, so the exact
    # same record is a cardinality mismatch there, with no way for a
    # caller to select the n_rounds=1 interpretation instead.
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])
    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]
    assert detail["recorded_intermediate_count"] == 0
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "intermediate_count_mismatch"


# =====================================================================
# Scenario R -- final/intermediate alias/cardinality integrity (no
# double-count of the final observation)
# =====================================================================

def test_scenario_r_final_text_never_double_counted_as_an_intermediate(tmp_path):
    """If final_text's own observation were accidentally also present in
    intermediate_texts (an aliasing bug), the recorded_intermediate_count
    would be one too many and correctly rejected as a mismatch -- proving
    the scorer does not silently tolerate that shape either."""
    task = _clean_task("r")
    task["intermediate_texts"].append(dict(task["final_text"]))  # simulate aliasing
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["recorded_intermediate_count"] == ECHO_CHAMBER_CANONICAL_N_ROUNDS
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "intermediate_count_mismatch"


# =====================================================================
# Sec 40 -- additional required invariant tests
# =====================================================================

def test_evidence_unit_integrity_fields_are_tasks_not_rounds(tmp_path):
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(5))
    raw = score_echo_chamber(tmp_path)
    assert raw["n_sequences"] == 5  # 5 tasks, a legacy-shape alias for recorded_tasks
    assert raw["planned_tasks"] == 10  # NOT round-derived
    assert raw["usable_tasks"] == 5  # coincidence of this fixture, not the unit


def test_planned_applicable_ten_invariant_across_shapes(tmp_path):
    for tasks in (
        _batch_of_clean_tasks(5),
        _batch_of_clean_tasks(2) + [_failed_task("f1"), _failed_task("f2")],
        [_clean_task("solo")],
    ):
        _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks)
        raw = score_echo_chamber(tmp_path)
        assert raw["planned_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
        assert raw["applicable_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR


def test_frozen_denominator_is_not_a_runtime_override(tmp_path):
    """The canonical scorer must not accept a runtime planned/applicable
    denominator override -- 10 is a real invariant of the function, not a
    caller-configurable default. Final Echo Chamber Freeze-Integrity
    Correction: `n_rounds` is likewise no longer an ordinary parameter --
    the canonical scorer takes only `run_dir` (Scenario W has the full
    signature-immutability proof for both the scorer and the result
    wrapper)."""
    import inspect

    sig = inspect.signature(score_echo_chamber)
    assert "planned_tasks" not in sig.parameters
    assert "applicable_tasks" not in sig.parameters
    assert "n_rounds" not in sig.parameters
    assert set(sig.parameters.keys()) == {"run_dir"}

    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(3))
    result = score_echo_chamber(tmp_path)
    assert result["planned_tasks"] == 10
    assert result["applicable_tasks"] == 10


def test_usable_equals_evaluable_only(tmp_path):
    tasks = _batch_of_clean_tasks(3)
    broken = _clean_task("broken")
    broken["intermediate_texts"][0] = _obs("", "empty_text")
    tasks.append(broken)
    _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks)

    raw = score_echo_chamber(tmp_path)
    assert raw["usable_tasks"] == 3
    assert sum(1 for d in raw["details"] if d["evaluable"]) == raw["usable_tasks"]


def test_no_partial_task_value_all_or_nothing(tmp_path):
    """Sec 7.6: there is no partial-evidence state within a task -- a
    non-evaluable task's detail record never carries a similarity/drift
    value, even though its intermediate chain has a genuinely valid
    prefix before the break."""
    task = _clean_task("partial")
    task["intermediate_texts"][-1] = _obs("", "empty_text")  # break at the very end
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]
    assert detail["evaluable"] is False
    assert detail["similarity"] is None
    assert detail["drift"] is None


def test_value_state_invariant(tmp_path):
    scored_dir = tmp_path / "scored"
    insufficient_dir = tmp_path / "insufficient"
    scored_dir.mkdir()
    insufficient_dir.mkdir()
    _write_jsonl(scored_dir / "echo_chamber.jsonl", _batch_of_clean_tasks(5))
    _write_jsonl(insufficient_dir / "echo_chamber.jsonl", _batch_of_clean_tasks(4))

    scored = score_echo_chamber_result(scored_dir)
    insufficient = score_echo_chamber_result(insufficient_dir)

    assert scored.measurement_state == MeasurementState.SCORED
    assert scored.value is not None
    assert insufficient.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert insufficient.value is None


def test_threshold_boundary_both_sides(tmp_path):
    below_dir = tmp_path / "below"
    at_dir = tmp_path / "at"
    below_dir.mkdir()
    at_dir.mkdir()
    _write_jsonl(below_dir / "echo_chamber.jsonl", _batch_of_clean_tasks(4))
    _write_jsonl(at_dir / "echo_chamber.jsonl", _batch_of_clean_tasks(5))

    below = score_echo_chamber(below_dir)
    at = score_echo_chamber(at_dir)
    assert below["usable_tasks"] == ECHO_CHAMBER_MIN_EVALUABLE_TASKS - 1
    assert below["evaluable_tasks_eligible"] is False
    assert at["usable_tasks"] == ECHO_CHAMBER_MIN_EVALUABLE_TASKS
    assert at["evaluable_tasks_eligible"] is True


def test_validation_invariant_always_provisional_never_frozen(tmp_path):
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(5))
    result = score_echo_chamber_result(tmp_path)
    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.validation_status != ValidationStatus.FROZEN


def test_canonical_invariant_always_false(tmp_path):
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(5))
    result = score_echo_chamber_result(tmp_path)
    assert result.canonical_consumption_eligible is False


def test_sec_7_9_canonical_inclusion_status_not_encoded_anywhere(tmp_path):
    """Sec 7.9's battery-level canonical-inclusion status is UNRESOLVED and
    must not be merged into validation_status, canonical_consumption_eligible,
    or any per-run field -- both scored and insufficient-evidence runs must
    look identical along that axis regardless of Sec 7.9's separate,
    unresolved status."""
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(5))
    result = score_echo_chamber_result(tmp_path)
    result_dict = result.__dict__
    assert "canonical_inclusion" not in result_dict
    assert "experimental" not in {str(k).lower() for k in result_dict}
    assert result.validation_status == ValidationStatus.PROVISIONAL


def test_unusable_tasks_excluded_from_estimator_does_not_change_aggregate(tmp_path):
    tasks = _batch_of_clean_tasks(5)
    _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks)
    without_extra = score_echo_chamber(tmp_path)

    broken = _clean_task("extra_broken")
    broken["final_text"] = _obs("", "provider_refusal")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks + [broken])
    with_extra = score_echo_chamber(tmp_path)

    assert with_extra["usable_tasks"] == without_extra["usable_tasks"] == 5
    assert with_extra["epb_drift"] == pytest.approx(without_extra["epb_drift"])
    assert with_extra["avg_drift"] == pytest.approx(without_extra["avg_drift"])


def test_no_load_bearing_default_for_task_status_missing_key(tmp_path):
    """A completed-shaped record with no task_status key at all defaults to
    "completed" (Sec 7.3's implicit pre-Phase-1 default) -- this default is
    diagnostic-only, not scientifically load-bearing, because evaluability
    is still gated entirely by the full-chain observation check below it."""
    task = _clean_task("no_status")
    del task["task_status"]
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]
    assert detail["task_status"] == "completed"
    assert detail["evaluable"] is True


def test_no_ecz_conflation_documented(tmp_path):
    """Direct proof the module documents the ECZ/empirical-Echo-Chamber
    separation this phase requires, rather than merely asserting it in
    conversation -- a regression lock on the module docstring."""
    import epb.scoring.echo_scoring as echo_scoring_module

    doc = echo_scoring_module.__doc__
    assert "Echo Chamber Zero" in doc
    assert "ECZ" in doc
    assert "does not open, modify, or cite ECZ" in doc


def test_recorded_tasks_never_substituted_for_applicable_in_result_wrapper(tmp_path):
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(5))
    result = score_echo_chamber_result(tmp_path)
    raw = score_echo_chamber(tmp_path)
    assert result.applicable == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert result.applicable != raw["recorded_tasks"] or raw["recorded_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert raw["recorded_tasks"] == 5
    assert result.applicable == 10


# =====================================================================
# Final Echo Chamber Freeze-Integrity Correction -- Scenarios S-W
# =====================================================================

def _clean_task_missing_seed(task_id):
    """A structurally perfect chain (all intermediates + final VALID_TEXT)
    but with the initial_text key entirely absent -- isolates the seed
    defect from every chain-related concern already covered by A-R."""
    task = _clean_task(task_id)
    del task["initial_text"]
    return task


def test_scenario_s_missing_seed_otherwise_perfect_chain(tmp_path):
    """Correction B: chain observations are all individually valid, but
    the task-authored comparison seed was never persisted -- the
    scientific comparison (seed vs. final) cannot be established at all,
    so the task must not be evaluable despite a flawless generated chain."""
    task = _clean_task_missing_seed("s")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["chain_valid"] is True  # the generated chain itself is fine
    assert detail["seed_present"] is False
    assert detail["seed_valid"] is False
    assert detail["seed_issue"] == "missing_initial_text"
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "missing_initial_text"
    assert detail["similarity"] is None
    assert detail["drift"] is None
    assert result["usable_tasks"] == 0


def test_scenario_t_missing_seed_cannot_cross_five_of_ten(tmp_path):
    """4 fully legitimate evaluable tasks, plus one otherwise-perfect task
    with a missing seed -- exact 4/10 arithmetic, INSUFFICIENT_EVIDENCE.
    Under the pre-correction behavior, the missing-seed task's `""` seed
    would have reached compute_tfidf_similarity and become a 5th usable
    task, wrongly crossing the publication floor."""
    tasks = _batch_of_clean_tasks(4) + [_clean_task_missing_seed("t_missing")]
    _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks)

    raw = score_echo_chamber(tmp_path)
    assert raw["recorded_tasks"] == 5
    assert raw["usable_tasks"] == 4
    assert raw["applicable_tasks"] == ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    assert raw["coverage"] == pytest.approx(4 / 10, abs=1e-4)
    assert raw["evaluable_tasks_eligible"] is False
    assert raw["epb_drift"] is None

    result = score_echo_chamber_result(tmp_path)
    assert result.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert result.value is None
    assert result.usable == 4
    assert result.applicable == 10


def test_scenario_u_missing_seed_cannot_alter_estimator(tmp_path):
    """5 legitimate evaluable tasks, plus one otherwise-perfect
    missing-seed task -- usable count and every estimator output must be
    byte-identical with and without the extra task."""
    tasks = _batch_of_clean_tasks(5)
    _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks)
    without_extra = score_echo_chamber(tmp_path)

    _write_jsonl(tmp_path / "echo_chamber.jsonl", tasks + [_clean_task_missing_seed("u_missing")])
    with_extra = score_echo_chamber(tmp_path)

    assert with_extra["usable_tasks"] == without_extra["usable_tasks"] == 5
    assert with_extra["epb_drift"] == pytest.approx(without_extra["epb_drift"])
    assert with_extra["avg_drift"] == pytest.approx(without_extra["avg_drift"])
    assert with_extra["avg_similarity"] == pytest.approx(without_extra["avg_similarity"])


@pytest.mark.parametrize("mutate,expected_issue,expected_present", [
    (lambda t: t.__setitem__("initial_text", None), "null_initial_text", True),
    (lambda t: t.__setitem__("initial_text", 42), "non_string_initial_text", True),
    (lambda t: t.__setitem__("initial_text", ["not", "a", "string"]), "non_string_initial_text", True),
    (lambda t: t.__setitem__("initial_text", ""), "empty_initial_text", True),
    (lambda t: t.__setitem__("initial_text", "   \t\n  "), "empty_initial_text", True),
])
def test_scenario_v_malformed_seed_shapes_all_block_evaluability(tmp_path, mutate, expected_issue, expected_present):
    """Correction B: canonical spec/echo_chamber_v1.jsonl inspection found
    all 10 tasks have a non-empty, non-whitespace string seed -- no
    canonical evidence supports treating any of these malformed shapes as
    a legitimate value, so the narrowest structural rule (non-evaluable)
    applies uniformly to all of them, each with a distinct diagnostic
    `seed_issue` (never an `ObservationKind` value -- the seed is not a
    model observation, Sec 7.3). Final Seed-Presence Diagnostic
    Correction: every one of these mutated shapes leaves the
    `initial_text` key structurally present in the record, so
    `seed_present` is True for all of them -- only a genuinely absent key
    (Scenario V's companion presence test) is `seed_present=False`."""
    task = _clean_task("v")
    mutate(task)
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["seed_present"] is expected_present
    assert detail["seed_valid"] is False
    assert detail["seed_issue"] == expected_issue
    assert detail["evaluable"] is False
    assert detail["break_reason"] == expected_issue
    assert detail["similarity"] is None
    assert detail["drift"] is None
    # Never conflated with the model-observation taxonomy.
    assert expected_issue not in {k.value for k in ObservationKind}


def test_scenario_v_missing_seed_key_distinct_from_present_none(tmp_path):
    """Final Seed-Presence Diagnostic Correction: `seed_present` answers a
    purely structural question -- was the `initial_text` key present in
    the persisted record at all -- and must NOT be conflated with
    `seed_valid`. A genuinely absent key is `seed_present=False`; a key
    present with an explicit `None` value IS structurally present
    (`seed_present=True`), even though `None` is not a usable seed
    (`seed_valid=False`). Both remain scientifically non-evaluable, but
    the diagnostic must not collapse the two distinct provenance shapes
    into the same `seed_present` reading. This test fails under the
    pre-correction implementation, which returned `seed_present=False`
    for both shapes."""
    absent = _clean_task_missing_seed("v_absent")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [absent])
    result_absent = score_echo_chamber(tmp_path)
    detail_absent = result_absent["details"][0]
    assert detail_absent["seed_present"] is False
    assert detail_absent["seed_valid"] is False
    assert detail_absent["seed_issue"] == "missing_initial_text"

    present_none = _clean_task("v_none")
    present_none["initial_text"] = None
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [present_none])
    result_none = score_echo_chamber(tmp_path)
    detail_none = result_none["details"][0]
    assert detail_none["seed_present"] is True  # the key WAS structurally present
    assert detail_none["seed_valid"] is False   # but None is not a usable seed
    assert detail_none["seed_issue"] == "null_initial_text"

    # Both are still scientifically non-evaluable -- this correction
    # changes only diagnostic truthfulness, never evaluability.
    assert detail_absent["evaluable"] is False
    assert detail_none["evaluable"] is False


def test_seed_presence_validity_matrix(tmp_path):
    """Direct proof of the full presence/validity matrix (Final
    Seed-Presence Diagnostic Correction Sec 6): seed_present tracks
    structural key presence only; seed_valid tracks scientific usability;
    they diverge exactly once, for the explicit-None case."""
    cases = [
        ("absent", lambda: _clean_task_missing_seed("matrix_absent"), False, False),
        ("none", lambda: {**_clean_task("matrix_none"), "initial_text": None}, True, False),
        ("int", lambda: {**_clean_task("matrix_int"), "initial_text": 7}, True, False),
        ("empty", lambda: {**_clean_task("matrix_empty"), "initial_text": ""}, True, False),
        ("whitespace", lambda: {**_clean_task("matrix_ws"), "initial_text": "  \n "}, True, False),
        ("valid", lambda: _clean_task("matrix_valid"), True, True),
    ]
    for label, build, expected_present, expected_valid in cases:
        _write_jsonl(tmp_path / "echo_chamber.jsonl", [build()])
        detail = score_echo_chamber(tmp_path)["details"][0]
        assert detail["seed_present"] is expected_present, f"{label}: seed_present"
        assert detail["seed_valid"] is expected_valid, f"{label}: seed_valid"


# =====================================================================
# Final Failed-Task Diagnostic Referent Correction
# =====================================================================

def _failed_task_with_seed(task_id, seed="seed"):
    """The actual historical run_battery.py shape: run_echo_chamber_battery's
    exception handler persists `initial_text: seed_text` in its
    `extra` dict (the seed was read before the try block that could fail),
    so a real failed Echo Chamber record always has this key present."""
    return {
        "task_id": task_id,
        "task_status": "failed",
        "initial_text": seed,
        "failure": {"kind": "orchestration_error", "error_type": "RuntimeError", "error_message": "boom"},
    }


def test_scenario_e_failed_task_with_valid_persisted_seed(tmp_path):
    """Final Failed-Task Diagnostic Referent Correction, Sec 3: a failed
    record whose initial_text key IS present and holds a genuinely valid
    seed (the real, historically-observed run_battery.py shape) must
    report seed_present=True, seed_valid=True -- the prior hard-coded
    seed_present=False was a false provenance diagnostic for this exact
    shape. The valid seed does NOT rescue the task: it remains
    unconditionally non-evaluable because the generated chain itself
    never completed."""
    task = _failed_task_with_seed("failed_with_seed")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["seed_present"] is True
    assert detail["seed_valid"] is True
    assert detail["seed_issue"] is None
    assert detail["chain_complete"] is False
    assert detail["chain_valid"] is False
    assert detail["evaluable"] is False
    assert detail["break_reason"] == "task_failed"
    assert detail["similarity"] is None
    assert detail["drift"] is None
    assert result["usable_tasks"] == 0


def test_scenario_e_failed_task_without_seed(tmp_path):
    """Companion fixture, Sec 4: a failed record with NO initial_text key
    at all must still report seed_present=False, seed_valid=False --
    proving the corrected branch genuinely reads the record rather than
    unconditionally flipping seed_present to True for every failure."""
    task = _failed_task("failed_without_seed")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["seed_present"] is False
    assert detail["seed_valid"] is False
    assert detail["seed_issue"] == "missing_initial_text"
    assert detail["chain_complete"] is False
    assert detail["chain_valid"] is False
    assert detail["evaluable"] is False


def test_scenario_e_failed_task_with_none_seed(tmp_path):
    """Sec 5: a failed record with initial_text explicitly None must
    apply the full presence-validity matrix exactly as any other branch
    does -- seed_present=True (the key IS present), seed_valid=False (a
    None value is not usable), seed_issue="null_initial_text"."""
    task = _failed_task_with_seed("failed_none_seed", seed=None)
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    result = score_echo_chamber(tmp_path)
    detail = result["details"][0]

    assert detail["seed_present"] is True
    assert detail["seed_valid"] is False
    assert detail["seed_issue"] == "null_initial_text"
    assert detail["evaluable"] is False


def test_universal_seed_diagnostic_invariant_across_task_status(tmp_path):
    """Direct proof of the required universal invariant (Sec 9): for
    every task record, regardless of task_status, seed_present/seed_valid/
    seed_issue are derived from the identical _seed_validity(task)
    semantics whenever a persisted record exists. task_status must not
    silently redefine what seed_present means."""
    cases = [
        ("completed_absent", _clean_task_missing_seed("cu_a"), False, False),
        ("completed_none", {**_clean_task("cu_n"), "initial_text": None}, True, False),
        ("completed_valid", _clean_task("cu_v"), True, True),
        ("failed_absent", _failed_task("fu_a"), False, False),
        ("failed_none", _failed_task_with_seed("fu_n", seed=None), True, False),
        ("failed_valid", _failed_task_with_seed("fu_v"), True, True),
    ]
    for label, task, expected_present, expected_valid in cases:
        _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])
        detail = score_echo_chamber(tmp_path)["details"][0]
        assert detail["seed_present"] is expected_present, f"{label}: seed_present"
        assert detail["seed_valid"] is expected_valid, f"{label}: seed_valid"
        # Regardless of seed state, every failed task remains non-evaluable.
        if task.get("task_status") == "failed":
            assert detail["evaluable"] is False, f"{label}: must remain non-evaluable"


def test_failed_record_break_reason_never_missing_record(tmp_path):
    """Sec 10: a persisted failed record (with or without a seed) must
    never report break_reason == "missing_record" -- that label is
    reserved (were it ever needed) for a genuinely absent record, a
    condition this module does not currently produce at all, since every
    line in echo_chamber.jsonl is by definition a present JSONL record."""
    for task in (
        _failed_task("br_no_seed"),
        _failed_task_with_seed("br_with_seed"),
        _failed_task_with_seed("br_none_seed", seed=None),
    ):
        _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])
        detail = score_echo_chamber(tmp_path)["details"][0]
        assert detail["break_reason"] == "task_failed"
        assert detail["break_reason"] != "missing_record"


def test_scenario_v_seed_defect_never_classified_with_observation_kind(tmp_path):
    """Direct proof that seed-validity diagnostics are structurally
    distinct from the model-observation taxonomy -- Sec 7.3: initial_text
    is task-authored, never a model observation, so it must never be
    classified with ObservationKind."""
    task = _clean_task("v_kind")
    task["initial_text"] = ""
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])
    detail = score_echo_chamber(tmp_path)["details"][0]
    valid_observation_kind_values = {k.value for k in ObservationKind}
    assert detail["break_reason"] not in valid_observation_kind_values


def test_seed_and_chain_conditions_compose_with_and_not_or(tmp_path):
    """Direct proof of the required composition (governing prompt Sec 15):
    a task with BOTH an invalid seed AND an invalid chain is non-evaluable
    (obviously), AND a task with a valid seed but invalid chain remains
    non-evaluable (already proven by B-D), AND a task with an invalid seed
    but a perfectly valid chain is ALSO non-evaluable (Scenario S) --
    neither branch alone is sufficient; only valid-seed AND valid-chain
    together produce evaluable=True (Scenario A)."""
    both_broken = _clean_task_missing_seed("both_broken")
    both_broken["intermediate_texts"][0] = _obs("", "empty_text")
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [both_broken])
    detail = score_echo_chamber(tmp_path)["details"][0]
    assert detail["evaluable"] is False
    assert detail["seed_valid"] is False
    assert detail["chain_valid"] is False


def test_scenario_w_canonical_api_exposes_no_round_count_override(tmp_path):
    """Correction A, the completion-criteria proof: neither the canonical
    scorer nor the canonical result wrapper accepts an n_rounds argument,
    so no caller can assign a different evaluability state to the same
    persisted task by choosing a different round count -- the prior
    Scenario Q defect is now structurally impossible, not merely
    untested."""
    import inspect

    scorer_sig = inspect.signature(score_echo_chamber)
    result_sig = inspect.signature(score_echo_chamber_result)

    assert "n_rounds" not in scorer_sig.parameters
    assert "n_rounds" not in result_sig.parameters
    assert set(scorer_sig.parameters.keys()) == {"run_dir"}
    assert set(result_sig.parameters.keys()) == {"run_dir"}

    # Direct behavioral confirmation: calling either canonical function
    # with an n_rounds keyword argument is a TypeError, not a silently
    # accepted override.
    _write_jsonl(tmp_path / "echo_chamber.jsonl", _batch_of_clean_tasks(5))
    with pytest.raises(TypeError):
        score_echo_chamber(tmp_path, n_rounds=1)
    with pytest.raises(TypeError):
        score_echo_chamber_result(tmp_path, n_rounds=1)


def test_scenario_w_same_persisted_task_same_evaluability_regardless_of_caller(tmp_path):
    """The scientific consequence of Scenario W's signature proof: since
    there is no parameter left to vary, two independent calls against the
    same persisted record necessarily agree -- there is no longer any
    caller-facing axis that could make them disagree."""
    task = {
        "task_id": "w",
        "task_status": "completed",
        "initial_text": "seed",
        "intermediate_texts": [],
        "final_text": _obs("final"),
    }
    _write_jsonl(tmp_path / "echo_chamber.jsonl", [task])

    first = score_echo_chamber(tmp_path)["details"][0]
    second = score_echo_chamber(tmp_path)["details"][0]
    assert first["evaluable"] == second["evaluable"] is False
    assert first["break_reason"] == second["break_reason"] == "intermediate_count_mismatch"
