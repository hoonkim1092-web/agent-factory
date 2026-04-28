# Harness 전략 — Claude × Codex 합의안

> 날짜: 2026-04-26
> 선행 문서:
> - `docs/참고/2026-04-25-harness-market-agent-factory-saas-strategy.md` (Codex 작성, 7-phase 전략)
> - `docs/참고/2026-04-26-harness-strategy-critique.md` (Claude 작성, 비평)
> 작성 방식: Claude가 합의안 초안 → Codex CLI에 직접 의견 요청 → Codex 응답 반영 → 최종 합의
> 결론 한 줄: AF의 척추는 **Resumable Execution**이고, 그 위에 작은 task 1개를 끝까지 굴리는 검증이 다음 행동이다. SaaS·multi-tenant·marketplace는 그 다음.

---

## 1. 사용자가 정한 진짜 목표 (심판 기준)

| # | 목표 | 의미 |
|---|------|------|
| ① | "만들어줘" → 처음부터 끝까지 결과물 | 요구사항~배포까지 한 번에 |
| ② | 토큰 부족 / PC 꺼짐 → **멈춘 자리에서 재개** | **이게 AF의 척추** |
| ③ | 작업을 **아주 작은 단위**로 쪼갬 | ②를 가능하게 하는 메커니즘 |
| ④ | 기존 대형 프로젝트에 붙어서 분석·리팩토링·버그·기능 | "유지보수 가능한 하네스" |

---

## 2. 두 모델이 합의한 사실

### 2.1 동의 (논쟁 없음)

- AF는 Claude Code/Codex/Manus 대체가 아니라 **컨트롤 타워**다
- Codex App Server adapter 필요 (stdout 파싱은 가장 약한 고리)
- RunBudget 글로벌 싱글톤은 SaaS 부적합 → CostEvent + agent/project 단위 attribution
- 영속 RAG가 차별화 핵심 (project-scoped)

### 2.2 충돌 후 합의된 지점

| 쟁점 | Codex 원안 | Claude 비평 | 최종 합의 |
|------|-----------|------------|---------|
| 진행 속도 | 7-phase 동시 설계 | Step 0 + 1 수직 슬라이스 | **Claude 안 채택** — 7-phase는 북극성, 실행은 좁힘 |
| Demo 크기 | repo 5개 | repo 1개 × task 1개 | **부분 채택** — 1 task 맞지만 README 오타급은 NO, "작은 버그/기능"으로 |
| 재개 가능성 위치 | Phase 4 | Step 1에 함의 | **둘 다 수정** — Tier 1로 승격 (Codex가 "내 배치 실수" 인정) |
| Multi-tenant SaaS | Phase 4 핵심 | PMF 후 보류 | **Claude 안 채택** — 사용자 목표에 multi-tenant 없음 |
| Hosted sandbox | Manus류 흡수 | BYO로 충분 | **Claude 안 채택** — 사용자 목표 ④ = 고객 환경 그대로 |

---

## 3. Codex가 보강한 두 가지 (둘 다 채택)

### 3.1 Checkpoint 구성요소 확장

Claude의 "RunEvent + Checkpoint" 스키마만으론 부족하다. 다음 4개를 Checkpoint에 묶어야 진짜 재개가 가능하다.

| 항목 | 의미 | 왜 필요한가 |
|------|------|-----------|
| **idempotency key** | step별 고유 식별자 | 재개 시 중복 PR/중복 commit 방지 |
| **artifact/worktree snapshot** | 파일 상태 스냅샷 | PC 꺼졌다 켜도 같은 파일 상태에서 재개 |
| **next-step cursor** | 다음 실행할 step 포인터 | "어디서 멈췄나"를 명시적으로 |
| **test/acceptance 결과** | 통과한 검증 영속화 | 재개 시 통과했던 test 다시 안 돌림 |

**근거**: 사용자 목표 ②는 단순 이벤트 로그가 아니라 **"재현 가능한 상태 스냅샷"**이 있어야 진짜 작동한다.

### 3.2 Step 0 의사결정 +1 (5개 → 6개)

Codex 추가: **State Source of Truth 결정**.

> RunEvent, Checkpoint, artifact의 권위 저장소가 어디냐?
> - SQLite (로컬 단일 파일, 단일 PC)
> - Postgres (서버, multi-machine 동기화 가능 — 현재 Supabase 사용 중)
> - Object storage (S3 등 — artifact 전용)

**근거**: Tier 1 (1)을 만들려면 "어디에 쓸 건가"를 먼저 정해야 한다. 사용자 목표 ②(다른 PC에서 재개)를 진지하게 다루려면 SQLite 단독은 부족할 수 있음.

---

## 4. 최종 합의안 — 3 Tier 구조

### Tier 1 — 척추 (지금 시작)

#### (1) RunEvent + Checkpoint 스키마

**왜**: 사용자 목표 ②의 직접 구현. 모든 작업이 "이벤트 로그 + 재현 가능 스냅샷"으로 표현되면 PC가 꺼져도 재개 가능.

**구성**:
```
RunEvent {
  tenant_id, project_id, run_id, agent_id, step_id,
  event_type, payload, ts, cost_event_id
}

Checkpoint {
  run_id, step_id,
  idempotency_key,           # Codex 보강
  worktree_snapshot,         # Codex 보강
  next_step_cursor,          # Codex 보강
  test_acceptance_results    # Codex 보강
}
```

**효과**:
- 토큰 한도 초과 → 자동 일시중단 → 한도 복원 시 같은 task부터 재개
- PC 꺼짐 → `af resume <run_id>` → 멈춘 step부터
- Provider(Codex/Claude) 죽어도 다른 provider로 같은 step 재실행

#### (2) Atomic Task Decomposition (5~15분 단위)

**왜**: 사용자 목표 ③의 직접 구현. 큰 task 한 번 실패 = 처음부터 재시작 = 비용·시간 손실.

**메커니즘**: 기존 `core/dynamic_orchestrator.py` task board를 step 단위로 쪼개고, 각 step이 독립적인 RunEvent + Checkpoint를 남기게 한다.

**효과**:
- 토큰 끊겨도 1개 step만 중단됨 (몇 분치 손실)
- 사람 검토도 5분짜리 diff라 부담 적음
- 재시도 비용 최소화

---

### Tier 2 — 시장 진입 (Tier 1 후)

#### (3) Step 0 의사결정 — 6개 (이번 주)

| # | 결정 항목 | 후보 | 메모 |
|---|---------|------|------|
| 1 | Worker runtime | BYO 로컬 / Docker / hosted | **사용자 목표 ④ 기준 BYO 우선** |
| 2 | Provider 1순위 | Codex App Server / Claude API / CLI | |
| 3 | 첫 ICP repo | Python / React / etc | 1개만 |
| 4 | 첫 task 종류 | 작은 버그 / 작은 기능 | **README 오타급 NO** |
| 5 | Pricing 가설 | seat / accepted-PR / token passthrough | |
| 6 | **State source of truth** 🆕 | SQLite / Postgres / Object storage | **Codex 보강** |

**효과**: 1주 투자로 다음 3개월 방향이 추측에서 확정으로.

#### (4) 1 repo × 1 task 수직 슬라이스 (4~8주)

**왜**: 사용자 목표 ① 검증. "끝까지 결과물"이 정말 작동하는지 한 번도 안 해봄.

**범위 (Codex 보강 반영)**:
- 1개 repo
- 1개 task = **"기존 Python repo의 1개 함수 버그 수정 + 회귀 테스트 추가"** 정도
- repo연결 → 분석 → patch → test → PR → cost기록 end-to-end
- 성공률 80% 도달 후에야 확장

**효과**:
- Tier 1의 재개·원자성도 이 슬라이스에서 같이 검증
- 결합 결함을 작게 잡음

#### (5) Project-scoped Persistent Memory

**왜**: 사용자 목표 ④의 차별화. 두 번째 작업이 첫 번째보다 똑똑해져야.

**메커니즘**: `MemoryScope.PROJECT` 토대에 영속 vector store 연결. `project_id` scope를 모든 memory record에 강제.

**효과**:
- 같은 repo 두 번째 PR이 회사 컨벤션 자동 인지
- 같은 원인 실패 반복 안 함
- 리팩토링 시 "이전에 망가뜨린 곳" 회피

---

### Tier 3 — 안정화

#### (6) Codex App Server adapter

**왜**: stdout 파싱이 결함 발생 1순위.
**효과**: long-running 작업이 끊겨도 thread/turn/item 단위로 진행 상태 정확히 복원. Tier 1 재개 가능성이 provider 수준에서도 보장.

#### (7) Approval/Cost/Audit 통합

**왜**: 분산된 trace/hook log/run ledger를 한 schema로.
**효과**: Tier 1 RunEvent가 그대로 audit 로그가 됨. 한 화면에서 디버깅·비용·승인 통합.

---

### 보류 (PMF 후) — Codex도 동의

| 항목 | 보류 사유 |
|------|---------|
| Multi-tenant SaaS Control Plane | 사용자 목표에 "여러 회사 격리" 없음 |
| Background heartbeat maintenance | 검증 메커니즘 약한 상태에서 자동 PR = noise 폭발 |
| Marketplace / Skill 상품화 | PMF 전엔 빈 진열대 |
| Manus류 hosted sandbox | 사용자 목표 ④면 BYO 로컬이 맞음 |

---

## 5. 의견 교환 기록 — Codex 응답 원문

Codex CLI(`codex exec`)에 합의안을 보내고 받은 답변 (2026-04-26T03:02 KST):

```
1. **동의** — 사용자 목표 ②가 제품 척추라서 Tier 1에 RunEvent/Checkpoint와
   atomic task를 두는 게 맞다.

2. **동의** — 재개 불가능하면 "만들어줘 → 끝까지"가 성립하지 않는다.
   내 Phase 4 배치는 후순위로 둔 실수다.

3. **부분동의** — 5개 demo 축소는 맞다. 다만 1 task는 README 오타급이면 안 되고,
   "기존 repo에 붙는 작은 버그/기능"이어야 한다.

4. **부분동의** — 누락: RunEvent만으로는 부족하고 `idempotency key`,
   artifact/worktree snapshot, next-step cursor, test/acceptance 결과까지
   Checkpoint에 묶어야 한다.

5. **부분동의** — Step 0에 하나 추가: **state/source-of-truth 결정**.
   예: SQLite/Postgres/object storage 중 무엇이 RunEvent, Checkpoint,
   artifact의 권위 저장소인가.
```

→ Q4·Q5의 부분동의를 모두 채택. Q3은 task 난이도를 "작은 버그/기능"으로 상향 조정.

---

## 6. 두 모델이 동의한 한 줄

> AF의 척추는 **Resumable Execution**이고, 그 위에 작은 task 1개를 끝까지 굴리는 검증이 다음 행동이다. SaaS·multi-tenant·marketplace는 그 다음.

---

## 7. 다음 행동 (사용자 의사결정 대기)

1. **이번 주**: Step 0 6개 결정 — 사용자가 직접 골라야 함
   - 가장 중요한 두 개: ⑥ source of truth, ① worker runtime
2. **2~4주**: Tier 1 (1)(2) 구현 — `core/events/run_event.py` + `core/checkpoint/`
3. **4~8주**: Tier 2 (4) — 1 repo × 1 task 수직 슬라이스 (작은 버그/기능)

---

## 8. 한계 — 이 합의안이 검증 안 한 것

- 시장 데이터·ICP 인터뷰 없이 작성됨
- 경쟁자(Cursor BG Agents, Devin, Sweep, Aider, OpenHands) 직접 사용 비교 없음
- "BYO 로컬이 빠르다"는 가설은 검증 필요
- Step 0 결정 5번(Pricing) 및 6번(SoT)은 가설 단계

다음 검증: Step 0 6개 결정을 위한 1주 spike + 첫 ICP 1명 인터뷰.
