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
from epb.runner.run_benchmark import run_benchmark
from epb.scoring.mirror_loop_scoring import score_mirror_loop
from epb.scoring.confab_scoring import score_confabulation
from epb.scoring.violation_scoring import score_violation_state
from epb.scoring.echo_scoring import score_echo_chamber
from epb.scoring.aggregate import compute_epb_truth, get_certification_level

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__epb_version__, prog_name="epb")
def cli():
    """EPB: Epistemic Pathology Benchmark - The MLPerf of AI Truth Systems."""
    pass


@cli.command()
@click.option(
    "--output",
    type=click.Path(),
    default="epb_config.yaml",
    help="Output path for config file"
)
def init_config(output):
    """Initialize a sample EPB configuration file."""
    # Get the package directory
    package_dir = Path(__file__).parent.parent
    default_config = package_dir / "config" / "epb_v1.yaml"

    if not default_config.exists():
        click.echo(f"Error: Default config not found at {default_config}", err=True)
        sys.exit(1)

    output_path = Path(output)

    if output_path.exists():
        if not click.confirm(f"{output} already exists. Overwrite?"):
            click.echo("Aborted.")
            return

    shutil.copy(default_config, output_path)
    click.echo(f"Created config file: {output_path}")
    click.echo("\nNext steps:")
    click.echo("1. Edit the config file to set your model and API key")
    click.echo("2. Run: epb run --config epb_config.yaml")


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Path to EPB config YAML file"
)
@click.option(
    "--output",
    type=click.Path(),
    default="runs",
    help="Output directory for run results"
)
@click.option(
    "--battery",
    type=click.Choice(["mirror_loop", "confabulation", "violation_state", "echo_chamber"]),
    help="Run only a specific battery (default: all)"
)
@click.option(
    "--quick",
    is_flag=True,
    help="Quick mode: sample only a few tasks per battery"
)
def run(config, output, battery, quick):
    """Run the EPB benchmark."""
    config_path = Path(config)
    output_dir = Path(output)

    click.echo(f"EPB Version: {__epb_version__}")
    click.echo(f"Config: {config_path}")
    click.echo(f"Output: {output_dir}")

    if quick:
        click.echo("Mode: QUICK (sampling subset of tasks)")

    if battery:
        click.echo(f"Battery: {battery} only")

    try:
        run_id = run_benchmark(
            config_path=config_path,
            output_dir=output_dir,
            battery=battery,
            quick=quick
        )
        click.echo(f"\n✓ Run completed successfully!")
        click.echo(f"Run ID: {run_id}")
        click.echo(f"Results saved to: {output_dir / run_id}")
        click.echo(f"\nNext: epb score --run-dir {output_dir / run_id}")

    except Exception as e:
        click.echo(f"Error running benchmark: {e}", err=True)
        logger.exception("Benchmark run failed")
        sys.exit(1)


@cli.command()
@click.option(
    "--run-dir",
    type=click.Path(exists=True),
    required=True,
    help="Path to run directory containing results"
)
@click.option(
    "--output",
    type=click.Path(),
    help="Output path for results JSON (default: <run-dir>/results.json)"
)
def score(run_dir, output):
    """Score EPB benchmark results."""
    run_path = Path(run_dir)

    # Load config used for the run
    config_path = run_path / "config_used.yaml"
    if not config_path.exists():
        click.echo(f"Error: config_used.yaml not found in {run_path}", err=True)
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    click.echo(f"Scoring run: {run_path.name}")

    scores = {}
    details = {}

    # Score Mirror Loop
    if (run_path / "mirror_loop.jsonl").exists():
        click.echo("Scoring Mirror Loop...")
        try:
            ml_config = config["scoring"]["mirror_loop"]
            ml_result = score_mirror_loop(
                run_path,
                collapse_threshold=ml_config["collapse_threshold"],
                min_consecutive=ml_config["min_consecutive"]
            )
            scores["mirror_loop_phi"] = ml_result["epb_phi"]
            details["mirror_loop"] = ml_result
            click.echo(f"  EPB Phi: {ml_result['epb_phi']}")
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            scores["mirror_loop_phi"] = 0.0

    # Score Confabulation
    if (run_path / "confabulation.jsonl").exists():
        click.echo("Scoring Confabulation...")
        try:
            cf_config = config["scoring"]["confabulation"]
            cf_result = score_confabulation(
                run_path,
                hedging_patterns=cf_config["hedging_patterns"]
            )
            scores["confab_persistence"] = cf_result["epb_persistence"]
            details["confabulation"] = cf_result
            click.echo(f"  EPB Persistence: {cf_result['epb_persistence']}")
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            scores["confab_persistence"] = 0.0

    # Score Violation State
    if (run_path / "violation_state.jsonl").exists():
        click.echo("Scoring Violation State...")
        try:
            vs_config = config["scoring"]["violation_state"]
            vs_result = score_violation_state(
                run_path,
                refusal_patterns=vs_config["refusal_patterns"]
            )
            scores["violation_contamination"] = vs_result["epb_contamination"]
            details["violation_state"] = vs_result
            click.echo(f"  EPB Contamination: {vs_result['epb_contamination']}")
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            scores["violation_contamination"] = 0.0

    # Score Echo Chamber
    if (run_path / "echo_chamber.jsonl").exists():
        click.echo("Scoring Echo Chamber...")
        try:
            ec_result = score_echo_chamber(run_path)
            scores["echo_drift"] = ec_result["epb_drift"]
            details["echo_chamber"] = ec_result
            click.echo(f"  EPB Drift: {ec_result['epb_drift']}")
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            scores["echo_drift"] = 0.0

    # Compute aggregate score
    if len(scores) == 4:
        weights = config["weights"]
        epb_truth = compute_epb_truth(
            phi=scores.get("mirror_loop_phi", 0.0),
            persistence=scores.get("confab_persistence", 0.0),
            contamination=scores.get("violation_contamination", 0.0),
            drift=scores.get("echo_drift", 0.0),
            weights=weights
        )
        certification = get_certification_level(epb_truth, config["certification"])

        click.echo(f"\n{'='*50}")
        click.echo(f"EPB TRUTH SCORE: {epb_truth}")
        click.echo(f"Certification: {certification.upper()}")
        click.echo(f"{'='*50}")
    else:
        epb_truth = 0.0
        certification = "incomplete"
        click.echo("\nWarning: Not all batteries completed. Cannot compute EPB Truth.", err=True)

    # Build results
    results = {
        "epb_version": __epb_version__,
        "model_name": config["adapter"]["model_name"],
        "provider": config["adapter"]["provider"],
        "run_id": run_path.name,
        "scores": {
            **scores,
            "epb_truth": epb_truth
        },
        "certification": certification,
        "metadata": {
            "run_date": run_path.name.split("_")[0] if "_" in run_path.name else "unknown",
            "config": config
        },
        "details": details
    }

    # Save results
    if output:
        output_path = Path(output)
    else:
        output_path = run_path / "results.json"

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    click.echo(f"\nResults saved to: {output_path}")


@cli.command()
@click.option(
    "--results",
    type=click.Path(exists=True),
    required=True,
    help="Path to results JSON file"
)
@click.option(
    "--url",
    envvar="EPB_LEADERBOARD_URL",
    help="Leaderboard API URL (or set EPB_LEADERBOARD_URL env var)"
)
@click.option(
    "--api-key",
    envvar="EPB_API_KEY",
    help="API key for leaderboard (or set EPB_API_KEY env var)"
)
def submit(results, url, api_key):
    """Submit results to the EPB leaderboard."""
    if not url:
        click.echo("Error: Leaderboard URL not provided. Use --url or set EPB_LEADERBOARD_URL", err=True)
        sys.exit(1)

    if not api_key:
        click.echo("Error: API key not provided. Use --api-key or set EPB_API_KEY", err=True)
        sys.exit(1)

    # Load results
    with open(results, "r") as f:
        results_data = json.load(f)

    click.echo(f"Submitting to: {url}")
    click.echo(f"Model: {results_data['model_name']}")
    click.echo(f"EPB Truth: {results_data['scores']['epb_truth']}")

    try:
        import requests

        response = requests.post(
            f"{url}/submissions",
            json=results_data,
            headers={"X-API-Key": api_key}
        )

        if response.status_code == 200 or response.status_code == 201:
            click.echo("✓ Submission successful!")
            result = response.json()
            if "id" in result:
                click.echo(f"Submission ID: {result['id']}")
        else:
            click.echo(f"Error: {response.status_code} - {response.text}", err=True)
            sys.exit(1)

    except ImportError:
        click.echo("Error: requests library not installed. Install with: pip install requests", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error submitting: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
