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

1. [Critical] `paused_hitl` can be auto-approved by the backward-compatible `run()` path
   - Section: “`paused_hitl`는 성공이 아니다 … `runner_continued = false`”
   - Issue: Existing `ProjectPipeline.run()` unconditionally calls `prepared.gate().approve()` before `execute()` for backward compatibility ([core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1508)). Current `ApprovalGate.approve()` only blocks `verification_blocked` and warning decisions, not `paused_hitl` ([core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:207)). If Stage 0 creates a paused gate, the compatibility path can flip it to `approved` unless the design explicitly changes both paths.
   - Suggestion: Add a hard rule: `ApprovalGate.approve()` must return `False` when status is `paused_hitl`, and `ProjectPipeline.run()` must detect `paused-hitl.md` before auto-approval and return an incomplete/pending result.

2. [High] Proposed `ApprovalGate.initialize()` call does not match current API
   - Section: “`gate.initialize(..., status="paused_hitl", execution_open=False)`”
   - Issue: Current signature only accepts `work_item_id`, `run_id`, `work_kind`, `blast_radius` ([core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:155)). The design says status/execution parameters are “required” but does not include a concrete API change or acceptance criterion for parse/render compatibility.
   - Suggestion: Define the exact new signature, valid statuses, render format, parser behavior, and tests. Add P5 criteria for `initialize(status="paused_hitl")`, `get_status()`, `is_execution_open()`, and `approve()` refusal.

3. [High] Paused file-map path conflicts with current `prepare_documents()` verification flow
   - Section: “ProjectPipeline는 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지하고 plan verification를 건너뛴다”
   - Issue: After `generate_work_items()`, current `prepare_documents()` immediately runs `PlanVerifier`, structural gate, work-item doc-set QA, and document review over `work_item_files.values()` ([core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:970), [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1021)). A paused map without `feature-plan.md`, `feature-spec.md`, `implementation-design.md`, and `implementation-tasks.md` will be treated as an incomplete document set unless the skip point is specified before those gates.
   - Suggestion: Add an explicit branch immediately after `generate_work_items()`: if `"paused-hitl.md"` exists in the map, skip PlanVerifier/T1/doc review, build `PreparedProject` with paused metadata, and return without normal work-item QA.

4. [High] Timeout adapter requirement conflicts with existing `ControlPlaneLLM`
   - Section: “`timeout_sec` 실제 CLI/provider 호출까지 전달 … 기존 hardcoded `timeout_sec=300` 경로를 우회하거나 확장”
   - Issue: `ControlPlaneLLM._generate_via_cli()` currently hardcodes `timeout_sec=300` inside `CliChatRequest` ([core/control_plane_llm.py](D:/hoonProJect/worktrees/agent-factory/core/control_plane_llm.py:114)). The design says QuestionRouter should not call `control_plane_llm.py` directly, but does not specify whether to extend `ControlPlaneLLM`, bypass it, or duplicate provider selection/failover.
   - Suggestion: Pick one contract. Prefer adding `timeout_sec` to `ControlPlaneLLM.generate_json()` and `_generate_via_cli()`, then let `QuestionRouterLLMCaller` wrap it without duplicating provider logic.

5. [Medium] Atomic-write policy is not tied to the existing non-atomic helper
   - Section: “write `<name>.tmp.<pid>` / fsync / replace target atomically”
   - Issue: Current `write_text()` truncates in place ([core/file_io.py](D:/hoonProJect/worktrees/agent-factory/core/file_io.py:117)), and `ApprovalGate.initialize()/approve()` use it ([core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:177)). The design lists atomic writes but does not say whether to add a new helper, replace `write_text()`, or update gate writes.
   - Suggestion: Define `atomic_write_text()` in `core/file_io.py`, use it for Stage 0 artifacts and `approval-gate.md`, and add a test that rejects direct `write_text()` for these paths.

6. [Medium] New Stage 0 modules are listed for `af.spec`, but package data for YAML schemas is missing
   - Section: “`core.control.questions/goal_clarification.yaml`, `brainstorming.yaml` 추가”
   - Issue: Hidden imports cover Python modules, but PyInstaller also needs non-Python data files. Current `af.spec` hiddenimports do not solve loading YAML files from `core/control/questions`.
   - Suggestion: Add an explicit `datas` entry or runtime fallback path for `core/control/questions/*.yaml`, and include the frozen smoke test in P7.

### Missing from Design

- Exact `ProjectPipeline.run()` behavior for paused HITL and auto-approval compatibility.
- Exact `ApprovalGate` status model: allowed statuses, approval refusal rules, parse/render format.
- Package-data handling for YAML question sets in frozen builds.
- Concrete insertion point in `prepare_documents()` where paused flow bypasses plan/doc gates.
- Whether `ControlPlaneLLM` is extended or bypassed for per-call timeouts.

### Positive Observations

- The design correctly preserves `generate_work_items()` as a `dict[str, str]` file-path map instead of introducing a new return object, which matches [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959).
- It correctly rejects invalid `blast_radius` tokens and aligns with the current four-token contract documented in [core/control/change_impact.py](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:16).