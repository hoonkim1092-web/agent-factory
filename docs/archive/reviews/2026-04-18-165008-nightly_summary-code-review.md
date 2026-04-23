# Code Review: nightly_summary

> Source: scripts/nightly_summary.py
> Date: 2026-04-18 16:50
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

High-severity 결함 3건 — 모두 단독 플래그지만 코드 증거가 명확하다. `WatchdogState.from_dict()` 두 건은 `BudgetState.from_dict()`의 올바른 구현과 직접 비교 가능하며, `load_state()` 베어 except는 이전 세션 ACCEPT [High] 미수정 항목이다.

---

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [High] `WatchdogState.from_dict()` — `watchdog_level` 검증 없음
- **Critic**: "임의 문자열 허용 → STALL 에스컬레이션 영구 무력화 가능"
- **Cross**: not flagged
- **Judgment**: `is_checkpoint_only()` L61이 `== "CHECKPOINT_ONLY"` 하드 비교를 사용하므로, 유효하지 않은 값이 들어오면 레벨 비교가 영원히 실패한다. `BudgetState.from_dict()`는 `int()` 강제로 올바르게 처리 — 불일치 명확.
- **Action Required**: `_VALID_LEVELS` 집합으로 검증, 미해당 값은 `"OK"` fallback.

#### 2. [ACCEPT] [High] `WatchdogState.from_dict()` — `lineage_counters` 값 타입 강제 없음
- **Critic**: "dict 값이 문자열이면 `increment_lineage()` L57에서 `TypeError` → bare except(#3)에 삼켜져 전체 상태 초기화"
- **Cross**: not flagged
- **Judgment**: 연쇄 버그가 코드에서 직접 추적 가능(`watchdog.py:57` → `nightly_state.py:134`). `BudgetState.from_dict()` L69-73과의 불일치가 결함을 입증.
- **Action Required**: `{"level": int(...), "attempts": int(...)}` dict comprehension으로 강제 변환.

#### 3. [ACCEPT] [High] `load_state()` — 베어 `except Exception` → 상태 전손
- **Critic**: "JSON 오류, TypeError, 권한 오류 등 모두 `NightlyState()` 리셋 → 예산/STALL 상태 무효화, 로깅 없음"
- **Cross**: not flagged (간접적으로 #1에서 save_state 언급)
- **Judgment**: 이전 교차 리뷰 ACCEPT [High] 미수정 항목. `consumed_tokens=0` 리셋이 예산 초과 보호를 파괴하는 경로가 명확.
- **Action Required**: `logging.exception(...)` 추가 + JSON decode 오류와 데이터 오류 분리 처리.

#### 4. [ACCEPT] [Medium] `_write_json_file()` — 오류 무음 삼킴
- **Critic**: "파생 파일 쓰기 실패 시 호출자 알림 없음 → 외부 도구가 구버전 상태 읽음"
- **Cross**: not flagged
- **Judgment**: `save_state()`가 `_write_json_file()`의 성공을 가정하는 구조이므로, 쓰기 실패가 무음으로 지나가면 진단 불가 불일치 발생.
- **Action Required**: `logging.warning("Failed to write derived file %s: %s", path, e)` 추가.

#### 5. [ACCEPT] [Medium] `mark_alert()` — non-atomic 파일 쓰기
- **Critic**: "직접 `open().write()` 사용 → 크래시 시 빈/부분 파일"
- **Cross**: not flagged (Cross #3은 `write_summary()`를 다룸)
- **Judgment**: `save_state()`가 같은 파일에서 tempfile+replace 패턴을 올바르게 쓰는 반면 `mark_alert()`는 구 패턴 — 코드 내 불일치로 증거 충분.
- **Action Required**: `_write_json_file()` 또는 tempfile+replace 패턴으로 교체.

#### 6. [ACCEPT] [Medium] `render_summary()` — `workspace` 파라미터 데드
- **Critic**: "파라미터를 받지만 함수 본문에서 사용하지 않음 → API 계약 허위"
- **Cross**: not flagged
- **Judgment**: `write_summary()`가 `render_summary(state, workspace)`로 호출하므로 caller가 workspace가 경로 선택에 영향을 준다고 오해할 수 있다. 코드에서 직접 확인 가능.
- **Action Required**: 파라미터 제거 후 `render_summary(state)`로 호출.

#### 7. [ACCEPT] [Medium] `write_summary()` — non-atomic 파일 쓰기 (M10 패턴 반복)
- **Critic**: "`path.write_text()` 직접 쓰기 — M10 패턴 반복"
- **Cross**: "동일 패턴 ACCEPT, `code-review.md:317` 기존 이슈로 명시됨"
- **Judgment**: 양측 동시 플래그. `nightly_summary.md`는 derived state artifact로 설계 문서에 명시되어 있어 신뢰성 요구사항 명확.
- **Action Required**: `tempfile.mkstemp + os.replace` 패턴 적용.

#### 8. [ACCEPT] [Medium] `nightly-start/stop` 후 `.af/nightly_summary.md` 정체
- **Critic**: not flagged
- **Cross**: "`run_factory_cli.py:197,226`이 `save_state()`만 호출, `write_summary()` 미호출 → stop 후에도 `자율 모드: 활성` 표시 가능"
- **Judgment**: `nightly_tick.py`와의 코드 비교로 직접 입증. 설계 문서 L81이 summary를 reconstructable state set의 일부로 정의.
- **Action Required**: `save_state()` 내부에서 summary 갱신을 수행하거나 `nightly-start/stop` 핸들러에 `write_summary()` 호출 추가.

#### 9. [ACCEPT] [Medium] `nightly_summary.py` — `workspace` 미지정 시 `cwd` 기준 쓰기
- **Critic**: not flagged
- **Cross**: "임시 디렉토리에서 실행 시 그 위치에 `.af/nightly_summary.md` 생성 — 재현 확인됨"
- **Judgment**: Cross 리뷰어가 직접 재현. `nightly_tick.py:181`이 `_REPO_ROOT` 기본값을 사용하는 것과 불일치.
- **Action Required**: `argparse --workspace` 추가, 기본값 `Path(__file__).resolve().parents[1]`.

#### 10. [ACCEPT] [Low] `render_summary()` — `갱신` 타임스탬프가 렌더 시각
- **Critic**: not flagged
- **Cross**: "`state.last_tick_at`을 무시하고 `datetime.now()` 사용 → 오래된 스냅샷 재렌더 시 최신처럼 보임"
- **Judgment**: `nightly_tick.py:203-205`가 `last_tick_at`을 저장하지만 렌더러가 이를 무시하는 불일치. 실제로 오해를 유발하는 UX 버그.
- **Action Required**: `state.last_tick_at` 우선 사용, 없을 때만 `datetime.now()` fallback.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `watchdog_level` 검증 없음 | High | ACCEPT | Critic |
| 2 | `lineage_counters` 타입 강제 없음 | High | ACCEPT | Critic |
| 3 | `load_state()` 베어 except | High | ACCEPT | Critic |
| 4 | `_write_json_file()` 오류 무음 삼킴 | Medium | ACCEPT | Critic |
| 5 | `mark_alert()` non-atomic 쓰기 | Medium | ACCEPT | Critic |
| 6 | `workspace` 파라미터 데드 | Medium | ACCEPT | Critic |
| 7 | `write_summary()` non-atomic 쓰기 (M10) | Medium | ACCEPT | Both |
| 8 | nightly-start/stop stale summary | Medium | ACCEPT | Cross |
| 9 | `nightly_summary.py` cwd 기준 쓰기 | Medium | ACCEPT | Cross |
| 10 | `갱신` 타임스탬프 렌더 시각 | Low | ACCEPT | Cross |

---

### Recommendations

- **즉시 수정 (BLOCK 해제 조건)**: #1, #2, #3 — `WatchdogState.from_dict()` 두 건 + `load_state()` bare except. 이 세 건은 연쇄 버그 경로를 형성하므로 함께 수정.
- **동시 수정 권장**: #5, #7을 M10 패턴 일괄 정리 커밋으로 묶어 처리. `mark_alert()`, `write_summary()` 모두 tempfile+replace로 통일.
- **설계 개선**: #8 해결을 위해 `save_state()` 내부에서 summary를 자동 갱신하는 방향이 가장 안전 — 호출자가 잊을 수 없는 구조.
- **스크립트 강화**: #9(workspace 기본값)와 #6(dead param 제거)은 한 번에 처리 가능.
- **Low priority**: #10은 기능상 무해하지만 운영 가시성에 영향 — #8 수정 시 함께 반영 권장.