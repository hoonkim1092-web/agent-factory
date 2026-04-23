# 3계층 통합 설계 — Evals-FSA 연결 + 메모리 회상 타이밍 + Plane 경계 정리

> 날짜: 2026-04-09
> 상태: Reviewed (교차검증 완료 — `docs/archive/code_review/26_0409_three_plane_cross_review.md` 참조)
> 브랜치: `agent-factory_harness_Claude_Setup_and_Pipeline_v1`
> 선행 문서: `docs/super_harness_3_layer_architecture.md`

---

## 1. 문제 정의

3계층 아키텍처(Control / Quality / Memory Plane)는 **설계 문서상 완성**되었으나, 실제 코드에서 3곳이 끊겨있다.

### 문제 A: Evals → FSA 통합 끊김

```
현재:
  SkillEvalHarness.evaluate() → SkillEvalReport (JSON 저장만)
  FSALoop._try_evolve_failed_skill() → evolve_skill() (평가 결과 무시)

문제: 평가 결과(recommended_stage, pass_rate)가 진화 의사결정에 반영되지 않음
결과: 평가 실패한 스킬도 registry에 등재 가능, 품질 게이트 없음
```

### 문제 B: 메모리 회상 타이밍

```
현재:
  요청 → ControlPlaneIntake.normalize() → Planning → Execution(여기서 첫 메모리 회상)

문제: Planning이 과거 경험 없이 수립됨
결과: 같은 실수 반복, 추상적 계획, 이전 성공 패턴 미활용
```

### 문제 C: 3계층 경계 불명확

```
현재:
  DynamicOrchestrator — 멀티 에이전트 실행 (Control)
  ProjectPipeline — 계획 + 실행 (Quality + Control 혼재)
  FSALoop — 자동화 + 평가 (Control + Quality 혼재)

문제: 한 모듈이 여러 Plane의 책임을 가져 역할 경계가 불분명
결과: 유지보수 어려움, 평가 시스템 3중 중복 (eval_harness, evaluator, parallel_critique)
```

---

## 2. 설계 원칙

1. **기존 코드 최소 변경**: 새 클래스/함수 추가 > 기존 시그니처 변경
2. **점진적 통합**: 각 문제를 독립적으로 해결 가능하게 설계
3. **역방향 호환**: 기존 동작을 깨뜨리지 않음 (새 기능은 opt-in)
4. **3계층 원칙 준수**: Control은 흐름만, Quality는 품질만, Memory는 기억만

---

## 3. Part A: Evals → FSA 통합

### 3.1 현재 흐름 (끊긴 상태)

```
[스킬 생성/진화]
  skill_creator.evolve_skill()
    → 새 skill.py 파일 생성
    → (끝 — 평가 없음)

[스킬 평가]
  SkillEvalHarness.evaluate(skill_path)
    → SkillEvalReport (JSON 저장)
    → (끝 — registry 연결 없음)

[FSA 실패 시]
  _try_evolve_failed_skill()
    → evolve_skill() 호출
    → _hot_reload_registry()
    → (끝 — 평가 결과 확인 없음)
```

### 3.2 목표 흐름 (통합)

```
[스킬 생성/진화]
  skill_creator.evolve_skill()
    → 새 skill.py 생성
    ↓
  SkillQualityGate.validate(skill_path)        ← NEW
    → SkillEvalHarness.evaluate() 실행
    → pass_rate >= 0.8?
      YES → registry.register() + stage="canary"
      NO  → registry에 등록 안 함 + 실패 사유 반환
    ↓
  registry 메타데이터에 eval_report 첨부
    → passed_at, pass_rate, test_count, recommended_stage

[FSA 실패 시]
  _try_evolve_failed_skill()
    → evolve_skill()
    → SkillQualityGate.validate()              ← NEW
      → 통과 시만 _hot_reload_registry()
      → 실패 시 실패 사유를 다음 사이클 피드백에 주입
```

### 3.3 신규 모듈: `core/skill_quality_gate.py` (~80줄)

```python
"""
core/skill_quality_gate.py
===========================
스킬 품질 게이트 — 평가 통과한 스킬만 registry에 등재.

Quality Plane 컴포넌트.
Evals(SkillEvalHarness) → Registry(SkillRegistry) 연결 다리.
"""

@dataclass
class GateResult:
    passed: bool
    skill_path: str
    recommended_stage: str          # "draft"|"canary"|"candidate"
    pass_rate: float                # 0.0~1.0
    eval_report_path: str           # JSON 보고서 경로
    failure_reasons: list[str]      # 실패 시 사유 목록
    
class SkillQualityGate:
    """스킬 평가 → 등재 게이트."""
    
    PASS_RATE_THRESHOLD = 0.8       # 80% 이상이어야 통과
    
    def __init__(self, registry: SkillRegistry | None = None):
        from core.skill_registry import get_global_registry
        self.registry = registry or get_global_registry()
        self.harness = SkillEvalHarness()
    
    def validate(
        self,
        skill_path: str,
        *,
        baseline_skill_path: str | None = None,
        auto_register: bool = True,
    ) -> GateResult:
        """
        스킬을 평가하고, 통과 시 registry에 자동 등록.
        
        Args:
            skill_path: 평가할 스킬 디렉토리 경로
            baseline_skill_path: Shadow eval용 기준선 스킬 (선택)
            auto_register: True면 통과 시 자동 registry 등록
            
        Returns:
            GateResult — passed, recommended_stage, pass_rate 등
        """
        # 1. 평가 실행 (skill_path는 디렉토리 — harness는 파일 경로를 기대)
        import os
        skill_py = os.path.join(skill_path, "skill.py")
        report = self.harness.evaluate(
            skill_py,
            baseline_skill_path=baseline_skill_path,
        )
        
        # 2. 통과 여부 판정
        passed = report.contract_eval.pass_rate >= self.PASS_RATE_THRESHOLD
        failure_reasons = []
        if not passed:
            failure_reasons.append(
                f"contract pass_rate {report.contract_eval.pass_rate:.1%} "
                f"< threshold {self.PASS_RATE_THRESHOLD:.0%}"
            )
            for case in report.contract_eval.details:
                if not case.passed:
                    failure_reasons.append(f"  FAIL: {case.name} — {case.error}")
        
        # 3. 통과 시 registry 등록
        if passed and auto_register:
            self._register_with_eval(skill_path, report)
        
        return GateResult(
            passed=passed,
            skill_path=skill_path,
            recommended_stage=report.recommended_stage,
            pass_rate=report.contract_eval.pass_rate,
            eval_report_path=report.report_path,
            failure_reasons=failure_reasons,
        )
    
    def _register_with_eval(self, skill_path, report):
        """eval 메타데이터를 포함하여 registry에 등록."""
        # SkillMetadata 로드 (기존 로직)
        # eval_meta 추가: passed_at, pass_rate, test_count, recommended_stage
        # registry.register(metadata)
        ...
```

### 3.4 `fsa_loop.py` 변경 (~20줄)

```python
# 기존 _try_evolve_failed_skill() 내부, evolve_skill() 호출 후:

# ── 기존 ──
evolved_skill = evolve_skill(...)
self._hot_reload_registry(skill_dir)

# ── 변경 ──
evolved_skill = evolve_skill(...)

# 품질 게이트 통과 확인
from core.skill_quality_gate import SkillQualityGate
gate = SkillQualityGate()
gate_result = gate.validate(skill_dir, auto_register=True)

if gate_result.passed:
    self._hot_reload_registry(skill_dir)
    # EvolutionBus 브로드캐스트 유지 (캐시 무효화 + 이벤트 전파)
    from core.skill_evolution_bus import SkillEvolutionBus
    SkillEvolutionBus.on_skill_evolved(skill_dir)
    _safe_print(f"[FSA] Skill evolved & validated: {skill_dir} "
                f"(pass_rate={gate_result.pass_rate:.0%})")
else:
    # 실패 사유를 다음 사이클 피드백에 주입
    _safe_print(f"[FSA] Skill evolution failed quality gate: "
                f"{gate_result.failure_reasons}")
    # hot reload 하지 않음 — 이전 버전 유지
```

### 3.5 에피소드 기록 (Memory Plane 연결)

```python
# fsa_loop.py run_mission() 최종 단계에서:

# ── 성공/실패 에피소드 저장 ──
try:
    facade = UnifiedMemoryFacade.get_instance()
    if facade._initialised:
        from core.memory_system.models import EpisodeRecord
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
        _run_async_safe(facade.record_episode(episode))
except Exception:
    pass
```

### 3.6 변경 파일 목록

| 파일 | 변경 | 규모 |
|------|------|------|
| `core/skill_quality_gate.py` | **신규** | ~80줄 |
| `core/fsa_loop.py` | 수정 — `_try_evolve_failed_skill()`에 gate 삽입 + 에피소드 기록 | ~30줄 |
| `core/skill_eval_harness.py` | ~~수정~~ — `report_path` 필드 ✅ 이미 구현됨 | 0줄 |
| `af.spec` | 수정 — `core.skill_quality_gate` hiddenimport | ~1줄 |

---

## 4. Part B: 메모리 회상 타이밍

### 4.1 현재 흐름 (회상 없음)

```
ControlPlaneIntake.normalize()
  ① work_kind 분류
  ② issue_context 바인딩
  ③ continuity_snapshot 구축       ← 이건 상태 복원이지 메모리 회상이 아님
  ④ change_impact 분석
  ⑤ execution_policy 결정
  ⑥ state_machine 초기화
  → NormalizedRequest 반환

ProjectPlanningDirector.plan()
  → 입력: task_input, project_brief
  → 출력: roles, modules, tasks
  → (과거 경험 참조 없음)
```

### 4.2 목표 흐름 (메모리 회상 추가)

```
ControlPlaneIntake.normalize()
  ① work_kind 분류
  ② issue_context 바인딩
  ③ continuity_snapshot 구축
  ④ ★ memory_recall 실행 (NEW)     ← 여기!
     → search_semantic(task_input)
     → 유사 에피소드 검색
     → 실패 패턴 + 성공 패턴 추출
  ⑤ change_impact 분석
  ⑥ execution_policy 결정
  ⑦ state_machine 초기화
  → NormalizedRequest(memory_context=recall_result) 반환

ProjectPlanningDirector.plan()
  → 입력: task_input, project_brief, ★memory_context
  → "과거에 이런 작업에서 X가 실패했다. Y 접근이 효과적이었다."
  → 구체적 계획 수립
```

### 4.3 NormalizedRequest 확장

```python
# core/control/intake.py — NormalizedRequest에 필드 추가

@dataclass
class NormalizedRequest:
    # ... 기존 필드 ...
    memory_context: dict = field(default_factory=dict)
    
    # ⚠️ to_dict()도 반드시 업데이트 (수동 dict 구성 방식이므로):
    # def to_dict(self):
    #     d = { ... 기존 필드 ... }
    #     d["memory_context"] = self.memory_context
    #     return d
    
    # 구조:
    # {
    #   "recalled_episodes": [
    #     {"task": "JWT 인증 구현", "outcome": "failure", 
    #      "patterns": ["보안:인증누락"], "lesson": "..."},
    #   ],
    #   "recalled_lessons": [
    #     {"content": "Redis 캐시 TTL은 300초가 적절", "confidence": 0.85},
    #   ],
    #   "recall_count": 3,
    #   "recall_time_ms": 120,
    # }
```

### 4.4 ControlPlaneIntake 변경 (~30줄)

```python
# core/control/intake.py — normalize() 내부, ③ continuity_snapshot 이후에 추가

def normalize(self, task_input, workspace, route, board=None):
    # ... 기존 ①~③ ...

    # ④ Memory Recall (NEW)
    memory_context = self._recall_from_memory(task_input)

    # ... 기존 ⑤~⑦ ...

    return NormalizedRequest(
        # ... 기존 필드 ...
        memory_context=memory_context,
    )


def _recall_from_memory(self, task_input: str) -> dict:
    """Memory Plane에서 관련 기억을 회상한다.
    
    UnifiedMemoryFacade가 초기화되지 않았으면 빈 dict 반환 (graceful).
    """
    try:
        from core.memory_system.facade import UnifiedMemoryFacade
        facade = UnifiedMemoryFacade.get_instance()
        if not facade._initialised:
            return {}
        
        import time
        t0 = time.time()
        
        # 동기 컨텍스트에서 비동기 호출
        from core.agent_runner import _run_async_safe
        records = _run_async_safe(
            facade.search_semantic(task_input, limit=5)
        )
        
        elapsed_ms = (time.time() - t0) * 1000
        
        if not records:
            return {"recall_count": 0, "recall_time_ms": elapsed_ms}
        
        episodes = []
        lessons = []
        for r in records:
            if r.memory_type and r.memory_type.value == "episodic":
                episodes.append({
                    "task": r.metadata.get("task_input", "")[:200],
                    "outcome": r.metadata.get("outcome", ""),
                    "patterns": r.metadata.get("failure_patterns", []),
                    "lesson": r.content[:300],
                })
            else:
                lessons.append({
                    "content": r.content[:300],
                    "confidence": r.metadata.get("confidence", 0.5),
                })
        
        return {
            "recalled_episodes": episodes,
            "recalled_lessons": lessons,
            "recall_count": len(records),
            "recall_time_ms": round(elapsed_ms, 1),
        }
    except Exception:
        return {}
```

### 4.5 ProjectPlanningDirector 변경 (~15줄)

```python
# core/bootstrap_roles.py — plan() 메서드 내부

def plan(self, task_input: str, project_brief: dict, 
         memory_context: dict | None = None) -> dict:
    # 기존 프롬프트 구성 ...
    
    # ── 메모리 컨텍스트 주입 (NEW) ──
    if memory_context and memory_context.get("recall_count", 0) > 0:
        memory_section = "\n\n## Past Lessons (from Memory Plane)\n\n"
        
        for ep in memory_context.get("recalled_episodes", []):
            outcome = "✅ 성공" if ep["outcome"] == "success" else "❌ 실패"
            memory_section += f"- [{outcome}] {ep['task']}\n"
            if ep.get("patterns"):
                memory_section += f"  실패 패턴: {', '.join(ep['patterns'])}\n"
            if ep.get("lesson"):
                memory_section += f"  교훈: {ep['lesson']}\n"
        
        for ls in memory_context.get("recalled_lessons", []):
            memory_section += f"- 교훈 (신뢰도 {ls['confidence']:.0%}): {ls['content']}\n"
        
        memory_section += (
            "\n위 과거 경험을 참고하여:\n"
            "1. 이전에 실패한 접근 방식을 피하라\n"
            "2. 이전에 성공한 패턴을 재사용하라\n"
            "3. 새로운 위험을 식별했으면 계획에 반영하라\n"
        )
        
        # 프롬프트에 추가
        prompt += memory_section
```

### 4.6 UnifiedMemoryFacade 조기 초기화

현재 `agent_runner.run()`에서 초기화되므로, Planning 시점에는 facade가 없을 수 있다.

```python
# core/project_pipeline.py — prepare() 시작 부분에 추가

def prepare(self, task_input, workspace, ...):
    # ── Memory Plane 조기 초기화 (Planning 전에 필요) ──
    try:
        from core.memory_system.facade import UnifiedMemoryFacade
        facade = UnifiedMemoryFacade.get_instance()
        if not facade._initialised:
            from core.agent_runner import _run_async_safe
            facade = UnifiedMemoryFacade(project_id=project_id or "agent_factory")
            # 최소 어댑터만 등록 (빠른 초기화)
            from core.memory_system.adapters.core_memory import CoreMemoryAdapter
            from core.memory_system.adapters.knowledge_graph import KnowledgeGraphAdapter
            facade.register_adapter(CoreMemoryAdapter())
            facade.register_adapter(KnowledgeGraphAdapter(workspace=workspace))
            _run_async_safe(facade.initialise())
            UnifiedMemoryFacade.set_instance(facade)
    except Exception:
        pass  # 메모리 없어도 파이프라인은 동작
    
    # ... 기존 prepare() 로직 ...
    
    # ── memory_context를 plan() 호출에 전달 ──
    # prepare() 내부에서 직접 recall 수행 후 plan()에 전달
    memory_context = {}
    try:
        from core.control.intake import ControlPlaneIntake
        memory_context = ControlPlaneIntake._recall_from_memory(
            ControlPlaneIntake, task_input
        )
    except Exception:
        pass
    
    plan_result = self.planner.plan(
        task_input, project_brief, memory_context=memory_context
    )
```

### 4.7 변경 파일 목록

| 파일 | 변경 | 규모 |
|------|------|------|
| `core/control/intake.py` | 수정 — `_recall_from_memory()` + NormalizedRequest.memory_context | ~40줄 |
| `core/bootstrap_roles.py` | 수정 — `plan(memory_context=None)` + 프롬프트 주입 | ~20줄 |
| `core/project_pipeline.py` | 수정 — `prepare()`에서 facade 조기 초기화 + memory_context 전달 | ~20줄 |

---

## 5. Part C: 3계층 경계 정리

### 5.1 현재 책임 분포 (혼재)

```
DynamicOrchestrator:
  ✅ Control: 에이전트 큐, 재시도, 상태 동기화
  ❌ Quality: _cross_verified_evaluate() — Quality Plane 책임
  ❌ Quality: _try_evolve_from_patterns() — Quality Plane 책임

ProjectPipeline:
  ❌ Control: execute() 내에서 DynamicOrchestrator 직접 호출
  ✅ Quality: prepare() — 문서 생성, 구조 검증, 교차검증
  ✅ Quality: run_structural_gate()

FSALoop:
  ✅ Control: 워크스페이스 git, 사이클 관리
  ❌ Quality: _run_cross_verified_evaluator() — Quality Plane
  ❌ Quality: _try_evolve_failed_skill() — Quality Plane
```

### 5.2 목표 책임 분배

```
Control Plane (흐름 제어):
  DynamicOrchestrator — 멀티 에이전트 라우팅 + 태스크 큐
  FSALoop — 단일 에이전트 사이클 + 워크스페이스 관리
  ControlPlaneIntake — 요청 정규화 + 메모리 회상
  ApprovalGate — 승인 게이트

Quality Plane (품질 보장):
  SkillQualityGate — 스킬 평가 → 등재 게이트 (NEW)
  SkillEvalHarness — 3단계 스킬 평가
  CrossVerificationLoop — 멀티 CLI 교차검증
  DocumentReviewSession — 문서 교차검증 (NEW, 이미 구현)
  ProjectPipeline.prepare() — 문서 생성 + 품질 파이프라인
  AggregatedVerdict — 6차원 가중 품질 점수

Memory Plane (기억 관리):
  UnifiedMemoryFacade — 통합 진입점
  KnowledgeInjectionHook — 실행 전 지식 주입
  MemoryConsolidationHook — 실행 후 에피소드 캡처
  ControlPlaneIntake._recall_from_memory() — Planning 전 회상 (NEW)
```

### 5.3 리팩토링 방향 (점진적)

현재 혼재된 책임을 **한 번에 분리하지 않는다**. 대신:

**Phase 1 (이번 설계)**: 새 기능을 올바른 Plane에 배치
- SkillQualityGate → Quality Plane (신규)
- _recall_from_memory → Memory Plane (신규)
- DocumentReviewSession → Quality Plane (이미 완료)

**Phase 2 (후속)**: 기존 혼재 코드를 점진적으로 위임
- DynamicOrchestrator._cross_verified_evaluate() → CrossVerificationLoop 직접 호출로 변경
- FSALoop._try_evolve_failed_skill() → SkillQualityGate.validate()로 대체
- ProjectPipeline.execute() → DynamicOrchestrator에 위임만 (내부 로직 최소화)

**Phase 3 (장기)**: Plane 인터페이스 표준화
- 각 Plane에 명시적 인터페이스 정의 (`ControlPlaneAPI`, `QualityPlaneAPI`, `MemoryPlaneAPI`)
- 모듈 간 호출은 인터페이스를 통해서만

### 5.4 평가 시스템 정리

현재 3개 평가 시스템의 역할을 명확히 구분:

| 평가 시스템 | 시점 | 대상 | Plane |
|------------|------|------|-------|
| `SkillEvalHarness` | 배포 전 (Pre-flight) | 스킬 코드 | Quality |
| `CrossVerificationLoop` | 실행 중 (Runtime) | 에이전트 출력 | Quality |
| `parallel_critique` | 실행 후 (Post-flight) | 최종 산출물 | Quality |

```
Pre-flight: "이 스킬을 써도 되는가?" → SkillEvalHarness + SkillQualityGate
Runtime:    "이 결과가 맞는가?"       → CrossVerificationLoop
Post-flight: "최종 결과가 좋은가?"    → parallel_critique + AggregatedVerdict
```

### 5.5 변경 파일 목록 (Phase 1만)

Phase 1은 Part A + Part B에 포함되므로 **추가 변경 없음**. 
경계 정리는 Part A의 SkillQualityGate과 Part B의 _recall_from_memory 배치로 자연스럽게 달성.

---

## 6. 통합 흐름 (3개 문제 해결 후)

```
[사용자 요청]
  ↓
ControlPlaneIntake.normalize()                    ← Control Plane
  ├─ work_kind 분류
  ├─ issue_context 바인딩
  ├─ ★ _recall_from_memory()                      ← Memory Plane (NEW)
  │   → "이전에 JWT 구현에서 인증 누락으로 실패"
  │   → "Redis TTL 300초가 적절했음"
  └─ NormalizedRequest(memory_context=recall)
  ↓
ProjectPipeline.prepare()                         ← Quality Plane
  ├─ ★ Memory Facade 조기 초기화                   ← Memory Plane (NEW)
  ├─ Research Evidence Collection
  ├─ ProjectPlanningDirector.plan(memory_context)  ← Quality (NEW 인자)
  │   → "JWT 인증을 반드시 포함하라 (과거 실패 패턴)"
  │   → "Redis TTL은 300초로 설정하라 (검증됨)"
  ├─ Work-Item 생성
  ├─ 구조 검증 (RubricCompiler)
  └─ 문서 교차검증 (DocumentReviewSession)
  ↓
ApprovalGate.approve()                            ← Control Plane
  ↓
ProjectPipeline.execute()                         ← Control + Quality
  ├─ DynamicOrchestrator.run_project()            ← Control Plane
  │   ├─ AgentRunner.run()
  │   │   ├─ KnowledgeInjectionHook.pre_execute()  ← Memory Plane
  │   │   └─ MemoryConsolidationHook.post_execute() ← Memory Plane
  │   └─ 실패 시:
  │       ├─ CrossVerificationLoop                  ← Quality Plane
  │       └─ FSALoop._try_evolve_failed_skill()     ← Control Plane
  │           └─ ★ SkillQualityGate.validate()      ← Quality Plane (NEW)
  │               ├─ SkillEvalHarness.evaluate()
  │               ├─ 통과 → registry 등록 + hot reload
  │               └─ 실패 → 이전 버전 유지 + 피드백
  ↓
★ 에피소드 저장                                    ← Memory Plane (NEW)
  └─ facade.record_episode(outcome, patterns, gate_result)
```

---

## 7. 구현 순서

| 순서 | 작업 | 의존성 | 규모 | Plane |
|:---:|------|--------|------|-------|
| **1** | `core/skill_quality_gate.py` 신규 | 없음 | ~80줄 | Quality |
| **2** | `core/fsa_loop.py` — gate 삽입 + 에피소드 기록 | 1 | ~30줄 | Control→Quality |
| **3** | `core/control/intake.py` — `_recall_from_memory()` | 없음 | ~40줄 | Memory |
| **4** | `core/bootstrap_roles.py` — `plan(memory_context)` | 3 | ~20줄 | Quality |
| **5** | `core/project_pipeline.py` — facade 조기 초기화 + memory_context 전달 | 3, 4 | ~20줄 | Quality→Memory |
| ~~6~~ | ~~`core/skill_eval_harness.py` — report_path 필드~~ | — | — | ✅ 이미 구현됨 |
| **6** | `af.spec` — hiddenimports | 1 | ~1줄 | — |
| **7** | `Master_Blueprint.md` — §3, §12 | 전체 | — | — |

**총 규모**: 신규 1개(~80줄) + 수정 5개(~115줄) = **~195줄**

---

## 8. 검증 방법

```bash
# 1. SkillQualityGate 단위 테스트
python -m pytest tests/test_skill_quality_gate.py -v

# 2. 메모리 회상 통합 테스트
af -p test_memory_recall -t "JWT 인증 API 구현" --mode fsa --pipeline project
# 확인: Planning 프롬프트에 "Past Lessons" 섹션 존재
# 확인: NormalizedRequest.memory_context.recall_count > 0

# 3. Evals → FSA 통합 테스트
af -p test_eval_gate -t "간단한 계산기 스킬" --mode fsa
# 확인: 스킬 진화 시 SkillQualityGate.validate() 로그
# 확인: pass_rate < 0.8 시 hot reload 스킵 로그
# 확인: pass_rate >= 0.8 시 registry 등록 로그

# 4. 에피소드 저장 확인
# 실행 후 Memory Plane에 에피소드 기록 확인
python -c "
from core.memory_system.facade import UnifiedMemoryFacade
facade = UnifiedMemoryFacade.get_instance()
if facade:
    import asyncio
    records = asyncio.run(facade.search_semantic('JWT'))
    print(f'Found {len(records)} records')
"

# 5. 기존 테스트 회귀
python -m pytest tests/ -v
```

---

## 9. 변경 파일 총 목록

| 파일 | 상태 | 규모 | Plane |
|------|------|------|-------|
| `core/skill_quality_gate.py` | **신규** | ~80줄 | Quality |
| `core/fsa_loop.py` | 수정 | ~30줄 | Control |
| `core/control/intake.py` | 수정 | ~40줄 | Control + Memory |
| `core/bootstrap_roles.py` | 수정 | ~20줄 | Quality |
| `core/project_pipeline.py` | 수정 | ~20줄 | Quality |
| `core/skill_eval_harness.py` | ✅ 이미 구현됨 | 0줄 | Quality |
| `af.spec` | 수정 | ~1줄 | — |
| `Master_Blueprint.md` | 수정 | — | — |
| **합계** | 신규 1 + 수정 6 | ~190줄 | |

---

## 10. 리스크 및 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 메모리 회상 지연 (search_semantic 느림) | prepare() 시간 증가 | timeout 3초 + 실패 시 빈 dict 반환 |
| facade 조기 초기화가 agent_runner 초기화와 충돌 | 싱글톤 이중 초기화 | `get_instance()` 체크 후 없을 때만 생성 |
| SkillQualityGate가 eval 실행 중 크래시 | 스킬 진화 전체 실패 | try/except로 래핑, 실패 시 기존 동작(게이트 없이 진화) 유지 |
| Planning 프롬프트 토큰 증가 | 비용 증가 | memory_context를 최대 5개 에피소드, 각 300자로 제한 |
