# EPB Phase 3B-3 — Echo Chamber Code Appendix

Mechanical verification artifact for Phase 3B-3 (Echo Chamber only). This
document is a literal record of what Phase 3B-3 implemented, not an
analysis of it — the implementation report, delivered separately in this
phase's final response, carries the scientific/design commentary and the
semantic-referent audit. Every source block below was extracted directly
from the actual files on disk after implementation via Python's `ast`
module (`node.lineno`/`node.end_lineno`, including decorators) for
individual function boundaries, or via a direct full-file/full-block
line-range read where that is itself the unambiguous boundary. No block
was paraphrased, reconstructed from memory, or truncated. This is a
separate artifact from `EPB_PHASE3A_CODE_APPENDIX.md`,
`EPB_PHASE3B1_MIRROR_LOOP_CODE_APPENDIX.md`, and
`EPB_PHASE3B2_VIOLATION_STATE_CODE_APPENDIX.md`, none of which is
overwritten or modified by this pass.

This is the OLD empirical EPB `echo_chamber` battery (TF-IDF/cosine
seed-vs-final similarity). It is explicitly NOT "Echo Chamber Zero" (ECZ),
a separate theoretical CCL construct — ECZ was not opened, modified, or
cited as an implementation basis anywhere in this pass. See Item 1's module
docstring for the implementation-level statement of this separation.

Repository: `/Users/bentleydevilling/Desktop/epb-benchmark`
Branch: `claude/build-epb-v1-019fiQ3GAZQXNXmUKdctF6VT`
HEAD at extraction time (unchanged by this phase): `a3732e8299da4286b1651d7f68bb654a3db80577`

## Final Failed-Task Diagnostic Referent Correction (this revision)

This revision regenerates Item 1 (`echo_scoring.py`) and Item 8 (the test
file) after one final diagnostic-referent defect found by direct review:
`_task_evaluability`'s `task_status == "failed"` early-return branch
hard-coded `seed_present=False`, `seed_valid=False`, `seed_issue=None`,
bypassing `_seed_validity(task)` entirely -- a second violation of the
same `seed_present` definition the prior (Final Seed-Presence Diagnostic)
correction had just established: "was the `initial_text` key structurally
present in the persisted record."

Directly confirmed against `run_battery.py::run_echo_chamber_battery`'s
own exception handler before coding: `seed_text = config["seed_text"]` is
read BEFORE the `try` block that can fail, and the handler's `extra`
dict explicitly includes `"initial_text": seed_text` — so every real,
historically-producible failed Echo Chamber record has `initial_text`
structurally present (with the actual seed value), never absent. The
prior hard-coded `seed_present=False` was therefore a false provenance
diagnostic for the real, historically-observed shape, not merely a
theoretical edge case.

Fix: the failed-task branch now calls `_seed_validity(task)` -- the exact
same function every other branch uses -- and spreads its result
(`seed_present`, `seed_valid`, `seed_issue`) into the returned record,
rather than hard-coding those three fields separately. There is now
exactly one implementation of seed-presence/validity semantics in this
module, applied uniformly regardless of `task_status`. `break_reason` for
a failed task is renamed from `"missing_record"` (false — the JSONL
record itself is genuinely present) to `"task_failed"` (truthful — a
present record reporting that generation raised), used unconditionally
regardless of the task's seed state (the failure is the controlling
reason a failed task is non-evaluable, not its seed).

This is a diagnostic-truthfulness correction only, with the same
non-goal boundary as the two prior corrections: a valid persisted seed on
a failed task does NOT rescue it — `evaluable` remains unconditionally
`False` for every `task_status == "failed"` record regardless of what
`_seed_validity` reports, verified unchanged by direct regression:
`usable_tasks`, the 5/10 publication floor, `planned`/`applicable`=10,
the TF-IDF estimator and its input population, chain cardinality, the
canonical five-round immutability, `QuantityResult` field mapping,
`validation_status`, Sec 7.9's unresolved status, CLI behavior, and ECZ
non-conflation — all 283 full-suite tests pass, with the corrected
diagnostic confirmed to fail under the pre-fix hard-coded branch before
the fix was applied (simulated the old branch's literal output against
the real failed-with-seed shape and observed `seed_present=False`,
`break_reason="missing_record"`, both false, before editing the source).

Per the governing prompt's Sec 11, the separate, already-logged
diagnostic-precedence follow-up (which reason wins `break_reason` when a
non-failed task has both an invalid seed and an invalid chain) remains
untouched and unresolved by this pass — mechanically unrelated to the
failed-task branch, which never reaches that precedence question at all
(a failed task's `break_reason` is unconditionally `"task_failed"`).

Items 2-7 (result_adapter.py's docstring, import+constants block, and
`score_echo_chamber_result`; all three of cli/main.py's Echo Chamber
blocks) are untouched by this correction — reproduced below for
traceability completeness, re-verified against current source at the
same line ranges as the prior revision (line counts match exactly,
confirming no incidental change).

---

## Traceability table

| Frozen Phase 2 requirement / correction | Implementation symbol | Acceptance scenario | Test | Appendix item | Independent source match |
|---|---|---|---|---|---|
| **Final Failed-Task Diagnostic Referent Correction — failed-task branch reads the same `_seed_validity(task)` as every other branch, never hard-coded** | `echo_scoring.py::_task_evaluability` (`task_status == "failed"` branch) | E | `test_scenario_e_failed_task_with_valid_persisted_seed`, `test_scenario_e_failed_task_without_seed`, `test_scenario_e_failed_task_with_none_seed` | Item 1 | Verified |
| **`break_reason` for a failed task is `"task_failed"`, never `"missing_record"`** | `echo_scoring.py::_task_evaluability` | E | `test_scenario_e_task_failure_record`, `test_failed_record_break_reason_never_missing_record` | Item 1 | Verified |
| **Seed diagnostics are identical across task_status (universal invariant)** | `echo_scoring.py::_seed_validity` (single implementation, called from both branches) | E, S | `test_universal_seed_diagnostic_invariant_across_task_status` | Item 1 | Verified |
| **A valid persisted seed on a failed task does not rescue it — remains unconditionally non-evaluable** | `echo_scoring.py::_task_evaluability` (`"evaluable": False` unconditional in the failed branch) | E | `test_scenario_e_failed_task_with_valid_persisted_seed` | Item 1 | Verified |
| Final Seed-Presence Diagnostic Correction — seed_present tracks structural key presence only (prior pass, unchanged) | `echo_scoring.py::_seed_validity` | V | `test_scenario_v_missing_seed_key_distinct_from_present_none`, `test_seed_presence_validity_matrix` | Item 1 | Verified |
| Explicit-None seed gets its own diagnostic code (prior pass, unchanged) | `echo_scoring.py::_seed_validity` (`seed_issue="null_initial_text"`) | V | `test_scenario_v_malformed_seed_shapes_all_block_evaluability` | Item 1 | Verified |
| Correction A — canonical round count not caller-overridable (prior pass, unchanged) | `echo_scoring.py::ECHO_CHAMBER_CANONICAL_N_ROUNDS`, `score_echo_chamber` (no `n_rounds` param) | Q, W | `test_scenario_q_...`, `test_scenario_w_...` | Item 1 | Verified |
| Correction B — missing/malformed seed makes task non-evaluable (prior pass, unchanged) | `echo_scoring.py::_seed_validity`, `_task_evaluability` | S, T, U, V | `test_scenario_s_...` through `test_scenario_v_...` | Item 1 | Verified |
| ECZ non-conflation (module documents the separation) | `echo_scoring.py` module docstring | — | `test_no_ecz_conflation_documented` | Item 1 | Verified |
| Natural evidence unit is the task, not the round (Sec 7.4) | `echo_scoring.py::score_echo_chamber` | — | `test_evidence_unit_integrity_fields_are_tasks_not_rounds` | Item 1 | Verified |
| Full-chain evaluability (Sec 7.5, FROZEN) | `echo_scoring.py::_task_evaluability` | A, B, C, D, F | `test_scenario_a_...` through `test_scenario_f_...` | Item 1 | Verified |
| Cardinality check against the `all([])` vacuous-truth trap | `echo_scoring.py::_task_evaluability` | P, Q | `test_scenario_p_...`, `test_scenario_q_...` | Item 1 | Verified |
| Truncated/excess chain shape rejected | `echo_scoring.py::_task_evaluability` | L, M, R | `test_scenario_l_...`, `test_scenario_m_...`, `test_scenario_r_...` | Item 1 | Verified |
| All-or-nothing at task level, no partial-task salvage (Sec 7.6) | `echo_scoring.py::_task_evaluability` | C, N | `test_no_partial_task_value_all_or_nothing` | Item 1 | Verified |
| Legacy bare-string never promoted to VALID_TEXT | `Observation.from_dict` (via `_task_evaluability`) | O | `test_scenario_o_...` (x2) | Item 1 | Verified |
| planned = applicable = 10, literal frozen anchor, not caller-overridable (Sec 7.7) | `echo_scoring.py::ECHO_CHAMBER_PLANNED_TASKS_ANCHOR`, `score_echo_chamber` | G, H, K | `test_planned_applicable_ten_invariant_across_shapes`, `test_frozen_denominator_is_not_a_runtime_override`, `test_scenario_k_...` | Item 1 | Verified |
| recorded_tasks is a distinct diagnostic, never substituted for applicable | `echo_scoring.py::score_echo_chamber` | K | `test_scenario_k_...`, `test_recorded_tasks_never_substituted_for_applicable_in_result_wrapper` | Item 1 | Verified |
| Minimum score-eligibility threshold >=5/10 (Sec 7.8, PROVISIONAL) | `echo_scoring.py::ECHO_CHAMBER_MIN_EVALUABLE_TASKS` | G, H, T | `test_scenario_g_...`, `test_scenario_h_...`, `test_threshold_boundary_both_sides`, `test_scenario_t_...` | Item 1 | Verified |
| TF-IDF/cosine estimator formula unchanged; only inclusion set changes | `metrics.py::compute_tfidf_similarity` (unmodified) | I, U | `test_scenario_i_...`, `test_scenario_u_...` | Item 1 | Verified (unmodified — N/A diff) |
| Unusable tasks excluded from the estimator | `echo_scoring.py::score_echo_chamber` | I, U | `test_unusable_tasks_excluded_from_estimator_does_not_change_aggregate`, `test_scenario_u_...` | Item 1 | Verified |
| Sec 7.9 canonical-inclusion status UNRESOLVED, not encoded anywhere | `echo_scoring.py`/`result_adapter.py` module docstrings | — | `test_sec_7_9_canonical_inclusion_status_not_encoded_anywhere` | Items 1, 2, 4 | Verified |
| Single granularity: `planned`/`applicable`/`usable` share one unit (Sec 7.11) | `result_adapter.py::score_echo_chamber_result` | G, H | (implicit in G/H's `result.coverage` assertions) | Item 4 | Verified |
| PROVISIONAL validation, never FROZEN (Sec 7.8/7.11) | `result_adapter.py::ECHO_CHAMBER_VALIDATION_STATUS` | G, H | `test_validation_invariant_always_provisional_never_frozen` | Item 3 | Verified |
| No canonical eligibility (Sec 8.3, unmodified architecture) | `result.py::QuantityResult.canonical_consumption_eligible` | G, H | `test_canonical_invariant_always_false` | — (not modified) | N/A (unmodified) |
| Insufficient-evidence vs scoring-error categorical separation | `result_adapter.py::score_echo_chamber_result` | J | `test_scenario_j_...` | Item 4 | Verified |
| Legacy CLI bucket reuse (`insufficient_evidence_batteries`, never `scoring_failures`) | `cli/main.py::score`, Echo Chamber block (unchanged) | — | Exercised via `test_cli_result_architecture.py`/`test_cli_scoring_failure.py` fixtures | Item 6 | Verified |
| No aliasing / no double-count between `final_text` and `intermediate_texts` | `echo_scoring.py::_task_evaluability` | R | `test_scenario_r_final_text_never_double_counted_as_an_intermediate` | Item 1 | Verified |

---

## Universal seed-diagnostic invariant table (Sec 9 of this correction pass)

| task_status | initial_text shape | seed_present | seed_valid |
|---|---|---:|---:|
| completed | absent | False | False |
| completed | `None` | True | False |
| completed | valid | True | True |
| failed | absent | False | False |
| failed | `None` | True | False |
| failed | valid | True | True |

Directly proven by `test_universal_seed_diagnostic_invariant_across_task_status`
(all six rows) — `task_status` never redefines what `seed_present` means;
the identical `_seed_validity(task)` call governs every row. A failed row
additionally asserts `evaluable is False` unconditionally, regardless of
seed state.

## Diagnostic-precedence follow-up (logged in the prior revision — still not resolved)

Unchanged by this pass and mechanically unrelated to the failed-task
branch (a failed task's `break_reason` is unconditionally `"task_failed"`,
never reaching the seed-vs-chain precedence question at all). Still
explicitly deferred per the governing prompt's Sec 11.

---

## Item 1 — `epb/scoring/echo_scoring.py (entire file, CORRECTED this pass -- Final Failed-Task Diagnostic Referent Correction)` (lines 1–515)

```python
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
```

## Item 2 — `epb/scoring/result_adapter.py, module docstring (unchanged this pass)` (lines 1–62)

```python
"""Phase 3A/3B control-flow seam: converts each battery scorer's
output/exception into the frozen two-axis `QuantityResult` representation
(EPB_PHASE2_EVIDENCE_SEMANTICS.md Sec 8.4).

Mirror Loop (Phase 3B-1), Violation State (Phase 3B-2), and Echo Chamber
(Phase 3B-3) now implement Phase 2's frozen battery-specific evidence
semantics (Sec 4.4-4.9, Sec 6.3-6.7, and Sec 7.4-7.8 respectively) directly
-- see `score_mirror_loop_result`'s, `score_violation_state_result`'s, and
`score_echo_chamber_result`'s own docstrings for their field mappings.
Confabulation remains the one battery still on the Phase 3A transitional
path for its `fabrication_incidence`/`persistence` sub-quantities (see
`score_confabulation_result` and `ConfabulationResult` below) -- Phase
3B-4's not-yet-reached work.

The generic `_run_single_quantity` helper below still describes the
transitional Phase 1 condition it was originally built for:

    Phase 1 scoreable (no blocked tasks)  -> measurement_state = SCORED
    Phase 1 UnscoreableEvidenceError      -> measurement_state = INSUFFICIENT_EVIDENCE
    any other exception (a genuine bug)   -> measurement_state = SCORING_ERROR

but as of this phase it is no longer called by any of Mirror Loop,
Violation State, or Echo Chamber's wrappers -- each now has its own
battery-specific function, matching its own frozen Phase 2 semantics
directly rather than reusing this generic transitional mapping.
- Confabulation's two sub-quantities do NOT follow that same
  all-or-nothing/`planned==applicable==usable` pattern (see
  `score_confabulation_result`):
  - `fabrication_incidence` is `Optional[QuantityResult]` -- `None`, not an
    instantiated `SCORED` (or any other) `QuantityResult`, whenever the
    underlying Phase 1 scorer call succeeds. `SCORED` asserts a validly
    computable measurement exists (Phase 2 Sec 8.1); Phase 3A has not
    implemented the admissibility/coverage/provenance predicate (Sec
    5.4/5.5) that would let it truthfully know whether that measurement
    exists, let alone what it is -- so no `QuantityResult` is instantiated
    for it at all in that case, rather than instantiating one with a
    guessed state. See `ConfabulationResult`'s docstring for the full
    dependency-stop analysis and `fabrication_incidence_raw` for where the
    Phase 1 raw counts (`fabrication_count`/`n_tasks`/`labels_used`) still
    live, clearly not under the Phase 2 scientific name. This is narrower
    than the blocked/error cases below: when Phase 1's own (unchanged)
    task-level evidence-validity gate fails, or the scorer genuinely
    errors, `fabrication_incidence` IS still instantiated (as
    `INSUFFICIENT_EVIDENCE`/`SCORING_ERROR`) -- those conditions are true
    regardless of what Phase 3B's eventual admissibility formula turns out
    to be, unlike `SCORED`, which would require knowing that formula.
  - `persistence.applicable`/`.usable` are deliberately left `None` even
    in the `SCORED` case -- Phase 1 has no opportunity-count concept for
    persistence at all; Phase 2 Sec 5.8 defines `applicable` for
    persistence as the confirmed-fabrication count, and routing
    `applicable == 0` to `NO_APPLICABLE_EVIDENCE` is explicitly Phase 3B's
    work (this phase's governing prompt Sec 6/Sec 9.6). This pass leaves
    `persistence` unchanged (this phase's governing prompt Sec 6 requires
    it): unlike fabrication_incidence, `persistence.value` is a real,
    already-computed number (`raw["epb_persistence"]`, the same formula
    that will remain the numerator under Phase 2's eventual admissible
    denominator) -- `SCORED` there does not have fabrication_incidence's
    specific defect of asserting a measurement exists while `value is
    None`. Whether persistence's `SCORED` state is fully Phase-2-admissible
    once Sec 5.8's completeness rule is implemented is a separate question,
    out of this pass's scope.
"""
```

## Item 3 — `epb/scoring/result_adapter.py, Echo Chamber import + validation-status constant (unchanged this pass)` (lines 64–83)

```python
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dataclasses import dataclass

from epb.scoring.confab_scoring import score_confabulation
from epb.scoring.echo_scoring import score_echo_chamber
from epb.scoring.exceptions import UnscoreableEvidenceError
from epb.scoring.mirror_loop_scoring import score_mirror_loop
from epb.scoring.result import MeasurementState, QuantityResult, ValidationStatus
from epb.scoring.violation_scoring import score_violation_state


# Frozen current validation statuses (Phase 2 Sec 8.2, Sec 16/16.2). Phase
# 3A encodes these constants as-is; it never derives, computes, or upgrades
# them (this phase's governing prompt Sec 4/Sec 9.3). No current battery
# quantity reaches FROZEN.
MIRROR_LOOP_VALIDATION_STATUS = ValidationStatus.PROVISIONAL
VIOLATION_STATE_VALIDATION_STATUS = ValidationStatus.PROVISIONAL
ECHO_CHAMBER_VALIDATION_STATUS = ValidationStatus.PROVISIONAL
```

## Item 4 — `epb/scoring/result_adapter.py::score_echo_chamber_result (unchanged this pass)` (lines 380–459)

```python
def score_echo_chamber_result(run_dir: Path) -> QuantityResult:
    """Structured-result wrapper around `score_echo_chamber` (Phase 3B-3:
    implements the frozen Phase 2 empirical Echo Chamber semantics, Sec
    7.4-7.8 -- no longer a generic `_run_single_quantity`-style wrapper,
    for the same reason as Mirror Loop's and Violation State's own
    battery-specific wrappers: Echo Chamber's `SCORED`-vs-
    `INSUFFICIENT_EVIDENCE` distinction is no longer "did any task's
    evidence fail Phase 1's validity check" (that no longer blocks the
    battery -- Sec 7.5/7.6 generalize the Sec 4.7/6.4 correction to this
    construct); it is now "did evaluable-task coverage clear Sec 7.8's
    literal floor," a condition `score_echo_chamber` itself already
    resolves into `evaluable_tasks_eligible`/`epb_drift`.

    Final Echo Chamber Freeze-Integrity Correction: this wrapper takes no
    `n_rounds` argument (Correction A) -- `score_echo_chamber` itself
    derives the expected chain length unconditionally from
    `ECHO_CHAMBER_CANONICAL_N_ROUNDS`, so there is no round-count
    parameter left for this wrapper to pass through. Neither production
    caller ever passed a non-default value before this correction
    (verified directly against `epb/cli/main.py`, the only caller), so no
    legitimate use case is removed.

    `QuantityResult` field mapping for Echo Chamber -- like Violation
    State (and UNLIKE Mirror Loop), this battery has only ONE relevant
    granularity: Phase 2 Sec 7.4/7.6 fix the evidence unit at the task
    level (exactly one seed-vs-final comparison per task, no round-level
    denominator), and Sec 7.7/7.8 define `planned`/`applicable`/`usable`
    AND the eligibility gate all directly in that same task unit -- there
    is no intervening per-task verdict step the way Mirror Loop's
    COLLAPSED/NOT_COLLAPSED/CENSORED sits between a transition-level
    evidence unit and a task-level eligibility count. So:

    - `planned` = `planned_tasks` (10, Sec 7.7's literal anchor).
    - `applicable` = `applicable_tasks` (== `planned`, Sec 7.7 -- fixed
      regardless of failed/missing task records; NEVER derived from
      `recorded_tasks`, a genuinely distinct, separately reported
      diagnostic of how many task records this specific run's file
      actually contains).
    - `usable` = `usable_tasks` -- exactly the quantity Sec 7.8's
      eligibility gate itself uses (`usable_tasks >= 5`), so `coverage`
      (derived `usable/applicable`) is, honestly and not coincidentally,
      the same quantity the gate reads.

    Sec 7.9's battery-level canonical-inclusion status (UNRESOLVED,
    EXPERIMENTAL/DEFER as the working default) is a separate, wider-scope
    question this function does not decide and does not encode anywhere
    -- it is not `validation_status`, not folded into
    `canonical_consumption_eligible`, and not affected by whether a given
    run's `epb_drift` reaches `SCORED`. See this module's and
    `echo_scoring.py`'s docstrings for the full two-scope distinction
    (Sec 7.11).
    """
    try:
        raw = score_echo_chamber(run_dir)
    except Exception as exc:
        # A genuine scorer/implementation anomaly (malformed JSONL, missing
        # file) -- score_echo_chamber no longer raises
        # UnscoreableEvidenceError for any per-task evidence condition (Sec
        # 7.5/7.6 supersede that for this construct), so every exception
        # reaching here is a genuine bug, never a scientific
        # evidence-usability condition.
        return QuantityResult(
            quantity="echo_chamber.drift",
            measurement_state=MeasurementState.SCORING_ERROR,
            validation_status=ECHO_CHAMBER_VALIDATION_STATUS,
            error=f"{type(exc).__name__}: {exc}",
        )

    eligible = raw["evaluable_tasks_eligible"]

    return QuantityResult(
        quantity="echo_chamber.drift",
        measurement_state=MeasurementState.SCORED if eligible else MeasurementState.INSUFFICIENT_EVIDENCE,
        validation_status=ECHO_CHAMBER_VALIDATION_STATUS,
        value=raw["epb_drift"] if eligible else None,
        planned=raw["planned_tasks"],
        applicable=raw["applicable_tasks"],
        usable=raw["usable_tasks"],
        details=raw,
    )
```

## Item 5 — `epb/cli/main.py, import block (unchanged this pass)` (lines 1–36)

```python
"""CLI for EPB (Epistemic Pathology Benchmark)."""

import json
import logging
import os
import shutil
import sys
from pathlib import Path

import click
import yaml

from epb import __epb_version__
from epb.adapters.base import OBSERVATION_SCHEMA_VERSION
from epb.runner.run_benchmark import run_benchmark
from epb.scoring.mirror_loop_scoring import (
    MIRROR_LOOP_MIN_VERDICT_BEARING_TASKS,
    score_mirror_loop,
)
from epb.scoring.confab_scoring import score_confabulation
from epb.scoring.violation_scoring import (
    VIOLATION_STATE_MIN_USABLE_BENIGN_TURNS,
    score_violation_state,
)
from epb.scoring.echo_scoring import (
    ECHO_CHAMBER_MIN_EVALUABLE_TASKS,
    score_echo_chamber,
)
from epb.scoring.aggregate import compute_epb_truth, get_certification_level
from epb.scoring.result import RESULT_SCHEMA_VERSION
from epb.scoring.result_adapter import (
    score_confabulation_result,
    score_echo_chamber_result,
    score_mirror_loop_result,
    score_violation_state_result,
)
```

## Item 6 — `epb/cli/main.py::score, Echo Chamber legacy scoring block (unchanged this pass)` (lines 328–367)

```python
    # Score Echo Chamber
    if (run_path / "echo_chamber.jsonl").exists():
        click.echo("Scoring Echo Chamber...")
        try:
            ec_result = score_echo_chamber(run_path)
            if ec_result["epb_drift"] is None:
                # Phase 3B-3: Echo Chamber's frozen evaluable-task-coverage
                # publication gate (Phase 2 Sec 7.8) was not met -- a
                # legitimate scientific INSUFFICIENT_EVIDENCE state, not a
                # parse/scoring exception. Same representation established
                # in Phase 3B-1/3B-2: never `scoring_failures` (the scorer
                # did not raise), never a silent None into `scores` --
                # recorded in the separate, honestly-named
                # `insufficient_evidence_batteries` bucket.
                click.echo(
                    f"  Insufficient evaluable-task coverage: "
                    f"{ec_result['usable_tasks']}/{ec_result['applicable_tasks']} "
                    f"(floor: {ECHO_CHAMBER_MIN_EVALUABLE_TASKS})",
                    err=True,
                )
                insufficient_evidence_batteries["echo_chamber"] = {
                    "reason": "insufficient_evaluable_task_coverage",
                    "detail": (
                        f"Only {ec_result['usable_tasks']} of "
                        f"{ec_result['applicable_tasks']} applicable tasks were "
                        f"evaluable (Phase 2 Sec 7.8 requires "
                        f">= {ECHO_CHAMBER_MIN_EVALUABLE_TASKS})."
                    ),
                }
                details["echo_chamber"] = ec_result
            else:
                scores["echo_drift"] = ec_result["epb_drift"]
                details["echo_chamber"] = ec_result
                click.echo(f"  EPB Drift: {ec_result['epb_drift']}")
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            scoring_failures["echo_chamber"] = {
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
```

## Item 7 — `epb/cli/main.py::score, Echo Chamber quantities block (unchanged this pass)` (lines 494–496)

```python

    if (run_path / "echo_chamber.jsonl").exists():
        quantities["echo_chamber.drift"] = score_echo_chamber_result(run_path).to_dict()
```

## Item 8 — `tests/test_echo_chamber_phase3b3.py (entire file, EXTENDED this pass -- Scenario E corrected, 5 new failed-task diagnostic tests)` (lines 1–1131)

```python
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
```

