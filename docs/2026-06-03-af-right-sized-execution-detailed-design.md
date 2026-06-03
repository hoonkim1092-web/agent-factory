# AF Right-Sized Execution — 상세 설계 (슬라이스 1)

Date: 2026-06-03
Status: Detailed design — 구현 대기 (Sonnet)
Depends on: `docs/2026-06-03-af-right-sized-execution-decision.md` §Converged Design
Scope: **슬라이스 1만**. 보수적 2-way 라우팅을 dogfood DEVELOP 진입부에 연결한다.
       슬라이스 2(`ProjectPipeline` stage-선택 파라미터)는 본 문서 범위 밖.

---

## 0. 이 문서가 확정하는 것 / 안 하는 것

확정:
- 신규 모듈 `core/right_sized_router.py`의 공개 API·데이터 shape·함수 시그니처
- 두 결정적 안전 floor의 정확한 판정 로직과 우선순위
- 보수적 fallback의 트리거 조건과 결과
- `core/dogfood.py` DEVELOP 진입부 배선 (light vs full 분기)
- dogfood 네이티브 light 경로의 구성 (기존 결정적 빌더 + AI codegen 재사용)
- test-first 테스트 계약, af.spec/Blueprint 동반 수정

안 함 (슬라이스 2 또는 별도):
- `ProjectPipeline.run()`에 stage-선택 파라미터 추가 (monolithic 유지)
- top-level(사용자 요청 → dogfood 진입 여부) 라우팅 — 본 라우터는 재사용 가능하게 설계하나 슬라이스 1 소비처는 DEVELOP 내부 한 곳
- ControlPlaneLLM 시그니처 변경 (`workspace` 파라미터 추가 등)

---

## 1. 코드 baseline (실제 코드, 2026-06-03 grep 캡처)

> 메모리 규칙 `feedback_analysis_doc_baseline_must_be_real_code` 준수 — 아래 좌표는 추정이 아니라 실제 코드.

### 1.1 라우팅 엔진 후보
- `core/control_plane_llm.py:39` `class ControlPlaneLLM`
  - `:161` `generate_json(self, prompt: str, output_schema: type | None = None) -> dict`
    — provider 없으면 `{}`, JSON 파싱 실패 시도 `{}` 반환 (`:175`)
  - `:93` `_generate_via_cli` → `:122` `workspace=os.getcwd()`, `:124` `allow_file_edit=False`
    (control-plane은 JSON만, 파일편집 도구 차단 — T3에서 source-write leak 차단 확인된 경로)
- `core/express_router.py`
  - `:26` `_PHASES: dict[str,list[str]]` = direct/light/full/dogfood 각 phase 리스트 (stage 어휘 SSOT)
  - `:119` `RouteDecision` (정적 dataclass), `:166` `_classify` (토큰 룰), `:206` `route_task`
  - `:46` `_SELF_MOD = ("core/", "af.spec", "master_blueprint", "dogfood", "self-modifying")`
  - **사실**: `route_task`는 production 호출처 0 (NEXT_STEPS 확인, `test_express_router.py`만 참조). 정적 토큰 룰.

### 1.2 안전 floor 재사용 대상
- `scripts/blast_radius.py` (stdlib만, core 의존 0 → import 안전; `from scripts import blueprint_updater` 선례가 dogfood.py:958에 존재 = namespace 패키지로 import 가능)
  - `:120` `classify_path(rel_path: str) -> Tier`  — **path-only, 결정적, 파일 존재 불필요** (신규 파일도 분류 가능)
  - `:164` `classify_with_content(rel_path, workspace) -> Tier` — 파일 읽음 (신규 파일엔 부적합)
  - `:48` `_TIER3_PATHS`, `:74` `_TIER3_PREFIXES`, `:23` `_TIER3_REGEX`
  - `:194` `required_agents(tier) -> list[str]`

### 1.3 dogfood 통합 지점
- `core/dogfood.py`
  - `:105` `_PHASE_ORDER = PENDING → ISOLATE → DEVELOP → VERIFY → REVIEW → FINALIZE → MERGE → COMPLETE`
    — **DEVELOP는 ISOLATE 다음**: classify 시점엔 이미 worktree 격리 상태 (isolation_status="ready")
  - `:136` `DogfoodState` — `:138 task`, `:139 phase`, `:146 worktree_workspace`, `:148 isolation_status`,
    `:163 plan_path`, `:165 develop_changed_paths`. `:185 _cwd()` = isolation ready면 worktree 반환.
    `:194 to_dict` / `from_dict`(:254) 직렬화.
  - `:1626` `_run_develop_phase(state, pipeline)` — **현재: 무조건 `pipeline.run(task_input, workspace=worktree, runtime_workspace)`**.
    `:1660-1712` 결과 정규화(ok/verification_requirements/steps) + `:1684 state.develop_changed_paths` 설정.
    `:1618 _ISO_ENV_KEYS` 격리 env (try/finally).
  - `:1516` `_run_implement_phase(state, context)` — **레거시 AI-codegen 경로** (DogfoodPhase.IMPLEMENT용, 여전히 dispatch됨 `:2022`).
    plan_dict 로드 → command step 실행 + commands 없는 step은 `_ai_executor`(:1568) 위임 →
    반환 `{executed, failures, skipped_no_commands, actual_changed, ok}`. cwd=`state._cwd()` (worktree).
  - `:1715` `_run_verify_phase(state, context)` — plan_dict의 verification_requirements를 `state._cwd()`에서 실행.
  - `:438` `_default_ai_executor` / `:457` `_ai_executor` (monkeypatch 주입 가능)
  - `:1817` `run_all(...)` — `agent_launcher.py:1060`에서 `project_pipeline=_af.project_pipeline`로 호출.
    `:1876` DEVELOP 분기 → `run_phase(state, project_pipeline=...)` → `:2021 _run_develop_phase`.

### 1.4 light 경로용 결정적 빌더 (LLM·멀티에이전트 불필요)
- `core/spec_compiler.py:141` `compile_spec(interview_artifact, evidence_bundle, research_brief=None) -> CompiledSpec`
  — `{"task_input": task}` 최소 입력으로 동작, `:101 _scope_from_intent(intent)`로 scope 파생. 순수 dict 연산.
- `core/premortem.py:594` `run_premortem(spec) -> PremortomResult` — 결정적 AST 디텍터(R10~R17).
- `core/planner.py:499` `build_plan(spec, premortem) -> ExecutablePlan` — 결정적.
- **핵심 사실**: 위 3개는 LLM 호출도, 외부 터미널 spawn도 없다. "200+ cycle busy-wait"의 원인은
  `ProjectPipeline.run()`이 designer/qa/reviewer를 `terminal_per_agent=True`로 분해하는 것 (decision 문서 §Background).
  light 경로의 유일한 LLM 호출은 `_run_implement_phase` 내부 `_ai_executor`(codegen 1~N회) + `_router_llm.generate_json`(분류 1회).

---

## 2. 핵심 설계 결정과 트레이드오프 (구현 전 명시)

| # | 결정 | 근거 / 트레이드오프 |
|---|------|-------------------|
| A | classify는 `_run_develop_phase` **진입부**에서 1회 호출 | decision §Step 5. DEVELOP는 ISOLATE 다음이라 이미 worktree. → isolation floor는 슬라이스1 DEVELOP에선 사실상 satisfied(이미 worktree), **활성 floor는 blast_radius Tier3**. isolation floor는 라우터 재사용성·정합성 위해 구현하되 슬라이스1 주 효과는 review-stage floor. |
| B | classify 시점에 실제 diff 없음 → **의도 scope를 `_scope_from_intent(task)`로 파생**해 `changed_files`로 전달 | scope 파생이 sensitive 파일을 놓치면 floor가 못 잡음. **완화**: scope 파생 0건 = 저신뢰 → fallback full. scope 중 Tier3 1개라도 → full. 보수적 비대칭(under-route 금지) 유지. |
| C | light 경로 = `compile_spec({"task_input": task}) → run_premortem → build_plan → _run_implement_phase → _run_verify_phase`. **Triad(run_triad) 생략** | decision light 경로 정의가 `build_plan→implement→verify`(triad 없음). leaf task엔 plan-critique 과잉. sensitive는 floor가 full로 보냄. |
| D | `DogfoodState`에 `route_decision: dict` 신규 필드 + to_dict/from_dict | decision "분류는 state/artifact에 이유와 함께 기록" 요구. |
| E | light 판정은 **floor 적용 후** `set(required_stages) ⊆ {plan,implement,test}` AND `confidence ≥ 0.7` | floor가 review/cross_review를 주입하면 자동으로 light 탈락 → full. confidence는 보조(LLM 과신 가능), blast_radius가 결정적 backstop. |
| F | 라우터 LLM은 `ControlPlaneLLM().generate_json` (`allow_file_edit=False` 이미 박힘) 재사용. `workspace=os.getcwd()`는 변경 안 함 | ControlPlaneLLM의 **파일편집 도구** leak은 `allow_file_edit=False`로 차단됨(T3 PASS). **잔여 감시**: os.getcwd()가 source root 가리킴 — 파일편집 차단으로 무해하나 NEXT_STEPS leak 회귀 감시 포인트에 등록. ControlPlaneLLM 시그니처 변경은 슬라이스1 scope 밖. |
| F2 | **light 경로도 `_ISO_ENV_KEYS` 격리 env를 full과 동일하게 설정** (공유 context manager로 추출) | ⚠️ **cross-review High finding 수용**. `_run_implement_phase`가 위임하는 `_ai_executor`/`registry_manager`는 `allow_file_edit`와 **무관한 별도 write 경로** — `AF_DISABLE_REGISTRY_WRITE`/`AGENT_PROJECT_ROOT`/`AF_SELF_RUN`/`AF_SKIP_DOMAIN_REVIEW`를 light에서 빠뜨리면 AI codegen 중 source root registry write·skill lookup이 worktree 밖으로 샌다. full 경로(`dogfood.py:1639-1655`)와 동일 격리 필수. |
| G | 테스트 주입은 모듈 전역 `_router_llm` (default None → lazy `ControlPlaneLLM`) | dogfood `_ai_executor` 주입 패턴 미러. |
| H | scope=[] (task에 파일경로 토큰 없음) → **light 거부, full fallback** | ⚠️ **cross-review Medium finding 수용**. `_scope_from_intent`는 "확장자+경로구분자" 토큰만 추출(`spec_compiler.py:101-109`) → bare `"geometric_mean"`은 []. scope=[]이면 ① floor의 Tier3 검사 불가 ② `build_plan` steps=[] → codegen 미발생. 둘 다 under-route 위험 → scope=[]는 저신뢰로 full. **acceptance task는 실제 dogfood 형식**(`"core/utils.py에 geometric_mean(...) 추가"`)으로 파일경로 포함 — 그때만 scope 파생 성공. |

---

## 3. Module 1 — `core/right_sized_router.py` (신규, Tier 3)

### 3.1 데이터 shape

```python
from __future__ import annotations
from dataclasses import dataclass, field

# 어휘 (express_router._PHASES 와 정합 — stage 이름 재사용)
ISOLATION_LEVELS = ("none", "source", "worktree", "dogfood")   # 순서 = 위험도 오름차순
STAGE_VOCAB = ("research", "design", "plan", "implement", "test", "review", "cross_review")
LIGHT_STAGES = frozenset({"plan", "implement", "test"})         # 이 부분집합이면 네이티브 light 후보

_LIGHT_CONFIDENCE_THRESHOLD = 0.7   # 이 미만이면 light 거부 → full (보수적)

@dataclass
class RouteDecision:
    isolation: str                       # ISOLATION_LEVELS 중 하나
    required_stages: list[str]           # STAGE_VOCAB 부분집합, 순서 보존
    review_depth: str                    # "none" | "standard" | "deep"  (슬라이스1은 기록용)
    confidence: float                    # 0.0 ~ 1.0
    reason: str                          # LLM 또는 fallback 사유
    floors_applied: list[str] = field(default_factory=list)   # 적용된 결정적 floor 라벨
    source: str = "llm"                  # "llm" | "fallback"

    def is_light(self) -> bool:
        """floor 적용 후 호출 — 네이티브 light 경로 적격 여부."""
        return (
            self.source == "llm"
            and self.confidence >= _LIGHT_CONFIDENCE_THRESHOLD
            and set(self.required_stages) <= LIGHT_STAGES
        )

    def to_dict(self) -> dict: ...        # 직렬화 (state 기록용)
```

`review_depth`는 슬라이스 1에서 **기록만** 한다 (dogfood 자체 REVIEW phase + review-gate가 검토 강도를 실제로 집행).
슬라이스 2/top-level 라우팅에서 소비처가 생긴다.

### 3.2 공개 함수

```python
def classify(
    task: str,
    workspace: str,
    *,
    changed_files: list[str] | None = None,
) -> RouteDecision:
    """task를 실행 경로로 분류한다.

    1. _router_llm.generate_json(_build_prompt(...)) 로 후보 결정 생성
    2. 파싱·검증 실패 / 저신뢰 / 예외 → _fallback_decision()
    3. _apply_safety_floors() 로 결정적 하한 강제 (LLM override)

    changed_files: 의도된 scope 파일 경로(없으면 floor의 Tier3 검사 생략 → 저신뢰 취급).
    """
```

```python
# 주입 가능 — 테스트는 core.right_sized_router._router_llm 에 stub 대입
_router_llm = None   # lazy ControlPlaneLLM

def _get_router_llm():
    global _router_llm
    if _router_llm is None:
        from core.control_plane_llm import ControlPlaneLLM
        _router_llm = ControlPlaneLLM()
    return _router_llm
```

### 3.3 프롬프트 빌더

```python
def _build_prompt(task: str, changed_files: list[str], tier_hint: dict[str, int]) -> str:
    """LLM에 의도·범위·위험·설계필요도 종합 판단을 요청.

    제공 컨텍스트: task 전문, 파생 scope 파일 목록, 각 파일의 blast_radius Tier(힌트).
    요청 출력: RouteDecision JSON shape (isolation/required_stages/review_depth/confidence/reason).
    명시 규칙(프롬프트에 박음):
      - 작아도 설계/리뷰 필요하면 design/review/cross_review를 required_stages에 넣어라.
      - 순수 구현(leaf)만 plan/implement/test.
      - 확신 없으면 confidence를 낮춰라(0.5 미만).
    """
```

`tier_hint`는 **참고용** — LLM이 무시해도 §3.4 floor가 결정적으로 덮는다. (하드코딩 금지는 *경로 선택*에, 결정적은 *안전 하한*에 — 서로 다른 층.)

### 3.4 안전 floor (`_apply_safety_floors`)

```python
def _apply_safety_floors(
    decision: RouteDecision, workspace: str, changed_files: list[str],
) -> RouteDecision:
    applied: list[str] = []

    # ── Floor 1: self-mod → isolation 최소 worktree ──────────────────
    if _is_self_modification(workspace, changed_files):
        if _isolation_rank(decision.isolation) < _isolation_rank("worktree"):
            decision.isolation = "worktree"
            applied.append("self_mod_isolation>=worktree")

    # ── Floor 2: blast_radius Tier3 → design+review+cross_review 강제 ──
    if changed_files and _max_tier(changed_files) >= 3:
        forced = ("design", "review", "cross_review")
        added = [s for s in forced if s not in decision.required_stages]
        if added:
            decision.required_stages = _stage_ordered_union(decision.required_stages, forced)
            applied.append("blast_radius_tier3:" + ",".join(added))

    decision.floors_applied = applied
    return decision
```

보조 함수:
```python
def _is_self_modification(workspace: str, changed_files: list[str]) -> bool:
    """workspace가 agent-factory 소스이고 scope가 core/·.githooks/·af.spec 등을 건드리면 True.
    express_router._SELF_MOD 토큰을 재사용 (SSOT) + changed_files prefix 검사 결합."""

def _max_tier(changed_files: list[str]) -> int:
    """scope 파일들의 blast_radius Tier 최댓값. classify_path (path-only) 사용 —
    신규 파일도 분류 가능. import: from scripts.blast_radius import classify_path."""

def _isolation_rank(level: str) -> int:        # ISOLATION_LEVELS.index, 미지값은 0
def _stage_ordered_union(base, extra) -> list  # STAGE_VOCAB 순서 보존 union
```

**floor 우선순위**: floor는 LLM 결정을 **상향(strengthen)만** 한다. 절대 하향 안 함
(isolation 낮춤·stage 제거 없음). under-route 금지의 결정적 구현.

### 3.5 보수적 fallback

```python
_FALLBACK = RouteDecision(
    isolation="worktree",
    required_stages=list(STAGE_VOCAB),     # research 포함 full
    review_depth="deep",
    confidence=0.0,
    reason="",                              # 호출 시 사유 주입
    source="fallback",
)

def _fallback_decision(reason: str) -> RouteDecision:
    d = replace(_FALLBACK, reason=reason)   # dataclasses.replace 로 새 인스턴스
    return d
```

fallback 트리거 (모두 → `required_stages=full`, `isolation=worktree`, `source="fallback"` → `is_light()` False):
1. `_router_llm.generate_json` 예외
2. 반환 `{}` (provider 없음 / 파싱 실패)
3. 스키마 검증 실패 (필수 키 누락, isolation/stage 어휘 위반, confidence 범위 밖)
4. `confidence < _LIGHT_CONFIDENCE_THRESHOLD` 이지만 LLM이 light subset 제안 — fallback까진 아니고
   floor 후 `is_light()`가 confidence로 자동 False 처리 (즉 full로 흐름).

> "research는 생략 가능해도 design/review는 안 낮춘다" — fallback은 design/review/cross_review를 **항상 포함**.

### 3.6 검증 (`_validate_raw`)

LLM 반환 dict를 RouteDecision으로 강건 파싱:
- `isolation ∈ ISOLATION_LEVELS`, 아니면 fallback
- `required_stages` = STAGE_VOCAB 교집합 (미지 stage 무시), 빈 리스트면 fallback
- `confidence` float 강제 (캐스팅 실패 → 0.0)
- `review_depth ∈ {none,standard,deep}`, 아니면 "deep"(보수)
- `reason` str (없으면 "")

---

## 4. Module 2 — `core/dogfood.py` 통합

### 4.0 공유 격리 env context manager (신규 — full·light 공통)

cross-review High finding 수용: light/full **양쪽**이 동일한 worktree-confine env를 보장하도록
현 `_run_develop_phase:1639-1655`의 try/finally를 context manager로 추출한다.

```python
from contextlib import contextmanager

@contextmanager
def _develop_isolation_env(worktree: str):
    """_ISO_ENV_KEYS를 worktree-confine 값으로 설정하고 종료 시 무조건 복원.

    registry write 차단(AF_DISABLE_REGISTRY_WRITE), self-run 표식(AF_SELF_RUN),
    skill lookup root(AGENT_PROJECT_ROOT=worktree), domain-gate skip(AF_SKIP_DOMAIN_REVIEW).
    light 경로의 _run_implement_phase→_ai_executor/registry_manager write도 이 격리에 의존.
    """
    prior = {k: os.environ.get(k) for k in _ISO_ENV_KEYS}
    try:
        os.environ["AF_DISABLE_REGISTRY_WRITE"] = "1"
        os.environ["AF_SELF_RUN"] = "1"
        os.environ["AGENT_PROJECT_ROOT"] = worktree
        os.environ["AF_SKIP_DOMAIN_REVIEW"] = "1"
        yield
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
```

### 4.1 `_run_develop_phase` 리팩토링 (라우터로 변경)

기존 단일 body를 **라우터 + 2 핸들러**로 분리:

```python
def _run_develop_phase(state: DogfoodState, pipeline: Any) -> dict[str, Any]:
    if pipeline is None:
        raise ValueError("project_pipeline is required for DEVELOP phase")

    from core.right_sized_router import classify
    scope = _intended_scope(state.task)                 # _scope_from_intent 재사용
    route = classify(state.task, state._cwd(), changed_files=scope)
    _record_route_decision(state, route)                # state.route_decision + artifact

    # scope=[] (파일경로 미파생) → floor·codegen 둘 다 불가 → under-route 차단(full)
    if route.is_light() and scope:
        return _run_develop_light(state)                # 네이티브 경량
    return _run_develop_full(state, pipeline)           # 기존 ProjectPipeline 경로
```

```python
def _intended_scope(task: str) -> list[str]:
    """task 의도에서 scope 파일 경로 파생 (floor 입력). 결정적·LLM 없음.

    _scope_from_intent는 '확장자+경로구분자' 토큰만 추출(spec_compiler.py:101) —
    파일경로 없는 task는 [] 반환 → 위 라우터가 full로 보냄.
    """
    from core.spec_compiler import _scope_from_intent
    return _scope_from_intent(task)
```

```python
def _record_route_decision(state: DogfoodState, route) -> None:
    """분류 + floor override 사유를 state와 artifact에 기록 (decision 요구사항)."""
    state.route_decision = route.to_dict()
    # 선택: _artifact_path(state, ARTIFACT_ROUTE) 에 별도 기록 (ARTIFACT_ROUTE 신규 상수)
```

### 4.2 `_run_develop_full` — 기존 body 추출 (env 블록은 §4.0 CM으로 치환)

현재 `_run_develop_phase` 본문(`dogfood.py:1638-1712`)을 `_run_develop_full(state, pipeline)`로 추출.
유일한 변경: 인라인 try/finally env 블록(`:1639-1655`)을 `with _develop_isolation_env(worktree):`로 치환
(동일 env·동일 복원 → **행위 무변**, 기존 테스트 GREEN 유지). 나머지(정규화·changed_files fallback)는 그대로.

### 4.3 `_run_develop_light` — 신규 네이티브 경량 경로

```python
def _run_develop_light(state: DogfoodState) -> dict[str, Any]:
    """leaf task용 경량 DEVELOP — ProjectPipeline 멀티에이전트 미사용.

    결정적 빌더(spec/premortem/plan) + AI codegen(_run_implement_phase) 재사용.
    _run_develop_full과 동일한 정규화 shape를 반환해 VERIFY/MERGE가 무변경 소비.
    full과 동일한 _develop_isolation_env로 worktree write를 격리(§4.0).
    """
    from core.spec_compiler import compile_spec
    from core.premortem import run_premortem
    from core.planner import build_plan

    worktree = state.worktree_workspace or state.source_workspace
    spec = compile_spec({"task_input": state.task}, None, None)
    premortem = run_premortem(spec)
    plan = build_plan(spec, premortem)
    plan_d = plan.to_dict()                              # ExecutablePlan.to_dict() 는 항상 "steps" 포함

    # plan artifact 기록 (full 경로의 _run_plan_phase와 동일 — VERIFY/merge가 plan_path 소비)
    plan_path = _artifact_path(state, ARTIFACT_PLAN)
    atomic_write_json(plan_path, plan_d)
    state.plan_path = str(plan_path)
    state.completion_criteria = list(spec.success_criteria)

    # AI codegen — _run_implement_phase 재사용 (worktree cwd, _ai_executor 위임).
    # full과 동일 격리: registry write 차단 + skill lookup root = worktree.
    with _develop_isolation_env(worktree):
        impl = _run_implement_phase(state, {"plan_dict": plan_d})

    # changed_files: 우선 impl["actual_changed"], 없으면 full 경로와 같은 git fallback 재사용
    changed = list(impl.get("actual_changed") or [])
    if not changed:
        changed = _changed_files_fallback(state)        # full 경로 1660-1683 로직 헬퍼화
    state.develop_changed_paths = changed

    # full 경로와 동일한 정규화 (ok / verification_requirements / steps).
    # plan_d["steps"]는 항상 존재 → full의 "steps not in" 데드분기 미사용. 대신:
    #   - verification_requirements 비면 changed 기반 pytest 명령 파생(full과 동일)
    #   - steps=[] (scope/risk 0)면 VERIFY F-PHASE-COMPLETE guard가 미발동하므로,
    #     이 경로 진입 자체를 §4.1에서 scope=[] 차단으로 막는다(steps 비는 케이스 도달 불가).
    normalized = dict(plan_d)
    normalized["ok"] = bool(impl.get("ok", False))
    if not normalized.get("verification_requirements"):
        normalized["verification_requirements"] = _derive_verify_cmds(changed)  # 1695-1705 헬퍼화
    return normalized
```

**공유 헬퍼 추출** (full·light 정규화 중복 제거 — DRY, surgical):
- `_changed_files_fallback(state)` ← 현 `dogfood.py:1660-1683` (git diff → status fallback)
- `_derive_verify_cmds(changed)` ← 현 `dogfood.py:1695-1705` (test 파일 → pytest 명령)

> **steps 데드분기 제거 (cross-review Medium 수용)**: `ExecutablePlan.to_dict()`는 항상 `"steps"` 키를
> 포함하므로(`planner.py`) full 경로의 `if "steps" not in normalized` 분기는 light에서 재현하지 않는다.
> scope=[]→steps=[]→VERIFY guard 미발동 구멍은 §4.1의 `and scope` 가드로 **진입 전 차단**한다
> (scope 있는 task만 light → build_plan이 최소 1개 implementation step 생성 → steps 비지 않음).

> 정규화 동형성이 **핵심 불변식**: light/full 어느 쪽이든 `run_all`의 DEVELOP 분기(`:1890 ok` 체크)와
> VERIFY(`:1902 plan_dict=develop_result`)가 동일하게 동작해야 한다. 테스트로 봉인(§5 inv-NORM).

### 4.4 `DogfoodState` 신규 필드

```python
# dogfood.py:165 develop_changed_paths 아래
route_decision: dict[str, Any] = field(default_factory=dict)
```
`to_dict`(:194)/`from_dict`(:254)에 `route_decision` 추가 (직렬화 누락 시 재시작 후 사유 유실).

### 4.5 `ARTIFACT_ROUTE` 상수 (선택)

decision "artifact에 기록" 충족을 위해 `route_decision.json` artifact를 둘지, state 필드로 충분한지.
**결정**: 슬라이스 1은 `state.route_decision` 필드 + phase_trace 기록으로 충분.
별도 artifact 파일은 over-engineering — `ARTIFACT_ROUTE` 신설 안 함. (Karpathy #2 simplicity)

---

## 5. 테스트 계약 (test-first, Tier 3 → 3-Tier 필수)

### 5.1 `tests/test_right_sized_router.py` (신규)

라우터 단위 — `_router_llm` stub 주입:

| ID | 시나리오 | 기대 |
|----|---------|------|
| R-LIGHT | stub: `{isolation:source, required_stages:[plan,implement,test], confidence:0.9}`, scope=Tier2 파일 | `is_light()==True`, floors_applied=[] |
| R-FULL-STAGE | stub: required_stages에 design 포함 | `is_light()==False` |
| R-LOWCONF | stub: confidence 0.5, light subset | `is_light()==False` (full로) |
| R-FLOOR-TIER3 | stub: light subset, scope=`core/providers/cli.py`(Tier3) | required_stages에 design/review/cross_review 강제 주입, `is_light()==False`, floors_applied 비어있지 않음 |
| R-FLOOR-SELFMOD | stub: `isolation:source`, scope=`core/foo.py`, workspace=agent-factory | isolation→worktree override |
| R-FB-EMPTY | stub: `{}` 반환 | fallback: required_stages=full, isolation=worktree, source="fallback" |
| R-FB-EXC | stub: 예외 raise | fallback (예외 사유 reason) |
| R-FB-BADSCHEMA | stub: `{isolation:"banana"}` | fallback |
| R-FB-NOSCOPE | scope=[] 빈 리스트 | floor Tier3 검사 skip, 저신뢰 취급 검증 |

### 5.2 `tests/test_dogfood.py` 확장

| ID | 시나리오 | 기대 |
|----|---------|------|
| inv-LIGHT-ROUTE | classify stub→light, `_ai_executor` stub | `_run_develop_full` **미호출**(pipeline.run 0회), `_run_develop_light` 경로, leaf 구현 |
| inv-FULL-ROUTE | classify stub→full | 기존 `pipeline.run()` 호출 (회귀: 행위 무변) |
| inv-NORM | light/full 양쪽 develop_result에 ok/verification_requirements/steps 키 존재 + VERIFY 동일 소비 | shape 동형 |
| inv-RECORD | run 후 `state.route_decision` 비어있지 않음 + floors_applied 직렬화 | state/artifact 기록 |
| inv-FLOOR-E2E | scope가 Tier3(sensitive 1줄)인 task → classify가 light 줘도 floor가 full로 | under-route 차단 |
| inv-NOSCOPE | task에 파일경로 토큰 없음(scope=[]) → classify가 light 줘도 `_run_develop_full` | §4.1 `and scope` 가드 |
| inv-ISO-ENV | light 경로 실행 중 `AF_DISABLE_REGISTRY_WRITE`/`AGENT_PROJECT_ROOT`=worktree 설정됨 + 종료 후 복원 | `_develop_isolation_env` 적용 검증 (cross-review High) |

### 5.3 acceptance (실제 dogfood run — decision §Step 6)

1. leaf 함수 task — **파일경로 포함 실제 형식** (예: `"core/utils.py에 geometric_mean(values) 함수 추가, tests/test_utils.py에 TestGeometricMean 작성"`) → **light 경로** (orchestrator/외부 터미널 0개, 200+ cycle 미발생) + worktree 구현 + source 무변. (`core/utils.py`는 Tier2이므로 floor 미발동.)
2. sensitive 파일 변경 task (예: `core/providers/cli.py` Tier3) → blast_radius floor로 **full pipeline**.
3. `_router_llm` 예외 주입 run → **full fallback**.
4. 파일경로 없는 모호한 task → scope=[] → **full** (§4.1 가드).

검증 레버: `AGENT_CHAT_PROVIDER=claude_cli` 고정 (NOT `AF_SKIP_PROVIDER` — NEXT_STEPS 확인).

---

## 6. 동반 수정 (CLAUDE.md 규칙)

- `af.spec` `hiddenimports`에 `core.right_sized_router` 추가 (신규 core/*.py 필수)
- `Master_Blueprint.md` §0 빠른 참조 테이블(신규 파일) + §3 해당 서브시스템 + §10 Blast Radius(dogfood→right_sized_router 의존) + §12 이력
- 신규 `inspired_by:` 없음 (AF 자체 모듈)

---

## 7. 잔여 위험 / 감시 포인트

1. **scope 파생 누락**: `_scope_from_intent`가 sensitive 파일을 못 뽑으면 floor 우회 가능.
   완화 = scope 0건 → 저신뢰, Tier3 1개라도 → full. 그래도 의도 문자열에 파일명이 안 들어간 task는 한계.
   → acceptance run에서 sensitive task의 scope 파생을 직접 확인.
2. **ControlPlaneLLM workspace=os.getcwd()**: source root 가리킴. `allow_file_edit=False`로 무해하나
   leak 회귀 감시 포인트(NEXT_STEPS 등록). 슬라이스1 scope 밖이나 default=True 신규 코드 경계.
3. **classify LLM 비용**: DEVELOP마다 generate_json 1회 추가. leaf task엔 멀티에이전트 storm 대비 무시 가능
   하지만 full로 갈 task엔 순수 오버헤드. 측정 후 캐시/skip 검토(슬라이스2).
4. **premortem 무거움 가능성**: `run_premortem`이 scope 전체 AST 스캔. leaf 1함수엔 가벼우나
   대형 파일 scope면 비용. 측정 대상.

---

## 8. 구현 순서 (Sonnet 핸드오프)

```
1. tests/test_right_sized_router.py 작성 (RED) — §5.1 9케이스
2. core/right_sized_router.py 구현 (GREEN) — §3 전체
3. tests/test_dogfood.py 확장 (RED) — §5.2 5케이스
4. dogfood.py: _develop_isolation_env CM + _changed_files_fallback + _derive_verify_cmds 헬퍼 추출 (순수 refactor — _run_develop_phase의 인라인 env/fallback을 CM·헬퍼로 치환, 기존 테스트 GREEN 유지)
5. dogfood.py: _run_develop_full 추출(env→CM) + _run_develop_light 신규(CM 적용) + _run_develop_phase 라우터화(scope=[] 가드 포함) (GREEN)
6. DogfoodState.route_decision 필드 + 직렬화
7. af.spec + Blueprint §0/§3/§10/§12
8. acceptance dogfood run 3종 (§5.3)
9. 3-Tier: af-critic → af-cross-review → af-test-runner (core/ Tier3 → cross-review 필수)
```

설계 = Opus(본 문서). 구현 = `/model sonnet`.
```
```
