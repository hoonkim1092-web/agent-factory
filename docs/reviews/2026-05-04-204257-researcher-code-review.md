# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-04 20:42
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: **BLOCK**

Cross Review는 프로바이더 오류로 결과를 반환하지 못했습니다. Critic의 발견 사항을 diff 코드 증거와 대조하여 독립 판정합니다.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] `_local_pipelines` dict — 락 없는 get-check-set 레이스

- **Critic**: "`_collect_local_references`(Thread 1)와 `_collect_llm_prior_knowledge`(Thread 2)가 동시에 `self._local_pipelines`에 접근. get→check→set이 원자적이지 않아 이중 생성 + I/O 중복 실행 가능."
- **Cross**: 프로바이더 오류로 미수행
- **Judgment**: diff에서 `ThreadPoolExecutor(max_workers=2)`로 두 작업을 병렬 실행함이 명확하다. `_collect_secondary`가 `_collect_llm_prior_knowledge`를 호출하면 두 스레드 모두 `self._local_pipelines`에 접근한다. CPython GIL은 개별 바이트코드만 보호하며, `LOAD_ATTR` → `IS`→`STORE_ATTR` 시퀀스는 원자적이지 않다. `force=True` I/O 중복은 파일 손상 가능성도 포함.
- **Action Required**: `_local_pipelines` 접근을 `threading.Lock`으로 보호하거나, Critic 제안대로 local 수집을 먼저 순차 완료 후 secondary만 병렬화.

#### 2. [ACCEPT] [Medium] `_tavily_skip_logged` 플래그 — 락 없는 멀티스레드 read-write

- **Critic**: "if-check → print → set 시퀀스를 두 스레드가 동시에 실행 가능. 실제 피해는 중복 print이나, #1과 동형 결함."
- **Cross**: 미수행
- **Judgment**: diff에서 두 thread가 동시에 실행되므로 플래그 경쟁이 발생 가능하다. 피해는 중복 로그 출력에 한정되어 Critical은 아니나, 같은 코드베이스에서 락 부재 패턴이 반복됨을 보여준다. #1 수정 시 같은 `threading.Lock`으로 함께 처리 가능.
- **Action Required**: `_tavily_skip_logged` 읽기/쓰기를 동일 인스턴스 락으로 보호.

#### 3. [ACCEPT] [Medium] `local_refs` 미초기화 — `requires_web` 경로 예외 시 NameError

- **Critic**: "`_fut_local.result()`가 예외를 던지면 `local_refs`가 미할당 상태로 이후 호출에 도달."
- **Cross**: 미수행
- **Judgment**: diff의 `requires_web` 분기에서 `local_refs = _fut_local.result()` 한 줄만 할당한다. `_fut_local`이 예외를 전파하면 `local_refs`는 NameError 상태가 된다. `fast_synthesis`와 `else` 분기는 정상 순차 할당이므로 `requires_web` 분기만 해당.
- **Action Required**: `requires_web` 분기 진입 전 `local_refs: list[dict] = []` 초기화 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_local_pipelines` 락 없는 get-check-set | High | ACCEPT | Critic + Diff 확인 |
| 2 | `_tavily_skip_logged` 락 없는 read-write | Medium | ACCEPT | Critic + Diff 확인 |
| 3 | `local_refs` 미초기화 (requires_web 예외 경로) | Medium | ACCEPT | Critic + Diff 확인 |

---

### Recommendations

- **#1 우선 수정**: 가장 단순한 픽스는 `local_refs = self._collect_local_references(...)` 순차 선행 후 `_collect_secondary`만 ThreadPoolExecutor에 넣는 것. `_local_pipelines` 레이스가 완전히 사라지고 secondary I/O(HTTP/LLM)에서 parallelism 이득 유지.
- **#2 함께 처리**: `threading.Lock` 인스턴스 1개를 `__init__`에 추가하고 `_tavily_skip_logged` 접근을 감싸면 됨.
- **#3 방어 초기화**: `requires_web` 분기 상단에 `local_refs: list[dict] = []` 1줄 추가.
- **Cross Review 재수행 필요**: 이번 교차검증은 프로바이더 오류로 단일 리뷰만 반영됨. 수정 후 af-test-runner → af-critic → af-cross-review Tier 2 재발화 권장.