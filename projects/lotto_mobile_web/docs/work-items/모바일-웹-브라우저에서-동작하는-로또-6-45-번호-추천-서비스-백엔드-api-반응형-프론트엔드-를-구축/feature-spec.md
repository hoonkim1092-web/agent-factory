# Feature Spec

## Metadata

- work_item: 모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축
- source_plan: feature-plan.md
- status: draft
- last_updated: 2026-04-18T01:20:57

## Feature Overview

모바일 웹 브라우저에서 동작하는 로또 6/45 번호 추천 서비스(백엔드 API + 반응형 프론트엔드)를 구축한다.

## User Scenarios

- 사용자: 스마트폰 브라우저로 접속 -> 시스템: 모바일 반응형 추천 화면 렌더링
- 사용자: 조합 개수·분석 회차 슬라이더 조정 후 추천받기 탭 -> 시스템: GET /api/recommend 호출 후 카드 5개 렌더링
- 사용자: 네트워크 오프라인 상태에서 추천받기 탭 -> 시스템: 로컬 캐시 기반 폴백 응답과 source=offline 표시
- 사용자: 카드 탭 -> 시스템: 점수·홀짝 비율·구간 분포 상세 영역 표시
- 개발자: pytest 실행 -> 시스템: API 단위 + 프론트 smoke 테스트 전 케이스 통과

## Functional Requirements

- [로또 추천 REST API 서버] 로또 추천 REST API 서버을(를) 구현한다.
- [모바일 반응형 추천 웹 UI] 모바일 반응형 추천 웹 UI을(를) 구현한다.
- [조합 카드 시각화 컴포넌트] 조합 카드 시각화 컴포넌트을(를) 구현한다.
- [파라미터 슬라이더 컨트롤] 파라미터 슬라이더 컨트롤을(를) 구현한다.
- [오프라인 캐시 폴백 모듈] 오프라인 캐시 폴백 모듈을(를) 구현한다.
- [API 단위 테스트 스위트] API 단위 테스트 스위트을(를) 구현한다.
- [프론트엔드 렌더링 smoke 테스트] 프론트엔드 렌더링 smoke 테스트을(를) 구현한다.
- [모바일 웹 설계 문서] 모바일 웹 설계 문서을(를) 구현한다.

## Non-Functional Requirements

- 네트워크 오류 시 offline 캐시 폴백 제공

## Inputs and Outputs

- **RecommendationRequest** [memory]: n, draws, offline
- **RecommendationCombo** [memory]: numbers, score, odd_even_ratio, section_distribution
- **RecommendationResponse** [memory]: generated_at, source, draws_used, combos
- **DrawCache** [json]: round, numbers, bonus, fetched_at

## Exceptions and Failure Scenarios

- (edit required)

## Existing Behavior To Preserve

- (edit required)

## Acceptance Criteria

- 로또 추천 REST API 서버의 핵심 기능이 구현된다.
- 관련 파일과 산출물이 갱신된다.
- 검증 결과가 정리된다.
- 잔여 리스크와 후속 작업이 기록된다.
- 모바일 반응형 추천 웹 UI의 핵심 기능이 구현된다.
- 조합 카드 시각화 컴포넌트의 핵심 기능이 구현된다.
- 파라미터 슬라이더 컨트롤의 핵심 기능이 구현된다.
- 오프라인 캐시 폴백 모듈의 핵심 기능이 구현된다.
- API 단위 테스트 스위트의 핵심 기능이 구현된다.
- 프론트엔드 렌더링 smoke 테스트의 핵심 기능이 구현된다.
- 모바일 웹 설계 문서의 핵심 기능이 구현된다.

## Evidence

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

## Out Of Scope

- 사용자 계정/로그인 기능 제공
- 실제 복권 구매 연동
- iOS/Android 네이티브 앱 패키징
- 새로운 패턴 분석 알고리즘 개발
- 실시간 추첨 중계 기능
