# Design Review: 2026-05-14-dev-workflow-paradigm-shift

> Source: docs/2026-05-14-dev-workflow-paradigm-shift.md
> Date: 2026-05-14 22:05
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Proposed “hook artifact exclusion” does not match the actual `new-files-added` path
   - Section: “review-gate에서 hook 실행 도중 생성된 파일(`docs/reviews/`, `docs/work-items/` 자동 산출물)을 new-files-added 검사에서 제외.”
   - Issue: Current gate only checks `py_files = [f for f in state["files"] if f.endswith(".py")]`, then compares those against the highest-tier snapshot in [scripts/review_gate.py](/Users/hoon/workTree/agent-factory/scripts/review_gate.py:190). Markdown artifacts under `docs/reviews/` or `docs/work-items/` cannot directly trigger `new-files-added`. Also [scripts/enqueue_agent_review.py](/Users/hoon/workTree/agent-factory/scripts/enqueue_agent_review.py:34) only enqueues `.py` review targets under `core/`, `scripts/`, selected root files, and top-level `skills/*/skill.py`.
   - Suggestion: Before implementation, capture an actual blocked `.af_review_queue/pending_agent_review.json` and identify the `.py` path absent from `files_snapshot`. Fix that exact source. If generated artifacts are involved, the likely bug is stale `state["files"]` or snapshot timing, not Markdown exclusion.

2. [High] `project_pipeline.py dry-run` is not a real supported mode
   - Section: “`project_pipeline.py`를 AF 자신에게 dry-run 적용”
   - Issue: [core/project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:1233) has `execute()` that performs approval checks, syncs the board, materializes roles, then calls `DynamicOrchestrator.run_project()` at line 1329. The compatibility `run()` auto-approves and executes at [core/project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py:1491). The only `--dry-run` found is `agent_launcher.py project sync-todo --dry-run`, which only prints todo sync output, not pipeline dogfooding.
   - Suggestion: Define dry-run precisely as either `prepare_brief + prepare_documents only` in a temp workspace, or add an explicit `dry_run`/mock-orchestrator path. Without that, “dogfooding” may run real agents and mutate repo state.

3. [High] “af-critic HIGH+ → cross-review 자동 승격” is underspecified and partly redundant
   - Section: “af-critic 결과가 HIGH 이상일 때 자동으로 Tier 3(af-cross-review) 진입”
   - Issue: For `blast_tier >= 2`, `af-cross-review` is already required by `_required_tiers_for()` in [scripts/review_gate.py](/Users/hoon/workTree/agent-factory/scripts/review_gate.py:162). For `blast_tier == 1`, `af-critic` is not required, so there is no af-critic result to promote. Current hook recording only maps fixed agents and records verdicts in [scripts/hook_runner.py](/Users/hoon/workTree/agent-factory/scripts/hook_runner.py:288); it does not parse finding severity or spawn another agent.
   - Suggestion: Clarify the intended scope: design-doc review flow, Tier 1 escalation, or runtime review queue. Specify the caller, severity parser, idempotency guard, and where the spawned `af-cross-review` task is requested.

4. [Medium] Worktree parallelization omits isolation details that matter for AF
   - Section: “`wt-fast-cleanup` … `wt-dogfood` … 각 worktree에서 독립적인 Claude Code 세션 운영”
   - Issue: The existing skill notes each worktree has independent gate state, but shared Git object DB and branch constraints. The design does not specify branch names, parent paths, hook setup, `.venv` reuse, `.af_review_queue` isolation, or cleanup/merge policy. This matters because review-gate and generated docs are workspace-local, while Git state is shared.
   - Suggestion: Add a concrete command plan: `git worktree add -b ... ../agent-factory-wt-fast-cleanup main`, per-worktree dependency/bootstrap step, branch naming, merge order, and cleanup criteria.

5. [Medium] Failure and partial-recovery cases are absent for the top-priority fix
   - Section: “매번 `AF_SKIP_REVIEW_GATE=1` 우회 강제 → review-gate 안전장치 사실상 무효화”
   - Issue: The design does not state what happens if the hook generates artifacts after review completion but before commit, if `pending_agent_review.json` is stale/corrupt, if multiple agents record concurrently, or if a commit partially succeeds and `post_commit_clear` misses cleanup. Existing review-gate code has lock/atomic-write paths, so the fix must preserve those invariants.
   - Suggestion: Add acceptance tests around `new-files-added`, generated artifact paths, stale queue recovery, and concurrent `record_review_done()`/enqueue behavior.

### Missing from Design

- Actual blocked queue example: `.af_review_queue/pending_agent_review.json`, `hook_events.log`, and the exact file causing `new-files-added`.
- Test plan: at minimum `tests/test_review_gate.py`, `tests/test_review_gate_phase0.py`, and `tests/test_hook_runner_builtins.py`.
- Clear integration point for HIGH+ escalation: `check_pending_review.py`, `hook_runner.py`, agent instructions, or manual CLI.
- Windows behavior: `_state_lock()` is no-op on Windows, so concurrent queue edits need explicit risk acceptance or a cross-platform lock.
- Frozen build impact: if new `core/*.py` modules are added for dogfooding/escalation, `af.spec` hiddenimports must be updated.
- Rollback plan for worktrees and generated review docs.

### Positive Observations

- The document correctly prioritizes the review-gate bypass problem before broader workflow changes.
- Rejecting a six-agent specialist split is consistent with the project context: `code-review.md` describes many cross-cutting subsystems and shared runtime/control/provider dependencies.