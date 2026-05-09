# Task Execution Plan

## Overview
- project_goal: 모바일 웹 브라우저에서 동작하는 로또 6/45 번호 추천 서비스(백엔드 API + 반응형 프론트엔드)를 구축한다.
- execution_strategy: parallel
- role_count: 3
- module_count: 8
- task_count: 24

## Evidence
- Local reference: docs/architecture.md -> ## 메타데이터 - 마지막 업데이트: 2026-04-18T01:19:38 - 상태: active - 문서 언어: 한국어 (OS: `ko-KR`)
- Local reference: docs/architecture.md -> ## 문서 규칙 - 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다. - 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다. - 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다. - 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
- Local reference: docs/change_history.md -> # 변경 이력 설계, 아키텍처, 워크플로, 구현 전략이 바뀔 때마다 항목을 하나씩 추가한다.
- LLM prior knowledge (unverified): Mobile-first responsive design with viewport meta tag and touch-friendly tap targets (minimum 44x44 CSS pixels per WCAG/Apple HIG)
- LLM prior knowledge (unverified): Stateless REST JSON API with query parameter validation for numeric ranges (n: 1-10, draws: 100-500)
- NotebookLM synthesis: Conversation ID: fd8bf2ba-4a2a-471a-8981-90ed49151e30 Use --conversation-id for follow-up questions
- NotebookLM: Conversation ID: fd8bf2ba-4a2a-471a-8981-90ed49151e30 Use --conversation-id for follow-up questions

## Stage Order
1. 범위와 계약 정의
   objective: 기능 경계를 모듈 단위로 나누고 역할별 인터페이스를 고정한다.
   exit_criteria: 모든 작업이 owner_role과 depends_on을 가진다., 핵심 산출물이 모듈별로 정리된다.
2. 기능 슬라이스 구현
   objective: 독립 배포 가능한 작은 기능 단위로 구현을 진행한다.
   exit_criteria: 각 모듈이 최소 1개의 구현 작업을 가진다., 기능 슬라이스가 파일/산출물 기준으로 분리된다.
3. 통합과 핸드오프
   objective: 역할 간 의존성을 정리하고 결과를 다음 작업자가 이어받을 수 있게 만든다.
   exit_criteria: 의존 작업이 정리되고 handoff 기준이 명시된다., 검증 전에 필요한 연결 작업이 완료된다.
4. 검증과 마감
   objective: 기능 동작, 회귀 리스크, 남은 이슈를 명시적으로 검증한다.
   exit_criteria: 검증 작업이 존재한다., 잔여 리스크와 후속 작업이 기록된다.

## Module Breakdown By Role
### 로또 추천 REST API 서버
- owner_role: Backend Dev
- objective: 로또 추천 REST API 서버을(를) 구현한다.
- feature_slices: 로또 추천 REST API 서버을(를) 구현한다.
- deliverables: 로또 추천 REST API 서버
- depends_on: -
- tasks:
  - [scope] Backend Dev: 로또 추천 REST API 서버 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 로또 추천 REST API 서버 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: 로또 추천 REST API 서버을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 로또 추천 REST API 서버의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: 로또 추천 REST API 서버 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 모바일 반응형 추천 웹 UI
- owner_role: Frontend Dev
- objective: 모바일 반응형 추천 웹 UI을(를) 구현한다.
- feature_slices: 모바일 반응형 추천 웹 UI을(를) 구현한다.
- deliverables: 모바일 반응형 추천 웹 UI
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 모바일 반응형 추천 웹 UI 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 모바일 반응형 추천 웹 UI 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 모바일 반응형 추천 웹 UI을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 모바일 반응형 추천 웹 UI의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 모바일 반응형 추천 웹 UI 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 조합 카드 시각화 컴포넌트
- owner_role: Frontend Dev
- objective: 조합 카드 시각화 컴포넌트을(를) 구현한다.
- feature_slices: 조합 카드 시각화 컴포넌트을(를) 구현한다.
- deliverables: 조합 카드 시각화 컴포넌트
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 조합 카드 시각화 컴포넌트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 조합 카드 시각화 컴포넌트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 조합 카드 시각화 컴포넌트을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 조합 카드 시각화 컴포넌트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 조합 카드 시각화 컴포넌트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 파라미터 슬라이더 컨트롤
- owner_role: Frontend Dev
- objective: 파라미터 슬라이더 컨트롤을(를) 구현한다.
- feature_slices: 파라미터 슬라이더 컨트롤을(를) 구현한다.
- deliverables: 파라미터 슬라이더 컨트롤
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 파라미터 슬라이더 컨트롤 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 파라미터 슬라이더 컨트롤 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 파라미터 슬라이더 컨트롤을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 파라미터 슬라이더 컨트롤의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 파라미터 슬라이더 컨트롤 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 오프라인 캐시 폴백 모듈
- owner_role: Frontend Dev
- objective: 오프라인 캐시 폴백 모듈을(를) 구현한다.
- feature_slices: 오프라인 캐시 폴백 모듈을(를) 구현한다.
- deliverables: 오프라인 캐시 폴백 모듈
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 오프라인 캐시 폴백 모듈 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 오프라인 캐시 폴백 모듈 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 오프라인 캐시 폴백 모듈을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 오프라인 캐시 폴백 모듈의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 오프라인 캐시 폴백 모듈 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### API 단위 테스트 스위트
- owner_role: QA Engineer
- objective: API 단위 테스트 스위트을(를) 구현한다.
- feature_slices: API 단위 테스트 스위트을(를) 구현한다.
- deliverables: API 단위 테스트 스위트
- depends_on: -
- tasks:
  - [scope] QA Engineer: API 단위 테스트 스위트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: API 단위 테스트 스위트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: API 단위 테스트 스위트을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: API 단위 테스트 스위트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: API 단위 테스트 스위트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 프론트엔드 렌더링 smoke 테스트
- owner_role: QA Engineer
- objective: 프론트엔드 렌더링 smoke 테스트을(를) 구현한다.
- feature_slices: 프론트엔드 렌더링 smoke 테스트을(를) 구현한다.
- deliverables: 프론트엔드 렌더링 smoke 테스트
- depends_on: -
- tasks:
  - [scope] QA Engineer: 프론트엔드 렌더링 smoke 테스트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 프론트엔드 렌더링 smoke 테스트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: 프론트엔드 렌더링 smoke 테스트을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 프론트엔드 렌더링 smoke 테스트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: 프론트엔드 렌더링 smoke 테스트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 모바일 웹 설계 문서
- owner_role: Frontend Dev
- objective: 모바일 웹 설계 문서을(를) 구현한다.
- feature_slices: 모바일 웹 설계 문서을(를) 구현한다.
- deliverables: 모바일 웹 설계 문서
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 모바일 웹 설계 문서 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 모바일 웹 설계 문서 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 모바일 웹 설계 문서을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 모바일 웹 설계 문서의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 모바일 웹 설계 문서 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

## Execution Rules
- Each task should finish as a small, independent slice of work.
- Resolve dependencies using `depends_on` before parallelizing the next step.
- Define scope and file boundaries before implementation begins.
- Keep verification work as separate tasks instead of burying it inside build tasks.

## Handoff Rules
- Agents should communicate using task_id-scoped handoff, blocker, decision_request, decision_response, review_request, review_result, and result messages.
- Include relevant file paths and acceptance criteria in each handoff or review request.
- Every blocker should state what is blocked, why, and what decision or input is required.
- Each receiving agent should check the inbox and acknowledge required messages before starting work.
