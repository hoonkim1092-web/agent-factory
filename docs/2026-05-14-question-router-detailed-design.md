---
title: Work Pipeline Stage 0 Question Router 상세 설계
date: 2026-05-14
status: Draft (v4 — Codex 라운드 5 합의 + 7건 in-place 정정)
revision: v4
adr: ADR-20260514-133054-question-router-stage0
inspired_by: superpowers/brainstorming
authors: hoonkim (Opus 4.7), cross-vendor consensus (Codex)
---

# Work Pipeline Stage 0 Question Router 상세 설계

> ADR `docs/decisions/ADR-20260514-133054-question-router-stage0.md`가 정책을 정한다.
> 본 문서는 구현 계약을 정한다. ADR과 충돌하면 ADR이 우선이다.

## 1. Scope

### 1.1 이 문서가 정의하는 것

본 문서는 **이미 work-item 생성 대상으로 분류된 요청**에만 적용되는 Work Pipeline 내부 Stage 0 설계다.

정의 범위:

- `generate_work_items()` 내부에서 Stage 1~3 전에 삽입되는 Stage 0
- `work_kind` 기반 분기
- 기존 프로젝트용 Light Context Scan
- 새 프로젝트용 Goal Clarification Question Router
- 공통 Brainstorming Question Router
- `domain-review.md`, `project-goal.md`, `context-scan.md`, `assumptions.md` 산출물 계약
- `ApprovalGate`와 `DomainVerdict` 연동
- `paused_hitl` 상태 처리 계약
- E2E 검증 기준

### 1.2 이 문서가 정의하지 않는 것

이 문서는 범용 사용자 요청 하네스를 정의하지 않는다.

다음은 후속 설계 문서에서 다룬다.

- Request Harness
- Request Decomposer
- RequestKindRouter
- Freshness / Evidence Planner
- Subtask DAG
- AnswerPipeline / ResearchPipeline / WorkPipeline dispatcher
- 복합 요청의 partial completion / unified report

즉, 다음 요청은 이 문서의 직접 대상이 아니다.

```text
오늘 최신 뉴스 알려줘
이 문서 요약해줘
이 코드 설명해줘
오늘 최신 뉴스 알려줘, 회의록 녹음/요약 앱 만들어줘
```

위 요청들은 상위 Request Harness가 먼저 분해하고, 그중 `new_project`, `maintenance`, `bugfix`, `feature_update`, `refactor`로 판정된 work subtask만 본 Stage 0로 들어온다.

### 1.3 상위 구조에서의 위치

```text
User Request
 -> Request Harness                         (후속 설계)
 -> Request Decomposer / Subtask Router      (후속 설계)
 -> Evidence Planner                         (후속 설계)
 -> Work Pipeline Dispatcher                 (후속 설계)
 -> generate_work_items()                    (본 문서 범위)
      -> Stage 0 Question Router
      -> Stage 1 plan
      -> Stage 2 spec + design
      -> Stage 3 tasks
      -> af-runner
      -> af-test-runner
      -> Report
```

핵심 경계:

```text
Request Harness = 사용자 요청 전체를 분해/라우팅
Question Router = work pipeline 내부 Stage 0 질문 처리
```

## 2. 근거 기반 현재 상태

### 2.1 `work_kind` / `blast_radius`는 전달되지만 Stage 흐름에는 쓰이지 않는다

검증 근거:

- `core/work_item_generator.py:1072` `generate_work_items()`는 `work_kind`, `blast_radius`를 keyword-only 인자로 받는다.
- `core/project_pipeline.py:970-971`은 `project_brief`에서 `work_kind`, `blast_radius`를 넘긴다.
- `core/work_item_generator.py:1083-1184`의 Stage 1~3 실행 흐름에서는 두 값을 Stage 분기에 사용하지 않는다.
- `core/work_item_generator.py:1238`에서만 `gate.initialize(..., work_kind=work_kind, blast_radius=blast_radius)`로 전달한다.

결론:

```text
분류 결과는 존재하지만 Stage orchestration에는 반영되지 않는다.
Stage 0은 이 gap을 메우는 work pipeline 내부 확장이다.
```

### 2.2 `blast_radius` 토큰은 기존 계약을 따라야 한다

현재 유효 토큰:

```text
isolated | module | cross_module | system_wide
```

근거:

- `core/control/change_impact.py`가 위 4개 토큰을 산출한다.
- `core/control/execution_policy.py`도 위 토큰을 기준으로 정책을 고른다.
- `tests/test_approval_gate_domain_review.py`는 `"local"` 같은 invalid historical token 사용을 거부한다.

따라서 본 설계는 다음 토큰을 `blast_radius`로 사용하지 않는다.

```text
local
security
data
```

`security`, `data`는 blast radius가 아니라 `BlockCause`, domain concern, 또는 후속 Evidence Planner의 risk axis에서 다룬다.

### 2.3 기존 반환 계약을 깨면 안 된다

`generate_work_items()`는 현재 `dict[str, str]` 형태의 file map을 반환한다. `core/project_pipeline.py`는 `work_item_files.values()`를 파일 경로로 보고 열어 검증한다.

따라서 Stage 0이 `paused_hitl`을 만들더라도 `generate_work_items()`가 임의 상태 객체를 반환하면 안 된다.

비양보 계약:

```text
generate_work_items() 반환값은 기존 file-path map 계약을 유지한다.
paused_hitl 상태는 artifact + ledger + optional sentinel file로 표현한다.
상위 caller가 상태 객체를 받는 구조는 별도 명시적 contract 변경 없이는 금지한다.
```

## 3. 핵심 결정

### 3.1 Stage 0 삽입 위치

정상 경로:

```text
core/work_item_generator.py
 -> generate_work_items()
    -> _copy_extra_templates()
    -> Stage 0 Question Router             (NEW)
    -> cleanup_stale_sessions()
    -> Stage 1 plan
    -> Stage 2 spec + design
    -> Stage 3 tasks
    -> gate.initialize() at line 1238       (정상 종료, status="review_pending")
```

paused_hitl 경로 (v4 A안 — Codex 라운드 4 합의):

```text
generate_work_items()
 -> _copy_extra_templates()
 -> Stage 0 Question Router
    -> paused_hitl 감지
    -> StageRouter가 paused-hitl.md 생성
    -> gate.initialize(..., status="paused_hitl", execution_open=False)  (1회 호출)
    -> approval-gate.md 생성
    -> file-path map 반환 (Stage 1~3 skip, line 1238 정상 호출 skip)
```

**핵심 계약**:
- paused 분기는 line 1238 정상 initialize **호출하지 않는다** (분기 종료로 도달 안 함, 자연스러움)
- paused 분기 자체에서 `gate.initialize()` 1회 호출로 `approval-gate.md` 생성
- ApprovalGate 시그니처에 `status`, `execution_open` 파라미터 추가 의무 (§9.4 참조)

paused_hitl 시 반환 file-path map:

```text
approval-gate.md       (paused 분기에서 gate.initialize(paused) 가 생성)
domain-review.md       (StageRouter가 생성)
project-goal.md or context-scan.md
assumptions.md
paused-hitl.md         (sentinel)
```

caller는 정상/paused 양쪽에서 동일하게 file-path map을 받는다.

### 3.2 Work kind 분기

```text
work_kind == new_project
 -> Goal Clarification QR
 -> project-goal.md
 -> Brainstorming QR
 -> domain-review.md

work_kind in {maintenance, bugfix, feature_update, refactor}
 -> Light Context Scan
 -> context-scan.md
 -> Brainstorming QR
 -> domain-review.md

empty or non-enum work_kind (legacy/direct caller compatibility guard, v4 정정)
 -> Stage 0 skip
 -> 기존 Stage 1~3 실행
```

**Empty/non-enum work_kind guard** (v4 — Codex 라운드 4 합의):

이 분기는 정상 `WorkKindClassifier` 산출 결과("unknown")가 아니다 — classifier는 항상 5개 enum 중 하나를 반환한다 (`core/control/work_kind.py:84-93`). 본 가드는 다음 경로 보호용이다:

1. `project_brief.get("work_kind")` 가 None 인 경우 (intake crash, partial init)
2. 미래 direct caller 가 `work_kind` 인자를 생략하는 경우 (시그니처 `work_kind: str = ""` 기본값)
3. future bug 로 enum 외 값이 들어오는 경우

명칭은 "unknown work_kind" 가 아니라 **"empty or non-enum work_kind compatibility guard"** 다.

### 3.3 기존 Stage 1~3 보존

Stage 0은 Stage 1~3을 대체하지 않는다.

```text
보존:
- Stage 1 plan
- Stage 2 spec + design
- Stage 3 tasks
- af-runner
- af-test-runner
- Report
```

Stage 0의 역할은 Stage 1에 들어가기 전 다음을 정리하는 것이다.

```text
- 기존 프로젝트의 최소 컨텍스트
- 새 프로젝트의 목표
- Brainstorming 결과
- research_scope
- domain verdict
- assumptions ledger
```

## 4. 용어와 enum

### 4.1 enum 분리

```python
class QuestionRoute(Enum):
    PASS = "pass"
    LLM_DELEGATE = "llm_delegate"
    HITL = "hitl"
    BLOCK = "block"


class DomainVerdict(Enum):
    PASS = "pass"
    NEEDS_ADR = "needs_adr"
    BLOCK = "block"


class BlockCause(Enum):
    MISSING_REQUIRED_INPUT = "missing_required_input"
    DESIGN_CONFLICT = "design_conflict"
    HIGH_RISK = "high_risk"
    POLICY_VIOLATION = "policy_violation"
    SAFETY = "safety"
```

원칙:

```text
QuestionRoute = 질문 처리 방식
DomainVerdict = 작업 진행 가능성
BlockCause = BLOCK 원인
```

로그와 artifact에서도 필드명을 분리한다.

```json
{
  "question_route": "llm_delegate",
  "domain_verdict": "needs_adr",
  "block_cause": null
}
```

`{"status": "pass"}` 같은 모호한 로그는 금지한다.

### 4.2 Router와 Gate 책임 분리

```text
QuestionRouter:
- 질문별 route 결정
- 값/assumption/block candidate 반환
- 파일 쓰기 없음
- pause/abort/ADR 생성 없음

StageRouter:
- QuestionRouter 결과를 artifact로 렌더링
- ledger append 요청
- paused artifact 생성

ApprovalGate:
- DomainVerdict + BlockCause + blast_radius 기반으로 continue/pause/block 결정
- ADR 생성 트리거의 단일 정책 경로
```

## 5. YAML Question Schema

### 5.1 허용 필드

Schema-level 필드:

```yaml
schema_version: 1
question_set_id: goal_clarification
questions: []
```

Question-level 필드:

```yaml
- id: deployment_target
  text: "배포 대상 환경은 무엇입니까?"
  output_field: deployment_target
  required: true
  fallback: "development"
  default_route: llm_delegate
  block_category_if_missing: missing_required_input
```

Question-level routing policy metadata는 아래 4개로 제한한다.

```text
required
fallback
default_route
block_category_if_missing
```

금지:

```text
risk
failure_policy
escalation_policy
fallback_allowed
require_hitl_when
```

민감한 질문은 `default_route: hitl`로 표현한다.

```yaml
- id: data_deletion_policy
  text: "기존 데이터를 삭제해도 됩니까?"
  output_field: data_deletion_policy
  required: true
  fallback: null
  default_route: hitl
  block_category_if_missing: missing_required_input
```

### 5.2 validation hard fail

**단일 YAML 로드 시 hard fail 조건**:

- `schema_version` 누락 또는 지원하지 않는 버전
- `question_set_id` 누락
- `questions[].id` 중복 (단일 YAML 내부)
- `id` 또는 `output_field` 누락
- `default_route`가 `QuestionRoute` enum 외 값
- `block_category_if_missing`가 `BlockCause` enum 외 값
- `required: true`인데 `block_category_if_missing` 누락
- 허용되지 않은 routing policy metadata 사용

MVP에서는 `id == output_field`를 권장한다. 별도 mapping을 허용하려면 resume 병합 테스트를 추가해야 한다.

### 5.2.1 Cross-YAML id uniqueness (v4 추가 — Codex 라운드 5 합의)

**비양보 계약**: StageRouter는 시작 시 **모든 active question set YAML을 함께 로드**하고, 전체 active questions 에 대해 `question.id` 중복을 hard fail 한다.

근거:
- paused_hitl resume 시 응답 병합 키는 `question.id` 단독을 유지 (단순성)
- cross-yaml 중복 허용 시 silent data corruption 위험 (goal_clarification.deployment_target vs brainstorming.deployment_target)
- A안 (전역 active id uniqueness) + ledger provenance 가 MVP scope + Karpathy Simplicity 부합

**구현 계약**:

```python
class StageRouter:
    def __init__(self, workspace: str, run_ledger: RunLedger):
        self._active_schemas = self._load_active_question_sets()  # 모든 active YAML 한 번에 로드
        self._validate_cross_yaml_id_uniqueness(self._active_schemas)  # hard fail

    def _load_active_question_sets(self) -> dict[str, dict]:
        """
        반환: {question_set_id: parsed_schema_dict}
        활성 대상: goal_clarification.yaml, brainstorming.yaml (MVP 2-set).
        future: Request Harness 도입 시 active set 동적 결정.
        """

    def _validate_cross_yaml_id_uniqueness(self, schemas: dict[str, dict]) -> None:
        """
        global active namespace 에서 question.id 중복 hard fail.
        예: goal_clarification.deployment_target + brainstorming.deployment_target → RuntimeError
        """
        seen: dict[str, str] = {}  # question_id -> question_set_id
        for set_id, schema in schemas.items():
            for q in schema["questions"]:
                if q["id"] in seen:
                    raise RuntimeError(
                        f"Cross-YAML question.id collision: '{q['id']}' "
                        f"in both '{seen[q['id']]}' and '{set_id}'. "
                        f"MVP requires global active id uniqueness."
                    )
                seen[q["id"]] = set_id
```

**미래 확장 (§15 OQ4 참조)**: Request Harness 도입으로 question set 수가 3개 이상으로 늘거나 id 재사용 요구가 생기면 `QuestionRef(question_set_id, question_id)` composite key 로 마이그레이션한다. 본 마이그레이션은 ledger entry / paused artifact / resume merge logic 의 1회 breaking change 를 동반한다.

### 5.3 schema version과 hash

source YAML에는 `schema_hash`를 저장하지 않는다.

이유:

```text
raw bytes hash를 YAML 내부 schema_hash 필드에 다시 쓰면,
쓰기 자체가 bytes를 바꿔 hash를 무효화한다.
```

정책:

```text
YAML:
- schema_version만 보관

artifact / ledger:
- question_set_id
- schema_version
- schema_hash
```

`schema_hash`는 source YAML의 canonical bytes로 계산한다. MVP에서는 다음 중 하나를 선택한다.

```text
Option A: raw bytes hash, source YAML에는 기록하지 않음
Option B: parsed YAML에서 schema_hash 같은 runtime-only 필드를 제외한 canonical hash
```

본 설계의 기본값은 Option A다.

```text
schema_hash = sha256(source_yaml_bytes)
```

YAML을 자동 수정해 hash를 채워 넣는 동작은 금지한다.

### 5.4 question id 안정성

`question.id`는 resume 병합 키다.

규칙:

- 기존 id rename 금지
- 삭제 대신 `deprecated`는 후속 버전에서 검토
- 같은 id의 `output_field` 변경은 schema drift로 취급
- paused HITL 응답은 `question.id` 기준으로 병합

## 6. Question Router

### 6.1 인터페이스

```python
@dataclass(frozen=True)
class Question:
    id: str
    text: str
    output_field: str
    required: bool = False
    fallback: Any = None
    default_route: QuestionRoute = QuestionRoute.LLM_DELEGATE
    block_category_if_missing: BlockCause | None = None


@dataclass
class QuestionResult:
    question_id: str
    output_field: str
    question_route: QuestionRoute
    value: Any = None
    block_cause: BlockCause | None = None
    used_fallback: bool = False
    source: str = ""
    warning: str = ""


@dataclass
class QuestionBatchResult:
    question_set_id: str
    schema_version: int
    schema_hash: str
    results: list[QuestionResult]
    paused_hitl_ids: list[str]
    block_results: list[QuestionResult]
```

### 6.2 LLM_DELEGATE 실패 정책

```python
def handle_llm_failure(q: Question, blast_radius: str, exc: Exception) -> QuestionResult:
    if q.required and q.fallback is None:
        return promote_to_hitl(q, reason=f"llm_failed:{type(exc).__name__}")

    if not q.required and q.fallback is not None:
        return use_fallback(q, reason=f"llm_failed:{type(exc).__name__}")

    if not q.required and q.fallback is None:
        return skip_with_warning(q, reason=f"llm_failed:{type(exc).__name__}")

    # required and fallback exists
    if blast_radius in ("cross_module", "system_wide"):
        return promote_to_hitl(q, reason="required_with_fallback_high_blast")

    return use_fallback(q, reason=f"llm_failed:{type(exc).__name__}")
```

주의:

```text
security/data는 blast_radius가 아니다.
민감한 질문은 default_route=hitl 또는 BlockCause로 표현한다.
```

### 6.3 LLM 응답 검증

LLM이 `block_cause`를 반환하면 반드시 `BlockCause` enum으로 검증한다.

무효값이면:

```text
해당 질문만 HITL 승격
run_ledger에 llm_schema_violation 기록
Stage 1~3 진행 여부는 ApprovalGate가 판단
```

## 7. Stage Artifacts

모든 artifact는 다음 메타를 가진다.

```text
artifact_type
question_set_id, 필요한 경우
schema_version
schema_hash
created_at
```

### 7.1 ContextScanArtifact

```python
@dataclass
class ContextScanArtifact:
    artifact_type: str
    schema_version: int
    schema_hash: str
    work_dir: str
    work_kind: str
    blast_radius: str
    relevant_files: list[str]
    affected_modules: list[str]
    existing_tests: list[str]   # v4: Stage 1 plan prompt 소비 (생성/소비 명시)
    risk_signals: list[str]
```

저장 위치:

```text
<work_dir>/context-scan.md
```

**`existing_tests` 생성/소비 (v4 — Codex 라운드 5 합의)**:

- **생성**: `LightContextScanner.scan()` 가 정적 분석으로 `tests/`, `test_*.py`, `*_test.py` 및 affected_modules 와 매칭되는 테스트 파일 경로를 산출 (LLM 0회)
- **소비**: `core/work_item_generator.py:908` `_exec_stage1()` 의 prompt 구성에 `Existing Tests` 섹션 추가. 기존 `episode_hints_section` 패턴(line 1105) 과 동일 방식 — placeholder `{existing_tests_section}` 형태로 prompt template 에 주입
- **Stage 3 직접 주입 금지** (v4 정정): existing_tests 는 Stage 1 plan 안에 녹아들어 자연 흐름으로 Stage 3 prompt 에 전달됨 (`work_item_generator.py:715` `prev_plan` 블록을 통해)

### 7.2 ProjectGoalArtifact

```python
@dataclass
class ProjectGoalArtifact:
    artifact_type: str
    question_set_id: str
    schema_version: int
    schema_hash: str
    work_kind: str
    goal_summary: str
    deployment_target: str           # v4: platform 필드 제거 (중복, 정당화 부재)
    success_criteria: list[str]
    out_of_scope: list[str]
    assumptions_used: list[str]
```

저장 위치:

```text
<work_dir>/project-goal.md
```

**v4 변경**: `platform` 필드 제거. `deployment_target` 과 의미 중복이고 MVP 소비처 명시 부재 (Karpathy "추측성 코드 금지" 위반). 미래에 platform 이 별도 의미를 가져야 하면 그 시점에 정당화 + 소비처 명시 후 재도입.

### 7.3 DomainReviewArtifact

```python
@dataclass
class DomainReviewArtifact:
    artifact_type: str
    question_set_id: str
    schema_version: int
    schema_hash: str
    domain_verdict: DomainVerdict
    block_cause: BlockCause | None
    domain_concerns: list[str]
    suggested_adrs: list[str]
    research_scope: list[str]        # v4: Stage 1 plan prompt scope constraint 소비
    review_questions: list[dict]
    paused_hitl_ids: list[str]
```

저장 위치:

```text
<work_dir>/domain-review.md
```

기존 호환성:

```text
첫 줄 또는 상단 metadata에 반드시 `- verdict: PASS|NEEDS_ADR|BLOCK` 유지
BLOCK일 때 `- block_cause: <BlockCause>` 추가
```

**`research_scope` 생성/소비 (v4 — Codex 라운드 5 합의)**:

- **생성**: `BrainstormingQR` LLM 응답의 `_meta.research_scope` 필드 (LLM 이 도메인 검토 결과 산출). Brainstorming 의 핵심 산출물.
- **소비**: `core/work_item_generator.py:908` `_exec_stage1()` 의 prompt 구성에 `Research Scope` 섹션 추가 (scope constraint). Stage 1 plan 이 본 scope 를 넘어서지 않도록 제약. 기존 `episode_hints_section` 패턴과 동일 방식 — placeholder `{research_scope_section}` 형태로 prompt template 에 주입
- **Stage 3 직접 주입 금지**: Stage 1 plan 의 자연 흐름으로 Stage 3 prompt 에 전달됨

### 7.4 AssumptionLedgerEntry

```python
@dataclass
class AssumptionLedgerEntry:
    artifact_type: str
    schema_version: int
    schema_hash: str
    timestamp: str
    question_set_id: str          # v4 신규: ledger provenance (Codex 라운드 5 합의)
    question_id: str
    output_field: str
    value: Any
    source: str        # llm_delegate | fallback | hitl
    rationale: str = ""
```

저장 위치:

```text
<work_dir>/assumptions.md
```

모든 `LLM_DELEGATE`와 `fallback` 사용은 assumptions ledger에 남긴다.

**v4 `question_set_id` 필드 (Codex 라운드 5 합의 — A안 + ledger provenance)**:

병합 키는 `question.id` 단독 유지 (cross-yaml uniqueness 강제, §5.2.1). `question_set_id` 는 **provenance 전용** — debug/audit 시 어느 question set 에서 발생한 assumption 인지 추적 가능. 검색/필터링 인덱스로만 사용, 병합 로직에는 영향 없음.

### 7.5 Paused HITL artifact

```python
@dataclass
class PausedHitlQuestion:
    """v4 — paused 질문 별 provenance (Codex 라운드 5 합의 ledger provenance)."""
    question_set_id: str
    question_id: str


@dataclass
class PausedHitlArtifact:
    artifact_type: str
    status: str                                # paused_hitl
    terminal_success: bool                     # false
    report_required: bool                      # true
    questions: list[PausedHitlQuestion]        # v4: question_id 만이 아닌 set_id 포함
    schema_version: int
    schema_hash: str                           # 마지막 활성 schema bundle 의 hash (drift 감지)
    resume_entrypoint: str
    reason: str
```

저장 위치:

```text
<work_dir>/paused-hitl.md
```

`paused_hitl`은 성공이 아니다.

```text
status = paused_hitl
terminal_success = false
runner_continued = false
report_required = true
```

**v4 변경 — `questions` 구조 (Codex 라운드 5 합의)**: 기존 `question_ids: list[str]` → `questions: list[PausedHitlQuestion]`. 병합 키는 여전히 `question_id` 단독 (cross-yaml uniqueness 보장, §5.2.1)이지만 provenance 정보를 paused artifact 에 함께 기록해 debug/audit 가능.

domain-review.md 의 `paused_hitl_ids: list[str]` 도 동일하게 `paused_hitl_questions: list[PausedHitlQuestion]` 으로 변경 의무 (§7.3 dataclass 갱신 동반).

## 8. ApprovalGate 정책

### 8.1 DomainVerdict 매트릭스

기존 `blast_radius` 토큰만 사용한다.

| DomainVerdict | blast_radius | 동작 |
| --- | --- | --- |
| PASS | * | 진행 |
| NEEDS_ADR | isolated, module | ADR 생성 + warning + 진행 가능 |
| NEEDS_ADR | cross_module, system_wide | ADR 생성 + pause |
| BLOCK + MISSING_REQUIRED_INPUT | * | HITL clarification batch |
| BLOCK + DESIGN_CONFLICT | * | ADR 생성 + pause |
| BLOCK + HIGH_RISK | * | ADR 생성 + pause |
| BLOCK + POLICY_VIOLATION | * | abort + report |
| BLOCK + SAFETY | * | abort + report |

### 8.2 기존 gate semantics 변경 명시

현재 테스트는 `blast_radius != system_wide`이면 domain gate를 skip하는 계약을 가진다.

본 설계는 이를 변경한다.

```text
기존:
system_wide만 domain gate 강제

변경:
DomainVerdict와 blast_radius 매트릭스로 gate 판단
```

따라서 다음이 필요하다.

- `tests/test_approval_gate_domain_gate.py` 기대값 업데이트
- `tests/test_approval_gate_domain_review.py` invalid token 보호 유지
- NEEDS_ADR × 4개 blast_radius 토큰 테스트
- BLOCK × BlockCause 테스트

### 8.3 ApprovalGate.initialize() 시그니처 변경 (v4 — Codex 라운드 5 합의)

**비양보 의무**: `core/approval_gate.py:156` `initialize()` 에 `status`, `execution_open` 파라미터 추가. 기본값 유지로 backward-compatible.

**변경 전** (현재 `:156-178`):

```python
def initialize(
    self,
    work_item_id: str = "",
    run_id: str = "",
    *,
    work_kind: str = "",
    blast_radius: str = "",
) -> None:
    """approval-gate.md 최초 생성 (execution_open: false)."""
    os.makedirs(self.work_item_dir, exist_ok=True)
    content = self._render(
        work_item=work_item_id or self.slug,
        approver="",
        status="review_pending",        # 하드코딩
        snapshots={},
        gate_statuses={},
        execution_open=False,           # 하드코딩
        review_notes="",
        work_kind=work_kind,
        blast_radius=blast_radius,
    )
    write_text(self.gate_path, content)
    _emit_approval_event("approval_requested", self, run_id)
```

**변경 후**:

```python
def initialize(
    self,
    work_item_id: str = "",
    run_id: str = "",
    *,
    work_kind: str = "",
    blast_radius: str = "",
    status: str = "review_pending",         # v4 신규 (기본값 유지 → backward-compatible)
    execution_open: bool = False,           # v4 신규 (기본값 유지)
) -> None:
    """approval-gate.md 최초 생성. paused_hitl 분기는 status='paused_hitl' 전달."""
    os.makedirs(self.work_item_dir, exist_ok=True)
    content = self._render(
        work_item=work_item_id or self.slug,
        approver="",
        status=status,                       # 하드코딩 제거
        snapshots={},
        gate_statuses={},
        execution_open=execution_open,       # 하드코딩 제거
        review_notes="",
        work_kind=work_kind,
        blast_radius=blast_radius,
    )
    write_text(self.gate_path, content)
    _emit_approval_event("approval_requested", self, run_id)
```

기존 호출자 (`work_item_generator.py:1238`) 는 status/execution_open 인자 생략 → 기본값 "review_pending"/False 적용 → 기존 동작 동일.

Stage 0 paused 분기 호출:
```python
gate.initialize(
    work_item_id=slug,
    run_id=run_id,
    work_kind=work_kind,
    blast_radius=blast_radius,
    status="paused_hitl",
    execution_open=False,
)
```

### 8.4 ADR 생성 책임

`QuestionRouter`는 ADR을 만들지 않는다.

정책:

```text
DomainReviewArtifact:
- suggested_adrs만 제안

ApprovalGate 또는 그 호출자:
- 실제 ADR 생성
- pause/continue/abort 결정
```

## 9. `paused_hitl` 처리 계약

### 9.1 반환 계약

`generate_work_items()`는 `dict[str, str]` file-path map을 유지한다.

`paused_hitl`일 때 예시:

```python
{
    "approval_gate": "<work_dir>/approval-gate.md",
    "domain_review": "<work_dir>/domain-review.md",
    "project_goal": "<work_dir>/project-goal.md",
    "assumptions": "<work_dir>/assumptions.md",
    "paused_hitl": "<work_dir>/paused-hitl.md",
}
```

Stage 1~3 산출물은 생성하지 않는다.

**`approval_gate` 키 생성 의무 (v4 — Codex 라운드 4 합의 A안)**:

paused 분기에서도 `approval-gate.md` 파일이 실제로 생성되어야 한다 (반환 dict 에 키만 있고 파일 없으면 `project_pipeline.py:1129` `to_portable_path(p)` 또는 후속 `gate.read_block_decision()` 처리 시 FileNotFoundError 또는 silent skip 위험).

paused 분기는 **gate.initialize(..., status="paused_hitl", execution_open=False)** 를 1회 호출해 파일 생성한다. 정상 분기의 `work_item_generator.py:1238` initialize 호출은 paused 분기에서 도달하지 않으므로 중복 호출 위험 없다.

### 9.2 caller 처리

`ProjectPipeline`은 `paused-hitl.md` 또는 `approval-gate.md` metadata를 감지해 plan verification을 건너뛴다.

필수 동작:

```text
paused_hitl 감지
 -> work-item incomplete 처리
 -> final report에 pending questions 표시
 -> af-runner / af-test-runner 미실행
```

### 9.3 resume 진입점

MVP resume 진입점은 `ProjectPipeline`로 정한다.

```text
사용자 HITL 응답 입력
 -> ProjectPipeline이 paused-hitl.md 로드
 -> 응답을 Stage 0 input에 병합
 -> Stage 0만 재실행
 -> paused_hitl 해소 시 Stage 1~3 진행
```

이 진입점은 후속 Request Harness가 생기면 parent request 상태와 연결한다.

## 10. LLM Caller와 예산

### 10.1 LLMCaller adapter

`QuestionRouter`는 직접 `control_plane_llm.py`를 호출하지 않는다. adapter를 둔다.

```python
class QuestionRouterLLMCaller:
    def batch_route(
        self,
        questions: list[Question],
        context: dict[str, Any],
        timeout_sec: float,
    ) -> dict[str, Any]:
        ...
```

필수 계약:

```text
timeout_sec는 실제 CLI/provider 호출까지 전달되어야 한다.
기존 hardcoded timeout_sec=300 경로를 우회하거나 확장한다.
```

### 10.2 예산

| 단계 | 예산 |
| --- | ---: |
| Goal Clarification QR | 90s |
| Light Context Scan | 0s LLM |
| Brainstorming QR | 180s |
| Stage 1 plan | 90s |
| Stage 2 spec + design | 400s |
| Stage 3 tasks | 110s |

권장 `TOTAL_BUDGET`:

```text
new_project: 800s
maintenance 계열: 700s
```

## 11. 파일 쓰기와 동시성

야간/병렬 실행을 전제로 artifact 쓰기 정책을 명시한다.

### 11.1 atomic write

다음 artifact는 temp file 후 atomic replace로 쓴다.

```text
domain-review.md
project-goal.md
context-scan.md
paused-hitl.md
approval-gate.md
```

정책:

```text
write <name>.tmp.<pid>
fsync where practical
replace target atomically
```

### 11.2 assumptions append

`assumptions.md`는 append-only라 동시 write 위험이 있다.

MVP 정책:

```text
work_dir 단위 lock 사용
JSONL block append
append 실패 시 Stage 0 warning이 아니라 hard fail
```

감사 ledger가 깨지면 downstream 디버깅이 불가능하므로 hard fail이 맞다.

## 12. PyInstaller / frozen build

신규 동적 import 모듈은 frozen build에 반영해야 한다.

추가 대상:

```text
core.control.stage_router
core.control.question_router
core.control.stage_artifacts
core.control.verdicts
core.control.context_scanner
```

검증 기준:

```text
af.spec hiddenimports 반영
dist/af/af.exe 또는 현재 프로젝트의 frozen build smoke test 통과
```

## 13. E2E 시나리오

### 13.1 new_project PASS

```text
input:
  work_kind = new_project
  blast_radius = isolated

expected:
  project-goal.md 생성
  domain-review.md verdict PASS
  assumptions.md 생성
  Stage 1~3 실행
```

### 13.2 maintenance NEEDS_ADR low blast

```text
input:
  work_kind = maintenance
  blast_radius = module

expected:
  context-scan.md 생성
  domain-review.md verdict NEEDS_ADR
  ADR 생성 + warning
  Stage 1~3 진행 가능
```

### 13.3 feature_update NEEDS_ADR high blast

```text
input:
  work_kind = feature_update
  blast_radius = cross_module

expected:
  domain-review.md verdict NEEDS_ADR
  ADR 생성
  paused/review required
  Stage 1~3 진행 중단
```

### 13.4 HITL batch

```text
input:
  required question unresolved

expected:
  paused-hitl.md 생성
  run_ledger paused_hitl event
  generate_work_items()는 file path map 반환
  ProjectPipeline은 incomplete 처리
  af-runner / af-test-runner 미실행
```

### 13.5 BLOCK causes

각각 검증:

```text
MISSING_REQUIRED_INPUT -> HITL batch
DESIGN_CONFLICT -> ADR + pause
HIGH_RISK -> ADR + pause
POLICY_VIOLATION -> abort + report
SAFETY -> abort + report
```

### 13.6 fallback

```text
input:
  optional question LLM timeout
  fallback exists

expected:
  fallback 사용
  assumptions.md에 source=fallback 기록
  Stage 1~3 계속 진행
```

### 13.7 schema drift

```text
input:
  paused-hitl artifact의 schema_hash와 현재 YAML hash 불일치

expected:
  WARN
  run_ledger schema_drift event
  사용자 선택 필요
  자동 migration 없음
```

## 14. P0~P7 Acceptance Criteria

### P0: 설계 정리

- [ ] 본 문서가 Work Pipeline Stage 0 전용임을 명시
- [ ] 기존 design review BLOCK 항목 반영
- [ ] ADR과 blast_radius 토큰 정합성 확보

### P1: StageRouter

- [ ] `core/control/stage_router.py` 추가
- [ ] 5개 work_kind 분기 테스트
- [ ] unknown work_kind fallback 테스트

### P1.5: StageArtifact

- [ ] `core/control/stage_artifacts.py` 추가
- [ ] render markdown 호환성 테스트
- [ ] atomic write helper 사용

### P1.6: QuestionRouter

- [ ] `core/control/question_router.py` 추가
- [ ] `core/control/verdicts.py` 추가
- [ ] YAML validation hard fail 테스트
- [ ] LLM invalid enum -> HITL 승격 테스트
- [ ] required/fallback/blast_radius fallback 테스트

### P3: LightContextScanner

- [ ] `core/control/context_scanner.py` 추가
- [ ] LLM 0회 보장
- [ ] existing_tests / relevant_files 산출

### P4: GoalClarification QR

- [ ] `core/control/questions/goal_clarification.yaml` 추가
- [ ] schema_version 포함
- [ ] source YAML에 schema_hash 미기록

### P2: Brainstorming QR

- [ ] `core/control/questions/brainstorming.yaml` 추가
- [ ] PASS / NEEDS_ADR / BLOCK 산출 테스트
- [ ] research_scope 산출

### P5: ApprovalGate

- [ ] `DomainVerdict` 파싱
- [ ] `BlockCause` 파싱
- [ ] `initialize()` 시그니처에 `status`, `execution_open` 파라미터 추가 (§8.3)
- [ ] NEEDS_ADR × `isolated/module/cross_module/system_wide` 테스트
- [ ] 기존 invalid blast_radius token 테스트 유지

**Migration test action table** (v4 — Codex 라운드 5 합의):

| 기존 test (line) | v4 액션 |
|------------------|---------|
| `test_skips_domain_gate_for_module_blast_radius:150` | **분할 3개**: module × PASS / NEEDS_ADR / BLOCK |
| `test_skip_env_bypasses_domain_gate:184` | 변경 없음 (AF_SKIP_REVIEW_GATE 우회 유지) |
| `test_skip_env_no_version_stored:190` | 변경 없음 |
| `test_no_invalid_blast_radius_local_token` | 유지 (정칙 보호) |
| `test_no_invalid_blast_radius_system_token` | 유지 |
| F5 헤더 (`tests/test_approval_gate_domain_gate.py:6`) | "blast_radius != system_wide → skip" 갱신 → "DomainVerdict 매트릭스 적용" |

**신규 test (P5 acceptance)**:

- `test_needs_adr_isolated_proceeds_with_warning`
- `test_needs_adr_module_proceeds_with_warning`
- `test_needs_adr_cross_module_pauses`
- `test_needs_adr_system_wide_pauses`
- `test_block_cause_parsed_from_domain_review_md`
- `test_initialize_with_paused_hitl_status` (시그니처 변경 검증, §8.3)
- `test_initialize_default_status_backward_compatible` (기존 호출자 회귀 보호)

### P6a: Ledger

- [ ] assumption event
- [ ] paused_hitl event
- [ ] schema_drift event
- [ ] append lock 테스트

### P7: Integration

- [ ] E2E 7개 경로 통과
- [ ] `ProjectPipeline` paused file-path map 처리
- [ ] Stage 1~3 기존 시그니처 회귀 없음
- [ ] af-runner / af-test-runner 회귀 없음
- [ ] af.spec hiddenimports 반영
- [ ] frozen build smoke test

## 15. Open Questions

### OQ1. Request Harness 설계

본 문서는 상위 범용 요청 하네스를 다루지 않는다. 후속 문서가 필요하다.

추천 파일:

```text
docs/2026-05-14-request-harness-and-pipeline-dispatcher-design.md
```

### OQ2. `id == output_field` 강제 해제 여부

MVP는 강제 또는 강력 권장. 해제하려면 resume 병합 테스트와 schema migration 정책이 필요하다.

### OQ3. schema hash canonicalization

MVP 기본은 source YAML raw bytes hash다. 다만 주석/공백 변경 false positive가 많으면 canonical YAML hash로 전환한다.

### OQ4. paused_hitl garbage collection

장기 미응답 paused work-item 정리 정책은 P6b 이후 별도 설계한다.

### OQ5. Composite QuestionRef 마이그레이션 시점 (v4 신규)

MVP 는 A안 — global active id uniqueness + ledger provenance (§5.2.1). 다음 조건 충족 시 composite key `QuestionRef(question_set_id, question_id)` 로 마이그레이션:

- Request Harness 도입으로 active question set 수가 3개 이상
- 동일 id 재사용 요구가 design smell 이 아닌 정당한 use case 로 명확화
- ledger entry / paused artifact / resume merge logic 1회 breaking change 비용 허용

trigger 측정 지표: cross-yaml id collision hard fail 발생 빈도 (run_ledger 검색).

## 16. References

- ADR: `docs/decisions/ADR-20260514-133054-question-router-stage0.md`
- Design review: `docs/reviews/2026-05-14-140412-2026-05-14-question-router-detailed-design-design-review.md`
- 영향 코드:
  - `core/work_item_generator.py`
  - `core/project_pipeline.py`
  - `core/approval_gate.py`
  - `core/control/change_impact.py`
  - `core/control/execution_policy.py`
  - `core/control/run_ledger.py`
  - `af.spec`

## 17. Next Step

1. ADR `blast_radius` 매트릭스는 4-token 정정 완료 (v2 ADR 정정 이력).
2. 본 v4 freeze 직후 라운드 3 design review 자동 발화 대기.
3. BLOCK 0건 → ADR Status → Accepted → P1 StageRouter 구현 진입.
4. BLOCK 1건 이상 → 사용자 결정 (작업 freeze vs ADR 이월, 3-round cap [[feedback_design_review_rounds_stop_rule]]).
5. Request Harness 는 후속 ADR + 별도 설계문서로 분리. composite QuestionRef 마이그레이션은 §15 OQ5 trigger 충족 시 진행.

## 18. Changelog

### v4 (2026-05-14) — Codex 라운드 5 합의 + 7건 in-place 정정

| # | 항목 | 위치 |
|---|------|------|
| 1 | gate.initialize() 시그니처 (`status`, `execution_open` 추가, backward-compatible) | §8.3, §14 P5 |
| 2 | paused_hitl 시 gate.initialize(paused mode) A안 흐름 + approval-gate.md 생성 의무 | §3.1, §9.1 |
| 3 | "unknown work_kind" → "empty/non-enum compatibility guard" 정확 명명 + 보호 대상 3가지 | §3.2 |
| 4 | §7.2 platform 제거 / §7.1 existing_tests + Stage 1 only 변경 지점 / §7.3 research_scope + Stage 1 only 변경 지점 | §7.1, §7.2, §7.3 |
| 5 | §14 P5 migration test action table + 신규 test 7건 | §14 |
| 6 | Cross-YAML question.id uniqueness hard fail (StageRouter 시작 시 전체 active set 로드) | §5.2.1 신규 |
| 7 | Ledger provenance — `question_set_id` 필드 추가 (AssumptionLedgerEntry, PausedHitlArtifact, DomainReviewArtifact) | §7.3, §7.4, §7.5 |

§15 OQ5 신규: Composite QuestionRef 마이그레이션 trigger 명시.

### v3 (2026-05-14) — Codex 재설계 (Scope 한정 + sentinel + atomic write)

§1.2 Scope 한정 (Request Harness 분리), §7.5 PausedHitlArtifact sentinel, §11 atomic write 5개 적용, §13 시나리오 확장.

### v2 (2026-05-14) — Codex 라운드 1 BLOCK 9건 흡수 (superseded)

blast_radius 4-token, schema_hash 자기참조 제거, paused_hitl 반환 계약, Router SRP, resume 진입점, ApprovalGate semantics, LLMCaller 어댑터, frozen build, atomic write.

### v1 (2026-05-14, superseded)

ADR Draft 기반 초안. 9건 결함으로 Codex cross-review BLOCK.
