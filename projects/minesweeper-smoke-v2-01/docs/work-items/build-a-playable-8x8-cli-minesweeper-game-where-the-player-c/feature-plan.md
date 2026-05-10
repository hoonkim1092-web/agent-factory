# Feature Plan

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| owner | Lilith Bootstrap (pd_director) |
| status | 승인 대기 |
| last_updated | 2026-05-08 |

---

## Background

이 프로젝트는 Agent Factory의 Work-Item 병렬 측정 파이프라인을 위한 경량 기준(baseline) 태스크다. 직전 기준 태스크였던 포커 게임은 웹 서버 의존성과 복잡한 게임 로직으로 인해 측정 노이즈가 컸다. 지뢰찾기는 외부 의존성이 없고 게임 규칙이 단순하며, Python 표준 라이브러리만으로 완결 가능해 FSA 문서 생성 처리량(plan → spec → work-items → design)을 병렬 vs. 순차 실행 간 비교하는 데 적합한 대안으로 선정됐다.

실행 타이밍은 `runtime/timing/minesweeper-baseline_baseline.jsonl`에 `doc_type`별 `elapsed_sec`으로 기록된다.

---

## Problem Statement

병렬 측정 파이프라인은 외부 의존성 없이 결정론적으로 실행 가능한 게임 태스크가 필요하다. 기존 포커 게임 기준은 웹 요소를 포함해 환경 편차가 발생했고, FSA 문서 생성 처리량 벤치마크의 신뢰성을 저하시켰다. 지뢰찾기는 이를 대체할 자기 완결적 CLI 게임으로, 동일한 측정 인프라 위에서 더 낮은 노이즈로 병렬/순차 처리량을 비교할 수 있게 한다.

---

## Goals

1. **플레이 가능한 8×8 CLI 지뢰찾기 구현** — 단일 터미널 세션에서 시작부터 승리/패배까지 완주 가능해야 한다.
2. **안전한 첫 클릭 보장** — 첫 번째 좌표 입력 시 지뢰가 배치되지 않아야 한다(safe-first-click).
3. **재귀 연쇄 공개 정확성** — 빈 셀 클릭 시 인접 빈 셀이 경계 초과 없이 연쇄 공개돼야 한다.
4. **승리/패배 조건 정확 감지** — 모든 비지뢰 셀 공개 시 WIN, 지뢰 셀 공개 시 LOSE 상태로 즉시 전환돼야 한다.
5. **지뢰 수 실행 시 설정** — 기본값 10, 실행 인수로 변경 가능해야 한다.
6. **단위 테스트 커버리지** — 핵심 검증 항목 5개(adjacent_count, 재귀 공개 경계, safe-first-click, WIN/LOSE 전환) 전부 pytest로 통과해야 한다.

---

## Non-Goals

- GUI 또는 웹 인터페이스 제공
- 점수 저장 또는 리더보드 기능
- 8×8 이외의 그리드 크기 동적 지원
- 멀티플레이어 또는 네트워크 기능
- 힌트 또는 자동 해결(auto-solve) 기능
- Python 표준 라이브러리 외 서드파티 패키지 사용 (테스트 전용 pytest 제외)

---

## Scope

### 포함

| 모듈 | 담당 역할 | 산출물 |
|------|-----------|--------|
| CLI 진입점 | Frontend Dev | `minesweeper.py` |
| 게임 로직 (지뢰 배치·셀 공개) | Frontend Dev / Game Logic Dev | 게임 로직 모듈 |
| 승리/패배 판정 및 보드 ASCII 렌더링 | Frontend Dev | 렌더링 출력 |
| 단위 테스트 스위트 | QA Engineer | `tests/` (pytest) |

### 주요 기능 목록

- `grid_initialization` — 8×8 셀 배열 초기화
- `mine_random_placement` — 첫 클릭 셀 제외 무작위 지뢰 배치
- `adjacent_mine_counting` — 각 셀의 인접 지뢰 수 계산
- `recursive_flood_reveal` — 빈 셀 클릭 시 연쇄 공개 (경계 조건 보장)
- `flag_toggle` — `f <row> <col>` 명령으로 깃발 토글
- `win_lose_detection` — 게임 종료 조건 감지
- `board_ascii_render` — 현재 보드 상태 터미널 출력
- `input_parsing_and_validation` — 좌표·명령 파싱 및 유효성 검사

### 제외

- 백엔드 서버·데이터 연동 레이어 (CLI 전용 게임이므로 backend_dev_module_5는 빈 셀 상태 메모리 관리로 축소)
- Product Designer의 시각 디자인 산출물 (ASCII 렌더링으로 대체)

---

## Stakeholders

| 역할 | 이름/식별자 | 책임 |
|------|-------------|------|
| PD Director | Lilith Bootstrap | 기능 계획 승인·역할 조율 |
| Frontend Dev | (담당자 미정) | CLI 진입점·렌더링 구현 |
| Game Logic Dev | (담당자 미정) | 핵심 게임 규칙·상태 전이 구현 |
| QA Engineer | (담당자 미정) | 단위 테스트 작성·검증 |
| Backend Dev | (담당자 미정) | 메모리 내 상태 관리 (서버 불필요) |

---

## Success Metrics

| 지표 | 기준 |
|------|------|
| 단위 테스트 통과율 | 5개 핵심 시나리오 100% PASS |
| 재귀 공개 경계 오류 | 8×8 범위 내 IndexError 0건 |
| Safe-first-click 보장 | 첫 클릭 셀이 지뢰인 케이스 0건 (100회 무작위 시드 반복) |
| WIN 상태 전환 정확도 | 모든 비지뢰 셀 공개 시 WIN 즉시 감지 |
| LOSE 상태 전환 정확도 | 지뢰 셀 공개 시 LOSE 즉시 감지 |
| 실행 환경 | Python 3.11 stdlib만으로 `python3 minesweeper.py` 기동 성공 |

---

## Risks and Assumptions

### 위험

| ID | 위험 | 심각도 | 완화 전략 |
|----|------|--------|-----------|
| R-1 | 재귀 셀 공개 시 8×8 범위 초과 IndexError | 높음 | 재귀 진입 전 경계 조건 guard 추가, pytest 경계 케이스 커버 |
| R-2 | 첫 클릭 셀에 지뢰 배치 충돌 | 중간 | 지뢰 배치를 첫 클릭 이후로 지연, 클릭 셀 제외 집합 전달 |
| R-3 | game_logic / cli_io 역할 경계 모호로 중복 구현 | 중간 | `minesweeper.py`(진입점·렌더링)와 `game_logic.py`(규칙·상태)를 파일 단위로 명확히 분리 |

### 가정

- Python 3.11 환경이 실행 머신에 이미 설치돼 있다.
- pytest는 테스트 전용으로만 사용하며 런타임 의존성이 아니다.
- 그리드 크기는 8×8로 고정이며 런타임 변경을 지원하지 않는다.
- 지뢰 수 기본값은 10이며 `--mines` 인수로 변경 가능하다.

---

## Evidence

| 출처 | 내용 요약 |
|------|-----------|
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §방법 A | 실행 명령: `python3 run_factory_cli.py --task '8x8 minesweeper game with mines' --project minesweeper-baseline --mode fsa` |
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §결과 형식 | 타이밍 출력 경로: `runtime/timing/minesweeper-baseline_baseline.jsonl` (doc_type·elapsed_sec 포함) |
| `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑 | Rule Engine → Game Logic Dev, UI/입력 → Frontend Dev, 테스트 → QA Engineer |
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §Brief 선택 | 포커 대비 경량 케이스로 minesweeper 선정 — Web 미요구, 단순 게임 로직 |

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md`
- `docs/codex/2026-05-08-af-productization-application-guide.md`
- `runtime/timing/minesweeper-baseline_baseline.jsonl` (실행 후 생성)

---

## Approval Request

이 Feature Plan은 아래 담당자의 승인을 요청한다.

| 역할 | 승인자 | 상태 |
|------|--------|------|
| PD Director | Lilith Bootstrap | 승인 대기 |
| 구현 총괄 | (담당자 미정) | 승인 대기 |

승인 후 `feature-plan.md` 상태를 `승인됨`으로 변경하고 구현 단계로 진입한다.
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
