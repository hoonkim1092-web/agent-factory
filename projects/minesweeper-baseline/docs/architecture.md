# 아키텍처

이 문서는 현재 아키텍처와 워크플로를 설명하는 살아 있는 기준 문서다.
설계, 워크플로, 인터페이스, 데이터 흐름, 구현 전략이 바뀌면 같은 작업 안에서 갱신한다.

## 메타데이터
- 마지막 업데이트: 2026-05-08T13:00:00
- 상태: active
- 문서 언어: 한국어 (OS: `ko-KR`)

## 현재 설계
- 요약:
  - Game Logic Dev 범위는 순수 게임 규칙 엔진으로 제한한다.
  - 게임 상태 전이와 승패 판정은 로직 모듈의 단일 책임으로 유지한다.
- 핵심 구성 요소:
  - `GameState`: 보드, 크기, 지뢰 수, 오픈 수, 게임 상태를 보유하는 루트 상태.
  - `Cell`: 지뢰 여부, 오픈 여부, 깃발 여부, 인접 지뢰 수를 보유.
  - 로직 함수: `createGame`, `openCell`, `toggleFlag`, `getGameStatus`, `getNeighborCoords`.
- 데이터 흐름:
  - 상위 모듈이 현재 `GameState`와 사용자 액션 좌표를 전달한다.
  - 로직 함수가 새로운 `GameState`를 반환한다.
  - 상위 모듈은 반환 상태를 렌더링/저장 계층으로 전달한다.
- 제약 사항:
  - UI 렌더링, 입력 파싱, 파일 I/O는 Game Logic Dev 범위에서 제외한다.
  - 좌표 검증과 mineCount 검증은 로직 모듈 내부에서 보장한다.
- 열린 질문:
  - 빈 셀 연쇄 오픈 구현에서 BFS와 DFS 중 기본 전략을 어떤 것으로 고정할지(성능/가독성 기준).

## Game Logic Dev 구현 범위
- 포함:
  - 보드 생성 및 지뢰 배치
  - 인접 지뢰 수 계산
  - 셀 오픈/깃발 토글 규칙
  - 빈 셀 연쇄 오픈
  - 승리/패배 판정
- 제외:
  - CLI/GUI 렌더링
  - 사용자 입력 처리
  - 저장/로드

## 의존성 및 산출물
- 선행 의존성:
  - 없음 (독립 구현 가능)
- 후행 의존성:
  - 호출 계층(프론트엔드/백엔드)은 본 인터페이스를 사용해 상태를 갱신해야 함
- 산출물:
  - 구현 범위/인터페이스/순서가 고정된 설계 문서
  - 아키텍처 기준 문서 및 변경 이력 갱신

## 구현 순서
1. 상태 모델(`GameState`, `Cell`, `Coord`)과 불변성 규칙 정의
2. 보드 생성, 지뢰 배치, 인접 지뢰 수 계산 구현
3. `openCell` 기본 동작 구현
4. 빈 셀 연쇄 오픈 구현
5. `toggleFlag` 및 예외 처리 구현
6. `getGameStatus` 중심 승패 판정 일원화
7. 경계값 검증 및 최소 테스트 기준 확정

## Product Designer 구현 범위

- 포함:
  - 보드 렌더링 포맷 (ASCII 레이아웃, 행/열 레이블 형식)
  - 셀 기호 사전 (미공개 `?`, 깃발 `F`, 숫자 `1`~`8`, 빈 셀 `.`, 지뢰 `*`)
  - 화면 흐름 명세 (게임 시작·턴 반복·승리·패배 상태별 출력 순서)
  - 사용자 대면 메시지 문자열 (한국어, 승리/패배/오류/안내/프롬프트)
  - 입력 프롬프트 포맷
- 제외:
  - Python 코드 구현 (Frontend Dev 담당)
  - 게임 로직 및 상태 전이 (Game Logic Dev 담당)
  - 단위 테스트 (QA Engineer 담당)
  - 서버/데이터/외부 연동 (Backend Dev 담당)

## Product Designer 인터페이스

- 입력:
  - `feature-spec.md` — FR-08(보드 렌더링), FR-09(입력 파싱), EX-01~EX-06(오류 처리), User Scenarios
  - `implementation-design.md` — Interface Impact, State And Data Model
- 출력:
  - `docs/designer/ui-spec.md` — 보드 포맷·셀 기호·메시지 문자열·화면 흐름·입력 프롬프트 명세
- 소비자:
  - Frontend Dev: `minesweeper.py` 출력 로직 구현 시 참조
  - QA Engineer: 수락 기준(AC-06, AC-07, AC-08) 검증 시 참조
- 계약:
  - `ui-spec.md` 변경 시 `change_history.md`에 기록하고 Frontend Dev에 통보한다.
  - 메시지 문자열은 반드시 한국어(OS: `ko-KR`)로 작성한다.

## Product Designer 구현 순서

1. 화면 흐름 정의 (게임 상태 전이별 출력 순서)
2. 보드 렌더링 포맷 명세 (행/열 레이블, 격자 구분 문자)
3. 셀 기호 사전 확정
4. 메시지 문자열 목록 작성 (한국어)
5. 입력 프롬프트 포맷 확정

## Backend Dev 구현 범위

### 담당 범위

Backend Dev는 **데이터 모델 레이어**를 전담한다.
CLI 지뢰찾기에는 서버·DB·외부 API가 없으므로,
Backend Dev 역할은 게임 상태를 표현하는 핵심 데이터 구조체와 보드 초기화 로직을 담당한다.

#### 구현 대상

| 번호 | 구현체 | 위치 | 설명 |
|------|--------|------|------|
| BD-01 | `GameState` | `minesweeper.py` 상단 | 게임 진행 상태 열거형 |
| BD-02 | `Cell` | `minesweeper.py` | 개별 셀 데이터 구조체 |
| BD-03 | `Board.__init__` | `minesweeper.py` | 보드 초기화 (빈 격자 생성만) |

> Game Logic Dev의 `GameState`, `Cell`, `Coord` 개념과 동일하다.
> 두 역할의 인터페이스가 충돌하지 않도록 아래 시그니처를 단일 기준으로 고정한다.

#### 제외 범위 (다른 역할 담당)

| 기능 | 담당 역할 |
|------|-----------|
| 지뢰 배치 (`place_mines`) | game_logic_dev |
| 인접 지뢰 수 계산 (`compute_adjacent`) | game_logic_dev |
| 셀 공개 로직 (`reveal_cell`) | game_logic_dev |
| 깃발 토글 (`toggle_flag`) | game_logic_dev |
| 승리/패배 판정 | game_logic_dev |
| CLI 진입점, 입력 파싱, 보드 렌더링 | frontend_dev |
| pytest 테스트 스위트 | qa_engineer |

### 공개 인터페이스 (Public API)

다른 역할이 의존하는 Backend Dev 산출물의 확정 시그니처.

#### `GameState` (enum.Enum)

```python
import enum

class GameState(enum.Enum):
    PLAYING = "playing"
    WIN     = "win"
    LOSE    = "lose"
```

#### `Cell` (dataclass)

```python
from dataclasses import dataclass

@dataclass
class Cell:
    is_mine:        bool = False
    adjacent_count: int  = 0
    is_revealed:    bool = False
    is_flagged:     bool = False
```

#### `Board.__init__`

```python
class Board:
    SIZE: int = 8

    def __init__(self, mine_count: int = 10, seed: int | None = None) -> None:
        self.mine_count: int = mine_count
        self.seed: int | None = seed
        self.state: GameState = GameState.PLAYING
        self.first_reveal_done: bool = False
        self.cells: list[list[Cell]] = [
            [Cell() for _ in range(self.SIZE)]
            for _ in range(self.SIZE)
        ]
```

- `Board.__init__`은 **빈 격자 초기화만** 수행한다. 지뢰 배치는 하지 않는다.
- `first_reveal_done`: game_logic_dev가 safe-first-click 구현 시 사용한다.
- `seed`: `random.seed()` 호출 전 보존용. 실제 호출은 game_logic_dev의 `place_mines`에서 한다.

### 의존성

#### 입력 의존성 (Backend Dev가 필요로 하는 것)

| 의존 대상 | 이유 |
|-----------|------|
| `enum` (stdlib) | `GameState` 열거형 정의 |
| `dataclasses` (stdlib) | `Cell` 데이터클래스 정의 |

외부 모듈 의존 없음. Backend Dev 레이어가 최하위 계층이다.

#### 출력 의존성 (Backend Dev 산출물을 사용하는 역할)

| 사용 역할 | 사용 대상 | 용도 |
|-----------|-----------|------|
| game_logic_dev | `Board`, `Cell`, `GameState` | 지뢰 배치, 공개 로직, 상태 전환 |
| frontend_dev | `Board`, `GameState` | 보드 렌더링, 게임 루프 |
| qa_engineer | `Board`, `Cell`, `GameState` | 단위 테스트 |

### 산출물

| 산출물 | 파일 경로 | 설명 |
|--------|-----------|------|
| `GameState` 열거형 | `minesweeper.py` 상단 | 게임 상태 3종 |
| `Cell` 데이터클래스 | `minesweeper.py` | 셀 상태 4개 필드 |
| `Board.__init__` 메서드 | `minesweeper.py` | 빈 8×8 격자 초기화 |

예상 코드량: 약 35~50 LOC

### 구현 순서

```
1단계 — GameState 열거형 정의
  검증: GameState.PLAYING / WIN / LOSE 값 접근 가능

2단계 — Cell 데이터클래스 정의
  검증: Cell() 생성 시 모든 필드가 기본값(False, 0)

3단계 — Board.__init__ 메서드 정의
  검증: Board(mine_count=10) 생성 시 8×8 Cell 격자 모두 기본값
         board.state == GameState.PLAYING
         board.first_reveal_done == False
```

각 단계는 독립 검증 가능하며, game_logic_dev와 frontend_dev는
3단계 완료 후 병렬로 진행 가능하다.

## 문서 규칙
- 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다.
- 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다.
- 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다.
- 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
