# Code Review: check_pending_review

> Source: scripts/check_pending_review.py
> Date: 2026-04-30 08:23
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

`check_pending_review.py`의 Phase 0 정책 구현(MAX_ROUNDS, WARN-only no-fire, Tier 1 경량화)은 의도대로 동작하며 코드 품질도 양호합니다. 그러나 **(1) marker 파일에 대한 락 없는 read-modify-write race**, **(2) max-rounds·WARN-only 분기에서 게이트가 차단을 유지하면서 사용자에게 안내가 없는 dead-end UX**, **(3) commit 후 round_count 리셋 누락**이 결합되어 "검증도 안 되고 commit도 안 되는" 봉쇄 상태를 만들 수 있습니다. 머지 전 #1·#2는 보강 권장.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Marker 파일 read-modify-write가 락 없이 수행 — 동시 쓰기 손실
- **Critic**: read-modify-write가 `review_gate._state_lock`(fcntl.LOCK_EX) 보호 없이 수행되어, enqueue/record_review_done의 동시 쓰기와 race window를 형성. 이번 PR이 새 필드(`round_count`, `last_round_summary`, `blast_tier`)를 추가하면서 race window를 더 넓힘.
- **Cross**: not flagged
- **Judgment**: 코드 증거 명확. `scripts/check_pending_review.py:67-130`에서 lock 없이 `json.load` → mutate → atomic write를 수행하는 반면, `scripts/review_gate.py:53-73`은 동일 marker에 대해 `_state_lock`을 잡음. atomic write는 stale snapshot을 atomic하게 덮어쓸 뿐이라 손실 보장이 안 됨. enqueue 동시성 시 편집 파일이 큐에서 누락 → 검증 우회 가능.
- **Action Required**: `review_gate._state_lock(workspace)`을 import하여 read·mutate·write 전체를 같은 락 안에서 수행. 또는 `fired_at`만 별도 sentinel(`.fired`)로 분리해 marker JSON을 변경하지 않게 분리.

#### 2. [ACCEPT] [High] Dead-end UX — 게이트가 차단 유지 + 알림 부재
- **Critic** (#2): MAX_ROUNDS 도달 시 silent return. `review_gate.py:184-187`은 잔존 BLOCK이면 `verdict-block`으로 차단 유지 → 사용자는 commit 막힘 + 안내 없음.
- **Cross** (#1): WARN-only suppression 후 재편집 시 `enqueue_agent_review.py:89-92`가 `updated_at`을 갱신하지만, `review_gate.py:163-173`은 `round_count < 2`인 동안 `stale-review`로 차단. notifier가 `check_pending_review.py:89`에서 출력 억제 → 게이트와 정책 불일치.
- **Judgment**: 두 리뷰어가 동일 root cause(notifier 억제 vs 게이트 차단의 정책 불일치)를 다른 진입 시나리오에서 지목. 양쪽 모두 commit 차단 + 발화 안 됨 dead-end로 수렴.
- **Action Required**: 두 분기(MAX_ROUNDS 도달, WARN-only suppression) 모두에서 한 번이라도 사용자에게 안내 출력 — "MAX_ROUNDS 도달 → AF_SKIP_REVIEW_GATE=1 또는 수동 재실행", "WARN-only로 발화 보류 — commit이 막힌다면 우회 옵션 사용". marker에 `capped_notified_at`/`warn_only_notified_at` 1회용 플래그를 두고 stderr/stdout으로 출력. 또는 `review_gate.py`가 동일 WARN-only/capped 케이스를 PASS 처리하도록 정책 정렬. 통합 테스트 추가(no-BLOCK round → re-edit → notifier/gate 일치 검증).

#### 3. [ACCEPT] [Medium] commit 후 `round_count`/`last_round_summary` 리셋 누락
- **Critic** (#4): `scripts/review_gate.py:266-292` `clear_committed_files`가 files/reviews는 비우지만 `round_count`와 `last_round_summary`는 보존. 다음 사이클에서 enqueue가 `setdefault`로만 다루므로 이전 값 유지 → 새 사이클임에도 본 PR의 MAX_ROUNDS 캡이 즉시 발화 봉쇄.
- **Cross**: not flagged
- **Judgment**: 코드 증거 명확. `scripts/enqueue_agent_review.py:109` `setdefault` 동작과 본 PR(`check_pending_review.py:83`) silent skip 결합 시 새 사이클이 즉시 봉쇄됨. 본 PR의 MAX_ROUNDS 효과를 무력화하는 버그.
- **Action Required**: `clear_committed_files`에서 `state["files"]`가 빈 리스트가 될 때 `state["round_count"] = 0`, `state.pop("last_round_summary", None)` 함께 수행. 본 PR 또는 즉시 후속 PR에 포함.

#### 4. [ACCEPT] [Medium] 본 PR이 `review_gate.round_count` 카운팅 정확성에 의존
- **Critic** (#3): MAX_ROUNDS·WARN-only no-fire는 `round_count`가 정확해야 의미 있음. 직전 라운드 비평에서 `record_review_done`이 round_count를 부풀릴 수 있다는 [Critical] 결함이 확인됨(`scripts/review_gate.py:222-247`).
- **Cross**: not flagged
- **Judgment**: 본 파일은 결함 없으나 의존 결함이 미수정이면 효과 보장 안 됨. PR 시리즈 차원의 정합성 이슈.
- **Action Required**: 같은 PR/시리즈에서 `record_review_done()`에 `round_started_at` 또는 `round_token` 가드를 추가해 라운드 경계 명시. 본 PR 단독 머지는 권장하지 않음.

#### 5. [ACCEPT] [Low] 누락/null 필드에 대한 `int()` 캐스트 TypeError 위험
- **Critic** (#5): `round_count = int(data.get("round_count", 0))` 등이 `None`/`dict`이면 TypeError. 외부 try/except는 `json.load`만 보호.
- **Cross**: not flagged
- **Judgment**: 정상 경로에서는 발생 안 하나 marker 손상 시 hook을 깸. 방어 코딩 차원에서 처리 권장.
- **Action Required**: 65-80행 try 블록을 90행 직전까지 확장하거나 `_safe_int(v, default)` 헬퍼로 감싸기.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Marker read-modify-write race | High | ACCEPT | Critic |
| 2 | Dead-end UX (suppress + block) | High | ACCEPT | Both |
| 3 | commit 후 round_count 리셋 누락 | Medium | ACCEPT | Critic |
| 4 | review_gate.round_count 의존 | Medium | ACCEPT | Critic |
| 5 | int() TypeError 위험 | Low | ACCEPT | Critic |

### Recommendations
- **머지 전 필수**: #1 락 도입(또는 sentinel 분리), #2 알림 1회 출력 또는 게이트 정책 정렬(통합 테스트 추가).
- **본 PR 또는 즉시 후속 PR**: #3 `clear_committed_files`에서 `round_count`/`last_round_summary` 리셋, #4 `record_review_done`에 라운드 경계 토큰 추가.
- **선택적 강화**: #5 marker 파싱 try 블록 확장 또는 `_safe_int` 헬퍼.
- **Cross가 REJECT한 사항**(Tier 1 단일 에이전트, `_agents_for_tier` 중복)은 현행 동작 일관성·메인테너빌리티 노트 수준으로 차단 사유 아님.