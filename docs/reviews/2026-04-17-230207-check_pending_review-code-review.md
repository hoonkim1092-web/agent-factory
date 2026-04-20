# Code Review: check_pending_review

> Source: scripts/check_pending_review.py
> Date: 2026-04-17 23:02
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff presented to the Critic was empty, so it found nothing. The Cross reviewer independently explored the codebase and surfaced 2 real issues in `scripts/check_pending_review.py`. Both findings have strong code evidence — treating them as ACCEPT per Rule 2.

---

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [High] 첫 발화 기준이 `updated_at`가 아닌 `created_at`에 고정됨

- **Critic**: 리뷰 대상 diff 없음 — 미평가
- **Cross**: `check_pending_review.py:65`에서 첫 발화 여부를 `created_at` 기준으로 판단. `enqueue_agent_review.py:75-86`은 재편집 시 `updated_at`만 갱신하므로, `t=0`에 생성 후 `t=299`에 재편집된 파일이 `t=300`에 즉시 발화 — 사실상 최신 편집 1초 후 트리거됨.
- **Judgment**: debounce 설계 의도("편집이 계속 쌓이는 동안 발화 억제")가 `created_at` 기준으로는 달성되지 않음. `docs/2026-04-17-review-trigger-unified-architecture.md:313-318` 설계 노트와 실제 코드가 불일치. 강한 증거.
- **Action Required**: `check_pending_review.py:65`의 기준을 `max(created_at, updated_at)` 또는 `updated_at`으로 변경. `created_at`이 오래됐지만 `updated_at`이 최근인 케이스를 커버하는 회귀 테스트 추가.

---

#### 2. [ACCEPT] [Medium] 10개 초과 배치에서 파일 경로가 잘려 후속 에이전트가 누락 파일 처리 불가

- **Critic**: 미평가
- **Cross**: `check_pending_review.py:70`에서 hook stdout에 최대 10개 경로만 출력. `CLAUDE.md:32` 및 `.claude/settings.local.json:191-198`에 따르면 UserPromptSubmit이 이 stdout을 제어 신호로 사용하며, `pending_agent_review.json`을 직접 읽는 병렬 소비자는 없음. 11번째 이후 파일은 에이전트에게 전달되지 않음.
- **Judgment**: 배치가 10개를 초과하면 리뷰 누락이 발생. 현재 테스트는 소규모 목록만 커버.
- **Action Required**: 전체 경로 출력 또는 마커 파일(`pending_agent_review.json`) 경로를 항상 stdout에 포함시켜 에이전트가 전체 배치를 직접 로드할 수 있게 수정. `>10` 파일 케이스 테스트 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 첫 발화 기준 `created_at` 고정 debounce 오작동 | High | ACCEPT | Cross |
| 2 | 10개 초과 배치 경로 잘림 | Medium | ACCEPT | Cross |

---

### Recommendations

- `check_pending_review.py:65` — `created_at` → `updated_at` (또는 `max`) 로 기준 변경
- `check_pending_review.py:70` — 마커 파일 경로를 stdout에 항상 포함, 또는 전체 경로 출력으로 변경
- `tests/test_pending_review.py` — (a) `created_at` 오래됐지만 `updated_at` 최근인 케이스, (b) 파일 11개 이상 배치 케이스 회귀 테스트 추가
- Critic에게 빈 diff가 전달된 원인 확인 필요 — 실제 변경이 있는 파일이 리뷰 대상에서 누락됐을 가능성 있음