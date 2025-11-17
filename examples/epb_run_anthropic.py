#!/usr/bin/env python3
"""
Example script for running EPB with Anthropic Claude models.

This script demonstrates how to:
1. Configure for Anthropic
2. Run a specific battery
3. Score and analyze results

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/epb_run_anthropic.py
"""

import os
import sys
import yaml
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from epb.runner.run_benchmark import run_benchmark
from epb.scoring.mirror_loop_scoring import score_mirror_loop
from epb.scoring.confab_scoring import score_confabulation
from epb.scoring.violation_scoring import score_violation_state
from epb.scoring.echo_scoring import score_echo_chamber
from epb.scoring.aggregate import compute_epb_truth, get_certification_level


def main():
    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    # Paths
    package_dir = Path(__file__).parent.parent
    config_path = package_dir / "epb" / "config" / "epb_v1.yaml"
    output_dir = Path("runs_anthropic")

    print("=" * 60)
    print("EPB Example: Anthropic Claude")
    print("=" * 60)

    # Create modified config for Anthropic
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Modify for Anthropic
    config["adapter"]["provider"] = "anthropic"
    config["adapter"]["model_name"] = "claude-3-5-sonnet-20241022"
    config["adapter"]["api_key_env"] = "ANTHROPIC_API_KEY"

    # Save temporary config
    temp_config = Path("temp_anthropic_config.yaml")
    with open(temp_config, "w") as f:
        yaml.dump(config, f)

    # Run benchmark
    print("\n[1/2] Running benchmark (quick mode)...")
    print(f"Model: {config['adapter']['model_name']}")
    print(f"Output: {output_dir}")
    print("\nRunning all batteries with sampled tasks...\n")

    try:
        run_id = run_benchmark(
            config_path=temp_config,
            output_dir=output_dir,
            battery=None,
            quick=True  # Quick mode
        )
    except Exception as e:
        print(f"\nError running benchmark: {e}")
        temp_config.unlink()  # Clean up
        sys.exit(1)
    finally:
        # Clean up temp config
        if temp_config.exists():
            temp_config.unlink()

    run_dir = output_dir / run_id

    print(f"\n✓ Run completed: {run_id}")

    # Score results
    print("\n[2/2] Scoring results...")

    try:
        scores = {}
        details = {}

        # Score each battery
        if (run_dir / "mirror_loop.jsonl").exists():
            ml_result = score_mirror_loop(run_dir)
            scores["mirror_loop_phi"] = ml_result["epb_phi"]
            details["mirror_loop"] = ml_result
            print(f"  Mirror Loop: {ml_result['epb_phi']}")

        if (run_dir / "confabulation.jsonl").exists():
            cf_result = score_confabulation(
                run_dir,
                hedging_patterns=config["scoring"]["confabulation"]["hedging_patterns"]
            )
            scores["confab_persistence"] = cf_result["epb_persistence"]
            details["confabulation"] = cf_result
            print(f"  Confabulation: {cf_result['epb_persistence']}")

        if (run_dir / "violation_state.jsonl").exists():
            vs_result = score_violation_state(
                run_dir,
                refusal_patterns=config["scoring"]["violation_state"]["refusal_patterns"]
            )
            scores["violation_contamination"] = vs_result["epb_contamination"]
            details["violation_state"] = vs_result
            print(f"  Violation State: {vs_result['epb_contamination']}")

        if (run_dir / "echo_chamber.jsonl").exists():
            ec_result = score_echo_chamber(run_dir)
            scores["echo_drift"] = ec_result["epb_drift"]
            details["echo_chamber"] = ec_result
            print(f"  Echo Chamber: {ec_result['epb_drift']}")

        # Compute overall score
        if len(scores) == 4:
            epb_truth = compute_epb_truth(
                phi=scores["mirror_loop_phi"],
                persistence=scores["confab_persistence"],
                contamination=scores["violation_contamination"],
                drift=scores["echo_drift"],
                weights=config["weights"]
            )
            certification = get_certification_level(epb_truth, config["certification"])

            print("\n" + "=" * 60)
            print(f"EPB TRUTH SCORE: {epb_truth}")
            print(f"Certification: {certification.upper()}")
            print("=" * 60)

            # Per-battery analysis
            print("\nDetailed Analysis:")
            print(f"\n1. Mirror Loop:")
            print(f"   - Score: {details['mirror_loop']['epb_phi']}")
            print(f"   - Collapse rate: {details['mirror_loop']['collapse_rate'] * 100:.1f}%")
            print(f"   - Collapsed: {details['mirror_loop']['n_collapsed']}/{details['mirror_loop']['n_loops']}")

            print(f"\n2. Confabulation:")
            print(f"   - Score: {details['confabulation']['epb_persistence']}")
            print(f"   - Persistence rate: {details['confabulation']['persistence_rate'] * 100:.1f}%")
            print(f"   - Fabrications: {details['confabulation']['fabrication_count']}")

            print(f"\n3. Violation State:")
            print(f"   - Score: {details['violation_state']['epb_contamination']}")
            print(f"   - Contamination rate: {details['violation_state']['contamination_rate'] * 100:.1f}%")
            print(f"   - Contaminated: {details['violation_state']['contaminated_benign_turns']}/{details['violation_state']['total_benign_turns']}")

            print(f"\n4. Echo Chamber:")
            print(f"   - Score: {details['echo_chamber']['epb_drift']}")
            print(f"   - Average drift: {details['echo_chamber']['avg_drift'] * 100:.1f}%")
            print(f"   - Average similarity: {details['echo_chamber']['avg_similarity'] * 100:.1f}%")

        else:
            print("\nWarning: Not all batteries completed")

        print(f"\nResults directory: {run_dir}")

    except Exception as e:
        print(f"\nError scoring results: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n✓ Example completed successfully!")


if __name__ == "__main__":
    main()
