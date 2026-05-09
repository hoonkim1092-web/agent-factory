# B2-6 설계: 모듈 단위 상태 granularity (v7)

<!-- created: 2026-04-21 | revised: v2~v5 (doc-qa+critic 반복) v6 (Codex cross-review) v7 (af-critic+af-doc-qa WARN 해소) | author: Claude (design), handoff to Sonnet (implementation) -->

## 변경 이력

- **v1 → v2 (2026-04-21)**:
  - [Critical] `run_board` (orchestrator state_board)에는 tasks/modules 키가 없음 → `load_project_board(workspace)`로 교체
  - [High] `stopped_max_cycles`는 per-module 평가 유지. `_INFRA_STATUSES = {crashed, unknown}`
  - [High] C2는 `board["modules"][i]["status"]` 직접 사용. `module_status_from_board` 별도 함수 제거
  - [High] 테스트 파일 경로 수정
  - [High] 테스트 전략을 board fixture + `_DummyOrchestrator` 확장으로 변경
  - [High] `render_summary`의 workspace 우선순위 명시
  - [Medium] §2.1 status 표 2행 압축

- **v2 → v3 (2026-04-21)**:
  - [High] **핵심 변경: ledger 기록 블록을 `ProjectPipeline._record_ledger_outcomes()` 메서드로 추출** — `pipeline.run()` 내부 `build_project_board`(line 734)의 board overwrite 영향 없이 단위 테스트 가능
  - [High] `_make_board_fixture`에 `"instruction"` 필드 필수 명시 + fixture 생성 후 `assert board["modules"][i]["status"] == expected` 직접 검증 단계 추가
  - [High] `_seen` dedup + 모듈별 outcome 충돌 정책 §5.3 L3로 명시: "동일 (pattern, owner)의 다른 outcome은 먼저 처리된 모듈 기준으로 고정" (의도적 동작)
  - [Medium] `load_project_board`는 내부 catch로 예외 전파 없음 → try/except 분리 (import 실패만 보호)

- **v3 → v4 (2026-04-21)**:
  - [High] §5.3 L3 범위 명확화 — "현재 배치 내 dedup. 이전 실행의 레코드에는 새 배치 카운터가 누산됨" (ledger 전역 고정 아님)
  - [High] §4.1 fixture 검증에 disk roundtrip(`load_project_board` 재로드 후 assert) 추가 — silent false-positive 완전 차단
  - [High] `test_ledger_seen_dedup_first_outcome_wins`에 `pipeline` 인스턴스 초기화 라인 추가
  - [Medium] §5.1 I8 문구 수정 — "예외" 표현 제거, 실제 동작("빈 dict 반환") 명시
  - [Medium] §4.2에 I2(module board 부재) + I3(empty owner) 테스트 2건 추가
  - [Medium] `_make_board_fixture`의 `roles` 중복 제거 (유니크 owner_role 기반)

- **v4 → v5 (2026-04-21, 최종)**:
  - [High] I8 테스트 1건 추가 — `test_ledger_skips_on_empty_board` (board 파일 부재 시 skip 직접 검증)
  - [High] `_render_modules_section`의 `try/except` dead code 제거 — `load_project_board`는 예외 던지지 않음. C2 테스트도 "(board 로드 실패)" 대신 "(모듈 정보 없음)"으로 수정
  - [High] `reset_strategy_ledger` 호출 위치 명확화 — 각 테스트 **시작 시** `tmp_path`로 호출하여 캐시 격리 (기록 전 초기화, 기록 후 재조회는 동일 인스턴스 OK)
  - [Medium] §4.2 테스트 목록을 §7 Handoff checklist와 동일한 **8건**으로 단일화 — `test_ledger_per_module_at_risk` 제거(mixed에 흡수)
  - [Medium] `_make_board_fixture`의 `enumerate(..., 1)` 시작값 명시 — task_id는 `{mod_id}_t1, _t2, ...` 형식 고정

- **v5 → v6 (2026-04-21, af-cross-review Codex 반영)**:
  - [Critical] **Task-level INFRA failure 필터 추가** — board의 task notes가 `"infra_failure:"` 접두사를 가지면 `at_risk` 판정에서 제외
  - [High] **C0 precursor 커밋 추가** — `write_project_board` atomic write
  - [High] **Owner drift 처리** — 모듈 내 task들의 `owner_role`이 module.owner_role과 다르면 skip
  - [High] §5.3에 L4~L6 한계 명시
  - [Medium] 테스트 3건 신규, 총 12건으로 확장

- **v6 → v7 (2026-04-21, af-critic + af-doc-qa WARN 해소)**:
  - [Critical] **INFRA 접두사 집합 확장** — `_INFRA_NOTE_PREFIXES = {"infra_failure:", "lineage_maxed:", "fsa_failed:"}`. `dynamic_orchestrator.py:765, 820`의 `lineage_maxed:`/`fsa_failed:` 경로도 인프라 속성 인지
  - [High] **`detect_owner_drift`에서 review phase task 제외** — `task.get("phase") == "review"`인 task는 다른 role로 주입되므로 drift 판정에서 제외. `_inject_review_tasks_if_needed` 자동 흐름에서 과도 skip 방지
  - [High] **Board 재탐색 O(n²) 최적화** — `_record_ledger_outcomes` 시작 시 `task_map`, `module_map`을 한 번 빌드하고 `module_outcome_from_board`/`detect_owner_drift`가 이를 재사용 (헬퍼 시그니처 확장)
  - [Medium] C0 코드 주석에 `BOARD_FILENAME = "project_board_state.json"` (서브디렉토리 없음, `dir_=workspace`) 명시
  - [Medium] §5.1 I10(C2 불변식) 문구 수정 — "load_project_board는 `{}` 반환하므로 예외 경로 제거. board 비어있으면 `(모듈 정보 없음)`"으로 일관
  - [WARN] §3 §C1 "2. 테스트" 목록 **12건으로 동기화** (§7 handoff와 일치)
  - [WARN] `logger.warning` vs `logger.info` 레벨 일관 — owner drift는 `warning`, INFRA skip은 `info`로 확정
  - [WARN] `reset_strategy_ledger` 호출 위치 — **모든 테스트의 첫 줄**로 통일

---

## 0. 요약

세 개의 커밋으로 분리 (C0 precursor + C1 bug fix + C2 enhancement).

| 커밋 | 대상 | 성격 | 파일 |
|------|------|------|------|
| **C0** (atomic write) | `write_project_board` atomic 보장 | 데이터 무결성 precursor | `core/project_task_board.py` |
| **C1** (B2-6 fix) | strategy ledger 기록 정확도 | 버그 fix | `core/project_pipeline.py`, `core/project_task_board.py` (helper) |
| **C2** (summary enhancement) | nightly summary 모듈 뷰 | 가시성 enhancement | `scripts/nightly_summary.py` |

**공통 데이터 소스:** `core/project_task_board.py:load_project_board(workspace)` — C0이 atomic write 보장 후, 이 함수가 반환하는 board는 `_recalculate_board`를 통해 각 `module["status"]`가 자동 계산되어 있다.

**핵심 주의:** `module["status"]`는 `_module_status(tasks)`로 계산되며, **INFRA failure task를 필터링하지 않는다**. B2-6 fix는 별도 헬퍼 `_module_outcome_from_board(board, module_id)`를 도입해 INFRA failure(task notes의 `"infra_failure:"` 접두사)를 제외한 판정을 수행한다 — §2.2 참조.

---

## 1. 문제 정의

### 1.1 B2-6 (C1) — Ledger 오염

**Appendix B 원문** (`docs/2026-04-19-review-gate-enforcement.md:643`):
> `core/project_pipeline.py:963, 971-981` Medium — 프로젝트 전역 `status`로 전 모듈에 일괄 fail 기록 → 정상 모듈도 패널티

**현재 코드** (`core/project_pipeline.py:973`):
```python
_succeeded = status == "completed"
# 모든 모듈에 _succeeded 일괄 적용
```

**문제 증명:**
- `status`는 orchestrator `state_board["current_status"]`
  (`core/dynamic_orchestrator.py:1010-1035`)
- 가능 값: `{"running", "stopped_max_cycles", "partial", "completed", "crashed"}` + `"unknown"` (fallback)
- `completed` 외는 전부 fail로 기록되어 실제로 성공한 모듈도 ledger에서 fail
- 인프라 실패(`crashed`)는 역할 적합성과 무관한데도 pass/fail 카운터에 계산

**오염 경로:**
1. ledger pass/fail 누적 → `lookup_best_role` score = pass / (pass + fail)
2. score < 0.5인 role은 `_pick_owner_role`에서 필터링
3. 반복될수록 "올바른 role이 배제"되는 cascade

### 1.2 Summary 모듈 뷰 부재 (C2)

**현재 `.af/nightly_summary.md`** (`scripts/nightly_summary.py:50-69`):
- Watchdog level, budget, active_assignments, lineage_counters

**누락:**
- 모듈별 완료 집계 (5/10 completed)
- blocker 모듈 명시 (어떤 모듈이 N tick째 움직이지 않는가)

**근거** (design doc §I5, `docs/2026-04-18-nightly-autonomous-pipeline.md:81`):
> `.af/state_snapshot.json`, `.af/nightly_summary.md`, `.af/board_state.json` 세 파일만으로 **무엇이 걸려 있는지** 재구성 가능

현재 summary는 watchdog·budget만 표시하여 이 요구사항 미달.

---

## 2. 설계 — Contract & Invariants

### 2.1 C1 — Ledger 기록 규칙

**전역 status 분기 (2행):**

| 전역 status | Ledger 처리 | 이유 |
|------------|------------|------|
| `crashed`, `unknown` | **전체 skip** (`_INFRA_STATUSES`) | 인프라 실패 또는 불확실 결과. 역할 적합성 정보 아님 |
| `completed`, `partial`, `stopped_max_cycles` | **모듈별 평가** | orchestration이 어떤 형태로든 종료됨. 각 모듈의 task 결과로 판정 |

**모듈별 결정 (3-value + 추가 필터):**

`module["status"]`는 `_module_status()` 기반으로 `_recalculate_board`가 계산하는데, INFRA failure task를 구분하지 않는다. B2-6 fix는 **신규 헬퍼** `_module_outcome_from_board(board, module_id) -> "completed" | "at_risk" | "skip"`를 도입해 다음을 수행:

1. `module["task_ids"]`의 각 task를 `board["tasks"]`에서 조회
2. **INFRA failure 필터:** task의 notes가 `"infra_failure:"` 접두사를 포함하면 해당 task는 무시 (status 집계에서 제외)
3. 필터링된 task 집합으로 outcome 판정:

| 필터링 후 상태 | Ledger 액션 | 근거 |
|-------------|------------|------|
| 모두 `completed` | `record_role_success` | 역할 배정 성공 확정 |
| 최소 1개 `failed` (INFRA 외) | `record_role_failure` | 역할 배정 실패 확정 |
| 그 외 (in_progress/pending 포함) | **skip** | 결과 미정 또는 모두 INFRA 실패로 제외됨 |

**Owner drift 가드 (High 3 대응):**

`_record_ledger_outcomes`는 ledger 기록 전 각 모듈에 대해 `_detect_owner_drift(module, board_tasks)`를 호출:
- 모듈의 (INFRA 외) task들의 `owner_role` 집합이 `module["owner_role"]` 단일값인지 확인
- 드리프트 감지 시 해당 모듈을 skip + warning log

**오케스트레이터 → board 동기화 보장:**

`dynamic_orchestrator.py:745-748` — INFRA failure는 `update_project_board_task(..., "failed", note=f"infra_failure: {reason}", ...)`로 기록. B2-6 필터는 이 note를 식별. 다른 task 실패는 `note`가 `"infra_failure:"`로 시작하지 않음.

### 2.2 데이터 흐름 (C1)

```
orchestrator.run_project(...)
    ↓
state_board (current_status만 의미)
    ↓
project_pipeline.execute() — status = state_board["current_status"]
    ↓
if status in _INFRA_STATUSES:
    log.info("ledger skip — infra failure")
    return
    ↓
board = load_project_board(workspace)   # _recalculate_board로 module.status 자동 계산됨
    ↓
for module in prepared.role_plan.modules:   # 계획 시점 모듈 목록
    mod_in_board = board.modules.find(id=module.id)
    if not mod_in_board:
        skip  # board에 없는 모듈은 결과 알 수 없음
    match mod_in_board.status:
        "completed" → record_role_success (pattern, owner)
        "at_risk"   → record_role_failure (pattern, owner)
        else        → skip
```

**중요:** `prepared.role_plan.modules`는 계획 시점 스냅샷, `board["modules"]`는 실행 후 상태. 두 리스트의 id 집합은 일반적으로 동일하지만, 사용자가 approval 후 work-item을 편집해 새 task(`module_id=""`)가 추가된 경우 `prepared.role_plan.modules`에 없던 항목이 board에 존재할 수 있다. 이 경우는 학습 대상 외로 skip한다 (기존 B2-4 fix 정책 유지).

### 2.0 C0 Precursor — `write_project_board` atomic write

**문제:** 현재 `write_project_board`(line 574-577)가 `write_text`(`core/file_io.py:117-120`, non-atomic)를 사용. crash 중 partial write 시 JSON 파싱 실패 → `load_project_board` `{}` 반환 → C1이 조용히 skip.

**수정:** `project_pipeline.py:_write_json`과 동일한 tempfile + os.replace 패턴 적용:

```python
# core/project_task_board.py (write_project_board 교체)
# BOARD_FILENAME = "project_board_state.json" (line 15 정의, 서브디렉토리 없음)
# 따라서 dir_ = os.path.abspath(workspace) (workspace 루트)

def write_project_board(workspace: str, board: dict[str, Any]) -> str:
    import tempfile
    path = os.path.join(os.path.abspath(workspace), BOARD_FILENAME)
    dir_ = os.path.dirname(path) or "."  # = os.path.abspath(workspace)
    os.makedirs(dir_, exist_ok=True)
    payload = json.dumps(_recalculate_board(dict(board or {})), ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path
```

**테스트:** `tests/test_project_task_board.py` 또는 `_dispatch.py`에 1건:
```python
def test_write_project_board_atomic_on_crash(tmp_path, monkeypatch):
    """write 도중 os.replace 실패 시 tempfile 정리 확인."""
    # mkstemp→write 성공 후 os.replace가 raise하도록 patch → board 파일 미생성 + tempfile 정리 확인
```

**C0 커밋 메시지:** `fix(board): write_project_board atomic write — crash-safe JSON persistence`

---

### 2.3 C1 기록 로직 — 메서드 추출 (refactor + fix)

**`core/project_pipeline.py` 변경:**

1. 기존 line 967-1004 블록을 `ProjectPipeline._record_ledger_outcomes()` 메서드로 추출
2. `execute()`에서는 단일 호출로 대체

**새 헬퍼 (core/project_task_board.py 추가):**

```python
# core/project_task_board.py (line 148 이후 위치)

# v7: INFRA 접두사 집합 확장 — dynamic_orchestrator가 사용하는 모든 인프라성 note 패턴
_INFRA_NOTE_PREFIXES: tuple[str, ...] = (
    "infra_failure:",   # dynamic_orchestrator.py:747 (quota, auth 등)
    "lineage_maxed:",   # dynamic_orchestrator.py:765 (lineage 상한 강제 degrade)
    "fsa_failed:",      # dynamic_orchestrator.py:822 (FSA 루프 복구 실패, 인프라성 재시도 소진)
)


def _task_is_infra_failure(task: dict) -> bool:
    """task의 notes가 INFRA 접두사 중 하나를 포함하면 True.

    notes 필드 타입 규약 (`update_project_board_task` 기준, core/project_task_board.py:707-708):
      - 기본적으로 list[str] (`task["notes"] = _clean_list(task.get("notes")) + [note]`)
      - 방어적으로 str 단일 케이스도 허용 (레거시/테스트 fixture)
    """
    notes = task.get("notes")
    candidates: list[str] = []
    if isinstance(notes, list):
        candidates = [n for n in notes if isinstance(n, str)]
    elif isinstance(notes, str):
        # 레거시 호환 — 현 생산 코드 경로는 list지만 테스트 fixture가 str을 쓸 수 있음
        candidates = [notes]
    for n in candidates:
        stripped = n.strip()
        if any(stripped.startswith(p) for p in _INFRA_NOTE_PREFIXES):
            return True
    return False


def _build_board_maps(board: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    """board를 한 번 스캔하여 task_map, module_map을 빌드한다 (O(n) 1회).

    B2-6 v7: module_outcome_from_board + detect_owner_drift가 이를 공유하여
    outer loop에서 O(n²) 재탐색을 피한다.
    """
    if not isinstance(board, dict):
        return {}, {}
    task_map = {
        str(t.get("task_id") or ""): t
        for t in (board.get("tasks") or [])
        if isinstance(t, dict) and t.get("task_id")
    }
    module_map = {
        str(m.get("id") or ""): m
        for m in (board.get("modules") or [])
        if isinstance(m, dict) and m.get("id")
    }
    return task_map, module_map


def module_outcome_from_board(
    board: dict, module_id: str,
    task_map: dict[str, dict] | None = None,
    module_map: dict[str, dict] | None = None,
) -> str:
    """INFRA failure task를 필터링한 모듈 outcome 반환.

    반환값: "completed" | "at_risk" | "skip"
    task_map/module_map이 주어지면 재사용 (O(n²) 회피). 없으면 내부에서 빌드.
    """
    if not isinstance(board, dict) or not module_id:
        return "skip"
    if task_map is None or module_map is None:
        task_map, module_map = _build_board_maps(board)

    mod = module_map.get(module_id)
    if not mod:
        return "skip"
    module_tasks = [
        task_map[str(tid)] for tid in (mod.get("task_ids") or [])
        if str(tid) in task_map
    ]
    if not module_tasks:
        return "skip"

    non_infra = [t for t in module_tasks if not _task_is_infra_failure(t)]
    if not non_infra:
        return "skip"

    statuses = {str(t.get("status") or "pending") for t in non_infra}
    if statuses == {"completed"}:
        return "completed"
    if "failed" in statuses:
        return "at_risk"
    return "skip"


def detect_owner_drift(
    module: dict, board: dict,
    task_map: dict[str, dict] | None = None,
) -> bool:
    """모듈 내 (INFRA·review 외) task의 owner_role이 module.owner_role과 일치하는지 확인.

    반환값: True = drift 감지(학습 skip 권장), False = 일관
    - review phase task는 `_inject_review_tasks_if_needed`가 자동 주입하며
      다른 role로 설정 가능 → drift 판정에서 제외 (v7)
    """
    mod_owner = str(module.get("owner_role") or "")
    if not mod_owner:
        return False
    if task_map is None:
        task_map, _ = _build_board_maps(board)
    for tid in (module.get("task_ids") or []):
        t = task_map.get(str(tid))
        if not t:
            continue
        if _task_is_infra_failure(t):
            continue
        # v7.1: 실제 review task의 phase 값은 "code_review" 또는 "cross_validate"
        # (core/project_task_board.py:943, 977 inject_review_tasks 참조)
        if str(t.get("phase") or "") in {"code_review", "cross_validate"}:
            continue  # auto-injected review task 제외
        task_owner = str(t.get("owner_role") or "")
        if task_owner and task_owner != mod_owner:
            return True
    return False
```

**새 메서드 시그니처 (core/project_pipeline.py):**

```python
def _record_ledger_outcomes(
    self,
    status: str,
    role_plan: dict,
    workspace: str,
) -> None:
    """프로젝트 실행 후 strategy ledger에 모듈별 outcome을 기록한다.

    - status in {crashed, unknown} → 전체 skip
    - 그 외: board 로드 → 모듈별 module_outcome_from_board + detect_owner_drift 판정
    - 단위 테스트 용이성을 위해 인스턴스 메서드로 추출 (B2-6 v3)
    """
    _INFRA_STATUSES = {"crashed", "unknown"}
    if status in _INFRA_STATUSES:
        logger.info("strategy ledger 기록 skip — 인프라/불확실 실패 (status=%s)", status)
        return

    try:
        from core.memory_system.strategy_ledger import get_strategy_ledger
        from core.project_task_board import (
            load_project_board,
            module_outcome_from_board,
            detect_owner_drift,
            _build_board_maps,
        )
    except Exception as exc:
        logger.warning("strategy ledger/board import 실패: %s", exc)
        return

    # load_project_board는 내부 catch로 항상 dict 반환 (예외 전파 없음)
    board = load_project_board(workspace)
    if not board:
        logger.info("strategy ledger 기록 skip — board 비어있음")
        return

    # v7 최적화: board를 한 번만 스캔하여 맵 빌드 (O(n) 1회)
    task_map, module_map = _build_board_maps(board)

    ledger = get_strategy_ledger(workspace)
    project_id = os.path.basename(workspace)

    batch: list[tuple[str, str, str, bool]] = []
    seen: set[tuple[str, str]] = set()  # (pattern, owner) 배치 dedup (B2-4 유지)

    for mod in (role_plan.get("modules") or []):
        owner = str(mod.get("owner_role") or "")
        if not owner:
            continue  # I3
        mid = str(mod.get("id") or "")
        if mid not in module_map:
            continue  # I2: board에 없는 모듈

        outcome_label = module_outcome_from_board(
            board, mid, task_map=task_map, module_map=module_map,
        )
        if outcome_label == "completed":
            outcome = True
        elif outcome_label == "at_risk":
            outcome = False
        else:
            continue  # skip (in_progress/pending/전부 INFRA)

        # Owner drift 가드 (v7: task_map 재사용 + review phase 제외)
        board_module = module_map.get(mid)
        if board_module and detect_owner_drift(board_module, board, task_map=task_map):
            logger.warning(  # v7: drift는 이상 조건이므로 warning
                "strategy ledger skip — owner drift 감지 (module=%s, plan_owner=%s)",
                mid, owner,
            )
            continue

        for raw in [str(mod.get("name") or "")] + list(mod.get("deliverables") or []):
            words = str(raw).strip().lower().split()
            dp = " ".join(words[:4]).strip()
            if dp and (dp, owner) not in seen:
                seen.add((dp, owner))
                batch.append((dp, owner, project_id, outcome))

    if batch:
        try:
            ledger.record_role_batch(batch)
        except Exception as exc:
            logger.warning("strategy ledger 배치 기록 실패: %s", exc)
```

**`execute()` 호출부 (기존 967-1004 블록 교체):**

```python
        status = str(run_board.get("current_status", "unknown"))

        # ── strategy ledger: 모듈별 outcome 기록 (B2-6) ──────────────
        self._record_ledger_outcomes(
            status=status,
            role_plan=prepared.role_plan,
            workspace=workspace,
        )

        append_dashboard_run(...)  # 기존 그대로
```

**핵심 이점:**
- `_record_ledger_outcomes`는 `ProjectPipeline` 인스턴스 메서드이므로 단위 테스트에서 `pipeline._record_ledger_outcomes(status="crashed", role_plan={...}, workspace=str(tmp_path))` 형식으로 직접 호출 가능
- `pipeline.run()` 전체를 돌리지 않아 `build_project_board`의 board overwrite 영향 없음
- fixture로 준비한 board 파일이 그대로 살아남음

**B2-4 fix 보존 항목:**
- `record_role_batch` 사용
- `seen` 배치 전체 (pattern, owner) 중복 제거
- 앞 4단어 절삭 패턴 정규화
- owner 미배정 모듈 skip

### 2.4 C2 — Summary 렌더 확장

**`scripts/nightly_summary.py:render_summary`에 섹션 추가:**

```markdown
## 모듈별 상태

| 상태 | 모듈 | 담당 Role | Tasks |
|------|------|----------|-------|
| ✅ completed | api_server | backend_dev | 3/3 |
| 🔄 in_progress | ui_frontend | frontend_dev | 1/3 |
| ⏸ pending | qa_integration | qa_engineer | 0/2 |
| ⚠️ at_risk | data_pipeline | backend_dev | 2/4 (1 failed) |

- **완료**: 1/4
- **진행 중**: 1/4
- **대기**: 1/4
- **위험**: 1/4
```

**데이터 소스 + workspace 우선순위:**

```python
def render_summary(state: NightlyState, workspace: str | Path | None = None) -> str:
    ...
    # board 로드용 경로 — 호출자가 명시적으로 넘긴 workspace 우선, 없으면 state.active_workspace
    ws_for_board = workspace or state.active_workspace
    modules_section = _render_modules_section(ws_for_board)  # 내부에서 load_project_board 호출
```

**`_render_modules_section(ws: str | Path | None) -> str`:**

```python
def _render_modules_section(workspace: str | Path | None) -> str:
    from core.project_task_board import load_project_board
    if not workspace:
        return "## 모듈별 상태\n\n(프로젝트 비활성)\n"
    # load_project_board는 예외를 내부 catch하고 {} 반환 — try/except 불필요
    board = load_project_board(str(workspace))
    modules = board.get("modules") or []
    if not modules:
        return "## 모듈별 상태\n\n(모듈 정보 없음)\n"
    tasks_by_id = {
        str(t.get("task_id") or ""): t
        for t in (board.get("tasks") or [])
        if isinstance(t, dict)
    }
    # 이모지/상태별 카운터 + 테이블 렌더
    ...
```

**이모지 매핑:**

| status | emoji | 표시 |
|--------|-------|------|
| completed | ✅ | ✅ completed |
| in_progress | 🔄 | 🔄 in_progress |
| at_risk | ⚠️ | ⚠️ at_risk |
| pending | ⏸ | ⏸ pending |
| (기타) | ❓ | ❓ unknown |

**Task 진행률:** 각 module의 `task_ids`를 순회하며 `tasks_by_id`에서 status 집계. at_risk 모듈은 "2/4 (1 failed)" 형식으로 실패 수 명시.

---

## 3. 구현 순서

### C1 (B2-6 fix)

1. **`core/project_pipeline.py`**
   - line 967-1004 블록을 §2.3 의사 코드로 교체
   - 파일 상단 import 추가: `from core.project_task_board import load_project_board` (함수 내부 lazy import 권장 — 순환 참조 회피)

2. **테스트 (v7: 12건, §7 handoff와 일치)**
   - 기존 파일 `tests/test_project_task_board_dispatch.py`가 있으나 이번 변경은 board 읽기에만 의존 → 신규 통합 테스트는 `tests/test_strategy_ledger.py`에 추가
   - 추가 테스트 (§4.2) — 12건 전체 목록은 §7 Handoff Checklist 참조. 각 테스트의 **첫 줄**에 `reset_strategy_ledger(str(tmp_path))` 호출 필수

3. **회귀 확인**
   - `tests/test_project_pipeline.py::test_project_pipeline_writes_planning_artifacts_and_roles`가 `_DummyOrchestrator`를 사용하는데, 이 dummy는 현재 `{"current_status": "completed"}`만 반환.
   - C1 이후 코드는 `load_project_board(workspace)`를 호출 → `_DummyOrchestrator.run_project`가 workspace를 받아도 board 파일은 실제 orchestration에서 `update_project_board_task`로 쓰여짐
   - 테스트 케이스에서는 board 파일이 미리 `build_project_board` + `write_project_board`로 작성되므로 load 가능. 다만 module status가 `pending` 상태이면 ledger 기록이 0건이 될 수 있음 → 기존 테스트가 ledger 결과를 assert하지 않으면 무영향
   - **구현자 확인 필수:** `test_project_pipeline.py`가 ledger 상태를 assert하는지 검토. 만약 assert하면 fixture에서 board task status를 "completed"로 업데이트해야 함.

4. **Blueprint**
   - §3.1 ProjectPipeline 핵심 내부 흐름에 "모듈별 status로 ledger 기록 판정 (B2-6 fix)" 한 줄 추가
   - §12: `2026-04-21 | fix(B2-6): strategy ledger 모듈별 granularity — status=crashed/unknown skip, 모듈별 3-value 판정`

5. **Review-gate**: tier 1→2→3 완주

6. **커밋 메시지:**
   ```
   fix(B2-6): strategy ledger 모듈별 granularity

   - project_pipeline.py: 전역 status 단일 플래그 → 모듈별 3-value 판정
   - crashed/unknown은 infra 실패로 skip
   - completed/partial/stopped_max_cycles는 board.modules[i].status 기반 평가
   - tests/test_strategy_ledger.py: 통합 테스트 6건 추가
   ```

### C2 (Summary enhancement)

1. **`scripts/nightly_summary.py`**
   - `_render_modules_section(workspace)` 함수 추가 (§2.4 의사 코드)
   - `render_summary`에서 `## 진행 중 태스크` 섹션 뒤에 삽입
   - `ws_for_board = workspace or state.active_workspace` 우선순위 적용

2. **테스트 — `tests/test_nightly_summary.py` 신규**
   - `test_render_summary_no_workspace`: workspace=None, state.active_workspace=None → "(프로젝트 비활성)"
   - `test_render_summary_no_board`: workspace 있으나 `project_board_state.json` 없음 → "(board 로드 실패: ...)" 또는 "(모듈 정보 없음)"
   - `test_render_summary_modules_mix`: board fixture 작성 후 ✅/🔄/⏸/⚠️ 모두 포함 확인 + 집계 정확도
   - `test_render_summary_workspace_priority`: 호출자 `workspace` 파라미터가 `state.active_workspace`보다 우선 적용됨

3. **Blueprint**
   - §0 또는 §3.1의 scripts/nightly_summary 라인에 "모듈별 상태 섹션" 언급
   - §12: `2026-04-21 | feat(summary): nightly summary 모듈별 상태 섹션`

4. **Review-gate**: tier 1→2→3 완주

5. **커밋 메시지:**
   ```
   feat(summary): nightly summary 모듈별 상태 섹션

   - _render_modules_section: load_project_board → module.status 집계
   - workspace 우선순위: param > state.active_workspace
   - 엣지케이스: 비활성 프로젝트, 보드 부재, 모듈 없음
   - tests/test_nightly_summary.py: 4건 테스트 신규
   ```

---

## 4. 테스트 전략

### 4.1 Board fixture 헬퍼

```python
# tests/test_strategy_ledger.py
def _make_board_fixture(workspace: Path, modules_spec: list[dict]) -> dict:
    """board 파일을 workspace에 작성하고 board dict를 반환.

    modules_spec 예:
    [
        {"id": "ma", "owner_role": "backend", "name": "API server",
         "deliverables": ["REST endpoint"], "task_statuses": ["completed", "completed"]},
        {"id": "mb", "owner_role": "frontend",
         "deliverables": ["UI"], "task_statuses": ["failed", "pending"]},
    ]

    주의:
    - 모든 task에 "title"과 "instruction" 필드가 반드시 있어야 board에서 필터링되지 않음
      (build_project_board:508의 `if not task["task_id"] or not task["instruction"]: continue`)
    - 호출자는 반환된 board를 검증하여 module.status가 기대대로 설정되었는지 assert해야 함
      (silent false-positive 방지)
    """
    from core.project_task_board import (
        build_project_board,
        write_project_board,
    )
    # roles 리스트는 유니크 owner_role로 구성 (중복 제거)
    _unique_owners = []
    _seen_owners: set = set()
    for s in modules_spec:
        if s["owner_role"] and s["owner_role"] not in _seen_owners:
            _seen_owners.add(s["owner_role"])
            _unique_owners.append({"id": s["owner_role"], "name": s["owner_role"]})
    role_plan = {
        "execution_strategy": "sequential",
        "roles": _unique_owners,
        "modules": [
            {
                "id": s["id"],
                "name": s.get("name", s["id"]),
                "owner_role": s["owner_role"],
                "deliverables": s.get("deliverables", []),
                "tasks": [
                    {
                        "id": f"{s['id']}_t{i}",
                        "title": f"{s['id']} task {i}",
                        "instruction": f"do {s['id']} task {i}",  # 필수 — 빈 문자열이면 탈락
                        "owner_role": s["owner_role"],
                        "phase": "build",
                        "status": status,
                    }
                    for i, status in enumerate(s["task_statuses"], 1)
                ],
            }
            for s in modules_spec
        ],
    }
    board = build_project_board({"goal": "test"}, role_plan)
    write_project_board(str(workspace), board)
    return board  # 호출자 검증용
```

**필수 검증 패턴 (silent false-positive 방지):**

```python
def test_ledger_per_module_completed(tmp_path):
    board = _make_board_fixture(tmp_path, [
        {"id": "ma", "owner_role": "backend", "deliverables": ["api"],
         "task_statuses": ["completed"]},
    ])
    # 1) fixture의 in-memory 결과 검증
    ma_mod = next(m for m in board["modules"] if m["id"] == "ma")
    assert ma_mod["status"] == "completed", f"fixture 오류: ma status={ma_mod['status']}"

    # 2) disk roundtrip 검증 — _record_ledger_outcomes가 실제로 호출할 경로
    from core.project_task_board import load_project_board
    reloaded = load_project_board(str(tmp_path))
    assert reloaded, "write/load roundtrip 실패"
    reloaded_ma = next(m for m in reloaded["modules"] if m["id"] == "ma")
    assert reloaded_ma["status"] == "completed", f"disk roundtrip 후 status 유실: {reloaded_ma['status']}"

    # 3) 이제 실제 테스트 로직 진행
    ...
```

**중요:** 1)만 검증하면 `_clean_text`, `json.dumps/load`, `_recalculate_board` 재호출 경로에서 status가 변조될 때 감지 못함. 반드시 2)를 포함해 `_record_ledger_outcomes`가 읽을 실제 데이터와 동일한 경로를 검증할 것.

### 4.2 C1 단위 테스트 (`tests/test_strategy_ledger.py`)

**테스트 전략 변경 (v3):** `pipeline.run()` 전체를 돌리지 않고 추출된 `_record_ledger_outcomes` 메서드를 직접 호출. board는 `_make_board_fixture`로 준비, role_plan은 테스트 내에서 직접 구성.

```python
def _make_role_plan(modules_spec: list[dict]) -> dict:
    """_record_ledger_outcomes에 전달할 role_plan을 생성."""
    return {
        "modules": [
            {
                "id": s["id"],
                "name": s.get("name", s["id"]),
                "owner_role": s["owner_role"],
                "deliverables": s.get("deliverables", []),
            }
            for s in modules_spec
        ],
    }


def test_ledger_skips_on_crashed(tmp_path):
    """status='crashed' → record 0건 (I1)."""
    from core.project_pipeline import ProjectPipeline
    from core.memory_system.strategy_ledger import reset_strategy_ledger
    reset_strategy_ledger(str(tmp_path))  # 테스트 시작 시 캐시 격리
    pipeline = ProjectPipeline(mr=None, agent_mgr=None, research_agent=None, procurer=None)

    _make_board_fixture(tmp_path, [
        {"id": "ma", "owner_role": "backend", "deliverables": ["api"],
         "task_statuses": ["completed"]},
    ])
    role_plan = _make_role_plan([
        {"id": "ma", "owner_role": "backend", "deliverables": ["api"]},
    ])

    pipeline._record_ledger_outcomes(
        status="crashed", role_plan=role_plan, workspace=str(tmp_path),
    )
    ledger_path = tmp_path / "memory" / "episodes" / "strategy_ledger.json"
    assert not ledger_path.exists() or json.loads(ledger_path.read_text())["role_assignments"] == []


def test_ledger_skips_on_unknown(tmp_path):
    """status='unknown' → record 0건 (I1). 위 crashed와 동일 fixture, status만 다름."""
    # test_ledger_skips_on_crashed의 body 복제 + status='unknown'


def test_ledger_skips_on_empty_board(tmp_path):
    """board 파일 부재 → load_project_board가 {} 반환 → skip (I8)."""
    from core.project_pipeline import ProjectPipeline
    from core.memory_system.strategy_ledger import reset_strategy_ledger, get_strategy_ledger
    reset_strategy_ledger(str(tmp_path))
    pipeline = ProjectPipeline(mr=None, agent_mgr=None, research_agent=None, procurer=None)

    # board 파일 미생성 — tmp_path에 project_board_state.json 없음
    role_plan = _make_role_plan([
        {"id": "m1", "owner_role": "backend", "deliverables": ["x"]},
    ])
    pipeline._record_ledger_outcomes(
        status="partial", role_plan=role_plan, workspace=str(tmp_path),
    )
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}

def test_ledger_per_module_completed(tmp_path):
    """partial + 모듈 A completed + 모듈 B failed → A만 pass, B만 fail."""
    from core.project_pipeline import ProjectPipeline
    pipeline = ProjectPipeline(mr=None, agent_mgr=None, research_agent=None, procurer=None)

    board = _make_board_fixture(tmp_path, [
        {"id": "ma", "owner_role": "backend", "deliverables": ["api server"],
         "task_statuses": ["completed", "completed"]},
        {"id": "mb", "owner_role": "frontend", "deliverables": ["ui"],
         "task_statuses": ["failed", "pending"]},
    ])
    # fixture 검증 (silent false-positive 방지)
    assert next(m for m in board["modules"] if m["id"] == "ma")["status"] == "completed"
    assert next(m for m in board["modules"] if m["id"] == "mb")["status"] == "at_risk"

    role_plan = _make_role_plan([
        {"id": "ma", "owner_role": "backend", "deliverables": ["api server"]},
        {"id": "mb", "owner_role": "frontend", "deliverables": ["ui"]},
    ])
    pipeline._record_ledger_outcomes(
        status="partial", role_plan=role_plan, workspace=str(tmp_path),
    )

    from core.memory_system.strategy_ledger import get_strategy_ledger, reset_strategy_ledger
    reset_strategy_ledger(str(tmp_path))  # 캐시 클리어
    ledger = get_strategy_ledger(str(tmp_path))
    # backend는 "api server" 패턴으로 pass 기록
    key_backend = "api server::backend"
    assert ledger._role_assignments[key_backend].pass_count == 1
    # frontend는 "ui" 패턴으로 fail 기록
    key_frontend = "ui::frontend"
    assert ledger._role_assignments[key_frontend].fail_count == 1


def test_ledger_skips_pending_module(tmp_path):
    """stopped_max_cycles + 모듈 전부 pending → 기록 0건."""
    # fixture의 task status를 모두 pending으로
    # 호출 후 ledger 비어있음 assert


def test_ledger_mixed_module_status(tmp_path):
    """completed + at_risk + pending 모듈 혼재 → completed만 pass, at_risk만 fail, pending skip."""
    # 3종 모듈 fixture + role_plan + 호출
    # 3건 중 2건만 기록됨 assert


def test_ledger_seen_dedup_first_outcome_wins(tmp_path):
    """동일 (pattern, owner)가 두 모듈에 걸쳐 다른 outcome일 때 먼저 처리된 쪽이 배치에 포함됨 (L3).

    주의: L3는 **현재 배치 내** 중복 제거 정책. 이전 실행에서 쌓인 카운터에는 영향 없음.
    """
    from core.project_pipeline import ProjectPipeline
    pipeline = ProjectPipeline(mr=None, agent_mgr=None, research_agent=None, procurer=None)

    _make_board_fixture(tmp_path, [
        {"id": "m_a", "owner_role": "backend", "deliverables": ["api v1"],
         "task_statuses": ["completed"]},
        {"id": "m_b", "owner_role": "backend", "deliverables": ["api v1"],
         "task_statuses": ["failed"]},
    ])
    role_plan = _make_role_plan([
        {"id": "m_a", "owner_role": "backend", "deliverables": ["api v1"]},
        {"id": "m_b", "owner_role": "backend", "deliverables": ["api v1"]},
    ])
    pipeline._record_ledger_outcomes(
        status="partial", role_plan=role_plan, workspace=str(tmp_path),
    )
    reset_strategy_ledger(str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments["api v1::backend"].pass_count == 1
    assert ledger._role_assignments["api v1::backend"].fail_count == 0


def test_ledger_module_missing_in_board(tmp_path):
    """role_plan에는 있지만 board의 modules에 없는 모듈 → skip (I2)."""
    from core.project_pipeline import ProjectPipeline
    pipeline = ProjectPipeline(mr=None, agent_mgr=None, research_agent=None, procurer=None)

    _make_board_fixture(tmp_path, [
        {"id": "in_board", "owner_role": "backend", "deliverables": ["api"],
         "task_statuses": ["completed"]},
    ])
    # role_plan에 board 없는 모듈 "ghost" 추가
    role_plan = _make_role_plan([
        {"id": "in_board", "owner_role": "backend", "deliverables": ["api"]},
        {"id": "ghost", "owner_role": "qa", "deliverables": ["phantom test"]},
    ])
    pipeline._record_ledger_outcomes(
        status="partial", role_plan=role_plan, workspace=str(tmp_path),
    )
    reset_strategy_ledger(str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    # in_board는 기록, ghost는 skip
    assert "api::backend" in ledger._role_assignments
    assert not any(k.endswith("::qa") for k in ledger._role_assignments)


def test_ledger_empty_owner_role_skip(tmp_path):
    """owner_role 빈 문자열 → skip (I3)."""
    from core.project_pipeline import ProjectPipeline
    pipeline = ProjectPipeline(mr=None, agent_mgr=None, research_agent=None, procurer=None)

    _make_board_fixture(tmp_path, [
        {"id": "m1", "owner_role": "backend", "deliverables": ["api"],
         "task_statuses": ["completed"]},
    ])
    # role_plan에서 m1의 owner_role을 빈 문자열로
    role_plan = {
        "modules": [
            {"id": "m1", "owner_role": "", "name": "M1", "deliverables": ["api"]},
        ],
    }
    pipeline._record_ledger_outcomes(
        status="completed", role_plan=role_plan, workspace=str(tmp_path),
    )
    reset_strategy_ledger(str(tmp_path))
    ledger = get_strategy_ledger(str(tmp_path))
    assert ledger._role_assignments == {}
```

**`_DummyOrchestrator` 확장 불필요:** `_record_ledger_outcomes`를 직접 호출하므로 orchestrator mock 필요 없음.

**기존 `test_project_pipeline.py::test_project_pipeline_writes_planning_artifacts_and_roles` 회귀:**
- ledger assert 없음 확인됨 → C1 변경은 무영향
- 다만 pipeline.run() 이후 `_record_ledger_outcomes`가 호출될 때 `load_project_board(workspace)`가 방금 `write_project_board`로 쓴 board를 읽고, 그 board의 task status는 `_DummyOrchestrator`가 업데이트하지 않은 `pending` 상태 → 모든 모듈 `pending` → 기록 0건. 기존 동작은 전역 `status="completed"`로 일괄 pass 기록이었던 반면 이제는 board 기반으로 0건이 됨. **기존 테스트의 ledger assert가 없으므로 무영향이지만, 향후 기존 테스트를 수정할 때 주의.**

### 4.3 C2 테스트 (`tests/test_nightly_summary.py` 신규)

```python
def test_render_summary_no_workspace():
    state = NightlyState()  # active_workspace=None
    out = render_summary(state, workspace=None)
    assert "(프로젝트 비활성)" in out

def test_render_summary_modules_mix(tmp_path):
    _make_board_fixture(tmp_path, [
        {"id": "ma", "owner_role": "backend", "task_statuses": ["completed"]*3},
        {"id": "mb", "owner_role": "frontend", "task_statuses": ["failed", "pending"]},
    ])
    state = NightlyState()
    out = render_summary(state, workspace=str(tmp_path))
    assert "## 모듈별 상태" in out
    assert "✅" in out and "⚠️" in out
    assert "**완료**: 1" in out and "**위험**: 1" in out

def test_render_summary_workspace_priority(tmp_path):
    """호출자 workspace가 state.active_workspace보다 우선."""
    _make_board_fixture(tmp_path, [...])
    state = NightlyState(active_workspace="/nonexistent")
    out = render_summary(state, workspace=str(tmp_path))
    assert "## 모듈별 상태" in out  # tmp_path board를 정상 로드
```

### 4.4 교차검증 절차

각 커밋(C1, C2) 전:
1. af-test-runner (tier 1)
2. af-critic (tier 2)
3. af-cross-review (tier 3)

---

## 5. 엣지 케이스 & 불변식

### 5.1 C1 불변식

- **I1.** `status ∈ _INFRA_STATUSES = {"crashed", "unknown"}` → ledger record 0건
- **I2.** 모듈이 `prepared.role_plan.modules`에 있으나 board의 modules에 없음 → skip
- **I3.** `module.owner_role` 빈 문자열 → skip (기존 동작 유지)
- **I4.** `board["modules"][i]["status"] ∈ {in_progress, pending}` → skip (결과 미정)
- **I5.** `board["modules"][i]["status"] == "at_risk"` → fail 1회 기록 (at_risk = 최소 1개 task failed)
- **I6.** (pattern, owner) 쌍은 배치 전체에서 중복 제거 (B2-4 fix 유지)
- **I7.** Pattern = 모듈명 + deliverables 앞 4단어, 소문자, 단어 경계 절삭 (B2-4 fix 유지)
- **I8.** `load_project_board`는 파일 부재 또는 JSON 파싱 실패 시 예외를 내부 catch하고 `{}`를 반환. 반환이 빈 dict이면 `logger.info("...board 비어있음")` 후 skip. 예외 전파 없음.

### 5.2 C2 불변식

- **I9.** `workspace=None AND state.active_workspace=None` → "(프로젝트 비활성)" 섹션만 추가, 렌더 완주
- **I10.** `load_project_board`는 예외를 내부 catch하여 `{}` 반환 (§5.1 I8 동일 계약). `board == {}` 또는 `board["modules"]` 빈 리스트면 `(모듈 정보 없음)` 표시, 다른 섹션은 정상 렌더. **예외 경로 없음** (v7: v5 `try/except` dead code 제거에 따른 불변식 문구 통일)
- **I11.** `board["modules"]` 빈 리스트 → "(모듈 정보 없음)" 표시
- **I12.** 모듈 이름 > 40자 → 40자 트런케이션 + "…"
- **I13.** workspace 우선순위: `ws = workspace or state.active_workspace` (호출자 명시 우선)
- **I14.** tick 주기 1회당 `load_project_board` 1회 호출 (I/O O(tasks + modules))

### 5.3 알려진 한계 (설계 시 인지)

- **L1.** `stopped_max_cycles` 상태에서 완료 모듈만 pass 기록되어 "빠른 모듈"에 편향 누적 가능. 그러나 이는 legitimate signal이므로 수용. 필요시 후속 작업으로 가중치 조정 도입.
- **L2.** 사용자가 approval 후 work-item을 편집해 추가한 task의 `module_id=""` 케이스는 학습 대상 외. 기존 B2-4 fix 정책 유지.
- **L3.** `_seen` dedup + 모듈별 outcome 충돌 — 동일 (pattern, owner) 쌍이 **현재 배치 내** 여러 모듈에서 서로 다른 outcome을 가질 때, `role_plan.modules` 순서상 **먼저 처리된 모듈**의 outcome이 배치에 1건만 포함되고 이후는 `_seen`에 의해 탈락한다. **범위 제한:** 이는 현재 배치 내 중복 제거 정책이며, 이전 실행에서 이미 쌓인 `(pattern, owner)` 레코드의 pass/fail 카운터는 이 배치의 카운터와 누산된다 (`record_role_batch`의 `key in self._role_assignments` 분기, `strategy_ledger.py:210-214`). 즉 L3는 **배치 레벨 보장**이지 **ledger 전역 이력 고정**이 아니다.

- **L4. (v6 신설) 삭제 보존 task로 인한 pending 오분류** — `sync_board_from_work_items`(`core/work_item_parser.py:188-194`)가 사용자 work-item 편집으로 삭제된 task도 board에 보존한다. 해당 task는 status=pending으로 고정되어 모듈 분류를 pending으로 끌고 간다 → skip 처리되어 legitimate pass 신호 유실. B2-6 fix가 이를 우회하지 않으며(삭제 여부 판별 불가), 문서화된 한계로 남는다. 완화책: v6에서 `module_outcome_from_board`가 INFRA 필터링 후 빈 셋이면 skip이므로, 최소한 "INFRA만 남은 모듈이 pending으로 잘못 at_risk되는 경로"는 차단.

- **L5. (v6 신설) Owner drift 감지 시 skip** — 사용자가 work-item에서 task의 owner_role을 수정한 경우, module.owner_role과 불일치. `detect_owner_drift` 가드가 이를 감지하여 해당 모듈 skip. drift 발생 빈도가 높은 프로젝트는 학습 신호 손실이 있을 수 있으나, 잘못된 owner로 기록되는 것보다는 보수적. 후속 작업으로 task별 owner 기반 기록 고도화 가능.

- **L6. (v6 신설) INFRA 필터 범위 한계** — `_task_is_infra_failure`는 task notes의 `"infra_failure:"` 접두사만 인식. dynamic_orchestrator.py가 일부 경로에서 다른 prefix(`"lineage_maxed:"` 등)를 사용하면 필터링되지 않는다. `lineage_maxed:`도 인프라 속성이 있으므로 v6.1에서 검토 필요 (현재는 implementation 실패로 분류되는 것이 설계 의도).

---

## 6. 롤백 계획

### C1 롤백
- `core/project_pipeline.py:967-1004` 블록을 HEAD~1 (B2-4 fix 결과)로 복원
- Ledger 파일 데이터는 유지 (과거 오염 데이터 제거하려면 `memory/episodes/strategy_ledger.json` 수동 삭제 필요)

### C2 롤백
- `render_summary`에서 `_render_modules_section` 호출 라인만 주석 처리
- 다음 tick에 이전 포맷으로 복귀

---

## 7. 구현자에게 — Handoff Checklist

### C0 (atomic write precursor)

- [ ] `core/project_task_board.py:write_project_board`를 §2.0 의사 코드로 교체 (`tempfile.mkstemp` + `os.replace`)
- [ ] `tests/test_project_task_board_dispatch.py`에 `test_write_project_board_atomic_on_crash` 1건 추가 (monkeypatch로 `os.replace` 실패 시 tempfile 정리 확인)
- [ ] Blueprint §3.1 내부 흐름에 "atomic write 보장" 한 줄 추가
- [ ] Review-gate 3단계 완주
- [ ] 커밋 메시지: `fix(board): write_project_board atomic write — crash-safe JSON persistence`

### C1 (B2-6 fix)

- [ ] `core/project_task_board.py`에 §2.3 신규 헬퍼 3개 추가:
  - `_task_is_infra_failure(task)` (모듈 private)
  - `module_outcome_from_board(board, module_id)` (공개, export)
  - `detect_owner_drift(module, board)` (공개, export)
- [ ] `core/project_pipeline.py`에 `_record_ledger_outcomes(self, status, role_plan, workspace)` 메서드 추가 — §2.3 의사 코드
- [ ] 기존 line 967-1004 ledger 기록 블록을 `self._record_ledger_outcomes(status, prepared.role_plan, workspace)` 단일 호출로 교체
- [ ] import는 메서드 내부 lazy import (순환 회피)
- [ ] 기존 B2-4 fix의 `seen`, `record_role_batch`, 4단어 절삭 로직 **보존** 확인
- [ ] `tests/test_strategy_ledger.py`에 §4.1 `_make_board_fixture` + `_make_role_plan` 헬퍼 추가
- [ ] `_make_board_fixture`의 task 스펙에 `"instruction"` 필수 필드 확인
- [ ] fixture 반환 board의 `module.status`가 기대값인지 **직접 assert**하는 검증 단계 포함
- [ ] §4.2 단위 테스트 **12건** 추가 (v6에 신규 3건 + 기존 9건):
  - `test_ledger_skips_on_crashed` (I1)
  - `test_ledger_skips_on_unknown` (I1)
  - `test_ledger_skips_on_empty_board` (I8)
  - `test_ledger_per_module_completed` (I5)
  - `test_ledger_skips_pending_module` (I4)
  - `test_ledger_mixed_module_status` (I4, I5)
  - `test_ledger_seen_dedup_first_outcome_wins` (L3, I6)
  - `test_ledger_module_missing_in_board` (I2)
  - `test_ledger_empty_owner_role_skip` (I3)
  - **`test_ledger_4word_truncation`** (I7 직접) — deliverable `"rest api endpoint with jwt authentication and refresh"` → 저장 패턴 `"rest api endpoint with"` 검증
  - **`test_ledger_skips_infra_failure`** (L6) — task note `"infra_failure: quota_exceeded"` → at_risk 대신 skip
  - **`test_ledger_skips_on_owner_drift`** (L5) — module.owner=backend, task.owner=frontend → skip + warning log
- [ ] `tests/test_strategy_ledger.py` 각 테스트 시작 시 `reset_strategy_ledger(str(tmp_path))` 호출로 캐시 격리
- [ ] `tests/test_project_pipeline.py` 기존 테스트가 ledger 상태를 assert하지 않는지 grep 확인 (없음 — 검증 완료)
- [ ] Blueprint §3.1 + §12 업데이트
- [ ] Review-gate 3단계 완주 (tier 1→2→3)
- [ ] 커밋 메시지: `fix(B2-6): strategy ledger 모듈별 granularity`

### C2 (Summary enhancement)

- [ ] `scripts/nightly_summary.py`에 `_render_modules_section(workspace)` 추가 — §2.4 의사 코드
- [ ] `render_summary`에서 `ws_for_board = workspace or state.active_workspace` 우선순위 적용
- [ ] `## 진행 중 태스크` 섹션 뒤에 삽입
- [ ] `tests/test_nightly_summary.py` 신규 작성 (§4.3 4건)
- [ ] Blueprint §0 또는 §3.1 + §12 업데이트
- [ ] Review-gate 3단계 완주
- [ ] 커밋 메시지: `feat(summary): nightly summary 모듈별 상태 섹션`

### 구현 중 주의사항

1. **`module.status`는 이미 계산된 필드.** `load_project_board()` 내부에서 `_recalculate_board`가 자동 호출되어 각 module의 status가 최신 상태로 갱신됨. 별도 계산 함수를 만들지 말고 `board["modules"][i]["status"]`를 직접 읽을 것.

2. **`run_board`는 사용 금지.** `orchestrator.run_project()`가 반환하는 값은 `state_board`(`{current_status, completed_subtasks, failed_subtasks, ...}`)로 tasks/modules 키가 **없다**. 반드시 `load_project_board(workspace)` 사용.

3. **`_DummyOrchestrator`는 board 파일을 생성하지 않음.** 기존 `test_project_pipeline.py`는 board 파일이 pipeline 내부(`write_project_board`)에서 생성된다는 전제로 동작. C1 테스트에서는 orchestration 결과 대신 fixture로 board 파일을 미리 준비.

4. **순환 import 방지.** `project_pipeline.py` 상단에서 `project_task_board`를 통째 import하면 순환 가능. 함수 내부 lazy import 권장.

5. **B2-4 fix 보존.** `_seen`의 (pattern, owner) 튜플 중복 제거, 4단어 절삭, `record_role_batch` — 모두 유지. C1은 `_outcome` 결정 방식만 교체.

---

## 8. 변경 영향 범위

### C1 (B2-6)
- **파일**:
  - `core/project_pipeline.py` (~40줄, `_record_ledger_outcomes` 메서드 추출)
  - `core/project_task_board.py` (+4 헬퍼: `_task_is_infra_failure`, `_build_board_maps`, `module_outcome_from_board`, `detect_owner_drift`)
  - `tests/test_strategy_ledger.py` (+12 테스트 + fixture 헬퍼 `_make_board_fixture`, `_make_role_plan`)
  - `Master_Blueprint.md` (§3.1, §12)
- **리스크**:
  - 기존 ledger 파일 영향 없음 (누적 데이터 유지, 새 기록부터 정확도 개선)
  - `test_project_pipeline.py`가 ledger 상태를 assert하면 수정 필요 (확인 후 대응)
- **의존성**: `core.project_task_board.load_project_board` (기존 함수)

### C2 (Summary)
- **파일**: `scripts/nightly_summary.py` (~40줄 추가), `tests/test_nightly_summary.py` (신규), `Master_Blueprint.md` (§0/§3.1, §12)
- **리스크**: tick 주기마다 `load_project_board` I/O 추가 — 측정치 미미 예상 (tick = 15분, 파일 사이즈 ~수십 KB)
- **의존성**: `core.project_task_board.load_project_board` (기존 함수)

---

## 9. 참조

- Appendix B: `docs/2026-04-19-review-gate-enforcement.md:643`
- B2-4 fix 커밋: `5cd96564` (2026-04-21)
- Design doc (nightly pipeline): `docs/2026-04-18-nightly-autonomous-pipeline.md` §I5
- `load_project_board`: `core/project_task_board.py:580-591`
- `_recalculate_board`: `core/project_task_board.py:543-563` (module.status 자동 계산)
- orchestrator status values: `core/dynamic_orchestrator.py:1010-1035`
- `update_project_board_task`: `core/dynamic_orchestrator.py:858` (task 실패 시 board 반영)
- `render_summary` 시그니처: `scripts/nightly_summary.py:26`
- `NightlyState.active_workspace`: `core/nightly_state.py:84`
