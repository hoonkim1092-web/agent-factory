# Code Review: nightly_state

> Source: core/nightly_state.py
> Date: 2026-04-18 16:42
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

두 리뷰어 모두 High 결함을 발견했으며, 교차 리뷰에서는 런타임 재현(TypeError, False 반환)이 확인되었습니다.

---

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [High] `WatchdogState.from_dict()` — `watchdog_level` 검증 없음
- **Critic**: 임의 문자열이 그대로 저장되어 stall 감지 로직 무력화 가능
- **Cross**: not flagged
- **Judgment**: Critic만 플래그했으나 `is_checkpoint_only()` 하드비교 코드 증거가 명확. BUG-15 패턴과 일치.
- **Action Required**: `_VALID_LEVELS` 집합으로 필터링 후 저장. 유효하지 않은 값은 `"OK"` 폴백.

#### 2. [ACCEPT] [High] `WatchdogState.from_dict()` — `lineage_counters` 문자열 값 → `TypeError`
- **Critic**: `increment_lineage()` L57 `entry["attempts"] += 1`에서 `TypeError` 재현 확인 (이전 세션 교차검증)
- **Cross**: not flagged (다른 파일 집중)
- **Judgment**: 재현 스크립트로 확인된 BUG-15 패턴. `load_state()`의 베어 except가 이를 삼켜 상태 전손으로 이어지는 연쇄 버그.
- **Action Required**: `from_dict()`에서 `int()` 강제 변환 적용. `BudgetState.from_dict()` 패턴 참조.

#### 3. [ACCEPT] [High] `load_state()` — 베어 `except Exception` → 상태 전손
- **Critic**: `consumed_tokens` 리셋 = 예산 초과 후 풀 예산 재시작 위험. H3 패턴.
- **Cross**: Finding 2의 `TypeError`가 이 경로로 삼켜져 `NightlyState()` 재초기화 유발을 확인
- **Judgment**: 두 리뷰어가 독립적으로 동일 경로의 위험성 확인. 최소한 로깅 추가 필수.
- **Action Required**: `except json.JSONDecodeError`로 범위 축소 + `logger.warning("load_state failed: %s", e)` 추가. 근본 해결은 Finding 2 수정.

#### 4. [ACCEPT] [High] `nightly_tick._dispatch_actions()` — 보드 스키마 불일치로 역할 미발견
- **Critic**: not flagged
- **Cross**: `board["modules"][*]["tasks"][*]["role"]` 접근이 실제 `build_project_board()` 출력 구조와 불일치. `roles_in_board` 항상 빈 집합 → tick 즉시 `False` 반환 재현 확인
- **Judgment**: Cross 단독이나 재현 스크립트 증거 강함. nightly 파이프라인 자체가 동작하지 않는 Critical 경로.
- **Action Required**: `board["role_index"]` 또는 최상위 `tasks[*].owner_role`에서 역할 도출로 수정.

#### 5. [ACCEPT] [High] `nightly_tick` — 태스크 페이로드 키 불일치 + `run_id` 누락
- **Critic**: not flagged
- **Cross**: `_dispatch_from_board()`가 `assigned_role`/`subtask_instruction` 반환하지만 nightly 경로는 `role`/`subtask` 읽음. `_execute_agent_task()` `run_id` 누락 `TypeError` 재현.
- **Judgment**: 재현 로그(`태스크 실행 실패 (:): 'role'`) 포함 명확한 증거.
- **Action Required**: 페이로드 키 매핑(`assigned_role→role`, `subtask_instruction→subtask`) + `run_id` 생성 (`nightly_{tick_id}_{role}`) 또는 오케스트레이터 기존 dispatch 경로 재사용.

#### 6. [ACCEPT] [Medium] `NightlyState` — 보드 스냅샷 미저장 (설계/구현 불일치)
- **Critic**: not flagged
- **Cross**: `to_dict()`에 `board` 필드 없음. `.af/board_state.json` 미생성. 설계 문서(L154) 요구사항 위반.
- **Judgment**: 설계 문서 근거 있는 스펙 위반. 재시작 복구 불가능 상태.
- **Action Required**: `NightlyState`에 board snapshot 저장 + `.af/board_state.json` 렌더링 추가. 또는 설계 문서를 `project_board_state.json`을 진실 소스로 명시적 완화.

#### 7. [ACCEPT] [Medium] `active_assignments` — 할당 직후 저장 안 됨
- **Critic**: not flagged
- **Cross**: `finally`에서 클리어 후 L217 `save_state()` 호출 → 스냅샷에 항상 빈 `active_assignments`. 재시작 복구 무효.
- **Judgment**: 코드 흐름 증거 명확. 스펙 계약 불이행.
- **Action Required**: 할당 직후 즉시 `save_state()` 호출, 완료/실패 시 재저장. 또는 `active_assignments`를 영속 계약에서 제거.

#### 8. [ACCEPT] [Medium] `mark_alert()` — 비원자적 파일 쓰기
- **Critic**: `save_state()`·`_write_json_file()`은 atomic 패턴 사용하나 `mark_alert()`만 직접 `open(path, 'w')` 사용. M10 패턴.
- **Cross**: not flagged
- **Judgment**: 동일 파일 내 atomic 패턴 레퍼런스 존재. 수정 방향 명확.
- **Action Required**: `tempfile.mkstemp` → 쓰기 → `os.replace` 패턴 적용.

#### 9. [ACCEPT] [Medium] `_write_json_file()` — 예외 무음 삼킴
- **Critic**: 디스크 오류 시 파생 파일 구버전 잔존하나 오류 전혀 보고 안 됨
- **Cross**: not flagged
- **Judgment**: H3 패턴. 진단 불가 위험 존재.
- **Action Required**: `except Exception as e: logger.debug("_write_json_file failed for %s: %s", path, e)` 추가.

#### 10. [ACCEPT] [Medium] `NightlyState.from_dict()` — `task_retry_count` 타입 미강제
- **Critic**: `BudgetState.from_dict()` 대비 `int()` 변환 누락. 수동 편집 시 TypeError 가능.
- **Cross**: not flagged
- **Judgment**: Critic 단독이나 `BudgetState` 내 동일 패턴과의 불일치가 코드 증거.
- **Action Required**: `{k: int(v) for k, v in (...).items()}` 적용.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `watchdog_level` 검증 없음 | High | ACCEPT | Critic |
| 2 | `lineage_counters` 타입 미검증 → TypeError | High | ACCEPT | Critic |
| 3 | `load_state()` 베어 except → 상태 전손 | High | ACCEPT | Both |
| 4 | `_dispatch_actions()` 보드 스키마 불일치 | High | ACCEPT | Cross |
| 5 | 페이로드 키 불일치 + `run_id` 누락 | High | ACCEPT | Cross |
| 6 | 보드 스냅샷 미저장 (설계 위반) | Medium | ACCEPT | Cross |
| 7 | `active_assignments` 항상 빈 채로 저장 | Medium | ACCEPT | Cross |
| 8 | `mark_alert()` 비원자적 쓰기 | Medium | ACCEPT | Critic |
| 9 | `_write_json_file()` 예외 무음 삼킴 | Medium | ACCEPT | Critic |
| 10 | `task_retry_count` 타입 미강제 | Medium | ACCEPT | Critic |

---

### Recommendations

- **즉시 수정 (BLOCK 해제 조건)**: Finding 1-5. 특히 2→3 연쇄(TypeError → 상태 전손) 및 4→5 연쇄(역할 미발견 → 페이로드 오류)가 nightly 파이프라인 전체를 마비시킴.
- **`from_dict()` 방어 패턴 통일**: `BudgetState.from_dict()`의 `int()` 강제 변환 패턴을 `WatchdogState`와 `NightlyState`에 일관 적용 (Finding 1, 2, 10).
- **설계 문서 vs 구현 정합**: Finding 6 해결 전 `docs/2026-04-18-nightly-autonomous-pipeline.md` 업데이트로 현재 구현 상태를 명확히 문서화.
- **테스트 공백 보완**: Cross 리뷰 지적대로 `tests/`에 `nightly_state`·`watchdog` 관련 테스트 전무. Finding 1-5 수정 후 `build_project_board()` 실출력을 입력으로 쓰는 통합 테스트 추가.
- **Finding 7 선택**: `active_assignments` 영속 계약 유지 시 할당 직후 즉시 저장; 구현 비용이 크면 스펙에서 제거하고 문서 갱신.