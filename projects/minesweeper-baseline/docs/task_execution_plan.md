# Task Execution Plan

## Overview
- project_goal: Build a playable 8x8 CLI minesweeper game where the player can reveal cells and flag mines.
- execution_strategy: parallel
- role_count: 5
- module_count: 7
- task_count: 21

## Evidence
- Local reference: docs/2026-05-08-work-item-parallel-measurement-handoff.md -> # 방법 A: 직접 실행 python3 run_factory_cli.py --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa
- Local reference: docs/2026-05-08-work-item-parallel-measurement-handoff.md -> # 방법 B: af CLI alias (설치된 경우) af --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa ``` > **주의**: `--brief`, `--target-path` 플래그는 존재하지 않음. 파서 파라미터: `--task/-t`, `--project/-p`, `--mode`, `--pipeline` 등 (`run_factory_cli.py:55...
- Local reference: docs/codex/2026-05-08-af-productization-application-guide.md -> ### 권장 강제 매핑 - Rule Engine -> Game Logic Dev - Realtime Server/WebSocket -> Backend Dev - UI/화면/입력 -> Frontend Dev - 테스트/회귀/품질게이트 -> QA Engineer

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
### 8x8 지뢰찾기 CLI 실행 파일
- owner_role: Frontend Dev
- objective: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)을(를) 구현한다.
- feature_slices: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)을(를) 구현한다.
- deliverables: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 8x8 지뢰찾기 CLI 실행 파일 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 8x8 지뢰찾기 CLI 실행 파일 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 8x8 지뢰찾기 CLI 실행 파일의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 8x8 지뢰찾기 CLI 실행 파일 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 지뢰 배치 및 셀 공개 게임 로직 모듈
- owner_role: Frontend Dev
- objective: 지뢰 배치 및 셀 공개 게임 로직 모듈을(를) 구현한다.
- feature_slices: 지뢰 배치 및 셀 공개 게임 로직 모듈을(를) 구현한다.
- deliverables: 지뢰 배치 및 셀 공개 게임 로직 모듈
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 지뢰 배치 및 셀 공개 게임 로직 모듈 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 지뢰 배치 및 셀 공개 게임 로직 모듈 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 지뢰 배치 및 셀 공개 게임 로직 모듈을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 지뢰 배치 및 셀 공개 게임 로직 모듈의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 지뢰 배치 및 셀 공개 게임 로직 모듈 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 패배 판정 및 보드 렌더링 출력
- owner_role: Frontend Dev
- objective: 승리/패배 판정 및 보드 렌더링 출력을(를) 구현한다.
- feature_slices: 승리/패배 판정 및 보드 렌더링 출력을(를) 구현한다.
- deliverables: 승리/패배 판정 및 보드 렌더링 출력
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 패배 판정 및 보드 렌더링 출력 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 패배 판정 및 보드 렌더링 출력 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 승리/패배 판정 및 보드 렌더링 출력을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 패배 판정 및 보드 렌더링 출력의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 패배 판정 및 보드 렌더링 출력 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### 단위 테스트 스위트
- owner_role: QA Engineer
- objective: 단위 테스트 스위트 (pytest)을(를) 구현한다.
- feature_slices: 단위 테스트 스위트 (pytest)을(를) 구현한다.
- deliverables: 단위 테스트 스위트 (pytest)
- depends_on: -
- tasks:
  - [scope] QA Engineer: 단위 테스트 스위트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 단위 테스트 스위트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: 단위 테스트 스위트 (pytest)을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 단위 테스트 스위트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: 단위 테스트 스위트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### Backend Dev 구현
- owner_role: Backend Dev
- objective: 서버, 데이터, 외부 연동 레이어를 구현한다.
- feature_slices: 서버, 데이터, 외부 연동 레이어를 구현한다.
- deliverables: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)
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
- deliverables: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)
- depends_on: -
- tasks:
  - [scope] Game Logic Dev: Game Logic Dev 구현 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: Game Logic Dev 구현 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Game Logic Dev: 핵심 규칙과 상태 전이를 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: Game Logic Dev 구현의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Game Logic Dev: Game Logic Dev 구현 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다.

### Product Designer 구현
- owner_role: Product Designer
- objective: 정보 구조와 화면 흐름, 비주얼 방향을 설계한다.
- feature_slices: 정보 구조와 화면 흐름, 비주얼 방향을 설계한다.
- deliverables: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)
- depends_on: -
- tasks:
  - [scope] Product Designer: Product Designer 구현 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: Product Designer 구현 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Product Designer: 정보 구조와 화면 흐름, 비주얼 방향을 설계한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: Product Designer 구현의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Product Designer: Product Designer 구현 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
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
