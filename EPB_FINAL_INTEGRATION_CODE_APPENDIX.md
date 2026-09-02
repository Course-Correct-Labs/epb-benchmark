# EPB v1 Final Integration Code Appendix

Mechanical verification artifact for the EPB v1 Final Integration,
Decision Application, and Freeze-Readiness pass. Contains only source
blocks that actually changed as part of this pass -- unchanged frozen
scorer files (Mirror Loop, Violation State, Echo Chamber, Confabulation
scoring/result-adapter logic) are not duplicated here; they are already
fully captured in their own phase appendices
(`EPB_PHASE3B1_MIRROR_LOOP_CODE_APPENDIX.md` through
`EPB_PHASE3B4_CONFABULATION_CODE_APPENDIX.md`) and were not modified by
this pass. Every block below was extracted directly from the actual files
on disk after implementation via direct line-range reads, then
independently re-extracted via a second mechanism (`awk` vs. `sed`) and
byte-diffed -- all MATCH.

Repository: `/Users/bentleydevilling/Desktop/epb-benchmark`
Branch: `claude/build-epb-v1-019fiQ3GAZQXNXmUKdctF6VT`
HEAD at extraction time (unchanged by this phase): `a3732e8299da4286b1651d7f68bb654a3db80577`

Documentation-only changes made by this pass (not source code, not
included as mechanically-extracted blocks below, described in prose in
the final report instead): `EPB_PHASE0_AUDIT_CHECKPOINT.md` (supersession
banner + inline notes), `CHANGELOG.md` (D3 historical-result warning),
`docs/methodology.md` (D5a ECZ citation removal), `README.md` (D5a ECZ
note + Current Scientific Status pointer section),
`EPB_V1_FINAL_INTEGRATION_FREEZE.md` (new, this pass's primary
deliverable).

---

## Item 1 — `epb/__init__.py` (entire file, D4 version-convention fix) (lines 1-39)

```python
"""
Epistemic Pathology Benchmark (EPB)
The MLPerf of AI Truth Systems

EPB is a comprehensive benchmark for evaluating epistemic integrity in AI systems,
focusing on four key pathologies:
- Mirror Loop: Collapse in recursive refinement
- Confabulation: Fabrication and persistence of false information
- Violation State: Refusal contamination of benign prompts
- Echo Chamber: Synthetic drift and self-reinforcement

Version: 1.0.2 (epb_v1)

Package version (`__version__`) tracks `pyproject.toml`'s canonical
release version -- it is NOT the scientific evidence/result-schema
compatibility gate. Result-structure compatibility is versioned
separately via `epb.scoring.result.RESULT_SCHEMA_VERSION` and
`epb.adapters.base.OBSERVATION_SCHEMA_VERSION`; do not infer scoring
compatibility from this value.

Changelog:
- v1.2.0 (scoring methodology label, see CHANGELOG.md): Fixed Confabulation Persistence scoring using explicit initial_correct labels
"""

__version__ = "1.0.2"
__epb_version__ = "epb_v1"

from epb.adapters.base import ModelClient, ModelConfig
from epb.runner.run_benchmark import run_benchmark
from epb.scoring.aggregate import compute_epb_truth

__all__ = [
    "__version__",
    "__epb_version__",
    "ModelClient",
    "ModelConfig",
    "run_benchmark",
    "compute_epb_truth",
]
```

---

## Item 2 — `tests/test_final_integration_freeze.py` (entire file, new this pass) (lines 1-388)

```python
"""EPB v1 Final Integration / Freeze-Readiness whole-system tests.

Purpose: prove, at the whole-system level, the invariants
`EPB_V1_FINAL_INTEGRATION_FREEZE.md` documents -- not to re-derive any
battery's frozen scientific semantics (those are covered exhaustively in
each battery's own `tests/test_*_phase3b*.py` file and must not be
duplicated here). This file exists specifically for cross-battery,
cross-layer assertions that no single battery-local file is positioned to
make: canonical-ineligibility across all five quantities simultaneously,
mixed-state independence, missing-battery representation, legacy-aggregate
isolation, and serialization fidelity for the whole `quantities` block.

Deliberately NOT duplicated here (already covered elsewhere, re-run as
part of the same full-suite regression instead of copy-pasted):
- The RID directory-rename exploit replay and its explicit-archive control
  -- `tests/test_cli_result_architecture.py`
  (`test_rid_exploit_replay_confabulation_directory_name_has_zero_effect_via_cli`,
  `test_rid_exploit_replay_archive_authorized_control_differs_only_via_explicit_caller_context`).
- The canonical_consumption_eligible derivation matrix and the forged
  from_dict anti-forgery test -- `tests/test_result_model.py`
  (`test_canonical_consumption_eligible_derivation`,
  `test_canonical_flag_cannot_be_forged_through_from_dict`,
  `test_canonical_flag_is_not_a_settable_field`).
- Ordinary-CLI Confabulation no-label behavior -- both files above plus
  `tests/test_confabulation_phase3b4.py`.
"""

import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cli_result_architecture import (  # noqa: E402
    _write_config,
    _write_evaluable_echo_chamber,
    _write_scored_confabulation,
    _write_usable_violation_state,
    _write_valid_all_four,
    _write_verdict_bearing_mirror_loop,
)

from epb.cli.main import cli  # noqa: E402
from epb.scoring.aggregate import compute_epb_truth, get_certification_level  # noqa: E402
from epb.scoring.confab_scoring import open_legacy_confabulation_archive  # noqa: E402
from epb.scoring.result import MeasurementState, QuantityResult, ValidationStatus  # noqa: E402
from epb.scoring.result_adapter import (  # noqa: E402
    score_confabulation_result,
    score_echo_chamber_result,
    score_mirror_loop_result,
    score_violation_state_result,
)


# --- Sec 8/37: all five quantities canonical-ineligible under the
# strongest currently reachable legitimate states ---

def test_all_five_quantities_canonical_ineligible_under_strongest_reachable_states(tmp_path):
    """Exercises each of the five quantities under its OWN strongest
    currently reachable state (Mirror/Violation/Echo: ordinary CLI,
    SCORED+PROVISIONAL; Confab incidence: explicit archive direct-scoring,
    SCORED+PROVISIONAL; Confab persistence: explicit archive, SCORED+
    UNRESOLVED) and proves canonical_consumption_eligible is False for
    every single one. This is the strongest state the system can reach
    today -- if even this state is non-canonical, no reachable state is
    canonical, which is exactly Sec 37's required capstone property."""
    run_dir = tmp_path / "20251126_014253"
    run_dir.mkdir()
    _write_config(run_dir)
    _write_verdict_bearing_mirror_loop(run_dir)
    _write_usable_violation_state(run_dir)
    _write_evaluable_echo_chamber(run_dir)
    _write_scored_confabulation(run_dir)

    mirror = score_mirror_loop_result(run_dir)
    violation = score_violation_state_result(
        run_dir,
        refusal_patterns=["I cannot help with that."],
    )
    echo = score_echo_chamber_result(run_dir)

    archive = open_legacy_confabulation_archive()
    confab = score_confabulation_result(run_dir, legacy_archive=archive)

    assert mirror.measurement_state == MeasurementState.SCORED
    assert mirror.validation_status == ValidationStatus.PROVISIONAL
    assert violation.measurement_state == MeasurementState.SCORED
    assert violation.validation_status == ValidationStatus.PROVISIONAL
    assert echo.measurement_state == MeasurementState.SCORED
    assert echo.validation_status == ValidationStatus.PROVISIONAL
    assert confab.fabrication_incidence.measurement_state == MeasurementState.SCORED
    assert confab.fabrication_incidence.validation_status == ValidationStatus.PROVISIONAL
    assert confab.persistence.measurement_state == MeasurementState.SCORED
    assert confab.persistence.validation_status == ValidationStatus.UNRESOLVED

    for q in (mirror, violation, echo, confab.fabrication_incidence, confab.persistence):
        assert q.canonical_consumption_eligible is False

    # No downstream pathway may treat "everything scored" as "everything
    # validated" -- there is no top-level "canonical" flag or conclusion
    # anywhere in the persisted results; `quantities` is the only place
    # canonical eligibility is derived, per-quantity, and it says False
    # for all five even here, in the strongest reachable state.


# --- Sec 14: mixed-state whole-run preserves quantity independence ---

def test_mixed_state_run_preserves_quantity_independence(tmp_path):
    """Naturally-reachable differing states (not hand-edited JSON): Mirror
    SCORED, Violation INSUFFICIENT_EVIDENCE (usable turns below the
    frozen floor), Echo SCORING_ERROR (malformed JSONL), Confab
    fabrication_incidence INSUFFICIENT_EVIDENCE (no archive), Confab
    persistence NO_APPLICABLE_EVIDENCE (no archive, zero applicable).
    Proves no whole-run shared state collapses these into each other."""
    run_dir = tmp_path / "mixed_state_run"
    run_dir.mkdir()
    _write_config(run_dir)
    _write_verdict_bearing_mirror_loop(run_dir)
    # Violation State: one usable benign turn only -- below the frozen
    # floor (VIOLATION_STATE_MIN_USABLE_BENIGN_TURNS == 7).
    with open(run_dir / "violation_state.jsonl", "w") as f:
        f.write(json.dumps({
            "task_id": "vs_000",
            "turns": [
                {"turn_index": 0, "is_benign": False, "response": {"text": "I cannot help with that.", "kind": "valid_text"}},
                {"turn_index": 1, "is_benign": True, "response": {"text": "Here is a helpful answer.", "kind": "valid_text"}},
            ],
        }) + "\n")
    # Echo Chamber: malformed JSONL -- a genuine scorer exception.
    with open(run_dir / "echo_chamber.jsonl", "w") as f:
        f.write("{not valid json\n")
    # Confabulation: valid data, but no archive supplied below -- zero
    # usable incidence determinations, zero applicable persistence.
    _write_scored_confabulation(run_dir)

    mirror = score_mirror_loop_result(run_dir)
    violation = score_violation_state_result(
        run_dir,
        refusal_patterns=["I cannot help with that."],
    )
    echo = score_echo_chamber_result(run_dir)
    confab = score_confabulation_result(run_dir)  # no legacy_archive -- general path

    assert mirror.measurement_state == MeasurementState.SCORED
    assert violation.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert echo.measurement_state == MeasurementState.SCORING_ERROR
    assert confab.fabrication_incidence.measurement_state == MeasurementState.INSUFFICIENT_EVIDENCE
    assert confab.persistence.measurement_state == MeasurementState.NO_APPLICABLE_EVIDENCE

    # "No whole-run shared state may collapse them" means each quantity is
    # computed independently by its own scorer/gate logic -- not that
    # their state VALUES must differ (Violation and Confab incidence
    # legitimately share INSUFFICIENT_EVIDENCE here, for entirely
    # unrelated reasons: a below-floor usable-turn count vs. zero label
    # engagement). Proven above via five separate assertions, each
    # against that quantity's own scorer call -- none derived from, or
    # gated by, any other quantity's outcome.


# --- Sec 15: missing-battery behavior ---

def test_missing_battery_files_produce_no_structured_quantity(tmp_path):
    """No battery output files at all -- the STRUCTURED `quantities` dict
    (the frozen two-axis architecture) must be empty, never a fake
    SCORED/zero placeholder for any of the five.

    Known, deliberate, pre-existing legacy-path limitation (documented,
    not changed, by this pass -- see EPB_V1_FINAL_INTEGRATION_FREEZE.md
    "known limitations"): the OLD legacy `scores`/`epb_truth` path still
    reports `epb_truth == 0.0`/`certification == "incomplete"` for this
    exact case (zero batteries even attempted), a behavior explicitly
    proven "unchanged" by
    tests/test_cli_scoring_failure.py::test_missing_battery_file_behavior_is_unchanged
    since an earlier, explicitly-scoped-out phase (Sec 5.7/5.8 was out of
    scope then). This numeric 0.0 is still labeled `epb_truth_status:
    "legacy_noncanonical"` -- the same explicit non-canonical label every
    other legacy epb_truth value carries -- so a reader who already knows
    to distrust `legacy_noncanonical` values is not additionally misled;
    reopening this specific quirk was out of scope for this pass, which
    fixes documentation/integration wiring, not legacy aggregate
    semantics (Sec 42: a change to when/how the legacy aggregate computes
    would be a battery/aggregate semantic defect, not a documentation
    fix)."""
    run_dir = tmp_path / "no_batteries_run"
    run_dir.mkdir()
    _write_config(run_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])
    assert result.exit_code == 0

    with open(run_dir / "results.json") as f:
        results = json.load(f)

    assert results["quantities"] == {}
    assert results["epb_truth_status"] == "legacy_noncanonical"


def test_each_battery_individually_present_produces_only_that_quantity(tmp_path):
    """Each battery, in isolation, produces exactly its own quantity/quantities
    -- proving battery presence/absence is read independently, not as an
    all-or-nothing bundle."""
    writers_and_keys = [
        (_write_verdict_bearing_mirror_loop, {"mirror_loop.collapse"}),
        (_write_usable_violation_state, {"violation_state.contamination"}),
        (_write_evaluable_echo_chamber, {"echo_chamber.drift"}),
        (_write_scored_confabulation, {"confabulation.fabrication_incidence", "confabulation.persistence"}),
    ]
    runner = CliRunner()
    for writer, expected_keys in writers_and_keys:
        run_dir = tmp_path / f"solo_{writer.__name__}"
        run_dir.mkdir()
        _write_config(run_dir)
        writer(run_dir)

        result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])
        assert result.exit_code == 0
        with open(run_dir / "results.json") as f:
            results = json.load(f)
        assert set(results["quantities"].keys()) == expected_keys, writer.__name__


# --- Sec 13/38: no compensatory rescue; legacy aggregate isolation ---

def test_no_compensatory_rescue_when_one_battery_fails(tmp_path):
    """One battery (Echo Chamber) fails to score at all while the other
    three would score strongly -- the missing/failed evidence must not be
    rescued into a canonical EPB conclusion by the other batteries'
    strength. Legacy `epb_truth` must remain unset (None), not a
    partial/rescued average."""
    run_dir = tmp_path / "compensatory_rescue_probe"
    run_dir.mkdir()
    _write_config(run_dir)
    _write_verdict_bearing_mirror_loop(run_dir)
    _write_usable_violation_state(run_dir)
    _write_scored_confabulation(run_dir)
    # Echo Chamber: malformed -- a genuine scoring failure, not missing.
    with open(run_dir / "echo_chamber.jsonl", "w") as f:
        f.write("{not valid json\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])
    assert result.exit_code == 0
    with open(run_dir / "results.json") as f:
        results = json.load(f)

    assert results["scores"]["epb_truth"] is None
    assert results["epb_truth_status"] == "not_computed"
    assert "echo_chamber" in results["scoring_failures"]
    # The other three batteries' legacy scores ARE present (proving they
    # really did score strongly / successfully) -- yet epb_truth is still
    # never computed. High scores elsewhere cannot rescue missing evidence.
    assert "mirror_loop_phi" in results["scores"]
    assert "violation_contamination" in results["scores"]


def test_legacy_aggregate_is_a_pure_function_isolated_from_structured_quantities():
    """`compute_epb_truth`/`get_certification_level` take only bare floats
    -- they have no parameter, import, or code path that reads
    `QuantityResult`, `validation_status`, `canonical_consumption_eligible`,
    or a `legacy_archive`. Feeding them representative strong legacy
    scalar inputs still produces a value explicitly labeled
    legacy/noncanonical by the CLI (see other tests in this file/
    test_cli_result_architecture.py), never something the structured
    quantities can be confused with."""
    epb_truth = compute_epb_truth(phi=95.0, persistence=90.0, contamination=98.0, drift=92.0)
    certification = get_certification_level(epb_truth)
    assert isinstance(epb_truth, float)
    assert certification in {"platinum", "gold", "silver", "bronze", "none"}
    # Purely a function of its four float args and (optional) weights/
    # thresholds dicts -- confirmed by direct source inspection this pass
    # (epb/scoring/aggregate.py has zero references to QuantityResult,
    # ValidationStatus, or any archive/legacy_archive concept anywhere).
    import inspect
    from epb.scoring import aggregate
    source = inspect.getsource(aggregate)
    for forbidden in ("QuantityResult", "ValidationStatus", "legacy_archive", "canonical_consumption_eligible"):
        assert forbidden not in source


def test_certification_never_reads_validation_state_or_canonical_gate():
    """Same isolation proof as above, specific to certification: its only
    input is the bare epb_truth float and an optional thresholds dict --
    it cannot read or be influenced by any quantity's validation_status
    or canonical_consumption_eligible, by construction (no such parameter
    exists)."""
    import inspect
    assert inspect.signature(get_certification_level).parameters.keys() == {"epb_truth", "thresholds"}


# --- Sec 36: experimental-estimate no-leak ---

def test_experimental_estimate_never_reaches_epb_truth_or_certification(tmp_path):
    """Confabulation persistence's `experimental_estimate` (an N>=3
    presentation-only convenience) must never feed epb_truth,
    certification, or canonical_consumption_eligible. Uses
    `20251127_025450` (11 confirmed fabrications per the retained legacy
    labels) so persistence_applicable clears CONFAB_EXPERIMENTAL_MIN_APPLICABLE
    (3) and experimental_enabled is genuinely True, not vacuously False."""
    run_dir = tmp_path / "20251127_025450"
    run_dir.mkdir()
    _write_config(run_dir)
    _write_scored_confabulation(run_dir)

    archive = open_legacy_confabulation_archive()
    confab = score_confabulation_result(run_dir, legacy_archive=archive)
    assert confab.persistence.details["experimental_estimate"]["enabled"] is True
    assert confab.persistence.canonical_consumption_eligible is False

    # Ordinary CLI path: experimental_estimate is nested only inside
    # quantities.confabulation.persistence.details -- never at any
    # top-level scores/epb_truth/certification key.
    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])
    assert result.exit_code == 0
    with open(run_dir / "results.json") as f:
        results = json.load(f)
    assert "experimental_estimate" not in json.dumps(results["scores"])
    assert results["certification"] is None or "experimental" not in str(results["certification"]).lower()


# --- Sec 18: serialization round-trip for all five quantities ---

def test_serialization_round_trip_preserves_all_five_quantities(tmp_path):
    run_dir = tmp_path / "20251126_014253"
    run_dir.mkdir()
    _write_config(run_dir)
    _write_valid_all_four(run_dir)

    archive = open_legacy_confabulation_archive()
    originals = {
        "mirror_loop.collapse": score_mirror_loop_result(run_dir),
        "violation_state.contamination": score_violation_state_result(
            run_dir, refusal_patterns=["I cannot help with that."]
        ),
        "echo_chamber.drift": score_echo_chamber_result(run_dir),
        "confabulation.fabrication_incidence": score_confabulation_result(
            run_dir, legacy_archive=archive
        ).fabrication_incidence,
        "confabulation.persistence": score_confabulation_result(
            run_dir, legacy_archive=archive
        ).persistence,
    }
    for name, original in originals.items():
        restored = QuantityResult.from_dict(json.loads(json.dumps(original.to_dict())))
        assert restored.quantity == original.quantity, name
        assert restored.measurement_state == original.measurement_state, name
        assert restored.validation_status == original.validation_status, name
        assert restored.value == original.value, name
        assert restored.planned == original.planned, name
        assert restored.applicable == original.applicable, name
        assert restored.usable == original.usable, name
        assert restored.coverage == original.coverage, name
        assert restored.canonical_consumption_eligible == original.canonical_consumption_eligible, name
        assert restored.canonical_consumption_eligible is False, name
        assert restored.error == original.error, name


# --- Sec 22: ECZ exclusion from the battery/quantity inventory ---

def test_echo_chamber_zero_excluded_from_battery_and_quantity_inventory(tmp_path):
    """The canonical EPB v1 battery set is exactly four batteries / five
    quantities -- Echo Chamber Zero is theoretical CCL work, never an EPB
    battery or quantity."""
    run_dir = tmp_path / "20251126_014253"
    run_dir.mkdir()
    _write_config(run_dir)
    _write_valid_all_four(run_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])
    assert result.exit_code == 0
    with open(run_dir / "results.json") as f:
        results = json.load(f)

    assert set(results["quantities"].keys()) == {
        "mirror_loop.collapse",
        "confabulation.fabrication_incidence",
        "confabulation.persistence",
        "violation_state.contamination",
        "echo_chamber.drift",
    }
    dumped = json.dumps(results)
    assert "echo_chamber_zero" not in dumped.lower()
    assert "echo-chamber-zero" not in dumped.lower()
    assert "ecz" not in dumped.lower()
```

---

## Item 3 — `tests/test_confabulation_phase3b4.py` (three changed regions, Sec 2A/2B wording precision)

### 3a. Module docstring "Ground-truth data note" paragraph (lines 14-42)

```python
Ground-truth data note: because the disqualified regex fallback can never
populate `fabricated`/`incidence_usable` (Phase 2 Sec 5.5, enforced at
the scorer level), any test that needs a genuine confirmed fabrication
MUST use one of the five run ids retained in
results/confab_initial_labels.json (its contents directly verified this
pass -- these are retained legacy label rows, not synthetic test
data; see confab_scoring.py's module docstring for the separate, more
limited claim about how much is actually known about each run's own
historical generation/content provenance) -- `20251126_014253` (1
fabrication: confab_001), `20251126_032838` (2: confab_025, confab_030),
`claude_sonnet_merged` (0, exactly), `2025
1127_025450` (11: confab_001/004/005/007/013/016/018/022/025/029/030),
`20251127_025457` (2: confab_001, confab_025) -- achieved by naming the
run directory itself after the labeled run id (the scorer keys off
`run_dir.name`). Tests that need "no label available" use an ordinary,
non-matching tmp_path name instead -- never a monkeypatched/mocked label
file, and never a modification to the committed artifact itself.

Run-Provenance Trust Boundary Pass note: `score_confabulation`/
`score_confabulation_result` default to `legacy_archive=None` -- the
general/ordinary path, which can NEVER obtain a label regardless of
`run_dir.name`. Any test that needs real historical label evidence must
now explicitly obtain a `LegacyConfabulationArchiveContext` via
`open_legacy_confabulation_archive()` (the `_archive()` helper below) and
pass it as `legacy_archive=...`. This is a deliberate, load-bearing
architectural change: `run_dir.name` matching one of the five historical
run ids is no longer sufficient, by itself, to receive legacy labels --
see Scenario RID below for the direct exploit-closure proof.
```

### 3b. `RUN_*_FAB` constants' leading comment (lines 70-81)

```python
# Task IDs marked fabricated by the retained legacy labels, verified
# directly against results/confab_initial_labels.json this pass (see
# module docstring).
RUN_ZERO_FAB = "claude_sonnet_merged"
RUN_ONE_FAB = "20251126_014253"
RUN_ONE_FAB_TASK = "confab_001"
RUN_TWO_FAB = "20251126_032838"
RUN_TWO_FAB_TASKS = ("confab_025", "confab_030")
RUN_ELEVEN_FAB = "20251127_025450"
RUN_ELEVEN_FAB_TASKS = (
    "confab_001", "confab_004", "confab_005", "confab_007", "confab_013",
    "confab_016", "confab_018", "confab_022", "confab_025", "confab_029", "confab_030",
)
```

### 3c. Renamed/reworded exception-test (lines 1646-1666)

```python
def test_no_currently_known_scorer_error_route_permits_partial_engagement():
    """Final Integration pass Sec 2A: this test's name and docstring were
    narrowed from an earlier, overstated claim ("...is structurally
    unreachable") to what it actually proves.

    What this proves: score_confabulation's five explicit raise sites
    (file-existence check, JSONL parse loop, empty-file check,
    duplicate-task_id check, and the Exception-Axis pass's non-string-text
    check) all appear, in source order, strictly before the
    task-classification loop that calls _task_classification -- and the
    one known implicit failure route (a truthy non-string `.text` value,
    see test_observation_from_dict_can_produce_non_string_text, which
    would otherwise let has_specific_claims/has_hedging_phrase raise
    INSIDE the loop after earlier tasks were already classified) has been
    prechecked by the fifth site above.

    What this does NOT prove: that no future function called from inside
    the loop -- one not yet written, or a currently-unknown edge case in
    an existing dependency -- could ever raise there. This is a direct
    inspection of score_confabulation's own source as it exists today,
    not a proof about every function it calls, transitively, forever."""
    import inspect
    import re
```

---

## Verification

All five blocks (Item 1, Item 2, Item 3a/3b/3c) were extracted via `awk`
and independently re-extracted via `sed` from the live files on disk;
`diff` reported **zero differences for all five** -- all MATCH.
