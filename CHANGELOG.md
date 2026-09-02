# Changelog

All notable changes to EPB (Epistemic Pathology Benchmark) will be documented in this file.

## [2.0.0] - 2026-09-01

### Changed (breaking, package version only -- scientific methodology unchanged)

- **Package version bump only.** This is a Python packaging/API version
  change under SemVer, not a scientific methodology change:
  `epb.__epb_version__` remains `"epb_v1"`, `RESULT_SCHEMA_VERSION` and
  `OBSERVATION_SCHEMA_VERSION` are unchanged, and no frozen scoring
  behavior was altered.
- Scorer function signatures changed in ways that break old caller code
  written against `epb-benchmark==1.0.2`. Most notably,
  `score_confabulation(run_dir, hedging_patterns)` no longer accepts a
  `hedging_patterns` argument at all (it now takes an optional
  `legacy_archive` argument instead) -- old code passing
  `hedging_patterns=` now raises `TypeError`. Confabulation scoring uses
  its own frozen, canonical hedging-pattern set internally regardless of
  caller input; see `docs/api.md` and `docs/scoring.md`.
- `results.json` gained a new top-level `quantities` structure (the
  current authoritative structured representation of a scored run, with
  `measurement_state`/`validation_status`/`canonical_consumption_eligible`
  per quantity) alongside the retained legacy `scores`/`certification`
  fields. See "Results JSON Format" in `docs/api.md`.
- This is why the package version jumped from `1.0.2` to `2.0.0` rather
  than incrementing minor/patch: SemVer requires a major bump for a
  breaking public API change, independent of the underlying EPB v1
  scientific methodology (which remains frozen and unchanged).

## Historical result notice (added during EPB v1 Final Integration)

The run `20251126_014253` (gpt-5), present in `results/epb_scores_v1.0.json`
and `results/epb_scores_v1.2.json` below, is **LEGACY / NONCANONICAL**:

- Phase 0's audit identified plausible empty-response / observation-validity
  contamination affecting how this run's numbers should be interpreted
  (`EPB_PHASE0_AUDIT_CHECKPOINT.md` §5/§8).
- It has **not** been rescored under the frozen EPB v1 evidence semantics
  established in `EPB_PHASE2_EVIDENCE_SEMANTICS.md` and Phase 3B.
- Its evidentiary basis is inadequate under the methodology established
  afterward -- this is not a claim that the historical number is known to
  be false, only that it predates and was never re-evaluated against the
  methodology that would be needed to interpret it today.
- **Do not use it for current model comparison, validation claims, or
  canonical EPB conclusions.**

The other four runs in the same files (`20251126_032838`, `claude_sonnet_merged`,
`20251127_025450`, `20251127_025457`) predate the same frozen evidence
semantics and carry the identical limitation, though no specific defect was
identified for them in the Phase 0 audit.

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
