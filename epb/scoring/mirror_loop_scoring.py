"""Mirror Loop battery scoring (EPB Phi).

Phase 3B-1: implements the frozen Phase 2 Mirror Loop semantics
(EPB_PHASE2_EVIDENCE_SEMANTICS.md Sec 4.4-4.9), replacing Phase 1's
transitional all-or-nothing blocking for this battery specifically. Every
other battery's Phase 1 blocking behavior (UnscoreableEvidenceError) is
unchanged by this phase -- only Mirror Loop's evidence-usability rule
changes here.

Governing frozen rules, applied below, unchanged from Phase 2's text:

- Natural evidence unit: the transition (one Delta-I value between a
  consecutive response pair) -- Sec 4.4.
- A transition is usable only when both endpoints are
  ObservationKind.VALID_TEXT -- Sec 4.5.
- Usable transitions for a task = the transitions within the longest
  unbroken valid prefix starting at step 0. The first non-VALID_TEXT
  response at step k truncates the usable prefix to [0, k); everything
  from step k onward, including any later individually-valid response, is
  unusable -- Sec 4.6. Non-adjacent valid responses are never reconnected
  across a gap.
- Task-level verdict (Sec 4.7, corrected/frozen there), asymmetric by
  direction:
    - collapse_established == True                                -> COLLAPSED
    - collapse_established == False AND prefix_complete == True    -> NOT_COLLAPSED
    - collapse_established == False AND prefix_complete == False   -> CENSORED
  where `collapse_established` is the exact, unmodified `detect_collapse`
  formula applied to the usable prefix's delta sequence, and
  `prefix_complete` is True iff the usable prefix covers all n_steps-1
  intended transitions (i.e. no break occurred anywhere in the task). A
  positive collapse finding is irrevocable regardless of what happens
  afterward; a negative (NOT_COLLAPSED) finding requires the complete
  intended sequence.
- n_loops (the collapse_rate denominator) = COLLAPSED count + NOT_COLLAPSED
  count. CENSORED tasks are excluded from n_loops but always explicitly
  counted and reported -- never silently absorbed into either bucket --
  Sec 4.8.
- Minimum score-eligibility threshold (Sec 4.9, PROVISIONAL): at least 10
  of the 20 planned tasks reach an established verdict (verdict-bearing
  coverage >= 50%). Below the threshold, no numeric epb_phi/collapse_rate
  is published for this run -- an all-or-nothing publication gate, not a
  confidence interval (Sec 4.10).

A task whose evidence is not fully recorded at all (a Phase 1 Area 3
orchestration-failure record, task_status == "failed", no "responses" key)
is treated identically to a task whose usable prefix has length 0 -- the
exact same frozen rule applied to the k=0 edge case, not a new rule.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from epb.adapters.base import Observation, ObservationKind
from epb.scoring.metrics import compute_delta_i, detect_collapse

COLLAPSED = "collapsed"
NOT_COLLAPSED = "not_collapsed"
CENSORED = "censored"

# Phase 2 Sec 4.9's literal, frozen-for-this-implementation-phase
# publication gate: "at least 50% of the 20 planned tasks reach an
# established verdict... (>=10 of 20)". Encoded as the literal numbers
# Phase 2 states, not re-derived as int(0.5 * planned_tasks) -- Phase 2
# anchors this specific rule to the 20-task battery configured in
# epb/config/epb_v1.yaml, not to an abstract "50% of whatever N turns out
# to be" formula; if a future run's planned task count differs from 20,
# that is a new scientific question outside this implementation's scope,
# not something this constant silently re-derives an answer for.
#
# The *rule* (this literal floor) is frozen for this implementation phase;
# the *scientific validation status* of the floor itself is PROVISIONAL
# (Sec 4.9/4.10) -- no repeated-trials variance data exists to say whether
# 50%, 80%, or another floor is where collapse_rate becomes stable. See
# epb.scoring.result_adapter.MIRROR_LOOP_VALIDATION_STATUS.
MIRROR_LOOP_PLANNED_TASKS_ANCHOR = 20
MIRROR_LOOP_MIN_VERDICT_BEARING_TASKS = 10


def _usable_prefix_length(observations: List[Observation]) -> int:
    """Longest unbroken valid prefix length, from step 0 (Phase 2 Sec 4.6).

    Returns the count of leading observations that are all
    ObservationKind.VALID_TEXT. The first non-VALID_TEXT observation (or
    running out of recorded observations) ends the prefix; nothing after
    that point is ever reconnected into the usable prefix, even if it is
    itself individually valid.
    """
    k = 0
    for obs in observations:
        if obs.kind != ObservationKind.VALID_TEXT:
            break
        k += 1
    return k


def _task_verdict(
    observations: List[Observation],
    n_steps: int,
    collapse_threshold: float,
    min_consecutive: int,
) -> Dict[str, Any]:
    """Apply Phase 2 Sec 4.7's frozen, asymmetric task-verdict rule to one
    task's recorded observations. Returns a diagnostic record including the
    verdict and everything needed to audit it (Sec 4.7/Sec 10).
    """
    k = _usable_prefix_length(observations)
    n_usable_transitions = max(0, k - 1)
    prefix_complete = k == n_steps

    delta_sequence = [
        compute_delta_i(observations[i - 1].text, observations[i].text)
        for i in range(1, k)
    ]
    collapse_established = detect_collapse(
        delta_sequence, threshold=collapse_threshold, min_consecutive=min_consecutive
    )

    if collapse_established:
        verdict = COLLAPSED
    elif prefix_complete:
        verdict = NOT_COLLAPSED
    else:
        verdict = CENSORED

    # Diagnostic detail about where/why the causal chain broke, for
    # CENSORED (and any other non-complete) tasks -- Sec 10.
    break_index: Optional[int] = None
    break_reason: Optional[str] = None
    if k < len(observations):
        break_index = k
        break_reason = observations[k].kind.value
    elif k < n_steps:
        break_index = k
        break_reason = "missing_response"

    return {
        "usable_prefix_length": k,
        "n_usable_transitions": n_usable_transitions,
        "prefix_complete": prefix_complete,
        "delta_sequence": delta_sequence,
        "collapse_established": collapse_established,
        "verdict": verdict,
        "break_index": break_index,
        "break_reason": break_reason,
        "n_recorded_responses": len(observations),
    }


def score_mirror_loop(
    run_dir: Path,
    collapse_threshold: float = 0.05,
    min_consecutive: int = 3,
    n_steps: int = 5,
) -> Dict[str, Any]:
    """Score the Mirror Loop battery results under the frozen Phase 2
    task-verdict/coverage-gate semantics (Sec 4.4-4.9).

    Every planned task always resolves to exactly one verdict (COLLAPSED,
    NOT_COLLAPSED, or CENSORED) -- no individual task's evidence blocks the
    whole battery any more (Sec 4.7 explicitly supersedes Phase 1's ad hoc
    whole-battery block for this construct). The battery-level publication
    gate (Sec 4.9) is instead a verdict-bearing-coverage floor: below it,
    `epb_phi`/`collapse_rate` are None, but every count and the coverage
    figure itself remain fully computed and returned -- Phase 2 Sec 4.8
    requires all three verdict counts, and the coverage they imply, to be
    reported "never just the ones that produced a number."

    Args:
        run_dir: Path to the run directory containing mirror_loop.jsonl
        collapse_threshold: Delta-I threshold for detecting collapse
            (unchanged Phase 1 estimator parameter)
        min_consecutive: Number of consecutive low-Delta-I steps for
            collapse (unchanged Phase 1 estimator parameter)
        n_steps: Number of intended generation steps per task (5 per
            epb/config/epb_v1.yaml -- 4 intended transitions)

    Returns:
        Dictionary with:
        - epb_phi: Overall score (0-100), or None if the verdict-bearing
          coverage floor (Sec 4.9) was not met
        - collapse_rate: collapsed_count / n_loops, or None under the same
          condition
        - verdict_bearing_eligible: True iff n_loops >=
          MIRROR_LOOP_MIN_VERDICT_BEARING_TASKS (Sec 4.9's literal floor)
        - planned_tasks: total planned task count (len of mirror_loop.jsonl)
        - collapsed_count / not_collapsed_count / censored_count: Sec 4.8's
          required task-level verdict breakdown, always all three reported
        - n_loops: collapsed_count + not_collapsed_count (Sec 4.8)
        - verdict_bearing_coverage: n_loops / planned_tasks (Sec 4.8/4.9)
        - censored_rate: censored_count / planned_tasks (Sec 4.8)
        - planned_transitions / applicable_transitions / usable_transitions:
          the transition-level evidence accounting (Sec 4.8) -- distinct
          from, and not to be confused with, the task-level verdict counts
          above
        - details: per-task diagnostic records (Sec 10)

    Raises:
        FileNotFoundError: if mirror_loop.jsonl does not exist.
        ValueError: if mirror_loop.jsonl is empty.
        (Malformed JSONL content raises json.JSONDecodeError, propagated
        unchanged -- a genuine parse failure, never a scientific
        evidence-usability condition; Phase 3A's result_adapter.py
        converts it to SCORING_ERROR, never INSUFFICIENT_EVIDENCE.)
    """
    mirror_loop_file = run_dir / "mirror_loop.jsonl"

    if not mirror_loop_file.exists():
        raise FileNotFoundError(f"Mirror loop results not found: {mirror_loop_file}")

    loops = []
    with open(mirror_loop_file, "r") as f:
        for line in f:
            loops.append(json.loads(line))

    if not loops:
        raise ValueError("No mirror loop tasks found in results")

    planned_tasks = len(loops)
    planned_transitions = planned_tasks * (n_steps - 1)

    collapsed_count = 0
    not_collapsed_count = 0
    censored_count = 0
    usable_transitions = 0
    details: List[Dict[str, Any]] = []

    for loop in loops:
        task_id = loop.get("task_id", "unknown")
        task_status = loop.get("task_status", "completed")

        if task_status == "failed":
            # A Phase 1 Area 3 orchestration-failure record: no responses
            # were ever recorded. This is the k=0 edge case of the exact
            # same frozen prefix rule, not a new rule -- zero usable
            # transitions, an incomplete (empty) prefix, no collapse
            # observed, so it lands in CENSORED like any other broken
            # chain.
            observations: List[Observation] = []
        else:
            observations = [Observation.from_dict(r) for r in loop.get("responses", [])]

        verdict_record = _task_verdict(
            observations, n_steps, collapse_threshold, min_consecutive
        )
        usable_transitions += verdict_record["n_usable_transitions"]

        verdict = verdict_record["verdict"]
        if verdict == COLLAPSED:
            collapsed_count += 1
        elif verdict == NOT_COLLAPSED:
            not_collapsed_count += 1
        else:
            censored_count += 1

        details.append({"task_id": task_id, **verdict_record})

    n_loops = collapsed_count + not_collapsed_count
    verdict_bearing_coverage = n_loops / planned_tasks if planned_tasks else 0.0
    censored_rate = censored_count / planned_tasks if planned_tasks else 0.0

    # Sec 4.9's frozen publication gate: below the literal floor, no
    # numeric epb_phi/collapse_rate is published for this run at all --
    # an all-or-nothing gate, not a partial-credit calculation, and not
    # merely a downstream QuantityResult-architecture concern (Sec 4.9's
    # own text: "no numeric epb_truth or certification value is produced
    # in either case" reads as a construct-level publication rule this
    # scorer itself must honor, so every caller -- including the legacy
    # CLI path that calls this function directly -- sees the correct
    # scientific state, not just the new Phase 3A/3B architecture path).
    eligible = n_loops >= MIRROR_LOOP_MIN_VERDICT_BEARING_TASKS
    if eligible and n_loops > 0:
        collapse_rate = collapsed_count / n_loops
        epb_phi = round(100 * (1 - collapse_rate), 2)
        collapse_rate = round(collapse_rate, 4)
    else:
        # Either the coverage floor was not met, or (n_loops == 0) no
        # ratio is even mathematically defined -- either way, no numeric
        # substitute is manufactured (this phase's governing prompt Sec
        # 9's "value-state invariant").
        collapse_rate = None
        epb_phi = None

    return {
        "epb_phi": epb_phi,
        "collapse_rate": collapse_rate,
        "verdict_bearing_eligible": eligible,
        "planned_tasks": planned_tasks,
        "collapsed_count": collapsed_count,
        "not_collapsed_count": not_collapsed_count,
        "censored_count": censored_count,
        "n_loops": n_loops,
        "verdict_bearing_coverage": round(verdict_bearing_coverage, 4),
        "censored_rate": round(censored_rate, 4),
        "planned_transitions": planned_transitions,
        "applicable_transitions": planned_transitions,
        "usable_transitions": usable_transitions,
        "details": details,
    }
