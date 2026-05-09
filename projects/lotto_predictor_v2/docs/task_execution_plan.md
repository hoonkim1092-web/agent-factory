# Task Execution Plan

## Overview
- project_goal: 한국 로또 6/45 최근 500회차 1등 당첨번호를 동행복권 API에서 수집·통계 분석하여 패턴 기반 1등 번호 5개 조합을 추천하고 PyInstaller로 더블클릭 실행 가능한 단일 실행 파일로 배포하는 데스크톱 도구를 구축한다.
- execution_strategy: parallel
- role_count: 4
- module_count: 10
- task_count: 30

## Evidence
- Local reference: docs/architecture.md -> ## 문서 규칙 - 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다. - 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다. - 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다. - 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
- LLM prior knowledge (unverified): Frequency analysis of historical draws to identify hot and cold numbers
- LLM prior knowledge (unverified): Combinatorial filtering (odd/even ratio, low/high split, sum range, consecutive runs)
- NotebookLM synthesis: Conversation ID: d68298d4-d15b-4e78-9caf-c342f528fc0c Use --conversation-id for follow-up questions
- NotebookLM: Conversation ID: d68298d4-d15b-4e78-9caf-c342f528fc0c Use --conversation-id for follow-up questions

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
### 동행복권 회차 수집기 모듈
- owner_role: Frontend Dev
- objective: 동행복권 회차 수집기 모듈을(를) 구현한다.
- feature_slices: 동행복권 회차 수집기 모듈을(를) 구현한다.
- deliverables: 동행복권 회차 수집기 모듈
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 동행복권 회차 수집기 모듈 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 동행복권 회차 수집기 모듈 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 동행복권 회차 수집기 모듈을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 동행복권 회차 수집기 모듈의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 동행복권 회차 수집기 모듈 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 회차 데이터 로컬 캐시 저장소
- owner_role: Frontend Dev
- objective: 회차 데이터 로컬 캐시 저장소을(를) 구현한다.
- feature_slices: 회차 데이터 로컬 캐시 저장소을(를) 구현한다.
- deliverables: 회차 데이터 로컬 캐시 저장소
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 회차 데이터 로컬 캐시 저장소 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 회차 데이터 로컬 캐시 저장소 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 회차 데이터 로컬 캐시 저장소을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 회차 데이터 로컬 캐시 저장소의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 회차 데이터 로컬 캐시 저장소 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 통계 분석 엔진
- owner_role: Frontend Dev
- objective: 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)을(를) 구현한다.
- feature_slices: 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)을(를) 구현한다.
- deliverables: 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 통계 분석 엔진 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 통계 분석 엔진 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 통계 분석 엔진의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 통계 분석 엔진 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 패턴 기반 번호 조합 추천기
- owner_role: Frontend Dev
- objective: 패턴 기반 번호 조합 추천기을(를) 구현한다.
- feature_slices: 패턴 기반 번호 조합 추천기을(를) 구현한다.
- deliverables: 패턴 기반 번호 조합 추천기
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 패턴 기반 번호 조합 추천기 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 패턴 기반 번호 조합 추천기 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 패턴 기반 번호 조합 추천기을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 패턴 기반 번호 조합 추천기의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 패턴 기반 번호 조합 추천기 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 터미널 포맷 출력 리포트
- owner_role: Frontend Dev
- objective: 터미널 포맷 출력 리포트을(를) 구현한다.
- feature_slices: 터미널 포맷 출력 리포트을(를) 구현한다.
- deliverables: 터미널 포맷 출력 리포트
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 터미널 포맷 출력 리포트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 터미널 포맷 출력 리포트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 터미널 포맷 출력 리포트을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 터미널 포맷 출력 리포트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 터미널 포맷 출력 리포트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### PyInstaller 빌드 스펙 및 산출물
- owner_role: Frontend Dev
- objective: PyInstaller 빌드 스펙 및 산출물을(를) 구현한다.
- feature_slices: PyInstaller 빌드 스펙 및 산출물을(를) 구현한다.
- deliverables: PyInstaller 빌드 스펙 및 산출물
- depends_on: -
- tasks:
  - [scope] Frontend Dev: PyInstaller 빌드 스펙 및 산출물 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: PyInstaller 빌드 스펙 및 산출물 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: PyInstaller 빌드 스펙 및 산출물을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: PyInstaller 빌드 스펙 및 산출물의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: PyInstaller 빌드 스펙 및 산출물 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 사용자 실행 가이드 문서
- owner_role: Frontend Dev
- objective: 사용자 실행 가이드 문서을(를) 구현한다.
- feature_slices: 사용자 실행 가이드 문서을(를) 구현한다.
- deliverables: 사용자 실행 가이드 문서
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 사용자 실행 가이드 문서 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 사용자 실행 가이드 문서 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 사용자 실행 가이드 문서을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 사용자 실행 가이드 문서의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 사용자 실행 가이드 문서 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### Backend Dev 구현
- owner_role: Backend Dev
- objective: 서버, 데이터, 외부 연동 레이어를 구현한다.
- feature_slices: 서버, 데이터, 외부 연동 레이어를 구현한다.
- deliverables: 동행복권 회차 수집기 모듈
- depends_on: -
- tasks:
  - [scope] Backend Dev: Backend Dev 구현 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: Backend Dev 구현 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: 서버, 데이터, 외부 연동 레이어를 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: Backend Dev 구현의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: Backend Dev 구현 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### Game Logic Dev 구현
- owner_role: Game Logic Dev
- objective: 핵심 규칙과 상태 전이를 구현한다.
- feature_slices: 핵심 규칙과 상태 전이를 구현한다.
- deliverables: 동행복권 회차 수집기 모듈
- depends_on: -
- tasks:
  - [scope] Game Logic Dev: Game Logic Dev 구현 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: Game Logic Dev 구현 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Game Logic Dev: 핵심 규칙과 상태 전이를 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: Game Logic Dev 구현의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Game Logic Dev: Game Logic Dev 구현 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### QA Engineer 검증
- owner_role: QA Engineer
- objective: 핵심 플로우와 회귀 시나리오를 검증한다.
- feature_slices: 핵심 플로우와 회귀 시나리오를 검증한다.
- deliverables: `verification-report.md`, 검증 실행 기록, 회귀 시나리오 목록, handoff 메모
- depends_on: `frontend_dev_module_1_build_2`, `frontend_dev_module_2_build_2`, `frontend_dev_module_3_build_2`, `frontend_dev_module_4_build_2`, `frontend_dev_module_5_build_2`, `frontend_dev_module_6_build_2`, `frontend_dev_module_7_build_2`, `backend_dev_module_8_build_2`, `game_logic_dev_module_9_build_2`
- interface:
  - 입력: 모듈 진입점, 빌드 산출물 경로, 사용자 가이드 문서, 재현 파라미터(`seed`, 회차 범위)
  - 출력: 검증 결과 문서, 실패/회귀 목록, handoff 메모
- execution_order:
  - 1. 수집기 및 캐시 smoke 검증
  - 2. 분석 엔진 결과 검증
  - 3. 추천기 재현성 검증
  - 4. 터미널 리포트 형식 검증
  - 5. PyInstaller 산출물 및 사용자 가이드 검증
  - 6. 통합 회귀 시나리오 실행 및 결과 정리
- tasks:
  - [scope] QA Engineer: QA Engineer 검증 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: QA Engineer 검증 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: 핵심 플로우와 회귀 시나리오를 검증한다. 기능을 작은 슬라이스로 나눠 구현한다.
    depends_on: `qa_engineer_module_10_scope_1`, `frontend_dev_module_1_build_2`, `frontend_dev_module_2_build_2`, `frontend_dev_module_3_build_2`, `frontend_dev_module_4_build_2`, `frontend_dev_module_5_build_2`, `frontend_dev_module_6_build_2`, `frontend_dev_module_7_build_2`, `backend_dev_module_8_build_2`, `game_logic_dev_module_9_build_2`
    acceptance: QA Engineer 검증의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: QA Engineer 검증 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    depends_on: `qa_engineer_module_10_build_2`
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
