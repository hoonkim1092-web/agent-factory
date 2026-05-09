# Task Execution Plan

## Overview
- project_goal: 동행복권 API에서 최근 500회차 로또 당첨번호를 수집·통계 분석하여 가중 랜덤 기반 1등 후보 5조합을 추천하는 macOS CLI 도구를 개발한다.
- execution_strategy: parallel
- role_count: 2
- module_count: 7
- task_count: 21

## Evidence
- LLM prior knowledge (unverified): HTTP GET to the 동행복권 (dhlottery.co.kr) public API endpoint that returns winning numbers by draw round as JSON
- LLM prior knowledge (unverified): Frequency analysis of individual numbers and pair/triplet co-occurrence across historical draws
- NotebookLM synthesis: Conversation ID: a6e109cb-b12e-4120-97e8-aabdbafb2b3e Use --conversation-id for follow-up questions
- NotebookLM: Conversation ID: a6e109cb-b12e-4120-97e8-aabdbafb2b3e Use --conversation-id for follow-up questions

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
### 동행복권 API 데이터 수집 모듈
- owner_role: Backend Dev
- objective: 동행복권 API 데이터 수집 모듈을(를) 구현한다.
- feature_slices: 동행복권 API 데이터 수집 모듈을(를) 구현한다.
- deliverables: 동행복권 API 데이터 수집 모듈
- depends_on: -
- tasks:
  - [scope] Backend Dev: 동행복권 API 데이터 수집 모듈 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 동행복권 API 데이터 수집 모듈 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: 동행복권 API 데이터 수집 모듈을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 동행복권 API 데이터 수집 모듈의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: 동행복권 API 데이터 수집 모듈 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### SQLite 기반 당첨번호 캐시 저장소
- owner_role: Backend Dev
- objective: SQLite 기반 당첨번호 캐시 저장소을(를) 구현한다.
- feature_slices: SQLite 기반 당첨번호 캐시 저장소을(를) 구현한다.
- deliverables: SQLite 기반 당첨번호 캐시 저장소
- depends_on: -
- tasks:
  - [scope] Backend Dev: SQLite 기반 당첨번호 캐시 저장소 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: SQLite 기반 당첨번호 캐시 저장소 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: SQLite 기반 당첨번호 캐시 저장소을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: SQLite 기반 당첨번호 캐시 저장소의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: SQLite 기반 당첨번호 캐시 저장소 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 번호별 출현빈도·동시출현·구간 통계 분석 엔진
- owner_role: Backend Dev
- objective: 번호별 출현빈도·동시출현·구간 통계 분석 엔진을(를) 구현한다.
- feature_slices: 번호별 출현빈도·동시출현·구간 통계 분석 엔진을(를) 구현한다.
- deliverables: 번호별 출현빈도·동시출현·구간 통계 분석 엔진
- depends_on: -
- tasks:
  - [scope] Backend Dev: 번호별 출현빈도·동시출현·구간 통계 분석 엔진 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 번호별 출현빈도·동시출현·구간 통계 분석 엔진 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: 번호별 출현빈도·동시출현·구간 통계 분석 엔진을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 번호별 출현빈도·동시출현·구간 통계 분석 엔진의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: 번호별 출현빈도·동시출현·구간 통계 분석 엔진 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 가중 랜덤 기반 5조합 추천 생성기
- owner_role: Backend Dev
- objective: 가중 랜덤 기반 5조합 추천 생성기을(를) 구현한다.
- feature_slices: 가중 랜덤 기반 5조합 추천 생성기을(를) 구현한다.
- deliverables: 가중 랜덤 기반 5조합 추천 생성기
- depends_on: -
- tasks:
  - [scope] Backend Dev: 가중 랜덤 기반 5조합 추천 생성기 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 가중 랜덤 기반 5조합 추천 생성기 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: 가중 랜덤 기반 5조합 추천 생성기을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 가중 랜덤 기반 5조합 추천 생성기의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: 가중 랜덤 기반 5조합 추천 생성기 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 터미널 통계 요약 출력 포맷터
- owner_role: Backend Dev
- objective: 터미널 통계 요약 출력 포맷터을(를) 구현한다.
- feature_slices: 터미널 통계 요약 출력 포맷터을(를) 구현한다.
- deliverables: 터미널 통계 요약 출력 포맷터
- depends_on: -
- tasks:
  - [scope] Backend Dev: 터미널 통계 요약 출력 포맷터 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 터미널 통계 요약 출력 포맷터 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: 터미널 통계 요약 출력 포맷터을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 터미널 통계 요약 출력 포맷터의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: 터미널 통계 요약 출력 포맷터 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### CLI 엔트리포인트
- owner_role: Backend Dev
- objective: CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)을(를) 구현한다.
- feature_slices: CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)을(를) 구현한다.
- deliverables: CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)
- depends_on: -
- tasks:
  - [scope] Backend Dev: CLI 엔트리포인트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: CLI 엔트리포인트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: CLI 엔트리포인트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: CLI 엔트리포인트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### QA Engineer 검증
- owner_role: QA Engineer
- objective: 핵심 플로우와 회귀 시나리오를 검증한다.
- feature_slices: 핵심 플로우와 회귀 시나리오를 검증한다.
- deliverables: 동행복권 API 데이터 수집 모듈
- depends_on: -
- tasks:
  - [scope] QA Engineer: QA Engineer 검증 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: QA Engineer 검증 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: 핵심 플로우와 회귀 시나리오를 검증한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: QA Engineer 검증의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: QA Engineer 검증 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
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
