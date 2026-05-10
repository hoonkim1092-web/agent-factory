# Feature Plan

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| owner | Game Logic Dev / Frontend Dev / QA Engineer |
| status | draft |
| last_updated | 2026-05-08 |

---

## Background

Agent Factory의 work-item 병렬 측정 파이프라인(plan → spec → work-items → design)은 처리량 벤치마크를 위해 결정론적이고 자기완결적인 기준 태스크가 필요하다. 이전 베이스라인으로 사용하던 포커 게임은 웹 서버 의존성 때문에 순수 CLI 환경에서 실행하기 어려웠다. 지뢰찾기는 외부 의존성이 없고 게임 로직이 단순하며 Python stdlib만으로 구현 가능해 경량 대체 케이스로 선정되었다. 본 실행은 `runtime/timing/minesweeper-baseline_baseline.jsonl`에 타이밍 JSONL을 기록하도록 계측된다.

---

## Problem Statement

병렬 측정 파이프라인이 FSA 문서 생성 처리량(병렬 vs. 순차 실행)을 비교하려면 외부 의존성이 없고 단일 터미널 세션에서 완료 가능한 결정론적 게임 태스크가 필요하다. 현재 해당 기준을 만족하는 자기완결적 CLI 게임 구현체가 없으므로, 8x8 지뢰찾기 CLI를 직접 구현하여 베이스라인으로 확립한다.

---

## Goals

1. Python 3.11 표준 라이브러리만으로 동작하는 8×8 지뢰찾기 CLI 게임(`minesweeper.py`)을 구현한다.
2. 지뢰 수를 실행 시점에 인자로 지정할 수 있으며, 기본값은 10이다.
3. 플레이어가 셀을 공개하거나 깃발을 꽂을 수 있고, 승리·패배 조건이 명확히 판정된다.
4. 첫 번째 클릭에서는 지뢰가 배치되지 않는 safe-first-click을 보장한다.
5. 빈 셀 클릭 시 연쇄 공개(flood-reveal)가 재귀적으로 동작하고 경계를 초과하지 않는다.
6. pytest 단위 테스트 스위트가 핵심 게임 로직을 검증한다.
7. AF 파이프라인 타이밍 JSONL(`runtime/timing/minesweeper-baseline_baseline.jsonl`)이 정상 기록된다.

---

## Non-Goals

- GUI 또는 웹 인터페이스 제공
- 점수 저장 또는 리더보드 기능
- 8×8 이외의 그리드 크기 동적 지원
- 멀티플레이어 또는 네트워크 기능
- 힌트 제공 또는 자동 해결 기능
- 서드파티 패키지 사용 (pytest 제외 — 테스트 전용)

---

## Scope

### 포함 범위

| 모듈 | 담당 역할 | 산출물 |
|------|-----------|--------|
| CLI 진입점 | Frontend Dev | `minesweeper.py` |
| 게임 로직 (지뢰 배치·인접 카운트·재귀 공개) | Game Logic Dev | `game_logic.py` (또는 `minesweeper.py` 내 클래스) |
| 보드 ASCII 렌더링 및 입력 파싱 | Frontend Dev | `minesweeper.py` |
| 승리/패배 판정 | Game Logic Dev | `minesweeper.py` 내 상태 머신 |
| 단위 테스트 스위트 | QA Engineer | `test_minesweeper.py` |

### 필수 기능 슬라이스

1. **grid_initialization** — 8×8 셀 배열 생성, 초기 상태 `HIDDEN`
2. **mine_random_placement** — `random` 모듈로 지뢰 위치 무작위 배치, 첫 클릭 좌표 제외
3. **adjacent_mine_counting** — 8방향 이웃 지뢰 수 계산
4. **recursive_flood_reveal** — 인접 지뢰 수 0인 셀 클릭 시 연쇄 공개, 경계 초과 방지
5. **flag_toggle** — `f row col` 명령으로 깃발 토글
6. **win_lose_detection** — 지뢰 셀 공개 시 LOSE, 비지뢰 셀 전체 공개 시 WIN
7. **board_ascii_render** — 열 헤더·행 번호 포함 ASCII 보드 출력
8. **input_parsing_and_validation** — `row col` 또는 `f row col` 형식 파싱, 범위 외 입력 거부

### 데이터 모델

**Board**

| 필드 | 타입 | 설명 |
|------|------|------|
| `grid_size` | `int` | 고정값 8 |
| `mine_count` | `int` | 기본값 10, 실행 인자로 변경 가능 |
| `cells` | `list[list[Cell]]` | 8×8 셀 행렬 |
| `revealed` | `set[tuple]` | 공개된 좌표 집합 |
| `flagged` | `set[tuple]` | 깃발 표시된 좌표 집합 |
| `game_state` | `str` | `PLAYING` / `WIN` / `LOSE` |

**Cell**

| 필드 | 타입 | 설명 |
|------|------|------|
| `row`, `col` | `int` | 좌표 |
| `is_mine` | `bool` | 지뢰 여부 |
| `adjacent_count` | `int` | 인접 지뢰 수 (0–8) |
| `is_revealed` | `bool` | 공개 여부 |
| `is_flagged` | `bool` | 깃발 여부 |

---

## Stakeholders

| 역할 | 담당자 | 관심사 |
|------|--------|--------|
| Game Logic Dev | 미배정 | 핵심 규칙·상태 전이 정확성 |
| Frontend Dev | 미배정 | CLI 입출력 UX, 렌더링 정확성 |
| QA Engineer | 미배정 | 경계 조건·회귀 커버리지 |
| AF Pipeline Owner | hoon | 타이밍 JSONL 기록 정합성 |

---

## Success Metrics

| 지표 | 기준 |
|------|------|
| 단위 테스트 통과율 | 100% (pytest, 0 failures) |
| 인접 지뢰 수 정확도 | 전체 64셀 adjacent_count 오류 0 |
| 재귀 공개 무한루프 | 8×8 전 좌표에서 스택 오버플로 없음 |
| safe-first-click 보장 | 첫 클릭 좌표에 지뢰 배치 확률 0% |
| WIN 전환 조건 | 비지뢰 셀 전체 공개 시 WIN 상태 전환 확인 |
| LOSE 전환 조건 | 지뢰 셀 공개 시 LOSE 상태 전환 확인 |
| stdlib 전용 실행 | `pip install` 없이 `python3 minesweeper.py` 실행 성공 |
| 타이밍 JSONL 기록 | `runtime/timing/minesweeper-baseline_baseline.jsonl` 생성 및 `elapsed_sec` 포함 |

---

## Risks and Assumptions

### 위험 요소

| ID | 위험 | 영향도 | 대응 방안 |
|----|------|--------|-----------|
| R-1 | 재귀 셀 공개 시 8×8 범위 초과 인덱스 오류 | 높음 | 재귀 진입 전 `0 <= r < 8 and 0 <= c < 8` 가드 의무화 |
| R-2 | 지뢰 배치 시 첫 클릭 셀과 충돌 | 중간 | 배치 루프에서 첫 클릭 좌표를 제외 후 샘플링 |
| R-3 | game_logic과 cli_io 역할 경계 모호로 중복 구현 | 중간 | `Board` 클래스(로직)와 `render()`/`parse_input()`(UI) 명확 분리, 역할 인터페이스를 scope 단계에서 고정 |
| R-4 | `random.sample` 편향으로 특정 패턴에 지뢰 집중 | 낮음 | 표준 `random.sample` 사용 — 균등 분포 보장됨 |

### 가정

- Python 3.11 환경이 실행 머신에 설치되어 있다.
- pytest 7.x는 테스트 전용으로 허용되며 게임 실행 시에는 불필요하다.
- 8×8 고정 크기는 변경되지 않는다.
- 타이밍 JSONL 경로(`runtime/timing/`)는 AF 파이프라인이 자동 생성한다.

---

## Evidence

- **실행 명령 근거**: `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §방법 A
  ```
  python3 run_factory_cli.py --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa
  ```
- **역할 매핑 근거**: `docs/codex/2026-05-08-af-productacion-application-guide.md` §권장 강제 매핑
  - Rule Engine → Game Logic Dev
  - UI/화면/입력 → Frontend Dev
  - 테스트/회귀/품질게이트 → QA Engineer
- **경량 케이스 선택 근거**: `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §Brief 선택: minesweeper — 포커 게임 대비 Web 미요구, 단순 게임 로직

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md`
- `docs/codex/2026-05-08-af-productization-application-guide.md`
- `runtime/timing/minesweeper-baseline_baseline.jsonl` (예상 출력 경로)

---

## Approval Request

본 Feature Plan은 아래 조건을 만족할 때 승인된 것으로 간주한다.

- [ ] 역할별 모듈 경계(Game Logic Dev / Frontend Dev / QA Engineer)가 Scope 섹션 기준으로 팀 내 합의됨
- [ ] R-1~R-3 위험 대응 방안이 spec 단계에서 인터페이스 계약으로 반영됨
- [ ] safe-first-click 동작이 Success Metrics 기준으로 테스트 케이스에 포함됨
- [ ] AF 파이프라인 타이밍 JSONL 경로가 실행 환경에서 검증됨
## Episode Hints

_과거 유사 프로젝트에서 학습된 주의사항:_

- stub-only 테스트는 실제 기능 존재를 보장하지 않는다 — e2e_command 필수
- e2e_command가 `needs_backfill`인 태스크는 PASS 처리 불가
- 테스트 작성 시 최소 1개의 실제 실행 경로(비mock)를 포함해야 한다
- approval-gate `status=completed` = 파일 존재 + 금지토큰 0 + e2e exit 0 모두 충족
- 라이브러리 함수명 발명 금지: 항상 공식 문서에서 확인된 API만 사용한다
- mock 전용 테스트는 실제 import 오류를 잡지 못한다 — 최소 1개 실행 테스트 필요
- Level 1 retry에서 같은 패턴이 반복되면 pivot(Level 2)으로 즉시 에스컬레이션
- 존재하지 않는 심볼 사용 시도가 감지되면 작업 전 경고 로그를 주입한다
