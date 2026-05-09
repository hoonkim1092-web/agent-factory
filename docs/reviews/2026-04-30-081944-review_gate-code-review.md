# Code Review: review_gate

> Source: scripts/review_gate.py
> Date: 2026-04-30 08:19
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

3건의 Critical 결함이 두 리뷰어에 의해 독립 확인되거나 코드 증거가 명확합니다. 게이트의 핵심 불변식 — round counting 정확성, BLOCK verdict 우회 금지, commit 후 사이클 리셋 — 이 동시에 깨지므로 머지 전 수정 필수.

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [Critical] `round_count`가 라운드당 1회가 아닌 에이전트 기록당 1회 증가
- **Critic**: round_count는 새 라운드 시작/완료가 아닌 "all required in reviews + 1초 가드 통과"로 증가. Tier 2~3 시나리오에서 T1만 재기록되어도 `this_completed > last_completed + 1.0` 통과 → round_count 폭주.
- **Cross**: 같은 결함 — `record_review_done()`이 already-existing reviews에 의존, round id/`fired_at` guard 부재로 same firing 내 재증가 가능.
- **Judgment**: 두 리뷰 일치, 코드 증거 명확(`scripts/review_gate.py:222-247`). 1초 가드는 분~십분 걸리는 실제 라운드 간격에서는 무의미.
- **Action Required**: `state["round_started_at"]` (또는 `fired_at`/`round_token`) 도입. `all(reviews[a].completed_at >= round_started_at for a in required)`일 때만 증가시키고, 다음 라운드용으로 즉시 갱신.

#### 2. [ACCEPT] [Critical] `stale-but-rounds-capped`가 verdict-block 검사 이전에 PASS 반환
- **Critic**: round_count>=2일 때 step 5에서 즉시 `(False, "stale-but-rounds-capped")` 반환 → step 7의 BLOCK verdict 검사에 도달 못함.
- **Cross**: 동일 결함 확인 — `scripts/review_gate.py:171-172` < `:183-187`. `scripts/check_pending_review.py:82-85`의 정책과도 모순.
- **Judgment**: 두 리뷰 일치. BLOCK verdict 우회 수단은 `AF_SKIP_REVIEW_GATE=1`이어야지 무관한 파일 편집이 아님.
- **Action Required**: rounds-capped 분기는 `stale-review` 차단만 건너뛰고 step 6/7 (new-files-added, verdict-block)에 fall-through하도록 변경. 또는 verdict-block 검사를 step 5 이전으로 이동.

#### 3. [ACCEPT] [Critical] `clear_committed_files`가 `round_count`/`last_round_summary`를 리셋하지 않음
- **Critic**: commit 후 round_count=2가 잔존 → `check_pending_review.py:83`이 `MAX_ROUNDS` 초과로 자동 발화 영구 차단. 게이트는 stale-but-rounds-capped로 통과 → 영구 silent-fail.
- **Cross**: 직접 플래그하지 않음 (단, finding #1·#2와 인과 연결).
- **Judgment**: Critic 단독이지만 코드 증거 결정적(`scripts/review_gate.py:266-292`에 round_count/last_round_summary 손대지 않음 + `enqueue_agent_review.py:109` `setdefault` 보존 동작). 다음 작업 사이클 silent-fail은 Critical.
- **Action Required**: `clear_committed_files` 끝부분에서 `state["files"]`가 비면 `state.pop("round_count", None)`, `state.pop("last_round_summary", None)` 추가. 부분 commit 시 새 라운드용으로 명시적 리셋 정책 결정.

#### 4. [ACCEPT] [High] enqueue 경로의 file-lock 부재로 record_review_done 메타데이터 클로버 위험
- **Critic**: `enqueue_agent_review.py:82-92`는 락 없이 RMW. 새로 추가된 `last_round_summary`/`claim_id`/`round_count`를 enqueue가 인지하지 않아 인터리브 시 손실.
- **Cross**: 플래그 안 됨.
- **Judgment**: Critic 단독이지만 `_state_lock()` 디자인 의도와 명백히 충돌. H5(이미 알려진 락 누락 패턴)의 재현이라는 지적이 타당.
- **Action Required**: `enqueue_agent_review.py`에서 `_state_lock()` 사용. 또는 enqueue가 `reviews`/`last_round_summary`/`claim_id`/`round_count` 키를 보존(merge)하도록 변경.

#### 5. [ACCEPT] [High] `_make_claim_id` 분 단위 절단으로 라운드 식별 충돌
- **Critic**: 분 절단으로 인접 라운드가 같은 분에 들어가면 collision. `time.localtime()`의 timezone/DST 의존성도 위험.
- **Cross**: 동일 결함이지만 HOLD — "현재 consumer가 테스트 외엔 없으므로 의도된 contract에 따라 결정 필요".
- **Judgment**: 두 리뷰 일치. Cross의 HOLD는 "고치지 말자"가 아니라 "invariant 명시 후 고치자". 새로 도입된 `claim_id`가 외부 dedupe에 쓰이는 순간 사일런트 버그.
- **Action Required**: invariant 결정 후 구현 — (a) 라운드 unique → `round_count`/`fired_at` 포함, `time.gmtime()` 사용. (b) 라운드 stable → 영속 round token에서 파생.

#### 6. [HOLD] [Medium] step 5 stale의 'highest tier snapshot' 가정과 병렬 실행 종료 순서 불일치
- **Critic**: 3 에이전트 병렬 시 highest_tier가 마지막에 끝난다는 보장 없음. T3.snapshot이 T2 진행 중 신규 파일을 못 볼 수 있음.
- **Cross**: 플래그 안 됨.
- **Judgment**: 이론적으로 가능하나 실제 enqueue 동작과의 상호작용(파일 추가 타이밍) 미검증. 의미 정합 정책(`union` vs `intersection`) 결정이 선결.
- **Question for Author**: 병렬 발화 시 "신규 파일"의 정의를 어떻게 할 것인가? (모두가 본 파일만 리뷰됨 vs 누구라도 본 파일은 리뷰됨)

#### 7. [ACCEPT] [Medium] 매직 넘버 `+1.0` 초 가드 — 의미 불명확
- **Critic**: 1초가 동시 호출 dedupe인지 라운드 분리인지 불명. Finding #1과 결합 시 라운드 분리에는 무력.
- **Cross**: 직접 플래그 안 됨 (Finding #1과 인과 연결).
- **Judgment**: Finding #1 수정 시 자연스럽게 제거 가능. 단독 Action 불필요.
- **Action Required**: Finding #1의 `round_started_at` 도입과 함께 제거. 동시 호출 dedupe 필요시 별도 sequence/lock token으로.

#### 8. [ACCEPT] [Low] `time.time()` 이중 호출
- **Critic**: L218과 L241에서 별도 호출 → 마이크로초 어긋남.
- **Cross**: 플래그 안 됨.
- **Judgment**: 영향 미미하나 가독성/추론 명료화에 유용. 사소한 cleanup.
- **Action Required**: 함수 진입에서 `now = time.time()` 한 번 잡아 양쪽 사용.

### Cross가 REJECT한 항목
- **Tier 1이 cross-review snapshot 사용 안 함**: Cross가 정확히 분석 — `blast_radius.py:123-125` + `check_pending_review.py:46-55`와 일관됨. Critic은 이를 이슈로 삼지 않음. **REJECT 유지**.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | round_count 증가 시점 결함 | Critical | ACCEPT | Both |
| 2 | stale-rounds-capped가 BLOCK 우회 | Critical | ACCEPT | Both |
| 3 | clear_committed_files 리셋 누락 | Critical | ACCEPT | Critic |
| 4 | enqueue 경로 락 부재 | High | ACCEPT | Critic |
| 5 | claim_id 분 절단 충돌 | High | ACCEPT | Both |
| 6 | 병렬 실행 snapshot 정합성 | Medium | HOLD | Critic |
| 7 | 매직 넘버 +1.0초 | Medium | ACCEPT | Critic |
| 8 | time.time() 이중 호출 | Low | ACCEPT | Critic |

### Recommendations

1. **(필수, Critical 3건 묶음)** 라운드 모델 재설계:
   - `round_started_at` (또는 `fired_at`) 영속 토큰 도입
   - `record_review_done`은 모든 required 에이전트가 `>= round_started_at`으로 완료될 때만 round_count++
   - `clear_committed_files`에서 사이클 종료 시 `round_count`/`last_round_summary`/`round_started_at` 리셋
   - `is_gate_blocked`의 rounds-capped 분기는 stale 차단만 건너뛰고 verdict-block 검사로 fall-through
2. **(필수, High)** `enqueue_agent_review.py`에 `_state_lock()` 적용 또는 라운드 메타데이터 보존 merge 명시
3. **(필수, High)** `_make_claim_id`에 `round_count` (또는 `round_token`) 포함, `time.gmtime()` 전환
4. **(권장)** 함수 진입 시점 `now` 캐싱, +1.0초 가드 제거 (Finding #1 수정 후)
5. **(보류)** 병렬 snapshot 정합성 정책 결정 후 별도 PR