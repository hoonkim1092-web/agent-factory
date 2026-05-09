# Agent Factory — 마스터 구현 로드맵 (전략 + 진단 통합본)

> 날짜: 2026-04-26
> 목적: 사용자 목표 4개 → 전략 합의 → 코드 진단 → 구현 단계까지 한 문서로
> 통합 대상:
> - `docs/참고/2026-04-25-harness-market-agent-factory-saas-strategy.md` (Codex 7-phase 전략)
> - `docs/참고/2026-04-26-harness-strategy-critique.md` (Claude 비평)
> - `docs/참고/2026-04-26-harness-strategy-consensus.md` (Claude × Codex 1차 합의)
> - 코드 진단 결과 (Explore agent, 2026-04-26 04:09 KST)
> 검증 절차: af-critic + af-cross-review 병렬 + Codex CLI 크로스체크 (이 문서 다음 단계)

---

## 1. 사용자 목표 4개 (모든 판정의 기준)

| # | 목표 | 의미 |
|---|------|------|
| ① | "만들어줘" → 처음부터 끝까지 결과물 | 요구사항~배포까지 한 번에 |
| ② | 토큰 부족 / PC 꺼짐 → **멈춘 자리에서 재개** | **AF의 척추** |
| ③ | 작업을 **아주 작은 단위**로 쪼갬 | ②를 가능하게 하는 메커니즘 |
| ④ | 기존 대형 프로젝트에 붙어서 분석·리팩토링·버그·기능 | 유지보수 가능한 하네스 |

---

## 2. 전략 포지셔닝 (Claude × Codex 합의)

### 2.1 두 모델이 동의한 결론 한 줄

> **AF는 Claude Code/Codex/Manus의 대체가 아니라, 그것들을 컨트롤하는 상위 plane이다. 척추는 Resumable Execution이고, 그 위에 작은 task 1개를 끝까지 굴리는 검증이 다음 행동이다. SaaS·multi-tenant·marketplace는 그 다음.**

### 2.2 Codex 원안 vs Claude 비평 → 합의

| 쟁점 | Codex 원안 | Claude 비평 | 최종 합의 |
|------|-----------|------------|---------|
| 진행 속도 | 7-phase 동시 | Step 0 + 수직 슬라이스 1개 | **Claude 안 채택** — 7-phase는 북극성, 실행은 좁힘 |
| Demo 크기 | repo 5개 | repo 1개 × task 1개 | **부분 채택** — 1 task, 단 README 오타급 NO, "작은 버그/기능" |
| 재개 가능성 | Phase 4 후순위 | Step 1 함의 | **둘 다 수정** — Tier 1로 승격 (Codex가 "내 배치 실수" 인정) |
| Multi-tenant SaaS | Phase 4 핵심 | PMF 후 보류 | **Claude 안 채택** |
| Hosted sandbox | Manus류 흡수 | BYO 충분 | **Claude 안 채택** |

### 2.3 Codex가 추가한 보강 2개 (둘 다 채택)

**보강 1 — Checkpoint 4요소 확장**

| 요소 | 의미 | 필요성 |
|------|------|------|
| idempotency key | step별 고유 식별자 | 재개 시 중복 PR/commit 방지 |
| artifact/worktree snapshot | 파일 상태 스냅샷 | PC 꺼져도 같은 파일 상태에서 재개 |
| next-step cursor | 다음 step 포인터 | "어디서 멈췄나" 명시 |
| test/acceptance 결과 | 통과 검증 영속화 | 통과한 test 다시 안 돌림 |

**보강 2 — Step 0 의사결정 +1 (5개 → 6개)**

추가: **State Source of Truth 결정** (SQLite / Postgres / Object storage)

---

## 3. 코드 진단 결과 (Explore agent, 136 모듈)

### 3.1 사용자 목표 vs 현재 코드 점수

| 목표 | 점수 | 근거 |
|------|------|------|
| ② 재개 가능성 | **2/10** | CheckpointHook은 agent_runner 한 회차만 저장, project_pipeline `.checkpoint/{stage}.json` 저장은 되나 `execute()` 직전 **로드 코드 없음** |
| ③ atomic task | **4/10** | `completed_subtask_keys`가 memory_hub와 board 파일에서 불일치 가능, 같은 task_id 중복 실행 가능 |
| ④ repo 분석 | **1/10** | `_recall_from_memory()` 스텁 구현, `DocumentIndex` 고아, `memory_context`가 role_planning에 전달 안 됨 |

**합계 7/30점** — 사용자 직감 정확함.

### 3.2 깨진 연결 (BROKEN) — 즉시 수정 대상

| # | 위치 | 문제 | 영향 목표 |
|---|------|------|---------|
| B1 | `core/control/intake.py:262` | `_recall_from_memory()` 스텁 — 메모리 데이터 안 옴 | ④ |
| B2 | `agent_launcher.py:468` | `execute()` 직전 checkpoint 로드 없음 | ② |
| B3 | `dynamic_orchestrator.py:1021` | task_board와 memory의 completed_subtask_keys 불일치 → 중복 실행 가능 | ③ |

### 3.3 약한 연결 (WEAK)

| # | 위치 | 문제 |
|---|------|------|
| W1 | `core/providers/cli.py:698` | CLI 실패 시 native API 폴백 미완 |
| W2 | `agent_runner.py:1116` | `bus.run_pre_execute()` hook 반환값 검증 부족 |
| W3 | `approval_gate.py:127` | `is_execution_open()` 실패 시 `check_validity()` 실행 안 됨 — 우회 가능 |

### 3.4 고아 모듈 (ORPHAN)

- `core/document_index.py` — 정의만, project_pipeline에서 호출 0
- `core/memory_system/adapters/cortex_vector.py, sync_compyne.py` — 등록되나 호출 안 됨
- `core/hooks/skill_self_evolution.py` — Hook 등록은 되나 진화 경로는 dynamic_orchestrator 내부에만 있음

### 3.5 중복/분산 (3 그룹)

| 그룹 | 분산 위치 | 문제 |
|------|---------|------|
| Checkpoint | `hooks/checkpoint.py` + `project_pipeline.py` + `control/lifecycle_bridge.py` | 3가지 형식·경로·시점, canonical 없음 |
| Board sync | `dynamic_orchestrator.update_project_board_task` + `project_pipeline.sync_board_from_work_items` | execute() 시 race condition 가능 |
| Trace log | `agent_runner` (chat_trace) + `dynamic_orchestrator` (state_snapshot) + `hooks/memory_consolidation` (episode) | 같은 이벤트 3곳 다르게 기록 |

---

## 4. 진단이 합의안 우선순위를 검증함

| 합의안 항목 | 진단이 증명한 필요성 |
|----------|------------------|
| Tier 1 (1) RunEvent + Checkpoint | **재개 2/10** → 가장 시급, checkpoint 3곳 분산 통합 |
| Tier 1 (2) Atomic Task | **atomic 4/10** → board/memory 동기화부터 |
| Tier 2 (5) Persistent memory | **repo 분석 1/10** → DocumentIndex 고아 해결 |
| Tier 3 (7) Audit 통합 | **trace 3곳 분산** → 정합성 회복 |

→ 진단과 전략의 우선순위가 일치. 가설이 틀리지 않았다.

---

## 5. 최종 구현 로드맵 (3 Tier + 명시적 단계)

### Tier 1 — 척추 (지금 시작) ⭐⭐⭐

#### **Item T1-1: Unified RunEvent + Checkpoint (canonical SoT)**

**왜 해야 하나?**
- 현재 checkpoint가 3곳에 분산돼 있고 `execute()` 직전 **로드도 안 됨**. 사용자가 PC를 끄고 다시 켜면 prepare부터 처음 재실행.
- 사용자 목표 ②가 직접 무너지는 가장 큰 구멍.

**했을 때 효과**
- 토큰 한도 초과 → 자동 일시중단 → 한도 복원 시 같은 step부터 재개 (몇 분치 손실)
- PC 꺼짐 → `af resume <run_id>` → 멈춘 step부터
- Provider 죽어도 다른 provider로 같은 step 재실행 가능
- 통과한 test 다시 안 돌림 (시간·토큰 절약)

**명시적 단계**
1. **Step 0 결정 ⑥** (state SoT) 후 → SQLite vs Postgres 결정 반영
2. `core/events/run_event.py` 신설 — RunEvent dataclass + 저장/조회 API
3. `core/checkpoint/canonical.py` 신설 — Checkpoint dataclass (4요소: idempotency_key, worktree_snapshot, next_cursor, test_results)
4. 기존 3곳을 canonical로 마이그레이션:
   - `core/hooks/checkpoint.py` → 얇은 어댑터로
   - `core/project_pipeline.py` `.checkpoint/{stage}.json` → canonical로 흡수
   - `core/control/lifecycle_bridge.py` → canonical 사용
5. `agent_launcher.py:468`(=execute() 호출부) **직전에 checkpoint 로드 + resume 분기** 추가
6. `af resume <run_id>` CLI 명령 신설

**완료 기준**: prepare → role_plan → orchestrator step 1개 진행 → SIGKILL → `af resume` → 다음 step부터 정상 재개.

---

#### **Item T1-2: Atomic Task Decomposition + Idempotent Retry**

**왜 해야 하나?**
- 현재 `completed_subtask_keys`가 memory_hub와 board 파일에서 **불일치 가능** → 같은 task가 2번 실행될 수 있음.
- 사용자 목표 ③이 직접 무너짐. T1-1만 있고 T1-2 없으면 재개 시 같은 PR 두 번 만들어짐.

**했을 때 효과**
- task가 5~15분 단위로 쪼개져 한 번 실패 손실 최소화
- 재시도해도 **결과는 1번만** (idempotency)
- 사람 검토도 5분짜리 diff라 부담 적음

**명시적 단계**
1. `dynamic_orchestrator.py`의 task 단위를 **step**으로 재정의 (현재는 task가 너무 큼)
2. 각 step에 `idempotency_key = hash(work_item_id + step_index + input_digest)` 부여
3. board 파일과 memory_hub의 completed 상태를 **하나의 SoT(T1-1 RunEvent)**로 통합 — 둘 중 하나 폐기 또는 동기화 강제
4. retry 시 `idempotency_key` 동일하면 이전 결과 재사용, 다르면 새 step
5. `update_project_board_task` ↔ `sync_board_from_work_items` race condition 해결: **단일 진입점** 강제 (현재는 2곳에서 board 쓰기)

**완료 기준**: 같은 task를 강제로 2번 실행해도 PR/commit이 1번만 생기는 테스트 통과.

---

### Tier 2 — 시장 진입 (Tier 1 후)

#### **Item T2-3: Step 0 의사결정 6개 (이번 주, 사용자 직접)**

**왜 해야 하나?**
- 이거 안 정하면 Tier 1 구현 자체가 추측. 특히 ⑥(SoT)은 T1-1의 데이터베이스 선택이라 결정 후에야 구현 시작 가능.

**했을 때 효과**
- 1주 투자로 다음 3개월 방향 확정
- T1-1 코드가 SQLite에서 Postgres로 옮기는 마이그레이션 비용 0

**명시적 단계 (사용자가 답해야 할 6개 질문)**
| # | 질문 | 후보 | 권장 (근거) |
|---|------|------|----------|
| ① | Worker runtime | BYO 로컬 / Docker / hosted | **BYO 로컬** — 목표 ④ "기존 프로젝트에 붙음"과 일치 |
| ② | Provider 1순위 | Codex App Server / Claude API / CLI | **Codex App Server** — 진단 W1 stdout 파싱 약함 해소 |
| ③ | 첫 ICP repo | Python / React / etc | **Python** — AF 자체가 Python이라 dogfooding 가능 |
| ④ | 첫 task 종류 | 작은 버그 / 작은 기능 | **작은 버그픽스** — 회귀 테스트 작성이 의무라 검증 빠름 |
| ⑤ | Pricing 가설 | seat / accepted-PR / token passthrough | (사용자 결정) |
| ⑥ | **State SoT** | SQLite / Postgres / Object storage | **Postgres (Supabase 활용)** — 이미 sync 인프라 있음, 다른 PC 재개 가능 |

---

#### **Item T2-4: 1 repo × 1 task 수직 슬라이스 (4~8주)**

**왜 해야 하나?**
- 사용자 목표 ① "끝까지 결과물"이 진짜 작동하는지 한 번도 검증 안 됐음.
- Tier 1의 재개·원자성도 이 슬라이스에서 함께 검증.

**했을 때 효과**
- 진짜 동작하는 PR 1건 (가치 검증)
- 시장·기술 가설 검증 (이게 안 되면 Tier 3 무의미)

**명시적 단계**
1. ICP 후보 repo 1개 선정 (사용자 본인 repo 또는 작은 OSS)
2. "함수 1개 버그 수정 + 회귀 테스트 추가" task 정의
3. flow: repo 연결 → 분석 → patch → test → PR → cost 기록 end-to-end
4. 일부러 중간에 SIGKILL → `af resume` → 같은 PR 1건만 생성되는지 확인 (T1-1·T1-2 동시 검증)
5. 성공률 80% 도달까지 반복

**완료 기준**: 동일 task를 5번 실행 → PR 5개 생성, 그중 4개 이상 test 통과.

---

#### **Item T2-5: Project-scoped Persistent Memory**

**왜 해야 하나?**
- 진단: `_recall_from_memory()` 스텁, `DocumentIndex` 고아, `memory_context` 미전달 (목표 ④ 1/10).
- 두 번째 작업이 첫 번째보다 **똑똑해지지 않으면** AF의 차별화가 사라짐.

**했을 때 효과**
- 같은 repo 두 번째 PR이 회사 컨벤션 자동 인지
- 같은 원인 실패 반복 안 함
- 리팩토링 시 "이전에 망가뜨린 곳" 회피

**명시적 단계**
1. `core/control/intake.py:262` `_recall_from_memory()` 실제 구현 (B1 수정)
2. `DocumentIndex`를 `project_pipeline.prepare_documents`에서 호출하도록 연결 (고아 해소)
3. `memory_context`를 role_planning까지 전달 (현재 brief에만 저장됨)
4. `MemoryScope.PROJECT` 토대 위에 영속 vector store (Supabase pgvector 또는 로컬 chroma) 연결
5. `project_id` scope를 모든 memory record에 강제

**완료 기준**: 같은 repo 두 번째 task의 plan에 첫 번째 task의 결정·실패가 명시적으로 인용됨.

---

### Tier 3 — 안정화 (Tier 2 후)

#### **Item T3-6: Codex App Server adapter**

**왜 해야 하나?**
- 진단 W1: stdout 파싱이 결함 발생 1순위. 이번 세션 통합 결함 다수가 stdout 경계에서.
- App Server는 JSON-RPC라 메시지 경계 명확.

**효과**
- long-running 작업이 끊겨도 thread/turn/item 단위로 진행 상태 정확히 복원
- T1-1 재개 가능성이 provider 레벨에서도 보장

**명시적 단계**
1. `core/providers/codex_app_server.py` 신설
2. JSON-RPC client (codex App Server stdin/stdout)
3. `core/providers/cli.py`를 `core/providers/base.py` interface 뒤로 숨김
4. Codex 요청 시 App Server 우선, 실패 시 CLI 폴백

---

#### **Item T3-7: Approval/Cost/Audit를 RunEvent에 통합**

**왜 해야 하나?**
- 진단: trace 3곳 분산 (chat_trace, state_snapshot, episode).
- "이 PR에 얼마 썼고 누가 승인했는지"가 한 화면에서 안 보임.

**효과**
- T1-1 RunEvent가 그대로 audit 로그가 됨
- 디버깅·비용·승인이 한 schema로

**명시적 단계**
1. `RunBudget` 글로벌 싱글톤 폐기 → `CostEvent`(RunEvent 하위 type)로
2. `approval_gate.py`의 파일 hash 스냅샷을 RunEvent payload로
3. 3곳 trace 작성기 → 단일 RunEvent 작성기로 (다른 곳은 view-only)
4. W3 (`approval_gate.is_execution_open()` 실패 시 우회) 수정 — `check_validity()` 항상 실행

---

### 보류 (PMF 후, Codex도 동의)

| 항목 | 보류 사유 |
|------|---------|
| Multi-tenant SaaS Control Plane | 사용자 목표에 multi-tenant 없음 |
| Background heartbeat maintenance | 검증 메커니즘 약한 상태에서 자동 PR = noise 폭발 |
| Marketplace / Skill 상품화 | PMF 전엔 빈 진열대 |
| Manus류 hosted sandbox | 목표 ④면 BYO 로컬 |

---

## 6. 단계 요약 (이번 주 → 8주 → 그 이후)

```
[이번 주]
  Step 0 6개 결정 (사용자 직접)  ← T2-3
  ↓
[2~4주]
  T1-1 RunEvent + Checkpoint  ← Step 0 ⑥ 결정 후 시작
  T1-2 Atomic Task + Idempotent Retry
  ↓ (검증: 강제 SIGKILL 후 resume 정상 동작)
[4~8주]
  T2-4 1 repo × 1 task 수직 슬라이스
  T2-5 Persistent Memory  ← T2-4와 병행
  ↓ (검증: 동일 repo 두 번째 task가 첫 번째 학습 활용)
[8~12주]
  T3-6 Codex App Server adapter
  T3-7 Audit 통합
  ↓
[PMF 검증 후]
  Multi-tenant / heartbeat / marketplace
```

---

## 7. 즉시 수정 (Tier 1 시작 전, 1~2일 내)

진단에서 나온 **약한 연결 3건**은 Tier 1을 시작하기 전에 먼저 정리. 안 그러면 Tier 1 구현이 약한 토대 위에 쌓임:

| ID | 위치 | 수정 |
|----|------|------|
| W2 | `agent_runner.py:1116` | hook 반환값 명시 검증 (False면 차단 강제) |
| W3 | `approval_gate.py:127` | `is_execution_open()` 실패해도 `check_validity()` 실행 보장 |
| 고아 정리 | `skill_self_evolution.py` 등 | 진짜 사용 안 하면 삭제, 사용하려면 호출 경로 연결 |

---

## 8. 한계 / 검증 안 한 것

- 시장 데이터·ICP 인터뷰 0
- 경쟁자(Cursor BG Agents, Devin, Sweep, Aider, OpenHands) 직접 사용 비교 0
- "BYO 로컬 충분"은 가설 — 실제 고객 환경 변동성 검증 필요
- Step 0 ⑤(Pricing) ⑥(SoT)은 가설 단계

다음 검증: ① af-critic + af-cross-review 병렬 ② Codex CLI 크로스체크 (이 문서 다음 단계)

---

## 9. 검증 결과 + 정정 사항 (2026-04-26 추가)

> 검증 출처: **Codex 5.5 (codex exec)** + **af-critic** + **af-cross-review** 3자 병렬
> 핵심 결과: §3 진단 일부에 **오류 있음**. 진단을 그대로 따랐다면 잘못된 곳을 고쳤을 것.

### 9.1 진단 오류 (§3 정정)

| ID | §3 주장 | 실제 코드 검증 | 판정 |
|----|--------|------------|-----|
| **B1** | `core/control/intake.py:262` `_recall_from_memory()` 스텁 | `:262-298` 실제 구현. `UnifiedMemoryFacade.get_instance().search_semantic(task_input, limit=5)` 호출 → EPISODIC/SEMANTIC/PROCEDURAL dict 반환. `project_pipeline.py:625`에서 호출, `:746,:764`에서 `planner.plan(memory_context=memory_context)`로 role_planning까지 전달됨 | ❌ **REJECT** |
| **W3** | `approval_gate.py:127` `is_execution_open()` 실패 시 우회 가능 | `core/project_pipeline.py:992-1001`에서 순서 검증 코드 이미 존재 | ⚠️ **FALSE POSITIVE 가능성** — P0-A에서 직접 재검증 필요 |
| `DocumentIndex` "완전 고아" | 진짜 0 호출 | `core/researcher.py:258, :274` → `IngestionPipeline` → `DocumentIndex` 경로 존재 | ⚠️ **PARTIAL** — 일부 경로 있음, project_pipeline.prepare에서는 호출 안 됨 |
| 중복/분산 board write 2곳 | "2곳에서 board 쓰기" | `core/dynamic_orchestrator.py:699, :733, :770, :788, :826, :849, :878, :891, :1050, :1065 ...` 등 **12곳** | ✅ ACCEPT, 단 **과소평가** — T1-2 단일 진입점 강제는 12곳 정리 작업 |

### 9.2 진단 확정 (코드로 증명됨)

| ID | 증거 | 영향 |
|----|------|-----|
| **B2** | `core/project_pipeline.py:196` `_load_checkpoint` 정의됨, **callsite = 0건**. 저장은 `:175, :180, :682, :716, :788`에서 됨. `agent_launcher.py:468` execute() 호출 직전 로드 없음 | 진단 가장 강한 주장 정확. T1-1의 핵심 수정 대상 |
| Checkpoint 3곳 분산 | `core/hooks/checkpoint.py:32` (`runs/{run_id}/checkpoint.json`) + `core/project_pipeline.py:175` (`.checkpoint/{stage}.json`) + `core/control/lifecycle_bridge.py:161-176` (`.af_runtime/control/checkpoints/{run_id}.json`) | canonical 마이그레이션 필요 |

→ **사용자 목표 ④ 점수 1/10은 잘못된 점수** (B1·DocumentIndex 정정으로). 실제 약점은 "**memory 미연결**"이 아니라 "**벡터 영속화 부재**".

### 9.3 의견 충돌 → 결판

**충돌 1: SoT 결정을 T1 시작 전 게이트로?**

| 의견 | 입장 | 근거 |
|------|------|------|
| Codex 5.5 | YES, T1 게이트 | 마이그레이션 실패 위험 |
| af-critic | NO, 어댑터 패턴 | "결정 기다리다 2~4주 증발" |

**판정: af-critic 승** — 파일 SoT로 시작 → 어댑터 인터페이스 → DB 결정 후 swap. Codex의 마이그레이션 위험은 어댑터 패턴으로 해소.

**충돌 2: T2-5를 "_recall_from_memory 스텁 수정"으로 정의?**

§3 진단이 틀렸으므로(B1 REJECT) T2-5의 첫 단계도 잘못 정의됨. **재정의 필요**: T2-5는 "스텁 수정"이 아니라 "**벡터 영속화 레이어 추가**"가 본질.

### 9.4 BLOCK 3건 (Tier 1 진입 전 해결 필수)

| BLOCK | 위치 | 문제 | 해결 |
|-------|------|------|-----|
| **B-1** | T2-4 완료 기준 | "5번 실행 → 4개 통과"는 통계 부족 | **3분할**: ① smoke (1회 PR 생성) ② idempotency (강제 SIGKILL × 5회 → PR 1건만) ③ success rate (30+ 샘플로 80% 통과) |
| **B-2** | T1-2 idempotency_key | `input_digest`가 모호 — LLM output 포함하면 재시도마다 다른 key | **명시 정의**: `idempotency_key = hash(work_item_id + step_index + external_input_digest)` — `external_input_digest`는 user_request + repo_state_hash + tool_args만 (LLM output 제외) |
| **B-3** | T1-1 worktree snapshot | 동시에 2개 step이 같은 파일 수정하면 snapshot 충돌 정책 미정 | **정책 추가**: step별 worktree branch 격리 + merge 시점에만 snapshot. 충돌 시 last-writer-wins NO, 명시적 conflict 이벤트 발행 |

### 9.5 항목 보강 (정정 반영)

#### T1-1 보강 (3건)

1. **점진적 마이그레이션** (Codex 보강) — 기존 3곳 checkpoint를 한 번에 canonical로 옮기지 않고 **이중 쓰기 phase**(2주) → canonical 검증 → legacy 삭제. 마이그레이션 실패 시 즉시 legacy 복귀 가능.
2. **Worktree 충돌 정책** (B-3) — 위 9.4 참조.
3. **Launcher resume UX** — `agent_launcher.py:468` 직전에 단순 로드만 추가하지 말고, **메뉴**: `[1] 처음부터 [2] 마지막 step부터 재개 [3] 특정 step 선택`. CLI는 `af resume <run_id> [--from-step <id>]`.

#### T1-2 보강 (2건)

1. **idempotency_key 명시 정의** (B-2) — 위 9.4 참조.
2. **단일 진입점 강제 — 12곳 정리** (9.1 정정) — `dynamic_orchestrator.py`의 board 쓰기 12곳을 단일 함수(`_write_board_atomic(work_item_id, state_delta)`)로 라우팅. 직접 board 쓰기 호출은 lint 룰로 차단.

#### T2-4 보강 (1건)

- **완료 기준 3분할** (B-1) — 위 9.4 참조.

#### T2-5 재정의

- 원래 단계 1 ("`_recall_from_memory()` 실제 구현 (B1 수정)") **삭제** — 이미 구현됨.
- 새 단계 1: **벡터 영속화 어댑터 추가** (Supabase pgvector 또는 chroma). `MemoryScope.PROJECT` 데이터의 영속 backend를 명시.
- 새 단계 2: `IngestionPipeline → DocumentIndex` 경로를 `project_pipeline.prepare_documents`에 통합 (현재 researcher 경로만 있음).
- 단계 3-5는 그대로 유지.

### 9.6 시간순 실행 시퀀스 (정정판)

```
[Phase 0 — 완료 ✅ 2026-04-26]
  P0-A: B1 REJECT 확정 (intake.py:262-298 구현됨)
        W3 FALSE POSITIVE 확정 (project_pipeline.py:992-1001 순서 올바름)
  P0-B: 고아 모듈 전부 사용 중 확인 → 삭제 없음
        - document_index.py: ingestion_pipeline.py + retrieval_router.py 사용
        - skill_self_evolution.py: agent_runner.py:977 사용
        - cortex_vector.py: agent_runner.py:1045 조건부 등록
        - sync_compyne.py: agent_runner.py:1051 조건부 등록
  P0-C: W2 수정 완료 (event_bus.py:72-84)
        - hook 단위 try/except 추가 (예외 → block + log)
        - if not result → if result is False (명시적 False만 차단)
        - 비-bool 반환 시 warning log 추가
        - review-gate 통과 (af-test-runner PASS 63개 + af-critic WARN + af-cross-review PASS)
  후속 작업 (T1-1 시작 후):
        - run_post_execute/run_pre_tool_call 예외 처리 비대칭 개선 (af-critic WARN)
        - LangSmithTracingHook stdout 복원 경로 강화 (af-critic WARN)

[이번 주] Step 0 6개 결정 (사용자 직접) ← T2-3

[2~4주] T1-1 + T1-2 (BLOCK 3건 해결 포함)
  - 파일 SoT로 시작 (어댑터 인터페이스)
  - 이중 쓰기 phase 2주 후 legacy 제거
  - worktree 충돌 정책 적용
  - launcher resume 메뉴 + af resume CLI
  - idempotency_key external-input-only
  - 12곳 board write → 단일 진입점

[4~8주] T2-4 + T2-5 병행
  - T2-4: 3분할 완료 기준 (smoke / idempotency / success rate)
  - T2-5: 벡터 영속화 어댑터 (스텁 수정 NO, 새 레이어)

[8~12주] T3-6 + T3-7

[PMF 검증 후] Multi-tenant / heartbeat / marketplace
```

### 9.7 한 줄 결론

> 진단 점수표(②2 ③4 ④1)는 **B1/DocumentIndex/board 12곳 정정**으로 다시 그려야 한다. 단 **B2(checkpoint load 0건) 확정**은 T1-1을 척추로 두는 결정을 더 강하게 정당화한다. 다음 행동은 Phase 0 1~2일 → Step 0 6개 결정 → T1-1 시작.

---

## 10. Step 0 의사결정 — 사용자 확정 (2026-04-26)

> 사용자가 직접 답한 결정. 향후 모든 구현 결정의 기준이 된다.

| # | 항목 | 확정값 | 비고 |
|---|------|------|----|
| ① | Worker runtime | **BYO 로컬 (단기) → 웹 서비스 (장기)** | 2단계 진화. 단기 = 사용자 PC, 장기 = AF 호스팅 SaaS |
| ② | Provider 1순위 | **Codex App Server (장기) + CLI (단기)** | T3-6에서 App Server 전환 |
| ③+④ | 첫 ICP/task | **AF 완성 후 사용자가 본인 테스트 프로젝트로 직접 검증** | T2-4 in-house 데모 폐기, 사용자 자체 검증으로 대체 |
| ⑤ | Pricing | **PMF 후 보류** | 시장 데이터 부재로 결정 미룸 |
| ⑥ | State SoT | **파일 → Postgres (Supabase) swap** | 어댑터 패턴으로 마이그레이션 위험 해소. 웹 서비스 단계와 자연스럽게 맞음 |

### 사용자 목표 4개 명확화

| 목표 | 확정값 |
|------|------|
| ① "끝까지 결과물" | **사용자가 원하는 결과물 (PR + 결과물 실행)**. 종결점 = 사용자 OK |
| ② "재개" | 같은 PC + 미래 다른 PC, 시간 한도 7일 |
| ③ "작은 단위" | **1 기능 = 1 task** (step은 task 내부 더 잘게) |
| ④ "기존 프로젝트 한도" | **무한정 — 언어·크기·구조 비종속 설계**. AF는 범용 서비스가 목표 |

### Step 0 결정이 만든 설계 제약

1. **T1-1/T1-2는 언어·크기·monorepo 비종속** — 특정 언어 AST·특정 크기 가정 금지
2. **T2-4 (수직 슬라이스 in-house 데모) 폐기** → 사용자 자체 검증으로 대체
3. **"AF 완료" 정의** = Phase 0 + T1-1 + T1-2 + 최소 dogfood 1건
4. **결과물 실행 = (b)** — AF가 PR 만들고 사용자가 받아 실행 (CI 의존 X)
5. **SoT 어댑터 인터페이스 필수** — 처음부터 Postgres swap 가능하게 설계

---

## 11. 변경 이력

| 날짜 | 변경 | 출처 |
|------|------|-----|
| 2026-04-26 (초안) | §1~§8 작성 — 전략 합의 + Explore 진단 결과 통합 | Codex 7-phase + Claude 비평 + 1차 합의 + Explore agent 진단 |
| 2026-04-26 (정정) | §9 추가 — 3자 검증 결과, 진단 오류 정정, BLOCK 3건, 항목 보강, 시퀀스 갱신 | Codex 5.5 (codex exec) + af-critic + af-cross-review |
| 2026-04-26 (확정) | §10 추가 — Step 0 6개 결정 + 목표 4개 명확화 + 5개 설계 제약 | 사용자 직접 결정 |
