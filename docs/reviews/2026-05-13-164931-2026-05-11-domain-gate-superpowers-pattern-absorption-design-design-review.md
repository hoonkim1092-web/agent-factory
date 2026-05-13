# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:49
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `normalized` data flow does not exist in `project_pipeline.py`
   - Section: "`project_pipeline.py:963` ... `generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact.get(...))`" and "`ControlPlaneIntake.normalize()`"
   - Issue: Current `core/project_pipeline.py` never calls `ControlPlaneIntake.normalize()`. It only calls `ControlPlaneIntake()._recall_from_memory()` at `core/project_pipeline.py:710`. At `core/project_pipeline.py:963`, `generate_work_items()` is called without any `normalized` variable in scope.
   - Suggestion: Add an explicit normalization step in `prepare_brief()` or `prepare_documents()`, store `work_kind`/`blast_radius` in `PreparedBrief`, and pass those fields to `generate_work_items()`. Avoid re-running impact profiling if `ControlPlaneIntake` already did it.

2. [High] Domain review is only checked during approval, so later changes can bypass it
   - Section: "`read 시점: ApprovalGate.approve() 진입 직후`" and "`_DOMAIN_REVIEW_FILE` ... `_DOC_FILES`에 `domain-review.md` 추가하지 않음"
   - Issue: `project_pipeline.execute()` only calls `gate.is_execution_open()` at `core/project_pipeline.py:1268`. `is_execution_open()` validates `_DOC_FILES` snapshots via `check_validity()`, but the design deliberately excludes `domain-review.md`. If `domain-review.md` is deleted or changed from `PASS` to `BLOCK` after approval, execution can still proceed.
   - Suggestion: Re-check domain review in `is_execution_open()` or `check_validity()` when `blast_radius=="system_wide"`. Keep it outside `_DOC_FILES` if needed, but enforce a separate fail-closed runtime check.

3. [High] Bypass audit path conflicts with the existing hook log location
   - Section: "`AF_SKIP_DOMAIN_REVIEW=1` ... bypass 발동 시 `.af_runtime/hook_events.log`에 기록 의무"
   - Issue: Existing review-gate logging uses `.af_review_queue/hook_events.log` (`scripts/hook_runner.py:121`, `scripts/review_gate.py:22`). The design introduces `.af_runtime/hook_events.log` without defining a writer or reconciling the two audit sinks.
   - Suggestion: Reuse the existing `.af_review_queue/hook_events.log` path or define a shared logging helper and update tests to assert the exact sink.

4. [Medium] Work-item base path ignores `target_path` / external project docs
   - Section: "`base path`: `workspace/docs/work-items/<slug>`"
   - Issue: Current code supports external doc roots: `core/work_item_generator.py:1082-1087` uses `project_brief["target_path"]`, and `ApprovalGate(doc_root, slug, runtime_workspace=workspace)` is created at `core/work_item_generator.py:1234`. `PreparedProject.gate()` also uses `_effective_doc_root()` at `core/project_pipeline.py:95`. The design’s `workspace/docs/work-items` statement is incomplete for multi-PC / target project workflows.
   - Suggestion: Specify `effective_doc_root = target_path if absolute else workspace` everywhere, and add a test where `target_path != workspace`.

5. [Medium] Dead-code decision contradicts itself
   - Section: "`옵션 A — 즉시 제거`" / "`옵션 B(DEPRECATED 주석 유지)는 ... 폐기`" versus Q4 "`옵션 B (영향 범위 최소)`"
   - Issue: Sections 6.1, 7.3, and 10.3 adopt immediate removal of `core/skill_pack_bootstrapper.py`, but Open Question Q4 still selects Option B. Implementation planning can diverge.
   - Suggestion: Remove Q4 or update it to Option A, and keep the affected files list: `core/skill_pack_bootstrapper.py`, `tests/test_compact_step2.py`, `af.spec`, `Master_Blueprint.md`.

6. [Medium] Skill usage acceptance criterion assumes logging that `skill_loader` does not perform
   - Section: "`core/skill_loader.py` 자동 발견 + `data/skill-usage.jsonl` 호출 기록"
   - Issue: `core/skill_loader.py` loads/selects skills but does not append to `skill-usage.jsonl`. Usage events are written through `SkillFeedbackLoop.record_*()` in `core/skill_feedback.py`.
   - Suggestion: Change the criterion to “registry load succeeds” plus an explicit `SkillFeedbackLoop.record_selection()` or `record_runtime_result()` integration point.

### Missing from Design

- Exact owner for computing `work_kind`/`blast_radius`: `ProjectPipeline`, `RequestRouter`, or `ControlPlaneIntake`.
- Runtime enforcement path after approval, not just during `approve()`.
- A precise audit log helper/path for `AF_SKIP_DOMAIN_REVIEW`.
- Tests for `target_path` / external project doc roots.
- Concurrency behavior when `domain-review.md` changes while approval or execution is running.

### Positive Observations

- The design correctly avoids adding `domain-review.md` to `_DOC_FILES`, which prevents mass invalidation of existing work-items.
- It correctly uses the actual `blast_radius` enum value `system_wide` from `core/control/change_impact.py`, not the earlier incorrect `system` token.