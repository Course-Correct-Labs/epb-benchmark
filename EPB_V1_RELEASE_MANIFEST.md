# EPB v1 Release Manifest

Freeze date: **2026-09-01**

This manifest is operational, not a duplicate of
`EPB_V1_FINAL_INTEGRATION_FREEZE.md` (the authoritative scientific/semantic
freeze document -- see that file for the full frozen contract).

## Identity

| Identity | Value |
|---|---|
| Scientific methodology | EPB v1 |
| Methodology field | `epb_version = "epb_v1"` |
| Python package release | `epb-benchmark 2.0.0` |
| Planned Git tag | `v2.0.0` |
| Result schema | `RESULT_SCHEMA_VERSION = 1` (unchanged) |
| Observation schema | `OBSERVATION_SCHEMA_VERSION = 1` (unchanged) |

Package version and scientific methodology version are intentionally
independent axes -- see `epb/__init__.py`'s module docstring. The `2.0.0`
package bump reflects a breaking Python API change only (SemVer major),
not a change to EPB v1 science.

## Four batteries / five structured quantities

- Mirror Loop (`mirror_loop.collapse`)
- Confabulation (`confabulation.fabrication_incidence`,
  `confabulation.persistence`)
- Violation State (`violation_state.contamination`)
- Echo Chamber (`echo_chamber.drift`)

No quantity is currently `canonical_consumption_eligible` (none is yet
`FROZEN`). See `results.json["quantities"]` / `docs/api.md`.

## Authoritative freeze contract

`EPB_V1_FINAL_INTEGRATION_FREEZE.md` (repo root).

## Why the package version is 2.0.0, not 1.0.3/1.1.0

`epb-benchmark==1.0.2` is already published on PyPI. The frozen release
here contains breaking public API changes relative to it -- confirmed via
git history: `score_confabulation(run_dir, hedging_patterns)` (required
kwarg) at the last committed source no longer exists; the current
`score_confabulation(run_dir, legacy_archive=None)` takes no
`hedging_patterns` argument at all, so old caller code passing
`hedging_patterns=` now raises `TypeError`. SemVer requires a major bump
for a breaking public API change. See `CHANGELOG.md`'s `[2.0.0]` entry.

## Test result

Full suite: **382 passed, 1 xfailed, 0 failed** (matches the
pre-version-bump baseline exactly). Targeted subset (final integration,
result model, CLI architecture, Confabulation, Mirror Loop, Violation
State, Echo Chamber, adapters, result-adapter, run-battery isolation,
CLI scoring-failure): **337 passed, 0 failed**.

## Clean source-install result

Fresh venv, `pip install <repo>`: succeeded. `epb.__version__` = `2.0.0`,
`epb.__epb_version__` = `"epb_v1"`, schema versions unchanged. `epb --help`
shows exactly 4 commands; `--battery` choices are exactly the 4 canonical
batteries.

## Build result

`python -m build` produced `epb_benchmark-2.0.0.tar.gz` and
`epb_benchmark-2.0.0-py3-none-any.whl` from repo source (built to a
scratch `--outdir`, not the repo's own stale `dist/`). Wheel contents
verified via `python -m zipfile -l`: all 4 spec `.jsonl` files, the task
schema, `epb_v1.yaml`, and all `epb/` modules are present.

## Wheel-install result

Second fresh venv, wheel-only install (no source, no editable):
`epb.__file__` resolves into site-packages (not the source tree).
`epb.__version__` = `2.0.0`, `epb.__epb_version__` = `"epb_v1"`. CLI,
scorer imports, spec/config resource loading, and zero-cost scoring all
confirmed working identically to the source install.

## CLI-smoke result

`epb --help` / `run --help` / `score --help` / `init-config --help` /
`submit --help` all clean: 4 subcommands, 4-battery inventory, no ECZ
exposed as a battery. `epb --version` intentionally prints `epb_v1` (the
scientific methodology version, via `click.version_option`), not the
package version -- pre-existing, deliberate identity-separation design,
unchanged by this pass.

## Zero-cost source scoring result

Synthetic fixture (non-historical run-dir name) scored via the
source-installed CLI end to end. Result: Mirror Loop/Violation
State/Echo Chamber reach `measurement_state = "scored"`; Confabulation
correctly reaches `insufficient_evidence`/`no_applicable_evidence` with
`value: null` (no real historical label for a synthetic run id -- the
trust boundary holds, no fake evidence). `epb_truth_status =
"not_computed"`, `certification = null`.

## Zero-cost wheel scoring result

Same fixture, same CLI invocation, wheel-installed environment: byte-for-byte
identical scoring outcome to the source-install run above.

## Accepted known limitations (not reopened this pass)

- Zero-battery legacy `epb_truth = 0.0` / `certification = "incomplete"` quirk.
- Mirror/Violation parameter asymmetry (Mirror Loop's `collapse_threshold`/
  `min_consecutive` and Violation State's `refusal_patterns` are genuinely
  config-overridable; Confabulation's `hedging_patterns` and Echo Chamber's
  `n_rounds` are not -- confirmed again this pass via source inspection,
  not just docs).
- Dead transitional helpers (`UnscoreableEvidenceError`, `_run_single_quantity`).
- Historical Confabulation provenance limitations; historical result caveats
  (`CHANGELOG.md`'s "Historical result notice").

## vNext items

- `docs/scoring.md`'s legacy score formulas/regex-based fabrication
  description were flagged as stale this pass and caveated in place
  rather than rewritten wholesale -- a fuller rewrite of that document to
  natively describe the two-axis measurement/validation architecture
  (rather than caveating the legacy description) is a good candidate for
  the next documentation pass.
- Two untracked root-level items are orphaned/questionable for inclusion
  in the release commit and need an explicit decision: `spec/` (a
  byte-identical duplicate of `epb/spec/`, referenced nowhere) and
  `epb_config_gpt5.yaml` (an ad hoc model config, not gitignored, not
  referenced by package or docs).

## PyPI publication status

**NOT PUBLISHED.** No upload was attempted. `epb-benchmark==1.0.2` remains
the latest version live on PyPI as of this pass.

## Release commit / tag

- Exact release commit hash: placeholder until commit exists.
- Exact release tag: planned `v2.0.0` until tag exists.
