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

1. [Critical] R-axis entry command is not implementable as written
   - Section: ``R — 자기-실행 dogfooding ... `agent_launcher.py "<task>" --workspace .` ``
   - Issue: `agent_launcher.py` ad-hoc mode has no `--workspace` argument. The parser only defines `task`, `--mode`, `--fsa`, `--role`, and `--build` in [agent_launcher.py](D:/hoonProJect/worktrees/agent-factory/agent_launcher.py:821). The actual run path hardcodes `workspace=os.getcwd()` and `runtime_workspace=PROJECT_ROOT` at [agent_launcher.py](D:/hoonProJect/worktrees/agent-factory/agent_launcher.py:886). Step 3 would fail at argparse before testing anything.
   - Suggestion: Either change the experiment command to run from the target cwd, or add and test an explicit `--workspace` option before using it in the design.

2. [High] G7 dependency impact is under-scoped
   - Section: “G7 agent 실행 순서 정합 ... `check_pending_review.py:60` ... vs CLAUDE.md L127”
   - Issue: The design focuses on `scripts/check_pending_review.py`, but the old test-first order is also present in `scripts/blast_radius.py:207`, `scripts/hook_runner.py:319`, and `scripts/review_gate.py:536`. Tests also encode the old order at [tests/test_review_gate_phase0.py](D:/hoonProJect/worktrees/agent-factory/tests/test_review_gate_phase0.py:335). Updating only `_agents_for_tier()` leaves conflicting caller guidance in the gate failure path and required-agent helper.
   - Suggestion: Treat G7 as a small cross-file policy migration: `check_pending_review.py`, `blast_radius.py`, `hook_runner.py`, `review_gate.py`, and affected tests.

3. [High] R1 safety plan is report-only but uses the real repo/provider path
   - Section: “R3 scope guard 동시 — `allowed_paths=["core/utils.py"]` report-only”
   - Issue: A report-only guard does not prevent scope leaks. The same section proposes a real self-run that edits `.py`, and §2 flags R9 as “real repo + real provider.” If AF writes outside `core/utils.py`, the design only detects after damage. This is especially risky because `agent_launcher.py` currently passes the actual cwd as `workspace` while isolating only runtime state via `AGENT_PROJECT_ROOT`.
   - Suggestion: Make Step 3 blocking, not report-only: run in a temporary git worktree, enforce an allowlist before write/commit, and define rollback as `git diff --name-only` plus discard of the disposable worktree.

4. [Medium] G8 is labeled “1줄 fix” but has no regression test target
   - Section: “Step 0(d) G8 `check_design_pending.py` 안내 문구 정합 ← 1급 결함”
   - Issue: There is no test coverage for `scripts/check_design_pending.py` output. `rg` shows no `tests/*check_design_pending*`, while the stale behavior is exactly the printed contract at [scripts/check_design_pending.py](D:/hoonProJect/worktrees/agent-factory/scripts/check_design_pending.py:153). A one-line message fix can regress silently.
   - Suggestion: Add a focused test that creates `.af_review_queue/pending/design/*.json`, advances the quiet period, runs `main()`, and asserts only `af-cross-review` appears.

5. [Medium] G1 needs a shared constant, not another synchronized literal
   - Section: “G1 ... `MAX_ROUNDS = 2` ... `review_gate.py:282` ... 리터럴 `2`”
   - Issue: The design correctly identifies both sites, but the Step 0 fix still describes `review_gate.py:282 < 5` as a possible concrete edit. That preserves the drift pattern. The live code has `MAX_ROUNDS = 2` in [scripts/check_pending_review.py](D:/hoonProJect/worktrees/agent-factory/scripts/check_pending_review.py:28) and a separate `< 2` stale-review condition in [scripts/review_gate.py](D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:279).
   - Suggestion: Move the round cap to one shared constant or helper used by both scripts, then update `tests/test_pending_review.py` and `tests/test_review_gate_phase0.py`.

### Missing from Design

- Exact rollback path for R1 self-run if files outside the allowlist are modified.
- Provider failure handling for self-run experiments: unavailable CLI, auth expiry, quota/rate limits, and timeout.
- Full caller/message inventory for G7: `blast_radius.py`, `hook_runner.py`, `review_gate.py`, and tests.
- Frozen build check for any new import/helper introduced while sharing G1 policy constants.
- Regression test plan for `check_design_pending.py`.

### Positive Observations

- The document correctly separates governance dogfooding from self-execution dogfooding, which prevents mixing hook-policy fixes with agent-runtime proof.
- G1/G7/G8 are grounded in current code-vs-policy conflicts, and the G8 finding matches the actual live print path in `scripts/check_design_pending.py`.