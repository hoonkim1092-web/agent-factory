# Phase A 진행 전 결정 필요 사항

<!-- version: 1.2.0 | date: 2026-04-22 | author: Claude Haiku 4.5 -->
<!-- related: docs/2026-04-22-phase-a-gap-analysis.md -->
<!-- status: RESOLVED — Q1~Q3, Q8 사용자 확정 (2026-04-22) -->

## 0-A. 결정 결과 (2026-04-22 사용자 확정)

| 질문 | 답변 | 비고 |
|-----|------|------|
| **Q1. 작업 베이스라인 브랜치** | 현재 브랜치(`2026-04-14-build-diet`)에 커밋 및 push | detached HEAD → 로컬 브랜치 생성 후 push. 회사 미푸쉬 커밋과 충돌 가능(내일 회사에서 `git pull --rebase` 필요) |
| **Q2. 우선순위 순서** | **Codex 안**: ISE → COMPACT → EVOLUTION → MEMORY | Critical 2건(--mode ise 배선 + af.spec)이 ISE에 집중하므로 실행 차단 요소부터 해소 |
| **Q3. 문서 처리** | **(c)** 원문 archive 이동 + gap-analysis를 정식 요구사항서로 승격 | `docs/plans/AF_Phase_A_Requirements.md` → `docs/archive/2026-04-17-AF_Phase_A_Requirements.md`, gap-analysis.md 헤더에 "AUTHORITATIVE" 명시 |
| **Q8. GStack/Superpowers 연동** | **Phase A: (a) 탐지만 + Phase B: (d) 자동 부트스트랩** | AF가 멀티 프로바이더 환경에 GStack/Superpowers를 자동 설치·검증. Phase A는 미설치 시 경고 로그만, Phase B에서 어댑터 3종 실제 구현 |
| Q4~Q7, Q9~Q11 | (미답) 기본값 적용 | 각 Step 시작 시점에 해당 Quality 질문 재확인 |

이하 원본(의사결정 전 상태)은 히스토리 참조용으로 보존한다.

---

## 0. 이 문서의 용도

`2026-04-22-phase-a-gap-analysis.md`의 교차 검증 결과를 바탕으로 **사용자가 답해야 다음 단계를 진행할 수 있는 질문**만 모은다. 각 질문은 의사결정 항목이며, 보수적 기본값을 병기해 미답 시 자동 진행 가능하도록 명시한다.

각 항목은 3가지로 분류된다.
- 🔴 **Blocking** — 답이 없으면 다음 단계 진행 불가
- 🟡 **Quality** — 답이 있으면 결과물 품질 향상
- 🟢 **Context** — 답이 없어도 진행 가능하나 나중에 재작업 위험

---

## 1. 🔴 Blocking — 즉시 답변 필요

### Q1. 작업 베이스라인 브랜치

**질문**: 현재 `detached HEAD (origin/2026-04-14-build-diet, 486041ca)` 상태다. 또 working tree에 ~50개 파일이 modified 상태로 남아있다(CLAUDE.md, Master_Blueprint.md, AGENTS.md 등 루트 문서류 대부분). 작업을 어디서 시작할 것인가?

**선택지**:
- (a) 현재 detached HEAD에서 새 브랜치 `feat/phase-a-gap-filling` 분기 → 커밋 가능 상태로 전환
- (b) `origin/2026-04-14-build-diet`를 로컬 브랜치로 생성 후 그 위에서 분기
- (c) `main` 또는 다른 기준 브랜치로 이동해서 시작
- (d) 현재 modified 파일들을 먼저 커밋 or 스태시 처리한 뒤 결정

**기본값 (미답 시)**: (a). 새 브랜치 `feat/phase-a-gap-filling` 분기 + 현재 modified 파일은 WIP 스태시로 보관

---

### Q2. 우선순위 순서 확정

**질문**: 세 가지 안 중 어느 순서로 진행할 것인가?

| 안 | 순서 | 근거 |
|---|---|---|
| 원안 (Opus 4.6 문서) | COMPACT → ISE → EVOLUTION → MEMORY | 문서 기준, 이미 구현된 부분 재작업 |
| Claude 1차 제안 | MEMORY → COMPACT → ISE → EVOLUTION | "메모리가 살아야 다른 효과가 곱해진다"는 가정 기반 |
| Codex 제안 (교차검증 채택) | **ISE → COMPACT → EVOLUTION → MEMORY** | Critical 2건(--mode ise 배선 + af.spec)이 ISE에 집중 |

**기본값 (미답 시)**: Codex 제안. 이유는 gap-analysis.md §4 참조 — 사용자가 `af --mode ise`를 현재 실행할 수 없는 상태가 가장 큰 실행 차단 요소

---

### Q3. 문서 처리 방침

**질문**: `AF_Phase_A_Requirements.md` 원본(2026-04-17 Opus 4.6)에 ISE dead code 주장 등 사실 오류가 있다. 어떻게 처리할 것인가?

**선택지**:
- (a) 원문을 그대로 보존하고 `2026-04-22-phase-a-gap-analysis.md`로 보정만 유지
- (b) 원문을 현재 코드 기준으로 재작성(`AF_Phase_A_Requirements.v2.md`) 후 진행
- (c) 원문은 히스토리 자료로 `docs/archive/`에 이동, gap-analysis를 정식 요구사항서로 승격

**기본값 (미답 시)**: (a). 원문은 히스토리로 건드리지 않고 gap-analysis가 실행 근거 문서

---

## 2. 🟡 Quality — 결정이 제품 품질을 좌우

### Q4. "아침에 완성되어 있다"의 성공 판정 기준

**질문**: 야간 자율 실행 성공이란 구체적으로 어떤 상태인가?

**선택지**:
- (a) 테스트 전체 PASS + 커밋 완료
- (b) (a) + Blueprint 동기화 + exe 빌드 성공
- (c) (b) + 사용자 승인 리뷰 통과까지
- (d) 기타 (직접 기술)

**영향**: ISE `max_meta_cycles`, RunBudget, Supervisor heartbeat 타이트함 결정. 보수적이면 30분·10사이클, 공격적이면 2시간·30사이클

**기본값 (미답 시)**: (b). 단, 사용자 승인은 아침에 diff 리뷰로 대체

---

### Q5. 운영 환경 범위

**질문**: 실행 환경이 단일 데스크톱인가, 다중 머신 교차(맥+데스크톱)인가?

**영향**:
- 단일: 파일 락 단순, Supabase 동기화 보조용
- 다중: 에피소드 레코드 충돌 해소 정책(last-write-wins vs merge) 필요. `start_db/end_db` 의존성 증가. `source_machine` 필드 활용 로직 추가

**힌트**: 최근 pull 이력(`hoonkims-MacBook-Pro.local` + `DESKTOP-JPHA09P`)을 보면 **이미 다중 머신 환경**

**기본값 (미답 시)**: 다중 머신. 다만 Phase A에서는 충돌 해소를 last-write-wins로 단순화하고 Phase B에서 merge 전략 추가

---

### Q6. LLM 예산 (테스트 환경)

**질문**:
- E2E 테스트(예: 의도적 결함 스킬 → 진화 → 성공)를 **실제 Anthropic/Gemini API로 돌려도 되는가**? (품질 ↑ 비용 ↑)
- 진화·판정용 LLM 호출 1회당 평균 $0.10~0.50 (토큰 수에 따라). Phase A 완료까지 E2E 10~20회 예상
- Opus 판정 LLM을 현재 Opus 4.6 → 4.7로 업그레이드할지?

**선택지**:
- (a) 전부 mock. 실제 API 0회
- (b) 핵심 E2E 1~2건만 실제 API, 나머지 mock
- (c) 전부 실제 API
- 모델: (i) Opus 4.6 유지 (ii) Opus 4.7 업그레이드

**기본값 (미답 시)**: (b) + (ii). 예산 상한 $5 이하로 설정

---

### Q7. 교차검증 루프(CrossVerificationLoop) 포함 범위

**질문**: `AF_Phase_A_Requirements.md §0.2`가 "다중 CLI 독립 실행 + 순환 피어 리뷰 + Opus 판정"을 AF 고유 영역으로 정의하지만, §1~5 구체 요구사항에는 포함되지 않았다. Phase A에 포함할 것인가?

**선택지**:
- (a) Phase A 포함 (범위 ↑, 기간 +2일)
- (b) Phase B로 분리 (현재 계획 유지)
- (c) Phase A에는 Opus 판정 루프만 포함, 다중 CLI 피어 리뷰는 Phase B

**기본값 (미답 시)**: (b). Phase A의 5.5일 계획에 영향 주지 않도록 분리

---

### Q8. GStack/Superpowers 연동 방침

**질문**: 문서 §0.4는 "워크플로우 강제(TDD/역할 리뷰/보안 감사)는 하위 프로바이더의 GStack/Superpowers에 위임"을 제안한다. 이를 어느 정도 채택할 것인가?

**선택지**:
- (a) 문서 원안대로: 오케스트레이터 레벨 Phase Gate만 최소 구현, 나머지는 프로바이더 의존 (사용자가 각 프로바이더에 스킬팩을 수동 설치한 것으로 가정)
- (b) AF 자체 워크플로우도 병행 구현 (중복 있으나 독립성 ↑)
- (c) AF에는 없고 프로바이더에도 없을 때만 AF가 최소 구현 (하이브리드)
- (d) **AF가 프로바이더 환경에 GStack/Superpowers 자동 부트스트랩** (2026-04-22 추가)
  - Claude Code / Codex CLI / Gemini CLI 각각의 플러그인 경로를 어댑터로 추상화
  - AF 최초 실행 시 1회 설치 + 세션 시작 시 검증(멱등 업그레이드)
  - `SkillPackBootstrapper` + 프로바이더별 어댑터 3종 (~450 LOC 추정)
  - 오프라인 번들 옵션 병행 (에어갭 환경 대응)

**영향**: Phase Gate 구현 범위 결정.
- (a): plan_verifier 승격 수준
- (b): TDD 강제 스킬까지 AF 자체 구현 (중복)
- (c): 런타임 감지 로직 추가
- (d): 설치 자동화까지 확장 — 멀티 프로바이더 환경 일관성 보장

**확정 결정 (2026-04-22)**: **Phase A는 (a) 탐지만 + Phase B에서 (d) 자동 부트스트랩**.
- Phase A (5.5일 계획 유지): `SkillPackBootstrapper.check_installed()` 구현 + 미설치 시 경고 로그 + 수동 설치 안내 (~100 LOC)
- Phase B 이후: 프로바이더별 어댑터 구현, `install-af.ps1` 통합, 오프라인 번들 옵션 추가
- 근거: 각 프로바이더의 플러그인 시스템 학습 + 크로스 플랫폼 테스트는 별도 스프린트급 작업이며, Phase A 핵심 작업(ISE 배선 복구, COMPACT/EVOLUTION/MEMORY 보정)과 병행하면 5.5일 내 완료 어려움

**기본값 (미답 시)**: (a). 중복 최소화

---

## 3. 🟢 Context — 나중에 보완 가능

### Q9. 일 평균 실행 규모

**질문**: 하루 평균 태스크 개수와 태스크당 budget은?

**영향**: compaction 임계치(80/95%) 적정성 검증, decay 30일 주기 검증, Supabase 저장 용량 추정

**기본값 (미답 시)**: 일 10태스크, 태스크당 100K 토큰 budget

---

### Q10. 회귀 테스트 baseline 확보

**질문**: 작업 시작 전 `pytest -q` baseline을 제가 돌려 기록할까?

**영향**:
- baseline 없으면 Step 1~5에서 도입되는 회귀를 감지 불가
- 기존 테스트 현황:
  - MEMORY: Phase10/12/14/16 + stage4_7 강함
  - ISE/EVOLUTION 직접 테스트 0건 (신규 추가 대상)
  - PlanVerifier/ControlPlaneLLM/RunBudget 직접 테스트 0건

**선택지**:
- (a) Step 0로 baseline 측정 후 진행
- (b) 생략하고 각 Step 내에서 diff 기반 검증
- (c) baseline만 별도로 먼저 완료

**기본값 (미답 시)**: (a). 5분 내외로 완료 가능하므로 안전성 대비 비용 낮음

---

### Q11. Working Tree의 ~50개 modified 파일 처리

**질문**: 현재 `git status`에 CLAUDE.md, Master_Blueprint.md, AGENTS.md, README.md 등 다수 루트 문서가 modified 상태다. 이는 `start_db` 이전에 이미 변경된 건인가?

**선택지**:
- (a) 작업과 무관하므로 스태시 보관 후 Phase A 완료 후 복원
- (b) 먼저 검토 후 commit 하고 시작
- (c) 일부(CLAUDE.md 등 정책 문서)만 커밋하고 나머지는 스태시

**기본값 (미답 시)**: (a). Phase A 변경분과 섞이면 리뷰 어려움

---

## 4. 최소 답변 요청

제가 Phase A 실행을 시작하려면 **최소 Q1, Q2, Q3 (🔴 Blocking 3개)**는 답이 필요합니다.

나머지 Q4~Q11은 미답 시 기본값으로 진행하되, 각 Step 시작 시점에 해당 단계 관련 Quality 질문을 한 번 더 확인할 수 있습니다.

### 한 줄 답변 템플릿

```
Q1: a/b/c/d
Q2: 원안/Claude/Codex
Q3: a/b/c
[선택] Q4: a/b/c, Q5: 단일/다중, Q6: (a|b|c)+(i|ii), Q7: a/b/c, Q8: a/b/c/d, Q9: 일 N태스크·M토큰, Q10: a/b/c, Q11: a/b/c
```

### 전부 기본값으로 진행하려면

```
모두 기본값
```

라고만 답하시면 gap-analysis.md §5의 5.5일 계획대로 즉시 착수합니다.
