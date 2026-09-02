# EPB: Epistemic Pathology Benchmark

**The MLPerf of AI Truth Systems**

EPB (Epistemic Pathology Benchmark) is a comprehensive benchmark for evaluating epistemic integrity in AI systems. It measures four critical pathologies that affect AI truthfulness and reliability:

- **Mirror Loop**: Collapse in recursive self-refinement
- **Confabulation**: Fabrication and persistence of false information
- **Violation State**: Refusal contamination of benign prompts
- **Echo Chamber**: Synthetic drift and self-reinforcement

## Quick Start

### Installation

```bash
pip install epb-benchmark
```

Or install from source:

```bash
git clone https://github.com/Course-Correct-Labs/epb-benchmark.git
cd epb-benchmark
pip install -e .
```

### Running the Benchmark

1. Initialize a configuration file:

```bash
epb init-config
```

2. Edit `epb_config.yaml` to set your model and API key:

```yaml
adapter:
  provider: "openai"  # or "anthropic"
  model_name: "gpt-4"
  api_key_env: "OPENAI_API_KEY"
```

3. Set your API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

4. Run the benchmark:

```bash
epb run --config epb_config.yaml
```

5. Score the results:

```bash
epb score --run-dir runs/YYYYMMDD_HHMMSS
```

## What EPB Measures

EPB evaluates four distinct pathologies, each with an explicit metric:

### 1. Mirror Loop (EPB Phi)

Measures stability in recursive self-refinement. Models are asked to iteratively critique and improve their own outputs. **Collapse** occurs when the model gets stuck in repetitive patterns.

**Score**: 0-100 (higher is better)

### 2. Confabulation (EPB Persistence)

Measures fabrication of false information and its persistence after challenge. Models are asked unanswerable questions, then challenged on their answers.

**Score**: 0-100 (higher is better, less persistent confabulation)

### 3. Violation State (EPB Contamination)

Measures refusal contamination after seeing disallowed content. Models receive a violation request (which should be refused), followed by benign requests.

**Score**: 0-100 (higher is better, less contamination)

### 4. Echo Chamber (EPB Drift)

Measures semantic drift through iterative summarization. Models repeatedly summarize their own outputs, and drift is measured using TF-IDF cosine similarity.

**Score**: 0-100 (higher is better, less drift)

### Overall Score: EPB Truth

The overall **EPB Truth** score is a weighted average of the four sub-scores (default: equal weighting).

**Certification Levels**:
- **Platinum**: 95+
- **Gold**: 85+
- **Silver**: 70+
- **Bronze**: 50+

### Current Scientific Status (EPB v1 Final Integration)

The descriptions above ("Score: 0-100", "EPB Truth", certification tiers)
are EPB's original, legacy presentation. As of EPB v1's final integration
pass, they are **legacy / noncanonical**: `epb_truth` and certification
levels are retained for backward compatibility only and do not represent
a validated, canonical benchmark conclusion. Each battery's underlying
measurement is now reported as a structured result with its own
measurement state (was a value obtained at all?) and validation status
(how scientifically established is that measurement pathway?); no current
quantity meets the bar (`SCORED` + `FROZEN`) required for canonical
downstream consumption -- **included in EPB v1 does not mean canonically
validated.** Confabulation reports two independent quantities
(`fabrication_incidence`, `persistence`), so EPB v1 exposes **five**
structured scientific quantities across its four batteries. The current
structured representation of a scored run lives at
`results.json["quantities"]` -- one entry per quantity, each carrying its
own `measurement_state`, `validation_status`, `planned`/`applicable`/
`usable`/`coverage`, and a derived `canonical_consumption_eligible`. See
`EPB_V1_FINAL_INTEGRATION_FREEZE.md` for the current authoritative
posture, including Echo Chamber's inclusion-but-PROVISIONAL status and
the historical-result notice in `CHANGELOG.md`.

## EPB v1 Test Suite

EPB v1 includes:
- 20 Mirror Loop prompts
- 30 Confabulation questions
- 10 Violation State sequences
- 10 Echo Chamber scenarios

Total: 70 test tasks designed for quality over quantity.

### EPB v1.2 (Confabulation Persistence Fix)

EPB v1.2 updates the Confabulation Persistence metric. v1.0 incorrectly penalized models that correctly refused to fabricate but mentioned real facts (like years or proper nouns) while explaining why something doesn't exist. v1.2 uses explicit `initial_correct` labels for each confab example and counts persistence only when a fabricated or incorrect initial answer is defended under challenge.

**Key changes:**
- Added `results/confab_initial_labels.json` containing LLM-judged labels for each initial answer
- Persistence denominator is now only examples where `initial_correct == false`
- Models that correctly refuse to answer are no longer penalized

## Documentation

- [Quickstart Guide](docs/quickstart.md)
- [Methodology](docs/methodology.md)
- [Scoring Details](docs/scoring.md)
- [API Reference](docs/api.md)

## Leaderboard

**Note**: `coursecorrect.org` does not currently resolve (checked at
release time) -- treat the instructions below as documentation for a
leaderboard deployment, not a confirmed live production service. `epb
submit` will fail with a connection error until a real
`EPB_LEADERBOARD_URL` is available.

Submit your results to the public leaderboard:

```bash
export EPB_LEADERBOARD_URL="https://epb.coursecorrect.org/api"
export EPB_API_KEY="your-leaderboard-api-key"
epb submit --results runs/YYYYMMDD_HHMMSS/results.json
```

View the leaderboard at: https://epb.coursecorrect.org

## Architecture

EPB is designed to be:
- **Model-agnostic**: Works with any LLM through simple adapters
- **Reproducible**: Explicit metrics and deterministic scoring
- **Extensible**: Easy to add new batteries and adapters
- **Transparent**: Open-source specifications and scoring code

## Supported Models

Out of the box, EPB supports:
- OpenAI GPT models (GPT-4, GPT-3.5, etc.)
- Anthropic Claude models

To add support for other models, implement the `ModelClient` interface in `epb/adapters/`.

## Citation

If you use EPB in your research, please cite:

```bibtex
@software{epb2025,
  title = {EPB: Epistemic Pathology Benchmark},
  author = {Course Correct Labs},
  year = {2025},
  url = {https://github.com/Course-Correct-Labs/epb-benchmark}
}
```

## Contributing

We welcome contributions! Please see our contributing guidelines.

Areas for contribution:
- New model adapters
- Additional test tasks
- Improved scoring heuristics
- Bug fixes and documentation

## License

MIT License - see [LICENSE](LICENSE) for details.

## About

EPB is developed by [Course Correct Labs](https://coursecorrect.org), a research organization focused on epistemic integrity in AI systems.

Related work:
- [Mirror Loop](https://github.com/Course-Correct-Labs/mirror-loop)
- [Recursive Confabulation](https://github.com/Course-Correct-Labs/recursive-confabulation)
- [Violation State](https://github.com/Course-Correct-Labs/violation-state)

Note: [Echo Chamber Zero](https://github.com/Course-Correct-Labs/echo-chamber-zero)
is separate, theoretical Course Correct Labs work. It is **not** an EPB
battery and is not the scientific basis for EPB's empirical Echo Chamber
battery above (see `docs/methodology.md` for the correction and the
battery's actual, directly-described method).

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/Course-Correct-Labs/epb-benchmark/issues)
- Documentation: [docs/](docs/)
- Contact: hello@coursecorrect.org
