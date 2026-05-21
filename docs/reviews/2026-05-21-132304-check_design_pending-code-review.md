# Code Review: check_design_pending

> Source: scripts/check_design_pending.py
> Date: 2026-05-21 13:23
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

코드 변경 자체는 `CLAUDE.md:118` 정책과 일치하며 안전. 다만 메시지 wording 범위 모호성(Cross HOLD)과 Blueprint/companion 파일 동기화 미확인(Critic Low/Info) 2건이 남아있어 머지 전 정리 권장.

### Aggregated Findings (2 total)

#### 1. [HOLD] [Medium] 메시지 wording 범위 모호 — `design_review_watcher.py`와 충돌 가능
- **Critic**: 미플래그 (메시지 정합성을 positive로 평가)
- **Cross**: `scripts/design_review_watcher.py:260-276`은 여전히 `review_type == "design"`에서 critic + cross를 함께 실행. 새 메시지의 "af-critic은 설계문서에 효과 없음 — 2026-05-01 정책" 문구가 글로벌 정책으로 읽혀 watcher 동작과 모순으로 해석될 위험.
- **Judgment**: Cross의 evidence가 구체적 (`design_review_watcher.py:260` 명시). 변경의 의도가 *UserPromptSubmit hook 한정* 인지 *글로벌 정책 변경* 인지 diff에서 단언 불가 → HOLD.
- **Question for Author**: 이 변경은 (a) hook 메시지만 좁히는 것인가, (b) `design_review_watcher.py`도 cross-only로 바꿔야 하는가? (a)면 메시지를 "이 UserPromptSubmit 알림에는…"으로 좁히고, (b)면 watcher도 같은 커밋에서 갱신.

#### 2. [ACCEPT] [Low] Blueprint + companion 파일 동기화 확인 필요
- **Critic**: `Master_Blueprint.md`에 `af-design-review-pending` 옛 정책(af-critic 병렬) 흔적이 남아있을 가능성 + §12 이력 항목 미갱신 우려. 또한 `scripts/check_pending_review.py`(MAX_ROUNDS=2→5, agent 순서)가 동일 커밋에 묶여야 review-gate 일관성 보존.
- **Cross**: 미플래그 (caller path 호환성만 검증).
- **Judgment**: `git status` 상 `scripts/check_pending_review.py`, `scripts/review_gate.py`도 변경 중이므로 Critic 우려는 실재. 사용자 규칙 "코드 + Blueprint 같은 커밋" 적용.
- **Action Required**:
  1. `Master_Blueprint.md`에서 `af-design-review-pending` 관련 §섹션 + §12 이력 항목을 동일 커밋에 갱신.
  2. `check_design_pending.py`, `check_pending_review.py`, `review_gate.py` 3개를 정책 동기화 단일 커밋으로 묶기.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | wording 범위 모호 (watcher와 충돌) | Medium | HOLD | Cross |
| 2 | Blueprint + companion 파일 동기화 | Low | ACCEPT | Critic |

### Recommendations
- **결정 필요**: 메시지 문구가 hook-local인지 글로벌 정책인지 명시. hook-local이면 "이 UserPromptSubmit 알림에는 af-cross-review 1개만…"으로 좁힘. 글로벌이면 `design_review_watcher.py:260` 동시 갱신 + 테스트.
- **커밋 묶기**: `scripts/check_design_pending.py` + `scripts/check_pending_review.py` + `scripts/review_gate.py` + `Master_Blueprint.md`(§해당 섹션 + §12 이력)를 한 커밋으로 동시 staging.
- **테스트 갭**: `tests/test_check_design_pending.py` 부재는 기존 리뷰 문서(`docs/reviews/2026-05-21-120856-…`)에 이미 기록 — 본 PR에서 새 finding으로 추가하지 않음.