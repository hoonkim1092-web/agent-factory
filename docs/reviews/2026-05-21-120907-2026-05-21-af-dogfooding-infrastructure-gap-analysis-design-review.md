# Design Review: 2026-05-21-af-dogfooding-infrastructure-gap-analysis

> Source: docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md
> Date: 2026-05-21 12:09
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] Step 0(b) is under-scoped; it updates one emitter but leaves other user-facing order messages stale
   - Section: "`판정 1 (review-first 정책): check_pending_review.py:60 순서 뒤집기 + L56 t3_skip 분기도 동일 순서로 정합`"
   - Issue: The same agent-order instruction is also hardcoded in [.githooks/pre-commit](/D:/hoonProJect/worktrees/agent-factory/.githooks/pre-commit:65), [scripts/review_gate.py](/D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:528), and [scripts/hook_runner.py](/D:/hoonProJect/worktrees/agent-factory/scripts/hook_runner.py:318). The design only names `scripts/check_pending_review.py`, so implementation would still produce contradictory instructions.
   - Suggestion: Add a Step 0(b) callsite inventory and require updating all emitters plus tests: `tests/test_pending_review.py`, `tests/test_review_gate.py`, `tests/test_hook_runner*.py`, and `tests/test_phase1_blast_tier_invariant.py`.

2. [High] MAX_ROUNDS fix risks creating another duplicated truth
   - Section: "`판정 1 (Phase 1 의도): MAX_ROUNDS=5로 + review_gate.py:282 < 5로`"
   - Issue: The design correctly identifies `scripts/check_pending_review.py` has `MAX_ROUNDS = 2` and `scripts/review_gate.py` has a literal `< 2`, but the proposed fix is still two edits. That preserves the same failure mode: future drift between the hook notifier and gate enforcement.
   - Suggestion: Define one shared constant/helper, for example in `scripts/review_policy.py`, and import it from both `check_pending_review.py` and `review_gate.py`. If a new module is added, explicitly cover packaging/frozen-build impact and whether `af.spec` hiddenimports need adjustment.

3. [High] G8 conflates manual hook guidance with the actual background design-review runner
   - Section: "`판정 (단일 진실): 정책이 2026-05-01 변경으로 af-critic 제거를 명시 → 코드 정정`"
   - Issue: `scripts/check_design_pending.py` does print the wrong manual instruction, but the real watcher still runs critic + cross + aggregation for multi-provider reviews in [scripts/design_review_watcher.py](/D:/hoonProJect/worktrees/agent-factory/scripts/design_review_watcher.py:260). If the intent is only “Claude Code should spawn one af-cross-review agent,” the design should say not to change watcher internals. If the intent is “design review should never run critic,” then `design_review_watcher.py`, `core.review_runner`, prompts, and result schema are in scope.
   - Suggestion: Split G8 into two explicit scopes: UserPromptSubmit guidance only vs background review execution. Add tests for `check_design_pending.py` output and a non-change assertion for `design_review_watcher.py`, or include watcher changes deliberately.

4. [Medium] Step 1 claims permanent CRLF cleanup without specifying the permanent control
   - Section: "`git add --renormalize projects/agent_factory/   # 1회로 영구`"
   - Issue: `git add --renormalize` is not permanent by itself. Without `.gitattributes` or a documented generated-output policy, the same YAML/run artifact churn can return on another PC or tool run.
   - Suggestion: Add `.gitattributes`/line-ending policy verification, define whether `projects/agent_factory/runs/**` remains tracked, and include a post-step check: `git diff --check`, `git status --short`, and a second no-op regeneration run.

5. [Medium] R1 self-run experiment lacks rollback and scope-enforcement mechanics
   - Section: "`allowed_paths=[\"core/utils.py\"] report-only`" and "`git diff --name-only로 scope leak 측정`"
   - Issue: “report-only” does not prevent scope leaks in a real repo. The design also does not specify cleanup if AF edits additional files, mutates `.af_review_queue`, registry state, generated run artifacts, or leaves provider sessions behind.
   - Suggestion: Run R1 in a separate worktree, record a pre-run file manifest, enforce allowed paths as a hard post-run gate, and define cleanup/rollback commands for queue files, generated runs, and registry writes.

6. [Medium] Dependency/test impact is incomplete for the named changes
   - Section: "`Step 0 — 정책 정합`"
   - Issue: The design lists code files but not the test blast radius. Existing tests encode current order and tier requirements, for example [tests/test_pending_review.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_pending_review.py:75), [tests/test_review_gate_phase0.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_review_gate_phase0.py:330), and hook-runner tests.
   - Suggestion: Add a required verification set for Step 0: targeted pytest for pending review, review gate, hook runner, design pending, and phase invariant tests.

### Missing from Design

- Explicit distinction between user-facing hook messages and actual review execution architecture.
- Shared policy source for review order and max rounds.
- Frozen build packaging check if new shared scripts/modules are introduced.
- Windows path and shell compatibility for proposed grep commands; the repo is currently on PowerShell/Windows.
- Rollback plan for R1 self-run and generated artifacts.
- Concrete test matrix per step.

### Positive Observations

- The document correctly identifies real current-code conflicts for G7 and G8 against `CLAUDE.md`.
- It usefully separates G-axis governance dogfooding from R-axis self-execution dogfooding, which prevents premature investment in telemetry/frozen/sandbox work before R1 is proven.