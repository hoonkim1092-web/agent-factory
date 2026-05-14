# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:41
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `paused_hitl` cannot pause where the design says it pauses
   - Section: "`project_pipeline | plan_verifier 진입 전 gate.is_execution_open() 체크 → False면 plan/structural/cross-review 모두 skip`" (`docs/2026-05-14-question-router-detailed-design.md:872`)
   - Issue: Current [project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959) calls `generate_work_items()` and then immediately runs PlanVerifier, structural gates, and cross-review at lines 970+. There is no `gate.is_execution_open()` check before those stages. Also [work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1104) would continue Stage 1-3 after the proposed Stage 0 insertion unless an explicit early return is added.
   - Suggestion: Define the exact paused branch: if `StageZeroResult.paused_hitl`, write Stage 0 artifacts, initialize the gate as paused/review-pending, return only Stage 0 files, and make `project_pipeline.py` skip PlanVerifier/structural/cross-review when the prepared work item is paused.

2. [High] Proposed `CliChatRequest` usage does not match the real provider API
   - Section: "`CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=int(timeout_sec), response_format={...})`" (`docs/2026-05-14-question-router-detailed-design.md:563-567`)
   - Issue: The actual [CliChatRequest](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:30) fields are `provider_id`, `model`, `system_prompt`, `task_input`, `workspace`, `run_id`, `timeout_sec`, `auto_approve`. It has no `messages` or `response_format`. The default provider `"claude"` is also not a valid provider id; current ids are `claude_cli`, `gemini_cli`, `codex_cli`.
   - Suggestion: Rewrite §6.1 around the real constructor: choose a valid provider id via `detect_available_cli_providers()` or config, call `default_chat_model_for_provider(provider_id)`, pass JSON instructions in `system_prompt`, pass the batch prompt in `task_input`, and provide `workspace`.

3. [High] ApprovalGate is assigned paused/ADR responsibilities it does not have
   - Section: "`approval_gate | gate.initialize() 호출 시 paused 상태 인식 → execution_open=false`" (`docs/2026-05-14-question-router-detailed-design.md:871`)
   - Issue: [ApprovalGate.initialize()](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:155) only writes `execution_open=False`; it accepts no paused flag and reads no Stage 0 result. [ProjectPipeline.run()](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1508) then auto-calls `_gate.approve(...)`, so a paused Stage 0 can be accidentally advanced unless explicit blocking metadata is added.
   - Suggestion: Add a concrete gate contract: e.g. `stage0_status: paused_hitl|blocked|ready`, `paused_hitl_ids`, and have `approve()` refuse `paused_hitl` until HITL responses are merged.

4. [Medium] Blast-radius test plan reintroduces invalid tokens
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`" (`docs/2026-05-14-question-router-detailed-design.md:975`)
   - Issue: The same document says valid blast radius is `isolated|module|cross_module|system_wide` and that `local|security|data` were removed. Existing [tests/test_approval_gate_domain_review.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_review.py:4) explicitly rejects invalid tokens.
   - Suggestion: Replace the P5 test matrix with `{isolated, module, cross_module, system_wide}` and test `security/data` through `BlockCause` or policy/risk metadata, not `blast_radius`.

5. [Medium] `schema_hash` meaning is inconsistent across artifacts
   - Section: "`ContextScanArtifact.schema_hash ... # raw markdown SHA-256`" and "`AssumptionLedgerEntry.schema_hash ... QuestionRouter.schema_hash`" (`docs/2026-05-14-question-router-detailed-design.md:378`, `:437`)
   - Issue: `schema_hash` alternates between content hash and question schema hash. §4.2 says YAML schema hash is in-memory and embedded into artifacts, but context-scan has no question YAML and claims markdown hash. This will make drift detection ambiguous.
   - Suggestion: Split names: `question_schema_hash` for YAML drift, `content_hash` for rendered artifact content. Require `question_schema_hash` only on QR-derived artifacts.

6. [Medium] Budget acceptance is not enforceable by the current code
   - Section: "`TOTAL_BUDGET 800s로 확장 권장`" / "`TOTAL_BUDGET 800s 내 완료`" (`docs/2026-05-14-question-router-detailed-design.md:648`, `:986`)
   - Issue: [work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:29) defines `TOTAL_BUDGET = 600.0`, but the actual execution uses `STAGE_BUDGET` deadlines. Adding Stage 0 before `t_total_start` means Stage 0 time is outside the existing Stage 1-3 budget.
   - Suggestion: Either remove `TOTAL_BUDGET` as an acceptance criterion or implement a real global deadline that starts before Stage 0 and passes remaining time into Stage 1-3.

### Missing from Design

- Exact `ProjectPipeline` resume hook: method name, ledger query, and how `hitl-response.md` is located under multi-PC paths.
- How `ProjectPipeline.run()` auto-approval is disabled for `paused_hitl` and `BLOCK`.
- Concrete `af.spec` test for dynamic imports plus data inclusion for `core/control/questions/*.yaml`.
- POSIX locking detail: current [run_ledger.py](/D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:104) uses `msvcrt`; the design claims `fcntl` too, but no implementation detail is specified.

### Positive Observations

- The document correctly verifies the real `work_kind` / `blast_radius` pass-through path from `project_pipeline.py` to `work_item_generator.py` to `ApprovalGate`.
- The PyInstaller hiddenimports list for the five new `core.control.*` modules is explicitly called out, which matches the project’s frozen-build risk pattern.