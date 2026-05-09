# Document Review: 모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축

> Source: 모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축
> Date: 2026-04-18T01:25:30
> Type: document
> Providers: critic=claude, judge=claude
> Mode: single-provider
> Trigger: pipeline
> Round: 1/1

---

## 검증자 A (Critic): claude

## Critic Review

### Verdict: BLOCK

### Individual Document Scores
| Document | Score | Key Issues |
|----------|-------|-----------|
| feature-plan | 35/100 | Goals are deliverable names, not measurable goals; Success Metrics are tautological; no mitigation strategies for risks; stakeholders lack role specificity (no counts, no names for technical_writer role). |
| feature-spec | 25/100 | All acceptance criteria are generic boilerplate ("핵심 기능이 구현된다"); Exceptions/Existing Behavior/Out-of-Scope mostly "(edit required)"; no API interface spec (paths, methods, status codes, error shapes); NFR section has 1 item and it is actually a functional requirement. |
| implementation-design | 20/100 | Modules have no real design — each is a single-sentence restatement; Interface Impact, Compatibility, Alternatives all "(edit required)"; Data Flow is not a flow ("(시작) → module"); no dependency direction, no error handling, no rollback strategy. |
| implementation-tasks | 35/100 | Tasks are triplicated boilerplate (scope/build/verify per module) with no verifiable completion definition; no effort estimates; no tasks for API contract, offline cache schema, browser matrix, or NotebookLM-referenced design doc; technical_writer role from project_brief is missing entirely. |

### Cross-Consistency Matrix
| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | plan.risks → spec.nfr | FAIL | 5 risks (import breakage, 500-회차 지연, 브라우저 편차, stale cache, 파라미터 검증) → only 1 NFR line ("offline 폴백 제공"). No perf budget, no browser matrix, no param validation rule, no cache TTL. |
| 2 | plan.stakeholders → spec.user_scenarios | PARTIAL | plan lists Frontend/Backend/QA but project_brief also lists `technical_writer`. No scenario for writer. "개발자: pytest" scenario maps to QA but no stakeholder acts on Backend API owner perspective. |
| 3 | spec.acceptance_criteria → tasks.verification | FAIL | Spec has 8 boilerplate "핵심 기능이 구현된다" lines; tasks repeat the same sentence. There is no 1:1 measurable mapping — e.g. no criterion "GET /api/recommend returns 200 with ≤N combos within X ms". |
| 4 | spec.api_endpoints → tasks.implementation | FAIL | User scenario references `GET /api/recommend` but spec has NO `## API Endpoints` section and no task owns the endpoint contract. `source=offline` field appears only in scenarios, not in schema. |
| 5 | spec.user_scenarios → design.data_model | PARTIAL | DrawCache has `fetched_at` but no TTL/staleness rule, yet scenario uses offline cache and plan.risks warns about stale data. RecommendationCombo has `score` but no score range/meaning defined. |
| 6 | plan.constraints → design.tech_stack | PARTIAL | Constraint "lotto_predictor_v2 import 재사용" is absent from design modules — no module shows import path or wrapper layer. Touch-target 44×44 constraint is not reflected in any frontend module design. |
| 7 | design.modules → tasks.work_items | PASS (surface) | 8 modules → 8×3 tasks. But decomposition is mechanical, not architectural — e.g. "offline 캐시 폴백" is a frontend module though brief says server-layer reuses `lotto.cli.run` offline logic. **Contradiction.** |
| 8 | design.dependency_order → tasks.prerequisites | FAIL | Design says `execution_strategy: parallel` with no dependency edges, yet frontend modules (UI, cards, sliders, offline) obviously depend on backend API contract. No `depends_on` across modules — only within phase (scope→build→verify of same module). |
| 9 | Terminology consistency | FAIL | "오프라인 캐시 폴백 모듈" owner=`frontend_dev` in design but project_brief research_notes say "기존 lotto.cli.run의 offline 로직을 서버 계층에서 재사용 예정" → should be backend. |

### Findings

1. **[Critical] 오프라인 캐시 폴백 모듈의 소유자가 설계와 프로젝트 브리프 간 모순**
   - Documents: implementation-design.md + project_brief research_notes
   - Issue: 브리프는 서버 계층 재사용을 명시했는데 설계에선 frontend_dev가 소유.
   - Evidence: research_notes `"기존 lotto.cli.run의 offline 로직을 서버 계층에서 재사용 예정"` vs design `"### 오프라인 캐시 폴백 모듈 - owner: frontend_dev"`.
   - Suggestion: 모듈을 둘로 분리 — 서버측 `offline_cache_service`(backend_dev)와 클라이언트측 `offline_banner`(frontend_dev). 각각의 책임·상호작용을 설계에 명시.

2. **[Critical] API 계약이 어디에도 정의되지 않음**
   - Documents: feature-spec.md + implementation-design.md + implementation-tasks.md
   - Issue: 사용자 시나리오에 `GET /api/recommend` 호출이 명시됐지만 spec에 엔드포인트 섹션 없음, design의 Interface Impact는 `(edit required)`, tasks에도 API 스키마 정의 태스크 없음.
   - Evidence: feature-spec `"사용자: ... GET /api/recommend 호출"` vs implementation-design `"## Interface Impact - (edit required)"`.
   - Suggestion: feature-spec에 `## API Endpoints` 섹션 추가 — path/method/query params(n:1~10, draws:100~500)/200 response schema(RecommendationResponse)/4xx 오류 코드(422 validation, 503 offline_fallback)/5xx 처리. Backend scope 태스크의 acceptance에 "OpenAPI schema 생성됨" 추가.

3. **[Critical] 모든 acceptance criteria가 측정 불가능**
   - Documents: feature-spec.md + implementation-tasks.md
   - Issue: 8개 AC 전부 "X의 핵심 기능이 구현된다" 템플릿. 측정 방법·성공 기준·임계값 모두 없음.
   - Evidence: feature-spec `"- 로또 추천 REST API 서버의 핵심 기능이 구현된다."`; tasks `"acceptance: 로또 추천 REST API 서버의 핵심 기능이 구현된다."`
   - Suggestion: 각 AC를 구체화 — 예 "API: `GET /api/recommend?n=5&draws=500`이 p95 < 500ms 내 200 응답, combos 길이 ≤ n", "UI: iPhone 13 Safari에서 버튼 탭 타깃 ≥ 44×44 CSS px", "offline: navigator.onLine=false에서 `source=offline` 배지 표시".

4. **[High] Risk → NFR 매핑 누락**
   - Documents: feature-plan.md (7 risks) + feature-spec.md (1 NFR)
   - Issue: plan의 5개 기술 리스크 중 4개가 NFR에 전혀 반영 안 됨. "500회차 지연"은 퍼포먼스 NFR 필요, "브라우저 편차"는 지원 브라우저 매트릭스 필요, "파라미터 검증 누락"은 입력 검증 NFR 필요, "stale 캐시"는 캐시 TTL/만료 규칙 필요.
   - Evidence: feature-plan `"- 최근 500회차 분석 응답 지연..."` / `"- offline 캐시 stale 데이터가..."` vs feature-spec `"## Non-Functional Requirements - 네트워크 오류 시 offline 캐시 폴백 제공"` (1줄, 기능 요구사항).
   - Suggestion: NFR 섹션 재작성 — Performance(`/api/recommend` p95 < 500ms, 최악 < 1.5s), Compatibility(iOS Safari 15+, Android Chrome 100+), Validation(422 on out-of-range), Cache Freshness(DrawCache.fetched_at TTL 24h, UI에 timestamp 노출).

5. **[High] 모듈 간 의존성이 없어 병렬 실행 전제가 깨짐**
   - Documents: implementation-design.md + implementation-tasks.md
   - Issue: design `execution_strategy: parallel`, data_flow는 `(시작) → 모듈`만 반복. 그러나 프론트엔드 UI/카드/슬라이더/오프라인은 백엔드 API 계약 없이 구현 불가. QA 테스트는 양쪽 완료 후에만 가능.
   - Evidence: implementation-design `"실행 전략: parallel"` + `"- (시작) → **모바일 반응형 추천 웹 UI**"`; tasks `depends_on`이 동일 모듈 내 phase 간만 존재.
   - Suggestion: 크로스 모듈 의존성 추가 — `frontend_dev_module_2_build_2 depends_on backend_dev_module_1_scope_1` (API 계약 확정 후 UI 구현), `qa_engineer_module_6_build_2 depends_on backend_dev_module_1_build_2`, `qa_engineer_module_7_build_2 depends_on frontend_dev_module_2_build_2`.

6. **[High] technical_writer 역할이 브리프에서만 언급되고 문서에선 사라짐**
   - Documents: project_brief.role_hints + feature-plan.md + implementation-tasks.md
   - Issue: 브리프 `role_hints`에 technical_writer 포함, deliverables에 "모바일 웹 설계 문서" 포함, research_notes에 `docs/2026-04-18-mobile-web-design.md` 명시. 그러나 plan stakeholders엔 없고, 설계 문서 모듈 owner는 frontend_dev로 잘못 배정.
   - Evidence: project_brief `"role_hints": [..., "technical_writer"]`; design `"### 모바일 웹 설계 문서 - owner: frontend_dev"`.
   - Suggestion: plan stakeholders에 Technical Writer 추가, 설계 문서 모듈 owner를 technical_writer로 변경, acceptance에 "docs/2026-04-18-mobile-web-design.md 생성 + docs/change_history.md append" 명시.

7. **[High] 프로젝트 규칙(docs/architecture.md, change_history.md) 위반 가능성**
   - Documents: feature-plan.md evidence + implementation-tasks.md
   - Issue: 브리프와 evidence에 "설계 변경 시 같은 작업에서 architecture.md·change_history.md 동시 갱신" 규칙이 명시됐지만, 태스크에 해당 문서 갱신 액션 아이템이 없음.
   - Evidence: plan.Evidence `"설계 변경 시 같은 작업에서 architecture.md·change_history.md 동시 갱신"`; tasks에는 해당 파일명 등장 없음.
   - Suggestion: verify phase 태스크 중 최소 1개의 acceptance에 "docs/architecture.md 갱신됨 (lotto_mobile_web 섹션 추가)"·"docs/change_history.md에 항목 추가" 명시.

8. **[Medium] DrawCache 스키마에 TTL/만료 정책 없음**
   - Documents: implementation-design.md State And Data Model + feature-plan.md risks
   - Issue: `DrawCache (json): round, numbers, bonus, fetched_at` — fetched_at은 있으나 stale 판정 기준이 어디에도 없음. plan.risks의 "stale 데이터 노출" 리스크를 해결할 수 없음.
   - Evidence: implementation-design `"- **DrawCache** (json): round, numbers, bonus, fetched_at"`; plan.risks `"offline 캐시 stale 데이터가 사용자에게 노출될 가능성"`.
   - Suggestion: 데이터 모델에 `ttl_seconds` 또는 `max_age_hours` 필드 추가, UI는 `fetched_at` 기반으로 "X시간 전 캐시" 배지 표시 규칙 AC에 기재.

9. **[Medium] RecommendationCombo.score 의미·범위 미정의**
   - Documents: feature-spec.md + implementation-design.md
   - Issue: 사용자 시나리오에 "카드 탭 → 점수 상세 표시"가 있으나 score 필드의 계산식·범위·의미(frequency/consecutive/odd_even/section/trend 가중 합)가 명시 안 됨. 기존 lotto_predictor_v2 import를 전제로 한다면 원본 score semantics를 그대로 노출할지 여부 결정 필요.
   - Evidence: spec user_scenarios `"시스템: 점수·홀짝 비율·구간 분포 상세 영역 표시"`; design `"RecommendationCombo: numbers, score, odd_even_ratio, section_distribution"`.
   - Suggestion: score를 `score: float (0.0–1.0, 정규화된 pattern weight 합)`로 정의. 분해 필드(`score_breakdown: {frequency, gaps, odd_even, section, trend}`) 옵션 검토.

10. **[Medium] Success Metrics가 tautology (자기지시)**
    - Documents: feature-plan.md
    - Issue: 8개 메트릭 전부 "X — 완성 및 동작 검증됨" 형식. "완성"은 메트릭이 아니라 상태.
    - Evidence: feature-plan `"- 로또 추천 REST API 서버 — 완성 및 동작 검증됨"`.
    - Suggestion: 정량 메트릭으로 대체 — 예 "p95 API 응답 < 500ms (draws=500, n=5)", "Chrome/Safari/Firefox 모바일 smoke test 3/3 green", "pytest coverage ≥ 80%", "Lighthouse mobile score ≥ 85".

### Missing from Documents

- **API endpoint spec**: path, method, query params, request/response JSON schema, error codes (422, 503), 예시 curl. feature-spec에 필수.
- **Performance budget**: `/api/recommend` p95/p99, 캐시 히트율, 캐시 TTL.
- **Browser support matrix**: iOS Safari / Android Chrome 최소 버전, 테스트 기기.
- **Parameter validation rules**: n, draws 범위 초과 시 상태코드·메시지(한국어).
- **Security/rate limiting**: 퍼블릭 API인 경우 rate limit, CORS 정책.
- **Offline UX contract**: offline 판정 트리거(navigator.onLine vs fetch 실패), stale 임계값, fallback 배지 카피.
- **technical_writer의 산출물·소유자 귀속**: `docs/2026-04-18-mobile-web-design.md`, architecture.md·change_history.md 갱신 태스크.
- **Effort estimates**: 각 task에 hours 또는 story points.
- **Rollback plan**: FastAPI 배포 실패 시 이전 버전 롤백, lotto_predictor_v2 import 깨짐 감지 시 빌드 차단 CI 룰.
- **Alternatives Considered**: FastAPI vs Flask(브리프에서 둘 다 언급), SPA vs vanilla JS 선택 근거.

> Critic 소결: 발견 5개, 판정 BLOCK

---

## 최종 판정 (Judge): claude

### 종합 판정: BLOCK

## Critic Review

### Verdict: BLOCK

### Individual Document Scores
| Document | Score | Key Issues |
|----------|-------|-----------|
| feature-plan | 35/100 | Goals are deliverable names, not measurable goals; Success Metrics are tautological; no mitigation strategies for risks; stakeholders lack role specificity (no counts, no names for technical_writer role). |
| feature-spec | 25/100 | All acceptance criteria are generic boilerplate ("핵심 기능이 구현된다"); Exceptions/Existing Behavior/Out-of-Scope mostly "(edit required)"; no API interface spec (paths, methods, status codes, error shapes); NFR section has 1 item and it is actually a functional requirement. |
| implementation-design | 20/100 | Modules have no real design — each is a single-sentence restatement; Interface Impact, Compatibility, Alternatives all "(edit required)"; Data Flow is not a flow ("(시작) → module"); no dependency direction, no error handling, no rollback strategy. |
| implementation-tasks | 35/100 | Tasks are triplicated boilerplate (scope/build/verify per module) with no verifiable completion definition; no effort estimates; no tasks for API contract, offline cache schema, browser matrix, or NotebookLM-referenced design doc; technical_writer role from project_brief is missing entirely. |

### Cross-Consistency Matrix
| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | plan.risks → spec.nfr | FAIL | 5 risks (import breakage, 500-회차 지연, 브라우저 편차, stale cache, 파라미터 검증) → only 1 NFR line ("offline 폴백 제공"). No perf budget, no browser matrix, no param validation rule, no cache TTL. |
| 2 | plan.stakeholders → spec.user_scenarios | PARTIAL | plan lists Frontend/Backend/QA but project_brief also lists `technical_writer`. No scenario for writer. "개발자: pytest" scenario maps to QA but no stakeholder acts on Backend API owner perspective. |
| 3 | spec.acceptance_criteria → tasks.verification | FAIL | Spec has 8 boilerplate "핵심 기능이 구현된다" lines; tasks repeat the same sentence. There is no 1:1 measurable mapping — e.g. no criterion "GET /api/recommend returns 200 with ≤N combos within X ms". |
| 4 | spec.api_endpoints → tasks.implementation | FAIL | User scenario references `GET /api/recommend` but spec has NO `## API Endpoints` section and no task owns the endpoint contract. `source=offline` field appears only in scenarios, not in schema. |
| 5 | spec.user_scenarios → design.data_model | PARTIAL | DrawCache has `fetched_at` but no TTL/staleness rule, yet scenario uses offline cache and plan.risks warns about stale data. RecommendationCombo has `score` but no score range/meaning defined. |
| 6 | plan.constraints → design.tech_stack | PARTIAL | Constraint "lotto_predictor_v2 import 재사용" is absent from design modules — no module shows import path or wrapper layer. Touch-target 44×44 constraint is not reflected in any frontend module design. |
| 7 | design.modules → tasks.work_items | PASS (surface) | 8 modules → 8×3 tasks. But decomposition is mechanical, not architectural — e.g. "offline 캐시 폴백" is a frontend module though brief says server-layer reuses `lotto.cli.run` offline logic. **Contradiction.** |
| 8 | design.dependency_order → tasks.prerequisites | FAIL | Design says `execution_strategy: parallel` with no dependency edges, yet frontend modules (UI, cards, sliders, offline) obviously depend on backend API contract. No `depends_on` across modules — only within phase (scope→build→verify of same module). |
| 9 | Terminology consistency | FAIL | "오프라인 캐시 폴백 모듈" owner=`frontend_dev` in design but project_brief research_notes say "기존 lotto.cli.run의 offline 로직을 서버 계층에서 재사용 예정" → should be backend. |

### Findings

1. **[Critical] 오프라인 캐시 폴백 모듈의 소유자가 설계와 프로젝트 브리프 간 모순**
   - Documents: implementation-design.md + project_brief research_notes
   - Issue: 브리프는 서버 계층 재사용을 명시했는데 설계에선 frontend_dev가 소유.
   - Evidence: research_notes `"기존 lotto.cli.run의 offline 로직을 서버 계층에서 재사용 예정"` vs design `"### 오프라인 캐시 폴백 모듈 - owner: frontend_dev"`.
   - Suggestion: 모듈을 둘로 분리 — 서버측 `offline_cache_service`(backend_dev)와 클라이언트측 `offline_banner`(frontend_dev). 각각의 책임·상호작용을 설계에 명시.

2. **[Critical] API 계약이 어디에도 정의되지 않음**
   - Documents: feature-spec.md + implementation-design.md + implementation-tasks.md
   - Issue: 사용자 시나리오에 `GET /api/recommend` 호출이 명시됐지만 spec에 엔드포인트 섹션 없음, design의 Interface Impact는 `(edit required)`, tasks에도 API 스키마 정의 태스크 없음.
   - Evidence: feature-spec `"사용자: ... GET /api/recommend 호출"` vs implementation-design `"## Interface Impact - (edit required)"`.
   - Suggestion: feature-spec에 `## API Endpoints` 섹션 추가 — path/method/query params(n:1~10, draws:100~500)/200 response schema(RecommendationResponse)/4xx 오류 코드(422 validation, 503 offline_fallback)/5xx 처리. Backend scope 태스크의 acceptance에 "OpenAPI schema 생성됨" 추가.

3. **[Critical] 모든 acceptance criteria가 측정 불가능**
   - Documents: feature-spec.md + implementation-tasks.md
   - Issue: 8개 AC 전부 "X의 핵심 기능이 구현된다" 템플릿. 측정 방법·성공 기준·임계값 모두 없음.
   - Evidence: feature-spec `"- 로또 추천 REST API 서버의 핵심 기능이 구현된다."`; tasks `"acceptance: 로또 추천 REST API 서버의 핵심 기능이 구현된다."`
   - Suggestion: 각 AC를 구체화 — 예 "API: `GET /api/recommend?n=5&draws=500`이 p95 < 500ms 내 200 응답, combos 길이 ≤ n", "UI: iPhone 13 Safari에서 버튼 탭 타깃 ≥ 44×44 CSS px", "offline: navigator.onLine=false에서 `source=offline` 배지 표시".

4. **[High] Risk → NFR 매핑 누락**
   - Documents: feature-plan.md (7 risks) + feature-spec.md (1 NFR)
   - Issue: plan의 5개 기술 리스크 중 4개가 NFR에 전혀 반영 안 됨. "500회차 지연"은 퍼포먼스 NFR 필요, "브라우저 편차"는 지원 브라우저 매트릭스 필요, "파라미터 검증 누락"은 입력 검증 NFR 필요, "stale 캐시"는 캐시 TTL/만료 규칙 필요.
   - Evidence: feature-plan `"- 최근 500회차 분석 응답 지연..."` / `"- offline 캐시 stale 데이터가..."` vs feature-spec `"## Non-Functional Requirements - 네트워크 오류 시 offline 캐시 폴백 제공"` (1줄, 기능 요구사항).
   - Suggestion: NFR 섹션 재작성 — Performance(`/api/recommend` p95 < 500ms, 최악 < 1.5s), Compatibility(iOS Safari 15+, Android Chrome 100+), Validation(422 on out-of-range), Cache Freshness(DrawCache.fetched_at TTL 24h, UI에 timestamp 노출).

5. **[High] 모듈 간 의존성이 없어 병렬 실행 전제가 깨짐**
   - Documents: implementation-design.md + implementation-tasks.md
   - Issue: design `execution_strategy: parallel`, data_flow는 `(시작) → 모듈`만 반복. 그러나 프론트엔드 UI/카드/슬라이더/오프라인은 백엔드 API 계약 없이 구현 불가. QA 테스트는 양쪽 완료 후에만 가능.
   - Evidence: implementation-design `"실행 전략: parallel"` + `"- (시작) → **모바일 반응형 추천 웹 UI**"`; tasks `depends_on`이 동일 모듈 내 phase 간만 존재.
   - Suggestion: 크로스 모듈 의존성 추가 — `frontend_dev_module_2_build_2 depends_on backend_dev_module_1_scope_1` (API 계약 확정 후 UI 구현), `qa_engineer_module_6_build_2 depends_on backend_dev_module_1_build_2`, `qa_engineer_module_7_build_2 depends_on frontend_dev_module_2_build_2`.

6. **[High] technical_writer 역할이 브리프에서만 언급되고 문서에선 사라짐**
   - Documents: project_brief.role_hints + feature-plan.md + implementation-tasks.md
   - Issue: 브리프 `role_hints`에 technical_writer 포함, deliverables에 "모바일 웹 설계 문서" 포함, research_notes에 `docs/2026-04-18-mobile-web-design.md` 명시. 그러나 plan stakeholders엔 없고, 설계 문서 모듈 owner는 frontend_dev로 잘못 배정.
   - Evidence: project_brief `"role_hints": [..., "technical_writer"]`; design `"### 모바일 웹 설계 문서 - owner: frontend_dev"`.
   - Suggestion: plan stakeholders에 Technical Writer 추가, 설계 문서 모듈 owner를 technical_writer로 변경, acceptance에 "docs/2026-04-18-mobile-web-design.md 생성 + docs/change_history.md append" 명시.

7. **[High] 프로젝트 규칙(docs/architecture.md, change_history.md) 위반 가능성**
   - Documents: feature-plan.md evidence + implementation-tasks.md
   - Issue: 브리프와 evidence에 "설계 변경 시 같은 작업에서 architecture.md·change_history.md 동시 갱신" 규칙이 명시됐지만, 태스크에 해당 문서 갱신 액션 아이템이 없음.
   - Evidence: plan.Evidence `"설계 변경 시 같은 작업에서 architecture.md·change_history.md 동시 갱신"`; tasks에는 해당 파일명 등장 없음.
   - Suggestion: verify phase 태스크 중 최소 1개의 acceptance에 "docs/architecture.md 갱신됨 (lotto_mobile_web 섹션 추가)"·"docs/change_history.md에 항목 추가" 명시.

8. **[Medium] DrawCache 스키마에 TTL/만료 정책 없음**
   - Documents: implementation-design.md State And Data Model + feature-plan.md risks
   - Issue: `DrawCache (json): round, numbers, bonus, fetched_at` — fetched_at은 있으나 stale 판정 기준이 어디에도 없음. plan.risks의 "stale 데이터 노출" 리스크를 해결할 수 없음.
   - Evidence: implementation-design `"- **DrawCache** (json): round, numbers, bonus, fetched_at"`; plan.risks `"offline 캐시 stale 데이터가 사용자에게 노출될 가능성"`.
   - Suggestion: 데이터 모델에 `ttl_seconds` 또는 `max_age_hours` 필드 추가, UI는 `fetched_at` 기반으로 "X시간 전 캐시" 배지 표시 규칙 AC에 기재.

9. **[Medium] RecommendationCombo.score 의미·범위 미정의**
   - Documents: feature-spec.md + implementation-design.md
   - Issue: 사용자 시나리오에 "카드 탭 → 점수 상세 표시"가 있으나 score 필드의 계산식·범위·의미(frequency/consecutive/odd_even/section/trend 가중 합)가 명시 안 됨. 기존 lotto_predictor_v2 import를 전제로 한다면 원본 score semantics를 그대로 노출할지 여부 결정 필요.
   - Evidence: spec user_scenarios `"시스템: 점수·홀짝 비율·구간 분포 상세 영역 표시"`; design `"RecommendationCombo: numbers, score, odd_even_ratio, section_distribution"`.
   - Suggestion: score를 `score: float (0.0–1.0, 정규화된 pattern weight 합)`로 정의. 분해 필드(`score_breakdown: {frequency, gaps, odd_even, section, trend}`) 옵션 검토.

10. **[Medium] Success Metrics가 tautology (자기지시)**
    - Documents: feature-plan.md
    - Issue: 8개 메트릭 전부 "X — 완성 및 동작 검증됨" 형식. "완성"은 메트릭이 아니라 상태.
    - Evidence: feature-plan `"- 로또 추천 REST API 서버 — 완성 및 동작 검증됨"`.
    - Suggestion: 정량 메트릭으로 대체 — 예 "p95 API 응답 < 500ms (draws=500, n=5)", "Chrome/Safari/Firefox 모바일 smoke test 3/3 green", "pytest coverage ≥ 80%", "Lighthouse mobile score ≥ 85".

### Missing from Documents

- **API endpoint spec**: path, method, query params, request/response JSON schema, error codes (422, 503), 예시 curl. feature-spec에 필수.
- **Performance budget**: `/api/recommend` p95/p99, 캐시 히트율, 캐시 TTL.
- **Browser support matrix**: iOS Safari / Android Chrome 최소 버전, 테스트 기기.
- **Parameter validation rules**: n, draws 범위 초과 시 상태코드·메시지(한국어).
- **Security/rate limiting**: 퍼블릭 API인 경우 rate limit, CORS 정책.
- **Offline UX contract**: offline 판정 트리거(navigator.onLine vs fetch 실패), stale 임계값, fallback 배지 카피.
- **technical_writer의 산출물·소유자 귀속**: `docs/2026-04-18-mobile-web-design.md`, architecture.md·change_history.md 갱신 태스크.
- **Effort estimates**: 각 task에 hours 또는 story points.
- **Rollback plan**: FastAPI 배포 실패 시 이전 버전 롤백, lotto_predictor_v2 import 깨짐 감지 시 빌드 차단 CI 룰.
- **Alternatives Considered**: FastAPI vs Flask(브리프에서 둘 다 언급), SPA vs vanilla JS 선택 근거.

---

## 메타데이터

- 총 토큰: 0
- 소요 시간: 91.6s
