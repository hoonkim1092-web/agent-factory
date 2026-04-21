# Agent Factory — Phase A 상세 요구사항서

<!-- version: 1.0.0 | date: 2026-04-17 | author: Claude Opus 4.6 -->

> **목적**: Agent Factory v3의 핵심 엔진 4개를 완성하여 "설계만 앞선" 상태에서 "실행도 앞선" 상태로 전환한다.
> **범위**: 깊이(Phase A)만 다룬다. UI/거버넌스(Phase B)는 Phase A 완료 후 별도 문서로 작성한다.
> **완료 기준**: "밤에 태스크 던져놓고 자면 아침에 완성되어 있다"가 재현 가능하게 성립하는가?

---

## 0. 전략적 배경

### 0.1 경쟁 환경 요약 (2026-04-17 기준)

Agent Factory는 2026년 AI 코딩 에이전트 생태계에서 **독립 멀티 프로바이더 런타임**이라는 고유한 포지션을 점유하고 있다. 주요 경쟁·보완 관계는 다음과 같다.

- **Claude Code / Codex CLI** — 단일 프로바이더 하네스. 샌드박스·compaction·sub-agent 등 실행 안정성은 우위이나, 멀티 프로바이더 failover·스킬 자가진화·KG 메모리가 없다.
- **GStack / Superpowers** — Claude Code 위에 얹히는 스킬 팩. SKILL.md 기반이므로 Claude Code, Codex CLI, Cursor, Gemini CLI 등 범용 적용 가능. AF의 하위 프로바이더에 설치하면 자동 적용되므로 AF가 별도 구현할 필요 없다.
- **Paperclip** — 에이전트 회사 OS. 조직도·예산·거버넌스에 강점이나 코딩 도메인 깊이 부족. Phase B에서 참조할 대상.
- **Claude Managed Agents** — Anthropic 호스팅 런타임. 세션 외부 context 관리가 핵심 혁신이나, 멀티 프로바이더·자가진화 없음.

### 0.2 Agent Factory 고유 영역 (현존 도구에 없는 것)

1. 멀티 프로바이더 failover (claude → gemini → codex)
2. ISE 5단계 에스컬레이션 (retry → pivot → redesign → evolve → decompose)
3. 스킬 자가진화 + 7단계 캐시 무효화
4. Knowledge Graph 에피소드 메모리 + 시간 기반 decay
5. 교차검증 루프 (CrossVerificationLoop — 다중 CLI 독립 실행 + 순환 피어 리뷰 + Opus 판정)

### 0.3 현재 Gap (이 문서가 해결하는 것)

| Gap | 현상 | 결과 |
|-----|------|------|
| Context compaction 미구현 | 장시간 실행 시 context 초과 → 조용한 실패 | ISE·진화 루프가 중간에 끊김 |
| ISE dead code | ise_loop.py 1,344줄이 0 import | 자율 에스컬레이션 불가 |
| 스킬 진화 미검증 | evolve_skill() 존재하나 end-to-end 검증 없음 | 진화가 실제로 품질 향상시키는지 불명 |
| KG 메모리 미활용 | 에피소드 기록만 하고 다음 실행에 활용 안 함 | 같은 실수 반복 |

### 0.4 GStack / Superpowers 연동 전략

AF가 워크플로우 강제(TDD, 역할 기반 리뷰, 보안 감사)를 자체 구현할 필요는 없다. 이유:

1. GStack은 Claude Code, Codex CLI, Cursor, Gemini CLI 등 8개 호스트를 네이티브 지원한다.
2. Superpowers는 Anthropic 공식 marketplace에 등재되어 있으며, SKILL.md 표준으로 범용 적용 가능하다.
3. AF의 `claude_cli`, `codex_cli`, `gemini_cli` 어떤 프로바이더를 경유하든 해당 프로바이더에 GStack/Superpowers가 설치되어 있으면 자동 적용된다.

따라서 AF는 **오케스트레이터 레벨** 기능(compaction, ISE, 진화, 메모리)에만 집중하고, 워크플로우 강제는 하위 프로바이더의 스킬 팩에 위임한다.

단, GStack/Superpowers가 설치되지 않은 프로바이더 환경을 위해 **오케스트레이터 레벨 Phase Gate**(§1.5)를 최소한으로 구현한다.

---

## 1. REQ-COMPACT: Context Compaction

**우선순위**: P0 (최우선 — 나머지 3개의 전제조건)
**대상 파일**: `core/context_window_manager.py` (신규), `core/agent_runner.py`, `core/dynamic_orchestrator.py`
**Blueprint 참조**: v3 Phase 5B

### 1.1 문제 정의

현재 AF는 에이전트 실행 시 context window 관리를 전혀 하지 않는다. `agent_runner.py`가 CLI 프로바이더에 시스템 프롬프트 + 스킬 + 태스크 + 컨트랙트를 한 번에 전달하며, 실행이 길어지면 CLI 프로바이더 자체의 context 한계에 도달하여 silent failure가 발생한다.

ISE 에스컬레이션은 최대 5사이클 × 사이클당 N회 CLI 호출을 수행하므로, compaction 없이는 사이클 2-3에서 context가 넘칠 가능성이 높다.

### 1.2 목표

- 에이전트 실행 중 context 사용률을 추적하여 임계점(80%) 도달 시 자동 compaction을 수행한다.
- compaction 후에도 핵심 정보(태스크 목표, 현재 진행 상태, 최근 실패 원인)가 보존된다.
- ISE 5사이클 완주가 compaction으로 인한 중단 없이 가능하다.

### 1.3 기능 요구사항

#### 1.3.1 Context 사용률 추적

```
REQ-COMPACT-001: context_window_manager.py에 ContextWindowManager 클래스를 신설한다.
REQ-COMPACT-002: ContextWindowManager는 현재 context 사용량을 토큰 단위로 추적한다.
                 토큰 추정은 기존 run_budget.py의 4-char ≈ 1-token 휴리스틱을 재사용한다.
REQ-COMPACT-003: 프로바이더별 context window 크기를 설정으로 관리한다.
                 기본값: claude_cli=200K, codex_cli=128K, gemini_cli=1M
REQ-COMPACT-004: 사용률 80% 도달 시 WARNING 로그를 출력한다.
REQ-COMPACT-005: 사용률 95% 도달 시 자동 compaction을 트리거한다.
```

#### 1.3.2 Compaction 전략

```
REQ-COMPACT-010: compaction은 대화 히스토리의 초기 부분을 요약으로 대체한다.
REQ-COMPACT-011: 요약은 ControlPlaneLLM을 사용하여 생성한다.
                 ControlPlaneLLM 실패 시 rule-based fallback(최근 N턴만 유지)을 적용한다.
REQ-COMPACT-012: compaction 시 반드시 보존하는 정보:
                 - 원본 태스크 목표 및 수락 기준
                 - 현재까지의 파일 변경 목록
                 - 최근 실패 원인 및 에스컬레이션 레벨 (ISE 연동 시)
                 - 현재 작업 중인 파일 경로
REQ-COMPACT-013: compaction 전후 context의 SHA256 해시를 로그에 기록하여
                 디버깅 시 compaction 발생 시점을 추적 가능하게 한다.
```

#### 1.3.3 통합 지점

```
REQ-COMPACT-020: AgentRunner.run()에서 execute_cli_chat() 호출 전에
                 ContextWindowManager를 초기화한다.
REQ-COMPACT-021: execute_cli_chat()의 output을 ContextWindowManager에 누적한다.
REQ-COMPACT-022: FSALoop.run_mission()의 각 사이클 시작 시
                 ContextWindowManager 상태를 체크하고 필요 시 compaction을 수행한다.
REQ-COMPACT-023: DynamicOrchestrator는 에이전트 간 컨텍스트 전환 시
                 이전 에이전트의 ContextWindowManager를 리셋한다.
```

### 1.4 비기능 요구사항

```
REQ-COMPACT-NFR-001: compaction 자체의 LLM 호출은 1회 이하여야 한다.
REQ-COMPACT-NFR-002: compaction으로 인한 latency 증가는 30초 이내여야 한다.
REQ-COMPACT-NFR-003: compaction이 없는 환경(짧은 태스크)에서는 성능 오버헤드 0이어야 한다.
```

### 1.5 Orchestrator-Level Phase Gate (최소 구현)

GStack/Superpowers가 하위 프로바이더에 없는 경우를 위해, 오케스트레이터 레벨에서 최소한의 단계 강제를 구현한다.

```
REQ-COMPACT-030: plan_verifier.py를 확장하여 태스크 실행 전에
                 "plan 문서가 존재하는가?"를 검증하는 gate를 추가한다.
REQ-COMPACT-031: gate 실패 시 에이전트에게 plan 생성을 먼저 요청하는
                 프롬프트를 주입한다 (에러가 아닌 리다이렉트).
REQ-COMPACT-032: policy.yaml에 phase_gate_enabled: true (기본값) 설정을 추가한다.
                 사용자가 비활성화 가능하다.
```

### 1.6 테스트 요구사항

```
REQ-COMPACT-TEST-001: 단위 테스트 — ContextWindowManager 사용률 계산 정확도 검증
REQ-COMPACT-TEST-002: 단위 테스트 — compaction 트리거 임계값 검증 (80% WARNING, 95% COMPACT)
REQ-COMPACT-TEST-003: 단위 테스트 — compaction 후 필수 보존 정보 존재 검증
REQ-COMPACT-TEST-004: 통합 테스트 — FSA 5사이클 실행 시 compaction 자동 발동 및 완주 검증
REQ-COMPACT-TEST-005: 단위 테스트 — ControlPlaneLLM 실패 시 rule-based fallback 동작 검증
```

### 1.7 영향 범위 (Blast Radius)

| 수정 대상 | 직접 영향 | 간접 영향 |
|----------|----------|----------|
| `context_window_manager.py` (신규) | `agent_runner.py`, `fsa_loop.py` | 모든 에이전트 실행 |
| `agent_runner.py` (수정) | `dynamic_orchestrator.py` | context 추적 추가로 인한 미세 성능 변화 |
| `fsa_loop.py` (수정) | `project_pipeline.py` | 사이클 시작 시 compaction 체크 |

---

## 2. REQ-ISE: ISE Dead Code 활성화

**우선순위**: P1 (compaction 완료 후 즉시 착수)
**대상 파일**: `core/ise_loop.py`, `core/ise_redesigner.py`, `core/ise_analyzer.py`, `core/ise_stall_detector.py`, `core/ise_strategy_ledger.py`, `core/dynamic_orchestrator.py`, `core/control/supervisor.py`
**Blueprint 참조**: v3 Phase 1B
**Code Review 참조**: §2.6 ISE, §8 ISE 시스템 상세

### 2.1 문제 정의

ISE(Iterative Self-Enhancement) 시스템은 5개 파일, 1,344줄의 완전한 구현체가 존재하지만, 어디서도 import하지 않는 dead code 상태이다. 설계 의도는 FSA(5사이클) 위의 메타 루프로서, FSA가 실패하면 ISE가 더 높은 수준의 에스컬레이션(분해, 진화)을 수행하는 것이다.

현재 `fsa_loop.py`가 ISE의 일부 개념(ISEAnalyzer, ISERedesigner, StrategyLedger, StallDetector)을 직접 임포트하여 사용하고 있으나, `ise_loop.py`의 메타 루프 자체는 호출되지 않는다.

### 2.2 목표

- `ise_loop.py`를 실행 경로에 연결하여, `--mode ise`로 ISE 무한 자가진화 루프를 실행할 수 있게 한다.
- ISE가 FSA를 내부적으로 호출하고, FSA 실패 시 메타 레벨 에스컬레이션을 수행한다.
- 안전장치: 무한 루프 방지를 위한 max_meta_cycles 설정.

### 2.3 기능 요구사항

#### 2.3.1 ISELoop 연결

```
REQ-ISE-001: run_factory_cli.py에서 --mode ise 실행 시
             ise_loop.ISELoop.run_mission()을 호출한다.
REQ-ISE-002: ISELoop.run_mission()은 내부적으로 FSALoop.run_mission()을 호출하고,
             FSA 실패 시 메타 레벨 에스컬레이션을 수행한다.
REQ-ISE-003: ISELoop에 max_meta_cycles 파라미터를 추가한다.
             기본값: 10. policy.yaml에서 오버라이드 가능.
REQ-ISE-004: 각 메타 사이클 시작 시 ContextWindowManager를 리셋한다 (REQ-COMPACT 의존).
```

#### 2.3.2 기존 버그 수정

Code Review §8에서 식별된 버그를 ISE 활성화 전에 수정한다.

```
REQ-ISE-010: ise_loop.py L91 — while True 무한 루프를
             while meta_cycle < max_meta_cycles 로 교체한다.
REQ-ISE-011: ise_loop.py L274-278 — unreachable code를 제거하거나
             도달 가능하도록 로직을 수정한다.
REQ-ISE-012: ise_redesigner.py L111,171 — JSON 파싱 실패 시 silent retry를
             로그 출력 + 최대 3회 retry로 변경한다.
REQ-ISE-013: ise_analyzer.py L207-217 — LLM 호출에 timeout(120초)을 추가한다.
REQ-ISE-014: ise_analyzer.py L218 — except Exception silent pass를
             로그 출력으로 변경한다.
REQ-ISE-015: ise_strategy_ledger.py L225 — SHA256 16자 truncation을
             32자로 확장하여 충돌 가능성을 낮춘다.
REQ-ISE-016: ise_stall_detector.py L35,43 — threshold 매직넘버에
             docstring 설명을 추가한다.
```

#### 2.3.3 DynamicOrchestrator 연결

```
REQ-ISE-020: DynamicOrchestrator에 _should_decompose() 메서드를 추가한다.
             조건: 동일 태스크 3회 연속 실패 + ISE 레벨 5 도달 시.
REQ-ISE-021: _should_decompose() 트리거 시 ISERedesigner.decompose_task()를 호출하여
             3-7개 서브태스크로 분할한다.
REQ-ISE-022: 분할된 서브태스크는 기존 state_board에 추가하고
             동적 max_cycles 재계산(compute_max_cycles)을 트리거한다.
```

#### 2.3.4 Supervisor ISELoop 라우팅

```
REQ-ISE-030: control/supervisor.py에 deep_update 경로를 추가한다.
             Supervisor가 ISELoop의 stall을 감지하면
             human_escalation 또는 strategy 변경을 제안한다.
REQ-ISE-031: Supervisor의 heartbeat(30초) 간격 내에서
             ISELoop의 현재 메타 사이클 번호와 에스컬레이션 레벨을 모니터링한다.
```

### 2.4 비기능 요구사항

```
REQ-ISE-NFR-001: ISE 메타 사이클 1회의 최대 실행 시간은 30분이다.
                 초과 시 다음 사이클로 넘어간다.
REQ-ISE-NFR-002: ISE 활성화가 기존 FSA 모드(--mode fsa)에 영향을 주지 않아야 한다.
REQ-ISE-NFR-003: ISE 실행 중 모든 에스컬레이션 결정은 StrategyLedger에 기록되어
                 사후 분석이 가능해야 한다.
```

### 2.5 테스트 요구사항

```
REQ-ISE-TEST-001: 단위 테스트 — ISELoop max_meta_cycles 제한 동작 검증
REQ-ISE-TEST-002: 단위 테스트 — 각 에스컬레이션 레벨(L1-L5) 트리거 조건 검증
REQ-ISE-TEST-003: 단위 테스트 — StallDetector 정체 감지 → human_escalation 경로 검증
REQ-ISE-TEST-004: 단위 테스트 — ISERedesigner.decompose_task() 서브태스크 3-7개 생성 검증
REQ-ISE-TEST-005: 통합 테스트 — --mode ise 실행 시 ISELoop 진입 확인
REQ-ISE-TEST-006: 통합 테스트 — FSA 실패 → ISE 메타 에스컬레이션 → 스킬 진화 트리거 체인 검증
REQ-ISE-TEST-007: 회귀 테스트 — --mode fsa 기존 동작 무변경 확인
REQ-ISE-TEST-008: 단위 테스트 — REQ-ISE-010~016 각 버그 수정 검증
```

### 2.6 영향 범위

| 수정 대상 | 직접 영향 | 간접 영향 |
|----------|----------|----------|
| `ise_loop.py` (수정) | `run_factory_cli.py`, `fsa_loop.py` | 전체 ISE 실행 |
| `ise_redesigner.py` (수정) | `ise_loop.py`, `fsa_loop.py` | 태스크 분해 품질 |
| `ise_analyzer.py` (수정) | `ise_loop.py`, `fsa_loop.py` | 실패 분석 정확도 |
| `dynamic_orchestrator.py` (수정) | `project_pipeline.py` | _should_decompose 추가 |
| `control/supervisor.py` (수정) | `maintenance_pipeline.py` | deep_update 경로 |
| `run_factory_cli.py` (수정) | — | --mode ise 진입점 추가 |

---

## 3. REQ-EVOLUTION: 스킬 자가진화 End-to-End 검증

**우선순위**: P2 (ISE 활성화 후 착수)
**대상 파일**: `core/skill_creator.py`, `core/skill_procurer.py`, `core/skill_quality_gate.py`, `core/skill_evolution_bus.py`, `core/hooks/skill_self_evolution.py`, `core/fsa_loop.py`
**Blueprint 참조**: §4 자가진화 루프, §3.5 스킬 시스템

### 3.1 문제 정의

스킬 자가진화의 구성 요소는 모두 존재한다:
- `evolve_skill()` — LLM으로 개선 코드 생성
- `quick_guard()` — AST 검증
- `run_isolated()` — 샌드박스 테스트
- `SkillEvolutionBus` — 7단계 캐시 무효화
- `SkillQualityGate` — 품질 게이트
- `SkillSelfEvolutionHook` — 10회 실행마다 자동 감사

그러나 이 전체 체인이 end-to-end로 검증된 적이 없다. "실패 → 패턴 추출 → 스킬 진화 → 재실행 → 성공"이 실제로 성립하는지 불명확하다.

### 3.2 목표

- 자가진화 전체 체인을 end-to-end 검증하고, 발견된 문제를 수정한다.
- 진화 전후 스킬 품질 점수 변화를 측정 가능하게 한다.
- 진화 이력을 KG 메모리에 에피소드로 기록한다.

### 3.3 기능 요구사항

#### 3.3.1 End-to-End 체인 검증

```
REQ-EVOL-001: 다음 체인이 중단 없이 완주하는지 검증한다:
              CrossVerificationLoop.run()
                → Opus 판정 → failure_patterns 추출
                → _try_evolve_from_patterns()
                → evolve_skill()
                → quick_guard() + run_isolated()
                → SkillEvolutionBus.on_skill_evolved()
                → 7단계 캐시 무효화
                → 다음 사이클에서 진화된 스킬로 재실행
REQ-EVOL-002: 체인 중 어느 단계에서든 실패 시 graceful degradation:
              - evolve_skill() 실패 → 기존 스킬 유지, 로그 출력
              - quick_guard() 실패 → .bak에서 복원, 로그 출력
              - run_isolated() 실패 → .bak에서 복원, 로그 출력
REQ-EVOL-003: failure_patterns → 스킬 이름 매핑 로직을 검증한다.
              매핑 실패 시(관련 스킬을 찾을 수 없을 때) 로그를 남기고 진화를 스킵한다.
```

#### 3.3.2 진화 품질 측정

```
REQ-EVOL-010: 진화 전후의 스킬 품질 점수를 기록한다.
              품질 점수 = §4 품질 점수 공식 (최대 1.0)
REQ-EVOL-011: 진화가 품질 점수를 낮춘 경우 .bak에서 자동 복원한다 (regression guard).
REQ-EVOL-012: 진화 결과를 skill-eval-report.json에 append한다.
              포맷: {skill_name, version_before, version_after,
                     quality_before, quality_after, trigger_patterns, timestamp}
```

#### 3.3.3 SkillQualityGate 강화

```
REQ-EVOL-020: fsa_loop._try_evolve_failed_skill()에서
              SkillQualityGate를 호출하여 진화된 스킬을 검증한다.
REQ-EVOL-021: GateResult.passed == False인 경우:
              - 스킬을 .bak에서 복원한다.
              - SkillEvolutionBus.on_skill_evolved()를 호출하지 않는다.
              - 실패 사유를 StrategyLedger에 기록한다.
REQ-EVOL-022: GateResult에 quality_delta 필드를 추가한다.
              quality_delta = quality_after - quality_before
```

#### 3.3.4 에피소드 기록 (REQ-MEMORY 연동)

```
REQ-EVOL-030: 스킬 진화 성공 시 UnifiedMemoryFacade.write_episodic()을 호출한다.
              에피소드 내용: {event: "skill_evolved", skill_name, trigger_patterns,
                            quality_delta, version, timestamp}
REQ-EVOL-031: 스킬 진화 실패 시에도 에피소드를 기록한다.
              에피소드 내용: {event: "skill_evolution_failed", skill_name,
                            failure_reason, trigger_patterns, timestamp}
```

### 3.4 비기능 요구사항

```
REQ-EVOL-NFR-001: 단일 스킬 진화에 소요되는 시간은 120초 이내여야 한다.
REQ-EVOL-NFR-002: 진화로 인한 스킬 품질 하락률은 10% 이내여야 한다 (regression guard로 보장).
REQ-EVOL-NFR-003: .bak 복원은 원자적이어야 한다 (중간 상태 없음).
```

### 3.5 테스트 요구사항

```
REQ-EVOL-TEST-001: E2E 테스트 — 의도적 실패 스킬 → 진화 → 재실행 → 성공 시나리오
REQ-EVOL-TEST-002: 단위 테스트 — failure_patterns → 스킬 이름 매핑 정확도 검증
REQ-EVOL-TEST-003: 단위 테스트 — regression guard (.bak 복원) 동작 검증
REQ-EVOL-TEST-004: 단위 테스트 — GateResult.quality_delta 계산 검증
REQ-EVOL-TEST-005: 단위 테스트 — 에피소드 기록 내용 검증 (성공/실패 양쪽)
REQ-EVOL-TEST-006: 통합 테스트 — 7단계 캐시 무효화 후 다음 에이전트가 진화된 스킬을 로딩하는지 검증
```

### 3.6 영향 범위

| 수정 대상 | 직접 영향 | 간접 영향 |
|----------|----------|----------|
| `skill_quality_gate.py` (수정) | `fsa_loop.py` | 진화 품질 게이트 강화 |
| `fsa_loop.py` (수정) | `project_pipeline.py` | 진화 결과 에피소드 기록 |
| `skill_creator.py` (수정) | `skill_procurer.py` | regression guard 추가 |
| `hooks/skill_self_evolution.py` (수정) | `event_bus.py` | 에피소드 기록 연동 |

---

## 4. REQ-MEMORY: KG 메모리 실전 활용

**우선순위**: P3 (스킬 진화 검증 후 착수)
**대상 파일**: `core/memory_system/facade.py`, `core/memory_system/knowledge_injection.py`, `core/memory_system/episode_matcher.py`, `core/memory_system/graph_builder.py`, `core/bootstrap_roles.py`, `core/agent_specializer.py`
**Blueprint 참조**: §3.6 메모리 시스템

### 4.1 문제 정의

메모리 시스템의 인프라(facade, adapters, graph, decay)는 구축되어 있으나, 실제 활용이 제한적이다.

- `write_episodic()`은 호출되지만, 기록된 에피소드가 **다음 실행에 영향을 주는 경로가 미약**하다.
- `KnowledgeInjectionHook`이 에이전트별 개별 검색을 수행하지만, 에피소드 검색 결과가 프롬프트에 주입되는 정도가 불명확하다.
- `bootstrap_roles.plan()`에 `memory_context` 파라미터가 추가되었으나(§12 2026-04-09), 실제 에피소드가 계획에 반영되는 품질이 검증되지 않았다.

### 4.2 목표

- 과거 실행의 실패 에피소드가 다음 실행의 계획과 프롬프트에 구체적으로 반영된다.
- "같은 실수를 반복하지 않는다"가 측정 가능한 수준에서 성립한다.
- 에피소드 decay가 적절하게 동작하여 메모리가 무한 증가하지 않는다.

### 4.3 기능 요구사항

#### 4.3.1 에피소드 → 계획 반영

```
REQ-MEM-001: bootstrap_roles.ProjectPlanningDirector.plan()에서
             memory_context를 활용하여 과거 실패 교훈을 LLM 프롬프트에 주입한다.
REQ-MEM-002: 주입 형식을 구조화한다:
             "[과거 교훈] 태스크 '{task_name}'에서 '{failure_pattern}' 실패 발생.
              원인: {root_cause}. 회피 전략: {avoidance_strategy}"
REQ-MEM-003: 주입되는 에피소드 수를 최대 5개로 제한한다.
             관련성 점수(episode_matcher) 기준 상위 5개 선택.
REQ-MEM-004: 에피소드가 0개인 경우(첫 실행) graceful하게 건너뛴다.
```

#### 4.3.2 에피소드 → 에이전트 프롬프트 반영

```
REQ-MEM-010: AgentSpecializer.specialize()에서 해당 에이전트 역할과 관련된
             에피소드를 검색하여 시스템 프롬프트에 주입한다.
REQ-MEM-011: KnowledgeInjectionHook이 에피소드 검색 결과를 프롬프트에 주입할 때,
             "이전에 이런 실패가 있었으니 주의하세요" 형식으로 포맷한다.
REQ-MEM-012: 에피소드 주입으로 인한 context 증가량을 모니터링하고,
             ContextWindowManager(REQ-COMPACT)와 연동하여
             context가 부족하면 에피소드 주입 수를 줄인다.
```

#### 4.3.3 에피소드 기록 표준화

```
REQ-MEM-020: 모든 에피소드는 표준 스키마를 따른다:
             {
               "event_type": "task_success|task_failure|skill_evolved|
                              skill_evolution_failed|escalation",
               "task_id": str,
               "task_name": str,
               "agent_role": str,
               "provider": str,
               "failure_pattern": str | null,
               "root_cause": str | null,
               "resolution": str | null,
               "quality_delta": float | null,
               "escalation_level": int | null,
               "timestamp": ISO8601,
               "run_id": str
             }
REQ-MEM-021: DynamicOrchestrator._execute_agent_task() 완료 시
             성공/실패 모두에 대해 에피소드를 기록한다.
REQ-MEM-022: FSALoop.run_mission() 사이클 완료 시
             에스컬레이션 레벨 변경 에피소드를 기록한다.
```

#### 4.3.4 Decay 및 정리

```
REQ-MEM-030: 에피소드 decay는 30일 주기로 적용한다.
             30일 이상 된 에피소드의 relevance_score를 50% 감소시킨다.
REQ-MEM-031: relevance_score가 0.1 이하인 에피소드는 archive로 이동한다
             (삭제하지 않음).
REQ-MEM-032: decay 실행 시점: af run 시작 시 1회 (백그라운드 스레드).
```

#### 4.3.5 Knowledge Graph 활용

```
REQ-MEM-040: 스킬 진화 에피소드를 Knowledge Graph에 노드로 추가한다.
             노드: {skill_name} -[EVOLVED_DUE_TO]-> {failure_pattern}
REQ-MEM-041: 태스크 실패 에피소드를 Knowledge Graph에 노드로 추가한다.
             노드: {task_type} -[FAILED_WITH]-> {failure_pattern}
                   {failure_pattern} -[RESOLVED_BY]-> {resolution}
REQ-MEM-042: graph_query.py를 활용하여 "이 태스크 유형에서 자주 발생하는 실패 패턴"을
             조회하고 계획 단계에서 활용한다.
```

### 4.4 비기능 요구사항

```
REQ-MEM-NFR-001: 에피소드 검색(episode_matcher)은 100ms 이내에 완료되어야 한다.
REQ-MEM-NFR-002: 에피소드 저장소는 1,000개 에피소드까지 성능 저하 없이 동작해야 한다.
REQ-MEM-NFR-003: decay 백그라운드 작업은 메인 파이프라인을 1초 이상 블로킹하지 않아야 한다.
REQ-MEM-NFR-004: KG 노드 수는 10,000개까지 지원한다.
```

### 4.5 테스트 요구사항

```
REQ-MEM-TEST-001: E2E 테스트 — 실패 에피소드 기록 → 다음 실행에서 계획에 반영 확인
REQ-MEM-TEST-002: 단위 테스트 — 에피소드 스키마 검증 (필수 필드 존재)
REQ-MEM-TEST-003: 단위 테스트 — episode_matcher 관련성 점수 상위 5개 선택 검증
REQ-MEM-TEST-004: 단위 테스트 — decay 30일 규칙 + archive 이동 검증
REQ-MEM-TEST-005: 단위 테스트 — KG 노드 생성 및 조회 검증
REQ-MEM-TEST-006: 통합 테스트 — context 부족 시 에피소드 주입 수 자동 축소 검증
REQ-MEM-TEST-007: 성능 테스트 — 1,000 에피소드 환경에서 검색 100ms 이내 확인
```

### 4.6 영향 범위

| 수정 대상 | 직접 영향 | 간접 영향 |
|----------|----------|----------|
| `memory_system/facade.py` (수정) | 전체 메모리 시스템 | 에피소드 스키마 변경 시 모든 기록자 |
| `memory_system/knowledge_injection.py` (수정) | `agent_runner.py` | 에이전트 프롬프트 품질 |
| `bootstrap_roles.py` (수정) | `project_pipeline.py` | 계획 품질 |
| `agent_specializer.py` (수정) | `dynamic_orchestrator.py` | 에이전트 컨텍스트 품질 |
| `dynamic_orchestrator.py` (수정) | `project_pipeline.py` | 에피소드 기록 추가 |

---

## 5. 구현 순서 및 의존성 체인

```
REQ-COMPACT (P0)
     │
     │  compaction 없이 ISE 장시간 실행 불가
     ▼
REQ-ISE (P1)
     │
     │  ISE 에스컬레이션이 스킬 진화를 트리거
     ▼
REQ-EVOLUTION (P2)
     │
     │  진화 결과를 에피소드로 기록
     ▼
REQ-MEMORY (P3)
     │
     │  에피소드가 다음 실행에 반영
     ▼
[Phase A 완료]
     │
     ▼
Phase B (UI/거버넌스 — 별도 문서)
```

### 병렬 작업 가능 영역

- REQ-COMPACT-030~032 (Phase Gate) — REQ-COMPACT 본체와 병렬 가능
- REQ-MEM-020~022 (에피소드 스키마 정의) — REQ-ISE 작업 중 병렬 가능
- REQ-ISE-010~016 (기존 버그 수정) — REQ-COMPACT와 병렬 가능

---

## 6. 완료 기준 (Definition of Done)

### 6.1 Phase A 전체 완료 기준

1. `af run --mode ise --budget 100000` 실행 시 ISE 메타 루프가 진입하고, compaction이 자동으로 발동하며, 스킬 진화가 트리거되고, 에피소드가 기록된다.
2. 두 번째 `af run` 실행 시 첫 번째 실행의 실패 에피소드가 계획 단계에서 참조된다.
3. 단위 테스트 전체 PASS (기존 24건 + 신규 30건 이상).
4. PyInstaller 빌드 후 exe에서 동일하게 동작한다.

### 6.2 각 REQ별 완료 기준

| REQ | 완료 기준 |
|-----|----------|
| REQ-COMPACT | FSA 5사이클 + compaction 자동 발동 + 완주. 단위 테스트 5건 PASS |
| REQ-ISE | --mode ise 진입 + 메타 에스컬레이션 L1-L5 동작 + max_meta_cycles 제한. 단위 테스트 8건 PASS |
| REQ-EVOLUTION | E2E 체인 완주 + regression guard 동작 + 에피소드 기록. 단위 테스트 6건 PASS |
| REQ-MEMORY | 에피소드 → 계획 반영 확인 + decay 동작 + KG 노드 생성. 단위 테스트 7건 PASS |

---

## 7. 위험 및 완화 전략

| 위험 | 영향 | 확률 | 완화 |
|------|------|------|------|
| Compaction이 핵심 정보를 손실 | ISE 에스컬레이션 실패 | 중 | 필수 보존 필드 목록 + 검증 테스트 |
| ISE 무한 루프 (기존 버그 미발견) | 토큰 소진 | 중 | max_meta_cycles + RunBudget 이중 가드 |
| 스킬 진화가 품질을 저하 | regression | 높 | regression guard + .bak 자동 복원 |
| 에피소드 과잉 주입으로 context 부족 | 에이전트 성능 저하 | 중 | ContextWindowManager 연동 + 최대 5개 제한 |
| 프로바이더별 context window 크기 부정확 | compaction 타이밍 오류 | 낮 | 보수적 기본값 + 설정 오버라이드 |

---

## 8. Blueprint 업데이트 계획

Phase A 완료 시 Master_Blueprint.md에 업데이트할 섹션:

| 섹션 | 변경 내용 |
|------|----------|
| §0 빠른 참조 테이블 | `context_window_manager.py` 행 추가 |
| §2 실행 흐름 | Flow B에 ISELoop 메타 루프 추가, compaction 시점 표시 |
| §3.6 메모리 시스템 | 에피소드 스키마 v2 추가, decay 규칙 문서화 |
| §4 자가진화 루프 | regression guard 추가, 에피소드 기록 체인 추가 |
| §9 설정 레퍼런스 | max_meta_cycles, context_window_sizes 추가 |
| §11 알려진 제약 | ISE dead code 제거, compaction 미구현 제거 |
| §12 변경 이력 | Phase A 각 단계별 변경 기록 |

---

## 부록 A: 관련 파일 전체 목록

### 신규 생성

| 파일 | REQ |
|------|-----|
| `core/context_window_manager.py` | REQ-COMPACT |

### 수정 대상

| 파일 | REQ | 수정 내용 |
|------|-----|----------|
| `core/agent_runner.py` | COMPACT, MEM | context 추적, 에피소드 기록 |
| `core/dynamic_orchestrator.py` | COMPACT, ISE, MEM | context 리셋, _should_decompose, 에피소드 기록 |
| `core/fsa_loop.py` | COMPACT, ISE, EVOL | compaction 체크, ISELoop 연결, 진화 에피소드 |
| `core/ise_loop.py` | ISE | 버그 수정, max_meta_cycles |
| `core/ise_redesigner.py` | ISE | silent retry 수정 |
| `core/ise_analyzer.py` | ISE | timeout 추가, silent pass 수정 |
| `core/ise_stall_detector.py` | ISE | 문서화 |
| `core/ise_strategy_ledger.py` | ISE | SHA256 확장 |
| `core/control/supervisor.py` | ISE | deep_update 경로 |
| `core/run_factory_cli.py` | ISE | --mode ise 진입점 |
| `core/skill_creator.py` | EVOL | regression guard |
| `core/skill_quality_gate.py` | EVOL | quality_delta |
| `core/hooks/skill_self_evolution.py` | EVOL | 에피소드 기록 |
| `core/memory_system/facade.py` | MEM | 에피소드 스키마 v2 |
| `core/memory_system/knowledge_injection.py` | MEM | 프롬프트 주입 강화 |
| `core/memory_system/episode_matcher.py` | MEM | 관련성 검색 |
| `core/memory_system/graph_builder.py` | MEM | 스킬 진화/실패 노드 |
| `core/bootstrap_roles.py` | MEM | memory_context 활용 강화 |
| `core/agent_specializer.py` | MEM | 에피소드 프롬프트 주입 |
| `core/plan_verifier.py` | COMPACT | Phase Gate |
| `policy.yaml` | COMPACT, ISE | phase_gate, max_meta_cycles |

---

## 부록 B: 용어 정의

| 용어 | 정의 |
|------|------|
| **Compaction** | context window 사용률이 임계점을 초과했을 때 초기 대화 히스토리를 요약으로 대체하는 행위 |
| **ISE** | Iterative Self-Enhancement. FSA 위의 메타 루프로, FSA 실패 시 더 높은 수준의 에스컬레이션을 수행 |
| **FSA** | Finite State Automaton. 5사이클 제한의 에이전트 실행 루프 |
| **에스컬레이션 레벨** | L1(retry) → L2(pivot) → L3(redesign) → L4(evolve) → L5(decompose) |
| **StrategyLedger** | 전략 시도 원장. 동일 전략 반복 방지 |
| **StallDetector** | 엔트로피 기반 정체 감지. 진전 없으면 creativity_injection 또는 human_escalation |
| **regression guard** | 스킬 진화가 품질을 낮추면 .bak에서 자동 복원하는 안전장치 |
| **Phase Gate** | 오케스트레이터 레벨에서 plan → test → implement 순서를 강제하는 가드 |
| **decay** | 시간 경과에 따라 에피소드의 관련성 점수를 낮추는 메모리 에이징 메커니즘 |
