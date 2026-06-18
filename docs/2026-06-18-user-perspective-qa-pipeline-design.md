# 사용자 시점 자동 QA 파이프라인 — intake 테스트 명료화 + 리서치 폴백 설계

**날짜**: 2026-06-18
**상태**: Draft
**작성자**: Claude Opus 4.8
**연관 설계**: `docs/2026-06-17-af-completion-contract-goal-verification-design.md` (완료계약 — 이 설계의 **다운스트림 소비자**)

---

## §1 배경 및 동기

### §1.1 완료계약(2026-06-17)이 "포기한" 두 구멍이 이 설계의 동기다

완료계약 설계는 `GoalContract` + `AcceptanceGate`로 "생성≠완료"를 닫으려 했으나, §10에서 **두 가지를 명시적으로 범위 밖으로 던졌다**:

| 완료계약 §10 항목 | 그 결정 | 이 설계가 메우는 방식 |
|---|---|---|
| "GoalContract LLM 추출 정확도 — planner criteria 품질은 범위 밖" | 별도 조율 | **intake에서 사용자가 직접 골/테스트를 주거나, 스킵 시 리서치가 합성** |
| "정답 검증(기대출력 비교) 미구현 — 의미적 골은 CANNOT_VERIFY로 충분" | 미구현 | **사용자/리서치가 골든 예시(입력→기대출력)를 intake에서 제공 → 기대출력 기준 확보** |

즉 완료계약의 AcceptanceGate는 "어떻게 검증하는가"의 **실행기**이고, 이 설계는 "**무엇이 정답이고 어떻게 먹이는가**"를 만들어 그 실행기에 공급하는 **머리**다. 머리가 비면 게이트는 CANNOT_VERIFY만 찍는다.

### §1.2 핵심 통찰 (사용자, 2026-06-18)

1. **테스트 가능성은 제품마다 다르다.** meeting_stt는 "라이브 마이크 대신 녹음 파일 주입 + 골든 텍스트 비교"로 검증되지만, 다른 제품은 다른 방법을 **찾아야** 한다 → 제품별 질문지 N개가 아니라 **추상 질문 + 사용자 구체답 + LLM 특화**.
2. **테스트 명료화는 맨 앞(intake)에서 해야 한다.** "~만들어줘" 순간의 심층 질문 파이프라인에 **골 질문 + 테스트 질문**이 들어가야 한다.
3. **사용자가 스킵하면 LLM 리서치로 설계해야 한다.** 스킵 = 빈 기본값으로 추락이 아니라, 리서치가 골/기대출력 기준/seam을 **합성**.

### §1.3 테스트 seam — meeting_stt 사례로 본 원리

GUI+장치 앱조차, **테스트 이음새(seam)를 설계 단계에 박으면** 대부분 자동 검증 가능하다:

```
meeting_stt: 음성을 실시간으로 타이핑하듯 화면에 흘려보내는 앱
  입력 주입 seam:  --audio-file recording.wav   (라이브 마이크 대신)
  출력 캡처 seam:  타이핑 텍스트를 GUI 픽셀이 아니라 stdout/파일로도 노출
  real-time 속성:  부분 결과를 타임스탬프와 함께 흘리면 "실시간성"도 property로 검사
```

→ "사용자처럼 테스트" = **알려진 녹음 주입 → 텍스트 캡처 → 골든 비교 + 타임스탬프 검사**. 사람 입력 0.
진짜 못 막는 것은 "물리 마이크"와 "순수 픽셀 렌더링"뿐 → 정직하게 `CANNOT_VERIFY`로 남긴다.

---

## §2 현재 코드 진단 (grep 확정)

### §2.1 intake 경로 2개 — 둘 다 스킵 시 정적 기본값으로 추락

**경로 A — 비대화/FSA (`core/interview.py:150-176`)**:
```python
# interview.py:165-168
should_auto_answer = bool(non_interactive or deep_skip)
if should_auto_answer:
    enriched = auto_apply_defaults(base_brief, questions)   # ← 정적 q.get("default","")
    answers = [entry.get("answer", "") for entry in enriched.get("clarification_log", [])]
```

**경로 B — approval 대화 (`agent_launcher.py:524-547`)**:
```python
# agent_launcher.py:533
if not should_skip_clarification(prepared_brief.project_brief, ...):
    questions = generate_clarification_questions(...)
    answers = self._collect_clarification_answers(questions)
    prepared_brief.project_brief = merge_clarification(...)
# should_skip_clarification == True  →  질문도, 합성도 없이 그대로 진행
```

### §2.2 `auto_apply_defaults`의 약점 (`core/clarification.py:178-184`)

```python
def auto_apply_defaults(project_brief, questions):
    """FSA 모드: 모든 질문에 기본값 자동 적용."""
    answers = [q.get("default", "") for q in questions]   # ← 멍청한 정적 폴백
    return merge_clarification(project_brief, questions, answers)
```
`merge_clarification`(`:130`)도 빈 답 → `q.get("default","")`(`:143`). **즉 스킵·FSA·빈 답 = 골/기대출력 기준/seam이 빈 문자열.**

### §2.3 현재 질문 세트 (`core/control/questions/goal_clarification.yaml`)

| id | 필수 | 형태 | 한계 |
|---|---|---|---|
| `goal_summary` | 필수 | 자유텍스트 | 관찰가능한 골 아님 |
| `deployment_target` | 필수 | 자유텍스트 | — |
| `success_criteria` | **선택** | **자유텍스트** | 테스트 방법·기대출력 기준·seam 미추출 |
| `out_of_scope` | 선택 | 자유텍스트 | — |

→ "성공 기준"을 묻긴 하나 **선택 + 자유텍스트**라 구조화된 골/기대출력 기준/seam이 안 나온다.

### §2.4 리서치 엔진 — 이미 존재 (신규 인프라 아님)

- `core/research_router.py:202` `ResearchRouter`, `:214` `plan(request) -> ResearchPlan`
- `core/research_engine.py` · `research_brief.py` · `research_verifier.py` · `researcher.py`

스킵 경로는 **새 호출이 아니라 `ResearchRouter`로 라우팅**한다.

### §2.5 완료계약(2026-06-17) 산출물 — 이 설계의 소비처

- `core/completion_contract.py` (S1 완료): `GoalVerdict`/`GoalEvidence`/`GoalEntry`/`GoalContract`/`HarnessResult`
- 생성 SSOT = `project_pipeline.prepare():1246` → `task_board.acceptance_criteria` 파싱 → `GoalContract`
- S2(`ExecutionHarness`+`AcceptanceGate`)·S3(pipeline 통합)는 **미구현**

---

## §3 설계 원칙 (불변식)

**INV-Q1 (스킵 ≠ 빈값)**
골/테스트 질문을 스킵·FSA·빈 답으로 두면 정적 기본값이 아니라 **`ResearchRouter` 합성**을 트리거한다. 합성 실패 시에만 `provenance="default"`로 떨어진다.

**INV-Q2 (provenance 신뢰등급 — 거짓 VERIFIED 차단)**
모든 골/기대출력 기준/seam은 출처를 명시한다: `user`(높음) / `research`(중간, async 확인 필요) / `default`(낮음). 이 표기는 `GoalEntry` → `EvidenceLedger` → HTML 리포트까지 흐른다.

**INV-Q3 (seam = 구현 요구사항)**
테스트 방법으로 합의된 seam(예: 파일 입력 모드, 출력 캡처)은 **`deliverables`로 흘러 planner 태스크가 된다**. seam 없는 구현은 나중에 게이트가 돌 입구가 없어 CANNOT_VERIFY로 추락한다.

**INV-Q4 (리서치 합성 기대출력 기준은 구현 전 동결 + async 확인)**
리서치 합성 기대출력 기준은 **구현 추론과 섞이기 전(intake)에 동결**한다. 같은 LLM이 기대출력 기준·구현·판정을 모두 하면 자기 채점 순환이 최악이 되므로, ⓐ 기대출력 기준을 구현 전에 고정 ⓑ HTML 리포트에 `source=research` 가정을 명시해 사용자가 비동기로 확인.

---

## §4 질문 세트 확장 (`goal_clarification.yaml`)

제품 무관 추상 질문. 전부 **선택**(스킵 시 §6 리서치). LLM이 초안을 제시하고 사용자가 확인/수정(기존 `auto_apply_defaults` 철학 계승).

```yaml
  - id: observable_goal
    text: "다 됐다는 걸 어떻게 눈으로 확인합니까? 관찰 가능한 형태로 알려주세요."
    output_field: observable_goal
    required: false
    default_route: research_synthesize          # ← 신규 라우트 (스킵 시 §6)

  - id: golden_example
    text: "예시 입력 하나와, 그때 기대하는 출력을 알려주세요."
    output_field: golden_example                 # 기대출력 기준 씨앗
    required: false
    default_route: research_synthesize

  - id: test_seam
    text: "특수 장비 없이 먹일 수 있는 입력이 있나요? (예: 라이브 마이크 대신 녹음 파일)"
    output_field: test_seam                      # seam 발견
    required: false
    default_route: research_synthesize

  - id: manual_only
    text: "자동으로는 못 보고 직접 눈으로 확인해야 하는 부분은?"
    output_field: manual_only                    # 합의된 CANNOT_VERIFY
    required: false
    default_route: research_synthesize
```

> **제품 차이 흡수**: 같은 질문에 STT는 "이 wav→'안녕하세요'", 웹앱은 "이 URL 누르면 대시보드", CLI는 "이 인자→이 stdout"로 답한다. LLM이 그 구체답을 harness_type/시나리오/기대출력 기준으로 특화한다(§5/§8).

> **2026-06-18 정정 (BLOCK #3 — route/category 배선 요구)**: `default_route: research_synthesize`는 **현재 enum에 없다** — `core/control/verdicts.py:5-9` `QuestionRoute`는 `PASS/LLM_DELEGATE/HITL/BLOCK` 4개뿐(grep 확정). 따라서 이 YAML이 동작하려면 §Q-S2에서 **(a) `QuestionRoute.RESEARCH_SYNTHESIZE` enum 값 추가 + (b) `question_router.route_batch()`에 그 분기 추가**가 선행돼야 한다. 또한 seam 답을 §7 deliverables 채널로 보내려면 **경로별 승격 로직이 필요**하다(아래 §7 정정 — yaml은 `output_field` 기반이라 `merge_clarification`의 `category` 분기를 자동으로 안 탄다).

---

## §5 데이터 구조

### §5.1 `GoalEntry` 확장 — 완료계약 SSOT에 additive 필드 (타입 재선언 금지)

타입 SSOT 규칙(CLAUDE.md)에 따라 **새 타입을 만들지 않고** `core/completion_contract.py`의 기존 `GoalEntry`에 하위호환 필드를 추가한다:

```python
# core/completion_contract.py (기존 GoalEntry 확장)
Provenance = Literal["user", "research", "default"]

@dataclass
class GoalEntry:
    goal_id: str
    description: str
    harness_type: str
    evidence: GoalEvidence | None = None
    verdict: GoalVerdict = "UNVERIFIED"
    cannot_verify_reason: str = ""
    # ── 신규 (additive, 기본값으로 하위호환) ──
    scenario: list[str] = field(default_factory=list)   # 다단계 시나리오 (각 step 명령/검사)
    expected_output: str = ""                            # 기대출력/골든 (정답 기준)
    provenance: Provenance = "default"                   # 출처 신뢰등급 (INV-Q2)
```
`to_dict`/`from_dict`는 신규 필드를 포함하도록 갱신(round-trip 불변식 유지).

### §5.2 `TestManifest` — 프로젝트 레벨 도구/환경 요구 (신규 타입, 1개 파일 선언)

```python
# core/completion_contract.py (신규)
@dataclass
class TestManifest:
    required_tools: list[str] = field(default_factory=list)   # MCP·외부 프로그램·패키지
    required_env: list[str] = field(default_factory=list)     # env var·장치
    seam_requirements: list[str] = field(default_factory=list)# 구현이 노출해야 할 입력주입/출력캡처
    provenance: Provenance = "default"
```
`GoalContract`에 `manifest: TestManifest | None = None` 필드 추가(직렬화 round-trip 포함).

---

## §6 스킵 → 리서치 합성 경로

### §6.1 트리거 지점 (intake 경로 **3개** 전부 — cross-review BLOCK #2 반영)

> **2026-06-18 정정 (BLOCK #2)**: 초안은 경로 A·B 2개만 명시했으나, `goal_clarification` YAML을 독립 소비하는 **3번째 경로**가 있다(grep 확정): `core/control/stage_router.py:81,101-106` `_run_new_project()`가 `goal_clarification` 스키마를 로드해 `question_router.route_batch()`로 처리하고(`work_item_generator.py:1170-1171`에서 호출), 이 경로는 A·B와 **다른 메커니즘**(`output_field` 기반 route_batch)이다. 세 경로 모두 스킵→합성을 배선하지 않으면 new_project 경로가 정적 기본값으로 추락한다(배포 동등성 위반).

- **경로 A** `interview.py:167` — `auto_apply_defaults` 호출을 **`synthesize_via_research(base_brief, questions)`로 교체**(default_route가 `research_synthesize`인 질문만 합성, 나머지는 기존 정적 기본값 유지).
- **경로 B** `agent_launcher.py:533` — `should_skip_clarification == True`인 경우에도 골/테스트 질문은 합성 1회 수행(approval 모드라도 스킵된 골/테스트 항목은 리서치로 채움).
- **경로 C** `core/control/stage_router.py:101-106` `_run_new_project()` — `goal_clarification` YAML을 `question_router.route_batch()`로 처리. 이 경로의 신규 질문 스킵 시에도 합성을 태운다 → §Q-S2의 `QuestionRoute.RESEARCH_SYNTHESIZE` 분기가 route_batch에 배선돼야 발동(아래 §6.2 enum 의존).

### §6.2 합성 로직 (신규 `core/clarification.py` 또는 신규 헬퍼)

> **2026-06-18 정정 (BLOCK #1 — 존재하지 않는 API 호출)**: 초안 pseudo-code의 `research_engine.run(plan, brief)`·`findings.field_for()`는 **실재하지 않는다**(grep: `core/research_engine.py`에 `query_notebooklm`/`ResearchMode`/`classify_research_depth`만, `run()`/`field_for()` 없음). `ResearchRouter.plan()`(`research_router.py:214`)만 실재. 따라서 아래는 **의도(intent)를 보이는 illustrative pseudo-code이지 실제 호출이 아니다**. **Q-S3 선행 작업으로 실제 API 조사 + 어댑터 설계가 필수**다(메모리 `analysis_doc_baseline_must_be_real_code`).

```
# ⚠️ illustrative — 실제 함수 시그니처는 Q-S3에서 research_engine/researcher/research_router
#    실 API 조사 후 확정. 아래는 "무엇을 한다"의 의도만 표현.
synthesize_via_research(brief, questions):
    plan = ResearchRouter().plan(brief["goal"])          # ✅ 실재 (research_router.py:214)
    findings = <research 실행 — 실 API는 Q-S3 조사>       # ⚠️ run()은 미존재. 어댑터 필요
    for q in questions where default_route == research_synthesize:
        answer = <findings에서 q.output_field 후보 추출>   # ⚠️ field_for() 미존재. 어댑터 필요
        provenance = "research" if answer else "default"
    return merge_clarification(brief, questions, answers, provenance="research")
```

**Q-S3 선행 조사 산출물 (구현 전 필수)**: `research_engine.py`/`researcher.py`/`research_brief.py`의 실제 진입 함수 중 "goal 텍스트 → 골/기대출력/seam 후보"를 얻는 경로를 식별하고, 그 반환 구조에서 `output_field`별 값을 뽑는 **어댑터 함수**를 명세한다. 어댑터가 불가능하면(엔진이 그런 출력을 안 줌) §10 Q-S3을 "리서치 합성 미지원 → 스킵=UNVERIFIED"로 축소(아래 폴백이 그 안전망).

- 합성 실패(엔진 미가용/빈 결과/어댑터 부재) → `provenance="default"` + 해당 골 `verdict="UNVERIFIED"`(완료계약 §4.2 파서 폴백과 정합: 검증 못 정함 = UNVERIFIED = `is_done()==False`).
- **재사용 우선**: research_router/engine은 기존 모듈. 새 LLM 호출 경로를 만들지 않는다.

---

## §7 seam = 구현 요구사항 (INV-Q3)

> **2026-06-18 정정 (BLOCK #3 — "자동 같은 채널"은 사실 아님)**: 초안은 "seam도 `merge_clarification`의 scope→deliverables 채널을 자동으로 탄다"고 했으나 **두 경로의 메커니즘이 다르다**(grep 확정): `merge_clarification`(`clarification.py:157,164-168`)은 동적 생성 질문의 `category` 필드로 분기하는데, **`goal_clarification.yaml` 질문은 `category`가 아니라 `output_field` 기반**이고 경로 C(stage_router/route_batch)를 탄다. 따라서 seam 승격은 **공짜 재사용이 아니라 명시적 승격 로직**이 필요하다.

`merge_clarification`은 동적 질문의 scope 답을 `deliverables`로 매핑한다(`clarification.py:164-168`, `spec_compiler.py:115/158` 확인) — 단 이는 `category` 기반 경로. **seam(`output_field=test_seam`) 승격은 별도 배선**한다:

```
test_seam 답 / TestManifest.seam_requirements
   → (신규 승격 로직) enriched["deliverables"]에 "테스트 seam: --audio-file 입력 모드 노출" append
       · 경로 A/B(merge_clarification): test_seam 답을 deliverables로 명시 매핑 추가
       · 경로 C(route_batch): output_field=test_seam 결과를 deliverables로 승격하는 hook 추가
   → planner가 그 deliverable에 대한 구현 태스크 생성
   → 구현 산출물에 seam 포함 → AcceptanceGate가 실제로 돌 입구 확보
```
seam을 deliverable로 승격하지 않으면 INV-Q3 위반(검증 불가 제품 생산). **승격 로직은 Q-S4에서 두 경로 모두 배선**(§10 갱신).

---

## §8 완료계약 연결 — `prepare()`가 풍부해진 답을 소비

완료계약 §4.2의 생성 SSOT(`project_pipeline.prepare():1246`)는 현재 `acceptance_criteria`만 파싱한다. 이 설계 후:

```
prepare():1246
   acceptance_criteria  +  enriched["observable_goal"/"golden_example"/"test_seam"]
       ↓
   각 항목 → GoalEntry(description, harness_type, scenario, expected_output, provenance)
       - harness_type: golden_example/test_seam에서 LLM 분류 (cli/server/library/gui/none)
       - expected_output: golden_example의 기대출력
       - provenance: user | research | default
       ↓
   GoalContract(goals=[...], manifest=TestManifest(...))
```
`harness_type="gui"` + manual_only 항목 → `CANNOT_VERIFY`(완료계약 INV-C). 이로써 AcceptanceGate(S2)가 CANNOT_VERIFY 떡칠 대신 실제 VERIFIED를 찍는다.

---

## §9 HTML 리포트 (EvidenceLedger §7 → HTML 렌더러)

완료계약 §7의 JSON/텍스트 `evidence_ledger`를 입력으로 받는 **순수 렌더러**. 신규 로직 최소.

```
core/qa_report.py (신규):  render_html(evidence_ledger, run_dir) -> path
  섹션:
    [VERIFIED]      골별 command/exit_code/기대출력 비교 결과 + provenance 뱃지
    [FAILED]        골별 증거(실행 명령·실제출력·누락 키워드) + 로그 링크
    [CANNOT_VERIFY] 이유(장치/픽셀/manual_only)
    [UNVERIFIED]    검증법 미정
    [확인 요망]     provenance=research 가정 목록 — "리서치로 X를 정답이라 가정함. 맞나요?"
  산출: run 디렉터리에 자기완결 HTML 1파일 (외부 의존 없음)
```
- **provenance=research 골은 VERIFIED여도 [확인 요망]에 동시 표기**(INV-Q2/Q4) — 거짓 통과를 사람이 비동기로 잡는 안전망.
- HTML은 데이터·문자열 조작뿐 → blast radius 낮음(Tier 1~2).

---

## §10 구현 단계

| 단계 | 내용 | Tier / 검증 |
|---|---|---|
| **Q-S1** | `GoalEntry` 확장(scenario/expected_output/provenance) + `TestManifest` 신규 + `GoalContract.manifest` + 직렬화 round-trip 테스트 | Tier 2 (`completion_contract.py`, subprocess 없음) → af-critic + af-test-runner |
| **Q-S2** | (a) `QuestionRoute.RESEARCH_SYNTHESIZE` enum 추가(`verdicts.py:5-9`) + `question_router.route_batch()` 분기 (b) `goal_clarification.yaml` 4문항 추가 (c) `clarification.py` provenance 전파(`merge_clarification`) | Tier 2 → af-critic + af-test-runner |
| **Q-S3** | (사전 조사: research 실 API + 어댑터, §6.2) → `synthesize_via_research` + **경로 A·B·C 3곳 배선**(`interview.py:167`/`agent_launcher.py:533`/`stage_router.py:101-106`) | Tier 2~3 (research 엔진 호출) → 풀 3-Tier |
| **Q-S4** | seam → `deliverables` **명시 승격**(§7, 경로 A/B의 merge_clarification + 경로 C의 route_batch hook 둘 다) + `prepare():1246`가 골/기대출력 기준/manifest를 `GoalContract`로 흡수(§8) | Tier 3 (`project_pipeline.py`/`stage_router.py`) → 풀 3-Tier |
| **Q-S5** | `core/qa_report.py` HTML 렌더러(§9) — `evidence_ledger` 입력, provenance 뱃지 + [확인 요망] | Tier 1~2 → af-critic + af-test-runner |

> **선행 의존**: Q-S4의 `GoalContract` 흡수·AcceptanceGate 실행은 완료계약 **S2/S3 완료에 의존**한다. 이 설계의 Q-S1·Q-S2·Q-S5는 완료계약 S2와 **병렬 가능**(intake/구조/리포트는 게이트 실행과 독립).

---

## §11 불변식 + 테스트 요구사항

| ID | 내용 | 테스트 |
|---|---|---|
| INV-Q1 | 골/테스트 질문 스킵·FSA·빈 답 → `ResearchRouter` 합성 시도 (정적 기본값 금지). 합성 실패만 `default` | `test_skip_triggers_research`, `test_research_fail_falls_to_default` |
| INV-Q2 | 모든 골/기대출력 기준/seam에 `provenance` 표기, ledger·HTML까지 전파. `research`는 VERIFIED여도 [확인 요망] 동시 표기 | `test_provenance_propagates`, `test_research_verified_also_flagged` |
| INV-Q3 | `test_seam`/`seam_requirements` → `deliverables` 승격 → planner 태스크화 | `test_seam_becomes_deliverable` |
| INV-Q4 | 리서치 합성 기대출력 기준은 구현 전 동결(intake에서 GoalContract 고정), 구현 단계가 기대출력 기준을 못 바꿈 | `test_expected_output_frozen_before_implement` |
| INV-Q5 | 합성 못한 골(provenance=default + harness_type=none) → `verdict="UNVERIFIED"` → `is_done()==False` (완료계약 INV-F 정합) | `test_unsynthesized_goal_unverified` |

---

## §12 미결 / 의도적 제외

| 항목 | 결정 | 이유 |
|---|---|---|
| `ExecutionHarness`/`AcceptanceGate` 실행 내부 | **완료계약 2026-06-17 S2/S3** | 본 설계는 "무엇을/어떻게 먹이나"(머리)만. 실행기는 그 문서 |
| goal_failed 자동 수정 루프 (find→fix) | **완료계약 §6.4 후속 별도 메커니즘** | dogfood inv3 충돌 — 상위 재기동 + 신규 bound 필요. 본 설계 범위 밖 |
| 데스크톱 GUI 드라이버(pywinauto)·웹 Playwright | 보류 (별도 평가) | 신규 의존성·flaky. 본 설계는 seam+골든 비교까지. 픽셀은 CANNOT_VERIFY |
| 물리 장치(마이크/카메라) | CANNOT_VERIFY 명시 | seam(파일 주입)으로 우회 못 하는 잔여는 정직히 미검증 |
| research 합성 정확도 | provenance=research + async 확인으로 대응 | 합성 기대출력 기준 환각은 [확인 요망]으로 사람이 잡음 (INV-Q4) |

---

## §13 연결 지점

### §13.1 완료계약(2026-06-17)
- 이 설계 = 완료계약의 **머리**(intake 골/기대출력 기준/seam 공급). 완료계약 §10이 던진 "criteria 품질"·"정답 검증"을 정면으로 메움.
- `GoalEntry`는 완료계약 SSOT를 **확장**(재선언 금지, 타입 SSOT 규칙).

### §13.2 clarification/interview/research 서브시스템
- `clarification.py`/`interview.py` 확장(신규 질문 + 합성 라우트). `research_router`/`research_engine` **재사용**(신규 LLM 경로 금지).
- `merge_clarification`의 deliverables 매핑 채널을 seam 승격에 재사용(§7).

### §13.3 출력격리(`2026-06-18-product-output-isolation-design.md`) — **prerequisite**
- QA 산출물(HTML 리포트·seam 파일·시나리오)은 제품 workspace에 떨어진다. 그 workspace가 ad-hoc 경로에서 `os.getcwd()` 직하(=AF repo 오염 가능)로 결정되므로, **출력격리 설계가 선행 조건**이다 — 깨끗한 `<cwd>/<slug>/`가 있어야 QA 산출물도 정리된 위치에 쌓인다. §9 HTML 리포트의 `run_dir`은 그 격리된 workspace를 기준으로 한다.

### §13.4 메타-재귀 점검
- 산출물 = **AF가 사용자에게 만들어 주는 제품이 실제 작동·검증됨**. 내부 배관 추가가 아니라 제품 출력 품질 → product-value(NEXT_STEPS STREAM 정책의 안전한 쪽).

---

## §14 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-06-18 | Draft 작성 (Opus 4.8) — 완료계약 §10이 던진 criteria 품질·정답 검증 구멍을 intake 테스트 명료화 + 스킵→리서치 합성 + provenance 신뢰등급 + seam=구현요구 + HTML 리포트로 메우는 설계. 좌표 grep 확정(`interview.py:167`/`agent_launcher.py:533`/`clarification.py:178`/`goal_clarification.yaml`/`research_router.py:214`). |
| 2026-06-18 | af-cross-review **BLOCK 3건 반영 (Opus, 전건 grep 재확인)**: ① **#1** §6.2 `research_engine.run()`/`findings.field_for()` 미존재(실재는 `query_notebooklm`/`ResearchMode`/`classify_research_depth` + `ResearchRouter.plan()`만) → pseudo-code를 illustrative로 강등 + Q-S3 선행 "실 API 조사+어댑터" 명세, 어댑터 불가 시 스킵=UNVERIFIED로 축소 ② **#2** §6.1 intake 경로 누락 — `stage_router.py:101-106 _run_new_project`(goal_clarification을 route_batch로 독립 처리, `work_item_generator.py:1170-1171` 호출)이 3번째 경로 → 경로 C 추가, Q-S3을 3곳 배선으로 ③ **#3** §4 `default_route: research_synthesize`가 `QuestionRoute` enum(`verdicts.py:5-9` PASS/LLM_DELEGATE/HITL/BLOCK)에 부재 → Q-S2에 enum 추가+route_batch 분기 / §7 seam→deliverables가 "자동 같은 채널" 아님(yaml은 output_field 기반, merge_clarification은 category 기반) → 명시 승격 로직(경로 A/B+C 둘 다)으로 정정. Advisory(INV-Q4 동결 enforcement 메커니즘 미명시)는 Q-S1 구현 시 결정으로 보류. |
