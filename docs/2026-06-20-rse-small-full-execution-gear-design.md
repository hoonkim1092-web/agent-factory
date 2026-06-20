# RSE "작은 full" 중간 실행 기어 신설 설계

- 날짜: 2026-06-20
- 작성: Opus 4.8 (설계), 구현=Sonnet
- 상태: **SUPERSEDED / 폐기** (2026-06-20) — 미구현. **R2 af-cross-review가 핵심 전제 붕괴 발견** + **B안 채택으로 흡수**.
  - **폐기 사유**: R2에서 `project_pipeline`이 design·plan 단계를 `_stage_enabled`로 게이팅하지 않음(`grep design project_pipeline.py`=0건, research·review/cross만 게이팅:749/:1142)이 드러남 → small-full의 "research·design·plan 생략" 전제 중 **design·plan 스킵이 무효**(small-full ≡ full−research). gear의 유일한 실효 가치 = 우선순위5(`plan()`) 분해 축소 입력뿐인데, 우선순위5는 이미 `project_brief["route"]["required_stages"]`를 받아 **gear 없이 직접 규모 판단 가능**(YAGNI, 소비자 1개). → 라우터 무변경하고 우선순위5에 흡수(B안).
  - **보존 가치**: R1/R2 finding 기록(F1 review-less 가드, F2 design 복원 no-op)·stage-gating 실태 진단·gear 계약 탐색은 향후 **두 번째 규모 소비자**(예산·모델라우팅·머지정책) 생겨 gear를 라우터로 승격할 때 재활용. 그 전까지 미구현.
- 부모 설계: `docs/2026-06-20-dogfood-false-success-spin-fix-design.md` §6.1 (우선순위 3 진입점)
- 형제 설계: 우선순위 5 (`bootstrap_roles.plan()` 규모 조건부화) — **본 문서는 그 파일을 설계·인용하지 않는다.** §3에서 인터페이스 요구만 명시.
- 변경 이력: **R1 (2026-06-20) af-cross-review BLOCK 흡수** — F1(High, `is_small_full()` review-less 집합 허용 → INV-G5 위반)에 외부리뷰 실재 가드 추가(§2.2), F2(Medium, auto에서 design 미복원 → INV-G6 허상)에 `_restore_design_for_full` 신설(§4.1). baseline 인용 17건 stale 0 확인.

---

## 0. 범위 선언 (무엇을 고치고 무엇을 미루나)

부모 진단의 Bug 4(과분해):

```
full이 규모 무관 단일기어(_FULL_STAGES 고정, right_sized_router.py:104)
   ↓
중간 크기 변경(예: 1~2개 기존 모듈의 contract 변경)도 7단계 full로 처리
   ↓
research+design까지 강제 → 과한 분해·낭비 사이클 (부모 §6.1 "비싼 게이트가 싼 걸 가린다"의 반대)
```

**이 설계가 고치는 것 (라우팅 기어 3분):**
- **G1** — `right_sized_router.py`: light↔full 이분법을 **light / small-full / full 3분**으로 확장. small-full = build→test→review→cross_review (research·design·plan 생략).
- **G2** — `RouteDecision`에 **`gear` named 계약 필드** 신설 + `is_small_full()` 자격 판정. 형제 설계가 소비할 SSOT.
- **G3** — Floor2(Tier3 강제)를 **gear 인식형으로 조건부화**: Tier3여도 small-full 자격이면 design을 강제하지 않고 review+cross_review만 강제(부모 §6.2 `merge_mode∈{never,manual}` 제약 준수).
- **G4** — `dogfood.py:1876` 분기를 **3-way**로: light / small-full(신규) / full.

**이 설계가 미루는 것 (본 문서 밖):**
- 형제 우선순위 5 (`bootstrap_roles.plan()` 프롬프트 규모 조건부화) — gear를 **소비**. 본 문서는 gear **생산·전파**만 책임지고, §3에서 소비 인터페이스 계약만 명시.
- 부모 S1~S3 (가짜성공/spin correctness) — 이미 부모 문서가 닫음. 본 문서와 disjoint.
- small-full 내부의 "스코프 재리뷰(2회차 diff만)"·"하드 루프 캡" 실행흐름 (부모 §6.1 원칙 ②③) — 단계 집합이 아니라 **단계 내부 루프 정책**이라 dynamic_orchestrator/review_runner 층. 본 슬라이스는 **단계 집합 3분**만. (분리 근거: §5)

**무죄 확정 (red herring):** light 경로(`is_light()`, `LIGHT_STAGES`)는 본 설계에서 **완전 무변** — small-full은 light보다 무겁고 full보다 가벼운 신규 중간 기어로, light 판정 로직에 손대지 않는다(INV-G0).

---

## 1. Baseline (실제 코드, 2026-06-20 라인 재검증 완료)

### 1.1 right_sized_router.py — 2단계 기어의 현 구조

`core/right_sized_router.py:33`:
```python
LIGHT_STAGES: frozenset[str] = frozenset({STAGE_PLAN, STAGE_IMPLEMENT, STAGE_TEST})
```

`right_sized_router.py:28-31` (STAGE_VOCAB, 7단계 SSOT):
```python
STAGE_VOCAB: tuple[str, ...] = (
    STAGE_RESEARCH, STAGE_DESIGN, STAGE_PLAN, STAGE_IMPLEMENT,
    STAGE_TEST, STAGE_REVIEW, STAGE_CROSS_REVIEW,
)
```

`right_sized_router.py:44-53` (RouteDecision 필드):
```python
@dataclass
class RouteDecision:
    isolation: str
    required_stages: list[str]
    review_depth: str           # "none" | "standard" | "deep"
    confidence: float
    reason: str
    floors_applied: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)
    source: str = "llm"         # "llm" | "fallback"
```

`right_sized_router.py:55-70` (`is_light()` — light 자격 단일 판정):
```python
    def is_light(self) -> bool:
        threshold = (
            _EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD
            if ROUTE_MARKER_SCOPE_UNCERTAIN in self.markers
            else _LIGHT_CONFIDENCE_THRESHOLD
        )
        return (
            self.source == "llm"
            and self.confidence >= threshold
            and set(self.required_stages) <= LIGHT_STAGES
        )
```

`right_sized_router.py:72-82` (`to_dict()` — state·pipeline 전파용 직렬화. **gear는 여기에 실려야 dogfood→pipeline까지 도달**):
```python
    def to_dict(self) -> dict[str, Any]:
        return {
            "isolation": self.isolation,
            "required_stages": list(self.required_stages),
            "review_depth": self.review_depth,
            "confidence": self.confidence,
            "reason": self.reason,
            "floors_applied": list(self.floors_applied),
            "markers": list(self.markers),
            "source": self.source,
        }
```

`right_sized_router.py:104` (full 단일기어 — 규모 무관 7단계 고정):
```python
_FULL_STAGES: list[str] = list(STAGE_VOCAB)
```

`right_sized_router.py:106-115` (`_fallback_decision` — 보수적 full):
```python
def _fallback_decision(reason: str) -> RouteDecision:
    return RouteDecision(
        isolation="worktree",
        required_stages=list(_FULL_STAGES),
        review_depth="deep",
        confidence=0.0,
        reason=reason,
        floors_applied=[],
        source="fallback",
    )
```

`right_sized_router.py:205-227` (`_apply_safety_floors` — Floor1 self-mod, **Floor2 Tier3 강제**):
```python
def _apply_safety_floors(decision, workspace, changed_files):
    applied: list[str] = []
    # Floor 1: self-mod → isolation 최소 worktree
    if _is_self_modification(workspace, changed_files):
        if _isolation_rank(decision.isolation) < _isolation_rank("worktree"):
            decision.isolation = "worktree"
            applied.append("self_mod_isolation>=worktree")
    # Floor 2: blast_radius Tier3 → design+review+cross_review 강제
    if changed_files and _max_tier(changed_files, workspace) >= 3:
        forced = (STAGE_DESIGN, STAGE_REVIEW, STAGE_CROSS_REVIEW)
        added = [s for s in forced if s not in decision.required_stages]
        if added:
            decision.required_stages = _stage_ordered_union(decision.required_stages, forced)
            applied.append("blast_radius_tier3:" + ",".join(added))
    decision.floors_applied = applied
    return decision
```

`right_sized_router.py:327-365` (`classify` 공개 API): 빈 scope → `_classify_empty_scope`(:341), else `_build_prompt`+LLM+`_validate_raw`(:360)+`_apply_safety_floors`(:364).

### 1.2 dogfood.py — production caller (2-way 분기)

`core/dogfood.py:1861-1878` (`_run_develop_phase` — 라우팅 진입점):
```python
def _run_develop_phase(state, pipeline):
    if pipeline is None:
        raise ValueError("project_pipeline is required for DEVELOP phase")
    from core.right_sized_router import classify
    scope = _intended_scope(state.task)
    route = classify(state.task, state._cwd(), changed_files=scope)
    _record_route_decision(state, route)              # :1873
    policy = build_merge_policy(state, state.merge_mode)  # :1875
    if route.is_light() and _light_allowed(route, scope, state):  # :1876
        return _run_develop_light(state, policy)      # :1877
    return _run_develop_full(state, pipeline)         # :1878
```

`dogfood.py:1745-1747` (`_record_route_decision` — `route.to_dict()`를 state에 기록. gear가 to_dict에 실리면 자동 보존):
```python
def _record_route_decision(state, route):
    state.route_decision = route.to_dict()
```

`dogfood.py:1766-1775` (`_run_develop_full` — pipeline.prepare에 `route=state.route_decision` 전달 → pipeline이 `required_stages`/gear 소비):
```python
def _run_develop_full(state, pipeline):
    worktree = state.worktree_workspace or state.source_workspace
    with _develop_isolation_env(worktree):
        prepared = pipeline.prepare(
            task_input=state.task,
            workspace=worktree,
            runtime_workspace=state.runtime_workspace,
            route=state.route_decision or None,   # :1774 — gear 전파 경로
        )
        ...
```

`dogfood.py:317,330` (`MergePolicy.tier3_floor_mode` — "observe"|"enforce", Floor2 무게와 연동), `dogfood.py:1175` (`build_merge_policy`).

**핵심 사실 (배포 동등성 경로):** gear는 `RouteDecision.to_dict()` → `state.route_decision`(`:1747`) → `pipeline.prepare(route=...)`(`:1774`) → `project_pipeline._stage_enabled`/플래너로 **이미 존재하는 dict 통로**를 그대로 탄다. 신규 전파 채널 불필요 — `gear` 키 하나만 그 dict에 얹으면 픽스처-only 없이 production까지 도달.

---

## 2. G1+G2 — 기어 3분 + named 계약 (right_sized_router.py)

### 2.1 설계 판단 (해석 분기 명시 — CLAUDE.md 원칙 1)

**핵심 질문 1·2 답: small-full의 단계 집합과 판별 기준.**

부모 §6.1 합의 실행흐름 `build(구현+테스트) → [존재가드] → test → fix → (초록일 때만) review → cross_review` 를 단계 어휘로 사상하면:

| gear | 단계 집합 | 생략 단계 | 의미 |
|------|----------|----------|------|
| **light** | plan, implement, test | research·design·review·cross_review | leaf 함수 추가 (무변) |
| **small-full** (신규) | implement, test, review, cross_review | **research·design·plan** | 기존 모듈 contract 변경 — 설계 불필요하나 외부리뷰 필요 |
| **full** | research, design, plan, implement, test, review, cross_review | 없음 | 신규 시스템·다파일·고불확실 |

> small-full이 **design을 빼는** 근거: 부모 §6.1 4원칙의 핵심은 "test 초록 전엔 cross_review 안 돈다"이지 "design을 항상 한다"가 아니다. 중간 크기 = 기존 인터페이스 위에서의 국소 변경 → up-front design 산출물의 ROI가 낮다(과분해의 정확한 발원지). 단 **review+cross_review는 유지** — Tier3 contract 변경은 외부 검증 가치가 높다.
> small-full이 **plan을 빼는** 근거: build(implement+test)가 plan 없이도 닫히는 규모가 small-full의 정의. plan은 다단계 분해 도구이고, 형제 설계(우선순위 5)가 "규모를 알면 분해를 줄인다"를 plan() 프롬프트 층에서 별도로 다룬다. **단계로서의 plan 생략 ≠ 형제의 plan() 프롬프트 조건부화** — 두 레버는 독립이며 §3에서 합류 계약을 명시.

**판별 기준 (질문 2):** 단일 신호 — **LLM이 명시적으로 산출한 `required_stages` 집합**. 별도 tier 임계나 confidence 분기를 새로 만들지 않는다(과설계 회피). gear는 `required_stages`에서 **파생**된다:

- `set(required_stages) ⊆ LIGHT_STAGES` → light (기존 `is_light()` 그대로)
- `set(required_stages) ⊆ SMALL_FULL_STAGES` AND ⊄ LIGHT_STAGES → small-full
- 그 외 (research 또는 design 포함) → full

> 근거: 라우터 LLM은 이미 `required_stages`를 산출한다(프롬프트 :306-312). gear는 그 출력의 **결정적 분류**일 뿐 — 새 LLM 신호·새 임계 도입은 추측성 유연성(원칙 2 위반). blast_radius tier는 Floor2(§2.3)에서만 쓰고 gear 1차 판별엔 안 쓴다.

### 2.2 변경

**(1) 상수 신설** (`:33` LIGHT_STAGES 옆):
```python
SMALL_FULL_STAGES: frozenset[str] = frozenset(
    {STAGE_IMPLEMENT, STAGE_TEST, STAGE_REVIEW, STAGE_CROSS_REVIEW}
)
GEAR_LIGHT: Final[str] = "light"
GEAR_SMALL_FULL: Final[str] = "small_full"
GEAR_FULL: Final[str] = "full"
```

**(2) `RouteDecision`에 `gear` 필드** (`:53` source 다음, 기본값 → 하위호환):
```python
    gear: str = GEAR_FULL    # "light" | "small_full" | "full" — required_stages 파생, classify가 확정
```

**(3) `is_small_full()` 자격 판정 메서드** (`:70` is_light() 다음 — 질문 4 답):
```python
    def is_small_full(self) -> bool:
        """floor 적용 후 호출 — small-full 중간 기어 적격 여부.

        light보다 무겁고(plan-only 아님) full보다 가벼움(research·design 없음).
        is_light()와 상호배타. **review 또는 cross_review가 반드시 포함**돼야 함(INV-G5)
        — 외부리뷰 없는 {implement,test}-only 집합은 small-full이 아니라 full로 보낸다.
        """
        if self.source != "llm":
            return False
        if self.is_light():
            return False
        stages = set(self.required_stages)
        if not (stages & {STAGE_REVIEW, STAGE_CROSS_REVIEW}):
            return False   # F1 가드: 외부리뷰 미포함 → small-full 부적격(보수적 full)
        return stages <= SMALL_FULL_STAGES
```

> **F1 가드(외부리뷰 필수) — cross-review R1 BLOCK 흡수**: `set(required_stages) ⊆ SMALL_FULL_STAGES`만으로는 `{implement,test}`(review·cross_review 부재)도 통과한다 — 이 집합이 SMALL_FULL_STAGES의 부분집합이기 때문. 그런 review-less 집합이 small-full로 분류되면 `_run_develop_full` 위임 후 `_stage_enabled(review,cross_review)=False`로 **외부검증 없이 완료**돼 INV-G5를 깬다. 따라서 **review 또는 cross_review가 required_stages에 실제로 있어야** small-full 적격.
> **저신뢰 처리**: `{implement,test}` + confidence<0.7 같은 저신뢰 leaf 집합은 `is_light()=False`(임계 미달)이지만 F1 가드로 small-full도 False → **full로 폴백**(저신뢰는 보수적으로 full, 정확). `source != "llm"`은 fallback 보수(항상 full), `is_light()` 선체크는 상호배타.

**(4) gear 확정 헬퍼 + classify 말미 배선** (`_apply_safety_floors` 반환 후 — floor가 stage를 바꾸므로 gear는 floor **이후** 확정):
```python
def _derive_gear(decision: RouteDecision) -> str:
    if decision.is_light():
        return GEAR_LIGHT
    if decision.is_small_full():
        return GEAR_SMALL_FULL
    return GEAR_FULL
```
`classify()` (`:364` floor 적용 후, return 전):
```python
    decision = _apply_safety_floors(decision, workspace, files)
    decision.gear = _derive_gear(decision)   # 신규: floor 후 확정
    return decision
```
`_classify_empty_scope` 반환 직전(`:289` marker 부착 옆)과 `_fallback_decision`(:106, 명시 `gear=GEAR_FULL`)도 동일 확정. **단일 SSOT 원칙: gear는 오직 `_derive_gear`로만 설정** — 분산 대입 금지.

**(5) `to_dict()`에 gear 키** (`:81` source 다음):
```python
            "gear": self.gear,
```

### 2.3 G3 — Floor2 gear 인식형 조건부화 (질문 3 답)

**현 Floor2**(`:218-224`)는 Tier3면 `design+review+cross_review` 3개를 무조건 union → small-full 후보(implement,test,review,cross_review)도 design이 끼면서 **full로 끌어올려진다**. 이게 과분해의 floor-층 발원지.

**해석 분기 (원칙 1):**

| 안 | Floor2가 Tier3에서 강제하는 stage | 결과 |
|----|--------------------------------|------|
| A (현행) | design + review + cross_review | small-full도 full로 승격 — 과분해 지속 |
| B (채택) | **gear==small_full이고 merge∈{never,manual}이면 review + cross_review만** (design 생략), 그 외 종전대로 3개 | small-full 보존, 외부리뷰는 유지 |

**채택 B의 변경** (`:218-224` 대체):
```python
    # Floor 2: blast_radius Tier3 → 외부리뷰 강제 (gear 인식형)
    if changed_files and _max_tier(changed_files, workspace) >= 3:
        # small-full 자격(implement·test만 + 충분 confidence)이면 design 생략 가능 —
        # 단 merge_mode 억제 조건은 dogfood 층(_small_full_allowed)에서 최종 판정.
        # 라우터는 design 미강제 후보를 만들고, review+cross_review는 항상 강제.
        candidate_small = set(decision.required_stages) <= (
            SMALL_FULL_STAGES | {STAGE_PLAN}  # design·research 없으면 small 후보
        ) and not ({STAGE_DESIGN, STAGE_RESEARCH} & set(decision.required_stages))
        if candidate_small:
            forced = (STAGE_REVIEW, STAGE_CROSS_REVIEW)      # design 생략
        else:
            forced = (STAGE_DESIGN, STAGE_REVIEW, STAGE_CROSS_REVIEW)
        added = [s for s in forced if s not in decision.required_stages]
        if added:
            decision.required_stages = _stage_ordered_union(decision.required_stages, forced)
            applied.append("blast_radius_tier3:" + ",".join(added))
```

> **부모 §6.2 제약 준수:** 라우터는 design 미강제 *후보*만 만든다. "merge∈{never,manual}일 때만 억제"의 **최종 게이트는 dogfood 층 `_small_full_allowed`**(§4) — auto_policy에서는 small-full이 full로 폴백(§4.2 INV-G6). 이렇게 둘로 나누는 근거: Floor2는 workspace/changed_files만 알고 merge_mode를 모른다(시그니처에 없음). merge_mode 결합은 이미 `_light_allowed`가 하는 dogfood 층의 책임 — 동형 패턴 재사용(원칙 3).

### 2.4 효과·불변식

- **INV-G0**: light 경로 완전 무변 — `is_light()`·`LIGHT_STAGES`·임계 미변경. small-full은 light이 False일 때만 평가.
- **INV-G1**: gear는 `required_stages`의 **결정적 파생** — 같은 stage 집합은 항상 같은 gear. 새 LLM 신호·임계 없음.
- **INV-G2**: gear ∈ {light, small_full, full} 닫힘 집합. fallback·invalid → full(보수).
- **INV-G3 (상호배타)**: `is_light()`와 `is_small_full()` 동시 True 불가(전자 선체크 + 집합 disjoint).
- **INV-G4 (Floor2 보존)**: Tier3 + non-small 후보(design/research 포함)는 종전대로 design+review+cross_review 강제 — full 안전성 무손실.
- **INV-G5 (외부리뷰 불변)**: small-full **적격 자체가 review 또는 cross_review의 required_stages 실재를 요구**(F1 가드) — review-less 집합은 small-full이 아니라 full. Tier3 small-full은 Floor2가 review+cross_review를 강제해 이 조건을 자동 충족. design만 ROI 기준 생략.

### 2.5 테스트 (신규)

- LLM이 `required_stages=[implement,test,review,cross_review]`, conf=0.8 → `gear=="small_full"`, `is_small_full() True`, `is_light() False`.
- LLM이 `[plan,implement,test]` conf=0.8 → `gear=="light"`(무변), `is_small_full() False`.
- LLM이 `[research,design,...]` → `gear=="full"`.
- fallback → `gear=="full"`, `is_small_full() False`.
- **F1 가드(review-less leaf)**: LLM이 `[implement,test]`(review·cross_review 없음) conf=0.5, Tier1/2 scope(Floor2 미작동) → `is_light() False`(임계), `is_small_full() False`(외부리뷰 미포함), `gear=="full"`. ← R1 BLOCK 재현 케이스, full 폴백 검증.
- **F1 가드(저신뢰+review 有)**: LLM이 `[implement,test,review]` conf=0.6 → `is_small_full() True`(review 포함), `gear=="small_full"`. 저신뢰여도 외부리뷰 있으면 small-full 허용(small-full은 review 유지가 안전망).
- Floor2: small 후보 + Tier3 파일 → `required_stages`에 review·cross_review 추가되나 **design 미추가**, `gear` 여전히 small_full, `floors_applied`에 `blast_radius_tier3:review,cross_review`.
- Floor2: design 포함 후보 + Tier3 → design+review+cross_review 강제(종전), `gear=="full"`.
- `to_dict()` round-trip에 `gear` 키 존재.

---

## 3. 형제 공유 seam — named gear 계약 (우선순위 5 인터페이스 요구)

**본 섹션은 형제 설계(우선순위 5, `bootstrap_roles.plan()` 규모 조건부화)와의 계약 SSOT다.** 본 문서는 gear를 **생산·전파**하고, 형제는 그것을 **소비**한다. `bootstrap_roles.py`는 본 문서가 설계·인용하지 않으므로(churn 차단), 소비측 요구만 인터페이스로 명문화한다.

### 3.1 named 계약: gear 신호의 생산→전파→소비 사슬

```
[생산] right_sized_router.classify()
          → RouteDecision.gear ∈ {"light","small_full","full"}   (§2.2, _derive_gear)
          → RouteDecision.to_dict()["gear"]                       (§2.2-(5))
   ↓
[전파] dogfood._record_route_decision (:1747)
          → state.route_decision["gear"]
   ↓ (full·small-full 경로 공통)
       dogfood._run_develop_full → pipeline.prepare(route=state.route_decision) (:1774)
          → project_pipeline가 project_brief["route"]["gear"] 보존
   ↓
[소비] plan 단계 빌더(형제 영역)가 route["gear"]를 읽어 분해 강도 조절
```

### 3.2 형제 `plan()`이 소비할 인터페이스 요구 (본 문서가 보장하는 계약)

1. **계약 키**: `route` dict에 `"gear"` 키가 항상 존재한다(`to_dict`가 보장, 기본 `"full"`). 형제는 `route.get("gear", "full")`로 안전 폴백할 수 있다.
2. **값 도메인**: `"light" | "small_full" | "full"` 3값만. 형제는 이 닫힌 집합을 가정해도 된다(INV-G2).
3. **의미 계약**:
   - `gear=="small_full"` → "기존 인터페이스 위 국소 변경, up-front design 불요". 형제 `plan()`은 이 신호를 받으면 **분해 강도를 낮춰야** 한다(모듈 수 최소화, research/design 산출물 가정 금지). 이것이 Bug 4(과분해) 뿌리 해소의 형제측 레버.
   - `gear=="full"` → 종전 full 분해.
   - `gear=="light"` → plan 단계는 형제 영역에서 light 빌더가 별도 처리(본 문서 §4 light 경로 무변).
4. **레버 독립성**: 본 문서 §2의 "plan **단계** 생략(small-full required_stages에서 plan 제외)"과 형제의 "plan() **프롬프트** 조건부화"는 **직교**한다.
   - small-full은 plan 단계를 안 돌리므로(§2.1 표), small-full 경로에서는 형제 plan()이 호출되지 않을 수 있다 — 그 경우 gear 소비는 no-op(안전).
   - 그러나 **full 경로에서도** 형제는 `route["gear"]`를 받는다(gear는 small-full 전용이 아니라 항상 부착). full 안에서도 형제가 추가 규모 신호로 분해를 미세조정할 여지를 남긴다. **본 문서는 gear를 모든 경로에 부착**하여 형제가 어떤 경로에서든 읽을 수 있게 보장한다.
5. **금지**: 형제는 gear를 **생산·재계산하지 않는다** — 오직 라우터 산출 `route["gear"]`만 읽는다. 형제가 자체 규모 분류를 만들면 SSOT 위반(2-source-of-truth) → 본 계약은 라우터를 유일 생산자로 고정한다.

### 3.3 계약 검증 책임 분담

| 책임 | 본 문서(우선순위 3) | 형제(우선순위 5) |
|------|--------------------|------------------|
| `route["gear"]` 키 존재·도메인 | ✅ to_dict 테스트(§2.5) | (가정) |
| gear 값 정확성(stage→gear 파생) | ✅ §2.5 | (가정) |
| state→pipeline 전파 도달 | ✅ §6 배선 테스트 | (가정) |
| plan() 분해 강도 응답 | (계약 명시만) | ✅ 형제 테스트 |

---

## 4. G4 — dogfood 3-way 분기 (production 배선, 질문 5 답)

### 4.1 변경

**(1) `_small_full_allowed` 신설** (`_light_allowed` 옆 `:1763` 다음 — 동형 패턴, 부모 §6.2 merge 제약):
```python
def _small_full_allowed(route: Any, state: DogfoodState) -> bool:
    """small-full(design 생략, review+cross_review 유지)은 merge∈{never,manual}일 때만 허용.

    auto_policy는 내부리뷰가 유일 게이트이므로 design 생략 시 self-수정 무검열 통로 위험
    → auto에서는 full 폴백(부모 §6.2 제약). _light_allowed와 동형.
    """
    return state.merge_mode in ("never", "manual")
```

**(2) `_restore_design_for_full` 신설** (`_small_full_allowed` 옆 — F2 해소, INV-G6의 "단계의 full" 보장):
```python
def _restore_design_for_full(state: DogfoodState) -> None:
    """small-full이 merge_mode 게이트에서 불허(auto_policy)됐을 때, design을
    required_stages에 복원하고 gear를 full로 강등한다.

    Floor2(라우터)는 merge_mode를 모르므로 small 후보의 design을 미리 생략했다.
    auto에서 _run_develop_full에 진입만 해도 required_stages에 design이 없으면
    project_pipeline._stage_enabled(design)=False로 design이 그대로 스킵된다.
    여기서 명시 복원해야 "단계의 full"이 성립(부모 §6.2, INV-G6).
    """
    from core.right_sized_router import STAGE_VOCAB, STAGE_DESIGN, GEAR_FULL
    rd = state.route_decision or {}
    stages = list(rd.get("required_stages") or [])
    if STAGE_DESIGN not in stages:
        wanted = set(stages) | {STAGE_DESIGN}
        rd["required_stages"] = [s for s in STAGE_VOCAB if s in wanted]  # 순서 보존
    rd["gear"] = GEAR_FULL
    state.route_decision = rd
```

**(3) `_run_develop_phase` 3-way 분기** (`:1876-1878` 대체):
```python
    policy = build_merge_policy(state, state.merge_mode)
    if route.is_light() and _light_allowed(route, scope, state):
        return _run_develop_light(state, policy)
    if route.is_small_full():
        if _small_full_allowed(route, state):
            return _run_develop_small_full(state, pipeline)
        # auto_policy: design 생략 불허 → design 복원 후 full(부모 §6.2, INV-G6)
        _restore_design_for_full(state)
    return _run_develop_full(state, pipeline)
```

**(4) `_run_develop_small_full` 신설** — **`_run_develop_full`을 재사용**하되 단계 생략은 이미 `required_stages`가 표현하므로 본질적으로 동일 경로. 최소 변경:
```python
def _run_develop_small_full(state: DogfoodState, pipeline: Any) -> dict[str, Any]:
    """Small-full DEVELOP path: full pipeline 위임이나 route.required_stages가
    research·design·plan을 생략 → project_pipeline._stage_enabled가 자동 스킵.

    별도 빌더 불요 — _run_develop_full과 동일 prepare/execute 경로.
    gear 신호는 state.route_decision["gear"]로 이미 pipeline에 전파됨(§3.1).
    """
    return _run_develop_full(state, pipeline)
```

> **과설계 회피 (원칙 2):** small-full 전용 빌더를 새로 만들지 **않는다**. `project_pipeline._stage_enabled`(baseline `:42-51`)가 이미 `required_stages` 기준으로 research·design·plan을 자동 스킵하므로, small-full은 "research·design·plan이 빠진 required_stages를 가진 full 경로"와 정확히 동치다. `_run_develop_small_full`은 의도 명시·미래 분기점 확보용 얇은 wrapper. 형제·후속이 small-full 전용 처리를 넣을 단일 hook이 된다.

### 4.2 효과·불변식

- **INV-G6 (merge 억제 + design 복원)**: auto_policy에서 small-full → `_small_full_allowed False` → **`_restore_design_for_full`이 design을 required_stages에 복원 + gear=full 강등** → `_run_develop_full`이 `_stage_enabled(design)=True`로 design 강제. design 생략은 never/manual에서만(부모 §6.2). **"경로의 full"(어느 함수 호출)만으론 부족 — "단계의 full"(required_stages에 design 실재)까지 복원해야 INV-G6 성립**(cross-review R1 F2 해소). auto는 무검열 self-수정 통로 차단 유지.
- **INV-G7 (배포 동등성)**: 3-way 분기는 `_run_develop_phase`(`:1861`, dogfood 유일 DEVELOP 진입점)에 직접 들어감 — 픽스처-only 아님. `_run_develop_full` 재사용으로 prepare/execute/changed_files/goal_contract 처리 전부 검증된 경로 상속.
- **INV-G8 (light 무변)**: light 분기(`:1876`)는 첫 조건으로 그대로 — small-full은 light가 False일 때만 평가(순서 보존).
- **INV-G9 (gear 감사성)**: `_record_route_decision`(`:1747`)이 `to_dict()`(gear 포함)를 기록 → state·run 로그에 gear 보존, 어느 기어로 갔는지 사후 추적 가능.

### 4.3 테스트 (신규, production 경로)

- `_run_develop_phase`: route.gear=small_full + merge=manual + scope有 → `_run_develop_small_full` 호출(full pipeline.prepare가 route 전달받음, research/design/plan stage_enabled=False).
- 동일하나 merge=auto → `_restore_design_for_full` 호출 후 `_run_develop_full`. `state.route_decision["required_stages"]`에 `design` **복원됨**(STAGE_VOCAB 순서), `gear=="full"`로 강등. (F2: auto에서 design 실제 강제 검증 — "단계의 full")
- `_restore_design_for_full` 단위: design 부재 required_stages → design 삽입(순서 보존), 이미 design 有면 무변, gear→full.
- route.gear=light → `_run_develop_light`(무변).
- route.gear=full → `_run_develop_full`(무변).
- `state.route_decision["gear"]`가 `prepare(route=...)`까지 전달됨(전파 도달 테스트, §3.3 책임).

---

## 5. 범위 경계 — 무엇을 본 슬라이스에 넣지 않나 (churn 방지)

부모 §6.1 4원칙 중 **단계 집합으로 표현 가능한 것만** 본 슬라이스에 넣는다:

| 부모 §6.1 원칙 | 본 슬라이스 처리 | 이유 |
|---------------|-----------------|------|
| ① 싼 게이트가 비싼 걸 가린다(test 초록 전 cross_review 금지) | **범위 밖** — review_runner/orchestrator 실행순서 정책 | 단계 *집합*이 아니라 단계 *간 조건부 게이팅*. dogfood/orchestrator 층. 부모 S3와 인접하나 별도. |
| ② 스코프 재리뷰(2회차 diff만) | **범위 밖** — review 단계 내부 상태 | 단계 집합 무관, review_runner 내부. |
| ③ 하드 루프 캡 | **범위 밖** — 부모 S3가 이미 dynamic_orchestrator에 hard-stop 도입 | 중복 회피. |
| ④ 수렴 정의 명문화 | **범위 밖** | 위 ①~③의 종합 정의. |
| (신규) 규모별 단계 집합 기어 | **✅ 본 슬라이스** | light/small-full/full 3분 — 단계 집합 차원. |

> 분리 근거(메모리 `cross_review_stale_baseline_repeat`): 본 슬라이스는 `right_sized_router.py`(stage 집합·gear)와 `dogfood.py`(3-way 분기) **2파일·순수 분류 로직**으로 disjoint. ①~④의 실행순서·루프·diff 정책을 섞으면 review_runner/orchestrator baseline까지 churn에 노출되어 cross-review BLOCK 진동. 단계 집합 3분을 먼저 닫고, 실행순서 정책은 후속 전용 문서로.

---

## 6. 구현 순서·병렬성·배선 (Sonnet 핸드오프)

| 슬라이스 | 파일 | 의존 | 병렬 |
|---------|------|------|------|
| G1+G2+G3 | `core/right_sized_router.py` | 없음 | 선행 (gear 계약 생산) |
| G4 | `core/dogfood.py` | G2(`is_small_full`·`gear`·`_small_full_allowed`) 필요 | G1~G3 후 |

권장: **G1~G3 먼저**(라우터 gear 계약 확정 — 형제·G4 양쪽이 의존하는 SSOT), 그 다음 **G4**(dogfood 3-way). G4는 G2의 `is_small_full()`·`RouteDecision.gear`에 직접 의존하므로 순차.

**배포 동등성 체크리스트 (메모리 `pipeline_deploy_parity` — 픽스처-only 미허용):**
- G1~G3: `classify()`(`:327`, dogfood `:1872`가 유일 호출처)가 gear를 확정·to_dict 직렬화 → 자동 적용.
- G4: `_run_develop_phase`(`:1861`)가 dogfood DEVELOP 유일 진입점. 3-way 분기가 거기 직접 들어감.
- gear 전파: `_record_route_decision`(`:1747`) → `state.route_decision` → `_run_develop_full`의 `prepare(route=...)`(`:1774`) → `project_pipeline._stage_enabled`(`:42`). **이미 존재하는 dict 통로 재사용** — 신규 채널 0개.
- 형제 소비 도달: `route["gear"]`가 `project_brief["route"]`에 보존(project_pipeline `:848` baseline)되어 plan 빌더가 읽을 수 있음(§3.1).

**검증 grep (구현 후 의무):**
```
grep -rn "is_small_full\|\.gear\|GEAR_\|_small_full_allowed\|SMALL_FULL_STAGES" core/
```
→ 라우터 생산처·dogfood 소비처가 모두 잡혀야 함. 형제 영역(`bootstrap_roles.py`)은 본 PR에 없어야 함(영역 분리).

**3-Tier(전부 Tier-3 파일):** af-critic → af-cross-review → af-test-runner.

---

## 7. 불변식 요약

- **INV-G0**: light 경로 완전 무변(is_light·LIGHT_STAGES·임계 미변경).
- **INV-G1**: gear = required_stages 결정적 파생. 새 LLM 신호·임계 0개.
- **INV-G2**: gear ∈ {light, small_full, full} 닫힘. fallback/invalid → full.
- **INV-G3**: is_light ⊻ is_small_full (상호배타).
- **INV-G4**: Tier3 + design/research 포함 후보 → 종전 full floor(안전 무손실).
- **INV-G5**: small-full 적격 = review 또는 cross_review가 required_stages에 **실재**(F1 가드) — review-less {impl,test}는 full 폴백. Tier3는 Floor2가 review+cross_review 강제로 자동 충족.
- **INV-G6**: small-full design 생략은 merge∈{never,manual}일 때만. auto는 `_restore_design_for_full`로 design을 required_stages에 **복원** 후 full(경로의 full이 아니라 단계의 full까지 보장, F2 해소).
- **INV-G7**: 3-way 분기는 dogfood 유일 DEVELOP 진입점에 직접 — 픽스처-only 아님.
- **INV-G8**: light 분기 우선순위 보존(small-full은 light False일 때만).
- **INV-G9**: gear가 state.route_decision에 기록 — 사후 감사 가능.
- **공통**: gear named 계약은 라우터가 유일 생산자(§3.5 금지) — 형제는 소비만.

---

## 부록 A — named gear 계약 시그니처 (형제 핸드오프)

```python
# core/right_sized_router.py — 생산자 SSOT
SMALL_FULL_STAGES: frozenset[str] = frozenset(
    {STAGE_IMPLEMENT, STAGE_TEST, STAGE_REVIEW, STAGE_CROSS_REVIEW}
)
GEAR_LIGHT: Final[str]      = "light"
GEAR_SMALL_FULL: Final[str] = "small_full"
GEAR_FULL: Final[str]       = "full"

@dataclass
class RouteDecision:
    ...
    gear: str = GEAR_FULL                    # required_stages 파생, classify가 확정
    def is_small_full(self) -> bool: ...     # light보다 무겁고 full보다 가벼움
    def to_dict(self) -> dict[str, Any]:     # "gear" 키 포함 → state·pipeline 전파

def _derive_gear(decision: RouteDecision) -> str:  # gear 단일 설정 SSOT

# 전파 계약 (소비자는 read-only)
route_dict["gear"]: str   # "light" | "small_full" | "full", 기본 "full" 폴백 안전
```
