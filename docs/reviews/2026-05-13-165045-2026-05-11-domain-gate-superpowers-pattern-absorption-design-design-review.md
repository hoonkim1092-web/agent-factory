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

1. [Critical] `work_kind` / `blast_radius` data path does not exist in the current `ProjectPipeline`
   - Section: "`project_pipeline.py:963 → generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact[\"blast_radius\"])`"
   - Issue: `core/project_pipeline.py` does not create or carry a `normalized` object. The only `ControlPlaneIntake` use in this file is `_recall_from_memory()` around `core/project_pipeline.py:706-707`; `ControlPlaneIntake.normalize()` is not called. `generate_work_items()` at `core/project_pipeline.py:959-966` currently receives only `workspace`, `slug`, `project_brief`, `role_plan`, `task_board`, and `run_id`.
   - Suggestion: Add an explicit integration point: either make `ProjectPipeline.prepare()` accept a `NormalizedRequest`, or compute `work_kind` / `change_impact` inside `prepare_documents()` and store them in `PreparedProject` / `project_brief`. Update `MaintenancePipeline._full_prepare()` too, because it currently delegates only `task_input` to `ProjectPipeline.prepare()`.

2. [High] Blast radius enum is still inconsistent with actual code
   - Section: "`change_impact.blast_radius` enum: `{\"local\", \"module\", \"cross_module\", \"system_wide\"}`"
   - Issue: `core/control/change_impact.py:16` and `core/control/change_impact.py:35` define `"isolated" | "module" | "cross_module" | "system_wide"`, and `_compute_blast_radius()` returns `"isolated"` at `core/control/change_impact.py:238-239`. The design’s `"local"` value is not real.
   - Suggestion: Replace every `"local"` mention with `"isolated"` and change the static grep acceptance criterion so it does not reject legitimate existing tokens like `"isolated"`, `"module"`, and `"cross_module"`.

3. [High] Design contradicts itself on whether `domain-review.md` belongs in `_DOC_FILES`
   - Section: "`_DOC_FILES`에 `domain-review.md` **추가하지 않음**"
   - Section: "`core/approval_gate.py` ... `requires_domain_review` 정책 + frontmatter read + `_DOC_FILES` 확장 + verdict 검사"
   - Issue: These two instructions conflict. Adding `domain-review.md` to `_DOC_FILES` would affect `compute_snapshots()` and `check_validity()` in `core/approval_gate.py:377-383` and `core/approval_gate.py:363-375`, potentially invalidating existing approved work-items.
   - Suggestion: Make the spec unambiguous: introduce only `_DOMAIN_REVIEW_FILE = "domain-review.md"` and explicitly forbid adding it to `_DOC_FILES`. Keep a regression test for `compute_snapshots()` proving no `domain_review` key appears.

4. [High] Bypass audit path is not compatible with the current approval event subsystem
   - Section: "`AF_SKIP_DOMAIN_REVIEW=1` ... bypass 발동 시 `.af_runtime/hook_events.log`에 기록 의무"
   - Issue: `core/approval_gate.py` currently emits approval events through `core.events.run_event.get_default_store().append()` in `_emit_approval_event()` at `core/approval_gate.py:53-67`, and only when `run_id` is present. There is no `hook_events.log` writer in `ApprovalGate`, and the design also says "`runtime_workspace`는 본 경로에 **사용하지 않음**", which leaves no clear runtime path for that log.
   - Suggestion: Reuse the existing RunEvent store for bypass events, or specify a concrete writer, path, lock/atomicity behavior, and behavior when `run_id` is empty. Do not introduce a second audit channel without a migration reason.

5. [Medium] The required machine-readable verdict is missing from the proposed template
   - Section: "`domain-review.md`에 1줄 machine-readable line 의무: `- verdict: PASS|NEEDS_ADR|BLOCK`"
   - Section: "`## 4. Verdict` ... `- [ ] PASS` / `- [ ] NEEDS_ADR` / `- [ ] BLOCK`"
   - Issue: The template in §3.4 uses checkboxes, but the parser design requires a single `- verdict:` line. That will make the first generated template fail the proposed parser unless implementers remember an unstated addition.
   - Suggestion: Put `- verdict: PASS|NEEDS_ADR|BLOCK` directly in the template, preferably before the checkbox prose, and define whether checkbox values are ignored or rejected.

6. [Medium] Frozen build coverage only mentions hiddenimports, not packaged document templates
   - Section: "`docs/work-items/_template/domain-review.md` | A | 도메인 검토 템플릿"
   - Section: "`af.spec hiddenimports 갱신 ... 신설 core/*.py 모두 hiddenimports 등재`"
   - Issue: `af.spec:27-32` packages `skills`, `config`, `policy.yaml`, and `core/research/packs`, but not `docs/work-items/_template`. `core/work_item_generator.py:1087-1088` reads templates from `workspace/docs/work-items/_template`; a frozen `af.exe` environment without the repo docs will not have the new template.
   - Suggestion: Either package the required templates in `af.spec` datas or define that frozen builds require an external workspace docs tree. Add a frozen-smoke criterion for `domain-review.md` template availability.

7. [Medium] Dead-code removal decision is internally inconsistent
   - Section: "`core/skill_pack_bootstrapper.py` | **파일 삭제**"
   - Section: "`Q4 ... 처분 ... 옵션 B (DEPRECATED 주석)? | 옵션 B (영향 범위 최소)`"
   - Issue: The implementation table says delete the file, while the open question says the preferred answer is deprecation. Actual references exist in `tests/test_compact_step2.py:21`, `tests/test_compact_step2.py:92`, and `af.spec:122`.
   - Suggestion: Pick one disposal path before implementation. If deleting, include test removal/update and `af.spec` removal in the same phase. If deprecating, remove the “파일 삭제” instruction.

### Missing from Design

- A concrete storage path for `work_kind` and `blast_radius` between `ControlPlaneIntake`, `ProjectPipeline.prepare()`, `PreparedProject`, and `ApprovalGate`.
- A precise config/feature-flag location for `requires_domain_review=False/True`; no current symbol exists.
- Atomic write/concurrency behavior for approval-gate changes; `core/file_io.py:117-120` writes directly, not atomically.
- Frozen build verification for `docs/work-items/_template/domain-review.md`, not just Python hiddenimports.
- Parser behavior for conflicting verdict sources: checkbox checked as PASS but `- verdict: BLOCK`.

### Positive Observations

- The design correctly avoids adding `domain-review.md` to snapshot invalidation in §3.2; that is the right direction for old work-item compatibility.
- The decision to avoid direct Superpowers imports is consistent with the existing local skill infrastructure and avoids a new external CLI dependency.