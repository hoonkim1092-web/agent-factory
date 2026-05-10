# Work-Item 병렬 생성 — Option C-3stages 설계

> **상태**: draft (cross-review 대기)
> **선행 문서**: `docs/2026-05-08-work-item-parallel-generation-investigation.md` (조사 핸드오프)
> **선행 리뷰**: 직전 세션 BLOCK 리포트 14건 ACCEPT — 본 설계가 모두 흡수
> **목적**: feature-plan / feature-spec / implementation-design / implementation-tasks 4종 LLM 호출의 부분 병렬화. 시간 1.7~2배 단축, rubric 점수 보존.
> **비고**: approval-gate는 LLM 호출 없는 파일 생성이라 본 설계 범위 밖 (현행 유지).

---

## 1. 채택 결정 요약

| 항목 | 결정 | 비고 |
|------|------|------|
| **Stage 구조** | C-3stages: `plan → [spec, design] 병렬 → tasks` | finding #4 흡수 (tasks가 spec §N 인용 가능) |
| **run_id 격리** | (D) `{base}_{doc_type}_{pid}_{ts}` | finding #1 해소 |
| **Stage 1 실패 정책** | A2: 폴백으로 채우고 진행 | 기존 sequential 흐름과 일관 |
| **prev_doc 합성** | B3: design 전문 + spec 섹션 목차만 (tasks용) | finding #4 + 토큰 한도 |
| **deadline 처리** | C3: Stage별 + carry-over | finding #6 해소 |
| **executor 패턴** | D3: per-future timeout + 폴백 | finding #6 + A2와 정합 |
| **state 파일 정리** | 30일 TTL cleanup hook | (D) 누적 위험 대비 |
| **관측성** | `DocGenerationResult` dataclass 도입 | finding #8 |

---

## 2. Stage 구조 (C-3stages)

```
Stage 1 (단독):  plan
                  ↓ plan 완료 후
Stage 2 (병렬 2): spec ← plan 참고
                  design ← plan 참고
                  ↓ 둘 다 완료 후
Stage 3 (단독):  tasks ← design 전문 + spec 섹션목차
```

### 시간 추정 (sequential 대비)
- Sequential: `plan + spec + design + tasks` = 4 단위
- C-3stages: `plan + max(spec, design) + tasks` ≈ 3 단위
- **단축률**: 약 25% (1.33배). refine loop 가산 시 더 큼.

> 핸드오프 §3에서 추정한 "2배"는 Option C-2stages 기준이었음. 3-stages는 1.33~1.7배가 정확.

### 정합성 보존
- **consistency** (plan ↔ spec, weight 0.15): Stage 2가 plan을 prev_doc으로 받음 → 보존
- **traceability** (spec ↔ tasks, weight 0.10): Stage 3가 spec 목차를 받음 → 보존

---

## 3. run_id 격리 정책 (D방식)

### 형식
```
{base_run_id}_{doc_type}_{pid}_{epoch_ts}
예: claude_cli_run_plan_12345_1715077200
    claude_cli_run_spec_12345_1715077201
```

- `base_run_id`: 호출자가 제공 (없으면 `claude_cli_run` 폴백)
- `doc_type`: `plan` / `spec` / `design` / `tasks`
- `pid`: `os.getpid()` — 디버깅 용이
- `epoch_ts`: `int(time.time())` — 재실행 격리

### 전파 경로 (필수 시그니처 변경)

```
generate_work_items(run_id=...)                        # 기존, 변경 없음
  └─ _generate_and_refine(run_id=..., doc_type=...)    # 신규 인자 추가
      └─ generator_fn(..., run_id=...)                 # 4개 함수 시그니처에 추가
          └─ _generate_doc_with_llm(prompt, fb, run_id=...)  # 신규 인자
              └─ execute_document_prompt(prompt, run_id=full_run_id)
```

`full_run_id` 생성은 `_generate_and_refine` 내부에서:
```python
full_run_id = f"{run_id or 'claude_cli_run'}_{doc_type}_{os.getpid()}_{int(time.time())}"
```

### 부작용
- `runtime/cli_sessions/claude_cli_*.json` 파일이 호출당 1개씩 생성 (병렬 4개 다 분리)
- frozen build 환경(`af.exe`)에선 `_write_claude_settings`가 우회되므로 별도 검증 (finding #9)

---

## 4. file lock 정책

`.claude/settings.local.json`은 4개 호출이 **읽기**만 하면 안전. **쓰기**는 첫 호출 시에만.

### 구현
- `prepare_cli_session()` 진입 시 `core/file_lock.py` (신규 또는 기존)로 cross-process advisory lock
- 락 파일: `.claude/settings.local.json.lock`
- lock 획득 후 settings 존재/유효성 체크 → 없으면 작성, 있으면 skip
- timeout: 5초 (실패 시 경고만, hook 동작 보장 못함을 표기)

> 기존 코드에 `core/file_lock.py`가 있으면 재사용. 없으면 `fcntl.flock` (Unix) / `msvcrt.locking` (Windows) 분기 1회.

---

## 5. `DocGenerationResult` 구조체

기존 `_generate_doc_with_llm`은 `(content, used_fallback)` tuple 반환. 정보 손실 큼.

### 신규 dataclass

```python
@dataclass
class DocGenerationResult:
    doc_type: str            # plan / spec / design / tasks
    content: str             # 생성된 markdown 본문
    provider_id: str         # claude_cli / codex_cli / openai_api ...
    model: str               # 실제 사용된 모델명
    elapsed_sec: float       # LLM 호출~응답 시간
    used_fallback: bool      # _fallback_*() 사용 여부
    refine_attempts: int     # placeholder refine 루프 횟수 (0~2)
    timeout_fallback: bool   # CLI timeout으로 폴백된 경우 True
    errors: list[str]        # provider 실패 누적 로그
    run_id: str              # 격리된 full_run_id
```

### 활용
- pipeline 종료 시 `runtime/work_item_telemetry/{slug}.json`에 4건 dump
- §11 검증 비교표가 이 dump를 직접 파싱
- finding #7 (T1 retry 부작용)은 `refine_attempts` 컬럼으로 측정

---

## 6. Stage별 deadline + carry-over (C3)

### 기존 (sequential)
```python
doc_gen_deadline = time.time() + 300   # 5b~5d 합산
if time.time() < doc_gen_deadline: ...
```

### 신규 (C-3stages)
```python
TOTAL_BUDGET = 360.0   # 기존 300s + 병렬 오버헤드 60s 마진
stage_budget = {1: 90.0, 2: 180.0, 3: 90.0}   # 합 = 360s

t_start = time.time()
# Stage 1
plan_result = _exec_stage1(timeout=stage_budget[1])
elapsed_1 = time.time() - t_start
carry_over_1 = stage_budget[1] - elapsed_1   # 음수면 0으로 clamp

# Stage 2 — 잔여 + carry
stage2_timeout = stage_budget[2] + max(0, carry_over_1)
spec_result, design_result = _exec_stage2(timeout=stage2_timeout)

# Stage 3 — 동일
stage3_timeout = stage_budget[3] + leftover_2
tasks_result = _exec_stage3(timeout=stage3_timeout)
```

### timeout 의미 정정 (finding #5)
- `execute_document_prompt(timeout_sec=...)` — **단일 LLM 호출** 한도 (기존 default 120s)
- `stage_budget[N]` — Stage 단위 wall-clock 한도
- CLI provider의 `_default_cli_timeout_sec()=900` 폴백은 별도 — 본 설계는 명시적으로 `timeout_sec`을 전달해 폴백 회피

---

## 7. ThreadPoolExecutor + 폴백 (D3 + A2)

### Stage 2 패턴

```python
with ThreadPoolExecutor(max_workers=2, thread_name_prefix="wi-stage2") as ex:
    fut_spec = ex.submit(
        _generate_and_refine, "spec", _generate_feature_spec,
        work_item_id, project_brief, role_plan, task_board,
        _prev_doc=plan_content, run_id=base_run_id,
    )
    fut_design = ex.submit(
        _generate_and_refine, "design", _generate_implementation_design,
        work_item_id, project_brief, role_plan,
        _prev_doc=plan_content, run_id=base_run_id,
    )

    per_future_timeout = stage2_timeout
    spec_result = _await_or_fallback(fut_spec, per_future_timeout, _fallback_feature_spec, ...)
    design_result = _await_or_fallback(fut_design, per_future_timeout, _fallback_impl_design, ...)
```

### `_await_or_fallback` 헬퍼

```python
def _await_or_fallback(future, timeout_sec, fallback_fn, *args) -> DocGenerationResult:
    try:
        result = future.result(timeout=timeout_sec)
        return result
    except FuturesTimeoutError:
        # future cancel 시도. 백그라운드는 끝날 때까지 돔 (CLI subprocess는 별도 timeout)
        future.cancel()
        return DocGenerationResult(
            content=fallback_fn(*args),
            used_fallback=True,
            timeout_fallback=True,
            ...
        )
    except Exception as exc:
        return DocGenerationResult(
            content=fallback_fn(*args),
            used_fallback=True,
            errors=[str(exc)],
            ...
        )
```

### 워커 수
- `max_workers=2` (Stage 2만 병렬)
- refine loop 포함 worst-case: 2 (Stage 2) × 3 (refine) = **동시 6 호출**
- finding #3 흡수: `Option B의 12-병렬`보다 절반

---

## 8. prev_doc 합성 정책 (B3)

### Stage 2 입력
- `spec` ← `prev_plan = plan_content` (전문)
- `design` ← `prev_spec = ""` (Stage 2이라 spec 아직 없음). `prev_plan = plan_content`을 prompt에 추가 주입 (시그니처 확장 또는 design용 새 prev 인자)

### Stage 3 입력 (tasks)
- `prev_design = design_content` (전문)
- **추가**: `spec_outline = _extract_section_outline(spec_content)` — §1 §2 §3 등 섹션 헤더만 추출

### `_extract_section_outline` 정의
```python
def _extract_section_outline(markdown: str) -> str:
    """## 섹션 헤더만 뽑아 §N 형식으로 정렬한 목차 텍스트 반환."""
    lines = []
    section_idx = 0
    for line in markdown.splitlines():
        m = re.match(r"^##\s+(.+)$", line.strip())
        if m:
            section_idx += 1
            lines.append(f"§{section_idx} {m.group(1)}")
    return "\n".join(lines)
```

### tasks prompt 확장
`_generate_implementation_tasks` 프롬프트에 다음 블록 추가:
```
- Feature Spec Outline (refer with §N):
{spec_outline}
```
+ Rules에 `"acceptance에 spec §N 참조 권장"` 명시 → traceability rubric 충족.

### 토큰 절감 효과
- spec 본문 평균 3000~5000 tokens → outline은 200~400 tokens
- tasks prompt 50~70% 절감

---

## 9. State 파일 cleanup TTL (30일)

### 위치
- `runtime/cli_sessions/claude_cli_*.json`
- `runtime/cli_sessions/claude_cli_*.events`

### 정책
- 매 `generate_work_items()` 진입 시 1회 호출 (idempotent)
- 30일 이상 된 파일 삭제
- 함수: `core/cli_session_cleanup.py:cleanup_stale_sessions(days=30)`
- 실패해도 main flow에 영향 없음 (try/except)

```python
def cleanup_stale_sessions(days: int = 30) -> int:
    cutoff = time.time() - days * 86400
    root = Path("runtime/cli_sessions")
    if not root.exists():
        return 0
    deleted = 0
    for p in root.glob("claude_cli_*.*"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted
```

---

## 10. 변경 대상 파일/함수

| 파일 | 변경 내용 |
|------|----------|
| `core/work_item_generator.py:523-534` | `_generate_doc_with_llm` 시그니처에 `run_id`, `doc_type` 추가. `DocGenerationResult` 반환 |
| `core/work_item_generator.py:537-694` | 4개 generator 시그니처에 `run_id` 추가 + design에 `prev_plan` 추가 |
| `core/work_item_generator.py:740-831` | `generate_work_items` 본문을 sequential → C-3stages로 재구성 |
| `core/work_item_generator.py:834-870` | `_generate_and_refine`이 `run_id`/`doc_type` 받아 `full_run_id` 생성, `DocGenerationResult` 반환 |
| `core/requirement_llm.py:173-230` | `execute_document_prompt`에 `provider_id`/`model`/`elapsed_sec` 응답 키 추가 (이미 있음 — 확인) |
| `core/file_lock.py` | (신규 또는 기존 재활용) cross-process advisory lock |
| `core/cli_session_cleanup.py` | (신규) 30일 TTL cleanup |
| `core/session_adapter.py:474, 476` | frozen build 분기 검토 (finding #9 — 필요 시 별도 fix) |
| `core/project_pipeline.py:999` | T1 refine 결과를 `DocGenerationResult.refine_attempts`에 반영 (finding #7) |

---

## 11. 검증 절차 (재구성된 §4)

### Step 0 — 인프라 보강 검증 (finding #1, #2)
1. `run_id` 전파 경로 grep으로 확인 (위 §3 호출 체인)
2. `.claude/settings.local.json` lock 동작: 4-병렬 강제 호출 후 파일 무결성 (`json.loads(...)` 통과) 확인
3. `runtime/cli_sessions/claude_cli_*.json` 4개 분리 생성 + 각 `task_preview` 다름 assert
4. `.claude/settings.local.json` hook entry 개수가 단일 호출 후와 동일 assert

### Step 1 — prev_doc 의존도 정량 측정 (finding #10)
- 동일 brief × 5쌍 생성 (sequential vs C-3stages)
- 메트릭: `phase_count_match` 분포 (rubric consistency 차원의 raw 측정)
- 합격: C-3stages 평균이 sequential 평균 ± 0.5 이내

### Step 2 — 실 work-item 길이 4-병렬 smoke (finding #2)
- minesweeper 같은 실제 brief로 1회 실행
- assert: `ok=True ×4`, state 파일 4종 분리, hook 개수 보존
- 가짜 짧은 프롬프트(`'1+1=?'`) 사용 금지

### Step 3 — source + frozen build 양쪽 (finding #9)
- `python3 -m core.work_item_generator ...` (source)
- `dist/af/af.exe ...` (PyInstaller 빌드, `.spec`에 `core.file_lock` `core.cli_session_cleanup` 추가)
- 양쪽에서 Step 2 통과 확인

### Step 4 — 비교표 (finding #5, #7)

| 메트릭 | Sequential | C-3stages |
|--------|------------|-----------|
| Total time (incl. retry) | ? | ? |
| Timeout-fallback 횟수 | ? | ? |
| Provider 분포 (claude/codex/api) | ? | ? |
| Raw 점수 (rubric weighted_avg) | ? | ? |
| T1-후 점수 (project_pipeline 정제 후) | ? | ? |
| `refine_attempts` 합계 | ? | ? |
| Token 사용량 | ? (finding #11에 의존) | ? |

### Step 5 — 의사결정 임계 (finding #4 반영, §3 §5 재교정)
- C-3stages 채택 조건:
  - Total time 단축 ≥ 1.3배
  - Raw 점수 하락 ≤ 0.3 (5점 만점)
  - Timeout-fallback 비율 ≤ 10%

---

## 12. 위험 / 미해결

### 위험
- **R1**: file lock 미지원 환경(NFS 등) — Windows + WSL 혼용 시 `fcntl.flock` 동작 검증 필요
- **R2**: refine loop이 Stage timeout을 초과할 경우 — Stage timeout이 LLM 호출 timeout × 3 이상이어야. 현재 `stage_budget[2]=180`은 `120 + 2*30`로 가정 (refine 1~2회). 부족 시 carry-over로 흡수
- **R3**: Stage 2의 spec/design이 같은 plan 본문을 동시 참조 → token usage 2배. claude_cli rate-limit 우려 (finding #3)

### 미해결 (Open Questions)
- **OQ1 (finding #11)**: `execute_document_prompt` 응답에 token usage 필드가 들어오는가? 없으면 `len(prompt) + len(text)` 문자수로 대체 측정
- **OQ2**: Stage 2 design이 spec 결과 없이 작성되면 design.metadata.source_spec 필드를 어떻게 채울지 — 후처리로 채울지, 빈 값 허용할지

---

## 13. 변경 이력

- 2026-05-08: 초안 작성. BLOCK 리포트 14건 ACCEPT 흡수, C-2stages → C-3stages로 변경 (finding #4)
