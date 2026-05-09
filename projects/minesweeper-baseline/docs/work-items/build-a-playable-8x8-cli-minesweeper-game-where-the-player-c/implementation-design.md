```markdown
# Implementation Design

## Metadata

- work_item: build-a-playable-8x8-cli-minesweeper-game-where-the-player-c
- spec_type: feature
- source_spec: feature-spec.md
- status: draft
- last_updated: 2026-05-08T11:15:11

## Design Summary

Build a playable 8x8 CLI minesweeper game where the player can reveal cells and flag mines.

아키텍처: cli

기술 스택: Python 3.11, stdlib only (random, sys, os), pytest 7.x (테스트 전용)

실행 전략: parallel

## Planned Modules

### 8x8 지뢰찾기 CLI 실행 파일
- owner: frontend_dev
- objective: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)을(를) 구현한다.
- deliverables: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)
- feature_slices: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)을(를) 구현한다.

### 지뢰 배치 및 셀 공개 게임 로직 모듈
- owner: frontend_dev
- objective: 지뢰 배치 및 셀 공개 게임 로직 모듈을(를) 구현한다.
- deliverables: 지뢰 배치 및 셀 공개 게임 로직 모듈
- feature_slices: 지뢰 배치 및 셀 공개 게임 로직 모듈을(를) 구현한다.

### 패배 판정 및 보드 렌더링 출력
- owner: frontend_dev
- objective: 승리/패배 판정 및 보드 렌더링 출력을(를) 구현한다.
- deliverables: 승리/패배 판정 및 보드 렌더링 출력
- feature_slices: 승리/패배 판정 및 보드 렌더링 출력을(를) 구현한다.

### 단위 테스트 스위트
- owner: qa_engineer
- objective: 단위 테스트 스위트 (pytest)을(를) 구현한다.
- deliverables: 단위 테스트 스위트 (pytest)
- feature_slices: 단위 테스트 스위트 (pytest)을(를) 구현한다.

### Backend Dev 구현
- owner: backend_dev
- objective: 서버, 데이터, 외부 연동 레이어를 구현한다.
- deliverables: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)
- feature_slices: 서버, 데이터, 외부 연동 레이어를 구현한다.

### Game Logic Dev 구현
- owner: game_logic_dev
- objective: 핵심 규칙과 상태 전이를 구현한다.
- deliverables: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)
- feature_slices: 핵심 규칙과 상태 전이를 구현한다.

### Product Designer 구현
- owner: designer
- objective: 정보 구조와 화면 흐름, 비주얼 방향을 설계한다.
- deliverables: 8x8 지뢰찾기 CLI 실행 파일 (minesweeper.py)
- feature_slices: 정보 구조와 화면 흐름, 비주얼 방향을 설계한다.


## Data Flow

- (시작) → **8x8 지뢰찾기 CLI 실행 파일**
- (시작) → **지뢰 배치 및 셀 공개 게임 로직 모듈**
- (시작) → **패배 판정 및 보드 렌더링 출력**
- (시작) → **단위 테스트 스위트**
- (시작) → **Backend Dev 구현**
- (시작) → **Game Logic Dev 구현**
- (시작) → **Product Designer 구현**

## Event Sequence / Phase Flow

- **Phase 1 — 초기화**: 시스템 준비 및 의존성 설정
- **Phase 2 — 입력 수신**: 사용자/외부 이벤트 수신 및 유효성 검사
- **Phase 3 — 핵심 처리**: 비즈니스 로직 실행 및 상태 전환
- **Phase 4 — 결과 반환**: 처리 결과 직렬화 및 응답 전송

## Interface Impact

플레이어는 표준 입력(stdin)으로 `r <행> <열>` (셀 공개) 또는 `f <행> <열>` (깃발 토글) 명령을 입력한다. 표준 출력(stdout)에 8×8 보드가 텍스트로 렌더링된다. 외부 API·네트워크·파일시스템 인터페이스는 없으며, `minesweeper.py` 단일 파일이 진입점이다. 타이밍 계측 결과는 `runtime/timing/minesweeper-baseline_baseline.jsonl`에 JSONL로 기록된다 (Agent Factory 파이프라인 전용, 게임 자체 인터페이스와 무관).

## State And Data Model

- **Board** (memory): grid_size, mine_count, cells, revealed, flagged, game_state
- **Cell** (memory): row, col, is_mine, adjacent_count, is_revealed, is_flagged

## Compatibility Considerations

- **Python 버전**: 3.11 이상 필수. `random`, `sys`, `os` 외 서드파티 패키지 사용 금지 — 추가 `pip install` 없이 단일 파일로 즉시 실행 가능해야 한다.
- **플랫폼**: macOS/Linux 터미널을 1차 대상으로 하며, Windows CMD/PowerShell에서도 stdlib 범위 내 동작해야 한다 (`os.system('clear')` 대신 `'\n' * N` 스크롤 방식 사용 권장).
- **그리드 크기**: 8×8 고정. `mine_count`는 기동 시 CLI 인수로 지정 가능하며 기본값은 10. 범위는 1~54로 제한한다 (전체 셀 64 − 안전 보장 최소 여백 10).
- **재귀 깊이**: 8×8 격자에서 최대 연쇄 공개 깊이는 64이므로 Python 기본 재귀 한도(1 000) 이내. `sys.setrecursionlimit` 조정 불필요.
- **기존 코드 호환**: Agent Factory 파이프라인(`run_factory_cli.py`)이 `--project minesweeper-baseline` 플래그로 호출하므로, `projects/minesweeper-baseline/` 디렉터리 구조를 유지해야 한다.

## Migration Requirement

- none

## Risks

- 재귀 셀 공개 시 8x8 범위 초과 인덱스 오류
- 지뢰 배치 시 첫 클릭 셀과 충돌
- FSA 문서 생성 단계에서 game_logic과 cli_io 역할 경계 모호로 중복 구현 가능성

## Alternatives Considered

- **`curses` 기반 TUI**: 방향키·실시간 입력이 가능하지만 Windows 호환성이 낮고 stdlib 이식성 테스트 비용이 증가한다. CLI 텍스트 입력 방식으로 대체.
- **웹 기반 UI(Flask/HTTP)**: 이전 baseline(포커 게임)이 브라우저 의존성으로 측정 노이즈를 유발했기 때문에 배제. 지뢰찾기는 CLI-only 조건을 명시적으로 요구한다.
- **반복(iterative) BFS 셀 공개**: 재귀 대신 `collections.deque`를 사용하는 방안. 8×8 한도에서는 재귀 스택 오버플로 위험이 없으므로 재귀 방식을 선택해 코드를 단순하게 유지한다.
- **지뢰 배치 — 첫 클릭 후 배치**: 첫 클릭 셀을 반드시 안전하게 보장하기 위해 첫 입력 수신 후 지뢰를 배치하는 방식. 구현 복잡도가 약간 높아지지만 UX 품질을 위해 채택한다.

## Design Evidence

- Local reference: docs/2026-05-08-work-item-parallel-measurement-handoff.md -> # 방법 A: 직접 실행 python3 run_factory_cli.py --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa
- Local reference: docs/2026-05-08-work-item-parallel-measurement-handoff.md -> # 방법 B: af CLI alias (설치된 경우) af --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa ``` > **주의**: `--brief`, `--target-path` 플래그는 존재하지 않음. 파서 파라미터: `--task/-t`, `--project/-p`, `--mode`, `--pipeline` 등 (`run_factory_cli.py:55...
- Local reference: docs/codex/2026-05-08-af-productization-application-guide.md -> ### 권장 강제 매핑 - Rule Engine -> Game Logic Dev - Realtime Server/WebSocket -> Backend Dev - UI/화면/입력 -> Frontend Dev - 테스트/회귀/품질게이트 -> QA Engineer

## References

- Local: docs/2026-05-08-work-item-parallel-measurement-handoff.md | # 방법 A: 직접 실행
- Local: docs/2026-05-08-work-item-parallel-measurement-handoff.md | # 방법 B: af CLI alias (설치된 경우)
- Local: docs/codex/2026-05-08-af-productization-application-guide.md | ### 권장 강제 매핑
- Local: docs/2026-05-08-work-item-parallel-measurement-handoff.md | ### Brief 선택: **minesweeper** (가벼움)
- Local: docs/2026-05-08-work-item-parallel-measurement-handoff.md | ## 5. 결과 형식

## Test Strategy

- Unit tests per module
- Integration tests for cross-module flows
```