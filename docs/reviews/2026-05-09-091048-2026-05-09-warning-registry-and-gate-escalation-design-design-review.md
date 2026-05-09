# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 09:10
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] 잘못된 lock 모듈 참조로 구현 지시가 실패함
   - Section: "`jsonl append는 `core/file_io.locked_file` 사용 (이미 Phase D에서 도입). multi-thread 안전.`"
   - Issue: `core/file_io.py`에는 `locked_file`이 없다. 실제 lock은 `core/file_lock.py:37`의 `locked_file(path, timeout=...)`이다. 설계 그대로 구현하면 import 단계에서 실패한다.
   - Suggestion: 문서를 `from core.file_lock import locked_file`로 수정하고, `record()`의 jsonl append와 `_summary.json` read-modify-write 모두 동일한 lock 파일을 쓰도록 명시하라.

2. [High] `owner_role_mismatch` 기록에 필요한 데이터가 현재 helper에서 나오지 않음
   - Section: "`helper 시그니처는 유지하되, 호출처(`core/project_pipeline.py:1401`)에서 drift 발견 시 `WarningRegistry.record(... count=len(mismatched) ... affected_ids=[module_id])``"
   - Issue: 현재 `detect_owner_drift()`는 `bool`만 반환한다 (`core/project_task_board.py:227-248`). 호출처도 boolean만 본다 (`core/project_pipeline.py:1401`). `mismatched` 리스트가 존재하지 않으므로 `count=len(mismatched)`는 구현 불가능하다.
   - Suggestion: `find_owner_drift(module, board, task_map=None) -> list[str]` 같은 새 helper를 추가하고, 기존 `detect_owner_drift()`는 그 helper를 감싼 bool wrapper로 유지하라.

3. [High] `runtime/warnings` 저장 기준이 frozen/multi-PC 구조와 충돌함
   - Section: "`runtime/warnings/<project_slug>/...`", "`runtime/warnings/_global/`"
   - Issue: 기준 루트가 정의되지 않았다. 현재 프로젝트 런타임 저장소는 여러 곳에서 `{workspace}/.af_runtime/...`를 쓴다 (`core/control/run_ledger.py`, `core/continuity/runtime_paths.py`). 반면 상대 경로 `runtime/warnings`는 실행 cwd, frozen `dist/af/af.exe`, `AGENT_PROJECT_ROOT`가 다른 환경에서 서로 다른 위치에 생긴다. 같은 `project_slug`를 가진 다른 PC/워크스페이스도 충돌 가능하다.
   - Suggestion: 프로젝트별 record는 `{workspace}/.af_runtime/warnings/<slug>/`로 고정하고, `_global`은 `AGENT_GLOBAL_PROJECT_ROOT` 또는 `core/config_paths.GLOBAL_DATA_DIR` 하위로 명시하라. approval-gate 링크도 절대경로가 아니라 work-item 기준 상대경로로 계산하라.

4. [Medium] `evidence_quality_warn` record에 필요한 `project_slug`/workspace 주입 경로가 빠짐
   - Section: "`core/research_verifier.py:362-366` ... `WarningRegistry.record(rule_id=\"evidence_quality_warn\", affected_phase=\"scope\", ...)`"
   - Issue: `ResearchVerifier()`는 현재 상태가 없고, `verify_with_retry()` 인자도 `evidence_fn`, `task_input`, `max_retries`뿐이다. 호출처 `core/project_pipeline.py:725-759`는 `target_workspace`를 알고 있지만 verifier에 전달하지 않는다. `WarningRecord.project_slug`가 필수인데 이 migration에는 slug를 얻는 방법이 없다.
   - Suggestion: record는 `ProjectPipeline` 호출처에서 `_vr.status != "pass"`일 때 수행하거나, `ResearchVerifier(workspace, project_slug)` / `verify_with_retry(..., project_slug=...)` 계약을 설계에 추가하라.

5. [Medium] frozen build hiddenimports 갱신 누락
   - Section: "`core/warning_registry.py` 신설", "`core/escalation_evaluator.py` stub 신설", P1 PR scope 목록
   - Issue: `af.spec`는 core 모듈을 명시 hiddenimports로 관리 중이고 현재 `core.warning_registry`, `core.escalation_evaluator`가 없다. Agent Factory는 frozen build 호환을 요구하는데 P1 scope에 `af.spec` 변경이 빠져 있다.
   - Suggestion: P1 scope에 `af.spec` hiddenimports 추가와 frozen smoke 검증을 넣어라.

6. [Medium] approval-gate link wiring의 idempotency가 정의되지 않음
   - Section: "`initialize()` / `apply_verification_verdict()` 시 link 자동 주입."
   - Issue: `ApprovalGate._render()`는 `review_notes` 문자열만 받는다 (`core/approval_gate.py:323-360`). `apply_verification_verdict()`는 기존 notes에 새 라인을 누적한다 (`core/approval_gate.py:213-240`). link 주입을 단순 문자열 append로 구현하면 approve/invalidate/block 흐름에서 중복 라인이 생길 수 있다.
   - Suggestion: `_ensure_decision_report_link(review_notes, slug)`를 별도 helper로 두고, 이미 `gate_decision_report:`가 있으면 교체/유지하는 idempotent 동작을 acceptance에 추가하라.

### Missing from Design

- `WarningRegistry.record()` 호출 시 `workspace`/storage root를 어떻게 받을지.
- `project_slug`가 없거나 같은 slug가 여러 workspace에 존재할 때의 충돌 처리.
- `_summary.json` 손상/부분 write 복구 방식.
- frozen build 검증 항목과 `af.spec` 수정 항목.
- `false_positive_override`가 `_decision.md`의 사용자 텍스트에서 어떤 record에 매핑되는지.
- Windows 경로에서 approval-gate 링크를 POSIX-style markdown relative path로 렌더링하는 규칙.

### Positive Observations

- 기존 logger warning과 `evidence._warnings`를 유지하고 registry를 병행 기록하는 방향은 하위 호환성이 좋다.
- approval-gate 본문에 decision report를 inline하지 않고 링크로 분리한 판단은 현재 `_parse()`/`_render()`의 5섹션 구조와 잘 맞는다.