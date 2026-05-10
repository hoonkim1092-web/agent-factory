# Feature Spec

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| source_plan | `feature-plan.md` (Lilith Bootstrap, 2026-05-08) |
| status | 검토 대기 |
| last_updated | 2026-05-08 |

---

## Feature Overview

Python 3.11 표준 라이브러리만으로 동작하는 8×8 CLI 지뢰찾기 게임을 구현한다. 플레이어는 단일 터미널 세션에서 셀을 공개하거나 깃발을 꽂으며 게임을 완주할 수 있다. 지뢰 수는 실행 인수(`--mines`)로 설정 가능하며 기본값은 10이다.

이 구현은 Agent Factory 병렬 측정 파이프라인의 경량 기준(baseline) 태스크로 설계됐다. 외부 의존성이 없고 결정론적으로 실행 가능해야 하며, FSA 문서 생성 처리량(plan → spec → work-items → design)의 병렬 vs. 순차 비교 벤치마크에 적합해야 한다.

---

## User Scenarios

### 시나리오 1: 정상 플레이 — 셀 공개

1. 플레이어가 `python3 minesweeper.py` 로 게임을 시작한다.
2. 시스템이 8×8 빈 보드를 ASCII로 출력하고 좌표 입력 프롬프트를 표시한다.
3. 플레이어가 `3 4`를 입력한다.
4. 시스템이 해당 셀을 공개한다. 인접 지뢰가 없으면 연쇄 공개, 있으면 숫자를 표시한다.
5. 플레이어는 이 과정을 반복하며 게임을 진행한다.

### 시나리오 2: 깃발 토글

1. 플레이어가 `f 2 5`를 입력한다.
2. 시스템이 해당 셀에 깃발(`F`)을 표시하거나, 이미 깃발이 있으면 제거한다.
3. 깃발이 꽂힌 셀은 공개 명령으로 열 수 없다.

### 시나리오 3: 패배 — 지뢰 셀 공개

1. 플레이어가 지뢰가 있는 셀 좌표를 입력한다.
2. 시스템이 즉시 LOSE 상태로 전환하고, 모든 지뢰 위치를 공개한 최종 보드를 출력한다.
3. 게임이 종료된다.

### 시나리오 4: 승리 — 모든 비지뢰 셀 공개

1. 플레이어가 지뢰를 피해 모든 비지뢰 셀을 공개한다.
2. 시스템이 즉시 WIN 상태로 전환하고 승리 메시지를 출력한다.
3. 게임이 종료된다.

### 시나리오 5: 안전한 첫 클릭

1. 플레이어가 첫 번째 좌표를 입력한다.
2. 시스템은 해당 좌표를 제외한 나머지 셀에 지뢰를 배치한다.
3. 첫 번째 클릭은 항상 지뢰가 없는 셀을 공개한다.

### 시나리오 6: 지뢰 수 커스텀 설정

1. 플레이어가 `python3 minesweeper.py --mines 15`로 게임을 시작한다.
2. 시스템이 지뢰 15개로 초기화한다.
3. 나머지 플레이는 기본 설정과 동일하다.

---

## Functional Requirements

### FR-1 그리드 초기화

- 그리드 크기는 8×8로 고정이다.
- 게임 시작 시 모든 셀은 미공개(hidden) 상태다.
- 셀은 `row`(0-indexed), `col`(0-indexed), `is_mine`, `adjacent_count`, `is_revealed`, `is_flagged` 속성을 가진다.

### FR-2 지뢰 배치

- 지뢰는 첫 번째 클릭 좌표와 해당 인접 셀을 제외한 범위에 무작위 배치한다.
- 지뢰 수는 기본값 10, `--mines <N>` 인수로 변경 가능하다.
- 지뢰 수는 1 이상 63 이하(8×8 − 1)여야 한다. 범위를 벗어나면 오류 메시지 출력 후 종료한다.

### FR-3 인접 지뢰 수 계산

- 지뢰 배치 후 모든 비지뢰 셀의 `adjacent_count`를 계산한다.
- 계산 범위는 8방향(상하좌우 + 대각선)이며 격자 경계를 초과하는 방향은 무시한다.

### FR-4 셀 공개

- 플레이어가 미공개 비지뢰 셀을 선택하면 해당 셀을 공개한다.
- `adjacent_count`가 0인 셀을 공개하면 인접 셀을 재귀적으로 연쇄 공개한다.
- 재귀는 격자 경계(0~7)를 벗어나지 않으며, 이미 공개된 셀은 재방문하지 않는다.
- 깃발이 꽂힌 셀은 공개 명령으로 열리지 않는다.

### FR-5 깃발 토글

- `f <row> <col>` 명령으로 미공개 셀에 깃발을 꽂거나 제거한다.
- 이미 공개된 셀에는 깃발을 꽂을 수 없다.

### FR-6 승리/패배 감지

- **LOSE**: 플레이어가 지뢰 셀을 공개하는 즉시 LOSE 상태로 전환한다.
- **WIN**: 지뢰 셀을 제외한 모든 셀이 공개되는 즉시 WIN 상태로 전환한다.
- 게임 종료 후 추가 입력은 처리하지 않는다.

### FR-7 보드 ASCII 렌더링

- 매 턴 보드를 다음 심볼로 출력한다.

| 심볼 | 의미 |
|------|------|
| `.` | 미공개 셀 |
| `F` | 깃발 셀 |
| ` ` (공백) | 공개된 빈 셀 (adjacent_count = 0) |
| `1`~`8` | 공개된 셀의 인접 지뢰 수 |
| `*` | 지뢰 (LOSE 시 전체 공개) |

- 행·열 번호(0-indexed)를 함께 표시해 입력 좌표 확인을 돕는다.

### FR-8 입력 파싱 및 유효성 검사

- 공개 명령: `<row> <col>` (예: `3 4`)
- 깃발 명령: `f <row> <col>` (예: `f 2 5`)
- 종료 명령: `q` 또는 `quit`
- 유효하지 않은 입력(범위 초과, 형식 오류)은 오류 메시지를 출력하고 재입력을 요청한다.

---

## Non-Functional Requirements

### NFR-1 실행 환경

- Python 3.11 표준 라이브러리(`random`, `sys`, `os`)만 사용한다.
- `python3 minesweeper.py`로 추가 설치 없이 기동 가능해야 한다.

### NFR-2 외부 의존성

- 런타임에 서드파티 패키지를 사용하지 않는다.
- pytest는 테스트 실행 전용으로만 허용한다.

### NFR-3 자기 완결성

- 웹 서버, 브라우저, 네트워크 연결 없이 단일 터미널 세션에서 완주 가능해야 한다.

### NFR-4 결정론적 실행

- 동일 시드로 실행 시 동일한 지뢰 배치 결과를 보장한다(`random.seed` 지원).
- 병렬 측정 파이프라인에서 반복 실행 시 일관된 타이밍을 위해 예외를 억제하거나 무한 루프를 유발하는 경로가 없어야 한다.

### NFR-5 성능

- 8×8 그리드에서 연쇄 공개(전체 64셀)가 즉시(< 1초) 완료돼야 한다.
- 재귀 깊이 초과(`RecursionError`)가 발생하지 않아야 한다 (8×8 최대 64개 셀로 스택 한도 초과 없음).

---

## Inputs and Outputs

### 입력

| 입력 | 형식 | 설명 |
|------|------|------|
| 셀 공개 | `<row> <col>` | 0-indexed 정수 두 개, 공백 구분 |
| 깃발 토글 | `f <row> <col>` | `f` 접두어 + 0-indexed 정수 두 개 |
| 종료 | `q` 또는 `quit` | 게임 즉시 종료 |
| 지뢰 수 설정 | `--mines <N>` | 실행 인수, 기본값 10 |

### 출력

| 출력 | 시점 | 내용 |
|------|------|------|
| 초기 보드 | 게임 시작 | 8×8 빈 보드 ASCII |
| 갱신 보드 | 매 턴 | 현재 공개·깃발 상태 반영 |
| 승리 메시지 | WIN 상태 전환 시 | 축하 메시지 + 최종 보드 |
| 패배 메시지 | LOSE 상태 전환 시 | 실패 메시지 + 지뢰 위치 전체 공개 보드 |
| 오류 메시지 | 유효하지 않은 입력 | 재입력 안내 |

---

## Exceptions and Failure Scenarios

### EX-1 범위 초과 좌표

- 입력 좌표가 0~7 범위를 벗어나면 오류 메시지를 출력하고 같은 턴을 반복한다.
- 보드 상태를 변경하지 않는다.

### EX-2 이미 공개된 셀 재선택

- 이미 공개된 셀을 다시 공개하려 하면 경고 메시지를 출력하고 재입력을 요청한다.

### EX-3 깃발 셀 공개 시도

- 깃발이 꽂힌 셀을 공개하려 하면 동작하지 않고 안내 메시지를 출력한다.

### EX-4 비정수 입력

- 숫자가 아닌 값이 입력되면 형식 오류 메시지를 출력하고 재입력을 요청한다.

### EX-5 지뢰 수 범위 위반

- `--mines` 값이 1 미만이거나 63 초과이면 오류 메시지를 출력하고 프로세스를 종료한다(`sys.exit(1)`).

### EX-6 첫 클릭 시 지뢰 배치 불가

- 첫 번째 클릭 좌표 및 인접 셀에는 지뢰를 배치하지 않는다. 해당 셀 집합이 전체 셀보다 작아 지뢰 배치 공간이 부족한 경우는 발생하지 않는다 (8×8 − 9 = 55 ≥ 최대 지뢰 수 63의 예외 케이스는 NFR 지뢰 수 상한으로 방지).

---

## Existing Behavior To Preserve

이 프로젝트는 신규 구현이므로 보존해야 할 기존 동작은 없다.

단, Agent Factory 측정 인프라의 다음 계약은 변경하지 않는다.

- 타이밍 출력 파일 경로: `runtime/timing/minesweeper-baseline_baseline.jsonl`
- 각 레코드 필드: `doc_type`, `work_item`, `elapsed_sec`, `refine_attempts`, `output_chars`, `ts`
- 실행 명령 인터페이스: `python3 run_factory_cli.py --task '...' --project minesweeper-baseline --mode fsa`

---

## Acceptance Criteria

### AC-1 기동 성공

`python3 minesweeper.py` 실행 시 8×8 보드가 출력되고 입력 프롬프트가 표시된다. 추가 패키지 설치 없이 동작한다.

### AC-2 지뢰 수 설정

`python3 minesweeper.py --mines 15` 실행 후 지뢰가 정확히 15개 배치된다. `--mines 0` 또는 `--mines 64` 입력 시 프로세스가 exit code 1로 종료된다.

### AC-3 Safe-first-click 보장

100회 무작위 시드로 게임을 시작해 첫 번째 좌표를 입력했을 때, 단 한 번도 지뢰 셀이 선택되지 않는다.

### AC-4 인접 지뢰 수 정확성

고정 시드로 지뢰를 배치한 후 모든 셀의 `adjacent_count`가 실제 인접 지뢰 수와 일치한다. pytest 단위 테스트로 검증한다.

### AC-5 재귀 연쇄 공개 경계 안전성

`adjacent_count = 0`인 셀을 공개했을 때 `IndexError`와 `RecursionError` 없이 종료되며, 8×8 격자 범위를 벗어난 셀이 공개 목록에 포함되지 않는다.

### AC-6 LOSE 상태 전환

지뢰 셀 공개 시 즉시 LOSE 상태로 전환되고, 모든 지뢰 위치(`*`)가 표시된 최종 보드가 출력된다. 이후 입력은 처리되지 않는다.

### AC-7 WIN 상태 전환

지뢰를 제외한 모든 셀이 공개되는 즉시 WIN 상태로 전환되고 승리 메시지가 출력된다. 이후 입력은 처리되지 않는다.

### AC-8 단위 테스트 전체 통과

`pytest tests/` 실행 시 아래 5개 핵심 시나리오가 모두 PASS한다.

| 테스트 ID | 검증 항목 |
|-----------|-----------|
| T-1 | `adjacent_count` 정확성 (고정 시드, 전체 셀) |
| T-2 | 재귀 공개 경계 조건 (`IndexError` 0건) |
| T-3 | safe-first-click (첫 클릭 셀 지뢰 0건) |
| T-4 | WIN 상태 전환 (모든 비지뢰 셀 공개 후 즉시 WIN) |
| T-5 | LOSE 상태 전환 (지뢰 셀 공개 후 즉시 LOSE) |

### AC-9 깃발 토글 동작

`f <row> <col>` 입력 시 해당 셀에 `F` 심볼이 표시되고, 동일 명령 재입력 시 깃발이 제거된다. 깃발이 꽂힌 셀은 공개 명령으로 열리지 않는다.

### AC-10 유효하지 않은 입력 처리

범위 초과 좌표, 비정수 입력, 이미 공개된 셀 재선택 시 오류 메시지가 출력되고 게임 상태가 변경되지 않으며 다음 입력을 기다린다.

---

## Evidence

| 출처 | 내용 |
|------|------|
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §방법 A | 실행 명령: `python3 run_factory_cli.py --task '8x8 minesweeper game with mines' --project minesweeper-baseline --mode fsa` |
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §결과 형식 | 타이밍 출력: `runtime/timing/minesweeper-baseline_baseline.jsonl` (doc_type·elapsed_sec 포함) |
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §Brief 선택 | 포커 대비 경량 케이스로 minesweeper 선정 — Web 미요구, 단순 게임 로직 |
| `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑 | Rule Engine → Game Logic Dev, UI/입력 → Frontend Dev, 테스트 → QA Engineer |
| Task Board (전체 35개 태스크 completed) | 모든 모듈의 scope → build → code_review → cross_validate → verify 완료 |

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md`
- `docs/codex/2026-05-08-af-productization-application-guide.md`
- `feature-plan.md` (Lilith Bootstrap, 2026-05-08)
- `runtime/timing/minesweeper-baseline_baseline.jsonl` (실행 후 생성)

---

## Out Of Scope

| 항목 | 제외 이유 |
|------|-----------|
| GUI 또는 웹 인터페이스 | CLI 전용 설계; 외부 의존성 배제 |
| 점수 저장 및 리더보드 | 측정 파이프라인 범위 외; 단일 세션 완결 |
| 8×8 이외의 그리드 크기 동적 지원 | 고정 크기가 벤치마크 결정론성 보장 조건 |
| 멀티플레이어 및 네트워크 기능 | CLI 단독 실행 요건과 충돌 |
| 힌트 및 자동 해결(auto-solve) | 요구사항 외 기능; 측정 노이즈 유발 |
| Python 표준 라이브러리 외 런타임 패키지 | NFR-1 제약; pytest는 테스트 전용으로만 허용 |
| 백엔드 서버·DB 연동 | CLI 게임에 서버 불필요; 메모리 내 상태 관리로 대체 |