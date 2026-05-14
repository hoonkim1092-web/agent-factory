# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:37
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `generate_work_items()` paused return breaks the caller contract
   - Section: "`if stage0.paused_hitl: return _build_paused_response(work_dir, stage0)`" and "`Stage 1~3 ... skip`"
   - Issue: [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1069) currently returns `dict[str, str]` of file paths. [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959) immediately treats the result as file paths and iterates `work_item_files.values()` at line 975. A paused status dict will be misread as paths and the pipeline will continue into plan verification instead of stopping.
   - Suggestion: Add an explicit paused contract at `ProjectPipeline.prepare_documents()`: either raise a `StageZeroPaused` exception from `generate_work_items()` and catch it there, or return a typed `WorkItemGenerationResult(files, paused, ledger_state)` and update every caller before implementation.

2. [High] Blast radius taxonomy is still inconsistent
   - Section: "`if blast_radius in (\"system_wide\", \"security\", \"data\")`" and "`unit test: NEEDS_ADR × {local, module, system_wide, security, data}`"
   - Issue: The actual taxonomy in [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:35) is only `isolated | module | cross_module | system_wide`. The design also says v2 corrected this, but later sections still use `local`, `security`, and `data`. Current approval tests also prove non-system scopes bypass domain review: [tests/test_approval_gate_domain_gate.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_gate.py:149).
   - Suggestion: Replace all remaining `local/security/data` blast-radius checks with `isolated/module/cross_module/system_wide`. Model security/data as `BlockCause` or policy risk, not blast radius.

3. [High] Frozen build support is incomplete
   - Section: "`core/control/question_router.py 신규`", "`core/control/stage_router.py 신규`", "`core/control/stage_artifacts.py 신규`", "`core/control/questions/goal_clarification.yaml 신규`"
   - Issue: [af.spec](/D:/hoonProJect/worktrees/agent-factory/af.spec:33) has explicit hiddenimports, but no `core.control.stage_router`, `core.control.question_router`, `core.control.stage_artifacts`, `core.control.verdicts`, or `core.control.context_scanner`. Its `datas` also does not include `core/control/questions`, so YAML loading by filesystem path can fail in `dist/af/af.exe`.
   - Suggestion: Add a frozen-build section: hiddenimports for every new `core.control.*` module and `datas=[('core/control/questions', 'core/control/questions')]`, plus a smoke test against the PyInstaller bundle.

4. [High] HITL/block recovery path is not designed
   - Section: "`paused_hitl resume 진입점 ... resume 코드 위치 미결정`" and "`P7 ... 5경로 + drift integration test`"
   - Issue: The design requires pausing Stage 1-3 and later resuming, but OQ6 leaves the resume entry point undecided. Current execution only checks `approval-gate.md` openness in [core/project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1265); there is no path that reloads `paused_hitl_ids`, applies answers, and re-enters Stage 0/1.
   - Suggestion: Decide before implementation whether resume lives in `ProjectPipeline.prepare_documents()`, supervisor, or a CLI command. Define the persisted state shape and one test: paused run -> user answers -> same run resumes without regenerating unrelated artifacts.

5. [Medium] LLM adapter is underspecified despite timeout/cost claims
   - Section: "`class LLMCaller ... batch_route(... timeout_sec: float)`", "`Goal Clar QR ... 90s`", "`Brainstorming QR ... 180s`"
   - Issue: The project already has `execute_cli_chat()` with `CliChatRequest.timeout_sec` in [core/providers/cli.py](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:698), and `ControlPlaneLLM` hardcodes `timeout_sec=300`. The design defines an abstraction but not the concrete adapter, provider ordering, unavailable-provider behavior, or how a single JSON text response maps to per-question partial failures.
   - Suggestion: Add `QuestionRouterLLMCaller` explicitly: provider source, timeout propagation, JSON schema parsing, provider failure fallback, and partial-result semantics.

### Missing from Design

- Exact caller contract for paused/block outcomes from `generate_work_items()` through `ProjectPipeline.prepare_documents()`.
- Frozen bundle resource loading for `core/control/questions/*.yaml`.
- Resume workflow for `paused_hitl`.
- Cleanup/migration plan for existing tests expecting `NEEDS_ADR` to pass on `system_wide`.
- Concrete adapter from `LLMCaller` to existing provider CLI stack.

### Positive Observations

- The document correctly verifies that `work_kind` and `blast_radius` now reach `generate_work_items()` and `ApprovalGate.initialize()` via [project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959) and [work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1233).
- The schema-hash self-reference problem is recognized and mostly corrected by moving the hash out of YAML and into artifacts/ledger entries.