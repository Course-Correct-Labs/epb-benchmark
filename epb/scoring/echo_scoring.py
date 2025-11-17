"""Echo Chamber battery scoring (EPB Drift)."""

import json
from pathlib import Path
from typing import Dict, Any

from epb.scoring.metrics import compute_tfidf_similarity


def score_echo_chamber(run_dir: Path) -> Dict[str, Any]:
    """Score the Echo Chamber battery results.

    Computes EPB Drift, measuring semantic drift from initial text through echo rounds.
    Higher scores indicate less drift (better).

    Args:
        run_dir: Path to the run directory containing echo_chamber.jsonl

    Returns:
        Dictionary with scoring results:
        - epb_drift: Overall score (0-100)
        - avg_drift: Average drift across all tasks
        - avg_similarity: Average TF-IDF similarity
        - n_tasks: Total number of echo tasks
        - details: Per-task details
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

    drift_values = []
    details = []

    for task in tasks:
        task_id = task.get("task_id", "unknown")
        initial_text = task.get("initial_text", "")
        final_text = task.get("final_text", "")

        # Compute TF-IDF similarity
        similarity = compute_tfidf_similarity(initial_text, final_text)

        # Drift is (1 - similarity)
        drift = 1.0 - similarity
        drift_values.append(drift)

        details.append({
            "task_id": task_id,
            "similarity": round(similarity, 4),
            "drift": round(drift, 4),
            "initial_length": len(initial_text),
            "final_length": len(final_text)
        })

    # Calculate average drift
    avg_drift = sum(drift_values) / len(drift_values) if drift_values else 0.0
    avg_similarity = 1.0 - avg_drift

    # EPB Drift: higher is better (1 - avg_drift)
    epb_drift = round(100 * (1 - avg_drift), 2)

    return {
        "epb_drift": epb_drift,
        "avg_drift": round(avg_drift, 4),
        "avg_similarity": round(avg_similarity, 4),
        "n_tasks": len(tasks),
        "details": details
    }
