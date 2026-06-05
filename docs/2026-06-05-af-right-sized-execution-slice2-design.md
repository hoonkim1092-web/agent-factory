# AF Right-Sized Execution — 상세 설계 (슬라이스 2)

Date: 2026-06-05
Status: Detailed design — 구현 대기 (Sonnet)
Depends on:
- `docs/2026-06-03-af-right-sized-execution-decision.md` §Converged Design (Step 7)
- `docs/2026-06-03-af-right-sized-execution-detailed-design.md` (슬라이스 1, 구현 완료 `f208b632`)
Scope: **슬라이스 2만**. `ProjectPipeline`의 monolithic 실행을 `RouteDecision.required_stages`에 따라
       **additive 단계(research / doc-review)를 조건부 skip**하도록 만든다.

---

## 0. 이 문서가 확정하는 것 / 안 하는 것

확정:
- `RouteDecision.required_stages`가 `ProjectPipeline`까지 흐르는 **채널**(기존 `route` dict 재사용)
- `ProjectPipeline`에서 **실제로 skip 가능한 단계의 정확한 경계** (research, doc cross-review)
- skip 판정 helper(`_stage_enabled`)의 시맨틱과 하위호환 규칙
- production 배선 1곳 (`dogfood._run_develop_full` → `pipeline.run(route=...)`)
- test-first 테스트 계약 + Blueprint 동반 수정

안 함 (슬라이스 3 또는 별도):
- `plan` / `implement` / `test` 단계의 분리 실행 (= 파이프라인 본체 해체, 대수술)
- `design`(domain spec 생성)의 research-독립 실행 — §4.4의 알려진 한계로 기록
- `ProjectPipeline.run()`에 **신규 명시 파라미터** 추가 — §3.1에서 route-dict 채널 선택 (트레이드오프 명시)
- top-level(사용자 요청 → dogfood 진입) 라우팅 — 슬라이스 2 소비처는 dogfood full 경로 한 곳

---

## 1. 코드 baseline (실제 코드, 2026-06-05 grep 캡처)

> 메모리 규칙 `feedback_analysis_doc_baseline_must_be_real_code` 준수 — 아래 좌표는 추정이 아니라 실제 코드.

### 1.1 라우팅 산출물 (슬라이스 1, 이미 존재)
- `core/right_sized_router.py:33` `RouteDecision` — `:51 to_dict()`가 **`required_stages` 포함**해 직렬화.
  `:43 is_light()` = `source=="llm" AND confidence>=0.7 AND set(required_stages) ⊆ {plan,implement,test}`.
- `core/dogfood.py:1717` `_record_route_decision(state, route)` → `state.route_decision = route.to_dict()`
  (floor 적용된 최종 결정. Tier3면 design/review/cross_review 포함).
- `core/dogfood.py:1773` `_run_develop_phase` — `route.is_light() and scope` → `_run_develop_light`,
  else → `_run_develop_full(state, pipeline)`. **즉 `_run_develop_full`은 non-light 경로 전용.**

### 1.2 `ProjectPipeline`의 실제 단계 구성 (`core/project_pipeline.py`)
- `:1522 run()` = `:1538 prepare()` + auto-approve + `:1553 execute()`.
- `:1225 prepare()` = `:1239 prepare_brief()` + `:1248 prepare_documents()`.
- `:679 prepare_brief(task_input, workspace, ..., route: dict | None = None)`:
  - `:725-795` **research 블록** — `collect_evidence = getattr(self.research, "collect_project_evidence", None)`
    → `verifier.verify_with_retry(...)` (web search + 품질 검증 retry). **가장 비싼 additive 단계.**
  - `:727 risk_level = (route or {}).get("risk_level")`, `:728 comparison_mode = (route or {}).get(...)` — **route는 이미 소비 중.**
  - `:813-829` brief 생성 — `research_project_brief(...)`. `evidence_bundle`은 **optional kwarg**(`:803 "evidence_bundle" in brief_params`) → research_evidence 비어도 동작.
  - `:825 project_brief["route"] = route or {}` — **route가 project_brief에 보존됨**(prepare_documents에서 회수 가능).
- `:856 prepare_documents(prepared_brief, ...)`:
  - `project_brief = prepared_brief.project_brief`. **현재 코드엔 route 회수 라인 없음** — slice2 구현 시 `project_brief.get("route")` 회수 라인을 신규 추가(§3.3). prepare_documents는 route를 인자로 받지 않으므로 `project_brief["route"]`가 유일 경로.
  - `:933-967` Domain Spec Gate — `_domain = (project_brief.get("research_plan") or {}).get("domain")`. **research_plan은 research_evidence 산물**(`:928-931 D3 주입`) → research skip 시 domain="" → spec/ADR 생성 자체가 안 일어남(§4.4).
  - `:1076-1138` **doc cross-review 블록** — `DocumentReviewSession`. `:1080 if _level != "starter":` 가드. 1~2 라운드 LLM 문서 검토. **두 번째 additive 단계.**
- `:1254 execute()` = 승인 → role materialize → `:1347 DynamicOrchestrator(terminal_per_agent=True).run_project()`. **파이프라인 본체(implement/test) — slice2 비대상.**

### 1.3 production caller (배선 영향 평가)
- `core/dogfood.py:1726` `pipeline.run(task_input=, workspace=, runtime_workspace=)` — **route 미전달**. ← slice2가 고칠 유일한 곳.
- `agent_launcher.py:676` `self.project_pipeline.run(...)` — route는 express/intake 산물(risk_level/comparison_mode). required_stages 없음 → 하위호환.
- `run_factory_cli.py:922` `factory.run(...)`, `:910 prepare_brief(...)` — 동일.
- `core/control/maintenance_pipeline.py:164` `prepare(task_input)` — route 없음 → 하위호환.
- `core/pdca_commands.py:243` `pp.prepare(...)` — route 없음 → 하위호환.

**결론**: required_stages를 route dict로 흘리면 production caller 4곳은 **무변경으로 전체 실행**(현 행위 보존), dogfood 1곳만 명시 배선.

---

## 2. 핵심 설계 결정과 트레이드오프 (구현 전 명시)

| # | 결정 | 근거 / 트레이드오프 |
|---|------|-------------------|
| A | slice2의 skippable 단계는 **research·doc-review 2개로 한정** | ProjectPipeline에서 plan/implement는 본체(역할→보드→orchestrator), design(domain spec)은 research 종속. 이 둘만 분리하려면 파이프라인 해체 = slice3. research·doc-review만 진정한 *additive*. decision Step 7 "no-research pipeline" 예시와 정확히 일치. |
| B | required_stages를 **기존 `route` dict로 전달** (신규 명시 파라미터 추가 안 함) | route는 이미 라우팅 메타 채널(risk_level/comparison_mode)이고 prepare_brief 인자+project_brief 양쪽에서 접근 가능 → **0개 시그니처 변경**. RouteDecision.to_dict()가 이미 required_stages 직렬화. **트레이드오프**: 제어 플래그가 dict에 "숨음"(명시 파라미터보다 발견성↓). **반론 기각 근거**: 명시 파라미터는 run/prepare/prepare_brief/prepare_documents 4개 시그니처 + 2번째 채널 신설 → surgical 원칙 위배. route가 곧 "stage-선택 파라미터". |
| C | skip 판정 = **보수적 기본 "전체 실행"** | `required_stages` 키가 없거나 빈 리스트 → **모든 단계 실행**(하위호환). 명시적으로 non-empty 리스트일 때만, 해당 단계가 리스트에 **없으면** skip. under-route(필요한데 생략) 금지의 결정적 구현 — slice1과 동일 비대칭. |
| D | doc-review는 `review` **또는** `cross_review` 중 하나라도 있으면 실행 | RouteDecision 어휘는 둘을 분리(STAGE_VOCAB). DocumentReviewSession은 단일 게이트 → 둘 중 하나라도 요구되면 켠다(보수적 OR). |
| E | research skip 시 research_evidence를 **`{}`로 두되 artifact·checkpoint는 동일 shape로 기록** | 후행 단계(plan-verify, domain gate, dashboard)가 research_evidence를 읽으므로 키 부재가 아닌 빈 dict로 통일 → 정규화 동형성 유지. `_coverage_blocked({})==False`, `_domain==""` 자연 흐름. |
| F | floor 상호작용은 slice1이 이미 보장 | Tier3 파일 → slice1 `_apply_safety_floors`가 design/review/cross_review를 required_stages에 강제 주입 → slice2 doc-review 게이트는 Tier3에서 **항상 켜짐**. sensitive 변경이 무검토로 새는 경로 없음. |

---

## 3. Module — `core/project_pipeline.py` 변경

### 3.1 stage 게이트 helper (모듈 전역 신규)

```python
def _stage_enabled(route: dict | None, *stage_names: str) -> bool:
    """route.required_stages 기준으로 단계 실행 여부 판정.

    required_stages 키 부재/빈 리스트 → True (전체 실행, 하위호환).
    non-empty 리스트면 stage_names 중 하나라도 포함될 때만 True.
    """
    stages = (route or {}).get("required_stages")
    if not stages:
        return True
    return any(n in stages for n in stage_names)
```

> 단일 진실: skip 시맨틱을 이 함수 하나에 모은다(하드코딩 분기 금지, NEXT_STEPS §하드코딩 금지 원칙).

### 3.2 research 게이트 (`prepare_brief`, `:725-795`)

현 research 블록 전체를 게이트로 감싼다. **블록 경계만 들여쓰고 내부는 무변경**:

```python
# -- Research --
research_agent = build_bootstrap_agent("research_director")
risk_level = str((route or {}).get("risk_level") or "normal").strip()
comparison_mode = bool((route or {}).get("comparison_mode", False))
research_evidence: dict = {}
if _stage_enabled(route, "research"):
    collect_evidence = getattr(self.research, "collect_project_evidence", None)
    if callable(collect_evidence):
        ...  # 기존 verify_with_retry 블록 전체 (무변경)
else:
    print("[ProjectPipeline] research stage skipped (route.required_stages)")
# research_evidence_path 쓰기 + checkpoint는 게이트 밖 — 항상 기록(빈 dict라도 shape 유지)
research_evidence_path = os.path.join(planning_dir, "research_evidence.json")
self._write_json(research_evidence_path, research_evidence)
self._save_checkpoint(state_workspace, "evidence_acquisition", research_evidence)
```

핵심: `research_evidence_path` write + `_save_checkpoint`는 **게이트 밖에 유지**(현 `:793-795`와 동일 위치) →
skip 경로도 빈 `research_evidence.json`을 남겨 artifact 무결성·재시작 정합 유지(결정 E).
brief 생성(`:797-829`)은 게이트 밖 — research 없이도 `evidence_bundle={}`로 동작(`:803` optional kwarg).

### 3.3 doc cross-review 게이트 (`prepare_documents`, `:1076-1138`)

> **신규 라인**: `_route = project_brief.get("route")`는 현재 `prepare_documents`에 **없는 코드**다 — slice2가 추가한다
> (prepare_documents는 route 인자를 안 받으므로 `project_brief["route"]`(prepare_brief가 `:825`에서 보존)가 유일 회수 경로).

```python
# -- 문서 교차검증 QA --
cross_review_result = None
_route = project_brief.get("route")   # ← slice2 신규: prepare_brief가 :825에서 보존
if _stage_enabled(_route, "review", "cross_review"):
    try:
        from core.review_report import DocumentReviewSession
        ...  # 기존 블록 전체 (무변경)
    except Exception as _cr_err:
        _safe_print(f"[Pipeline] doc cross-review skipped: {_cr_err}")
else:
    _safe_print("[Pipeline] doc cross-review skipped (route.required_stages)")
```

> 기존 `_level != "starter"` 가드는 게이트 **안쪽**에 그대로 둔다(starter는 여전히 doc-review 없음).
> 즉 실행 조건 = `(review|cross_review 요구) AND level != starter`. 두 게이트는 AND로 합쳐짐.

### 3.4 정규화 동형성 (불변식)

research skip 여부와 무관하게 `prepare_documents` 반환 `PreparedProject`의 필드 shape는 동일하다
(`research_evidence`는 `{}`, `research_evidence_path`는 빈 dict를 가리킴). `execute()`·dashboard·dogfood
`_normalize_develop_result`는 변경 없이 동일하게 소비. 테스트로 봉인(§5 inv-NORM).

---

## 4. production 배선 — `core/dogfood.py`

### 4.1 `_run_develop_full` route 전달 (`:1722-1735`)

```python
def _run_develop_full(state: DogfoodState, pipeline: Any) -> dict[str, Any]:
    """Full DEVELOP path: delegate to ProjectPipeline inside isolation env."""
    worktree = state.worktree_workspace or state.source_workspace
    with _develop_isolation_env(worktree):
        result = pipeline.run(
            task_input=state.task,
            workspace=worktree,
            runtime_workspace=state.runtime_workspace,
            route=state.route_decision or None,   # ← slice2: required_stages 전달
        )
    ...  # 이하 무변경
```

`state.route_decision`은 `_record_route_decision`이 floor 적용된 `route.to_dict()`로 채움(§1.1).
`required_stages`가 fallback(full 7단계)이면 research 포함 → 현 행위와 동일. subset(research 없음)이면 skip.
`{}`(미설정) 방어를 위해 `or None` — `_stage_enabled(None, ...)` → True(전체 실행).

### 4.2 배선 검증 (CLAUDE.md 파이프라인 배포 동등성 규칙)

- `state.route_decision`은 `_run_develop_phase`가 `_run_develop_full` 호출 **전에** `_record_route_decision`으로 채움 → null 아님 보장(단 `to_dict()` 결과).
- `route` dict에 `risk_level`/`comparison_mode` 키는 없음(RouteDecision.to_dict() 비포함) → `prepare_brief:727-728`의 `.get(... )` 기본값으로 안전(normal/False).
- 나머지 4 caller는 무변경 → required_stages 없는 route → 전체 실행(§1.3).

### 4.3 light 경로 무영향

`_run_develop_light`은 ProjectPipeline을 안 쓰므로 slice2 게이트와 무관. slice1 동작 그대로.

### 4.4 알려진 한계 (정직 기록 — slice3 후보)

- **design(domain spec) ⊥ research 분리 불가**: ProjectPipeline의 design 산물(SpecGenerator/ADR/traceability)은
  `research_plan.domain`에 게이트되고 research_plan은 주로 research_evidence 산물. 따라서 research를 끄면 design도 **대개** 자동으로 꺼진다.
  required_stages=[design,plan,implement,test](research 없이 design만)는 **현 파이프라인에서 명시 표현 불가** —
  design을 research-독립으로 만들려면 SpecGenerator 입력을 brief에서 직접 파생해야 함(slice3 대수술). slice2는 이 조합을 **research 켜짐으로 안전 처리하지 않음** — 단지 design이 대개 안 도는 더 가벼운 파이프라인이 됨.
  - ⚠️ **조건부 예외 (cross-review ACCEPT-ADV #1)**: D3 주입(`project_pipeline.py:928 if not project_brief.get("research_plan") and research_evidence`)은 brief에 research_plan이 **없을 때만** evidence에서 주입한다. 그런데 LLM `research_project_brief()`가 brief에 `research_plan`을 **직접 포함**해 반환하면 D3을 건너뛰고 `_domain`이 채워진다 → research_evidence={} 상태에서도 domain spec 블록이 실행된다(`SpecGenerator().generate(project_brief)`는 evidence 없이 project_brief만 소비, `_coverage_blocked({})==False`로 예외 없이 통과). 즉 "research skip → design 자동 꺼짐"은 **brief가 research_plan을 직접 안 줄 때만** 성립. 이는 결함이 아니라 결합의 한계 — slice2는 이를 막지 않고 관측만 한다(§5.3 Case 3은 "항상 관측"이 아니라 "조건부 관측").

---

## 5. 테스트 계약 (test-first, Tier 3 → 3-Tier 필수)

### 5.1 `tests/test_project_pipeline.py` (또는 신규 `test_project_pipeline_stage_gate.py`) — `_stage_enabled` 단위

| ID | route | 호출 | 기대 |
|----|-------|------|------|
| G-NONE | `None` | `_stage_enabled(None,"research")` | True (전체) |
| G-EMPTY | `{"required_stages": []}` | `("research")` | True (전체) |
| G-NOKEY | `{"risk_level":"low"}` | `("research")` | True (하위호환) |
| G-IN | `{"required_stages":["research","plan"]}` | `("research")` | True |
| G-OUT | `{"required_stages":["plan","implement","test"]}` | `("research")` | False |
| G-OR-HIT | `{"required_stages":["review"]}` | `("review","cross_review")` | True |
| G-OR-MISS | `{"required_stages":["plan"]}` | `("review","cross_review")` | False |

### 5.2 `prepare_brief` / `prepare_documents` 통합 (mock research/review)

| ID | 시나리오 | 기대 |
|----|---------|------|
| inv-RESEARCH-SKIP | `route={"required_stages":["design","plan","implement","test","review"]}`, `collect_project_evidence` mock | mock **미호출**, `research_evidence=={}`, `research_evidence.json` 존재(빈 dict), brief 생성됨 |
| inv-RESEARCH-RUN | `route=None` | `collect_project_evidence` **호출**(회귀: 기존 행위) |
| inv-REVIEW-SKIP | `route={"required_stages":["plan","implement","test"]}`, `DocumentReviewSession` mock | session **미생성**, prepared 정상 반환 |
| inv-REVIEW-RUN | `route=None`, level=dynamic | DocumentReviewSession 호출(회귀) |
| inv-NORM | research skip vs run 양쪽 `PreparedProject` 필드 키 동일 + `research_evidence_path` 항상 존재 | shape 동형 |
| inv-STARTER | `route={"required_stages":["review"]}`, level="starter" | doc-review **여전히 skip**(AND 게이트) |

### 5.3 dogfood 배선 + acceptance

| ID | 시나리오 | 기대 |
|----|---------|------|
| inv-WIRE | `_run_develop_full` + `pipeline` mock | `pipeline.run`이 `route=state.route_decision`로 호출됨 |
| inv-WIRE-FALLBACK | `state.route_decision={}` | `pipeline.run(route=None)` (방어) |

acceptance (실제 dogfood run, 검증 레버 `AGENT_CHAT_PROVIDER=claude_cli`):
1. **research 없는 full task** — required_stages에 research 빠진 결정 유도(예: 알려진 코드 영역의 design+plan+implement+review) → ProjectPipeline이 research collect 호출 **0회**(로그 `research stage skipped`) + 나머지 정상. cost 절감 관측.
2. **fallback full task** — LLM 예외/저신뢰 → required_stages=full(research 포함) → 기존과 동일 전체 실행(회귀).
3. **design-without-research 한계 관측**(§4.4) — required_stages=[design,...]를 유도해 domain spec 거동 관측. **brief가 research_plan을 직접 안 주면** domain spec skip(예상), **주면** research_evidence={}여도 domain spec 실행(§4.4 조건부 예외). 둘 다 버그 아님 — 결합 한계 기록(slice3 경계).

---

## 6. 동반 수정 (CLAUDE.md 규칙)

- **신규 core/*.py 없음** → af.spec 변경 없음.
- `Master_Blueprint.md` §3 project_pipeline 서브시스템(stage 게이트) + §10 Blast Radius(dogfood→project_pipeline route 전달) + §12 이력.
- `RouteDecision` STAGE_VOCAB·is_light() 무변경(slice2는 소비만 추가).

---

## 7. 잔여 위험 / 감시 포인트

1. **route dict 채널 오염**: required_stages를 route에 실은 뒤, 누군가 같은 route에 risk_level 등 추가해도
   `_stage_enabled`는 required_stages만 읽으므로 무해. 단 route를 새로 만드는 신규 caller가 required_stages를
   **의도치 않게** 빈 아닌 리스트로 채우면 silent skip 위험 → 기본 None/미키 = 전체실행이 안전판.
2. **research skip → domain spec cascade**(§4.4): design이 함께 꺼지는 의도된 결합. slice3에서 분리 검토.
3. **doc-review skip의 품질 영향**: non-Tier3 + review 미요구 시 work-item 문서 무검토 통과. floor가 Tier3는 보호하나
   Tier1/2 문서 품질은 dogfood 자체 REVIEW phase + review-gate에 의존. 측정 후 재평가.
4. **prepare_documents의 plan-verify(`:992-1033`)는 게이트 안 함** — 항상 실행. research skip해도 PlanVerifier는 돌아
   work-item 정합 최소 보장 유지(의도).

---

## 8. 구현 순서 (Sonnet 핸드오프)

```
1. tests: _stage_enabled 단위 7케이스 (RED) — §5.1
2. project_pipeline.py: _stage_enabled helper 추가 (GREEN)
3. tests: prepare_brief/prepare_documents 게이트 6케이스 (RED) — §5.2
4. project_pipeline.py: research 게이트(prepare_brief) + doc-review 게이트(prepare_documents) (GREEN)
   — 블록 들여쓰기만, 내부 무변경. research_evidence write/checkpoint는 게이트 밖 유지.
5. tests: dogfood _run_develop_full 배선 2케이스 (RED) — §5.3
6. dogfood.py: _run_develop_full에 route=state.route_decision or None 추가 (GREEN)
7. Blueprint §3/§10/§12
8. acceptance dogfood run 3종 (§5.3)
9. 3-Tier: af-critic → af-cross-review → af-test-runner (core/ Tier3 → cross-review 필수)
```

설계 = Opus(본 문서). 구현 = `/model sonnet`.
```
```
