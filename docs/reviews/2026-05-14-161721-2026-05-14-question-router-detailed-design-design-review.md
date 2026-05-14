# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 16:17
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [High] `paused_hitl` path is under-specified for the real caller pipeline
   - Section: "`ProjectPipeline`는 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지하고 plan verification을 건너뛴다."
   - Issue: The design states the desired behavior, but does not specify the actual insertion point before current callers consume the returned file map. Today [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:963) calls `generate_work_items()`, then immediately iterates `work_item_files.values()` for `PlanVerifier` at line 979, loads all docs for structural gate at line 1027, and runs `DocumentReviewSession` at line 1060. A paused file map containing only `domain-review.md`, `project-goal.md/context-scan.md`, `assumptions.md`, `paused-hitl.md`, and `approval-gate.md` will still enter those gates unless the design mandates an early return path.
   - Suggestion: Add a concrete `ProjectPipeline.prepare()` branch immediately after `generate_work_items()` that detects `paused-hitl.md` or `approval-gate.md status=paused_hitl`, builds a `PreparedProject`-like incomplete result/report, and skips PlanVerifier, structural gate, document review, board sync, auto-approve, af-runner, and af-test-runner.

2. [High] ApprovalGate changes are incomplete for paused and new artifacts
   - Section: "`gate.initialize(..., status=\"paused_hitl\", execution_open=False)`"
   - Issue: The design adds `status` and `execution_open`, but the existing gate also snapshots a fixed `_DOC_FILES` set: `feature-plan.md`, `feature-spec.md`, `implementation-design.md`, `implementation-tasks.md` in [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:81). New Stage 0 artifacts are not part of approval snapshots or validity checks, and `check_validity()` at line 410 can treat “no feature docs” as valid if snapshots are empty. This can make paused/resume state drift invisible.
   - Suggestion: Define whether `domain-review.md`, `project-goal.md`, `context-scan.md`, `assumptions.md`, and `paused-hitl.md` are approval-controlled artifacts. If yes, extend snapshot metadata and validity checks. If no, explicitly exclude them and define separate drift checks before resume.

3. [High] Ledger design conflicts with existing telemetry primitives
   - Section: "`run_ledger paused_hitl event`", "`run_ledger schema_drift event`", "`assumption event`"
   - Issue: [core/control/run_ledger.py](D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:22) stores `LedgerEntry` state snapshots, not typed events. The typed append-only event system already exists in `core/events/run_event.py`, but `RunEventType` has no `paused_hitl`, `schema_drift`, or `assumption_recorded` values. The design mixes “ledger” and “event” semantics without choosing a persistence target.
   - Suggestion: Choose one: extend `RunEventType` and write Stage 0 events to `RunEventStore`, or extend `LedgerEntry.metadata` with a documented schema. Do not call them `run_ledger ... event` unless `RunLedger` gets an explicit event API.

4. [Medium] Atomic write requirement does not cover existing write paths it depends on
   - Section: "`approval-gate.md` ... temp file 후 atomic replace"
   - Issue: `ApprovalGate.initialize()` currently writes with `write_text()` at [core/approval_gate.py](D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:177), and `write_text()` is plain truncate/write in [core/file_io.py](D:/hoonProJect/worktrees/agent-factory/core/file_io.py:117). The design requires atomic writes for `approval-gate.md`, but the acceptance criteria only mention “StageArtifact atomic helper” and do not require migrating `ApprovalGate` itself.
   - Suggestion: Add a P5/P7 acceptance item requiring `ApprovalGate` writes to use the same atomic helper, including `approve()`, `reset()`, and `apply_verification_verdict()` paths, not just StageRouter-created artifacts.

5. [Medium] LLM budget/timeout contract is not tied to the real provider path
   - Section: "`QuestionRouter`는 직접 `control_plane_llm.py`를 호출하지 않는다. adapter를 둔다." / "`기존 hardcoded timeout_sec=300 경로를 우회하거나 확장한다.`"
   - Issue: The current hardcoded timeout is real: [core/control_plane_llm.py](D:/hoonProJect/worktrees/agent-factory/core/control_plane_llm.py:123) passes `timeout_sec=300` to `execute_cli_chat()`. The design names an adapter but does not specify whether it wraps `ControlPlaneLLM`, `requirement_llm.execute_document_prompt`, or `providers/cli.execute_cli_chat` directly. Without that, implementers can add a `timeout_sec` parameter that never reaches the CLI subprocess.
   - Suggestion: Specify the exact adapter call chain and required signature changes, including tests that assert a 90s/180s router timeout reaches `CliChatRequest.effective_timeout_sec`.

6. [Medium] Paused artifact schema is internally inconsistent
   - Section: `DomainReviewArtifact ... paused_hitl_ids: list[str]`
   - Section: "`domain-review.md 의 paused_hitl_ids: list[str] 도 동일하게 paused_hitl_questions: list[PausedHitlQuestion] 으로 변경 의무`"
   - Issue: §7.3 defines `paused_hitl_ids`, while §7.5 later says it must be renamed to structured `paused_hitl_questions`. That is easy to implement incorrectly, especially because resume logic depends on question provenance.
   - Suggestion: Update the §7.3 dataclass itself to `paused_hitl_questions: list[PausedHitlQuestion]` and remove the obsolete field from examples and acceptance criteria.

### Missing from Design

- Exact `ProjectPipeline.prepare()` early-return contract for paused HITL.
- Concrete resume storage format for user answers and how answers are merged back into Stage 0 inputs.
- Whether Stage 0 artifacts are approval-controlled, snapshot-controlled, or only audit artifacts.
- Run event vs run ledger persistence decision.
- Hiddenimports acceptance should also mention YAML question resource inclusion for frozen builds, not only Python modules.
- Failure behavior for malformed or missing active YAML files in frozen `dist/af/af.exe`.

### Positive Observations

- The design correctly preserves `generate_work_items()` returning `dict[str, str]`, matching the current caller contract in `core/project_pipeline.py`.
- The blast radius token set is aligned with existing `core/control/change_impact.py` and `core/control/execution_policy.py`: `isolated`, `module`, `cross_module`, `system_wide`.