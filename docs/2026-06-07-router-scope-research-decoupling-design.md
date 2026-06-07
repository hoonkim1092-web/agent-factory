# Router scope/research decoupling — 설계문서

- 작성일: 2026-06-07
- 작성: Opus (3라운드 deliberation 수렴, 메모리 `project_router_research_decoupling`)
- 브랜치: `2026-06-04-right-sized-execution-slice1`
- 상태: **af-cross-review WARN (BLOCK 0, single-vendor) 3건 + 외부리뷰 5건 검토·반영 완료. → `/model sonnet` Phase 1+2 구현 대기.**
  - af-cross-review 반영: #1 markers/to_dict(사실오류), #2 INV-5 의존 명시, #3 _emit_phase_trace API 오류.
  - 외부리뷰 반영: #1 MergePolicy 소유권 근거 명시(별도 구조 기각), #2 actual_changed=[] 관측불능 3분류+테스트, #5 is_light() marker-aware 0.85 SSOT. **#3(auto_policy 금지 테스트)·#4(markers)는 이미 반영돼 있던 항목 — 재확인.**
- 선행: RSE 슬라이스1/2(완료), codebase wiki light COMPLETE 실증(`7a3f44e5`)
- 관련 설계: `docs/2026-06-03-af-right-sized-execution-detailed-design.md`(§3 라우터), `docs/2026-06-05-af-right-sized-execution-slice2-design.md`(stage skip)

---

## §0 제품 목표 (사용자 확정 — 재논쟁 금지)

사용자가 자연어로 "만들어줘 / 문서화해줘 / 고쳐줘"를 던지면 AF가:

1. **입구(routing)**: 불필요한 full/research로 새지 않고 적절한 light로 진입한다.
2. **출구(completion)**: 완료를 *phase success* 가 아니라 *evidence-backed criteria* 로 닫는다.

OMO ULW-loop 원칙(스마트 입구 / evidence 출구)만 흡수하며 파이프라인 베끼기가 아니다.

이 문서는 **입구(Phase 1+2)** 를 구현 대상으로 확정하고, **출구(Phase 3+4)** 는 게이트 뒤로 명시 보류한다.

---

## §1 결함 (baseline = 실제 코드, grep 확정)

### 1.1 입구 결함 — scope 추출 성공이 routing을 오염

`core/dogfood.py:1784` `_run_develop_phase` → `_intended_scope(task)` → `core/spec_compiler.py:101 _scope_from_intent`:

```python
# spec_compiler.py:108-109
matches = _PATH_TOKEN_RE.findall(intent)
return [m for m in dict.fromkeys(matches) if _PATH_RE.search(m) and not m.startswith("//")]
```

토큰이 **확장자 AND 경로 구분자** 둘 다 가져야 scope로 인정된다. 따라서:

- `"codebase symbols.md 만들어줘"` → `symbols.md`는 경로 구분자 없음 → **scope=[]**
- scope=[] → `right_sized_router.classify:268-269`:

```python
# right_sized_router.py:267-269
files: list[str] = list(changed_files or [])
if not files:
    return _fallback_decision("no changed_files: scope required for routing")
```

→ LLM 판단(`:283`) **앞에서** 무조건 full(7-stage + worktree)로 단락. deterministic greenfield 문서화 작업이 멀티에이전트 full 오케스트레이터로 과분해 → 문서 sprawl → blocked. **실증**: 첫 wiki throw `symbols.md`가 full로 빠져 191 cycle 후 blocked, 경로 한정 재-throw(`scripts/codebase_symbols.py`)는 light 수렴(run `1780813496`).

**즉 "scope 추출 실패"가 "research/full 필요"로 잘못 해석된다.** 이것이 자연어 UX 입구 버그.

### 1.2 입구 결함의 이중 단락 (Phase 1이 둘 다 풀어야 함)

scope=[]는 **두 곳**에서 light를 막는다:

1. `right_sized_router.classify:268-269` — LLM 호출 전 early fallback.
2. `dogfood.py:1788` dispatch guard:

```python
# dogfood.py:1788-1790
if route.is_light() and scope:        # ← `and scope` belt-and-suspenders
    return _run_develop_light(state)
return _run_develop_full(state, pipeline)
```

router만 고치고 dispatch guard를 두면 scope=[] light는 여전히 full로 강등된다. **두 지점 모두 의도 변경 대상.**

### 1.3 출구 단절 4곳 (grep 확정 — Phase 3 대상, 본 PR 미구현)

| # | 위치 | 현재 동작 | 결함 |
|---|------|----------|------|
| ① | `completion_criteria` (`dogfood.py:175` 필드, 채움 `:1413` full / `:1759` light from `spec.success_criteria`) | 저장만 됨 | **gate-reader 0건** — 소비처는 역직렬화(`:264`)·planner(`:531`)뿐, 완료 판정에 미사용 |
| ② | `VerifyResult` (`dogfood.py:328`) | `passed / commands_run / failures` | criteria 필드 없음 — 검증이 criteria와 무관 |
| ③ | `board_is_complete` (`project_task_board.py:738`, `:744 return bool(total) and total == completed`) | task 카운트만 | acceptance(`:973`)는 프롬프트 텍스트로만 노출, 완료 게이트 아님 |
| ④ | `_run_review_phase` (`dogfood.py:1837`, `:1845 passed = verify_result.get("passed", True)`) | `verify.passed`만 본다 | criteria 충족 검사 0. finalize commit은 `AF_SKIP_REVIEW_GATE=1`(`:1052`)로 review-gate 우회 |

→ 완료가 "phase가 ok로 끝났는가"로 닫히고 "criteria가 evidence로 충족됐는가"로 닫히지 않는다.

### 1.4 wiki 산출물은 Tier2 — observe-first 근거 정정

`classify_with_content('scripts/codebase_symbols.py')=2` (grep 확정). 즉 wiki 산출물은 post-implement Tier3 floor에 **안 걸린다**. 반면 `core/dogfood.py`는 content=3(self-mod risky core).

→ **observe-first의 근거는 "wiki run 보호"가 아니라 "floor trip-rate 캘리브레이션"**. enforce를 바로 켜면 정당한 run을 false-trip시킬지 미관측. 관측 후 승격.

---

## §2 blast radius (grep 확정 — 재논쟁 금지)

- **`classify()` production 호출처 = `dogfood.py:1785` 단 1곳.** `project_pipeline.py:12`는 STAGE 상수만 import, `classify()` 미호출.
  → **Phase 1 blast radius = dogfood DEVELOP(=self-run) 한정.** full 머신(ProjectPipeline / Lilith / board)은 무변.
- `right_sized_router._validate_raw`·`_apply_safety_floors`·`is_light()`는 단위 테스트 외 호출처 없음 → 내부 리팩토링 안전.

---

## §3 4-Phase 계획 (수렴, 순서 확정)

| Phase | 내용 | 본 PR | 게이트 |
|-------|------|-------|--------|
| **1** | router decoupling — 빈-scope → uncertainty LLM path | ✅ 구현 | — |
| **2** | post-implement Tier3 floor (observe-first) | ✅ 구현 | Phase 1과 **묶여야** 함(1만=unsafe, 2만=UX 안 열림) |
| **3** | completion contract — 단절 4곳 연결 | ❌ 보류 | 게이트 뒤 (대형 내부 리팩토링) |
| **4** | iterative light | ❌ 보류 | 게이트 뒤 (끌어내는 task 0) |

게이트 = **자연어 wiki throw 실측** → complete인데 불완전 산출물이면 Phase 3 spice, 아니면 3/4 보류.

---

## §4 불변식 (설계문서에 동결 — 구현이 위반하면 BLOCK)

### INV-1 — scope 있는 routing 무변
scope가 비어있지 않으면 `classify()` 동작은 **현행과 완전 동일**. 신규 경로는 `scope=[]` 한 갈래만 분기한다.

### INV-2 — 보수적 fallback 유지
빈-scope LLM path에서 **LLM 실패 / 무효 응답 / low-confidence** → 기존 `_fallback_decision`(full + worktree). 빈-scope가 light 자격을 얻는 건 *명시적으로 높은 임계 통과* 시에만.

### INV-3 — 빈-scope light는 uncertainty marker를 단다
빈-scope에서 나온 light 결정은 route metadata에 **uncertainty marker**(Final 상수 키)를 남긴다. 다운스트림(dispatch guard, Phase 2 floor, 향후 Phase 3 gate)이 "이 light는 scope 미확정 추론 결과"임을 식별할 수 있어야 한다.

### INV-4 (δA) — observe-first에 명시 승격 기준 필수
observe-first는 **승격 기준 없이는 영구 dead-safety**가 된다. 승격 기준을 코드/문서에 박는다:
> `AF_SELF_RUN` dogfood K회 관측 + 정당 run false-trip 0건 → **self-run 한정** enforce flip.

본 PR은 **observe 모드만** 구현하며 enforce flip은 K회 관측 데이터 확보 후 별도 PR(승격 기준 §6.3).

### INV-5 (δB) — 빈-scope light ↔ non-auto_policy 결합
observe 윈도우 동안 빈-scope light는 `merge ∈ {never, manual}` 일 때만 허용한다. `auto_policy`는 enforce flip 전까지 **기존 빈-scope → full** 유지.

**근거**: self-run이 Tier3 self-수정을 무검열 auto-merge할 위험. 현재 light 경로의 검증 사슬이:
- `_run_review_phase`(`:1845`) = `verify.passed`만 (코드리뷰 0건)
- finalize(`:1052`) = `AF_SKIP_REVIEW_GATE=1` (review-gate 우회)

→ auto_policy + 빈-scope light + Tier3 self-mod 조합은 source 오염 통로. enforce(Phase 2 floor가 review 강제) 전까지 auto_policy 빈-scope는 full로 묶는다.

### INV-6 — 하드코딩 / abspath 금지 (test_coding_conventions.py 강제)
| 항목 | 수단 |
|------|------|
| 빈-scope 임계 | named 상수 `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD: float`, 강제는 `is_light()` 단일 SSOT (외부리뷰 #5) |
| uncertainty marker | `Final` 상수 키 |
| observe/enforce 모드 | `MergePolicy` 필드 + `__post_init__` 검증 (`allow_partial_impl` 선례) — CLI → policy → runner 스레딩 |
| self-run 신호 | `AF_SELF_RUN` env (`dogfood.py:1641` 기존) |
| Tier3 판정 | 기존 `classify_with_content` (`right_sized_router.py:184`) |
| 경로 | `state._cwd()` / `state.worktree_workspace` 만 (abspath 리터럴 금지) |

---

## §5 Phase 1 설계 (router decoupling)

### 5.1 right_sized_router.py 변경

**신규 상수** (`:35` 인근):
```python
_LIGHT_CONFIDENCE_THRESHOLD: float = 0.7            # 기존 (scope 있음)
_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD: float = 0.85  # 신규 — scope 미확정 전용, 상향
```
근거: scope 없는 추론은 더 불확실 → light 자격 임계를 일반(0.7)보다 높인다.

**임계 강제 위치 = `is_light()` 단일 SSOT** (외부리뷰 #5): 0.85 게이트를 `_classify_empty_scope`의
제어흐름에 묻으면 "empty-scope light 자격"이 *생성 함수*와 *판정 메서드* 두 곳에 분산된다.
대신 `is_light()`가 marker를 보고 임계를 선택하게 해 자격 판정을 한 곳에 모은다:
```python
def is_light(self) -> bool:
    threshold = (
        _EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD          # marker 있으면 0.85
        if ROUTE_MARKER_SCOPE_UNCERTAIN in self.markers
        else _LIGHT_CONFIDENCE_THRESHOLD                 # 없으면 기존 0.7 (INV-1: scope 경로 무변)
    )
    return (
        self.source == "llm"
        and self.confidence >= threshold
        and set(self.required_stages) <= LIGHT_STAGES
    )
```
이로써 `required_stages=[plan,implement,test], confidence=0.75 + marker` 같은 결정이 기존 0.7
게이트를 통과하는 누수를 차단한다 (marker 있으면 0.85 강제). marker 없는 결정은 0.7 그대로 →
scope 경로 완전 무변 (INV-1). markers 미선언 시 기본 `[]`라 기존 RouteDecision 생성 경로도 무변.

**uncertainty marker** (Final 상수):
```python
from typing import Final
ROUTE_MARKER_SCOPE_UNCERTAIN: Final[str] = "scope_uncertain"
```
**결정: `RouteDecision`에 `markers` 신규 필드 추가** (의미 분리 — `floors_applied`는 안전 floor 전용). 현행 `RouteDecision`(`right_sized_router.py:42-50`)은 `markers` 미선언이므로 다음 **두 곳을 반드시** 함께 수정한다 (cross-review #1):
```python
@dataclass
class RouteDecision:
    ...
    floors_applied: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)   # 신규
    source: str = "llm"

    def to_dict(self) -> dict[str, Any]:
        return {
            ...,
            "floors_applied": list(self.floors_applied),
            "markers": list(self.markers),              # 신규 — 누락 시 _record_route_decision audit 깨짐
            "source": self.source,
        }
```
`to_dict()` 미갱신 시 `_record_route_decision(state, route)`가 marker를 직렬화하지 못해 런타임 속성(`route.markers`)과 저장 state가 불일치한다.

**`classify()` 빈-scope 분기 교체** (`:267-269`):
```python
files: list[str] = list(changed_files or [])
if not files:
    return _classify_empty_scope(task, workspace)   # 신규 — early fallback 대체
# ... 이하 scope 있는 기존 경로 무변 (INV-1)
```

**신규 `_classify_empty_scope(task, workspace) -> RouteDecision`**:
```python
def _classify_empty_scope(task: str, workspace: str) -> RouteDecision:
    """scope 미확정 task를 LLM으로 분류. 보수적 — 높은 임계 + marker.

    INV-2: LLM 실패/무효/low-conf → full fallback.
    INV-3: light 결정에 ROUTE_MARKER_SCOPE_UNCERTAIN 부착.

    [안전성 — cross-review #2] 빈-scope는 changed_files=[]이므로 _apply_safety_floors
    의 Floor 1(self-mod)·Floor 2(blast_radius Tier3)가 둘 다 'changed_files 있을 때만'
    가드(:200, :206)라 자연 생략된다. 이 생략의 안전성은 *floor가 대신 막는 게 아니라*
    dispatch의 INV-5(δB)에 의존한다: 빈-scope light는 merge∈{never,manual}일 때만 통과
    (_light_allowed). 따라서 산출물이 사후에 Tier3 파일을 건드려도 auto_policy 무검열
    auto-merge로 새지 않는다. enforce flip(Phase 2) 전까지 이 결합이 유일 방어선.
    """
    prompt = _build_empty_scope_prompt(task)   # scope 섹션 "(미확정)" 명시
    try:
        raw = _get_router_llm().generate_json(prompt)
    except Exception as exc:
        return _fallback_decision(f"empty-scope LLM error: {exc}")

    decision = _validate_raw(raw)
    if decision is None:
        return _fallback_decision(f"empty-scope invalid LLM response: {raw!r}")

    # marker만 부착하고 반환. light 자격(0.85 + light-stages)은 is_light()가 marker를
    # 보고 단일 판정(외부리뷰 #5). conf 낮은 결정도 marker 단 채 그대로 반환되며
    # dispatch의 is_light()=False → _run_develop_full로 낙하한다. _run_develop_full은
    # route.isolation을 읽지 않고 항상 worktree_workspace에서 돌므로(dogfood는 ISOLATE
    # phase가 worktree 격리 보장) low-conf empty-scope가 full로 가도 격리는 안전.
    # audit 이점: _fallback_decision으로 덮어쓰지 않아 "LLM이 실제 무엇을 판단했는지"
    # (conf/stages/reason)가 state.route_decision에 보존된다.
    decision.markers = [ROUTE_MARKER_SCOPE_UNCERTAIN]
    return decision
```
※ 빈-scope는 `changed_files=[]`라 `_apply_safety_floors`의 Floor 1·2(둘 다 `changed_files
있을 때만` 가드)가 자연 생략된다. 이 생략의 안전성은 floor가 아니라 INV-5(δB)에 의존 — §5.1
docstring 및 INV-5 참조.

**`is_light()` 영향**: 기존 `is_light()`는 `confidence >= _LIGHT_CONFIDENCE_THRESHOLD`(0.7)를 본다. 빈-scope light 결정은 conf≥0.85이므로 0.7 게이트도 자동 통과 → `is_light()` 로직 변경 불필요. **단** `_classify_empty_scope`가 이미 light 자격을 확정했으므로 dispatch는 `is_light()` 재확인으로 일관 유지.

### 5.2 dogfood.py dispatch guard 변경 (`:1788`)

빈-scope light를 통과시키되 INV-5(δB)로 auto_policy를 막는다:
```python
route = classify(state.task, state._cwd(), changed_files=scope)
_record_route_decision(state, route)

if route.is_light() and _light_allowed(route, scope, state):
    return _run_develop_light(state)
return _run_develop_full(state, pipeline)
```

**신규 `_light_allowed(route, scope, state) -> bool`**:
```python
def _light_allowed(route, scope, state) -> bool:
    """scope 있는 light는 무조건 허용(INV-1).
    빈-scope light는 marker 보유 + non-auto_policy merge 일 때만(INV-5/δB)."""
    if scope:
        return True
    from core.right_sized_router import ROUTE_MARKER_SCOPE_UNCERTAIN
    if ROUTE_MARKER_SCOPE_UNCERTAIN not in (route.markers or []):
        return False
    return state.merge_mode in ("never", "manual")
```
→ scope 있는 경로는 `and scope`를 떼어내도 동작 동일(INV-1 보존). 빈-scope만 marker+merge_mode 조건.

### 5.3 계약 테스트 갱신 (R-FB-NOSCOPE 재작성)

`tests/test_right_sized_router.py:182-195` `test_r_fb_noscope`는 "scope=[] → fallback, LLM not called"를 **계약화**하고 있다. Phase 1이 이 계약을 의도 변경하므로 재작성한다:

| 신규 테스트 | 계약 |
|------------|------|
| `test_empty_scope_calls_llm` | scope=[] → LLM **호출됨** (stub 호출 카운트 ≥1) |
| `test_empty_scope_low_conf_full` | conf < 0.85 → fallback(full) |
| `test_empty_scope_high_conf_light` | conf ≥ 0.85 + light stages → light 가능 + `ROUTE_MARKER_SCOPE_UNCERTAIN` 잔류 |
| `test_empty_scope_llm_error_full` | LLM 예외 → fallback |
| `test_empty_scope_invalid_full` | bad schema → fallback |
| `test_empty_scope_non_light_stages_full` | conf 높아도 design/review 포함 → fallback |
| `test_marker_serialized_in_to_dict` | marker 부착 결정 → `to_dict()["markers"]`에 `scope_uncertain` 포함 (cross-review #1 회귀 봉인) |

dogfood dispatch 계약(`tests/test_dogfood*.py`):
| 신규 테스트 | 계약 |
|------------|------|
| `test_empty_scope_light_auto_policy_blocked` | 빈-scope light + `merge_mode=auto_policy` → full (INV-5) |
| `test_empty_scope_light_never_allowed` | 빈-scope light + `merge_mode=never` → light |
| `test_scope_present_light_unchanged` | scope 있는 light는 merge_mode 무관 light (INV-1) |

---

## §6 Phase 2 설계 (post-implement Tier3 floor, observe-first)

### 6.1 위치
`_run_develop_light()`(`dogfood.py:1739`) 종료 직후, `actual_changed` 기준으로 산출물의 max blast tier를 측정한다. (사전 scope tier가 아니라 **실제 변경 파일** tier — 산출물이 예상과 다를 수 있음.)

### 6.2 observe 모드 (본 PR)

**API 정정 (cross-review #3)**: `_emit_phase_trace`는 실재하지 않는다. 실제 기록 헬퍼는
`_append_phase_trace(state, phase, input_data, output_data, started_at, *, fallback_used,
llm_called, exception_type, blocked_reason)`(`dogfood.py:2182`)이며 **고정 record 구조**라
자유형 dict("event"/"mode"/"changed_tier3")를 직접 받지 못한다(record는 phase/input_keys/
output_keys/critical_counts/... 만 기록 → 어느 파일이 Tier3였는지 캘리브레이션 데이터 유실).

→ **결정: observe 관측은 DEVELOP result dict의 신규 키로 기록**한다. `_run_develop_light`이
반환하는 result는 `_run_develop_phase` → VERIFY context로 흐르고 `_append_phase_trace`의
`output_data`로 들어가 `output_keys`에 자동 포착된다. 상세 파일 목록은 result dict 본문에 보존:

```python
# _run_develop_light 말미, changed 확정 후 (_normalize_develop_result 호출 전)
from scripts.blast_radius import classify_with_content
worktree = state.worktree_workspace or state.source_workspace   # INV-6: 리터럴 금지
from_uncertain = ROUTE_MARKER_SCOPE_UNCERTAIN in (state.route_decision.get("markers") or [])
if not changed:
    # 관측 불능 (외부리뷰 #2): impl.actual_changed=[] + _changed_files_fallback(:1764-1767)도
    # 빈 경우 — git diff/status 실패 또는 no-op 구현. Tier 판정 근거 없음 → observe는
    # "no_changes"로 기록(트립률 분모 정확화). no-op이 complete되는 더 큰 문제는 Phase 3 영역.
    base["tier3_floor"] = {"mode": policy.tier3_floor_mode, "observability": "no_changes",
                           "from_uncertain_scope": from_uncertain}
else:
    tier3_changed = [f for f in changed if classify_with_content(f, worktree) >= 3]
    if tier3_changed:
        # observe: complete 기존대로 — block/review 강제 안 함 (트립률 캘리브레이션만)
        base["tier3_floor"] = {"mode": policy.tier3_floor_mode, "observability": "observed",
                               "changed_tier3": tier3_changed, "from_uncertain_scope": from_uncertain}
```
observe 모드는 **complete 흐름 무변**. result.tier3_floor가 phase_trace에 흘러 trip-rate를
사후 측정 가능하게 한다 (`no_changes` ≠ `observed`+tier3 없음 ≠ `observed`+tier3 있음 3분류).
(enforce 모드 §6.3은 이 키를 읽어 review 강제 — `no_changes`는 enforce에서도 block 대상 아님:
변경이 없으면 위험도 없으므로. 단 empty-scope light + no_changes는 "산출물 0 complete" 신호이므로
Phase 3 게이트 진입 시 우선 점검 대상으로 phase_trace에 남긴다.)

### 6.3 enforce 모드 (본 PR 미구현 — 승격 기준 충족 후)
`MergePolicy.tier3_floor_mode: str = "observe"` (`{"observe","enforce"}` `__post_init__` 검증). enforce 시:
- Tier3 변경 감지 → review_depth 강제 상향 또는 BLOCK (`_run_review_phase`가 verify.passed만 보는 단절 ④를 보완).
- **승격 조건 (INV-4/δA)**: `AF_SELF_RUN` dogfood run K회(예: K=5) 관측 + 정당 run false-trip 0건 → self-run 한정 `tier3_floor_mode="enforce"` 기본값 flip. K·flip은 관측 데이터 기반 별도 PR.

### 6.4 MergePolicy 필드 추가

**소유권 근거 (외부리뷰 #1)**: 이름은 "Merge"지만 `MergePolicy`(`dogfood.py:282`)는 이미 merge
이전 lifecycle 전 단계 정책을 소유한다 — `require_verify_pass`(VERIFY), `require_review_pass`
(REVIEW), `require_plan_triad_pass`(PLAN), `allow_partial_impl`(IMPLEMENT→VERIFY 진행 허용),
`cleanup_worktree_on_block`(BLOCK 처리). 즉 **실질적으로 dogfood lifecycle policy SSOT**다.
`tier3_floor_mode`(DEVELOP 직후 관측 정책) 추가는 이 선례에 정합한다. 별도 `DevelopSafetyPolicy`
신설은 정책 객체 2개를 lifecycle 전체에 스레딩하는 비용만 늘리는 과설계(Simplicity First)라 기각.
단 차후 lifecycle 정책이 더 늘면 `MergePolicy` → `DogfoodLifecyclePolicy` 개명을 검토 (본 PR 범위 외).

```python
# dogfood.py MergePolicy (allow_partial_impl 선례)
tier3_floor_mode: str = "observe"   # {"observe","enforce"}

def __post_init__(self):
    ...  # 기존
    if self.tier3_floor_mode not in ("observe", "enforce"):
        raise ValueError(f"invalid tier3_floor_mode: {self.tier3_floor_mode!r}")
```
CLI → MergePolicy → runner 스레딩(`allow_partial_impl` 경로 재사용). 본 PR은 기본값 `observe`만 production 도달.

**policy 접근 경로 (§6.2 record가 `policy.tier3_floor_mode`를 읽음)**: `_run_develop_light`은 현재 `policy` 인자를 받지 않는다(`:1739`). observe record의 `mode` 값을 하드코딩("observe" 리터럴, INV-6 위반)하지 않으려면 SSOT인 MergePolicy 필드를 읽어야 한다. → `_run_develop_phase`가 `build_merge_policy(state, state.merge_mode)`로 policy를 만들어 `_run_develop_light(state, policy)`로 전달(시그니처 1개 추가). full 경로(`_run_develop_full`)는 tier3_floor 관측 대상 아님(ProjectPipeline이 자체 review 보유)이므로 policy 인자 불필요.

### 6.5 Phase 2 테스트
| 테스트 | 계약 |
|--------|------|
| `test_tier3_floor_observe_emits_warning` | Tier3 산출물 → `tier3_floor.observability=="observed"` + `changed_tier3` 채움, phase=complete 유지 |
| `test_tier2_floor_no_warning` | Tier2 산출물(wiki) → `observed` + tier3 없음 (1.4 정정 반영) |
| `test_actual_changed_empty_records_no_changes` | `actual_changed=[]` + fallback도 `[]` → `tier3_floor.observability=="no_changes"` (외부리뷰 #2) |
| `test_tier3_floor_mode_validation` | `tier3_floor_mode="bogus"` → ValueError |
| `test_observe_does_not_block` | observe 모드는 BLOCK 안 함 (no_changes·observed 공통) |

---

## §7 Phase 3/4 — 보류 (게이트 뒤, 본 PR 미구현)

### Phase 3 (completion contract) — 왜 게이트 뒤인가
단절 4곳을 criteria↔evidence↔all-pass gate로 연결하는 건 단순 배선이 아니다:
- ledger 4개(evolution / ise_strategy / lineage / run) + board + verify + review + approval 화해 = **대형 내부 리팩토링** (메타-재귀 1순위 위험).
- **진짜 병목은 criteria 부재가 아니라 criteria SOURCE 품질**: non-interactive greenfield는 1줄 task에서 LLM이 success_criteria 자동생성 → garbage-in이면 gate도 garbage.
- 하위호환 기본값(criteria 없으면 legacy 완료 판정) 없으면 기존 run 전부 회귀.

→ 자연어 wiki throw 실측에서 "complete인데 산출물 불완전"이 **실제로 관측될 때만** spice. 추측성 구현 금지.

### Phase 4 (iterative light) — 왜 게이트 뒤인가
끌어내는 task가 0이다. wiki는 one-shot light가 COMPLETE 실증(run `1780813496`). 메모리 `project_af_codebase_wiki_direction`의 "(iii)는 task가 끌어낼 때만" 원칙. 지금 짓는 건 추측성 인프라.

---

## §8 키워드 분류기 금지 (사용자·Claude 합의)

scope=[] 처리를 "키워드 매칭"으로 풀지 않는다:
- `express_router.py` route_task() 死코드 전례 (런타임 호출 0).
- "인증 시스템 만들어줘"는 위험 키워드 없이 복잡 / "디렉터리 문서화"는 wiki 키워드 없이 deterministic → 양방향 샘.

**정답 = LLM stage 판단 + confidence + 결정적 floor.** Phase 1의 `_classify_empty_scope`가 정확히 이 형태.

---

## §9 구현 순서 (Sonnet, test-first — 재설계 금지)

1. **RED**: §5.3 + §6.5 테스트 전부 작성 → 실패 확인.
2. `right_sized_router.py`: `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` + `ROUTE_MARKER_SCOPE_UNCERTAIN`(Final) + `RouteDecision.markers` 필드 **+ `to_dict()`에 `"markers"` 추가**(cross-review #1) **+ `is_light()` marker-aware threshold**(외부리뷰 #5 — 0.85 게이트 SSOT) + `_classify_empty_scope`(marker만 부착, docstring에 INV-5 의존 명시 #2) + `_build_empty_scope_prompt` + `classify` 빈-scope 분기 교체.
3. `dogfood.py`: `_light_allowed` + dispatch guard 교체(`:1788`) + `MergePolicy.tier3_floor_mode` + `__post_init__` 검증 + `_run_develop_light` 시그니처에 `policy` 추가 + observe tier3_floor 관측(result dict 키, **`_append_phase_trace` 사용 — `_emit_phase_trace` 아님**, #3) + `_run_develop_phase`가 policy 생성·전달.
4. **GREEN**: 테스트 통과.
5. `test_coding_conventions.py` 통과 확인 (INV-6: 매직 넘버/abspath 0).
6. 3-Tier: af-critic → af-cross-review → af-test-runner.
7. Blueprint §3(right_sized_router, dogfood) + §12 이력 동기화 (같은 커밋).

---

## §10 게이트 (구현 후 멈춤·재평가)

자연어 wiki throw 실측(`"<디렉터리> 문서화해줘"` 형태, scope=[] 유발):
- **complete + 산출물 완전** → Phase 3/4 보류 확정. 입구 결함 해소로 종료.
- **complete + 산출물 불완전** → Phase 3(completion contract) spice 재진입.
- **여전히 full로 빠짐** → Phase 1 분기 재진단 (marker/dispatch guard grep).

🚦 이 게이트 통과 전 Phase 3/4 착수 금지.
