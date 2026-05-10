# Feature Spec

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| source_plan | Feature Plan (2026-05-08) |
| status | draft |
| last_updated | 2026-05-09 |

---

## Feature Overview

Python 3.11 표준 라이브러리만으로 동작하는 8×8 지뢰찾기 CLI 게임이다. 플레이어는 단일 터미널 세션에서 셀을 공개하거나 깃발을 꽂아 지뢰를 피하며, 지뢰 외 모든 셀을 공개하면 승리한다. 지뢰 수는 실행 시 인자로 지정하며 기본값은 10이다.

본 구현은 Agent Factory의 work-item 병렬 측정 파이프라인(plan → spec → work-items → design)에서 FSA 문서 생성 처리량을 비교하기 위한 결정론적 베이스라인 태스크로 사용된다. 이전 베이스라인인 포커 게임은 웹 서버 의존성으로 인해 순수 CLI 환경에서 실행하기 어려웠으며, 지뢰찾기가 그 경량 대체재로 선정되었다.

**핵심 모듈 구성**

| 모듈 | 담당 역할 | 산출물 |
|------|-----------|--------|
| CLI 진입점 및 입력 파싱 | Frontend Dev | `minesweeper.py` |
| 게임 로직 (지뢰 배치·인접 카운트·재귀 공개·승패 판정) | Game Logic Dev | `minesweeper.py` 내 `Board` 클래스 |
| 보드 ASCII 렌더링 | Frontend Dev | `minesweeper.py` |
| 단위 테스트 스위트 | QA Engineer | `test_minesweeper.py` |

---

## User Scenarios

### 시나리오 1 — 정상 게임 시작 및 첫 셀 공개

1. 사용자가 `python3 minesweeper.py` 또는 `python3 minesweeper.py --mines 15`를 실행한다.
2. 시스템이 8×8 빈 보드를 ASCII로 출력하고 좌표 입력 프롬프트를 표시한다.
3. 사용자가 `3 4`를 입력한다.
4. 시스템이 해당 셀을 공개하고 갱신된 보드를 출력한다. 인접 지뢰가 없으면 연쇄 공개가 일어난다.
5. 첫 번째 입력 좌표에는 지뢰가 배치되지 않는다(safe-first-click 보장).

### 시나리오 2 — 깃발 토글

1. 사용자가 `f 2 5`를 입력한다.
2. 시스템이 (2, 5) 셀에 깃발 기호(`F`)를 표시한다.
3. 같은 명령을 다시 입력하면 깃발이 제거된다.
4. 깃발이 꽂힌 셀은 공개 명령으로 공개되지 않는다.

### 시나리오 3 — 지뢰 셀 공개 (패배)

1. 사용자가 지뢰가 있는 좌표를 공개한다.
2. 시스템이 게임 오버 메시지를 출력하고 모든 지뢰 위치를 보드에 표시한다.
3. 프로그램이 종료된다.

### 시나리오 4 — 모든 비지뢰 셀 공개 (승리)

1. 사용자가 지뢰 외 모든 셀을 공개한다.
2. 시스템이 승리 메시지를 출력한다.
3. 프로그램이 종료된다.

### 시나리오 5 — 잘못된 입력 처리

1. 사용자가 범위를 벗어난 좌표(`9 0`, `-1 3`)나 형식 오류(`abc`) 입력을 한다.
2. 시스템이 오류 메시지를 출력하고 재입력 프롬프트를 표시한다.
3. 게임 상태는 변경되지 않는다.

---

## Functional Requirements

### FR-1 보드 초기화

- 8×8 (고정) 셀 배열을 생성한다. 크기 변경은 지원하지 않는다.
- 모든 셀의 초기 상태는 `HIDDEN`이다.
- `game_state`의 초기값은 `PLAYING`이다.

### FR-2 지뢰 배치

- 첫 번째 공개 명령이 실행될 때 `random.sample`로 지뢰 위치를 결정한다.
- 첫 클릭 좌표는 지뢰 배치 대상에서 반드시 제외된다(safe-first-click).
- 기본 지뢰 수는 10이며, `--mines N` 인자로 변경할 수 있다. N은 1 이상 63 이하여야 한다.

### FR-3 인접 지뢰 수 계산

- 지뢰 배치 직후 8방향(상·하·좌·우·대각선 4방향) 이웃의 지뢰 수를 각 셀에 기록한다.
- 보드 경계를 벗어나는 이웃 좌표는 무시한다.
- 지뢰 셀 자체의 `adjacent_count`는 계산 대상에서 제외한다.

### FR-4 재귀 연쇄 공개 (Flood Reveal)

- 공개한 셀의 `adjacent_count`가 0이면, 이웃 8방향 셀을 재귀적으로 공개한다.
- 이미 공개된 셀, 깃발이 꽂힌 셀, 보드 경계 바깥은 재귀 대상에서 제외한다.
- 재귀 진입 전 `0 <= r < 8 and 0 <= c < 8` 범위 가드를 반드시 적용한다.
- 무한루프 방지를 위해 방문한 좌표를 추적한다.

### FR-5 깃발 토글

- `f row col` 형식의 명령으로 해당 셀의 깃발을 토글한다.
- 이미 공개된 셀에는 깃발을 꽂을 수 없다.
- 깃발이 꽂힌 셀은 일반 공개 명령으로 공개되지 않는다.

### FR-6 승패 판정

- **LOSE**: 플레이어가 지뢰 셀을 공개하면 즉시 `game_state = LOSE`로 전환하고 모든 지뢰 위치를 노출한 후 종료한다.
- **WIN**: 지뢰 셀을 제외한 모든 셀이 공개되면 즉시 `game_state = WIN`으로 전환하고 승리 메시지를 출력한 후 종료한다.

### FR-7 보드 ASCII 렌더링

- 열 헤더(0–7)와 행 번호(0–7)를 포함한 ASCII 보드를 매 턴 출력한다.
- 셀 표시 규칙:

| 상태 | 표시 문자 |
|------|-----------|
| 미공개 | `.` |
| 깃발 | `F` |
| 공개 (지뢰 없음, 인접 0) | ` ` (공백) |
| 공개 (인접 1–8) | 해당 숫자 |
| 공개 (지뢰, 게임 오버 시) | `*` |

### FR-8 입력 파싱 및 검증

- 공개 명령: `row col` (두 정수, 공백 구분)
- 깃발 명령: `f row col`
- 입력이 위 형식을 벗어나거나 좌표 범위(0–7)를 초과하면 오류 메시지를 출력하고 재입력을 요청한다.
- 이미 공개된 셀에 공개 명령을 입력하면 경고를 출력하고 재입력을 요청한다.

### FR-9 실행 인자

- `python3 minesweeper.py` — 기본 지뢰 수 10으로 시작
- `python3 minesweeper.py --mines N` — 지뢰 수 N으로 시작 (1 ≤ N ≤ 63)
- 범위를 벗어난 N 입력 시 오류 메시지를 출력하고 종료한다.

---

## Non-Functional Requirements

### NFR-1 의존성

- Python 3.11 표준 라이브러리(`random`, `sys`, `os`)만 사용한다. 서드파티 패키지는 일절 사용하지 않는다.
- pytest 7.x는 테스트 실행 전용으로 허용하며, 게임 실행 경로에 import하지 않는다.

### NFR-2 성능

- 8×8 보드에서 재귀 연쇄 공개가 스택 오버플로 없이 완료되어야 한다.
- 모든 사용자 입력에 대한 응답(렌더링 포함)이 100ms 이내에 완료된다.

### NFR-3 이식성

- `python3 minesweeper.py` 단일 명령으로 macOS, Linux, Windows 환경에서 실행 가능하다.
- 터미널 환경에서 외부 라이브러리 설치 없이 즉시 실행 가능하다.

### NFR-4 테스트 커버리지

- pytest 단위 테스트는 FR-2~FR-6의 핵심 경로를 최소 1개 이상 실제 실행 경로(비mock)로 검증한다.
- 테스트 중 최소 1개는 e2e 실행 명령(`python3 minesweeper.py` 서브프로세스 호출 또는 `Board` 전체 게임 루프)을 포함한다.

### NFR-5 코드 구조

- `Board` 클래스가 게임 로직(지뢰 배치, 인접 계산, 공개, 판정)을 전담한다.
- `render()` 함수와 `parse_input()` 함수가 UI 레이어를 전담하며, `Board` 내부 상태를 직접 수정하지 않는다.
- 역할 경계(`Board` ↔ CLI UI)가 파일 내에서 명확히 분리된다.

---

## Inputs and Outputs

### 입력

| 입력 | 형식 | 예시 | 설명 |
|------|------|------|------|
| 실행 인자 | `--mines N` | `--mines 15` | 지뢰 수 지정 (선택, 기본 10) |
| 공개 명령 | `row col` | `3 4` | 해당 좌표 셀 공개 |
| 깃발 명령 | `f row col` | `f 2 5` | 해당 좌표 깃발 토글 |

### 출력

| 출력 | 시점 | 설명 |
|------|------|------|
| 초기 보드 | 게임 시작 시 | 열 헤더·행 번호 포함 8×8 ASCII 보드 |
| 갱신 보드 | 매 유효 입력 후 | 변경된 셀 상태 반영 |
| 오류 메시지 | 잘못된 입력 시 | 재입력 안내 포함 |
| 게임 오버 메시지 | LOSE 시 | 모든 지뢰 위치 노출 보드 포함 |
| 승리 메시지 | WIN 시 | 축하 문구 출력 후 종료 |

---

## Exceptions and Failure Scenarios

### EX-1 범위 초과 좌표 입력

- **조건**: 입력 좌표가 0–7 범위를 벗어남
- **처리**: "유효하지 않은 좌표입니다. 0–7 범위의 정수를 입력하세요." 출력 후 재입력 요청
- **게임 상태 변경**: 없음

### EX-2 형식 오류 입력

- **조건**: 정수가 아닌 값 입력, 공백 구분자 누락, 추가 토큰 존재
- **처리**: "입력 형식 오류. 'row col' 또는 'f row col' 형식으로 입력하세요." 출력 후 재입력 요청
- **게임 상태 변경**: 없음

### EX-3 이미 공개된 셀 재공개 시도

- **조건**: 공개 명령 대상 셀이 이미 `REVEALED` 상태
- **처리**: "이미 공개된 셀입니다." 출력 후 재입력 요청
- **게임 상태 변경**: 없음

### EX-4 공개된 셀에 깃발 시도

- **조건**: 깃발 명령 대상 셀이 이미 `REVEALED` 상태
- **처리**: "공개된 셀에는 깃발을 꽂을 수 없습니다." 출력 후 재입력 요청
- **게임 상태 변경**: 없음

### EX-5 지뢰 수 인자 범위 초과

- **조건**: `--mines N`에서 N < 1 또는 N > 63
- **처리**: "지뢰 수는 1 이상 63 이하여야 합니다." 출력 후 프로그램 종료 (exit code 1)

### EX-6 재귀 공개 경계 초과 시도

- **조건**: 재귀 연쇄 공개 중 보드 경계 바깥 좌표 접근 시도
- **처리**: 해당 좌표를 조용히 무시하고 재귀를 계속 진행
- **사용자 노출**: 없음 (내부 가드)

---

## Existing Behavior To Preserve

본 구현은 신규 작성이므로 보존해야 할 기존 동작은 없다. 단, 아래 AF 파이프라인 인터페이스는 변경하지 않는다.

- `runtime/timing/minesweeper-baseline_baseline.jsonl` 경로 및 JSONL 스키마(`doc_type`, `work_item`, `elapsed_sec`, `refine_attempts`, `output_chars`, `ts`)는 AF 파이프라인이 기록하며, `minesweeper.py`는 이 파일을 생성하거나 수정하지 않는다.

---

## Acceptance Criteria

### AC-1 stdlib 전용 실행

- `pip install` 없이 `python3 minesweeper.py` 명령이 exit code 0으로 실행을 시작한다.
- `import` 목록에 `random`, `sys`, `os` 외의 서드파티 모듈이 없다.

### AC-2 safe-first-click 보장

- 임의의 첫 번째 좌표 입력 후, 해당 좌표의 셀이 지뢰가 아닌 것을 `Board.cells[r][c].is_mine == False`로 확인할 수 있다.
- 100회 반복 시뮬레이션에서 첫 클릭 좌표에 지뢰가 배치된 경우가 0회여야 한다.

### AC-3 인접 지뢰 수 정확성

- 지뢰를 배치한 후 전체 64개 셀의 `adjacent_count` 값이 실제 이웃 지뢰 수와 일치한다.
- pytest 테스트에서 고정 시드(`random.seed(42)`)를 사용하여 결정론적으로 검증된다.

### AC-4 재귀 공개 무한루프 없음

- 8×8 전체 좌표에서 `adjacent_count == 0`인 셀을 공개할 때 `RecursionError` 또는 무한루프가 발생하지 않는다.
- 테스트에서 빈 셀만 존재하는 보드(지뢰 0개)를 생성하여 임의의 셀 공개 시 64개 셀이 전부 공개됨을 확인한다.

### AC-5 WIN 상태 전환

- 지뢰 셀을 제외한 모든 셀이 공개되면 `Board.game_state == "WIN"`이 된다.
- pytest 테스트에서 비지뢰 셀을 순서대로 전부 공개한 뒤 `game_state`가 `"WIN"`임을 검증한다.

### AC-6 LOSE 상태 전환

- 지뢰 셀을 공개하면 `Board.game_state == "LOSE"`가 된다.
- pytest 테스트에서 지뢰 좌표를 직접 공개하여 `game_state`가 `"LOSE"`임을 검증한다.

### AC-7 깃발 토글

- `f row col` 명령 후 해당 셀에 깃발이 표시된다.
- 같은 명령 재입력 후 깃발이 제거된다.
- 깃발 셀에 공개 명령 입력 시 상태 변경 없이 경고가 출력된다.

### AC-8 입력 유효성 검증

- 범위 초과 좌표, 비정수 입력, 형식 오류 입력에 대해 게임 상태 변경 없이 오류 메시지가 출력된다.
- `--mines 0`, `--mines 64`, `--mines abc` 입력 시 exit code 1로 종료된다.

### AC-9 보드 렌더링 정확성

- 공개된 셀의 표시 문자가 FR-7 규칙과 일치한다.
- 열 헤더(0–7)와 행 번호(0–7)가 매 턴 출력된다.

### AC-10 pytest 통과율

- `pytest test_minesweeper.py` 실행 결과 0 failures, 0 errors여야 한다.
- 최소 1개의 테스트는 `Board` 객체를 직접 생성하고 실제 게임 로직을 호출하는 비mock 실행 경로를 포함한다.

---

## Evidence

- **실행 명령 근거**: `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §방법 A
  ```
  python3 run_factory_cli.py --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa
  ```
- **역할 매핑 근거**: `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑
  - Rule Engine → Game Logic Dev
  - UI/화면/입력 → Frontend Dev
  - 테스트/회귀/품질게이트 → QA Engineer
- **경량 케이스 선택 근거**: `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §Brief 선택: minesweeper — 포커 게임 대비 Web 미요구, 단순 게임 로직
- **예상 타이밍 출력**: `runtime/timing/minesweeper-baseline_baseline.jsonl` (`doc_type`별 `elapsed_sec` 기록)

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md`
- `docs/codex/2026-05-08-af-productization-application-guide.md`
- `runtime/timing/minesweeper-baseline_baseline.jsonl` (AF 파이프라인 타이밍 출력 경로)

---

## Out Of Scope

- GUI 또는 웹 인터페이스 제공
- 점수 저장, 최고 기록, 리더보드 기능
- 8×8 이외의 그리드 크기 동적 지원 (런타임 파라미터 포함)
- 멀티플레이어 또는 네트워크 기능
- 힌트 제공 또는 자동 해결(solver) 기능
- `runtime/timing/` JSONL 직접 생성 — AF 파이프라인 담당
- 서드파티 패키지 의존성 (pytest 테스트 실행 제외)