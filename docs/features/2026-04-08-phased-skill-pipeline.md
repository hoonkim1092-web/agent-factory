# Phased Skill Pipeline: spec → plan → build

> **상태**: 설계 (코드 수정 없음)
> **작성일**: 2026-04-08
> **영향 범위**: `core/project_pipeline.py`, `agent_launcher.py`, `core/dynamic_orchestrator.py`, `core/project_task_board.py`, `core/agent_specializer.py`

---

## 1. 목적

현재 `prepare()`가 한 번에 수행하는 spec + plan을 독립 phase로 분리하고,
`execute()`의 전체 실행도 슬라이스 단위 build로 전환하여
**각 단계에서 LLM 집중도를 높이고 사용자 개입점을 추가**한다.

### 현재 흐름 (2-Phase)

```
prepare()                              execute()
┌────────────────────────────┐        ┌──────────────────────────┐
│ research_evidence          │        │ sync_board_from_work_items│
│ project_brief       ← spec │        │ _materialize_roles       │
│ role_plan           ← plan │  →승인→ │ DynamicOrchestrator      │
│ task_board          ← plan │        │   .run_project() ← build │
│ work_items          ← plan │        │   (전체 한 번에 실행)      │
└────────────────────────────┘        └──────────────────────────┘
```

**문제:**
- LLM이 "뭘 만들지"와 "어떻게 만들지"를 동시에 요구받음
- 사용자 개입점이 1회(승인 게이트)뿐
- spec이 불확실한 채로 plan이 나오면 plan 전체가 흔들림
- build는 Lilith가 전체 board를 한 번에 오케스트레이션

### 변경 후 흐름 (3-Phase)

```
spec()                    plan()                    build()
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ research_evidence│     │ role_plan        │     │ 슬라이스 단위 실행 │
│ project_brief    │ →승인→ task_board       │ →승인→ 모듈 A 완료      │
│                  │     │ work_items       │     │ → 승인 → 모듈 B   │
│ "뭘 만들지"만     │     │ "어떻게 만들지"만  │     │ "한 번에 하나만"   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## 2. 설계 원칙

1. **하위호환 필수** — 기존 `prepare()` / `execute()` API를 깨지 않는다
2. **Canonical 유지** — board/role_plan 등 shared state 구조 변경 없음 (이전 설계 문서 원칙 계승)
3. **점진적 전환** — 1단계(파이프라인 분리)를 먼저 하고, 2단계(스킬 추출)는 이후
4. **각 Phase는 idempotent** — 같은 입력으로 재실행해도 같은 산출물

---

## 3. Phase 상세

### 3-1. Phase 1: spec()

**책임**: "뭘 만들지" 정의. 리서치 + 프로젝트 브리프 생성.

**입력**: `task_input` (사용자 요청 문자열)
**산출물**:
- `planning/research_evidence.json`
- `planning/project_brief.json`

**현재 코드 매핑**:
- `project_pipeline.py:535-618` (Research + Brief 부분)을 추출

```python
def spec(
    self,
    task_input: str,
    workspace: str,
    route: dict | None = None,
    requested_role: str = "",
) -> SpecResult:
    """Phase 1: 프로젝트 스펙 정의. 리서치 + 브리프만 생성."""
    # ... research_evidence 수집 ...
    # ... project_brief 생성 ...
    return SpecResult(
        workspace=workspace,
        project_brief=project_brief,
        research_evidence=research_evidence,
        # 경로들...
    )
```

**승인 게이트**:
- `spec()` 완료 후 사용자에게 `project_brief.json` 리뷰 요청
- 사용자가 brief를 수정할 수 있음 (목표, 제약조건, 스코프 조정)
- 승인 후 `plan()`으로 진행

**LLM 집중도 향상**:
- 현재: "리서치하고 브리프 쓰고 역할 분해하고 태스크 보드 만들어" (한 번에)
- 변경: "리서치하고 브리프만 써" → 사용자 검토 → 확정된 브리프로 다음 단계

---

### 3-2. Phase 2: plan()

**책임**: "어떻게 만들지" 계획. 확정된 brief 기반으로 역할 분해 + 태스크 보드 + work-item 생성.

**입력**: `SpecResult` (확정된 brief)
**산출물**:
- `planning/role_plan.json`
- `project_board_state.json`
- `docs/task_execution_plan.md`
- `docs/work-items/{slug}/*.md`
- `.todo.md`

**현재 코드 매핑**:
- `project_pipeline.py:620-695` (Planning + Board + Work Items 부분)을 추출

```python
def plan(
    self,
    spec_result: SpecResult,
    execution_mode: str = "approval",
) -> PlanResult:
    """Phase 2: 실행 계획 수립. 확정된 brief 기반."""
    # ... role_plan 생성 (ProjectPlanningDirector.plan()) ...
    # ... task_board 생성 (build_project_board()) ...
    # ... work_items 생성 (generate_work_items()) ...
    return PlanResult(
        spec=spec_result,
        role_plan=role_plan,
        task_board=task_board,
        # 경로들...
    )
```

**승인 게이트**:
- `plan()` 완료 후 사용자에게 work-item 문서 세트 리뷰 요청
- 사용자가 `implementation-tasks.md` 등을 편집 가능
- 승인 후 `build()`로 진행

**LLM 집중도 향상**:
- 현재: brief가 아직 불확실한 상태에서 plan을 짬 → hallucination
- 변경: 사용자가 확인/수정한 brief를 기반으로 plan → 정확도 상승

---

### 3-3. Phase 3: build()

**책임**: "한 번에 하나의 슬라이스만" 구현.

**입력**: `PlanResult` (확정된 plan) + `slice_id` (실행할 모듈/슬라이스)
**산출물**: 해당 슬라이스의 코드 + 테스트

**현재 코드 매핑**:
- `project_pipeline.py:701-800` (execute 부분)
- `dynamic_orchestrator.py:272` (_lilith_decide_next — 전체 board에서 다음 태스크 선택)

```python
def build(
    self,
    plan_result: PlanResult,
    slice_id: str | None = None,
    enable_build: bool = False,
    execution_mode: str = "approval",
) -> BuildResult:
    """Phase 3: 슬라이스 단위 구현."""
    # slice_id 없으면 → 다음 실행 가능 슬라이스 자동 선택
    # slice_id 있으면 → 해당 슬라이스만 실행
    #
    # 1. board에서 해당 슬라이스의 태스크 필터
    # 2. _materialize_roles() (해당 역할만)
    # 3. 오케스트레이션 (해당 태스크만)
    # 4. board 상태 갱신
    return BuildResult(
        slice_id=slice_id,
        ok=True/False,
        board=updated_board,
    )
```

**슬라이스 단위 실행의 핵심 변경**:

현재 `execute()`는 `DynamicOrchestrator.run_project()`를 **한 번** 호출하여 전체 프로젝트를 실행:
```python
# 현재 (project_pipeline.py:768)
run_board = orchestrator.run_project(task_input, roles, workspace)
```

변경 후 `build()`는 **모듈/슬라이스 단위**로 실행:
```python
# 변경 후
slice_tasks = filter_board_tasks(board, slice_id)
slice_roles = extract_roles_for_tasks(slice_tasks)
run_board = orchestrator.run_project(task_input, slice_roles, workspace,
                                      task_filter=slice_tasks)
```

**승인 게이트**:
- 각 슬라이스 완료 후 사용자에게 결과 리뷰 요청
- 다음 슬라이스 진행 여부 결정
- 실패 시 해당 슬라이스만 재실행 (전체 재실행 불필요)

---

## 4. 하위호환 전략

기존 `prepare()` / `execute()`를 유지하면서 내부적으로 새 phase를 사용.

```python
class ProjectPipeline:

    # ── 기존 API (하위호환) ──────────────────────
    def prepare(self, task_input, workspace, **kwargs) -> PreparedProject:
        """기존 호출자를 위한 래퍼. spec + plan을 한 번에 실행."""
        spec_result = self.spec(task_input, workspace, **kwargs)
        plan_result = self.plan(spec_result, **kwargs)
        return plan_result.to_prepared_project()

    def execute(self, prepared, **kwargs) -> dict:
        """기존 호출자를 위한 래퍼. 전체 build를 한 번에 실행.
        ★ 반환 타입 dict 유지 — 기존 호출자가 result.get("roles") 등 dict 키 접근.
        BuildResult를 기존 12-key dict로 변환하는 to_legacy_dict() 사용."""
        plan_result = PlanResult.from_prepared_project(prepared)
        build_result = self.build(plan_result, slice_id=None, **kwargs)
        return build_result.to_legacy_dict(prepared)

    # ── 새 API (3-Phase) ────────────────────────
    def spec(self, ...) -> SpecResult: ...
    def plan(self, ...) -> PlanResult: ...
    def build(self, ...) -> BuildResult: ...
```

**호출 경로 영향 분석**:

| 호출자 | 현재 경로 | 변경 영향 |
|--------|----------|----------|
| `agent_launcher.py:409` `project_pipeline.run()` | `prepare() + execute()` | 변경 없음 (래퍼) |
| `agent_launcher.py:417` `_run_project_with_approval()` | `prepare() → 승인 → execute()` | 변경 없음 (래퍼) |
| `interactive_chat.py:219` `_run_project_turn()` | `AgentFactory.run()` | 변경 없음 |
| **신규**: 3-Phase 직접 호출 | - | `spec() → plan() → build()` |

---

## 5. 결과 객체 설계

### SpecResult

```python
@dataclass
class SpecResult:
    run_id: str
    workspace: str
    project_brief: dict
    research_evidence: dict
    project_brief_path: str
    research_evidence_path: str
    doc_root: str = ""

    def summary_lines(self) -> list[str]:
        return [
            f"  목표: {self.project_brief.get('goal', '')}",
            f"  제약조건: {len(self.project_brief.get('constraints', []))}개",
            f"  required_skills: {self.project_brief.get('required_skills', [])}",
        ]
```

### PlanResult

```python
@dataclass
class PlanResult:
    spec: SpecResult
    role_plan: dict
    task_board: dict
    work_item_slug: str
    work_item_files: dict[str, str]
    planning_files: list[str]
    role_plan_path: str
    task_board_path: str
    task_execution_plan_path: str
    todo_path: str

    def to_prepared_project(self) -> PreparedProject:
        """하위호환: 기존 PreparedProject로 변환."""
        return PreparedProject(
            run_id=self.spec.run_id,
            workspace=self.spec.workspace,
            work_item_slug=self.work_item_slug,
            project_brief=self.spec.project_brief,
            role_plan=self.role_plan,
            task_board=self.task_board,
            planning_files=self.planning_files,
            work_item_files=self.work_item_files,
            project_brief_path=self.spec.project_brief_path,
            role_plan_path=self.role_plan_path,
            task_board_path=self.task_board_path,
            task_execution_plan_path=self.task_execution_plan_path,
            todo_path=self.todo_path,
            research_evidence=self.spec.research_evidence,
            research_evidence_path=self.spec.research_evidence_path,
            doc_root=self.spec.doc_root,  # ★ 누락 시 gate(), work_item_dir() 오류
        )

    @classmethod
    def from_prepared_project(cls, prepared: PreparedProject) -> "PlanResult":
        """하위호환: 기존 PreparedProject에서 복원.

        PreparedProject → PlanResult 필드 매핑:
        ┌─────────────────────────────────┬──────────────────────────────────────┐
        │ PreparedProject 필드            │ PlanResult 대응                      │
        ├─────────────────────────────────┼──────────────────────────────────────┤
        │ run_id                          │ spec.run_id                          │
        │ workspace                       │ spec.workspace                       │
        │ project_brief + project_brief_path │ spec.project_brief, spec.project_brief_path │
        │ research_evidence + research_evidence_path │ spec.research_evidence, spec.research_evidence_path │
        │ doc_root                        │ spec.doc_root                        │
        │ role_plan + role_plan_path      │ role_plan, role_plan_path            │
        │ task_board + task_board_path    │ task_board, task_board_path          │
        │ work_item_slug                  │ work_item_slug                       │
        │ work_item_files                 │ work_item_files                      │
        │ planning_files                  │ planning_files                       │
        │ task_execution_plan_path        │ task_execution_plan_path             │
        │ todo_path                       │ todo_path                            │
        └─────────────────────────────────┴──────────────────────────────────────┘

        주의: PreparedProject에는 SpecResult가 분리되어 있지 않으므로
        from_prepared_project()는 내부적으로 SpecResult를 먼저 재구성한 후
        나머지 plan 필드를 매핑해야 함.
        """
        spec = SpecResult(
            run_id=prepared.run_id,
            workspace=prepared.workspace,
            project_brief=prepared.project_brief,
            research_evidence=prepared.research_evidence,
            project_brief_path=prepared.project_brief_path,
            research_evidence_path=prepared.research_evidence_path,
            doc_root=prepared.doc_root,
        )
        return cls(
            spec=spec,
            role_plan=prepared.role_plan,
            task_board=prepared.task_board,
            work_item_slug=prepared.work_item_slug,
            work_item_files=prepared.work_item_files,
            planning_files=prepared.planning_files,
            role_plan_path=prepared.role_plan_path,
            task_board_path=prepared.task_board_path,
            task_execution_plan_path=prepared.task_execution_plan_path,
            todo_path=prepared.todo_path,
        )

    def slices(self) -> list[str]:
        """실행 가능한 슬라이스(모듈) ID 목록.
        ★ board.tasks의 module_id에서 추출 (role_plan.modules가 아님).
        이유: build_project_board() → enrich_role_plan()이 safe_id() 정규화를 적용하므로
        board가 정규화된 module_id의 실질적 source of truth.
        role_plan.modules는 LLM 응답 기반이라 modules 배열이 없을 수 있음."""
        tasks = self.task_board.get("tasks") or []
        return list(dict.fromkeys(
            t.get("module_id") for t in tasks
            if isinstance(t, dict) and t.get("module_id")
        ))

    def summary_lines(self) -> list[str]:
        roles = self.role_plan.get("roles") or []
        tasks = self.task_board.get("tasks") or []
        modules = self.role_plan.get("modules") or []
        return [
            f"  역할 수: {len(roles)}",
            f"  모듈 수: {len(modules)}",
            f"  작업 수: {len(tasks)}",
            f"  슬라이스: {self.slices()}",
        ]
```

### BuildResult

```python
@dataclass
class BuildResult:
    slice_id: str | None         # None이면 전체 실행
    ok: bool
    reason: str
    board: dict                  # 갱신된 board 상태
    roles_used: list[str]
    installed_skills: dict[str, list[str]]
    remaining_slices: list[str]  # 아직 실행 안 된 슬라이스

    def to_legacy_dict(self, prepared: "PreparedProject") -> dict:
        """execute() 래퍼용: 기존 호출자가 기대하는 12-key dict로 변환.
        agent_launcher.py:371 등에서 result.get("roles"), result.get("board") 사용."""
        return {
            "ok": self.ok,
            "reason": self.reason,
            "roles": self.roles_used,
            "board": self.board,
            "installed_skills": self.installed_skills,
            "project_brief_path": prepared.project_brief_path,
            "role_plan_path": prepared.role_plan_path,
            "task_board_path": prepared.task_board_path,
            "work_item_slug": prepared.work_item_slug,
            "changed_files": [],  # build에서 수집
        }
```

---

## 6. build() 슬라이스 실행 상세

### 슬라이스 선택 전략

```python
def _next_slice(self, plan_result: PlanResult) -> str | None:
    """의존성이 해소된 다음 슬라이스를 선택."""
    board = load_project_board(plan_result.spec.workspace)
    # ★ role_plan.modules가 아닌 board.tasks에서 module_id 집합 추출
    # 이유: build_project_board() → enrich_role_plan()이 safe_id() 정규화를 적용하므로
    #       board가 정규화된 module_id의 실질적 source of truth
    all_tasks = board.get("tasks") or []
    module_ids = list(dict.fromkeys(
        t.get("module_id") for t in all_tasks
        if isinstance(t, dict) and t.get("module_id")
    ))

    for module_id in module_ids:
        module_tasks = [t for t in all_tasks
                        if t.get("module_id") == module_id]
        # ★ 빈 태스크 목록 방어: all([]) == True이므로
        #    태스크가 없는 모듈은 "완료"로 오판됨 → 명시적 체크
        if not module_tasks:
            continue  # 태스크 없는 모듈은 스킵
        if all(t.get("status") == "completed" for t in module_tasks):
            continue  # 이미 완료
        # 의존 모듈이 모두 완료됐는지 확인
        # ★ board.modules[].depends_on 직접 사용 (태스크 역추적 불필요)
        deps = _get_module_depends_on(board, module_id)
        if all(_is_module_completed(board, dep) for dep in deps):
            return module_id  # 실행 가능

    return None  # 전부 완료 또는 blocked

def _get_module_depends_on(board: dict, module_id: str) -> list[str]:
    """board.modules에서 해당 모듈의 depends_on 반환. 신규 헬퍼."""
    for m in (board.get("modules") or []):
        if isinstance(m, dict) and m.get("id") == module_id:
            return [str(d) for d in (m.get("depends_on") or []) if d]
    return []

def _is_module_completed(board: dict, module_id: str) -> bool:
    """해당 모듈의 모든 태스크가 completed인지 확인. 신규 헬퍼.
    ★ 태스크가 0개인 모듈은 False 반환 (all([]) 방어)."""
    tasks = [t for t in (board.get("tasks") or [])
             if isinstance(t, dict) and t.get("module_id") == module_id]
    return bool(tasks) and all(t.get("status") == "completed" for t in tasks)
```

**주의 사항**:
- `all([]) == True` 버그: 태스크가 0개인 모듈은 `all()` 호출 시 `True`를 반환하여 "완료"로 오판됨. `not module_tasks` 가드 + `_is_module_completed()`에서 `bool(tasks)` 체크 필수.
- 모듈 의존성: `board.modules[].depends_on`이 이미 모듈 ID 목록으로 존재 (`build_project_board():420`에서 `safe_id()` 적용됨). 태스크 `depends_on`에서 역추적하는 것보다 직접 읽는 것이 단순하고 정확.

### DynamicOrchestrator 변경

현재 `run_project()`는 전체 역할을 받아 전체 board를 실행:
```python
# 현재 (dynamic_orchestrator.py)
def run_project(self, task_input, roles, workspace):
```

슬라이스 필터 파라미터 추가:
```python
# 변경 후
def run_project(self, task_input, roles, workspace, task_filter=None):
    # task_filter가 있으면 해당 task_id만 실행
    # _lilith_decide_next()에서 task_filter 범위 내에서만 선택
```

**Lilith 프롬프트 변경**:
- 현재: `_lilith_decide_next()` (:272)이 전체 board + .todo.md + mailbox를 LLM에 로드
- 변경: `task_filter`가 있으면 해당 모듈의 태스크만 표시
  → **토큰 절감**: 전체 board 대신 슬라이스 범위만 로드

**필터링 적용 포인트 3곳** (누락 시 Lilith가 슬라이스 밖 태스크를 배정함):

1. **`board_prompt_digest()`** (:649) — `module_id` 필터 파라미터 추가 필요
   현재 시그니처: `board_prompt_digest(board, max_tasks=12, max_instruction_chars=200)`
   변경: `board_prompt_digest(board, max_tasks=12, max_instruction_chars=200, module_filter=None)`
   → `project_task_board.py`가 변경 대상이 되는 이유

2. **`.todo.md` 로드** — `_lilith_decide_next()`가 .todo.md 전체를 읽는데,
   슬라이스 모드에서는 해당 모듈의 섹션만 추출하거나,
   또는 rule-based `_dispatch_from_board()` 바이패스로 LLM 호출 자체를 생략 가능
   (슬라이스 내 태스크가 명확하므로 LLM 판단 불필요한 경우)

3. **`next_board_tasks()`** (:518) — `module_filter` 화이트리스트 파라미터 추가
   현재: `next_board_tasks(board, available_roles, completed_ids)`
   변경: `next_board_tasks(board, available_roles, completed_ids, module_filter=None)`
   → `_fallback_next_tasks()` (:183) 경로에서도 슬라이스 범위 준수

**filter 전파 체인** (시그니처 변경 필수):
```
run_project(task_filter)
  → _orchestration_loop(task_filter)    # 시그니처 추가
    → _lilith_decide_next(task_filter)  # :272 시그니처 추가
      → board_prompt_digest(board, module_filter=task_filter)
    → _fallback_next_tasks(task_filter) # :183 시그니처 추가
      → next_board_tasks(board, roles, completed, module_filter=task_filter)
    → _dispatch_from_board(task_filter) # :240 시그니처 추가
      → _fallback_next_tasks(task_filter)
```
★ 이 체인의 모든 시그니처가 변경되어야 슬라이스 밖 태스크 배정이 차단됨.

**대안 검토**: 슬라이스 실행 시 Lilith를 우회하고 rule-based 디스패치만 사용하는 방식.
`_dispatch_from_board()` (:240)는 현재 2줄짜리 래퍼로 `_fallback_next_tasks()`를 호출할 뿐이며,
module_filter 없이는 슬라이스 밖 태스크도 배정됨. 바이패스를 사용하려면
`_dispatch_from_board()`에도 `module_filter` 전달이 필수.

---

## 7. 사용자 인터페이스 흐름

### CLI 흐름 (af.exe)

현재 argparse 구조 (`run_factory_cli.py:195-213`):
- 태스크 입력: `--task` / `-t` 플래그 (positional이 아님)
- 파이프라인 모드: `--pipeline` choices=["auto", "single", "project"]
- 실행 모드: `--mode` choices=["approval", "fsa", "ise"]

`--phased`는 `--pipeline` 선택지에 추가하는 것이 자연스러움:
```python
# run_factory_cli.py 변경
parser.add_argument("--pipeline", choices=["auto", "single", "project", "phased"],
                    default="auto", help="Pipeline mode")
```

```
$ af -p my-project --task "JWT 인증 시스템 만들어줘" --pipeline phased

[spec] 리서치 중...
[spec] 완료. 프로젝트 브리프:
  목표: JWT 인증 시스템 (access + refresh token rotation)
  제약조건: FastAPI, PostgreSQL
  required_skills: [fastapi_server, jwt_auth, db_migration]

브리프를 수정하시겠습니까? (y/N/edit): N

[plan] 역할 분해 중...
[plan] 완료.
  역할: backend_engineer, qa_engineer
  모듈: auth_schema(0 deps) → token_service(1 dep) → auth_middleware(1 dep)
  작업: 8개

work-item 문서를 수정하시겠습니까? (y/N/edit): N

[build] 다음 슬라이스: auth_schema (의존성 없음)
  실행 중... 완료 ✓

[build] 다음 슬라이스: token_service (auth_schema 완료)
  실행 중... 완료 ✓

[build] 다음 슬라이스: auth_middleware (token_service 완료)
  실행 중... 실패 ✗
  → auth_middleware만 재실행하시겠습니까? (Y/n): Y
  실행 중... 완료 ✓

[완료] 3/3 슬라이스 완료.
```

### 기존 호출 (하위호환)

```
$ af -p my-project --task "JWT 인증 시스템 만들어줘"
# --pipeline auto (기본값) → 기존 동작: prepare() → 승인 → execute()
```

---

## 8. 2단계 확장: 스킬 시스템 추출 (미래)

1단계(이 문서)의 파이프라인 분리가 안정화되면,
각 phase를 스킬로 추출하여 에이전트가 자율적으로 호출 가능하게 확장.

```
현재 스킬 타입:     action (코드 실행) | knowledge (정보 제공)
추가 스킬 타입:     workflow (phase 실행)
```

| 스킬 | 타입 | 입력 | 산출물 |
|------|------|------|--------|
| `project-spec` | workflow | task_input | SpecResult (brief) |
| `project-plan` | workflow | SpecResult | PlanResult (board + work-items) |
| `project-build` | workflow | PlanResult + slice_id | BuildResult |

workflow 스킬은 **artifact 전달 체인**이 필요:
- 스킬 간 결과 객체를 전달하는 메커니즘
- 중간 산출물의 파일 기반 직렬화/역직렬화
- 현재 `SpecResult` / `PlanResult`는 이미 이를 고려한 설계

이 확장은 별도 설계 문서에서 다룬다.

---

## 9. 변경 파일 및 영향 범위

| 파일 | 변경 내용 | 난이도 |
|------|----------|--------|
| `core/project_pipeline.py` | `spec()`, `plan()`, `build()` 메서드 추출 + `prepare()`/`execute()` 래퍼화 | 중간 |
| `core/project_pipeline.py` | `SpecResult`, `PlanResult`, `BuildResult` dataclass 추가 | 낮음 |
| `core/dynamic_orchestrator.py` | `run_project()` `task_filter` 파라미터 추가 | 낮음 |
| `core/dynamic_orchestrator.py` | `_lilith_decide_next()` 필터 적용 | 낮음 |
| `agent_launcher.py` | `_run_project_with_approval()` 3-phase 분기 추가 | 중간 |
| `run_factory_cli.py` | `--pipeline phased` 선택지 추가 | 낮음 |
| `core/project_task_board.py` | `next_board_tasks()` `module_filter` 파라미터 추가, `board_prompt_digest()` `module_filter` 파라미터 추가 | 낮음 |

**주의**: `project_task_board.py`는 canonical board **구조** 변경이 아닌 **조회 함수 시그니처** 확장.
기존 호출자는 `module_filter=None` 기본값으로 동작이 변하지 않음 (하위호환).

**건드리지 않는 파일**:
- `project_task_board.py` 의 board JSON 스키마 — canonical 구조 변경 없음
- `work_item_generator.py` — 기존 로직 유지
- `bootstrap_roles.py` — PlanningDirector 변경 없음
- `agent_specializer.py` — worker 프롬프트 구조 변경 없음 (이미 task 단위 프롬프트)

---

## 10. 구현 우선순위

| 순서 | 내용 | 이유 |
|------|------|------|
| **P0** | `SpecResult` / `PlanResult` / `BuildResult` dataclass | 다른 모든 작업의 기반 |
| **P1** | `spec()` 추출 | `prepare()`에서 Research+Brief 부분 분리 |
| **P2** | `plan()` 추출 | `prepare()`에서 Planning+Board+WorkItems 부분 분리 |
| **P3** | `prepare()` 래퍼화 | `spec() + plan()` 호출로 변경 (하위호환) |
| **P4** | `build()` 슬라이스 실행 | `execute()` + `DynamicOrchestrator` task_filter |
| **P4** | `project_task_board.py` 조회 함수 확장 | `next_board_tasks()` + `board_prompt_digest()` module_filter 추가 |
| **P4** | Lilith 슬라이스 필터링 | board_prompt_digest + .todo.md + next_board_tasks 3곳 |
| **P5** | `execute()` 래퍼화 | `build(slice_id=None)` 호출로 변경 (하위호환) |
| **P6** | CLI `--pipeline phased` | 기존 argparse `--pipeline` 선택지 확장 |

---

## 11. enrich_role_plan() 타이밍 주의

`plan()` 내부에서 `build_project_board()`가 호출되면 `enrich_role_plan()`이 실행되어
`safe_id()` 정규화 + module 구조 보강이 일어남. 이 시점 이후의 `role_plan`과 `task_board`는
정규화된 ID를 사용하므로, `spec()` 단계에서 생성한 `project_brief`의 원본 식별자와
`plan()` 이후의 정규화된 식별자가 다를 수 있음.

**구현 시 주의**: `PlanResult`는 반드시 `enrich_role_plan()` 이후의 정규화된 `role_plan`을 보유해야 함.
`SpecResult`의 `project_brief`는 원본 그대로 유지 (사용자가 수정/승인한 버전).

---

## 12. 체크리스트

- [ ] P0: `SpecResult`, `PlanResult`, `BuildResult` dataclass 정의
- [ ] P0: `PlanResult.from_prepared_project()` 역직렬화 + `to_prepared_project()` 전체 필드 매핑
- [ ] P0: `BuildResult.to_legacy_dict()` — execute() 래퍼용 dict 변환
- [ ] P1: `spec()` 메서드 — research + brief 추출
- [ ] P2: `plan()` 메서드 — planning + board + work-items 추출
- [ ] P3: `prepare()` → `spec() + plan()` 래퍼화, 기존 테스트 통과 확인
- [ ] P4: `build()` 메서드 — 슬라이스 단위 실행
- [ ] P4: `_next_slice()` — `all([]) == True` 방어 + board 기반 module_id 추출
- [ ] P4: `_get_module_depends_on()` + `_is_module_completed()` 신규 헬퍼 구현
- [ ] P4: `DynamicOrchestrator.run_project()` task_filter 추가
- [ ] P4: `project_task_board.py` — `next_board_tasks()` + `board_prompt_digest()` module_filter 파라미터 추가
- [ ] P4: Lilith 프롬프트 슬라이스 필터링 (board_prompt_digest + .todo.md + next_board_tasks 3곳)
- [ ] P4: filter 전파 체인 시그니처 변경 (run_project → _orchestration_loop → _lilith_decide_next → _fallback_next_tasks → _dispatch_from_board)
- [ ] P5: `execute()` → `build(slice_id=None)` 래퍼화, 기존 테스트 통과 확인
- [ ] P6: CLI `--pipeline phased` 선택지 추가 (기존 argparse 구조에 맞춤)
- [ ] 전체: Master_Blueprint.md §2 실행 흐름, §3.1 ProjectPipeline 업데이트
