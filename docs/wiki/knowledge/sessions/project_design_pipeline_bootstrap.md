---
name: 설계 파이프라인 부트스트랩 분리 (2026-04-21)
description: 설계 문서 3게이트 검증 파이프라인이 자기참조 순환에 빠져 v1.3이 FROZEN되고 3개 문서(bootstrap/normative/aspiration)로 분할된 결정의 배경과 현재 진행 상태.
type: project
originSessionId: 1b919e04-75d9-485b-8e36-184b5fa1e525
---
# 설계 파이프라인 부트스트랩 분리

**결정일**: 2026-04-21
**커밋**: `59d29d22`

## 결정 내용

설계 문서 3게이트 검증 파이프라인(`2026-04-21-design-doc-review-pipeline.md`) v1.3이 재검증 3회 연속 결함 증가(5→6→9건) 패턴을 보임. 원인: 검증 규범을 담은 문서가 자기 자신을 심사 → Tarski 메타언어 분리 원칙 위반. 해결: 1개 문서를 3개로 분할하고 종료 카운터는 외부 메모리로 옮김.

**Why**: 자기 참조는 수렴하지 않는다. 컴파일러 부트스트랩과 동일한 원리 — 첫 번째는 다른 언어로 작성, 자기 자신으로의 재컴파일은 그다음. 검증 파이프라인 자체는 다른 feature 문서가 합격해야만 정당성 입증 가능.

**How to apply**:
- 새로운 "검증 규범"을 정의하는 설계 문서를 쓸 때는 반드시 `document_class: bootstrap / normative / aspiration / normal` frontmatter로 분리.
- bootstrap 문서는 자기 자신을 검증 대상으로 두지 말 것. 형식 lint 1회 PASS만 요구.
- 합격 기준(scoring)은 bootstrap 외부의 normative 문서에 단독 존재(SSOT).
- 종료 카운터는 문서가 아니라 메모리(`feedback_bootstrap_protocol.md`)에 기록.

## 현재 문서 배치

| 파일 | 클래스 | 역할 |
|-----|-------|-----|
| `docs/features/2026-04-21-design-doc-review-pipeline.md` | FROZEN predecessor | v1.3 자기참조 실패 사례 보존 |
| `docs/features/2026-04-21-design-doc-review-pipeline-v2.md` | bootstrap | 게이트 규범 SSOT + Phase 1 Step 1만 확정 구현 |
| `docs/features/2026-04-21-design-gate-scoring-v2.md` | normative | 다른 feature 문서에 적용되는 합격 기준 (G1-G6 + 밴드 판정) |
| `docs/features/2026-04-21-design-pipeline-future-work.md` | aspiration | 확정 전 항목 격리 (Phase 1 Step 2+, Phase 2-4, CLI 등) |

## 현재 진행 상태

- **Stage 1** (v2.0 형식 lint PASS): 완료 (2026-04-21).
- **Stage 2** (Phase 1 Step 1 `ensure_watcher` 호출 제거): 완료 (commit `59d29d22`).
- **Stage 3** (다른 feature 문서 1건 scoring-v2 PASS/CONDITIONAL): 대기.
- **Stage 4** (누적 2~3건): 대기.
- **14일 임계**: 2026-05-05까지 첫 PASS 미달성 시 scoring 복잡도 재검토.

## 남은 기술 부채 (별도 feature로 승격 필요)

- **BR2**: `core/hooks/design_review_hook.py` line 25 import + line 118, 163에 `ensure_watcher` 호출 잔존. Phase 1 Step 1 범위 규율 유지를 위해 이번 커밋에서 미처리. Phase 3 watcher 파일 삭제 시 일괄 처리 예정.
- **Phase 1 Step 2+, Phase 2-4**: 전부 `design-pipeline-future-work.md`에 격리. 각 항목이 별도 feature 문서로 작성되고 scoring-v2 검증 통과해야 확정 계약으로 승격.

## 관련 원칙 (다른 영역에도 적용 가능)

- **Tarski 메타언어 분리**: 진리 술어는 상위 언어에 있어야 한다.
- **SSOT**: 같은 사실·숫자·상태는 단 1곳에만 존재.
- **spec / roadmap / aspiration 분리**: 확정 계약·바라는 UX·후속 아이디어를 같은 문서에 섞지 않는다.
