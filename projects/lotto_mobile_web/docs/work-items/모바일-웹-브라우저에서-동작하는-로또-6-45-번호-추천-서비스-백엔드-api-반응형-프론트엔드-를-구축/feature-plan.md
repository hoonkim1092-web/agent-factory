# Feature Plan

## Metadata

- work_item: 모바일-웹-브라우저에서-동작하는-로또-6-45-번호-추천-서비스-백엔드-api-반응형-프론트엔드-를-구축
- owner: (edit required)
- status: draft
- last_updated: 2026-04-18T01:20:57

## Background

기존 lotto_predictor_v2는 CLI 환경에서만 동작하여 외부에서 빠르게 추천을 받기 어려웠다. 해당 저장소의 패턴 분석 로직(frequency, consecutive gaps, odd/even ratio, section distribution, trend weights)은 검증되어 있어 재사용 가치가 높다. 모바일 접근성을 확보하면 사용자가 외출 중에도 즉시 추천 조합을 확인할 수 있다.

## Problem Statement

CLI 전용 추천 파이프라인은 모바일/원격 사용자가 접근할 수 없고, 슬라이더 기반 파라미터 조정이나 카드형 시각화 같은 터치 친화적 UX가 부재하다. 또한 네트워크 불안정 시 사용자에게 의미 있는 폴백 경험을 제공하지 못한다.

## Goals

- 로또 추천 REST API 서버
- 모바일 반응형 추천 웹 UI
- 조합 카드 시각화 컴포넌트
- 파라미터 슬라이더 컨트롤
- 오프라인 캐시 폴백 모듈
- API 단위 테스트 스위트
- 프론트엔드 렌더링 smoke 테스트
- 모바일 웹 설계 문서

## Non-Goals

- 사용자 계정/로그인 기능 제공
- 실제 복권 구매 연동
- iOS/Android 네이티브 앱 패키징
- 새로운 패턴 분석 알고리즘 개발
- 실시간 추첨 중계 기능

## Scope

- **로또 추천 REST API 서버**: 로또 추천 REST API 서버을(를) 구현한다.
- **모바일 반응형 추천 웹 UI**: 모바일 반응형 추천 웹 UI을(를) 구현한다.
- **조합 카드 시각화 컴포넌트**: 조합 카드 시각화 컴포넌트을(를) 구현한다.
- **파라미터 슬라이더 컨트롤**: 파라미터 슬라이더 컨트롤을(를) 구현한다.
- **오프라인 캐시 폴백 모듈**: 오프라인 캐시 폴백 모듈을(를) 구현한다.
- **API 단위 테스트 스위트**: API 단위 테스트 스위트을(를) 구현한다.
- **프론트엔드 렌더링 smoke 테스트**: 프론트엔드 렌더링 smoke 테스트을(를) 구현한다.
- **모바일 웹 설계 문서**: 모바일 웹 설계 문서을(를) 구현한다.

## Stakeholders

- Frontend Dev: 사용자 화면과 상호작용 레이어를 구현한다.
- Backend Dev: 서버, 데이터, 외부 연동 레이어를 구현한다.
- QA Engineer: 핵심 플로우와 회귀 시나리오를 검증한다.

## Success Metrics

- 로또 추천 REST API 서버 — 완성 및 동작 검증됨
- 모바일 반응형 추천 웹 UI — 완성 및 동작 검증됨
- 조합 카드 시각화 컴포넌트 — 완성 및 동작 검증됨
- 파라미터 슬라이더 컨트롤 — 완성 및 동작 검증됨
- 오프라인 캐시 폴백 모듈 — 완성 및 동작 검증됨
- API 단위 테스트 스위트 — 완성 및 동작 검증됨
- 프론트엔드 렌더링 smoke 테스트 — 완성 및 동작 검증됨
- 모바일 웹 설계 문서 — 완성 및 동작 검증됨

## Risks and Assumptions

- lotto_predictor_v2 내부 API 변경 시 import 경로 깨짐 위험
- 최근 500회차 분석 응답 지연으로 모바일 UX 저하 가능성
- 브라우저별 슬라이더/레이아웃 렌더링 편차
- offline 캐시 stale 데이터가 사용자에게 노출될 가능성
- API 파라미터 검증 누락 시 서버 에러 또는 과도한 연산
- 기존 lotto_predictor_v2의 패턴 분석 모듈을 신규 구현 없이 import 방식으로 재사용
- 네트워크 오류 시 offline 캐시 폴백 제공

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

## Approval Request

- Review this scope and confirm approval-gate.md when ready.
