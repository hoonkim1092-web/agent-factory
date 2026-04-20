# Code Review: strategy_ledger

> Source: core/memory_system/strategy_ledger.py
> Date: 2026-04-21 00:54
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

두 리뷰어 모두 `record_role_batch()` 신규 메서드에서 실질적 결함을 발견. Critical 없음, High/Medium 4건 → 병합 가능하나 문서화된 리스크 필요.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] 프로젝트-레벨 실패가 모든 역할의 fail_count를 오염

- **Critic**: strategy_ledger.py:268 — eviction이 신규 배치 항목 우선 삭제 (간접 언급)
- **Cross**: `project_pipeline.py:973-997`에서 `stopped_max_cycles`, `partial`, `crashed` 등 인프라 실패도 `succeeded=False`로 매핑 → 모든 (pattern, role) 쌍에 fail 누적
- **Judgment**: diff의 `record_role_batch()` 루프는 `succeeded` 구분 없이 모든 패턴에 카운터를 적용. 오케스트레이션 크래시 1회로 수십 개 role 학습 데이터가 영구 손상됨. Cross 리뷰어가 직접 `python3` 검증까지 수행.
- **Action Required**: `record_role_batch()` 호출부에서 실패 카테고리 구분 추가 — `succeeded=False`인 경우 `INFRA` 실패 여부를 파라미터로 받아 skip하거나, 실패 시엔 아예 기록하지 않는 정책으로 변경.

#### 2. [ACCEPT] [Medium] 단일 프로젝트 반복 패턴으로 "3-sample 임계치" 위조 가능

- **Critic**: 신규 배치 항목이 eviction에서 먼저 삭제됨 (연관 지적)
- **Cross**: `record_role_batch()` 내부에서 `(pattern, owner_role)` 중복 비제거 → 한 배치에 동일 튜플 3개면 즉시 `lookup_best_role()` 신뢰 구간 충족
- **Judgment**: Cross 리뷰어가 실제 Python 검증으로 재현. diff 코드의 루프가 중복 체크 없이 바로 카운터를 증가시키는 구조임이 코드에서 명확.
- **Action Required**: `record_role_batch()` 진입 시 `(pattern.lower(), owner_role, project_id)` 기준으로 `seen_keys` set을 만들어 중복 항목은 첫 번째만 처리.

#### 3. [ACCEPT] [Medium] 회귀 테스트 부재 + 예외 무음 삼킴

- **Critic**: 미언급
- **Cross**: `tests/test_project_pipeline.py`에 `record_role_batch` 또는 `strategy_ledger.json` 검증 없음. 호출부가 `except Exception`으로 모든 실패를 warning log로만 처리.
- **Judgment**: Cross 리뷰어가 `tests/` 전체를 grep으로 확인. 예외 삼킴은 diff 외부(`project_pipeline.py:995-999`)이나 이 변경으로 활성화되는 코드 경로임.
- **Action Required**: (1) `StrategyLedger.record_role_batch()` 단위 테스트 — 혼합 성공/실패, 중복 키 케이스 포함. (2) `lookup_best_role()` 후속 결과 검증 통합 테스트 추가.

#### 4. [ACCEPT] [Medium] Eviction이 방금 추가된 배치 항목을 우선 삭제

- **Critic**: strategy_ledger.py:268 — eviction 순서 문제 명시
- **Cross**: 직접 언급 없으나 Finding #2와 동일 코드 경로
- **Judgment**: `_evict_if_needed()`가 배치 루프 완료 후 1회 호출되는 구조상, 배치 자체가 용량 초과를 유발하면 방금 삽입한 항목들이 삭제 대상이 됨. Critic의 단독 발견이나 코드 구조상 명확한 결함.
- **Action Required**: `_evict_if_needed()` 내 삭제 순서를 `last_seen` 또는 `pass_count+fail_count` 기준으로 정렬해 low-signal 항목을 먼저 제거하도록 변경.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 프로젝트 실패가 role fail_count 오염 | **High** | ACCEPT | Cross |
| 2 | 단일 배치 중복으로 임계치 위조 | Medium | ACCEPT | Both |
| 3 | 회귀 테스트 없음 + 예외 삼킴 | Medium | ACCEPT | Cross |
| 4 | Eviction이 신규 배치 항목 우선 삭제 | Medium | ACCEPT | Critic |

> **Critic #1-3, #5** (project_pipeline.py:786, task_board.py:779, episode_matcher.py:126, record_role_success) — 이번 diff 범위 밖 기존 파일. 별도 이슈로 추적 권장.

---

### Recommendations

1. **즉시**: `record_role_batch()` 진입부에 `seen_keys = set()` 추가 → Finding #2 해소
2. **즉시**: 실패 카테고리 파라미터 또는 성공만 기록 정책 도입 → Finding #1 해소 (High)
3. **병행**: `_evict_if_needed()` 삭제 우선순위 로직 수정 → Finding #4
4. **이번 PR 전**: `record_role_batch` 단위 테스트 + 통합 테스트 최소 1건 → Finding #3