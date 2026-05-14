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

1. [Critical] `work_kind` / `blast_radius` source is not wired, so Stage 0 will usually no-op
   - Section: "`core/project_pipeline.py:970-971`은 `project_brief`에서 `work_kind`, `blast_radius`를 넘긴다" and "`empty or non-enum work_kind ... -> Stage 0 skip`"
   - Issue: Current `core/project_pipeline.py` only adds `requested_role`, `route`, and `generated_at` to `project_brief`. Repo search shows `ControlPlaneIntake.normalize()` is not called in the project path; only `_recall_from_memory()` is used. Therefore `generate_work_items()` receives `work_kind=""`, `blast_radius=""`, and the proposed compatibility guard skips Stage 0 for normal project runs.
   - Suggestion: Add an explicit normalization step before `prepare_documents()` or inside it: call `ControlPlaneIntake.normalize(task_input, workspace, route)` or directly use `WorkKindClassifier` + `ChangeImpactProfiler`, then persist `project_brief["work_kind"]` and `project_brief["blast_radius"]`.

2. [High] Frozen build will miss YAML question schemas
   - Section: "`core/control/questions/goal_clarification.yaml` 추가", "`core/control/questions/brainstorming.yaml` 추가", and "`af.spec hiddenimports 반영`"
   - Issue: `af.spec` currently bundles `skills`, `config`, `policy.yaml`, and `core/research/packs`, but not `core/control/questions`. Hidden imports only cover Python modules. In `dist/af/af.exe`, `QuestionRouter` can import successfully but fail loading YAML schemas by path.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `datas`, or use `importlib.resources` with PyInstaller data collection. Add a frozen smoke test that loads both YAML files.

3. [High] `paused_hitl` contract is not concrete enough for the current `ProjectPipeline`
   - Section: "`ProjectPipeline`은 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지해 plan verification을 건너뛴다"
   - Issue: Current `core/project_pipeline.py` immediately runs plan verifier, structural gates, and document cross-review after `generate_work_items()`. There is no pause check between `work_item_files = generate_work_items(...)` and the verification loops. A paused-only file map can still be treated as normal work-item documents.
   - Suggestion: Define an explicit control signal, not only a sentinel file. For example, `generate_work_items()` returns a file map plus `stage0_status`, or `ProjectPipeline` checks `paused-hitl.md` immediately after generation and returns a `PreparedProject` marked `paused_hitl` with execution disabled.

4. [Medium] LLM caller adapter lacks compatibility details for the real provider API
   - Section: "`QuestionRouter`는 직접 `control_plane_llm.py`를 호출하지 않는다 ... `QuestionRouterLLMCaller.batch_route(...)`"
   - Issue: Current `core/providers/cli.py` requires `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, ...)` and returns a dict with `ok/text/reason`. The design does not specify provider selection, model selection, JSON extraction from `text`, or failover behavior.
   - Suggestion: Define the adapter against the real `CliChatRequest` contract: provider IDs like `claude_cli`, model resolution, schema instructions in `system_prompt`, serialized questions in `task_input`, and JSON parse/failure mapping.

5. [Medium] `schema_hash` is overloaded across unrelated artifact types
   - Section: "`schema_hash = sha256(source_yaml_bytes)`" and `ContextScanArtifact ... schema_hash: str`
   - Issue: `ContextScanArtifact` is produced by static scanning, not a question YAML schema. Reusing `schema_hash` for both YAML drift and artifact/schema identity makes resume drift checks ambiguous.
   - Suggestion: Use `question_schema_hash` only for QR-derived artifacts, and a separate `artifact_schema_version` or `content_hash` for scanner/rendered artifacts.

### Missing from Design

- Concrete insertion point that populates `project_brief["work_kind"]` and `project_brief["blast_radius"]`.
- PyInstaller `datas` handling for `core/control/questions/*.yaml`.
- Exact `ProjectPipeline` paused return/execute/report behavior.
- Real `QuestionRouterLLMCaller` implementation contract against `core.providers.cli`.
- Migration/update plan for `ApprovalGate._render()`, `_parse()`, and `approve()` to support `status`, `execution_open`, `DomainVerdict`, and `BlockCause`.

### Positive Observations

- The design correctly preserves `generate_work_items()` returning a file-path map instead of introducing a new return object that would break current callers.
- Separating `QuestionRoute`, `DomainVerdict`, and `BlockCause` avoids mixing routing mechanics with domain gate policy.