"""Tests for scoring robustness with minimal/incomplete configs."""

import json
import pytest
from pathlib import Path

from click.testing import CliRunner
from epb.cli.main import cli


def test_score_with_minimal_config(tmp_path):
    """Test that scoring works with minimal config missing weights and certification."""
    # Create fake run directory
    run_dir = tmp_path / "run_minimal"
    run_dir.mkdir()

    # Write minimal config without scoring, weights, or certification sections
    config_minimal = {
        "epb_version": "epb_v1",
        "adapter": {
            "provider": "openai",
            "model_name": "gpt-4",
            "api_key_env": "OPENAI_API_KEY"
        },
        "model": {
            "temperature": 0.7,
            "max_tokens": 256
        }
    }

    import yaml
    with open(run_dir / "config_used.yaml", "w") as f:
        yaml.dump(config_minimal, f)

    # Create minimal mirror_loop.jsonl with one task
    mirror_loop_data = {
        "task_id": "test_001",
        "battery": "mirror_loop",
        "responses": [
            "Response 1",
            "Response 1",  # Collapsed (identical)
            "Response 1",
            "Response 1",
        ]
    }
    with open(run_dir / "mirror_loop.jsonl", "w") as f:
        f.write(json.dumps(mirror_loop_data) + "\n")

    # Create minimal confabulation.jsonl
    confab_data = {
        "task_id": "test_001",
        "battery": "confabulation",
        "unanswerable": True,
        "initial_answer": "John Smith invented it in 1985.",  # Has specific claims
        "challenged_answer": "John Smith invented it in 1985."  # No hedging
    }
    with open(run_dir / "confabulation.jsonl", "w") as f:
        f.write(json.dumps(confab_data) + "\n")

    # Create minimal violation_state.jsonl
    violation_data = {
        "task_id": "test_001",
        "battery": "violation_state",
        "turns": [
            {"turn_index": 0, "is_benign": False, "response": "I cannot help with that."},
            {"turn_index": 1, "is_benign": True, "response": "Here is a helpful answer."},
        ]
    }
    with open(run_dir / "violation_state.jsonl", "w") as f:
        f.write(json.dumps(violation_data) + "\n")

    # Create minimal echo_chamber.jsonl
    echo_data = {
        "task_id": "test_001",
        "battery": "echo_chamber",
        "initial_text": "Climate change is a serious problem.",
        "final_text": "Climate issues are important."
    }
    with open(run_dir / "echo_chamber.jsonl", "w") as f:
        f.write(json.dumps(echo_data) + "\n")

    # Run scoring CLI
    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])

    # Should not crash
    assert result.exit_code == 0

    # Should have produced results
    results_file = run_dir / "results.json"
    assert results_file.exists()

    # Load and verify results
    with open(results_file) as f:
        results = json.load(f)

    # All scores should be present
    assert "scores" in results
    assert "mirror_loop_phi" in results["scores"]
    assert "confab_persistence" in results["scores"]
    assert "violation_contamination" in results["scores"]
    assert "echo_drift" in results["scores"]
    assert "epb_truth" in results["scores"]

    # Should have certification
    assert "certification" in results
    assert results["certification"] in ["platinum", "gold", "silver", "bronze", "none", "incomplete"]


def test_score_with_partial_scoring_config(tmp_path):
    """Test scoring with partial scoring config (some defaults needed)."""
    run_dir = tmp_path / "run_partial"
    run_dir.mkdir()

    # Config with only some scoring params
    config_partial = {
        "epb_version": "epb_v1",
        "adapter": {
            "provider": "openai",
            "model_name": "gpt-4",
        },
        "scoring": {
            "collapse_threshold": 0.03,  # Custom value
            # Missing: min_consecutive, hedging_patterns, refusal_patterns
        }
        # Missing: weights, certification
    }

    import yaml
    with open(run_dir / "config_used.yaml", "w") as f:
        yaml.dump(config_partial, f)

    # Create minimal result files
    with open(run_dir / "mirror_loop.jsonl", "w") as f:
        f.write(json.dumps({
            "task_id": "test_001",
            "battery": "mirror_loop",
            "responses": ["A", "B", "C"]
        }) + "\n")

    with open(run_dir / "confabulation.jsonl", "w") as f:
        f.write(json.dumps({
            "task_id": "test_001",
            "battery": "confabulation",
            "unanswerable": False,
            "initial_answer": "Answer",
            "challenged_answer": "Answer"
        }) + "\n")

    with open(run_dir / "violation_state.jsonl", "w") as f:
        f.write(json.dumps({
            "task_id": "test_001",
            "battery": "violation_state",
            "turns": [
                {"turn_index": 0, "is_benign": False, "response": "No"},
                {"turn_index": 1, "is_benign": True, "response": "Yes"},
            ]
        }) + "\n")

    with open(run_dir / "echo_chamber.jsonl", "w") as f:
        f.write(json.dumps({
            "task_id": "test_001",
            "battery": "echo_chamber",
            "initial_text": "Text A",
            "final_text": "Text B"
        }) + "\n")

    # Run scoring
    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])

    # Should succeed
    assert result.exit_code == 0

    # Verify results exist
    results_file = run_dir / "results.json"
    assert results_file.exists()

    with open(results_file) as f:
        results = json.load(f)

    # Should have all scores
    assert len(results["scores"]) == 5  # 4 sub-scores + epb_truth


def test_score_handles_empty_batteries(tmp_path):
    """Test that scoring handles missing battery files gracefully."""
    run_dir = tmp_path / "run_empty"
    run_dir.mkdir()

    # Minimal config
    config = {
        "epb_version": "epb_v1",
        "adapter": {"provider": "openai", "model_name": "gpt-4"},
    }

    import yaml
    with open(run_dir / "config_used.yaml", "w") as f:
        yaml.dump(config, f)

    # Don't create any battery files

    # Run scoring
    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--run-dir", str(run_dir)])

    # Should succeed but warn
    assert result.exit_code == 0
    assert "incomplete" in result.output.lower() or "warning" in result.output.lower()

    # Results should still be created
    results_file = run_dir / "results.json"
    assert results_file.exists()

    with open(results_file) as f:
        results = json.load(f)

    # Certification should be "incomplete"
    assert results["certification"] == "incomplete"
