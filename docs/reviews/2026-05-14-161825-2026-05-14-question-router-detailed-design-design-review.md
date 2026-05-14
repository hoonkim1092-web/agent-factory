# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 16:18
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] `paused_hitl` caller handling is too narrow for the current pipeline
   - Section: "`ProjectPipeline`은 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지해 plan verification을 건너뛴다."
   - Issue: Current caller does more than plan verification after `generate_work_items()`: `PlanVerifier` reads every `work_item_files.values()` at `core/project_pipeline.py:970-981`, then structural gate at `1021-1027`, document cross-review/refine at `1058-1112`, then builds `PreparedProject` at `1134`. A paused artifact set can still be structurally checked, cross-reviewed, and possibly rewritten.
   - Suggestion: Specify an early paused branch immediately after `generate_work_items()` in `core/project_pipeline.py`: skip PlanVerifier, work-item structural gate, doc cross-review, execution checkpoint-to-orchestrate, and return/report a distinct incomplete state. Add a `PreparedProject` flag or explicit result reason so `execute()` returns `paused_hitl`, not generic `approval_required`.

2. [High] Frozen build will miss the new YAML question files
   - Section: "`core/control/questions/goal_clarification.yaml` 추가", "`core/control/questions/brainstorming.yaml` 추가", and "`af.spec hiddenimports 반영`"
   - Issue: `hiddenimports` only bundles Python modules. Current `af.spec:27-32` datas include `skills`, `config`, `policy.yaml`, and `core/research/packs`, but not `core/control/questions`. In `dist/af/af.exe`, StageRouter will not be able to load the YAML files or compute `schema_hash = sha256(source_yaml_bytes)`.
   - Suggestion: Add `('core/control/questions', 'core/control/questions')` to `datas`, and require a loader based on `importlib.resources` or PyInstaller-aware `_MEIPASS` paths. Add a frozen smoke test that loads both YAML files and computes schema hashes.

3. [High] Ledger hard-fail requirement conflicts with existing `RunLedger`
   - Section: "`append 실패 시 Stage 0 warning이 아니라 hard fail`" and E2E: "`run_ledger paused_hitl event`"
   - Issue: `core/control/run_ledger.py:123-124` catches all append failures and only prints `[RunLedger] append failed`, so Stage 0 cannot hard-fail on missing `paused_hitl`, `assumption`, or `schema_drift` audit events if it uses the existing ledger. On non-Windows, the `msvcrt` path also falls back to writing without a cross-process lock.
   - Suggestion: Define a strict append path, e.g. `RunLedger.append_strict()` that raises, or change append to return success/failure. Use `core/file_lock.py::locked_file` for cross-platform locking and add failure-injection tests.

4. [Medium] Return map key contract is inconsistent
   - Section: paused map lists file names in §3.1, but §9.1 shows keys like `"approval_gate"`, `"domain_review"`, `"project_goal"`, `"paused_hitl"`.
   - Issue: Existing code treats keys as document names in places: `core/project_pipeline.py:1060-1061` only cross-reviews keys ending with `.md`, and refinement checks `if _dtype in work_item_files` at `1110-1112`. Mixed underscore keys and filename keys will create inconsistent behavior.
   - Suggestion: Standardize on existing filename keys: `"approval-gate.md"`, `"domain-review.md"`, `"project-goal.md"`, `"context-scan.md"`, `"assumptions.md"`, `"paused-hitl.md"`.

5. [Medium] LLM timeout path is stated but not tied to a real caller change
   - Section: "`timeout_sec는 실제 CLI/provider 호출까지 전달되어야 한다. 기존 hardcoded timeout_sec=300 경로를 우회하거나 확장한다.`"
   - Issue: Current `ControlPlaneLLM` has `generate(prompt)` / `generate_json(prompt)` without timeout parameters, and `core/control_plane_llm.py:114-123` hardcodes `timeout_sec=300`. The design does not say whether `QuestionRouterLLMCaller` extends this API or bypasses it with `execute_cli_chat`.
   - Suggestion: Make the adapter contract concrete: either add timeout-aware methods to `ControlPlaneLLM`, or require `QuestionRouterLLMCaller` to call `execute_cli_chat` directly. Add a test proving 90s/180s budgets reach `CliChatRequest.timeout_sec`.

### Missing from Design

- Exact `ProjectPipeline` paused state model: field, return shape, checkpoint cursor, and final report behavior.
- `af.spec` `datas` update for `core/control/questions/*.yaml`.
- Strict ledger API or failure propagation plan.
- Cross-platform locking requirement for `assumptions.md` and run ledger.
- Consistent file-path map key names.

### Positive Observations

- The design correctly preserves `generate_work_items() -> dict[str, str]`, which avoids breaking the current caller contract.
- The `blast_radius` token set is aligned with `core/control/change_impact.py` and existing approval-gate tests, avoiding the old invalid `local`/`system` tokens.