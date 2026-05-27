# Design Review: 2026-05-25-r1-complex-proof-result

> Source: docs/dogfooding/2026-05-25-r1-complex-proof-result.md
> Date: 2026-05-25 16:51
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Empty-plan failure is diagnosed, but the proposed implementation path misses the actual call chain
   - Section: “**F-PLAN-EMPTY** ... `research_brief`, `spec`, `plan` artifacts 모두 빈 구조(`steps: []`, `scope: []`)”
   - Issue: The document says to “grep LLM 호출 경로” in `core/research_brief.py`, `core/spec_compiler.py`, `core/planner.py`, but the current call chain is deterministic and already explains the failure: `core/dogfood.py:694-699` returns research context unchanged, `core/spec_compiler.py:117-123` only copies `scope` and `success_criteria` from the interview artifact, and `core/planner.py:211-223` creates steps only from `spec.scope` and premortem risks. If non-interactive interview returns no scope, the plan will be empty by construction.
   - Suggestion: Define hard invariants before implementation: block `SPEC` if `scope` or `success_criteria` is empty for code-change tasks, block `PLAN` if `steps` is empty, and update tests that currently codify empty plan success, especially [tests/test_dogfood.py](D:/warkSpaces/agent-factory/tests/test_dogfood.py:468) and [tests/test_dogfood.py](D:/warkSpaces/agent-factory/tests/test_dogfood.py:581).

2. [High] “COMPLETE” is treated as success even when no task work happened
   - Section: “**F-PHASE-COMPLETE** ... 빈 plan + 테스트 미완성에서도 `phase=complete`”
   - Issue: Current code makes this expected behavior: `_run_implement_phase()` returns `ok=True` for zero executed commands, `_run_verify_phase()` returns passed for an empty command list, `_run_review_phase()` defaults missing verification to passed, and `_run_merge_phase(..., "never")` sets `phase=COMPLETE` directly at [core/dogfood.py](D:/warkSpaces/agent-factory/core/dogfood.py:906). Tests also lock this in at [tests/test_dogfood_isolation.py](D:/warkSpaces/agent-factory/tests/test_dogfood_isolation.py:353).
   - Suggestion: Separate pipeline terminal state from task success, or require `task_outcome=passed|failed|no_op`. Completion should require non-empty criteria, at least one implementation artifact/change, and verification tied to those criteria.

3. [High] Scope-leak recommendation references a guard that does not protect dogfood worktrees
   - Section: “**F-SCOPE-LEAK 완화** ... R3 scope guard (`AF_SCOPE_GUARD_PATHS`)가 VERIFY 단계에서 작동하는지 확인”
   - Issue: `AF_SCOPE_GUARD_PATHS` is only registered in `agent_launcher.py` when `AF_SELF_RUN` is set, but `dogfood` is a known subcommand and is skipped by `_maybe_isolate_project_root_for_self_run()` at [agent_launcher.py](D:/warkSpaces/agent-factory/agent_launcher.py:101). The dogfood path instead commits all worktree changes in `finalize_dogfood_result()` and only applies merge policy later; `MergePolicy.allowed_paths` exists but is never derived from `spec.scope`.
   - Suggestion: Add a dogfood-native scope policy: persist allowed paths from `CompiledSpec.scope`, compare `git diff --name-only HEAD` and untracked files before `FINALIZE`, block out-of-scope changes before commit, and run the same check after `VERIFY` and `REVIEW`.

4. [Medium] The document omits current frozen-build impact even though touched modules are frozen entry-path modules
   - Section: “다음 단계 권고 ... `core/research_brief.py`, `core/spec_compiler.py`, `core/planner.py`”
   - Issue: These modules are real and already present in `af.spec` hiddenimports at [af.spec](D:/warkSpaces/agent-factory/af.spec:98), along with `core.premortem`, `core.triad`, `core.architect_agent`, and `core.dogfood`. If the fix introduces any new dogfood guard module, verifier module, or provider/agent wiring, the design must say whether `af.spec` needs updating.
   - Suggestion: Add an explicit dependency-impact table: existing modules to modify, new modules if any, tests to change, and `af.spec` hiddenimport status.

5. [Medium] The report says F-DIRTY is fixed, but does not close the recovery path for already-created dirty state
   - Section: “**F-DIRTY (수정 완료)** ... `.gitignore`에 추가 (`f896eeb9`)”
   - Issue: `.gitignore` now includes `planning/interview_brief.json`, and `core/interview.py:25-38` writes it atomically. That prevents future git dirty status for ignored files, but the design does not specify cleanup for existing tracked or already-present generated artifacts across PCs.
   - Suggestion: Add a recovery step: confirm `planning/interview_brief.json` is untracked, remove any accidentally tracked artifact with `git rm --cached` if needed, and include a regression test that dogfood isolation passes after non-interactive interview output.

### Missing from Design

- Exact phase gates for empty `research_brief`, empty `spec.scope`, empty `success_criteria`, empty `plan.steps`, and empty `verification_requirements`.
- A dogfood-native scope allowlist derived from `spec.scope`, enforced before `FINALIZE`.
- How non-interactive mode should produce structured scope and success criteria from a natural-language task.
- Test migration plan for existing tests that currently expect empty plans and empty verification to pass.
- Frozen build impact for any new modules added beyond existing `af.spec` entries.

### Positive Observations

- The report correctly identifies the real failure mode: formal pipeline completion does not imply task completion.
- It names the right subsystem files for the main investigation path: `core/research_brief.py`, `core/spec_compiler.py`, `core/planner.py`, and `core/dogfood.py`.