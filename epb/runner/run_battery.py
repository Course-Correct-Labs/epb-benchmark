"""Battery execution logic for EPB."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

from epb.adapters.base import ModelClient, Observation, ObservationKind, OBSERVATION_SCHEMA_VERSION

logger = logging.getLogger(__name__)


def _orchestration_failure_record(
    task_id: str,
    battery: str,
    description: str,
    error: Exception,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a persisted failure record for a task whose generation raised.

    This is the Area 3 task-level isolation boundary: a task-level
    exception (anything not already classified into an Observation inside
    an adapter -- e.g. a config/programming error, not an anticipated
    provider failure) is caught here, recorded explicitly, and the caller
    continues to the next task rather than aborting the whole battery.

    Per this phase's Sec 4.3 hard non-goal, this function only preserves
    the failure state -- it does not, and must not, decide whether the
    task counts toward any battery numerator, denominator, or coverage
    threshold. Downstream scoring code decides how (if at all) to treat a
    `task_status: "failed"` record; this function's only job is to make
    sure the failure is never silently indistinguishable from ordinary
    model output.
    """
    record: Dict[str, Any] = {
        "task_id": task_id,
        "battery": battery,
        "description": description,
        "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
        "task_status": "failed",
        "failure": {
            "kind": ObservationKind.ORCHESTRATION_ERROR.value,
            "error_type": type(error).__name__,
            # Truncated and derived from str(exception) only -- never a raw
            # provider object or environment dump, so no secret can leak
            # through this path.
            "error_message": str(error)[:500],
        },
    }
    if extra:
        record.update(extra)
    logger.error(
        "Task %s in battery %s failed and was isolated: %s: %s",
        task_id, battery, type(error).__name__, error,
    )
    return record


def _write_result(output_file: Optional[Path], result: Dict[str, Any]) -> None:
    if output_file:
        with open(output_file, "a") as f:
            f.write(json.dumps(result) + "\n")


def run_mirror_loop_battery(
    client: ModelClient,
    tasks: List[Dict[str, Any]],
    n_steps: int = 5,
    output_file: Path = None
) -> List[Dict[str, Any]]:
    """Run the Mirror Loop battery.

    Args:
        client: Model client to use
        tasks: List of mirror loop task specifications
        n_steps: Number of loop iterations
        output_file: Optional file to write results to

    Returns:
        List of results, one per task
    """
    results = []

    for task in tqdm(tasks, desc="Mirror Loop"):
        task_id = task["task_id"]
        config = task["config"]
        initial_prompt = config["initial_prompt"]
        loop_instruction = config["loop_instruction"]

        try:
            observations: List[Observation] = []

            # Step 0: Initial generation
            obs = client.generate(initial_prompt)
            observations.append(obs)
            current_response_text = obs.text

            # Steps 1 to n_steps-1: Loop iterations
            for step in range(1, n_steps):
                # Build the next prompt from the loop instruction and previous
                # response text -- unchanged from pre-Phase-1 behavior; only
                # the type carrying that text changed.
                next_prompt = f"{loop_instruction}\n\nPrevious response: {current_response_text}"
                obs = client.generate(next_prompt)
                observations.append(obs)
                current_response_text = obs.text

            result = {
                "task_id": task_id,
                "battery": "mirror_loop",
                "description": task.get("description", ""),
                "initial_prompt": initial_prompt,
                "loop_instruction": loop_instruction,
                "n_steps": n_steps,
                "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
                "task_status": "completed",
                "responses": [o.to_dict() for o in observations]
            }
        except Exception as e:
            result = _orchestration_failure_record(
                task_id=task_id,
                battery="mirror_loop",
                description=task.get("description", ""),
                error=e,
                extra={
                    "initial_prompt": initial_prompt,
                    "loop_instruction": loop_instruction,
                    "n_steps": n_steps,
                },
            )

        results.append(result)
        _write_result(output_file, result)

    return results


def run_confabulation_battery(
    client: ModelClient,
    tasks: List[Dict[str, Any]],
    challenge_prompt: str,
    output_file: Path = None
) -> List[Dict[str, Any]]:
    """Run the Confabulation battery.

    Args:
        client: Model client to use
        tasks: List of confabulation task specifications
        challenge_prompt: Standard challenge prompt to use
        output_file: Optional file to write results to

    Returns:
        List of results, one per task
    """
    results = []

    for task in tqdm(tasks, desc="Confabulation"):
        task_id = task["task_id"]
        config = task["config"]
        question = config["question"]
        unanswerable = config.get("unanswerable", False)

        try:
            # Initial answer
            initial_obs = client.generate(question)

            # Challenge
            challenged_obs = client.generate(
                challenge_prompt + f"\n\nYour previous answer: {initial_obs.text}"
            )

            result = {
                "task_id": task_id,
                "battery": "confabulation",
                "description": task.get("description", ""),
                "question": question,
                "unanswerable": unanswerable,
                "category": config.get("category", "unknown"),
                "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
                "task_status": "completed",
                "initial_answer": initial_obs.to_dict(),
                "challenged_answer": challenged_obs.to_dict(),
            }
        except Exception as e:
            result = _orchestration_failure_record(
                task_id=task_id,
                battery="confabulation",
                description=task.get("description", ""),
                error=e,
                extra={
                    "question": question,
                    "unanswerable": unanswerable,
                    "category": config.get("category", "unknown"),
                },
            )

        results.append(result)
        _write_result(output_file, result)

    return results


def run_violation_state_battery(
    client: ModelClient,
    tasks: List[Dict[str, Any]],
    output_file: Path = None
) -> List[Dict[str, Any]]:
    """Run the Violation State battery.

    Args:
        client: Model client to use
        tasks: List of violation state task specifications
        output_file: Optional file to write results to

    Returns:
        List of results, one per task
    """
    results = []

    for task in tqdm(tasks, desc="Violation State"):
        task_id = task["task_id"]
        config = task["config"]
        turn_specs = config["turns"]

        try:
            # Build conversation history
            conversation = []
            turn_results = []

            for i, turn_spec in enumerate(turn_specs):
                user_message = turn_spec["user_message"]
                is_benign = turn_spec["is_benign"]

                # Add user message to conversation
                conversation.append({"role": "user", "content": user_message})

                # Get model response
                response_obs = client.generate_chat(conversation)

                # Add assistant response to conversation -- unchanged from
                # pre-Phase-1 behavior; only the type carrying the text changed.
                conversation.append({"role": "assistant", "content": response_obs.text})

                turn_results.append({
                    "turn_index": i,
                    "user_message": user_message,
                    "is_benign": is_benign,
                    "response": response_obs.to_dict(),
                })

            result = {
                "task_id": task_id,
                "battery": "violation_state",
                "description": task.get("description", ""),
                "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
                "task_status": "completed",
                "turns": turn_results
            }
        except Exception as e:
            result = _orchestration_failure_record(
                task_id=task_id,
                battery="violation_state",
                description=task.get("description", ""),
                error=e,
            )

        results.append(result)
        _write_result(output_file, result)

    return results


def run_echo_chamber_battery(
    client: ModelClient,
    tasks: List[Dict[str, Any]],
    n_rounds: int = 5,
    output_file: Path = None
) -> List[Dict[str, Any]]:
    """Run the Echo Chamber battery.

    Args:
        client: Model client to use
        tasks: List of echo chamber task specifications
        n_rounds: Number of echo/summarization rounds
        output_file: Optional file to write results to

    Returns:
        List of results, one per task
    """
    results = []

    for task in tqdm(tasks, desc="Echo Chamber"):
        task_id = task["task_id"]
        config = task["config"]
        seed_text = config["seed_text"]
        pattern = config.get("pattern", "iterative_summary")
        instruction = config.get("instruction", "Summarize the following text concisely.")

        try:
            observations: List[Observation] = []
            current_text = seed_text

            # Run echo rounds
            for round_idx in range(n_rounds):
                if pattern == "iterative_summary":
                    # Simple iterative summarization
                    prompt = f"{instruction}\n\n{current_text}"
                    obs = client.generate(prompt)
                    observations.append(obs)
                    current_text = obs.text

                elif pattern == "multi_agent":
                    # Multi-agent pattern: summarize, then expand
                    if round_idx % 2 == 0:
                        prompt = f"{instruction}\n\n{current_text}"
                    else:
                        prompt = f"Expand on the key concepts in the following summary:\n\n{current_text}"
                    obs = client.generate(prompt)
                    observations.append(obs)
                    current_text = obs.text

            if observations:
                final_observation = observations[-1]
                intermediate_observations = observations[:-1]
            else:
                # n_rounds == 0: no generation occurred at all. Pre-Phase-1
                # behavior left final_text as the untouched seed text in
                # this case; mirror that exactly rather than fabricating an
                # EMPTY_TEXT observation for a generation that never happened.
                final_observation = Observation(text=seed_text, kind=ObservationKind.VALID_TEXT)
                intermediate_observations = []

            result = {
                "task_id": task_id,
                "battery": "echo_chamber",
                "description": task.get("description", ""),
                "pattern": pattern,
                "n_rounds": n_rounds,
                "observation_schema_version": OBSERVATION_SCHEMA_VERSION,
                "task_status": "completed",
                "initial_text": seed_text,
                "final_text": final_observation.to_dict(),
                "intermediate_texts": [o.to_dict() for o in intermediate_observations]
            }
        except Exception as e:
            result = _orchestration_failure_record(
                task_id=task_id,
                battery="echo_chamber",
                description=task.get("description", ""),
                error=e,
                extra={
                    "pattern": pattern,
                    "n_rounds": n_rounds,
                    "initial_text": seed_text,
                },
            )

        results.append(result)
        _write_result(output_file, result)

    return results
