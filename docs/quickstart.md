# EPB Quickstart Guide

This guide will help you run your first EPB benchmark in under 5 minutes.

## Prerequisites

- Python 3.9 or later
- An API key for OpenAI or Anthropic

## Installation

### From PyPI (recommended)

```bash
pip install epb-benchmark
```

### From Source

```bash
git clone https://github.com/Course-Correct-Labs/epb-benchmark.git
cd epb-benchmark
pip install -e .
```

## Step 1: Initialize Configuration

Create a configuration file:

```bash
epb init-config
```

This creates `epb_config.yaml` in your current directory with default settings.

## Step 2: Configure Your Model

Edit `epb_config.yaml` to set your model provider and name:

### For OpenAI models:

```yaml
adapter:
  provider: "openai"
  model_name: "gpt-4"
  api_key_env: "OPENAI_API_KEY"
```

**Note**: EPB automatically handles different OpenAI model families:
- **GPT-4 models** (gpt-4, gpt-4-turbo, gpt-4.1-mini, etc.): Uses `max_tokens` parameter
- **GPT-5 models** (gpt-5, gpt-5-mini, etc.): Uses `max_completion_tokens` parameter
- **Reasoning models** (o1, o1-mini, o3, o3-mini): Uses `max_completion_tokens` parameter

You only need to set `model_name` correctly - EPB will use the appropriate API parameter automatically.

### For Anthropic models:

```yaml
adapter:
  provider: "anthropic"
  model_name: "claude-3-5-sonnet-20241022"
  api_key_env: "ANTHROPIC_API_KEY"
```

## Step 3: Set Your API Key

```bash
# For OpenAI
export OPENAI_API_KEY="sk-..."

# For Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Step 4: Run the Benchmark

### Full Run

Run all batteries:

```bash
epb run --config epb_config.yaml
```

This will:
- Run all 70 test tasks (20 Mirror Loop + 30 Confabulation + 10 Violation State + 10 Echo Chamber)
- Save results to `runs/YYYYMMDD_HHMMSS/`
- Take approximately 10-30 minutes depending on the model

### Quick Mode (for testing)

Run a subset of tasks for quick testing:

```bash
epb run --config epb_config.yaml --quick
```

This samples only 3 tasks per battery and completes in a few minutes.

### Run Specific Battery

Run only one battery:

```bash
epb run --config epb_config.yaml --battery mirror_loop
```

Available batteries: `mirror_loop`, `confabulation`, `violation_state`, `echo_chamber`

## Step 5: Score the Results

After the run completes, score the results:

```bash
epb score --run-dir runs/YYYYMMDD_HHMMSS
```

Replace `YYYYMMDD_HHMMSS` with your actual run ID (printed at the end of the run).

This will:
- Compute each battery's current structured scientific quantity
  (`results.json["quantities"]` -- see below)
- Also compute the four legacy sub-scores and the legacy overall EPB
  Truth score / certification level, for backward compatibility
- Save results to `runs/YYYYMMDD_HHMMSS/results.json`

### Example Output

```
Scoring run: 20250117_143022
Scoring Mirror Loop...
  EPB Phi: 85.50
Scoring Confabulation...
  EPB Persistence: 72.30
Scoring Violation State...
  EPB Contamination: 95.00
Scoring Echo Chamber...
  EPB Drift: 88.20

==================================================
EPB TRUTH SCORE: 85.25
Certification: GOLD
==================================================

Results saved to: runs/20250117_143022/results.json
```

**Note**: `EPB TRUTH SCORE` and `Certification` above are the legacy,
noncanonical fields (`scores.epb_truth`/`certification` in the JSON
below) -- retained for backward compatibility, not a validated scientific
conclusion. For the current structured scientific interpretation of a
run, use `results.json["quantities"]` instead (Step 6).

## Step 6: View Results

The results JSON has two layers. For the **current scientific
interpretation**, read `quantities` -- one entry per measurable quantity,
each with its own `measurement_state`/`validation_status` and a derived
`canonical_consumption_eligible` (currently `false` for every EPB v1
quantity -- none is yet `FROZEN`). `scores` (including `epb_truth`) and
`certification` are **legacy/noncanonical** backward-compatibility
fields, not a validated scientific conclusion:

```json
{
  "epb_version": "epb_v1",
  "model_name": "gpt-4",
  "provider": "openai",
  "run_id": "20250117_143022",
  "quantities": {
    "mirror_loop.collapse": {
      "measurement_state": "scored",
      "validation_status": "provisional",
      "value": 85.50,
      "canonical_consumption_eligible": false
    },
    "...": "one entry per quantity -- see api.md for the full shape"
  },
  "scores": {
    "mirror_loop_phi": 85.50,
    "confab_persistence": 72.30,
    "violation_contamination": 95.00,
    "echo_drift": 88.20,
    "epb_truth": 85.25
  },
  "epb_truth_status": "legacy_noncanonical",
  "certification": "gold",
  "metadata": { ... },
  "details": { ... }
}
```

## Optional: Submit to Leaderboard

If you have leaderboard access:

```bash
export EPB_LEADERBOARD_URL="https://epb.coursecorrect.org/api"
export EPB_API_KEY="your-leaderboard-api-key"

epb submit --results runs/YYYYMMDD_HHMMSS/results.json
```

## Troubleshooting

### API Key Not Found

If you see `ValueError: API key not found`:
- Make sure you've exported the correct environment variable
- Check that the variable name matches `api_key_env` in your config
- Try printing the variable: `echo $OPENAI_API_KEY`

### Module Not Found

If you see `ModuleNotFoundError`:
- Make sure you've installed EPB: `pip install epb-benchmark`
- If installing from source, use `pip install -e .` in the repo directory

### Rate Limits

If you hit API rate limits:
- Use `--quick` mode for testing
- Adjust `temperature` and `max_tokens` in config to reduce token usage
- Add delays between requests (future feature)

## Next Steps

- Read [Methodology](methodology.md) to understand what EPB measures
- Read [Scoring Details](scoring.md) for the exact formulas
- Check [API Reference](api.md) for programmatic usage
- Try different models and compare results

## Configuration Reference

Key config parameters:

```yaml
# EPB version
epb_version: "epb_v1"

# Model settings
model:
  temperature: 0.7
  max_tokens: 1000
  top_p: 1.0

# Adapter
adapter:
  provider: "openai"
  model_name: "gpt-4"
  api_key_env: "OPENAI_API_KEY"

# Quick mode
quick_mode:
  enabled: false
  n_samples_per_battery: 3
```

See `epb/config/epb_v1.yaml` for full configuration options.
