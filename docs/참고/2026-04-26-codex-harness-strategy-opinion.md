# 코덱스 의견 — Harness 전략 비평에 대한 판단

> 날짜: 2026-04-26
> 대상 문서: `docs/참고/2026-04-26-harness-strategy-critique.md`
> 관련 문서: `docs/참고/2026-04-25-harness-market-agent-factory-saas-strategy.md`
> 결론 한 줄: 비평문의 핵심 판단은 맞다. 지금은 "PR Factory MVP 착수"가 아니라 **Step 0 의사결정 + Step 1 RunEvent 스파이크**가 우선이다.

---

## 1. 총평

`2026-04-26-harness-strategy-critique.md`는 원문 전략 문서보다 실행 판단이 더 좋다.

원문 전략은 Agent Factory의 포지셔닝을 잘 잡았다. AF를 Claude Code, Codex, Manus 같은 실행 에이전트의 대체재가 아니라, 이들을 통제하고 품질을 관리하는 상위 control plane으로 보자는 방향은 타당하다.

하지만 원문은 Phase 1부터 Phase 7까지를 제품 로드맵처럼 펼치면서 실제 실행 난이도를 과소평가했다. 특히 "GitHub repo 연결 + worker 실행 + PR 생성"을 Phase 1 MVP로 둔 것은 너무 크다.

비평문은 이 문제를 정확히 짚고 있다. 다음 행동은 Phase 1 전체 착수가 아니라:

1. worker runtime, provider, ICP repo type, task type, pricing 가설을 고정하는 Step 0
2. run/cost/audit/approval을 담을 RunEvent schema 스파이크

이 두 가지다.

---

## 2. 내가 강하게 동의하는 지점

### 2.1 PR Factory MVP는 생각보다 크다

비평문의 가장 중요한 지적은 Phase 1 "PR Factory MVP"가 실제로는 MVP보다 크다는 점이다.

원문은 다음 흐름을 Phase 1로 둔다.

```text
repo connect
→ baseline scan
→ issue/work-item 생성
→ plan/spec/task board
→ worker 실행
→ test/lint
→ code review
→ PR 생성
→ run report
```

이 흐름을 SaaS에서 안정적으로 제공하려면 최소한 다음 문제가 풀려야 한다.

- worker runtime을 어디서 돌릴 것인가
- GitHub App 또는 PAT를 어떻게 연결하고 보관할 것인가
- branch/worktree 격리와 tenant 격리를 어떻게 분리할 것인가
- 테스트 실행 로그와 diff를 어떻게 audit trail로 남길 것인가
- 실패한 run을 사용자가 이해할 수 있게 어떻게 보고할 것인가

따라서 "demo repo 5개에서 PR 생성"은 첫 단계가 아니라, 1개 repo/1개 task/1개 provider 시나리오가 통과된 이후 목표로 보는 편이 맞다.

### 2.2 RunEvent를 먼저 잡아야 한다

현재 AF에는 실행 이력이 여러 경로에 흩어져 있다.

- `core/control/run_ledger.py`는 run 단위 ledger를 JSONL로 남긴다.
- `core/providers/cli.py`는 provider 실행 결과를 stdout/stderr 기반으로 해석한다.
- `core/run_budget.py`는 글로벌 singleton 형태로 토큰 예산을 추정한다.
- hook log, memory episode, approval snapshot, trace가 서로 다른 구조로 존재한다.

이 상태에서 GitHub PR, SaaS dashboard, approval queue, cost dashboard를 먼저 붙이면 나중에 schema migration 비용이 커진다.

따라서 비평문의 Step 1, 즉 `RunEvent` 스파이크는 우선순위가 높다. 다만 처음부터 DB 중심의 큰 이벤트 플랫폼을 만들 필요는 없다. 기존 `RunLedger`와 맞물리는 append-only JSONL event store로 시작해도 충분하다.

초기 RunEvent는 다음 정도면 된다.

```text
run.started
worker.command_started
worker.command_completed
diff.created
test.completed
cost.recorded
approval.requested
approval.resolved
pr.opened
run.completed
run.failed
```

각 event는 최소한 아래 필드를 가져야 한다.

```text
event_id
event_type
created_at
tenant_id
project_id
repo_id
run_id
agent_id
provider_id
work_item_id
payload
```

### 2.3 Persistent Project RAG는 부가기능이 아니다

원문은 Persistent Project RAG를 Phase 3에 둔다. 비평문은 이것을 Step 2~3에서 같이 봐야 한다고 주장한다. 이 판단에 동의한다.

Agent Factory가 기존 repo 유지보수를 차별화로 삼는다면 repo memory와 project-scoped RAG는 핵심 제품 기능이다.

현재 `DocumentIndex`는 hybrid retrieval 구조를 갖고 있지만, 기본적으로 메모리 중심이고 `.system_generated/cache/document_index.json` 수준의 캐시만 가진다. 이것은 "세션 검색 성능 개선"에는 쓸 수 있지만, SaaS에서 장기적인 repo memory 자산이라고 부르기에는 부족하다.

AF가 반복 유지보수를 잘하려면 다음 데이터가 project/repo scope로 영속화되어야 한다.

- repo 문서와 architecture map
- 이전 PR diff
- 실패한 테스트와 원인
- 성공한 patch pattern
- coding convention
- reviewer 지적 사항
- 승인/거절된 결정

단, cross-project recall은 기본값이 되면 안 된다. 프로젝트 경계 hard filter가 기본이고, cross-project memory는 명시적 opt-in이어야 한다.

---

## 3. 내가 보완하고 싶은 지점

### 3.1 Codex App Server adapter를 너무 늦추면 안 된다

비평문은 "Codex App Server adapter는 PMF 후"라고 정리한다. 큰 구현을 지금 시작하지 말자는 취지는 맞다.

하지만 내부 adapter interface와 RunEvent schema는 지금부터 Codex App Server 같은 provider-native event stream을 수용할 수 있게 설계해야 한다.

현재 CLI provider는 subprocess 실행과 stdout/stderr parsing에 크게 의존한다. 특히 headless 실행을 위해 다음과 같은 모드가 들어가 있다.

- Claude CLI: `--permission-mode bypassPermissions`
- Gemini CLI: `--approval-mode yolo`
- Codex CLI: `--ask-for-approval never`

로컬 실험에서는 쓸 수 있지만 SaaS의 기본 실행 방식으로 오래 유지하기 어렵다.

따라서 권장 순서는 다음이다.

1. 지금은 Codex App Server 전체 구현을 미룬다.
2. 하지만 `WorkerAdapter` interface와 `RunEvent` payload는 thread/turn/item, approval request, diff stream을 받을 수 있게 설계한다.
3. CLI adapter는 이 interface의 첫 구현체로 둔다.
4. 1개 vertical 시나리오가 통과되면 Codex App Server adapter를 두 번째 구현체로 붙인다.

### 3.2 BYO runtime은 빠르지만 제품 가설은 반쪽이다

비평문은 초기에는 hosted sandbox보다 BYO runtime이 빠르다고 본다. 나도 초기 spike에서는 동의한다.

하지만 SaaS 가설을 검증하려면 언젠가 hosted runtime이 필요한지 판단해야 한다. 고객 로컬 환경에 의존하면 다음 문제가 생긴다.

- OS, package manager, language runtime 차이
- secret 접근 방식 차이
- CI와 local test 결과 불일치
- 고객 네트워크/VPN 의존
- 장기 run이 로컬 머신 sleep, network disconnect에 취약

따라서 Step 0의 worker runtime 결정은 "영구 선택"이 아니라 "첫 spike 선택"이어야 한다. 문서에는 다음 gate를 추가하는 편이 좋다.

```text
BYO local로 1개 repo/1개 task E2E 성공
→ 실패 원인의 30% 이상이 local environment variance라면 hosted sandbox spike 착수
→ 아니면 BYO/hybrid 유지
```

### 3.3 시장 검증이 더 필요하다

비평문도 한계로 인정하듯 시장 데이터가 없다.

AF가 PR Factory/AI Software Delivery OS로 가려면 최소한 다음 경쟁 제품을 실제로 써보고 비교해야 한다.

- Cursor Background Agents
- Devin
- Sweep
- Aider
- OpenHands
- Codex cloud/web 흐름

핵심 질문은 "AF도 PR을 만들 수 있는가"가 아니다. 이미 시장에는 PR을 만드는 agent가 많다.

진짜 질문은 이것이다.

```text
왜 사용자는 Cursor/Devin/Codex에 직접 일을 시키지 않고,
그 위에 Agent Factory라는 control plane을 하나 더 둬야 하는가?
```

내 가설은 다음이다.

- 여러 worker를 한 프로젝트 정책 아래 묶어야 할 때
- 반복 실패를 project memory로 줄여야 할 때
- cost/audit/approval이 팀 단위로 필요할 때
- "코드 생성"보다 "품질 게이트 통과한 PR 납품"이 더 중요할 때

하지만 이 가설은 ICP 인터뷰와 경쟁 제품 실사용으로 검증해야 한다.

---

## 4. 권장 실행 순서

### Step 0 — 이번 주 의사결정

다음 5개를 고정한다.

| 항목 | 권장 초기 선택 |
|------|----------------|
| Worker runtime | BYO local |
| Provider | 기존 CLI adapter 유지, interface는 provider-native 대응 가능하게 설계 |
| 첫 ICP repo type | 작고 테스트가 있는 Python/FastAPI 또는 React/Next.js 중 1개 |
| 첫 task type | 작은 bug fix 또는 copy/error-message 개선 |
| Pricing 가설 | beta는 seat + token passthrough, accepted PR credit은 보류 |

### Step 1 — RunEvent 스파이크

목표는 event platform 완성이 아니라 schema 위험 제거다.

해야 할 일:

1. `core/events/run_event.py`를 만든다.
2. append-only JSONL store를 둔다.
3. 기존 `RunLedger` open/update/close 시점에 RunEvent를 같이 남긴다.
4. CLI provider 완료 결과를 `worker.command_completed`로 남긴다.
5. RunBudget 기록을 `cost.recorded`로 남길 수 있는 최소 구조를 만든다.

성공 기준:

- run 1건에 대해 시작, worker 결과, cost, 종료 event가 한 timeline으로 복원된다.
- event에 `project_id`, `repo_id`, `run_id`, `agent_id`, `provider_id`가 빠지지 않는다.

### Step 2 — 1개 시나리오 수직 완성

초기 목표는 demo repo 5개가 아니다.

```text
1개 GitHub repo
1개 worker provider
1개 task type
1개 PR
1개 test result
1개 cost event
1개 run report
```

이 흐름이 안정적으로 끝나야 Phase 1 MVP라고 부를 수 있다.

### Step 3 — Project-scoped RAG 영속화

1개 repo에서 두 번째 작업을 수행할 때 planning 품질이 좋아지는지 확인한다.

성공 기준:

- 이전 실패 원인이 다음 run prompt 또는 planning에 반영된다.
- 이전 PR diff와 test 결과가 검색된다.
- project boundary가 깨지지 않는다.

### Step 4 — Provider-native adapter 판단

CLI provider로 충분한지, Codex App Server adapter가 필요한지 측정한다.

판단 기준:

- stdout/stderr parsing failure 빈도
- approval/diff/progress stream 필요성
- long-running worker 복원 필요성
- 사용자가 run dashboard에서 보고 싶어 하는 event granularity

---

## 5. 결론

비평문의 방향은 맞다.

원문 전략의 포지셔닝은 유지하되, 실행은 훨씬 좁혀야 한다.

내 최종 판단은 다음과 같다.

```text
원문 전략 = 북극성
비평문 = 실행 가능한 압축 로드맵
다음 행동 = Step 0 의사결정 + RunEvent 스파이크
```

단, Step 0에는 엔지니어링 의사결정만 넣으면 부족하다. ICP 인터뷰와 경쟁 제품 실사용 비교도 같이 들어가야 한다. AF의 진짜 리스크는 "PR을 만들 수 있느냐"가 아니라, "이미 강한 coding agent들 위에 AF control plane을 하나 더 둘 이유가 충분하냐"이기 때문이다.
