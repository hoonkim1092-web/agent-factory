# Task Execution Plan

## Overview
- project_goal: search_all_backends() 함수에 memory_type과 scope 필터 파라미터를 추가하여 search_semantic()과 인터페이스를 통일하고, 회귀 테스트 2건으로 검증한다
- execution_strategy: parallel
- role_count: 3
- module_count: 5
- task_count: 15

## Evidence
- Workspace note: existing_todo=.todo.md
- Workspace note: existing_project_board=project_board_state.json
- Workspace note: existing_agents=8
- Local reference: docs/features/2026-04-24-unified-memory-facade-rag-extension.md -> ### 6.4 기존 `search_all_backends` 호출부 - 변경 없음. project_id 필터 없는 무차별 검색 유지 ---
- Local reference: docs/features/2026-04-24-unified-memory-facade-rag-extension-v3.md -> # scope=MemoryScope.GLOBAL if node.project_id is None else MemoryScope.LOCAL,
- Local reference: docs/features/2026-04-08-phased-skill-pipeline.md -> # 현재 (dynamic_orchestrator.py) def run_project(self, task_input, roles, workspace): ``` 슬라이스 필터 파라미터 추가: ```python

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
### scope 필터 파라미터 추가
- owner_role: Backend Dev
- objective: search_all_backends() memory_type/scope 필터 파라미터 추가을(를) 구현한다.
- feature_slices: search_all_backends() memory_type/scope 필터 파라미터 추가을(를) 구현한다.
- deliverables: search_all_backends() memory_type/scope 필터 파라미터 추가
- depends_on: -
- tasks:
  - [scope] Backend Dev: scope 필터 파라미터 추가 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: scope 필터 파라미터 추가 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: search_all_backends() memory_type/scope 필터 파라미터 추가을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: scope 필터 파라미터 추가의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: scope 필터 파라미터 추가 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### search_semantic과 동일한 필터 적용 로직
- owner_role: Backend Dev
- objective: search_semantic()과 동일한 필터 적용 로직을(를) 구현한다.
- feature_slices: search_semantic()과 동일한 필터 적용 로직을(를) 구현한다.
- deliverables: search_semantic()과 동일한 필터 적용 로직
- depends_on: -
- tasks:
  - [scope] Backend Dev: search_semantic과 동일한 필터 적용 로직 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: search_semantic과 동일한 필터 적용 로직 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: search_semantic()과 동일한 필터 적용 로직을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: search_semantic과 동일한 필터 적용 로직의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: search_semantic과 동일한 필터 적용 로직 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### memory_type 필터 회귀 테스트 1건
- owner_role: QA Engineer
- objective: memory_type 필터 회귀 테스트 1건을(를) 구현한다.
- feature_slices: memory_type 필터 회귀 테스트 1건을(를) 구현한다.
- deliverables: memory_type 필터 회귀 테스트 1건
- depends_on: -
- tasks:
  - [scope] QA Engineer: memory_type 필터 회귀 테스트 1건 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: memory_type 필터 회귀 테스트 1건 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: memory_type 필터 회귀 테스트 1건을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: memory_type 필터 회귀 테스트 1건의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: memory_type 필터 회귀 테스트 1건 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### scope 필터 회귀 테스트 1건
- owner_role: QA Engineer
- objective: scope 필터 회귀 테스트 1건을(를) 구현한다.
- feature_slices: scope 필터 회귀 테스트 1건을(를) 구현한다.
- deliverables: scope 필터 회귀 테스트 1건
- depends_on: -
- tasks:
  - [scope] QA Engineer: scope 필터 회귀 테스트 1건 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: scope 필터 회귀 테스트 1건 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: scope 필터 회귀 테스트 1건을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: scope 필터 회귀 테스트 1건의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: scope 필터 회귀 테스트 1건 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### Game Logic Dev 구현
- owner_role: Game Logic Dev
- objective: 핵심 규칙과 상태 전이를 구현한다.
- feature_slices: 핵심 규칙과 상태 전이를 구현한다.
- deliverables: search_all_backends() memory_type/scope 필터 파라미터 추가
- depends_on: -
- tasks:
  - [scope] Game Logic Dev: Game Logic Dev 구현 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: Game Logic Dev 구현 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Game Logic Dev: 핵심 규칙과 상태 전이를 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: Game Logic Dev 구현의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Game Logic Dev: Game Logic Dev 구현 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
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
