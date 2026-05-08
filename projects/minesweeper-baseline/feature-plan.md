# Feature Plan

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| owner | Frontend Dev (주), Game Logic Dev, QA Engineer |
| status | pending |
| last_updated | 2026-05-08 |

---

## Background

Agent Factory의 work-item 병렬 측정 파이프라인은 FSA 문서 생성 처리량(plan → spec → work-items → design)을 병렬 vs 순차 실행 방식으로 벤치마킹하기 위한 결정론적·자기완결형 태스크를 필요로 한다. 이전 베이스라인이었던 포커 게임은 구조적으로 무거웠고 웹 의존성이 있었다. 지뢰찾기는 웹 서버 없이 순수 CLI만으로 동작하며, 게임 로직이 단순하고 외부 패키지가 불필요하다는 점에서 보다 가벼운 대안으로 선택되었다.

실행 타이밍은 `runtime/timing/minesweeper-baseline_baseline.jsonl`에 doc_type별 `elapsed_sec`로 기록되며, 이 데이터가 병렬화 효과 측정의 핵심 산출물이 된다.

---

## Problem Statement

병렬 측정 파이프라인에는 외부 의존성이 없고 결과가 결정론적이며 단일 터미널 세션에서 완결되는 게임 태스크가 필요하다. 현재 해당 조건을 만족하는 베이스라인 구현체가 없으며, FSA 역할(Game Logic Dev / CLI Frontend Dev / QA Engineer) 간 인터페이스가 정의되지 않아 중복 구현 위험이 있다.

---

## Goals

1. Python 3.11 표준 라이브러리만으로 동작하는 8×8 CLI 지뢰찾기 게임을 구현한다.
2. 플레이어가 셀을 공개하고 지뢰에 깃발을 꽂을 수 있는 완전한 게임 루프를 제공한다.
3. 지뢰 수를 실행 시점에 인수로 설정할 수 있게 한다 (기본값: 10).
4. pytest 단위 테스트로 핵심 게임 로직의 정확성을 검증한다.
5. 병렬 측정 파이프라인의 베이스라인 태스크로서 타이밍 JSONL을 정상 방출한다.

---

## Non-Goals

- GUI 또는 웹 인터페이스 제공
- 점수 저장 또는 리더보드
- 8×8 이외의 그리드 크기 동적 지원
- 멀티플레이어 또는 네트워크 기능
- 힌트 또는 자동 해결(Auto-Solve) 기능

---

## Scope

### 산출물

| 산출물 | 담당 역할 | 설명 |
|--------|-----------|------|
| `minesweeper.py` | Frontend Dev | CLI 진입점. 입력 파싱, 게임 루프, 보드 렌더링 |
| 게임 로직 모듈 | Game Logic Dev | 지뢰 배치, 셀 공개, 인접 수 계산, 재귀 플러드 공개 |
| 승리/패배 판정 및 보드 렌더링 | Frontend Dev | 상태 전이 감지 및 ASCII 보드 출력 |
| 단위 테스트 스위트 | QA Engineer | pytest 기반 핵심 로직 검증 |

### 핵심 기능 슬라이스

1. **그리드 초기화** — 8×8 셀 배열 생성, 모든 셀 미공개·미플래그 상태
2. **지뢰 무작위 배치** — 첫 클릭 셀 제외(safe-first-click), `random` 모듈 사용
3. **인접 지뢰 수 계산** — 각 셀의 8방향 이웃 지뢰 수 집계
4. **재귀 플러드 공개** — 인접 지뢰 0인 셀 공개 시 연쇄 공개 (BFS/DFS, 경계 조건 처리)
5. **깃발 토글** — 미공개 셀에 깃발 표시/해제
6. **승리/패배 판정** — 지뢰 셀 공개 → LOSE, 비지뢰 전체 공개 → WIN
7. **ASCII 보드 렌더링** — 행·열 번호 포함 출력
8. **입력 파싱 및 검증** — `r c` (공개), `f r c` (깃발), `q` (종료) 형식

### 데이터 모델

| 엔티티 | 주요 필드 |
|--------|-----------|
| `Board` | `grid_size`, `mine_count`, `cells`, `revealed`, `flagged`, `game_state` |
| `Cell` | `row`, `col`, `is_mine`, `adjacent_count`, `is_revealed`, `is_flagged` |

---

## Stakeholders

| 역할 | 책임 |
|------|------|
| Frontend Dev | CLI 실행 파일, 보드 렌더링, 승리/패배 출력 |
| Game Logic Dev | 지뢰 배치, 셀 공개, 상태 전이 로직 |
| QA Engineer | 단위 테스트 설계 및 실행 |
| Product Designer | CLI I/O 흐름 설계 (입력 포맷, 오류 메시지) |
| Backend Dev | 해당 없음 (외부 연동 없음, 스코프 외) |

---

## Success Metrics

| 지표 | 기준 |
|------|------|
| 단위 테스트 통과율 | 100% (pytest 전체 PASS) |
| safe-first-click 보장 | 첫 공개 셀이 지뢰인 경우 0% |
| 재귀 공개 경계 안전성 | 8×8 범위 초과 인덱스 오류 0건 |
| WIN 상태 전환 정확도 | 비지뢰 전체 공개 시 100% WIN 감지 |
| LOSE 상태 전환 정확도 | 지뢰 셀 공개 시 100% LOSE 감지 |
| 타이밍 JSONL 방출 | `minesweeper-baseline_baseline.jsonl` 정상 기록 |

---

## Risks and Assumptions

### 리스크

| 항목 | 설명 | 완화 방안 |
|------|------|-----------|
| 재귀 공개 인덱스 오류 | 8×8 경계 밖 접근 시 `IndexError` | 모든 이웃 탐색 전 범위 검사 (`0 <= r < 8 and 0 <= c < 8`) |
| 첫 클릭 지뢰 충돌 | 지뢰 배치 시 첫 클릭 좌표와 겹치면 게임 즉시 종료 | 첫 클릭 좌표를 배치 제외 목록에 추가 (safe-first-click) |
| 역할 경계 모호 | game_logic과 cli_io 중복 구현 가능성 | 인터페이스 명세를 scope 단계에서 먼저 고정 |

### 가정

- Python 3.11 이상 설치된 환경에서 실행한다.
- pytest는 테스트 전용 의존성으로 게임 실행에는 불필요하다.
- 게임 세션은 단일 터미널 세션 내에서 완결된다.
- 그리드 크기는 8×8로 고정이며 런타임 변경을 지원하지 않는다.

---

## Evidence

| 근거 | 출처 |
|------|------|
| 실행 명령 (`run_factory_cli.py --task ... --mode fsa`) | `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §방법 A |
| 역할 강제 매핑 (Rule Engine → Game Logic Dev, UI/입력 → Frontend Dev) | `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑 |
| 포커 대비 경량 케이스 — Web 미요구, 단순 게임 로직 | `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §Brief 선택: minesweeper |
| 타이밍 출력 경로 | `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §5. 결과 형식 |

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md`
- `docs/codex/2026-05-08-af-productization-application-guide.md`
- `runtime/timing/minesweeper-baseline_baseline.jsonl` (실행 후 생성)

---

## Approval Request

본 Feature Plan은 다음 구현 진입 조건이 충족되었을 때 승인된 것으로 간주한다.

- [ ] 역할별 인터페이스(함수 시그니처, 모듈 경계)가 scope 단계에서 문서화됨
- [ ] safe-first-click 구현 방식이 Game Logic Dev와 Frontend Dev 간 합의됨
- [ ] 재귀 공개(플러드 공개) 알고리즘의 경계 처리 방식이 QA Engineer에게 공유됨
- [ ] pytest 테스트 커버리지 대상 함수 목록이 QA Engineer에게 전달됨
