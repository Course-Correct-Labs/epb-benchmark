"""Battery execution logic for EPB."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

from epb.adapters.base import ModelClient

logger = logging.getLogger(__name__)


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

        responses = []
        current_prompt = initial_prompt

        # Step 0: Initial generation
        response = client.generate(current_prompt)
        responses.append(response)

        # Steps 1 to n_steps-1: Loop iterations
        for step in range(1, n_steps):
            # Build the next prompt from the loop instruction and previous response
            next_prompt = f"{loop_instruction}\n\nPrevious response: {response}"
            response = client.generate(next_prompt)
            responses.append(response)

        result = {
            "task_id": task_id,
            "battery": "mirror_loop",
            "description": task.get("description", ""),
            "initial_prompt": initial_prompt,
            "loop_instruction": loop_instruction,
            "n_steps": n_steps,
            "responses": responses
        }

        results.append(result)

        if output_file:
            with open(output_file, "a") as f:
                f.write(json.dumps(result) + "\n")

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

        # Initial answer
        initial_answer = client.generate(question)

        # Challenge
        challenged_answer = client.generate(challenge_prompt + f"\n\nYour previous answer: {initial_answer}")

        result = {
            "task_id": task_id,
            "battery": "confabulation",
            "description": task.get("description", ""),
            "question": question,
            "unanswerable": unanswerable,
            "category": config.get("category", "unknown"),
            "initial_answer": initial_answer,
            "challenged_answer": challenged_answer
        }

        results.append(result)

        if output_file:
            with open(output_file, "a") as f:
                f.write(json.dumps(result) + "\n")

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

        # Build conversation history
        conversation = []
        turn_results = []

        for i, turn_spec in enumerate(turn_specs):
            user_message = turn_spec["user_message"]
            is_benign = turn_spec["is_benign"]

            # Add user message to conversation
            conversation.append({"role": "user", "content": user_message})

            # Get model response
            response = client.generate_chat(conversation)

            # Add assistant response to conversation
            conversation.append({"role": "assistant", "content": response})

            turn_results.append({
                "turn_index": i,
                "user_message": user_message,
                "is_benign": is_benign,
                "response": response
            })

        result = {
            "task_id": task_id,
            "battery": "violation_state",
            "description": task.get("description", ""),
            "turns": turn_results
        }

        results.append(result)

        if output_file:
            with open(output_file, "a") as f:
                f.write(json.dumps(result) + "\n")

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

        texts = [seed_text]
        current_text = seed_text

        # Run echo rounds
        for round_idx in range(n_rounds):
            if pattern == "iterative_summary":
                # Simple iterative summarization
                prompt = f"{instruction}\n\n{current_text}"
                current_text = client.generate(prompt)
                texts.append(current_text)

            elif pattern == "multi_agent":
                # Multi-agent pattern: summarize, then expand
                if round_idx % 2 == 0:
                    prompt = f"{instruction}\n\n{current_text}"
                else:
                    prompt = f"Expand on the key concepts in the following summary:\n\n{current_text}"
                current_text = client.generate(prompt)
                texts.append(current_text)

        result = {
            "task_id": task_id,
            "battery": "echo_chamber",
            "description": task.get("description", ""),
            "pattern": pattern,
            "n_rounds": n_rounds,
            "initial_text": seed_text,
            "final_text": current_text,
            "intermediate_texts": texts[1:-1]  # All texts except first and last
        }

        results.append(result)

        if output_file:
            with open(output_file, "a") as f:
                f.write(json.dumps(result) + "\n")

    return results
