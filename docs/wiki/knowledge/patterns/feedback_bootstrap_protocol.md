---
name: 부트스트랩 문서 종료 프로토콜
description: 설계 검증 파이프라인 자체를 정의하는 문서는 자기 참조를 피하기 위해 "검증 대상 전이" 방식으로 종료 조건을 관리한다. 본 메모리는 그 종료 카운터와 규칙을 보관.
type: feedback
originSessionId: 1b919e04-75d9-485b-8e36-184b5fa1e525
---
# 부트스트랩 문서 종료 프로토콜

검증 파이프라인 자체를 정의하는 설계 문서(document_class: bootstrap)는 자기 자신을 검증 대상으로 두면 Tarski 메타언어 분리 원칙 위반. 이를 방지하기 위해 종료 조건을 **본 문서가 아니라 다른 문서의 외부 결과**로 관리한다.

**Why**: v1.0 ~ v1.3 `2026-04-21-design-doc-review-pipeline.md`에서 재검증 3회 연속 결함 증가 패턴(5→6→9건) 발견. 원인은 "설계가 자기 자신을 심사하는 순환". Codex 2차 피드백: "자기 자신의 합격 기준을 정의하는 예외조항은 면책 설계"로 지적.

**How to apply**:
1. **bootstrap 문서 식별**: frontmatter `document_class: bootstrap` 선언 문서. 현재 `docs/features/2026-04-21-design-doc-review-pipeline-v2.md`.
2. **bootstrap 문서 검증**: 형식 lint 1회만 PASS. Gate B(논리), Gate C(정합성)는 적용하지 않음. 자기 참조 방지.
3. **종료 조건**: bootstrap 문서는 "완벽해짐"으로 종료하지 않는다. **다른 feature 문서 2~3건이 `design-gate-scoring-v2.md`로 PASS/CONDITIONAL 달성 시** 은퇴.
4. **실패 임계** (bootstrap 폐기 조건):
   - 다른 feature 문서 3회 연속 BLOCK → scoring 재설계 + bootstrap 폐기.
   - 14일 내 첫 PASS 미달성 → scoring 복잡도 재검토.
   - 다른 문서에서 scoring 모호성 5건 이상 누적 → scoring 단순화.

## 종료 카운터 (수동 업데이트)

아래 카운터는 사용자 또는 메타 거버넌스 주체가 수동 업데이트한다. bootstrap 문서 자체가 자기 카운터를 올리면 안 됨(자기 참조).

- **시작일**: 2026-04-21
- **첫 목표일**: 2026-05-05 (14일 임계)
- **PASS/CONDITIONAL 누적**: 0건 (목표 2~3건) — 외부 적용 결과만 반영. 부트스트랩 본체는 미포함.
- **BLOCK 연속 횟수**: 0
- **scoring 모호성 누적**: 0
- **부트스트랩 내부 단계 (외부 증빙)**:
  - Stage 1 (형식 lint PASS 1회): 완료 — 2026-04-21 v2.0 작성 시 af-doc-qa 구조 확인.
  - Stage 2 (Phase 1 Step 1 구현): 완료 — commit `59d29d22` (scripts/design_review_trigger.py ensure_watcher 호출 제거).
  - Stage 3 (다른 feature 문서 1건 PASS/CONDITIONAL): 대기.
  - Stage 4 (누적 2~3건): 대기.
- **BR2 추적**: `core/hooks/design_review_hook.py` line 25 import + line 118, 163 호출 2건에 `ensure_watcher` 잔존. 별도 feature로 승격 시 처리.
- **최근 업데이트**: 2026-04-21 Stage 1/2 완료, commit 59d29d22

### 업데이트 규칙

- 다른 feature 문서 하나가 `design-gate-scoring-v2.md`로 검증되면 결과를 여기 기록.
- 카운터가 목표 달성(누적 ≥ 2) 시 bootstrap 문서 아카이브 가능.
- 실패 임계 도달 시 규범 재설계 논의 시작.

## 관련 문서

- `docs/features/2026-04-21-design-doc-review-pipeline.md` — FROZEN v1.3 (자기 참조 순환 실패 사례).
- `docs/features/2026-04-21-design-doc-review-pipeline-v2.md` — Active bootstrap edition.
- `docs/features/2026-04-21-design-gate-scoring-v2.md` — normative, 다른 feature 문서 검증 규범.
- `docs/features/2026-04-21-design-pipeline-future-work.md` — aspiration 격리.

## 연관 원칙

- **Tarski 메타언어 분리**: 어떤 언어도 자기 자신의 진리를 완전히 정의할 수 없다.
- **컴파일러 부트스트랩**: 첫 컴파일러는 다른 언어로 작성, 자기 자신으로 재컴파일은 그다음.
- **SSOT (Single Source of Truth)**: 같은 사실·숫자·상태·exit code·step 번호는 단 1곳에만 존재.
- **spec / roadmap / aspiration 분리**: "확정 계약"과 "원하는 UX"와 "후속 아이디어"를 같은 문서에 섞지 않는다.

## 관련
- [[code/symbols]]

