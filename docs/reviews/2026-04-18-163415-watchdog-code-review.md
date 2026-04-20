# Code Review: watchdog

> Source: core/watchdog.py
> Date: 2026-04-18 16:34
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High/Medium findings exist. Can merge with documented risks, but Finding 2 (data corruption/silent state loss) should be addressed before production use.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `from_dict` 타입 미검증 + 손상 snapshot 재초기화 (BUG-15 재현)

- **Critic**: "`watchdog_level`에 임의 문자열이 들어와도 예외 없이 통과 → stall 감지 무력화 가능" (Finding 3)
- **Cross**: "`lineage_counters` 엔트리 타입 미검증(문자열 `"3"` → 다음 tick에서 `TypeError`), `load_state()` 예외 삼킴 → 빈 `NightlyState()`로 재초기화, watchdog/budget 누적 상태 전멸" (Finding 1)
- **Judgment**: 두 리뷰어가 `from_dict` 유효성 부재를 다른 각도에서 확인. Cross가 재현 스크립트로 실제 `TypeError` + 상태 리셋을 입증했으며, `code-review.md:340`(BUG-15)와 동일 패턴. `load_state()` 예외 삼킴은 단순 Medium이 아니라 누적 상태 전손 위험이므로 High로 상향.
- **Action Required**:
  - `WatchdogState.from_dict()` — `lineage_counters` 엔트리 `level`/`attempts`를 `int()`로 강제 변환, 변환 실패 시 해당 엔트리 기본값으로 치환
  - `watchdog_level`은 `_VALID_LEVELS = {"OK","STALL_1","STALL_2","STALL_3","CHECKPOINT_ONLY"}`로 검증, 불일치 시 `"OK"` fallback (또는 `ValueError`)
  - `NightlyState.load_state()` — 예외 삼킴 금지. 최소 `logger.error` + quarantine 또는 직전 유효 snapshot 유지

#### 2. [ACCEPT] [Medium] `af.spec` hiddenimports 누락

- **Critic**: "`core/watchdog.py` 신규 파일이지만 `af.spec` hiddenimports 미등재 → frozen 빌드에서 `ModuleNotFoundError`"
- **Cross**: not flagged
- **Judgment**: CLAUDE.md에 명시된 필수 규칙("새 `core/*.py` 파일은 `af.spec` hiddenimports에 반드시 추가")이고, M9 재현 패턴. 단독이지만 규칙 위반 증거가 명확해 ACCEPT.
- **Action Required**: `af.spec` hiddenimports에 `'core.watchdog'`, `'core.nightly_state'` 추가

#### 3. [ACCEPT] [Medium] `lineage_counters` eviction 없음 — 무한 증가

- **Critic**: "`lineage_id`는 추가만 되고 제거 경로 없음 → 장기 실행 시 stale lineage 누적, H2(`_skill_module_cache`) 동일 패턴"
- **Cross**: not flagged (Finding 1과 대상 dict는 같지만 eviction은 별도 지적 없음)
- **Judgment**: H2 패턴과 동일한 구조적 문제. Critic 단독이지만 코드에서 삭제 경로가 없다는 사실이 자명. ACCEPT.
- **Action Required**: `tick_progress()` 또는 별도 `prune_lineage(max_age_ticks)` 에서 완료된 lineage 항목 정리 로직 추가

#### 4. [ACCEPT] [Medium] `CHECKPOINT_ONLY` 진입 시각이 영원히 `None`

- **Critic**: not flagged
- **Cross**: "16회 `tick_no_progress()` 후 결과 `CHECKPOINT_ONLY None`. `tick_no_progress()`는 `watchdog_level`만 바꾸고 `checkpoint_only_since`를 채우는 경로가 없음"
- **Judgment**: 재현으로 확인. 스키마에 필드가 있는데 값이 채워지지 않는 dead field는 향후 time-based escalation 로직이 잘못 동작할 수 있음. Cross 단독이지만 증거 명확. ACCEPT.
- **Action Required**: `tick_no_progress()`에서 `CHECKPOINT_ONLY`로 첫 전이 시점에만 `checkpoint_only_since = tick_id`(또는 현재 시각) 할당; `tick_progress()`에서 리셋

#### 5. [ACCEPT] [Medium] 런타임 진입점 없음 — 사실상 dead code

- **Critic**: not flagged
- **Cross**: "`WatchdogState` import는 `core/nightly_state.py` 하나뿐, 그 `nightly_state.py`도 `core/`·`scripts/`·`tests/` 어디서도 import 안 됨. 현재 PR 상태로는 watchdog 상태 모델이 런타임 행동을 바꾸지 않음. `code-review.md:354-356`도 0-import dead code를 반복 유지보수 문제로 분류."
- **Judgment**: 검색 결과로 입증. 구현 완성도와 무관하게 기능이 동작하지 않으면 리뷰 가치 없는 코드가 머지됨. ACCEPT.
- **Action Required**: tick dispatcher 또는 CLI 실제 진입점과 함께 묶어서 머지하거나, 최소 integration test 하나(`NightlyState`가 실제 `load_state`/`save_state`를 호출하는 경로)로 고정

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `from_dict` 타입 미검증 + 손상 재초기화 (BUG-15) | High | ACCEPT | Both |
| 2 | `af.spec` hiddenimports 누락 | Medium | ACCEPT | Critic |
| 3 | `lineage_counters` eviction 없음 | Medium | ACCEPT | Critic |
| 4 | `CHECKPOINT_ONLY` 진입 시각 미기록 | Medium | ACCEPT | Cross |
| 5 | 런타임 진입점 없음 (dead code) | Medium | ACCEPT | Cross |

---

### Recommendations

- **즉시**: `WatchdogState.from_dict()`에 `int()` 강제 변환 + `_VALID_LEVELS` 검증 추가 (Finding 1 — 데이터 손상 경로)
- **즉시**: `NightlyState.load_state()` 예외 삼킴 제거 → 로그 + quarantine 또는 직전 snapshot 유지 (Finding 1)
- **머지 전**: `af.spec`에 `core.watchdog`, `core.nightly_state` 등재 (Finding 2 — CLAUDE.md 필수 규칙)
- **머지 전**: `CHECKPOINT_ONLY` 전이 시 `checkpoint_only_since` 설정 (Finding 4)
- **이번 PR 또는 직후 PR**: tick dispatcher/CLI 진입점 연결 또는 integration test 추가 (Finding 5)
- **백로그**: `lineage_counters` prune 로직 추가 — 장기 실행 메모리 누수 방지 (Finding 3)