# Design Review Watcher 신뢰성 개선

> **상태**: 설계 (코드 수정 없음)
> **작성일**: 2026-04-08
> **영향 범위**: `core/design_review_utils.py`, `scripts/design_review_watcher.py`

---

## 1. 문제 정의

설계 문서 작성 시 교차 검증이 자동 실행되지 않는 문제. 두 가지 근본 원인.

### 버그 A: Windows PID 재사용으로 인한 좀비 watcher 오판

**위치**: `core/design_review_utils.py:126-141` `_is_watcher_alive()`

**현상**:
```
1. 이전 세션에서 watcher 시작 (PID 74860)
2. watcher가 IDLE_TIMEOUT(60s) 후 종료
3. _remove_pid()가 PID 파일 삭제 … 해야 하는데,
   Windows에서 다른 python.exe가 같은 PID 74860을 재사용
4. _is_watcher_alive() → os.kill(74860, 0) → 성공 (다른 프로세스)
5. "watcher 살아있음" 오판 → 새 watcher 안 띄움
6. pending 큐 영원히 처리 안 됨
```

**근본 원인**: `os.kill(pid, 0)`은 "해당 PID의 프로세스가 존재하는가"만 확인. Windows는 PID를 적극적으로 재사용하므로, 이전 watcher가 아닌 전혀 다른 프로세스가 같은 PID를 가질 수 있음.

### 버그 B: IDLE_TIMEOUT과 문서 작성 시간의 충돌

**위치**: `scripts/design_review_watcher.py:43-44`, `:486-494`

**현상**:
```
T+0s     첫 Write 훅 → watcher 시작
T+10s    poll → pending 비어있음 (아직 문서 작성 중)
T+20s    poll → pending 비어있음
...
T+60s    IDLE_TIMEOUT 도달 → watcher 자동 종료
T+180s   문서 작성 완료 → Write 훅 → enqueue
         → _is_watcher_alive() → PID 파일 있음 → 새 watcher 안 띄움 (버그 A 복합)
```

**근본 원인**: `IDLE_TIMEOUT = 60초`인데, 설계 문서 작성은 수 분 소요. 첫 훅 트리거(파일 생성)와 마지막 트리거(내용 완성) 사이에 watcher가 이미 죽음.

---

## 2. 수정 설계

### 수정 A: PID + start_time 기반 stale 감지

`_is_watcher_alive()`에서 PID 존재만 확인하는 대신, **PID 파일의 start_time과 heartbeat로 실제 watcher인지** 검증.

**방법**: PID 파일에 PID와 함께 `start_time`을 기록. watcher가 매 poll마다 `heartbeat`를 갱신. 확인 시 heartbeat 경과 시간으로 판단.

```python
# PID 파일 포맷 변경: JSON
# 기존: "74860" (PID만)
# 변경: {"pid": 74860, "start_time": 1775631000.0, "heartbeat": 1775631060.0}

# ★ REVIEW_TIMEOUT(600s) 동안 process_review()가 동기 블로킹하므로
# heartbeat가 갱신되지 않음. threshold는 반드시 REVIEW_TIMEOUT보다 커야 함.
HEARTBEAT_STALE_THRESHOLD = 660  # REVIEW_TIMEOUT(600) + POLL_INTERVAL(10) * 6

def _write_pid(workspace: str) -> None:
    pid_path = os.path.join(workspace, PID_FILE)
    now = time.time()
    data = {
        "pid": os.getpid(),
        "start_time": now,
        "heartbeat": now,
    }
    # atomic write: temp → os.replace
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(pid_path))
    with os.fdopen(tmp_fd, "w") as f:
        json.dump(data, f)
    os.replace(tmp_path, pid_path)
    # atexit는 finally와 이중 호출 (2번째는 FileNotFoundError → pass로 무해).
    # ★ 한계: TerminateProcess/SIGKILL 시 atexit·finally 모두 미호출 → PID 잔류.
    #    이 경우 heartbeat stale 감지가 유일한 안전망.
    atexit.register(_remove_pid, workspace)

def _update_heartbeat(workspace: str) -> None:
    """매 poll마다 호출하여 watcher 생존을 증명.
    ★ atomic write 사용 — open("w") truncate 후 불완전 JSON이
    _is_watcher_alive()에 읽히는 race condition 방지."""
    pid_path = os.path.join(workspace, PID_FILE)
    if not os.path.exists(pid_path):
        return
    try:
        with open(pid_path) as f:
            data = json.load(f)
        data["heartbeat"] = time.time()
        # atomic write: temp → os.replace
        tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(pid_path))
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, pid_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception:
        pass

def _is_watcher_alive(workspace: str) -> bool:
    pid_path = os.path.join(workspace, PID_FILE)
    if not os.path.exists(pid_path):
        return False
    try:
        with open(pid_path) as f:
            raw = f.read().strip()
        # 하위호환: 순수 숫자면 구형 포맷 → 무조건 stale 판정
        if raw.isdigit():
            raise OSError("legacy pid format, treat as stale")

        data = json.loads(raw)
        pid = int(data["pid"])
        heartbeat = float(data.get("heartbeat", data.get("start_time", 0)))

        os.kill(pid, 0)  # 프로세스 존재 확인

        # heartbeat 기반 stale 감지:
        # process_review()가 최대 REVIEW_TIMEOUT(600s) 동기 블로킹하므로
        # HEARTBEAT_STALE_THRESHOLD(660s) 이상 미갱신이면 확실히 다른 프로세스
        if (time.time() - heartbeat) > HEARTBEAT_STALE_THRESHOLD:
            raise OSError("stale heartbeat")

        return True
    except (ValueError, OSError, ProcessLookupError, json.JSONDecodeError, KeyError):
        try:
            os.remove(pid_path)
        except OSError:
            pass
        return False
```

**heartbeat 방식의 장점**:
- 기존 `STALE_PID_THRESHOLD = IDLE_TIMEOUT * 2`보다 watcher 생존 판정이 정확함
- heartbeat는 watcher가 살아있는 한 매 poll(10s)마다 갱신됨

**★ Critical 제약: process_review() 동기 블로킹** (2차 교차 검증 발견):
- `process_queue()` → `process_review()` → `subprocess.run(timeout=REVIEW_TIMEOUT)` 체인이 최대 600초간 **동기 블로킹**
- 이 동안 `run_daemon()` 루프가 진행되지 않으므로 heartbeat가 갱신되지 않음
- 따라서 `HEARTBEAT_STALE_THRESHOLD`는 반드시 `REVIEW_TIMEOUT(600s)`보다 커야 함
- `HEARTBEAT_STALE_THRESHOLD = 660초` (REVIEW_TIMEOUT + POLL_INTERVAL*6)로 설정
- **트레이드오프**: PID 재사용 감지 속도가 느려짐 (최대 660초 후 감지). 하지만 PID 재사용 자체가 드문 이벤트이므로 수용 가능.
- **대안**: heartbeat를 daemon thread에서 갱신하면 threshold를 60초로 낮출 수 있으나, 구현 복잡도가 높아 1단계에서는 threshold 상향으로 대응.

**하위호환**: 구형 PID 파일(순수 숫자)은 `raw.isdigit()` → 무조건 stale 판정.
★ 주의: 구형 watcher가 아직 리뷰 처리 중(최대 600초)일 수 있음.
이 경우 구형 PID를 stale로 판정하면 중복 watcher가 기동되지만,
구형→신형 전환 과정의 일회성 문제이며, 이후 신형 watcher는 heartbeat로 보호됨.

**변경 파일**:
- `core/design_review_utils.py` — `_is_watcher_alive()` 수정, `_update_heartbeat()` 추가
- `scripts/design_review_watcher.py` — `_write_pid()` 수정 (JSON + atexit), `run_daemon()` 루프에서 `_update_heartbeat()` 호출

### 수정 B: IDLE_TIMEOUT을 pending 기반으로 변경

현재 문제: "큐가 비어있으면 60초 후 종료"인데, 문서 작성 중에는 큐가 비어있는 게 정상.

**방법**: idle 판단 기준을 "처리 건수"에서 "pending 존재 여부 + 마지막 enqueue 시간"으로 변경.

```python
# 현재 (버그 있음)
IDLE_TIMEOUT = 60

while True:
    processed = process_queue(workspace)
    if processed > 0:
        last_activity = time.time()
    if time.time() - last_activity > IDLE_TIMEOUT:
        break  # ← 문서 작성 중에도 종료됨

# 수정 후
IDLE_TIMEOUT = 180  # 3분으로 확대

while True:
    processed = process_queue(workspace)
    if processed > 0:
        last_activity = time.time()

    # 처리 가능한 pending이 있으면 idle 타이머 리셋
    if _has_actionable_pending(workspace):
        last_activity = time.time()

    if time.time() - last_activity > IDLE_TIMEOUT:
        break
```

**`_has_actionable_pending()` 추가** (교차 검증 High 이슈 해소: stuck 파일 방지):
```python
MAX_PENDING_AGE = 900  # 15분 — 이보다 오래된 pending은 stuck으로 간주

def _has_actionable_pending(workspace: str) -> bool:
    """quiet period를 경과한 처리 가능한 pending이 있는지 확인.
    stuck 파일(MAX_PENDING_AGE 초과)은 무시하여 watcher 영구 생존 방지."""
    pending_dir = os.path.join(workspace, PENDING_DIR)
    if not os.path.isdir(pending_dir):
        return False
    now = time.time()
    for f in os.listdir(pending_dir):
        if not f.endswith(".json"):
            continue
        fpath = os.path.join(pending_dir, f)
        try:
            age = now - os.path.getmtime(fpath)
        except OSError:
            continue
        if QUIET_PERIOD <= age <= MAX_PENDING_AGE:
            return True  # 처리 가능한 pending
    return False
```

**IDLE_TIMEOUT 변경**: `60초 → 180초`. 설계 문서 작성은 보통 2-5분 소요. 180초면 마지막 pending 처리 후 3분간 대기하므로 충분.

**변경 파일**:
- `scripts/design_review_watcher.py` — `run_daemon()` 수정, `_has_pending()` 추가, `IDLE_TIMEOUT` 상수 변경

---

## 3. 전체 수정 변경점

| 파일 | 변경 내용 | 줄 수 |
|------|----------|-------|
| `core/design_review_utils.py` | `_is_watcher_alive()` heartbeat 기반 검증 | ~20줄 수정 |
| `core/design_review_utils.py` | `_update_heartbeat()` 추가 (atomic write) | ~18줄 추가 |
| `scripts/design_review_watcher.py` | `_write_pid()` JSON+atexit+atomic write 포맷 | ~12줄 수정 |
| `scripts/design_review_watcher.py` | `run_daemon()` pending 기반 idle 판단 + heartbeat 호출 | ~10줄 수정 |
| `scripts/design_review_watcher.py` | `_has_actionable_pending()` 추가 | ~12줄 추가 |
| `scripts/design_review_watcher.py` | `IDLE_TIMEOUT` 60→180, `MAX_PENDING_AGE` 추가 | 2줄 수정 |

**총 ~62줄** 변경. 신규 의존성 없음 (`atexit`는 stdlib).

---

## 4. 하위호환

| 항목 | 대응 |
|------|------|
| 기존 PID 파일 (순수 숫자) | `raw.isdigit()` → 무조건 stale 판정 → PID 파일 삭제 → 새 watcher 시작 |
| 기존 watcher 프로세스 | 다음 IDLE_TIMEOUT 후 자연 종료, 이후 새 포맷으로 재시작 |
| af.exe 빌드 | `design_review_utils.py`는 core/에 있으므로 빌드 포함 |

---

## 5. 검증 시나리오

### 시나리오 1: PID 재사용 감지
```
1. watcher 시작 → PID 파일에 {"pid": X, "start_time": T, "heartbeat": T} 기록
2. watcher IDLE_TIMEOUT 후 종료 (PID 파일 삭제됨)
   — 만약 종료가 비정상이라 PID 파일이 남으면:
3. 다른 프로세스가 PID X 재사용
4. ensure_watcher() → _is_watcher_alive()
   → heartbeat에서 HEARTBEAT_STALE_THRESHOLD(660s) 이상 경과
   → stale 판정 → PID 파일 삭제 → 새 watcher 시작
```

### 시나리오 2: 긴 문서 작성 중 watcher 유지
```
1. 첫 Write → enqueue + watcher 시작
2. 문서 작성 중 (2분 경과, 큐 비어있음)
3. watcher poll → _has_pending() = False, 하지만 아직 IDLE_TIMEOUT(180s) 미도달
4. T+150s: 문서 완성 → Write → enqueue
5. watcher poll → pending 발견 → quiet period(8s) 대기 → 처리
```

### 시나리오 3: 정상 자동 종료
```
1. 마지막 pending 처리 완료
2. 180초간 새 pending 없음
3. watcher 자동 종료 + PID 파일 삭제
```

---

## 6. 알려진 제약

| 제약 | 설명 | 후속 작업 |
|------|------|----------|
| TOCTOU race | `ensure_watcher()`에 Lock 없음 — 두 훅이 동시에 `_is_watcher_alive()==False`를 읽고 watcher 이중 시작 가능 | file lock 기반 보호 (`msvcrt.locking` / `fcntl.flock`) 도입 검토 |
| `enqueue()` 후 `ensure_watcher()` 실패 | 같은 try 블록 — enqueue 성공 후 watcher 시작 실패 시 pending만 남음 | `design_review_hook.py:117-118`에서 분리 또는 재시도 |

---

## 7. 체크리스트

- [ ] `core/design_review_utils.py` — `_is_watcher_alive()` heartbeat 기반 검증
- [ ] `core/design_review_utils.py` — `_update_heartbeat()` 추가
- [ ] `scripts/design_review_watcher.py` — `_write_pid()` JSON+atexit 포맷
- [ ] `scripts/design_review_watcher.py` — `_has_actionable_pending()` 함수 추가
- [ ] `scripts/design_review_watcher.py` — `run_daemon()` idle 판단 + heartbeat 호출
- [ ] `scripts/design_review_watcher.py` — `IDLE_TIMEOUT` 60→180, `MAX_PENDING_AGE` 추가
- [ ] 현재 좀비 PID 파일 정리 (`.af_review_queue/.watcher.pid` 삭제)
- [ ] 대기 중인 pending 처리 확인
- [ ] Master_Blueprint.md §3 해당 서브시스템 업데이트
