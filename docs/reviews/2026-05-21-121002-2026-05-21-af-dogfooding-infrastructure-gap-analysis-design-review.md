# Design Review: 2026-05-21-af-dogfooding-infrastructure-gap-analysis

> Source: docs/2026-05-21-af-dogfooding-infrastructure-gap-analysis.md
> Date: 2026-05-21 12:10
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] Step 0(b) misses multiple real caller/user-facing order sites
   - Section: “G7 agent 순서 정합 … `check_pending_review.py:60` … vs CLAUDE.md L127”
   - Issue: The design scopes the fix mainly to [scripts/check_pending_review.py](D:/hoonProJect/worktrees/agent-factory/scripts/check_pending_review.py:56), but the same test-first order is also hard-coded in [scripts/blast_radius.py](D:/hoonProJect/worktrees/agent-factory/scripts/blast_radius.py:207), [scripts/hook_runner.py](D:/hoonProJect/worktrees/agent-factory/scripts/hook_runner.py:319), [scripts/review_gate.py](D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:536), and [.githooks/pre-commit](D:/hoonProJect/worktrees/agent-factory/.githooks/pre-commit:65). Updating only `_agents_for_tier()` leaves conflicting instructions in commit-block output and helper APIs.
   - Suggestion: Define one canonical review-order source, or explicitly update all output/caller sites above. Add regression tests for emitted strings and `required_agents()`.

2. [High] T3-skip prompt sequence is underspecified under review-first order
   - Section: “check_pending_review.py:56 t3_skip 분기 — (b) 채택 시 함께 적용”
   - Issue: T3 skip is not just a string-order problem. [scripts/review_gate.py](D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:227) initially allows `[1,2]` for deterministic skip candidates before af-critic advisory exists, but [record_review_done](D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:345) can clear `fired_at` and expand back to Tier 3 when `t3_required` is `yes` or `unknown`. The design does not specify what the hook should print after af-critic runs first and changes the required tier set.
   - Suggestion: Add acceptance tests for `t3_required=no`, `yes`, and `unknown`, including re-prompt behavior for `af-cross-review`.

3. [Medium] Windows concurrent access risk is not addressed
   - Section: “Step 0 — 정책 정합 (네 항목 동시…)”
   - Issue: The design changes review queue behavior but does not address concurrency on Windows. Existing [review_gate._state_lock](D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:145) explicitly falls back to no-op on Windows, while `check_pending_review.py` and `record_review_done()` both read/write `.af_review_queue/pending_agent_review.json`. That conflicts with the checklist’s concurrent access and Windows support requirements.
   - Suggestion: Either implement a Windows-compatible lock using the existing project lock utility, or add a documented fail-open/fail-closed policy plus Windows race tests.

4. [Medium] CRLF renormalization plan is too broad and lacks containment
   - Section: “git add --renormalize projects/agent_factory/   # 1회로 영구”
   - Issue: This stages the entire project subtree, which code-review history shows already produces noisy `runs/**`, YAML, and dashboard churn. The design does not define pre/post checks, excluded generated paths, or rollback if unrelated files are staged.
   - Suggestion: Narrow the pathspec to known text config files, run `git diff --cached --name-only` verification, and explicitly exclude generated `runs/**` artifacts.

5. [Medium] Frozen-build validation is deferred without a minimum smoke contract
   - Section: “R8 frozen `af.exe` self-run 미검증 … 유효 — R1 이후”
   - Issue: The design postpones frozen validation, but Step 0 changes hook/review behavior that is part of the project’s developer control plane. Agent Factory has a documented frozen-build sensitivity around PyInstaller and hidden imports in [Master_Blueprint.md](D:/hoonProJect/worktrees/agent-factory/Master_Blueprint.md:1345). The design does not state whether these script-only changes are excluded from `af.spec`, nor what frozen smoke is enough before declaring dogfooding infrastructure adequate.
   - Suggestion: Add a minimal frozen compatibility statement: no `af.spec` change required for script-only hook text changes, and R1/R8 must include either `dist/af/af.exe --version` plus one self-run dry path, or an explicit deferral rationale.

### Missing from Design

- Explicit caller/callee update list for Step 0(b): `check_pending_review.py`, `blast_radius.py`, `hook_runner.py`, `review_gate.py`, `.githooks/pre-commit`, and tests.
- Windows lock behavior for `.af_review_queue/pending_agent_review.json`.
- Concrete tests for T3 skip advisory transitions.
- Staging safety plan for `git add --renormalize`.
- Frozen build smoke criteria and `af.spec hiddenimports` decision.

### Positive Observations

- The G/R split is useful and maps to real entrypoints: `.githooks/pre-commit → scripts/review_gate.py` vs `agent_launcher.py --workspace`.
- The document correctly rejects the stale `review_gate.py:214 round_count<2` claim and points to the current implementation path.