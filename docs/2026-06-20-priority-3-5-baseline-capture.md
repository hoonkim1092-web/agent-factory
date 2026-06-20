# 우선순위 3·5 별도 설계용 baseline 캡처 (실코드 동결)

- 날짜: 2026-06-20
- 목적: `docs/2026-06-20-dogfood-false-success-spin-fix-design.md` §6.1(우선순위 3)·§6.2(우선순위 5) 전용 설계문서 작성 시 **stale baseline로 인한 cross-review BLOCK 진동**(메모리 `cross_review_stale_baseline_repeat`) 방지. 설계 착수 전 실코드 사실을 동결한다.
- 캡처 방식: read-only Explore 에이전트 2개 병렬(S2 구현과 동시 진행). 아래 라인 번호는 캡처 시점(2026-06-20) 기준 — 설계 착수 시 재확인 의무.
- ⚠️ 이 문서는 reference(사실 동결)이지 설계가 아니다. 설계는 별도 dated 문서로.

---

## A. 우선순위 3 — 작은 Tier-3 실행 기어 (`core/right_sized_router.py`)

| 항목 | 사실 | 라인 |
|------|------|------|
| Light 자격 함수 | `is_light()` — `source=="llm"` AND `confidence>=threshold` AND `set(required_stages) <= LIGHT_STAGES` | 55-70 |
| Light 임계값 | `_LIGHT_CONFIDENCE_THRESHOLD=0.7` / `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD=0.85`(SCOPE_UNCERTAIN marker 시) | 35-36 |
| Light 단계 집합 | `LIGHT_STAGES = frozenset({plan, implement, test})` | 33 |
| Full 단계 집합 | `_FULL_STAGES = list(STAGE_VOCAB)` = [research, design, plan, implement, test, review, cross_review] | 104, 28-31 |
| Floor 2 주입 | `_apply_safety_floors()` 내: `changed_files and _max_tier(...)>=3` → `(design, review, cross_review)` 강제 union | 205-227 (조건 218-224) |
| Production caller | `core/dogfood.py:1872` `_run_develop_phase()` → `classify(state.task, cwd, changed_files=scope)` → `route.is_light()`로 light/full 분기 | dogfood.py 1861-1878 |

**핵심 사실**: 이 라우터는 **분류만** 한다. 단계별 build/test/review 구현 템플릿은 라우터 밖(소비처: `project_pipeline.py`, `dogfood.py`)에 있다. full은 규모 무관 단일 기어(`_FULL_STAGES` 고정). §6.1이 말하는 "작은 full 기어"는 여기에 light↔full 이분법을 3분(light / small-full / full)으로 확장하는 것.

## B. 우선순위 5 — 과분해(Bug 4) 뿌리 (`core/bootstrap_roles.py`)

| 항목 | 사실 | 라인 |
|------|------|------|
| `plan()` 시그니처 | `plan(self, task_input, project_brief, memory_context=None) -> dict` | 398 |
| 반환 | `{execution_strategy, planning_steps, roles, modules, todo_items}` | — |
| 프롬프트 정체성 | `"You are a project planning director."` | 400 |
| 분해 지시 | JSON 스키마 + Module Design Rules + Evidence Grounding | 404-475 |
| 모듈0 금지 | `Each role owns 1-3 modules. Do NOT make a role own zero modules.`(프롬프트 규칙) | 465 |
| QA 필수(프롬프트) | `MANDATORY: You MUST always include a "qa_engineer" role.` | 473-474 |
| QA 필수(코드 강제) | `_ensure_qa_role(payload)` — QA 역할 부재 시 강제 추가 + verify 모듈 주입. `plan()`이 normalized_payload에 호출 | 318-396 (호출 513) |
| **규모 인지 입력** | **없음** — `plan()`은 scale/size/tier 파라미터를 받지 않음. project_brief에 규모 필드가 있어야만 LLM이 인지 가능 | 398 시그니처 |
| Production caller | `core/project_pipeline.py:911`(memory_context 有) / `:913`(TypeError 폴백) — `_gen_role_plan()` 내 유일 호출 | pipeline.py 909-914 |

**핵심 사실**: full 경로는 규모를 모르는 채 항상 director 프롬프트로 최대 분해. `_ensure_qa_role`이 verify 모듈까지 강제 주입해 작은 변경에도 풀 프로젝트 역할/모듈이 생성됨(과분해). §6.2 수정 방향 = (1) plan() 프롬프트를 규모 조건부화(작은 변경 → 최소 분해), (2) full 단일 기어 분해. **단 §6.2는 `merge_mode∈{never,manual}` 조건일 때만 Floor2 억제 결합**(auto_policy는 내부리뷰가 유일 게이트).

---

## C. 두 설계를 합치지 말 것

§6.1(라우팅)·§6.2(프롬프트)는 둘 다 아키텍처 변경이라 baseline이 spec churn에 노출된다. 각각 **전용 dated 설계문서**로 분리하고, 각 문서는 이 baseline의 해당 절만 인용한다. (S1~S3가 disjoint correctness 슬라이스로 1라운드에 닫힌 것과 대조 — 메모리 `cross_review_stale_baseline_repeat` 학습.)
