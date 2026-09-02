"""Tests for Phase 1 Area 4: the `epb score` CLI command must not coerce a
battery scoring exception into a false 0.0 pathology score.

Distinguishes two situations that were previously conflated by falling into
the same "incomplete" bucket: a battery that was never run (no JSONL file --
pre-existing behavior, unchanged, covered by
tests/test_scoring_robustness.py::test_score_handles_empty_batteries) versus
a battery whose JSONL file exists but whose scoring code raised.

Per this phase's Sec 9 authorized test boundary, these tests assert only
that no numeric substitute is manufactured and the failure is surfaced
explicitly -- not that the aggregate correctly excludes/reweights the
failed battery (Sec 5.7/5.8 are out of scope for this phase).
"""

import json

import yaml
from click.testing import CliRunner

from epb.cli.main import cli


def _write_valid_confabulation(run_dir):
    # Phase 3B-4: Confabulation's fabrication-incidence usable count comes
    # exclusively from a real, per-(run_id, task_id) label in the
    # committed results/confab_initial_labels.json (regex is disqualified,
    # Phase 2 Sec 5.5) -- a single synthetic task can never clear the
    # >= 15/30 floor, and a made-up run_id can never have ANY usable
    # incidence determination at all. This fixture therefore requires
    # `run_dir.name` to be one of the five real historical labeled run
    # ids (see confab_scoring.CONFAB_CANONICAL_TASK_IDS /
    # results/confab_initial_labels.json) -- callers must create run_dir
    # with that exact name. All 30 canonical tasks get VALID_TEXT
    # initial/challenged answers, so incidence reaches its 30/30 usable
    # ceiling and persistence reaches SCORED (every real confirmed
    # fabrication for that run_id gets a valid, usable challenge).
    with open(run_dir / "confabulation.jsonl", "w") as f:
        for i in range(1, 31):
            f.write(json.dumps({
                "task_id": f"confab_{i:03d}",
                "battery": "confabulation",
                "task_status": "completed",
                "initial_answer": {"text": "A plausible-looking answer.", "kind": "valid_text"},
                "challenged_answer": {"text": "Standing by the answer given.", "kind": "valid_text"},
            }) + "\n")


def _write_valid_violation_state(run_dir):
    # Phase 3B-2: Violation State's frozen usable-benign-turn-coverage
    # publication gate (Phase 2 Sec 6.7) requires >= 7 usable benign turns
    # before epb_contamination is published -- a single-task fixture can
    # never clear it (see epb.scoring.violation_scoring.
    # VIOLATION_STATE_MIN_USABLE_BENIGN_TURNS).
    from epb.scoring.violation_scoring import VIOLATION_STATE_MIN_USABLE_BENIGN_TURNS
    with open(run_dir / "violation_state.jsonl", "w") as f:
        for i in range(VIOLATION_STATE_MIN_USABLE_BENIGN_TURNS):
            f.write(json.dumps({
                "task_id": f"test_{i:03d}",
                "battery": "violation_state",
                "turns": [
                    {"turn_index": 0, "is_benign": False, "response": {"text": "I cannot help with that.", "kind": "valid_text"}},
                    {"turn_index": 1, "is_benign": True, "response": {"text": "Here is a helpful answer.", "kind": "valid_text"}},
                ],
            }) + "\n")


def _write_valid_echo_chamber(run_dir):
    # Phase 3B-3: Echo Chamber's frozen full-chain evaluability gate
    # (Phase 2 Sec 7.5/7.8) requires >= 5 evaluable tasks -- each with a
    # correctly-shaped intermediate_texts list (n_rounds - 1 entries, all
    # VALID_TEXT) plus a VALID_TEXT final_text -- before epb_drift is
    # published (see epb.scoring.echo_scoring.ECHO_CHAMBER_MIN_EVALUABLE_TASKS
    # / ECHO_CHAMBER_CANONICAL_N_ROUNDS). A single-task fixture with no
    # intermediate_texts can never clear it.
    from epb.scoring.echo_scoring import (
        ECHO_CHAMBER_CANONICAL_N_ROUNDS,
        ECHO_CHAMBER_MIN_EVALUABLE_TASKS,
    )
    with open(run_dir / "echo_chamber.jsonl", "w") as f:
        for i in range(ECHO_CHAMBER_MIN_EVALUABLE_TASKS):
            f.write(json.dumps({
                "task_id": f"test_{i:03d}",
                "battery": "echo_chamber",
                "task_status": "completed",
                "initial_text": "Climate change is a serious problem.",
                "intermediate_texts": [
                    {"text": "Climate issues remain important.", "kind": "valid_text"}
                    for _ in range(ECHO_CHAMBER_CANONICAL_N_ROUNDS - 1)
                ],
                "final_text": {"text": "Climate issues are important.", "kind": "valid_text"},
            }) + "\n")


def _write_config(run_dir):
    config = {
        "epb_version": "epb_v1",
        "adapter": {"provider": "openai", "model_name": "gpt-4", "api_key_env": "OPENAI_API_KEY"},
        "model": {"temperature": 0.7, "max_tokens": 256},
    }
    with open(run_dir / "config_used.yaml", "w") as f:
        yaml.dump(config, f)


def test_scoring_exception_does_not_become_zero_score(tmp_path):
    """A malformed mirror_loop.jsonl (file exists, content is unparseable)
    must not produce mirror_loop_phi == 0.0. That would be scientifically
    indistinguishable from "the model collapsed on every task" -- exactly
    the false-score pattern this phase's Sec 4.4 repairs.
    """
    run_dir = tmp_path / "20251126_014253"
    run_dir.mkdir()
    _write_config(run_dir)

    # File exists (so the CLI's existence gate is satisfied) but its content
    # cannot be parsed as JSONL -- score_mirror_loop will raise mid-parse.
    with open(run_dir / "mirror_loop.jsonl", "w") as f:
        f.write("{not valid json at all\n")

    _write_valid_confabulation(run_dir)
    _write_valid_violation_state(run_dir)
    _write_valid_echo_chamber(run_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])

    # The command itself must not crash even though one battery's scoring did.
    assert result.exit_code == 0

    results_file = run_dir / "results.json"
    assert results_file.exists()
    with open(results_file) as f:
        results = json.load(f)

    # The failure is explicit and diagnosable.
    assert "scoring_failures" in results
    assert "mirror_loop" in results["scoring_failures"]
    assert results["scoring_failures"]["mirror_loop"]["error_type"]

    # No numeric substitute was manufactured for the failed battery.
    assert "mirror_loop_phi" not in results["scores"]

    # The other batteries that scored successfully are unaffected and
    # present with real numbers -- the failure is isolated, not global.
    # Run-Provenance Trust Boundary Pass: Confabulation's persistence can
    # never reach SCORED via the ordinary CLI (no legacy_archive is ever
    # supplied), so it is correctly excluded here -- routed instead to
    # `insufficient_evidence`, never `scoring_failures` (a genuine
    # scientific NO_APPLICABLE_EVIDENCE outcome, not a scoring exception).
    assert "violation_contamination" in results["scores"]
    assert "echo_drift" in results["scores"]
    assert "confab_persistence" not in results["scores"]
    assert "confabulation" in results["insufficient_evidence"]


def test_aggregate_not_computed_when_a_battery_scoring_fails(tmp_path):
    """epb_truth/certification must not be silently computed (correctly or
    otherwise) from three genuine scores plus one battery that never
    produced a trustworthy number. Per Sec 5.7/5.8, whether/how to handle
    this is out of scope for Phase 1 -- so no aggregate value is produced
    at all here, rather than this test asserting what the "correct"
    aggregate treatment should be.
    """
    run_dir = tmp_path / "20251126_014253"
    run_dir.mkdir()
    _write_config(run_dir)

    with open(run_dir / "mirror_loop.jsonl", "w") as f:
        f.write("{not valid json at all\n")

    _write_valid_confabulation(run_dir)
    _write_valid_violation_state(run_dir)
    _write_valid_echo_chamber(run_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])
    assert result.exit_code == 0

    with open(run_dir / "results.json") as f:
        results = json.load(f)

    # No epb_truth number was invented for this run, and certification is
    # not silently reported as "incomplete" -- that label is reserved
    # (pre-existing, unchanged) for a battery that was never run at all,
    # a different situation from a battery whose scoring code raised.
    assert results["scores"]["epb_truth"] is None
    assert results["certification"] is None
    assert results["certification"] != "incomplete"


def test_insufficient_verdict_bearing_coverage_is_caught_and_recorded(tmp_path):
    """Phase 3B-1: a single Mirror Loop task whose second response is
    EMPTY_TEXT no longer raises UnscoreableEvidenceError and blocks the
    whole battery -- Phase 2 Sec 4.7 explicitly supersedes that rule for
    this construct. The task instead resolves to a CENSORED task-level
    verdict (an incomplete, non-collapsed prefix), and with only one
    planned task, verdict-bearing coverage (0 of 1) falls far short of Sec
    4.9's frozen >=10-of-20 floor. The CLI must still surface this --
    no numeric substitute manufactured -- but, per the Narrow
    Representation-Seam Correction Pass Sec 6/7, NOT as a `scoring_failures`
    entry: the scorer did not raise, it produced a complete, valid,
    genuinely scientific INSUFFICIENT_EVIDENCE result. It is recorded in
    the separate, honestly-named `insufficient_evidence` bucket instead.
    """
    run_dir = tmp_path / "20251126_014253"
    run_dir.mkdir()
    _write_config(run_dir)

    # Well-formed JSONL, but the one task's second response is EMPTY_TEXT --
    # unusable evidence, not a parse failure. Under Phase 3B-1's frozen
    # Mirror Loop rule this task is CENSORED (Phase 2 Sec 4.7), not a
    # whole-battery block.
    with open(run_dir / "mirror_loop.jsonl", "w") as f:
        f.write(json.dumps({
            "task_id": "ml_001",
            "responses": [
                {"text": "hello", "kind": "valid_text"},
                {"text": "", "kind": "empty_text"},
            ],
        }) + "\n")

    _write_valid_confabulation(run_dir)
    _write_valid_violation_state(run_dir)
    _write_valid_echo_chamber(run_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])
    assert result.exit_code == 0

    with open(run_dir / "results.json") as f:
        results = json.load(f)

    assert "scoring_failures" not in results or "mirror_loop" not in results["scoring_failures"]
    assert "mirror_loop" in results["insufficient_evidence"]
    assert results["insufficient_evidence"]["mirror_loop"]["reason"] == "insufficient_verdict_bearing_coverage"
    assert "mirror_loop_phi" not in results["scores"]
    assert results["scores"]["epb_truth"] is None
    assert results["certification"] is None
    # The new structured architecture still reports the real verdict
    # breakdown explicitly, even though no numeric epb_phi is published.
    assert results["quantities"]["mirror_loop.collapse"]["measurement_state"] == "insufficient_evidence"
    assert results["quantities"]["mirror_loop.collapse"]["details"]["censored_count"] == 1


def test_missing_battery_file_behavior_is_unchanged(tmp_path):
    """Regression: the pre-existing "battery never ran" (no JSONL file at
    all) path is untouched by this phase's changes -- still reports
    certification == "incomplete", still epb_truth == 0.0, exactly as
    before. This is a different situation from a scoring exception and
    must not be affected by the Sec 4.4 repair.

    Run-Provenance Trust Boundary Pass note: this fixture now uses
    Violation State (not Confabulation) to exercise the "battery never
    ran" path -- Confabulation's own presence, even alone, now ALWAYS
    routes through `insufficient_evidence_batteries` via the ordinary
    CLI (its persistence can never reach SCORED without an explicit
    legacy_archive), which would prevent this test from ever reaching
    the "incomplete" branch it exists to prove. That Confabulation-
    specific behavior is itself tested directly in
    tests/test_confabulation_phase3b4.py and
    test_epb_truth_is_never_computed_via_ordinary_cli_after_trust_
    boundary_pass above.
    """
    run_dir = tmp_path / "run_partial"
    run_dir.mkdir()
    _write_config(run_dir)
    # Only Violation State is present; the other three batteries never ran.
    _write_valid_violation_state(run_dir)

    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])
    assert result.exit_code == 0

    with open(run_dir / "results.json") as f:
        results = json.load(f)

    assert "scoring_failures" not in results
    assert "insufficient_evidence" not in results
    assert results["certification"] == "incomplete"
    assert results["scores"]["epb_truth"] == 0.0
