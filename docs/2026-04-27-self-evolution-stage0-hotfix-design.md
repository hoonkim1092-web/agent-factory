# 자가진화 Stage 0 — Hotfix 설계메모 (v7)

> **목적**: 자가진화 시스템의 silent failure를 봉쇄한다. 구조 변경 최소(공용 모듈 1개 신규). 라인 단위 픽스.
> **범위**: Stage 1+ (candidate staging, EvolutionLedger, Controller)는 별도 설계문서. 본 메모는 Stage 0 한정.
> **출처**: 사용자(Codex 5.5) 비평 7건 + Claude 코드 검증 + Codex 5 양방향 응답 + af-critic + af-cross-review 통합 (v1→v6 6회 반복 검증, 결함 14건 봉쇄).
> **이력**:
> - v1~v4 (2026-04-27): 결함 12건 봉쇄
> - v5 (2026-04-27): H5 PASS 분기 try 범위 확장
> - v6 (2026-04-27): H5 try 평탄화 (3개 독립 try + Step 4 cleanup)
> - **v7 (2026-04-27)**: af-critic v6 + af-cross-review v6 합의 반영. H5 PASS 분기 **외부 try/finally 래핑** (Step 4 cleanup이 BaseException + except 내부 예외 모두에서 도달 보장). `old_version` 스코프 명시 주석, T4-meta ⑩ 문구 정정.

---

## 1. 배경

| 결함 | 위치 | 현재 동작 | 문제 |
|------|------|----------|------|
| F1 | `agent_runner.py:976-980` | `SkillSelfEvolutionHook(check_interval=10)`을 `run()` 메서드 내부에서 매번 신규 생성 | 카운터 누적 0회 → 메타 보강 트리거 사실상 영구 비활성 |
| F2 | `trace_log.py:45-47` + `facade.py:130-145` | `TraceLogAdapter.write()` 항상 `return False` → facade write 결과 None | 진화 이벤트 영속성 0, RunEventStore에도 ledger에도 안 남음 |
| F3 | `skill_evolution_bus.py:115-131` | `on_bulk_enriched()`가 `_step7_broadcast()` 미호출 | 메타 보강 이벤트가 후속 hook에 전달 안 됨, 진화 이력 누적 불가 |
| F4 | `fsa_loop.py:615-620` | 품질 게이트 실패 시 print + return만 (rollback 없음) | live skill이 진화된 채 방치 |
| F6 | `dynamic_orchestrator.py:594` | `bus = SkillEvolutionBus()` 새 인스턴스 (싱글톤 X 사용) | runner/loader 미바인딩 → step5/6 무효 |
| F6' | `dynamic_orchestrator.py:596-601` | `bus.on_skill_evolved(skill_name=...)` (시그니처는 `skill_id`) | TypeError + 외부 try/except가 silent fail |
| F8 | `cross_verification.py:653-668` | `evolve_skill()` 직후 gate/rollback 없이 `bus.on_skill_evolved()` 호출 (Codex 5 발견) | live skill 변경 후 검증 없이 broadcast |

> 결함 #5(`_detect_failed_skill_dir` 문자열 매칭)와 #7(feedback → trigger 정책 부재)은 **Stage 1+에서 처리**. Stage 0 범위 외.

---

## 2. 7개 Hotfix 변경 명세 (H1~H7)

### H1. DynamicOrchestrator의 SkillEvolutionBus 싱글톤 사용

**파일**: `core/dynamic_orchestrator.py`
**라인**: 594

**Before:**
```python
bus = SkillEvolutionBus()
```

**After:**
```python
bus = SkillEvolutionBus.get_instance()
```

**이유**: 새 인스턴스는 runner/loader 바인딩이 없어 step5(module_cache evict), step6(loader_cache evict) 효과 없음. 싱글톤이 표준 진입점.

**영향 범위**: dynamic_orchestrator만. SkillEvolutionBus.get_instance()는 이미 존재 (skill_evolution_bus.py 클래스 메서드).

---

### H2. DynamicOrchestrator의 잘못된 kwarg 수정

**파일**: `core/dynamic_orchestrator.py`
**라인**: 596-601

**Before:**
```python
bus.on_skill_evolved(
    skill_name=name,
    trigger="cross_verification_orchestrator",
    old_version="",
    new_version="",
)
```

**After:**
```python
bus.on_skill_evolved(
    skill_id=name,
    trigger="cross_verification_orchestrator",
    old_version="",
    new_version="",
)
```

**이유**: `on_skill_evolved` 시그니처(`skill_evolution_bus.py:69`)는 `skill_id: str`. `skill_name=`은 unexpected kwarg → TypeError. 외부 try/except가 삼킴.

**영향 범위**: 호출 사이트 1곳.

---

### H2'. DynamicOrchestrator의 silent except 제거 (v2 추가, v3 logger 임포트 명시)

**파일**: `core/dynamic_orchestrator.py`
**라인**: 602-603, 604-605 영역 + 모듈 상단

**v3 사전 조건 (af-critic v2 High 발견 — NameError 방지)**:

`grep -n "^import logging\|^logger" core/dynamic_orchestrator.py` 결과 0건 확인. **logger를 그대로 사용하면 NameError 즉시 발생**. 따라서 모듈 상단에 다음 추가가 **필수**:

```python
# 모듈 상단 (다른 import 직후)
import logging
logger = logging.getLogger(__name__)
```

**Before (호출 사이트):**
```python
            except Exception:
                pass
    except Exception as exc:
        print_agent_msg("Evolve", f"자가진화 시도 실패 (무시): {exc}", "")
```

**After:**
```python
            except Exception as bus_exc:
                logger.error(
                    "[Evolve] SkillEvolutionBus.on_skill_evolved 실패 (skill=%s): %s",
                    name, bus_exc,
                )
    except Exception as exc:
        logger.error("[Evolve] _try_evolve_from_patterns 예외: %s", exc)
        print_agent_msg("Evolve", f"자가진화 시도 실패 (로그 기록): {exc}", "")
```

**이유**: `except: pass` 자체가 silent failure 구조의 본질. H1+H2가 TypeError를 제거해도, 다음 결함이 추가되면 또 silent fail. 로그 기록 명시화로 향후 결함 가시성 확보.

**영향 범위**: dynamic_orchestrator만. logger 임포트 + getLogger 1줄 추가가 **본 H2' 구현 필수 단계**.

---

### H3. on_bulk_enriched broadcast 추가

**파일**: `core/skill_evolution_bus.py`
**라인**: 115-131 (`on_bulk_enriched()` 메서드)

**Before:**
```python
def on_bulk_enriched(self, skill_ids: list[str]) -> None:
    if not skill_ids:
        return
    logger.info("[EvolutionBus] bulk enrich: %d개 스킬", len(skill_ids))
    self._step1_reload_registry()
    self._step2_invalidate_dep_graph()
    self._step3_recompute_embeddings()
    self._step4_clear_relevance_caches()
    for skill_id in skill_ids:
        self._step5_evict_module_cache(skill_id)
    self._step6_evict_loader_cache()
    logger.info("[EvolutionBus] bulk 캐시 체인 무효화 완료")
```

**After (추가만):**
```python
def on_bulk_enriched(self, skill_ids: list[str]) -> None:
    if not skill_ids:
        return
    logger.info("[EvolutionBus] bulk enrich: %d개 스킬", len(skill_ids))
    self._step1_reload_registry()
    self._step2_invalidate_dep_graph()
    self._step3_recompute_embeddings()
    self._step4_clear_relevance_caches()
    for skill_id in skill_ids:
        self._step5_evict_module_cache(skill_id)
    self._step6_evict_loader_cache()
    # H3: 메타 보강 이벤트도 broadcast (후속 hook 관찰성 확보)
    for skill_id in skill_ids:
        self._step7_broadcast(
            skill_id=skill_id,
            old_version="",
            new_version="",
            trigger="metadata_enriched",
        )
    logger.info("[EvolutionBus] bulk 캐시 체인 무효화 완료 (broadcast 포함)")
```

**이유**: 단일 진화는 step1~7, bulk는 step1~6만 → 후속 hook이 metadata enrichment 이벤트를 관찰 못함.

**영향 범위**: `_step7_broadcast`는 이미 존재. 호출만 추가. 후속 hook(`SkillSelfEvolutionHook.on_skill_evolved`)은 **trigger 분기 없이 단순 기록**한다 (`skill_self_evolution.py:63-75` 확인). 즉 H3은 "관찰성 확보" 목적만 달성하며, "trigger='metadata_enriched'로 분기"는 발생하지 않는다. **Stage 1에서 trigger별 분기 추가 예정** (af-cross-review REJECT 반영).

---

### H4. SkillSelfEvolutionHook 인스턴스 생애주기 수정

**파일**: `core/agent_runner.py`
**라인**: 976-985 영역

**Before:**
```python
try:
    from core.hooks.skill_self_evolution import SkillSelfEvolutionHook
    from core.skill_evolution_bus import SkillEvolutionBus
    _sse_hook = SkillSelfEvolutionHook(check_interval=10)
    bus.register(_sse_hook)
    _evo_bus = SkillEvolutionBus.get_instance()
    _evo_bus.bind_runner(self)
    _evo_bus.bind_event_bus(bus)
except Exception as _sse_err:
    _safe_print(f"[Runner] SkillSelfEvolutionHook registration failed: {_sse_err}")
```

**After (lazy 인스턴스 속성으로 끌어올림):**
```python
try:
    from core.hooks.skill_self_evolution import SkillSelfEvolutionHook
    from core.skill_evolution_bus import SkillEvolutionBus
    if not hasattr(self, "_sse_hook") or self._sse_hook is None:
        self._sse_hook = SkillSelfEvolutionHook(check_interval=10)
    bus.register(self._sse_hook)
    _evo_bus = SkillEvolutionBus.get_instance()
    _evo_bus.bind_runner(self)
    _evo_bus.bind_event_bus(bus)
except Exception as _sse_err:
    _safe_print(f"[Runner] SkillSelfEvolutionHook registration failed: {_sse_err}")
```

**이유**: 매 `run()`마다 신규 인스턴스 → 카운터 0 리셋 → check_interval=10 영구 미달.
`AgentRunner` 인스턴스 1개가 여러 `run()`을 받는 표준 사용 패턴에서 hook 인스턴스를 재사용하면 카운터 누적.

**영향 범위**: `AgentRunner.__init__`은 변경 없음(`hasattr` 체크로 lazy 생성). 매 run에서 같은 hook 인스턴스를 다시 register하면 EventBus가 중복 처리할 가능성 있으니 EventBus 동작도 확인 필요(아래 검증 항목 V4 참조).

**대안 고려**: `__init__`에 직접 추가도 가능하나, import 시점 문제(circular)가 발생할 수 있어 lazy 패턴 채택.

---

### H5. fsa_loop 품질 게이트 실패 시 명시 rollback

**파일**: `core/fsa_loop.py`
**라인**: 615-620

**Before:**
```python
gate_result = self._run_quality_gate(skill_dir, skill_name)
if gate_result is not None and not gate_result.passed:
    for reason in gate_result.failure_reasons:
        print_agent_msg("SkillEvolve", reason, "⚠️")
    print_agent_msg("SkillEvolve", f"품질 게이트 실패 — hot_reload 스킵: {skill_name}", "🚫")
    return gate_result
```

**After v4 (3분기 모두 cleanup/rollback 명시 + try/finally 보장):**

```python
# core/fsa_loop.py:615-638 영역
gate_result = self._run_quality_gate(skill_dir, skill_name)

# 분기 1: gate FAIL (정상 실패)
if gate_result is not None and not gate_result.passed:
    for reason in gate_result.failure_reasons:
        print_agent_msg("SkillEvolve", reason, "⚠️")
    print_agent_msg("SkillEvolve", f"품질 게이트 실패 — rollback 시작: {skill_name}", "🚫")
    self._rollback_skill(skill_dir, skill_name)  # H5: meta.yaml/meta.json 포함 복원
    return gate_result

# 분기 2: gate PASS (정상 성공) — v7 외부 try/finally + 3개 내부 독립 try
elif gate_result is not None and gate_result.passed:
    # H5 v7 (af-critic v6 #2 + af-cross-review v6 합의 반영):
    # v6의 3개 독립 try 구조는 v5 결함(외부 except → EvolutionBus 누락)을 해소했으나,
    # Step 4 cleanup이 일반 호출이라 다음 두 경로에서 미실행 위험:
    #   (a) BaseException (KeyboardInterrupt, SystemExit) — except Exception이 catch 못함
    #   (b) except 블록 내부 logger.error/print_agent_msg가 예외 던질 때 (BrokenPipeError 등)
    # v7: 외부 try/finally로 Step 1~3 전체 감쌈. Step 4는 finally에서 항상 실행.
    #
    # `old_version`은 본 elif 진입 전 외부 함수 스코프(_try_evolve_failed_skill line 591)에서
    # 이미 읽힌 변수. 본 PASS 분기는 그 값을 참조한다.
    new_version = "unknown"

    try:
        # Step 1: registry 핫리로드 (실패해도 진행)
        try:
            self._hot_reload_registry(skill_name)
        except Exception as reload_exc:
            logger.error("[SkillEvolve] hot_reload 예외 (%s): %s", skill_name, reload_exc)
            print_agent_msg("SkillEvolve", f"hot_reload 실패 (계속 진행): {skill_name}", "⚠️")

        # Step 2: 새 버전 읽기 (실패해도 fallback)
        try:
            new_version = self._read_skill_version(skill_dir)
        except Exception as ver_exc:
            logger.error("[SkillEvolve] read_skill_version 예외 (%s): %s", skill_name, ver_exc)
            print_agent_msg("SkillEvolve", f"version 조회 실패 (fallback=unknown): {skill_name}", "⚠️")

        # Step 3: EvolutionBus broadcast (캐시 무효화 보장 — Step 1/2 실패해도 호출됨)
        try:
            evo_bus = SkillEvolutionBus.get_instance()
            evo_bus.bind_runner(self.runner)
            evo_bus.on_skill_evolved(
                skill_id=skill_name,
                skill_dir=skill_dir,
                old_version=old_version,  # 외부 함수 스코프(_try_evolve_failed_skill)에서 읽힌 값
                new_version=new_version,
                trigger="fsa_failure",
            )
            print_agent_msg("SkillEvolve", f"스킬 진화 성공 + 전체 캐시 무효화: {skill_name}", "✅")
        except Exception as bus_exc:
            logger.error("[SkillEvolve] EvolutionBus.on_skill_evolved 예외 (%s): %s", skill_name, bus_exc)
            print_agent_msg("SkillEvolve", f"EvolutionBus 실패 (계속 진행): {skill_name}", "⚠️")
    finally:
        # Step 4 v7: 외부 finally — BaseException + except 내부 예외 모두에서 도달 보장.
        # cleanup 자체가 예외 던지면 propagate (silent fail 금지, H2' 일관).
        self._cleanup_skill_baks(skill_dir)
    return gate_result

# 분기 3: gate None (게이트 자체 미완료/예외)
else:
    # H5 v4 (af-cross-review v3 BLOCK Q1): _run_quality_gate가 예외로 None 반환한 경우
    # (fsa_loop.py:731-733). 게이트 자체가 신뢰 불가이므로 진화 결과를 보존하지 않고
    # rollback이 안전한 선택. cleanup만으로는 메타파일이 진화 상태로 남음.
    print_agent_msg("SkillEvolve", f"품질 게이트 미완료 — rollback (보수적): {skill_name}", "⚠️")
    self._rollback_skill(skill_dir, skill_name)
    return None
```

**v4 변경 요약:**
- 분기 1 (FAIL): v3 그대로
- **분기 2 (PASS)**: try/except/finally 도입 — EvolutionBus 예외 시에도 `_cleanup_skill_baks` 보장 (af-critic v3 #1 해소)
- **분기 3 (None)**: 단순 return → `_rollback_skill` 명시 (af-cross-review v3 BLOCK Q1 해소). 게이트 신뢰 불가 시 보수적 선택

**이유**: 현재 sandbox/AST 실패만 rollback (line 610). 품질 게이트 실패 분기가 누락되어 live skill이 진화된 채 방치. Stage 1에서 candidate dir로 근본 해결 예정이지만, Stage 0에서 즉시 봉쇄 필요.

**v2 BLOCK 해제 — meta.yaml 백업/복원 누락 (af-cross-review 발견):**

기존 `_rollback_skill`(`fsa_loop.py:700-716`)은 `skill.py/SKILL.md/skill.md`만 복원한다. 하지만 진화 흐름에서:
- `skill_creator.py:756-762` `evolve_skill()`이 `meta.yaml`의 version을 직접 bump 후 `_write_meta` (백업 없음)
- `skill_enricher.py:259-263` `enrich_skill_metadata(force=True)`가 description/keywords 등을 meta.yaml에 추가 저장 (백업 없음)
- `fsa_loop.py:604` enrich가 quality gate 전에 이미 호출됨

→ **gate 실패 시 meta.yaml은 진화 상태로 영구 잔류** (코드만 복원되고 메타는 못 돌림).

**v3 보강 5건 (정확한 라인 + gate PASS cleanup 추가):**

1. **`core/skill_creator.py:756`** `if skill_type == "action":` 분기 안, `_write_meta(...)` 호출 직전:
   ```python
   # H5 v3: meta.yaml 백업 (action 타입 skill에서만 적용)
   meta_yaml = os.path.join(skill_dir, "meta.yaml")
   if os.path.exists(meta_yaml):
       shutil.copy2(meta_yaml, meta_yaml + ".bak")
   _write_meta(skill_dir, name, ...)  # 기존 호출 (line 762)
   ```
   주의: `evolve_skill`(line 682)에서 `skill_type == "action"` 분기 안에서만 meta.yaml을 다루므로, .bak도 동일 분기 안에서 생성. knowledge 타입 skill은 미적용.

2. **`core/skill_enricher.py`** `enrich_skill_metadata()` 진입 직후 (line 261 `_write_meta` 직전):
   ```python
   # H5 v3: 메타 백업 (외부 evolve_skill이 먼저 만든 .bak이 있으면 보존)
   meta_yaml = os.path.join(skill_dir, "meta.yaml")
   if os.path.exists(meta_yaml) and not os.path.exists(meta_yaml + ".bak"):
       shutil.copy2(meta_yaml, meta_yaml + ".bak")
   ```
   호출 순서: `fsa_loop.py:593 evolve_skill` → `fsa_loop.py:604 enrich_skill_metadata` → enricher의 not exists 체크가 evolve_skill의 .bak를 보존 (af-cross-review Q1 ACCEPT 검증 완료).

3. **`core/fsa_loop.py:704`** `_rollback_skill`의 복원 대상 확장:
   ```python
   for filename in ("skill.py", "SKILL.md", "skill.md", "meta.yaml", "meta.json"):
       bak = os.path.join(skill_dir, filename + ".bak")
       src = os.path.join(skill_dir, filename)
       if os.path.exists(bak):
           shutil.copy2(bak, src)
           os.remove(bak)
   ```

4. **`core/fsa_loop.py:621-622`** gate PASS 분기 — `_hot_reload_registry(skill_name)` 직후 .bak cleanup 추가 (v3 신규):
   ```python
   elif gate_result is not None and gate_result.passed:
       self._hot_reload_registry(skill_name)
       # H5 v3: gate PASS 시 .bak 명시 정리 (다음 사이클에서 stale .bak 우회 방지)
       self._cleanup_skill_baks(skill_dir)
   ```

   신규 메서드 `_cleanup_skill_baks(skill_dir)` (`fsa_loop.py` 클래스 내):
   ```python
   def _cleanup_skill_baks(self, skill_dir: str) -> None:
       """gate PASS 후 .bak 정리. stale .bak이 다음 진화 사이클에서 enricher의 not exists 체크를 우회하는 것을 막는다."""
       import os
       for filename in ("skill.py", "SKILL.md", "skill.md", "meta.yaml", "meta.json"):
           bak = os.path.join(skill_dir, filename + ".bak")
           if os.path.exists(bak):
               try:
                   os.remove(bak)
               except Exception as e:
                   logger.warning("[SkillEvolve] .bak 정리 실패 %s: %s", bak, e)
   ```

5. **신규 테스트 T4-meta**: ① gate FAIL → meta.yaml.bak으로 복원 ② gate PASS → meta.yaml.bak 정리 확인 ③ stale .bak이 다음 진화 사이클에 영향 없음 검증.

**영향 범위**: skill_creator.py + skill_enricher.py + fsa_loop.py 3 파일. .bak이 없으면 graceful.

**v3 추가 이유 (af-cross-review BLOCK Q1)**: gate PASS 시 .bak이 영구 잔류하면 → 다음 진화 사이클에서 enricher의 `not os.path.exists(bak)` 체크가 stale .bak을 보존 → enricher가 메타 백업을 못함 → 그 사이클 rollback 발동 시 잘못된 baseline으로 복원. 데이터 정합성 위험.

---

### H6. trace_log 영속성 우회 (RunEventStore 라우팅)

**파일**: `core/hooks/skill_self_evolution.py`
**라인**: 146-188 (`_record_evolution_to_memory`)

**현재 동작**: `UnifiedMemoryFacade.write(target_backend="trace_log")` → `TraceLogAdapter.write()` always False → facade returns None → 영속성 0.

**선택지:**
- **선택지 A (권장, Stage 0)**: trace_log 라우팅을 **RunEventStore append**로 변경
- 선택지 B: TraceLogAdapter.write를 실제 구현 — 큰 침습 (다른 호출자 영향), Stage 0 범위 외

**선택지 A 변경**:

**Before:**
```python
async def _write() -> None:
    await facade.write(
        content,
        memory_type=MemoryType.SEMANTIC,
        metadata={"event_type": "skill_evolution", "skill_id": skill_id},
        target_backend="trace_log",
    )
```

**v4 H6 최종안 (sentinel run_id + size 경고 patch 명시):**

1. **enum 추가** (`core/events/run_event.py:23-35`):
   ```python
   class RunEventType(str, Enum):
       # ... 기존 ...
       SKILL_EVOLVED = "skill_evolved"
   ```

   **+ logger 정의 추가** (모듈 상단, 현재 logger 정의 0건 확인됨):
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```

1-b. **`FileRunEventStore.append()` size 경고 patch** (`core/events/run_event.py:100-107` 영역):

   v4 (af-cross-review v3 BLOCK Q3 해소): 위험표에만 적었던 "1MB 경고"의 실제 patch 코드를 명시.

   **Before** (현재 코드):
   ```python
   def append(self, event: RunEvent) -> None:
       path = self._path(event.run_id)
       os.makedirs(os.path.dirname(path), exist_ok=True)
       try:
           with open(path, "a", encoding="utf-8") as f:
               f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
       except Exception:
           pass
   ```

   **After v4**:
   ```python
   _SIZE_WARN_THRESHOLD = 1_048_576  # 1MB
   _size_warned_paths: set[str] = set()  # 모듈 수준 — 같은 파일에 대해 반복 경고 방지

   def append(self, event: RunEvent) -> None:
       path = self._path(event.run_id)
       os.makedirs(os.path.dirname(path), exist_ok=True)
       try:
           # H6 v4: append 전 size 경고 (sentinel run_id의 무한 증가 가시화)
           if path not in _size_warned_paths and os.path.exists(path):
               try:
                   if os.path.getsize(path) > _SIZE_WARN_THRESHOLD:
                       logger.warning(
                           "[RunEventStore] events.jsonl > 1MB: %s — Stage 2 rotation 도입 전까지 모니터링",
                           path,
                       )
                       _size_warned_paths.add(path)
               except OSError:
                   pass
           with open(path, "a", encoding="utf-8") as f:
               f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
       except Exception as e:
           logger.error("[RunEventStore] append 실패 %s: %s", path, e)  # silent except 제거 (H2' 일관)
   ```

   주의: `except: pass` → `logger.error`로 교체 (H2' 일관성). 같은 파일에 대해 1회만 경고하도록 모듈 수준 set 사용 (로그 폭주 방지).

   **v5 한계 명시 (af-cross-review v4 HOLD #4 + af-critic v4 #4 반영):**
   - `_size_warned_paths`는 **per-process 1회 경고**. 멀티프로세스(예: PyInstaller frozen + 서브프로세스 worker) 환경에서는 프로세스별로 1회씩 경고가 출력될 수 있음.
   - 같은 프로세스 내 멀티스레드에서 check-then-act 패턴 race로 경고가 드물게 2회 출력 가능 (CPython GIL이 set.add는 atomic 보장하나 if-not-in 체크 사이 race 가능). 기능 안전성 영향 없음 (경고 폭주 완화 목적이므로 가끔 중복 OK).
   - 기존 코드베이스 패턴과 동일 수준 (`core/events/run_event.py:128 _default_store`, `core/skill_evolution_bus.py:39-50` singleton 등). 추가 Lock 도입 시 성능 손해 > 이득.
   - Stage 2에서 RunEventStore rotation 정책 정식 도입 시 본 메커니즘 deprecated.

2. **`SkillSelfEvolutionHook._record_evolution_to_memory` 변경**:
   ```python
   def _record_evolution_to_memory(self, skill_id, old_version, new_version, trigger):
       try:
           from core.events.run_event import RunEvent, RunEventType, get_default_store
           store = get_default_store()
           # H6 v2: sentinel run_id 고정 — Stage 1에서 hook에 run_id 주입 인터페이스 추가 시 교체
           # trigger를 run_id로 쓰면 runs/cross_verification/events.jsonl 같은 가짜 디렉토리 생성됨
           run_id = getattr(self, "_current_run_id", None) or "_skill_evolution"
           ev = RunEvent(
               run_id=run_id,
               event_type=RunEventType.SKILL_EVOLVED,
               payload={
                   "skill_id": skill_id,
                   "old_version": old_version,
                   "new_version": new_version,
                   "trigger": trigger,
                   "ts": now_iso(),
               },
           )
           store.append(ev)
       except Exception as e:
           logger.debug("[SelfEvolution] RunEvent 기록 실패 (무시): %s", e)
   ```

**이유**: trace_log가 read-only로 굳어있는 상태에서 daemon write가 무한 silent fail하는 것을 즉시 봉쇄. RunEventStore는 file-based append-only로 검증된 인프라(T1-1, T3-7).

**v2 sentinel 결정 (af-critic Q4 WARN 반영):**

v1에서 `run_id=trigger or "skill_evolution"`을 사용했으나, `trigger` 값이 `"cross_verification"`/`"fsa_failure"` 같은 문자열이면 `runs/cross_verification/events.jsonl` 같은 **가짜 run 디렉토리**가 생성됨. 진화 이벤트가 실제 실행 run의 events.jsonl에 합산되지 않는 구조적 문제.

**v2 해결**:
- 우선: `self._current_run_id`를 hook에 주입 (Stage 1에서 인터페이스 추가)
- Stage 0 sentinel: `"_skill_evolution"` 고정 (밑줄 prefix로 가짜 run 디렉토리임을 명시)
- 모든 진화 이벤트는 `runs/_skill_evolution/events.jsonl` 단일 파일에 누적 → 사후 분석 시 실제 run과 분리되어 있음을 명확히 표현

**Stage 1 인계**: `SkillSelfEvolutionHook.__init__(run_id=...)` 인터페이스 추가 + `agent_runner.py`에서 hook 생성 시 현재 run_id 전달. 그 후 `"_skill_evolution"` sentinel은 fallback으로만 사용.

**영향 범위**:
- enum 1줄 추가 (`run_event.py:23-35`)
- hook 메서드 본체 교체 (`skill_self_evolution.py:146-188`)
- threading.Thread 제거 가능 (RunEventStore.append는 동기, 빠름)
- 외부 enum 소비자: `from_dict(et)`가 unknown 시 raw string fallback (`run_event.py:65-69`) → graceful

---

### H7. cross_verification의 evolve_skill 패턴 정리

**파일**: `core/cross_verification.py`
**라인**: 653-668

**Before:**
```python
ok = evolve_skill(
    skill_dir=skill_dir,
    feedback=judgment.feedback,
    error_log=f"실패 패턴: {patterns}",
)
if ok:
    evolved.append(skill_name)
    old_v = "unknown"
    new_v = "evolved"
    bus.on_skill_evolved(
        skill_id=skill_name,
        skill_dir=skill_dir,
        old_version=old_v,
        new_version=new_v,
        trigger="cross_verification",
    )
```

**Stage 0 범위**: Stage 1까지는 candidate staging이 없으므로 evolve_skill 본체 동작은 그대로. 다만 H1+H2와 같은 안전 패턴 적용:
1. `bus = SkillEvolutionBus.get_instance()` 사용 (이미 같은 함수 상단에서 사용 중인지 확인 필요)
2. kwarg 정합성 확인 (현재는 `skill_id=` 올바름 → 변경 없음)
3. **추가**: evolve_skill 후 sandbox 검증 1회 명시 호출 — 실패 시 rollback (fsa_loop._verify_evolved_skill + _rollback_skill 패턴 차용)

**After:**
```python
ok = evolve_skill(
    skill_dir=skill_dir,
    feedback=judgment.feedback,
    error_log=f"실패 패턴: {patterns}",
)
if ok:
    # H7: Stage 0 보강 — sandbox 검증 1회. 실패 시 rollback.
    skill_py = os.path.join(skill_dir, "skill.py")
    verified = self._verify_evolved_skill_sandbox(skill_py, skill_name)
    if not verified:
        self._rollback_evolved_skill(skill_dir, skill_name)
        continue
    evolved.append(skill_name)
    bus.on_skill_evolved(
        skill_id=skill_name,
        skill_dir=skill_dir,
        old_version="unknown",
        new_version="evolved",
        trigger="cross_verification",
    )
```

**v2 H7 재구성 (af-cross-review ACCEPT — 공용 모듈 분리):**

v1은 cross_verification.py 내부에 helper 메서드 2개를 추가했으나, 이는 fsa_loop의 `_verify_evolved_skill`/`_rollback_skill`과 동일 로직 사본. Codex가 "공용 모듈로 빼라"고 권고. 비용/효과 분석 결과 채택.

**v3 신규 모듈** (af-cross-review BLOCK Q3 + af-critic v2 #4 반영): `core/skill_evolution_safety.py`

**v3 핵심 정정**:
- ✅ `quick_guard` 보안 검사 단계 보존 (`fsa_loop.py:677, 682-684`와 동등)
- ✅ `rollback_evolved_skill`의 silent except → `logger.warning` (H2'와 일관)
- ✅ logger 명시 정의

```python
"""
core/skill_evolution_safety.py
==============================
스킬 진화 안전망 헬퍼. fsa_loop와 cross_verification이 공유.

Stage 0 임시 모듈. Stage 1에서 SelfEvolutionController로 흡수 예정.

# TODO(Stage1): SelfEvolutionController가 이 모듈을 흡수하면서
#               candidate staging 기반으로 재구성. 본 모듈은 deprecated 후 제거.
"""
from __future__ import annotations
import logging
import os
import shutil

from core.security_guard import quick_guard, run_isolated

logger = logging.getLogger(__name__)


def verify_evolved_skill_sandbox(skill_py: str, skill_name: str, *, timeout_sec: int = 15) -> bool:
    """
    진화된 스킬을 보안 검사 + 샌드박스 실행으로 검증.

    fsa_loop._verify_evolved_skill (core/fsa_loop.py:674-698)와 동일 로직:
      1. quick_guard(code) — 금지 import/함수 정적 검사
      2. run_isolated(skill_py) — 서브프로세스 + 타임아웃 실행

    두 단계 모두 통과해야 True. 한 단계라도 실패하면 False.
    """
    if not os.path.exists(skill_py):
        logger.warning("[evolution_safety] skill_py 미존재: %s", skill_py)
        return False
    try:
        # Step 1: 보안 정적 검사
        with open(skill_py, "r", encoding="utf-8") as f:
            code = f.read()
        safe, violations = quick_guard(code)
        if not safe:
            logger.warning(
                "[evolution_safety] 보안 검사 실패 (%s): %s",
                skill_name, violations,
            )
            return False

        # Step 2: 샌드박스 실행
        ok, result, stderr = run_isolated(skill_py, timeout_sec=timeout_sec)
        if not ok:
            reason = (result.get("reason") or result.get("error") or stderr) if isinstance(result, dict) else stderr
            logger.warning(
                "[evolution_safety] 샌드박스 검증 실패 (%s): %s",
                skill_name, reason,
            )
            return False
        return True
    except Exception as e:
        logger.error("[evolution_safety] 검증 중 예외 (%s): %s", skill_name, e)
        return False


def rollback_evolved_skill(skill_dir: str, skill_name: str) -> bool:
    """
    진화 실패 시 .bak으로 복원. meta.yaml/meta.json 포함 (H5 v2 정합).

    각 파일별 복원 실패는 warning으로 기록 (silent fail 금지, H2' 일관).
    하나라도 복원되면 True.
    """
    restored = False
    for filename in ("skill.py", "SKILL.md", "skill.md", "meta.yaml", "meta.json"):
        bak = os.path.join(skill_dir, filename + ".bak")
        src = os.path.join(skill_dir, filename)
        if os.path.exists(bak):
            try:
                shutil.copy2(bak, src)
                os.remove(bak)
                restored = True
            except Exception as e:
                logger.warning(
                    "[evolution_safety] rollback 실패 %s/%s: %s",
                    skill_dir, filename, e,
                )
    return restored
```

**호출자 정리 v4 (3개 호출자, 가시성 회복):**

v4 (af-critic v3 #2 + af-cross-review v3 HOLD 해소): `dynamic_orchestrator.py`에도 sandbox 검증 적용 (silent failure 봉쇄 일관성). 각 호출자가 보안/샌드박스 실패 시 `print_agent_msg`를 명시 호출하여 사용자 가시성 복원.

1. **`core/cross_verification.py:653-668`**:
   ```python
   from core.skill_evolution_safety import verify_evolved_skill_sandbox, rollback_evolved_skill

   ok = evolve_skill(skill_dir=skill_dir, feedback=judgment.feedback, error_log=...)
   if ok:
       skill_py = os.path.join(skill_dir, "skill.py")
       if not verify_evolved_skill_sandbox(skill_py, skill_name):
           # H7 v4+v5: 사용자 가시성 회복 — helper는 logger.warning만 남기고
           # 콘솔 알림은 호출자가 책임 (책임 분리)
           # cross_verification은 self._print 사용 (클래스 내부 ANSI 컬러 래퍼 — fsa_loop의 print_agent_msg와 UX 등가).
           # cross_verification.py 상단의 _print 정의가 stdout flush + ANSI 처리를 보장.
           self._print(f"⚠️ 보안/샌드박스 검증 실패 — rollback: {skill_name}", "31")
           rollback_evolved_skill(skill_dir, skill_name)
           continue
       evolved.append(skill_name)
       bus.on_skill_evolved(skill_id=skill_name, ...)
   ```

   **v5 등가성 검증 (af-critic v4 #6 반영)**: `cross_verification.py`의 `self._print(text, color_code)`는 클래스 내부 helper로 ANSI 색상 코드를 적용해 stdout에 출력. `print_agent_msg(prefix, text, emoji)`와는 시그니처가 다르지만 모두 stdout flush 보장. 사용자 가시성 동등.

2. **`core/fsa_loop.py:674-716`** (보너스 정리): 위임으로 단순화 + 가시성 보존
   ```python
   def _verify_evolved_skill(self, skill_py: str, skill_name: str) -> bool:
       from core.skill_evolution_safety import verify_evolved_skill_sandbox
       result = verify_evolved_skill_sandbox(skill_py, skill_name, timeout_sec=15)
       if not result:
           # H7 v4: 가시성 회복 — print_agent_msg는 fsa_loop의 기존 UX 패턴
           print_agent_msg("SkillEvolve", f"검증 실패 (자세한 사유는 logger): {skill_name}", "🛑")
       return result

   def _rollback_skill(self, skill_dir: str, skill_name: str):
       from core.skill_evolution_safety import rollback_evolved_skill
       restored = rollback_evolved_skill(skill_dir, skill_name)
       if restored:
           print_agent_msg("SkillEvolve", f"롤백 완료: {skill_name}", "⏪")
   ```

3. **`core/dynamic_orchestrator.py:587-590`** (v4 신규 — H7' 확장):

   v4 (af-critic v3 #2 해소): 기존 코드는 `evolve_skill` 호출 후 검증 없이 `bus.on_skill_evolved` 호출 → cross_verification과 동일한 silent failure가 잔존했음. H7과 같은 안전망 적용.

   **Before**:
   ```python
   if any(kw and kw in name_lower for kw in keywords if len(kw) > 2):
       skill_dir = os.path.join(skills_dir, skill_name)
       ok = evolve_skill(skill_dir, feedback=feedback, error_log=error_log[:1000])
       if ok:
           evolved.append(skill_name)
           print_agent_msg("Evolve", f"스킬 진화 성공: {skill_name}", "")
   ```

   **After v4**:
   ```python
   if any(kw and kw in name_lower for kw in keywords if len(kw) > 2):
       skill_dir = os.path.join(skills_dir, skill_name)
       ok = evolve_skill(skill_dir, feedback=feedback, error_log=error_log[:1000])
       if ok:
           # H7' v4: cross_verification/fsa_loop와 동일 안전망 적용 (silent failure 봉쇄 일관성)
           from core.skill_evolution_safety import verify_evolved_skill_sandbox, rollback_evolved_skill
           skill_py = os.path.join(skill_dir, "skill.py")
           if not verify_evolved_skill_sandbox(skill_py, skill_name):
               print_agent_msg("Evolve", f"⚠️ 검증 실패 — rollback: {skill_name}", "")
               rollback_evolved_skill(skill_dir, skill_name)
               continue
           evolved.append(skill_name)
           print_agent_msg("Evolve", f"스킬 진화 성공: {skill_name}", "")
   ```

**Stage 1 인계 (필수, TODO 주석):**
- `core/skill_evolution_safety.py` 파일 헤더에 `# TODO(Stage1): SelfEvolutionController가 이 모듈을 흡수`
- `cross_verification.py` 호출 사이트에 `# TODO(Stage1): SelfEvolutionController.submit()으로 교체`
- `fsa_loop.py` 위임 메서드에 `# TODO(Stage1): SelfEvolutionController가 직접 candidate staging 처리`

**영향 범위**:
- 신규: `core/skill_evolution_safety.py` (1 파일)
- 수정: `cross_verification.py` (helper 호출), `fsa_loop.py` (위임으로 단순화)
- `af.spec` hiddenimports에 `core.skill_evolution_safety` 추가
- 신규 테스트: `tests/test_skill_evolution_safety.py`

**리스크 완화**: TODO 주석을 "권장"이 아닌 **필수 삽입**으로 격상 (af-critic WARN 반영). Stage 1 시작 시 grep으로 모든 TODO 회수.

---

## 3. 검증 종료 조건 (각 H별)

| H | 검증 방법 |
|---|----------|
| H1 | `python3 -c "from core.skill_evolution_bus import SkillEvolutionBus; b1 = SkillEvolutionBus.get_instance(); b2 = SkillEvolutionBus.get_instance(); assert b1 is b2"` |
| H2 | `dynamic_orchestrator._try_evolve_from_patterns` mock 호출 시 TypeError 없음 (단위 테스트 신규 1건) |
| H3 | `bus.on_bulk_enriched(["test_skill"])` 호출 후 `_step7_broadcast` 호출 횟수 ≥ 1 (mock 검증) |
| H4 | `runner = AgentRunner(); for _ in range(3): runner.run(...); assert runner._sse_hook._execution_count == 3` (post_execute 누적 확인) |
| H5 | mock GateResult.passed=False 시 `_rollback_skill` 호출 추적 (단위 테스트 1건) |
| H6 | enum에 SKILL_EVOLVED 존재 + `runs/{run_id}/events.jsonl`에 진화 이벤트 1건 이상 기록 |
| H7 | mock evolve_skill 성공 + sandbox 실패 케이스에서 `_rollback_evolved_skill` 호출 (단위 테스트 1건) |

---

## 4. 새 단위 테스트 (Stage 0 신규, v2 보강)

| 테스트 | 파일 | 검증 |
|--------|------|------|
| T1 | `tests/test_evolution_hotfix_h1_h2.py` | DynamicOrchestrator on_skill_evolved 정상 호출 (TypeError 없음). H2' 추가: silent except 제거 검증 (logger.error 호출) |
| T2 | `tests/test_evolution_hotfix_h3.py` | on_bulk_enriched가 _step7_broadcast를 skill_ids 개수만큼 호출 |
| T3 | `tests/test_evolution_hotfix_h4.py` | **v2 보강**: ① 같은 AgentRunner 인스턴스로 run() 3회 호출 → `runner._sse_hook._execution_count == 3` ② 매 run마다 새 HookEventBus 생성됨을 명시 (bus 객체는 != identity, hook은 == identity) ③ register 중복 차단 검증 (event_bus.py:38-46 동작) |
| T4 | `tests/test_evolution_hotfix_h5.py` | fsa_loop 품질 게이트 실패 시 _rollback_skill 호출 추적 |
| **T4-meta** | `tests/test_evolution_hotfix_h5_meta.py` | **v6 보강**: ① evolve_skill + enrich_skill_metadata 호출 후 meta.yaml.bak 생성 확인 ② **gate FAIL 분기**: meta.yaml이 baseline 내용으로 복원 + .bak 정리 ③ **gate PASS 분기**: meta.yaml.bak이 `_cleanup_skill_baks`로 정리됨 ④ **gate None 분기**: `_run_quality_gate` 예외 시뮬레이션 → meta.yaml이 baseline으로 복원 + .bak 정리 ⑤ **EvolutionBus 예외 + gate PASS**: cleanup 실행 검증 ⑥ **`_hot_reload_registry` 예외 + gate PASS**: cleanup 실행 + **(v6 신규) EvolutionBus는 fallback version으로 호출됨 검증** (캐시 stale 방지) ⑦ **`_read_skill_version` 예외 + gate PASS**: cleanup + **(v6 신규) EvolutionBus가 new_version="unknown" fallback으로 호출됨 검증** ⑧ stale .bak이 다음 진화 사이클에서 enricher의 not exists 체크를 우회하지 않음 ⑨ gate None 분기 + enrich .bak 미생성 시나리오 ⑩ **knowledge 타입 skill의 gate FAIL 분기 (v7 정정)**: knowledge 타입에서는 `_write_meta` 호출이 없어 meta.yaml.bak 미생성이 정상. `_rollback_skill`은 5파일 모두 시도하지만 .bak 없는 파일은 graceful skip. 결과: skill.py.bak/SKILL.md.bak 등 실제 존재하는 .bak만 복원. action 분기 한정 동작 확인 ⑪ **(v7 신규) except 내부 예외 시 cleanup 도달**: Step 1 except 블록의 `logger.error`가 OSError 던지도록 mock + Step 4 cleanup이 외부 finally에서 호출됨 검증 (BrokenPipeError, OSError 시뮬레이션) |
| T5 | `tests/test_evolution_hotfix_h6.py` | **v4 보강**: ① RunEventType.SKILL_EVOLVED enum 존재 ② RunEvent가 `runs/_skill_evolution/events.jsonl` (sentinel)에 기록 ③ trigger 문자열을 run_id로 쓰지 않음 ④ **size 경고 (v4 신규)**: events.jsonl > 1MB 시뮬레이션 → logger.warning 1회 호출 + 두 번째 append에선 미호출(_size_warned_paths set) ⑤ append 예외 시 logger.error 호출 (silent except 미발생) |
| T6 | `tests/test_skill_evolution_safety.py` | **v4 보강**: ① verify_evolved_skill_sandbox quick_guard + sandbox 모두 ok=true → True ② **quick_guard 위반 (v4 신규)**: 금지 import 코드 → False, logger.warning 호출 ③ sandbox 예외 → False ④ rollback_evolved_skill이 skill.py + meta.yaml + meta.json 모두 복원 ⑤ rollback 일부 실패 → 다른 파일 복원 계속 + logger.warning 출력 ⑥ .bak 없으면 graceful (False 반환) |
| **T7** | `tests/test_evolution_hotfix_h7_orchestrator.py` | **v5 보강** (H7' dynamic_orchestrator 확장): ① `_try_evolve_from_patterns`에서 evolve_skill 성공 + verify 실패 → rollback 호출 + bus.on_skill_evolved 미호출 검증 ② verify 성공 → bus.on_skill_evolved 정상 호출 ③ **(v5 신규) 다중 패턴 재매칭**: pattern A에서 skill_X 검증 실패 + rollback 후, pattern B가 동일 skill_X를 매칭하면 evolve_skill이 다시 호출됨을 확인 (의도된 동작 — Stage 1 cooldown 도입 전까지 허용) ④ **(v5 신규) evolved 리스트 일관성**: 동일 skill_X가 결국 evolved에 포함될지는 마지막 패턴 시도 결과에 따름 — 회기 정합성 검증 |

각 테스트는 mock 기반, 외부 LLM 호출 없음. T4-meta + T6은 임시 디렉토리 사용 (tmp_path fixture).

---

## 5. 변경 파일 목록 (Review-Gate용, v2)

```
[수정]
core/agent_runner.py                    (H4 — lazy hook 인스턴스)
core/cross_verification.py              (H7 — skill_evolution_safety + 호출자 print_agent_msg)
core/dynamic_orchestrator.py            (H1, H2, H2', H7' — singleton + skill_id + logger + sandbox 검증)
core/events/run_event.py                (H6 v4 — SKILL_EVOLVED enum + logger 정의 + size 경고 patch + silent except 제거)
core/fsa_loop.py                        (H5 v4 — 3분기 cleanup/rollback, try/finally, _cleanup_skill_baks 신규, _verify/_rollback 위임 + 가시성)
core/hooks/skill_self_evolution.py      (H6 — RunEventStore 라우팅, sentinel run_id)
core/skill_creator.py                   (H5 v3 — meta.yaml.bak 생성, action 분기 line 756)
core/skill_enricher.py                  (H5 v3 — meta.yaml.bak 생성, line 261 직전)
core/skill_evolution_bus.py             (H3 — on_bulk_enriched broadcast)

[신규]
core/skill_evolution_safety.py          (H7 v2 — 공용 헬퍼)
af.spec                                 (hiddenimports에 skill_evolution_safety 추가)

[테스트 신규]
tests/test_evolution_hotfix_h1_h2.py
tests/test_evolution_hotfix_h3.py
tests/test_evolution_hotfix_h4.py       (H4 EventBus 인스턴스 공유 검증 포함)
tests/test_evolution_hotfix_h5.py
tests/test_evolution_hotfix_h5_meta.py  (v4 보강 — gate FAIL/PASS/None + try/finally)
tests/test_evolution_hotfix_h6.py       (v4 보강 — sentinel + size 경고)
tests/test_skill_evolution_safety.py    (v4 보강 — quick_guard 위반 케이스)
tests/test_evolution_hotfix_h7_orchestrator.py  (v4 신규 — H7' dynamic_orchestrator)
```

총: 코드 9 수정 + 2 신규(`skill_evolution_safety.py`, `af.spec`) + 테스트 7개. **3-Tier Review-Gate 필수.**

---

## 6. 위험 평가 (v3)

| 위험 | 가능성 | 영향 | 완화 |
|------|-------|------|------|
| H4 lazy 인스턴스 — 매 run에서 register 중복 | 낮 | 중복 처리 가능 | **(검증 완료)** `event_bus.py:38-46`의 register가 identity 체크로 idempotent. 같은 인스턴스 재등록 시 조기 반환 |
| H6 SKILL_EVOLVED enum 추가 → 외부 소비자 영향 | 낮 | 소비자가 enum 매핑하면 KeyError 가능 | **(검증 완료)** `run_event.py:65-69 from_dict`가 ValueError catch + raw string fallback (graceful) |
| H7 cross_verification 헬퍼 중복 | 낮 | 코드 중복 | Stage 1에서 SelfEvolutionController로 통합 시 제거 (TODO **필수** 주석) |
| evolve_skill의 .bak 정책 모듈 간 불일치 | 낮 | rollback 실패 가능 | v3 `_cleanup_skill_baks` + `rollback_evolved_skill`로 통일 |
| **(v3 신규) H6 sentinel `_skill_evolution` — 새 디렉토리 관례** | 중 | 외부 분석 도구가 `_` prefix run 처리 모름 | grep 결과 코드베이스에 `runs/_*` 선례 0건 → 새 관례 도입. 외부 분석 도구가 sentinel run을 별도 처리하도록 문서화. Stage 1 인계: hook에 실제 run_id 주입 인터페이스 추가 |
| **(v3 신규) H6 events.jsonl 무한 증가** | 중 | 디스크 점유 + 검색 성능 저하 | Stage 0 단순 완화: append 시 파일 크기 1MB 초과하면 `logger.warning("events.jsonl size > 1MB")` 1회 출력. Stage 2에서 RunEventStore rotation 정책 정식 도입 |
| **(v3 신규) H7 신규 모듈 PyInstaller frozen 빌드 실패** | 낮 | exe 빌드 import 실패 | `af.spec` `hiddenimports`에 `core.skill_evolution_safety` 추가 + `python build_exe.py` 후 frozen 환경에서 import 검증 |
| **(v3 신규) H7 verify에서 quick_guard 누락 시 보안 회귀** | 매우 높 | live skill에 금지 import 통과 | **(v3 해결)** `verify_evolved_skill_sandbox`에 quick_guard 단계 명시 포함 (af-cross-review Q3 BLOCK 해제) |
| **(v3 신규) H5 gate PASS 후 stale .bak 잔존** | 중 | 다음 사이클에서 enricher가 백업 못함 → rollback 시 잘못된 baseline | **(v3 해결)** `_cleanup_skill_baks` 명시 호출 (gate PASS 분기) |
| **(v4 신규) H5 gate None 경로 (gate 자체 예외)에서 stale 진화 잔존** | 중 | 게이트 신뢰 불가 + 메타파일 진화 상태 영구 잔류 | **(v4 해결)** else 분기에 `_rollback_skill` 명시 (보수적 선택). 게이트 자체가 실패한 진화는 신뢰 불가 |
| **(v4 신규) H5 EvolutionBus 예외 시 cleanup 미실행** | 중 | gate PASS인데 bus 호출 중 예외 → cleanup 건너뜀 → stale .bak | **(v4 해결)** try/except/finally로 cleanup 보장. except는 logger.error로 가시화 |
| **(v4 신규) H7' dynamic_orchestrator silent failure 잔존** | 중 | cross_verification만 H7 적용 → orchestrator 경로의 evolve_skill은 검증 없이 publish | **(v4 해결)** `dynamic_orchestrator._try_evolve_from_patterns`에도 verify_evolved_skill_sandbox 적용. silent failure 봉쇄 일관성 |
| **(v4 신규) H7 보안 실패 사용자 가시성 회귀** | 낮 | helper의 logger.warning만으론 운영자가 보안 실패 알림 놓침 | **(v4 해결)** 호출자(cross_verification, fsa_loop, dynamic_orchestrator)가 print_agent_msg 명시 호출 |
| **(v4 신규) H6 size 경고 명세 누락** | 중 | 위험표에만 적고 실제 patch 코드 없음 → 구현 시 빠질 위험 | **(v4 해결)** `FileRunEventStore.append` patch 코드 명시 + 모듈 수준 `_size_warned_paths` set으로 로그 폭주 방지 |
| **(v5 신규) H5 PASS 분기 try 범위 결함** | 높 | `_hot_reload_registry`/`_read_skill_version` 예외 시 v4의 finally가 안 탐 → stale .bak 잔존 | **(v5 해결)** 외부 try/except/finally가 hot_reload+read_version+EvolutionBus 모두 감싸도록 재배치. 모든 예외 경로에서 `_cleanup_skill_baks` 보장 |
| **(v5 신규) H6 race condition (멀티스레드)** | 매우 낮 | 같은 path에 size 경고 1~2회 중복 (기능 영향 없음, 폭주 방지 95% 달성) | **(v5 명시)** per-process 1회 경고로 명시. 기존 코드베이스 singleton 패턴(skill_evolution_bus.py:39-50)과 동일 안전성 |
| **(v5 신규) H6 멀티프로세스 경고 N회** | 낮 | PyInstaller frozen worker 등에서 프로세스별 경고 출력 | **(v5 명시)** Stage 2 RunEventStore rotation 정책 정식 도입 시 본 메커니즘 deprecated |
| **(v5 신규) H7' 다중 패턴 재매칭으로 동일 skill 재진화 시도** | 낮 | pattern A 실패 후 pattern B가 같은 skill을 다시 매칭 → 재진화 | **(v5 명시)** Stage 0 한정 의도된 동작. Stage 3 TriggerPolicy yaml의 per-skill cooldown으로 정식 제어 |
| **(v6 신규) H5 v5 외부 except 시 EvolutionBus 호출 누락 (silent stale cache)** | 중 | hot_reload/read_version 예외 → 내부 try 미진입 → 캐시 무효화 누락 → 디스크는 새 버전, 캐시는 구버전 stale | **(v6 해결)** v6 try 평탄화 — 각 단계 독립 try. hot_reload/read_version 실패해도 EvolutionBus는 fallback version으로 호출 → 캐시 무효화 항상 보장 |
| **(v7 신규) H5 v6 Step 4 cleanup 미도달 (BaseException + except 내부 예외)** | 매우 낮 | `KeyboardInterrupt`/`SystemExit` 또는 `logger.error`/`print_agent_msg`의 `BrokenPipeError`/`OSError` → cleanup 미실행 → stale .bak | **(v7 해결)** 외부 try/finally 래핑 — Step 4가 모든 예외 경로(BaseException 포함)에서 도달 보장. cleanup 자체 예외는 propagate (silent fail 금지) |

---

## 7. 롤백 절차 (Stage 0 자체가 회귀 유발 시, v2)

각 H는 독립적이므로 개별 revert 가능. H별 커밋 분리:
- **C1**: H1+H2+H2' — `dynamic_orchestrator.py` (singleton + skill_id + silent except 제거)
- **C2**: H3 — `skill_evolution_bus.py` on_bulk_enriched broadcast
- **C3**: H4 — `agent_runner.py` lazy hook 인스턴스
- **C4**: H5 — `fsa_loop.py` rollback 호출 + 복원 범위 확장
- **C5**: H5 v2 — `skill_creator.py` + `skill_enricher.py` meta.yaml.bak 생성
- **C6**: H6 — `events/run_event.py` enum 추가 + `skill_self_evolution.py` RunEventStore 라우팅
- **C7**: H7 — `skill_evolution_safety.py` 신규 + `cross_verification.py` 사용 + `fsa_loop.py` 위임 + `af.spec`

**총 7 커밋**. 각각 3-Tier Review-Gate 통과 후 push.

**커밋 간 의존성**: 없음 (af-critic Q5 PASS 확인). 단 권장 순서는 C1 → C2 → C3 → C4 → C5 → C6 → C7 (논리적 일관성).

---

## 8. Stage 1으로의 명시적 인계 (v2)

다음 항목은 Stage 0에서 **임시방편**이며 Stage 1에서 근본 해결:

| Stage 0 임시 | Stage 1 근본 해결 |
|-------------|-----------------|
| H5의 `_rollback_skill` 호출 (live 파일 진화 후 rollback) | candidate dir로 격리 → publish 전엔 live 미수정 |
| H5 v2의 meta.yaml.bak (live 파일 백업 우회) | candidate dir로 격리하면 백업 불필요 |
| H7의 `core/skill_evolution_safety.py` 공용 헬퍼 | SelfEvolutionController가 모듈 흡수 (TODO **grep 회수 필수**, "TODO(Stage1)" 패턴) |
| **(v3) H6 sentinel `"_skill_evolution"` — 새 디렉토리 관례** | `SkillSelfEvolutionHook.__init__(run_id=...)` 인터페이스 추가 + agent_runner에서 주입. sentinel은 fallback으로만 |
| **(v3) H6 events.jsonl 1MB 경고 (`_size_warned_paths` set 메커니즘 포함)** | Stage 2에서 RunEventStore rotation/size limit 정책 정식 도입 시 본 메커니즘 전체 deprecated |
| **(v3) H5 .bak cleanup이 gate PASS 분기 한정** | candidate dir로 격리하면 .bak 자체 불필요 |
| H6의 SKILL_EVOLVED enum 단일 사용 | METADATA_ENRICHED, EVOLUTION_REQUESTED, EVOLUTION_PUBLISHED, EVOLUTION_ROLLED_BACK 분화 |
| H6의 `"_skill_evolution"` sentinel run_id | `SkillSelfEvolutionHook.__init__(run_id=...)` 인터페이스 + `agent_runner`에서 주입 |
| H3의 trigger 단순 기록 (분기 없음) | trigger별 분기 추가 (메타 보강 vs 코드 진화 vs 회귀 등) |
| `_detect_failed_skill_dir` 문자열 매칭 (Stage 0 미변경) | Stage 6 skill_id provenance |
| feedback → trigger 정책 (Stage 0 미변경) | Stage 3 TriggerPolicy yaml |
| **(v2 추가) skill_creator.py:751 `open(w)` 비원자 쓰기** (af-critic 발견) | tempfile + os.replace 또는 Stage 1 candidate publish |
| **(v2 추가) bulk_enrich 호출 사이트 정합성** (af-critic 발견) | `bulk_enrich_all_skills`가 실제로 `on_bulk_enriched`를 호출하는지 grep 검증 후 명시 호출 |
| **(v2 추가) RunBudget 진화 비용 연동** (af-critic 발견) | evolve_skill LLM 호출을 RunBudget에 가산 |

---

## 9. 검증 후 진행

본 메모 작성 후 즉시:
1. **af-critic + af-cross-review 2개 병렬 실행** (단일 설계문서 기준)
2. BLOCK 판정 시 본 메모 수정 후 재검증
3. PASS 시 Sonnet으로 모델 전환 → 구현 진입
4. 구현 후 3-Tier Review-Gate (af-test-runner → af-critic → af-cross-review)
5. H별 커밋 6건으로 분리하여 푸시

**구현 시 모델**: Claude Sonnet 4.6
**리뷰 시 모델**: af-critic / af-cross-review (각각 자체 모델 사용)
