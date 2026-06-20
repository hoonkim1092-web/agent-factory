# 규모 인지 역할 분해 설계 (plan() 과분해 억제)

- 날짜: 2026-06-20
- 작성: Opus 4.8 (설계), 구현=Sonnet
- 상태: Draft — **B안 채택 (2026-06-20)**. 구현은 **다음 세션**(Sonnet).
- ⚠️ **B안 재작성 필요 (§3)**: 형제 우선순위3(gear) **폐기**됨. 규모 신호를 **`route["gear"]`가 아니라 `route["required_stages"]`에서 직접 유도**한다. §3.3 어댑터: `gear=="small_full"` → `STAGE_RESEARCH ∉ stages AND STAGE_DESIGN ∉ stages`(둘 다 부재면 small → `decomposition_strength="minimal"`, 아니면 standard). §2(프롬프트 분기)·§4(QA/merge_mode 완화)·§7(fallback)은 **유지**. cross-review 결과: 본 문서 R1 = WARN(Medium advisory 2건, BLOCK 0).
- 부모 설계: `docs/2026-06-20-dogfood-false-success-spin-fix-design.md` §6.2 (우선순위 5 — Bug 4 뿌리)
- 흡수 출처: `docs/2026-06-20-rse-small-full-execution-gear-design.md` (우선순위3, SUPERSEDED) — gear 소비를 required_stages 직접 판단으로 대체.
- 진단 동결 출처: 메모리 `project_dogfood_false_success_spin`, 부모 설계 §0 死因 사슬 [Bug 4] 과분해

---

## 0. 범위 선언 (무엇을 고치고 무엇을 미루나)

부모 진단의 死因 사슬에서 **[Bug 4] 과분해**(작은 변경에 full 프로젝트 조직표 생성)가 본 문서의 대상이다. 조연이지만 태스크 수를 부풀려 [Bug 3] 빈-사이클 grind를 악화시킨 증폭 인자다.

**이 설계가 고치는 것 (즉시):**
- **D1** — `plan()` 프롬프트를 **규모 신호에 따라 조건부화**한다. 작은 변경(small-full 기어) → "최소 분해" 프롬프트, 일반(full 기어) → 기존 director 프롬프트.
- **D2** — `_ensure_qa_role` 강제 주입을 **규모 + merge_mode 조건**으로 완화한다 (Floor2 억제는 `merge_mode∈{never,manual}`일 때만).
- **D3** — 규모 신호가 production caller(`project_pipeline.py:911`)까지 도달하는 배선. `plan()` 시그니처에 **additive·하위호환** 규모 파라미터 추가.

**이 설계가 미루는 것 (본 문서 밖):**
- `right_sized_router.py`의 gear 분류 자체 — **형제 설계(우선순위 3)의 영역**. 본 문서는 그 gear 신호를 **소비**만 한다. router 라인은 인용·수정하지 않는다 (churn 위험, 메모리 `cross_review_stale_baseline_repeat`).
- 단계템플릿/Floor2 라우팅 무게 조건부화 — 형제 영역.
- `_fallback_roles`의 규모 인지 (§7에서 판단: **불필요**로 결론. 근거는 §7).

**무죄 확정 (red herring):** `plan()`이 LLM을 못 부르는 환경(`_llm_available==False`)의 폴백은 이미 모듈 0개·5역할 캡(`bootstrap_roles.py:203`)이라 과분해의 진원이 아니다 (§7).

---

## 1. Baseline (실제 코드, 전수 인용 — 2026-06-20 live 재검증)

### 1.1 core/bootstrap_roles.py — plan() 과분해 진원

- `plan(self, task_input, project_brief, memory_context=None) -> dict`: **시그니처 `:398`**. 규모/size/tier/gear 파라미터 **없음**. project_brief에 규모가 실려야만 LLM이 인지 가능.
- 프롬프트 정체성 `"You are a project planning director."`: **`:400`** — 항상 최대 분해 정체성.
- 프롬프트 본문(JSON 스키마 + Module Design Rules + Evidence Grounding): `:399-475`.
- `_build_policy_rules()` 주입: **`:451`**.
- 모듈0 금지 규칙: **`:465`** `"- Each role owns 1-3 modules. Do NOT make a role own zero modules."`
- QA 필수 규칙: **`:473-474`**:
  ```
  MANDATORY: You MUST always include a "qa_engineer" role. QA is non-negotiable.
  The qa_engineer must own at least one module with verify-phase tasks.
  ```
- memory_context 주입: `:477-495` (프롬프트 끝에 append).
- LLM 가용성 가드: **`:498-499`** → `_fallback_roles`.
- 반환 normalized_payload `{execution_strategy, planning_steps, roles, modules, todo_items}`: **`:506-512`**.
- `_ensure_qa_role(normalized_payload)` 호출: **`:513`**. except 폴백: `:515-516`.

- `_ensure_qa_role(self, payload) -> None`: **`:318-396`**. QA 역할 부재 시:
  - QA 역할 강제 append: `:338-345` (policy.yaml `required_roles`에서 정의 로드).
  - verify-phase 모듈 부재 시 `qa_verification` 모듈 강제 주입: `:358-389` (verify-phase task `qa_integration_verify` 포함).
  - todo_items에 QA 항목 추가: `:392-396`.

- `_fallback_roles(self, task_input, project_brief) -> dict`: **`:133-205`**. 스킬 토큰 grouping → 역할 최대 5개(`:203` `roles[:5]`), **모듈 미생성**(반환 dict에 `modules` 키 없음, `:201-205`).

### 1.2 production caller — 배포 동등성 경로

- `core/project_pipeline.py:911` `_gen_role_plan()` 내부:
  ```python
  raw = self.planner.plan(task_input, project_brief, memory_context=memory_context)
  ```
  TypeError 폴백 `:913` `raw = self.planner.plan(task_input, project_brief)`. **이것이 plan()의 유일 production 호출.**
- `core/project_pipeline.py:848` `project_brief["route"] = route or {}` — **route dict가 prepare 단계에서 project_brief에 보존됨**. 이미 존재하는 seam. (`route`는 `:706` `prepare(..., route: dict|None=None)` 파라미터로 진입.)

### 1.3 규모 신호의 현재 출처 (형제 gear 계약과의 접점)

- dogfood full 경로는 `route=state.route_decision`을 pipeline에 전달(`core/dogfood.py:1774`), `state.route_decision = route.to_dict()`(`core/dogfood.py:1747`)는 router `classify()` 산출물이다.
- 따라서 **형제 설계가 RouteDecision(→`route.to_dict()`)에 `gear` 필드를 심으면, 그 값은 `project_brief["route"]`(`:848`)에 자동으로 흘러 들어와 `plan()`에서 `project_brief["route"].get("gear")`로 읽을 수 있다.** 새 배선 0줄로 신호가 도달한다.
- `merge_mode`는 `DogfoodState`(`core/dogfood.py:158`)에 있고 **현재 route/project_brief로 흐르지 않는다** → D2를 위해 명시 배선 필요(§4).

> ⚠️ `right_sized_router.py`의 라인·필드명은 **인용·단정 금지**. 본 설계는 "route dict에 `gear` 키가 존재할 수 있다"는 **인터페이스 가정**으로만 기술한다 (§3).

---

## 2. D1 — plan() 규모 조건부 프롬프트

### 2.1 설계 판단 (해석 분기 명시 — CLAUDE.md 원칙 1)

규모를 어떻게 표현할지 후보 2종:

| 표현 | 장점 | 단점 | 채택 |
|------|------|------|------|
| 분해 강도 enum `"minimal" \| "standard"` | 프롬프트 분기가 명확, 형제 gear와 1:1 매핑 가능 | enum 추가 | ✅ |
| 자유 텍스트 규모 힌트를 프롬프트에 끼움 | 코드 분기 없음 | LLM이 무시·오해 위험, 검증 불가 | ❌ |

**채택**: `decomposition_strength: str` (값 `"minimal" | "standard"`, 기본 `"standard"`). director 프롬프트(`:400-475`)는 `"standard"` 경로로 **무변 유지**(하위호환). `"minimal"`일 때만 별도 프롬프트 본문을 쓴다.

### 2.2 시그니처 확장 (additive·하위호환)

```python
def plan(
    self,
    task_input: str,
    project_brief: dict,
    memory_context: dict | None = None,
    decomposition_strength: str = "standard",   # 신규, 기본값 = 기존 동작
) -> dict:
```

- **INV-D1a (하위호환)**: 기존 호출(`plan(task, brief)`, `plan(task, brief, memory_context=...)`)은 `decomposition_strength="standard"`로 떨어져 **바이트 동일 프롬프트** → 기존 동작 무파손. `project_pipeline.py:913` TypeError 폴백 경로도 영향 없음.
- **INV-D1b**: 값 정규화 — `decomposition_strength`가 `{"minimal","standard"}` 외면 `"standard"`로 강제(미지 입력은 안전한 최대분해로 fail-safe).

### 2.3 minimal 프롬프트가 director 프롬프트와 다른 점

`"minimal"` 경로는 다음만 다르고 나머지(JSON 스키마, Evidence Grounding)는 **동일 스키마 재사용**한다 (스키마 일관성 → 다운스트림 normalize 무변):

| 항목 | standard (`:400-474` 현행) | minimal (신규) |
|------|---------------------------|----------------|
| 정체성(`:400`) | `"You are a project planning director."` | `"You are a senior engineer scoping a SMALL, surgical change."` |
| 분해 지침 | 최대 분해 | **`"Prefer the FEWEST roles and modules. A single-function or single-file change SHOULD yield exactly 1 role and 1 module. Do NOT invent organizational structure that the task does not require."`** |
| 모듈0 금지(`:465`) | 유지 | **유지** (1 모듈은 만들되 0은 여전히 금지 — 빈 분해 방지) |
| 역할 수 | 암묵 다수 | `"At most 2 roles unless the task genuinely spans separate subsystems."` |
| QA 필수(`:473-474`) | 유지 | **조건부 — §3에서 결정** (merge_mode와 결합) |

> **단순성(Karpathy 원칙 2)**: minimal 프롬프트는 director 프롬프트의 **별도 사본이 아니라**, 공통 스키마 블록(`:404-448`) + 공통 Evidence Grounding(`:468-471`)을 헬퍼로 묶고 정체성/분해지침/QA지침 **3개 슬롯만 분기**한다. 코드 중복 최소화.

- **INV-D1c**: standard 경로의 최종 프롬프트 문자열은 리팩토링 전후 **바이트 동일**해야 한다 (회귀 테스트로 고정 — §2.4). 이것이 하위호환의 핵심 검증.

### 2.4 테스트 (신규)

- `plan(..., decomposition_strength="standard")` 프롬프트 == 현행 프롬프트 (골든 스트링 비교, 바이트 동일).
- `plan(..., decomposition_strength="minimal")` 프롬프트에 `"FEWEST roles and modules"` 포함 AND `"project planning director"` 미포함.
- `decomposition_strength="garbage"` → standard로 정규화 (프롬프트 == standard).
- 기존 2-arg/3-arg 호출이 standard 프롬프트 생성 (하위호환).

---

## 3. 규모 신호 입력 계약 (형제 gear와의 공유 seam) — 전용 섹션

본 설계는 형제(우선순위 3)가 정의할 gear 분류의 **소비자**다. 형제가 어떤 필드명을 확정할지 **단정하지 않고**, 인터페이스 요구사항으로만 기술한다.

### 3.1 인터페이스 요구사항

1. 형제 설계는 RouteDecision에 **3분 기어**(light / small-full / full)를 named 계약으로 노출한다. 그 직렬화(`route.to_dict()`)에 기어를 식별하는 **단일 문자열 키**가 존재한다고 가정한다. 본 설계는 이를 **`route["gear"]`**로 참조한다 (형제 확정 키명과 다르면 §3.3 어댑터 1줄만 수정).
2. **gear → decomposition_strength 매핑** (본 설계가 소유):

   | 형제 gear | decomposition_strength | 근거 |
   |-----------|------------------------|------|
   | `small_full` | `"minimal"` | 작은 full 변경 → 최소 분해 |
   | `full` | `"standard"` | 기존 동작 유지 |
   | `light` | (plan() 미도달) | light는 ProjectPipeline을 안 타므로(`core/dogfood.py:1801` light 경로) plan() 호출 자체가 없음 — 매핑 불필요 |
   | 키 부재/미지값 | `"standard"` | fail-safe (형제 미배포 시 기존 동작) |

3. **light는 plan()에 도달하지 않는다**: light DEVELOP는 `_run_develop_light`(`core/dogfood.py:1801`)로 ProjectPipeline을 우회한다. 따라서 plan()이 보는 gear는 사실상 `{small-full, full}` 2종 + 부재뿐이다. 이 사실이 매핑을 단순하게 만든다.

### 3.2 신호가 plan()에 도달하는 경로 (배선)

기존 seam을 재사용한다 — **새 파이프라인 파라미터 0개**:

```
형제: classify() → RouteDecision.gear
        ↓ route.to_dict()  (core/dogfood.py:1747)
state.route_decision["gear"]
        ↓ prepare(route=...)  (core/dogfood.py:1774, project_pipeline.py:706)
project_brief["route"]["gear"]  (project_pipeline.py:848)
        ↓ _gen_role_plan()  (project_pipeline.py:909-914)
plan() 내부에서 project_brief["route"].get("gear") 읽음
```

### 3.3 plan() 내부 매핑 (어댑터, 1곳)

`plan()` 본문 진입부에서 `decomposition_strength` 파라미터가 **명시 전달되지 않은 경우에만** project_brief의 route에서 유도:

```python
# decomposition_strength가 호출자에서 명시되면 그것을 우선.
# 아니면 project_brief["route"]["gear"]에서 유도 (형제 gear 계약 소비).
if decomposition_strength == "standard":   # 미명시 기본값
    gear = str((project_brief.get("route") or {}).get("gear") or "").strip()
    if gear == "small_full":   # 형제 우선순위 3 확정 리터럴 (GEAR_SMALL_FULL)
        decomposition_strength = "minimal"
    # full / 부재 / light / 미지 → standard 유지 (fail-safe)
```

- **INV-D3a (배선 단일화)**: gear→strength 매핑은 **이 한 곳에만** 존재. 형제 우선순위 3 설계가 키 `"gear"` / 값 `"small_full"`(`GEAR_SMALL_FULL`)로 확정 → 본 리터럴은 그에 정렬됨(통합 정렬 완료).
- **INV-D3b (이중 입력 우선순위)**: 호출자가 `decomposition_strength="minimal"`을 명시하면 route 유도를 건너뛴다 (테스트·직접 호출자 우선). route 유도는 production 기본 경로 전용.
- **INV-D3c (형제 미배포 안전)**: 형제 gear 미배포(키 부재) → 항상 `"standard"` → 기존 동작 100% 보존. 두 설계는 **독립 머지 가능**.

> **가정 정렬 결과 (CLAUDE.md 원칙 1)**: 형제 우선순위 3 설계가 **키 `"gear"` / 값 `"small_full"`**(`GEAR_SMALL_FULL`, `right_sized_router` SSOT)로 확정했고, 본 §3.3 어댑터 리터럴은 그에 정렬됐다. 두 설계가 동일 seam(`project_brief["route"]["gear"]`)에 합의한 상태 — 머지 시 추가 통합 작업 없음. (형제가 추후 라벨을 바꾸면 §3.3의 단일 리터럴만 재정렬.)

---

## 4. D2 — _ensure_qa_role / QA필수 규칙의 규모·merge_mode 조건부화

### 4.1 설계 판단 (왜 merge_mode 조건이 필수인가)

부모 §6.2 동결 제약: **Floor2(QA/verify 강제) 억제는 `merge_mode∈{never,manual}`일 때만**. 근거:
- `auto_policy`는 **내부 리뷰가 유일한 머지 게이트** → QA/verify를 빼면 검증 없이 자동 머지 위험.
- `never`/`manual`은 사람이 머지 결정 → QA 모듈을 자동 강제하지 않아도 안전.

따라서 QA 완화는 **`decomposition_strength=="minimal"` AND `merge_mode∈{never,manual}`** 두 조건의 **교집합**에서만 일어난다. 둘 중 하나라도 아니면 QA 강제 **유지**(현행 동작).

### 4.2 merge_mode 신호 배선 (신규 — route에 없음)

§1.3대로 `merge_mode`는 현재 project_brief로 흐르지 않는다. 최소 배선:

- dogfood full 경로에서 `prepare()` 호출 시 route dict에 merge_mode를 실어 보낸다. 가장 작은 변경은 `state.route_decision`에 merge_mode를 합류시키는 것이나, **route_decision은 router 산출물(형제 영역)이라 오염 금지**. 대신 **`prepare()`가 받는 route와 별개로**, dogfood가 project_brief 보존 시점에 merge_mode를 끼우는 경로를 택한다.

채택 배선 (형제 router 무관, dogfood→pipeline 국소 변경):
1. `pipeline.prepare(...)`에 이미 존재하는 route dict를 통해 전달하되, **router가 만든 키와 충돌하지 않는 네임스페이스 키** `route["_merge_mode"]`(언더스코어 접두 = pipeline 내부 메타)로 dogfood가 주입.
2. `core/dogfood.py:1774` 인근에서 `route` 전달 직전 `route = {**(state.route_decision or {}), "_merge_mode": state.merge_mode}`.
3. `project_pipeline.py:848`이 이를 `project_brief["route"]["_merge_mode"]`로 보존(기존 코드 무변 — 통째 dict 보존).
4. `plan()`이 `project_brief["route"].get("_merge_mode")`로 읽음.

- **INV-D2a (기본 안전)**: merge_mode 부재(키 없음) → `auto_policy`로 간주 → QA **강제 유지**. 비-dogfood 호출자(merge_mode 개념 없음)는 항상 QA 강제 → 현행 동작 보존.

### 4.3 변경 — plan()의 _ensure_qa_role 호출 조건부화

현행 `:513`은 **무조건** `_ensure_qa_role` 호출. 이를 조건부로:

```python
qa_relaxed = (
    decomposition_strength == "minimal"
    and str((project_brief.get("route") or {}).get("_merge_mode") or "auto_policy")
        in ("never", "manual")
)
if not qa_relaxed:
    self._ensure_qa_role(normalized_payload)
```

추가로 **minimal+relaxed 경로의 프롬프트**(§2.3)에서 QA 필수 문구(`:473-474` 등가물)를 **생략**한다 (프롬프트와 후처리 양쪽 정합). standard 경로 프롬프트는 QA 문구 유지.

- **INV-D2b**: `auto_policy`(기본)에서는 minimal이어도 QA 강제 유지 — 부모 §6.2 제약 충족.
- **INV-D2c**: standard(full)에서는 merge_mode 무관하게 QA 강제 유지 — 큰 변경은 항상 QA.
- **INV-D2d**: `_ensure_qa_role` 함수 자체(`:318-396`)는 **무변** — 호출 여부만 게이팅. 다른 호출자가 있다면(grep로 확인: 현재 `:513` 단일 호출) 영향 없음.

### 4.4 모듈0금지(`:465`) 규칙의 규모별 처리

- minimal 경로도 **모듈0 금지는 유지**한다(§2.3). 이유: 0 모듈은 빈 분해 → 다운스트림 board 생성(`project_pipeline.py:938` `build_project_board`)이 빈 작업이 되어 또 다른 침묵 실패 위험. minimal의 목표는 **"1 모듈"**이지 "0 모듈"이 아니다.
- 즉 규모 조건부화의 효과는 **"항상 1 모듈"** 보장 + **QA 모듈 추가 억제**(relaxed 시). 모듈 수 N→1 축소가 과분해 억제의 본체.

### 4.5 테스트 (신규)

- minimal + merge_mode="never" → `_ensure_qa_role` 미호출 (payload에 qa_engineer 없음, qa_verification 모듈 없음).
- minimal + merge_mode="manual" → 동일 (미호출).
- minimal + merge_mode="auto_policy" → `_ensure_qa_role` **호출**(QA 주입됨) — INV-D2b.
- minimal + merge_mode 부재 → 호출 (auto_policy 간주) — INV-D2a.
- standard + merge_mode="never" → 호출 (full은 항상 QA) — INV-D2c.
- minimal payload는 roles≥1 AND modules≥1 (모듈0 금지 유지) — INV §4.4.

---

## 5. 구현 순서·병렬성 (Sonnet 핸드오프)

| 슬라이스 | 파일 | 의존 | 비고 |
|---------|------|------|------|
| D1 | `core/bootstrap_roles.py` | 없음 | 시그니처 확장 + 프롬프트 슬롯 분기 + standard 골든 회귀 |
| D2 | `core/bootstrap_roles.py` (`:513` 조건부) + `core/dogfood.py` (`:1774` merge_mode 주입) | D1 선행 | qa_relaxed 게이팅 |
| D3 | `core/bootstrap_roles.py` (§3.3 어댑터) | D1 선행 | gear→strength 매핑 |

- D1을 먼저 닫고(시그니처+프롬프트), D2·D3는 같은 파일이라 순차. dogfood 변경은 D2 1곳(`:1774` 인근)뿐.
- **배포 동등성 (메모리 `pipeline_deploy_parity`)**: 픽스처-only 미허용. production caller `project_pipeline.py:911`까지 신호 도달을 grep로 검증 — gear는 `project_brief["route"]`(`:848`) 경유, merge_mode는 `core/dogfood.py:1774` 주입 경유. 둘 다 end-to-end 연결 확인 의무.
- **형제 독립성**: 형제 gear 미배포 시에도 D1~D3는 standard 기본값으로 무해(INV-D3c). 두 PR은 머지 순서 무관, §3.3 리터럴만 통합 시점에 정렬.
- 3-Tier(전부 Tier-3 파일 — core/): af-critic → af-cross-review → af-test-runner.

---

## 6. 핵심 설계 질문 답변 (요구된 5문)

1. **규모 신호가 plan()에 어떻게 도달?** — `plan()`에 `decomposition_strength="standard"` 파라미터 additive 추가(§2.2). production에서는 명시 전달 대신 **기존 `project_brief["route"]` seam**(`:848`)에 형제가 심은 `gear`를 §3.3 어댑터가 읽어 유도. 하위호환은 기본값 `"standard"` = 바이트 동일 프롬프트로 보장(INV-D1a/c).
2. **minimal이 director와 다른 점?** — 정체성("senior engineer scoping a SMALL change") + 분해지침("FEWEST roles/modules, 단일 파일→1역할 1모듈") + 역할 ≤2 + (relaxed 시) QA 문구 생략(§2.3). 스키마·Evidence 규칙은 공유.
3. **_ensure_qa_role 완화?** — `:513` 호출을 `decomposition_strength=="minimal" AND merge_mode∈{never,manual}` 교집합에서만 skip(§4.3). `auto_policy`는 QA 강제 유지(부모 §6.2 제약, INV-D2b).
4. **모듈0금지·qa필수 조건부화?** — 모듈0 금지는 **모든 규모에서 유지**(빈 분해 방지, §4.4). qa필수는 minimal+relaxed에서만 프롬프트·후처리 양쪽 완화(§4.3).
5. **fallback도 규모 인지 필요?** — **불필요**(§7).

---

## 7. _fallback_roles 규모 인지 판단 (불필요 결론)

`_fallback_roles`(`:133-205`)는 LLM 미가용 시에만 진입(`:498-499`, `:515-516`). 분석:
- **모듈을 아예 생성하지 않는다** (`:201-205` 반환 dict에 `modules` 키 없음) → 과분해의 진원이 아니다.
- 역할은 스킬 토큰 grouping + 5개 캡(`:203`). 작은 변경이면 `required_skills`가 적어 자연히 역할도 적다.
- `_ensure_qa_role`은 fallback 반환에는 **호출되지 않는다** (`:513`은 LLM 성공 경로 전용; fallback은 `:499`/`:516`에서 즉시 return).

→ fallback은 이미 최소 분해에 가깝고 QA 강제도 없다. 규모 인지를 추가하면 **추측성 복잡도**(Karpathy 원칙 2 위반). **변경하지 않는다.** 단, fallback이 plan() 시그니처 변경의 영향을 받지 않음을 회귀 테스트로 확인(`_llm_available=False` → fallback 반환 무변).

- **INV-F1**: `plan()` 시그니처 확장 후에도 `_llm_available=False` 경로는 기존 fallback dict를 바이트 동일하게 반환.

---

## 8. 불변식 요약

- **INV-D1a/b/c**: standard 기본값=기존 동작 무파손, 미지값→standard fail-safe, standard 프롬프트 바이트 동일(골든).
- **INV-D2a/b/c/d**: merge_mode 부재→auto_policy→QA강제, auto_policy minimal도 QA강제, full은 항상 QA, `_ensure_qa_role` 함수 본체 무변.
- **INV-D3a/b/c**: gear→strength 매핑 단일 지점, 명시 호출자 우선, 형제 미배포 시 standard로 독립 안전.
- **INV-F1**: fallback 경로 무변(규모 인지 미적용).
- **공통**: 배포 동등성 — gear는 `project_brief["route"]`(`project_pipeline.py:848`) seam, merge_mode는 `core/dogfood.py:1774` 주입으로 production caller `project_pipeline.py:911`까지 end-to-end 도달(픽스처-only 미허용).
- **형제 경계**: `right_sized_router.py` 무인용·무수정. gear 계약은 §3 인터페이스 요구사항으로만 소비.
