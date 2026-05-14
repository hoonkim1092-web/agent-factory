# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 16:16
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] `paused_hitl` is not integrated with the real `ProjectPipeline.prepare()` path
   - Section: "`ProjectPipeline`는 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지해 plan verification을 건너뛴다."
   - Issue: The current caller does not have this branch. After `generate_work_items()` returns, [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959) immediately runs `PlanVerifier` over `work_item_files.values()` at lines 970-981, then structural gate and cross-review at 1013-1116. A paused file map containing only `domain-review.md`, `project-goal.md`, `assumptions.md`, `paused-hitl.md`, and `approval-gate.md` will still enter those QA paths.
   - Suggestion: Specify the exact branch in `ProjectPipeline.prepare()` immediately after `generate_work_items()`: if `"paused-hitl.md"` or `"paused_hitl"` is present, skip plan verifier, structural gate, document cross-review, af-runner preparation side effects, and return a `PreparedProject` marked incomplete/pending HITL.

2. [High] ApprovalGate responsibility is assigned to code that currently cannot perform it
   - Section: "`ApprovalGate ... 실제 ADR 생성 ... pause/continue/abort 결정`" and "`DomainVerdict × blast_radius matrix`"
   - Issue: Current [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:228) only enforces domain review for `blast_radius == "system_wide"`, and only inside `approve()`. It does not parse `DomainVerdict`, `BlockCause`, `NEEDS_ADR`, or create ADRs. The design only changes `initialize(status, execution_open)`, which is insufficient for the matrix in §8.1.
   - Suggestion: Add a concrete API contract, e.g. `ApprovalGate.apply_domain_verdict(domain_review_path, run_id)` or move ADR creation/pause decisions to `StageRouter`. Define the file written, status values, and how `approve()` blocks `paused_hitl`/`NEEDS_ADR high blast`.

3. [High] Frozen build plan misses YAML data files
   - Section: "`af.spec hiddenimports 반영` ... `core.control.stage_router`, `question_router`, `stage_artifacts`, `verdicts`, `context_scanner`"
   - Issue: The new runtime schemas are `core/control/questions/goal_clarification.yaml` and `brainstorming.yaml`, but current [af.spec](/D:/hoonProJect/worktrees/agent-factory/af.spec:27) `datas` includes `skills`, `config`, `policy.yaml`, and `core/research/packs` only. Hidden imports do not bundle YAML files, so frozen `dist/af/af.exe` can import code and still fail schema loading.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `datas`, or specify `importlib.resources` loading plus a PyInstaller data collection rule. The frozen smoke test must load both YAML files, not just import modules.

4. [Medium] Stage 1 context injection target is wrong for the current generator
   - Section: "`core/work_item_generator.py:908` `_exec_stage1()` prompt 구성에 `Existing Tests` / `Research Scope` 섹션 추가 ... placeholder `{existing_tests_section}`"
   - Issue: Current [_exec_stage1](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:906) does not build the prompt. It calls `_generate_and_refine("plan", _generate_feature_plan, ...)` and only appends `episode_hints_section` after generation at lines 917-925. Adding placeholders to `_exec_stage1()` will not influence the Stage 1 LLM prompt unless `_generate_feature_plan` or `project_brief` is changed.
   - Suggestion: Define the actual integration point: either inject `existing_tests` and `research_scope` into `project_brief` before `_generate_feature_plan`, or modify `_generate_feature_plan` prompt construction directly.

5. [Medium] Artifact schema is internally inconsistent for paused HITL IDs
   - Section: `DomainReviewArtifact ... paused_hitl_ids: list[str]` followed by "`paused_hitl_ids` ... `paused_hitl_questions: list[PausedHitlQuestion]` 로 변경해야 함"
   - Issue: The dataclass in §7.3 still shows `paused_hitl_ids: list[str]`, while §7.5 says it must be replaced with structured `{question_set_id, question_id}` entries. This will produce mismatched renderer/parser/tests for `domain-review.md` and `paused-hitl.md`.
   - Suggestion: Update the §7.3 dataclass and all examples to a single field name and shape, preferably `paused_hitl_questions: list[PausedHitlQuestion]`.

### Missing from Design

- Exact `ProjectPipeline.prepare()` control flow for paused HITL and abort states.
- Concrete `ApprovalGate` API for `DomainVerdict`, `BlockCause`, ADR creation, and status transitions.
- PyInstaller `datas` handling for `core/control/questions/*.yaml`.
- Real Stage 1 prompt injection location in `work_item_generator.py`.
- Resume input format and validation path for HITL answers.

### Positive Observations

- The design preserves `generate_work_items() -> dict[str, str]`, which matches the current caller contract in `ProjectPipeline`.
- It correctly keeps `QuestionRouter` side-effect-free and assigns artifact/ledger writing to `StageRouter`, which fits the existing `core/control` layering.