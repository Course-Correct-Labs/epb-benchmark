#!/usr/bin/env python3
"""
Generate confab initial labels using LLM-as-judge or manual template.

This script reads confabulation.jsonl files from specified runs and labels
each initial_answer as epistemically correct or incorrect.
"""

import json
import os
import sys
from pathlib import Path

# Run ID to model name mapping
RUN_MODEL_MAP = {
    "20251122_041711": "gpt-5-mini",
    "20251126_014253": "gpt-5",
    "20251126_032838": "gpt-4o",
    "claude_sonnet_merged": "claude-sonnet-4-5-20250929",
}

# Ordered list of runs to process
RUNS_TO_PROCESS = [
    "20251126_014253",      # gpt-5
    "20251126_032838",      # gpt-4o
    "claude_sonnet_merged", # claude-sonnet-4-5-20250929
]


def load_judge_prompt(repo_root: Path) -> str:
    """Load the judge prompt from prompts/confab_initial_judge.md"""
    prompt_path = repo_root / "prompts" / "confab_initial_judge.md"
    with open(prompt_path, "r") as f:
        return f.read()


def load_confab_data(repo_root: Path, run_id: str) -> list[dict]:
    """Load confabulation.jsonl for a given run"""
    confab_path = repo_root / "runs" / run_id / "confabulation.jsonl"
    if not confab_path.exists():
        print(f"WARNING: {confab_path} not found, skipping")
        return []

    data = []
    with open(confab_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def call_llm_judge(api_key: str, base_prompt: str, question: str, initial_answer: str) -> dict:
    """Call Claude API to judge an answer"""
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    user_prompt = f"""Question: {question}

Model's Initial Answer: {initial_answer}

Based on the criteria above, evaluate this answer."""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=200,
        temperature=0,
        system=base_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    # Parse JSON response
    response_text = response.content[0].text.strip()

    # Handle potential markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        match = re.search(r'\{[^}]+\}', response_text)
        if match:
            return json.loads(match.group())
        return {"initial_correct": None, "reason": f"Failed to parse: {response_text[:100]}"}


def main():
    # Find repo root
    repo_root = Path("/Users/bentleydevilling/Desktop/epb-benchmark")
    if not repo_root.exists():
        # Try to find it
        import subprocess
        result = subprocess.run(
            ["find", str(Path.home()), "-type", "d", "-name", "epb-benchmark"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            repo_root = Path(result.stdout.strip().split("\n")[0])
        else:
            print("ERROR: Could not find epb-benchmark repo")
            sys.exit(1)

    os.chdir(repo_root)
    print(f"Repo root: {repo_root}")

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    use_llm = bool(api_key)

    if use_llm:
        print("ANTHROPIC_API_KEY found - using LLM-as-judge")
        base_prompt = load_judge_prompt(repo_root)
    else:
        print("No ANTHROPIC_API_KEY - generating manual template")

    # Process all runs
    all_labels = []
    model_stats = {}

    for run_id in RUNS_TO_PROCESS:
        model_name = RUN_MODEL_MAP.get(run_id, run_id)
        print(f"\nProcessing {run_id} ({model_name})...")

        confab_data = load_confab_data(repo_root, run_id)
        if not confab_data:
            continue

        print(f"  Found {len(confab_data)} examples")

        correct_count = 0
        incorrect_count = 0

        for i, example in enumerate(confab_data):
            task_id = example.get("task_id", f"unknown_{i}")
            question = example.get("question", "")
            initial_answer = example.get("initial_answer", "")

            if use_llm:
                try:
                    result = call_llm_judge(api_key, base_prompt, question, initial_answer)
                    initial_correct = result.get("initial_correct")
                    reason = result.get("reason", "")

                    if initial_correct is True:
                        correct_count += 1
                    elif initial_correct is False:
                        incorrect_count += 1

                except Exception as e:
                    print(f"    ERROR on {task_id}: {e}")
                    initial_correct = None
                    reason = f"Error: {str(e)}"
            else:
                initial_correct = None
                reason = ""

            label_entry = {
                "run_id": run_id,
                "task_id": task_id,
                "model": model_name,
                "initial_correct": initial_correct,
                "reason": reason
            }
            all_labels.append(label_entry)

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"    Processed {i + 1}/{len(confab_data)}")

        model_stats[model_name] = {
            "correct": correct_count,
            "incorrect": incorrect_count,
            "total": len(confab_data)
        }

        if use_llm:
            print(f"  {model_name}: {correct_count} correct, {incorrect_count} incorrect")

    # Write output
    output_path = repo_root / "results" / "confab_initial_labels.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(all_labels, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Labels saved to: {output_path.absolute()}")
    print(f"Total labels: {len(all_labels)}")

    if use_llm:
        print(f"\n{'='*50}")
        print("Per-model summary:")
        total_correct = 0
        total_incorrect = 0
        for model, stats in model_stats.items():
            print(f"  {model}: {stats['correct']} correct, {stats['incorrect']} incorrect (of {stats['total']})")
            total_correct += stats['correct']
            total_incorrect += stats['incorrect']
        print(f"\nTotal: {total_correct} correct, {total_incorrect} incorrect")
    else:
        print("\nManual template generated - fill in initial_correct and reason fields")


if __name__ == "__main__":
    main()
