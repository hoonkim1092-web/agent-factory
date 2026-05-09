# 코드 리뷰 및 교차검증 파이프라인 설계

> 생성일: 2026-04-16
> 상태: draft (v2 — critic BLOCK 6건 + doc-qa Critical 2건 반영)
> 영향 범위: core/dynamic_orchestrator.py, core/project_task_board.py, core/agent_runner.py, core/providers/registry.py, core/documentation_policy.py, core/work_item_generator.py

## 1. 문제

현재 AF의 검증 체계는 QA Engineer(테스트 작성/실행)만 존재한다.
- 코드 품질/보안/설계 리뷰가 누락
- 작성자와 다른 CLI 모델에 의한 교차검증이 없음
- QA는 "테스트 통과 여부"만 확인하고 코드 자체를 리뷰하지 않음

### 1.1 기존 교차검증 체계와의 관계

AF에는 두 계층의 교차검증이 존재한다:

| 계층 | 메커니즘 | 대상 | 트리거 |
|------|---------|------|--------|
| **사람 수준** | af-critic + af-cross-review (CLAUDE.md hook) | AF 코어 코드 (`core/*.py`) | PostToolUse → UserPromptSubmit |
| **에이전트 수준 (신규)** | Code Reviewer + Cross Validator (오케스트레이션 내부) | AF가 생성하는 프로젝트 코드 | build 완료 후 자동 |

이 설계는 **에이전트 수준** 교차검증을 추가한다. 사람 수준 검증과 독립적으로 동작하며 대체하지 않는다.

## 2. 설계

### 2.1 역할 구조

각 구현 역할(Dev)마다 전담 검증 3종이 자동 생성된다:

```
{Role} Dev (provider-A)
  ├── {Role} QA (provider-B)              — 테스트 작성/실행
  ├── {Role} Code Reviewer (provider-B)    — 코드 품질/보안/설계 리뷰
  └── {Role} Cross Validator (provider-A 또는 B) — 전체 교차검증
```

용어: CLI-A/B 대신 기존 코드베이스의 `provider` 용어를 사용한다.

### 2.2 CLI provider 교차 선택: `pick_review_provider()`

`core/providers/registry.py`에 추가:

```python
def pick_review_provider(author_provider: str) -> str:
    """작성자와 다른 CLI provider를 반환한다. 없으면 같은 provider를 반환."""
    available = detect_available_cli_providers()
    candidates = [p for p in available if p != author_provider]
    if candidates:
        return candidates[0]  # 첫 번째 사용 가능한 다른 provider
    return author_provider  # 폴백: 같은 provider, 별도 세션 (독립 run_id)
```

폴백 동작: 같은 provider라도 **다른 run_id**로 실행되므로 이전 세션 컨텍스트가 없는 독립 세션이 보장된다.

### 2.3 CLI 환경별 폴백 정책

| 설치된 CLI 수 | Code Reviewer | Cross Validator |
|--------------|---------------|-----------------|
| 3개 (claude+codex+gemini) | 다른 provider | 또 다른 provider |
| 2개 (claude+codex) | 다른 provider | **Code Reviewer와 같은 provider** (별도 세션) |
| 1개 | 같은 provider (별도 세션) | **생략** — QA + Code Reviewer로 충분 |

1개 환경에서 Cross Validator를 생략하는 이유: 같은 모델의 같은 편향으로 2회 리뷰하는 것보다 Code Reviewer 1회에 집중하는 것이 효율적.

### 2.4 phase 확장

기존 `integrate` phase는 **유지**하되, 새 phase를 추가한다:

```python
_PHASE_ORDER = {
    "scope": 0,
    "build": 1,
    "integrate": 2,       # 기존 유지 (수동 사용 시 호환)
    "code_review": 3,
    "cross_validate": 4,
    "verify": 5,
}
```

`core/work_item_generator.py:98`의 `phase_order`도 동일하게 업데이트한다.

**기존 호환성**: `integrate` phase를 사용하는 기존 board는 정상 동작한다. code_review/cross_validate는 자동 주입되므로 `_task_template()`의 기본 3단계(scope/build/verify)는 변경하지 않는다.

### 2.5 태스크 자동 주입 메커니즘

`core/project_task_board.py`에 추가:

```python
def inject_review_tasks(workspace: str, completed_task: dict) -> list[dict]:
    """build phase 태스크 완료 시 code_review + cross_validate 태스크를 board에 주입한다."""
    if completed_task.get("phase") != "build":
        return []

    module_id = completed_task.get("module_id", "")
    owner_role = completed_task.get("owner_role", "")
    build_task_id = completed_task.get("task_id", "")

    review_tasks = []

    # Code Review 태스크
    cr_task_id = f"{module_id}_code_review"
    review_tasks.append({
        "task_id": cr_task_id,
        "module_id": module_id,
        "owner_role": f"{owner_role}_code_reviewer",  # 예: backend_dev_code_reviewer
        "phase": "code_review",
        "instruction": f"[Code Review] {module_id} build 산출물의 코드 품질을 리뷰한다.",
        "depends_on": [build_task_id],
        "status": "pending",
    })

    # Cross Validate 태스크 (CLI 2개 이상일 때만)
    available_providers = detect_available_cli_providers()
    if len(available_providers) >= 2:
        cv_task_id = f"{module_id}_cross_validate"
        review_tasks.append({
            "task_id": cv_task_id,
            "module_id": module_id,
            "owner_role": f"{owner_role}_cross_validator",
            "phase": "cross_validate",
            "instruction": f"[Cross Validate] {module_id} 전체 정합성을 교차검증한다.",
            "depends_on": [cr_task_id],
            "status": "pending",
        })

    # verify 태스크의 depends_on 업데이트
    _update_verify_dependency(workspace, module_id, review_tasks[-1]["task_id"])

    # board에 주입
    _append_tasks_to_board(workspace, review_tasks)
    return review_tasks
```

호출 위치: `dynamic_orchestrator.py`의 `_execute_agent_task` 완료 핸들러 내부.

### 2.6 역할 동적 등록

Code Reviewer/Cross Validator 역할은 **태스크 주입 시점에 동적 생성**한다:

```python
# dynamic_orchestrator.py — 태스크 완료 핸들러
def _on_task_completed(self, task_result, workspace):
    injected = inject_review_tasks(workspace, task_result)
    for task in injected:
        role = task["owner_role"]
        if role not in self.state_board["agents_status"]:
            self.state_board["agents_status"][role] = "idle"
            # AgentManager에 역할 등록
            self._agent_manager.get_or_create(role, workspace=workspace)
```

역할 이름 규칙: `{original_role}_code_reviewer`, `{original_role}_cross_validator`

### 2.7 BLOCK 판정 시 수정 루프

```
Code Reviewer → BLOCK 반환
  ↓
_handle_review_verdict() 호출
  ↓
원본 build 태스크를 "pending"으로 재설정
  + mailbox에 blocker 메시지 전송 (issues 포함)
  + _block_retry_count[task_id] += 1
  ↓
Dev가 수정 후 다시 build → code_review 재진행
```

**재시도 제한**:

```python
# 기존 _task_retry_count (impl 실패용)와 별도
_block_retry_count: Dict[str, int] = {}
MAX_BLOCK_RETRIES = 2

# 총합 상한: impl retry(3) + block retry(2) = 최대 5회
# 합산 5회 초과 시 태스크를 "failed"로 확정
```

Board 상태 매핑:
| 판정 | Board status | 후속 동작 |
|------|-------------|----------|
| PASS | code_review 태스크 → completed | cross_validate 진행 |
| WARN | code_review 태스크 → completed | cross_validate 진행 (경고 기록) |
| BLOCK | code_review 태스크 → failed, build 태스크 → pending | Dev 수정 재시도 |

### 2.8 Code Reviewer 시스템 프롬프트

```
[Code Review Contract]
당신은 {role} Code Reviewer다. {dev_role}이 작성한 코드를 리뷰한다.

검토 항목:
1. 보안 취약점 (OWASP Top 10, 인젝션, 인증)
2. 버그 및 엣지 케이스 (off-by-one, null 처리, 경계값)
3. 설계 품질 (단일 책임, 의존성 방향, 인터페이스 일관성)
4. 에러 처리 (예외 누락, 복구 전략)
5. 성능 (불필요한 I/O, O(n^2) 루프)

판정: PASS / WARN (경고 + 진행) / BLOCK (수정 필수)
JSON 형식으로 응답:
{"verdict": "PASS|WARN|BLOCK", "issues": [...], "summary": "..."}
```

주입 방식: `inject_documentation_contract()` 패턴을 따라 `inject_code_review_contract()` 함수 추가.

### 2.9 Cross Validator 시스템 프롬프트

```
[Cross Validation Contract]
당신은 {role} Cross Validator다. 모듈 전체의 정합성을 검증한다.

검토 항목:
1. 모듈 간 인터페이스 일관성 (입출력 타입, 계약)
2. 설계 문서와 구현의 괴리
3. 테스트 커버리지 갭 (QA가 놓친 시나리오)
4. 의존성 그래프 정합성
5. 문서 업데이트 누락

판정: PASS / WARN / BLOCK
JSON 형식으로 응답:
{"verdict": "PASS|WARN|BLOCK", "issues": [...], "summary": "..."}
```

### 2.10 구현 위치

| 변경 대상 | 변경 내용 |
|----------|----------|
| `core/project_task_board.py` | `inject_review_tasks()`, `_update_verify_dependency()`, `_append_tasks_to_board()` 추가. `_PHASE_ORDER` 확장 (integrate 유지 + code_review/cross_validate 추가) |
| `core/work_item_generator.py` | `phase_order` 동기화 |
| `core/dynamic_orchestrator.py` | `_on_task_completed()` → `inject_review_tasks()` 호출. `_block_retry_count` 관리. `_handle_review_verdict()` 추가 |
| `core/agent_runner.py` | `inject_code_review_contract()`, `inject_cross_validation_contract()` 시스템 프롬프트 주입 |
| `core/providers/registry.py` | `pick_review_provider()` 함수 추가 |
| `core/documentation_policy.py` | Code Review Contract / Cross Validation Contract 텍스트 |

Blueprint 업데이트: 구현 시 `Master_Blueprint.md` §3(서브시스템) + §12(이력) 동시 업데이트 필요.

### 2.11 max_cycles 영향

phase 가중치 추가:
```python
_PHASE_CYCLE_WEIGHTS = {
    "scope": 8, "build": 25, "integrate": 10,
    "code_review": 6, "cross_validate": 6,
    "verify": 12,
}
```

실행 시간 증가 계산:
- 기존 3 phase: 8+25+12 = 45/모듈
- 신규 5 phase: 8+25+6+6+12 = 57/모듈
- **증가율: 26.7%** (cycle 가중치 기준)

7 모듈 프로젝트: 7 × 57 = **399 cycles**

## 3. 면제 조건

| 면제 대상 | 판별 기준 | 이유 |
|----------|----------|------|
| 비코드 산출물 | build 산출물에 `.py` 파일이 없음 | requirements.txt, .command 등은 리뷰 불필요 |
| scope/verify 단계 | `phase != "build"` | 문서만 생성하는 단계 |
| CLI 1개 환경의 Cross Validator | `len(available_providers) < 2` | 같은 모델 2회 리뷰는 비효율 |

## 4. 대안 검토

| 대안 | 기각 이유 |
|------|----------|
| QA 역할 확장 (리뷰 겸임) | 테스트 작성과 코드 리뷰는 관점이 다름. 분리가 품질에 유리 |
| 리뷰 없이 테스트만 | 테스트 통과해도 설계 결함/보안 이슈 놓침 |
| 단일 CLI로 셀프 리뷰 | 같은 모델이 같은 편향으로 리뷰 — 교차의 의미 없음 |
| phase 추가 대신 build 후처리 hook | 기존 phase 인프라를 재활용하는 것이 일관성 유지에 유리 |

## 5. 리스크

| 리스크 | 대응 | 구현 위치 |
|--------|------|----------|
| cycle 증가 (~27%) | phase 가중치에 반영, Run Budget이 상위 guard | `_PHASE_CYCLE_WEIGHTS` |
| BLOCK 무한 루프 | `_block_retry_count` 전용 카운터, max=2. impl retry와 합산 상한 5회 | `dynamic_orchestrator.py` |
| CLI 1개 환경 | Cross Validator 자동 생략, Code Reviewer는 같은 provider 별도 세션 | `pick_review_provider()` |
| 동적 주입 후 max_cycles 부족 | 10 cycle마다 `compute_max_cycles` 재평가에서 자동 반영 | `_orchestration_loop` |
