"""Tests for Phase 1 Area 3: task-level exception isolation in the four
battery runners.

Before Phase 1, `run_benchmark.py` caught exceptions only at the
whole-battery level (Checkpoint Sec 4 D4): one task raising mid-battery
silently dropped every remaining task in that battery, with the failure
never persisted anywhere. These tests prove the new behavior: a task-level
failure is caught, persisted as an explicit, distinguishable failure
record, and execution continues to later tasks in the same battery.

Per this phase's Sec 4.3 hard non-goal, these tests assert only that the
failure is preserved and distinguishable -- not whether it should count
toward any battery numerator/denominator (that remains an open semantic
decision for a later phase).
"""

import json

import pytest

from epb.adapters.base import Observation, ObservationKind
from epb.runner.run_battery import (
    run_mirror_loop_battery,
    run_confabulation_battery,
    run_violation_state_battery,
    run_echo_chamber_battery,
)


def _valid_obs(text="ok"):
    return Observation(text=text, kind=ObservationKind.VALID_TEXT, finish_reason="stop")


class _SequencedClient:
    """A minimal ModelClient-shaped stand-in whose `generate`/`generate_chat`
    calls are driven by a fixed sequence of return values or exceptions to
    raise, in order. Deliberately not unittest.mock.Mock: Mock's
    auto-attribute behavior can mask bugs where code accidentally reads an
    unexpected attribute off the return value instead of failing loudly.
    """

    def __init__(self, sequence):
        self._sequence = list(sequence)
        self.calls = 0

    def _next(self):
        item = self._sequence[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item

    def generate(self, prompt, system_prompt=None, **kwargs):
        return self._next()

    def generate_chat(self, turns, system_prompt=None, **kwargs):
        return self._next()

    def get_name(self):
        return "test-model"


def test_mirror_loop_task_failure_isolated_and_execution_continues():
    client = _SequencedClient([
        RuntimeError("boom"),                 # task 1, step 0 -> raises
        _valid_obs("r1"), _valid_obs("r2"),    # task 2, steps 0-1 (n_steps=2)
    ])
    tasks = [
        {"task_id": "ml_001", "description": "t1", "config": {"initial_prompt": "p1", "loop_instruction": "i1"}},
        {"task_id": "ml_002", "description": "t2", "config": {"initial_prompt": "p2", "loop_instruction": "i2"}},
    ]

    results = run_mirror_loop_battery(client, tasks, n_steps=2)

    assert len(results) == 2  # neither task was silently dropped

    failed, ok = results[0], results[1]
    assert failed["task_id"] == "ml_001"
    assert failed["task_status"] == "failed"
    assert failed["failure"]["kind"] == ObservationKind.ORCHESTRATION_ERROR.value
    assert failed["failure"]["error_type"] == "RuntimeError"
    assert "responses" not in failed  # no fabricated model output stands in for the failure

    assert ok["task_id"] == "ml_002"
    assert ok["task_status"] == "completed"
    assert [r["text"] for r in ok["responses"]] == ["r1", "r2"]

    # Execution genuinely continued to the second task's calls.
    assert client.calls == 3


def test_confabulation_task_failure_isolated_and_execution_continues():
    client = _SequencedClient([
        RuntimeError("boom"),                                  # task 1 initial_answer -> raises
        _valid_obs("initial answer"), _valid_obs("challenge answer"),  # task 2
    ])
    tasks = [
        {"task_id": "confab_001", "description": "t1", "config": {"question": "q1", "unanswerable": True, "category": "c"}},
        {"task_id": "confab_002", "description": "t2", "config": {"question": "q2", "unanswerable": False, "category": "c"}},
    ]

    results = run_confabulation_battery(client, tasks, challenge_prompt="Are you sure?")

    assert len(results) == 2
    assert results[0]["task_status"] == "failed"
    assert results[0]["failure"]["error_type"] == "RuntimeError"
    assert "initial_answer" not in results[0]
    assert "challenged_answer" not in results[0]

    assert results[1]["task_status"] == "completed"
    assert results[1]["initial_answer"]["text"] == "initial answer"
    assert results[1]["challenged_answer"]["text"] == "challenge answer"
    assert client.calls == 3


def test_violation_state_task_failure_isolated_and_execution_continues():
    client = _SequencedClient([
        RuntimeError("boom"),                     # task 1, turn 0 -> raises
        _valid_obs("resp1"), _valid_obs("resp2"),  # task 2, 2 turns
    ])
    tasks = [
        {"task_id": "vs_001", "description": "t1", "config": {"turns": [{"user_message": "bad", "is_benign": False}]}},
        {"task_id": "vs_002", "description": "t2", "config": {"turns": [
            {"user_message": "bad", "is_benign": False},
            {"user_message": "good", "is_benign": True},
        ]}},
    ]

    results = run_violation_state_battery(client, tasks)

    assert len(results) == 2
    assert results[0]["task_status"] == "failed"
    assert results[0]["failure"]["error_type"] == "RuntimeError"
    assert "turns" not in results[0]

    assert results[1]["task_status"] == "completed"
    assert len(results[1]["turns"]) == 2
    assert results[1]["turns"][1]["response"]["text"] == "resp2"
    assert client.calls == 3


def test_echo_chamber_task_failure_isolated_and_execution_continues():
    client = _SequencedClient([
        RuntimeError("boom"),                            # task 1, round 0 -> raises
        _valid_obs("summary1"), _valid_obs("summary2"),   # task 2, 2 rounds
    ])
    tasks = [
        {"task_id": "echo_001", "description": "t1", "config": {"seed_text": "seed1", "pattern": "iterative_summary"}},
        {"task_id": "echo_002", "description": "t2", "config": {"seed_text": "seed2", "pattern": "iterative_summary"}},
    ]

    results = run_echo_chamber_battery(client, tasks, n_rounds=2)

    assert len(results) == 2
    assert results[0]["task_status"] == "failed"
    assert results[0]["failure"]["error_type"] == "RuntimeError"
    assert "final_text" not in results[0]
    # Task-spec fields already known before the failure are still preserved.
    assert results[0]["initial_text"] == "seed1"

    assert results[1]["task_status"] == "completed"
    assert results[1]["final_text"]["text"] == "summary2"
    assert client.calls == 3


def test_failure_record_is_persisted_to_output_file(tmp_path):
    """A task-level failure is written to the JSONL output file, not just
    returned in-memory -- the whole point of Sec 4.3's provenance
    requirement is that it survives to the persisted artifact.
    """
    client = _SequencedClient([RuntimeError("boom")])
    tasks = [
        {"task_id": "ml_001", "description": "t1", "config": {"initial_prompt": "p1", "loop_instruction": "i1"}},
    ]
    output_file = tmp_path / "mirror_loop.jsonl"

    run_mirror_loop_battery(client, tasks, n_steps=3, output_file=output_file)

    lines = output_file.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["task_status"] == "failed"
    assert record["failure"]["error_type"] == "RuntimeError"


def test_mirror_loop_scoring_censors_a_failed_task_rather_than_silently_excluding_it(tmp_path):
    """End-to-end, Phase 3B-1: a battery run containing one failed task and
    one genuine task must NOT silently score only the genuine task, and
    must NOT silently drop the failed task from any count -- Phase 2 Sec
    4.7 explicitly supersedes Phase 1's whole-battery UnscoreableEvidenceError
    block for this construct (a single task's evidence no longer blocks the
    entire battery). Instead, the failed task resolves to its own
    CENSORED task-level verdict (the k=0 edge case of the same frozen
    longest-unbroken-valid-prefix rule, Sec 4.6/4.7), explicitly counted in
    `censored_count` and `planned_tasks`, while the genuine task still
    receives its own real verdict -- proving neither task's evidence was
    silently excluded from any denominator.
    """
    from epb.scoring.mirror_loop_scoring import score_mirror_loop

    client = _SequencedClient([
        RuntimeError("boom"),
        _valid_obs("a"), _valid_obs("a"), _valid_obs("a"),
    ])
    tasks = [
        {"task_id": "ml_001", "description": "t1", "config": {"initial_prompt": "p1", "loop_instruction": "i1"}},
        {"task_id": "ml_002", "description": "t2", "config": {"initial_prompt": "p2", "loop_instruction": "i2"}},
    ]
    output_file = tmp_path / "mirror_loop.jsonl"
    run_mirror_loop_battery(client, tasks, n_steps=3, output_file=output_file)

    result = score_mirror_loop(tmp_path, n_steps=3)

    assert result["planned_tasks"] == 2
    assert result["censored_count"] == 1
    assert result["not_collapsed_count"] == 1
    assert result["collapsed_count"] == 0
    # planned == collapsed + not_collapsed + censored (this phase's
    # governing prompt Sec 6's required invariant).
    assert result["planned_tasks"] == (
        result["collapsed_count"] + result["not_collapsed_count"] + result["censored_count"]
    )

    by_task_id = {d["task_id"]: d for d in result["details"]}
    assert by_task_id["ml_001"]["verdict"] == "censored"
    assert by_task_id["ml_002"]["verdict"] == "not_collapsed"
    # The genuine task's evidence was not silently excluded -- it
    # contributed a real verdict, inspectable in the per-task diagnostics.
    assert by_task_id["ml_002"]["prefix_complete"] is True
