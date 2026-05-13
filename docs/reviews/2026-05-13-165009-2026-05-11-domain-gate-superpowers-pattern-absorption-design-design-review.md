# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:50
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Proposed `normalized.work_kind`/`blast_radius` caller does not exist in the project pipeline
   - Section: "`project_pipeline.py:963` ... `generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact[\"blast_radius\"])`"
   - Issue: `ProjectPipeline.prepare_documents()` calls `generate_work_items()` at [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959), but there is no `normalized` object in that scope. The current pipeline only calls `ControlPlaneIntake()._recall_from_memory()` in `prepare_brief()` at [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:706), not `ControlPlaneIntake.normalize()`. `AgentFactory.run()` passes only `route` into the project pipeline.
   - Suggestion: Add a concrete propagation design: either store `NormalizedRequest` on `PreparedBrief`/`PreparedProject`, or call `ControlPlaneIntake.normalize(task_input, workspace, route, board)` after `task_board` exists and pass explicit `work_kind`/`blast_radius` from that object.

2. [High] `target_path`/`doc_root` compatibility is contradicted by the design’s base path claim
   - Section: "base path: `workspace/docs/work-items/<slug>` (= `ApprovalGate.work_item_dir`)"
   - Issue: Existing work-item docs are not always under `workspace`. `generate_work_items()` switches to `project_brief["target_path"]` when absolute at [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1079), creates docs under `doc_root`, and initializes `ApprovalGate(doc_root, slug, runtime_workspace=workspace)` at [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1230). The design’s fixed `workspace/docs/...` assumption will miss gates for multi-PC or external target projects.
   - Suggestion: Define domain-review lookup relative to `PreparedProject._effective_doc_root()` / `ApprovalGate.workspace`, not the runtime workspace. Add a `target_path` fixture test.

3. [High] Metadata will be lost unless every `_render()` path is redesigned
   - Section: "`approval-gate.md ## Metadata` ... `- work_kind: refactor` / `- blast_radius: system_wide`"
   - Issue: `_parse()` can already read arbitrary metadata lines at [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:455), but `_render()` only writes `work_item`, `approver`, `status`, and `last_updated` at [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:521). `approve()` rewrites the file through `_render()` at [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:208), so added metadata will disappear after approval unless preserved.
   - Suggestion: Add a `metadata: dict[str, str]` parameter to `_render()` and thread it through `initialize()`, `approve()`, `invalidate()`, and `apply_verification_verdict()`.

4. [High] The design still contains a `system` vs `system_wide` contradiction
   - Section: "`return blast_radius == \"system_wide\"`"
   - Section: "Phase 2 ... `True for blast_radius == \"system\"`"
   - Issue: Code uses `"system_wide"` in `ImpactProfile` and `_compute_blast_radius()` at [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:35) and [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:217). The migration section still says `"system"`, which will create a fail-open false negative if implemented literally.
   - Suggestion: Replace every design occurrence of `blast_radius == "system"` with `blast_radius == "system_wide"` and add the grep test before implementation.

5. [Medium] The proposed trigger source is unreliable for pre-implementation work-items
   - Section: "`change_impact.blast_radius == \"system_wide\"` ... sole trigger"
   - Issue: `ChangeImpactProfiler` derives impact from current `git diff` plus filenames in the user input. At planning time, that can reflect unrelated dirty files, no files at all, or generated docs rather than the intended future implementation. Also `ControlPlaneIntake` only profiles impact for `maintenance`, `bugfix`, `refactor`, and `feature_update` at [core/control/intake.py](/D:/hoonProJect/worktrees/agent-factory/core/control/intake.py:108); greenfield/forced project requests default to `"module"`.
   - Suggestion: For new work-items, compute intended blast radius from planned artifacts/modules in the generated task board, or explicitly document that this gate applies only to maintenance/update flows.

6. [Medium] `domain-review.md` verdict format conflicts with the parser requirement
   - Section: "`_read_domain_review_verdict(path) -> Literal[\"PASS\", \"NEEDS_ADR\", \"BLOCK\", \"\"]`"
   - Section: template shows checkboxes: "`- [ ] PASS`, `- [ ] NEEDS_ADR`, `- [ ] BLOCK`"
   - Issue: The design says the parser requires a machine-readable `- verdict: PASS|NEEDS_ADR|BLOCK`, but the proposed template’s verdict section does not include that line. That will fail closed or require ad hoc checkbox parsing.
   - Suggestion: Put `- verdict: NEEDS_ADR` or blank machine-readable line directly in the template and make checkbox text purely human-facing.

7. [Medium] Bypass audit path is not aligned with existing logging
   - Section: "`AF_SKIP_DOMAIN_REVIEW=1` ... `.af_runtime/hook_events.log`"
   - Issue: Existing review-gate bypass logging writes `.af_review_queue/hook_events.log` in `scripts/review_gate.py`, while `ApprovalGate` emits run events through `_emit_approval_event()` at [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:54). The design introduces a third path without naming the writer or frozen-build behavior.
   - Suggestion: Reuse the RunEvent store or the existing `.af_review_queue/hook_events.log` convention; specify the function to call and add a test mirroring `tests/test_review_gate.py`.

8. [Medium] SkillPackBootstrapper disposition is internally inconsistent
   - Section: "`core/skill_pack_bootstrapper.py` | **file delete**"
   - Section: "Q4 ... Option B (DEPRECATED comment)"
   - Issue: The same design says immediate deletion in §7.3 but selects deprecation in Open Questions. This affects `af.spec`, `tests/test_compact_step2.py`, and `Master_Blueprint.md`; the implementation scope cannot be estimated from the document.
   - Suggestion: Pick one disposition before implementation. If deletion is selected, include the test removal and `af.spec` hiddenimport removal in Phase A, not as an ambiguous side task.

### Missing from Design

- Concrete `PreparedBrief` / `PreparedProject` schema changes for carrying `work_kind`, `blast_radius`, and possibly `NormalizedRequest`.
- Tests for `target_path` work-items where docs live outside the runtime workspace.
- A preservation test proving `work_kind` and `blast_radius` survive `initialize()` → `approve()` → `invalidate()`.
- Exact bypass audit writer and log path.
- Frozen build verification for any new `core/*.py` file, especially optional `core/brainstorm_prompts.py`.
- Concurrency behavior if `domain-review.md` changes between `approve()` and `execute()`.

### Positive Observations

- The design correctly keeps `domain-review.md` out of `_DOC_FILES`, which avoids invalidating existing approval snapshots for legacy work-items.
- It correctly identifies `system_wide` as the real code enum in the main trigger section and references the current `ChangeImpactProfiler` output.