# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:38
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] `blast_radius` taxonomy is still inconsistent inside the design
   - Section: "`if blast in (\"system_wide\", \"security\", \"data\")`", "`blast_radius=\"local\"`", "`unit test: NEEDS_ADR × {local, module, system_wide, security, data}`"
   - Issue: §1.5 says valid tokens are only `isolated | module | cross_module | system_wide`, matching `core/control/change_impact.py:16,35,207-239`. But later sections still use invalid `local`, `security`, and `data`. Existing `tests/test_approval_gate_domain_review.py` explicitly rejects historical `local`.
   - Suggestion: Replace all `local` with `isolated`; replace `security/data` blast-radius logic with `BlockCause` or `risk_level`. P5 tests should cover `{isolated, module, cross_module, system_wide}` only.

2. [Critical] `paused_hitl` return path breaks `generate_work_items()` caller contract
   - Section: "`if stage0.paused_hitl: return _build_paused_response(work_dir, stage0)`"
   - Issue: `generate_work_items()` returns `dict[str, str]` at `core/work_item_generator.py:1069-1079`. `ProjectPipeline.prepare_documents()` immediately iterates `work_item_files.values()` and opens each value as a path at `core/project_pipeline.py:975-979`. `_build_paused_response()` is not defined in current code or in the design, and any non-path status payload will break plan verification.
   - Suggestion: Define an explicit paused contract and update `ProjectPipeline` before implementation. Either return only real artifact file paths plus a sentinel file, or return a typed `WorkItemGenerationResult` and change the caller to branch before plan verification.

3. [High] `paused_hitl` skips `ApprovalGate.initialize()` but E2E expects an approval gate state
   - Section: "`Stage 1~3 건너뛰고 즉시 반환`" and "`approval_gate | execution_open=false (paused_hitl 상태)`"
   - Issue: The insertion point is before current `ApprovalGate(doc_root, slug...).initialize(...)` at `core/work_item_generator.py:1233-1235`. If the function returns at §7.1, `approval-gate.md` is never created unless `_build_paused_response()` secretly does it, which the design does not specify.
   - Suggestion: Move gate initialization before the paused return, or specify that `_build_paused_response()` writes `approval-gate.md` and returns its path. Also distinguish `paused_hitl` from normal unapproved review state.

4. [High] `StageRouter` construction is internally inconsistent
   - Section: "`class StageRouter: def __init__(self, workspace: str, run_ledger: RunLedger)`" vs "`stage0 = StageRouter(workspace).run(...)`"
   - Issue: §5.6 requires a `RunLedger`, but §7.1 instantiates with only `workspace`. Implementation will fail or silently omit `append_assumption()` / `append_paused_hitl()` behavior.
   - Suggestion: Show the real construction, e.g. `ledger = RunLedger(workspace); stage0 = StageRouter(workspace, ledger).run(...)`, and add the import/update to §7.1.

5. [Medium] LLM budget design is not wired to the current LLM abstraction
   - Section: "`LLMCaller.batch_route(... timeout_sec: float)`", "`Goal Clar QR ... 90s`", "`Brainstorming QR ... 180s`"
   - Issue: Existing `core/control_plane_llm.py` exposes `generate()` / `generate_json()` only, and `_generate_via_cli()` hardcodes `timeout_sec=300` at `core/control_plane_llm.py:114-124`. The proposed 90s/180s budgets will not apply unless a new adapter bypasses or extends this API.
   - Suggestion: Add a concrete `QuestionRouterLLMCaller` implementation plan using `core.providers.cli.CliChatRequest(timeout_sec=...)`, including API fallback behavior and partial-response handling.

6. [Medium] Frozen build impact is missing from acceptance criteria
   - Section: "`core/control/question_router.py 신규`", "`core/control/stage_router.py 신규`", "`core/control/stage_artifacts.py 신규`"
   - Issue: §7.1 dynamically imports `core.control.stage_router`. `af.spec` currently lists `core.control_plane_llm` but no `core.control.stage_router`, `core.control.question_router`, `core.control.stage_artifacts`, `core.control.verdicts`, or `core.control.context_scanner`. PyInstaller can miss these.
   - Suggestion: Add `af.spec` hiddenimports updates and a frozen-build smoke test to P7.

### Missing from Design

- Exact `_build_paused_response()` schema and caller handling.
- Resume entry point for `paused_hitl`: `ProjectPipeline`, `MaintenancePipeline`, or `work_item_generator`.
- `af.spec` hiddenimports and frozen `dist/af/af.exe` verification.
- Consistent mapping among `blast_radius`, `risk_level`, and `BlockCause`.
- Concurrency policy for duplicate slug/work_dir runs; only `assumptions.md` append locking is addressed.

### Positive Observations

- The design correctly identifies the real Stage 0 insertion point before Stage 1 in `core/work_item_generator.py`.
- The v2 schema-hash section removes the self-referential YAML hash problem by making source YAML hash output-only in artifacts/ledger.