# Self-Evolution Stage 1 설계 — 아키텍처 스켈레톤

> **목적**: Stage 0 hotfix가 봉쇄한 silent failure 위에, **candidate-staging 기반 영속 진화 파이프라인**을 도입한다. 핵심 결정은 `SelfEvolutionController` 단일 진입점 + `EvolutionLedger` 영속 + `RunEventType` 4종 분화.
> **범위**: Stage 1 한정. Stage 2(rotation)·Stage 3(TriggerPolicy yaml)·Stage 6(skill_id provenance)는 별도 문서. 단, **저장소 경계는 본 문서에서 결정**한다 (Stage 2의 인터페이스를 미리 예약하지 않으면 EvolutionLedger 설계가 굳어버리기 때문).
> **출처**: Stage 0 hotfix 설계서 §8 인계 표 14행 + 라운드 1 (af-critic + af-cross-review/Codex) + 라운드 2 (양방향 단독 발견 평가)
> **선행**: [`2026-04-27-self-evolution-stage0-hotfix-design.md`](./2026-04-27-self-evolution-stage0-hotfix-design.md)
> **이력**:
> - v1: 2026-04-28 초안 (옵션 B + 9건 + 5섹션 + 600~800줄 합의안 반영)
> - v2: 2026-04-28 라운드 2 비평 BLOCK 해제 5건 + 머지 후 권고 6건 일괄 수정 (§9.2 RunBudget API 재작성, §1.3 5행 + 헤더 명확화, §3.4 grep 결과 명시, §6.3 trigger whitelist + DEFERRED 라우팅 분리, §8.2 검증 완료 못박음, §10.2 Sprint 4→3 축소, §12.1 F6/F7 테스트 추가, §0.1 F10/F11 추적성 추가, §13 라운드 2 리스크 4건)
> - v3: 2026-04-28 라운드 3 신규 결함 4건 인라인 수정 (§7.2 startswith → whitelist 통일, §9.2 pre_consumed 캡처 + read_text 명시 + LLM 비용 한계 §9.2.1 추가, §10.2 (7) Sprint 1 배치 정합성 → `core/evolution_types.py` 분리, §6.3 frozenset 정의 위치 산문 명시)

---

## 0. 변경 요약

### 0.1 결함 (Stage 0가 남긴 임시방편)

| # | Stage 0 임시 | Stage 1 근본 해결 |
|---|-------------|-----------------|
| F1 | `live skill 파일 → 진화 → .bak 백업 → 검증 실패 시 복원` 패턴 (race 조건, 부분 복원 위험) | candidate dir로 격리 → publish 게이트 통과 후 atomic publish |
| F2 | `core/skill_evolution_safety.py` 공용 헬퍼 모듈 (Stage 0 임시) | `SelfEvolutionController` 클래스로 흡수 |
| F3 | `meta.yaml.bak` (action 타입 한정) | candidate 격리 시 백업 자체 불필요 |
| F4 | `SkillSelfEvolutionHook` `_current_run_id` sentinel `"_skill_evolution"` (`hooks/skill_self_evolution.py:168`) | `__init__(run_id=...)` 정식 인터페이스 |
| F5 | `RunEventType.SKILL_EVOLVED` 단일 enum (메타 보강·진화·롤백을 구분 못 함) | METADATA_ENRICHED / EVOLUTION_REQUESTED / EVOLUTION_PUBLISHED / EVOLUTION_ROLLED_BACK 4종 분화 |
| F6 | `SkillSelfEvolutionHook.on_skill_evolved` trigger 단순 기록 (분기 없음, `hooks/skill_self_evolution.py:70-82`) | trigger별 분기 (메타 보강 vs 코드 진화 vs 회귀) |
| F7 | `bulk_enrich_all_skills` → `on_bulk_enriched` 호출 사이트 정합성 미검증 (`hooks/skill_self_evolution.py:131-139`) | 호출 사이트 grep 검증 + 명시적 결합 |
| F8 | `evolve_skill` LLM 비용이 RunBudget에 가산되지 않음 (`skill_creator.py:682`, `742`) | RunBudget `record(text)` 결합 |
| F9 | `skill_creator.py:754` `open(w)` 비원자 쓰기 (Stage 0 §8 Row12) | candidate dir 격리로 자연 해소 (별도 코드 변경 불필요, 명시만) |
| F10 | `dynamic_orchestrator._try_evolve_from_patterns` (line 584-624)에 `TODO(Stage1)` 마커 부재 + Stage 0가 hotfix만 적용 (Stage 0 §8 v4 행) | Controller 흡수 시 본 호출 사이트 회수 (§1.3 #4) |
| F11 | `.bak cleanup이 gate PASS 분기 한정` (Stage 0 §8 v3 행, `fsa_loop._cleanup_skill_baks`) | candidate 격리로 `.bak` 자체 불필요, 메서드 제거 (§5) |

### 0.2 비범위 (Stage 1 미해결)

- Stage 2: `RunEventStore` rotation/size limit (`run_event.py:21` `_size_warned_paths` 프로세스 전역 set 정식 deprecated)
- Stage 3: `TriggerPolicy` yaml (feedback → trigger 정책)
- Stage 6: `_detect_failed_skill_dir` 휴리스틱 (`fsa_loop.py:670`) → `skill_id` provenance

단, **Stage 6 분리 리스크**: candidate publish 게이트가 잘못된 skill 격리도 차단하므로 live 영향은 0이지만, 휴리스틱 오탐 자체는 Stage 1 이후에도 잔존. §11에 명시.

### 0.3 합의 결과 요약 (라운드 1+2 + v2 검증)

| 결정 | 출처 |
|------|------|
| 9건 (5건 + Row7/9/13/14) | af-cross-review/Codex 단독 발견 채택 |
| 호출 사이트 매핑 표 5행 (cross_verification + fsa_loop 메인 흐름 + dynamic_orchestrator + fsa_loop 위임 메서드 + skill_evolution_safety 모듈 자체) | v2: 라운드 2 검증 후 4행 → 5행 확장 (fsa_loop 메인 흐름과 위임 메서드 분리) |
| `bus.on_skill_evolved` skill_dir **Optional 유지** (필수화 철회) | v2: 라운드 2 검증 (`bus.py:72`에서 default 보유 확인 → 필수화는 비호환) |
| 분량 600~800줄 | 양쪽 AGREE (Stage 0 §2 단독 700줄 근거). v2 후 약 720줄 |
| EvolutionLedger 병렬 트랙 | af-critic 라운드 2 권고 (Ledger 미구현 = (1) Controller 블록 노드 위험) |
| Stage 6 publish 게이트 보호망 명시 | af-critic 라운드 2 (Codex의 "효용 약화" 주장 부정) |
| Stage 2 경계 결정 본 문서에 포함 | af-critic 라운드 2 입장 유지 (RunEventStore 공유 hook 코드 근거) |
| RunBudget API 실제 시그니처 (`record`/`is_exhausted`/`remaining`) | v2: 라운드 2 CRITICAL 수정 (`run_budget.py` 직접 검증) |
| trigger whitelist (frozenset) + DEFERRED payload 분리 | v2: 라운드 2 CONCERN 수정 |
| §8.2 grep 검증 결과 본문에 못박음 | v2: 라운드 2 비평 반영 (Sprint 4 → Sprint 1 회귀 테스트만) |
| Sprint 4 → Sprint 3 축소 | v2: §8.2 검증 완료로 (8) Sprint 1로 이동 |

---

## 1. SelfEvolutionController (신규)

### 1.1 목적

Stage 0의 `core/skill_evolution_safety.py` (84줄, `verify_evolved_skill_sandbox` + `rollback_evolved_skill` 2함수) + 3개 호출 사이트(cross_verification, fsa_loop, dynamic_orchestrator)에 분산된 진화 파이프라인을 **단일 진입점**으로 통합한다.

### 1.2 클래스 stub (시그니처만, 구현 X)

**모듈 분리** (라운드 3 N2 채택):
- `core/evolution_types.py` (Sprint 1, 가벼움): `EvolutionDecision` enum + `EvolutionResult` dataclass
- `core/skill_evolution_controller.py` (Sprint 2, Controller 본체): 위 types를 import해서 사용
- `core/hooks/skill_self_evolution.py` (Sprint 1): `EvolutionDecision`만 import해서 §6.3 라우팅에 사용

이 분리로 (7) trigger 분기를 Sprint 1에 안전 배치 가능 (§10.2 참조).

```python
# core/evolution_types.py — Sprint 1 신규

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EvolutionDecision(Enum):
    PUBLISHED = "published"   # candidate → live atomic publish 성공
    REJECTED = "rejected"     # sandbox/quality gate 실패 → candidate 폐기
    DEFERRED = "deferred"     # 게이트 신뢰 불가 → 보수적 폐기 (FSALoop None 분기)
                              # ※ ROLLED_BACK과 의미 분리: 게이트 자체 미실행 = 결정 보류
    ERROR = "error"           # 예외 발생 → candidate 폐기 + 로그


@dataclass
class EvolutionResult:
    skill_id: str
    decision: EvolutionDecision
    candidate_dir: Optional[str]   # ERROR/DEFERRED 시 None 가능
    new_version: Optional[str]
    rejection_reason: Optional[str]
    cost_tokens: int = 0           # F8: RunBudget 가산용


# core/skill_evolution_controller.py — Sprint 2 신규

from core.evolution_types import EvolutionDecision, EvolutionResult
from typing import Optional


class SelfEvolutionController:
    """
    스킬 진화 단일 진입점.

    호출자는 trigger와 feedback을 제공한다. Controller는 candidate dir 생성,
    LLM 진화, sandbox 검증, quality gate, publish 또는 폐기까지 한 번에 처리하고
    EvolutionResult를 반환한다.

    Bus 시그니처 결정 (라운드 2 갱신):
        `core/skill_evolution_bus.py:69-76`의 `on_skill_evolved`는 이미
        `skill_dir: str = ""` default를 보유한다. 따라서 본 Stage 1은 시그니처를
        "필수화"하지 않고 Optional 유지를 선택한다. Controller 내부에서는 publish
        시점에 항상 `skill_dir`을 알고 있으므로 명시 전달하되, 외부 호출자(미래
        hooks 등)가 default를 의지하던 곳은 비파괴 유지.
    """

    def __init__(
        self,
        ledger: Optional["EvolutionLedger"] = None,    # §4.4 병렬 트랙 패턴
        run_id: Optional[str] = None,
        budget: Optional["RunBudget"] = None,          # F8 — core.run_budget.RunBudget
    ) -> None: ...

    def submit(
        self,
        *,
        skill_dir: str,
        skill_id: str,
        trigger: str,
        feedback: str = "",
        error_log: str = "",
    ) -> EvolutionResult: ...

    def _create_candidate(self, skill_dir: str) -> str:
        """candidate dir 생성. live 미수정. F1/F3/F9 모두 candidate 격리로 해소."""
        ...

    def _verify_sandbox(self, candidate_dir: str, skill_id: str) -> bool:
        """quick_guard + run_isolated. skill_evolution_safety.verify_*와 동일 로직."""
        ...

    def _publish(self, candidate_dir: str, skill_dir: str) -> None:
        """candidate → live atomic publish (shutil.move, 같은 파티션).

        publish 후 SkillEvolutionBus.on_skill_evolved를 호출하되, 시그니처는
        기존 default(`skill_dir=""`)를 유지하면서 Controller가 명시 전달한다.
        """
        ...
```

### 1.3 호출 사이트 매핑 표 (5행)

> **헤더 명확화** (라운드 2 비평 반영): 본 표는 **두 가지 매핑을 동시에 다룬다** — (a) 코드에 박힌 `TODO(Stage1)` 마커 회수 위치, (b) Controller로 교체될 호출 사이트. 두 매핑이 1:1이 아니다. 특히 **`dynamic_orchestrator.py:584-624`에는 TODO 마커가 부재**하지만(Stage 0가 hotfix만 적용하고 마커를 박지 않음 — F10), Controller 흡수 시 회수 필요. `fsa_loop.py:644`의 `bus.on_skill_evolved` 직접 호출도 마커 없이 Controller로 흡수.

| 호출 사이트 (실제 코드 라인) | 현재 코드 (Stage 0) | Stage 1 교체 | TODO 마커 | trigger 값 |
|-------|------------------|--------------|----------|-----------|
| `core/cross_verification.py:653-680` | `evolve_skill()` → 인라인 `verify_evolved_skill_sandbox` + `rollback_evolved_skill` + `bus.on_skill_evolved(skill_id, skill_dir, old_version, new_version, trigger)` | `result = controller.submit(skill_dir=, skill_id=, trigger="cross_verification", feedback=judgment.feedback, error_log=...)` 단일 호출. `bus.on_skill_evolved`는 Controller 내부 publish 분기에서 발화 | line 660 (있음) | `cross_verification` |
| `core/fsa_loop.py:580-664` `_try_evolve_failed_skill` 메인 흐름 | `evolve_skill()` (line 596) → `enrich_skill_metadata` (607) → `_verify_evolved_skill` 위임 (611) → `_rollback_skill` 위임 (613/624/663) → `_run_quality_gate` (616) → 3분기 분기 (619/627/660) → `bus.on_skill_evolved(... trigger="fsa_failure")` 직접 호출 (line 644) | **메인 흐름 전체를 `controller.submit()` 단일 호출로 교체**. Controller가 evolve+verify+gate+publish를 흡수. 위임 메서드 `_verify_evolved_skill`(700-709), `_rollback_skill`(711-719) 모두 제거 | line 703, 714 (위임 메서드만, 메인 호출엔 부재) | `fsa_failure` |
| `core/dynamic_orchestrator.py:584-624` `_try_evolve_from_patterns` | `evolve_skill()` (line 590) → 인라인 `verify_evolved_skill_sandbox` (599) + `rollback_evolved_skill` (601) + 별도 try block에서 `bus.on_skill_evolved(skill_id=, trigger=, old_version="", new_version="")` (line 611-616, skill_dir 누락) + `name = "(unknown)"` NameError 방지 (607) | `controller.submit()` 단일 호출. NameError 방지 패턴도 Controller 내부로 흡수 | **부재** (F10) — Stage 1 PR에서 회수 | `cross_verification_orchestrator` |
| `core/fsa_loop.py:700-719` `_verify_evolved_skill` / `_rollback_skill` 위임 메서드 | `skill_evolution_safety.verify_evolved_skill_sandbox(skill_py, skill_name, timeout_sec=15)` / `rollback_evolved_skill(skill_dir, skill_name)` | **메서드 자체 제거**. Controller 내부로 흡수. rollback 개념 제거 (candidate 폐기로 대체) — F1 | line 703, 714 | — |
| `core/skill_evolution_safety.py` 모듈 자체 | 84줄, `verify_evolved_skill_sandbox` + `rollback_evolved_skill` 2함수 | **모듈 deprecated** 후 1 sprint 내 제거. Controller가 동일 로직 흡수 | 헤더 line 8 | — |

**핵심 정합성 결정** (라운드 2 갱신): `bus.on_skill_evolved`는 이미 `skill_dir: str = ""` default를 보유 (`skill_evolution_bus.py:72`). 따라서 **"skill_dir 필수화"는 비호환 변경**이며 철회. Stage 1은 Optional 유지 + Controller가 publish 시 항상 명시 전달 + hook 측 시그니처(`hooks/skill_self_evolution.py:70-76`)는 비변경. 이로써 외부 호출자(미래 hooks, tools)와의 시그니처 충돌 방지.

### 1.4 영향 범위

- 신규: `core/evolution_types.py` (Sprint 1, EvolutionDecision + EvolutionResult), `core/skill_evolution_controller.py` (Sprint 2, Controller 본체)
- 제거: `core/skill_evolution_safety.py` (deprecated 단계 후 1 sprint 내 제거)
- 수정: `core/cross_verification.py`, `core/fsa_loop.py`(`_try_evolve_failed_skill` 메인 흐름 + 위임 메서드 2개), `core/dynamic_orchestrator.py`(`_try_evolve_from_patterns`)
- `core/skill_evolution_bus.py`: **비변경** (skill_dir default 유지 결정)
- `core/hooks/skill_self_evolution.py`: §3에서 `__init__(run_id=)` 추가 + §6.3에서 `_record_evolution_to_memory` 4종 분화 라우팅 + §7.2 trigger 분기 + 모듈 상수 frozenset 2개. **`on_skill_evolved` 메서드 시그니처는 비변경** (`skill_id, old_version, new_version, trigger` 유지)
- `af.spec` `hiddenimports`: `core.evolution_types`, `core.skill_evolution_controller`, `core.evolution_ledger` 추가, `core.skill_evolution_safety` 제거 (deprecated 후)
- `.gitignore`: `candidates/`, `data/evolution/` 추가

---

## 2. CandidateStagingArea (candidate dir 격리)

### 2.1 목적

`evolve_skill` (`skill_creator.py:682-790`)이 현재 live 파일을 직접 수정한다 (`open(src, "w")` line 754, `_write_meta` line 772). Stage 0는 `.bak` 백업 + rollback으로 봉쇄했지만, race 조건과 부분 복원 위험은 잔존. Stage 1은 **live 파일을 절대 수정하지 않는** 격리를 도입한다.

### 2.2 디렉토리 구조

```
skills/{skill_id}/                    ← live (publish 통과한 것만)
  skill.py
  SKILL.md
  meta.yaml
  meta.json

candidates/{skill_id}/{run_id}/       ← candidate (격리된 진화 작업 공간)
  {timestamp}_{trigger_hash}/
    skill.py                          ← LLM 진화 결과
    SKILL.md
    meta.yaml                         ← bumped 버전 포함
    meta.json
    .candidate.lock                   ← 동시 진화 방지

# Stage 0의 .bak은 candidate 격리 후 제거 (F3, F9 자연 해소)
```

### 2.3 publish API 시그니처

```python
# core/skill_evolution_controller.py 내 _publish() 메서드 본체

def _publish(self, candidate_dir: str, live_dir: str) -> None:
    """
    candidate → live atomic publish.

    원자성 보장:
      1. candidate_dir 검증 (필수 파일 존재, lock 파일 제거)
      2. shutil.move(candidate_dir/*, live_dir/*) — 같은 파티션 atomic rename
      3. candidate 부모 디렉토리 정리

    실패 시: candidate 폐기 + EvolutionResult.ERROR
    """
```

### 2.4 skill_creator.py 연동 지점

`skill_creator.evolve_skill(skill_dir, ...)` 시그니처를 **변경하지 않는다**. 대신 호출 측(Controller)이 `live_dir → candidate_dir` 매핑을 처리하고, `evolve_skill`에는 candidate_dir만 넘긴다. 즉:

```python
# Controller 내부
candidate_dir = self._create_candidate(live_dir)  # candidates/{skill_id}/{run_id}/{ts}/
ok = evolve_skill(skill_dir=candidate_dir, ...)   # 기존 evolve_skill은 그대로
# evolve_skill의 line 754 open(w)는 candidate_dir에만 쓰므로 비원자라도 무해 (F9)
```

이 접근의 장점:
- `skill_creator.py`의 비원자 쓰기 (F9, Stage 0 §8 Row12) 자연 해소 — 코드 변경 0줄
- `evolve_skill` 함수 시그니처 안정성 유지

단점:
- `evolve_skill` 내부의 `.bak` 생성 로직 (line 765-772 `meta_yaml.bak`)이 candidate에서도 실행되어 무의미한 .bak 파일 생성
- → §5에서 `meta.yaml.bak` 메커니즘 제거로 처리

### 2.5 영향 범위

- 신규: `candidates/` 디렉토리 (gitignore 추가)
- 신규 import: Controller에서 `core.skill_creator.evolve_skill` 호출
- 제거: `fsa_loop._cleanup_skill_baks` (`fsa_loop.py:721-730`) — candidate 격리되면 `.bak` 자체 없음

---

## 3. SkillSelfEvolutionHook `__init__(run_id=...)` 인터페이스 (F4)

### 3.1 목적

Stage 0는 `_record_evolution_to_memory`에서 `getattr(self, "_current_run_id", None) or "_skill_evolution"` sentinel을 사용한다 (`hooks/skill_self_evolution.py:168`). 이는 모든 진화 이벤트가 `runs/_skill_evolution/events.jsonl`에 누적되어 실제 run과 분리되는 임시 구조. Stage 1은 **hook 생성 시점에 run_id 주입**으로 정상화.

### 3.2 변경 시그니처

```python
# core/hooks/skill_self_evolution.py

class SkillSelfEvolutionHook:
    def __init__(
        self,
        check_interval: int = 10,
        max_enrich_per_cycle: int = 5,
        quality_threshold: float = 0.5,
        coding_engine: Optional[str] = None,
        run_id: Optional[str] = None,        # ← Stage 1 추가 (필수 권장)
    ) -> None:
        ...
        self._run_id = run_id    # 명시적 인스턴스 변수
```

### 3.3 `_record_evolution_to_memory` 수정

```python
# Before (Stage 0, line 168)
run_id = getattr(self, "_current_run_id", None) or "_skill_evolution"

# After (Stage 1)
run_id = self._run_id or "_skill_evolution"   # sentinel은 fallback으로만
```

### 3.4 호출자 (agent_runner) 수정 — grep 결과 명시

**검증된 사실** (라운드 2 비평 반영, `grep -n "_current_run_id" core/`):
- `core/hooks/skill_self_evolution.py:162` (docstring)
- `core/hooks/skill_self_evolution.py:168` (sentinel fallback)
- → **`_current_run_id` 속성을 외부에서 주입하는 코드는 코드베이스에 부재**. Stage 0 docstring이 "AgentRunner 등이 주입한다"고 명시했으나 실제 주입 코드는 없음. 따라서 Stage 0에서 sentinel fallback이 항상 사용되며, F4가 실질적으로 미작동 상태.

**Stage 1 신규 추가 작업**:

```python
# core/agent_runner.py — hook 등록 사이트 (정확한 라인은 구현 시 grep)

# 현재 (Stage 0)
hook = SkillSelfEvolutionHook(check_interval=10, ...)

# Stage 1
hook = SkillSelfEvolutionHook(check_interval=10, run_id=self.run_id, ...)
```

`hook._current_run_id = ...` 형태의 setter 패턴은 도입하지 않는다 (private 속성 외부 변경 antipattern). `__init__(run_id=)` 정식 인터페이스만 사용.

### 3.5 영향 범위

- 수정: `core/hooks/skill_self_evolution.py` — `__init__(run_id=)` 추가 + `_record_evolution_to_memory` sentinel 로직 변경
- 수정: `core/agent_runner.py` — hook 등록 사이트에서 `run_id=self.run_id` 명시 (Stage 1에서 신규 추가, 기존 코드 부재)
- 호환성: `run_id=None`이면 sentinel fallback. 기존 외부 호출자 비파괴.

---

## 4. EvolutionLedger (영속화) — **(1) Controller와 병렬 트랙**

### 4.1 목적

진화 이력을 **RunEventStore와 분리된** 영속 저장소에 기록한다. 진화는 run lifecycle을 넘어 누적되는 메타 자산(어떤 trigger에서 어떤 skill이 어떤 버전으로 진화했나, 최종 publish vs rejection 비율)이므로 별도 ledger가 필요.

### 4.2 RunEventStore와의 경계 (Stage 2 인터페이스 예약)

| 저장소 | 책임 | 수명 |
|-------|------|------|
| RunEventStore (`runs/{run_id}/events.jsonl`) | 단일 run의 모든 이벤트 (4종 분화 SKILL_EVOLVED 포함) | run-scoped |
| EvolutionLedger (`data/evolution/ledger.jsonl` 또는 SQLite) | 진화 결정 영구 이력 (skill_id × version × trigger × decision × cost × timestamp) | 영구 |

**중복 방지 정책**:
- RunEventStore는 **이벤트 발생 시 자동 기록** (4종 분화 SKILL_EVOLVED enum)
- EvolutionLedger는 **publish 결정 시점에만 기록** (REJECTED / DEFERRED는 별도 sub-store 또는 ledger 단일 jsonl의 decision 컬럼)
- 두 저장소 모두 append-only

**Stage 2 인터페이스 예약**: `run_event.py:21` `_size_warned_paths` 프로세스 전역 set 메커니즘이 Stage 2에서 rotation으로 deprecated될 때, EvolutionLedger의 `ledger.jsonl` 크기 정책은 **별도 결정**한다 (RunEventStore와 동일 정책 적용 X). 이유: ledger는 run을 넘어 누적되므로 rotation 기준이 다름.

### 4.3 클래스 stub

```python
# core/evolution_ledger.py — 신규

@dataclass
class LedgerEntry:
    skill_id: str
    old_version: str
    new_version: str
    trigger: str
    decision: EvolutionDecision  # PUBLISHED / REJECTED / DEFERRED / ERROR
    cost_tokens: int
    candidate_dir: str           # 사후 분석용
    rejection_reason: Optional[str]
    run_id: str                  # F4 정상화 후 실제 run_id 보장
    ts: str


class EvolutionLedger:
    def __init__(self, ledger_path: str = "data/evolution/ledger.jsonl") -> None: ...
    def append(self, entry: LedgerEntry) -> None: ...
    def list_for_skill(self, skill_id: str) -> list[LedgerEntry]: ...
    def list_for_run(self, run_id: str) -> list[LedgerEntry]: ...
    def stats(self) -> dict:
        """publish_rate, rejection_breakdown, total_cost 등 집계."""
```

### 4.4 병렬 트랙 결정 (라운드 2 채택)

EvolutionLedger 구현이 (1) Controller의 선행 필수가 되면, Ledger 미구현 동안 Controller 작업이 블록된다. 따라서:

- (1) Controller는 `ledger: Optional[EvolutionLedger] = None`으로 받는다
- Ledger가 None이면 ledger.append() 호출은 no-op
- Ledger 구현은 별도 PR / 별도 작업자가 병렬 진행 가능
- 통합 테스트는 Ledger 구현 완료 후 한 번에 검증

### 4.5 영향 범위

- 신규: `core/evolution_ledger.py`, `data/evolution/` 디렉토리
- 의존: Controller (선택적)
- gitignore: `data/evolution/` 추가 (런타임 산출물)

---

## 5. `meta.yaml.bak` 메커니즘 제거 (F3)

### 5.1 현재 위치

- `core/skill_creator.py:765-772`: action 타입 skill에 한해 `meta.yaml` → `meta.yaml.bak` 백업
- `core/skill_evolution_safety.py:69`: rollback 시 `meta.yaml.bak` 복원 대상에 포함
- `core/fsa_loop.py:721-730`: `_cleanup_skill_baks`가 gate PASS 후 .bak 정리

### 5.2 제거 절차

candidate dir 격리(§2)가 도입되면 live `meta.yaml`이 진화 중 변경되지 않으므로 백업 자체가 불필요.

| 위치 | 제거 |
|------|-----|
| `skill_creator.py:765-772` | `if skill_type == "action": ... shutil.copy2(...meta.yaml.bak)` 블록 삭제 |
| `skill_evolution_safety.py:69` | `meta.yaml`, `meta.json` 항목을 `rollback_evolved_skill`의 복원 대상에서 제거 (모듈 자체가 §1에서 deprecated되므로 자연 해소) |
| `fsa_loop.py:721-730` `_cleanup_skill_baks` | 메서드 자체 삭제 |
| `fsa_loop.py` gate PASS 분기 (`fsa_loop.py:649` 부근) | `self._cleanup_skill_baks(skill_dir)` 호출 제거 |

### 5.3 검증

기존 테스트 `tests/test_skill_evolution_safety.py` 중 `meta.yaml.bak` 복원 케이스(약 7건 중 2건)는 candidate dir 격리 검증으로 대체.

---

## 6. RunEventType 4종 분화 (Row7, F5)

### 6.1 enum 변경

```python
# core/events/run_event.py:42

# Before
class RunEventType(str, Enum):
    ...
    SKILL_EVOLVED = "skill_evolved"

# After (Stage 1)
class RunEventType(str, Enum):
    ...
    METADATA_ENRICHED = "metadata_enriched"            # bulk_enrich → on_bulk_enriched
    EVOLUTION_REQUESTED = "evolution_requested"        # Controller.submit() 진입
    EVOLUTION_PUBLISHED = "evolution_published"        # candidate → live publish 성공
    EVOLUTION_ROLLED_BACK = "evolution_rolled_back"    # REJECTED / DEFERRED / ERROR (candidate 폐기)
    # SKILL_EVOLVED = "skill_evolved"  ← deprecated (호환성 위해 1 sprint 유지 후 제거)
```

### 6.2 EvolutionLedger와 독립 진행 (라운드 2 채택)

af-critic 라운드 2 평가: "Row7 분화는 enum 추가 + `_record_evolution_to_memory` 라우팅 분기 수정으로 독립 처리 가능. EvolutionLedger 미존재 상태에서도 분화 자체는 가능". 따라서 (4) Ledger와 (6) 분화는 병렬 가능 항목.

### 6.3 라우팅 분기

**trigger 문자열 whitelist** (라운드 2 비평 반영): `bus.py:138`은 `trigger="metadata_enriched"` (과거형). `startswith` 매칭은 의도 불명이므로 명시적 whitelist 사용.

**정의 위치** (라운드 3 N1 명시): 본 frozenset 2개는 `core/hooks/skill_self_evolution.py` **모듈 상수**로 정의 (클래스 외부, 모듈 import 시점에 고정). §7.2 `on_skill_evolved` 분기와 §6.3 `_record_evolution_to_memory` 라우팅이 동일 모듈에서 import 없이 참조.

```python
# core/hooks/skill_self_evolution.py 모듈 상수 (클래스 외부)

_METADATA_TRIGGERS = frozenset({"metadata_enriched"})  # bus.py:138와 일치
_CODE_EVOLUTION_TRIGGERS = frozenset({
    "fsa_failure",                       # fsa_loop.py:649
    "cross_verification",                # cross_verification.py:679
    "cross_verification_orchestrator",   # dynamic_orchestrator.py:613
})

# core/hooks/skill_self_evolution.py:153-181 _record_evolution_to_memory

# Stage 1 변경: trigger와 decision으로 4종 분화
if trigger in _METADATA_TRIGGERS:
    event_type = RunEventType.METADATA_ENRICHED
elif decision == EvolutionDecision.PUBLISHED:
    event_type = RunEventType.EVOLUTION_PUBLISHED
elif decision == EvolutionDecision.DEFERRED:
    # DEFERRED는 게이트 자체 미실행 = 결정 보류. ROLLED_BACK과 의미 분리.
    # RunEventType에 EVOLUTION_DEFERRED 추가 또는 ROLLED_BACK + payload.reason="deferred"
    event_type = RunEventType.EVOLUTION_ROLLED_BACK  # payload.reason="deferred"로 구분
elif decision in (EvolutionDecision.REJECTED, EvolutionDecision.ERROR):
    event_type = RunEventType.EVOLUTION_ROLLED_BACK
else:
    event_type = RunEventType.EVOLUTION_REQUESTED  # 진입 시점 기록
```

**EvolutionDecision.DEFERRED 라우팅 결정** (라운드 2 채택): DEFERRED는 의미상 ROLLED_BACK과 다름(게이트 미신뢰 vs 명시적 폐기)이지만 RunEventType enum 4종을 5종으로 늘리면 외부 소비자 영향이 커진다. **타협: payload에 `reason="deferred"` 명시**하여 사후 분석 시 구분 가능. EvolutionLedger는 EvolutionDecision 원본을 영속하므로 영속 레벨에선 손실 없음.

### 6.4 외부 소비자 영향

- `RunEvent.from_dict` (`run_event.py:70-87`)는 ValueError catch + raw string fallback 보유. enum 누락 시 graceful → 외부 소비자 비파괴 (Stage 0 §10 검증 완료)
- `SKILL_EVOLVED` 제거는 1 sprint deprecated 후

---

## 7. Trigger 분기 처리 (Row9, F6)

### 7.1 현재 동작

`SkillSelfEvolutionHook.on_skill_evolved` (`hooks/skill_self_evolution.py:70-82`)는 trigger 종류와 무관하게 단순히 logger.info + `_record_evolution_to_memory`만 실행. 즉:

- `trigger="metadata_enrich"` (메타 보강) → 단순 기록
- `trigger="cross_verification"` (코드 진화) → 단순 기록
- `trigger="cross_verification_orchestrator"` (orchestrator 진화) → 단순 기록

### 7.2 Stage 1 분기

§6.3에서 도입한 frozenset whitelist를 동일 함수 내에서 일관 사용 (라운드 3 N1 수정).

```python
def on_skill_evolved(self, skill_id, old_version, new_version, trigger, decision=None) -> None:
    if trigger in _METADATA_TRIGGERS:
        # 메타 보강은 enricher가 즉시 캐시 무효화 → 추가 동작 불필요
        logger.info("[SelfEvolution] 메타 보강: %s", skill_id)
    elif trigger in _CODE_EVOLUTION_TRIGGERS:
        # 코드 진화는 ledger 기록 + memory consolidation hint
        logger.info("[SelfEvolution] 코드 진화: %s (%s→%s)", skill_id, old_version, new_version)
        self._notify_consolidation(skill_id)  # 신규 메서드
    else:
        logger.warning("[SelfEvolution] 알 수 없는 trigger: %s (skill=%s)", trigger, skill_id)

    self._record_evolution_to_memory(skill_id, old_version, new_version, trigger, decision)
```

### 7.3 Stage 3와의 경계

trigger 문자열 분기 자체는 Stage 1. Stage 3는 **trigger를 어떻게 결정하는지** (yaml 정책)를 다룸. 즉 본 §7은 "trigger 받은 후 처리", Stage 3는 "trigger 발생 결정". 분리 안전.

### 7.4 영향 범위

- 수정: `core/hooks/skill_self_evolution.py`
- 신규 메서드: `_notify_consolidation` (memory_consolidation hook으로 진화 신호 전파)

---

## 8. bulk_enrich 호출 정합성 (Row13, F7)

### 8.1 현재 동작 검증 (설계서 작성 시점 grep 결과 못박음)

`core/hooks/skill_self_evolution.py:131-139`:

```python
enriched_ids = bulk_enrich_all_skills(...)
if enriched_ids:
    evo_bus = SkillEvolutionBus.get_instance()
    evo_bus.on_bulk_enriched(enriched_ids)   # ← 명시적 호출 OK
```

`core/skill_evolution_bus.py:115-141` `on_bulk_enriched`:
- `_step1_reload_registry` → `_step2_invalidate_dep_graph` → `_step3_recompute_embeddings` → `_step4_clear_relevance_caches` → `_step5_evict_module_cache` (per skill_id) → `_step6_evict_loader_cache` → `_step7_broadcast(trigger="metadata_enriched")` (per skill_id)
- 즉 단일 진화의 step1~7과 동일한 캐시 체인 + step7 broadcast 포함.

### 8.2 결론 (라운드 2 비평 반영)

**검증 완료. Sprint 4 별도 작업 불필요.** 다음 사실이 확인됨:

1. `bulk_enrich_all_skills` 호출 → `on_bulk_enriched(enriched_ids)` 명시 호출 (`hooks/skill_self_evolution.py:131-139`)
2. `on_bulk_enriched` 내부: step1~6 캐시 체인 + step7 broadcast (`bus.py:115-141`)
3. broadcast trigger 값 = `"metadata_enriched"` (`bus.py:138`)
4. §6.3 `_METADATA_TRIGGERS` whitelist와 일치 → 라우팅 정합

**결론**: 본 항목(F7)은 설계서 작성 시점 검증으로 종료. Stage 1 코드 변경 0줄. 다만 **회귀 방지 테스트 필요** — §12.1에 `test_bulk_enrich_trigger_routing.py` 추가.

### 8.3 회귀 방지 (장래 변경 차단)

`bulk_enrich_all_skills` 또는 `on_bulk_enriched` 시그니처 변경 시 본 §8.1의 trigger 문자열 일관성이 깨질 수 있음. §12.1 신규 테스트가 다음을 강제:

- `_METADATA_TRIGGERS` whitelist에 `"metadata_enriched"` 포함
- `on_bulk_enriched` 호출 시 step7 broadcast의 trigger 인자가 whitelist 값
- enricher가 향후 code 보강을 추가하면 별도 trigger 값 + whitelist 추가 필요

---

## 9. RunBudget 진화 비용 연동 (Row14, F8)

### 9.1 현재 동작

`evolve_skill` (`skill_creator.py:682`)이 `generate_skill_content` 호출(`skill_creator.py:742`)로 LLM에 토큰을 소비하지만, **이 비용이 RunBudget에 가산되지 않음**. 즉 진화는 사실상 무한 예산.

### 9.2 Stage 1 통합 — 실제 RunBudget API 사용

**라운드 2 CRITICAL 수정**: 이전 의사코드의 `can_afford()` / `consume(source=, run_id=)` 메서드는 **`core/run_budget.py`에 존재하지 않는다**. 실제 API:

| 메서드 | 시그니처 | 동작 |
|-------|---------|-----|
| `record(text: str)` | LLM 호출 결과 텍스트를 직접 받음 | 4-char ≈ 1-token 휴리스틱으로 `consumed` 갱신. 80%/100% 자동 마일스톤 emit |
| `is_exhausted()` | `→ bool` | `stopped` 플래그 반환 (100% 도달 시 True) |
| `remaining()` | `→ int` | `max_tokens - consumed` (max_tokens=0 시 999_999_999) |
| `_emit_cost_event(milestone)` | 내부 호출 | COST_INCURRED RunEvent 자동 emit (run_id 인스턴스 속성 사용) |

전역 함수: `set_run_budget(max_tokens, *, run_id, project_id)`, `get_run_budget()`. **`source=` 인자 없음** — RunBudget 인스턴스의 `run_id`/`project_id` 속성이 자동으로 RunEvent에 박힘.

```python
class SelfEvolutionController:
    def submit(self, *, skill_dir, skill_id, trigger, ...) -> EvolutionResult:
        # 1. 진입 가드 — 이미 소진됐으면 즉시 REJECTED
        if self._budget and self._budget.is_exhausted():
            return EvolutionResult(
                skill_id=skill_id,
                decision=EvolutionDecision.REJECTED,
                candidate_dir=None,
                new_version=None,
                rejection_reason="budget_exhausted_pre_call",
                cost_tokens=0,
            )

        # 2. (선택) 예상 비용 사전 점검 — remaining이 너무 작으면 REJECTED
        ESTIMATED_COST = 2000  # 진화 1회 평균 (튜닝 가능)
        if self._budget and self._budget.remaining() < ESTIMATED_COST:
            return EvolutionResult(
                skill_id=skill_id,
                decision=EvolutionDecision.REJECTED,
                candidate_dir=None,
                new_version=None,
                rejection_reason="budget_insufficient_remaining",
                cost_tokens=0,
            )

        # 3. LLM 호출 전 consumed 캡처 (cost_tokens 산정용, 라운드 3 N3 수정)
        pre_consumed = self._budget.consumed if self._budget else 0

        # 4. LLM 호출 (skill_creator.evolve_skill 내부에서 generate_skill_content)
        candidate_dir = self._create_candidate(skill_dir)
        # ... evolve_skill(candidate_dir, ...) 호출 ...

        # 5. 비용 기록 — record(text)는 4-char ≈ 1-token 휴리스틱
        # (skill_creator.evolve_skill은 bool 반환이라 LLM 응답 텍스트를 직접 못 받음)
        if self._budget:
            from pathlib import Path
            try:
                evolved_content = Path(candidate_dir, "skill.py").read_text(encoding="utf-8")
                self._budget.record(evolved_content)
                # record() 내부에서 80%/100% 마일스톤 자동 emit (COST_INCURRED RunEvent)
            except (OSError, IOError) as e:
                # candidate가 비었거나 읽기 실패 — 비용 추정 불가, 0으로 처리
                logger.warning("[Controller] candidate skill.py 읽기 실패: %s", e)

        # 6. 결과 반환 — cost_tokens는 record() 호출 전후 차이로 산정
        cost_tokens = (self._budget.consumed - pre_consumed) if self._budget else 0
        return EvolutionResult(..., cost_tokens=cost_tokens, ...)
```

### 9.2.1 한계 (라운드 3 N2 명시)

**candidate `skill.py` 크기 ≠ 실제 LLM 토큰 비용**:
- 실제 LLM 비용 = 입력 프롬프트(피드백 + 에러 로그 + 기존 콘텐츠) + 응답
- 본 §9.2의 `record(evolved_content)`는 **응답 일부**(`skill.py` 출력만, `meta.yaml`/`meta.json` 미포함)만 추정
- 입력 프롬프트 비용은 **누락**

**누락 영향**: 진화 1회 실측 비용이 4-char≈1-token 휴리스틱 측정값보다 실제로는 1.5~3배 (입력 프롬프트 길이에 비례). RunBudget 80%/100% 마일스톤 발화가 실제 소진보다 늦게 발생.

**Stage 1 한정 결정**: 본 한계를 limitation으로 명시하고 Stage 1 이후로 미룸. 정확한 비용 측정은 `skill_creator.generate_skill_content` 시그니처를 변경(반환값에 input/output 텍스트 별도 포함)해야 하는데, 이는 `skill_creator` 내부 리팩토링이 필요. Stage 2 또는 별도 작업.

**임시 완화**: `ESTIMATED_COST = 2000`을 보수적으로 잡아 사전 점검(§9.2 step 2)이 실제 소진보다 일찍 차단하도록 함.

### 9.3 RunBudget 신규 메서드 도입 여부

- **도입하지 않음**. 기존 `record()` + `is_exhausted()` + `remaining()` 조합으로 §9.2의 4단계 흐름 구현 가능
- `can_afford(estimated)` 같은 헬퍼는 Controller 내부 private 메서드(`self._can_afford(cost)`)로 구현. RunBudget 자체는 비변경

### 9.4 영향 범위

- 수정: `core/skill_evolution_controller.py` (신규 파일이므로 처음부터 RunBudget 통합)
- `core/skill_creator.evolve_skill`: 시그니견 비변경, 호출 측(Controller)이 record() 처리
- `core/run_budget.py`: **비변경** (라운드 2 검증 완료)

---

## 10. 종속성 그래프 (병렬 트랙)

### 10.1 Cut points

```
(3) Hook __init__(run_id=)        ← 독립 가능 (sentinel fallback 유지)
       ↓
(1) SelfEvolutionController       ← (3) 후, (4)와 병렬
(6) RunEventType 4종 분화         ← (1)과 병렬 가능 (라운드 2 합의)
       ↓
(2) candidate dir 격리            ← (1) 의존
       ↓
(5) meta.yaml.bak 제거            ← (2) 후만 안전
       ↓
(7) trigger 분기                  ← (1) + (6) 후
(8) bulk_enrich 정합성            ← (7) 후 (분기 추가 case)
(9) RunBudget 연동                ← (1) 내부에서 처리

(4) EvolutionLedger               ← 병렬 트랙 (1)과 독립
```

### 10.2 권고 작업 순서 (라운드 2 갱신)

| Sprint | 항목 | 비고 |
|--------|------|------|
| Sprint 1 | (3) Hook `__init__(run_id=)` + agent_runner 주입 + (6) RunEventType 4종 분화 + (7) trigger 분기 routing + (8) bulk_enrich whitelist 회귀 테스트 | 모두 독립 또는 (6)→(7) 단방향. (8)은 §8.2에서 검증 완료, 회귀 테스트만 |
| Sprint 2 | (1) Controller 본체 + (9) RunBudget 통합. 동시에 (4) Ledger 별도 PR | (9)는 (1) 내부에서 처리 = 동일 PR. (4)는 병렬 트랙 |
| Sprint 3 | (2) candidate 격리 + (5) `meta.yaml.bak` 제거 + (4) Ledger 통합 테스트 | (5)는 (2) PR 후만 안전 — 같은 Sprint 내 PR 순서 강제 |

**주요 변경** (라운드 2 비평 반영):
- 이전 Sprint 4 (7)+(8) → Sprint 1로 앞당김. 종속성 그래프상 (7)은 (1)+(6) 후 가능하나 (1)이 Sprint 2이므로 (7)은 원래 Sprint 2 이후 가능
- (8) bulk_enrich는 §8.2에서 grep 검증 완료 → Stage 1 코드 변경 0줄. 회귀 방지 테스트만 Sprint 1
- 총 Sprint 4 → 3으로 축소

**(7) Sprint 1 배치를 위한 구조 결정** (라운드 3 N2 수정):

`_record_evolution_to_memory`의 라우팅 분기(§6.3)가 `decision: EvolutionDecision`을 받으려면 (7)이 (1) Controller 모듈을 import해야 한다. 이 import 의존이 (7)을 Sprint 2 이후로 묶는 원인.

**해결**: `EvolutionDecision` enum + `EvolutionResult` dataclass를 별도 모듈 `core/evolution_types.py`로 분리. `SelfEvolutionController`(`skill_evolution_controller.py`)는 이 모듈을 import해서 사용. hook 모듈도 같은 evolution_types를 import.

```
core/evolution_types.py            ← Sprint 1 (가벼움, types만)
  ├── EvolutionDecision (Enum)
  ├── EvolutionResult (dataclass)
  └── (관련 type alias)

core/skill_evolution_controller.py ← Sprint 2 (Controller 본체)
  └── from core.evolution_types import EvolutionDecision, EvolutionResult

core/hooks/skill_self_evolution.py ← Sprint 1에서 evolution_types만 import
  └── from core.evolution_types import EvolutionDecision  # decision 파라미터용
```

이로써 (7)의 §6.3 라우팅이 (1) Controller 본체 없이도 `evolution_types` import만으로 가능 → Sprint 1 배치 정합성 회복. §10.1 그래프 (7) ← (1)+(6) 의존성은 "Controller 본체"가 아닌 "Decision enum 정의"에 한정되며, enum이 별도 경량 모듈로 분리되므로 (1) Controller PR 이전에 (7) 머지 가능.

각 Sprint는 단독 mergeable. 의존성 없는 트랙은 병렬 진행.

---

## 11. Stage 6 분리 리스크 (publish 게이트 보호망 명시)

### 11.1 잠재 위험

`core/fsa_loop.py:670-698` `_detect_failed_skill_dir`는 에러 로그 텍스트에서 실패 skill 디렉토리를 추출하는 휴리스틱. 잘못 추출하면 무관한 skill을 진화 대상으로 식별. Stage 6에서 `skill_id` provenance로 정식 해결 예정.

### 11.2 publish 게이트 보호망 (Stage 1 차단 효과)

candidate dir 격리(§2) 도입 후 흐름:

```
1. _detect_failed_skill_dir이 잘못된 skill_X를 식별
2. Controller.submit(skill_id=skill_X, ...)
3. candidate dir 생성 → evolve_skill → sandbox 검증
4-a. 검증 통과 시: candidate publish → live skill_X 변경 (오탐 미차단 ❌)
4-b. 검증 실패 시: candidate 폐기 → live skill_X 무영향 (오탐 차단 ✅)
```

→ **publish 게이트는 잘못된 skill 격리를 sandbox 실패 시에만 차단**. sandbox 통과한 잘못된 진화는 live에 적용된다. 따라서 Stage 6 분리는 안전하지 않은 "효용 약화"가 아니라 "위험 잔존".

### 11.3 완화 (Stage 1 한정)

- Controller `submit()`이 받는 `skill_id`가 호출자 책임이라는 점을 docstring에 명시
- 잘못된 skill_id 식별로 인한 진화는 EvolutionLedger에 기록되어 사후 분석 가능 (`stats()` 결과로 진화 빈도 이상 감지)
- Stage 6 작업 우선순위를 명시 (Sprint 5 이내 권고)

### 11.4 라운드 2 의견 차이 처리

af-cross-review/Codex: "publish 게이트가 보호망이므로 효용 약화 없음" → 부분 정확 (sandbox 실패 시만)
af-critic 라운드 2: "publish 게이트가 보호망" → 채택 (sandbox 통과한 오탐은 별개 위험)

→ 본 §11은 **양쪽을 통합**: publish 게이트는 sandbox 실패에 한해 차단. sandbox 통과한 오탐은 Stage 6에서 정식 해결.

---

## 12. 검증 / 테스트 계획

### 12.1 신규 테스트 파일

| 파일 | 커버 항목 | F번호 |
|------|----------|-------|
| `tests/test_self_evolution_controller.py` | submit 4종 결과(PUBLISHED/REJECTED/DEFERRED/ERROR), candidate dir 생성/폐기, sandbox 검증 위임, publish atomicity | F1, F2 |
| `tests/test_candidate_staging.py` | candidate dir 동시성(.candidate.lock), live 미수정 보장, publish 후 candidate 정리, `skill_creator.py:754` 비원자 쓰기 자연 해소 검증 | F1, F3, F9 |
| `tests/test_evolution_ledger.py` | LedgerEntry 영속, list_for_skill/list_for_run 인덱싱, stats 집계, `Optional[Ledger]=None` no-op 보장 | F4 (병렬 트랙) |
| `tests/test_run_event_evolution_split.py` | 4종 분화 enum 라우팅, DEFERRED → ROLLED_BACK + payload.reason="deferred", deprecated `SKILL_EVOLVED` 호환성 | F5 |
| `tests/test_skill_self_evolution_hook_runid.py` | `__init__(run_id=)` 정상화, sentinel fallback, agent_runner 주입 통합 | F4 (run_id) |
| `tests/test_evolution_budget.py` | RunBudget `record()` 가산, `is_exhausted()` 시 즉시 REJECTED, `remaining() < ESTIMATED_COST` 시 budget_insufficient_remaining | F8 |
| `tests/test_skill_evolution_trigger_routing.py` | trigger 4종(`fsa_failure` / `cross_verification` / `cross_verification_orchestrator` / `metadata_enriched`) → §6.3 라우팅 검증 + §7.2 분기 처리 | F6 (라운드 2 신규) |
| `tests/test_bulk_enrich_trigger_routing.py` | `on_bulk_enriched` step7 broadcast가 `"metadata_enriched"` trigger 사용 보장, `_METADATA_TRIGGERS` whitelist 일치, enricher 시그니처 변경 시 회귀 차단 | F7 (라운드 2 신규) |

### 12.2 기존 테스트 마이그레이션

- `tests/test_skill_evolution_safety.py` (Stage 0, 7건): meta.yaml.bak 복원 케이스 2건 → candidate 격리 검증으로 대체. quick_guard / run_isolated 호출 검증 5건 → Controller 내부로 이동
- `tests/test_evolution_hotfix_h6.py` (Stage 0): SKILL_EVOLVED enum → 4종 분화 검증으로 확장

### 12.3 통합 검증

- `python build_exe.py` 후 frozen 환경에서 `core.skill_evolution_controller`, `core.evolution_ledger` import 검증
- `af.spec` `hiddenimports` 갱신 확인
- `python3 scripts/review_gate.py --debug`로 Review-Gate 통과 확인
- 호출 사이트 4개(§1.3 표) 각각의 통합 테스트: cross_verification → Controller, fsa_loop → Controller, dynamic_orchestrator → Controller, skill_evolution_safety 모듈 deprecated 후 import 부재 확인

---

## 13. 리스크 + 완화

| 리스크 | 영향 | 완화 |
|-------|------|------|
| EvolutionLedger 미구현 시 Controller가 ledger 호출 → AttributeError | 중 | `ledger: Optional[EvolutionLedger] = None`으로 받고 None 체크 (라운드 2 채택) |
| candidate dir 디스크 점유 | 중 | publish/reject 후 즉시 정리. EvolutionLedger에 candidate_dir 기록되어 사후 정리 가능 |
| `RunEventType.SKILL_EVOLVED` 외부 소비자 누락 | 낮 | `from_dict`의 ValueError catch + raw string fallback (Stage 0 §10 검증 완료). 1 sprint deprecated 유지 |
| `skill_evolution_safety.py` deprecated 후 외부 호출자 | 낮 | grep 결과 호출자 3개(cross_verification, fsa_loop, dynamic_orchestrator) 모두 본 문서 §1.3에서 교체 명시 |
| `bulk_enrich_all_skills` 내부 명세 불일치 (§8) | 낮 | §8.2에서 grep 검증 완료 (코드 변경 0). 회귀 방지 테스트만 Sprint 1 |
| Stage 6 sandbox 통과 오탐 위험 (§11) | 중 | EvolutionLedger.stats()로 이상 빈도 감지. Stage 6 Sprint 5 이내 권고 |
| Stage 2 RunEventStore rotation이 EvolutionLedger 정책에 영향 | 낮 | §4.2에서 두 저장소 정책 분리 명시. Stage 2 작업 시 본 §4.2 재참조 |
| **(라운드 2 신규) `bus.on_skill_evolved` skill_dir 시그니처 비호환 변경 위험** | 낮 | "필수화" 결정 철회 → Optional 유지. Controller가 항상 명시 전달하면서 외부 호출자 비파괴 |
| **(라운드 2 신규) `_current_run_id` 외부 주입 부재** (현재 sentinel fallback이 항상 사용) | 중 | §3.4에서 grep 결과 명시 + Stage 1 Sprint 1에서 agent_runner 신규 추가 |
| **(라운드 2 신규) RunBudget API 의사코드 오류** | 낮 | §9.2에서 실제 API(`record`/`is_exhausted`/`remaining`)로 재작성. 신규 메서드 도입 X |
| **(라운드 2 신규) `EvolutionDecision.DEFERRED` 의미 손실** | 낮 | RunEventType은 4종 유지 + payload.reason="deferred"로 구분. EvolutionLedger는 원본 enum 영속 |

---

## 14. 검증 후 진행

본 메모 작성 후 즉시:

1. **af-critic + af-cross-review 2개 병렬 실행** (단일 설계문서 기준, CLAUDE.md 룰)
2. BLOCK 판정 시 본 메모 수정 후 재검증
3. ACCEPT 시 NEXT_STEPS.md "다음 후보"에서 "Stage-1 설계 + 구현"을 분리:
   - Stage-1 설계: ✅ 완료 (본 문서 머지 후)
   - Stage-1 구현: Sprint 1~4 (§10.2 권고 순서)
4. Master_Blueprint.md §0/§3/§12 업데이트 (본 문서 머지 커밋과 동일 커밋)
5. `git commit` + `git push`
