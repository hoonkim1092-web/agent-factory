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

1. [Critical] `work_kind` / `blast_radius` propagation path is not implemented in the current pipeline
   - Section: "`project_pipeline.py:963` ... `generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact[\"blast_radius\"])`"
   - Issue: Current [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959) calls `generate_work_items(...)` without a `NormalizedRequest`. It only calls `ControlPlaneIntake()._recall_from_memory(...)` at [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:706), not `normalize()`. Repo-wide search shows no `ControlPlaneIntake().normalize(...)` caller in the main pipeline.
   - Suggestion: Design the actual insertion point for `ControlPlaneIntake.normalize(task_input, target_workspace, route, board)` and account for its side effects: run ledger creation, state machine init, issue context binding, and memory recall. This is not a 5 LOC `generate_work_items` call-site change.

2. [High] Enforcement token is internally inconsistent: `system_wide` vs `system`
   - Section: "`blast_radius == \"system_wide\"` 단독 트리거" and later "`True for `blast_radius == \"system\"`"
   - Issue: The actual enum is `"isolated" | "module" | "cross_module" | "system_wide"` in [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16), and `_compute_blast_radius()` returns `"system_wide"` at [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:218). The migration section still says `"system"`, which would silently disable the new gate if copied into implementation.
   - Suggestion: Replace every remaining `"system"` blast-radius reference with `"system_wide"` and add a regression test that a `system_wide` fixture blocks while a legacy `"system"` token is rejected or normalized explicitly.

3. [High] `ApprovalGate` contract changes are underspecified for existing parser/render flow
   - Section: "`approve()` False 반환 + `self.last_block_reason` 속성에 사유 기록"
   - Issue: Current [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:107) has no `last_block_reason` attribute. `approve()` currently parses, computes snapshots, and writes `status="approved"` directly at [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:171). `_parse()` only reads `## Metadata`, `## Approved Snapshot`, `## Gate Status`, and `## Review Notes` at [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:436).
   - Suggestion: Specify exact initialization/reset semantics for `last_block_reason`, where the domain check runs inside `approve()`, and how it composes with existing `verification_blocked`, `read_block_decision()`, auto-approve, snapshots, and `execution_open`.

4. [High] `domain-review.md` verdict template does not match the required machine-readable parser
   - Section: "`domain-review.md`는 1줄 machine-readable line 필수: `- verdict: PASS|NEEDS_ADR|BLOCK`"
   - Issue: The proposed template’s Verdict section only shows checkbox lines: `- [ ] PASS`, `- [ ] NEEDS_ADR`, `- [ ] BLOCK`. A parser expecting `- verdict: PASS` will fail closed on the provided template.
   - Suggestion: Put the required line in the template itself, preferably under `## Metadata`:
     `- verdict: ""`
     Then keep checkboxes as human-readable support only.

5. [Medium] `generate_work_items()` signature and template copying impact are undercounted
   - Section: "`core/work_item_generator.py` ... signature에 `work_kind`, `blast_radius` 추가 ... `_copy_extra_templates()` extra에 `domain-review.md` 추가"
   - Issue: Current `generate_work_items()` signature has no optional metadata parameters at [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1072), and `_copy_extra_templates()` only copies three files at [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1387). Adding metadata to `approval-gate.md` likely touches render paths around gate initialization, not just the generator signature.
   - Suggestion: Add a concrete output example of generated `approval-gate.md ## Metadata`, and include tests for default `""` values, existing callers, and target-path mode where `doc_root != workspace`.

6. [Medium] Frozen build impact is still split across sections
   - Section: "`core/brainstorm_prompts.py` (선택)" and "`af.spec hiddenimports ... Phase C 시 ... 추가`"
   - Issue: `docs/code_review/code-review.md` calls out manual `af.spec` hiddenimports as a frozen-build risk. The design mentions hiddenimports in validation, but the modified-file list does not include `af.spec` for the optional new `core/brainstorm_prompts.py`, while [af.spec](/D:/hoonProJect/worktrees/agent-factory/af.spec:33) manually enumerates core modules.
   - Suggestion: Make `af.spec` and `version.py` explicit Phase C modified files whenever any new `core/*.py` module is introduced.

### Missing from Design

- Exact call-site plan for creating and reusing `NormalizedRequest` without duplicating ledger/state side effects.
- Full parser contract for `domain-review.md`, including duplicate verdicts, lowercase values, missing file, blank template, and invalid value behavior.
- Concurrency behavior if approval, verification verdict, and domain-review edits happen at the same time.
- End-to-end frozen-build test or at least `af.spec` checklist tied to each optional Python module.
- Migration correction for the remaining `"system"` token in §10.2.

### Positive Observations

- The design correctly avoids adding `domain-review.md` to `_DOC_FILES`, which would otherwise invalidate existing work-item snapshots.
- It identifies the real build/test references for `core.skill_pack_bootstrapper`: [af.spec](/D:/hoonProJect/worktrees/agent-factory/af.spec:122) and [tests/test_compact_step2.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_compact_step2.py:92).