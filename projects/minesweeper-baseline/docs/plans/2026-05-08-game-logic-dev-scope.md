# Game Logic Dev Scope 설계 검토서

## 목적
`task_id=game_logic_dev_module_6_scope_1`의 scope 단계에서 Game Logic Dev의 구현 경계, 인터페이스 계약, 구현 순서를 고정한다.

## 설계 의도
- 게임 규칙의 단일 책임 영역을 `게임 상태 전이`와 `지뢰/인접 수 계산`으로 한정한다.
- UI, 입출력, 저장/로드, 점수 관리는 범위에서 제외한다.
- 상위 모듈이 일관된 방식으로 호출할 수 있도록 함수 단위 인터페이스를 명시한다.

## 영향 범위
- 포함:
  - 보드 초기화 규칙
  - 셀 열기/깃발 토글 규칙
  - 승패 판정 규칙
  - 연쇄 오픈(빈 셀 확장) 규칙
- 제외:
  - CLI/GUI 렌더링
  - 사용자 입력 파싱
  - 파일 I/O
  - 테스트 러너 구성

## 인터페이스 초안
- 데이터 타입
  - `Cell`: `{ isMine: boolean; isOpen: boolean; isFlagged: boolean; adjacentMines: number }`
  - `GameState`: `{ board: Cell[][]; width: number; height: number; mineCount: number; openedCount: number; status: 'ready' | 'playing' | 'won' | 'lost' }`
  - `Coord`: `{ x: number; y: number }`
- 함수 계약
  - `createGame(width, height, mineCount, firstClick?) -> GameState`
  - `openCell(state, coord) -> GameState`
  - `toggleFlag(state, coord) -> GameState`
  - `getGameStatus(state) -> 'ready' | 'playing' | 'won' | 'lost'`
  - `getNeighborCoords(state, coord) -> Coord[]`

## 의존성
- 선행 의존성
  - 없음 (순수 로직으로 독립 구현 가능)
- 후행 의존성
  - 프론트엔드/백엔드 모듈은 본 인터페이스를 통해서만 게임 상태를 갱신해야 한다.

## 산출물
- 본 문서(설계 의도 및 대안 검토)
- `docs/architecture.md`의 범위/인터페이스/구현 순서 섹션 갱신
- `docs/change_history.md` 이력 추가

## 구현 순서 고정
1. 상태 모델 및 불변성 규칙 정의 (`GameState`, `Cell`, `Coord`)
2. 보드 생성 및 지뢰 배치 + 인접 지뢰 수 계산
3. `openCell` 기본 동작(지뢰 클릭/일반 셀 클릭)
4. 빈 셀 연쇄 오픈(BFS/DFS) 적용
5. `toggleFlag` 및 오픈 셀 예외 처리
6. 승리/패배 판정 일원화 (`getGameStatus`)
7. 경계값 검증(좌표 범위, mineCount 유효성) 및 최소 단위 테스트 기준 확정

## 대안
- 대안 A: `class GameEngine` 단일 객체 인터페이스
- 대안 B(채택): 순수 함수 기반 인터페이스

채택 이유:
- 테스트 격리 용이
- 상태 직렬화/복원 단순
- UI 프레임워크 의존성 최소화

## 교차검증 요청 상태
- 현재 실행 환경에 `send_mailbox_message` 도구가 노출되지 않아 자동 요청 전송은 보류 상태다.
- 도구가 제공되면 `review_request` 타입으로 즉시 교차검증을 요청한다.
