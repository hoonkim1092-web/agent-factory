---
name: 3-Tier 검증 비용 감축 플랜 (Phase 1~4)
description: 3-tier 검증 비용(195K 토큰/28분 → 60K/6~10분) 감축 플랜이 진행 중. Phase 1부터 순서대로 진행.
type: project
originSessionId: 0298a7dc-abb2-441c-909b-48c280653b83
---
3-tier 교차검증 비용 감축 플랜이 2026-04-30 합의되어 진행 중. 전체 설계 문서: `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md`.

**Why**: 이번 commit 검증 비용 195K 토큰 / 28분 — WARN-only인데 과도. af-critic 46 tool call의 대부분이 반복 탐색. cross-review가 가장 가치 있는 발견(WARN-1: blast_tier 책임 경계)을 했지만 137K 소모.

**진행 순서 (변경 금지 — 핵심 reordering이 합의의 본질)**:
1. **Phase 1** — blast_tier/verdict/routing_state **3-개념 분리**. 자기참조 검증 위험 인식 → 6-layer deterministic 검증을 primary trust로, 3-tier를 secondary ceremony로 운영. `downgrade_blast_tier()`는 본문을 `NotImplementedError` + deprecation으로 교체 (함수 정의 자체 삭제는 별도 cleanup commit).
2. **Phase 2** — `scripts/build_review_bundle.py` 생성기. 모든 에이전트가 같은 bundle을 먼저 읽도록.
3. **Phase 2.5** — tool call cap (안전망, 임시).
4. **Phase 3** — bundle-first scope + extension log enforcement (post-hoc 감사 가능).
5. **Phase 3.5** — 1주 데이터 수집 (의무, Phase 4 진입 전). 핵심 메트릭: T3-only accepted finding rate.
6. **Phase 4** — Smart routing + Tier 3 조건부 발화 (측정 데이터 기반).

**핵심 설계 원칙**:
- "행동 제한"이 아닌 "탐색 비용 제거" (scope cut은 reframing 발견을 놓침)
- routing 결정과 비용 최적화 분리 (`downgrade_blast_tier`처럼 섞이면 신뢰 손상)
- 에이전트 독립성 유지 (af-critic + af-cross-review 통합 X, bundle만 공유)
- Tier 3 발화 조건은 "위험군" 기준 (finding-count 기반 X)
- Phase 4 진입 전 1주 데이터 수집 의무 (추정 routing 변경 금지)

**항상-Tier-3 리스트** (Phase 4에서 강제):
- `scripts/{hook_runner,review_gate,check_pending_review,check_design_pending,enqueue_agent_review,blast_radius,build_review_bundle}.py`
- `.claude/agents/*.md`, `.claude/skills/*`
- `core/providers/*`, `core/.*provider.*\.py`

**How to apply**:
- Phase 1부터 순서대로. 건너뛰기 금지.
- Phase 1 작업 시:
  - 자기참조 검증 위험: 3-tier가 막 수정한 코드 위에서 동작 → primary trust는 6-layer deterministic 테스트 (단위/통합/회귀/dry-run/state matrix)
  - 4-question docstring 명문화: blast_tier 결정자, verdict 기록 위치, gate 차단 근거, routing 계산 위치
  - `downgrade_blast_tier()` 본문 → `raise NotImplementedError(...)` + deprecation. 함수 정의 자체 삭제는 별도 cleanup commit.
  - 풀 3-tier는 6-layer 모두 PASS 후 의식적 1회. BLOCK 2회 시 manual brief(옵션 C) 후퇴.
- Phase 2 작업 시: bundle 무효화 규칙(updated_at 비교), 크기 cap(100KB), caller 추출 룰(심볼당 최대 3개) 필수.
- Phase 3 작업 시: extension log 형식은 ML 후처리 가능하도록 일관 유지. Soft enforcement (post-hoc audit).
- Phase 3.5 핵심 메트릭: T3-only accepted finding rate. 임계값 30%/10%로 Phase 4 routing 조건 fine-tune.
- Phase 4 작업은 Phase 3.5 데이터 없이 진입 금지.

**기준일**: 2026-04-30. Sonnet 4.6에서 발견 → Opus 4.7로 deliberation 후 합의.

## 관련
- [[code/symbols]]

