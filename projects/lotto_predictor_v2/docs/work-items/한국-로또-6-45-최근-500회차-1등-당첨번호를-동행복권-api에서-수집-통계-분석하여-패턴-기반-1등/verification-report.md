# Document Review: 한국-로또-6-45-최근-500회차-1등-당첨번호를-동행복권-api에서-수집-통계-분석하여-패턴-기반-1등

> Source: 한국-로또-6-45-최근-500회차-1등-당첨번호를-동행복권-api에서-수집-통계-분석하여-패턴-기반-1등
> Date: 2026-04-17T01:29:29
> Type: document
> Providers: critic=claude, judge=claude
> Mode: single-provider
> Trigger: pipeline
> Round: 1/1

---

## 검증자 A (Critic): claude

## Critic Review

### Verdict: **BLOCK**

문서 4종 모두 자동 생성 템플릿 수준의 플레이스홀더로 채워져 있고 project_brief의 구체적 요구사항이 거의 반영되지 않음. 구현 착수 시 대규모 재작업이 확정됨.

### Individual Document Scores

| Document | Score | Key Issues |
|----------|-------|-----------|
| feature-plan | 32/100 | Stakeholders가 brief와 불일치(frontend_dev/game_logic_dev 등장), Goals가 deliverables 복사, Success Metrics가 "완성됨" 수준 |
| feature-spec | 18/100 | Acceptance Criteria가 모두 "핵심 기능이 구현된다"로 반복, NFR 1줄, Exceptions/Existing Behavior 공란, LottoDraw 스키마 누락(drwtNo5/6/bnusNo 등) |
| implementation-design | 22/100 | 10개 모듈 중 7개가 frontend_dev 소유(이 프로젝트는 CLI), Data Flow가 전부 "(시작) →" 병렬, Interface Impact/Compatibility/Alternatives 공란 |
| implementation-tasks | 25/100 | 30개 태스크 전부 "범위 정의/구현/검증" 3종 반복, PyInstaller·seed·retry·rate limit·면책 고지 태스크 전무, 의존성은 자기 모듈 내부만 |

### Cross-Consistency Matrix

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | plan.risks → spec.nfr | **FAIL** | 6개 risk 중 1개만 NFR에 반영(캐시 복구). API 스키마 변경, rate limit, 면책 고지, Gatekeeper, 과적합 → NFR 전무 |
| 2 | plan.stakeholders → spec.user_scenarios | **FAIL** | plan에 Frontend/Backend/Game Logic Dev가 stakeholder로 등장하나 brief의 role_hints는 `backend_dev, data_analyst, build_engineer, qa_engineer`. 개발자 역할 오매핑 |
| 3 | spec.acceptance_criteria → tasks.verification | **FAIL** | AC가 모듈별 "핵심 기능이 구현된다"로 측정 불가 → 1:1 매핑이 논리적으로 성립 불가 |
| 4 | spec.api_endpoints → tasks.implementation | **FAIL** | `lottery.go.kr/common.do?method=getLottoNumber&drwNo=N` 엔드포인트가 spec의 Inputs/Outputs에 없고 태스크에도 수집 구현·retry·최신회차 탐지 태스크 없음 |
| 5 | spec.user_scenarios → design.data_model | **PARTIAL** | "재현용 seed" 시나리오 있으나 Recommendation에 seed 필드 있음 ✓. 반면 spec의 LottoDraw는 drwtNo4까지만 정의되어 시나리오 불가 |
| 6 | plan.constraints → design.tech_stack | **FAIL** | brief 제약 8종(ko-KR, onefile, seed 고정, 면책 고지, 비공식 스크래핑 금지 등) 중 design에 반영된 것 없음. 기술 스택은 적절하나 제약 추적 불가 |
| 7 | design.modules → tasks.work_items | **PARTIAL** | 10개 모듈 → 30개 태스크(scope/build/verify)로 기계적 매핑. 하지만 "Backend Dev 구현" 같은 역할명 모듈이 실제 모듈인지 롤업인지 불명 |
| 8 | design.dependency_order → tasks.prerequisites | **FAIL** | design Data Flow가 전부 "(시작) →" 병렬. tasks depends_on은 자기 모듈 scope→build→verify만. 수집기→캐시→분석→추천→리포트→빌드의 실제 의존 체인 없음 |
| 9 | ALL → ALL 용어 일관성 | **FAIL** | spec LottoDraw: `drwtNo1~4`. design LottoDraw: `drwtNo1~6, bnusNo, totSellamnt, firstWinamnt`. 같은 엔티티 스키마 불일치 |

### Findings

1. **[Critical] 스펙 데이터 모델이 설계와 불일치하며 핵심 필드 누락**
   - Documents: feature-spec.md vs implementation-design.md
   - Issue: `LottoDraw`의 당첨번호 필드가 스펙은 4개, 설계는 6개+보너스+금액. 로또 6/45는 6개 번호가 필수이므로 스펙이 실질적으로 틀림
   - Evidence: spec "**LottoDraw** [sqlite]: drwNo, drwNoDate, drwtNo1, drwtNo2, drwtNo3, drwtNo4" vs design "drwtNo1, drwtNo2, drwtNo3, drwtNo4, drwtNo5, drwtNo6, bnusNo, totSellamnt, firstWinamnt"
   - Suggestion: spec의 LottoDraw 정의를 design과 동일하게 교정하고, brief의 research_notes에 명시된 `drwtNo1~6, bnusNo, drwNoDate, returnValue` 원본 필드를 권위 source로 참조

2. **[Critical] 수락 기준이 전부 측정 불가 — 검증 불가능한 스펙**
   - Documents: feature-spec.md (Acceptance Criteria)
   - Issue: "X의 핵심 기능이 구현된다" 패턴으로 10항목 모두 동일. "핵심 기능"의 판정 기준 없음. QA 태스크가 무엇을 PASS 처리할지 정의 불가
   - Evidence: "동행복권 회차 수집기 모듈의 핵심 기능이 구현된다.", "통계 분석 엔진의 핵심 기능이 구현된다." …
   - Suggestion: brief의 구체 지표로 치환 — 예: "최근 500회차를 1분 이내 전량 수집", "rate limit 회피 위해 회차 간 ≥300ms 지연", "동일 seed로 재호출 시 동일 5조합 반환", "macOS/Windows에서 더블클릭 실행 시 0초 이내 환영 화면 표출"

3. **[Critical] brief의 핵심 제약이 태스크에 하나도 반영되지 않음**
   - Documents: project_brief.json vs implementation-tasks.md
   - Issue: constraints 8종(ko-KR 출력, PyInstaller onefile, SQLite/JSON 캐시, seed 재현성, 면책 고지, 교차 OS, rate limit 회피)이 30개 태스크 어디에도 명시되지 않음. "범위 정의 → 구현 → 검증" 3단 템플릿만 반복
   - Evidence: 모든 build 태스크 acceptance = "X의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다." — 제약 조건 0개
   - Suggestion: 제약별 전용 태스크 추가: (a) 동행복권 엔드포인트 증분 수집 + `returnValue=fail` 감지, (b) requests 세션 + 지수 백오프 retry, (c) seed 인자 CLI 노출 + 재현 테스트, (d) 면책 고지 문자열 필수 출력 + 리포트 헤더 배치, (e) `af.spec` hiddenimports + onefile 빌드, (f) SQLite 스키마 마이그레이션

4. **[High] 모듈 소유자(role)가 프로젝트 성격과 불일치**
   - Documents: implementation-design.md (Planned Modules)
   - Issue: 이 프로젝트는 터미널 CLI + 데이터 파이프라인인데 7개 모듈 소유자가 `frontend_dev`. brief.role_hints에 frontend_dev가 없음. 또한 "Game Logic Dev"는 로또 도메인에 부적합(확률 게임 상태전이가 아니라 통계 분석)
   - Evidence: brief `"role_hints": ["backend_dev", "data_analyst", "build_engineer", "qa_engineer"]` vs design 모듈 owner가 frontend_dev / game_logic_dev
   - Suggestion: 수집기·캐시는 `backend_dev`, 통계 엔진·추천기는 `data_analyst`, PyInstaller 스펙은 `build_engineer`, 리포트 포맷은 `backend_dev`로 재할당. game_logic_dev 전면 제거

5. **[High] API 계약 섹션 부재 — 외부 의존성이 명세되지 않음**
   - Documents: feature-spec.md (Inputs and Outputs)
   - Issue: 유일한 외부 의존인 동행복권 엔드포인트의 URL·쿼리 파라미터·응답 스키마·실패 신호(`returnValue=fail`)·rate limit 정책이 어느 문서에도 없음. brief.research_notes에만 있고 spec에 전사되지 않음
   - Evidence: brief "동행복권 공식 엔드포인트: https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={회차}" — spec Inputs/Outputs에는 "LottoDraw/NumberFrequency/Recommendation/FetchCheckpoint" 내부 저장 스키마만 존재
   - Suggestion: spec에 "External API Contract" 섹션 추가 — 요청/응답/에러/증분 탐지 로직(최신 회차까지 drwNo 증분 조회 후 returnValue=fail 직전 회차를 최신으로 확정)

6. **[High] 의존 관계 그래프가 전부 병렬 — 실제 파이프라인과 모순**
   - Documents: implementation-design.md (Data Flow) vs 실제 도메인
   - Issue: Data Flow가 "(시작) → 모듈X" 10줄로 모든 모듈을 병렬화. 실제로는 `수집기 → 캐시 → 통계 엔진 → 추천기 → 리포트`의 단방향 체인. tasks.depends_on도 모듈 내부 phase 순서만 정의하고 모듈 간 의존성 없음
   - Evidence: design "(시작) → **동행복권 회차 수집기 모듈**, (시작) → **회차 데이터 로컬 캐시 저장소**, ..." — 실행 전략도 "parallel"로 선언
   - Suggestion: Data Flow를 실제 파이프라인으로 재작성. build 단계 태스크 depends_on에 모듈 간 선행 관계 추가 (예: `frontend_dev_module_3_build_2 depends_on frontend_dev_module_2_build_2`)

7. **[High] Risk 항목이 NFR/완화 전략으로 이어지지 않음**
   - Documents: feature-plan.md vs feature-spec.md
   - Issue: plan에 6개 risk, NFR에 1개만. "rate limit → 지연/backoff", "API 스키마 변경 → 스키마 버전 감지/알림", "Gatekeeper → 공지", "오해 → 면책 고지 출력", "과적합 → 면책 + 검증용 역테스트" 등 대응 NFR 전무
   - Evidence: plan.Risks 6개 vs spec.NFR 1개 ("네트워크 장애 시 로컬 캐시…") — 심지어 이건 brief에서도 "constraints"에 있던 항목
   - Suggestion: 각 risk별 NFR 1:1 매핑 — 성능/신뢰성/보안/법적 면책 카테고리로 구조화

8. **[Medium] work_item 제목이 중간 절단됨**
   - Documents: 모든 4문서 Metadata
   - Issue: `work_item: 한국-로또-6-45-최근-500회차-1등-당첨번호를-동행복권-api에서-수집-통계-분석하여-패턴-기반-1등` — "1등"에서 끝나 문장 미완성
   - Suggestion: slug 생성기에 문장 단위 truncation 또는 해시 접미사 적용. 현재 제목으로는 GitHub issue/PR 연결 시 가독성 저해

9. **[Medium] NFR과 Risk의 항목이 동일 문장 — 분류 오류**
   - Documents: feature-spec.md (NFR) vs feature-plan.md (Risks)
   - Issue: "네트워크 장애 시 로컬 캐시(SQLite 또는 JSON)로 재시도·복구"가 NFR이면서 동시에 plan의 Risk에 등장. 이건 risk가 아니라 완화책
   - Evidence: plan.Risks의 마지막 항목, spec.NFR의 유일한 항목 동일 문자열
   - Suggestion: plan의 Risks에서 제거, spec NFR에 유지하되 "API 타임아웃 5초 + 지수 백오프 3회 재시도 후 로컬 캐시로 fallback" 수준으로 구체화

### Missing from Documents

- 동행복권 API 응답 스키마·에러 응답·최신 회차 탐지 알고리즘
- HTTP retry/backoff 정책, rate limit 회피 지연 간격
- `--seed`, `--count`, `--refresh` 등 CLI 플래그 설계
- 면책 고지 문구(필수 출력)와 배치 위치
- PyInstaller spec(hiddenimports, datas, onefile 옵션) 구체안
- macOS Gatekeeper/Windows SmartScreen 경고 사용자 안내 문서
- 캐시 스키마 마이그레이션 정책(컬럼 추가/변경 시)
- 통계 지표별 임계값(hot/cold 경계, 연속번호 허용 한계)
- 재현성 검증 테스트(동일 seed 입력 → 동일 출력 assertion)
- brief에 명시된 `docs/architecture.md` 및 `docs/change_history.md` 동시 갱신 규칙 반영 태스크
- Non-Goals로 선언된 2등 예측·GUI·웹·결제 연동에 대한 방어적 가드
- Exceptions and Failure Scenarios 섹션(현재 "(edit required)") — 최소 5종 실패 경로 필요: 네트워크 단절, API 404, 스키마 변경, 디스크 쓰기 실패, seed 충돌

**종합**: 4문서 모두 brief의 풍부한 도메인 정보를 활용하지 못하고 generic 템플릿 확장에 그쳤음. 구현 착수 전 스펙/설계를 실제 도메인 지식으로 재작성 필수.

> Critic 소결: 발견 5개, 판정 BLOCK

---

## 최종 판정 (Judge): claude

### 종합 판정: BLOCK

## Critic Review

### Verdict: **BLOCK**

문서 4종 모두 자동 생성 템플릿 수준의 플레이스홀더로 채워져 있고 project_brief의 구체적 요구사항이 거의 반영되지 않음. 구현 착수 시 대규모 재작업이 확정됨.

### Individual Document Scores

| Document | Score | Key Issues |
|----------|-------|-----------|
| feature-plan | 32/100 | Stakeholders가 brief와 불일치(frontend_dev/game_logic_dev 등장), Goals가 deliverables 복사, Success Metrics가 "완성됨" 수준 |
| feature-spec | 18/100 | Acceptance Criteria가 모두 "핵심 기능이 구현된다"로 반복, NFR 1줄, Exceptions/Existing Behavior 공란, LottoDraw 스키마 누락(drwtNo5/6/bnusNo 등) |
| implementation-design | 22/100 | 10개 모듈 중 7개가 frontend_dev 소유(이 프로젝트는 CLI), Data Flow가 전부 "(시작) →" 병렬, Interface Impact/Compatibility/Alternatives 공란 |
| implementation-tasks | 25/100 | 30개 태스크 전부 "범위 정의/구현/검증" 3종 반복, PyInstaller·seed·retry·rate limit·면책 고지 태스크 전무, 의존성은 자기 모듈 내부만 |

### Cross-Consistency Matrix

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | plan.risks → spec.nfr | **FAIL** | 6개 risk 중 1개만 NFR에 반영(캐시 복구). API 스키마 변경, rate limit, 면책 고지, Gatekeeper, 과적합 → NFR 전무 |
| 2 | plan.stakeholders → spec.user_scenarios | **FAIL** | plan에 Frontend/Backend/Game Logic Dev가 stakeholder로 등장하나 brief의 role_hints는 `backend_dev, data_analyst, build_engineer, qa_engineer`. 개발자 역할 오매핑 |
| 3 | spec.acceptance_criteria → tasks.verification | **FAIL** | AC가 모듈별 "핵심 기능이 구현된다"로 측정 불가 → 1:1 매핑이 논리적으로 성립 불가 |
| 4 | spec.api_endpoints → tasks.implementation | **FAIL** | `lottery.go.kr/common.do?method=getLottoNumber&drwNo=N` 엔드포인트가 spec의 Inputs/Outputs에 없고 태스크에도 수집 구현·retry·최신회차 탐지 태스크 없음 |
| 5 | spec.user_scenarios → design.data_model | **PARTIAL** | "재현용 seed" 시나리오 있으나 Recommendation에 seed 필드 있음 ✓. 반면 spec의 LottoDraw는 drwtNo4까지만 정의되어 시나리오 불가 |
| 6 | plan.constraints → design.tech_stack | **FAIL** | brief 제약 8종(ko-KR, onefile, seed 고정, 면책 고지, 비공식 스크래핑 금지 등) 중 design에 반영된 것 없음. 기술 스택은 적절하나 제약 추적 불가 |
| 7 | design.modules → tasks.work_items | **PARTIAL** | 10개 모듈 → 30개 태스크(scope/build/verify)로 기계적 매핑. 하지만 "Backend Dev 구현" 같은 역할명 모듈이 실제 모듈인지 롤업인지 불명 |
| 8 | design.dependency_order → tasks.prerequisites | **FAIL** | design Data Flow가 전부 "(시작) →" 병렬. tasks depends_on은 자기 모듈 scope→build→verify만. 수집기→캐시→분석→추천→리포트→빌드의 실제 의존 체인 없음 |
| 9 | ALL → ALL 용어 일관성 | **FAIL** | spec LottoDraw: `drwtNo1~4`. design LottoDraw: `drwtNo1~6, bnusNo, totSellamnt, firstWinamnt`. 같은 엔티티 스키마 불일치 |

### Findings

1. **[Critical] 스펙 데이터 모델이 설계와 불일치하며 핵심 필드 누락**
   - Documents: feature-spec.md vs implementation-design.md
   - Issue: `LottoDraw`의 당첨번호 필드가 스펙은 4개, 설계는 6개+보너스+금액. 로또 6/45는 6개 번호가 필수이므로 스펙이 실질적으로 틀림
   - Evidence: spec "**LottoDraw** [sqlite]: drwNo, drwNoDate, drwtNo1, drwtNo2, drwtNo3, drwtNo4" vs design "drwtNo1, drwtNo2, drwtNo3, drwtNo4, drwtNo5, drwtNo6, bnusNo, totSellamnt, firstWinamnt"
   - Suggestion: spec의 LottoDraw 정의를 design과 동일하게 교정하고, brief의 research_notes에 명시된 `drwtNo1~6, bnusNo, drwNoDate, returnValue` 원본 필드를 권위 source로 참조

2. **[Critical] 수락 기준이 전부 측정 불가 — 검증 불가능한 스펙**
   - Documents: feature-spec.md (Acceptance Criteria)
   - Issue: "X의 핵심 기능이 구현된다" 패턴으로 10항목 모두 동일. "핵심 기능"의 판정 기준 없음. QA 태스크가 무엇을 PASS 처리할지 정의 불가
   - Evidence: "동행복권 회차 수집기 모듈의 핵심 기능이 구현된다.", "통계 분석 엔진의 핵심 기능이 구현된다." …
   - Suggestion: brief의 구체 지표로 치환 — 예: "최근 500회차를 1분 이내 전량 수집", "rate limit 회피 위해 회차 간 ≥300ms 지연", "동일 seed로 재호출 시 동일 5조합 반환", "macOS/Windows에서 더블클릭 실행 시 0초 이내 환영 화면 표출"

3. **[Critical] brief의 핵심 제약이 태스크에 하나도 반영되지 않음**
   - Documents: project_brief.json vs implementation-tasks.md
   - Issue: constraints 8종(ko-KR 출력, PyInstaller onefile, SQLite/JSON 캐시, seed 재현성, 면책 고지, 교차 OS, rate limit 회피)이 30개 태스크 어디에도 명시되지 않음. "범위 정의 → 구현 → 검증" 3단 템플릿만 반복
   - Evidence: 모든 build 태스크 acceptance = "X의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다." — 제약 조건 0개
   - Suggestion: 제약별 전용 태스크 추가: (a) 동행복권 엔드포인트 증분 수집 + `returnValue=fail` 감지, (b) requests 세션 + 지수 백오프 retry, (c) seed 인자 CLI 노출 + 재현 테스트, (d) 면책 고지 문자열 필수 출력 + 리포트 헤더 배치, (e) `af.spec` hiddenimports + onefile 빌드, (f) SQLite 스키마 마이그레이션

4. **[High] 모듈 소유자(role)가 프로젝트 성격과 불일치**
   - Documents: implementation-design.md (Planned Modules)
   - Issue: 이 프로젝트는 터미널 CLI + 데이터 파이프라인인데 7개 모듈 소유자가 `frontend_dev`. brief.role_hints에 frontend_dev가 없음. 또한 "Game Logic Dev"는 로또 도메인에 부적합(확률 게임 상태전이가 아니라 통계 분석)
   - Evidence: brief `"role_hints": ["backend_dev", "data_analyst", "build_engineer", "qa_engineer"]` vs design 모듈 owner가 frontend_dev / game_logic_dev
   - Suggestion: 수집기·캐시는 `backend_dev`, 통계 엔진·추천기는 `data_analyst`, PyInstaller 스펙은 `build_engineer`, 리포트 포맷은 `backend_dev`로 재할당. game_logic_dev 전면 제거

5. **[High] API 계약 섹션 부재 — 외부 의존성이 명세되지 않음**
   - Documents: feature-spec.md (Inputs and Outputs)
   - Issue: 유일한 외부 의존인 동행복권 엔드포인트의 URL·쿼리 파라미터·응답 스키마·실패 신호(`returnValue=fail`)·rate limit 정책이 어느 문서에도 없음. brief.research_notes에만 있고 spec에 전사되지 않음
   - Evidence: brief "동행복권 공식 엔드포인트: https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={회차}" — spec Inputs/Outputs에는 "LottoDraw/NumberFrequency/Recommendation/FetchCheckpoint" 내부 저장 스키마만 존재
   - Suggestion: spec에 "External API Contract" 섹션 추가 — 요청/응답/에러/증분 탐지 로직(최신 회차까지 drwNo 증분 조회 후 returnValue=fail 직전 회차를 최신으로 확정)

6. **[High] 의존 관계 그래프가 전부 병렬 — 실제 파이프라인과 모순**
   - Documents: implementation-design.md (Data Flow) vs 실제 도메인
   - Issue: Data Flow가 "(시작) → 모듈X" 10줄로 모든 모듈을 병렬화. 실제로는 `수집기 → 캐시 → 통계 엔진 → 추천기 → 리포트`의 단방향 체인. tasks.depends_on도 모듈 내부 phase 순서만 정의하고 모듈 간 의존성 없음
   - Evidence: design "(시작) → **동행복권 회차 수집기 모듈**, (시작) → **회차 데이터 로컬 캐시 저장소**, ..." — 실행 전략도 "parallel"로 선언
   - Suggestion: Data Flow를 실제 파이프라인으로 재작성. build 단계 태스크 depends_on에 모듈 간 선행 관계 추가 (예: `frontend_dev_module_3_build_2 depends_on frontend_dev_module_2_build_2`)

7. **[High] Risk 항목이 NFR/완화 전략으로 이어지지 않음**
   - Documents: feature-plan.md vs feature-spec.md
   - Issue: plan에 6개 risk, NFR에 1개만. "rate limit → 지연/backoff", "API 스키마 변경 → 스키마 버전 감지/알림", "Gatekeeper → 공지", "오해 → 면책 고지 출력", "과적합 → 면책 + 검증용 역테스트" 등 대응 NFR 전무
   - Evidence: plan.Risks 6개 vs spec.NFR 1개 ("네트워크 장애 시 로컬 캐시…") — 심지어 이건 brief에서도 "constraints"에 있던 항목
   - Suggestion: 각 risk별 NFR 1:1 매핑 — 성능/신뢰성/보안/법적 면책 카테고리로 구조화

8. **[Medium] work_item 제목이 중간 절단됨**
   - Documents: 모든 4문서 Metadata
   - Issue: `work_item: 한국-로또-6-45-최근-500회차-1등-당첨번호를-동행복권-api에서-수집-통계-분석하여-패턴-기반-1등` — "1등"에서 끝나 문장 미완성
   - Suggestion: slug 생성기에 문장 단위 truncation 또는 해시 접미사 적용. 현재 제목으로는 GitHub issue/PR 연결 시 가독성 저해

9. **[Medium] NFR과 Risk의 항목이 동일 문장 — 분류 오류**
   - Documents: feature-spec.md (NFR) vs feature-plan.md (Risks)
   - Issue: "네트워크 장애 시 로컬 캐시(SQLite 또는 JSON)로 재시도·복구"가 NFR이면서 동시에 plan의 Risk에 등장. 이건 risk가 아니라 완화책
   - Evidence: plan.Risks의 마지막 항목, spec.NFR의 유일한 항목 동일 문자열
   - Suggestion: plan의 Risks에서 제거, spec NFR에 유지하되 "API 타임아웃 5초 + 지수 백오프 3회 재시도 후 로컬 캐시로 fallback" 수준으로 구체화

### Missing from Documents

- 동행복권 API 응답 스키마·에러 응답·최신 회차 탐지 알고리즘
- HTTP retry/backoff 정책, rate limit 회피 지연 간격
- `--seed`, `--count`, `--refresh` 등 CLI 플래그 설계
- 면책 고지 문구(필수 출력)와 배치 위치
- PyInstaller spec(hiddenimports, datas, onefile 옵션) 구체안
- macOS Gatekeeper/Windows SmartScreen 경고 사용자 안내 문서
- 캐시 스키마 마이그레이션 정책(컬럼 추가/변경 시)
- 통계 지표별 임계값(hot/cold 경계, 연속번호 허용 한계)
- 재현성 검증 테스트(동일 seed 입력 → 동일 출력 assertion)
- brief에 명시된 `docs/architecture.md` 및 `docs/change_history.md` 동시 갱신 규칙 반영 태스크
- Non-Goals로 선언된 2등 예측·GUI·웹·결제 연동에 대한 방어적 가드
- Exceptions and Failure Scenarios 섹션(현재 "(edit required)") — 최소 5종 실패 경로 필요: 네트워크 단절, API 404, 스키마 변경, 디스크 쓰기 실패, seed 충돌

**종합**: 4문서 모두 brief의 풍부한 도메인 정보를 활용하지 못하고 generic 템플릿 확장에 그쳤음. 구현 착수 전 스펙/설계를 실제 도메인 지식으로 재작성 필수.

---

## 메타데이터

- 총 토큰: 0
- 소요 시간: 102.4s
