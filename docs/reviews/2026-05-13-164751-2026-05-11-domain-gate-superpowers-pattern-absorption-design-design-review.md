# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:47
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `normalized` data path still does not exist
   - Section: "`project_pipeline.py:963 → generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact['blast_radius'])`"
   - Issue: Current `core/project_pipeline.py` does not create or carry `normalized`. `prepare_brief()` only calls `ControlPlaneIntake()._recall_from_memory()` around `core/project_pipeline.py:710`, not `ControlPlaneIntake.normalize()`. `PreparedBrief` / `PreparedProject` also have no `NormalizedRequest` field, and `generate_work_items()` is currently called with only `workspace`, `slug`, `project_brief`, `role_plan`, `task_board`, `run_id`.
   - Suggestion: Add a concrete integration step: call `ControlPlaneIntake.normalize()` in `prepare_brief()` or `prepare_documents()`, store it on `PreparedBrief`/`PreparedProject`, then pass `work_kind` and `blast_radius` into `generate_work_items()`. If impact needs the board, normalize after `task_board` exists.

2. [High] `system_wide` trigger will miss `new_project` and other unprofiled requests
   - Section: "`change_impact.blast_radius == 'system_wide' 단독 트리거 — work_kind 무관, false negative 최소화`"
   - Issue: `core/control/intake.py` only computes `change_impact` when `work_kind in ('maintenance', 'bugfix', 'refactor', 'feature_update')`. For `new_project`, `change_impact` is `{}` and `blast_radius` falls back to `"module"`, so the proposed work-kind-agnostic domain gate will not actually fire.
   - Suggestion: Either compute `ChangeImpactProfiler.profile()` for all work kinds, or define a separate deterministic trigger for domain gate, such as “new PROJECT_CONTEXT/ADR/domain docs present” or “target files include `core/`, `docs/decisions/`, or domain glossary changes.”

3. [High] `_DOC_FILES` policy contradicts itself
   - Section: "`_DOC_FILES`에 `domain-review.md` 추가하지 않음" vs "`core/approval_gate.py` ... `_DOC_FILES` 확장 + verdict 검사"
   - Issue: The design correctly says not to add `domain-review.md` to `_DOC_FILES`, but later repeats `_DOC_FILES 확장`. In current `core/approval_gate.py`, `_DOC_FILES` drives snapshots and gate statuses, so adding `domain-review.md` would make old work-items fail validity or produce unexpected snapshot keys.
   - Suggestion: Remove every `_DOC_FILES 확장` reference. Specify only `_DOMAIN_REVIEW_FILE = 'domain-review.md'`, read conditionally when `requires_domain_review()` is true, and exclude it from `compute_snapshots()` / `check_validity()`.

4. [Medium] Stale identifier and exception language remain in acceptance criteria
   - Section: "`blast_radius=='system' 단독 트리거`" and "`BlockedExecutionError 발생률`"
   - Issue: Earlier sections corrected the enum to `"system_wide"` and explicitly rejected `BlockedExecutionError`, but the cross-review checklist and rollout table still mention `"system"` and exception occurrence. This will produce implementation drift or tests for behavior the design says not to implement.
   - Suggestion: Replace remaining `"system"` references with `"system_wide"` and replace `BlockedExecutionError 발생률` with `approve()==False` plus `last_block_reason` metrics.

5. [Medium] Existing callers are not updated to handle domain-block reasons
   - Section: "`caller는 gate.last_block_reason으로 분기`"
   - Issue: Current callers do not branch on this. `agent_launcher.py` treats `approve()==False` as “approval-gate.md not found”, and `ProjectPipeline.prepare_and_execute()` ignores the return value from `_gate.approve()` before execution later fails as generic `approval_required`. The design adds `last_block_reason` but does not list caller changes.
   - Suggestion: Add required modifications for `agent_launcher.py`, `run_factory_cli.py`, and `ProjectPipeline.prepare_and_execute()` so `missing_domain_frontmatter`, `missing_verdict`, and `domain_review_blocked` are surfaced distinctly.

### Missing from Design

- Exact root policy for `PROJECT_CONTEXT.md` and ADRs when `target_path` is absolute: AF workspace `docs/` vs external `doc_root/docs/`.
- Migration behavior for existing `approval-gate.md` files without `work_kind` / `blast_radius`.
- Frozen build verification for new Python module candidates such as `core/brainstorm_prompts.py` if Phase C chooses that path.
- Tests for `new_project` and `target_path` mode, not only synthetic `system_wide` fixtures.

### Positive Observations

- The design correctly separates `domain-review.md` from normal snapshot invalidation in the main §3.2 text.
- The decision to keep `approve()` returning `bool` is compatible with the current `ApprovalGate` public API, provided callers are updated.