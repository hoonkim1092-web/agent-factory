# Agent Factory — 전체 파이프라인 도식

> **목적**: 코드를 열지 않고 한 문서로 시스템 전체 흐름을 파악한다.
> **범위**: CLI 진입 → 파이프라인 → 에이전트 실행 → 자가검증/자가진화 → 안전장치까지 단계별 도식.
> **출처**: `Master_Blueprint.md` §1~§7 기반 (2026-04-27 시점).

---

## 0. 한 눈에 보는 단계 시퀀스

```
[STAGE 1] CLI 진입 분기
   ↓
[STAGE 2] Setup Gate (외부 도구 점검)
   ↓
[STAGE 3] 실행 모드 분기 (interactive | approval | fsa | ise | worker)
   ↓
[Phase 1] ProjectPipeline.prepare()  — 문서/계획 생성
   ↓
[승인 게이트] ApprovalGate.is_execution_open()
   ↓
[Phase 2] ProjectPipeline.execute()  — 멀티 에이전트 실행
   ↓
[자가검증] CrossVerificationLoop  — 실패 시 진입
   ↓
[자가진화] evolve_skill() + SkillEvolutionBus
   ↓
[Dashboard] dashboard.append_dashboard_run()
```

---

## 1. 5-레이어 시스템 아키텍처

```mermaid
flowchart TB
    L5["Layer 5 · 사용자 인터페이스<br/>run_factory_cli.py · interactive_chat.py"]
    L4["Layer 4 · 파이프라인 오케스트레이션<br/>project_pipeline.py · fsa_loop.py · ise_loop.py"]
    L3["Layer 3 · 멀티 에이전트 실행<br/>dynamic_orchestrator.py · agent_specializer.py"]
    L2["Layer 2 · 단일 에이전트 실행<br/>agent_runner.py · providers/cli.py · skill_loader.py"]
    L1["Layer 1 · 공유 인프라<br/>memory_system/ · message_broker.py · hooks/<br/>model_router.py · skill_evolution_bus.py"]

    L5 --> L4 --> L3 --> L2 --> L1
```

| 레이어 | 역할 | 핵심 파일 |
|-------|------|----------|
| 5 | CLI 진입·대화형 UX | `run_factory_cli.py`, `interactive_chat.py` |
| 4 | Phase1/Phase2 + FSA/ISE 루프 | `project_pipeline.py`, `fsa_loop.py`, `ise_loop.py` |
| 3 | 다중 역할 동시 실행 | `dynamic_orchestrator.py`, `agent_specializer.py` |
| 2 | CLI 프로바이더 호출 | `agent_runner.py`, `providers/cli.py` |
| 1 | 메모리·메시지·훅·라우팅 | `memory_system/`, `message_broker.py`, `hooks/` |

---

## 2. CLI 진입 단계 (STAGE 1 → 2 → 3)

```mermaid
flowchart TD
    A["사용자: af / run_factory_cli.py"] --> S1{"STAGE 1<br/>숨은 서브커맨드?"}
    S1 -- "setup / worker / skill-* / __nlm / preflight" --> X["즉시 분기<br/>(setup gate 우회)"]
    S1 -- "그 외" --> S2["STAGE 2<br/>_run_setup_gate()"]
    S2 --> S2a["ensure_external_research_capabilities()<br/>TAVILY · NotebookLM 인증·노트북 점검"]
    S2a -- "실패" --> W["stderr 경고만, 계속 진행"]
    S2a --> S3{"STAGE 3<br/>인자 분석"}
    W --> S3
    S3 -- "인자 없음" --> IM["interactive_chat.run_interactive()"]
    S3 -- "--mode approval" --> AM["ProjectPipeline.run()"]
    S3 -- "--mode fsa" --> FM["FSALoop.run_mission()"]
    S3 -- "--mode ise" --> IS["ISELoop (FSA 래퍼)"]
    S3 -- "worker 서브커맨드" --> WO["agent_worker.main()"]
```

| 모드 | 트리거 | 루프 |
|------|--------|------|
| Interactive | 인자 없음 | 사용자 입력 반복 |
| Approval | `--mode approval` | Phase1 → 승인 → Phase2 |
| FSA | `--mode fsa` | `FSALoop.run_mission()` 직접 호출 — Level 1~5 에스컬레이션, 최대 5 사이클 |
| ISE | `--mode ise` | `ISELoop` 호환 래퍼 (48줄) → 내부에서 `FSALoop.run_mission()` 위임. **현재 FSA와 동일 동작** |
| Worker | `worker` 서브커맨드 | 단일 태스크 (PyInstaller 전용) |

> **ISE 축소 이력 (2026-04-22, Phase A Step 1):** 기존 `ISELoop` 본체는 `FSALoop`이 Level 1~5 파이프라인을 완전히 구현하면서 dead code가 되어 48줄짜리 위임 래퍼로 축소됨 (`core/ise_loop.py`). API 호환성 유지를 위해 클래스만 남아 있으며, ISE 독자 차별화는 Phase B 이후로 미뤄짐.
>
> **호출 경로 차이:**
> - `--mode fsa` → 직접 `FSALoop` 사용
> - `--mode ise` → `ISELoop` 래퍼 경유 (단일 에이전트 경로 전용)
> - 프로젝트 파이프라인의 IMPL 실패 → `DynamicOrchestrator._execute_agent_task`가 `AF_ISE_ENABLED=1`(기본) 시 `FSALoop`에 위임 (ISELoop을 거치지 않음)

---

## 3. Project Pipeline — Phase 1 → 승인 → Phase 2

### 3.1 Phase 1: 문서·계획 생성

```mermaid
flowchart LR
    BR["사용자 brief"] --> PP["ProjectPipeline.prepare()"]
    PP --> PD["bootstrap_roles.<br/>ProjectPlanningDirector"]
    PD --> RB["generate_research_brief()<br/>→ project_brief.json"]
    PD --> RP["generate_role_plan()<br/>→ role_plan.json"]
    PD --> TB["generate_task_board()<br/>→ project_board_state.json"]
    PP --> IG["ingestion_pipeline.run()<br/>→ document_index (RAG)"]
    PP --> WI["work_item_generator.<br/>generate_work_items()<br/>→ docs/work-items/{slug}/*.md"]
    PP --> AG["approval_gate.initialize()<br/>execution_open: false"]
```

**산출물:**
- `project_brief.json` — 리서치 브리프
- `role_plan.json` — 역할 분담
- `project_board_state.json` — 태스크 보드
- `docs/work-items/{slug}/{4 docs}` — 작업 단위 4개 문서 세트
- `document_index` — RAG 검색 인덱스

### 3.2 ApprovalGate 상태 전환

```mermaid
stateDiagram-v2
    [*] --> Pending: initialize()<br/>execution_open=false<br/>status="pending"
    Pending --> Approved: approve()<br/>SHA256 스냅샷<br/>execution_open=true<br/>status="approved"
    Approved --> Pending: invalidate()<br/>(문서 수정 감지)
    Approved --> Executing: is_execution_open()=true<br/>(execution_open AND status==approved)
    Executing --> [*]
```

> `is_execution_open()` = `execution_open == true` **AND** `status == "approved"` (둘 다 충족 필수).
> `check_validity()`는 신규 문서 추가도 감지 (T3-7, 2026-04-27).

### 3.3 Phase 2: 멀티 에이전트 실행

```mermaid
flowchart TD
    EX["ProjectPipeline.execute()"] --> CK{"approval_gate.<br/>is_execution_open()?"}
    CK -- "false" --> ER["에러: 미승인"]
    CK -- "true" --> SY["work_item_parser.<br/>sync_board_from_work_items()"]
    SY --> DO["DynamicOrchestrator.run()"]
    DO --> NR["print_startup_routing_notice()"]
    DO --> MB["MessageBroker TCP 서버 시작"]
    DO --> LL["Lilith LLM 사이클 루프<br/>max_cycles=compute_max_cycles()"]
    LL --> LD["_lilith_decide_next()<br/>다음 태스크 선택"]
    LD --> SP["AgentSpecializer.specialize()"]
    SP --> RUN{"실행 모드"}
    RUN -- "frozen" --> FW["af.exe worker --task-file ..."]
    RUN -- "dev" --> PW["python core/agent_worker.py ..."]
    FW --> RES["result"]
    PW --> RES
    RES -- "ok=false" --> CV["_cross_verified_evaluate()"]
    CV --> EV["_try_evolve_from_patterns()"]
    EV --> LL
    RES -- "ok=true" --> NEXT{"미완료 태스크?"}
    NEXT -- "있음" --> LL
    NEXT -- "없음" --> DASH["dashboard.<br/>append_dashboard_run()"]
```

---

## 4. 단일 에이전트 실행 (Layer 2)

```mermaid
flowchart LR
    A["AgentRunner.run(agent, task, workspace)"] --> M["ModelRouter.<br/>pick_provider(agent)"]
    M --> P["preferred_provider"]
    A --> AC["all_cli_providers =<br/>get_requested_cli_providers()"]
    P --> CL["cli_providers =<br/>[preferred] + [fallbacks]"]
    AC --> CL
    CL --> IC["Inject Contracts<br/>① documentation_policy<br/>② destructive_guard<br/>③ implementation_language_policy"]
    IC --> SK["AdaptiveSkillLoader.load(task)<br/>(max 12 skills)"]
    SK --> H1["HookEventBus.run_pre_execute()"]
    H1 --> EX["providers/cli.<br/>execute_cli_chat()"]
    EX --> H2["HookEventBus.run_post_execute()"]
    H2 --> RT["return {ok, output, ...}"]
```

---

## 5. FSA 에스컬레이션 루프 (Level 1~5, 5사이클)

```mermaid
flowchart TD
    OE["DynamicOrchestrator.<br/>_execute_agent_task()"] --> R1["runner.run() → result"]
    R1 -- "ok=true" --> SUC["RETURN SUCCESS"]
    R1 -- "ok=false" --> FC["failure_classifier.<br/>classify_failure()"]
    FC -- "INFRA" --> BF["board=failed<br/>(no retry)"]
    FC -- "IMPL + AF_ISE_ENABLED=1" --> LM{"lineage_ledger.<br/>is_maxed()?"}
    LM -- "yes" --> DG["board=failed<br/>(lineage_maxed) + degrade"]
    LM -- "no" --> FL["FSALoop.run_mission()"]
    FL --> CY["For cycle in 1..5"]
    CY --> SD["StallDetector.check()"]
    SD --> GC["git.commit() / rollback()<br/>워크스페이스 스냅샷"]
    GC --> RR["runner.run() → result"]
    RR -- "ok=true" --> LS["lineage_ledger.<br/>on_success() → RETURN"]
    RR -- "ok=false" --> AN["ISEAnalyzer.<br/>analyze_failure()"]
    AN --> DE["_decide_escalation()<br/>Level 1~5 결정"]
    DE --> RA["ledger.record_attempt()"]
    RA --> LO["lineage_ledger.<br/>on_task_failure(level)"]
    LO --> ACT{"Level별 ACT"}
    ACT -- "L1" --> L1A["apply_retry_feedback()"]
    ACT -- "L2" --> L2A["apply_pivot()"]
    ACT -- "L3" --> L3A["redesign_task()"]
    ACT -- "L4" --> L4A["_try_evolve_failed_skill()<br/>+ redesign_task()"]
    ACT -- "L5" --> L5A["_decompose_and_execute()<br/>(서브태스크 분할)"]
    L1A --> CY
    L2A --> CY
    L3A --> CY
    L4A --> CY
    L5A --> CY
```

| Level | 액션 | 의미 |
|-------|------|------|
| L1 | retry feedback | 같은 접근 + 피드백 |
| L2 | pivot | 접근 방식 전환 |
| L3 | redesign | 태스크 재설계 |
| L4 | evolve skill + redesign | 스킬 진화 후 재설계 |
| L5 | decompose | 서브태스크 분할 |

---

## 6. 자가진화 루프 (Self-Evolution)

```mermaid
flowchart TD
    F["태스크 실패 감지"] --> CV["_cross_verified_evaluate()"]
    CV --> CVL["CrossVerificationLoop.run()"]
    CVL --> P1["병렬 실행 → 결과 수집"]
    CVL --> P2["순환 피어 리뷰"]
    CVL --> P3["Opus 판정<br/>→ failure_patterns 추출"]
    P3 --> EV["_try_evolve_from_patterns()"]
    EV --> MAP["패턴 키워드<br/>→ 스킬 이름 매핑"]
    MAP --> ES["evolve_skill(skill_dir, feedback)"]
    ES --> BAK[".bak 백업"]
    ES --> LM["LLM 개선 코드 생성"]
    ES --> QG["quick_guard() AST 검증"]
    ES --> RI["run_isolated() 샌드박스"]
    ES --> VB["version bump (0.x.y → 0.x.(y+1))"]
    VB --> SEB["SkillEvolutionBus.<br/>on_skill_evolved()<br/>→ 7단계 캐시 무효화"]
    SEB --> RT{"_task_retry_count >= 3?"}
    RT -- "yes" --> SK["SKIP (다음 태스크)"]
    RT -- "no" --> NC["다음 사이클에서 재실행"]
```

### 백그라운드 자동 품질 감사

| 훅 | 우선순위 | 트리거 | 작업 |
|----|---------|--------|------|
| `SkillSelfEvolutionHook` | 80 | 에이전트 10회 실행마다 | 품질<0.5 스킬 메타데이터 자동 개선 |
| `CodeReviewDocHook` | 85 | 실행 성공 후 | git diff → ControlPlaneLLM 리뷰 → `docs/code_review.md` append |

**스킬 품질 점수 공식 (최대 1.0):**
```
description(>10자)  +0.20
when_to_use         +0.20
keywords            +0.20
semantic_tags       +0.20
category(비기본값)   +0.10
when_NOT_to_use     +0.10
```

---

## 7. 에이전트 간 통신

```mermaid
flowchart LR
    subgraph TCP["TCP MessageBroker (DynamicOrchestrator 내부)"]
        MB["message_broker.py<br/>pub/sub · 동적 포트"]
    end
    subgraph FILE["File Mailbox (project_mailbox.py)"]
        IN["{workspace}/data/comm/messages.jsonl"]
    end

    A1["에이전트 A"] --> MB
    A2["에이전트 B"] --> MB
    MB --> A1
    MB --> A2

    A1 --> IN
    IN --> A2
```

**Mailbox 메시지 타입 (우선순위순):**

| 타입 | 우선순위 | 용도 |
|------|---------|------|
| `blocker` | 0 | 차단 이슈, 즉시 해결 필요 |
| `decision_request` | 1 | 결정 요청 |
| `review_request` | 2 | 검토 요청 |
| `handoff` | 3 | 작업 인계 |
| `result` | 6 | 완료 결과 |

---

## 8. 모델 라우팅

```mermaid
flowchart LR
    R["역할명 (role_name)"] --> IE["_infer_engine_id()"]
    IE --> EM["_ROLE_ENGINE_MAP"]
    EM --> EID["engine_id"]
    EID --> CP["_ROLE_CLI_PREFERENCE"]
    CP --> PL["[provider1, provider2, ...]"]
    PL --> IS["get_requested_cli_providers()<br/>교집합"]
    IS --> SEL["첫 번째 가용 프로바이더 선택"]
```

**엔진 매핑 (`_ROLE_ENGINE_MAP`):**

| 역할 키워드 | 엔진 |
|------------|------|
| qa, tester, quality, test_eng | `codex` |
| architect, design, blueprint | `architect_claude` |
| coder, developer, _dev, engineer | `coder_claude` |
| researcher, analyst, planner | `researcher_gemini` |
| writer, docs, document | `writer_claude` |

**프로바이더 우선순위 (`_ROLE_CLI_PREFERENCE`):**

| 엔진 | 우선순위 |
|------|----------|
| codex | codex_cli → claude_cli → gemini_cli |
| architect_claude | claude_cli → codex_cli → gemini_cli |
| coder_claude | claude_cli → codex_cli → gemini_cli |
| researcher_gemini | gemini_cli → claude_cli → codex_cli |

> 설치된 CLI가 1개면 모든 역할이 동일 프로바이더 사용 (startup notice 출력).

---

## 9. 안전장치 (5+1 레이어)

```mermaid
flowchart TB
    L1["Layer 1 · 정책 검증<br/>policy.yaml → 태스크 분해 규칙, 역할 수 제한"]
    L2["Layer 2 · 코드 정적 분석 (AST)<br/>security_guard.quick_guard()<br/>금지: os, sys, subprocess, shutil, importlib, eval, exec, __import__"]
    L3["Layer 3 · 격리 실행<br/>security_guard.run_isolated()<br/>서브프로세스 + 10초 타임아웃<br/>I/O: DATA_DIR, ARTIFACTS_DIR만"]
    L4["Layer 4 · 위험 명령 차단<br/>destructive_guard<br/>rm, del, git reset/clean/checkout"]
    L5["Layer 5 · 인간 승인 게이트<br/>ApprovalGate (SHA256)<br/>execution_open + status==approved"]
    L6["Layer 6 · 3-Tier Review-Gate<br/>af-test-runner → af-critic → af-cross-review"]

    L1 --> L2 --> L3 --> L4 --> L5 --> L6
```

### 9.1 Pre-commit 교차검증 게이트

```
git commit → .githooks/pre-commit
  ├─ Blueprint 스테이징 체크
  └─ scripts/pre_commit_review.py
       ├─ docs/reviews/ 에서 파일별 최신 리뷰 수집
       ├─ severity 집계 (Critical / High / Medium / Low)
       └─ 판정: PASS / WARN / BLOCK
```

**판정 기준:** `AF_PRE_COMMIT_REVIEW_BLOCK_ON=high` (기본) → High 1건 이상 차단.
**우회:** `AF_PRE_COMMIT_REVIEW=0` 또는 `git commit --no-verify`.

### 9.2 3-Tier Review-Gate

```mermaid
flowchart LR
    PY[".py 변경 커밋"] --> T1["Tier 1<br/>af-test-runner"]
    T1 --> T2["Tier 2<br/>af-critic"]
    T2 --> T3["Tier 3<br/>af-cross-review"]
    T3 --> CM["git commit 통과"]

    T1 -. "verdict=block/fail" .-> BLK["BLOCK"]
    T2 -. "verdict=block/fail" .-> BLK
    T3 -. "verdict=block/fail" .-> BLK
    PY -. "리뷰 후 재편집" .-> ST["BLOCK<br/>(stale-review)"]
```

**상태 파일:** `.af_review_queue/pending_agent_review.json`

**BLOCK 조건 (순서대로):**

| 조건 | reason |
|------|--------|
| `.py` 파일 없음 | `no-py-files` → PASS |
| tier 1 미완료 | `missing-tier-1` |
| tier 2 미완료 | `missing-tier-2` |
| tier 3 미완료 | `missing-tier-3` |
| 리뷰 완료 후 재편집 | `stale-review` |
| tier-3 snapshot에 없는 `.py` 신규 추가 | `new-files-added` |
| 어느 tier에서든 verdict=block/fail | `verdict-block:<agent>` |

**우회:**
- `AF_SKIP_REVIEW_GATE=1 git commit ...` (hook_events.log 기록)
- `AF_GATE_ALLOW_VERDICT_BLOCK=1` (verdict-block만 무시)
- `git commit --no-verify` (전체 우회)

---

## 10. Phase 4 — 에피소드 메모리 재사용

```mermaid
flowchart TD
    GW["generate_work_items()"] --> EH["_build_episode_hints_section()"]
    EH --> EN{"AF_MEMORY_REPLAY?"}
    EN -- "0 (off)" --> SK["skip"]
    EN -- "1 (on, 기본)" --> SS["_search_seed_episodes(<br/>brief_text, top_k=5)"]
    SS --> SC["memory/episodes/*.md 스캔<br/>(keyword_similarity)"]
    SC --> HE["힌트 추출"]
    HE --> FP["feature-plan.md<br/>+ 'Episode Hints' 섹션 주입"]

    PR["_pick_owner_role()"] --> SL["StrategyLedger.<br/>lookup_best_role()"]
    SL --> CK{"성공률 > 50%<br/>+ 샘플 ≥ 3건?"}
    CK -- "yes" --> LR["ledger role 반환"]
    CK -- "no" --> KW["키워드 폴백<br/>(keyword_map)"]
```

**`StrategyLedger` (memory/episodes/strategy_ledger.json):**

| 메서드 | 용도 |
|--------|------|
| `record_role_success/failure()` | 단건 기록 |
| `record_role_batch(entries)` | 다수 패턴 1회 _save() 일괄 기록 |
| `record_failure_pattern()` | 패턴 기록 |
| `can_auto_save()` | PASS ≥ 80% gate |
| `get_warnings_for(task)` | 경고 주입 |

---

## 11. 파이프라인 상태·산출물 위치

| 카테고리 | 경로 | 설명 |
|---------|------|------|
| 태스크 보드 | `data/projects/{slug}/project_board_state.json` | 현재 태스크 상태 |
| 작업 단위 | `docs/work-items/{slug}/*.md` | 4-문서 세트 |
| 에피소드 메모리 | `memory/episodes/*.md` | 과거 실행 학습 |
| 전략 원장 | `memory/episodes/strategy_ledger.json` | 역할·실패 패턴 누적 |
| Lineage 원장 | `lineage_ledger.json` | lineage 기반 Level 누적 (max=5) |
| 메시지 채널 | `{workspace}/data/comm/messages.jsonl` | 에이전트 mailbox |
| 대시보드 | `dashboard.json` | 실행 이력 |
| 리뷰 큐 | `.af_review_queue/pending_agent_review.json` | 3-Tier 게이트 상태 |
| Run Events | RunEventStore | T1-1 canonical 이벤트 |
| Run Budget | `core.run_budget.RunBudget` | 글로벌 토큰 예산 |

---

## 12. 종단 간 시퀀스 다이어그램 (Approval 모드)

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant CLI as run_factory_cli
    participant SG as setup_wizard
    participant PP as ProjectPipeline
    participant PD as PlanningDirector
    participant AG as ApprovalGate
    participant DO as DynamicOrchestrator
    participant AR as AgentRunner
    participant CV as CrossVerification
    participant SE as SkillEvolution
    participant DB as Dashboard

    U->>CLI: af --mode approval "brief"
    CLI->>SG: ensure_external_research_capabilities()
    SG-->>CLI: ok / 경고
    CLI->>PP: prepare(brief)
    PP->>PD: generate_research_brief / role_plan / task_board
    PD-->>PP: 산출물 3종
    PP->>AG: initialize() — execution_open=false
    PP-->>U: Phase 1 완료, 사용자 검토 대기
    U->>AG: approve() — SHA256 스냅샷
    AG-->>PP: status=approved
    U->>CLI: 재실행 / continue
    CLI->>PP: execute(prepared)
    PP->>AG: is_execution_open()
    AG-->>PP: true
    PP->>DO: run()
    loop Lilith 사이클
        DO->>DO: _lilith_decide_next()
        DO->>AR: run(agent, task)
        AR-->>DO: result
        alt result.ok=false
            DO->>CV: _cross_verified_evaluate()
            CV-->>DO: failure_patterns
            DO->>SE: _try_evolve_from_patterns()
            SE-->>DO: evolved skill
        end
    end
    DO-->>PP: 모든 태스크 완료
    PP->>DB: append_dashboard_run()
    PP-->>U: 결과 리턴
```

---

## 13. 환경 변수로 토글되는 단계

| 환경 변수 | 기본 | 효과 |
|-----------|------|------|
| `AF_ISE_ENABLED` | `1` | IMPL 실패 시 FSA 루프 활성화 |
| `AF_MEMORY_REPLAY` | `1` | 에피소드 힌트 주입 |
| `AF_PRE_COMMIT_REVIEW` | `1` | pre-commit 교차검증 게이트 |
| `AF_PRE_COMMIT_REVIEW_BLOCK_ON` | `high` | High 이상 severity 차단 |
| `AF_SKIP_REVIEW_GATE` | (unset) | `=1` 시 3-Tier Review-Gate 우회 |
| `AF_GATE_ALLOW_VERDICT_BLOCK` | (unset) | verdict-block만 무시 |

---

## 14. 더 깊이 파고들 때 참조할 위치

| 주제 | 참조 |
|------|------|
| 파일·클래스 빠른 조회 | `Master_Blueprint.md` §0 |
| 서브시스템 상세 | `Master_Blueprint.md` §3 |
| 자가진화 알고리즘 | `Master_Blueprint.md` §4 |
| 통신 프로토콜 | `Master_Blueprint.md` §5 |
| 모델·프로바이더 매핑 | `model_utils.py:1-845` |
| 안전장치 코드 | `core/security_guard.py`, `core/destructive_guard.py`, `core/approval_gate.py` |
| 의존성 영향 매트릭스 | `Master_Blueprint.md` §10 |
| 알려진 제약·이슈 | `Master_Blueprint.md` §11 |
| 변경 이력 | `Master_Blueprint.md` §12 |
