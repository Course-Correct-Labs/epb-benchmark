# EPB Documentation

Welcome to the Epistemic Pathology Benchmark (EPB) documentation.

## Getting Started

- **[Quickstart Guide](quickstart.md)**: Get up and running with EPB in 5 minutes
- **[README](../README.md)**: Overview and installation instructions

## Understanding EPB

- **[Methodology](methodology.md)**: What EPB measures and why
- **[Scoring Details](scoring.md)**: Exact formulas and algorithms

## Using EPB

- **[API Reference](api.md)**: CLI commands and Python API
- **[Examples](../examples/)**: Sample scripts for OpenAI and Anthropic

## EPB v1 Specifications

EPB v1 measures four epistemic pathologies:

### 1. Mirror Loop (20 tasks)
Tests stability in recursive self-refinement. Models iteratively critique and improve their own outputs.

**Metric**: EPB Phi (0-100, higher is better)

### 2. Confabulation (30 tasks)
Tests fabrication and persistence of false information. Models answer unanswerable questions and are then challenged.

**Metric**: EPB Persistence (0-100, higher is better)

### 3. Violation State (10 tasks)
Tests refusal contamination. Models receive violation requests followed by benign requests.

**Metric**: EPB Contamination (0-100, higher is better)

### 4. Echo Chamber (10 tasks)
Tests semantic drift through iterative summarization. Models repeatedly summarize their own outputs.

**Metric**: EPB Drift (0-100, higher is better)

### Overall Score
**EPB Truth**: Weighted average of the four sub-scores (default: equal weighting)

## Quick Reference

### Installation
```bash
pip install epb-benchmark
```

### Basic Usage
```bash
# Initialize config
epb init-config

# Edit epb_config.yaml and set your API key

# Run benchmark
epb run --config epb_config.yaml

# Score results
epb score --run-dir runs/YYYYMMDD_HHMMSS
```

### Certification Levels

| Level | Score |
|-------|-------|
| Platinum | 95+ |
| Gold | 85+ |
| Silver | 70+ |
| Bronze | 50+ |

## Architecture

```
epb-benchmark/
├── epb/
│   ├── config/          # Configuration files
│   ├── spec/            # Task specifications (JSONL)
│   ├── adapters/        # Model adapters
│   ├── runner/          # Benchmark execution
│   ├── scoring/         # Scoring algorithms
│   └── cli/             # Command-line interface
├── docs/                # Documentation
├── examples/            # Example scripts
└── tests/               # Test suite
```

## Contributing

EPB is open source and welcomes contributions:

- New model adapters
- Additional test tasks
- Improved scoring heuristics
- Bug fixes and documentation

See our [GitHub repository](https://github.com/Course-Correct-Labs/epb-benchmark).

## Support

- **Issues**: [GitHub Issues](https://github.com/Course-Correct-Labs/epb-benchmark/issues)
- **Email**: hello@coursecorrect.org
- **Website**: https://coursecorrect.org

## License

EPB is released under the MIT License. See [LICENSE](../LICENSE) for details.

## Citation

```bibtex
@software{epb2025,
  title = {EPB: Epistemic Pathology Benchmark},
  author = {Course Correct Labs},
  year = {2025},
  url = {https://github.com/Course-Correct-Labs/epb-benchmark}
}
```

## Related Work

EPB is based on research from Course Correct Labs:

- [Mirror Loop](https://github.com/Course-Correct-Labs/mirror-loop)
- [Recursive Confabulation](https://github.com/Course-Correct-Labs/recursive-confabulation)
- [Violation State](https://github.com/Course-Correct-Labs/violation-state)

Note: [Echo Chamber Zero](https://github.com/Course-Correct-Labs/echo-chamber-zero)
is separate, theoretical Course Correct Labs work. It is **not** an EPB
battery and is not the scientific basis for EPB's empirical Echo Chamber
battery (see `docs/methodology.md` for the correction).
