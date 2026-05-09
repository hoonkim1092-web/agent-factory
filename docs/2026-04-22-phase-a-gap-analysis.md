# Phase A 요구사항서 (정식) — 교차 검증 Gap 분석 기반

<!-- version: 1.1.0 | date: 2026-04-22 | author: Claude Haiku 4.5 + Codex (cross-review) -->
<!-- status: AUTHORITATIVE (Phase A 실행 기준 문서) -->
<!-- base: docs/archive/2026-04-17-AF_Phase_A_Requirements.md (Opus 4.6, 역사 참조용) -->
<!-- decisions: docs/archive/resolved/2026-04-22-phase-a-decisions-required.md (Q1~Q3 확정: 2026-04-22) -->
<!-- commit_at_writing: 486041ca (origin/2026-04-14-build-diet) -->

## 0. 개요

> **승격 고지 (2026-04-22)**: 이 문서는 원문(`docs/archive/2026-04-17-AF_Phase_A_Requirements.md`)의 사실 오류(ISE dead code 주장 등)를 교차 검증으로 보정한 결과물이며, Phase A 실행의 **정식 요구사항서**로 승격됐다(Q3 결정: (c)). 원문은 히스토리 자료로 `docs/archive/`에 보관한다.
>
> **채택된 우선순위 (Q2 결정)**: **ISE → COMPACT → EVOLUTION → MEMORY** (Codex 안). 근거는 §4 참조.

이 문서는 `AF_Phase_A_Requirements.md`(2026-04-17 Opus 4.6 작성, 631줄)와 현재 코드(`486041ca`, `2026-04-14-build-diet`) 사이의 실제 괴리를 실증 기반으로 확정한 결과물이다. 조사는 다음 단계로 수행했다.

1. Claude 4개 Explore 에이전트 병렬 탐색 (4개 요구영역: COMPACT/ISE/EVOLUTION/MEMORY)
2. Codex 독립 자율 리뷰(`af-cross-review`)로 **32개 주장 전량 교차 검증**
3. DISPUTED·REFINED 판정 항목 재확인 및 신규 이슈 추가 발굴

**결론 요약**: 문서는 2026-04-17 기준으로 작성됐으나 코드는 그보다 먼저 상당 부분 구현이 완료된 상태다. 문서의 미구현 주장 중 다수가 **이미 구현됨**으로 판정됐고, 대신 문서가 짚지 못한 Critical 배선 단절이 발견됐다.

---

## 1. 판정 요약 (32개 주장 전량)

| 분류 | 개수 | 비고 |
|---|---|---|
| VERIFIED (라인 정확) | 22 | 주장이 근거 라인까지 일치 |
| VERIFIED (라인 드리프트 ±20) | 7 | 기능은 맞으나 라인 번호 미세 차이 (CRLF/LF·버전 차이 추정) |
| DISPUTED | 2 | Claude 사실 오류 — **M7, E8** |
| REFINED | 1 | Claude 설명이 불완전 — **M6** |

### DISPUTED 상세

- **M7** — Claude 주장: "`bootstrap_roles.py` `memory_context`가 `recall_count` 생성자 없어 dead branch."
  - **반박 근거**: `core/control/intake.py:275, 294`에서 실제 생성되고 `core/project_pipeline.py:608`에서 소비되어 `core/bootstrap_roles.py:478`(Claude가 L226이라 한 곳)로 전달, `Past Lessons` 섹션으로 프롬프트 주입됨. **Live branch**
- **E8** — Claude 주장: "`write_episodic()` 호출"
  - **반박 근거**: 실제 심볼은 `facade.record_episode()`. `write_episodic`은 repo 전체 0건. 기능 존재는 맞지만 **명칭 인용 오류**

### REFINED 상세

- **M6** — Claude 주장: "`record_episode()` 호출 2곳뿐 (`fsa_loop.py:741`, `memory_consolidation.py:152`)"
  - **정정**: facade 직접 호출 site 기준으론 2곳이 맞지만, `core/fsa_loop.py` 내부 래퍼 `_record_episode`가 L211(cycle 성공), L321(분해 성공), L358(max_cycles 소진) 3곳에서 추가 호출됨. "재시도 성공 후만"이라는 해석은 오해

---

## 2. 영역별 최종 판정

### 2.1 REQ-COMPACT — 6/6 VERIFIED

| # | 주장 | 판정 | 근거 |
|---|---|---|---|
| C1 | `core/context_window_manager.py` 633줄 완성 (ContextBudget/ToolTracker/HistoryManager/KnowledgeInjector/ContextWindowManager) | VERIFIED | 줄수는 CRLF/LF 차로 621~633 변동, 클래스 존재는 확정 |
| C2 | `run_budget.py:28` 4-char ≈ 1-token 휴리스틱 | VERIFIED | `self.consumed += max(1, len(text) // 4)` |
| C3 | `agent_runner.py:1315` CWM import, L1483~1485 통계 | VERIFIED | cross-cycle reset 로직 부재도 확인 |
| C4 | `fsa_loop.py:149`, `dynamic_orchestrator.py:896` context 체크 없음 | VERIFIED | cycle 진입부 빈 상태 |
| C5 | `plan_verifier.py:50` PASS_THRESHOLD=0.7, `policy.yaml`에 `phase_gate_enabled` 없음 | VERIFIED | grep 0건 |
| C6 | `ControlPlaneLLM` 사용처 2곳 이상 | VERIFIED + 확장 | Claude가 놓친 `core/hooks/code_review_doc.py:125-126` 추가 확인 |

### 2.2 REQ-ISE — 7/7 VERIFIED, **신규 Critical 2건**

| # | 주장 | 판정 | 근거 |
|---|---|---|---|
| I1 | `ise_loop.py` 48줄 얇은 래퍼 (문서 "1,344줄" 주장 반박) | VERIFIED | L46-48 `return self.fsa.run_mission(...)`. 역사적으로도 최대 469줄 (커밋 `3f8ff28d`), 1344줄은 **존재한 적 없음** |
| I2 | `ise_analyzer.py:218` silent `except Exception: pass` | VERIFIED | — |
| I3 | `ise_strategy_ledger.py:225` SHA256 16자 truncation | VERIFIED | `hexdigest()[:16]` |
| I4 | `run_factory_cli.py:479,493` `--mode ise` 분기 존재 | VERIFIED + **확장** | ⚠️ Codex 결정적 발견 → **NEW-C1** |
| I5 | `fsa_loop.py:39-42` ISE 4클래스 import, L84-86 인스턴스화 | VERIFIED | 메타 루프 로직은 삭제가 아니라 `fsa_loop.py:149/364/413/534`로 이관됨 |
| I6 | `DynamicOrchestrator._should_decompose()` 미구현 | VERIFIED | grep 0건 (docs/plans에만 등장) |
| I7 | ise_loop.py 역사적 최대 크기 검증 | VERIFIED | 최초 커밋 469줄 → 커밋 `97366bed`에서 FSALoop 위임 wrapper로 축소 |

### 2.3 REQ-EVOLUTION — 8/9 VERIFIED, 1 DISPUTED

| # | 주장 | 판정 | 근거 |
|---|---|---|---|
| E1 | `skill_creator.py:682` `evolve_skill()` | VERIFIED | — |
| E2 | `security_guard.py:57, 86` quick_guard/run_isolated | VERIFIED | — |
| E3 | `skill_evolution_bus.py:69, 93-111` 7단계 캐시 무효화 | VERIFIED | `_step1_reload_registry` ~ `_step7_broadcast` |
| E4 | `skill_quality_gate.py:15, 25, 36` GateResult / SkillQualityGate / validate() | VERIFIED | 현재 `pass_rate`만 있고 `quality_delta` 부재 |
| E5 | `hooks/skill_self_evolution.py` 10회마다 감사 | VERIFIED | `check_interval=10` (L36), modulo 분기 L58 |
| E6 | `fsa_loop.py:292, 536` `_try_evolve_failed_skill()` | VERIFIED | L292 Level 4 분기, L536 메서드 정의 |
| E7 | `fsa_loop.py` _detect_failed_skill_dir/_rollback_skill/_run_quality_gate | VERIFIED | L621/L677/L695 (Claude·Codex 라인 번호 미세 드리프트) |
| E8 | "write_episodic() 호출" 표기 | **DISPUTED** | 실제 심볼은 `facade.record_episode`. 기능 존재, **명칭 오류** |
| E9 | GateResult에 `quality_delta` 필드 없음 | VERIFIED | 코드 grep 0건 |

### 2.4 REQ-MEMORY — 8/10 VERIFIED, 1 DISPUTED, 1 REFINED

| # | 주장 | 판정 | 근거 |
|---|---|---|---|
| M1 | UnifiedMemoryFacade 메서드 완비 | VERIFIED | `facade.py` L26 클래스, L105/149/164/220/275/305 |
| M2 | KnowledgeInjectionHook PRIORITY=10, pre_execute | VERIFIED | `knowledge_injection.py:26, 34` |
| M3 | `agent_runner.py:993-1055` KI/MC 훅 등록 | VERIFIED | bus.register 확인 |
| M4 | EpisodeMatcher Jaccard 0.4 임계 | VERIFIED | `episode_matcher.py:22, 65-77` |
| M5 | Relevance 공식 0.50/0.25/0.15/0.10 | VERIFIED | `config.py:43-48` 기본값 일치 |
| M6 | "record_episode 호출 2곳뿐" | **REFINED** | 직접 site는 2곳, 내부 래퍼 경유 5곳 |
| M7 | "recall_count 생성자 없음 → dead branch" | **DISPUTED** | `control/intake.py:275,294` 생성자 존재, `bootstrap_roles.py:478`에서 실제 프롬프트 주입 |
| M8 | `agent_specializer.py`에 memory 주입 없음 | VERIFIED | memory 심볼 0건 |
| M9 | `agent_runner.py:1125-1129` `_knowledge_context` append | VERIFIED | 유일하게 정상 작동하는 주입 경로 |
| M10 | EpisodeRecord 스키마 gap (7필드 부재) | VERIFIED | `models.py:137-151` 12필드 중 event_type/task_id/failure_pattern/root_cause/resolution/quality_delta/escalation_level 없음 |

---

## 3. Codex·독립 조사로 추가 발견한 신규 이슈

### 3.1 Critical

#### NEW-C1 — `--mode ise` 파싱-실행 배선 단절

- **현상**: `run_factory_cli.py:484`에서 `execution_mode="ise"`가 생성되지만 `agent_launcher.py:408, 461`은 `"fsa"`만 분기 처리. 사용자가 `af --mode ise ...`로 실행해도 실제로는 approval 모드로 떨어짐
- **의미**: Opus 4.6 문서가 "ISE dead code"라 지적한 **진짜 근거**는 파일 크기가 아니라 이 배선 단절이었다. 문서가 근거를 잘못 제시했지만 결론은 부분적으로 옳았음
- **영향**: P0 — 사용자가 현재 ISE 모드를 실행할 수 없음
- **수정 위치**: `agent_launcher.py:408, 461` (분기 추가)

#### NEW-C2 — ISE 모듈 5개 `af.spec` hiddenimports 누락

- **현상**: `core.ise_loop`, `core.ise_analyzer`, `core.ise_redesigner`, `core.ise_stall_detector`, `core.ise_strategy_ledger` 모두 `af.spec` `hiddenimports`에 explicit 등록 없음
- **위험**: `fsa_loop.py`가 top-level import하므로 현재는 PyInstaller 자동 분석에 포함되지만, 런타임 동적 import 경로가 추가되면 ImportError 발생
- **영향**: P0 — 빌드 회귀 잠재 위험
- **수정 위치**: `af.spec` `hiddenimports` 리스트

### 3.2 High

#### NEW-H1 — RunBudget 실사용 거의 0

- **현상**:
  - `core/run_budget.py:51` `set_run_budget()` 정의 존재, 런타임 호출처 **0건**
  - `RunBudget.record()` 호출은 `agent_runner.py:915` 1곳뿐인데, 참조하는 `result["text"]` 키가 `agent_runner.py:1485`의 실제 result 스키마에 **없음** → **Dead write**
- **의미**: COMPACT 요구사항(토큰 예산 추적)이 사실상 미작동
- **영향**: P1 — 비용 통제 부재

#### NEW-H2 — `search_semantic`이 어댑터 semantic score를 버린다

- **현상**: `facade.py:215`가 `rank_by_relevance(deduped)`만 호출, `semantic_scores` 인자 누락. `decay.py:131` `rank_by_relevance`는 sem map이 없으면 0.0으로 처리 → **semantic 가중치(0.50)가 실제 점수에 기여하지 않음**
- **의미**: recency 0.25 + frequency 0.15 + confidence 0.10만 반영되는 "semantic-degraded ranking"이 되고 있음. 공식 M5는 VERIFIED지만 실전 경로에서 semantic 0 주입
- **영향**: P1 — 메모리 검색 품질 체감 저하

#### NEW-H3 — CheckpointHook 등록 0건

- **현상**: `core/hooks/checkpoint.py:16` 구현 존재, `bus.register(CheckpointHook())` grep **0건**
- **영향**: P1 — Hook 생태계에서 고립된 dead registration

### 3.3 Medium

- **NEW-M1**: E8 용어 혼동 — 외부 문서와의 용어 맞춤 필요 (`write_episodic` → `record_episode`)
- **NEW-M2**: 테스트 커버리지 편차
  - MEMORY: Phase10/12/14/16 + stage4_7 강함
  - COMPACT: `test_context_window_manager.py:227` 중간
  - ISE: `ise_loop/ise_analyzer/ise_strategy_ledger/--mode ise` 직접 테스트 **0건**
  - EVOLUTION: SkillEvolutionBus/SkillQualityGate/SkillSelfEvolutionHook 직접 테스트 **0건**
  - PlanVerifier/ControlPlaneLLM/RunBudget 직접 테스트 **0건**

### 3.4 Low

- **NEW-L1**: `fsa_loop.py:741` 직접 호출 + `memory_consolidation.py:146-209` async pending/flush 경로 이중화 → 호출 확대 시 I/O 중복·종료 시점 race 잠재
- **NEW-L2**: `_rollback_skill` `.bak` 의존 — `evolve_skill`이 `.bak` 생성을 전제로 하며 일부 경로에서 스킵되면 롤백 무효

---

## 4. 우선순위 재조정 판정

### 원안 vs 대안

- **AF_Phase_A_Requirements.md 원안**: `COMPACT → ISE → EVOLUTION → MEMORY`
- **Claude 1차 제안**: `MEMORY → COMPACT → ISE → EVOLUTION`
- **Codex 제안 (채택)**: `ISE → COMPACT → EVOLUTION → MEMORY`

### 채택 근거

1. **MEMORY 후순위 타당**: 14개 Phase 테스트, facade/adapter 7종, Knowledge Graph 실제 동작 확인. M7(Claude가 dead라 한 것)도 실제로는 live. 주요 갭은 NEW-H2(semantic score 누수)와 M8(agent_specializer 비통합) 2개로 한정적
2. **ISE가 최우선**: NEW-C1(배선 단절) + NEW-C2(af.spec) + I6(_should_decompose) + NEW-M2(ISE 테스트 0건) — **Critical 2개 포함**. 사용자가 현재 ISE를 실행할 수 없음
3. **COMPACT 차우선**: CWM 구현은 됐으나 C4(cross-cycle reset 부재) + NEW-H1(RunBudget dead write) → 기능이 켜지지 않은 상태
4. **EVOLUTION 완성도 높음**: E1~E9 중 8개 VERIFIED, 체인 완전 연결. E9(`quality_delta`)와 NEW-M2(직접 테스트)만 남음

---

## 5. 실행 전략 (재배치)

### Step 0 — Regression Baseline 측정 (0.25일, Q10 (a))

- `pytest -q` 전체 실행 → `docs/2026-04-22-phase-a-baseline.md`에 결과 기록 (pass/fail/skip 카운트 + 실패 테스트 목록)
- 기존에 깨져 있던 테스트를 "pre-existing failure"로 태깅 → 각 Step 이후 회귀 감지 기준선 확보
- 이 단계의 실패는 Phase A가 만든 게 아니므로 해결 대상 아님 (단, 기록하여 Phase B로 이월)

### Q6·Q9 반영 — 전역 파라미터 조정

- **Q6 (c) 전부 실제 API**: Mock 비중 최소화. 핵심 E2E는 실제 Anthropic/Gemini 호출로 검증. 예산 상한 $30~50 (Opus 4.7 기준 Phase A 전체). Rate limit + flakiness 대응 위해 `retry_with_exponential_backoff` 적용
- **Q9 무거움 (일 30×200K)**: 
  - `memory_system/decay.py` `DEFAULT_TTL_DAYS = 30 → 15`
  - `run_budget.py` 태스크당 기본 한도 상향 (200K)
  - Supabase 유료 티어 전환 예상 시점 안내 (Step 5 Blueprint 갱신 시 명시)

### Step 1 — ISE 배선 복구 (1일)

- `agent_launcher.py:408, 461`에 `execution_mode=="ise"` 분기 추가 → `ise_loop.ISELoop.run_mission()` 호출 경로 연결
- `af.spec` `hiddenimports`에 ISE 5모듈 명시 추가
- `ise_analyzer.py:218` silent pass → 로그 출력 + 레벨별 대응
- `ise_strategy_ledger.py:225` SHA256 16자 → 32자 확장
- `DynamicOrchestrator._should_decompose()` 신규 구현 (3연속 실패 + L5 트리거)
- 단위 테스트 4건 신규 추가 (NEW-M2 해소)

### Step 2 — COMPACT 연동 활성화 (1.5일)

- `agent_runner.py:915`의 `result["text"]` 키 수정 → RunBudget.record() 실제 작동 복구
- `fsa_loop.py:149` cycle 진입부 + `dynamic_orchestrator.py:896` 에이전트 전환부에 CWM 상태 체크·리셋 훅 추가
- `policy.yaml`에 `phase_gate_enabled`, `context_window_sizes`, `compaction_thresholds` 추가 + 기본값 로더
- `plan_verifier.py`를 Phase Gate로 승격 (plan 부재 시 생성 리다이렉트)
- **`SkillPackBootstrapper.check_installed()` 구현** (Q8 Phase A 결정: (a) 탐지만)
  - Claude Code / Codex CLI / Gemini CLI 플러그인 경로에 Superpowers/GStack 존재 여부 감지
  - 미설치 시 경고 로그 + 수동 설치 안내 메시지 출력
  - 실제 자동 설치(어댑터 3종 구현)는 Phase B로 분리 (근거: `docs/archive/resolved/2026-04-22-phase-a-decisions-required.md` §Q8 확정 결정)
- RunBudget / ContextWindowManager / SkillPackBootstrapper 직접 테스트 4건

### Step 3 — EVOLUTION 마무리 (0.5일)

- `GateResult`에 `quality_delta: float | None = None` default 필드 추가
  - 소비자 L704/L736 영향 최소 (default None)
- `skill-eval-report.json` append 포맷 고정 + 스키마 JSON Schema 문서화
- SkillEvolutionBus / SkillQualityGate / SkillSelfEvolutionHook 직접 테스트 3건 + 의도적 결함 스킬 E2E 1건 (mock LLM)
- 회귀 테스트: 진화가 품질 낮추면 롤백되는지 음성 테스트

### Step 4 — MEMORY 품질 향상 (2일)

- `facade.py:215`에서 어댑터별 semantic score 모아 `rank_by_relevance(deduped, semantic_scores=...)` 전달 → NEW-H2 해소
- `agent_specializer.py`에 에피소드 주입 추가 → M8 해소
- EpisodeRecord 확장은 **단계적**으로: `metadata: dict` 안에 `event_type/failure_pattern/root_cause` 먼저 삽입, first-class 필드 승격은 Phase B로 분리 (M10 모든 필드 동시 추가는 to_dict/from_dict 동기 수정 부담 큼)
- `DynamicOrchestrator._execute_agent_task()` 성공/실패 양쪽 record_episode 추가 → 기록 밀도 향상
- KG 노드 생성: 진화 에피소드 → `{skill}-[EVOLVED_DUE_TO]->{pattern}`, 실패 에피소드 → `{task_type}-[FAILED_WITH]->{pattern}-[RESOLVED_BY]->{resolution}`

### Step 5 — Blueprint 동기화 & exe 빌드 (0.5일)

- `Master_Blueprint.md` §0/§2/§3.6/§4/§9/§11/§12 갱신 (같은 커밋)
- `python build_exe.py` → exe에서 `--mode ise` 스모크 테스트
- 버전 bump (`version.py` + `install-af.ps1` 3곳)

**총 예상 기간: 5.75일** (Step 0 baseline 0.25일 추가. Q4 OS별 크로스 플랫폼 빌드 scope에 따라 Step 5가 +0.5~1일 증가 가능)

- Step 0: Baseline 측정 (0.25일)
- Step 1: ISE 배선 복구 (1일)
- Step 2: COMPACT 연동 활성화 (1.5일)
- Step 3: EVOLUTION 마무리 (0.5일)
- Step 4: MEMORY 품질 향상 (2일)
- Step 5: Blueprint 동기화 & exe 빌드 (0.5일)

---

## 6. 건드리지 말아야 할 것 (회귀 방지)

- **EpisodeRecord 스키마 7필드 동시 추가 금지**: 모든 어댑터 `to_dict`/`from_dict` 동기 수정 필요. 단계적 접근 필수
- **`fsa_loop.py`의 ISE 4클래스 import 제거 금지**: 메타 루프 로직이 이미 `fsa_loop.py:149/364/413/534`에 이관돼 있음. 단순 "dead code 삭제"는 FSA 자체를 깨뜨림
- **기존 `record_episode` 이중 경로 병합 금지 (Phase A 범위)**: NEW-L1 race는 실측 유의미 미확인. Phase B에서 통합 리팩토링

---

## 7. 참고 절대 경로

```
D:\warkSpaces\agent-factory\core\ise_loop.py
D:\warkSpaces\agent-factory\core\fsa_loop.py
D:\warkSpaces\agent-factory\core\run_budget.py
D:\warkSpaces\agent-factory\core\context_window_manager.py
D:\warkSpaces\agent-factory\core\control_plane_llm.py
D:\warkSpaces\agent-factory\core\agent_runner.py
D:\warkSpaces\agent-factory\core\dynamic_orchestrator.py
D:\warkSpaces\agent-factory\agent_launcher.py
D:\warkSpaces\agent-factory\run_factory_cli.py
D:\warkSpaces\agent-factory\af.spec
D:\warkSpaces\agent-factory\policy.yaml
D:\warkSpaces\agent-factory\core\skill_quality_gate.py
D:\warkSpaces\agent-factory\core\skill_evolution_bus.py
D:\warkSpaces\agent-factory\core\hooks\skill_self_evolution.py
D:\warkSpaces\agent-factory\core\memory_system\facade.py
D:\warkSpaces\agent-factory\core\memory_system\models.py
D:\warkSpaces\agent-factory\core\memory_system\decay.py
D:\warkSpaces\agent-factory\core\memory_system\config.py
D:\warkSpaces\agent-factory\core\memory_system\knowledge_injection.py
D:\warkSpaces\agent-factory\core\memory_system\episode_matcher.py
D:\warkSpaces\agent-factory\core\control\intake.py
D:\warkSpaces\agent-factory\core\project_pipeline.py
D:\warkSpaces\agent-factory\core\bootstrap_roles.py
D:\warkSpaces\agent-factory\core\agent_specializer.py
D:\warkSpaces\agent-factory\core\hooks\memory_consolidation.py
D:\warkSpaces\agent-factory\core\hooks\checkpoint.py
```
