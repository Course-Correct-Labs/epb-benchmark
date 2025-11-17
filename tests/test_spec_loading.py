"""Tests for loading and validating spec files."""

import json
from pathlib import Path

import pytest


def test_mirror_loop_spec_exists():
    """Test that mirror loop spec file exists."""
    spec_file = Path("epb/spec/mirror_loop_v1.jsonl")
    assert spec_file.exists(), "Mirror loop spec file not found"


def test_mirror_loop_spec_valid():
    """Test that mirror loop spec is valid JSONL."""
    spec_file = Path("epb/spec/mirror_loop_v1.jsonl")
    tasks = []

    with open(spec_file, "r") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    task = json.loads(line)
                    tasks.append(task)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON at line {line_num}: {e}")

    assert len(tasks) == 20, f"Expected 20 tasks, found {len(tasks)}"

    # Validate structure
    for task in tasks:
        assert "task_id" in task
        assert "battery" in task
        assert task["battery"] == "mirror_loop"
        assert "description" in task
        assert "config" in task
        assert "initial_prompt" in task["config"]
        assert "loop_instruction" in task["config"]


def test_confabulation_spec_valid():
    """Test that confabulation spec is valid."""
    spec_file = Path("epb/spec/confabulation_v1.jsonl")
    tasks = []

    with open(spec_file, "r") as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))

    assert len(tasks) == 30, f"Expected 30 tasks, found {len(tasks)}"

    # Check for unanswerable tasks
    unanswerable_count = sum(1 for t in tasks if t["config"].get("unanswerable", False))
    assert unanswerable_count > 0, "Should have some unanswerable tasks"

    # Validate structure
    for task in tasks:
        assert "task_id" in task
        assert "battery" in task
        assert task["battery"] == "confabulation"
        assert "config" in task
        assert "question" in task["config"]
        assert "unanswerable" in task["config"]


def test_violation_state_spec_valid():
    """Test that violation state spec is valid."""
    spec_file = Path("epb/spec/violation_state_v1.jsonl")
    tasks = []

    with open(spec_file, "r") as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))

    assert len(tasks) == 10, f"Expected 10 tasks, found {len(tasks)}"

    # Validate structure
    for task in tasks:
        assert "task_id" in task
        assert "battery" in task
        assert task["battery"] == "violation_state"
        assert "config" in task
        assert "turns" in task["config"]

        turns = task["config"]["turns"]
        assert len(turns) >= 2, "Should have at least 2 turns"

        # First turn should be violation (not benign)
        assert not turns[0]["is_benign"], "First turn should be violation"

        # Later turns should include benign ones
        benign_count = sum(1 for t in turns if t["is_benign"])
        assert benign_count > 0, "Should have benign turns"


def test_echo_chamber_spec_valid():
    """Test that echo chamber spec is valid."""
    spec_file = Path("epb/spec/echo_chamber_v1.jsonl")
    tasks = []

    with open(spec_file, "r") as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))

    assert len(tasks) == 10, f"Expected 10 tasks, found {len(tasks)}"

    # Validate structure
    for task in tasks:
        assert "task_id" in task
        assert "battery" in task
        assert task["battery"] == "echo_chamber"
        assert "config" in task
        assert "seed_text" in task["config"]
        assert "pattern" in task["config"]
        assert task["config"]["pattern"] in ["iterative_summary", "multi_agent"]


def test_task_id_uniqueness():
    """Test that all task IDs are unique across all specs."""
    all_task_ids = []

    spec_files = [
        "epb/spec/mirror_loop_v1.jsonl",
        "epb/spec/confabulation_v1.jsonl",
        "epb/spec/violation_state_v1.jsonl",
        "epb/spec/echo_chamber_v1.jsonl"
    ]

    for spec_file in spec_files:
        with open(spec_file, "r") as f:
            for line in f:
                if line.strip():
                    task = json.loads(line)
                    all_task_ids.append(task["task_id"])

    assert len(all_task_ids) == len(set(all_task_ids)), "Task IDs must be unique"


def test_total_task_count():
    """Test that total task count is 70."""
    spec_files = [
        "epb/spec/mirror_loop_v1.jsonl",
        "epb/spec/confabulation_v1.jsonl",
        "epb/spec/violation_state_v1.jsonl",
        "epb/spec/echo_chamber_v1.jsonl"
    ]

    total_tasks = 0
    for spec_file in spec_files:
        with open(spec_file, "r") as f:
            for line in f:
                if line.strip():
                    total_tasks += 1

    assert total_tasks == 70, f"Expected 70 total tasks, found {total_tasks}"
