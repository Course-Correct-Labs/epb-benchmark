"""Mirror Loop battery scoring (EPB Phi)."""

import json
from pathlib import Path
from typing import Dict, List, Any

from epb.scoring.metrics import compute_delta_i, detect_collapse


def score_mirror_loop(
    run_dir: Path,
    collapse_threshold: float = 0.05,
    min_consecutive: int = 3
) -> Dict[str, Any]:
    """Score the Mirror Loop battery results.

    Computes EPB Phi, the metric for mirror loop stability.
    Higher scores indicate less collapse (better).

    Args:
        run_dir: Path to the run directory containing mirror_loop.jsonl
        collapse_threshold: ΔI threshold for detecting collapse
        min_consecutive: Number of consecutive low-ΔI steps for collapse

    Returns:
        Dictionary with scoring results:
        - epb_phi: Overall score (0-100)
        - collapse_rate: Fraction of loops that collapsed
        - n_loops: Total number of loops evaluated
        - n_collapsed: Number of collapsed loops
        - details: Per-task details
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

    n_collapsed = 0
    details = []

    for loop in loops:
        task_id = loop.get("task_id", "unknown")
        responses = loop.get("responses", [])

        if len(responses) < 2:
            # Not enough responses to compute deltas
            continue

        # Compute ΔI for each consecutive pair
        delta_sequence = []
        for i in range(1, len(responses)):
            prev_text = responses[i - 1]
            curr_text = responses[i]
            delta = compute_delta_i(prev_text, curr_text)
            delta_sequence.append(delta)

        # Check for collapse
        collapsed = detect_collapse(
            delta_sequence,
            threshold=collapse_threshold,
            min_consecutive=min_consecutive
        )

        if collapsed:
            n_collapsed += 1

        details.append({
            "task_id": task_id,
            "collapsed": collapsed,
            "delta_sequence": delta_sequence,
            "n_steps": len(responses)
        })

    n_loops = len(details)
    collapse_rate = n_collapsed / n_loops if n_loops > 0 else 0.0

    # EPB Phi: higher is better (1 - collapse_rate)
    epb_phi = round(100 * (1 - collapse_rate), 2)

    return {
        "epb_phi": epb_phi,
        "collapse_rate": round(collapse_rate, 4),
        "n_loops": n_loops,
        "n_collapsed": n_collapsed,
        "details": details
    }
