# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:39
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] LLM adapter will not instantiate the current CLI request type
   - Section: "`req = CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=..., response_format={...})`"
   - Issue: Current [core/providers/cli.py](/D:/hoonProJect/worktrees/agent-factory/core/providers/cli.py:31) defines `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id="", timeout_sec=0, auto_approve=False)`. It has no `messages` or `response_format` fields. Also provider IDs are `claude_cli`, `gemini_cli`, `codex_cli`; the design default `"claude"` will fail `get_cli_provider_spec()`.
   - Suggestion: Change the design to construct:
     `CliChatRequest(provider_id="claude_cli", model=default_chat_model_for_provider(...), system_prompt=..., task_input=prompt, workspace=str(workspace), run_id=run_id, timeout_sec=int(timeout_sec))`.
     Include `workspace` and `run_id` in `QuestionRouterCliLLMCaller`.

2. [High] paused_hitl does not actually prevent Stage 1-3 generation
   - Section: "`Stage 0이 생성한 artifact 경로를 반환 dict에 흡수`" and "`paused_hitl 상태는 별도 채널 ... gate.initialize(...) 가 line 1238에서 호출되며 ... project_pipeline.py 가 plan_verifier 진입 전 gate.is_execution_open() 체크`"
   - Issue: In current [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1104), Stage 1 starts immediately after the proposed insertion point. `ApprovalGate.initialize()` is only called after Stage 1-3 at [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1233). A `project_pipeline` check before plan verification would still happen after all LLM-heavy Stage 1-3 documents were already generated.
   - Suggestion: Define an explicit early branch inside `generate_work_items()` after Stage 0. Either initialize the gate immediately and return only Stage 0 artifacts, or move gate creation before Stage 1 and skip Stage 1-3 when `stage0.paused_hitl` is true.

3. [High] ApprovalGate snippet uses an out-of-scope `blast_radius`
   - Section: "`if blast_radius in _HIGH_BLAST:`"
   - Issue: Current `ApprovalGate.approve()` has no `blast_radius` parameter; it reads metadata from `current = self._parse()` at [core/approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:207). The design snippet would raise `NameError` unless implementation silently diverges.
   - Suggestion: Use `_clean(current.get("blast_radius"))` in the matrix. Also update tests around [tests/test_approval_gate_domain_gate.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_approval_gate_domain_gate.py:6), whose current contract says non-`system_wide` skips the domain gate.

4. [High] Frozen build impact is underspecified
   - Section: "`core/control/stage_router.py 신규`, `question_router.py`, `stage_artifacts.py`, `context_scanner.py`, `core/control/questions/*.yaml`"
   - Issue: [af.spec](/D:/hoonProJect/worktrees/agent-factory/af.spec:33) manually lists hidden imports and `datas`. It currently includes neither the new dynamic modules nor `core/control/questions` YAML files. Because the design proposes importing `StageRouter` inside `generate_work_items()`, PyInstaller can miss it.
   - Suggestion: Add explicit `af.spec` changes to P1/P7: hiddenimports for `core.control.stage_router`, `question_router`, `stage_artifacts`, `context_scanner`, `verdicts`; datas entry for `core/control/questions`.

5. [Medium] Budget decision targets an unused constant
   - Section: "`TOTAL_BUDGET 800s로 확장 권장`" and P7 "`TOTAL_BUDGET 800s 내 완료`"
   - Issue: Current `TOTAL_BUDGET = 600.0` at [core/work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:29) is not used in the generation deadlines; `STAGE_BUDGET` drives Stage 1-3. Inserting Stage 0 before `t_total_start` means the new 90s/180s calls are outside the existing measured budget.
   - Suggestion: Either remove `TOTAL_BUDGET` from acceptance criteria or implement a real end-to-end deadline that includes Stage 0 and passes remaining time into Stage 1-3.

6. [Medium] `assumptions.md` append safety is asserted but not designed
   - Section: "`assumptions.md ... append ... RunLedger의 cross-process safe 패턴 재사용`"
   - Issue: The concrete §7.3 helpers append only to RunLedger. There is no concrete writer for `<work_dir>/assumptions.md`. Current [core/file_io.py](/D:/hoonProJect/worktrees/agent-factory/core/file_io.py:117) `write_text()` is non-atomic, and [core/control/run_ledger.py](/D:/hoonProJect/worktrees/agent-factory/core/control/run_ledger.py:106) only uses `msvcrt`; POSIX `fcntl` is not implemented despite the design text.
   - Suggestion: Specify a dedicated `append_assumption_file(path, entry)` using `core.file_lock.locked_file()` or extend `RunLedger` locking into a reusable helper. Cover Windows and Unix in tests.

7. [Medium] Schema drift scenario contradicts the v2 schema decision
   - Section: "`schema_hash YAML 기록 ❌`" and later "`입력: brainstorming.yaml 의 schema_hash 값 vs raw bytes hash 불일치`"
   - Issue: The design removes `schema_hash` from YAML, so an E2E test based on YAML’s `schema_hash` mismatch is impossible. Drift can only compare prior artifact/ledger hash against current raw YAML hash.
   - Suggestion: Rewrite §8.6 to seed a previous artifact/ledger entry with an old hash, mutate `brainstorming.yaml`, then verify `schema_drift`.

### Missing from Design

- Concrete `project_pipeline.py` insertion point for paused Stage 0 before plan verifier, including how `PreparedProject` should represent `paused_hitl`.
- `af.spec` changes for new modules and YAML data files.
- Correct `CliChatRequest` construction using current provider API.
- Resume entry point for `paused_hitl`; OQ6 leaves it open but P7 claims E2E coverage.
- Concrete atomic/locked implementation for `assumptions.md`.

### Positive Observations

- The document correctly verifies current `work_kind` / `blast_radius` flow into `generate_work_items()` and `ApprovalGate`.
- The v2 correction from `local/system/security/data` toward the actual `isolated/module/cross_module/system_wide` blast-radius taxonomy is directionally aligned with [core/control/change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:35).