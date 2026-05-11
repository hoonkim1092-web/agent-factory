# Pipeline 순서 평가 + ASTEngine 연결 리뷰 (코덱스 논의용)

- 작성일: 2026-05-11
- 작성자: Claude Opus 4.7 세션 (`7691900e-3d22-4a26-a89c-4afeb0b9e804`)
- 목적: 코덱스와 함께 (a) 메인 파이프라인 순서의 최적성 검증, (b) ASTEngine 모듈군의 dead code 의혹 해소
- 후속: 본 문서에 대해 추후 `mcp__codex__codex` 1라운드 → `codex-reply` deliberation 권장
- 검증 상태: **본 문서는 분석 결과의 초안이며, 코덱스 cross-review 미실시**

---

## 0. 컨텍스트

Master_Blueprint.md §0~§12를 기반으로, "agent-factory의 200+ 코어 모듈이 어떤 순서로 실행되며, ASTEngine이 그 흐름에 정상 연결되어 있는가"를 점검한 세션의 결과물.

추적 도구: Grep / Read (소스 직접 읽기). 동작 검증(런타임 실행)은 미수행 — **정적 분석만 수행**했음을 코덱스에 명시 필요.

---

## 1. 파이프라인 실제 실행 순서

Approval 모드(가장 일반적인 경로) 기준. Master_Blueprint §2 Flow A + 코드 직접 추적으로 보강.

```
[부팅]
run_factory_cli.main()
  → STAGE 1: 숨은 서브커맨드 dispatch (해당 시 즉시 종료)
  → STAGE 2: setup_wizard.ensure_external_research_capabilities()
              (TAVILY/NotebookLM 점검, mode="auto")
  → STAGE 3: 모드 분기

[Phase 1 — ProjectPipeline.prepare]
ProjectPlanningDirector
  → generate_research_brief()
       └─ HimariResearchAgent + ResearchRouter + QualityContract(P4)
  → generate_role_plan()
  → generate_task_board()
ingestion_pipeline.run()                      # RAG 인덱싱
work_item_generator.generate_work_items()     # 3-stages 병렬
  ├─ Stage1 plan + EpisodeHints
  ├─ Stage2 spec/design (ThreadPoolExecutor)
  └─ Stage3 outline + tasks
  └─ Domain Spec Gate / ADR / Traceability (P2 C1+C3+C4)
  └─ 3-Tier Quality Gate (T1 Rubric → T2 critic → T3 cross/judge)
approval_gate.initialize()                    # execution_open=false

[사용자 검토·승인]                              # cliff edge

[Phase 2 — ProjectPipeline.execute]
approval_gate.read_block_decision()           # WarningRegistry escalation
approval_gate.is_execution_open()
work_item_parser.sync_board_from_work_items()
DynamicOrchestrator.run()
  while not exhausted:
    RunBudget.is_exhausted() 체크
    _dispatch_from_board()                    # rule-based, 0 토큰
    _needs_llm_intervention() → _lilith_intervene()
    AgentSpecializer.specialize()             # 페르소나+태스크+에피소드
    AgentRunner.run() / agent_worker
      → ModelRouter → CLI provider
      → AdaptiveSkillLoader (max 12)
      → 컨트랙트 주입 (doc/destructive/lang)
      → HookEventBus pre/post
    실패 시:
      failure_classifier (INFRA→종료 / IMPL→다음)
      [AF_ISE_ENABLED=1] FSALoop.run_mission()
        cycle 1..5: StallDetector → git snap → ISEAnalyzer
        L1 retry / L2 pivot / L3 redesign / L4 evolve / L5 decompose
      _cross_verified_evaluate() → CrossVerificationLoop
        병렬→피어리뷰→Opus 판정→failure_patterns
      _try_evolve_from_patterns() → evolve_skill
        → SkillEvolutionBus 7단계 캐시 무효화

[종료]
dashboard.append_dashboard_run()

[부수 — 백그라운드 항상 동작]
SkillSelfEvolutionHook  (10회마다)
CodeReviewDocHook       (실행 성공 후 git diff → docs append)

[부수 — git commit 시점 트리거]
.githooks/pre-commit
  → blueprint_updater (자동 sync)
  → pre_commit_review (docs/reviews/ 결과 확인)
review_gate
  → Tier1 af-test-runner
  → Tier2 af-critic
  → Tier3 af-cross-review (4-Round Deliberation)
```

---

## 2. 파이프라인 순서 논리적 평가

### 2.1 잘 설계된 결정 (8건)

| 순서 결정 | 근거 |
|---------|------|
| STAGE 1 → 2 → 3 (setup gate 진입 직전) | 외부 리서치 의존성을 Phase 1 시작 전에 확정 → Domain Spec Gate가 nlm/tavily 가용성을 가정 가능 |
| `research_brief → role_plan → task_board` | role 결정에 research가 선행, task 생성에 role이 선행 — 단방향 의존 |
| `ingestion_pipeline → work_item_generator` | work-item 생성 LLM이 RAG 컨텍스트를 사용 가능 |
| `Domain Spec Gate → work-item → 3-Tier Quality Gate` | spec이 work-item 입력, work-item이 게이트 입력 |
| Phase 1↔Phase 2 사이 ApprovalGate cliff | 인간 검토 지점을 강제하는 명시적 경계 |
| Phase 2 진입: `read_block_decision → is_execution_open → sync_board → run` | fail-fast, 비용 큰 orchestrator를 마지막에 |
| Orchestrator: `rule-based dispatch → LLM intervention 트리거 검사` | 0-토큰 경로 우선, LLM은 필요 시만 |
| 실패: `failure_classifier (INFRA 즉시 종료)` | quota/timeout으로 retry 낭비 차단 |

### 2.2 약점 4건 (코덱스 검증 요청)

#### 약점 1 — `FSALoop`와 `_cross_verified_evaluate` 발화 조건 모호

IMPL 실패 시 둘 다 trigger 가능한 분기. 코드 추적 결과 `AF_ISE_ENABLED=1`(기본)이면 `_execute_agent_task`가 FSA로 위임되고 cross-verification은 별도 경로에서도 호출됨.

**확인 필요**:
- 한 실패에 대해 양쪽이 동시에 발화하는 경로가 존재하는지
- 존재한다면 비용 폭증 → short-circuit 또는 명확한 우선순위 정책 필요
- 또는 FSA L4(`_try_evolve_failed_skill`)와 `_try_evolve_from_patterns`가 같은 파일을 evolve해 버리는 race 가능성

**관련 파일**: `core/dynamic_orchestrator.py:_execute_agent_task`, `core/fsa_loop.py:run_mission`, `core/cross_verification.py:CrossVerificationLoop.run`

#### 약점 2 — 3-Tier Review-Gate가 git commit 시점에만 발화

Phase 2 에이전트 산출물은 cross-verification(orchestrator 내부)만 통과하고, **3-Tier(test-runner+critic+cross-review)는 사람이 `git commit`을 명시적으로 칠 때만** 동작.

야간 자율 파이프라인에서 `nightly_tick`이 자동 commit해야 발화 — 진짜 "에이전트 산출물에 대한" 검증이 비동기·간접적임. 자율 모드에서 commit 없이 산출물만 누적되면 영원히 검증 안 됨.

**확인 필요**:
- nightly_tick이 commit을 강제하는지 (또는 commit 없이도 산출물 검증 경로가 있는지)
- 사람이 commit하지 않으면 검증이 무한 지연되는 시나리오의 실측 빈도

#### 약점 3 — STAGE 2 setup_wizard 매번 진입

모든 `af` 호출마다 nlm/tavily 점검 진입. `.af_setup_state.json` 캐시는 있지만 `_load_setup_state()` IO + filelock 획득 비용 발생.

Worker 서브커맨드처럼 자식 프로세스가 부모 wizard 결과를 재사용하지 않고 재진입 → graceful fail이라 안전하지만 부팅 지연 누적.

**확인 필요**:
- frozen exe 환경에서 worker 자식이 setup_wizard에 재진입하는지
- 재진입 시 락 경합으로 worker 시작이 지연되는 실측 사례

#### 약점 4 — ApprovalGate ↔ WarningRegistry escalation 의미 중복

Phase 2 진입 시 `read_block_decision()` (escalation)과 `is_execution_open()` (approval)이 둘 다 평가됨. 두 시스템이 독립적으로 진화하면서 차단 의미가 겹침.

§3.8에 P4a `current_phase` 단일 진실원으로 정리됐지만, 호출 순서 코드(`project_pipeline.execute`)는 두 게이트를 순차 호출. 어느 한쪽이 BLOCK이면 다른 쪽 평가는 무의미.

**확인 필요**:
- 두 게이트의 직교성(독립 결정 영역)이 보장되는지
- 합치거나 짧은 short-circuit으로 단순화 가능 여부

---

## 3. 파이프라인 순서대로 카테고리 재정렬 (28개 그룹)

```
═══════════════════════════════════════════════════════════════
[부팅 단계]
═══════════════════════════════════════════════════════════════
Cat A. CLI 진입점          (run_factory_cli.py)
Cat B. STAGE 1 분기         (숨은 서브커맨드 14종)
Cat C. STAGE 2 외부 리서치  (setup_wizard + nlm/tavily)
Cat D. STAGE 3 모드 라우팅  (interactive/approval/fsa/ise/worker)

═══════════════════════════════════════════════════════════════
[Phase 1 — 문서·계획 생성]
═══════════════════════════════════════════════════════════════
Cat E. 리서치 계층
       ├─ ResearchRouter (mode/gap 분류)
       ├─ HimariResearchAgent (web/local 수집)
       └─ QualityContract (P4 — pack overlay + ChecklistMerger)

Cat F. 부트스트랩 계획
       └─ ProjectPlanningDirector (brief → role_plan → task_board)

Cat G. RAG 인덱싱
       └─ IngestionPipeline + DocumentChunker + DocumentIndex + RetrievalRouter

Cat H. Work-Item 생성 v3.1 (3-stages 병렬)
       ├─ Stage1: plan + EpisodeHints (StrategyLedger top-k)
       ├─ Stage2: spec/design (ThreadPoolExecutor)
       ├─ Stage3: outline + tasks
       └─ requirement_llm (timeout 분리: google/openai/anthropic)

Cat I. Spec/ADR/Traceability 자동 생성 (P2 C1+C3+C4)
       └─ SpecGenerator + AdrGenerator + TraceabilityGenerator

Cat J. 3-Tier Quality Gate (문서)
       ├─ T1: RubricCompiler 구조 검사 + 1회 refine
       ├─ T2: DocumentReviewSession critic
       └─ T3: cross/judge (provider≥2)

Cat K. ApprovalGate 초기화 (execution_open=false)

═══════════════════════════════════════════════════════════════
[사용자 검토·승인 — cliff edge]
═══════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════
[Phase 2 — 실행]
═══════════════════════════════════════════════════════════════
Cat L. Escalation/Approval 차단 검사
       ├─ WarningRegistry.read_block_decision (P2 fail-closed)
       └─ ApprovalGate.is_execution_open

Cat M. Board 동기화
       └─ work_item_parser.sync_board_from_work_items

Cat N. DynamicOrchestrator (Event-Driven Sparse Governor)
       ├─ RunBudget 토큰 게이트
       ├─ rule-based dispatch (0 토큰)
       ├─ Lilith intervention trigger 감지
       │  └─ ControlPlaneLLM (CLI-first)
       ├─ MessageBroker TCP + ProjectMailbox JSONL
       └─ AstMemoryHub (★ 약식 — §4 참조)

Cat O. 단일 에이전트 실행
       ├─ AgentSpecializer (페르소나+태스크+에피소드 메모리)
       ├─ ModelRouter + provider_detect (3-state CLI 감지)
       ├─ AdaptiveSkillLoader (max 12, 점수 0.35×0.40×0.25)
       │  └─ SkillRegistry → Forge → EvolutionBus
       ├─ 컨트랙트 주입 (documentation/destructive_guard/language)
       ├─ HookEventBus pre/post (12 hooks)
       └─ providers/cli.execute_cli_chat

Cat P. 메모리 시스템 (실행 중 read/write)
       └─ UnifiedMemoryFacade (5 type × 4 scope × 7 adapter)

Cat Q. 실패 처리 (분기)
       ├─ failure_classifier → INFRA: 즉시 abort
       ├─ FSALoop (AF_ISE_ENABLED=1): L1~L5 × 5 cycle
       │  ├─ StallDetector / git snapshot
       │  ├─ ISEAnalyzer / _decide_escalation
       │  └─ LineageLedger / StrategyLedger
       └─ CrossVerificationLoop (or FSA L4 evolve)
          ├─ ThreadPoolExecutor 병렬
          ├─ 순환 피어 리뷰 A→B→C→A
          ├─ Opus 판정 (failure_patterns)
          └─ _try_evolve_from_patterns → SkillEvolutionBus 7단계 무효화

Cat R. 안전장치 (전체 layer 적용)
       ├─ AST quick_guard (스킬 코드만)
       ├─ run_isolated 격리 실행
       ├─ destructive_guard 명령 차단
       └─ security_guard / IntentGate

═══════════════════════════════════════════════════════════════
[종료 단계]
═══════════════════════════════════════════════════════════════
Cat S. dashboard.append_dashboard_run
Cat T. Continuity (manifest 저장 → 다음 세션 resume)
Cat U. Control 서브시스템 (supervisor/maintenance/rollback/run_ledger)

═══════════════════════════════════════════════════════════════
[병행 — 백그라운드 항상 동작]
═══════════════════════════════════════════════════════════════
Cat V. SkillSelfEvolutionHook (10회마다 bulk_enrich)
Cat W. CodeReviewDocHook (실행 성공 후 git diff → docs)

═══════════════════════════════════════════════════════════════
[병행 — 커밋 시점 발화]
═══════════════════════════════════════════════════════════════
Cat X. Blueprint 자동 sync (.githooks/pre-commit + blueprint_updater)
Cat Y. 3-Tier Review-Gate
       ├─ Tier 1: af-test-runner
       ├─ Tier 2: af-critic
       └─ Tier 3: af-cross-review (4-Round Deliberation)
Cat Z. pre_commit_review (docs/reviews/ 결과 확인)

═══════════════════════════════════════════════════════════════
[야간 자율 모드]
═══════════════════════════════════════════════════════════════
Cat AA. nightly_tick + nightly_summary + install_scheduler
Cat AB. NightlyState + state_snapshot.json + tick 재기동 복원
```

---

## 4. ASTEngine 연결 리뷰 — **상당 부분 dead code**

### 4.1 `core/ast_engine.py` (구조적 search/replace)

| 항목 | 결과 |
|------|------|
| 정의된 API | `search` / `replace` / `search_file` / `search_dir` / `replace_file` (5종) |
| Production 사용처 | **단 1곳** — `core/review_bundle.py:77` (`ast_engine.search_file`) |
| 호출 진입점 | `scripts/build_review_bundle.py:run(workspace)` 만 호출 |
| 핵심 파이프라인 사용 | **0건** — `dynamic_orchestrator`, `agent_runner`, `fsa_loop`, `agent_specializer`, `skill_creator`, `skill_forge` 어디서도 import 안 함 |
| 에이전트 코드 수정 도구 | **연결 없음** — 에이전트 CLI(claude/gemini/codex)가 자체 file-edit tool로 처리, ast_engine은 호출되지 않음 |

**결론**: `ast_engine`은 review bundle 생성 시 코드 패턴 매칭에만 쓰이는 보조 유틸. `ast_engine.py:5`의 doctring "에이전트가 코드를 *구조적*으로 이해하고 수정합니다"는 **현실과 불일치**.

검증 명령:
```bash
grep -rn "from core.ast_engine\|from core import ast_engine\|ast_engine\." \
  --include="*.py" core/ scripts/ run_factory_cli.py agent_launcher.py
# → core/review_bundle.py 와 자기 자신만 매칭
```

### 4.2 `core/ast_memory_hub.py` (AST pub/sub 메모리 허브)

dynamic_orchestrator에서 호출은 하지만 **3가지 결함**:

#### 결함 1 — filepath가 가짜 경로

`dynamic_orchestrator.py:782` 및 `:885`:
```python
await self.memory_hub.update_ast_state(
    filepath=f"Project_Scope_{role}",       # ← 실제 파일 경로 아님
    author_role=role,
    changes_summary=f"Completed subtask: {subtask[:50]}",
)
```
실제로 변경된 파일을 추적하지 않고 역할명만 키로 사용. AST 변경 추적이라는 모듈 목적과 무관한 free-text 로그로 변질.

#### 결함 2 — `parsed_ast_data` 항상 미전달 → MOCK 저장

`ast_memory_hub.py:100`:
```python
"ast_tree": parsed_ast_data or "AST_TREE_MOCK",   # ← 호출처에서 None만 전달
```
실제 AST 데이터가 한 번도 저장되지 않음. `get_file_ast()`가 반환하는 건 항상 mock string.

#### 결함 3 — `subscribe()` 호출자 0건

`publish("ast_updates", event)` (`ast_memory_hub.py:130`)는 호출되지만, **`subscribe()`를 호출하는 production 코드가 전혀 없음**. callback 리스트가 항상 비어있어 `publish`는 no-op. 즉 pub/sub 메커니즘 자체가 **dead**.

검증 명령:
```bash
grep -rn "memory_hub.subscribe\|hub.subscribe\|\.subscribe(" \
  --include="*.py" core/ scripts/
# → AstMemoryHub.subscribe 호출자: 0건
```

#### 유일하게 살아있는 경로

- `get_summary()` → `dynamic_orchestrator.py:391`에서 Lilith LLM 프롬프트의 "Global Context (Shared AST Memory)" 섹션에 free-text로 주입. 내용은 "Completed subtask: ..." 같은 자유 텍스트일 뿐 AST 정보 없음.

### 4.3 `core/memory_system/adapters/ast_hub.py` (UnifiedMemoryFacade 어댑터)

- AstMemoryHub singleton을 wrap하여 facade에 노출
- `initialise()`/`shutdown()`에서 `.system_generated/cache/ast_hub_snapshot.json` 영속화
- `read/write/search/list_recent` 정상 구현
- **다만 입력 데이터가 결함 1·2 때문에 mock string + 가짜 경로** → 영속화된 스냅샷도 의미 없음

### 4.4 종합 판정

| 모듈 | 상태 | 권장 조치 |
|------|------|---------|
| `ast_engine.py` | 보조 유틸 (review_bundle만) | 1) doctring을 실제 용도("review bundle용 패턴 매칭")로 교정. 2) 또는 `agent_runner` 컨트랙트에 ast_engine을 도구로 노출하여 의도된 활용 회복 |
| `ast_memory_hub.py` | 핵심 결함 3건, 사실상 dead | 1) filepath 실제 경로로 교체 (orchestrator가 git diff로 변경 파일 추출), 2) subscribe 호출처 추가 (예: agent_specializer가 다른 에이전트의 AST 변경 감지), 3) `parsed_ast_data` 실제 파싱 결과 전달 또는 필드 제거 |
| `adapters/ast_hub.py` | 입력 결함의 피해자 | hub 결함 수정 후 재평가 |

**Master_Blueprint와의 갭**: §0에서 `core/ast_engine.py`를 "AST 분석 엔진 (ast-grep-py wrapper)", `core/ast_memory_hub.py`를 "AST 기반 메모리 허브"로 명시했지만, 실제로는 (a) ast_engine은 review_bundle에서만, (b) ast_memory_hub는 mock 데이터로 free-text 로그를 저장. **Blueprint가 의도를 표현하고 코드는 실현하지 못한 케이스**.

---

## 5. 코덱스에게 묻고 싶은 것 (4개 질문)

### Q1. 약점 1 (FSA + cross-verification 중복 발화) 실측 확인

`AF_ISE_ENABLED=1` 환경에서 한 번의 IMPL 실패가 (a) `FSALoop.run_mission` 5사이클 + (b) `_cross_verified_evaluate` ThreadPoolExecutor 병렬 실행을 동시에 trigger하는 경로가 있는가? 코드 path traversal로 확인 부탁.

대상 코드:
- `core/dynamic_orchestrator.py:_execute_agent_task` (실패 분기)
- `core/fsa_loop.py:FSALoop.run_mission`
- `core/cross_verification.py:CrossVerificationLoop.run`

### Q2. 약점 2 (3-Tier Gate 발화 의존성) 자율 모드 실측

`scripts/nightly_tick.py`가 산출물 commit을 강제하는가? commit 없이 nightly가 진행되면 3-Tier Review-Gate가 영원히 발화하지 않는 시나리오가 있는가?

### Q3. ASTEngine dead code 판정 동의 여부

위 §4의 "ast_engine은 review_bundle 1곳, ast_memory_hub는 mock 데이터로 dead pub/sub" 판정에 동의하는가? 반례 사용처가 존재하면 제시 부탁.

특히 다음 중 어느 쪽이 옳은 처분인지 의견:
- (a) Master_Blueprint §0 설명을 현실에 맞게 축소(현재 코드 유지)
- (b) ASTEngine이 본래 의도대로 동작하도록 통합(orchestrator가 실제 git diff 기반 filepath + parsed AST 전달, agent_specializer가 subscribe)

### Q4. 카테고리 28개 분할의 적절성

§3의 28개 카테고리 분할이 실행 흐름을 정확히 반영하는가? 빠진 카테고리, 잘못 묶인 카테고리, 순서가 틀린 카테고리가 있는가?

---

## 6. 본 문서의 한계 (코덱스에 사전 고지)

- **정적 분석만 수행** — 실제 런타임 실행 검증(pytest/실 파이프라인 트리거) 없음
- 약점 1·2의 발화 빈도는 코드 path 추적 추정값. 실측 데이터 미수집
- ASTEngine 사용처 검색은 `*.py` 파일에 한정. C 확장/binary blob 사용처는 검사 안 됨 (사실상 없을 것이지만)
- Master_Blueprint v1.2.28 시점 기준. 이후 변경 미반영
