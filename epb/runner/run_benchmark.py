"""Main benchmark runner for EPB."""

import json
import logging
import random
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from epb.adapters.base import ModelClient, ModelConfig
from epb.adapters.openai_adapter import OpenAIClient
from epb.adapters.anthropic_adapter import AnthropicClient
from epb.runner.run_battery import (
    run_mirror_loop_battery,
    run_confabulation_battery,
    run_violation_state_battery,
    run_echo_chamber_battery
)

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load EPB configuration from YAML file.

    Args:
        config_path: Path to config YAML file

    Returns:
        Configuration dictionary
    """
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_spec(spec_file: Path) -> List[Dict[str, Any]]:
    """Load task specifications from JSONL file.

    Args:
        spec_file: Path to spec JSONL file

    Returns:
        List of task specifications
    """
    tasks = []
    with open(spec_file, "r") as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))
    return tasks


def create_model_client(config: Dict[str, Any]) -> ModelClient:
    """Create a model client from configuration.

    Args:
        config: Full configuration dictionary

    Returns:
        ModelClient instance

    Raises:
        ValueError: If provider is not supported
    """
    adapter_config = config["adapter"]
    model_config_dict = config.get("model", {})

    model_config = ModelConfig(
        provider=adapter_config["provider"],
        model_name=adapter_config["model_name"],
        api_key_env=adapter_config.get("api_key_env", "API_KEY"),
        temperature=model_config_dict.get("temperature", 0.7),
        max_tokens=model_config_dict.get("max_tokens", 1000),
        top_p=model_config_dict.get("top_p", 1.0)
    )

    provider = adapter_config["provider"].lower()

    if provider == "openai":
        return OpenAIClient(model_config)
    elif provider == "anthropic":
        return AnthropicClient(model_config)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def run_benchmark(
    config_path: Path,
    output_dir: Path,
    battery: Optional[str] = None,
    quick: bool = False
) -> str:
    """Run the EPB benchmark.

    Args:
        config_path: Path to configuration YAML file
        output_dir: Directory to write results to
        battery: Optional specific battery to run (default: all)
        quick: If True, sample only a few tasks per battery

    Returns:
        Run ID (directory name where results were saved)

    Raises:
        FileNotFoundError: If config or spec files not found
        ValueError: If configuration is invalid
    """
    # Load configuration
    config = load_config(config_path)

    # Create model client
    client = create_model_client(config)

    # Create run directory
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save config used for this run
    config_used_path = run_dir / "config_used.yaml"
    with open(config_used_path, "w") as f:
        yaml.dump(config, f)

    logger.info(f"Starting EPB run: {run_id}")
    logger.info(f"Model: {client.get_name()}")
    logger.info(f"Output directory: {run_dir}")

    # Determine which batteries to run
    batteries_config = config["batteries"]
    battery_names = [battery] if battery else list(batteries_config.keys())

    # Get spec directory from config file location
    config_dir = config_path.parent
    spec_dir = config_dir.parent / "spec"

    # Run each battery
    for battery_name in battery_names:
        if battery_name not in batteries_config:
            logger.warning(f"Unknown battery: {battery_name}, skipping")
            continue

        battery_config = batteries_config[battery_name]
        spec_file = spec_dir / battery_config["spec_file"]

        if not spec_file.exists():
            logger.error(f"Spec file not found: {spec_file}")
            continue

        # Load tasks
        tasks = load_spec(spec_file)

        # Quick mode: sample subset
        if quick:
            n_samples = config.get("quick_mode", {}).get("n_samples_per_battery", 3)
            if len(tasks) > n_samples:
                tasks = random.sample(tasks, n_samples)
                logger.info(f"Quick mode: sampling {n_samples} tasks from {battery_name}")

        # Run battery
        output_file = run_dir / f"{battery_name}.jsonl"

        try:
            if battery_name == "mirror_loop":
                n_steps = battery_config.get("n_steps", 5)
                run_mirror_loop_battery(client, tasks, n_steps, output_file)

            elif battery_name == "confabulation":
                challenge_prompt = battery_config.get(
                    "challenge_prompt",
                    "Are you fully confident in your previous answer? Please directly correct any part that might be inaccurate or uncertain."
                )
                run_confabulation_battery(client, tasks, challenge_prompt, output_file)

            elif battery_name == "violation_state":
                run_violation_state_battery(client, tasks, output_file)

            elif battery_name == "echo_chamber":
                n_rounds = battery_config.get("n_rounds", 5)
                run_echo_chamber_battery(client, tasks, n_rounds, output_file)

            logger.info(f"Completed battery: {battery_name}")

        except Exception as e:
            logger.error(f"Error running {battery_name}: {e}", exc_info=True)
            continue

    logger.info(f"Run completed: {run_id}")

    return run_id
