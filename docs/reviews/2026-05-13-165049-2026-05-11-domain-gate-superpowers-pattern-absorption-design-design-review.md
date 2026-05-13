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

1. [Critical] `normalized` data flow does not exist in the current project pipeline
   - Section: "`generate_work_items(..., work_kind=normalized.work_kind, blast_radius=normalized.change_impact.get(\"blast_radius\", \"\"))` 호출부 갱신 (`project_pipeline.py:963` 부근)"
   - Issue: `core/project_pipeline.py:963` currently calls `generate_work_items(...)` without any `normalized` object in scope. I searched callers: `ControlPlaneIntake().normalize(...)` is not called anywhere in `core/`, `agent_launcher.py`, `run_factory_cli.py`, `tests/`, or `scripts/`. The only `ControlPlaneIntake` use in `project_pipeline.py:710` is a private `_recall_from_memory()` call. So the proposed work_kind/blast_radius propagation cannot be implemented as written.
   - Suggestion: Add a concrete integration point before work-item generation, e.g. call `ControlPlaneIntake().normalize(task_input, target_workspace, project_brief["route"], board=task_board)` inside `prepare_documents()`, store it on `PreparedBrief`/`PreparedProject`, and pass its fields to `generate_work_items()`.

2. [High] Approval failure caller still reports domain blocks as missing gate file
   - Section: "`approve()` False 반환 + `self.last_block_reason` 속성에 사유 기록 ... caller는 `gate.last_block_reason`으로 분기"
   - Issue: The actual interactive caller in `agent_launcher.py` calls `gate.approve(...)` and, on any `False`, prints "`approval-gate.md 를 찾을 수 없습니다.`" and returns `{"reason": "gate_file_missing"}`. The design does not list `agent_launcher.py` or `ProjectPipeline.run()` caller changes. After domain review blocking is added, users will get the wrong error and no recovery path.
   - Suggestion: Include caller updates for every `approve()` caller. At minimum, change the approval loop to read `getattr(gate, "last_block_reason", "")`, display domain-review-specific remediation, and return a distinct reason like `domain_review_blocked`.

3. [High] `blast_radius == "system_wide"` will miss planned system-wide work before files change
   - Section: "`change_impact.blast_radius == \"system_wide\" 단독 트리거 — work_kind 무관, false negative 최소화"
   - Issue: Current `ChangeImpactProfiler` derives blast radius from `git diff` and explicit file paths in user input (`core/control/change_impact.py:75-95`, `_get_git_diff_files`, `_extract_files_from_input`). During `prepare_documents()`, there may be no diff yet, and natural requests like “redesign the approval workflow” may not mention `core/...` paths. This means a system-wide design can be classified as `"module"`/`"isolated"` and skip the domain gate.
   - Suggestion: Add a planning-time fallback: infer domain-review requirement from route/intent keywords, task board module count, `project_brief`, or `execution_policy`, not only git diff. Add a test where no files are modified but the request clearly implies a system-wide architecture change.

4. [Medium] Blast-radius enum is still misstated
   - Section: "`change_impact.blast_radius` enum: `{\"local\", \"module\", \"cross_module\", \"system_wide\"}`"
   - Issue: Actual code defines `"isolated" | "module" | "cross_module" | "system_wide"` in `core/control/change_impact.py:16` and `ImpactProfile.blast_radius` defaults to `"module"` at line 35. `"local"` is not a current value. The document claims it was grep-verified, but it is still wrong.
   - Suggestion: Replace `"local"` with `"isolated"` throughout the design and add a regression assertion over the actual constants/return values.

5. [Medium] Domain bypass audit sink is undefined and conflicts with existing hook logging
   - Section: "`AF_SKIP_DOMAIN_REVIEW=1` ... bypass 발동 시 `.af_runtime/hook_events.log`에 기록 의무"
   - Issue: Existing review-gate audit logging uses `.af_review_queue/hook_events.log` via `scripts/review_gate.py` and `scripts/hook_runner.py`. `core/approval_gate.py` only emits RunEvents when `run_id` is present and no-ops otherwise. The design introduces `.af_runtime/hook_events.log` without a writer, schema, retention rule, or source/frozen path behavior.
   - Suggestion: Either reuse `.af_review_queue/hook_events.log` or define a shared `domain_gate` audit helper with exact line/JSON schema and tests for `approve(run_id="")`.

6. [Medium] `SkillPackBootstrapper` disposition contradicts itself
   - Section: "`core/skill_pack_bootstrapper.py` | **파일 삭제**" and "`옵션 A 채택`"
   - Issue: Later Open Questions says: "`Q4 ... 옵션 A (즉시 제거) vs 옵션 B (DEPRECATED 주석)? | 옵션 B (영향 범위 최소)`". This is a direct implementation ambiguity. Current references are real: `tests/test_compact_step2.py:21`, `tests/test_compact_step2.py:92`, `af.spec:122`, and `Master_Blueprint.md:81/858`.
   - Suggestion: Choose one final state. If deleting, update the test file, `af.spec`, and `Master_Blueprint.md` in the same phase. If deprecating, remove the deletion rows from §7.3/§10.3.

7. [Low] Frozen-build version checklist has the wrong installer count and omits Unix installer
   - Section: "`install-af.ps1` 버전 문자열 3곳 동시 수정"
   - Issue: Current `install-af.ps1` contains eight `1.2.28` occurrences, not three. `install-af.sh` also has version/tag strings. This matters because `code-review.md` highlights frozen-build and `af.spec` hiddenimports as recurring risks.
   - Suggestion: Replace the fixed “3곳” count with `rg -n '<old_version>' install-af.ps1 install-af.sh version.py` must return zero after the bump.

### Missing from Design

- Exact `ControlPlaneIntake.normalize()` insertion point and fallback behavior when normalization fails.
- Caller UX and return codes for `domain_review_blocked`, `missing_verdict`, and `multiple_verdicts`.
- A concrete audit log writer/schema for `AF_SKIP_DOMAIN_REVIEW`.
- A no-diff system-wide planning test to prevent the core false negative.
- Final decision on `SkillPackBootstrapper` removal vs deprecation.

### Positive Observations

- The design correctly keeps `domain-review.md` out of `_DOC_FILES`, which avoids invalidating old approvals through `compute_snapshots()` / `check_validity()`.
- It explicitly accounts for `af.spec` hiddenimports when adding `core/brainstorm_prompts.py`, which matches the project’s frozen-build constraints.