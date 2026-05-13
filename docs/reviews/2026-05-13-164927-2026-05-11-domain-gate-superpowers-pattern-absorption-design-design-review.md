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

1. [Critical] Proposed data flow references `normalized`, but `ProjectPipeline` does not have that object
   - Section: "`generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact.get(\"blast_radius\", \"\"))` 호출부 갱신"
   - Issue: In current code, [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:963) calls `generate_work_items(...)` from `prepare_documents()` with only `project_brief`, `role_plan`, `task_board`, and `run_id`. There is no `normalized` variable in that scope. `ControlPlaneIntake.normalize()` exists in [core/control/intake.py](/D:/hoonProJect/worktrees/agent-factory/core/control/intake.py:69), but the project pipeline path does not call it or carry `NormalizedRequest`.
   - Suggestion: Add an explicit source for these values. Either pass `NormalizedRequest`/`change_impact` into `prepare_brief()`/`prepare_documents()`, or derive and store `work_kind` and `blast_radius` inside `project_brief` before work-item generation. Update both direct `prepare()` callers and the `agent_launcher.py` two-phase path.

2. [High] Design contradicts itself on `_DOC_FILES` vs `_DOMAIN_REVIEW_FILE`
   - Section: "`_DOC_FILES`에 `domain-review.md` 추가하지 않음" and later "`core/approval_gate.py` ... `_DOC_FILES` 확장 + verdict 검사"
   - Issue: These are mutually incompatible. Current `_DOC_FILES` in [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:80) drives snapshots, invalidation, and status rendering. Adding `domain-review.md` there would make existing work-items without that file fail or become invalidated, which §3.2 explicitly says to avoid.
   - Suggestion: Remove “`_DOC_FILES` 확장” from §7.2 and make the implementation rule unambiguous: add `_DOMAIN_REVIEW_FILE = "domain-review.md"` only, never include it in `compute_snapshots()` or `check_validity()`.

3. [High] `approval-gate.md` metadata will be overwritten unless every `_render()` path is changed
   - Section: "`approval-gate.md ## Metadata` 섹션에 두 필드 기록" and "`ApprovalGate.approve()` 진입 시 _parse() 통해 metadata read"
   - Issue: Current `_render()` writes only `work_item`, `approver`, `status`, and `last_updated` in [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:524). `approve()`, `invalidate()`, and `apply_verification_verdict()` all rewrite the file through `_render()`. If `work_kind` / `blast_radius` are inserted only at initialization or by the generator, the next approval/invalidation rewrite drops them. A re-approval after edit can then skip the domain gate because the metadata is gone.
   - Suggestion: Specify `_render(..., metadata: dict | None)` or explicit `work_kind` / `blast_radius` parameters, and preserve those fields in `approve()`, `invalidate()`, and `apply_verification_verdict()`.

4. [Medium] Blast-radius enum is still wrong in the design
   - Section: "`blast_radius ∈ {\"local\",\"module\",\"cross_module\",\"system_wide\"}`" and "`change_impact.blast_radius enum: {\"local\", ...}`"
   - Issue: Current code documents and returns `"isolated"`, not `"local"`, in [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16) and [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:238). The design says it corrected `"system"` to `"system_wide"`, but it leaves a second stale token.
   - Suggestion: Replace `local` with `isolated` everywhere, and add a test that imports/uses `ChangeImpactProfiler` outputs instead of relying only on grep.

5. [Medium] The domain-review template markdown fence is malformed
   - Section: "`### §3.4 domain-review.md 템플릿 구조`"
   - Issue: The template starts a ```markdown fence, then opens a nested ```text fence for `- verdict: PASS`. In Markdown, the inner fence closes the outer fence, so the rest of the template is no longer part of the code block. If copied as a template, this can produce broken documentation or omit intended sections.
   - Suggestion: Use an indented example line or a longer outer fence such as ````markdown ... ```text ... ``` ... ````.

6. [Medium] Dead-code removal decision is inconsistent
   - Section: "`옵션 A — 즉시 제거`" vs Q4 "`잠정 답: 옵션 B (영향 범위 최소)`"
   - Issue: §7.3 says delete [core/skill_pack_bootstrapper.py](/D:/hoonProJect/worktrees/agent-factory/core/skill_pack_bootstrapper.py:26), remove the tests in [tests/test_compact_step2.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_compact_step2.py:21), and remove `af.spec:122`. §12 Q4 says the provisional answer is Option B. Implementation cannot know whether to delete or deprecate.
   - Suggestion: Resolve Q4 before implementation. If deleting, update all four listed references in one change. If deprecating, remove §7.3’s “파일 삭제” requirement.

### Missing from Design

- How `NormalizedRequest` reaches `ProjectPipeline.prepare_documents()` in both direct and `agent_launcher.py` two-phase flows.
- Exact `_render()` metadata preservation strategy across approval, invalidation, verification-blocked, and auto-approve paths.
- Tests for re-approval after edit, where metadata loss is most likely.
- A concrete hook-events logging path for `AF_SKIP_DOMAIN_REVIEW=1`; current `approval_gate.py` emits events through `_emit_approval_event`, but the design does not specify event type or payload.

### Positive Observations

- The design correctly avoids adding `domain-review.md` to the snapshot set in §3.2, which is the right compatibility direction for existing work-items.
- It identifies the real build/test references for `SkillPackBootstrapper`: `af.spec`, `tests/test_compact_step2.py`, and `Master_Blueprint.md`, not just the production import graph.