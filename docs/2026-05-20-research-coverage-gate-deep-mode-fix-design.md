# 2026-05-20 Research Coverage Gate — deep/fresh/live 모드 우회 수정 설계

## 0. 요약

`core/researcher.py`의 `collect_project_evidence()`에서 coverage gate가 `archive_research`
모드에만 사실상 적용되고, `risk_level="high"`인 `deep_source_research` /
`live_project_analysis`와 `fresh_lookup`에서는 우회된다. 가장 엄격해야 할 경로가
게이트를 안 받는 구조적 역전이다. 본 설계는 두 가지 surgical fix를 다룬다.

- **Step A** — coverage checklist 계산을 분기 밖으로 hoist (동작 변경 / 본 설계 핵심)
- **Step B** — escalation 재귀 시 `scores` 보존 (관측성 / 2줄, 저위험)

비범위: Width planner, Permission policy, planner ordering + prompt rule, persisted
`project_brief.json` 부채. (§6 참조)

근거: 2026-05-19~20 Codex ↔ Claude 교차 검토. 코드 baseline은 §2에 실제 발췌로 고정.

> **v2 (2026-05-20)**: af-cross-review WARN 4건 반영 — checklist 계산 시
> 순수 fast_synthesis 제외(§3), no-Tavily `llm_prior_refs`를 coverage에 반영(§3),
> Step B 논거에 `external_stack_score>=3` 경로 보강(§1), 테스트 2건 추가(§5).

---

## 1. 문제 (확인된 팩트)

### Step A — coverage gate 우회

`collect_project_evidence()`(`researcher.py:933`)는 3개 분기로 evidence를 수집한다.

| 분기 | 조건 | `_domain_checklist` 할당 |
|------|------|--------------------------|
| `if research_plan.requires_web:` (`:971`) | fresh_lookup / deep_source_research / live_project_analysis | **없음 (None 유지)** |
| `elif mode == "fast_synthesis":` (`:989`) | fast_synthesis | **없음 (None 유지)** |
| `else:` (`:993`) | archive_research 등 | `:995`에서 할당 |

`_emit_coverage_report()`(`:736`)는 `if not domain_checklist or not domain: return {}`
(`:747`)로 조기 반환한다. 따라서 requires_web / fast_synthesis 모드에서는
`coverage_report`가 `initial_evidence`에 들어가지 않는다(`:1134` `if _coverage:` 미충족).

다운스트림 `_coverage_blocked()`(`project_pipeline.py:281-282`)는
`coverage_report.get("block")`을 보므로, report가 없으면 항상 `False` →
work-item 생성이 무차단 통과한다(`project_pipeline.py:962`).

**결과**: coverage gate가 `domain` 있는 `archive_research` 프로젝트에만 적용된다.
`risk_level="high"` 모드(deep/live)는 게이트가 0이다.

### Step B — escalation scores 손실

router-gap escalation 재귀 호출(`researcher.py:1109`)이 `research_plan=`을 넘기지
않는다. escalation 분기(`:952`)는 `ResearchPlan.for_mode(escalated_mode)`를 `scores=`
없이 호출 → 생성된 plan의 `scores={}`.

동작 영향은 없다. escalation은 `final_mode ∈ {fast_synthesis, fresh_lookup}`일 때만
발화한다(`research_router.py:240` `is_pre_deep`). `_select_mode`의 deep 직접 진입
조건은 `deep_decision_score >= 2 or operational_risk_score >= 3`(`:315`)이므로,
escalation이 발화하려면 이 둘이 **모두 거짓** — 즉 `deep_decision_score < 2` 및
`operational_risk_score < 3`. 한편 `detect_complexity_gaps`의 `deep_signal`은
`external_stack_score >= 3`도 포함하므로(`:235-238`), escalation은 실제로는
주로 `external_stack_score >= 3` 신호로 발화한다(이 신호는 `_select_mode`의
deep 직접 진입 조건에는 없는 비대칭). 그러나 어느 escalation 경로든
`operational_risk_score < 3`이 보장되고, `for_mode`의 `research_depth="deep"`는
`operational_risk_score >= 3`을 요구하므로(`:114`), scores를 넘기든 안 넘기든
`research_depth="normal"`이 된다. `requires_research`도 `mode=="deep_source_research"`라
항상 True. 따라서 scores 전달은 동작을 바꾸지 않고 관측성만 회복한다.

**결과**: 동작 불변. 단 `research_evidence.json`의 `research_plan.scores`가 `{}`로
남아 "왜 escalation 됐는지"(어떤 신호가 임계를 넘겼는지) 추적이 불가능하다.
domain은 `:953`(`research_plan.domain = prev_domain`)에서 이미 보존되므로 손실 없음.

---

## 2. Baseline (실제 코드 발췌)

`core/researcher.py:969-1019` (분기 구조, 발췌):

```python
_domain_checklist: list[str] | None = None  # B1: else 분기에서 할당, 이후 재사용

if research_plan.requires_web:
    # fresh_lookup/deep/live: local + secondary 병렬 수집
    ...   # _domain_checklist 미할당
elif mode == "fast_synthesis":
    local_refs = self._collect_local_references(task_input, target_workspace)
    ...   # _domain_checklist 미할당
else:
    # archive_research 또는 기타: RecoverySearchLoop
    _quality_contract = self._build_quality_contract(task_input, research_plan)
    _domain_checklist = (
        [item.id.replace("_", " ") for item in _quality_contract.checklist]
        if _quality_contract
        else self._load_domain_manifest(research_plan.domain)
    )
    if not _domain_checklist:
        _domain_checklist = ["requirements_coverage", "architecture_rationale"]
    _max_rounds = 3 if research_plan.research_depth == "deep" else 2
    local_refs = self._collect_local_references(task_input, target_workspace)
    _recovery_rounds = 0
    while _recovery_rounds < _max_rounds:
        ...   # RecoverySearchLoop — _domain_checklist 사용
```

`core/researcher.py:1103-1115` (escalation 재귀):

```python
if hint_gaps is None:
    router_gaps = ResearchRouter().detect_complexity_gaps(task_input, initial_evidence, mode)
    if router_gaps:
        return self.collect_project_evidence(
            task_input,
            workspace=workspace,
            risk_level=risk_level,
            comparison_mode=comparison_mode,
            hint_gaps=router_gaps,        # research_plan= 미전달
        )
```

`core/researcher.py:946-953` (escalation 분기):

```python
if hint_gaps:
    escalated_mode = gap_to_mode(hint_gaps)
    if escalated_mode and (research_plan is None or research_plan.mode != escalated_mode):
        prev_domain = (research_plan.domain if research_plan else None) or ResearchRouter()._detect_domain(task_input)
        research_plan = ResearchPlan.for_mode(escalated_mode)   # scores= 미전달 → scores={}
        research_plan.domain = prev_domain
```

---

## 3. Step A 설계 — checklist 계산 hoist

### 변경 A-1 — checklist 계산 hoist (순수 fast_synthesis 제외)

`_quality_contract` + `_domain_checklist` 계산 블록을 3분기 **진입 전**으로 올린다.
단 무조건 hoist하지 않는다 — `_build_quality_contract`는 `WorkSpecExtractor` 경유
**LLM 호출**(`core/research/work_spec.py:55-63`)을 포함하므로, 게이트가 어차피
미적용인 순수 `fast_synthesis` 경로에서는 호출을 건너뛴다.

계산 조건: **`research_plan.requires_web or mode != "fast_synthesis"`**.
이는 "requires_web 분기" + "else 분기"를 포함하고, `requires_web=False`인 순수
`fast_synthesis` 분기만 제외한다(fast_synthesis + secondary fresh_lookup은
`requires_web=True`이므로 포함됨 — coverage 필요).

```python
# 분기 진입 전 (조건부 hoist)
_quality_contract = None
_domain_checklist: list[str] | None = None
if research_plan.requires_web or mode != "fast_synthesis":
    _quality_contract = self._build_quality_contract(task_input, research_plan)
    _domain_checklist = (
        [item.id.replace("_", " ") for item in _quality_contract.checklist]
        if _quality_contract
        else self._load_domain_manifest(research_plan.domain)
    )
    if not _domain_checklist:
        _domain_checklist = ["requirements_coverage", "architecture_rationale"]

if research_plan.requires_web:
    ...
elif mode == "fast_synthesis":
    ...                     # _domain_checklist 는 None — 호출 자체가 스킵됨
else:
    _max_rounds = 3 if research_plan.research_depth == "deep" else 2
    ...                     # while 루프는 hoist된 _domain_checklist 재사용
```

`_max_rounds`는 `else` 분기에 남긴다(RecoverySearchLoop 전용).

### 변경 A-2 — no-Tavily `llm_prior_refs`를 coverage에 반영

no-Tavily 환경에서 requires_web 모드는 `web_refs` 대신 `llm_prior_refs`를
수집한다(`researcher.py:976,988`). 그런데 `_emit_coverage_report`는
`local_refs + web_refs`만 join하고(`:761`) `llm_prior_refs` 파라미터가 없다.
Step A로 게이트를 켜면 **TAVILY 키 없는 배포 사용자**의 deep/fresh/live 프로젝트가
llm_prior 증거를 가졌어도 local-only 기준으로 평가되어 false BLOCK될 수 있다 —
CLAUDE.md "파이프라인 배포 동등성 규칙" 위반.

수정: `_emit_coverage_report`에 `llm_prior_refs` 파라미터를 추가하고 join 대상에
포함한다. 호출부(`researcher.py:1125-1133`)도 `llm_prior_refs`를 전달한다.
`_final_unmet` 계산(`_identify_unmet_gaps`, `:1087`)도 동일하게 `llm_prior_refs`를
반영해 일관성을 유지한다.

```python
def _emit_coverage_report(self, domain, domain_checklist, local_refs,
                          web_refs, slug, rounds_used, workspace=None,
                          llm_prior_refs=None):
    ...
    joined = " ".join(
        (r.get("excerpt") or "") + " " + (r.get("heading") or "") + " " + (r.get("title") or "")
        for r in local_refs + web_refs + (llm_prior_refs or [])
    ).lower()
```

### 부작용 분석

| 효과 | 분류 | 비고 |
|------|------|------|
| requires_web + `domain` 프로젝트가 `coverage_report` 생성 → BLOCK 가능 | **의도된 동작 변경** | 본 수정 목표 |
| 비-domain 프로젝트 `coverage_report` | **불변** | `_emit_coverage_report`의 `not domain` 가드(`:747`)가 여전히 `{}` 반환 |
| `_final_unmet`/`unmet_gaps`(`:1086-1100`)가 requires_web 모드에서도 채워짐 | **inert** | grep 결과 `unmet_gaps` 소비처 없음 — research_evidence.json 필드만 비→채워짐, 동작 영향 0 |
| `_build_quality_contract` LLM 호출이 requires_web 경로에 신규 추가 | **허용** | 순수 fast_synthesis는 변경 A-1 조건으로 제외. provider 불가/실패 시 `try/except`로 None → `_load_domain_manifest` fallback (`:636-638`) |
| no-Tavily 환경 deep/fresh/live 프로젝트의 coverage 평가 | **개선** | 변경 A-2로 `llm_prior_refs` 반영 → false BLOCK 방지, 배포 동등성 유지 |

`_build_quality_contract`는 `domain=""`에서도 `WorkSpecExtractor`로 task 기반 contract를
만들 수 있다(`:627-633`). 따라서 hoist 후 비-domain 프로젝트도 `_domain_checklist`가
non-empty가 될 수 있으나, `_emit_coverage_report`의 `not domain` 가드가 coverage_report를
계속 `{}`로 유지하므로 coverage gate 동작은 불변이다.

### BLOCK 위험 범위

현재 `domain` 값은 `"poker"` 하나뿐(`research_router.py:_detect_domain_hints`).
따라서 Step A가 새로 BLOCK을 발생시킬 수 있는 대상은 **`domain="poker"` +
(deep_source_research | fresh_lookup | live_project_analysis)** 프로젝트로 한정되며,
그중에서도 `match_rate < 0.7` 또는 `missing >= 3`(`researcher.py:771`)일 때만이다.
비-poker 프로젝트는 동작 불변.

---

## 4. Step B 설계 — escalation scores 보존

```python
# researcher.py:1109 재귀 호출
return self.collect_project_evidence(
    task_input,
    workspace=workspace,
    risk_level=risk_level,
    comparison_mode=comparison_mode,
    research_plan=research_plan,      # 추가
    hint_gaps=router_gaps,
)
```

```python
# researcher.py:952
research_plan = ResearchPlan.for_mode(
    escalated_mode,
    scores=research_plan.scores if research_plan else None,   # 추가
)
```

효과: 동작 불변, `research_evidence.json`의 `research_plan.scores`에 escalation 직전
신호 점수가 보존됨 → escalation 사유 추적 가능. `prev_domain`도 재탐지 없이
직전 plan의 domain을 그대로 사용.

---

## 5. 테스트 계획

| # | 시나리오 | 기대 |
|---|----------|------|
| 1 | deep_source_research + domain=poker + requires_web=True | `research_evidence["coverage_report"] != {}` |
| 2 | fast_synthesis + domain="" | `coverage_report == {}` (회귀 — 불변) |
| 3 | archive_research + domain=poker (기존 else 경로) | coverage_report 기존과 동일 (회귀) |
| 4 | fresh_lookup → deep escalation | `research_evidence["research_plan"]["scores"] != {}` |
| 5 | escalation 후 | `research_plan["domain"]` 보존 (회귀) |
| 6 | TAVILY_API_KEY 미설정 + deep_source_research + domain=poker, `llm_prior_refs`에 poker 증거 포함 | coverage 계산이 `llm_prior_refs` 반영 → 증거 충분 시 false BLOCK 없음 (변경 A-2) |
| 7 | `external_stack_score=3, deep_decision_score=0, operational_risk_score=0` + fast_synthesis → deep escalation | escalation 발화 + `research_plan["research_depth"] == "normal"` (동작 불변 검증) |
| 8 | 순수 fast_synthesis (requires_web=False) | `_build_quality_contract` 미호출 — LLM 호출 0 (변경 A-1 비용 회귀 방지) |

---

## 6. 비범위 (명시적 제외)

- **C — research_plan ordering + planner prompt rule**: `project_pipeline.py:927`의
  주입을 planner 호출(`:888`) 앞으로 이동 + `bootstrap_roles.py` prompt에
  `research_plan.mode/domain/research_depth` 활용 규칙 추가. planner는 project_brief를
  JSON 통째로 받으므로(`bootstrap_roles.py:402`) ordering 단독은 효과가 약하고
  불안정 — prompt rule과 묶어야 의미. **Width planner 도입과 함께** 별도 진행.
- **D — WidthPlanner / PermissionPolicy**: 신규 기능. 별도 work-item.
- **persisted `project_brief.json` 부채**: `project_brief.json`은 prepare_brief
  (`project_pipeline.py:827-828`)에서 기록되고 D3 주입(`:928`) 이후 재기록되지
  않아 디스크 artifact에 research_plan이 누락된다. 디버깅/감사 부채 — 별도 항목.

---

## 7. Blast Radius

- 수정 파일: `core/researcher.py` (`collect_project_evidence`) — core 핵심, subprocess
  없음 → Review-Gate Tier 2~3 (af-critic → af-cross-review → af-test-runner).
- 직접 다운스트림: `core/project_pipeline.py` `_coverage_blocked` → work-item 생성 게이트.
- Blueprint 동기화 대상: §3 research 서브시스템 + §12 변경 이력.
