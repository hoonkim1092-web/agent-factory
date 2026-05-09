# Cross-Review Report — Warning Registry & Gate Escalation Design (P1)

- 리뷰 일시: 2026-05-09 09:43:40 KST
- 리뷰 대상: `docs/2026-05-09-warning-registry-and-gate-escalation-design.md` (422줄, v1)
- 리뷰 모드: 단일 설계문서 cross-review (CLAUDE.md 규칙 — af-cross-review 1라운드)
- 외부 프로바이더 fan-out: `codex_cli` (1개 — gemini_cli 미설치)
- Deliberation 라운드: CLI fallback (단일 라운드, codex MCP 미등록 → MCP 비활성)
- 작성 모델: Claude Opus 4.7 (1M context) — 검토 조정자

---

## 라운드 요약

- Round 0 (Claude self-grep baseline 검증): 설계가 인용한 baseline 6개 위치를 모두 grep 1차 반증 → 5개 정합 / 1개 모듈 경로 오기 발견.
- Round 1 (Codex Discovery, CLI exec): 4개 [High] / 1 [Medium] / 1 [Low] 결함 보고. 모두 acceptance #1/#2/#4/#6 직접 충돌.
- Round 2 (Claude Self-Challenge, baseline 재검증): 6개 finding 전부 grep + 코드 발췌로 ACCEPT 가능 확인.
- Round 3/4 (Defense): CLI fallback 경로이므로 생략.

---

## 최종 판정 (Findings)

#### 1. [ACCEPT] [High] §2.1/§5.1 affected_phase enum이 baseline phase taxonomy와 충돌
- **설계 원문**: `affected_phase: str # "scope" | "design" | "build" | "test" | "verify" | "integration"`, `affected_phase_in: [build, test, verify, integration]`
- **baseline 코드**: `core/project_task_board.py:17` — `_PHASE_ORDER = {"scope": 0, "build": 1, "integrate": 2, "code_review": 3, "cross_validate": 4, "verify": 5}`
- **충돌**: 설계의 `design`/`test`/`integration` 3개는 baseline에 존재하지 않음. baseline의 `integrate`/`code_review`/`cross_validate` 3개는 정책에서 누락. work_item_generator.py와 project_task_board.py가 task에 부여하는 실제 phase 값(`scope`/`build`/`verify`/`code_review`/`cross_validate`)과 정책 키가 일치하지 않아 §5.1 phase-aware exempt가 분기되지 않는다.
- **수정 제안**: enum을 baseline taxonomy와 통일. 새 phase("integration")가 필요하면 별도 spec/PR로 baseline 먼저 확장.

#### 2. [ACCEPT] [High] §3.1 row 1 — e2e_command record가 task별 phase를 잃어 §5.1 exempt 무력화
- **설계 원문 (§3.1)**: `WarningRegistry.record(rule_id="e2e_command_missing", count=len(missing_e2e), affected_phase="build", affected_ids=missing_e2e)`
- **baseline 코드**: `core/work_item_generator.py:1048-1056` — `tasks_list` 전체에서 e2e_command 결측만 집계, per-task `phase` 정보를 record에 전달하지 않음.
- **baseline 확인**: 동일 파일 `:166`/`:176`에서 task에 `phase` 필드가 존재함을 확인 (`phase_order.get(_clean(item.get("phase") or "build"), 99)`).
- **충돌**: 단일 record로 21건을 한 번에 기록하면서 phase를 강제로 `"build"`로 지정 → §5.1 정책의 `exempt_when affected_phase_in: [scope, design]`이 작동하지 않는다. P2 활성화 시 scope phase task의 placeholder 결측까지 BLOCK으로 전환되는 false positive 폭발 위험.
- **수정 제안**: phase 그룹별로 record 분할 (e.g., scope에 속한 missing 5건 / build에 속한 16건 별도 record). 또는 record 단위를 task-level로 변경.

#### 3. [ACCEPT] [High] §0/§1.2/§7.2 — BLOCK 활성화 시점 3-way 모순
- **§0 원문**: `실제 BLOCK 승격은 P4(escalation v1)에서 시작한다`
- **§1.2 원문**: `실제 BLOCK 동작은 P2부터 추가한다`
- **§7.2 원문 (Phase 표 P2 row)**: `phase-aware BLOCK (e2e_command_missing만, build/test/verify/integration)`
- **충돌**: 한 문서 내에서 BLOCK 활성화 시점이 3가지로 진술 — P2 차단 vs P4 차단 vs P2는 후보 마킹만(P4가 차단). acceptance #4 (escalation policy v0의 BLOCK 후보 조건)와 acceptance #6 (P2~P6 의존성)의 rollout 경계가 결정 불가.
- **수정 제안**: 한 곳만 정답으로 통일 (권장: §0/§1.2를 §7.2에 맞춰 "P2부터 e2e_command 한정 BLOCK 활성, P4에서 다른 rule들로 확장"으로 일관화하거나, 반대로 모든 BLOCK을 P4까지 stub으로 통일).

#### 4. [ACCEPT] [High] §3.1 row 2 — owner_role_mismatch 마이그레이션이 baseline 시그니처와 충돌
- **설계 원문 (§3.1 row 2)**: `WarningRegistry.record(rule_id="owner_role_mismatch", count=len(mismatched), affected_phase="design", affected_ids=[module_id])`
- **baseline `core/project_task_board.py:227-249`**: `def detect_owner_drift(...) -> bool` — 첫 mismatch에서 `return True`. mismatch 목록을 반환하지 않는다.
- **baseline 호출처 `core/project_pipeline.py:1401-1406`**:
  ```python
  if board_module and detect_owner_drift(board_module, board, task_map=task_map):
      logger.warning("strategy ledger skip — owner drift 감지 (module=%s, plan_owner=%s)", mid, owner,)
      continue
  ```
  변수 `mismatched`도 `module_id`도 존재하지 않음 (`mid` 사용).
- **충돌**: 설계대로 `len(mismatched)` 호출하면 즉시 NameError. `affected_phase="design"`도 §1 finding에 의해 baseline phase가 아님.
- **수정 제안**: 두 가지 중 택일.
  (a) `detect_owner_drift()` 시그니처를 `list[tuple[str,str]]` 반환으로 확장하고 호출처에서 `mismatches = detect_owner_drift(...)` 후 record.
  (b) record 호출 위치를 `detect_owner_drift` 내부로 옮기고, count는 첫 mismatch만이라도 1로 기록 (정확도 떨어지지만 변경 최소).
  + 어느 쪽이든 phase는 baseline에 존재하는 값(예: `build`)으로.

#### 5. [ACCEPT] [Medium] §4.4 — `core/file_io.locked_file` 모듈 경로 오기
- **설계 원문 (§4.4)**: `jsonl append는 core/file_io.locked_file 사용 (이미 Phase D에서 도입). multi-thread 안전.`
- **baseline grep 결과**: `locked_file` 정의는 `core/file_lock.py:38`. 사용처도 `from core.file_lock import locked_file` (project_task_board.py:12, project_mailbox.py:9, work_item_telemetry.py:9, providers/session_adapter.py:21).
- **충돌**: 설계대로 코드 작성 시 `from core.file_io import locked_file` → ModuleNotFoundError 또는 ImportError.
- **수정 제안**: §4.4를 `core/file_lock.locked_file`로 정정.

#### 6. [ACCEPT-ADV] [Low] §3.1 row 2 — 현재 동작 설명 부정확 (logger.info → 실제 logger.warning)
- **설계 원문 (§3.1 row 2 "현재 동작" 셀)**: `bool 반환만 (호출처에서 logger.info)`
- **baseline `core/project_pipeline.py:1402`**: `logger.warning("strategy ledger skip — owner drift 감지 ...")`
- **영향**: 동작 차이는 미미하나, baseline 인용 정확도 문제. 다른 검토자가 "기존엔 로그가 안 떴다"로 오해 가능.
- **수정 제안**: 표 셀을 `logger.warning`으로 정정.

---

## 종합 verdict

**BLOCK** — 4건의 [High] finding(phase enum 충돌, e2e record phase 손실, BLOCK 활성화 시점 모순, owner_role_mismatch 구현 불가능)이 acceptance #1/#2/#4/#6과 정면 충돌. 설계 그대로 P1 코드 구현에 진입하면:
1. P2/P4 escalation_evaluator가 phase 키 mismatch로 모든 분기에서 false positive 또는 silent skip.
2. owner_role_mismatch 마이그레이션 작성 시 NameError.
3. file_lock import 경로 오류로 record() 호출이 모두 ImportError.
4. acceptance #4 (BLOCK 후보 조건)의 rollout 시점이 결정 불가 — review 후 어떤 phase에서 어떤 BLOCK이 켜지는지 PR 머지 결정자가 알 수 없음.

이 4건은 설계 단계에서 수정 가능한 **표 정정 + 시그니처 결정** 수준이며, P1 코드 진입 전 v2 리비전이 권장됨.

Medium/Low 2건은 advisory.

---

## 메모리 규칙 적용 확인

- ✅ "분석 문서 baseline은 실제 코드여야": 설계 인용 6개 위치 모두 grep으로 1차 검증 (5개 정합, 1개 모듈 경로 오기).
- ✅ "stale baseline false positive 반복": 모든 finding은 실제 코드 발췌 + 라인 번호 + 원문 인용 3박자로 뒷받침.
- ✅ "역방향 sycophancy 주의": 균형 인상용 가짜 흠 끼우기 없음. PASS 가능했으나 baseline 충돌이 실재해 BLOCK.

---

## 수용 항목 적용 여부

- **High 4건은 v2 리비전 시 반드시 반영** (BLOCK 사유).
- **Medium 1건 (file_lock 경로)도 v2에서 정정** (코드 진입 시 즉시 import 오류).
- **Low 1건 (logger.info → logger.warning)은 advisory** — v2에서 같이 정정 권장하나 BLOCK 사유는 아님.

