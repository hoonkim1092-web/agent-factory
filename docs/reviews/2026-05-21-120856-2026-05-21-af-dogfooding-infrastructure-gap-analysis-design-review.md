# Design Review: 2026-05-21-af-dogfooding-infrastructure-gap-analysis

> Source: docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md
> Date: 2026-05-21 12:08
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: WARN

### Findings

1. [High] Agent order change misses real callers and tests
   - Section: "`Step 0(b) G7 agent ... check_pending_review.py:60 ... L56 t3_skip ...`"
   - Issue: The design only names `scripts/check_pending_review.py`, but the same order is encoded in `scripts/blast_radius.py:194` via `required_agents()`, asserted in `tests/test_review_gate_phase0.py:330`, printed by `scripts/review_gate.py:527`, and printed again by `.githooks/pre-commit:64`. Implementing only the listed edits leaves CLI/hook guidance and tests saying `af-test-runner -> af-critic -> af-cross-review`.
   - Suggestion: Add a single ordered-agent helper or constant and update `check_pending_review.py`, `blast_radius.py`, `review_gate.py`, `.githooks/pre-commit`, and tests together.

2. [High] `max_rounds` decision is underspecified for gate behavior
   - Section: "`Step 0(a) G1 max_rounds ... MAX_ROUNDS=5 ... review_gate.py:282 < 5 ...`"
   - Issue: `scripts/check_pending_review.py:28` has `MAX_ROUNDS = 2`, while `scripts/review_gate.py:279` hard-codes `< 2`. The design notices both, but leaves the actual policy unresolved as “option 1 / option 2”. Implementation cannot safely start until the policy owner decides whether CLAUDE.md is wrong or code is wrong.
   - Suggestion: Resolve the policy first. Then implement a shared `MAX_REVIEW_ROUNDS` constant used by both scripts and test stale review behavior at boundary values `1`, `2`, and selected max.

3. [Medium] Design-review hook change conflicts with actual hook output but lacks test coverage
   - Section: "`Step 0(d) G8 check_design_pending.py ... af-cross-review 1개만`"
   - Issue: `scripts/check_design_pending.py:9` and `:151` currently instruct `af-critic + af-cross-review`, while `CLAUDE.md:114-115` says only `af-cross-review`. The design correctly identifies this, but does not mention adding or updating tests for `check_design_pending.py`. I found no direct test coverage for `[af-design-review-pending]` output in the scanned test references.
   - Suggestion: Add a focused test that creates `.af_review_queue/pending/design/*.json`, advances quiet time, runs `check_design_pending.main()`, and asserts the output only names `af-cross-review`.

4. [Medium] Windows concurrency remains a known gap for modified review queue paths
   - Section: "`Step 0 ... dogfooding R축 진입 전 필수`"
   - Issue: These changes touch hook state paths that rely on `review_gate._state_lock()`. In `scripts/review_gate.py:143-163`, Windows falls back to no-op locking. The project context explicitly calls out Windows support, and these hooks modify `.af_review_queue/pending_agent_review.json` concurrently from `enqueue_agent_review.py`, `check_pending_review.py`, and `hook_runner.py`.
   - Suggestion: Either document that Step 0 does not solve Windows concurrent RMW risk, or include a small cross-platform file lock fix before changing review queue semantics.

5. [Medium] Step 1 uses a Unix-oriented command without Windows-safe procedure
   - Section: "`Step 1 ... git add --renormalize projects/agent_factory/`"
   - Issue: The repo runs on Windows and has recurring CRLF/LF churn. The design says to renormalize but does not specify `.gitattributes`, verification commands, or how to avoid staging generated `projects/agent_factory/runs/**` artifacts. Prior code-review history repeatedly flags run artifacts and line-ending noise as review blockers.
   - Suggestion: Add a concrete Windows-safe normalization plan: define `.gitattributes`, run `git add --renormalize`, verify with `git diff --cached --name-only`, and explicitly exclude generated `runs/**` unless intended.

6. [Low] R-axis self-run experiment lacks rollback and scope enforcement details
   - Section: "`Step 3 R1 .py self-run ... allowed_paths=[\"core/utils.py\"] report-only`"
   - Issue: “report-only” scope guard is not enough for a real dogfooding experiment that edits the same repo. The design does not specify rollback if AF edits outside `core/utils.py`, if provider execution partially succeeds, or if registry writes happen despite `AF_DISABLE_REGISTRY_WRITE=1`.
   - Suggestion: Require a separate worktree, pre/post `git diff --name-only`, hard fail on out-of-scope paths, and cleanup instructions for `.af_review_queue`, `runs/`, and generated artifacts.

### Missing from Design

- Exact test list to update: at minimum `tests/test_pending_review.py`, `tests/test_review_gate_phase0.py`, and a new/updated `check_design_pending` test.
- A single source of truth for review agent order and max rounds.
- Windows-safe locking strategy or explicit deferral for `.af_review_queue` concurrent writes.
- Frozen build impact statement. Script-only changes may not need `af.spec`, but Step 3 mentions frozen `af.exe` later and should state whether it is in or out of scope.
- Rollback plan for the self-run dogfooding experiment.

### Positive Observations

- The document correctly separates governance dogfooding (`G`) from self-execution dogfooding (`R`), which prevents mixing hook-policy fixes with agent-runtime experiments.
- It grounds several claims in current file paths and line-level evidence, especially `check_pending_review.py`, `review_gate.py`, `check_design_pending.py`, and `CLAUDE.md`.