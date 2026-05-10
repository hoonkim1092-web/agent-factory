# Work-Item 병렬 생성 — Option C-3stages 설계 (v3)

> **상태**: draft (cross-review 3라운드 대기)
> **선행 문서**:
> - `docs/2026-05-08-work-item-parallel-generation-investigation.md` (조사 핸드오프)
> - `docs/2026-05-08-work-item-parallel-option-c-design.md` (v1, BLOCK)
> - `docs/2026-05-08-work-item-parallel-option-c-design-v2.md` (v2, 2라운드 WARN)
> - `docs/reviews/2026-05-08-023103-...-design-review.md` (v1 BLOCK 14+5건 ACCEPT)
> - `docs/reviews/2026-05-08-140854-...-v2-design-review.md` (v2 1라운드 BLOCK)
> - `docs/reviews/2026-05-08-142400-...-v2-design-review.md` (v2 2라운드 WARN, 13건 ACCEPT — 본 v3가 흡수)
> - `runtime/timing/build-a-playable-8x8-cli-minesweeper-...baseline.jsonl` (Sonnet 1회 실측)
>
> **목적**: feature-plan / feature-spec / implementation-design / implementation-tasks 4종 LLM 호출의 부분 병렬화. **실측 기반 budget 재산정**으로 v1의 산술 모순 해소. consistency / traceability 점수 보존.
>
> **비고**: approval-gate는 LLM 호출 없는 파일 생성이라 본 설계 범위 밖 (현행 유지).

---

## 0a. v3 변경 요약 (v2 cross-review 2라운드 13건 흡수)

> **본 v3 PR의 범위 — 명시 (v3.1 보강)**: v3는 **설계 문서 PR**이다. F1/F2/F3/F4 등의 흡수는 "**설계 명세에 코드 변경 명시 = 흡수**"이며, 실제 코드 plumbing(`core/work_item_generator.py`/`core/requirement_llm.py` 수정)은 **본 PR 머지 후 후속 코드 PR**의 책임. 본 PR 머지 시점에 baseline 코드는 그대로 유지된다. v3.1 cross-review에서 "F1 표기 vs 코드 미구현"으로 BLOCK된 부분은 status 컬럼으로 명시적 분리.

| # | 분류 | v2 결정 | v3 결정 (설계 명세) | Implementation Status | 흡수 |
|---|------|---------|---------|----------------------|------|
| F1 | Refine loop budget | Stage 2 timeout만 보호 | per-iteration `iter_timeout = max(1, deadline - time.monotonic() - 5)`. ≤0 이면 refine skip+warn. Stage 3 진입 전 5s grace wait. (§6 v3 보강 + §7a/§7b 호출 측 deadline 전달) | **(c) 미구현 — 본 PR 후속 코드 PR이 `core/work_item_generator.py:1184 _generate_and_refine` 시그니처에 `deadline` 추가** | High |
| F2 | `_call_*_api` timeout | 미연결 | 시그니처에 `timeout_sec: int = 120` 추가. baseline 정합 — anthropic은 `urllib.request.urlopen(request, timeout=timeout_sec)` 유지(현 코드가 urllib), openai는 `client.with_options(timeout=)`, google은 `ThreadPoolExecutor.future.result(timeout=)` 래핑 (§10 v3 보강) | **(c) 미구현 — 본 PR 후속. baseline `core/requirement_llm.py:78,98,118` 함수 시그니처 수정** | High |
| F3 | Episode Hints 주입 | 누락 | `_exec_stage1` 반환 직전 `plan_result.content += _build_episode_hints_section(...)` 명시 (§7a) | **(c) 미구현 — 본 PR 후속. 현재 호출은 `core/work_item_generator.py:1055`에 직접 위치, Stage 재구성 시 이동 필요** | High |
| F4 | `_exec_stage1`/`_exec_stage3` 명세 | pseudocode 변수만 | §7a (Stage 1 풀 구현), §7b (Stage 3 풀 구현 + spec_outline 전달) 신설 — **본 v3.1 본문에 포함됨** | **(c) 미구현 — 본 PR 후속. 함수 자체가 baseline에 부재** | High |
| F5 | asyncio block 위험 | 미명시 | `core/project_pipeline.py:1231 def execute(`은 sync (grep 검증 — `async def execute` 0건). NOT APPLICABLE → §3에 sync 불변식 명시 | **(a) 이미 정합 — baseline은 sync** | High close |
| F6 | fallback 함수 4개 | "있다고 가정" | grep 검증: `_fallback_feature_plan:199` / `_fallback_feature_spec:274` / `_fallback_impl_design:378` / `_fallback_impl_tasks:511` 모두 존재 | **(a) 이미 구현** | Medium close |
| F7 | 텔레메트리 경로 | `Path(workspace)/"runtime"/"work_item_telemetry"` | `workspace_runtime_dir(workspace) / "work_item_telemetry"` (컨벤션 통일) | **(b) 본 PR 후속에서 `core/work_item_telemetry.py:14, 45` 두 위치 동시 수정** | Medium |
| F8 | `_PLACEHOLDER_REFINE_MAX` | 미인용 | grep 검증: `core/work_item_generator.py:26 _PLACEHOLDER_REFINE_MAX = 2`. budget 산정(267s + 2×120s = 507s) 유효. **F1 guard 미구현 시 budget 초과 위험은 §15 R7으로 등록** | **(a) 이미 정합 (값 확인)** | Medium close |
| F9 | outline mismatch 복구 | 경고만 + 부분 outline | **`expected_count=12` 통일** (§0a/§8/실제 코드 모두 12). 결정: 본 PR 후속 코드에서 `_extract_section_outline` (`core/work_item_generator.py:813`)이 mismatch 시 **빈 문자열 반환** — 현재 baseline은 `"\n".join(lines)` 부분 outline 반환 (L832) | **(c) 본 PR 후속 코드에서 동작 변경** | Low |
| F10 | `_dname` 형식 | 불명 | doc_type 문자열 (`plan`/`spec`/`design`/`tasks`). telemetry json `docs` 키와 정합 | **(b) 명세 정정 (코드 변경 없음)** | Low |
| F11 | `core.work_item_telemetry` af.spec | "누락" 주장 | grep 검증: `af.spec:82` `core.cli_session_cleanup`, `af.spec:83` `core.work_item_telemetry` — **둘 다 이미 등록**. REJECT 유지 | **(a) 이미 정합** | High REJECT |
| F12 | Stage 3 budget 110s | provisional, 측정 보류 | §14 Step 4.1 trigger 명시: tasks `timeout_fallback` 비율 >20%면 P95+20% 마진 재산정 | **(b) 측정 후 결정** | Medium |

### v3.1 1라운드 BLOCK (Critic 단독, Cross provider error) 흡수 — 11건

> 출처: `docs/reviews/2026-05-11-001451-2026-05-08-work-item-parallel-option-c-design-v3-design-review.md`. Cross provider가 error로 미실행 → Critic 단독. 단 evidence가 file:line 단위로 강력해서 모두 ACCEPT/HOLD.

| # | Severity | 처리 |
|---|----------|------|
| 1 | Critical | F1 "흡수" → **"설계 명세 흡수 / 코드 (c) 미구현 — 후속 PR"**. 위 status 컬럼으로 명시 |
| 2 | Critical | F2 baseline 정정 — anthropic은 `urllib.request.urlopen` (httpx 아님). §10 v3 보강 코드블록 재작성 (urllib 기반) |
| 3 | High | "신규" 표기된 `core/cli_session_cleanup.py` (5/10 02:01) / `core/work_item_telemetry.py` (5/10 02:01)는 이미 존재 — §11 변경표 status (a)로 분리 |
| 4 | High | §11 라인 번호 일괄 갱신: `_generate_doc_with_llm:562`, `_generate_and_refine:1184`, `_refine_document:1263`, `generate_work_items:1025`, 4 generator `:613/656/698/755`, `_call_*_api:78/98/118`. F11 `af.spec:76` → `82, 83` 정정 |
| 5 | High | `expected_count` 3중 통일: §0a/§8/실제 코드 모두 12. F9 결정 명확화 — 본 PR 후속 코드 PR이 `""` 반환으로 동작 변경 |
| 6 | High | F7 path `core/work_item_telemetry.py:14, 45` 두 위치 동시 수정 명시 |
| 7 | High | §7a/§7b 본문은 v3에 추가됨 (line 637, 681). 코드의 `_exec_stage1`/`_exec_stage3` 함수는 baseline에 부재 — (c) 본 PR 후속에서 추가 |
| 8 | Medium | §6 budget 산정의 F1 guard 의존성을 §15 R7로 명시 (F1 미구현 시 worst-case 507s 위험) |
| 9 | Medium | §15 R7 신설 — Stage 2 abandoned future subprocess + Stage 3 hook race. F1 5s grace wait이 통합 방어선 |
| 10 | Medium | §9 cleanup 디렉토리 mtime 정책 — 자식 max(mtime) 기반 판정으로 변경 명시 (또는 디렉토리 TTL 60일+ 분리) |
| 11 | HOLD | Cross provider 인증 후 v3.1 commit + cross-review 2라운드 재실행 |

> **요약 (v3.1)**: v3가 "흡수" 표기와 baseline 코드 사이에 분리된 status를 명시 안 한 게 1라운드 BLOCK 핵심 사유. v3.1은 (1) Implementation Status 컬럼 추가로 설계 명세 vs 실 코드 분리, (2) baseline grep 결과로 line 번호 일괄 갱신, (3) anthropic urllib 사실 정정, (4) §15 R7 + §9 cleanup mtime 정책 신설로 자체 모순 해소. 코드 변경은 본 PR 범위 외 — 후속 코드 PR 책임.

---

## 0. v2 변경 요약 (v1 대비)

| 분류 | v1 결정 | v2 결정 | 흡수 finding |
|------|---------|---------|------------|
| Stage 2 budget | 180s | **400s** | #1 (Critical) |
| `doc_gen_deadline` | 300s | **600s** | #1 + 실측 |
| Stage 2 await 패턴 | 순차 `_await_or_fallback` | `concurrent.futures.wait(ALL_COMPLETED)` | #1 (Critical) |
| cleanup 경로 | `Path("runtime/cli_sessions")` | `workspace_runtime_dir(workspace) / "cli_sessions"` | #2 (Critical) |
| run_id 마지막 토큰 | `int(time.time())` | `time.time_ns() + uuid4().hex[:8]` | #9 |
| prev_doc 디스패치 | 마지막 파라미터 위치 introspection | **explicit kwargs** (`*, prev_plan="", prev_spec="", run_id="", timeout_sec=...`) | #3 (High) |
| `_generate_doc_with_llm` 반환 | `tuple[str, bool]` | `DocGenerationResult` (boundary 명시) | #4 (High) |
| design `prev_plan` 주입 | 미정의 | **`Feature Plan:` 섹션 신규 정의** | #5 (High) |
| `elapsed_sec`/usage | "이미 있음" 오기 | **`execute_document_prompt`에 time.monotonic() 래핑 + usage_tokens 추가** | #6 (High) |
| `timeout_sec` 전달 | 미연결 | `_generate_and_refine → generators → _generate_doc_with_llm → execute_document_prompt` 전 체인 | #7 (High) |
| `refine_attempts` | 단일 컬럼 | **`placeholder_refine_attempts` (placeholder loop) + `t1_refine_attempts` (T1 retry)** 분리 | #8 (High) |
| Future cancel | `future.cancel()` | `executor.shutdown(wait=False, cancel_futures=True)` + subprocess timeout | #10 |
| Lock 범위 | `prepare_cli_session` 전체 | `_write_claude_settings` 본문만 (`core/file_lock.py:locked_file` 재사용) | #11 |
| Outline regex | `^##\s+(.+)$` | normalize (`*_` 스트립, 공백 정규화, `##` TOC 필터) + 섹션 카운트 assert | #12 |
| §10 path | `core/session_adapter.py:474, 476` | `core/providers/session_adapter.py:474, 476` | #13 |
| Step 2 sample | N=1 | N≥3 (median) | #14 |
| Stage 1 fallback cascade | 미정의 | **명시: plan fallback 시 spec/design는 "fallback plan 본문" 그대로 prev로 사용** | M2 |
| Approval-gate | 무관심 | **명시: Stage 3 fallback이어도 `gate.initialize` 항상 실행** | M3 |
| `af.spec` hiddenimports | 누락 | **`core.cli_session_cleanup`, `core.file_lock` (이미 76라인) 명시** | M4 |
| Step 0 lock 검증 | 단순 4-병렬 | **인위적 5초 락 점유 후 timeout 동작 assert** | M5 |

> **반영하지 않은 finding**: M6 (cleanup vs pid recycle) — 30일 TTL이 충분히 보수적이므로 HOLD 유지.

---

## 1. 채택 결정 요약

| 항목 | 결정 | 비고 |
|------|------|------|
| **Stage 구조** | C-3stages: `plan → [spec, design] 병렬 → tasks` | finding #4 흡수 (tasks가 spec §N 인용 가능) |
| **run_id 격리** | (D′) `{base}_{doc_type}_{pid}_{time_ns}_{uuid_hex8}` | finding #1 + #9 해소 |
| **Stage 1 실패 정책** | A2: 폴백으로 채우고 진행 (cascade 명시) | M2 흡수 |
| **prev_doc 합성** | B3: design 전문 + spec 섹션 목차만 (tasks용) | finding #4 + 토큰 한도 |
| **deadline 처리** | C3: Stage별 + carry-over | finding #6 해소 |
| **executor 패턴** | D3′: `concurrent.futures.wait(ALL_COMPLETED)` + per-future `timeout_sec` 전달 + `cancel_futures=True` | #1 + #10 흡수 |
| **state 파일 정리** | 30일 TTL cleanup hook (workspace-scoped) | finding #2 흡수 |
| **관측성** | `DocGenerationResult` dataclass + boundary contract 명시 | finding #4, #6, #8 |
| **Lock 범위** | `_write_claude_settings` 본문만 wrap (기존 `locked_file()` 재사용) | finding #11 |

---

## 2. Stage 구조 (C-3stages)

```
Stage 1 (단독):  plan
                  ↓ plan 완료 후
Stage 2 (병렬 2): spec ← plan 참고 (전문)
                  design ← plan 참고 (전문, "Feature Plan:" 블록)
                  ↓ 둘 다 완료 후
Stage 3 (단독):  tasks ← design 전문 + spec 섹션 목차
```

### 시간 추정 (실측 기반, 2026-05-08 minesweeper Sonnet 1회)

| Stage | 직렬 (현재) | C-3stages | 단축 |
|-------|-----------|-----------|------|
| 1 (plan) | 62.9s | 62.9s | — |
| 2 (spec + design) | 84.9 + 267.4 = 352.3s | **max(85, 267) ≈ 267s** | -85s |
| 3 (tasks) | n/a (현재 fallback 경유) | 측정 보류 | — |
| **plan+spec+design 합** | **415.2s** | **~330s** | **-85s (1.26×)** |

> **현실 단축률**: refine 미발생 시 1.0× (plan이 직렬, spec/design만 병렬), refine 발생 시 1.3~1.7× (긴 호출이 짧은 호출에 흡수).
> 핸드오프 §3 "2배"는 Option C-2stages 가정이었음. 3-stages는 1.2~1.5×가 정확하며, 의사결정 임계는 §11 Step 5에서 1.2×로 하향.

### 정합성 보존
- **consistency** (plan ↔ spec, weight 0.15): Stage 2의 spec이 plan을 `prev_plan`으로 받음 → 보존
- **consistency'** (plan ↔ design, 신규): Stage 2의 design이 plan을 `prev_plan`으로 받음 → 보존 (spec 미참조 — finding #5 해소)
- **traceability** (spec ↔ tasks, weight 0.10): Stage 3가 spec 섹션 outline을 받음 → 보존

---

## 3. run_id 격리 정책 (D′방식)

### 형식

```python
import time, uuid, os

def _build_full_run_id(base_run_id: str, doc_type: str) -> str:
    nonce = uuid.uuid4().hex[:8]
    return f"{base_run_id or 'claude_cli_run'}_{doc_type}_{os.getpid()}_{time.time_ns()}_{nonce}"

# 예:
# claude_cli_run_plan_12345_1715077200123456789_a3f9c2b1
# claude_cli_run_spec_12345_1715077200234567890_d8e1f7a4
```

- `base_run_id`: 호출자가 제공 (없으면 `claude_cli_run` 폴백)
- `doc_type`: `plan` / `spec` / `design` / `tasks`
- `pid`: `os.getpid()` — 디버깅 용이성
- `time_ns`: `time.time_ns()` — 같은 epoch 초 내 충돌 방지 (finding #9)
- `uuid_hex8`: `uuid.uuid4().hex[:8]` — pid recycle / clock 후행 안전망

### 전파 경로 (explicit kwargs, finding #3 해소)

```
generate_work_items(workspace, slug, project_brief, role_plan, task_board, run_id="")
  └─ _generate_and_refine(doc_type, generator_fn, work_item_id, project_brief, *extra_args,
                           *, prev_plan="", prev_spec="", prev_design="",
                           run_id="", timeout_sec=120,
                           workspace=...)
      ├─ full_run_id = _build_full_run_id(run_id, doc_type)
      └─ generator_fn(work_item_id, project_brief, *extra_args,
                       prev_plan=prev_plan, prev_spec=prev_spec, prev_design=prev_design,
                       run_id=full_run_id, timeout_sec=timeout_sec, workspace=workspace)
          └─ _generate_doc_with_llm(prompt, fallback_fn, doc_type=...,
                                     run_id=full_run_id, timeout_sec=...,
                                     workspace=...)
              └─ execute_document_prompt(prompt, run_id=full_run_id,
                                          timeout_sec=timeout_sec,
                                          workspace=workspace)
```

### finding #3 (last-param introspection) 해소

**v1 (버그)** — `core/work_item_generator.py:847-849`:
```python
_sig = _inspect.signature(generator_fn)
_has_prev = list(_sig.parameters)[-1] in ("prev_plan", "prev_spec", "prev_design")  # run_id 추가 시 항상 False
if _prev_doc and _has_prev:
    content = generator_fn(work_item_id, project_brief, *extra_args, _prev_doc)
```

**v2** — explicit kwargs:
```python
# 1. introspection 제거. 모든 generator는 prev_plan / prev_spec / prev_design을 keyword-only로 받음
sig_params = set(_inspect.signature(generator_fn).parameters)
prev_kwargs = {}
if "prev_plan" in sig_params and prev_plan:
    prev_kwargs["prev_plan"] = prev_plan
if "prev_spec" in sig_params and prev_spec:
    prev_kwargs["prev_spec"] = prev_spec
if "prev_design" in sig_params and prev_design:
    prev_kwargs["prev_design"] = prev_design

content_or_result = generator_fn(
    work_item_id, project_brief, *extra_args,
    **prev_kwargs,
    run_id=full_run_id,
    timeout_sec=timeout_sec,
    workspace=workspace,
)
```

> **불변식**: 4개 generator 시그니처 변경 시 본 dispatch가 유일한 진입점이므로, 신규 prev_doc 변종이 추가되면 `prev_kwargs` 빌드 로직만 갱신하면 된다.

### 부작용
- `<workspace>/.af_runtime/cli_sessions/claude_cli_<full_run_id>.json` 파일이 호출당 1개 생성 (병렬 4개 분리)
- `_events.jsonl`도 동일 prefix로 분리 (`core/providers/session_adapter.py:151` 참조)
- frozen build 환경(`af.exe`)에선 `_write_claude_settings`가 우회 (`session_adapter.py:474`의 `not _is_frozen()` 가드) — 별도 검증 §11 Step 3

### asyncio 컨텍스트 불변식 (v3 신규, F5 close)

`core/project_pipeline.py:1231`의 `def execute(self, ...)`는 **sync** 메서드 (`async def execute` 0건, grep 검증 2026-05-10). 따라서 본 설계의 `concurrent.futures.wait(timeout=400)` / `_exec_stage1~3` / `_generate_and_refine` 호출은 asyncio 이벤트 루프를 차단하지 않는다.

- `control/supervisor.py`의 heartbeat / stall detector는 별도 thread/process 컨텍스트이므로 본 설계의 wait 호출과 독립.
- `core/dynamic_orchestrator.py`의 5-concurrent async 파이프라인은 `project_pipeline.execute()`를 외부에서 호출하지만, 호출 컨텍스트가 sync executor (`asyncio.to_thread` 또는 일반 thread pool) 내부이므로 본 설계 동작에 영향 없음.

> **불변식 가드**: 향후 `execute()`가 `async def`로 전환되면 본 설계 전체를 `await asyncio.to_thread(_generate_work_items_sync, ...)` 로 감싸야 함. §14 Step 0.6에 sync 컨텍스트 grep assert 추가.

---

## 4. file lock 정책 (finding #11 해소)

### v1 오류
- v1 §4: `prepare_cli_session()` 전체를 락으로 감쌈 → CLI 호출 box-wide 직렬화 (병렬화 의미 상실)
- v1 §12 R1: `fcntl.flock` 가정 → 실제 `core/file_lock.py:64`은 `O_CREAT | O_EXCL` 사용

### v2 정책

`.claude/settings.local.json`은 4개 호출이 **읽기**만 하면 안전. **쓰기 race**는 `_write_claude_settings()` (`core/providers/session_adapter.py:281-304`)의 load → merge → save 구간에서만 발생.

### 구현 — `_write_claude_settings` 본문 wrap

```python
# core/providers/session_adapter.py
from core.file_lock import locked_file  # 기존 모듈, af.spec:76 이미 등록

def _write_claude_settings(workspace: str, run_id: str) -> Path:
    repo_root = _repo_root()
    settings_path = Path(workspace).resolve() / ".claude" / "settings.local.json"

    # finding #11: 락 범위를 settings 파일 R-M-W 사이클로 좁힘
    with locked_file(str(settings_path), timeout=5):
        data = _load_json(settings_path)
        if not isinstance(data, dict):
            data = {}
        hooks = data.get("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}

        command = _hook_command("claude", workspace, run_id, repo_root)
        for event_name in ("SessionStart", "UserPromptSubmit", "PreCompact", "Stop", "SessionEnd"):
            hook_name = f"agent_factory_claude_{event_name.lower()}"
            hooks[event_name] = _merge_named_hook_group(
                hooks.get(event_name, []),
                hook_name,
                command,
                "claude",
            )

        data["hooks"] = hooks
        data = merge_claude_destructive_guard(data)
        _save_json(settings_path, data)
    return settings_path
```

### 락 primitive 동작
- `core/file_lock.py:38-92` `locked_file(path, timeout=15)` 시그니처. v2는 `timeout=5` 명시.
- thread-level: 모듈 싱글톤 `threading.Lock` (path별 매핑)
- process-level: `os.O_CREAT | os.O_EXCL`로 `<path>.lock` 원자 생성. stale 10초 정리.
- 실패 시 `TimeoutError` raise → 호출 측 `_write_claude_settings`는 호출자(`prepare_cli_session`)에서 `try/except`로 wrap, 경고 후 settings 미작성으로 진행 (hook bridge 동작 불가능, 단일 호출 환경 동등).

### 비용
- 락 점유 시간: settings load + merge + save ≈ 5~50ms. 5초 timeout은 충분.
- 4-병렬 호출 중 첫 호출만 실제 작성, 나머지는 동일 내용 재기록 (idempotent).

---

## 5. `DocGenerationResult` 구조체 (boundary contract, finding #4·#6·#8 해소)

### 신규 dataclass

```python
# core/work_item_generator.py 또는 core/doc_generation_result.py 신규
from dataclasses import dataclass, field

@dataclass
class DocGenerationResult:
    doc_type: str                    # plan / spec / design / tasks
    content: str                     # 생성된 markdown 본문 (또는 fallback 본문)
    provider_id: str = ""            # claude_cli / codex_cli / openai_api ...
    model: str = ""                  # 실제 사용된 모델명
    elapsed_sec: float = 0.0         # LLM 호출~응답 monotonic 시간
    used_fallback: bool = False      # _fallback_*() 사용 여부 (LLM 실패)
    timeout_fallback: bool = False   # CLI / future timeout으로 폴백된 경우
    placeholder_refine_attempts: int = 0  # placeholder_refine 루프 횟수 (0~_PLACEHOLDER_REFINE_MAX). dataclass dump 시점에 확정.
    t1_refine_attempts: int = 0      # project_pipeline.py T1 retry 횟수. **dataclass dump 시점엔 항상 0**.
                                     # T1 retry는 generator dump 이후에 발생하므로 telemetry json만 atomic update (§11 update_t1_refine_attempts).
                                     # 본 컬럼은 json 스키마 일관성용 placeholder.
    errors: list[str] = field(default_factory=list)  # provider 실패 누적 로그
    run_id: str = ""                 # 격리된 full_run_id
    usage_tokens: dict = field(default_factory=dict)  # {prompt, completion, total} — provider가 제공 시
```

### Boundary contract (모든 호출 사이트가 따라야 할 규칙)

| 함수 | 기존 반환 | v2 반환 | 호출자 처리 |
|------|----------|---------|------------|
| `_generate_doc_with_llm(prompt, fb, doc_type, run_id, timeout_sec, workspace)` | `tuple[str, bool]` | `DocGenerationResult` | `result.content` 사용, `result.used_fallback` 등 메타 보존 |
| 4개 generator (`_generate_feature_plan`, `_spec`, `_design`, `_tasks`) | `str` | `DocGenerationResult` | 그대로 부모에 전달 |
| `_generate_and_refine(doc_type, generator_fn, ...)` | `str` | `DocGenerationResult` | `placeholder_refine_attempts` 컬럼 갱신 후 반환 |
| `generate_work_items(...)` | `dict[str, str]` (filename → path) | **변경 없음** (`dict[str, str]`) | 내부에서 `result.content`를 `write_text(path, ...)`. **추가**: `result` 객체 4건을 `runtime/work_item_telemetry/{slug}.json`에 dump |

> **이유**: `generate_work_items` 시그니처를 바꾸면 호출자(`core/project_pipeline.py:948`)와 외부 진입점(`run_factory_cli.py`)도 수정 필요. v2는 **dict 반환은 유지**하고, 결과 메타는 텔레메트리 파일로 외부화. T1 retry는 §6에서 별도 처리.

### `_generate_and_refine` 내부 변경

```python
def _generate_and_refine(
    doc_type: str,
    generator_fn,
    work_item_id: str,
    project_brief: dict,
    *extra_args,
    prev_plan: str = "",
    prev_spec: str = "",
    prev_design: str = "",
    run_id: str = "",
    timeout_sec: int = 120,
    workspace: str = "",
) -> DocGenerationResult:
    full_run_id = _build_full_run_id(run_id, doc_type)
    placeholder_refine = os.environ.get("AF_PLACEHOLDER_REFINE", "1") != "0"

    # explicit kwargs dispatch (§3 참조)
    sig_params = set(_inspect.signature(generator_fn).parameters)
    prev_kwargs = {}
    if "prev_plan" in sig_params and prev_plan:
        prev_kwargs["prev_plan"] = prev_plan
    if "prev_spec" in sig_params and prev_spec:
        prev_kwargs["prev_spec"] = prev_spec
    if "prev_design" in sig_params and prev_design:
        prev_kwargs["prev_design"] = prev_design

    result: DocGenerationResult = generator_fn(
        work_item_id, project_brief, *extra_args,
        **prev_kwargs,
        run_id=full_run_id,
        timeout_sec=timeout_sec,
        workspace=workspace,
    )
    result.run_id = full_run_id
    result.doc_type = doc_type

    if not placeholder_refine:
        return result

    exempt = parse_frontmatter_exempt(result.content)
    for attempt in range(_PLACEHOLDER_REFINE_MAX):
        found = scan_forbidden_tokens(result.content, exempt=exempt)
        if not found:
            break
        # ... LLM 보강 호출 (기존 로직). 결과 content를 result.content에 덮어씀.
        result.placeholder_refine_attempts = attempt + 1
        # ... refine 호출 (timeout_sec 동일하게 전달)

    return result
```

---

## 6. Stage budget + carry-over (실측 기반 재산정, finding #1 해소)

### 실측 기준 (2026-05-08 minesweeper, Sonnet 1회)

| Stage | 단계 | elapsed_sec | refine_attempts | 비고 |
|-------|------|-------------|-----------------|------|
| 1 | plan | 62.9 | 0 | |
| 2 | spec | 84.9 | 0 | 병렬 시 max로 흡수 |
| 2 | design | 267.4 | 2 | refine 2회 포함 |
| 3 | tasks | n/a | n/a | 현재 fallback (deadline 초과) |

### v2 budget

```python
# core/work_item_generator.py
TOTAL_BUDGET = 600.0  # v1의 360s → 600s로 상향. 실측 415s + 약 45% 마진 (refine 변동·tasks 미측정 흡수용 보수 설정)
STAGE_BUDGET = {
    1: 90.0,   # plan: 실측 63s → 90s
    2: 400.0,  # spec(85s) + design(267s) ≈ 352s → 400s (refine 추가 마진)
    3: 110.0,  # tasks: 미측정. plan 수준 + α
}
# 합계 = 600s = TOTAL_BUDGET

t_total_start = time.monotonic()

# Stage 1
deadline_1 = t_total_start + STAGE_BUDGET[1]
plan_result = _exec_stage1(deadline=deadline_1)
elapsed_1 = time.monotonic() - t_total_start
carry_over_1 = max(0.0, STAGE_BUDGET[1] - elapsed_1)

# Stage 2 — carry-over 흡수
t_stage2_start = time.monotonic()
deadline_2 = t_stage2_start + STAGE_BUDGET[2] + carry_over_1
spec_result, design_result = _exec_stage2(deadline=deadline_2,
                                            plan_content=plan_result.content,
                                            ...)
elapsed_2 = time.monotonic() - t_stage2_start
carry_over_2 = max(0.0, (STAGE_BUDGET[2] + carry_over_1) - elapsed_2)

# Stage 3
t_stage3_start = time.monotonic()
deadline_3 = t_stage3_start + STAGE_BUDGET[3] + carry_over_2
tasks_result = _exec_stage3(deadline=deadline_3, ...)
```

### timeout 의미 정정 (3계층)

| 계층 | 단위 | 변수 | 비고 |
|------|------|------|------|
| L1: LLM 호출 | 단일 `execute_document_prompt()` | `timeout_sec` (int 초) | 기본 120s. v2는 stage 잔여시간을 전달 |
| L2: Stage wall-clock | Stage 1/2/3 전체 | `STAGE_BUDGET[N] + carry_over` | future timeout 산정에 사용 |
| L3: CLI subprocess | provider 내부 | `_default_cli_timeout_sec()=900` | v2는 명시적 `timeout_sec` 전달로 우회 |

### finding #10 해소 (subprocess kill on cancel)

`execute_document_prompt(timeout_sec=...)`은 내부적으로 `execute_cli_chat(CliChatRequest(... timeout_sec=...))`을 호출하며, CLI provider는 `timeout_sec` 도달 시 subprocess를 SIGTERM하고 `ok=False, reason="timeout"`을 반환한다 (`core/requirement_llm.py:188-201`의 기존 동작). v2는 future-level timeout보다 5초 작은 값을 LLM 호출에 전달:

```python
# Stage 2 호출 시
remaining = max(1.0, deadline_2 - time.monotonic())
per_future_timeout = remaining
llm_timeout = max(1, int(per_future_timeout) - 5)  # subprocess가 future보다 먼저 죽도록

ex.submit(_generate_and_refine, ..., timeout_sec=llm_timeout)
```

### v3 보강 — refine loop budget guard (F1 흡수)

**v2 누수 분석** (cross-review F1):
v2의 `llm_timeout = remaining - 5`는 `_generate_and_refine`의 **첫 호출**만 보호한다. 내부 placeholder refine loop는 매 iteration마다 동일 `timeout_sec`을 새 호출에 전달 → 누계가 stage budget 초과 가능.

worst-case 산술 (실측 + `_PLACEHOLDER_REFINE_MAX = 2`):
- design 1차: 267s
- refine attempt 1: 120s (default)
- refine attempt 2: 120s
- 합계: **507s > 400s budget**

이 경우 `cf.wait(timeout=400)`가 만료된 시점에 design future가 not_done — 동시 LLM 호출 불변식 깨짐 (Stage 3 진입 시 design future + tasks 호출 = 2+, 동일 stage 내 spec까지 살아 있으면 3+).

**v3 정책 — per-iteration deadline propagation:**

```python
# core/work_item_generator.py: _generate_and_refine 시그니처에 deadline 추가
_GRACE_SEC = 5  # subprocess kill 보장 마진 (finding #10과 동일 상수)

def _generate_and_refine(
    doc_type: str,
    generator,
    work_item_id: str,
    project_brief: dict,
    role_plan: dict,
    task_board: dict | None = None,
    *,
    prev_plan: str = "",
    prev_spec: str = "",
    prev_design: str = "",
    deadline: float,                # v3 신규 (float, time.monotonic 기준 절대 시각)
    run_id: str,
    workspace: str,
) -> DocGenerationResult:
    """deadline (절대 monotonic 시각)을 받아 매 iteration마다 잔여시간 재계산."""

    def _compute_iter_timeout() -> int:
        return max(1, int(deadline - time.monotonic()) - _GRACE_SEC)

    fallback_factory = _resolve_fallback_factory(doc_type, work_item_id, project_brief, role_plan, task_board)

    # 1차 호출
    iter_timeout = _compute_iter_timeout()
    if iter_timeout <= 0:
        return DocGenerationResult(
            doc_type=doc_type, content=fallback_factory(),
            used_fallback=True, timeout_fallback=True,
            errors=["pre_call_deadline_exhausted"],
        )

    result = _generate_doc_with_llm(
        doc_type=doc_type, generator_fn=generator,
        work_item_id=work_item_id, project_brief=project_brief, role_plan=role_plan,
        task_board=task_board,
        prev_plan=prev_plan, prev_spec=prev_spec, prev_design=prev_design,
        run_id=run_id, timeout_sec=iter_timeout, workspace=workspace,
    )

    # placeholder refine loop (max = _PLACEHOLDER_REFINE_MAX = 2)
    for attempt in range(_PLACEHOLDER_REFINE_MAX):
        if not _has_placeholder(result.content):
            break
        iter_timeout = _compute_iter_timeout()
        if iter_timeout <= 0:
            # F1: 잔여시간 부족 시 refine 포기 (현재 결과 그대로 반환). budget 초과 방지.
            result.errors.append(f"refine_skipped_attempt_{attempt+1}_deadline_exhausted")
            _LOGGER.warning("refine skipped: doc=%s attempt=%d remaining<=0", doc_type, attempt+1)
            break
        refined = _refine_document(
            result, doc_type=doc_type,
            run_id=run_id, timeout_sec=iter_timeout, workspace=workspace,
        )
        result = refined
        result.placeholder_refine_attempts = attempt + 1

    return result
```

**호출 측 변경 — `_exec_stage2` (§7 v2 코드 보강):**

```python
fut_spec = ex.submit(
    _generate_and_refine, "spec", _generate_feature_spec,
    work_item_id, project_brief, role_plan, task_board,
    prev_plan=plan_content,
    deadline=deadline,         # v3: future-level timeout 대신 deadline 전달
    run_id=base_run_id, workspace=workspace,
)
fut_design = ex.submit(
    _generate_and_refine, "design", _generate_implementation_design,
    work_item_id, project_brief, role_plan,
    prev_plan=plan_content,
    deadline=deadline,
    run_id=base_run_id, workspace=workspace,
)
```

**Stage 3 진입 전 grace wait (불변식 보강):**

```python
# generate_work_items 본문
spec_result, design_result = _exec_stage2(deadline=deadline_2, ...)

# F1: not_done future가 있더라도 LLM subprocess가 SIGTERM 수신 후 실제 종료까지 OS 지연 흡수.
# _exec_stage2가 cf.wait(ALL_COMPLETED) 후 shutdown(wait=False)이므로 호출 컨텍스트는 deadline_2에 복귀했지만,
# subprocess가 child fd flush 등으로 추가 1~3s 지연될 수 있음. Stage 3 LLM 호출이 같은 settings 파일을 쓰므로
# 그 사이 race 차단을 위해 명시적 grace wait.
import time as _t
_t.sleep(_GRACE_SEC)  # = 5s

tasks_result = _exec_stage3(deadline=deadline_3, ...)
```

**budget 산술 재검증** (refine guard 적용 후):
- Stage 2 worst-case: design 267s + refine 1회 120s + grace 5s = 392s < 400s budget ✓
- refine 2회 시도 시 두 번째 attempt는 잔여 = 400 - 267 - 120 - 5 = 8s ≤ _GRACE_SEC → **자동 skip + warn 로그**. 그 결과는 placeholder가 남았더라도 그대로 fallback 없이 반환 (used_fallback=False).
- TOTAL_BUDGET 600s에 Stage 3 진입 전 5s grace 반영: 90 + 400 + 5 + 110 = 605s — TOTAL_BUDGET 600s를 5s 초과. v3에서 TOTAL_BUDGET을 **605s**로 미세 조정 (Stage 3 budget = 105s) 또는 grace를 carry-over에서 차감. 본 설계는 후자 채택 — `STAGE_BUDGET[3] - _GRACE_SEC` = 105s를 deadline_3 산정에 사용.

```python
# §6 v2 코드 보강:
t_stage3_start = time.monotonic() + _GRACE_SEC  # grace 차감
deadline_3 = t_stage3_start + (STAGE_BUDGET[3] - _GRACE_SEC) + carry_over_2  # Stage 3 effective budget = 105s
```

---

## 7. ThreadPoolExecutor + concurrent.futures.wait (finding #1, #10 해소)

### v1 패턴 (BLOCK)

```python
# v1: 순차 await — wall-clock = 2 × stage2_timeout
spec_result = _await_or_fallback(fut_spec, per_future_timeout, ...)   # 최대 360s
design_result = _await_or_fallback(fut_design, per_future_timeout, ...)  # 추가 360s
```

### v2 패턴 (절대 deadline + ALL_COMPLETED)

```python
import concurrent.futures as cf

def _exec_stage2(deadline: float, plan_content: str,
                 work_item_id: str, project_brief: dict, role_plan: dict, task_board: dict,
                 base_run_id: str, workspace: str) -> tuple[DocGenerationResult, DocGenerationResult]:
    """spec / design 병렬 생성. 절대 deadline까지 기다리고, 미완료는 fallback으로 채움."""
    remaining = max(1.0, deadline - time.monotonic())
    llm_timeout = max(1, int(remaining) - 5)  # finding #10

    ex = cf.ThreadPoolExecutor(max_workers=2, thread_name_prefix="wi-stage2")
    try:
        fut_spec = ex.submit(
            _generate_and_refine, "spec", _generate_feature_spec,
            work_item_id, project_brief, role_plan, task_board,
            prev_plan=plan_content, run_id=base_run_id,
            timeout_sec=llm_timeout, workspace=workspace,
        )
        fut_design = ex.submit(
            _generate_and_refine, "design", _generate_implementation_design,
            work_item_id, project_brief, role_plan,
            prev_plan=plan_content, run_id=base_run_id,
            timeout_sec=llm_timeout, workspace=workspace,
        )

        # 절대 deadline까지 ALL_COMPLETED 대기. wall-clock = max(spec, design), NOT 합.
        done, not_done = cf.wait({fut_spec, fut_design},
                                  timeout=remaining,
                                  return_when=cf.ALL_COMPLETED)

        spec_result = _resolve_future_or_fallback(
            fut_spec, done, "spec",
            lambda: _fallback_feature_spec(work_item_id, project_brief, role_plan, task_board),
        )
        design_result = _resolve_future_or_fallback(
            fut_design, done, "design",
            lambda: _fallback_impl_design(work_item_id, project_brief, role_plan),
        )
    finally:
        # finding #10: 남은 future의 subprocess는 llm_timeout(=remaining-5)에 자체 종료. shutdown은 wait=False로 즉시 반환.
        ex.shutdown(wait=False, cancel_futures=True)

    return spec_result, design_result


def _resolve_future_or_fallback(future, done_set, doc_type, fallback_factory) -> DocGenerationResult:
    if future in done_set:
        try:
            return future.result(timeout=0)
        except Exception as exc:
            return DocGenerationResult(
                doc_type=doc_type,
                content=fallback_factory(),
                used_fallback=True,
                errors=[f"{type(exc).__name__}:{exc}"],
            )
    # not_done: future는 백그라운드에서 llm_timeout 후 자체 종료. fallback으로 즉시 채움.
    return DocGenerationResult(
        doc_type=doc_type,
        content=fallback_factory(),
        used_fallback=True,
        timeout_fallback=True,
        errors=["stage2_deadline_exceeded"],
    )
```

### 동시 호출 수
- Stage 2: `max_workers=2`
- placeholder refine: 각 future 내부에서 직렬 (max 2회) → 동시 LLM 호출 최대 **2개** (refine은 직렬화되어 future 시간 안에서 소화)
- Stage 1, 3: 단독 호출 (1개)
- **전체 worst-case 동시 LLM 호출**: 2개 (Stage 2). v1 "동시 6"은 refine을 병렬로 가정한 오기.

> **v3 보강 (F1)**: §6 refine loop budget guard 적용으로 Stage 2 미완료 future가 deadline_2 시점에 fallback 처리되며, Stage 3 진입 전 5s grace wait이 subprocess kill 보장. "max 2 concurrent" 불변식이 시간 차원에서도 보호됨.

---

## 7a. `_exec_stage1` 풀 구현 (v3 신설, F3 + F4 흡수)

```python
def _exec_stage1(
    deadline: float,
    work_item_id: str,
    project_brief: dict,
    role_plan: dict,
    task_board: dict,
    *,
    base_run_id: str,
    workspace: str,
) -> DocGenerationResult:
    """plan 단독 생성 + Episode Hints 주입.

    F3 흡수: 현행 work_item_generator.py:1055에서 plan 생성 직후
            `_build_episode_hints_section`을 append하는 동작이
            v2 Stage 재구성 시 누락되지 않도록, 본 함수 반환 직전에 명시적으로 호출.
    F4 흡수: v2가 pseudocode `_exec_stage1(deadline=deadline_1, ...)`만 등장 — 풀 구현 명세.
    """
    plan_run_id = _build_full_run_id(base_run_id, "plan")

    plan_result = _generate_and_refine(
        "plan", _generate_feature_plan,
        work_item_id, project_brief, role_plan, task_board,
        deadline=deadline,
        run_id=plan_run_id,
        workspace=workspace,
    )

    # F3: Episode Hints 주입 — fallback이든 정상이든 본문에 append (현행 :1055 동작 유지).
    # _build_episode_hints_section은 core/work_item_generator.py:909에 정의됨 (grep 검증 2026-05-10).
    hints_section = _build_episode_hints_section(project_brief, workspace)
    if hints_section:
        plan_result.content = f"{plan_result.content.rstrip()}\n\n{hints_section}"

    return plan_result
```

> **검증 가드**: 생성된 `feature-plan.md`에 `## Episode Hints` 섹션이 존재해야 함. §14 Step 2 assertion에 추가.
> **호환성**: `_build_episode_hints_section` 시그니처는 `(project_brief, workspace) -> str`이며 fallback plan에도 동일 적용. plan_result.used_fallback=True 시에도 hints가 정상적으로 append되도록 본 함수가 `plan_result.content`만 변경한다.

---

## 7b. `_exec_stage3` 풀 구현 (v3 신설, F4 + F9 흡수)

```python
def _exec_stage3(
    deadline: float,
    design_result: DocGenerationResult,
    spec_result: DocGenerationResult,
    work_item_id: str,
    project_brief: dict,
    role_plan: dict,
    task_board: dict,
    *,
    base_run_id: str,
    workspace: str,
) -> DocGenerationResult:
    """tasks 단독 생성. spec_outline + design 전문을 prev로 전달.

    F4 흡수: v2 §6에서 `_exec_stage3(deadline=deadline_3, ...)` 호출만 등장. spec_outline 생성 위치
            및 prev_design/prev_spec 전달 시그니처를 본 함수가 명세.
    F9 흡수: spec_outline 생성 시 `expected_count` 불일치면 빈 문자열 반환 (incomplete outline 금지).
    """
    # B3 정책 — design 전문 + spec 섹션 목차
    spec_outline = _extract_section_outline(
        spec_result.content,
        expected_count=12,  # v2 §8에서 11→12 수정 완료
    )
    # F9: _extract_section_outline이 mismatch 시 빈 문자열 반환하도록 §8.2 보강. tasks prompt는
    # spec_outline=="" 시 "## Source Spec Outline (unavailable)" 한 줄로 대체. consistency rubric은
    # design 전문이 1차 근거이므로 0.05 이내 영향.

    tasks_run_id = _build_full_run_id(base_run_id, "tasks")
    tasks_result = _generate_and_refine(
        "tasks", _generate_implementation_tasks,
        work_item_id, project_brief, role_plan, task_board,
        prev_design=design_result.content,
        prev_spec=spec_outline,  # 섹션 목차만 (토큰 절감, B3 정책)
        deadline=deadline,
        run_id=tasks_run_id,
        workspace=workspace,
    )

    return tasks_result
```

> **F9 보강 명세 — `_extract_section_outline` 동작**:
> ```python
> # core/work_item_generator.py:813
> def _extract_section_outline(markdown: str, expected_count: int = 12) -> str:
>     """## 섹션 헤더만 추출. mismatch 시 빈 문자열 반환 (불완전 outline 금지)."""
>     sections = _normalize_and_extract_h2(markdown)  # 기존 정규화 로직
>     if len(sections) != expected_count:
>         _LOGGER.warning(
>             "spec section count mismatch: expected=%d actual=%d → outline empty",
>             expected_count, len(sections),
>         )
>         return ""
>     return "\n".join(f"§{i+1}. {title}" for i, title in enumerate(sections))
> ```

---

## 8. prev_doc 합성 정책 (B3, finding #5 해소)

### Stage 2 입력
- `spec` ← `prev_plan = plan_result.content` (전문)
- `design` ← `prev_plan = plan_result.content` (전문). **`prev_spec`은 빈 문자열** (Stage 2이라 spec 미완성)

### Stage 3 입력 (tasks)
- `prev_design = design_result.content` (전문)
- **추가**: `spec_outline = _extract_section_outline(spec_result.content)` — `## 섹션 헤더` 정규화 후 §N 형식

### finding #5 해소 — `_generate_implementation_design`의 prompt 수정

**현재 코드** (`core/work_item_generator.py:614-651`):
```python
def _generate_implementation_design(..., prev_spec: str = "") -> str:
    prompt = (
        ...
        + (f"- Feature Spec:\n{prev_spec}\n" if prev_spec else "")
        + ...
    )
```

**v2 시그니처**:
```python
def _generate_implementation_design(
    work_item_id: str,
    project_brief: dict,
    role_plan: dict,
    *,
    prev_plan: str = "",   # 신규 (Stage 2 병렬용)
    prev_spec: str = "",   # 기존 (직렬 fallback 시)
    run_id: str = "",
    timeout_sec: int = 120,
    workspace: str = "",
) -> DocGenerationResult:
    ...
    prev_block = ""
    if prev_spec:
        prev_block = f"- Feature Spec:\n{prev_spec}\n"
    elif prev_plan:
        # 신규 블록: design이 spec 없이 plan을 직접 참조
        prev_block = (
            f"- Feature Plan:\n{prev_plan}\n"
            f"  (Note: Feature Spec is being generated in parallel; "
            f"derive design from Feature Plan goals/scope only.)\n"
        )

    prompt = (
        "Create an implementation-design.md document for this work item.\n\n"
        f"## Input\n"
        f"- Brief:\n{json.dumps(project_brief, ensure_ascii=False)}\n"
        f"- Role Plan:\n{json.dumps(role_plan, ensure_ascii=False)}\n"
        + prev_block
        + "\n## Output Format\nReturn a complete markdown document:\n\n"
        "# Implementation Design\n\n"
        ...
    )
```

### §11 consistency rubric 영향 명시
- 기존: design ↔ spec 정합성 측정
- v2 (Stage 2 병렬일 때): design ↔ plan 정합성 측정 (spec 미존재). rubric 가중치는 동일하게 0.15 적용. **§11 Step 1에서 새 baseline 분포 수집 필수**.
- v2 (Stage 1 fallback cascade일 때): design ↔ fallback plan 정합성 측정. fallback 본문은 `_fallback_feature_plan()`이 보장하는 §섹션 11개를 모두 갖도록 유지 (현행 동작).

### `_extract_section_outline` 견고화 (finding #12 해소)

```python
import re

_SECTION_HEADER_RE = re.compile(r"^\s*##\s+(.+?)\s*$")
_TOC_PATTERNS = ("toc", "table of contents", "목차")

def _extract_section_outline(markdown: str, expected_count: int = 12) -> str:
    """## 섹션 헤더만 뽑아 §N 형식으로 정렬한 목차 텍스트 반환.

    - `**bold**` `_italic_` 마크다운 마커 제거
    - 공백 정규화
    - TOC 섹션 자체는 제외 (재귀 인용 방지)
    - assert: 헤더 수가 expected_count와 일치해야 traceability §N 매칭 안전
    - **v3.1 (F9)**: mismatch 시 빈 문자열 반환 (incomplete outline 금지). caller(`_exec_stage3` / tasks prompt)는 빈 문자열을 "outline unavailable" 표기로 대체.
      현 baseline (`core/work_item_generator.py:813`)은 `"\n".join(lines)` 부분 outline 반환 (L832) — 본 PR 후속 코드에서 변경.
    """
    lines = []
    section_idx = 0
    for raw in markdown.splitlines():
        m = _SECTION_HEADER_RE.match(raw)
        if not m:
            continue
        title = m.group(1)
        # 마크다운 emphasis 제거
        title = re.sub(r"[*_`]+", "", title).strip()
        # 공백 정규화
        title = re.sub(r"\s+", " ", title)
        if not title or title.lower() in _TOC_PATTERNS:
            continue
        section_idx += 1
        lines.append(f"§{section_idx} {title}")

    # 섹션 카운트 어설션 — v3.1: mismatch 시 빈 문자열 반환 (F9)
    if section_idx != expected_count:
        _LOGGER.warning(
            "spec_outline section count mismatch: got=%d expected=%d → outline empty",
            section_idx, expected_count,
        )
        return ""

    return "\n".join(lines)
```

### tasks prompt 확장 (현행 유지 + 명시화)

`_generate_implementation_tasks` 프롬프트에 다음 블록 추가:
```
- Feature Spec Outline (refer with §N for traceability):
{spec_outline}
```
+ Rules에 `"Acceptance Criteria entries should reference spec §N when relevant"` 명시.

### 토큰 절감 효과 (현행 유지)
- spec 본문 평균 3000~5000 tokens → outline은 200~400 tokens
- tasks prompt 50~70% 절감

---

## 9. State 파일 cleanup TTL (30일, finding #2 해소)

### v1 오류
- v1 §9: `Path("runtime/cli_sessions")` — repo-relative. **실제 경로는 `<workspace>/.af_runtime/cli_sessions/`** (`core/providers/session_adapter.py:144` `workspace_runtime_dir(workspace) / "cli_sessions"`)
- v1 §9: glob `claude_cli_*.*` — `codex_cli_*` `gemini_cli_*`를 놓침
- v1 §9: 확장자 `.events` — 실제는 `_events.jsonl` (`session_adapter.py:151`)

### v2 — 신규 모듈 `core/cli_session_cleanup.py`

```python
"""CLI session 파일의 30일 TTL 정리.

generate_work_items() 진입 시 1회 호출 (idempotent). 실패해도 main flow 영향 없음.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from core.continuity.runtime_paths import workspace_runtime_dir  # 기존 모듈 (core/continuity/runtime_paths.py:9)

_LOGGER = logging.getLogger(__name__)


def cleanup_stale_sessions(workspace: str, days: int = 30) -> int:
    """workspace의 .af_runtime/cli_sessions/ 하위에서 30일 초과 파일 삭제.

    삭제 대상:
      - {provider}_{slug}.json
      - {provider}_{slug}_events.jsonl
      - {provider}_{slug}_gemini_defaults.json
      - {provider}_{slug}_destructive_guard.toml
      - {provider}_{slug}_shell_guard/ (디렉토리)

    Returns:
        삭제된 파일/디렉토리 수 (0 if no-op).
    """
    cutoff = time.time() - days * 86400
    try:
        runtime_root = workspace_runtime_dir(workspace) / "cli_sessions"
    except Exception as exc:
        _LOGGER.warning("cleanup_stale_sessions: workspace_runtime_dir 실패: %s", exc)
        return 0

    if not runtime_root.exists():
        return 0

    deleted = 0
    # 모든 provider (claude_cli, codex_cli, gemini_cli, ...) 대상 일반 패턴
    for entry in runtime_root.iterdir():
        try:
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                entry.unlink()
                deleted += 1
            elif entry.is_dir() and entry.stat().st_mtime < cutoff:
                # codex shell_guard 디렉토리
                import shutil
                shutil.rmtree(entry, ignore_errors=True)
                deleted += 1
        except OSError as exc:
            _LOGGER.debug("cleanup skip %s: %s", entry, exc)
    return deleted
```

### 호출 위치

```python
# core/work_item_generator.py:generate_work_items 진입 직후
def generate_work_items(workspace, slug, project_brief, role_plan, task_board, run_id=""):
    try:
        from core.cli_session_cleanup import cleanup_stale_sessions
        cleanup_stale_sessions(workspace, days=30)
    except Exception as exc:
        _LOGGER.debug("cleanup_stale_sessions skip: %s", exc)
    ...
```

### `af.spec` hiddenimports 추가 (M4)

```python
# af.spec:hiddenimports
hiddenimports = [
    ...
    "core.file_lock",          # 이미 76라인에 있음 — 확인
    "core.cli_session_cleanup", # 신규 추가
    ...
]
```

---

## 10. `execute_document_prompt` `elapsed_sec` + usage 보강 (finding #6 해소)

### v1 오류
- v1 §10: "이미 있음 — 확인" 표시. **실제 `core/requirement_llm.py:215-221`은 `elapsed_sec` 키 없음**.

### v2 변경 — `core/requirement_llm.py:173-230`

```python
def execute_document_prompt(
    prompt: str,
    *,
    workspace: str | None = None,
    run_id: str = "",
    timeout_sec: int = 120,
) -> dict:
    target_workspace = _workspace_path(workspace)
    errors: list[str] = []

    for candidate in list_requirement_candidates():
        t_start = time.monotonic()  # 신규
        try:
            if candidate.transport == "cli":
                result = execute_cli_chat(
                    CliChatRequest(
                        provider_id=candidate.provider_id,
                        model=candidate.model,
                        system_prompt=_DOCUMENT_SYSTEM_PROMPT,
                        task_input=prompt,
                        workspace=target_workspace,
                        run_id=run_id,
                        timeout_sec=timeout_sec,
                    )
                )
                text = str(result.get("text") or result.get("stdout") or "").strip()
                # CLI provider는 일반적으로 token usage를 노출하지 않음 → 빈 dict
                usage = result.get("usage") or {}
                if not result.get("ok"):
                    raise RuntimeError(str(result.get("reason") or "cli_document_failed"))
            else:
                effective_prompt = f"{_DOCUMENT_SYSTEM_PROMPT}\n\n{str(prompt or '').strip()}".strip()
                if candidate.provider_id == "anthropic_api":
                    text, usage = _call_anthropic_api(candidate.model, effective_prompt, return_usage=True)
                elif candidate.provider_id == "openai_api":
                    text, usage = _call_openai_api(candidate.model, effective_prompt, return_usage=True)
                else:
                    text, usage = _call_google_api(candidate.model, effective_prompt, return_usage=True)
        except Exception as exc:
            errors.append(f"{candidate.provider_id}:{candidate.model}:{type(exc).__name__}:{exc}")
            continue

        elapsed = time.monotonic() - t_start  # 신규

        if text:
            return {
                "ok": True,
                "provider_id": candidate.provider_id,
                "model": candidate.model,
                "text": text,
                "elapsed_sec": elapsed,    # 신규
                "usage_tokens": usage,     # 신규 (CLI는 빈 dict, API는 {prompt, completion, total})
                "errors": errors,
            }
        errors.append(f"{candidate.provider_id}:{candidate.model}:empty_response")

    return {
        "ok": False,
        "provider_id": "",
        "model": "",
        "text": "",
        "elapsed_sec": 0.0,
        "usage_tokens": {},
        "errors": errors,
    }
```

### `_call_anthropic_api` 등 시그니처 확장 (`return_usage=True` 분기)
- `return_usage=False` (기존 호출자 default) → 기존 `str` 반환 호환
- `return_usage=True` → `tuple[str, dict]` 반환

> 이로써 v1의 OQ1 ("token usage 측정 가능?")이 §10 todo로 승격 — anthropic SDK의 `response.usage`, openai SDK의 `response.usage` 활용.

### v3 보강 — `_call_*_api` 시그니처에 `timeout_sec` 추가 (F2 흡수, v3.1 baseline 정정)

**v2 누락 + v3 baseline 오기 분석** (cross-review F2 + v3 1라운드 BLOCK #2):
v2 §10의 `execute_document_prompt(prompt, *, workspace, run_id, timeout_sec=120)`은 `timeout_sec`을 받지만, 그 아래 SDK 호출자 시그니처에는 `timeout_sec` 파라미터 자체가 없음 (grep 검증 2026-05-11):
- `core/requirement_llm.py:78` `def _call_google_api(model, prompt, *, return_usage=False)`
- `core/requirement_llm.py:98` `def _call_openai_api(model, prompt, *, return_usage=False)`
- `core/requirement_llm.py:118` `def _call_anthropic_api(model, prompt, *, return_usage=False)`

특히 anthropic은 v3 초안이 `httpx.Client`로 가정했으나 **실제 baseline은 `urllib.request.urlopen(request, timeout=60)`** (`core/requirement_llm.py:139` 기준). 추가 의존성 도입 없이 urllib 기반으로 plumbing.

**v3.1 변경 — `core/requirement_llm.py` (본 PR 후속 코드 PR 명세):**

```python
import urllib.request
import urllib.error
import json
import concurrent.futures as _cf  # google SDK timeout 래핑용

def _call_anthropic_api(
    model: str,
    prompt: str,
    *,
    return_usage: bool = False,
    timeout_sec: int = 120,
) -> str | tuple[str, dict]:
    api_key = get_engine_api_key("anthropic") or get_configured_engine_api_key("anthropic")
    if not api_key:
        raise RuntimeError("missing_anthropic_api_key")

    # baseline: urllib.request 사용 (v3.1 정정 — httpx 의존성 추가 없음)
    payload = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    # v3 plumbing: 하드코딩 60s → caller가 전달한 timeout_sec
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        data = json.loads(response.read().decode("utf-8"))
    parts: list[str] = []
    for item in data.get("content", []) or []:
        if str(item.get("type", "")).strip() == "text":
            value = str(item.get("text", "") or "").strip()
            if value:
                parts.append(value)
    text = "\n".join(parts).strip()
    if not return_usage:
        return text
    usage_raw = data.get("usage") or {}
    usage = _make_usage(
        int(usage_raw.get("input_tokens", 0) or 0),
        int(usage_raw.get("output_tokens", 0) or 0),
    )
    return text, usage


def _call_openai_api(
    model: str,
    prompt: str,
    *,
    return_usage: bool = False,
    timeout_sec: int = 120,
) -> str | tuple[str, dict]:
    api_key = get_engine_api_key("openai") or get_configured_engine_api_key("openai")
    if not api_key:
        raise RuntimeError("missing_openai_api_key")
    if OpenAI is None:
        raise RuntimeError("openai_package_unavailable")
    client = OpenAI(api_key=api_key)
    # OpenAI SDK는 with_options(timeout=)로 per-call timeout 인젝션 (v1.x SDK 표준 패턴)
    response = client.with_options(timeout=float(timeout_sec)).responses.create(
        model=model, input=prompt,
    )
    text = _extract_openai_text(response)
    if not return_usage:
        return text
    raw = getattr(response, "usage", None)
    usage: dict = {}
    if raw is not None:
        usage = _make_usage(
            getattr(raw, "input_tokens", 0) or 0,
            getattr(raw, "output_tokens", 0) or 0,
        )
    return text, usage


def _call_google_api(
    model: str,
    prompt: str,
    *,
    return_usage: bool = False,
    timeout_sec: int = 120,
) -> str | tuple[str, dict]:
    api_key = get_engine_api_key("google") or get_configured_engine_api_key("google")
    if not api_key:
        raise RuntimeError("missing_google_api_key")
    from google import genai

    client = genai.Client(api_key=api_key)
    # google genai SDK는 client-level timeout 미지원 → ThreadPoolExecutor + future.result(timeout=) 래핑
    with _cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix="genai-call") as ex:
        fut = ex.submit(
            generate_content_with_self_heal,
            client, normalize_model_name(model), prompt,
        )
        try:
            response = fut.result(timeout=float(timeout_sec))
        except _cf.TimeoutError:
            raise RuntimeError(f"google_api_timeout_{timeout_sec}s")
    text = str(getattr(response, "text", "") or "").strip()
    if not return_usage:
        return text
    meta = getattr(response, "usage_metadata", None)
    usage: dict = {}
    if meta:
        usage = _make_usage(
            getattr(meta, "prompt_token_count", 0) or 0,
            getattr(meta, "candidates_token_count", 0) or 0,
        )
    return text, usage
```

**`execute_document_prompt`에서 전달 (§10 v2 코드의 API 분기 line 728-735 패치):**

```python
if candidate.provider_id == "anthropic_api":
    text, usage = _call_anthropic_api(
        candidate.model, effective_prompt,
        return_usage=True, timeout_sec=timeout_sec,  # v3: 전달
    )
elif candidate.provider_id == "openai_api":
    text, usage = _call_openai_api(
        candidate.model, effective_prompt,
        return_usage=True, timeout_sec=timeout_sec,
    )
else:
    text, usage = _call_google_api(
        candidate.model, effective_prompt,
        return_usage=True, timeout_sec=timeout_sec,
    )
```

> **호환성**: 기존 호출자(`execute_requirement_prompt` 등)는 `timeout_sec` 파라미터 없이 호출 → default 120s 적용. 무영향.
> **transport timeout 의미** (v3.1 정정): anthropic의 `urllib.request.urlopen(request, timeout=...)`은 socket-level timeout (connect + read inactivity). 큰 응답 streaming 시 chunk 간 read 정체가 timeout 트리거. openai의 `with_options(timeout=)`는 read timeout 우선. google의 `future.result(timeout=)`은 wall-clock (request/response 전체).
> **단위 일관성**: `_call_*_api` 시그니처가 모두 `timeout_sec: int = 120` (정수 초). SDK 내부에서 float 변환은 각 함수가 처리. v3 §10 v2 코드의 `timeout_sec=timeout_sec` 직접 전달이 안전.

---

## 11. 변경 대상 파일/함수 (path 정정, finding #13)

| 파일 | 라인 (현재) | 변경 내용 |
|------|------------|----------|
| `core/work_item_generator.py:523-534` | `_generate_doc_with_llm` | 시그니처에 `doc_type, run_id, timeout_sec, workspace` 추가. `tuple[str, bool]` → `DocGenerationResult` 반환 |
| `core/work_item_generator.py:537-694` | 4개 generator | 시그니처를 keyword-only로: `*, prev_plan="", prev_spec="", prev_design="", run_id="", timeout_sec=120, workspace=""`. `str` → `DocGenerationResult` 반환 |
| `core/work_item_generator.py:614-651` | `_generate_implementation_design` | `prev_plan` 입력 시 "Feature Plan:" 블록 prompt 추가 (§8) |
| `core/work_item_generator.py:740-831` | `generate_work_items` 본문 | sequential → C-3stages 재구성. `cleanup_stale_sessions()` 1회 호출. budget 600s. 텔레메트리 dump |
| `core/work_item_generator.py:834-870` | `_generate_and_refine` | introspection 제거. `DocGenerationResult` 반환. `placeholder_refine_attempts` 갱신. explicit kwargs dispatch |
| `core/requirement_llm.py:173-230` | `execute_document_prompt` | `elapsed_sec`, `usage_tokens` 응답 키 추가 (§10) |
| `core/requirement_llm.py:_call_anthropic_api`, `_call_openai_api`, `_call_google_api` | API 호출자 | `return_usage=False` 옵션 추가. `True`일 때 `tuple[str, dict]` 반환 |
| `core/providers/session_adapter.py:281-304` | `_write_claude_settings` | 본문을 `with locked_file(str(settings_path), timeout=5):`로 wrap (§4) |
| `core/providers/session_adapter.py:474, 476` | `prepare_cli_session` (path 정정 from v1) | 별도 변경 없음. `not _is_frozen()` 가드는 frozen build 고려 |
| `core/cli_session_cleanup.py` | (신규) | `cleanup_stale_sessions(workspace, days=30)` (§9) |
| `core/file_lock.py` | (기존) | 변경 없음. 재사용만 |
| `core/project_pipeline.py:1003-1020` | T1 retry 블록 | T1 retry 발생 시 `runtime/work_item_telemetry/{slug}.json`의 doc 별 `t1_refine_attempts` 컬럼을 atomic locked update (§5) |
| `core/project_pipeline.py:948` | `generate_work_items` 호출 | 변경 없음 (반환은 `dict[str, str]` 그대로) |
| `af.spec` | hiddenimports | `core.cli_session_cleanup` 추가. `core.file_lock`은 이미 76라인 |
| `runtime/work_item_telemetry/{slug}.json` | (신규 dump 위치) | `generate_work_items` 종료 시 4개 `DocGenerationResult` json dump |

### v3.1 변경표 — baseline grep 결과 일괄 갱신 (Status 컬럼 추가)

> **Status 컬럼 의미**: (a) baseline에 이미 존재 — 변경 없음 / (b) 본 PR (설계 문서)에서 명세 정정 / (c) 본 PR 후속 코드 PR에서 plumbing 필요. v3.1이 1라운드 #3, #4 흡수하여 모든 라인 번호를 grep(2026-05-11) 결과로 일괄 갱신.

| 파일 | 실제 라인 (2026-05-11 grep) | v3.1 명세 | Status | Findings |
|------|----------------------------|----------|--------|----------|
| `core/requirement_llm.py:78` | `def _call_google_api(model, prompt, *, return_usage=False)` | 시그니처에 `timeout_sec: int = 120` 추가. google SDK는 client-level timeout 미지원 → `_cf.ThreadPoolExecutor(max_workers=1)` + `future.result(timeout=float(timeout_sec))` 래핑 | (c) | **F2** |
| `core/requirement_llm.py:98` | `def _call_openai_api(model, prompt, *, return_usage=False)` | `timeout_sec: int = 120` 추가. `client.with_options(timeout=float(timeout_sec)).responses.create(...)` 패턴 | (c) | **F2** |
| `core/requirement_llm.py:118` | `def _call_anthropic_api(model, prompt, *, return_usage=False)` — **`urllib.request.urlopen(request, timeout=60)` 하드코딩** (L139) | `timeout_sec: int = 120` 추가. `urllib.request.urlopen(request, timeout=timeout_sec)`로 변경 (httpx 의존성 도입 없음) | (c) | **F2** |
| `core/requirement_llm.py:203` | `execute_document_prompt` API 분기 3곳 | `timeout_sec=timeout_sec` 인자 전달 | (c) | **F2** |
| `core/work_item_generator.py:562` | `def _generate_doc_with_llm(...)` | 시그니처에 `doc_type, run_id, timeout_sec, workspace` 추가. `tuple[str, bool]` → `DocGenerationResult` 반환 | (c) | F3/F4 (boundary) |
| `core/work_item_generator.py:613` (plan), `:656` (spec), `:698` (design), `:755` (tasks) | 4개 generator 함수 시그니처 | keyword-only `*, prev_plan="", prev_spec="", prev_design="", run_id="", timeout_sec=120, workspace=""`. `str` → `DocGenerationResult` 반환 | (c) | (boundary) |
| `core/work_item_generator.py:909` | `def _build_episode_hints_section(project_brief, workspace) -> str` | 변경 없음 — `_exec_stage1` 반환 직전 호출 (§7a) | (a) | **F3** |
| `core/work_item_generator.py:1055` | `episode_hints_section = _build_episode_hints_section(project_brief, workspace)` | v2 Stage 재구성으로 `_exec_stage1` 내부로 이동. 호출 자체 보존 | (c) | **F3** |
| `core/work_item_generator.py:813` | `def _extract_section_outline(markdown, expected_count: int = 12) -> str` — **현 baseline은 mismatch 시 `_LOGGER.warning` + `"\n".join(lines)` 부분 outline 반환** (L831-832) | mismatch 시 **빈 문자열 반환**으로 변경 (`if section_idx != expected_count: return ""`). tasks prompt가 빈 outline 처리 | (c) | **F9** |
| `core/work_item_generator.py:1025` | `def generate_work_items(...)` | sequential → C-3stages 재구성. `cleanup_stale_sessions()` 1회 호출. budget 600s. 텔레메트리 dump | (c) | (전체) |
| `core/work_item_generator.py:1184` | `def _generate_and_refine(...)` (현재 deadline 인자 없음) | 시그니처에 `deadline: float` (절대 monotonic) 추가. 내부 refine loop에서 매 iteration `_compute_iter_timeout()` 사용 | (c) | **F1** |
| `core/work_item_generator.py:1263` | `def _refine_document(...)` (현재 timeout 인자 없음) | 시그니처에 `timeout_sec: int` 추가. caller(`_generate_and_refine`)가 잔여시간 전달 | (c) | **F1** |
| `core/work_item_generator.py:_exec_stage1`, `_exec_stage3` | **baseline에 부재** (`_exec_stage2`만 L860에 존재) | §7a/§7b 명세대로 신설. fallback 4개(L199/274/378/511) 호출 | (c) | **F4** |
| `core/work_item_generator.py:1003-1020` (T1 retry 블록) | `for _dname in ("plan", "spec", "design", "tasks"):` | `_dname` doc_type 문자열로 명세 — telemetry json `docs[_dname].t1_refine_attempts` 키와 정합 | (b) | **F10** |
| `core/work_item_telemetry.py:14` | `tele_dir = Path(workspace) / "runtime" / "work_item_telemetry"` | `from core.continuity.runtime_paths import workspace_runtime_dir`, `tele_dir = workspace_runtime_dir(workspace) / "work_item_telemetry"` | (c) | **F7** |
| `core/work_item_telemetry.py:45` | `tele_dir = Path(workspace) / "runtime" / "work_item_telemetry"` (write_initial_record 내) | 동일 변경 — **두 위치 동시 수정 필수** | (c) | **F7** |
| `core/providers/session_adapter.py:281-304` | `_write_claude_settings` | 본문을 `with locked_file(str(settings_path), timeout=5):` wrap (§4) | (c) | (lock) |
| `core/cli_session_cleanup.py` | **이미 존재** (5/10 02:01, 1613 bytes) | 변경 없음. `cleanup_stale_sessions(workspace, days=30)` 그대로 호출 | (a) | (§9) |
| `core/work_item_telemetry.py` | **이미 존재** (5/10 02:01, 2651 bytes) | F7 path 변경 (위 두 행) | (a) | (§5/§11) |
| `core/work_item_generator.py:199, 274, 378, 511` (fallback 4개) | `_fallback_feature_plan`, `_fallback_feature_spec`, `_fallback_impl_design`, `_fallback_impl_tasks` | 4개 모두 존재 (grep 검증). §12 cascade + §7a/§7b의 `*_factory` 호출 안전 | (a) | **F6 close** |
| `af.spec:82` | `'core.cli_session_cleanup',` | 이미 등록 — 변경 없음 | (a) | **F11 REJECT** |
| `af.spec:83` | `'core.work_item_telemetry',` | 이미 등록 — 변경 없음 (v3 초안 "76라인" 표기 정정 → 82, 83) | (a) | **F11 REJECT** |
| `core/project_pipeline.py:948` | `generate_work_items` 호출 | 변경 없음 (반환은 `dict[str, str]` 그대로) | (a) | (caller) |
| `runtime/work_item_telemetry/{slug}.json` | (dump 위치 — workspace_runtime_dir 적용 후 `<workspace>/.af_runtime/work_item_telemetry/{slug}.json`) | `generate_work_items` 종료 시 4개 `DocGenerationResult` json dump | (c) | (§5/§11) |

### T1 텔레메트리 atomic update (finding #8 해소)

```python
# core/work_item_telemetry.py (신규)
import json
from pathlib import Path
from core.file_lock import locked_file

def update_t1_refine_attempts(workspace: str, slug: str, doc_name: str, increment: int = 1) -> None:
    """T1 retry 발생 시 텔레메트리 파일의 해당 doc 컬럼을 atomic 증가."""
    tele_dir = Path(workspace) / "runtime" / "work_item_telemetry"
    tele_dir.mkdir(parents=True, exist_ok=True)
    tele_path = tele_dir / f"{slug}.json"

    with locked_file(str(tele_path), timeout=5):
        data = {}
        if tele_path.exists():
            try:
                data = json.loads(tele_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        docs = data.setdefault("docs", {})
        doc_entry = docs.setdefault(doc_name, {})
        doc_entry["t1_refine_attempts"] = int(doc_entry.get("t1_refine_attempts", 0)) + increment
        tele_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

`core/project_pipeline.py:1003-1020`의 T1 retry 루프에서 `_refine_document()` 성공 직후 `update_t1_refine_attempts(workspace, slug, _dname, 1)` 호출.

---

## 12. Stage 1 fallback cascade (M2 흡수)

### 정책

| Stage 1 결과 | Stage 2 동작 | Stage 3 동작 |
|--------------|--------------|--------------|
| `used_fallback=False` (정상) | spec/design `prev_plan = plan_result.content` | tasks `prev_design = design_result.content` |
| `used_fallback=True` (LLM 실패 → fallback plan) | **spec/design는 fallback plan 본문을 그대로 prev로 사용** (LLM 시도는 정상 진행) | 동일 — design 결과를 prev로 사용 |
| `timeout_fallback=True` (Stage 1 deadline 초과 → fallback) | 동일 — fallback plan 본문 사용 | 동일 |

### 이유
- fallback plan은 `_fallback_feature_plan()`이 §섹션 11개 + Rules 보장 → spec/design prompt가 깨지지 않음
- LLM 호출은 prev_plan이 fallback이어도 정상 진행 (단, consistency rubric은 낮아질 수 있음 — 측정 시 used_fallback 컬럼으로 분리)

### 코드

```python
# generate_work_items 본문
plan_result = _exec_stage1(deadline=deadline_1, ...)

# cascade 결정 (M2)
plan_for_prev = plan_result.content  # fallback이든 정상이든 본문 사용
if plan_result.used_fallback:
    _LOGGER.warning("Stage 1 fallback — Stage 2/3는 fallback plan을 prev로 사용")

spec_result, design_result = _exec_stage2(
    deadline=deadline_2, plan_content=plan_for_prev, ...
)
```

---

## 13. Approval-gate 동작 (M3 흡수)

**규칙**: Stage 1/2/3 어느 단계가 fallback이어도 `gate.initialize` 항상 실행.

```python
# generate_work_items 종료 직전 (현행 :827-829)
gate = ApprovalGate(doc_root, slug)
gate.initialize(work_item_id, run_id=run_id)
files["approval-gate.md"] = gate.gate_path
```

> approval-gate는 LLM 호출 없는 파일 생성이므로 Stage 결과 불문 항상 작성. 사용자가 수동으로 검토할 수 있도록 비워두는 게 fallback 시에도 안전.

---

## 14. 검증 절차

### Step 0 — 인프라 보강 검증 (finding #1, #2, #11)

1. **`run_id` 전파 grep** (§3 호출 체인): `_generate_and_refine`, `_generate_doc_with_llm`, `execute_document_prompt`에 `run_id` 인자 존재 확인.
2. **`.claude/settings.local.json` lock 동작** (M5):
   - 4-병렬 강제 호출 후 `json.loads(...)` 통과 확인.
   - **인위적 점유 테스트**: 별도 프로세스가 5초간 `<settings>.lock`을 점유한 상태에서 `_write_claude_settings` 호출 → `TimeoutError` raise 후 호출자가 경고 로그 + settings 미작성 동작.
3. **`<workspace>/.af_runtime/cli_sessions/` 분리 생성**: 4개 `.json` + 4개 `_events.jsonl` 분리. 각 `task_preview` 다름 assert.
4. `.claude/settings.local.json` hook entry 개수가 단일 호출 후와 동일 assert (`merge_named_hook_group`이 idempotent 보장).
5. **cleanup 동작**: 31일 전 mtime의 더미 파일 생성 후 `cleanup_stale_sessions(workspace, days=30)` → 삭제 카운트 ≥ 1.
6. **`project_pipeline.execute()` sync 컨텍스트 검증** (v3 신규, F5 close):
   ```bash
   grep -nE "^(async )?def execute\(" core/project_pipeline.py
   # 기대 출력: "1231:    def execute(" 1줄. "async def execute" 0줄.
   ```
   `async def`가 검출되면 본 설계 전체 호출을 `await asyncio.to_thread(_generate_work_items_sync, ...)` 로 감싸고, §3 asyncio 컨텍스트 불변식 가드를 활성화한다. 현재(2026-05-10) sync 확인됨 — 본 설계 그대로 진입 가능.
7. **telemetry 경로 컨벤션 검증** (v3 신규, F7):
   ```bash
   grep -n "tele_dir\|work_item_telemetry" core/work_item_telemetry.py
   # 기대: workspace_runtime_dir(workspace) / "work_item_telemetry" 사용.
   # 부정 기대: Path(workspace) / "runtime" / "work_item_telemetry" 잔재 없음.
   ```
8. **`_call_*_api` timeout_sec 시그니처 검증** (v3 신규, F2):
   ```bash
   grep -nE "def _call_(google|openai|anthropic)_api" core/requirement_llm.py
   # 기대: 3개 모두 시그니처에 "timeout_sec: int = 120" 포함.
   ```
   추가 동작 검증: anthropic의 `urllib.request.urlopen(timeout=...)` / openai SDK의 `with_options(timeout=...)` / google의 `_cf.ThreadPoolExecutor + future.result(timeout=...)` 호출이 단위 테스트로 timeout 강제 발동 확인 (mock으로 60s 슬립 후 timeout=2s 호출 → `socket.timeout` / `RuntimeError` / `TimeoutError` 전파).

### Step 1 — prev_doc 의존도 정량 측정 (sample N≥5, finding #5 영향)

- 동일 brief × **5쌍** (sequential vs C-3stages) 생성
- 메트릭: `phase_count_match` 분포 (rubric consistency 차원의 raw 측정), `placeholder_refine_attempts` 합계
- 합격: C-3stages 평균이 sequential 평균 ± 0.5 이내. **design ↔ plan baseline (Stage 2 병렬 시)** 도 별도 측정.

### Step 2 — 실 work-item smoke (N≥3, finding #14)

- minesweeper 같은 실제 brief로 **3회 실행** (median)
- assert (각 실행):
  - `ok=True ×4` (또는 fallback 사유 로그)
  - state 파일 4종 분리
  - hook 개수 보존
  - `runtime/work_item_telemetry/{slug}.json` 4개 doc 엔트리 존재 + `elapsed_sec > 0`
  - **`feature-plan.md`에 `## Episode Hints` 섹션 존재** (v3 신규 — F3 회귀 가드)
  - **Stage 2 wall-clock ≤ 405s** (v3 신규 — F1 budget guard 작동 확인. design 첫 호출 + refine 1회 + grace 5s 수렴)
- 가짜 짧은 프롬프트(`'1+1=?'`) 사용 금지

### Step 3 — source + frozen build 양쪽 (finding #9 영향)

- `python3 -m core.work_item_generator ...` (source)
- `dist/af/af.exe ...` (PyInstaller 빌드)
- `af.spec`에 `core.file_lock` (확인) + `core.cli_session_cleanup` (신규) 등록 검증
- 양쪽에서 Step 2 통과 확인

### Step 4 — 비교표 (N≥5, median)

| 메트릭 | Sequential | C-3stages | 측정 컬럼 |
|--------|------------|-----------|----------|
| Total elapsed (incl. retry) | ? | ? | `runtime/timing/*.jsonl` |
| Stage별 elapsed_sec median | n/a | ? | `DocGenerationResult.elapsed_sec` |
| Timeout-fallback 횟수 | ? | ? | `timeout_fallback` 컬럼 합 |
| Provider 분포 | ? | ? | `provider_id` 컬럼 |
| Raw rubric 점수 | ? | ? | review_session 출력 |
| T1-후 점수 | ? | ? | T1 retry 후 review_session |
| `placeholder_refine_attempts` 합계 | ? | ? | DocGenerationResult |
| `t1_refine_attempts` 합계 | ? | ? | telemetry json |
| Token usage (anthropic_api 한정) | ? | ? | `usage_tokens.total` |

### Step 4.1 — Stage 3 budget 재산정 트리거 (v3 신규, F12)

§14 Step 2의 N≥3 측정 결과에서 `tasks` 컬럼의 `timeout_fallback` 비율을 분석:

| 비율 | 처리 |
|------|------|
| ≤ 20% | `STAGE_BUDGET[3] = 110s` 유지 (provisional → confirmed) |
| > 20% | tasks elapsed_sec **P95** + 20% 마진 → 새 `STAGE_BUDGET[3]` 산정. §6 Stage budget 표 + TOTAL_BUDGET 갱신 |
| 측정 N < 3 | 재측정 (sample 부족) |

산정 결과를 §6 Stage budget 표와 §16 변경 이력에 기록.

### Step 5 — 의사결정 임계 (실측 반영)

C-3stages 채택 조건:
- **Total elapsed median 단축 ≥ 1.2배** (v1의 1.3배 → 1.2배로 하향. plan은 직렬, spec+design만 병렬화하므로 이론 최대 1.5×, refine 변동 흡수 후 현실은 1.2~1.4×)
- Raw rubric 점수 하락 ≤ 0.3 (5점 만점)
- Timeout-fallback 비율 ≤ 10%
- `t1_refine_attempts` 합계가 sequential 대비 ≤ 1.5배 (regression 방지)
- **F1 budget guard 작동 검증** (v3 신규): N≥3 중 어느 한 실행에서도 `cf.wait` 만료 시점에 `not_done` set 크기 = 0 (refine guard로 스스로 fallback 처리되어야 함). 하나라도 not_done > 0이면 §6 guard 로직 결함 — Step 2 재돌입.

---

## 15. 위험 / 미해결

### 위험
- **R1 (수정)**: `core/file_lock.py:64`은 `O_CREAT | O_EXCL` 사용 (NOT `fcntl.flock`). NFS에서도 `O_EXCL`은 POSIX-2008 이후 atomic 보장. Windows에서는 `os.open(O_CREAT | O_EXCL)`이 동작 — 단, 일부 SMB 마운트에서 race 가능성 있음. WSL+Windows 혼용 시 §11 Step 0.2의 인위적 점유 테스트로 검증.
- **R2**: refine loop이 Stage timeout을 초과할 경우 — `timeout_sec`을 stage 잔여시간에서 5초 뺀 값으로 전달하므로 단일 호출은 보호. 단, refine 2회 발생 시 합계 240s 가능. Stage 2 budget 400s는 spec(85s) + design(267s+α) + refine 마진 50s를 가정.
- **R3**: Stage 2의 spec/design이 같은 plan 본문을 동시 참조 → token usage ~2배 (CLI 미측정). claude_cli rate-limit 우려는 본 시점에서 finding 없음 (Sonnet 1회 측정에서 rate-limit 발생 없음).
- **R4 (신규)**: `_call_anthropic_api(return_usage=True)` 시그니처 변경 시 다른 호출자 (`execute_requirement_prompt` 등) 호환성 — `return_usage=False` default로 기존 호출 무영향.
- **R5 (신규)**: `runtime/work_item_telemetry/{slug}.json`이 `update_t1_refine_attempts` 동시 호출에 의해 corrupt — `locked_file()`로 atomic 보장.
- **R6 (신규)**: Stage 1 LLM 실패가 단순 일시 오류가 아닌 **provider-wide outage**일 경우 Stage 2/3도 cascade fallback으로 떨어져 모든 4개 문서가 fallback 본문으로 채워질 수 있음 — `used_fallback=True` 컬럼 합계가 4건이면 outage 의심. §11 Step 4 비교표에 "fallback 비율" 컬럼 추가, 모니터링 별도 필요. provider-wide outage 자체는 본 설계 범위 밖이며 `core/requirement_llm.py:list_requirement_candidates()`의 다중 provider 폴백이 1차 방어선.
- **R7 (v3.1 신규, 1라운드 #8 + #9 흡수)**: **Stage 2 abandoned future + Stage 3 hook race**. `cf.wait(timeout=remaining)` 만료 시 `not_done` future들의 LLM subprocess는 SIGTERM 수신 후 grace 5s 내 자체 종료가 일반적이지만, Stage 3가 같은 시점에 시작되면 `<workspace>/.af_runtime/cli_sessions/` + `_events.jsonl`을 동시 기록한다. §4 lock은 `_write_claude_settings` 본문만 보호하며 hook 호출 시점은 미보호. **방어선**: §6의 "Stage 3 진입 전 5s grace wait" (F1 guard)이 본 race에 대한 통합 방어. F1 미구현 시 R7도 active. 추가 방어로 Stage 3 진입 직전 `<workspace>/.af_runtime/cli_sessions/` 디렉토리 mtime이 (Stage 2 종료 + 5s) 이후이면 추가 1s wait 권고 — 실증 데이터로 P95 측정 후 결정 (§14 Step 2 신규 metric).
- **R8 (v3.1 신규, 1라운드 #10 흡수)**: **§9 cleanup 디렉토리 mtime 의미 불일치**. POSIX dir mtime은 자식의 add/remove에만 갱신되며 자식 modify와 무관. 즉 30일 동안 append만 일어나는 디렉토리는 dir mtime이 stale → `cleanup_stale_sessions(workspace, days=30)`이 active 세션을 파괴할 수 있음. 반대로 자식 자주 추가되면 dir mtime 갱신 → 영원히 정리 안 됨. **방어선** (§9 정책 변경 명시): 디렉토리 entry 판정 시 `entry.stat().st_mtime` 대신 `max(c.stat().st_mtime for c in entry.rglob("*") if c.is_file())` (자식 파일 max mtime)으로 대체. 또는 디렉토리 cleanup TTL을 60일+로 분리. 본 PR 후속 코드 PR이 `core/cli_session_cleanup.py`에 적용.

### 미해결 (Open Questions)
- **OQ1 (resolved)**: token usage는 §10에서 `usage_tokens` 컬럼으로 정식 추가. CLI provider는 빈 dict (CLI는 stdout만 노출).
- **OQ2 (resolved)**: design.metadata.source_spec 필드 — Stage 2 병렬일 때 `_generate_implementation_design` prompt가 "spec being generated in parallel" 명시 + Output Format의 source_spec 항목을 빈 값 허용 또는 "(parallel)" 표기로 후처리. `_fallback_impl_design`도 동일.
- **OQ3 (신규)**: `_generate_doc_with_llm`의 fallback 호출도 `DocGenerationResult` 반환 — `provider_id="fallback"`, `model="static"`, `elapsed_sec=0.0`로 채움.
- **OQ4 (신규)**: 4개 generator 시그니처를 keyword-only로 변경 시, 외부 호출자 (테스트 등) 영향 검토. grep 결과 production 호출자는 `_generate_and_refine` 단일 진입점뿐.

---

## 16. 변경 이력

- 2026-05-11 (v3.1): v3 1라운드 cross-review (`docs/reviews/2026-05-11-001451-...-v3-design-review.md`) 11건 흡수.
  - Cross provider error로 Critic 단독 평가였음 — evidence가 file:line 단위로 강력해서 모두 ACCEPT/HOLD.
  - **Critical 2건 처리**: F1 (refine guard) / F2 (timeout transport)를 "**설계 명세 흡수 / 코드 (c) 미구현 — 본 PR 후속**"으로 status 명시. v3 초안의 "흡수" 표기가 baseline 코드 변경 미포함이라는 사실을 §0a에 Implementation Status 컬럼으로 명시화.
  - **F2 baseline 정정**: anthropic은 `httpx.Client`가 아니라 `urllib.request.urlopen(timeout=60)` 하드코딩 (`core/requirement_llm.py:139`). v3.1 §10 코드블록을 urllib 기반으로 재작성 (의존성 추가 없음).
  - **High 4건**: §11 변경표 line 번호 일괄 갱신 (`_call_*_api:78/98/118`, `_generate_doc_with_llm:562`, `_generate_and_refine:1184`, `_refine_document:1263`, `generate_work_items:1025`, 4 generator `:613/656/698/755`, `_extract_section_outline:813`, `work_item_telemetry.py:14, 45`). af.spec line 76 → **82, 83** 정정. `cli_session_cleanup` / `work_item_telemetry`는 (a) 이미 구현. `expected_count` §0a/§8/실제 코드 모두 12로 통일. F9 결정 — 빈 문자열 반환으로 본 PR 후속 코드 변경 명시.
  - **Medium 3건**: §15 R7 신설 (Stage 2 abandoned future + Stage 3 race), R8 신설 (§9 cleanup 디렉토리 mtime 의미). §6 budget 산정의 F1 guard 의존성을 R7로 명시 — F1 미구현 시 worst-case 507s 위험.
  - **HOLD 1건**: Cross provider 인증 후 v3.1 commit + cross-review 2라운드 재실행.
  - 본 v3.1 commit 후 외부 CLI provider(codex/copilot/gemini-cli) 인증 상태 확인 후 cross-review 2라운드 트리거 — 단일 critic 의존 회피.
- 2026-05-10 (v3): v2 cross-review 2라운드 (`docs/reviews/2026-05-08-142400-...`) 13건 흡수.
  - **5 High** 모두 처리 — F1 (refine loop budget guard, §6 보강 + §7 호출 측 deadline 전달), F2 (`_call_*_api(timeout_sec=)` 시그니처 통일, §10 보강), F3 (Episode Hints 주입, §7a 신설), F4 (`_exec_stage1`/`_exec_stage3` 풀 구현, §7a/§7b 신설), F5 (asyncio NOT APPLICABLE — sync 컨텍스트 검증 후 §3 불변식 + §14 Step 0.6 가드).
  - **2 Medium 처리** — F7 (telemetry 경로 `workspace_runtime_dir(workspace) / "work_item_telemetry"`, §11), F12 (Stage 3 budget provisional → §14 Step 4.1 재산정 trigger).
  - **2 Medium close** — F6 (fallback 4개 grep 검증), F8 (`_PLACEHOLDER_REFINE_MAX = 2` grep 검증, budget 산정 그대로 유효).
  - **2 Low 처리** — F9 (outline mismatch 시 빈 문자열 반환, §7b/§8), F10 (`_dname` doc_type 문자열 명세, §11).
  - **1 REJECT 유지** — F11 (`af.spec:76` 이미 `core.work_item_telemetry` 등록, cross 라운드 검증).
  - 새로운 §0a (v3 변경 요약), §3 asyncio 불변식, §6 refine guard, §7a/§7b 풀 구현, §10 SDK timeout 인젝션, §11 v3 변경표, §14 Step 0.6/0.7/0.8 + Step 2 F3 가드 + Step 4.1 + Step 5 F1 가드 추가.
- 2026-05-08 (v2.1): cross-review WARN advisory 4건 수정 — §9 import 경로 (`core.workspace_paths` → `core.continuity.runtime_paths`, ImportError 즉발 방지), §6 마진 표현 (30% → 45%) 일관성, §5 `t1_refine_attempts` placeholder 주석, §15 R6 provider-wide outage cascade 위험 명시. cross-review BLOCK 0건 / WARN-only.
- 2026-05-08 (v2): v1 BLOCK 14건 + Critic Missing 5건 흡수.
  - Critical 2건 (Stage 2 await 패턴, cleanup path) 모두 코드 레벨 명시.
  - Stage budget을 실측 (415s) 기반 600s로 재산정. v1의 360s는 90s 부족.
  - explicit kwargs / DocGenerationResult / elapsed_sec 플러밍 / locked_file 재사용 등 boundary contract 모두 명시.
  - design `prev_plan` prompt 블록 신규 정의.
  - Step 2 sample N=1 → N≥3, Step 5 임계 1.3× → 1.2×.
- 2026-05-08 (v1): 초안. cross-review 14건+5건 ACCEPT BLOCK.
