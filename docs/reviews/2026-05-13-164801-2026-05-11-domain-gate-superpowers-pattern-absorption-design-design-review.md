# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:48
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `normalized` data is not available at the proposed `project_pipeline.py` call site
   - Section: "`project_pipeline.py:963` 부근 ... `generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact['blast_radius'])`"
   - Issue: Actual [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:963) calls `generate_work_items(...)` from `prepare_documents()`, but no `normalized` object exists in that scope. `ControlPlaneIntake.normalize()` is not on this path; [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:710) only calls `_recall_from_memory()`. Implementing the design literally will raise `NameError` or require an unplanned API change.
   - Suggestion: Add `work_kind` / `blast_radius` to `PreparedBrief` or `project_brief` during `prepare_brief()`, or pass an explicit `normalized` object into `ProjectPipeline.prepare()/prepare_documents()` and update all callers.

2. [High] Rollout section reintroduces the wrong blast-radius token
   - Section: "`True for blast_radius == \"system\"`"
   - Issue: The design correctly says earlier that [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:29) emits `"isolated" | "module" | "cross_module" | "system_wide"`, and `_compute_blast_radius()` returns `"system_wide"` at [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:201). But §10.2 still says `"system"`. That creates a direct false-negative implementation path for the central gate condition.
   - Suggestion: Replace every `"system"` trigger reference with `"system_wide"` and add the planned grep test against the design plus code.

3. [High] Domain review can become stale after approval because it is excluded from validity checks
   - Section: "`_DOC_FILES`에 `domain-review.md` 추가하지 않음 ... 별도 read, snapshot 비교 로직과 분리"
   - Issue: Current [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:338) only invalidates approved gates by comparing `_DOC_FILES` snapshots. If `domain-review.md` is separate and only read in `approve()`, a reviewer can approve with `PASS`, then `domain-review.md` can be edited to `BLOCK` or deleted, and [is_execution_open()](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:242) will still pass if the existing five docs are unchanged.
   - Suggestion: Re-check the domain verdict in `is_execution_open()` for `blast_radius=="system_wide"`, or store a domain-review hash/verdict in `approval-gate.md` and invalidate when it changes.

4. [High] `last_block_reason` is not integrated with execution callers
   - Section: "`approve()` False 반환 + `self.last_block_reason` 속성에 사유 기록 ... caller는 `gate.last_block_reason`으로 분기"
   - Issue: Actual [ProjectPipeline.execute()](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1268) calls `gate.is_execution_open()`, not `approve()`, and returns generic `"approval_required"`. [MaintenancePipeline._check_approval_gate()](/D:/hoonProJect/worktrees/agent-factory/core/control/maintenance_pipeline.py:310) does the same. The design does not specify updates to those callers, so domain blocks will be indistinguishable from missing approval.
   - Suggestion: Add `last_block_reason` initialization to `ApprovalGate.__init__`, set it in both `approve()` and `is_execution_open()`, and update `ProjectPipeline.execute()` plus `MaintenancePipeline._check_approval_gate()` to return it.

5. [Medium] `skills/systematic_debugging/SKILL.md` alone may not register as an AF skill
   - Section: "`skills/systematic_debugging/SKILL.md` 신설 ... `core/skill_loader.py` 자동 발견"
   - Issue: AF skill loading goes through registry metadata conversion, not just arbitrary `SKILL.md` presence. Existing skills have `meta.yaml`, and [core/skill_registry.py](/D:/hoonProJect/worktrees/agent-factory/core/skill_registry.py:133) loads directories via `auto_detect_and_convert()`. A markdown-only skill needs proven frontmatter compatibility or a `meta.yaml`.
   - Suggestion: Specify `skills/systematic_debugging/meta.yaml` with category `debug`, keywords, `content_path: SKILL.md`, and add a registry test asserting the skill appears in `get_global_registry().get_all()`.

6. [Medium] Bypass logging path is underspecified and inconsistent with existing hooks
   - Section: "`AF_SKIP_DOMAIN_REVIEW=1` ... `.af_runtime/hook_events.log`에 기록"
   - Issue: Existing review-gate bypass logs are under `.af_review_queue/hook_events.log` in [scripts/review_gate.py](/D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:22) and [scripts/hook_runner.py](/D:/hoonProJect/worktrees/agent-factory/scripts/hook_runner.py:121). `ApprovalGate` currently emits RunEvents only when `run_id` exists, via [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:54). The design names a new log path but not the writer or schema.
   - Suggestion: Either reuse `.af_review_queue/hook_events.log` or define a new helper for `.af_runtime/hook_events.log`, including fields and tests for no-`run_id` cases.

### Missing from Design

- Concrete propagation plan for `work_kind` / `blast_radius` through `PreparedBrief`, `PreparedProject`, `project_brief`, or `route`.
- Caller updates for `ProjectPipeline.execute()`, `ProjectPipeline.run()` auto-approve, and `MaintenancePipeline._check_approval_gate()`.
- Staleness handling for `domain-review.md` after approval.
- Skill registration metadata for `skills/systematic_debugging`.
- Exact bypass audit writer and log location.
- Frozen-build verification for any new Python module remains conditional, but should be mandatory if `core/brainstorm_prompts.py` is created.

### Positive Observations

- The design correctly identifies the real blast-radius enum in `ChangeImpactProfiler` as `"system_wide"` in the main policy section.
- Keeping `domain-review.md` separate from `_DOC_FILES` avoids breaking existing work-item snapshot compatibility, but it needs an explicit freshness check.