# Feature Plan

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | `build-a-playable-8x8-cli-minesweeper-game-where-the-player-c` |
| owner | Lilith Bootstrap (pd_director) |
| status | pending |
| last_updated | 2026-05-08 |

---

## Background

이 프로젝트는 Agent Factory의 작업 항목(work-item) 병렬 측정 파이프라인을 위한 경량 기준선(baseline) 태스크로 기획되었다. 직전 기준선이었던 포커 게임은 웹 서버 의존성이 있어 CLI 전용 환경에서 실행하기 어려웠다. 지뢰찾기(Minesweeper)는 외부 의존성 없이 단순한 게임 로직만으로 완결되는 대안으로 선택되었다.

파이프라인은 `plan → spec → work-items → design` 순서로 문서를 생성하며, 병렬 실행과 순차 실행의 처리 시간을 `runtime/timing/minesweeper-baseline_baseline.jsonl`에 기록한다. 이 산출물은 FSA 문서 생성 처리량(throughput)의 벤치마크 데이터로 사용된다.

---

## Problem Statement

병렬 측정 파이프라인은 외부 의존성이 없고 결정론적으로 실행 가능한 게임 태스크를 기준선으로 필요로 한다. 기존 포커 게임 기준선은 웹 서버를 요구하여 CLI 전용 계측 환경에 적합하지 않았다. 따라서 Python 3.11 표준 라이브러리만으로 동작하고, 단일 터미널 세션에서 완료 가능한 8x8 지뢰찾기 CLI 게임을 새 기준선으로 구현해야 한다.

---

## Goals

1. **플레이 가능한 8x8 CLI 지뢰찾기 구현** — 플레이어가 셀을 공개하고 지뢰에 깃발을 꽂을 수 있는 완전한 게임을 제공한다.
2. **Python 3.11 표준 라이브러리 전용** — `random`, `sys`, `os` 외 서드파티 패키지 없이 실행된다.
3. **단일 터미널 세션 완결** — 웹 서버·브라우저 없이 터미널 하나에서 게임 시작부터 종료까지 가능해야 한다.
4. **지뢰 수 설정 가능** — 실행 시 인자로 지뢰 수를 지정할 수 있고, 기본값은 10이다.
5. **단위 테스트 스위트 제공** — pytest 기반 테스트로 핵심 로직의 정확성을 검증한다.
6. **파이프라인 계측 호환** — AF 측정 파이프라인이 산출물 타이밍을 `runtime/timing/minesweeper-baseline_baseline.jsonl`에 기록할 수 있도록 구조가 적합해야 한다.

---

## Non-Goals

- GUI 또는 웹 인터페이스 제공
- 점수 저장 또는 리더보드 기능
- 8x8 이외의 그리드 크기 동적 지원
- 멀티플레이어 또는 네트워크 기능
- 힌트 또는 자동 해결(auto-solve) 기능

---

## Scope

### 포함 범위

| 모듈 | 담당 역할 | 산출물 |
|------|-----------|--------|
| CLI 실행 파일 | Frontend Dev | `minesweeper.py` (진입점, 입력 루프) |
| 게임 로직 모듈 | Game Logic Dev / Frontend Dev | 지뢰 배치, 셀 공개, 인접 수 계산 |
| 보드 렌더링·승패 판정 | Frontend Dev | ASCII 보드 출력, WIN/LOSE 상태 전환 |
| 단위 테스트 스위트 | QA Engineer | `test_minesweeper.py` (pytest 7.x) |
| 데이터 구조 | Backend Dev | `Board`, `Cell` 인메모리 모델 |
| CLI 화면 흐름 설계 | Product Designer | 입력 포맷, 프롬프트 UX 규격 |

### 핵심 기능 슬라이스

1. **그리드 초기화** — 8×8 빈 보드 생성, 셀 상태 초기화
2. **지뢰 랜덤 배치** — 첫 클릭 셀을 제외한 위치에 `mine_count`개 배치
3. **인접 지뢰 수 계산** — 모든 비지뢰 셀에 `adjacent_count` 부여
4. **재귀적 셀 공개(flood reveal)** — 인접 수 0인 셀 공개 시 연쇄 공개
5. **깃발 토글** — `f <row> <col>` 명령으로 셀에 깃발 표시/해제
6. **승리 판정** — 비지뢰 셀 전체 공개 시 WIN
7. **패배 판정** — 지뢰 셀 공개 시 LOSE, 전체 지뢰 위치 노출
8. **ASCII 보드 렌더링** — 매 턴 현재 상태를 터미널에 출력

---

## Stakeholders

| 역할 | 담당 |
|------|------|
| Product Director (PD) | Lilith Bootstrap |
| Frontend Dev | CLI 화면·입력 루프 구현자 |
| Game Logic Dev | 게임 규칙·상태 전이 구현자 |
| Backend Dev | Board/Cell 데이터 구조 구현자 |
| Product Designer | CLI 화면 흐름·UX 규격 설계자 |
| QA Engineer | 단위 테스트 스위트 작성자 |

---

## Success Metrics

| 기준 | 검증 방법 |
|------|-----------|
| 지뢰 배치 후 `adjacent_count` 정확성 (전 셀) | 단위 테스트: 모든 셀 카운트 검증 |
| 재귀 공개가 경계 조건에서 무한루프 없이 종료 | 단위 테스트: 코너·엣지 셀 flood reveal |
| 첫 클릭 시 지뢰 미배치 보장 (safe-first-click) | 단위 테스트: 첫 좌표 제외 지뢰 배치 확인 |
| 비지뢰 셀 전체 공개 시 WIN 상태 전환 | 단위 테스트: 게임 상태 체크 |
| 지뢰 셀 공개 시 LOSE 상태 전환 | 단위 테스트: 게임 상태 체크 |
| Python 3.11 표준 라이브러리만으로 실행 | `python3 minesweeper.py` 단독 실행 성공 |
| pytest 스위트 전체 통과 | `pytest test_minesweeper.py` 0 failures |

---

## Risks and Assumptions

### 리스크

| # | 리스크 | 영향 | 완화 방안 |
|---|--------|------|-----------|
| R1 | 재귀 셀 공개 시 8×8 경계 초과 인덱스 오류 | 런타임 크래시 | 재귀 진입 전 `0 ≤ row < 8`, `0 ≤ col < 8` 범위 검사 필수 |
| R2 | 지뢰 배치 시 첫 클릭 셀과 충돌 | 첫 번째 클릭에서 즉시 LOSE | 첫 클릭 좌표를 배치 제외 목록에 포함 |
| R3 | game_logic과 cli_io 역할 경계 모호로 중복 구현 | 코드 중복, 유지보수 비용 증가 | 모듈 계약 — `minesweeper.py`는 I/O만, 게임 상태 변경은 로직 함수에 위임 |

### 가정

- Python 3.11이 실행 환경에 설치되어 있다.
- pytest 7.x는 테스트 전용으로만 사용되며 게임 실행에는 불필요하다.
- 그리드 크기는 8×8로 고정이며 런타임에 변경하지 않는다.
- `mine_count` 기본값은 10이며, 1 이상 63 이하의 정수를 허용한다.

---

## Evidence

| 출처 | 근거 |
|------|------|
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §방법 A | 실행 명령: `python3 run_factory_cli.py --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa` |
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §Brief 선택 | 포커 게임 대비 경량 케이스 — Web 미요구, 단순 게임 로직 |
| `docs/codex/2026-05-08-af-productization-application-guide.md` §권장 강제 매핑 | 역할 매핑: Rule Engine → Game Logic Dev, UI/입력 → Frontend Dev, 테스트 → QA Engineer |
| `docs/2026-05-08-work-item-parallel-measurement-handoff.md` §결과 형식 | 타이밍 산출물: `runtime/timing/minesweeper-baseline_baseline.jsonl` |

---

## References

- `docs/2026-05-08-work-item-parallel-measurement-handoff.md` — 실행 방법 및 타이밍 출력 형식 명세
- `docs/codex/2026-05-08-af-productization-application-guide.md` — AF 역할 매핑 가이드
- `runtime/timing/minesweeper-baseline_baseline.jsonl` — 예상 타이밍 산출물 경로

---

## Approval Request

본 Feature Plan은 다음 항목에 대한 검토 및 승인을 요청한다.

1. **역할 경계 확정** — `frontend_dev`가 게임 로직 모듈(지뢰 배치·셀 공개)까지 소유하는 현재 구조가 적절한지, 혹은 `game_logic_dev`로 소유권을 이전할지 확인 필요.
2. **safe-first-click 구현 범위** — 첫 클릭 보호를 게임 로직 모듈에서 처리할지, CLI 입력 루프에서 처리할지 결정 필요.
3. **mine_count 입력 방법** — CLI 인자(`--mines 10`)로만 받을지, 게임 시작 시 인터랙티브 프롬프트도 제공할지 확인 필요.

승인 후 `spec.md` 작성 및 작업 항목 분해 단계로 진입한다.
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
