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

1. [Critical] `paused_hitl` 차단 지점이 Stage 1~3 이후라서 목적을 달성하지 못함
   - Section: "`StageRouter.run(...)` inserted at `:1095`" and "`gate.initialize(...)` called at line 1238; paused state ... `project_pipeline` checks before plan_verifier"
   - Issue: 현재 `core/work_item_generator.py` 흐름은 Stage 1 `:1104`, Stage 2 `:1125`, Stage 3 `:1156` 실행 후 `ApprovalGate.initialize()`가 `:1233`에서 호출된다. 설계대로면 HITL pause여도 이미 Stage 1~3 문서를 생성하고 LLM 비용을 쓴 뒤에야 gate가 만들어진다. `project_pipeline`의 plan_verifier 전 체크는 너무 늦다.
   - Suggestion: Stage 0 직후 `if stage0.paused_hitl or stage0.blocked:` 분기를 명시해야 한다. 이 경우 `approval-gate.md`를 즉시 생성하고 Stage 1~3에 진입하지 않는 반환 계약을 설계하라.

2. [Critical] `work_kind` / `blast_radius` 입력원이 아직 비어 있음
   - Section: "`core/project_pipeline.py:970-971` 호출 시 `work_kind=str(project_brief.get(\"work_kind\") or \"\")` 전달"
   - Issue: 실제 `core/project_pipeline.py:815-817`은 `requested_role`, `route`, `generated_at`만 `project_brief`에 넣는다. `ControlPlaneIntake.normalize()`는 `core/project_pipeline.py`에서 호출되지 않고, 현재 사용은 `_recall_from_memory()`뿐이다. 따라서 StageRouter는 대부분 `work_kind=""`, `blast_radius=""`로 실행된다.
   - Suggestion: `prepare_documents()`에서 `ControlPlaneIntake.normalize(task_input, target_workspace, route, board=task_board)`를 호출하고 결과의 `work_kind`와 `change_impact.blast_radius`를 `project_brief`에 저장한 뒤 `generate_work_items()`에 전달하도록 설계를 추가하라.

3. [High] frozen build 설계가 Python 모듈만 다루고 YAML 리소스를 누락함
   - Section: "`af.spec hiddenimports 추가 대상` ... `core.control.stage_router`, `question_router`, `stage_artifacts`, `verdicts`, `context_scanner`"
   - Issue: §9.12는 hiddenimports만 추가한다. 하지만 §9.6/§9.7에서 새로 만드는 `core/control/questions/goal_clarification.yaml`, `brainstorming.yaml`은 데이터 파일이다. 현재 `af.spec` datas는 `policy.yaml`, `core/research/packs`만 포함하므로 frozen `af.exe`에서 schema load가 실패할 수 있다.
   - Suggestion: `af.spec` `datas`에 `('core/control/questions', 'core/control/questions')`를 추가하거나 `importlib.resources` 기반 로딩 + PyInstaller data collection을 설계에 포함하라.

4. [High] `QuestionRouterCliLLMCaller` 예시가 현재 provider API와 맞지 않음
   - Section: "`CliChatRequest(... response_format={\"type\": \"json\"})`"
   - Issue: 실제 `core/providers/cli.py:31-39`의 `CliChatRequest`에는 `response_format` 필드가 없다. `execute_cli_chat()`도 `execute_cli_chat(request, run_command=None, install_command_runner=None)` 형태다. 설계대로 구현하면 `TypeError`가 난다.
   - Suggestion: JSON 강제는 `system_prompt/task_input`에 넣거나 provider별 지원 여부를 감싼 새 필드를 먼저 `CliChatRequest`에 추가하는 별도 설계가 필요하다.

5. [High] RunLedger 이벤트가 active run 상태를 오염시킬 수 있음
   - Section: "`append_assumption()` ... `LedgerEntry(state=\"assumption\")`", "`append_paused_hitl()` ... `state=\"paused_hitl\"`"
   - Issue: `RunLedger.get_active_runs()`는 최신 entry의 `closed_at`이 비어 있으면 active로 본다. 설계의 새 helper는 `started_at`, `updated_at`, `work_kind`, `change_impact_summary`를 기존 run에서 복사하지 않는다. assumption append가 최신 entry가 되면 해당 run이 `started_at=""`인 active/stale run처럼 보일 수 있다.
   - Suggestion: `append_assumption()`은 `update_run(..., metadata={...})` 형태로 기존 latest를 보존하거나, 별도 event journal을 둬야 한다. 최소한 latest entry의 lifecycle 필드를 복사하라.

6. [Medium] 4-token blast taxonomy를 선언했지만 acceptance test가 다시 invalid token을 사용함
   - Section: "`§7.2 ApprovalGate 매트릭스, §6.4 fallback 정책, §8 E2E 시나리오 모두 정정된 4-token taxonomy 사용`"
   - Issue: §9.8은 `NEEDS_ADR × {local, module, system_wide, security, data}` 5케이스를 요구한다. 실제 유효값은 `isolated | module | cross_module | system_wide`이고, 현재 `tests/test_approval_gate_domain_review.py`도 invalid `local/system` 토큰 방지를 검사한다.
   - Suggestion: §9.8을 `{isolated, module, cross_module, system_wide}`로 고치고 `security/data`는 `BlockCause` 테스트로 분리하라.

### Missing from Design

- Stage 0 pause/block 시 `generate_work_items()`가 Stage 1~3를 건너뛰는 정확한 반환 흐름.
- `project_brief["work_kind"]`와 `project_brief["blast_radius"]`를 누가 채우는지에 대한 concrete wiring.
- PyInstaller data file bundling for `core/control/questions/*.yaml`.
- `RunLedger` lifecycle state와 audit event를 분리하는 정책.
- `CliChatRequest` 현재 시그니처와 호환되는 JSON 응답 강제 방식.

### Positive Observations

- v2가 `schema_hash`를 YAML 자기참조 필드에서 제거하고 artifact/ledger 기록으로 옮긴 점은 실제 drift 문제를 잘 피한다.
- `QuestionRouter`를 side-effect-free로 두고 `StageRouter`가 파일/ledger 책임을 갖는 분리는 구현 경계가 명확하다.