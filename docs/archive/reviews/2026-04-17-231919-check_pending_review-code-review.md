# Code Review: check_pending_review

> Source: scripts/check_pending_review.py
> Date: 2026-04-17 23:19
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Critic's High findings are based on a **misread of an incomplete diff** — the Critic only saw the `300→90` change and assumed line 66 still used `created_at`. In reality, commit `9a494d41` also refactored line 66 to `elapsed = time.time() - updated_at` (verified via `git show 9a494d41`). The code and comment ARE consistent. Only Cross's documentation/test gaps remain.

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Medium] 문서/코드 debounce 값 불일치 (300초 vs 90초)
- **Critic**: not flagged
- **Cross**: "Stage 1 설계는 `300`초, 코드는 `90`초 — file/session cooldown 없이 트리거 빈도만 증가"
- **Judgment**: 확인됨. `docs/2026-04-17-review-trigger-unified-architecture.md:316`은 "기본 300초"로 명시, `Master_Blueprint.md:1106` 변경 이력도 300초 상향을 기록. 90초로 내렸다면 설계 문서와 Blueprint를 같이 갱신해야 함. CLAUDE.md 규칙("코드 수정 + Blueprint 업데이트는 같은 커밋")과도 배치됨.
- **Action Required**: `docs/2026-04-17-review-trigger-unified-architecture.md`와 `Master_Blueprint.md` §12에 "90초로 단축 + 이유(재편집 타이머 리셋 전제)" 한 줄 추가. Stage 2 file/session cooldown 미구현 상태임을 명시.

#### 2. [ACCEPT] [Medium] 실제 caller 경로 통합 테스트 부재
- **Critic**: not flagged
- **Cross**: "`scripts/hook_runner.py check_pending_review` 경로와 기본 debounce 계약(90초)을 frozen time으로 검증하는 테스트 없음"
- **Judgment**: 회귀 테스트 2종은 내부 로직만 monkeypatch 기반으로 검증. UserPromptSubmit → hook_runner → check_pending_review 실제 호출 경로와 **기본값 90초**가 바뀌었을 때 잡히는 가드가 없음.
- **Action Required**: `tests/test_pending_review.py`에 `hook_runner.py check_pending_review` 호출 기반 통합 케이스 1건 추가 + `MIN_BATCH_INTERVAL_SEC == 90` 상수 명시 assertion.

#### 3. [HOLD] [Low] `updated_at` fallback 의도가 주석에 없음
- **Critic**: "Line 57 `data.get("updated_at", data.get("created_at", 0))` — legacy marker 호환 목적 주석 없음"
- **Cross**: not flagged
- **Judgment**: 순수 스타일 지적. 기능 영향 없음. Critic #1~#3이 오독 기반이라 이 항목은 저우선 유지.
- **Question for Author**: legacy marker 파일이 실제 환경에 남아있을 가능성이 있나? 없다면 fallback 제거, 있다면 1줄 주석만 추가하면 됨.

### Critic 고평가 findings 기각 근거

| # | Critic 주장 | 기각 근거 |
|---|---|---|
| 1 (High) | line 66이 여전히 `created_at` | **실제 파일 line 66**: `elapsed = time.time() - updated_at` (verified) |
| 2 (High) | 90초 + `created_at`은 조기 발화 | 전제(#1)가 거짓이라 성립 안 함 |
| 3 (Medium) | 첫 발화 경로만 `created_at` raw | 실제로는 `updated_at` 사용, 비대칭 없음 |

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 문서/코드 debounce 값 불일치 | Medium | ACCEPT | Cross |
| 2 | hook_runner 통합 테스트 부재 | Medium | ACCEPT | Cross |
| 3 | fallback 주석 누락 | Low | HOLD | Critic |
| — | line 66 `created_at` 잔존 | (High 주장) | REJECT | Critic misread |

### Recommendations

- `Master_Blueprint.md` §12에 "2026-04-17: `MIN_BATCH_INTERVAL_SEC` 300→90 + `updated_at` 기준 전환" 한 줄 추가 (CLAUDE.md 규칙).
- `docs/2026-04-17-review-trigger-unified-architecture.md:316`을 실제 값(90초)으로 갱신하거나, 설계 의도대로 되돌리려면 300으로 복구.
- `tests/test_pending_review.py`에 `hook_runner.py check_pending_review` 경로 통합 테스트 1건 추가.
- Critic #1~#3은 incomplete diff에 의한 오독 — 이번 변경으로 조치 없음.