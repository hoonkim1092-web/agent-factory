# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:49
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: WARN

### Findings

1. [High] `work_kind` / `blast_radius` source path is not real in current pipeline
   - Section: "`RequestRouter.route()` → `ControlPlaneIntake.normalize()` → `NormalizedRequest{work_kind, change_impact, ...}` → `project_pipeline.py:963 generate_work_items(... work_kind=normalized.work_kind, blast_radius=...)`"
   - Issue: Current [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:963) calls `generate_work_items()` without any `normalized` object, and [prepare_brief()](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:706) only uses `ControlPlaneIntake()._recall_from_memory()`, not `normalize()`. The proposed call stack is architectural, not current.
   - Suggestion: Add an explicit Phase A step: either call `ControlPlaneIntake().normalize(...)` inside `prepare_documents()` and carry `work_kind/blast_radius` through `PreparedBrief/PreparedProject`, or derive them from `project_brief["route"]` with a documented fallback.

2. [High] Domain gate enforcement is attached to `approve()`, but execution checks `is_execution_open()`
   - Section: "read 시점: `ApprovalGate.approve()` 진입 직후" and "`approve()` False 반환 + `self.last_block_reason`"
   - Issue: Execution path in [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1263) gates on `gate.is_execution_open()`, then `read_block_decision()`. If a user approved before metadata or `domain-review.md` changed, the design does not say whether `is_execution_open()` revalidates the domain gate. Current `is_execution_open()` only checks approval snapshot validity via [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:253).
   - Suggestion: Domain-review validation must run in both `approve()` and `is_execution_open()` or be folded into `check_validity()`. Otherwise stale or missing domain review can pass after an older approval.

3. [Medium] `blast_radius` enum is still wrong in the design text
   - Section: "`change_impact.blast_radius` enum: `{\"local\", \"module\", \"cross_module\", \"system_wide\"}`"
   - Issue: Actual [core/control/change_impact.py](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16) and [line 35](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:35) use `"isolated"`, not `"local"`. The trigger uses `system_wide`, so this is not the main gate condition, but the validation criterion "`system_wide` 외 blast_radius 토큰 0건" will create false failures if implemented literally.
   - Suggestion: Replace `local` with `isolated` everywhere and define the allowed set once in the design.

4. [Medium] Bypass audit sink is unspecified and inconsistent with existing logging
   - Section: "`AF_SKIP_DOMAIN_REVIEW=1` ... bypass 발동 시 `.af_runtime/hook_events.log`에 기록 의무"
   - Issue: Existing review-gate bypass logs to `.af_review_queue/hook_events.log` via [scripts/review_gate.py](D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:22) and [scripts/hook_runner.py](D:/hoonProJect/worktrees/agent-factory/scripts/hook_runner.py:114). `ApprovalGate` currently emits RunEvents only when `run_id` exists and no-ops without it in [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:53). The new `.af_runtime/hook_events.log` path has no writer/schema.
   - Suggestion: Reuse `.af_review_queue/hook_events.log`, or specify a new helper, exact line format, and tests for `approve(run_id="")`.

5. [Medium] Design contradicts itself on `SkillPackBootstrapper` disposition
   - Section: "`옵션 A — 즉시 제거`" vs "`Q4 ... 결정: 옵션 B (영향 범위 최소)`"
   - Issue: §6.1/§7.3/§10.3 say immediate removal, but §12 Q4 still says Option B. Actual references exist in [tests/test_compact_step2.py](D:/hoonProJect/worktrees/agent-factory/tests/test_compact_step2.py:21), [af.spec](D:/hoonProJect/worktrees/agent-factory/af.spec:122), and `Master_Blueprint.md`.
   - Suggestion: Update Q4 to Option A and list the exact synchronized edits as mandatory, or keep Option B consistently.

### Missing from Design

- How `ControlPlaneIntake.normalize()` is invoked and how its result is persisted into `PreparedBrief` / `PreparedProject`.
- Whether domain-review validation is checked at execution time, not only approval time.
- Concrete schema and writer for `AF_SKIP_DOMAIN_REVIEW` audit logging.
- Tests for stale `domain-review.md` after approval.
- Frozen build verification for any new `core/*.py` module beyond the `af.spec` reminder.

### Positive Observations

- The design correctly avoids adding `domain-review.md` to `_DOC_FILES`, which prevents mass invalidation of existing work-items.
- It identifies the real current `generate_work_items()` caller at [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:963) and correctly notes that the current signature must change.