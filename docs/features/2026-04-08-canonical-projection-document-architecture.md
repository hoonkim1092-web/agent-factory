# Canonical + Projection 문서 아키텍처

> **상태**: 설계 (코드 수정 없음)
> **작성일**: 2026-04-08
> **영향 범위**: `core/project_pipeline.py`, `core/skill_procurer.py`, `core/project_task_board.py`, `core/dynamic_orchestrator.py`, `core/work_item_generator.py`

---

## 1. 목적

프로젝트 실행 시 생성되는 문서를 에이전트별로 더 잘게 쪼개되,
런타임 제어면(shared board)은 canonical로 유지하고
그 위에 역할별 projection 뷰를 추가한다.

### 해결하는 문제

| 문제 | 현재 상태 | 해결 방향 |
|------|----------|----------|
| 스킬 조달 추적 불가 | agent YAML `skills` 필드에 ID만 나열 | `skill_manifest.json`에 조달 이유/모드 기록 |
| 역할 정보 산재 | role_plan.json 배열 + agent YAML `project_role` 중복 | `role_spec.json`으로 단일 파생 뷰 |
| worker에 불필요한 board 로드 | agent_specializer가 이미 task 중심이지만 명시적 뷰 없음 | `task_view.json` 읽기 전용 필터 |
| work-item이 프로젝트 단위 1세트 | QA/integration 역할에 어색 | 모듈 단위로 재편 |

---

## 2. 설계 원칙

1. **Canonical은 건드리지 않는다**
   - `project_board_state.json` — 런타임 제어면, `locked_file()` 동시 쓰기 보호
     (★ 주의: `write_project_board()`는 현재 `open("w")` 직접 쓰기로, tempfile+os.replace 패턴이 아님.
     `locked_file()`이 동시 접근은 막아주지만 쓰기 중 프로세스 종료 시 파일 손상 가능.
     projection의 atomic write와 대비되는 불일치이나, board는 이 설계의 변경 범위가 아님)
   - `planning/role_plan.json` — 모든 역할의 single source
   - `planning/project_brief.json` — 프로젝트 전체 컨텍스트

2. **Projection은 파생 뷰다**
   - canonical에서 필터/추출한 읽기 전용 문서
   - projection이 stale해도 런타임에 영향 없음 (canonical이 진실)
   - 재생성 가능해야 함 (idempotent)

3. **별도 source of truth를 만들지 않는다**
   - `dependency_graph.json` 같은 별도 그래프 파일 금지
   - 의존성은 이미 `board.tasks.depends_on`에 있음

---

## 3. 변경 후 디렉토리 구조

```
projects/{project}/
├── planning/                           ← canonical (변경 없음)
│   ├── project_brief.json
│   ├── research_evidence.json
│   └── role_plan.json
│
├── project_board_state.json            ← canonical (변경 없음)
│
├── agents/{role_id}/                   ← ★ projection layer (신규)
│   ├── role_spec.json                  파생 뷰: role_plan → 해당 역할만 추출
│   ├── task_view.json                  파생 뷰: board → owner_role 필터
│   └── skill_manifest.json             조달 로그: procure 결과 기록
│
├── docs/
│   ├── work-items/{module_slug}/       ← ★ 모듈 단위로 재편
│   │   ├── feature-plan.md
│   │   ├── feature-spec.md
│   │   ├── implementation-design.md
│   │   ├── implementation-tasks.md
│   │   └── approval-gate.md
│   ├── architecture.md
│   └── change_history.md
│
├── .todo.md
└── docs/task_execution_plan.md
```

---

## 4. 각 projection 파일 상세

### 4-1. `agents/{role_id}/role_spec.json`

**생성 시점**: `_materialize_roles()` 내부, `write_yaml(agent_path, agent_data)` (:482) 직후
**생성 위치**: `core/project_pipeline.py:482` 이후

```jsonc
{
  "role_id": "backend_engineer",
  "name": "Backend Engineer",
  "objective": "REST API 서버 구축",
  "required_skills": ["fastapi_server", "db_migration"],
  "owned_modules": ["api_server", "database"],
  "feature_slices": ["auth_endpoint", "crud_operations"],
  "planning_steps": ["scope_contracts", "impl_api"],  // ★ 글로벌 필드 — 전 역할 동일 (역할별 필터 아님)
  "source": "planning/role_plan.json",       // 출처 명시
  "generated_at": "2026-04-08T12:00:00Z"
}
```

**현재 코드와의 관계**:
- 지금도 `_materialize_roles():470-481`에서 거의 동일한 정보를 `agent_data["project_role"]`에 씀
- 차이점: agent YAML은 에이전트 설정(persona, skills, signature 등)과 섞여 있음
- `role_spec.json`은 **역할 계약만 분리**한 깨끗한 뷰
- **주의**: `planning_steps`는 `role_plan.get("planning_steps")`에서 가져오는 글로벌 필드로, 모든 역할에 동일한 리스트가 복사됨. 역할별 단계가 아님.

**구현 시 변경점**:
- `_materialize_roles()` line 482 직후에 `role_spec.json` 쓰기 추가
- `agents/{role_id}/` 하위 디렉토리는 `_materialize_roles()` 루프 시작에서 미리 생성
  (★ 기존 `agents/{role_id}.yaml` 파일과 `agents/{role_id}/` 디렉토리가 공존함.
  파일시스템에서 `backend_engineer.yaml`과 `backend_engineer/`은 이름이 다르므로 문제 없음)
- 경로 생성 시 `safe_id(role_id)` 적용 필수 (role_name에 한글/공백 가능)
- 기존 `agent_data["project_role"]` 로직은 유지 (하위호환)
- atomic write 사용 (tempfile + os.replace) — non-atomic write 확산 방지

---

### 4-2. `agents/{role_id}/task_view.json`

**생성 시점**: board 상태 변경 시 (`update_project_board_task()` 호출 후)
**생성 위치**: `core/project_task_board.py:558` `update_project_board_task()` 반환 직전, 또는 orchestration 루프의 턴 시작 시점에서 별도 호출

```jsonc
{
  "role_id": "backend_engineer",
  "tasks": [
    {
      "task_id": "impl_auth_api",
      "instruction": "JWT 인증 엔드포인트 구현",
      "status": "pending",
      "depends_on": ["setup_db_schema"],
      "phase": "build"
    }
  ],
  "summary": {
    "total": 5,
    "pending": 3,
    "in_progress": 1,
    "completed": 1
  },
  "filtered_from": "project_board_state.json",
  "generated_at": "2026-04-08T12:00:00Z"
}
```

**현재 코드와의 관계**:
- `board_prompt_digest()` (:649)가 이미 전체 board를 텍스트 요약하는 함수
- `_lilith_decide_next()` (:272)는 `next_board_tasks()`를 직접 호출하지 않음 — LLM에 위임
- `next_board_tasks()` (:518)는 `_fallback_next_tasks()` (:183) 경로에서 호출됨
- `task_view.json`은 canonical board에서 `owner_role` 필터링한 **파일 캐시**

**구현 시 변경점**:
- `update_project_board_task()` 완료 후 해당 role의 task_view를 재생성 (상태 변경 트리거)
- 또는 orchestration 루프 턴 시작 시 전체 역할의 task_view 일괄 갱신 (권장)
- **locked_file 컨텍스트 주의**: `update_project_board_task()` 내부는 `locked_file(board_path)` 블록(:560-589) 안에서 실행됨.
  task_view는 projection(캐시)이므로 lock 블록 **바깥**에서 생성해야 함.
  lock 블록 밖에서 생성하려면 board 데이터를 반환받거나 다시 읽어야 하므로,
  **orchestration 루프 턴 시작 시 일괄 갱신 패턴이 더 단순**함.
- **재생성 대상 role 판별**: `update_project_board_task()`의 `role` 파라미터 대신,
  실제 변경된 task의 `owner_role` 필드를 board에서 직접 읽어야 정확함
  (task_id 기반 매칭 시 role 파라미터가 무시될 수 있음, :573-576)
- atomic write 사용 (tempfile + os.replace) — partial/corrupt JSON 파싱 에러 방지
- **읽기 전용**: worker가 이 파일을 수정하지 않음, board 갱신은 항상 canonical 경유
- `agent_specializer.py`에서는 task_view를 **참조하지 않음** (이미 task 단위 프롬프트 구성)
  → task_view는 디버깅/모니터링 용도로만 활용
- `_fallback_next_tasks()` (:183) 경로에서도 canonical board를 직접 읽으므로 task_view 도입은 런타임 성능에 영향 없음

**주의**: 이 파일은 순수 캐시/뷰. stale해도 실제 스케줄링은 canonical board 기준.

---

### 4-3. `agents/{role_id}/skill_manifest.json` ★ 가장 시급

**생성 시점**: `procure_multiple()` 완료 후
**생성 위치**: `core/skill_procurer.py:886-1144` 반환 직전

```jsonc
{
  "role_id": "backend_engineer",
  "run_id": "project_run_1712563200_backend_engineer",
  "skills": [
    {
      "skill_id": "fastapi_server",
      "requested": true,
      "installed": true,
      "decision_mode": "exact_match",       // exact_match/ranked_reuse/enhance/enhance_fallback_forge/shadow_reuse/external_install/forge
      "reused_from": null,
      "forge_run_id": null,
      "lifecycle_state": "active",
      "resolved_at": "2026-04-08T12:01:00Z"
    },
    {
      "skill_id": "db_migration",
      "requested": true,
      "installed": true,
      "decision_mode": "forge",
      "reused_from": null,
      "forge_run_id": "forge_db_migration_1712563205",
      "lifecycle_state": "candidate",
      "resolved_at": "2026-04-08T12:01:30Z"
    }
  ],
  "summary": {
    "requested": 2,
    "installed": 2,
    "by_mode": { "exact_match": 1, "forge": 1 }
  },
  "generated_at": "2026-04-08T12:02:00Z"
}
```

**현재 코드의 문제**:
- `manager.py:87-104` `install_skills()`는 agent YAML의 `skills` 배열에 ID만 append
- "왜 이 스킬이 붙었는지" (reuse? forge? enhance?) 정보가 사라짐
- `procure_multiple()`는 installed 리스트만 반환, 조달 경로 정보 미보존

**구현 시 변경점**:

`procure_multiple()` 내부 7개 분기(exact_match, ranked_reuse, enhance, enhance_fallback_forge, shadow_reuse, external_install, forge)에서
각 스킬의 조달 경로를 수집해야 함.

**수집 메커니즘** (구체적 패턴):
- `procure_multiple()` 상단에 `manifest_entries: list[dict] = []` accumulator 선언
- 각 분기에서 `_record_selection_feedback()` 호출 **직후**에 `manifest_entries.append({...})` 직접 호출
- ★ `_record_selection_feedback()` 확장이 아님 — 이 함수는 반환값 없는 side-effect 전용이고 시그니처 변경이 복잡함
- `procure_multiple()` 반환 시 `manifest_entries`를 함께 반환: 반환 타입을 `tuple[list[str], list[dict]]`로 변경
- 하위호환: `_materialize_roles()` line 490의 호출부만 수정하면 됨 (유일한 호출처)

**두 가지 저장 경로 모두 커버 필수**:
- `enable_build=True` 경로 (:484-499): `procure_multiple()` 내부에서 수집 → 반환
- `enable_build=False` 경로 (:500-502): `install_skills()` 직접 호출 — `_materialize_roles()` 내 `elif required_skills:` 블록 이후에 `decision_mode="direct_install"`로 단순 entry 생성

**manifest 저장 위치**: `_materialize_roles()` 내에서 `procure_multiple()` 반환 또는 `install_skills()` 호출 이후에 저장.
`procure_multiple()`은 `workspace`가 Optional이고 `role_id`를 시그니처에서 직접 받지 않으나,
반환 타입 확장으로 manifest 데이터를 호출자에게 전달하는 것이 가장 깔끔함.

**난이도**: 중간 (7개 분기 * 1-2줄 + 반환 타입 변경 + manifest 구성/저장 = ~20-25줄)

---

## 5. work-item 모듈 단위 재편

### 현재

```
docs/work-items/{project_slug}/
    ├── feature-plan.md          ← 프로젝트 전체를 한 세트로
    ├── feature-spec.md
    ├── implementation-design.md
    ├── implementation-tasks.md
    └── approval-gate.md
```

### 변경 후

```
docs/work-items/
    ├── {module_slug_1}/         ← 모듈 단위로 분리
    │   ├── feature-plan.md
    │   ├── feature-spec.md
    │   ├── implementation-design.md
    │   ├── implementation-tasks.md
    │   └── approval-gate.md
    ├── {module_slug_2}/
    │   └── ...
    └── _overview.md             ← 모듈 간 관계 요약 (선택)
```

**근거**:
- `role_plan.json`의 `modules` 배열에 `owner_role`, `feature_slices`, `tasks`가 모듈별로 구조화되도록 LLM에 프롬프트로 지시함 (`bootstrap_roles.py:424-442` — 주의: 이 부분은 프롬프트 템플릿이므로 LLM 응답이 이 스키마를 따르지 않을 수 있음)
- **modules 없음 fallback**: `_fallback_roles()` (:201-205) 반환 dict에는 `modules` 키가 아예 없음 → `role_plan.get("modules") or []`가 빈 리스트 반환 → 모든 역할의 `owned_modules`가 빈 배열. **fallback 정책**: modules가 없으면 work-item을 프로젝트 단위 1세트로 생성 (기존 동작 유지). 모듈 재편은 modules 배열이 있을 때만 적용.
- `generate_work_items()`(:478)에 `project_brief` + `role_plan` + `task_board` 전체가 들어가는데, 모듈 단위로 필터링하여 호출하면 됨
- QA 역할은 `bootstrap_roles.py:473-474`에서 반드시 모듈(verify 모듈)을 소유하도록 강제됨. 따라서 QA도 모듈별 work-item 구조에 자연스럽게 맞음. 단, QA의 verify 모듈이 cross-cutting인 경우 별도 처리 검토 필요

**구현 시 변경점**:
- `generate_work_items()` 시그니처에 `module_filter: str | None` 추가
- `prepare()`에서 모듈별 루프로 `generate_work_items()` 호출
- `sync_board_from_work_items()`의 work_dir 탐색 로직을 모듈별로 확장
- `ApprovalGate`도 모듈별로 생성 (또는 프로젝트 레벨 1개 유지 — 추후 결정)

---

## 6. 구현 우선순위

| 순서 | 항목 | 난이도 | 영향 범위 | 이유 |
|------|------|--------|----------|------|
| **P0** | `skill_manifest.json` | 낮음 | `skill_procurer.py` | 지금 당장 추적성 부재. 3-5줄 추가로 해결 |
| **P1** | `role_spec.json` | 낮음 | `project_pipeline.py` | `_materialize_roles()`에 3줄 추가. 기존 로직 변경 없음 |
| **P2** | `task_view.json` | 중간 | `dynamic_orchestrator.py` | 캐시 전략 결정 필요 (매 턴? 상태 변경 시?) |
| **P3** | work-item 모듈 재편 | 높음 | `work_item_generator.py`, `work_item_parser.py`, `project_pipeline.py`, `approval_gate.py` | 기존 slug 기반 경로 전체 수정 필요 |

---

## 7. 건드리지 않는 것 (명시적 제외)

| 항목 | 이유 |
|------|------|
| `project_board_state.json` 분할 | 런타임 제어면. `locked_file()` 원자성, cross-role 의존성 해소 로직 전면 재작성 필요 |
| `planning/role_plan.json` 분할 | work-item 생성의 입력. 분할하면 글로벌 문맥 소실 |
| 별도 `dependency_graph.json` | `board.tasks.depends_on`과 이중 관리 → drift 위험 |
| Lilith 프롬프트의 board 로드 축소 | 오케스트레이터는 전체 상태를 봐야 함. 토큰 최적화는 `board_prompt_digest()` 개선으로 대응 |

---

## 8. 체크리스트

- [ ] P0: `skill_manifest.json` — `procure_multiple()` 조달 경로 수집 + dump
- [ ] P1: `role_spec.json` — `_materialize_roles()` 끝에 파생 뷰 쓰기
- [ ] P2: `task_view.json` — 캐시 전략 결정 후 `dynamic_orchestrator.py`에 추가
- [ ] P3: work-item 모듈 재편 — `generate_work_items()` 시그니처 변경 + 루프 호출
- [ ] P3: `sync_board_from_work_items()` 모듈별 탐색 확장
- [ ] P3: `ApprovalGate` 모듈별/프로젝트별 전략 결정
- [ ] 전체: Master_Blueprint.md §3 서브시스템 업데이트
- [ ] 전체: code-review.md 반영
