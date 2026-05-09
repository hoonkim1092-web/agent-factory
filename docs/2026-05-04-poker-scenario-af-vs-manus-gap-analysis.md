# AF vs Manus — 8인 네트워크 포커 게임 시나리오 산출물 격차 분석

> **목적**: 동일 프롬프트에 대해 AF와 Manus가 만든 결과의 격차를 코드 차원에서 진단하고, AF 파이프라인 개선 작업으로 이어가기 위한 핸드오프 문서.
> **세션 인계**: clear 후 다음 세션 cold-start용. self-contained.
> **작성**: 2026-05-04
> **연관 메모리**: `feedback_post_edit_checklist`, `project_3tier_cost_reduction_plan`
>
> ⚠️ **2026-05-04 후속 정정** (§7 참조): 본 문서 §3 ⑥ 표현 일부 + §4 ④(intent-routed 양식 분기) **폐기**. 진단축이 빗나감 — 사용자가 "시뮬레이션 해줘"라 입력한 건 AF 작동 테스트 메타 명령이었고 진짜 의도는 처음부터 끝까지 build. 격차의 본체는 **양식이 아니라 깊이·근거**. 정정된 처방은 §7 후속 합의 + 신규 통합 설계문서 `docs/2026-05-04-af-research-quality-gate-design.md` 참조.

---

## 0. 다음 세션 진입 시 — 어디서 시작할 것인가 (정정됨)

> ⚠️ 본 §0의 원래 권고(단기 ①·②·③ 직접 착수, 중기 ④ 양식 분기 설계)는 §7로 대체됨. 아래는 정정된 진입 순서.

1. 본 문서 §1·§2·§3을 읽어 격차 사실을 파악 (코드 매핑 라인번호 9건은 HEAD 정합 — cross-review 검증 완료).
2. 본 문서 **§7 후속 합의** + `docs/Minus/codex_my_의견.md`(codex 분석 원본) 함께 읽기.
3. 신규 통합 설계문서 작성: `docs/2026-05-04-af-research-quality-gate-design.md` (§7.4 진입 가이드 + §7.5 의사결정 D1~D9 기반).
4. 작성 완료 시 hook 큐 자동 발화 → af-cross-review 1회 (단일 설계문서, CLAUDE.md 규칙).
5. cross-review WARN 이하 verdict 시 P0(§7.3 단계 트리) 착수.

**주의**: 원래 §4 ④(intent-routed 산출 양식 분기) 처방은 §7.1에서 폐기. 이유: 사용자 의도 = build, 격차의 본체 = evidence depth + 도메인 명세 강제 부재. 양식 분기는 본 격차와 무관.

---

## 1. 사용자 원본 요청 (그대로 보존)

```
실제 af 사용시 8인 네트워크 플레이 포커게임 만들어줘에 대한 실제 작동 시나리오를
시뮬레이션 해서 알려줘

목표 : 8인 네트워크 플레이 포커게임 만들기

최근 공신력 있는 세계 포커게임을 기반으로 규칙을 만들고, 초기 자산, 배팅룰, 배팅 금액 룰을 적용해
게임 로직 판단은 서버에서 하고, 클라이언트는 뷰어 역할만 한다,
클라이언트는 html5 개발하고, 앱웹 방식으로 모바일 피시 태블릿에서 작동하도록 개발한다.
```

핵심 요구 6가지:
1. **8인** 네트워크 플레이
2. **공신력 있는 세계 표준 룰** (= WSOP / Poker TDA 같은 권위 출처)
3. 초기 자산, 배팅룰, 배팅 금액 룰
4. **권위 서버** 모델 (서버에서 로직, 클라이언트는 뷰어)
5. **HTML5 + 앱웹** 방식
6. **모바일 / PC / 태블릿** 반응형
7. (메타) **시뮬레이션** 형태로 받고 싶음 (시퀀스/메시지 흐름)

---

## 2. 두 산출물 위치 + 비교

| 항목 | Manus 산출 | AF 산출 |
|---|---|---|
| 파일 | `docs/Minus/8인 네트워크 플레이 포커 게임 — 실제 작동 시나리오 시뮬레이션.md` | `docs/work-items/implement-a-browser-poker-game/plan.md` |
| 양식 | 단일 narrative 시뮬레이션 문서 (6 phase) | feature-plan.md 보일러플레이트 1개 (4-doc 세트 중 일부) |
| 사용자 원본 보존 | 그대로 | "implement a browser poker game"로 축약 |
| 인원수(8명) | 좌석/포지션 명시(P1~P8) | 누락 |
| 네트워크/서버권위 | 핵심 설계 원칙으로 채택 | **Non-Goals로 강등** |
| HTML5/앱웹/반응형 | 반응형 설계 표 포함 | 누락 |
| 룰 출처 | WSOP / Poker TDA 2024 / Bicycle / Upswing (4건) | "Poker rules" 한 줄, URL 0 |
| 포커 족보·블라인드·배팅룰 | 표로 명시 | 0건 |
| 6 phase 시뮬레이션 + JSON 메시지 | 있음 | 0건 |
| Tech Stack | Node.js + WebSocket(Socket.io) + Redis + Postgres + Canvas | "vanilla JS"만 |
| 즉시 개발 가능성 | 가능 | 불가 (요구의 절반 누락) |
| 작성 시간 | 약 5분 | 다회 라운드, 자체 점수 0.32~0.46 (메모리 기록) |

---

## 3. 6가지 구조적 원인 (코드 위치 명시)

### ① 사용자 원본 → "goal 한 줄" 강제 압축
- `core/researcher.py:919` `research_project_brief()`의 출력 스키마: `"goal": "single sentence describing what to build"`
- 이후 모든 다운스트림은 이 한 줄만 본다. `core/work_item_generator.py:528` `_generate_feature_plan()`도 `project_brief.get("goal")`만 prompt에 주입.
- 메모리 키도 이미 영문 한 줄로 normalizing (`original_request_build_a_poker_game_goal_implement_a_browser_poker_game_constraints_network_allowed`).
- `original_request` 전문은 `core/plan_verifier.py:200` 한 곳만 보존 — plan/spec/design/tasks 생성 prompt엔 흐르지 않음.

### ② 산출 형식이 사용자 의도와 무관하게 고정
- `core/work_item_generator.py`의 4개 생성기 함수가 만드는 것은 **항상**:
  - feature-plan.md (Background/Problem/Goals/Non-Goals/Scope/Stakeholders/Metrics/Risks/Evidence/Refs)
  - feature-spec.md
  - implementation-design.md
  - implementation-tasks.md
- 사용자가 "**시뮬레이션**"을 요청해도 이 4종 PM 보일러플레이트만 나옴.
- 시퀀스 시뮬레이션 / JSON 메시지 / 좌석 배치 / 라운드 흐름이 들어갈 자리가 양식에 없음.
- AF 어디에도 "시뮬레이션 문서" 양식 정의가 없음.

### ③ Goals/Non-Goals 추출이 사용자 핵심 요구를 매장
- AF plan.md의 Non-Goals: "**서버 사이드 멀티플레이어 네트워킹** (실시간 소켓 기반 대전)"
- 사용자 원본: "게임 로직 판단은 **서버에서** 하고 클라이언트는 뷰어"
- LLM이 압축된 goal "browser poker game"만 보고 single-player로 추측 → **요구사항 역전(inversion)**
- 즉 **사용자 핵심 요구가 비-Goal로 강등**되는 사고가 구조적으로 가능한 파이프라인.

### ④ Local references 노이즈가 brief를 오염
- `core/researcher.py:258` `_collect_local_references()`가 IngestionPipeline으로 워크스페이스 전체를 BM25 검색해 top-k.
- 결과로 `docs/architecture.md`(AF 자체 아키텍처 문서) 같은 무관 문서가 evidence에 박혀 plan.md References에 그대로 인용.
- 도메인 매칭 필터 부재 → "이게 왜 포커 게임 자료지?" 자기참조 노이즈.

### ⑤ 도메인 권위 1차 출처 강제 부재
- Tavily 키 없으면 web 0건, "LLM prior knowledge" fallback (`core/researcher.py:579`).
- 키 있어도 단순 top-4 + 260자 발췌. **공식 룰북(WSOP, TDA) 우선순위 없음**.
- Manus는 1차 도메인 권위에서 시작. AF는 임의 검색 결과 발췌만 봄.
- 결과: plan.md References가 "Poker rules — verify state transitions" 한 줄 placeholder.

### ⑥ fast_synthesis 모드 — 깊이 vs 속도 트레이드오프 잘못 고름
- `core/researcher.py:940` `mode = "fast_synthesis"`. evidence 수집 → 단 1회 LLM 호출로 brief 합성.
- Manus 흐름은 다단계로 보임("규칙 조사 → 시스템 요구 정리 → 시뮬레이션 → 메시지 포맷").
- AF는 "한 방"으로 끝내려다 깊이 상실. **시뮬레이션·아키텍처 요청은 multi-step chain이 필수**인데 그 mode가 없음.

부수: assistant_score 메모리에 0.32~0.46 점수가 반복 저장. **AF가 자기 산출물을 낮게 평가하면서도 같은 양식으로 재생산만 반복** — 평가 결과가 양식 변경으로 피드백되지 않는 churn loop.

---

## 4. 권고 — 무엇을 해야 하는가

### 단기 (이번 주, 큰 효과, 1-2일)

1. **`original_request` 전문 보존 + 모든 doc-gen prompt에 주입**
   - 위치: `core/work_item_generator.py:528 (_generate_feature_plan), :568 (_generate_feature_spec), :605 (_generate_implementation_design), :642 (_generate_implementation_tasks)`
   - 변경: 각 prompt에 `## Original User Request (verbatim)\n{original_request}\n` 섹션 추가
   - `project_brief`에 `original_request` 필드 신설 → researcher가 task_input 그대로 보존 → generator 4종이 prompt에 주입

2. **Goals/Non-Goals 자동 추출 시 "사용자 명시" vs "AI 추론" 분리**
   - 위치: `core/researcher.py:919` `research_project_brief()` 출력 스키마
   - 변경: `goals` → `{"explicit": [...], "inferred": [...]}` 구조. `non_goals`도 동일.
   - **추론 항목을 Non-Goal로 옮기는 것을 금지**(원본에 명시되지 않은 한)
   - 다운스트림: plan.md Non-Goals 섹션은 `explicit_non_goals`만 포함

3. **Local references 도메인 매칭 가드**
   - 위치: `core/researcher.py:258` `_collect_local_references()`
   - 변경: task_input의 도메인 키워드(simple noun extraction 또는 stopword 제거 후 token 집합)가 ref의 excerpt/heading에 1개도 없으면 evidence에서 제외
   - 또는 score 임계값 (≥ 0.35) 강화 + `_is_sufficient` 기준 강화

### 중기 (다음 sprint, 본질적 해결)

4. **요청 의도(intent) 분류 → 산출 양식 분기** ⭐ **본질 해결책**
   - 신규 파이프라인: `core/intent_classifier.py` (또는 기존 `core/intent.py` 확장)
   - 분기:
     - `build` ("구현해줘", "코드 만들어줘") → 현재 work-item 4-doc set
     - `simulate` / `walkthrough` ("시뮬레이션", "시나리오", "동작 흐름") → 단일 narrative 시뮬레이션 문서
     - `analyze` ("분석", "비교") → 분석 보고서
     - `architect` ("아키텍처", "설계") → architecture.md 단일 문서
   - 각 양식별 generator + prompt template을 `core/document_templates/` 같은 곳에 분리
   - 현재 구조 = 망치 하나 / 모든 것을 못으로 본다

5. **도메인 권위 1차 출처 우선 검색**
   - 위치: `core/researcher.py:311` `_collect_web_references()`
   - 변경: query에 "official rules" / "specification" / "standard" boost. 1차 출처 도메인 화이트리스트(`*.wsop.com`, `*.pokertda.com`, `*.w3.org`, `*.ietf.org` 등)를 만들고 score 가중.
   - 룰/표준 도메인 task에는 1차 출처 ≥ 1건 강제

6. **multi-step research mode 추가 (`deep_synthesis`)**
   - 위치: `core/research_router.py` (이미 라우팅 모듈 존재)
   - 변경: 시뮬레이션·아키텍처 intent에는 `mode = "deep_synthesis"`로 라우팅
   - 단계: domain_rules → architecture → state_machine → message_protocol → walkthrough — 각 단계 별도 LLM 호출
   - 비용 ↑이지만 결과 품질 격차가 본질적

### 근본 (Phase 2~)

7. **양식 라이브러리화** — work-item 4-doc은 "여러 산출 양식 중 하나"로 강등. simulation.md, runbook.md, architecture.md, comparison.md 등 양식을 라이브러리로.
8. **자기참조 evidence 차단 + 평가 점수 → 양식 변경 피드백** — 점수 낮으면 같은 양식으로 재생성하지 말고 양식 자체를 후보에서 다시 고르게 (intent classifier rerouting).

---

## 5. 한 줄 요약

**격차의 80%는 모델이 아니라 양식·라우팅·압축 단계의 설계에서 온다. AF는 "AF가 만들 수 있는 형태의 문서"를 만들고, Manus는 "사용자가 원하는 형태의 문서"를 만든다.**

---

## 6. 다음 세션 액션 체크리스트

> ⚠️ 본 §6의 체크리스트는 §7.1 정정으로 대체됨. 차기 세션은 §7.4 진입 가이드를 따를 것.

- [ ] ~~이 문서 §0·§3·§4 읽기~~ → §1~§3 + §7 읽기
- [ ] ~~단기 ①: `original_request` 전문 주입~~ → §7.3 P0 A1로 흡수 (researcher.py:919 schema만 수정, 작업량 1/5 축소)
- [ ] ~~단기 ②: Goals/Non-Goals explicit/inferred 분리~~ → 폐기 (P1 ResearchFirstPlanner가 흡수)
- [ ] ~~단기 ③: Local refs 도메인 매칭 가드~~ → §7.3 P0 A2로 유지
- [ ] ~~중기 ④ 설계문서 작성: intent-routed-output-formats~~ → 폐기. 대신 통합 설계문서 `docs/2026-05-04-af-research-quality-gate-design.md`
- [ ] (검증) 동일 build prompt 재실행 → §2 비교표 9차원 중 ≥ 7개 Manus 동등 이상 (정량 기준)

---

## 7. 후속 합의 — 2026-05-04 13:00 KST 세션 (clear 직전 정정)

### 7.1 진단 정정 — §3 ⑥ 표현 + §4 ④ 폐기 사유

**§4 ④ (intent-routed 산출 양식 분기) 폐기**:
- 사용자가 "시뮬레이션 해서 알려줘"라 입력한 건 AF 정상 작동 테스트 메타 명령이었음.
- 진짜 사용자 의도는 처음부터 끝까지 **build** ("8인 네트워크 포커게임 만들기").
- 빌드 배포본에 build prompt 직접 입력 시에도 동일한 4-doc 보일러플레이트 산출 → 양식 분기 무관.
- 격차의 본체는 **양식이 아니라 깊이·근거** (build intent 안에서 evidence depth, 도메인 명세 강제, 권위 출처 우선의 부재).

**§3 ⑥ 표현 완화**: fast_synthesis는 일반 build intent의 비용 최적화 default로 적합. 결함 묘사는 부정확. 단지 룰/명세 검증형 프로젝트에서는 깊이 부족 — 이는 fast_synthesis 자체가 아닌 sufficiency gate / RecoverySearchLoop 부재의 문제.

### 7.2 codex 의견 통합 — `docs/Minus/codex_my_의견.md`

codex 분석이 정합. 내가 처음 "과장"이라 라벨한 3개 ("5개 신규 모듈 신설" 뉘앙스 / "prepare() 앞단에 다 넣어라" / "10가지 강제 질문 포커 특화")는 모두 내 오독 — codex는 일관되게 "배선 강도" + "Gate를 넣어라"라 했지 신규 클래스 5개 신설을 명시하지 않음. 균형 인상을 위해 어줍짢은 흠을 끼운 역방향 sycophancy로 정정.

**Explore 에이전트 코드 grep 결과 (검증 완료)**:

| codex 컴포넌트 | AF 현재 | 코드 위치 | 강도 |
|---|---|---|---|
| ResearchFirstPlanner | 부분 구현 | `core/research_router.py:194 plan()` | soft (mode 분류만, requires_research flag 없음) |
| EvidenceMatrix | 부분 구현 | `core/researcher.py:672 collect_project_evidence()` + source_pack | soft (claim↔source 매핑 아닌 reference list) |
| CoverageGate | 부분 구현 | `core/researcher.py:550 _is_sufficient()` | soft (ref≥3 / score≥0.25 하드코드, 도메인 매니페스트 부재) |
| RecoverySearchLoop | **부재** | (1회 escalation만) | 부재 (loop 아님) |
| SpecBeforeTasks | **부재** | `core/project_pipeline.py:741 prepare_documents()` | 부재 (brief→role_plan→task_board→work_items 직행) |
| 권위 출처 우선 | **부재** | `core/researcher.py:311 _collect_web_references()` | 부재 (Tavily top-k만, trust_score 없음) |

→ 신규 모듈 ≤ 2개 + 기존 함수 강화 4-5개로 codex 비전 80% 달성 가능. 단일 거대 모듈 신설 불필요.

**의외의 발견**: `_generate_feature_plan/spec/design/tasks` 4 generator는 `json.dumps(project_brief)` 전체를 prompt에 넣음 (`work_item_generator.py:535/573/610/650`). brief에 `original_request` 필드만 추가하면 자동 흐름. 4 generator 함수 수정 불필요.

### 7.3 정정된 단계 트리 (P0~P3) — codex 산출물 5종 통합

```
P0 — 즉시 (1-2일, 신규 모듈 0, 후방 호환)
  A1.  researcher.py:919 schema에 original_request 필드 추가
  A2.  researcher.py:258 _collect_local_references() 도메인 매칭 가드
  A3.  researcher.py:311 _collect_web_references() trust_score + poker 화이트리스트
       (wsop.com / pokertda.com / pokerstars.com / upswingpoker.com)
  A4.  researcher.py:550 _is_sufficient() domain_checklist 옵션 매개변수 (None 시 기존 동작 유지)
  A5.  research_router.py:194 plan() 반환에 requires_research / domain / depth flag
  A6.  ★ project_brief.json 파일 저장 명시
       위치: docs/research/<slug>-project-brief.json

P1 — Quality Gate + Evidence (3-5일)
  B1.  collect_project_evidence() 안에 unmet_gaps 루프 (max_rounds=3)
  B2.  config/coverage_manifests/poker.yaml 신규 (8 항목)
       required_fields: [hand_ranking, blind_structure, betting_rules,
                         side_pot, all_in, showdown,
                         server_authoritative_events, client_hidden_state]
  B3.  research_router.plan() domain 라벨 → 매니페스트 selector
  B4.  ★ research_evidence.json 강화 — claim↔source structured 매핑
       구조: {claim, source_id, authority(primary/secondary/tertiary), confidence, applies_to}
       위치: docs/research/<slug>-evidence.json
  B5.  ★ coverage-report 자동 생성 — 매니페스트 vs evidence 비교
       위치: docs/research/<slug>-coverage.md + .json

P2 — Spec Before Tasks (5-7일, 신규 모듈 1: spec_generator)
  C1.  project_pipeline.py prepare_documents() L798/L810 사이 _verify_domain_spec() 게이트
  C2.  core/spec_generator.py 신규 — 5종 도메인 명세 generator
       (rules-spec / state-machine / server-architecture / event-protocol / client-view)
       위치: docs/specs/<slug>-*.md
  C3.  ★ decision-record (ADR) 자동 생성 — 룰 베이스 선택 시점
       양식: {decision, alternatives_considered, rationale, evidence_refs[]}
       위치: docs/decisions/<slug>-rule-baseline.md
  C4.  ★ traceability 자동 생성 — claim_id → source_id → spec_section → task_id 4단 매핑
       위치: docs/research/<slug>-traceability.md (MD 표 1개)

P3 — 평가 (1-2주)
  D1.  포커 build prompt 재실행 → §2 비교표 9차원 중 ≥ 7 Manus 동등
  D2.  traceability에서 plan.md References → spec → task 추적 가능 검증
  D3.  assistant_score 0.32~0.46 → ≥ 0.7 회복
```

### 7.4 차기 세션 진입 가이드 (cold-start)

**다음 세션이 해야 할 일** (이 순서대로):

1. `git pull --ff-only` + `python start_db.py agent-factory`
2. 본 문서 §1·§2·§3 + §7 읽기
3. `docs/Minus/codex_my_의견.md` 읽기 (codex 원본)
4. **신규 통합 설계문서 작성** — Opus 모델 권장 (설계 단계, 메모리 `feedback_model_per_phase`):
   - 파일: `docs/2026-05-04-af-research-quality-gate-design.md`
   - 구조:
     ```
     §0  다음 세션 진입 가이드 (cold-start용)
     §1  배경 — Manus 격차 + codex 의견 통합 + ④ 폐기 사유
     §2  AF 코드 매핑 (§7.2 표 흡수)
     §3  목표 (정량) — §2 비교표 9차원 ≥ 7, 매니페스트 8 항목 matched, score ≥ 0.7
     §4  비목표 — intent-routed 양식 분기, 100% 자동화, 다수 도메인 매니페스트
     §5  단계 트리 (P0~P3) — §7.3 흡수 + 각 항목 코드 스케치 + 검증 기준
     §6  산출물 5종 schema (project_brief.json / evidence.json / coverage / decision / traceability)
     §7  poker.yaml 매니페스트 설계 (8 필수 항목 정의)
     §8  의사결정 D1~D9 + 근거 (§7.5 흡수)
     §9  위험 + 완화 (RecoverySearchLoop 무한 루프, LLM 비용 폭증, 매니페스트 confused matching)
     §10 일정 + 의존성 그래프 (P0 → P1 → P2 → P3 직렬)
     §11 cold-start 진입 체크리스트
     ```
5. 작성 완료 후 hook 큐 자동 발화 → **af-cross-review 1회**만 실행 (단일 설계문서 규칙, CLAUDE.md)
6. cross-review WARN 이하 verdict → P0 착수 (Sonnet 모델 권장, 메모리 `feedback_model_per_phase`)
7. P0 완료 후 동일 포커 build prompt 재실행 → docs/research/<slug>-project-brief.json 파일 존재 + original_request 전문 포함 검증

**참고**: codex 회복 시점 2026-05-05 15:37 KST↑. 그 이전에 작성하면 fan-out 0 (Claude 단독 검증). 가능하면 codex 회복 후 작성해서 fan-out 검증을 받는 게 안전.

### 7.5 의사결정 D1~D9 — 사용자 합의 완료 (설계문서 §8에 흡수)

| ID | 결정 | 근거 |
|----|------|------|
| D1 | P0에 A4 (`_is_sufficient` domain_checklist 매개변수) 포함 | 1줄 추가, 후방 호환, P1 매니페스트 토대 |
| D2 | 매니페스트 = YAML 외부 파일 (`config/coverage_manifests/<domain>.yaml`) | 도메인 추가 시 코드 수정 0 |
| D3 | Spec/Evidence 산출물 git 추적 | References에서 ID 인용, 사용자 검증 가능 |
| D4 | 첫 매니페스트 = poker 1개만 | Karpathy "Simplicity First". 두 번째 매니페스트는 두 번째 케이스 발생 시 |
| D5 | EvidenceMatrix structured 매핑 → P1 B4로 끌어올림 | research_evidence.json 강화 결정과 동일 작업, 분리 무의미 |
| D6 | 본 gap-analysis 문서 처리 = **Supersede** (in-place 정정 X) | 진단 변천사 = 학습 자산. 헤더와 §7로 정정 사유 흡수 |
| D7 | 통합 설계문서 = **단일 문서** (P0~P3 합본) | phase 간 의존성 직렬·강함 — 분할 시 cross-review가 phase 정합성 못 보고 BLOCK 빈발 |
| D8 | docs/decisions/ 디렉토리 신설 | ADR 저장 위치, 기존 docs/specs/와 분리 (의도 명확) |
| D9 | traceability 양식 = **MD 표 1개** | JSON은 evidence.json이 이미 가짐, 중복 회피 |

### 7.6 codex 회복 후 검증 권고

본 §7 정정과 §7.3 단계 트리는 **Claude 단독 분석 + 1회 af-cross-review (Claude 단독, fan-out 0)**로 검증됨. codex/gemini 회복 후 (2026-05-05 15:37 KST↑) 신규 설계문서에 fan-out 포함 cross-review 1회 추가 권장. 본 문서 §7 자체는 추가 검증 불필요 (gap-analysis 정정 메타 기록).
