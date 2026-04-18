# Implementation Design

## Metadata

- work_item: 모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축
- spec_type: feature
- source_spec: feature-spec.md
- status: draft
- last_updated: 2026-04-18T01:20:57

## Design Summary

모바일 웹 브라우저에서 동작하는 로또 6/45 번호 추천 서비스(백엔드 API + 반응형 프론트엔드)를 구축한다.

아키텍처: web_app

기술 스택: Python 3.11, FastAPI, Uvicorn, Pydantic v2, HTML5, CSS3 (mobile-first), Vanilla JavaScript (ES2020), pytest, httpx TestClient

실행 전략: parallel

## Planned Modules

### 로또 추천 REST API 서버
- owner: backend_dev
- objective: 로또 추천 REST API 서버을(를) 구현한다.
- deliverables: 로또 추천 REST API 서버
- feature_slices: 로또 추천 REST API 서버을(를) 구현한다.

### 모바일 반응형 추천 웹 UI
- owner: frontend_dev
- objective: 모바일 반응형 추천 웹 UI을(를) 구현한다.
- deliverables: 모바일 반응형 추천 웹 UI
- feature_slices: 모바일 반응형 추천 웹 UI을(를) 구현한다.

### 조합 카드 시각화 컴포넌트
- owner: frontend_dev
- objective: 조합 카드 시각화 컴포넌트을(를) 구현한다.
- deliverables: 조합 카드 시각화 컴포넌트
- feature_slices: 조합 카드 시각화 컴포넌트을(를) 구현한다.

### 파라미터 슬라이더 컨트롤
- owner: frontend_dev
- objective: 파라미터 슬라이더 컨트롤을(를) 구현한다.
- deliverables: 파라미터 슬라이더 컨트롤
- feature_slices: 파라미터 슬라이더 컨트롤을(를) 구현한다.

### 오프라인 캐시 폴백 모듈
- owner: frontend_dev
- objective: 오프라인 캐시 폴백 모듈을(를) 구현한다.
- deliverables: 오프라인 캐시 폴백 모듈
- feature_slices: 오프라인 캐시 폴백 모듈을(를) 구현한다.

### API 단위 테스트 스위트
- owner: qa_engineer
- objective: API 단위 테스트 스위트을(를) 구현한다.
- deliverables: API 단위 테스트 스위트
- feature_slices: API 단위 테스트 스위트을(를) 구현한다.

### 프론트엔드 렌더링 smoke 테스트
- owner: qa_engineer
- objective: 프론트엔드 렌더링 smoke 테스트을(를) 구현한다.
- deliverables: 프론트엔드 렌더링 smoke 테스트
- feature_slices: 프론트엔드 렌더링 smoke 테스트을(를) 구현한다.

### 모바일 웹 설계 문서
- owner: frontend_dev
- objective: 모바일 웹 설계 문서을(를) 구현한다.
- deliverables: 모바일 웹 설계 문서
- feature_slices: 모바일 웹 설계 문서을(를) 구현한다.


## Data Flow

- (시작) → **로또 추천 REST API 서버**
- (시작) → **모바일 반응형 추천 웹 UI**
- (시작) → **조합 카드 시각화 컴포넌트**
- (시작) → **파라미터 슬라이더 컨트롤**
- (시작) → **오프라인 캐시 폴백 모듈**
- (시작) → **API 단위 테스트 스위트**
- (시작) → **프론트엔드 렌더링 smoke 테스트**
- (시작) → **모바일 웹 설계 문서**

## Interface Impact

- (edit required)

## State And Data Model

- **RecommendationRequest** (memory): n, draws, offline
- **RecommendationCombo** (memory): numbers, score, odd_even_ratio, section_distribution
- **RecommendationResponse** (memory): generated_at, source, draws_used, combos
- **DrawCache** (json): round, numbers, bonus, fetched_at

## Compatibility Considerations

- (edit required)

## Migration Requirement

- none

## Risks

- lotto_predictor_v2 내부 API 변경 시 import 경로 깨짐 위험
- 최근 500회차 분석 응답 지연으로 모바일 UX 저하 가능성
- 브라우저별 슬라이더/레이아웃 렌더링 편차
- offline 캐시 stale 데이터가 사용자에게 노출될 가능성
- API 파라미터 검증 누락 시 서버 에러 또는 과도한 연산
- 기존 lotto_predictor_v2의 패턴 분석 모듈을 신규 구현 없이 import 방식으로 재사용
- 네트워크 오류 시 offline 캐시 폴백 제공

## Alternatives Considered

- (edit required)

## Design Evidence

- Local reference: docs/architecture.md -> ## 메타데이터 - 마지막 업데이트: 2026-04-18T01:19:38 - 상태: active - 문서 언어: 한국어 (OS: `ko-KR`)
- Local reference: docs/architecture.md -> ## 문서 규칙 - 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다. - 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다. - 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다. - 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
- Local reference: docs/change_history.md -> # 변경 이력 설계, 아키텍처, 워크플로, 구현 전략이 바뀔 때마다 항목을 하나씩 추가한다.
- LLM prior knowledge (unverified): Mobile-first responsive design with viewport meta tag and touch-friendly tap targets (minimum 44x44 CSS pixels per WCAG/Apple HIG)
- LLM prior knowledge (unverified): Stateless REST JSON API with query parameter validation for numeric ranges (n: 1-10, draws: 100-500)
- NotebookLM synthesis: Conversation ID: fd8bf2ba-4a2a-471a-8981-90ed49151e30 Use --conversation-id for follow-up questions

## References

- Local: docs/architecture.md | ## 메타데이터
- Local: docs/architecture.md | ## 문서 규칙
- Local: docs/change_history.md | # 변경 이력
- Local: docs/change_history.md | ### 2026-04-18T01:19:38
- Local: docs/2026-04-17-review-trigger-unified-architecture.md | ### 8.1 단위 테스트
- Local: docs/code_review/code-review.md | ## 2026-04-17 23:21 — `2026-04-14-build-diet` (9a494d41)

## Test Strategy

- Unit tests per module
- Integration tests for cross-module flows
