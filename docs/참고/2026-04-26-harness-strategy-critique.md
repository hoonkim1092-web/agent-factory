# Harness 시장 전략 문서 비평 — Agent Factory 관점

> 날짜: 2026-04-26
> 대상 문서: `docs/참고/2026-04-25-harness-market-agent-factory-saas-strategy.md`
> 작성 목적: 위 전략 문서를 깊게 읽고 동의/반대/누락 지점을 정리하고, 실행 가능한 단계로 재구성한다.
> 결론 한 줄: 포지셔닝 진단(§1, §4, §10)은 90% 정확하지만, 로드맵(§5~§8)은 7-phase를 동시에 그려서 실행 위험이 높다. **Phase 1 시작이 아니라, "Step 0 의사결정 5건 + Step 1 RunEvent 스파이크"가 다음 행동**이다.

---

## 1. 문서가 잘 짚은 것 (동의)

| 주장 | 평가 | 근거 |
|------|------|------|
| "AF는 Claude Code 대체가 아니라 control plane이다" | **정확** | 이번 세션에서도 Memory/FSA/Episode/Lineage/Approval/Strategy 6개 plane이 이미 분리돼 있음을 확인 |
| "Codex App Server JSON-RPC adapter로 옮겨야 한다" | **정확** | `core/providers/cli.py`의 stdout parsing은 실제로 가장 취약한 통합 지점. 이번 세션 결함 다수가 stdout 파싱 경계에서 발생 |
| "RunBudget 글로벌 싱글톤은 SaaS 부적합" | **정확** | Phase A Step 2 작업 중 동일하게 확인. agent별 cost attribution 없음 |
| "evidence/RAG가 영속 자산이 아니라 세션 캐시" | **정확** | `DocumentIndex`는 in-memory 위주, persistent vector store 미구현 |
| "Control plane / execution plane 분리" | **정확** | 이미 AF 내부에서 일부 분리 시작됨 (`core/control/*` sidecar) |

---

## 2. 문서가 잘못 짚었거나 과소평가한 것 (반대)

### (a) Phase 1 "PR Factory MVP"의 숨은 비용을 안 다룸

"GitHub repo 연결 + worker 실행 + PR 생성"을 demo 5개에서 돌리려면:

- **Worker runtime**: 지금 AF는 로컬 Claude/Codex CLI 의존이다. SaaS면 이걸 어디서 돌릴지가 진짜 문제. Docker? Firecracker VM? Manus류 sandbox? 문서는 이 질문 자체를 스킵했음.
- **GitHub App scaffolding** 단독으로 2~3주 (webhook, OAuth, installation, permission scope, secret 보관)
- **Worktree 격리** ≠ tenant 격리. 두 개 별도 문제.

→ "demo repo 5개"는 Phase 1이 아니라 **Phase 1.5~2 규모**다.

### (b) "7-phase" 구조가 너무 평탄(flat)

6개 phase가 전부 "필수, 핵심, 표준"으로 나열됐는데, 실제로는 **Phase 1 + Phase 3 + Phase 5 게이트 일부**만 잘 되면 시장에 내놓을 수 있다. Phase 4 SaaS Control Plane 전체와 Phase 6 Background Maintenance는 product-market fit 확인 **이후** 작업이다. 지금 다 동시 설계하면 망한다.

### (c) "기존 repo 유지보수가 차별화"라는 주장 — 부분 동의

방향은 맞지만 실행 가능성이 약하다. 대형 repo 유지보수의 진짜 어려움:

- 기업 코드베이스 RAG는 보안/IP 문제로 클라우드 호스팅이 어렵다 → on-prem 또는 VPC 필요
- "동일 원인 실패 반복 안 함"은 episode memory만으론 안 됨. 회사별 코딩 컨벤션·아키텍처 규칙을 학습/검증하는 별도 레이어 필요

문서는 이걸 "project-scoped RAG"로 한 줄 처리했지만, 실제로는 제품의 절반이다.

### (d) "Manus/Paperclip/Codex의 좋은 점 흡수" — 위험한 표현

좋은 걸 다 흡수하겠다는 로드맵은 거의 항상 어느 것도 못 한다. **하나만 골라야 한다.**

권장:
- Paperclip식 control plane은 tenant/budget/audit만 뽑는다
- Manus sandbox는 **버린다** (SaaS 초기엔 BYO-runtime이 훨씬 빠르다)
- Codex App Server adapter는 PMF 후에 한다 (CLI provider 안정화가 우선)

---

## 3. 문서가 빠뜨린 것 (gap)

1. **Worker runtime 의사결정** — BYO(고객 로컬) vs hosted sandbox vs hybrid. 회사 비용 구조 전체를 결정한다.
2. **Anthropic/OpenAI API 직접 사용 vs CLI wrapping** — CLI(Claude Code, Codex CLI)는 SaaS에서 호스팅하기 매우 어렵다. API 직접 호출로 가야 할 수도. 이때 "Claude Code subagent 활용" 주장은 깨진다.
3. **데이터 잔류(data residency) / SOC2 / GDPR** — enterprise repo 만지면 법적 제약이 즉시 걸린다. Phase 4 governance에 명시 안 됨.
4. **Pricing model이 "accepted PR credit" 1줄** — 가장 어려운 부분인데 한 줄. 토큰 cost가 PR당 $5~50 변동인데 credit 모델이 어떻게 성립하는지 분석 없음.
5. **경쟁자 누락** — Cursor Background Agents, Devin, Cognition Lab, Sweep, Aider, OpenHands가 분석에 없다. 이들은 "PR Factory" 시장 정확히 노린다.

---

## 4. 재구성된 실행 단계 (권장)

> 문서의 7-phase는 **북극성**으로 두고, 실제 실행은 다음으로 좁힌다.

### Step 0 (이번 주) — 의사결정 5개 고정

- [ ] Worker runtime: BYO local / hosted Docker / Firecracker — **하나 선택**
- [ ] Provider 우선순위: Codex App Server vs Claude API vs Claude Code CLI — **1순위 1개**
- [ ] 첫 ICP repo type: Python/Django? React/Next.js? — **1개**
- [ ] 첫 task type: bug fix? small feature? dep update? — **1개**
- [ ] Pricing model 가설: seat / accepted-PR / token-passthrough — **1개**

이 5개 결정 없이 Phase 1 MVP 진입 금지. 문서 §4.3 "최종 포지션"에서 이걸 안 풀었다.

### Step 1 (2~4주) — Event Schema + RunEvent 스파이크

- 문서 §8.2 1번 `core/events/run_event.py` 우선
- 모든 기존 trace/hook/ledger를 통합 RunEvent로 정규화
- `tenant_id, project_id, repo_id, run_id, agent_id, cost_event_id` 필드 의무
- **이걸 먼저 안 하면** Phase 1~6 전부 schema migration이 발생함

### Step 2 (4~8주) — 한 시나리오를 *수직*으로 완성

문서 §8.3 demo 시나리오를 **하나의 specific repo에서** end-to-end로:

- 1개 GitHub repo
- 1개 worker provider
- 1개 task type ("README 오타 수정"부터)
- PR 생성 + test 결과 + cost 1건이 RunEvent로 남음
- 성공률 80%까지

이 단계를 통과해야 Phase 1 MVP라고 부를 수 있다. 문서의 "demo repo 5개"는 이 다음.

### Step 3 (Step 2 후) — Persistent Project RAG

- 문서는 Phase 3에 뒀지만 **차별화 핵심이라 Step 2~3에서 동시에**
- `project_id` scoping을 `core/memory_system/facade.py`에 강제
- 이번 세션에서 만든 `MemoryScope.PROJECT` 토대 활용

### Step 4 (Step 3 후) — Codex App Server adapter

- 문서 Phase 2지만 ROI 측정 후 진행
- stdout parsing 대비 안정성을 측정해서 결정

### Step 5 (PMF 후에만) — Tenant/Budget/Audit (문서 Phase 4)

- 단일 사용자에서 PMF 안 나오면 multi-tenant는 노력 낭비
- 외부 자금 조달 또는 첫 enterprise 계약 시점에 매칭

### 유보 (지금 하지 말 것)

- Phase 6 Background Maintenance — heartbeat가 만든 PR이 검증되는 메커니즘이 약한 상태에서 돌리면 noise 폭발
- Phase 7 Marketplace — PMF 전 marketplace는 빈 진열대
- Manus-like sandbox — BYO로 충분한지 먼저 확인

---

## 5. 결론

문서의 **포지셔닝(§1, §4, §10)은 90% 정확**하다. 하지만 **로드맵(§5~§8)은 7개 phase를 동시에 그려서 실제 실행에는 위험**하다.

지금 AF의 통합 결함을 잡은 직후 단계라면, 다음 행동은:

1. **"Phase 1 MVP 시작"이 아니다.**
2. **"Step 0 의사결정 5건 + Step 1 RunEvent 스파이크"** 두 개다.

이 두 개가 끝나야 Phase 1을 시작할 자격이 생긴다.

---

## 6. 첨언 — 이 비평이 가진 한계

- 시장 데이터 없이 작성됐다. ICP 인터뷰 5건만 해도 위 단계 절반은 다시 짜야 할 수 있다.
- 경쟁자(Cursor BG Agents, Devin, Sweep, Aider, OpenHands) 직접 사용 후 비교가 빠졌다.
- "BYO runtime이 더 빠르다"는 가설은 검증 필요. 실제로 고객사 로컬 환경 변동성이 크면 hosted sandbox가 결국 필요해진다.

다음 검증 단계: 위 Step 0 5개 의사결정을 위한 1주 spike.
