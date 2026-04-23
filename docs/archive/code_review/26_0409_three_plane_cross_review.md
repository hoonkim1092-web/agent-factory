# 3-Plane 통합 설계 교차 검증 보고서

**작성일**: 2026-04-09
**대상 문서**: `docs/2026-04-09-three-plane-integration-design.md`
**현재 구현율**: ~5% (report_path 필드만 구현됨)

---

## 검증 요약

- **Codex 피드백**: 7개 항목
  - 수용(ACCEPT): 5개
  - 기각(REJECT): 1개
  - 보류(HOLD): 1개
- **Claude 자체 발견**: 3개 추가 (ACCEPT)
- **총 수정 필요**: 8개

---

## 상세 판정

### 1. [ACCEPT / Critical] SkillRegistry.instance() 메서드 미존재

- **Codex 원문**: "설계 문서가 `SkillRegistry.instance()`를 호출하지만 실제 SkillRegistry에는 `instance()` 메서드가 없다"
- **대상 코드**: 설계 문서 섹션 3.3 (line 131) `self.registry = registry or SkillRegistry.instance()`
- **판정 근거**: `core/skill_registry.py`의 `SkillRegistry`는 `__new__` 기반 싱글톤이며 `instance()` 클래스 메서드가 없다. 프로젝트 전체에서 `get_global_registry()` 함수를 사용 (fsa_loop.py:292, skill_autodiscover.py:9, skill_evolution_bus.py:139 등 20개 이상).
- **수정 제안**: `SkillRegistry.instance()` → `get_global_registry()`로 변경. import도 `from core.skill_registry import get_global_registry`로 수정.

### 2. [ACCEPT / Critical] EpisodeRecord 필드 구조 불일치

- **Codex 원문**: "설계의 EpisodeRecord 생성자가 `failure_patterns`, `skill_evolved`, `gate_result`, `cycle_count` 필드를 사용하지만 실제 모델에 존재하지 않는다"
- **대상 코드**: 설계 문서 섹션 3.5 (line 228-239) vs `core/memory_system/models.py:137-167`
- **판정 근거**: 실제 `EpisodeRecord` 필드는 `episode_id, run_id, project_id, agent_name, task_input, actions, outcome, error_info, duration_ms, created_at, causal_links, metadata`. 설계에서 직접 필드로 쓴 4개는 모두 존재하지 않으며, 이대로 구현하면 `TypeError: __init__() got an unexpected keyword argument` 발생.
- **수정 제안**: 커스텀 필드는 `metadata` dict 안에 넣어야 한다:
  ```python
  episode = EpisodeRecord(
      task_input=task_input,
      outcome="success" if result.get("ok") else "failure",
      metadata={
          "failure_patterns": result.get("failure_patterns", []),
          "skill_evolved": evolved_skill_name or "",
          "gate_result": gate_result.pass_rate if gate_result else 0.0,
          "cycle_count": cycle,
      },
  )
  ```

### 3. [ACCEPT / High] skill_path vs skill_dir 혼동

- **Codex 원문**: "`SkillEvalHarness().evaluate(skill_path)` 호출 시 skill_path가 디렉토리인지 파일인지 혼동"
- **대상 코드**: 설계 문서 섹션 3.3 (line 153) vs `core/skill_eval_harness.py:117-128`
- **판정 근거**: `evaluate()`는 **파일 경로**(예: `.../skill.py`)를 기대. 반면 설계에서는 디렉토리를 넘기는 것으로 작성됨. `spec_from_file_location`에서 디렉토리를 파일로 로딩 시도해 크래시 가능.
- **수정 제안**: `SkillQualityGate.validate()` 내부에서 변환:
  ```python
  skill_py = os.path.join(skill_path, "skill.py")
  report = self.harness.evaluate(skill_py, baseline_skill_path=baseline_skill_path)
  ```

### 4. [ACCEPT / High] UnifiedMemoryFacade.get_instance() 반환값 오해

- **Codex 원문**: "`get_instance()`는 None을 반환하지 않고, 초기화되지 않은 stub facade를 반환한다"
- **대상 코드**: 설계 문서 섹션 4.4 (line 344) `if not facade: return {}` vs `core/memory_system/facade.py:38-45`
- **판정 근거**: `get_instance()`는 항상 truthy 객체를 반환. `if not facade:` 체크는 절대 빈 dict 분기에 진입하지 않음. 대신 `_ensure_initialised()`에서 `RuntimeError` 발생.
- **수정 제안**: `if not facade._initialised: return {}` 조건으로 변경

### 5. [ACCEPT / Medium] report_path 필드는 이미 구현됨

- **대상 코드**: 설계 문서 섹션 7 "순서 6: report_path 필드 ~5줄" vs `core/skill_eval_harness.py:92,172`
- **판정 근거**: `SkillEvalReport`에 `report_path: str = ""`가 이미 존재하고 `evaluate()`에서 설정됨. 이미 완료된 작업을 다시 할당.
- **수정 제안**: 구현 순서에서 항목 6을 "이미 완료"로 표시. 리넘버링.

### 6. [REJECT] NormalizedRequest 필드 추가의 호환성 문제

- **Codex 원문**: "`NormalizedRequest`에 `memory_context` 필드 추가 시 `to_dict()` 직렬화에 영향"
- **기각 근거**: 설계가 **의도적으로 변경하는 부분**. `@dataclass` 필드 추가는 의도된 것이며, `MaintenancePipeline` 호출자는 `getattr`/`dict.get` 패턴이므로 기존 로직 깨지지 않음. 단, `to_dict()` 업데이트 누락은 별도 항목(9번)에서 다룸.

### 7. [HOLD] _run_async_safe() timeout 10초의 충분성

- **Codex 원문**: "10초 하드코딩 timeout이 search_semantic에 충분하지 않을 수 있다"
- **보류 근거**: timeout 제어 지점이 `_run_async_safe`(10초)와 `search_semantic` 내부의 `search_timeout` 두 곳에 있어 어느 것이 먼저 트리거될지 불명확. 설계에서 3초 timeout을 언급했지만 설정 코드 미제시.
- **판단 필요**: memory config의 `search_timeout` 기본값과 실제 지연 시간 확인 후 결정.

---

## Claude 자체 발견 (Codex 미지적)

### 8. [ACCEPT / High] fsa_loop.py 변경이 SkillEvolutionBus 패턴과 충돌

- **대상 코드**: 설계 문서 섹션 3.4 (line 194-216) vs `core/fsa_loop.py:138-208`
- **판정 근거**: 현재 `_try_evolve_failed_skill()`는 `evolve_skill()` 성공 후 `SkillEvolutionBus.on_skill_evolved()`를 호출하여 캐시 무효화 + 이벤트 브로드캐스트 수행. 설계에서는 gate 삽입 후 `_hot_reload_registry()`만 호출하고 `SkillEvolutionBus` 호출이 완전히 빠짐. 진화 이벤트 미브로드캐스트로 다른 구성 요소 갱신 불가 regression 발생.
- **수정 제안**: gate 통과 후 `SkillEvolutionBus.on_skill_evolved()` 호출을 유지해야 함.

### 9. [ACCEPT / Medium] to_dict() 업데이트 누락

- **대상 코드**: 설계 문서 섹션 4.3 (line 296-316)
- **판정 근거**: `NormalizedRequest`의 `to_dict()`는 수동 dict 구성 방식. `memory_context` 필드 추가 시 `to_dict()`에도 명시적 업데이트 필요하나 설계에서 언급 없음.
- **수정 제안**: 변경 파일 목록에 `to_dict()` 업데이트 명시, 또는 `asdict(self)` 전환 검토.

### 10. [ACCEPT / Medium] prepare() → plan() memory_context 전달 경로 미명시

- **대상 코드**: 설계 문서 섹션 4.5 (line 393-421) vs `core/project_pipeline.py:671`
- **판정 근거**: `plan(memory_context=None)` 인자를 추가하지만, `prepare()` 내부에서 `_recall_from_memory()` 결과를 `plan()` 호출에 전달하는 경로가 불분명. `normalize()`는 `prepare()` 바깥에서 호출되므로 독립적 memory recall vs 인자 전달 방식이 정해지지 않음.
- **수정 제안**: `prepare()` 내부에서 recall 수행 → `plan(memory_context=recall_result)` 전달 경로를 명시.

---

## 구현 순서 검증

| 순서 | 내용 | 평가 |
|:---:|------|------|
| 1 | `core/skill_quality_gate.py` 신규 | 의존성 없음, 적절. `SkillRegistry.instance()` 수정 필요 |
| 2 | `fsa_loop.py` gate 삽입 | 순서 1에 의존, 적절. `SkillEvolutionBus` 유지 필요 |
| 3 | `intake.py` _recall_from_memory | 독립적, 적절 |
| 4 | `bootstrap_roles.py` plan(memory_context) | 순서 3에 의존, 적절 |
| 5 | `project_pipeline.py` facade 조기 초기화 | 순서 3,4에 의존, 적절. `get_instance()` 처리 수정 필요 |
| 6 | `skill_eval_harness.py` report_path | **이미 구현됨** — 제거 필요 |
| 7 | `af.spec` hiddenimports | 순서 1에 의존, 적절 |
| 8 | `Master_Blueprint.md` 업데이트 | 최종 단계, 적절 |

---

## 수정 필요 항목 요약

### Critical (즉시 수정 필요)
1. `SkillRegistry.instance()` → `get_global_registry()`
2. `EpisodeRecord` 필드를 `metadata` dict 내부로 이동

### High (구현 전 반드시 수정)
3. `skill_path` / `skill_dir` 혼동 해결
4. `get_instance()` 반환값 처리 로직 수정
5. `SkillEvolutionBus` 호출 유지

### Medium (구현 시 함께 반영)
6. `report_path` 항목 제거/완료 표시
7. `to_dict()` 업데이트 명시
8. `prepare()` → `plan()` memory_context 전달 경로 명시

---

## 설계 원칙 준수 평가

| 원칙 | 평가 |
|------|------|
| 최소 변경 | 준수. 새 클래스 1개 + 기존 수정 ~115줄 |
| 점진적 통합 | 준수. Part A, B, C 독립 구현 가능 |
| 역방향 호환 | 대체로 준수. `to_dict()` 미업데이트 시 직렬화 호환성 문제 |
| 에러 처리 | 준수. `try/except: pass` 패턴, graceful degradation |
