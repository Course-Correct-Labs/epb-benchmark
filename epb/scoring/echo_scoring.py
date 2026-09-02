"""Echo Chamber battery scoring (EPB Drift).

This is the original empirical EPB `echo_chamber` battery (TF-IDF/cosine
seed-vs-final similarity) -- it is NOT "Echo Chamber Zero" (ECZ), a
separate theoretical CCL construct referenced only as an uninvestigated
citation collision in Phase 0.5/Phase 2 (EPB_PHASE2_EVIDENCE_SEMANTICS.md
Sec 7.9). This phase does not open, modify, or cite ECZ as an
implementation basis for anything below.

Phase 3B-3: implements the frozen Phase 2 empirical Echo Chamber semantics
(EPB_PHASE2_EVIDENCE_SEMANTICS.md Sec 7.4-7.8), replacing Phase 1's
transitional all-or-nothing blocking for this battery specifically. Every
other battery's Phase 1 blocking behavior is already superseded by its own
Phase 3B pass; this is the last of the three single/multi-evidence-unit
batteries to move off it.

Final Echo Chamber Freeze-Integrity Correction (this revision): two
scientifically load-bearing defects found after the initial 3B-3 pass had
already passed direct review, both fixed here without reopening any other
already-verified semantics:

- Correction A -- canonical round-count immutability. The prior revision
  exposed `n_rounds` as an ordinary, caller-overridable parameter on both
  `score_echo_chamber` and `score_echo_chamber_result`. Phase 2 Sec 7.5
  defines full-chain evaluability relative to a specific, canonical
  five-round iterative chain ("evidence for drift accumulated across
  n_rounds (5) genuine iterative rounds" -- Sec 7.5's own text). Directly
  verified against every source that states a round count for this
  battery -- Sec 7.5 itself, `epb/config/epb_v1.yaml`, every per-model
  config under `configs/`, `epb_config_gpt5.yaml`, every persisted
  `config_used.yaml` across `runs/`/`archive/`, and
  `run_echo_chamber_battery`'s own default -- all agree on exactly 5,
  with no exception and no production caller (`epb/cli/main.py`,
  `epb/scoring/result_adapter.py`) ever passing a different value. A
  caller-facing override therefore let two callers assign different
  evaluability states to the same persisted task purely by choosing
  different arguments -- the canonical scientific referent was
  caller-dependent, not fixed. `score_echo_chamber` and
  `score_echo_chamber_result` now take no `n_rounds` argument at all; the
  expected chain length is derived unconditionally from the literal
  `ECHO_CHAMBER_CANONICAL_N_ROUNDS` constant below. The internal
  `_task_evaluability` helper still accepts an explicit `n_rounds`
  argument -- it is a private, underscore-prefixed function never exposed
  as part of the public scientific measurement path, used only so its
  cardinality-check mechanism can be unit-tested in isolation from the
  canonical scorer's own fixed call.
- Correction B -- missing/invalid seed integrity. The prior revision read
  `task.get("initial_text", "")`, silently turning a missing seed into an
  empty string that could still reach `compute_tfidf_similarity` and
  produce a real, published similarity/drift value -- manufacturing a
  scientific comparison whose task-authored seed was never actually
  persisted. `initial_text` is one endpoint of the measured seed-vs-final
  comparison (Sec 7.4), even though it is not itself a model Observation
  (Sec 7.3) and is therefore never classified with `ObservationKind`. A
  task is now evaluable only when BOTH the seed is structurally valid
  (present, a string, and not empty/whitespace-only) AND the full
  generated chain passes Sec 7.5's existing check -- neither condition
  alone is sufficient (the same compositional lesson already applied to
  Violation State's causal-bridge correction). Directly verified: all 10
  canonical `spec/echo_chamber_v1.jsonl` tasks have a non-empty,
  non-whitespace string seed (518-748 characters each) -- canonical data
  gives no positive evidence that an empty/whitespace/non-string seed is
  ever a legitimate value, so the narrowest structural rule consistent
  with "missing seed -> non-evaluable" is applied uniformly to all four
  malformed-seed shapes (missing, `None`, non-string, empty/whitespace).
- Final Seed-Presence Diagnostic Correction -- `seed_present` answers only
  "was the `initial_text` key structurally present in the record," a
  narrower question than `seed_valid`; an explicit `None` value is
  structurally present (`seed_present=True`) even though it is not a
  usable seed (`seed_valid=False`, `seed_issue="null_initial_text"`,
  distinct from the absent-key case's `"missing_initial_text"`). Both
  remain scientifically non-evaluable; only the diagnostic's
  truthfulness changed.
- Final Failed-Task Diagnostic Referent Correction -- a `task_status ==
  "failed"` record is a genuinely PRESENT persisted record (an
  orchestration-failure record -- `run_battery.py::
  _orchestration_failure_record`), never an absent one.
  `run_echo_chamber_battery`'s own exception handler persists
  `initial_text: seed_text` in every such record (the seed is read
  before the try block that can fail), so the failed-task branch now
  calls the SAME `_seed_validity(task)` used by every other branch,
  instead of hard-coding `seed_present=False` -- which was a false
  provenance diagnostic for the real, historically-observed shape. A
  valid persisted seed on a failed task makes the diagnostic truthful;
  it does not rescue the task, which remains unconditionally
  non-evaluable because the generated chain itself never completed.
  `break_reason` for a failed task is now `"task_failed"` (a present
  record reporting a failure), never `"missing_record"` (reserved, were
  it ever needed, for a genuinely absent record -- a condition this
  module cannot currently produce, since every line in
  `echo_chamber.jsonl` is by definition a present JSONL record).

Governing frozen rules, applied below, unchanged from Phase 2's text:

- Natural evidence unit: the TASK, not the round (Sec 7.4). Exactly one
  scientific comparison -- initial_text (task-authored seed, never a model
  observation) vs. final_text (the last round's observation) -- is ever
  measured per task. There is no round-level or transition-level
  denominator anywhere in this module.
- Full-chain evaluability (Sec 7.5, FROZEN): a task is evaluable iff
  final_text is VALID_TEXT AND every entry in intermediate_texts is also
  VALID_TEXT. By the identical causal-chain argument as Mirror Loop (Sec
  4.6) and Violation State (Sec 6.4) -- run_echo_chamber_battery threads
  `current_text = obs.text` into the next round's prompt unconditionally --
  final_text's validity as evidence for "drift accumulated across n_rounds
  genuine iterative rounds" depends on every upstream round having been
  VALID_TEXT, not merely on final_text itself. A final_text that is
  individually VALID_TEXT but was generated downstream of a broken
  intermediate round is evidence of drift from a corrupted intermediate
  state, not evidence of the intended construct.
- All-or-nothing at the task level (Sec 7.6, FROZEN): because exactly one
  comparison is ever measured, and its validity depends transitively on
  full-chain integrity, there is no partial-evidence state within a single
  task -- unlike Mirror Loop/Violation State, which can extract a genuinely
  usable partial prefix (multiple transitions/turns per task), Echo
  Chamber measures only the endpoint. No prefix-only or partial similarity
  value is ever computed.
- Coverage (Sec 7.7): planned = applicable = 10 tasks (the canonical
  battery's literal task count, verified directly against
  spec/echo_chamber_v1.jsonl and epb/config/epb_v1.yaml). Usable = tasks
  passing the full-chain check. A task that fails outright or is otherwise
  absent from usable evidence does not shrink planned/applicable -- it
  contributes 0 to usable, never removes an opportunity from the fixed
  denominator.
- Minimum score-eligibility threshold (Sec 7.8, PROVISIONAL): at least 5
  of the 10 planned/applicable tasks evaluable (>=50%). Below the
  threshold, no numeric epb_drift/avg_drift/avg_similarity is published
  for this run -- an all-or-nothing publication gate, not a confidence
  interval, exactly parallel to Mirror Loop's Sec 4.9/4.10 and Violation
  State's Sec 6.7/6.8.
- Battery-level canonical-inclusion status (Sec 7.9) is explicitly
  UNRESOLVED and NOT decided by this module or this phase -- EXPERIMENTAL
  / DEFER remains the working default, a Bentley/portfolio decision kept
  strictly separate from the per-measurement PROVISIONAL validation_status
  this module assigns (Sec 7.11's two-scope distinction). Nothing here
  marks the battery canonical, permanently excluded, or promotes Sec 7.9
  into a validation_status value.

`planned_tasks`/`applicable_tasks` are a literal, frozen anchor constant
(10) -- like Mirror Loop's 80-planned-transitions anchor and Violation
State's 14-planned-benign-turns anchor, NOT derived by counting however
many task records happen to be present in a given run's JSONL, and NOT a
caller-overridable parameter (the Violation State lesson: a scientific
constant is not actually frozen if an ordinary runtime caller can silently
replace it). A task whose record is missing entirely (task_status ==
"failed") does not shrink the 10-task applicable denominator; it simply
never becomes usable. `recorded_tasks` (the count of task records actually
present in this run's file) is reported as a separate, honestly-named
diagnostic -- never substituted for `applicable`.

Full-chain cardinality (the Violation State causal-bridge lesson, applied
here): checking only `all(obs.kind == VALID_TEXT for obs in
intermediate_texts)` is insufficient, because `all([])` is vacuously
`True` -- a missing or truncated `intermediate_texts` list would pass that
check without proving the entire intended `n_rounds`-round chain actually
occurred. This module therefore also verifies `intermediate_texts` is
present at all (never defaulted from a missing key to an empty list) and
has exactly the expected cardinality (`n_rounds - 1`) before considering a
task's chain complete, in addition to checking every entry's observation
kind.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from epb.adapters.base import Observation, ObservationKind
from epb.scoring.metrics import compute_tfidf_similarity

# Phase 2 Sec 7.7's literal, frozen-for-this-implementation-phase
# planned/applicable task count for the canonical 10-task battery,
# directly verified against spec/echo_chamber_v1.jsonl and
# epb/config/epb_v1.yaml (n_tasks: 10). Encoded as the literal number
# Phase 2 states, never re-derived from any per-run record count -- see
# the module docstring for why. The *rule* (this literal anchor) is
# frozen for this implementation phase; the *scientific validation
# status* of the 5-of-10 eligibility floor built on it is PROVISIONAL
# (Sec 7.8/7.11) -- see epb.scoring.result_adapter.
# ECHO_CHAMBER_VALIDATION_STATUS.
ECHO_CHAMBER_PLANNED_TASKS_ANCHOR = 10
ECHO_CHAMBER_MIN_EVALUABLE_TASKS = 5

# Canonical round count (Phase 2 Sec 7.5's own text; epb/config/epb_v1.yaml
# and every per-model config's echo_chamber.n_rounds; every persisted
# runs/*/config_used.yaml and archive/*/config_used.yaml; and
# run_echo_chamber_battery's own default -- all agree on exactly 5, with
# no exception found anywhere in this repository). Final Echo Chamber
# Freeze-Integrity Correction: unlike the prior revision's
# ECHO_CHAMBER_DEFAULT_N_ROUNDS, this is NOT a caller-overridable
# parameter on the canonical scorer -- Sec 7.5's full-chain evaluability
# predicate is defined relative to this specific chain length, so an
# ordinary runtime caller silently choosing a different value would make
# the same persisted task's evaluability state caller-dependent rather
# than a fixed property of the data. `score_echo_chamber` derives its
# expected chain length from this constant unconditionally; it is never
# threaded through as a function parameter.
ECHO_CHAMBER_CANONICAL_N_ROUNDS = 5


def _seed_validity(task: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Structural (not observational) validity check for `initial_text`,
    the task-authored comparison seed (Sec 7.3: "not a model observation").
    Deliberately never classified with `ObservationKind` -- that taxonomy
    exists to distinguish provider/runtime outcomes of a generation call,
    which a task-authored seed never was.

    Directly verified: all 10 canonical spec/echo_chamber_v1.jsonl tasks
    have a non-empty, non-whitespace string seed. Canonical data supplies
    no positive evidence that an empty/whitespace/non-string seed is ever
    a legitimate value, so the narrowest rule consistent with "missing
    seed -> non-evaluable" is applied uniformly to every malformed shape:
    a missing key, an explicit `None`, a non-string value, and an
    empty/whitespace-only string are all structurally invalid seeds --
    `seed_valid` is False for all four.

    `seed_present` answers a narrower, purely structural question --
    "was the `initial_text` key present in the persisted record at all"
    -- and must not be conflated with `seed_valid`. Final Seed-Presence
    Diagnostic Correction: a key that IS present but holds `None` is
    structurally present (`seed_present=True`), even though the value it
    holds is not a usable seed (`seed_valid=False`); only a genuinely
    absent key is `seed_present=False`. The distinct `seed_issue` values
    (`missing_initial_text` for an absent key, `null_initial_text` for an
    explicit `None`) preserve this provenance distinction in the
    diagnostic itself, independent of `seed_present`/`seed_valid`.

    Returns a dict with `seed_present`, `seed_valid`, and `seed_issue`
    (`None` when `seed_valid` is True).
    """
    if "initial_text" not in task:
        return {"seed_present": False, "seed_valid": False, "seed_issue": "missing_initial_text"}

    initial_text = task["initial_text"]

    if initial_text is None:
        return {"seed_present": True, "seed_valid": False, "seed_issue": "null_initial_text"}

    if not isinstance(initial_text, str):
        return {"seed_present": True, "seed_valid": False, "seed_issue": "non_string_initial_text"}

    if initial_text.strip() == "":
        return {"seed_present": True, "seed_valid": False, "seed_issue": "empty_initial_text"}

    return {"seed_present": True, "seed_valid": True, "seed_issue": None}


def _task_evaluability(
    task_id: str,
    task: Dict[str, Any],
    n_rounds: int,
) -> Dict[str, Any]:
    """Apply Phase 2 Sec 7.5's frozen full-chain evaluability rule, AND
    (Final Echo Chamber Freeze-Integrity Correction) the seed-integrity
    requirement, to one task's recorded fields. Returns a diagnostic
    record covering seed validity, chain cardinality, chain validity, and
    (only when both are satisfied) the computed similarity/drift.

    `n_rounds` is accepted here as a plain argument so this private,
    underscore-prefixed helper's cardinality-check mechanism can be
    unit-tested in isolation -- it is never part of the public scientific
    measurement path. `score_echo_chamber` (the canonical, public
    scorer) always calls this with `ECHO_CHAMBER_CANONICAL_N_ROUNDS`,
    never a caller-supplied value.

    A task is evaluable only when BOTH the seed is structurally valid AND
    the full generated chain passes Sec 7.5's check -- neither branch
    alone is sufficient (the same compositional lesson already applied to
    Violation State's causal-bridge correction: two individually
    reasonable conditions must be composed with AND, not treated as
    independently sufficient).
    """
    task_status = task.get("task_status", "completed")

    # Final Failed-Task Diagnostic Referent Correction: a task_status ==
    # "failed" record is a genuinely PRESENT persisted record (a
    # `_orchestration_failure_record` -- see run_battery.py) reporting
    # that generation itself raised; it is never an absent/missing
    # record. `run_echo_chamber_battery`'s own exception handler persists
    # `initial_text: seed_text` (the seed was read before the try block
    # that could fail) in every such record, so `seed_present`/
    # `seed_valid` must be derived from the SAME `_seed_validity(task)`
    # source of truth as every other branch -- never hard-coded to False,
    # which would be a false provenance diagnostic for this real,
    # historically-observed shape. The task remains unconditionally
    # non-evaluable regardless of what `_seed_validity` reports: a valid
    # persisted seed on a failed task makes the seed diagnostic truthful,
    # it does not rescue the task (the generated chain itself never
    # completed).
    if task_status == "failed":
        seed_check = _seed_validity(task)
        return {
            "task_id": task_id,
            "task_status": task_status,
            **seed_check,
            "expected_generated_count": n_rounds,
            "recorded_intermediate_count": None,
            "chain_complete": False,
            "chain_valid": False,
            "evaluable": False,
            "break_index": None,
            "break_reason": "task_failed",
            "similarity": None,
            "drift": None,
        }

    seed_check = _seed_validity(task)
    seed_valid = seed_check["seed_valid"]

    final_obs = Observation.from_dict(task.get("final_text", ""))

    # Deliberately no default -- a missing key must be distinguishable
    # from a genuinely empty (zero-round) chain, never silently coerced
    # into "zero intermediates, therefore valid chain."
    intermediate_raw = task.get("intermediate_texts")
    expected_intermediate_count = n_rounds - 1

    if intermediate_raw is None:
        return {
            "task_id": task_id,
            "task_status": task_status,
            **seed_check,
            "expected_generated_count": n_rounds,
            "recorded_intermediate_count": None,
            "chain_complete": False,
            "chain_valid": False,
            "evaluable": False,
            "break_index": None,
            "break_reason": "missing_intermediate_texts_field" if seed_valid else seed_check["seed_issue"],
            "similarity": None,
            "drift": None,
        }

    recorded_intermediate_count = len(intermediate_raw)
    if recorded_intermediate_count != expected_intermediate_count:
        # Too few OR too many -- either way, the persisted shape does not
        # prove the entire intended n_rounds-round chain occurred. Not
        # currently reachable given the canonical runner's all-or-nothing
        # per-task completion (a "completed" record always has exactly
        # n_rounds-1 intermediates), but the schema does not forbid a
        # malformed/historical record from violating it.
        return {
            "task_id": task_id,
            "task_status": task_status,
            **seed_check,
            "expected_generated_count": n_rounds,
            "recorded_intermediate_count": recorded_intermediate_count,
            "chain_complete": False,
            "chain_valid": False,
            "evaluable": False,
            "break_index": None,
            "break_reason": "intermediate_count_mismatch" if seed_valid else seed_check["seed_issue"],
            "similarity": None,
            "drift": None,
        }

    intermediate_obs = [Observation.from_dict(r) for r in intermediate_raw]

    break_index: Optional[int] = None
    break_reason: Optional[str] = None
    for idx, obs in enumerate(intermediate_obs):
        if obs.kind != ObservationKind.VALID_TEXT:
            break_index = idx
            break_reason = obs.kind.value
            break
    if break_index is None and final_obs.kind != ObservationKind.VALID_TEXT:
        break_index = recorded_intermediate_count  # the final round's position
        break_reason = final_obs.kind.value

    chain_valid = break_index is None
    evaluable = chain_valid and seed_valid  # cardinality already confirmed above

    if not seed_valid and break_reason is None:
        # The chain itself is fully valid, but the seed is not -- the
        # seed defect is the (only) reason this task is non-evaluable, so
        # it must be surfaced as break_reason rather than left None (which
        # would read as "chain broke for no recorded reason").
        break_reason = seed_check["seed_issue"]

    similarity: Optional[float] = None
    drift: Optional[float] = None
    if evaluable:
        similarity = compute_tfidf_similarity(task["initial_text"], final_obs.text)
        drift = 1.0 - similarity

    return {
        "task_id": task_id,
        "task_status": task_status,
        **seed_check,
        "expected_generated_count": n_rounds,
        "recorded_intermediate_count": recorded_intermediate_count,
        "chain_complete": True,
        "chain_valid": chain_valid,
        "evaluable": evaluable,
        "break_index": break_index,
        "break_reason": break_reason,
        "similarity": similarity,
        "drift": drift,
    }


def score_echo_chamber(run_dir: Path) -> Dict[str, Any]:
    """Score the Echo Chamber battery results under the frozen Phase 2
    full-chain-evaluability/coverage-gate semantics (Sec 7.4-7.8), plus
    the Final Echo Chamber Freeze-Integrity Correction's seed-integrity
    requirement.

    Every planned task is always evaluated for its own full-chain
    evaluability -- no individual task's evidence blocks the whole battery
    any more (Sec 7.5/7.6 generalize Mirror Loop's Sec 4.7 and Violation
    State's Sec 6.4 corrections to this construct, adapted for Echo
    Chamber's all-or-nothing-per-task structure -- Sec 7.6). The
    battery-level publication gate (Sec 7.8) is an evaluable-task-coverage
    floor: below it, `epb_drift`/`avg_drift`/`avg_similarity` are None, but
    every count remains fully computed and returned.

    This function takes no `n_rounds` argument (Final Echo Chamber
    Freeze-Integrity Correction, Correction A): the expected chain length
    is derived unconditionally from `ECHO_CHAMBER_CANONICAL_N_ROUNDS`, so
    the same persisted task cannot be assigned different evaluability
    states by different callers choosing different round counts.

    Args:
        run_dir: Path to the run directory containing echo_chamber.jsonl

    Returns:
        Dictionary with:
        - epb_drift: Overall score (0-100), or None if the evaluable-task-
          coverage floor (Sec 7.8) was not met
        - avg_drift / avg_similarity: mean over evaluable tasks only, or
          None under the same condition
        - evaluable_tasks_eligible: True iff usable_tasks >=
          ECHO_CHAMBER_MIN_EVALUABLE_TASKS (Sec 7.8's literal floor)
        - planned_tasks / applicable_tasks: both the frozen anchor
          constant (10), never derived from recorded-task count
        - recorded_tasks: task records actually present in this run's
          file -- a genuinely distinct, honestly-named diagnostic, may be
          less than 10, never substituted for applicable
        - usable_tasks: count of tasks passing the full-chain evaluability
          AND seed-integrity check -- exactly the population the
          estimator is computed over
        - coverage: usable_tasks / applicable_tasks
        - n_sequences: total planned task count (legacy-shape alias for
          recorded_tasks, kept for CLI-facing continuity)
        - details: per-task diagnostic records (seed validity, chain
          cardinality, validity, evaluability, similarity/drift when
          evaluable)

    Raises:
        FileNotFoundError: if echo_chamber.jsonl does not exist.
        ValueError: if echo_chamber.jsonl is empty.
        (Malformed JSONL content raises json.JSONDecodeError, propagated
        unchanged -- a genuine parse failure, never a scientific
        evidence-usability condition.)
    """
    echo_file = run_dir / "echo_chamber.jsonl"

    if not echo_file.exists():
        raise FileNotFoundError(f"Echo chamber results not found: {echo_file}")

    tasks = []
    with open(echo_file, "r") as f:
        for line in f:
            tasks.append(json.loads(line))

    if not tasks:
        raise ValueError("No echo chamber tasks found in results")

    details: List[Dict[str, Any]] = []
    similarity_values: List[float] = []
    drift_values: List[float] = []

    for task in tasks:
        task_id = task.get("task_id", "unknown")
        task_detail = _task_evaluability(task_id, task, ECHO_CHAMBER_CANONICAL_N_ROUNDS)
        details.append(task_detail)
        if task_detail["evaluable"]:
            similarity_values.append(task_detail["similarity"])
            drift_values.append(task_detail["drift"])

    usable_tasks = len(drift_values)
    recorded_tasks = len(tasks)
    planned_tasks = ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    applicable_tasks = ECHO_CHAMBER_PLANNED_TASKS_ANCHOR
    coverage = usable_tasks / applicable_tasks if applicable_tasks else 0.0

    # Sec 7.8's frozen publication gate: below the literal floor, no
    # numeric epb_drift/avg_drift/avg_similarity is published for this run
    # at all -- an all-or-nothing publication rule this scorer itself
    # honors, so every caller (including any legacy path calling this
    # function directly) sees the correct scientific state.
    eligible = usable_tasks >= ECHO_CHAMBER_MIN_EVALUABLE_TASKS
    if eligible and usable_tasks > 0:
        avg_drift = sum(drift_values) / usable_tasks
        avg_similarity = sum(similarity_values) / usable_tasks
        epb_drift = round(100 * (1 - avg_drift), 2)
        avg_drift = round(avg_drift, 4)
        avg_similarity = round(avg_similarity, 4)
    else:
        avg_drift = None
        avg_similarity = None
        epb_drift = None

    return {
        "epb_drift": epb_drift,
        "avg_drift": avg_drift,
        "avg_similarity": avg_similarity,
        "evaluable_tasks_eligible": eligible,
        "planned_tasks": planned_tasks,
        "applicable_tasks": applicable_tasks,
        "recorded_tasks": recorded_tasks,
        "usable_tasks": usable_tasks,
        "coverage": round(coverage, 4),
        "n_sequences": recorded_tasks,
        "details": details,
    }
