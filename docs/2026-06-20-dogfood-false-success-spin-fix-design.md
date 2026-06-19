# dogfood 가짜성공/spin 침묵사 수정 설계

- 날짜: 2026-06-20
- 작성: Opus 4.8 (설계), 구현=Sonnet
- 상태: Draft (af-cross-review 대기)
- 계기 run: `1781884669-a7502e9b` (task="core/completion_contract.py에 GoalContract.goal_count() 추가"), phase=blocked, last_failure=`stopped_max_cycles`, goal_count 끝내 미생성
- 진단 동결 출처: 메모리 `project_dogfood_false_success_spin` (재분석 금지)

---

## 0. 범위 선언 (무엇을 고치고 무엇을 미루나)

진단의 死因 사슬:

```
[Bug 0] codex_cli 셸 Windows 깨짐("batch file arguments are invalid")  = 방아쇠(환경)
   ↓
[Bug 1] 그 깨진 run이 ok:true로 집계  = ★핵심 소프트웨어 버그★
   ↓
[Bug 2] 산출물(goal_count) 부재인데 검증 없음
   ↓
[Bug 3] 보드 영영 미완 → 빈 사이클 100+바퀴 grind → stopped_max_cycles 침묵사
   ↓
[Bug 4] 과분해(작은 변경에 full 프로젝트 템플릿)  = 조연(태스크 수만 부풀림)
```

**이 설계가 고치는 것 (correctness, 즉시):**
- **S1 (Bug 0)** — `cli.py`: `batch file arguments are invalid`를 `shell_error`로 분류 → codex ok-승격 차단
- **S2 (Bug 1/2)** — `agent_runner.py`: CLI `ok` 맹신 지점에 **보수적** 가짜성공 가드(비정상 종료 + 산출물 변경 0 → ok:false)
- **S3 (Bug 3)** — `dynamic_orchestrator.py`: 무진전 fail-fast (보드 진전 0이 N사이클 지속 → max_cycles 갈기 전에 BLOCK)

**이 설계가 미루는 것 (별도 추적, 본 문서 밖):**
- 우선순위 3 (작은 Tier-3 실행 기어: build→존재가드→test→review→cross_review, 싼 게이트가 비싼 걸 가림) — `right_sized_router`/단계템플릿 재구조화
- 우선순위 5 (Bug 4 뿌리: `bootstrap_roles.plan()` 프롬프트 규모 조건부화 + full 단일기어 분해)

→ §6 "후속 설계"에서 이유와 진입점만 명시. **이 둘을 본 문서에 섞으면 baseline churn으로 cross-review BLOCK 루프 유발** (메모리 `cross_review_stale_baseline_repeat` 학습). S1~S3는 disjoint 파일·순수 correctness라 cross-review 1라운드로 닫힐 설계.

**무죄 확정 (red herring, 메모리 동결):** gemini 키 없음(死因 아님), 프리커밋 3-Tier 미발화(dogfood `AF_SKIP_REVIEW_GATE=1`), Tier-3 분류/Floor 2(태스크 수만 부풀린 조연).

---

## 1. Baseline (실제 코드, 전수 인용)

### 1.1 cli.py — ok 결정 (false-success 발원지)

`core/providers/cli.py:927-931`:
```python
issue = _classify_cli_issue(completed.stdout, completed.stderr)
ok = completed.returncode == 0 and bool(text.strip())
if not ok and request.provider_id == "codex_cli" and bool(text.strip()):
    if issue not in ("auth_required", "permission_denied", "hook_failure"):
        ok = True
```

`core/providers/cli.py:378-386` (`_classify_cli_issue`):
```python
def _classify_cli_issue(stdout: str, stderr: str) -> str:
    haystack = f"{stdout}\n{stderr}".lower()
    if any(marker in haystack for marker in _PERMISSION_DENIED_MARKERS):
        return "permission_denied"
    if any(marker in haystack for marker in _AUTH_REQUIRED_MARKERS):
        return "auth_required"
    if any(marker in haystack for marker in _HOOK_FAILURE_MARKERS):
        return "hook_failure"
    return ""
```

마커 튜플은 `cli.py:111-140`(`_PERMISSION_DENIED_MARKERS`/`_AUTH_REQUIRED_MARKERS`/`_HOOK_FAILURE_MARKERS`).

**핵심 사실**: `_classify_cli_issue`가 반환할 수 있는 비공백 issue는 전부 line 930 제외 튜플에 포함됨. 따라서 **issue가 비공백이면 ok-승격이 안 일어남**. 반대로 `batch file arguments are invalid`는 어느 마커에도 안 걸려 `issue==""` → line 928에서 ok=False였다가 line 929-931에서 **ok=True로 승격**됨. 이것이 Bug 0→1 정확한 기계.

### 1.2 agent_runner.py — CLI ok 맹신

`core/agent_runner.py:1226-1248`:
```python
if cli_result.get("ok"):
    cli_text = str(cli_result.get("text", "") or "").strip()
    if cli_text:
        print(f"{cli_text}")
    result = {
        "ok": True,
        "reason": provider_id,
        ...
    }
    ...
    return result
```
이 지점에 산출물/종료코드 교차검증 없음. `cli_result["ok"]`만 믿음. 워크스페이스 변경 추적 코드 부재(파일 내 mtime 사용처는 skill-module-cache 전용, `agent_runner.py:653-686`, 무관).

`cli_result` 가용 필드(§1.1 result dict): `ok`, `text`, `returncode`, `reason`, `stdout`, `stderr`, `command`.

### 1.3 dynamic_orchestrator.py — 무진전 spin

`core/dynamic_orchestrator.py` 주요 라인:
- `:1100` 루프 조건 `while cycle < max_cycles:`
- `:1124-1126` **stall 감지(로깅 전용)**:
  ```python
  cycles_since_completion = cycle - self._last_completion_cycle
  if cycles_since_completion >= self._stall_threshold and cycle > self._stall_threshold:
      print_agent_msg("Lilith", f"No progress for {cycles_since_completion} cycles — stall detected", "")
  ```
- `:76` `self._stall_threshold = int(os.getenv("AGENT_STALL_THRESHOLD", "15"))`
- `:338-343` infra-only 실패 판정(이미 존재):
  ```python
  cycles_since = cycle - self._last_completion_cycle
  if cycles_since >= self._stall_threshold and cycle > self._stall_threshold:
      _recent = self.state_board.get("failed_subtasks", [])[-self._stall_threshold:]
      if _recent and all(f.get("failure_category") == "infra" for f in _recent):
          return False  # infra 실패만 → LLM 재시도 무의미
      return True
  ```
- `:1147-1153` idle break(`not new_tasks and not active_workers`만 break — 재시도 churn은 안 잡힘)
- `:73-74` `self._task_retry_count: Dict[str,int] = {}` / `self._max_task_retries = 3`
- `:1172-1176` 재시도 소진 태스크 → "failed" 마킹 후 `continue`(보드에서 제거 X)
- `:1213-1217` 루프 종료 후 상태 결정:
  ```python
  if cycle >= max_cycles:
      self.state_board["current_status"] = "stopped_max_cycles"
  elif self.state_board["failed_subtasks"]:
      self.state_board["current_status"] = "partial"
  else:
      self.state_board["current_status"] = "completed"
  ```

**핵심 사실**: stall 감지·infra-only 판정은 **이미 있으나 둘 다 로깅/LLM개입 트리거일 뿐 hard break 없음**. 재시도 churn(태스크가 매 사이클 dispatch되나 영영 실패)은 `:1147` idle break를 못 타고 max_cycles까지 grind. 이 run이 정확히 그 경로.

---

## 2. S1 — codex shell_error 분류 (Bug 0)

### 2.1 변경

(1) 마커 튜플 신설 (`cli.py` ~140, 기존 튜플 옆):
```python
_SHELL_FAILURE_MARKERS = (
    "batch file arguments are invalid",
)
```
> 보수적: **실증된 시그니처 1개만**. 광범위 매칭은 정상 agent 텍스트 오탐 위험.

(2) `_classify_cli_issue`에 분기 추가 (기존 3분기 뒤, `return ""` 앞):
```python
    if any(marker in haystack for marker in _SHELL_FAILURE_MARKERS):
        return "shell_error"
```

(3) `cli.py:930` 제외 튜플에 `shell_error` 추가:
```python
    if issue not in ("auth_required", "permission_denied", "hook_failure", "shell_error"):
        ok = True
```

### 2.2 효과·불변식
- 깨진 codex run(stderr에 시그니처) → `issue=="shell_error"` → ok 미승격 → `ok=False`, `reason=="codex_cli_shell_error"`.
- **INV-S1a**: 시그니처 없는 기존 codex 동작 무변(text-bearing 성공은 여전히 승격).
- **INV-S1b**: shell_error는 `returncode==0` 정상 경로(line 928 ok=True)를 건드리지 않음 — line 929 `if not ok` 가드 안에서만 작동.

### 2.3 테스트 (신규)
- stderr="...batch file arguments are invalid..." + returncode=1 + text非공백 → `_classify_cli_issue=="shell_error"`, 결과 `ok is False`, `reason=="codex_cli_shell_error"`.
- 회귀: 동일 입력에서 시그니처만 제거 → 기존대로 `ok is True`(승격 유지).
- 회귀: auth/permission/hook 마커 결과 불변.

---

## 3. S2 — 가짜성공 가드 (Bug 1/2)

### 3.1 설계 판단 (해석 분기 명시 — CLAUDE.md 원칙 1)

가짜성공 신호 후보 3종의 안전성:

| 신호 | 신뢰도 | 하드게이트 적합성 |
|------|--------|------------------|
| 에이전트 자기보고 텍스트("못 함"/"막혔"/"unable") | 낮음 — 언어·표현 의존, LLM이 성공해도 겸양 표현 사용 | ❌ 하드게이트 부적합(false-fail 위험) |
| 워크스페이스 파일변경 0 | 중간 — 단, read/analysis/review 태스크는 정당하게 변경 0 | ❌ 단독 블랭킷 게이트 부적합 |
| 비정상 종료(`returncode != 0`) | 높음 — 명시적 실패 신호 | ✅ 단, codex agent_message 예외 존재 |

**채택(보수적 교집합)**: `cli_result["ok"]==True` 인데 **`returncode != 0` AND 파일변경 0** 인 경우에만 ok→False 강등.
- 근거: S1 적용 후 잔여 false-success는 "`returncode!=0` + `issue==""`(미분류) + text非공백 → 승격" 한 가지뿐(§1.1 핵심 사실). 그중 **아무것도 안 쓴** run은 build 태스크 실패가 확실. `returncode==0` 성공·read 태스크(정당한 변경0+정상종료)는 **불변**.
- 자기보고 텍스트는 **하드게이트 미채택**, 관측 로그로만 기록(추후 신호).

### 3.2 변경

(1) `agent_runner.py`에서 CLI 호출 전 워크스페이스 시그니처 1회 스냅샷:
```python
ws_sig_before = _workspace_mutation_signature(target_workspace)
```
`_workspace_mutation_signature(path) -> tuple[int, float]`: `(파일수, 최대 mtime)`. VCS/빌드 디렉터리 제외(`.git`, `node_modules`, `__pycache__`, `.af-dogfood`). 비용 완화 = 의심 분기에서만 after 스냅샷을 lazy 계산.

(2) `cli_result.get("ok")` 분기(`:1226`) 진입 직후, result 확정 전:
```python
rc = cli_result.get("returncode")
if rc is not None and rc != 0:
    ws_sig_after = _workspace_mutation_signature(target_workspace)
    produced_changes = ws_sig_after != ws_sig_before
    if not produced_changes:
        # 비정상 종료 + 산출물 0 → 가짜성공. 실패로 강등.
        cli_failures.append({**cli_result, "ok": False,
                             "reason": f"{provider_id}_false_success_no_output"})
        _append_trace("error", {"stage": provider_id,
                                "message": "false_success_no_output"})
        continue  # 다음 provider 또는 cli_failures 처리로
```
`produced_changes`(bool)는 정상 통과 시에도 result dict에 첨부 → S3 진전 판정 재사용 가능(§4.3).

> ⚠️ `continue`가 cli provider 루프(`:1215`)를 정상적으로 다음 반복/`cli_failures` 폴백(`:1259`)으로 보냄 — 기존 실패 경로 재사용, 신규 종료 경로 없음.

### 3.3 효과·불변식
- **INV-S2a**: `returncode==0` 성공은 절대 강등 안 됨(분기 진입 조건이 `rc != 0`).
- **INV-S2b**: 변경을 만든 run(파일 쓰기 성공한 부분완료)은 강등 안 됨 — 다음 게이트(test/AcceptanceGate)가 판정.
- **INV-S2c**: S1과 중복 안전망 — shell_error는 S1에서 이미 `ok=False`라 §3.2 분기에 도달 안 함. §3.2는 **미분류 비정상종료** 잔여만 잡음.
- 비용: 워크스페이스 walk 1회(before) + 의심 시 1회(after). 대형 워크스페이스 완화는 제외 디렉터리 + lazy after.

### 3.4 테스트 (신규)
- ok=True + returncode=1 + 변경0 → 강등(`ok False`, reason `*_false_success_no_output`), cli_failures에 적재.
- ok=True + returncode=1 + 변경有 → 강등 안 함(통과).
- ok=True + returncode=0 → 분기 미진입(불변).
- `_workspace_mutation_signature`: 파일 추가/수정 시 시그니처 변화, `.git` 변경은 무시.

---

## 4. S3 — 무진전 fail-fast (Bug 3)

### 4.1 설계 판단
이미 있는 stall 감지(`:1124`)·infra-only 판정(`:338-343`)을 **hard break로 승격**. 단 보수적:
- 실제 작업 진행 중(긴 태스크) 오발 방지 → 임계를 stall(15)보다 크게(`HARD_NO_PROGRESS_CYCLES`).
- "진전" = `completed_subtasks` 개수 증가. 기존 `_last_completion_cycle`(완료 사이클) 재사용 — 별도 카운터 불필요.

### 4.2 변경

(1) 상수 신설(`:76` 옆):
```python
self._hard_no_progress_cycles = int(os.getenv("AGENT_HARD_NO_PROGRESS", "20"))
```
> stall_threshold(15) > 가 아니라 20 — stall 로깅·LLM개입이 먼저 작동하고, 그래도 안 풀리면 hard stop.

(2) 루프 내(`:1124` stall 감지 직후) hard-stop 분기:
```python
cycles_since_completion = cycle - self._last_completion_cycle
if (cycles_since_completion >= self._hard_no_progress_cycles
        and cycle > self._hard_no_progress_cycles):
    _recent = self.state_board.get("failed_subtasks", [])[-self._stall_threshold:]
    all_infra = bool(_recent) and all(
        f.get("failure_category") == "infra" for f in _recent)
    retry_exhausted = (
        bool(self._task_retry_count)
        and all(v >= self._max_task_retries
                for v in self._task_retry_count.values()))
    if all_infra or retry_exhausted:
        print_agent_msg("Lilith",
            f"무진전 {cycles_since_completion}사이클 — fail-fast BLOCK", "")
        self.state_board["_blocked_no_progress"] = True
        break
```

(3) 종료 상태 결정(`:1213`) 분기 추가(맨 앞):
```python
if self.state_board.get("_blocked_no_progress"):
    self.state_board["current_status"] = "blocked_no_progress"
elif cycle >= max_cycles:
    self.state_board["current_status"] = "stopped_max_cycles"
elif ...
```

### 4.3 효과·불변식
- 이 run(재시도 churn 100+사이클, 진전0, codex shell 실패=infra) → 20사이클째 `blocked_no_progress` BLOCK. **6분 침묵사 → ~즉시 명확한 실패.**
- **INV-S3a**: 임계 내 완료되는 정상 run 불변(`_last_completion_cycle` 갱신되면 카운터 리셋).
- **INV-S3b**: max_cycles는 여전히 최종 캡(이중 안전망).
- **INV-S3c**: hard-stop은 `all_infra or retry_exhausted`일 때만 — 일반 실패(코드 버그로 test FAIL 반복하나 진짜 일하는 중)는 LLM 개입/재시도에 맡기고 hard-stop 안 함. (S2의 `produced_changes`를 진전 신호로 추가 결합하는 건 후속 — 본 슬라이스는 기존 신호만.)

### 4.4 테스트 (신규)
- `_last_completion_cycle` 고정 + cycle이 임계 초과 + failed 전부 infra → break, status `blocked_no_progress`.
- 동일하나 retry_exhausted=True(모든 retry_count >= 3) → break.
- 동일하나 failed에 non-infra 섞임 + retry 미소진 → break 안 함(기존 max_cycles 경로).
- 완료가 임계 내 발생(`_last_completion_cycle` 갱신) → break 안 함.

---

## 5. 구현 순서·병렬성 (Sonnet 핸드오프)

3 슬라이스는 **disjoint 파일** → 병렬 구현 가능:

| 슬라이스 | 파일 | 의존 | 병렬 |
|---------|------|------|------|
| S1 | `core/providers/cli.py` | 없음 | ✅ 동시 |
| S2 | `core/agent_runner.py` | S1 개념적 후행(잔여만 잡음)이나 코드 독립 | ✅ 동시 |
| S3 | `core/dynamic_orchestrator.py` | 없음 | ✅ 동시 |

권장: S1·S3 먼저(가장 단순·고레버리지), S2(워크스페이스 시그니처 헬퍼 신규)는 그 뒤. 단 파일 충돌 없어 동시 PR 가능.

각 슬라이스 완료 기준(메모리 `pipeline_deploy_parity`): production caller까지 연결 확인 — S1은 `_classify_cli_issue` 호출처(`:927`) 자동 적용, S2는 `agent_runner` CLI 루프가 유일 경로, S3는 orchestrator 메인 루프가 유일 경로. 픽스처-only 미허용.

3-Tier(전부 Tier-3 파일): af-critic → af-cross-review → af-test-runner.

---

## 6. 후속 설계 (본 문서 밖, 진입점만)

### 6.1 우선순위 3 — 작은 Tier-3 실행 기어
메모리 합의 실행흐름: `build(구현+테스트) → [존재가드] → test ──FAIL→ fix → (초록일 때만) code_review → cross_review`. 원칙 4종: 싼 게이트가 비싼 게이트를 가린다 / 스코프 재리뷰(2회차 diff만) / 하드 루프 캡 / 수렴 정의 명문화. 진입점: `core/right_sized_router.py` light↔full 이분법(`:55-70`, `:104`)에 "작은 full" 기어 추가 + 단계템플릿(층3)·Floor2(층4, `:218-224`) 무게 조건부화.

### 6.2 우선순위 5 — Bug 4 뿌리(과분해 의무화)
`bootstrap_roles.plan()`(`:398`) 프롬프트가 규모를 알면서도 최소분해 의무화: "project planning director" 정체성 + 모듈0 금지(`:465`) + qa_engineer/verify 필수(`:473-474`, `_ensure_qa_role:318-396`). full이 규모 무관 단일기어(`_FULL_STAGES`, `right_sized_router.py:104`)라 출구 없음. → 프롬프트 규모 조건부화 + full 기어 분해. **큰 별도** — Floor2 억제는 `merge_mode∈{never,manual}` 조건일 때만(auto_policy는 내부리뷰가 유일 게이트).

> §6.1·6.2를 본 문서에 넣지 않은 이유: 둘 다 라우팅·프롬프트 **아키텍처 변경**이라 baseline이 spec churn에 노출 → cross-review BLOCK 진동(메모리 `cross_review_stale_baseline_repeat`). S1~S3 correctness 슬라이스를 먼저 닫고, 우선순위 3·5는 전용 설계문서로.

---

## 7. 불변식 요약

- INV-S1a/b: 시그니처 없는 codex 무변, 정상종료 무변.
- INV-S2a/b/c: 정상종료 무강등, 변경有 무강등, S1과 중복 안전망(미분류 잔여만).
- INV-S3a/b/c: 임계 내 정상 run 무변, max_cycles 최종캡 유지, infra/retry-소진일 때만 hard-stop.
- 공통: dogfood 배포 동등성 — production caller가 유일 경로(픽스처-only 미허용).
