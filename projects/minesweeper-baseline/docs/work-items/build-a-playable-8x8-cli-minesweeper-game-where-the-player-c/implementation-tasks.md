# Implementation Tasks

## Metadata

- work_item: build-a-playable-8x8-cli-minesweeper-game-where-the-player-c
- source_design: implementation-design.md
- status: draft
- last_updated: 2026-05-08T11:17:37

## Preconditions

- 범위와 계약 정의
- 기능 슬라이스 구현
- 통합과 핸드오프
- 검증과 마감

## Task Evidence

- Local reference: docs/2026-05-08-work-item-parallel-measurement-handoff.md -> # 방법 A: 직접 실행 python3 run_factory_cli.py --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa
- Local reference: docs/2026-05-08-work-item-parallel-measurement-handoff.md -> # 방법 B: af CLI alias (설치된 경우) af --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa ``` > **주의**: `--brief`, `--target-path` 플래그는 존재하지 않음. 파서 파라미터: `--task/-t`, `--project/-p`, `--mode`, `--pipeline` 등 (`run_factory_cli.py:55...
- Local reference: docs/codex/2026-05-08-af-productization-application-guide.md -> ### 권장 강제 매핑 - Rule Engine -> Game Logic Dev - Realtime Server/WebSocket -> Backend Dev - UI/화면/입력 -> Frontend Dev - 테스트/회귀/품질게이트 -> QA Engineer

## Task List

- [ ] Backend Dev: Backend Dev 구현 범위와 인터페이스를 정의한다.
  - task_id: backend_dev_module_5_scope_1
  - owner_role: backend_dev
  - phase: scope
  - acceptance: Backend Dev 구현 범위가 명확히 정리된다.; 의존성과 산출물이 명시된다.
  - e2e_command: (needs_backfill)

- [ ] Product Designer: Product Designer 구현 범위와 인터페이스를 정의한다.
  - task_id: designer_module_7_scope_1
  - owner_role: designer
  - phase: scope
  - acceptance: Product Designer 구현 범위가 명확히 정리된다.; 의존성과 산출물이 명시된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 8x8 지뢰찾기 CLI 실행 파일 범위와 인터페이스를 정의한다.
  - task_id: frontend_dev_module_1_scope_1
  - owner_role: frontend_dev
  - phase: scope
  - acceptance: 8x8 지뢰찾기 CLI 실행 파일 범위가 명확히 정리된다.; 의존성과 산출물이 명시된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 지뢰 배치 및 셀 공개 게임 로직 모듈 범위와 인터페이스를 정의한다.
  - task_id: frontend_dev_module_2_scope_1
  - owner_role: frontend_dev
  - phase: scope
  - acceptance: 지뢰 배치 및 셀 공개 게임 로직 모듈 범위가 명확히 정리된다.; 의존성과 산출물이 명시된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 패배 판정 및 보드 렌더링 출력 범위와 인터페이스를 정의한다.
  - task_id: frontend_dev_module_3_scope_1
  - owner_role: frontend_dev
  - phase: scope
  - acceptance: 패배 판정 및 보드 렌더링 출력 범위가 명확히 정리된다.; 의존성과 산출물이 명시된다.
  - e2e_command: (needs_backfill)

- [ ] Game Logic Dev: Game Logic Dev 구현 범위와 인터페이스를 정의한다.
  - task_id: game_logic_dev_module_6_scope_1
  - owner_role: game_logic_dev
  - phase: scope
  - acceptance: Game Logic Dev 구현 범위가 명확히 정리된다.; 의존성과 산출물이 명시된다.
  - e2e_command: (needs_backfill)

- [ ] QA Engineer: 단위 테스트 스위트 범위와 인터페이스를 정의한다.
  - task_id: qa_engineer_module_4_scope_1
  - owner_role: qa_engineer
  - phase: scope
  - acceptance: 단위 테스트 스위트 범위가 명확히 정리된다.; 의존성과 산출물이 명시된다.
  - e2e_command: (needs_backfill)

- [ ] Backend Dev: Backend Dev 구현 기능을 구현한다.
  - task_id: backend_dev_module_5_build_2
  - owner_role: backend_dev
  - phase: build
  - depends_on: backend_dev_module_5_scope_1
  - acceptance: Backend Dev 구현의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다.
  - e2e_command: (needs_backfill)

- [ ] Product Designer: Product Designer 구현 기능을 구현한다.
  - task_id: designer_module_7_build_2
  - owner_role: designer
  - phase: build
  - depends_on: designer_module_7_scope_1
  - acceptance: Product Designer 구현의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 8x8 지뢰찾기 CLI 실행 파일 기능을 구현한다.
  - task_id: frontend_dev_module_1_build_2
  - owner_role: frontend_dev
  - phase: build
  - depends_on: frontend_dev_module_1_scope_1
  - acceptance: 8x8 지뢰찾기 CLI 실행 파일의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 지뢰 배치 및 셀 공개 게임 로직 모듈 기능을 구현한다.
  - task_id: frontend_dev_module_2_build_2
  - owner_role: frontend_dev
  - phase: build
  - depends_on: frontend_dev_module_2_scope_1
  - acceptance: 지뢰 배치 및 셀 공개 게임 로직 모듈의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 패배 판정 및 보드 렌더링 출력 기능을 구현한다.
  - task_id: frontend_dev_module_3_build_2
  - owner_role: frontend_dev
  - phase: build
  - depends_on: frontend_dev_module_3_scope_1
  - acceptance: 패배 판정 및 보드 렌더링 출력의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다.
  - e2e_command: (needs_backfill)

- [ ] Game Logic Dev: Game Logic Dev 구현 기능을 구현한다.
  - task_id: game_logic_dev_module_6_build_2
  - owner_role: game_logic_dev
  - phase: build
  - depends_on: game_logic_dev_module_6_scope_1
  - acceptance: Game Logic Dev 구현의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다.
  - e2e_command: (needs_backfill)

- [ ] QA Engineer: 단위 테스트 스위트 기능을 구현한다.
  - task_id: qa_engineer_module_4_build_2
  - owner_role: qa_engineer
  - phase: build
  - depends_on: qa_engineer_module_4_scope_1
  - acceptance: 단위 테스트 스위트의 핵심 기능이 구현된다.; 관련 파일과 산출물이 갱신된다.
  - e2e_command: (needs_backfill)

- [ ] Backend Dev: Backend Dev 구현 결과를 검증하고 handoff를 남긴다.
  - task_id: backend_dev_module_5_verify_3
  - owner_role: backend_dev
  - phase: verify
  - depends_on: backend_dev_module_5_build_2
  - acceptance: 검증 결과가 정리된다.; 잔여 리스크와 후속 작업이 기록된다.
  - e2e_command: (needs_backfill)

- [ ] Product Designer: Product Designer 구현 결과를 검증하고 handoff를 남긴다.
  - task_id: designer_module_7_verify_3
  - owner_role: designer
  - phase: verify
  - depends_on: designer_module_7_build_2
  - acceptance: 검증 결과가 정리된다.; 잔여 리스크와 후속 작업이 기록된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 8x8 지뢰찾기 CLI 실행 파일 결과를 검증하고 handoff를 남긴다.
  - task_id: frontend_dev_module_1_verify_3
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: frontend_dev_module_1_build_2
  - acceptance: 검증 결과가 정리된다.; 잔여 리스크와 후속 작업이 기록된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 지뢰 배치 및 셀 공개 게임 로직 모듈 결과를 검증하고 handoff를 남긴다.
  - task_id: frontend_dev_module_2_verify_3
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: frontend_dev_module_2_build_2
  - acceptance: 검증 결과가 정리된다.; 잔여 리스크와 후속 작업이 기록된다.
  - e2e_command: (needs_backfill)

- [ ] Frontend Dev: 패배 판정 및 보드 렌더링 출력 결과를 검증하고 handoff를 남긴다.
  - task_id: frontend_dev_module_3_verify_3
  - owner_role: frontend_dev
  - phase: verify
  - depends_on: frontend_dev_module_3_build_2
  - acceptance: 검증 결과가 정리된다.; 잔여 리스크와 후속 작업이 기록된다.
  - e2e_command: (needs_backfill)

- [ ] Game Logic Dev: Game Logic Dev 구현 결과를 검증하고 handoff를 남긴다.
  - task_id: game_logic_dev_module_6_verify_3
  - owner_role: game_logic_dev
  - phase: verify
  - depends_on: game_logic_dev_module_6_build_2
  - acceptance: 검증 결과가 정리된다.; 잔여 리스크와 후속 작업이 기록된다.
  - e2e_command: (needs_backfill)

- [ ] QA Engineer: 단위 테스트 스위트 결과를 검증하고 handoff를 남긴다.
  - task_id: qa_engineer_module_4_verify_3
  - owner_role: qa_engineer
  - phase: verify
  - depends_on: qa_engineer_module_4_build_2
  - acceptance: 검증 결과가 정리된다.; 잔여 리스크와 후속 작업이 기록된다.
  - e2e_command: (needs_backfill)

## Blockers

- none

## Rollback Sign-Off

- Commit after each module-level implementation milestone

## Definition Of Done

- All task checkboxes are complete
- verification-report.md 작성 완료 (`templates/verify-handoff.md.tpl` 참고)
  - `e2e_command:` 필드에 실행 명령어 기재
  - `- verdict:` 필드에 PASS/WARN/BLOCK 기재
