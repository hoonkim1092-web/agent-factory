# QA 단위 테스트 스위트 범위 정의

## 메타데이터
- task_id: qa_engineer_module_4_scope_1
- 작성일: 2026-05-08
- 대상 모듈: 단위 테스트 스위트 (`pytest`)
- 상태: 확정

## 목표
8x8 CLI 지뢰찾기의 핵심 규칙과 입출력 계약을 단위 테스트로 검증할 수 있도록 테스트 스위트의 범위와 인터페이스를 고정한다.

## 테스트 범위
- 포함:
  - 보드 초기화 규칙 검증 (크기 8x8, 지뢰 수 유효성)
  - 첫 클릭 안전 보장 규칙 검증
  - 셀 공개/연쇄 공개 규칙 검증
  - 깃발 토글 규칙 검증
  - 승리/패배 상태 전이 검증
  - 보드 렌더링 문자열 포맷 검증
  - 명령 파싱(`r row col`, `f row col`) 유효/무효 입력 처리 검증
- 제외:
  - 실제 터미널 상호작용 E2E 테스트
  - 성능/부하 테스트
  - 외부 시스템 연동 테스트 (해당 없음)

## 테스트 인터페이스 계약
- 테스트 프레임워크: `pytest`
- 실행 명령:
  - 전체: `pytest -q`
  - 모듈 단위: `pytest -q tests/test_minesweeper_unit.py`
- 테스트 대상 공개 인터페이스(예정):
  - `create_board(size: int = 8, mine_count: int = 10) -> Board`
  - `place_mines(board: Board, first_click: tuple[int, int]) -> None`
  - `reveal_cell(board: Board, row: int, col: int) -> None`
  - `toggle_flag(board: Board, row: int, col: int) -> None`
  - `check_game_state(board: Board) -> str`
  - `render_board(board: Board, reveal_all: bool = False) -> str`
  - `parse_command(raw: str) -> tuple[str, int, int]`
- 인터페이스 원칙:
  - 테스트는 표준입출력 대신 함수 호출 기반으로 검증한다.
  - 난수 의존 로직은 시드 고정 또는 배치 함수 분리로 결정론적으로 검증한다.

## 의존성
- 선행 구현 의존성:
  - `frontend_dev_module_2_build_2` (지뢰 배치 및 셀 공개 게임 로직)
  - `frontend_dev_module_3_build_2` (승리/패배 판정 및 렌더링)
- 도구 의존성:
  - Python 3.11+
  - `pytest 7.x`

## 산출물
- 테스트 코드: `tests/test_minesweeper_unit.py`
- 테스트 데이터/fixture (필요 시): `tests/fixtures/*.json` 또는 `tests/conftest.py`
- 검증 기록 연계: `docs/work-items/build-a-playable-8x8-cli-minesweeper-game-where-the-player-c/verification-report.md`

## 구현 순서(고정)
1. 테스트 파일/기본 fixture 골격 생성
2. 보드 초기화/지뢰 수/입력 파싱 테스트 작성
3. 첫 클릭 안전 보장 및 지뢰 배치 테스트 작성
4. 셀 공개/연쇄 공개 테스트 작성
5. 깃발 토글 및 상태 전이(승리/패배) 테스트 작성
6. 렌더링 문자열 포맷 테스트 작성
7. 전체 테스트 실행 및 실패 케이스를 기준으로 보완 포인트 기록

## 완료 판정 기준
- 본 문서 기준으로 테스트 범위와 제외 범위가 모호성 없이 구분되어야 한다.
- 테스트 대상 인터페이스가 함수 시그니처 수준으로 명시되어야 한다.
- 의존성과 산출물이 파일 경로 기준으로 식별 가능해야 한다.
- 구현 순서가 번호 목록으로 고정되어야 한다.
