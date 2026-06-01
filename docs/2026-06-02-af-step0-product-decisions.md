# AF Step 0 — 제품 방향 결정 (2026-06-02)

> **목적**: dogfood detector/infra stream 종료 후, "AF가 다음에 실제로 제공할 제품 가치"를 정한다.
> **계약**: 항목당 "결정 1줄 + 근거 1줄"만. 추가 분석 금지 (analysis-paralysis 차단 — 4/26 Step 0 정의 후 5주 미결 전례).
> **배경**: `docs/참고/2026-04-26-harness-strategy-critique.md` Step 0~5, 메모리 `project_saas_strategy_position`.

## 범위 축소 원칙

PMF 이전 단계이므로 **#3(대상)·#4(task type) 2건만 확정**하고, 나머지(#1 worker runtime / #2 provider / #5 pricing)는 **가설 1줄**로 박고 보류한다. PMF/외부 사용자 발생 시 재개.

## 결정

| # | 항목 | 상태 | 결정 | 근거 |
|---|------|------|------|------|
| **#3** | 첫 대상 (ICP) | ✅ 확정 | **Python 프로젝트 (AF 자신 포함), primary user = 개발자 본인** | AF가 Python이고 본인이 AF 개발에 쓸 것 → 가장 잘 아는 도메인, dogfood 즉시 검증 가능, 출고 최단. 외부 판매는 비목표(개인/내부 도구 포지션). |
| **#4** | 첫 task type | ✅ 확정 | **기능 추가 (실제 필요 기능 — 검증용 더미 금지)** | AF의 control+quality plane이 설계→구현→테스트→리뷰 전 과정을 이미 커버. 단 메타-재귀 방지 위해 "진짜 필요한 기능"만 대상. |
| #1 | Worker runtime | 🔸 가설 | BYO local (현재 로컬 CLI 실행 유지) | 개인/로컬 도구 단계. Docker/Firecracker는 외부 사용자 발생 전 불요. |
| #2 | Provider 우선순위 | 🔸 가설 | Claude Code CLI 우선 (현재 기본값) | 현 실행 경로 그대로. 변경은 비용/품질 실측 후. |
| #5 | Pricing model | 🔸 보류 | N/A (개인/내부 도구 → 과금 모델 불요) | 외부 판매 결정 시 재개. 지금 결정하면 투기. |

## 가드레일 (다음 work-item 선정 시 강제)

1. **더미 금지** — dogfood 검증용 throwaway 함수(`clamp`/`median`류)는 work-item이 아니다. AF가 실제로 아쉬워하는 기능만.
2. **메타-재귀 라우팅** — 대상 모듈이 파이프라인 의존(planner/premortem/dogfood/research_*)이면 dogfood run 금지, 손 구현 + 3-Tier. leaf 기능만 dogfood 가능.
3. **plane 정합** — 신규 기능은 control / quality / memory plane 중 하나에 속해야 함. 셋 다 아니면 범위 밖 재검토.

## 다음 단계 (Step 1 → 단계 3)

→ "AF가 실제로 필요로 하는 기능" 후보를 코드/문서/마찰 기록에서 발굴 → work-item 1개 선정 + 성공기준 명문화 + 라우팅(dogfood vs 3-Tier) 판정.
