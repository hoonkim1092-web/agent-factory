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

1. [High] `normalized` data path is still not real
   - Section: "`generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact.get(\"blast_radius\", \"\"))` 호출부 갱신 (`project_pipeline.py:963` 부근)"
   - Issue: Current [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:706) only calls `ControlPlaneIntake()._recall_from_memory(task_input)`, not `normalize()`. At [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959), `generate_work_items()` is called with no `normalized` object in scope. Current [core/work_item_generator.py](D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1069) also has no `work_kind` / `blast_radius` parameters.
   - Suggestion: Add a concrete source of truth: either store `normalized: NormalizedRequest` on `PreparedBrief`, or inject `project_brief["control_plane"] = {"work_kind": ..., "blast_radius": ...}` during `prepare_brief()`. Then update the call site from that real field, not an undefined `normalized`.

2. [High] Enforcement only at `approve()` misses execution-time drift
   - Section: "`read 시점: ApprovalGate.approve() 진입 직후`"
   - Issue: Execution uses [ApprovalGate.is_execution_open()](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:241), which validates `_DOC_FILES` snapshots through `check_validity()` but would not re-read `_DOMAIN_REVIEW_FILE`. If `domain-review.md` is changed from `PASS` to `BLOCK` after approval, execution can still proceed because [check_validity()](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:364) only compares `_DOC_FILES`.
   - Suggestion: Run domain-review validation in `is_execution_open()` or `check_validity()` whenever `requires_domain_review` is true. Store the approved domain verdict hash separately or fail closed if the current verdict is not `PASS`.

3. [High] Staged rollout has no implementation switch
   - Section: "`단계 1 ... False (all work-item)`" and "`return blast_radius == \"system_wide\"`"
   - Issue: The design says Phase A should ship with `requires_domain_review=False`, then enable after one week. But the proposed helper only checks `AF_SKIP_DOMAIN_REVIEW` and `blast_radius == "system_wide"`. There is no policy flag, config field, or versioned rollout switch to keep Phase A advisory-only.
   - Suggestion: Add `policy.yaml` or env-backed setting such as `domain_review.enforcement_stage = 1|2|3`, and make `require_domain_review()` read that single mechanism.

4. [Medium] `blast_radius` enum is still wrong in one section
   - Section: "`blast_radius ∈ {\"local\",\"module\",\"cross_module\",\"system_wide\"}`" and "`change_impact.blast_radius enum: {\"local\", \"module\", \"cross_module\", \"system_wide\"}`"
   - Issue: Current [core/control/change_impact.py](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16) uses `"isolated" | "module" | "cross_module" | "system_wide"`, and `_compute_blast_radius()` returns `"isolated"` at [core/control/change_impact.py](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:239). `"local"` is not real.
   - Suggestion: Replace `"local"` with `"isolated"` everywhere and add a test that rejects unknown blast-radius values.

5. [Medium] `approval-gate.md` metadata example mixes domain verdict into the wrong file
   - Section:
     ```markdown
     ## Metadata
     - work_kind: refactor
     - blast_radius: system_wide
     - verdict: PASS    # domain-review.md에 동일 형식, 별도 파일
     ```
   - Issue: The text says only `work_kind` / `blast_radius` belong in `approval-gate.md`, but the example includes `verdict`. Since [ApprovalGate._parse()](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:455) already parses arbitrary metadata keys from `approval-gate.md`, an implementer can accidentally read a stale `approval-gate.md` verdict instead of `domain-review.md`.
   - Suggestion: Remove `- verdict` from the `approval-gate.md` example. Show a separate `domain-review.md` snippet for `- verdict: PASS`.

6. [Medium] `SkillPackBootstrapper` disposition contradicts itself
   - Section: "`Option A adopted` / immediate removal" versus Q4 "`Option B (DEPRECATED comment)`"
   - Issue: §10.3 says immediate removal of [core/skill_pack_bootstrapper.py](D:/hoonProJect/worktrees/agent-factory/core/skill_pack_bootstrapper.py:26), [tests/test_compact_step2.py](D:/hoonProJect/worktrees/agent-factory/tests/test_compact_step2.py:92), and [af.spec](D:/hoonProJect/worktrees/agent-factory/af.spec:122). §12 Q4 says the tentative decision is Option B. These cannot both guide implementation.
   - Suggestion: Pick one. If Option A, remove Q4 or mark it resolved. If Option B, remove §10.3’s immediate-removal table.

### Missing from Design

- Exact `PreparedBrief` / `project_brief` schema change for carrying `work_kind` and `blast_radius`.
- Execution-time validation path for `domain-review.md`, not just approval-time validation.
- Concrete rollout switch for advisory versus enforced domain review.
- Tests for post-approval `domain-review.md` change from `PASS` to `BLOCK`.
- Unknown enum handling for `blast_radius`.

### Positive Observations

- The design correctly avoids adding `domain-review.md` to `_DOC_FILES`, which prevents legacy work-items from being invalidated by snapshot drift.
- The frozen-build checklist now calls out `af.spec`, `version.py`, `install-af.ps1`, and `build_exe.py`, which matches the project’s PyInstaller maintenance pattern.