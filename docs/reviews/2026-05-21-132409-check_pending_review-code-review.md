# Code Review: check_pending_review

> Source: scripts/check_pending_review.py
> Date: 2026-05-21 13:24
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

코드 변경 자체는 CLAUDE.md §Review-Gate 정책(review-first, max_rounds=5)과 일치하나, **(a) 동일 정책을 노출하는 다른 사용자 가시 표면 5+ 곳이 옛 순서를 유지**하고 **(b) `_agents_for_tier()` 가 정적 tier 리스트만 반환해 critic T3 escalation 재발화 시 이미 완료된 에이전트를 다시 안내**한다. 머지 가능하지만 propagation + 미반환 agent 계산은 같은 PR에서 정리 권장.

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] Review-order 변경이 다른 emitter/문서/테스트에 전파되지 않음
- **Critic**: `.githooks/pre-commit:65`, `Master_Blueprint.md:1208` (last_updated: 2026-05-21 표시지만 본문은 옛 순서)에서 옛 순서 유지. CLAUDE.md "코드+Blueprint 같은 커밋" 원칙 위반.
- **Cross**: 동일 + `scripts/review_gate.py:528`, `scripts/hook_runner.py:318`, `scripts/blast_radius.py:205`, `tests/test_review_gate_phase0.py:332`도 옛 순서. 5+ 표면 모두 `af-test-runner → af-critic → af-cross-review`.
- **Judgment**: 양쪽이 동일 영역을 지목하며 Cross가 더 광범위한 증거 제시. 사용자가 같은 정책에 대해 두 다른 순서를 동시에 보게 됨 → 운영상 혼선 보장된 상태. Severity 격상.
- **Action Required**: 동일 커밋에서 (1) `.githooks/pre-commit:65`, (2) `Master_Blueprint.md:1208` + §12 한 줄, (3) `scripts/review_gate.py:528`, (4) `scripts/hook_runner.py:318`, (5) `scripts/blast_radius.py:205`의 `required_agents()`, (6) `tests/test_review_gate_phase0.py:332` 모두 `af-critic → af-cross-review → af-test-runner`로 갱신. 가능하면 순서 상수를 단일 모듈(예: `review_gate.AGENT_ORDER`)로 export.

#### 2. [ACCEPT] [High] `_agents_for_tier()` 가 이미 완료된 에이전트를 재안내할 수 있음
- **Critic**: 미플래그.
- **Cross**: `scripts/check_pending_review.py:181` 에서 tier 기반 정적 리스트 반환. Deterministic T3-skip 후보가 `af-critic` 먼저 실행 → critic이 `t3_required: unknown|yes` 반환 → `review_gate.py:346-347` 이 `fired_at` 클리어 + tier 확장 → 다음 prompt 가 critic 완료를 무시하고 3-agent 전체를 다시 안내.
- **Judgment**: Cross 가 단독이지만 evidence 가 매우 구체적 (`review_gate.py:346-347`, `:224-228`, 기존 `test_review_gate.py:254` rearm 경로 명시). 본 패치가 도입한 review-first 순서와 deterministic T3-skip 조합에서 실제 발생 가능한 logic 갭. critic-first 가 디폴트가 된 만큼 이 경로가 hot path.
- **Action Required**: `_agents_for_tier()` 또는 호출부에서 `_required_tiers_for(data)` minus `state["reviews"]` 의 완료 목록으로 표시 리스트 계산. pending-hook 테스트 1건 추가: deterministic skip 후보 → critic `unknown` → 다음 prompt 에 `af-cross-review` + 누락 tier만 노출.

#### 3. [ACCEPT] [Low] `MAX_ROUNDS` 가 두 파일에 분리 관리됨 (현재 값 일치, 동기화 부재)
- **Critic**: `scripts/check_pending_review.py:30` (`MAX_ROUNDS = 5`) 와 `scripts/review_gate.py:282` (`< 5` 하드코딩) 분리. 다음에 한쪽만 7/10 으로 바꾸면 안내와 게이트 동작 어긋남. §3 M4 매직넘버 패턴 재현.
- **Cross**: REJECT — "현재 값은 정렬됨" + `tests/test_review_gate_phase0.py:279/:290` 가 5 를 커버.
- **Judgment**: Cross 의 REJECT 는 "지금 깨지지 않음"에 대한 평가, Critic 의 ACCEPT 는 "구조적 drift 리스크"에 대한 평가. 둘 다 사실. 본 패치는 **현재 정상**이지만 **단일 상수로 통합 또는 sync 주석**이 미래 사고 비용을 낮춤. Severity Low 로 격하.
- **Action Required**: `review_gate.py:282` 옆 `# Sync with scripts/check_pending_review.py MAX_ROUNDS` 주석 1줄, 또는 import 일원화 (1줄 패치).

#### 4. [ACCEPT] [Low] 기존 capped 큐가 cap 해소 후 자동 재발화 — 운영 로그 부재
- **Critic**: `scripts/check_pending_review.py:119-132`. 기존 `round_count==2, capped_notified_at` 큐가 본 패치 적용 후 `2 >= 5 = False` 로 재발화. 의도된 동작이나 추적 로그 부재.
- **Cross**: 미플래그.
- **Judgment**: Critic 단독, 코드 변경 미권장이라 명시. NEXT_STEPS.md 또는 §12 메모 1줄로 충분.
- **Action Required**: §12 변경 이력에 "MAX_ROUNDS 2→5: 기존 cap 도달 큐가 자동 재발화될 수 있음 (의도)" 한 줄.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Review-order 전파 누락 (.githooks/pre-commit, Blueprint, review_gate, hook_runner, blast_radius, tests) | High | ACCEPT | Both |
| 2 | `_agents_for_tier()` rearm 시 완료된 critic 재안내 | High | ACCEPT | Cross |
| 3 | `MAX_ROUNDS` 분리 관리 (현재 정렬, 미래 drift 리스크) | Low | ACCEPT | Critic (Cross REJECT 부분 수용) |
| 4 | 기존 capped 큐 재발화 — 운영 로그 부재 | Low | ACCEPT | Critic |

### Recommendations
- **머지 전 필수** (#1, #2): 6개 파일 순서 통일 + `_agents_for_tier()` 가 `state["reviews"]` 차감 후 미완료 에이전트만 노출하도록 수정 + pending-hook 테스트 1건 추가. 양쪽 다 본 패치가 도입한 review-first/critic-first 조합의 일관성 문제라 같은 PR 에서 닫는 게 정합.
- **머지 후 follow-up** (#3, #4): `MAX_ROUNDS` 단일 상수화 + §12 한 줄 메모. 별 PR 가능.
- **T3 advisory 수용**: Critic 의 t3_required=yes 판단(정책 상수 + 게이트 안내 변경은 운영 정책 변경)은 타당. cosmetic 분류 금지.