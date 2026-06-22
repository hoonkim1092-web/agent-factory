---
name: feedback-design-review-rounds-stop-rule
description: design doc cross-review 무한 정정 루프 차단 — finding 유형별 즉시정정/이월 분류 + 4차 freeze 규칙
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b3efd65c-90b1-4321-a7b9-332028d7c2c6
---

**규칙**: design doc cross-review는 **최대 3차 정정**까지만 진행. 4차부터는 무조건 freeze + 잔여 finding은 ADR로 이월.

각 라운드의 finding은 유형별로 처리:

| finding 유형 | 처리 |
|---|---|
| 식별자 회귀 (코드 미존재 토큰: `feature`/`system`/`local` 등) | **즉시 정정** — grep 5분, 비용 0 |
| 구조적 데이터 흐름 누락 (호출자 0건 등 거짓 흐름) | **즉시 정정** — design 단계에서만 잡힘. 구현 단계로 미루면 코드 폐기 |
| 호출자 영향 분석 누락 (signature 변경, 예외 클래스 신설 시) | **즉시 정정** — design freeze 전에 cover 안 하면 구현 회귀 |
| 문서 내부 충돌 (§X vs §Y 결정 불일치) | **즉시 정정** — 1줄 수정 |
| Medium/Low (측정 기준·attribution·점진 거버넌스·LOC 추정) | **ADR로 이월** — 구현 단계에서 검증, design 핵심 아님 |
| 새 결함 비율 < 30% AND Critical 0 | **PASS 격상** — 잔여는 ADR |

**PASS 격상 조건** (한 가지라도 충족):
- 직전 라운드 대비 Critical 0건
- 직전 라운드 대비 새 결함(이전 정정 회귀 제외) < 30%
- 잔여 finding 전부 ADR 이월 가능 (구현/배포 단계 검증)

**4차 freeze 절차**:
1. 3차 정정 후 cross-review가 또 BLOCK이면:
2. 잔여 finding을 `docs/decisions/ADR-YYYYMMDD-<slug>-residual-risks.md`로 이월
3. design doc은 "Phase A v1" 동결 (이후 정정 금지)
4. ADR에 각 finding의 검증 시점 명시 (코드 review / 회귀 테스트 / 배포 smoke)
5. Phase A 구현 진입 — 실제 구현 시 결함이 터지면 그때 정정

**Why**:
- 2026-05-11 ~ 2026-05-13 도메인 게이트 design doc 정정 3라운드 누적 (Total findings 11→12→5, Critical 2→2→1)
- cross-review는 이론상 영원히 finding 생성 가능 (실측 가능 격차 무한)
- 멈춤 기준 없으면 design 단계 무한 루프 — 구현이 진짜 검증임에도 design 무한 검토에 시간 소진
- "코드는 design에서 모든 결함 잡힐 때까지 안 짠다"는 비현실적

**How to apply**:
- 매 cross-review 라운드 결과 받을 때 위 표로 finding 분류
- 분류 결과 "즉시 정정 0건 + Medium 다수"면 PASS 격상 가능
- 3차 정정 후에도 Critical 잔존이면 4차 freeze + ADR 작성
- 메모리에 라운드 수 추적 — `project-superpowers-gsd-5-13-consensus` 같은 진행 메모리에 "Nth round"  기록
- 관련: [[feedback-design-doc-grep-before-write]] (식별자 회귀 사전 방지),
  [[feedback-design-review-mandatory]] (교차검증 필수 원칙은 유지, 라운드 수만 캡)
