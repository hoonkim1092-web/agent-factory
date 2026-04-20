# Code Review: nightly_tick

> Source: scripts/nightly_tick.py
> Date: 2026-04-20 00:51
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Cross reviewer reproduced three distinct behavioral bugs with evidence. Critic's `state_root` wiring concern directly contradicts Cross's REJECT-4 (Cross claims the fix IS present at L158-160 and L253, which aren't visible in the truncated diff). No single Critical finding, but three accepted Highs demand fixes before the next nightly run.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] 스테일 `active_assignments` 재실행 차단 및 허위 progress 계상

- **Critic**: not flagged
- **Cross**: "saved role을 현재 작업 중으로 처리 → 재디스패치 없이 `progress=True` 반환. 재현 완료."
- **Judgment**: Cross가 실제 실행으로 재현함. `busy_roles = set(active.keys())`(L118) + `if not available_roles: return True`(L123) 조합이 이전 tick의 stale 항목을 살아있는 작업으로 취급. 설계 문서(L194-195)가 명시적으로 `result_path` 없는 이전 tick 항목은 재디스패치 대상이라고 규정한다.
- **Action Required**: `busy_roles` 계산 전 이전 `tick_id`에서 온 항목 중 `result_path` 없는 것을 분리해 재디스패치 큐로 전환. stale 항목 시딩 후 실제 재디스패치를 검증하는 e2e 테스트 추가.

#### 2. [ACCEPT] [High] 미드디스패치 `save_state()` 실패가 정상 idle tick으로 오마스킹

- **Critic**: not flagged
- **Cross**: "`save_state` 실패 시 rollback 후 `continue` → tick_once()가 성공(0)으로 종료, consecutive_tick_failures 유지, watchdog STALL_1 진행. 재현 완료."
- **Judgment**: Cross가 monkeypatch로 재현. L159-165의 except 블록이 유일한 후보 태스크 실패를 삼켜버려 alert/failure accounting 전체가 무효화된다.
- **Action Required**: `save_state` 실패 후 re-raise하거나 `tick_once()`가 오류 경로(return 2)로 빠질 수 있는 신호를 전달. `_dispatch_actions()`의 첫 번째 `save_state` 강제 실패 회귀 테스트 추가.

#### 3. [ACCEPT] [Medium] `_max_task_retries` 나이틀리 경로에서 미적용

- **Critic**: not flagged
- **Cross**: "`restore_from()`이 `task_retry_count`를 복원하지만 `_dispatch_from_board()`는 retry 한도를 체크하지 않음. retry gate는 `_orchestration_loop()`(L972-978)에만 존재."
- **Judgment**: Cross가 코드 경로를 추적해 검증. 추가로 nightly tick의 retry key `f"{role}:{task_id}"`(L172)가 orchestrator의 `task_id or f"{role}:{instruction[:60]}"` 형식과 불일치해 복원된 retry state가 사실상 무효다.
- **Action Required**: retry 체크를 `_dispatch_actions()`나 공유 헬퍼로 이동. retry key 생성 로직 통일.

#### 4. [HOLD] [High] `state_root` 파라미터가 함수 내부 및 호출부에서 미연결

- **Critic**: "L157 `save_state(state, workspace)` — `state_root` 미사용. L244-245 호출부도 `state_root=ws` 미전달."
- **Cross**: "REJECT — L158-160에서 `state_root` 우선 사용, L253에서 `tick_once()`가 `state_root=ws` 전달. fix 적용됨."
- **Judgment**: 직접 모순. Diff가 truncated여서 L158-160과 L253 내용을 이 리뷰에서 확인 불가. Cross reviewer는 실제 파일을 실행/검사했고 REJECT 근거로 구체적 라인을 제시. Critic은 diff 일부만 보고 판단했을 가능성.
- **Question for Author**: `scripts/nightly_tick.py` L155-165 및 L250-255 실제 코드를 공유해 `state_root` 분기 존재 여부 확정 필요.

#### 5. [HOLD] [Medium] F2 주석과 `save_state` 경로 불일치 가능성

- **Critic**: "L156 주석(`# F2: assignment를 즉시 디스크에 영속`)이 crash 복원 보장을 명시하지만 `state_root` 미연결이면 경로 불일치 잔존."
- **Cross**: not flagged (finding 4 REJECT 시 같이 해소됨)
- **Judgment**: Finding 4 결론에 종속. `state_root` 실제 연결 확인 시 함께 해소됨.
- **Question for Author**: Finding 4와 동일 — 실제 코드 확인으로 해소.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Stale active_assignments 허위 progress | High | ACCEPT | Cross |
| 2 | save_state 실패 → idle tick 오마스킹 | High | ACCEPT | Cross |
| 3 | _max_task_retries 나이틀리 경로 미적용 | Medium | ACCEPT | Cross |
| 4 | state_root 미연결 여부 | High | HOLD | Critic↔Cross 모순 |
| 5 | F2 주석-경로 불일치 | Medium | HOLD | Critic |

---

### Recommendations

- **즉시**: `_dispatch_actions()` 진입 시 이전 tick stale `active_assignments` 정리 로직 추가 (Finding 1)
- **즉시**: `save_state` 예외 시 `tick_once()` 오류 경로 전파 — 정상 종료 위장 차단 (Finding 2)
- **단기**: retry gate를 `_dispatch_actions()`으로 이동, retry key 형식 통일 (Finding 3)
- **확인**: `nightly_tick.py` L155-165, L250-255 실제 코드 공개 → Finding 4/5 HOLD 해소
- **테스트 갭**: stale assignment 재디스패치, `save_state` 실패 회귀 테스트 2건 추가 필요