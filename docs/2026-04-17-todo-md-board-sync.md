# `.todo.md` ↔ `project_board_state.json` 동기화 설계

- 작성일: 2026-04-17
- 작성자: Claude Code (Opus 4.7)
- 상태: 개정 v2 (af-doc-qa WARN + af-critic BLOCK 반영)
- 관련 이슈: `projects/lotto_predictor_v2/` 실제 29/36 태스크 완료인데 `.todo.md`는 `[x]` 1개만 표기되는 추적 불일치

## 0. 개정 이력

| 버전 | 일시 | 변경 요약 |
|------|------|-----------|
| v1 | 2026-04-17 12:20 | 초안 작성 (옵션 A 추천, safe_id 매칭, lock 바깥 훅) |
| v2 | 2026-04-17 12:45 | **safe_id 매칭 제거** (60자 절단 허위 매칭 리스크), **lock 내부 훅**으로 이동, 동적 주입 태스크 처리 정책 명시, 데이터 롤백 절차 추가, `[/]` in_progress 보존 규칙 추가 |
| v3 | 2026-04-17 13:00 | `blocked`/`failed` 상태를 `[!]`로 구분, kill-switch를 실행 체크리스트에 편입, `--reset` 플래그를 Out-of-Scope로 명시 |

## 1. 배경

### 1.1 발견 경위
`lotto_predictor_v2` 진행 상황 점검 중 다음 불일치 확인.

| 소스 | 완료 상태 |
|------|-----------|
| `project_board_state.json` | 23 completed, 10 pending, 3 in_progress |
| `.todo.md` | `[x]` 1개, `[ ]` 35개 |
| 실제 코드/테스트 | 65 tests passing, 6개 모듈 구현 완료 |

사용자가 `.todo.md`만 보고 "아무것도 완료 안 됐다"고 오판하는 실제 사례 발생.

### 1.2 근본 원인
`.todo.md`는 프로젝트 생성 시 1회만 작성되고 이후 갱신 메커니즘이 없다. Board 상태 전이는 JSON 보드 파일에만 기록되고 마크다운으로 전파되지 않는다.

## 2. 현재 구조

### 2.1 파일 역할

| 파일 | 역할 | 갱신 주기 |
|------|------|-----------|
| `project_board_state.json` | **진실 원천(SSOT)** — 태스크별 `status`, `notes`, `updated_at` | 상태 전이마다 `update_project_board_task()`로 즉시 갱신 |
| `.todo.md` | 사람이 읽는 체크리스트 | 프로젝트 초기 생성 시 **1회만** |

### 2.2 관련 코드

| 위치 | 함수 | 역할 |
|------|------|------|
| `core/documentation_policy.py:285-291` | `write_project_todo(workspace, todo_items)` | `.todo.md` 생성 — 무조건 `- [ ]` prefix |
| `core/documentation_policy.py:276-282` | `documentation_todo_items`, `normalize_project_todo_items` | 문서화 공통 체크리스트(architecture.md/change_history.md 갱신 등 소수 고정 항목) 추가 |
| `core/project_task_board.py:528-533` | `board_todo_items(board)` | board task의 `instruction` 필드를 todo item 문자열로 변환 |
| `core/project_task_board.py:644-675` | `update_project_board_task(...)` | board task `status` 변경 + JSON 저장 (**`.todo.md` 미갱신**) |
| `core/project_task_board.py:878-888` | `inject_review_tasks` | review/cross_validate 태스크를 board에 주입. 이들도 `instruction` 필드를 채우므로 `board_todo_items()`에 포함됨 |
| `core/project_task_board.py:542-553` | `load_project_board(workspace)` | board JSON 로드 |
| `core/dynamic_orchestrator.py:122-150` | `_open_todo_items`, `_completed_todo_items` | `.todo.md` 파싱 — `[x]`, `[ ]`, `[/]` 모두 인식 |
| `core/dynamic_orchestrator.py:213-219` | `_todo_fully_completed` | board 우선, `.todo.md`는 폴백 |
| `core/dynamic_orchestrator.py:221-260` | `_fallback_next_tasks` | board가 비었을 때만 `.todo.md` 기반 라우팅 |
| `core/utils.py:60-64` | `safe_id` | slug 정규화 후 **60자로 절단** — ID용. 매칭 키로는 부적합 (충돌 위험) |

### 2.3 매칭 관계 (v2 수정)
`board_todo_items()`는 각 `task["instruction"]`를 `_clean_text`로 정규화해 리턴하고, `write_project_todo()`는 이를 `- [ ] {item}` 포맷으로 쓴다. 즉 **`.todo.md` 각 라인의 텍스트 = board task의 `instruction` 정규화 결과**와 문자열 동일하다. 단, `documentation_todo_items()`로 추가되는 문서화 공통 항목은 board에 대응 태스크가 없다.

## 3. 문제 정의

- **P1 (현재 발견)**: board 상태 전이 후 `.todo.md`가 갱신되지 않아 진행률 오판 발생.
- **P2 (잠재)**: 사용자가 수동으로 `.todo.md`를 편집해도 board에 반영될 경로가 없음 (현재 운영에서는 수동 편집 없음).
- **P3 (회귀 방지 요건, 문제가 아니라 요건)**: `_fallback_next_tasks` 폴백 경로는 board가 비었을 때만 작동하므로, 동기화 도입 후에도 폴백 로직 자체는 유지해야 한다.

## 4. 설계 대안

### 4.1 옵션 비교

| 옵션 | 방식 | 장점 | 단점 | 복잡도 |
|------|------|------|------|--------|
| **A. 단방향 재생성** | board 변경마다 `.todo.md` 전체 재작성 (board가 SSOT) | SSOT 명확, 매칭 로직 단순 | 사용자 수동 편집 덮어쓰기, 동적 주입 태스크 라인도 자동 추가됨 | 낮음 |
| B. 인플레이스 패치 | `[ ]` ↔ `[x]` 해당 라인만 치환 | 수동 편집/코멘트 보존 | 매칭 실패 라인이 stale로 잔류, 신규 태스크(동적 주입) 라인 추가 로직 별도 필요 | 중간 |
| C. 역할 분리 | `.todo.md` 초기 계획 고정 + `progress.md` 신설 | SSOT 분리 명확 | 파일 2개, 사용자 주의 분산, 기존 관성과 불일치 | 낮음 |
| D. 양방향 동기화 | `.todo.md` 편집 → board 반영 | 어느 쪽을 수정해도 됨 | 충돌/경쟁 처리, 파서 복잡 | 높음 |

### 4.2 추천안: **옵션 A (단방향 재생성, board → `.todo.md`)**

**근거**
1. `.todo.md`는 이미 `write_project_todo()`가 전체 덮어쓰는 **파생물(derived)** 성격이다. 수동 편집 보호 계약이 없다.
2. board task의 `instruction`과 todo 라인이 1:1 매핑되며, 동적 주입된 review/cross_validate 태스크도 `board_todo_items()`에 자동 포함되므로 전체가 한 번에 반영된다.
3. P1을 즉각 해소한다. P2/P3는 현 운영 범위에서 블로커가 아니다.

**옵션 B 거부 근거 (솔직 기술)**
- A 역시 `board_todo_items()`가 포함하지 않는 태스크는 누락되는 동일 한계가 있다. 그러나 현재 `board_todo_items()`는 **모든 task["instruction"]을 포함**(review/cross_validate 포함)하므로 실질 누락은 거의 없다.
- B는 여기에 더해 **(a)** 매칭 실패 라인이 stale로 남고, **(b)** 신규 주입 태스크 라인 추가 로직을 별도로 구현해야 하는 이중 부담이 있다. 즉 A의 한계 + α.
- 따라서 B는 기대 이득(수동 편집 보존)이 현 운영 요구에서 가치가 낮은 반면 복잡도는 높다.

**옵션 C 거부 근거**: 파일 수 증가 및 기존 `.todo.md` 관성과 불일치. `.todo.md` 한 곳만 보면 된다는 UX 이점 상실.

**옵션 D 거부 근거**: 사용자 수동 편집 요구가 아직 없음. 과공학.

## 5. 구현 설계 (v2 개정)

### 5.1 변경 지점 요약

```
core/documentation_policy.py
 └ write_project_todo() 시그니처 확장
    + board: dict | None 인자
    + completed/in_progress/pending 분기 마킹 ([x]/[/]/[ ])

core/project_task_board.py
 └ update_project_board_task() lock 내부에 동기화 호출 추가
    + write_project_todo(workspace, board_todo_items(board), board=board)
    + 실패 시 warning 로그 (board 쓰기는 이미 커밋, 순서 보장)

core/dynamic_orchestrator.py
 └ (변경 없음) _todo_fully_completed/fallback은 board 우선 유지

core/cli_commands.py (또는 유사 위치)
 └ af project sync-todo <project_dir> 서브커맨드 추가
    + 기존 프로젝트 일괄 복구용
    + --dry-run 플래그로 diff만 출력
```

### 5.2 `write_project_todo` 시그니처

**변경 전**
```python
def write_project_todo(workspace: str, todo_items: list[str] | None) -> str:
    lines = [f"# {project_todo_title()}", ""]
    for item in normalize_project_todo_items(todo_items):
        lines.append(f"- [ ] {item}")
    ...
```

**변경 후**
```python
def write_project_todo(
    workspace: str,
    todo_items: list[str] | None,
    board: dict[str, Any] | None = None,
) -> str:
    lines = [f"# {project_todo_title()}", ""]
    status_map = _instruction_status_map(board) if board else {}
    for item in normalize_project_todo_items(todo_items):
        mark = _mark_for_status(status_map.get(_normalize_instruction(item)))
        lines.append(f"- [{mark}] {item}")
    ...

def _mark_for_status(status: str | None) -> str:
    if status == "completed":
        return "x"
    if status == "in_progress":
        return "/"
    if status in ("blocked", "failed"):
        return "!"
    return " "

def _normalize_instruction(text: str) -> str:
    # _clean_text와 동일한 공백/제어문자 정규화, 대소문자 유지
    return " ".join(str(text or "").split())

def _instruction_status_map(board: dict) -> dict[str, str]:
    """정규화된 instruction 문자열 → 상태 매핑.
    동일 instruction을 가진 task가 여럿이면 '가장 덜 완료된 상태'를 채택
    (completed < in_progress < blocked/failed < pending 순으로 보수적).
    blocked/failed는 '주의 필요'를 시각화하기 위해 pending보다 우선순위가 낮지 않다 —
    하나라도 pending이 있으면 pending(0)이 최하위로 유지되어 `[ ]` 표기."""
    precedence = {"completed": 3, "in_progress": 2, "blocked": 1, "failed": 1, "pending": 0}
    result: dict[str, str] = {}
    for task in board.get("tasks") or []:
        instruction = _normalize_instruction(task.get("instruction") or "")
        if not instruction:
            continue
        status = str(task.get("status") or "pending")
        if instruction in result:
            # 보수적: 낮은 precedence(덜 완료) 유지
            if precedence.get(status, 0) < precedence.get(result[instruction], 0):
                result[instruction] = status
        else:
            result[instruction] = status
    return result
```

### 5.3 매칭 규칙 (v2 핵심 개정 — safe_id 폐기)

**v1 문제**: `safe_id`는 `core/utils.py:64`에서 60자로 절단한다. 긴 instruction 두 개의 앞 60자가 같으면 같은 키로 충돌해 **false-positive `[x]` 표기**(실제는 미완료인데 완료로 보임)가 발생. 이는 단순 UX 저하가 아니라 **잘못된 정보 제공**이므로 BLOCK.

**v2 해결**: 전체 instruction 문자열을 **공백 정규화(whitespace collapse)만 거친 완전 일치**로 매칭한다. 절단 없음.

**매칭 규칙**
1. board task 각각에 대해 `_normalize_instruction(task["instruction"])` 키를 산출.
2. todo item 문자열도 동일하게 정규화 후 조회.
3. 동일 정규화 키를 가진 task가 여럿일 경우 **가장 덜 완료된 상태를 채택**(보수적). 예: 한 쪽 completed, 다른 쪽 pending이면 `[ ]`로 표기.
4. 문서화 공통 항목(`documentation_todo_items()`, 소수 고정 항목)은 board에 대응 task가 없으므로 조회 실패 → `[ ]` 유지.
5. `in_progress` 상태는 `[/]`로 표기 (`_open_todo_items`가 이미 이 prefix를 인식하므로 폴백 경로와도 호환).

**허위 완료 표기 방지**: v2는 전체 문자열 비교이므로 v1의 60자 절단 충돌은 원천 차단. 동일 instruction을 가진 task가 중복 존재하는 병리적 케이스에서도 "가장 덜 완료된 상태 채택" 규칙으로 false-positive 불가.

**경계 케이스**
- board에 있는데 todo에 없는 instruction: `normalize_project_todo_items`가 추가하지 않은 항목이면 todo 라인 자체가 없음. (현재는 `board_todo_items()`가 전부 포함하므로 실질 발생 안 함)
- todo에 있는데 board에 없는 항목 (문서화 공통): `[ ]` 유지.
- instruction 텍스트가 도중에 수정된 task: 정규화 키 불일치로 `[ ]` 표기. 데이터 손실 없음.

### 5.4 `update_project_board_task` 훅 (v2 핵심 개정 — lock 내부로 이동)

**v1 문제**: lock 바깥에서 todo 쓰기 → 다중 에이전트 동시 실행 시 에이전트 A의 todo 쓰기가 에이전트 B의 신규 상태를 덮어 `.todo.md`가 이전 스냅샷으로 롤백되는 race. Agent Factory는 `asyncio.to_thread` + subprocess 기반 동시 실행 구조이므로 실질 위험.

**v2 해결**: `locked_file(board_path)` 컨텍스트 **내부에서** `write_project_todo` 호출.

```python
def update_project_board_task(workspace, role, instruction, status, note="", task_id=""):
    board_path = os.path.join(os.path.abspath(workspace), BOARD_FILENAME)
    with locked_file(board_path):
        board = load_project_board(workspace)
        if not board:
            return False
        # ... 기존 매칭/갱신 로직 ...
        if not updated:
            return False
        write_project_board(workspace, board)
        # v2: lock 내부에서 todo 동기화 — board 쓰기와 같은 critical section
        try:
            from core.documentation_policy import write_project_todo
            write_project_todo(workspace, board_todo_items(board), board=board)
        except Exception as exc:
            print_agent_msg("System", f".todo.md 동기화 실패: {exc}", "")
    return True
```

**설계 원칙**
- board lock 내부에서 순차 실행 → race 차단. 에이전트 B의 후속 트랜잭션은 A의 lock 해제 후 진입하므로 항상 최신 board 기준으로 todo를 재생성한다.
- todo 쓰기 예외는 warning 로그만 — board 트랜잭션은 이미 성공. 다음 태스크 전이 시 자연 복원.
- I/O 비용: `.todo.md`는 보통 수 KB, lock 체류 시간 증가는 무시 가능. 프로파일링 후 문제 시 debounce(예: 500ms 이내 연속 전이는 마지막 것만 반영) 도입 고려. 임계치: 단일 상태 전이당 lock 체류가 100ms 초과 시 검토.

### 5.5 CLI sync 서브커맨드 (기존 프로젝트 복구용)

```
$ af project sync-todo projects/lotto_predictor_v2
[sync] board: 23 completed / 3 in_progress / 10 pending / 36 total
[sync] wrote .todo.md (23 [x], 3 [/], 10 [ ])

$ af project sync-todo projects/lotto_predictor_v2 --dry-run
[sync] would change 32 lines (diff below)
...
```

**동작**
- `load_project_board` → board 유효성 검증 → `board_todo_items(board)` → `write_project_todo(workspace, items, board=board)`
- board가 없거나 비어있으면 오류 반환 (exit code 2), `.todo.md` 건드리지 않음
- `--dry-run`: diff만 stdout 출력, 파일 미수정

## 6. 회귀/리스크 (v2 재평가)

| 리스크 | 영향 | 완화 |
|--------|------|------|
| ~~safe_id 60자 절단 허위 매칭~~ | ~~false-positive `[x]`~~ | **v2에서 safe_id 폐기**, 전체 문자열 정규화 매칭으로 원천 차단 |
| ~~lock 바깥 todo 쓰기 race~~ | ~~`.todo.md` 롤백~~ | **v2에서 lock 내부로 이동** |
| 동기화 훅이 board lock 체류 시간 증가 | 성능 저하 | 수 KB I/O, 실측 후 debounce 검토. 임계치 100ms |
| 기존 `.todo.md`에 수동 편집 라인 존재 시 덮어쓰기 | 데이터 손실 | 배포 전 전 프로젝트 `git log -p -- .todo.md` 스캔 + CLI `--dry-run` 사전 확인 의무화 |
| 동적 주입 review/cross_validate 태스크 라인이 기존 `.todo.md`에 없어서 diff 발생 | 사용자 혼동 | 기대 동작으로 명시. 첫 sync 시 사용자에게 diff 리뷰 권고 |
| `documentation_todo_items` 소수 고정 항목이 항상 `[ ]` 유지 | 완료율 체감 왜곡 | 항목 수 소수라 전체 대비 영향 미미. 후속 과제에서 파일 존재 여부 기반 판정 도입 고려 |
| 동일 instruction을 가진 task 중복 | 한 쪽 완료여도 `[ ]`로 표기 | 보수적 표기가 false-positive 방지 측면에서 올바른 선택 |

## 7. 테스트 전략 (v2 확장)

### 7.1 단위 테스트 (신규)

`tests/test_documentation_policy.py`, `tests/test_project_task_board.py` 기준:

1. `write_project_todo`: board 없이 호출 → 기존 동작 유지 (모두 `[ ]`)
2. `write_project_todo`: board 제공 + 일부 completed → 해당 라인만 `[x]`
3. `write_project_todo`: board 제공 + in_progress task → `[/]` 표기
3b. `write_project_todo`: board 제공 + blocked task → `[!]` 표기
3c. `write_project_todo`: board 제공 + failed task → `[!]` 표기
3d. `_open_todo_items`/`_completed_todo_items` 파서가 `[!]` prefix를 파싱할 때 어떻게 동작하는지 확인 (현재는 `[!]`를 `- [ ]` 도 `- [x]`도 아닌 기타 라인으로 취급할 수 있음 → 필요 시 파서 보강 필요. 구현 단계에서 결정)
4. `write_project_todo`: documentation 공통 항목은 항상 `[ ]` 유지
5. `write_project_todo`: board에 있는데 todo에 없는 instruction → 무시 (라인 추가 없음)
6. `write_project_todo`: **동일 instruction을 가진 task 2개 중 한 쪽만 completed** → 보수적으로 `[ ]`
7. **`write_project_todo`: 60자 이상 긴 instruction 2개가 앞 60자 동일, 상태 다름 → 각각 올바르게 표기** (safe_id 회귀 방지)
8. `write_project_todo`: instruction에 포함된 공백/개행/특수문자 → 정규화 후 매칭 성공
9. `write_project_todo`: instruction 문자열이 `_clean_text`를 거치면서 실제로 어떻게 저장되는지 round-trip 검증
10. `update_project_board_task`: 상태 전이 후 `.todo.md` 해당 라인 `[x]` 검증
11. `update_project_board_task`: 훅 내부에서 `write_project_todo`가 예외를 던져도 board 쓰기는 성공 + 경고 로그

### 7.2 회귀 테스트
- 기존 `_fallback_next_tasks` 경로 테스트 (board 없는 프로젝트): `.todo.md`만으로 동작해야 함.
- `_todo_fully_completed`: board 우선 유지 확인.
- **`[/]` in_progress 라인 보존**: 재생성 시 in_progress task가 `[ ]`로 덮이지 않고 `[/]` 유지되는지 명시적 검증.

### 7.3 동시성 테스트
- 동일 workspace에 대해 2개 스레드가 서로 다른 task의 `update_project_board_task`를 동시 호출 → 최종 `.todo.md`가 마지막 상태 반영, 중간 스냅샷으로 롤백되지 않음.
- lock 내부 I/O 실패 주입(예: tmpfs 용량 초과) → board는 커밋되고 todo는 경고 후 다음 전이에서 복원.

### 7.4 통합 검증
- `lotto_predictor_v2`에 CLI `sync-todo --dry-run` → 변경 예상 라인 확인
- 실제 `sync-todo` 적용 후 23개 `[x]` + 3개 `[/]` + 10개 `[ ]` 복구 확인
- 다른 프로젝트(현재 `projects/` 하위 전부)에도 적용 후 git diff 리뷰

## 8. Master_Blueprint 갱신 범위

- **§0 빠른 참조**: `af project sync-todo` 서브커맨드 및 파일 추가 시 해당 항목
- **§3 서브시스템**: `project_task_board` ↔ `documentation_policy` 연동 다이어그램 보강, 훅 순서 명시
- **§10 Blast Radius**: `update_project_board_task` → `.todo.md` 추가 쓰기 경로 등록
- **§11 에러 코드**: 없음 (훅 실패는 warning만, 기존 로깅 채널 재사용)
- **§12 변경 이력**: "2026-04-17 .todo.md ↔ board 단방향 동기화 추가 (v2: 전체 문자열 매칭, lock 내부 훅, [/] 보존)" 한 줄

## 9. 롤백 계획 (v2 신규)

### 9.1 코드 롤백
1. `update_project_board_task`에서 `write_project_todo` 호출 라인 제거
2. `write_project_todo` 시그니처에서 `board` 인자 제거 (기본값 `None`이므로 호환 유지도 가능)
3. 관련 테스트 삭제 또는 skip
4. Master_Blueprint §12에 롤백 이력 추가

### 9.2 데이터 롤백
훅이 배포된 뒤 `.todo.md`가 재생성된 상태에서 롤백이 필요할 때:

1. **최근 커밋에 `.todo.md` 변경이 있다면**: `git log --all -- 'projects/*/.todo.md'`로 이전 버전 확인 후 `git checkout <sha> -- <path>`
2. **board로부터 재생성이 목적이라면**: `af project sync-todo <dir>`를 신규 규칙으로 재실행 (이미 v2 상태라면 변경 없음)
3. **완전 초기화가 필요하다면**: `af project sync-todo <dir> --reset`(후속 과제) 또는 수동으로 `write_project_todo(workspace, items, board=None)` 호출해 전체 `[ ]` 재생성

### 9.3 배포 후 장애 대응
- 훅 실행으로 `.todo.md`가 의도치 않게 덮였을 때: §9.2의 (1)로 복원
- 훅이 board lock을 과도하게 점유할 때: 훅 본문을 `try/except` 이후 `if os.getenv("AF_TODO_SYNC", "1") == "0": return`로 감싸 환경 변수 kill-switch 제공 (구현 단계에서 포함 권장)

## 10. 실행 체크리스트 (구현자용)

- [ ] 본 설계 문서 v2 교차검증 재실행 (af-doc-qa + af-critic 병렬) → OK 확인
- [ ] `core/documentation_policy.py`에 `_normalize_instruction`, `_mark_for_status`, `_instruction_status_map`, `write_project_todo` 개정
- [ ] 단위 테스트 7.1의 11개 시나리오 추가 (특히 #7 60자 회귀 방지)
- [ ] `core/project_task_board.py:update_project_board_task`에 lock 내부 훅 연결
- [ ] kill-switch 환경 변수 `AF_TODO_SYNC` 구현 (값이 `"0"`이면 훅 내부에서 즉시 return, 기본은 활성)
- [ ] `[!]` prefix(blocked/failed) 파싱 동작을 `_open_todo_items`/`_completed_todo_items`에서 확인하고 필요 시 파서 보강
- [ ] 동시성 테스트 7.3 추가
- [ ] `af project sync-todo` CLI 서브커맨드 + `--dry-run` 추가
- [ ] 전 프로젝트 `git log -p -- **/.todo.md` 스캔으로 수동 편집 흔적 조사
- [ ] `lotto_predictor_v2` 복구 (dry-run → 실제 실행) 및 결과 git diff 리뷰
- [ ] 나머지 `projects/*/`에 sync-todo 적용
- [ ] Master_Blueprint.md §0/§3/§10/§12 갱신
- [ ] 동일 커밋에 Blueprint + 코드 + 테스트 포함

## 11. Out-of-Scope (후속 과제)

- `documentation_todo_items`에 대한 자동 완료 판정 (예: `architecture.md` 최근 수정 시간 기반)
- 사용자 수동 편집 보존 정책 (옵션 B/D 이행 필요 시)
- `docs/handoff/*.md` 자동 생성/갱신 일관성 점검
- `.todo.md`에 task_id를 주석으로 삽입해 매칭을 instruction 문자열 대신 ID 기반으로 고도화 (현재 방식으로 충분하면 불필요)
- debounce 로직 (실측 후 필요 시)
- `af project sync-todo --reset` 플래그 (board 무시하고 전체 `[ ]` 재생성) — §9.2에서 언급된 완전 초기화 경로, 현 범위에서는 수동 코드 호출로 대체
