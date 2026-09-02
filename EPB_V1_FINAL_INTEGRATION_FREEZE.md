# EPB v1 Final Integration Freeze

This is the authoritative current integration reference for EPB v1. It
reconciles the frozen battery-specific specs (Phase 2), their
implementations (Phase 3A/3B), and the researcher decisions that closed
the remaining integration-level gaps (D2-D5, Phase 0/0.5, retroactive
Confabulation fingerprint binding). It is intentionally concise relative
to the phase appendices (`EPB_PHASE0_AUDIT_CHECKPOINT.md` through
`EPB_PHASE3B4_CONFABULATION_CODE_APPENDIX.md`), which remain the detailed
historical record and are not reproduced here.

This document does not itself declare EPB v1 frozen -- that is the
researcher's decision. It reports freeze-readiness evidence (§23).

## 1. EPB v1 purpose

EPB (Epistemic Pathology Benchmark) measures epistemic pathologies in AI
systems -- failure modes distinct from raw capability or knowledge
benchmarks. It is model-agnostic, reproducible (explicit metrics,
deterministic scoring), and structured around one measurable quantity per
scientific construct rather than a single opaque score.

## 2. Canonical battery set

Four batteries, final researcher-approved (D5b closes the last open
question):

1. **Mirror Loop** -- collapse in recursive self-refinement
2. **Violation State** -- refusal contamination of benign prompts
3. **Empirical Echo Chamber** -- synthetic drift under iterative
   summarization
4. **Confabulation** -- fabrication and its persistence under challenge

**Echo Chamber Zero is not a battery.** It is separate, theoretical Course
Correct Labs work, explicitly excluded from the EPB/Observatory battery
inventory (§12).

## 3. Five structured quantities

Confabulation exposes two independent scientific quantities, so the
structured `quantities` set contains five entries, not four:

| # | Quantity key | Battery |
|---|---|---|
| 1 | `mirror_loop.collapse` | Mirror Loop |
| 2 | `violation_state.contamination` | Violation State |
| 3 | `echo_chamber.drift` | Empirical Echo Chamber |
| 4 | `confabulation.fabrication_incidence` | Confabulation |
| 5 | `confabulation.persistence` | Confabulation |

`epb_truth` and certification are **not** quantities -- they are legacy
cross-battery scalars (§9/§10).

## 4. Measurement-state model

`MeasurementState` (`epb/scoring/result.py`): `SCORED`,
`INSUFFICIENT_EVIDENCE`, `NO_APPLICABLE_EVIDENCE`, `EXECUTION_FAILURE`,
`SCORING_ERROR`. Answers "did *this run* produce a computable
measurement?" -- a per-run outcome, never conflated with validation
status.

## 5. Validation-state model

`ValidationStatus`: `FROZEN`, `PROVISIONAL`, `UNRESOLVED`. Answers "is the
measurement *pathway* scientifically established, independent of whether
this run reached a measurement?" Set per-battery by the caller (never
derived from `measurement_state`).

## 6. Canonical-consumption rule

```python
canonical_consumption_eligible = (
    measurement_state == MeasurementState.SCORED
    and validation_status == ValidationStatus.FROZEN
)
```

Implemented as a read-only `@property` on `QuantityResult` (`epb/scoring/result.py`)
-- no constructor parameter, no setter, and `QuantityResult.from_dict`
never reads a persisted `canonical_consumption_eligible` value back from
JSON (it is always re-derived). A hand-edited `results.json` claiming
`"canonical_consumption_eligible": true` is silently ignored on reload
(`tests/test_result_model.py::test_canonical_flag_cannot_be_forged_through_from_dict`).

> **Only `SCORED && FROZEN` quantities are eligible for canonical
> downstream consumption.**

## 7. No current FROZEN quantity

| Quantity | Validation status |
|---|---|
| Mirror Loop collapse | PROVISIONAL |
| Violation State contamination | PROVISIONAL |
| Echo Chamber drift | PROVISIONAL |
| Confabulation fabrication_incidence | PROVISIONAL iff `usable_count > 0`, else UNRESOLVED |
| Confabulation persistence | UNRESOLVED, unconditionally |

No current quantity's validation status is `FROZEN`. This is not
implied to change automatically by future runs -- promoting any quantity
to `FROZEN` is a distinct, not-yet-made researcher decision.

## 8. No current canonical aggregate

Because no quantity is `FROZEN`, no quantity is
`canonical_consumption_eligible` -- confirmed by direct exercise of all
five real result adapters under each one's own strongest currently
reachable state, including Confabulation's fabrication_incidence and
persistence reaching `SCORED` via an explicit, caller-authorized archive
context (`tests/test_final_integration_freeze.py::test_all_five_quantities_canonical_ineligible_under_strongest_reachable_states`).
**No overall canonical EPB score exists.**

> **Included in EPB v1 does not mean canonically validated.**

## 9. `epb_truth`: legacy/noncanonical posture

`epb/scoring/aggregate.py::compute_epb_truth()` is a pure function of four
bare floats (a weighted average, default equal weights) -- verified by
direct source inspection to contain no reference to `QuantityResult`,
`ValidationStatus`, `canonical_consumption_eligible`, or any
`legacy_archive` concept anywhere
(`tests/test_final_integration_freeze.py::test_legacy_aggregate_is_a_pure_function_isolated_from_structured_quantities`).
It has no canonical scientific path: the four sub-scores are
noncommensurable, use opposite legacy-vs-structured directionality in
places, are gated by different evidence-usability rules, carry different
validation statuses, and no frozen weighting/compensation rule exists to
combine them scientifically. `epb/cli/main.py` persists it as
`results["scores"]["epb_truth"]`, always alongside an explicit
`results["epb_truth_status"]` of `"legacy_noncanonical"` (a real number
was computed, under the old rules) or `"not_computed"` (no number, most
commonly). It must never be presented as EPB's scientific truth, a
canonical model score, or a validated cross-battery conclusion --
retained only for backward compatibility, explicitly labeled.

## 10. Certification: legacy/noncanonical posture

`get_certification_level()` takes only `epb_truth` (a float) and an
optional thresholds dict -- confirmed by direct signature inspection to
have no parameter through which it could read validation state or the
canonical-consumption gate
(`tests/test_final_integration_freeze.py::test_certification_never_reads_validation_state_or_canonical_gate`).
It is a pure bronze/silver/gold/platinum threshold lookup over the
already-noncanonical `epb_truth`. Retained for backward compatibility,
explicitly non-canonical -- not a validated certification methodology.

## 11. Empirical Echo Chamber: included, PROVISIONAL

Empirical Echo Chamber (TF-IDF cosine drift under iterative
summarization) **is included in EPB v1** (D5b, closed):

- an EPB v1 battery;
- operationally frozen (Phase 2 §7.4-7.8, unchanged since Phase 1);
- currently `PROVISIONAL` validation status;
- `canonical_consumption_eligible = False`, same as every other current
  quantity.

> **Included in EPB v1 does not mean canonically validated.**

## 12. Echo Chamber Zero: excluded

Echo Chamber Zero is theoretical Course Correct Labs work, not an EPB
battery, and excluded from the EPB/Observatory battery inventory (Phase
0.5: "that question is closed"). It is **not** the scientific/citation
basis for the empirical Echo Chamber battery above -- an earlier
`docs/methodology.md` citation conflated the two (D5a); that citation has
been removed, and the empirical battery's method is now described
directly, without inventing a substitute citation (§21).

## 13. Confabulation: general-vs-archive distinction

`score_confabulation`/`score_confabulation_result` default to
`legacy_archive=None` (the general/ordinary path) -- with no archive,
`_task_classification` can structurally never obtain a label, regardless
of `run_dir.name`. Renaming a run directory to a historical labeled
run_id has zero scientific effect through the ordinary `epb score` CLI
(`tests/test_cli_result_architecture.py::test_rid_exploit_replay_confabulation_directory_name_has_zero_effect_via_cli`).
An explicit caller that consciously constructs a
`LegacyConfabulationArchiveContext` via `open_legacy_confabulation_archive()`
and passes `legacy_archive=...` can reproduce the retained legacy label
mapping -- the same directory name that produces zero effect through the
CLI produces real labels only when that archive is explicitly supplied
(`tests/test_cli_result_architecture.py::test_rid_exploit_replay_archive_authorized_control_differs_only_via_explicit_caller_context`).
The only live reader of `results/confab_initial_labels.json` in `epb/` is
`confab_scoring.py`'s `_get_labels()`/`_load_initial_labels()`, used
exclusively inside `LegacyConfabulationArchiveContext`/
`open_legacy_confabulation_archive()`. `epb/scoring/aggregate.py`
(legacy `epb_truth`/certification) never references it, directly or
transitively.

## 14. Historical Confabulation provenance limitations

Of the five run_ids in `results/confab_initial_labels.json`, only three
(`20251126_014253`, `20251126_032838`, `claude_sonnet_merged`) have
retained generation evidence in `scripts/generate_confab_initial_labels.py`'s
hardcoded `RUNS_TO_PROCESS`; the other two (`20251127_025450`,
`20251127_025457`) and `claude_sonnet_merged`'s own merge/construction
have documented gaps. `LegacyConfabulationArchiveContext` is directly,
publicly constructible by a conscious caller (used deliberately by
Scenario V) -- its actual guaranteed property is narrower than
"unforgeable": its constructor takes no `run_dir`/`run_id` parameter, so
nothing found inside a scored run can produce one merely from its own
filesystem-controlled identity.

## 15. Rejected retroactive fingerprint binding

Retroactive fingerprinting of historical Confabulation run files was
investigated and found technically possible (content-hash binding would
discriminate against the directory-rename exploit going forward).
However, current historical run bytes cannot be authenticated as the
exact original inputs an LLM judge actually scored -- no contemporaneous
hash, signature, or other binding was captured at labeling time.
Retroactively computing and attaching a fingerprint now would create only
the appearance of provenance assurance without the underlying guarantee,
risking provenance laundering. Retroactive binding was therefore rejected
as a fix for the five historically labeled runs. Provenance for any
future run must be established at run-creation time, not reconstructed
after the fact (§22).

Classification: **RESEARCHER DECISION + HISTORICAL LIMITATION + VNEXT
REQUIREMENT**. This decision is not derived from the original frozen
spec -- it is a researcher decision made during this integration work.

## 16. Historical result `20251126_014253`: warning

**RETAIN WITH WARNING** (D3, closed) -- not retracted. `results/epb_scores_v1.0.json`
and `results/epb_scores_v1.2.json` (unchanged JSON structure; no schema
modification, since these files have no established metadata mechanism)
still contain this run's numeric values. The warning is placed in
`CHANGELOG.md` (adjacent authoritative documentation, identifying the
exact run ID) and README.md's "Current Scientific Status" section:

> Legacy/noncanonical historical result. Phase 0 identified plausible
> observation-validity/empty-response contamination affecting
> interpretation. Not rescored under frozen EPB v1 evidence semantics. Do
> not use for current model comparison, validation, or canonical EPB
> conclusions.

This is not a claim that the historical number is known to be false --
its evidentiary basis is inadequate under the methodology established
afterward, which is a different, narrower claim.

## 17. Phase 0 PDF-authority supersession

Phase 0 (`EPB_PHASE0_AUDIT_CHECKPOINT.md`) originally treated
`EPB_Benchmark_Specification_v1.pdf` (dated June 2026) as the released,
source-of-truth specification. Phase 0.5 (`EPB_PHASE0_5_VNEXT_DESIGN.md`
§2) explicitly superseded that premise, per Bentley's own direct
correction: the PDF was assembled quickly from AI memory plus repo
inspection and is not a frozen normative specification; it is now
secondary descriptive evidence only. **Only the PDF-authority framing is
superseded** -- Phase 0's independent empirical findings (empty-response
defects, the Echo-Chamber-Zero citation collision, the adapter interface
gap, the Anthropic `content[0]` crash risk) remain part of the audit
record and were not derived from PDF authority. A supersession banner was
added at the top of `EPB_PHASE0_AUDIT_CHECKPOINT.md` and directly inline
at §3.0 and §11 Defect 0 -- the two places whose reasoning specifically
depended on PDF authority -- so a reader encounters the correction before
or immediately adjacent to the superseded conclusion, not only at the end
of the document. Phase 0's original text is preserved, not rewritten.

## 18. Package-vs-schema version distinction

`epb/__init__.py`'s `__version__` (`1.0.2`) now matches `pyproject.toml`'s
canonical version (`1.0.2`) -- D4's already-decided convention
(`pyproject.toml` as canonical source), now enforced in code. **Package
version is not the scientific compatibility gate.** Result-structure
compatibility is versioned independently: `RESULT_SCHEMA_VERSION = 1`
(`epb/scoring/result.py`) for `QuantityResult`/`quantities` shape, and
`OBSERVATION_SCHEMA_VERSION = 1` (`epb/adapters/base.py`) for
per-observation JSONL record shape. Neither was changed by this pass --
no material compatibility contradiction was found in either. `epb_version`
(`"epb_v1"`, `epb.__epb_version__`) is a separate, third concept: a
scoring-methodology generation label persisted into every `results.json`,
unrelated to either the package release version or the two schema
versions.

## 19. D2 resolution provenance qualifier

D2 (per-battery missing/invalid-observation denominator semantics) is
resolved by reference to Phase 2's already-frozen, independently
implemented and tested battery-specific evidence rules (§4.6-4.9 Mirror
Loop, §5.4-5.9 Confabulation, §6.4-6.5 Violation State, §7.4-7.8 Echo
Chamber) -- not by this final integration pass, or the decision-gap pass
immediately before it, freshly re-deriving all four battery denominator
rules from first principles. Confabulation's fidelity to its Phase 2 rule
was independently re-confirmed through this session's own extensive
implementation work; Mirror Loop, Violation State, and Echo Chamber's
code was not re-audited line-by-line during either the decision-gap pass
or this integration pass -- D2's closure rests on their already-completed
and independently verified Phase 2/3B work (each battery's own
`tests/test_*_phase3b*.py` suite, all passing), not a fresh re-derivation
here.

## 20. Observatory comparability warning

Persisted structured results currently expose: `epb_version`,
`RESULT_SCHEMA_VERSION`, `OBSERVATION_SCHEMA_VERSION`, per-quantity
identity (`quantity` key), `measurement_state`, `validation_status`,
`planned`/`applicable`/`usable`/`coverage`, `model_name`/`provider`, and
the full run config under `metadata.config`. **Missing**: no per-battery
scorer/spec-version identifier independent of the single global
`epb_version`; for Confabulation specifically, no field records whether a
given scored result used the general (no-archive) or explicit-archive
pathway -- `QuantityResult` has no such field (confirmed by direct
inspection of its dataclass fields: `quantity`, `measurement_state`,
`validation_status`, `value`, `planned`, `applicable`, `usable`,
`blocked`, `error`, `details`, `schema_version` -- no provenance-pathway
field). No implementation is proposed here (Observatory is explicitly not
built by this pass).

> **`SCORED` alone is insufficient for longitudinal comparability.**
> Observatory comparability eventually requires compatible
> battery/spec/scorer/coverage/adjudication/validation semantics, not
> merely a numeric value or `measurement_state == SCORED`.

Current output does not falsely claim comparability -- no
`observatory_comparable` flag or equivalent exists anywhere in the
codebase.

## 21. Known historical limitations

- `docs/methodology.md`'s References section no longer cites Echo Chamber
  Zero for the empirical Echo Chamber battery (D5a); no substitute
  citation was invented -- the method is described directly in that
  document's own "4. Echo Chamber" section.
- Only 3 of 5 historically labeled Confabulation run_ids have retained
  generation-script evidence (§14).
- `20251126_014253` carries the D3 warning (§16); the other four
  historical runs in the same results files predate the same frozen
  evidence semantics and share the same "not rescored" limitation, though
  no specific defect was identified for them in the Phase 0 audit.
- A pre-existing, deliberately-scoped-out legacy quirk (Phase 1 Area 4,
  unchanged by this pass): when zero battery files exist at all, the
  legacy `epb_truth` field is `0.0` (not `None`) and `certification` is
  `"incomplete"`, both still explicitly labeled
  `epb_truth_status: "legacy_noncanonical"`
  (`tests/test_cli_scoring_failure.py::test_missing_battery_file_behavior_is_unchanged`,
  `tests/test_final_integration_freeze.py::test_missing_battery_files_produce_no_structured_quantity`).
  The structured `quantities` dict is correctly empty in this case; only
  the legacy scalar path exhibits this quirk. Reopening it was out of
  scope for this pass (a legacy-aggregate semantic change, not a
  documentation/wiring fix) and is noted here as a known limitation, not
  silently fixed.
- Mirror Loop's `collapse_threshold`/`min_consecutive` and Violation
  State's `refusal_patterns` remain caller/config-overridable function
  parameters (with defaults matching their Phase 2-described values),
  unlike Confabulation's `CONFAB_CANONICAL_HEDGING_PATTERNS`, which was
  made a hardcoded, non-overridable module constant by an earlier,
  dedicated researcher decision. Whether Mirror Loop's/Violation State's
  equivalent parameters should receive the same treatment is an open
  question this pass discovered but did not resolve -- flagged as a
  remaining engineering limitation requiring a researcher decision, not
  silently decided either way here.
- `epb/scoring/exceptions.py::UnscoreableEvidenceError` and
  `epb/scoring/result_adapter.py::_run_single_quantity` are confirmed
  dead code (zero live call/raise sites anywhere in `epb/`, verified by
  grep) -- a Phase 1/early-3A transitional helper each of the four
  battery-specific `score_*_result` functions was rewritten away from.
  Classified **harmless dead compatibility code**: not misleading (each
  reference site explicitly says "no longer a... wrapper, for the same
  reason"), not dangerous (unreachable). Not deleted, per this pass's own
  instruction not to delete merely for tidiness.

## 22. vNext provenance requirement

> Future provenance must be established contemporaneously at run
> creation, not retroactively (§15).

Where this would eventually hook in (documentation only, not built by
this pass): `epb/runner/run_battery.py` (run execution), wherever a run
directory is first created under `runs/<run_id>/`, `config_used.yaml`'s
persistence at run start, and `score_confabulation`/`score_confabulation_result`'s
own entry points as the natural point to consult a future
contemporaneous-provenance manifest, if one is built.

## 23. Final integration test status

See the final report for exact regression counts, byte-diff results, and
the full 75-item accounting. Full suite at freeze-readiness evaluation
time: **380 passed, 1 xfailed, 0 failed** (baseline before this pass: 370
passed, 1 xfailed, 0 failed; 10 new tests added in
`tests/test_final_integration_freeze.py`, none removed).

A subsequent Final Documentation Closure pass corrected the three
remaining public-facing documentation files that still presented
`epb_truth`/certification without the legacy/noncanonical qualification
this document requires: `docs/api.md`, `docs/leaderboard.md`,
`docs/quickstart.md` (plus `docs/index.md`'s ECZ citation, found via that
pass's own sweep). No code, scorer, or test behavior changed; full suite
remained 380 passed, 1 xfailed, 0 failed.

A final API Documentation Accuracy Closure pass corrected the one
remaining live defect: `docs/api.md`'s Confabulation example documented
`score_confabulation(run_dir, hedging_patterns=[...])`, a keyword
argument removed from `score_confabulation`'s signature -- the example
would raise `TypeError` if run. Corrected to `score_confabulation(run_dir)`
plus a one-line note that hedging patterns are frozen internally, never
caller-supplied. The other three documented raw-scorer calls
(`score_mirror_loop`, `score_violation_state`, `score_echo_chamber`) were
directly checked against their live signatures via
`inspect.signature(...).bind(...)` and found valid; no other stale
signature exists in current-facing docs. Two narrow regression tests were
added (`tests/test_final_integration_freeze.py`:
`test_docs_api_md_has_no_known_removed_scorer_keywords`,
`test_docs_api_md_raw_scorer_examples_bind_against_live_signatures`) to
catch recurrence without a markdown parser. No production code, scorer
signature, or test-unrelated behavior changed; full suite: 382 passed, 1
xfailed, 0 failed.
