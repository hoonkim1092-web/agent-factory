# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:10
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `blast_radius=="system"` will never fire
   - Section: "`blast_radius=="system"` 트리거 분기", `return blast_radius == "system"`
   - Issue: Current code uses `"system_wide"`, not `"system"`. Evidence: `core/control/change_impact.py` defines `"isolated" | "module" | "cross_module" | "system_wide"` and returns `"system_wide"`; `core/control/execution_policy.py` also checks `blast_radius == "system_wide"`.
   - Suggestion: Replace every design reference and test expectation with `system_wide`, or define a shared constant/normalizer. Add regression test for a `core/` change producing `system_wide` and requiring `domain-review.md`.

2. [Critical] Proposed `work_kind` / `blast_radius` frontmatter path is not wired into project work-item generation
   - Section: "`ControlPlaneIntake.normalize()` → `NormalizedRequest{work_kind, change_impact, ...}` → `work_item_generator.create_work_item()`"
   - Issue: `core/project_pipeline.py` does not call `ControlPlaneIntake.normalize()` for work-item generation; it only calls `ControlPlaneIntake()._recall_from_memory()` at `core/project_pipeline.py:709-710`. `generate_work_items()` receives `project_brief`, `role_plan`, and `task_board`, not `NormalizedRequest` (`core/work_item_generator.py:1072`). So the planned frontmatter source does not exist on this path.
   - Suggestion: Decide one concrete data path: either pass `NormalizedRequest` into `prepare_documents()` / `generate_work_items()`, or compute/persist `work_kind` and `blast_radius` into `project_brief` before `generate_work_items()` at `core/project_pipeline.py:963`.

3. [High] Enforcement location misses existing execution callers
   - Section: "`ApprovalGate.approve()` 진입 직후 frontmatter read ... domain-review.md verdict 검사"
   - Issue: Execution is guarded by `is_execution_open()`, not by `approve()` alone. `ProjectPipeline.execute()` calls `gate.is_execution_open()` (`core/project_pipeline.py:1268`), `MaintenancePipeline` also calls only `gate.is_execution_open()` (`core/control/maintenance_pipeline.py:313`), and `run_factory_cli.py resume` checks `is_execution_open()` before execution. A previously approved gate can remain open unless domain-review validity is enforced in `is_execution_open()` / `check_validity()`.
   - Suggestion: Put domain-review required/verdict validation inside `is_execution_open()` or `check_validity()`, and add tests for project execution, resume, and maintenance execution paths.

4. [High] `_DOC_FILES` unconditional expansion conflicts with staged rollout
   - Section: "`_DOC_FILES`에 `domain-review.md` 추가" and "단계 1: `requires_domain_review = False` ... 기존 work-item은 자동 통과"
   - Issue: `_DOC_FILES` currently drives snapshots, gate statuses, and invalidation in `core/approval_gate.py`. If `domain-review.md` is added unconditionally, existing approved work-items can be invalidated when the template file appears or when hashes differ, even while `requires_domain_review=False`.
   - Suggestion: Make domain-review part of the snapshot set only when the gate metadata says it is required, or add a separate optional-doc validation path that does not affect legacy approvals.

5. [Medium] `NEEDS_ADR` has no concurrency-safe workflow
   - Section: "`NEEDS_ADR` — 새 ADR 작성 후 진입 필요"
   - Issue: The design creates `docs/decisions/ADR-template.md` and `ADR-0001...`, but does not define ADR ID allocation, locking, status transition, or multi-PC conflict handling. This project already has file-lock utilities and multi-PC concerns; concurrent ADR creation can collide or produce duplicate IDs.
   - Suggestion: Use `core.file_lock.locked_file` or avoid sequential IDs for new ADRs by using `<date>-<slug>.md`. Define how `NEEDS_ADR` becomes `PASS`.

6. [Medium] Frozen build impact is under-specified
   - Section: "`core/brainstorm_prompts.py` (선택)" and "`af.spec` line 122 ... hiddenimports에서 제거"
   - Issue: The design adds a possible new Python module but does not state whether `af.spec` hiddenimports must include it. It also proposes deprecating/removing `core.skill_pack_bootstrapper`, which is currently referenced by `af.spec:122` and `tests/test_compact_step2.py`.
   - Suggestion: Add an explicit frozen-build checklist: hiddenimports additions/removals, `pytest tests/test_compact_step2.py`, and a PyInstaller smoke check for the approval gate path.

### Missing from Design

- Exact parser contract for `domain-review.md`: machine-readable verdict line, allowed values, and behavior for missing/multiple verdicts.
- Where `work_kind` / `blast_radius` are stored for existing work-items and target-path workspaces.
- Rollback toggle for domain gate enforcement, equivalent to existing `AF_SKIP_ESCALATION`.
- PROJECT_CONTEXT staleness handling in Phase A; deferring it to Phase D weakens the “single source of truth” goal.
- Tests for all execution callers: `ProjectPipeline.execute`, `run_factory_cli resume`, and `MaintenancePipeline`.

### Positive Observations

- The design correctly rejects direct Superpowers import and keeps AF provider-neutral.
- The design identifies `core/skill_pack_bootstrapper.py` as real dead/low-value code and lists the dependent test and `af.spec` entry that must be handled.