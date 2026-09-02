# EPB Phase 1 — Foundational Observation-Integrity Repair: Implementation Checkpoint

Date: 2026-08-28
Author: Claude Code (single session; no sub-agents used)
Scope: narrow engineering repair only, per the Phase 1 governing prompt. No battery denominator, numerator, coverage-threshold, insufficient-evidence-score-mapping, aggregate, or certification semantics were decided.

---

## 1. Repository identity / starting state

| Field | Value |
|---|---|
| Working directory | `/Users/bentleydevilling/Desktop/epb-benchmark` |
| Git root | `/Users/bentleydevilling/Desktop/epb-benchmark` |
| Origin | `https://github.com/Course-Correct-Labs/epb-benchmark.git` |
| Branch | `claude/build-epb-v1-019fiQ3GAZQXNXmUKdctF6VT` |
| HEAD (before and after this phase) | `a3732e8299da4286b1651d7f68bb654a3db80577` — unchanged; all Phase 1 work is uncommitted working-tree changes |
| Same tree as Phase 0/0.5? | Yes — confirmed identical path/origin/branch/HEAD at the start of this phase |

Pre-existing untracked files at the start of this phase (none created by this phase, none touched by it): `EPB_PHASE0_AUDIT_CHECKPOINT.md`, `MANIFEST.in`, `epb_config_gpt5.yaml`, `spec/`, `EPB_PHASE0_5_VNEXT_DESIGN.md`.

## 2. Phase 0 / Phase 0.5 artifacts read

Both `EPB_PHASE0_AUDIT_CHECKPOINT.md` and `EPB_PHASE0_5_VNEXT_DESIGN.md` were already present in full in this session's context (written earlier in the same conversation) and were used as the evidentiary and design basis for this phase, per the governing prompt's instruction that this phase's own Sec 0 amendments (June 2026 PDF non-authority, Echo Chamber status frozen, unusable-observation principle, no Mirror Loop metric expansion, no confabulation judge redesign, pyproject.toml as canonical version, no `epb_truth`/certification redesign) supersede any contrary or broader Phase 0.5 recommendation.

## 3. Files changed

**Modified:**
- `epb/adapters/base.py` — added `ObservationKind`, `Observation`, `OBSERVATION_SCHEMA_VERSION`; `ModelClient.generate`/`generate_chat` now typed to return `Observation`.
- `epb/adapters/openai_adapter.py` — response classification (`_classify_openai_response`); SDK exceptions caught and classified, not raised.
- `epb/adapters/anthropic_adapter.py` — response classification (`_classify_anthropic_response`); fixes the Checkpoint Defect 3 `content[0].text` `AttributeError` by checking block `.type` first; SDK exceptions caught and classified.
- `epb/runner/run_battery.py` — all four `run_*_battery` functions: per-task try/except (Area 3 isolation), persist `Observation.to_dict()` records plus `observation_schema_version`/`task_status`.
- `epb/cli/main.py` — `score` command: scoring exceptions no longer coerced to `0.0`; recorded in `scoring_failures`; aggregate/certification computation omitted (not silently substituted) when any battery's scoring failed.
- `epb/scoring/mirror_loop_scoring.py`, `confab_scoring.py`, `violation_scoring.py`, `echo_scoring.py` — read the new typed-observation JSONL shape (with legacy bare-string compatibility); raise `UnscoreableEvidenceError` when any task's relevant evidence is not fully `VALID_TEXT`, computing nothing for that run; otherwise compute byte-for-byte the same formulas as pre-Phase-1.
- `tests/test_openai_adapter.py` — fixed pre-existing mocks (`Mock()` auto-attribute truthiness previously would have misclassified every response as a refusal under the new logic) and added classification coverage.
- `tests/test_scoring_robustness.py` (pre-existing file, predates this phase) — its two success-path fixtures (`test_score_with_minimal_config`, `test_score_with_partial_scoring_config`) used bare-string JSONL records; updated to the typed `{"text": ..., "kind": "valid_text"}` shape as a direct, necessary consequence of Sec 20's legacy-provenance correction (see Sec 20) — not an unrelated refactor.

**New:**
- `epb/scoring/exceptions.py` — `UnscoreableEvidenceError`.
- `tests/test_adapter_base.py`, `tests/test_anthropic_adapter.py`, `tests/test_cli_scoring_failure.py`, `tests/test_run_battery_isolation.py`, `tests/test_scoring_unscoreable_evidence.py`.

No other file, in this repository or any other, was modified.

## 4. Final Observation contract

```python
class ObservationKind(str, Enum):
    VALID_TEXT = "valid_text"
    EMPTY_TEXT = "empty_text"
    WHITESPACE_ONLY_TEXT = "whitespace_only_text"
    PROVIDER_REFUSAL = "provider_refusal"
    TRUNCATED = "truncated"
    NON_TEXT_TERMINAL = "non_text_terminal"
    PROVIDER_ERROR = "provider_error"
    ORCHESTRATION_ERROR = "orchestration_error"
    LEGACY_UNKNOWN = "legacy_unknown"  # only ever produced reading a pre-Phase-1 artifact

@dataclass
class Observation:
    text: str
    kind: ObservationKind
    finish_reason: Optional[str] = None
    error: Optional[str] = None
```

This is the taxonomy the governing prompt's Sec 4.1 sketched, unchanged in shape (no states added or merged beyond what was already proposed there). Grounded directly against the installed SDKs (see Sec 6 below), not guessed.

`OBSERVATION_SCHEMA_VERSION = 1` is persisted in every new-shape JSONL record, independent of `epb.__version__`/`pyproject.toml` (Sec 0.6).

## 5. Provider-state mappings implemented

### OpenAI (grounded against `openai==3.6.0`, installed in the scratch venv, see Sec 14)

| Signal observed | → ObservationKind |
|---|---|
| `message.refusal` populated | `PROVIDER_REFUSAL` |
| `finish_reason == "content_filter"` | `PROVIDER_REFUSAL` |
| `finish_reason in {"tool_calls","function_call"}`, no content | `NON_TEXT_TERMINAL` |
| `content is None`/`""`, `finish_reason == "length"` | `TRUNCATED` |
| `content is None`/`""`, otherwise | `EMPTY_TEXT` |
| `content.strip() == ""` (non-empty) | `WHITESPACE_ONLY_TEXT` |
| non-empty content, `finish_reason == "length"` | `TRUNCATED` (text preserved) |
| non-empty content, otherwise | `VALID_TEXT` |
| SDK raises `openai.OpenAIError` (any subclass) | `PROVIDER_ERROR`, caught, not raised |

A model-authored refusal written as ordinary text (no structured `.refusal`, no `content_filter`) remains `VALID_TEXT` — refusal *language* alone is never turned into a failure state (governing prompt Sec 4.1 explicit instruction).

### Anthropic (grounded against `anthropic==1.2.0`)

| Signal observed | → ObservationKind |
|---|---|
| `stop_reason == "refusal"` | `PROVIDER_REFUSAL` |
| empty `content` list, `stop_reason in {"max_tokens","model_context_window_exceeded"}` | `TRUNCATED` |
| empty `content` list, otherwise | `EMPTY_TEXT` |
| `content[0].type != "text"` | `NON_TEXT_TERMINAL` — this is the direct fix for Checkpoint Defect 3 |
| text block, empty text, truncating stop_reason | `TRUNCATED` |
| text block, empty text, otherwise | `EMPTY_TEXT` |
| text block, whitespace-only | `WHITESPACE_ONLY_TEXT` |
| text block, non-empty, truncating stop_reason | `TRUNCATED` (text preserved) |
| text block, non-empty, otherwise | `VALID_TEXT` |
| SDK raises `anthropic.AnthropicError` (any subclass) | `PROVIDER_ERROR`, caught, not raised |

`model_context_window_exceeded` is folded into `TRUNCATED` (smallest taxonomy that preserves the needed distinction — both are length/context cutoffs) rather than given its own kind.

## 6. How the provider mappings were grounded (no live calls)

A new, isolated scratch venv (Sec 14) had `openai>=1.0.0`/`anthropic>=0.18.0` installed per `pyproject.toml`'s unpinned floor, resolving to `openai==3.6.0`/`anthropic==1.2.0`. Both SDKs' Pydantic response schemas were introspected directly (`ChatCompletionMessage.model_json_schema()`, `Choice.model_json_schema()['properties']['finish_reason']['enum']`, `Message.model_json_schema()['properties']['stop_reason']`, the `ContentBlock` type union, and `openai.OpenAIError`/`anthropic.AnthropicError` exception hierarchies) to confirm exact field names and enum values before writing the classifiers. No live API call was made or needed.

## 7. Task-level failure handling (Area 3)

Each of the four `run_*_battery` functions in `run_battery.py` now wraps its entire per-task body in `try/except Exception`. On an exception that was not already classified into an `Observation` inside the adapter (i.e., a genuinely unanticipated error — the adapters catch expected `OpenAIError`/`AnthropicError` internally and return `PROVIDER_ERROR` rather than raising), the task's failure is recorded as an explicit `task_status: "failed"` record with a `failure: {kind: "orchestration_error", error_type, error_message}` block (error message truncated to 500 chars, derived only from `str(exception)` — no raw provider object or environment data, so no secret can leak through this path), and the loop continues to the next task. The outer per-battery `try/except` in `run_benchmark.py` (Checkpoint Defect 3's original whole-battery-abort mechanism) is left in place as an unused-in-practice defense-in-depth backstop; it is no longer the primary failure path.

## 8. Score-time error handling (Area 4)

`epb/cli/main.py::score` no longer sets a battery's score to `0.0` when its `score_*` call raises. Each failure is instead recorded in a `scoring_failures` dict (`{battery: {error_type, error_message}}`), persisted verbatim into `results.json`. When `scoring_failures` is non-empty, `epb_truth` and `certification` are both left `None` rather than computed from the (now three-quarters-empty) `scores` dict or silently routed into the pre-existing `"incomplete"` path — the latter would have conflated "battery never ran" with "battery's scoring code raised," two different situations. The pre-existing `"incomplete"`/`0.0` path for a genuinely-missing battery file is untouched and still fires only in that unchanged, original circumstance.

## 9. Scoring-boundary correction (mid-phase)

An initial implementation of the four `score_*` functions unwrapped every `Observation`'s `.text` unconditionally and fed it into the existing metric functions regardless of `kind`, only appending an `observation_kinds` field to the output afterward — this made the pre-existing empty-observation defect *traceable* without *fixing* the information/scientific-integrity boundary Sec 4.2 requires, and a companion test asserted `collapsed == True` for an all-`EMPTY_TEXT` Mirror Loop sequence as though that were a settled, correct result. This was caught and corrected before proceeding (see the correction report earlier in this session's transcript for full detail). The corrected design:

- Each `score_*` function first partitions every task into "fully valid-text evidence" or "blocked" (task-level failure record, or any relevant observation whose kind is not `VALID_TEXT`).
- If any task is blocked, the function raises `epb.scoring.exceptions.UnscoreableEvidenceError` — carrying `battery`, and a `blocked` list of `{task_id, reason, task_status, observation_kinds}` — and computes nothing: no numerator, no denominator, no partial result from the remaining valid tasks.
- Only when zero tasks are blocked does the original formula run, on exactly the same text values a pre-Phase-1 bare-string artifact would have supplied.
- `Violation State` blocks only on its **benign**-turn observations, since non-benign (violation-trigger) turn responses were never fed into `has_refusal_phrase` before Phase 1 either — and a task with **zero** benign turns is not blocked (no applicable evidence exists to be unusable, unchanged from before).
- `UnscoreableEvidenceError` is an ordinary `Exception` subclass, so it is caught by the exact same Area 4 CLI path as any other scoring exception — no CLI-side special-casing was needed.

## 10. Tests added

| File | Covers |
|---|---|
| `tests/test_adapter_base.py` | `Observation`/`ObservationKind` round-trip; legacy bare-string classification boundary — **as of Sec 22, every bare string (non-empty, whitespace-only, or exact-empty alike) → `LEGACY_UNKNOWN`**, text preserved exactly, never guessed provider cause |
| `tests/test_openai_adapter.py` (extended) | All 8 `ObservationKind` states reachable from mocked OpenAI responses; refusal-language-in-ordinary-text stays `VALID_TEXT`; provider exceptions classified not raised; pre-existing token-param tests unchanged |
| `tests/test_anthropic_adapter.py` (new) | Same state coverage for Anthropic, including the direct Defect 3 regression (leading non-text content block does not raise `AttributeError`); closes the "no Anthropic adapter test file exists at all" gap the Checkpoint flagged |
| `tests/test_run_battery_isolation.py` | Task-level isolation for all four battery runners (one task fails, next task's calls still happen, failure persisted with `task_status`/`failure` detail); persistence to output file; end-to-end proof that a mixed valid/failed run blocks scoring (`UnscoreableEvidenceError`) rather than silently excluding the failed task |
| `tests/test_cli_scoring_failure.py` | A genuine scoring exception (malformed JSONL) and an `UnscoreableEvidenceError` (unusable evidence) both land in `scoring_failures`, never `0.0`; `epb_truth`/`certification` stay `None`, never silently `"incomplete"`; the pre-existing missing-file `"incomplete"` path is proven unchanged |
| `tests/test_scoring_unscoreable_evidence.py` | For all four batteries: every non-`VALID_TEXT` kind (empty, whitespace, truncated, provider error, task-failure record, legacy bare-string of any shape) blocks scoring with correct diagnostics; one bad task blocks the whole battery, not just itself; fully-valid-text runs (typed only — see Sec 20) score identically to pre-Phase-1 formulas; Violation State's "no applicable evidence" non-blocking case |

## 11. Pre-change test results

Command: `python -m pytest tests/ -v` (scratch venv, `epb` installed editable per this working tree)

**61 passed, 1 xfailed** (`test_detect_collapse_borderline`, pre-existing, commit `8d70bab`), 1 unrelated Click deprecation warning.

## 12. Post-change test results

Same command, same environment.

**132 passed, 1 xfailed** (same pre-existing xfail), 1 unrelated Click deprecation warning. Net new: 71 tests, 0 regressions, 0 new failures.

## 13. Behavior intentionally unchanged because of Sec 5

- Mirror Loop's ΔI formula, collapse threshold, `min_consecutive`, and `epb_phi` formula: byte-for-byte identical to pre-Phase-1 (Sec 5.10). No semantic-similarity/embedding/TF-IDF/n-gram/entropy/plateau signal was added.
- Confabulation's fabrication/persistence definitions, hedging detection, and the LLM-judge-with-regex-fallback judging strategy: unchanged (Sec 0.5/5.11). No intervention conditions were added; no new judge was wired into the runtime.
- Violation State's contamination/refusal-phrase definitions: unchanged (Sec 5.12). No cross-modal infrastructure was added.
- Echo Chamber's TF-IDF construct and canonical/experimental status: unchanged (Sec 0.2/5.5) — its code was touched only for the same typed-observation/blocking mechanism as the other three, nothing about its scoring definition or citation.
- `epb_truth`'s formula, default weights, and `get_certification_level`'s thresholds/names: unchanged (Sec 5.7/5.8). The only change at that layer is *whether* they get computed at all for a given run (Sec 8/9 above) — not how.
- `pyproject.toml`'s package version and the pre-existing `pyproject.toml`(1.0.2)/`epb.__version__`(1.2.0) divergence (Checkpoint Sec 1 A4): untouched, per Sec 0.6's instruction not to perform unrelated version cleanup.
- No production benchmark task was added, removed, or rewritten; `spec/*.jsonl` files are untouched (Sec 5.13).
- No historical run directory, `results/epb_scores_*.json`, or `results/confab_initial_labels.json` was read for scoring purposes by any test (all tests use `tmp_path` fixtures) or otherwise modified (Sec 5.9).

## 14. Scratch environment

Path: `/private/tmp/claude-501/-Users-bentleydevilling-Desktop/0ef3ead1-39fb-483e-ae7c-4e88c405d404/scratchpad/epb_phase1_venv`

Newly created for this phase (per Sec 2.1), contains no pre-existing project data, is not inside any project repository. Used to: (a) introspect the OpenAI/Anthropic SDK response schemas offline to ground the `Observation` classification logic in real field names rather than guessed ones (Sec 6 above), and (b) install `epb-benchmark` editable (`pip install -e ".[dev]"`) to run the real test suite before and after this phase's changes. Left in place per Sec 2.1 (no cleanup requiring an ambiguous/broad deletion was attempted).

## 15. Live API spend

**$0.00.** No live provider/model API call was made or was necessary; every question this phase needed answered (SDK response shapes, classification correctness, task isolation, scoring-boundary behavior) was answerable from the SDKs' own type definitions and from mocked/synthetic fixtures.

## 16. Git status before and after

**Before** (start of this phase): clean tracked tree; untracked `EPB_PHASE0_AUDIT_CHECKPOINT.md`, `MANIFEST.in`, `epb_config_gpt5.yaml`, `spec/`, `EPB_PHASE0_5_VNEXT_DESIGN.md` (all pre-existing, none created by any phase of this session's work).

**After** (updated to reflect Sec 20's narrow correction; this document's own write not yet included):
```
Changes not staged for commit:
  modified:   epb/adapters/anthropic_adapter.py
  modified:   epb/adapters/base.py
  modified:   epb/adapters/openai_adapter.py
  modified:   epb/cli/main.py
  modified:   epb/runner/run_battery.py
  modified:   epb/scoring/confab_scoring.py
  modified:   epb/scoring/echo_scoring.py
  modified:   epb/scoring/mirror_loop_scoring.py
  modified:   epb/scoring/violation_scoring.py
  modified:   tests/test_openai_adapter.py
  modified:   tests/test_scoring_robustness.py

Untracked files:
  EPB_PHASE0_5_VNEXT_DESIGN.md          (pre-existing)
  EPB_PHASE0_AUDIT_CHECKPOINT.md        (pre-existing)
  EPB_PHASE1_FOUNDATIONAL_REPAIR.md     (Phase 1, this document)
  MANIFEST.in                           (pre-existing)
  epb/scoring/exceptions.py             (Phase 1)
  epb_config_gpt5.yaml                  (pre-existing)
  spec/                                 (pre-existing)
  tests/test_adapter_base.py            (Phase 1)
  tests/test_anthropic_adapter.py       (Phase 1)
  tests/test_cli_scoring_failure.py     (Phase 1)
  tests/test_run_battery_isolation.py   (Phase 1)
  tests/test_scoring_unscoreable_evidence.py  (Phase 1)
```
HEAD unchanged throughout: `a3732e8299da4286b1651d7f68bb654a3db80577`. No commit, push, tag, branch, stash, reset, or clean operation was performed at any point in this phase, including during the Sec 20 narrow correction.

## 17. Unresolved engineering defects encountered (not fixed, out of scope)

- `docs/scoring.md` still describes the old bare-string formulas and the old "excluded from EPB Truth if a battery didn't run" partial-aggregation behavior; it was not updated in this phase (documentation updates were not in the Sec 4 authorized scope).
- The example scripts (`examples/epb_run_openai.py`, `examples/epb_run_anthropic.py`) were surveyed and confirmed to need no changes — they only call `run_benchmark`/`score_*` at the top level and never touch `Observation` directly — but they will now surface `UnscoreableEvidenceError` (via their existing outer `try/except` + `traceback.print_exc()` + `sys.exit(1)`) on any run containing unusable evidence, which is new, correct behavior but untested end-to-end against a live provider in this phase (no live calls were made).
- The `leaderboard/` submission path (`epb submit`) was not touched. **Corrected claim** (the original version of this section incorrectly asserted a `KeyError`, without checking the actual code): `epb/cli/main.py::submit` reads `results_data['scores']['epb_truth']` (line ~376) — since Sec 8's design always keeps the `epb_truth` key present in `results["scores"]` (its *value* is `None` when `scoring_failures` is non-empty, the key is never omitted), this indexing does **not** raise `KeyError`. The actual, verified behavior: `submit` prints `"EPB Truth: None"` and then proceeds to `requests.post(...)`, submitting a payload containing `"epb_truth": null` to the configured leaderboard URL with no validation that the run scored successfully. `epb submit` assumes a numeric `epb_truth`; behavior with `None` requires later handling/verification — no fix was made to `submit` in this phase, since none was required to complete an authorized Phase 1 item, and fixing it would touch submission/aggregate-adjacent behavior this phase does not own.

## 18. GO/NO-GO recommendation for the next (semantic) phase

**GO**, with the same framing Phase 0.5 used: the foundational repair work (Areas 1, 2, 3, 4) is complete, tested, and does not decide any of the researcher-level questions listed in Phase 0.5 Sec 19 (D1–D6) or this phase's Sec 5. The next phase's job is exactly what Sec 0.3/Sec 5.4 deferred: deciding, per battery, what `UnscoreableEvidenceError`'s underlying condition should mean for a numerator, denominator, and coverage calculation — i.e., Phase 0.5 Sec 10's per-battery missing/invalid-observation semantics decisions (D2), now with a concrete, tested mechanical hook (`blocked` task lists with `reason`/`observation_kinds`) to build that logic on top of, rather than a defect to work around.

## 19. Filesystem and repository safety confirmation

- Canonical EPB repository: `/Users/bentleydevilling/Desktop/epb-benchmark`.
- Origin: `https://github.com/Course-Correct-Labs/epb-benchmark.git`.
- Branch: `claude/build-epb-v1-019fiQ3GAZQXNXmUKdctF6VT`.
- HEAD before this phase: `a3732e8299da4286b1651d7f68bb654a3db80577`. HEAD after this phase: `a3732e8299da4286b1651d7f68bb654a3db80577` (unchanged — all work is uncommitted).
- No existing repository, directory, or file outside the canonical EPB repository was modified.
- No other Course Correct Labs repository was modified.
- No existing sibling non-Git project directory, including `epb-testing/`, was modified.
- Temporary scratch environment created: `/private/tmp/claude-501/-Users-bentleydevilling-Desktop/0ef3ead1-39fb-483e-ae7c-4e88c405d404/scratchpad/epb_phase1_venv` (left in place per Sec 2.1).
- No destructive or broad filesystem command (`rm -rf`, `find -delete`, recursive `mv`/`cp`, broad globs) affected any parent, sibling, or project path at any point in this phase. The only filesystem deletion performed anywhere in this phase was `rm` of one file this session itself had created earlier in the same phase (`tests/test_scoring_observation_provenance.py`, replaced by `tests/test_scoring_unscoreable_evidence.py` during the mid-phase correction) — not a pre-existing file, not outside the canonical repo. No filesystem deletion of any kind occurred during the Sec 20 narrow correction.
- Git/GitHub state-changing operations performed: **none**, at any point across the whole phase including Sec 20. No commit, push, tag, release, stash creation/application/drop, reset, clean, or destructive checkout/restore occurred.
- Final `git status`: see Sec 16 above — eleven pre-existing tracked files modified in the working tree, four pre-existing untracked files unchanged, seven new untracked files added by this phase (`epb/scoring/exceptions.py`, five new test files, and this document itself). Nothing is staged; nothing is committed.

## 20. Narrow provenance correction (post-freeze review)

Before Phase 1 was frozen, a review caught a real defect in the legacy-artifact handling built during this phase: `Observation.from_dict` classified any non-empty, non-whitespace pre-Phase-1 bare string as `VALID_TEXT`. This invented historical provider/runtime provenance that was never retained — Phase 1's own OpenAI/Anthropic classifiers prove why non-emptiness alone can't establish that: a non-empty response can still be `TRUNCATED` when finish/stop metadata says so, and a legacy bare string carries no such metadata at all.

**Frozen rule applied:** `VALID_TEXT` means the observation system directly observed enough provider/runtime information (finish/stop-reason evidence ruling out truncation, a tool-call/non-text terminal state, or a structured refusal signal) to classify a response as valid text. A legacy bare string never satisfies that evidentiary standard solely because it is non-empty.

**Fix applied**, in `epb/adapters/base.py::Observation.from_dict`:
- A legacy bare string that is whitespace-only (`text.strip() == "" and text != ""`) is still classified `WHITESPACE_ONLY_TEXT` — this is a pure text-shape fact, and Phase 1's own *live* classifiers already assign this kind from text shape alone, without consulting finish/stop-reason evidence even when it's available, so applying the same shape test to a legacy string invents no additional provenance beyond what the live classifiers already treat as sufficient.

  **SUPERSEDED by Sec 22 below.** The premise in the bullet above ("live classifiers assign this kind from text shape alone... without consulting finish/stop-reason evidence") stopped being true once Sec 21's provider-terminal-precedence fix landed: the live classifiers now give truncation/refusal/non-text-terminal evidence precedence over whitespace shape whenever that evidence is available. Sec 22 corrects this bullet's conclusion: legacy whitespace-only strings are also `LEGACY_UNKNOWN`, not `WHITESPACE_ONLY_TEXT`. This paragraph is left as the historical record of what Phase 1 did *at that point*; it is not the current behavior.
- Every other legacy bare string — **exact-empty and non-empty alike** — is classified `LEGACY_UNKNOWN`. (Exact-empty was already `LEGACY_UNKNOWN` before this correction, per the original Phase 0 ambiguity finding; only the non-empty case changed, from `VALID_TEXT` to `LEGACY_UNKNOWN`.)
- Original stored text is preserved byte-for-byte in all cases; no provider cause, terminal state, or completion status is invented for either the exact-empty or non-empty case.

**Consequence, stated plainly:** because Phase 1's whole-battery blocking rule (Sec 9) treats any non-`VALID_TEXT` evidence as blocking, and because *no* legacy bare string can be `VALID_TEXT` anymore, a fresh `epb score` run against **any** pre-Phase-1 run directory — even one that was 100% clean, non-empty text throughout — will now raise `UnscoreableEvidenceError` rather than silently reproducing a number. This is the correct, intended effect of combining the corrected provenance rule with the existing fail-closed boundary, not a bug. It does not retroactively change any already-persisted historical `results.json`/`results/epb_scores_*.json` file (Sec 5.9 is untouched) — it only changes what happens if someone re-runs `epb score` fresh against an old run directory today.

**Whole-battery blocking is explicitly temporary Phase 1 scaffolding, not a discovered scientific rule.** This is now stated directly in: `UnscoreableEvidenceError`'s class docstring (`epb/scoring/exceptions.py`), `score_mirror_loop`'s docstring (the canonical explanation the other three battery docstrings point back to), the three other battery scorers' docstrings (one-line pointers back to `score_mirror_loop`'s), and the module docstring plus the two whole-battery-block tests in `tests/test_scoring_unscoreable_evidence.py`. It exists only because computing a score from the remaining valid tasks would itself have silently decided a denominator question (Sec 5.1) this phase does not own — it is not a claim that one bad task, of any kind including `LEGACY_UNKNOWN`, *should* invalidate a whole battery's score.

**Tests updated:**
- `tests/test_adapter_base.py`: `test_legacy_nonempty_string_is_valid_text` replaced by `test_legacy_nonempty_string_is_legacy_unknown_not_valid_text`, asserting text is preserved byte-for-byte and `kind == LEGACY_UNKNOWN` (not `VALID_TEXT`). The whitespace-only and exact-empty legacy tests were already correct and are unchanged.
- `tests/test_scoring_unscoreable_evidence.py`: the three tests that had asserted a legacy non-empty bare string scores identically to a typed `VALID_TEXT` record (`test_mirror_loop_legacy_bare_strings_score_exactly_as_typed`, `test_confabulation_legacy_bare_strings_score_exactly_as_typed`, `test_echo_chamber_legacy_bare_string_final_text_scores_exactly_as_typed`) were replaced with `..._block_not_score_as_valid_text` / `..._blocks_not_scores_as_valid_text` variants, each asserting only: original text is preserved, the observation kind is `LEGACY_UNKNOWN`, and the run reaches `UnscoreableEvidenceError` with the expected `task_id`/`observation_kinds` in `blocked`. None of the replacement tests assert what `LEGACY_UNKNOWN` should eventually mean for pathology polarity, numerator, denominator, coverage, exclusion, battery score, aggregate score, or certification. The module docstring and the two "one bad task blocks the whole battery" tests were updated to state explicitly that whole-battery blocking is temporary scaffolding, not a discovered rule.
- `tests/test_scoring_robustness.py` (pre-existing, predates any phase of this session's work): its two success-path fixtures used bare-string JSONL records for `mirror_loop`/`confabulation`/`violation_state`/`echo_chamber`. Under the corrected rule these are `LEGACY_UNKNOWN` and would have (correctly) started raising `UnscoreableEvidenceError`, breaking two tests whose actual purpose is verifying config-default-merging robustness, not legacy-string provenance. Fixed by converting the fixtures to the typed `{"text": ..., "kind": "valid_text"}` record shape — a direct, minimal, necessary consequence of the provenance correction, not a scope-expanding rewrite; the tests' assertions and intent are otherwise untouched.

**`epb submit` claim corrected:** see the updated Sec 17 above — the original claim of a `KeyError` was checked against the actual code (`epb/cli/main.py::submit`) and found to be wrong; the real behavior is that it prints `"EPB Truth: None"` and proceeds to POST the payload, with no crash and no validation.

**Test results for this narrow correction:**
- Before this correction (i.e., the Phase 1 state at the point this correction began — same as Sec 12's "post-change" count): **132 passed, 1 xfailed** (133 collected).
- Immediately after applying the `Observation.from_dict` fix, before updating `tests/test_scoring_robustness.py`: **130 passed, 2 failed, 1 xfailed** (133 collected) — the two failures were `test_score_with_minimal_config` and `test_score_with_partial_scoring_config`, exactly the pre-existing tests described above, confirmed via their actual `AssertionError` output (`'mirror_loop_phi' in {'epb_truth': None}` and `1 == 5`) before any fix was applied to them.
- After fixing `tests/test_scoring_robustness.py`'s fixtures: **132 passed, 1 xfailed** (133 collected) — same total count as before this correction, 0 regressions, 0 net-new tests (three tests renamed/replaced in `test_adapter_base.py`/`test_scoring_unscoreable_evidence.py`, two pre-existing tests repaired in `test_scoring_robustness.py`).

**Files changed by this narrow correction:** `epb/adapters/base.py` (the `from_dict` fix itself), `epb/scoring/exceptions.py` (scaffolding-status docstring note), `epb/scoring/mirror_loop_scoring.py`/`confab_scoring.py`/`violation_scoring.py`/`echo_scoring.py` (scaffolding-status docstring pointers only — no logic change), `tests/test_adapter_base.py`, `tests/test_scoring_unscoreable_evidence.py`, `tests/test_scoring_robustness.py`. No other file was touched by this correction.

**`git diff --stat` for the files touched by this correction** (shown against the committed HEAD, since this phase has no intermediate commit boundary to diff against — these are the same files' *cumulative* Phase 1 diffs, which for `mirror_loop_scoring.py`/`confab_scoring.py`/`violation_scoring.py`/`echo_scoring.py` also include Sec 9's earlier mid-phase correction, not just this narrow one):
```
 epb/adapters/base.py               | 155 ++++++++++++++++++++++++++++++++++++-
 epb/scoring/confab_scoring.py      |  58 ++++++++++++--
 epb/scoring/echo_scoring.py        |  56 +++++++++++++-
 epb/scoring/mirror_loop_scoring.py |  71 ++++++++++++++---
 epb/scoring/violation_scoring.py   |  87 ++++++++++++++++-----
 tests/test_scoring_robustness.py   |  48 ++++++++----
 6 files changed, 417 insertions(+), 58 deletions(-)
```

**Full cumulative Phase 1 `git diff --stat`** (all changes across the whole phase, this correction included):
```
 epb/adapters/anthropic_adapter.py  | 105 +++++++++--
 epb/adapters/base.py               | 155 ++++++++++++++++-
 epb/adapters/openai_adapter.py     |  97 ++++++++++-
 epb/cli/main.py                    |  51 +++++-
 epb/runner/run_battery.py          | 345 ++++++++++++++++++++++++-------------
 epb/scoring/confab_scoring.py      |  58 ++++++-
 epb/scoring/echo_scoring.py        |  56 +++++-
 epb/scoring/mirror_loop_scoring.py |  71 +++++++-
 epb/scoring/violation_scoring.py   |  87 ++++++++--
 tests/test_openai_adapter.py       | 200 +++++++++++++++++----
 tests/test_scoring_robustness.py   |  48 ++++--
 11 files changed, 1034 insertions(+), 239 deletions(-)
```

No Phase 2 architecture, semantics, or scope was opened by this correction. No battery denominator, numerator, coverage, exclusion, aggregate, certification, or eventual scientific treatment of `LEGACY_UNKNOWN` (or any other non-`VALID_TEXT` kind) was decided.

## 21. Final direct-code verification pass (pre-freeze)

A verification-only pass re-inspected the actual current code (not this document's prose) against four criteria: (A) legacy provenance, (B) provider-terminal-state precedence, (C) scoring-boundary containment, (D) no disguised exclusion. A-D all passed except one confirmed defect under B:

**Confirmed defect, both adapters:** whitespace-only content/text combined with an available truncating finish/stop reason (`finish_reason == "length"` for OpenAI; `stop_reason in {"max_tokens", "model_context_window_exceeded"}` for Anthropic) was classified `WHITESPACE_ONLY_TEXT`, not `TRUNCATED`, because each classifier's whitespace-shape check was reached before its truncation check for non-empty content. Real, observed provider-terminal evidence was silently overridden by a generic text-shape check. Exact-empty content + truncation was unaffected (already correctly `TRUNCATED` via a separate `not content`/`not text` branch); only the whitespace-only sub-case was wrong.

**Classification:** purely Phase-1 mechanical (classifier branch reordering only) — no denominator/numerator/coverage/exclusion/aggregate/certification decision was required or made to fix it.

**Fix applied:** in both `_classify_openai_response` and `_classify_anthropic_response`, the truncation check (and, for OpenAI, the non-text-terminal check) was moved before the whitespace/empty text-shape checks, so any available terminal evidence takes precedence regardless of what the leftover text looks like. Verified against every existing test case by hand-tracing branch order before applying; all pre-existing adapter tests pass unchanged.

**Tests added:** `test_classify_truncation_outranks_whitespace_shape` in both `tests/test_openai_adapter.py` and `tests/test_anthropic_adapter.py` — the exact precedence case that had been missing coverage, which is how the defect went undetected through the earlier mid-phase and narrow-provenance corrections.

**Files changed by this verification pass:** `epb/adapters/openai_adapter.py`, `epb/adapters/anthropic_adapter.py`, `tests/test_openai_adapter.py`, `tests/test_anthropic_adapter.py`. No other file was touched.

**Test results:** before this pass, 132 passed / 1 xfailed (134 collected including the not-yet-added tests would be 133 — see below). After adding the 2 precedence tests and applying the fix: **134 passed, 1 xfailed** (135 collected), 0 regressions. Both new tests independently verified passing via a targeted `-k "truncation_outranks"` run.

Criteria A, C, D were re-verified directly against the current code (not re-derived from this document) and found unchanged/correct from the prior narrow-provenance correction — no further code changes were needed for those three.

No Phase 2 semantics were opened by this verification pass.

## 22. Final legacy-whitespace provenance correction

Sec 20's fix left one carve-out: a legacy bare string that was whitespace-only was still classified `WHITESPACE_ONLY_TEXT`, on the premise that the live classifiers assigned that kind from text shape alone, without needing finish/stop-reason evidence. Sec 21's precedence fix (applied immediately afterward, in the same phase) made that premise false: the live classifiers now give truncation/refusal/non-text-terminal evidence precedence over whitespace shape whenever that evidence is available (`"   "` + `finish_reason == "length"` → `TRUNCATED`, not `WHITESPACE_ONLY_TEXT`). A pre-Phase-1 bare string never retained that evidence either way, so a stored whitespace-only legacy string proves only that the retained text is whitespace — not that the original observation state was genuinely `WHITESPACE_ONLY_TEXT` rather than a masked truncation or other terminal condition.

**Corrected rule (final):** every pre-Phase-1 bare string — empty, whitespace-only, or non-empty alike — is `LEGACY_UNKNOWN`. Text-shape facts (empty/whitespace/non-empty) remain directly inspectable via `.text`; none of them are promoted to a provider/runtime-state kind (`VALID_TEXT`, `EMPTY_TEXT`, `WHITESPACE_ONLY_TEXT`, `TRUNCATED`, or any other) for a legacy artifact.

**Fix applied**, in `epb/adapters/base.py::Observation.from_dict`:
```python
if isinstance(data, str):
    # Every pre-Phase-1 bare string -- empty, whitespace-only, or
    # non-empty alike -- is LEGACY_UNKNOWN: none of them can be
    # promoted to EMPTY_TEXT, WHITESPACE_ONLY_TEXT, or VALID_TEXT
    # without inventing provider/runtime provenance the historical
    # artifact never recorded. Original text preserved exactly.
    return Observation(text=data, kind=ObservationKind.LEGACY_UNKNOWN)
```
The prior three-way branch (whitespace-shape check, then a separate empty/non-empty split) was collapsed to this single unconditional return. The dict-record branch (typed observations, including live-classifier-assigned `WHITESPACE_ONLY_TEXT`) is completely untouched — this correction affects bare-string legacy reading only.

**Live adapter classifiers unchanged**, per A6: this correction is scoped strictly to legacy-artifact provenance; `_classify_openai_response`/`_classify_anthropic_response` (Sec 21) were not touched, and no new defect in them was found while making this change.

**Tests updated:**
- `tests/test_adapter_base.py`: `test_legacy_whitespace_only_string_is_classified_from_text_alone` (asserted `WHITESPACE_ONLY_TEXT`) replaced by `test_legacy_whitespace_only_string_is_legacy_unknown_not_whitespace_only_text` (asserts `LEGACY_UNKNOWN`, text preserved byte-for-byte).
- Searched all test files for any other bare-string (non-dict) whitespace-only legacy fixture that might depend on the old classification — found none. Every whitespace-only fixture in `tests/test_scoring_unscoreable_evidence.py` already uses the typed `{"text": "   ", "kind": "whitespace_only_text"}` record shape, not a bare string, so none needed updating. No scoring-boundary test assertion changed.

**Documentation corrected:** `Observation.from_dict`'s docstring rewritten to state the corrected rule and explain why the prior whitespace carve-out's premise no longer held (see the method source for full text). In this document, Sec 20's now-superseded whitespace bullet is annotated in place (not silently rewritten) pointing here, and Sec 10's `tests/test_adapter_base.py` table row is corrected.

**Test results:** 134 passed, 1 xfailed (135 collected) — identical counts to immediately before this correction. 0 regressions, 0 new failures, 1 test renamed/replaced (net test count unchanged).

**Stage A stop condition:** not triggered. This correction was purely mechanical (one classification branch in one method, one dependent test, one documentation update) and required no denominator/numerator/coverage/exclusion/aggregate/certification decision.

No Phase 2 semantics were opened by this correction.
