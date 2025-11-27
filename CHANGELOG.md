# Changelog

All notable changes to EPB (Epistemic Pathology Benchmark) will be documented in this file.

## [1.2.0] - 2025-11-27

### Fixed

- **Confabulation Persistence scoring**: v1.0 incorrectly penalized models that correctly refused to fabricate but mentioned real facts (like years or proper nouns) while explaining why something doesn't exist.

### Changed

- Added `initial_correct` labels via `results/confab_initial_labels.json`
- Persistence is now defined only over examples where the initial answer was incorrect (`initial_correct == false`) and the model defended that incorrect answer when challenged
- Recomputed Confab and EPB Truth scores for the existing n=70 benchmark runs
- Archived v1.0 scores as `results/epb_scores_v1.0.*` for transparency

### Added

- `results/confab_initial_labels.json`: LLM-judged labels for each confabulation initial answer
- `results/epb_scores_v1.0.json` and `.csv`: Archived v1.0 results
- `results/epb_scores_v1.2.json` and `.csv`: Updated v1.2 results
- `scripts/generate_confab_initial_labels.py`: Script to generate initial_correct labels
- `scripts/rescore_v1_2.py`: Script to rescore runs with v1.2 logic
- `prompts/confab_initial_judge.md`: Judge prompt for labeling initial answers

## [1.0.2] - 2025-11-22

### Added

- Initial public release of EPB v1
- Four benchmark batteries: Mirror Loop, Confabulation, Violation State, Echo Chamber
- CLI commands: `epb init-config`, `epb run`, `epb score`, `epb submit`
- Support for OpenAI and Anthropic model providers
- 70 test tasks (20 mirror loop, 30 confabulation, 10 violation state, 10 echo chamber)
