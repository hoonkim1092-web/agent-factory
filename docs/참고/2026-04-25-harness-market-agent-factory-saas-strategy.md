# AI 하네스 시장 비교 및 Agent Factory SaaS 전략

> 날짜: 2026-04-25
> 분석 대상: Claude Code, OpenAI Codex Harness/App Server, Manus, Paperclip, 최신 agent harness 패턴
> 분석 목적: `agent-factory`가 SaaS로 가치가 있는지 판단하고, 초기 프로젝트 생성과 기존 대형 프로젝트 유지보수/업데이트를 자동화하는 제품 방향을 정의한다.
> 결론: `agent-factory`는 실행 에이전트가 아니라, 실행 에이전트들을 고용하고 통제하는 `AI Software Delivery OS`로 가야 가치가 있다.

---

## 1. Executive Summary

`agent-factory`는 Claude Code, Codex, Manus를 직접 대체하는 제품으로 가면 승산이 낮다.
이들은 이미 실행 에이전트, IDE/CLI UX, 모델 통합, sandbox, approval, diff streaming, cloud runtime에서 강하다.

하지만 `agent-factory`가 다음 포지션을 잡으면 충분히 가치가 있다.

```text
Agent Factory = 기존 repo와 새 프로젝트를 끝까지 굴리는
Control Plane + Quality Plane + Memory Plane 기반 AI Software Delivery OS
```

즉, 사용자가 "이거 만들어줘", "기존 프로젝트에 기능 추가해줘", "버그 고쳐줘", "계속 유지보수해줘"라고 요청하면 AF는 다음을 담당한다.

1. 요청을 issue/work-item으로 정리한다.
2. 기존 repo와 문서를 인덱싱한다.
3. 요구사항, 설계, 작업 보드, acceptance criteria를 만든다.
4. Claude/Codex/Gemini/기타 worker를 adapter로 실행한다.
5. 테스트, 리뷰, 회귀 검증, 승인 게이트를 통과시킨다.
6. PR, preview, deploy, rollback, follow-up ticket까지 관리한다.
7. 이후 유지보수 작업을 memory와 heartbeat 기반으로 이어간다.

핵심 판단:

| 질문 | 판정 |
|------|------|
| AF가 Claude Code보다 좋은 코딩 CLI가 되어야 하나? | 아니오. 실행 plane은 Claude/Codex를 adapter로 써야 한다. |
| AF가 Manus처럼 범용 업무 agent가 되어야 하나? | 아니오. 범용 autonomous worker는 범위가 너무 넓다. |
| AF가 Paperclip처럼 control plane을 가져야 하나? | 예. 단, Paperclip 복제가 아니라 software delivery 특화 control plane이어야 한다. |
| AF의 차별화는 무엇인가? | project planning, quality gate, repo maintenance memory, multi-worker orchestration, skill forge. |
| SaaS 가치가 있나? | 있다. 단, CLI 실험체가 아니라 tenant/repo/run/cost/audit/approval 중심 서비스로 재구성해야 한다. |

---

## 2. 외부 하네스 분석

### 2.1 Claude Code

Claude Code의 본질은 로컬/IDE 중심 agentic coding harness다.
공식 문서 기준으로 설정 파일, memory file, permission rule, hooks, MCP, subagent, slash command가 강하게 통합되어 있다.

핵심 기능:

| 축 | 내용 |
|----|------|
| Project memory | `CLAUDE.md`, project/user 설정, startup context |
| Permissions | allow/ask/deny rule, additionalDirectories, bypass 제한 |
| Hooks | `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `SessionStart`, `Stop`, `SubagentStop` 등 |
| Subagents | 별도 context window, 별도 tools, task-specific system prompt |
| Tooling | Bash, Edit, MultiEdit, Read, Grep, Glob, WebFetch, WebSearch, TodoWrite 등 |
| MCP | 외부 tool/data source 연결 |

Claude Code가 강한 부분:

- 로컬 개발자의 실제 작업 루프에 밀착되어 있다.
- permission과 hook이 IDE/CLI 사용성에 자연스럽게 붙어 있다.
- subagent가 별도 context를 가지기 때문에 context pollution을 줄일 수 있다.
- `.claude/agents`, `CLAUDE.md`, settings 계층이 팀 단위 운영에 적합하다.

AF와의 차이:

| 항목 | Claude Code | Agent Factory |
|------|-------------|---------------|
| 주 객체 | coding session | project/run/work-item/role |
| 강점 | 코드 수정 UX, local tool loop | 프로젝트 계획, 역할 분해, approval gate, multi-provider |
| 약점 | 장기 multi-project control plane은 제한적 | 실행 UX와 provider-native 기능은 약함 |
| AF 전략 | worker로 사용 | Claude를 지휘하는 상위 plane |

AF가 흡수해야 할 것:

- project/user/enterprise 설정 precedence 모델
- hook event 표준화
- subagent 별도 context window 개념
- permission rule을 SaaS policy로 승격
- `CLAUDE.md`류 repo-local instruction file 자동 생성/관리

AF가 따라 하면 안 되는 것:

- Claude Code 같은 단일 로컬 coding CLI UX를 직접 경쟁 대상으로 삼는 것
- SaaS에서 `bypassPermissions`류 모드를 기본 운영 방식으로 쓰는 것

---

### 2.2 OpenAI Codex Harness 및 App Server

Codex의 핵심은 단일 CLI가 아니라 여러 제품 표면을 지탱하는 공통 harness다.
OpenAI 공개 글에 따르면 Codex web app, CLI, IDE extension, macOS app은 같은 Codex harness 위에서 동작하고, App Server가 client-friendly bidirectional JSON-RPC API 역할을 한다.

핵심 구조:

| 축 | 내용 |
|----|------|
| Harness | Codex agent loop, thread/session persistence, config/auth, sandbox tool execution |
| App Server | long-lived process, JSON-RPC over stdio, stable UI-ready event stream |
| Conversation primitives | thread, turn, item |
| Streaming | `item/started`, delta, `item/completed`, `turn/completed` |
| Approval | tool/action approval request가 turn을 pause하고 client 응답을 기다림 |
| Integration pattern | IDE, desktop, web, TUI가 같은 harness event protocol을 사용 |

Codex가 강한 부분:

- thread/turn/item primitive가 UI와 automation에 적합하다.
- diff, approval, command execution, streaming progress를 event stream으로 표현한다.
- Codex Web은 container runtime에서 long-running work를 이어갈 수 있다.
- App Server는 "Codex를 내 제품 안에 넣는" 가장 강한 통합 지점이다.

AF와의 차이:

| 항목 | Codex Harness | Agent Factory |
|------|---------------|---------------|
| 주 객체 | thread/turn/item | project/role/task board/run |
| 통합 표면 | App Server JSON-RPC | subprocess CLI wrapper 중심 |
| 강점 | 안정적 agent loop, UI event stream, approval primitive | project-level planning, multi-agent role orchestration |
| 약점 | 제품 수준 control plane은 Codex 외부에서 설계해야 함 | Codex-native event/diff/approval를 충분히 활용 못 함 |
| AF 전략 | Codex App Server adapter 구축 | Codex worker들을 project board에 붙임 |

AF가 흡수해야 할 것:

- `thread`, `turn`, `item`에 해당하는 내부 event schema
- approval request를 run event로 다루는 방식
- diff/test/progress streaming
- Codex App Server를 subprocess `codex exec`보다 우선하는 adapter로 도입
- web UI가 reconnect해도 run 상태를 이어받는 server-side source of truth

AF가 따라 하면 안 되는 것:

- App Server를 무시하고 계속 CLI stdout parsing에 의존하는 것
- Codex와 같은 범용 coding UI를 새로 만들려는 것

---

### 2.3 Manus

Manus의 본질은 범용 autonomous worker다.
공식 문서는 Manus를 단순 chatbot이 아니라 자기 virtual computer를 가진 agent로 설명한다.
Manus는 sandbox 환경, internet access, persistent file system, software install, custom tool creation을 통해 end-to-end 결과물을 만드는 방향이다.

핵심 기능:

| 축 | 내용 |
|----|------|
| Cloud sandbox | task별 격리 VM, filesystem, browser, network, software tools |
| Long task autonomy | 사용자가 단계별로 붙어 있지 않아도 계획, 실행, 산출물 생성 |
| File/artifact | task attachment, generated artifact, sandbox files |
| API | projects, tasks, files, webhooks, connectors |
| Browser/Desktop | local browser operator, desktop "My Computer"로 local file/terminal 접근 |
| Skills | `SKILL.md` 기반 workflow packaging, script execution, progressive disclosure |

Manus가 강한 부분:

- 사용자가 로컬 개발환경을 준비하지 않아도 cloud VM에서 실행한다.
- 결과물 중심 UX가 강하다.
- browser automation, code execution, file operations를 하나의 action environment로 묶는다.
- API로 task lifecycle과 file/webhook integration을 제공한다.

AF와의 차이:

| 항목 | Manus | Agent Factory |
|------|-------|---------------|
| 주 객체 | autonomous task/project | software project/work-item/role/run |
| 강점 | cloud execution, 범용 업무 자동화, zero setup | 기존 repo 유지보수, quality gate, role-based delivery |
| 약점 | software engineering governance와 repo-specific memory는 별도 제품화 필요 | cloud sandbox와 polished UX가 부족 |
| AF 전략 | 범용 Manus 복제 금지 | repo delivery 특화 제품으로 좁힘 |

AF가 흡수해야 할 것:

- task sandbox lifecycle
- artifact/file delivery UX
- API-first task/project/files/webhooks
- user가 브라우저를 닫아도 서버가 run을 계속 굴리는 구조
- skill packaging과 workflow reuse

AF가 따라 하면 안 되는 것:

- "무엇이든 다 하는 agent" 포지션
- 일반 사무 자동화, 웹 리서치, 이메일, CRM 등 모든 vertical을 한 번에 먹으려는 것

---

### 2.4 Paperclip

Paperclip의 본질은 execution plane이 아니라 control plane이다.
공식 문서는 Paperclip을 autonomous AI companies를 위한 control plane으로 정의하고, agent는 외부에서 실행되며 adapter가 control plane에 연결한다고 설명한다.

핵심 기능:

| 축 | 내용 |
|----|------|
| Company | company가 1급 객체, multi-company isolation |
| Org chart | agent hierarchy, role, reporting line |
| Goal alignment | company/project/agent/task goal ancestry |
| Heartbeat | agent가 주기적으로 wake up해서 assignment 확인 |
| Ticket system | issue/comment 중심 task management |
| Budget | agent/company 월 예산, token/cost event 추적 |
| Governance | approval gate, pause/terminate, audit trail |
| Adapter | Claude Code, Codex, Gemini, OpenCode 등 runtime adapter |

Paperclip이 강한 부분:

- 여러 agent를 "회사 조직"으로 관리한다.
- cost와 budget을 agent 단위로 강제한다.
- heartbeat protocol이 명확하다.
- task checkout과 budget enforcement를 atomic하게 설계한다.
- control plane과 execution plane을 분리한다.

AF와의 차이:

| 항목 | Paperclip | Agent Factory |
|------|-----------|---------------|
| 주 객체 | company/employee/issue/heartbeat | project/role/board/work-item/run |
| 강점 | governance, budget, org chart, multi-company UI | quality plane, planning, skill forge, repo implementation pipeline |
| 약점 | code quality/repo delivery 자체는 adapter 책임 | SaaS control plane과 UI가 약함 |
| AF 전략 | Paperclip식 control plane을 흡수 | software delivery 특화로 차별화 |

AF가 흡수해야 할 것:

- tenant/company/project/agent schema
- per-agent monthly budget
- cost event API
- durable issue/ticket queue
- heartbeat protocol
- agent adapter interface
- multi-company isolation
- audit log 일원화

AF가 따라 하면 안 되는 것:

- "AI 회사 운영"이라는 너무 넓은 product category를 그대로 복제
- software delivery quality plane을 포기하고 순수 관리 UI가 되는 것

---

### 2.5 기타 최신 하네스 패턴

최근 agent harness의 방향은 다음으로 수렴한다.

| 패턴 | 의미 | AF 적용 |
|------|------|---------|
| Control plane / execution plane 분리 | 관리/승인/예산과 실제 실행을 분리 | 필수 |
| Event stream primitive | tool, diff, approval, message를 typed event로 저장 | 필수 |
| Context isolation | subagent/fork/sandbox로 context pollution 방지 | 필수 |
| Durable task state | 브라우저/터미널이 꺼져도 run 지속 | SaaS 필수 |
| Skills / playbooks | 반복 업무를 재사용 가능한 절차로 패키징 | AF 강점화 |
| Approval as protocol | 승인 요청이 UI event와 policy object로 존재 | 필수 |
| Per-agent cost | agent/team/project별 cost attribution | 필수 |
| Repo-aware memory | 기존 프로젝트의 결정, 실패, 테스트, 설계를 기억 | AF 차별화 |

---

## 3. 현재 Agent Factory의 위치

현재 AF는 단순 CLI가 아니라 이미 상당한 하네스 구조를 갖고 있다.

주요 구현 근거:

| AF 구성 | 현재 역할 |
|---------|----------|
| `agent_launcher.py` | AgentFactory 조립, request routing, project pipeline 진입 |
| `core/project_pipeline.py` | brief/evidence, role plan, task board, work-item 문서, approval 후 execute |
| `core/approval_gate.py` | 승인 시 문서 hash snapshot 저장, 승인 후 변경 감지 |
| `core/dynamic_orchestrator.py` | 역할별 task dispatch, board 기반 실행, failure/FSA/review task injection |
| `core/agent_runner.py` | tool registry, hooks, memory hooks, CLI provider fallback |
| `core/providers/cli.py` | Claude/Gemini/Codex CLI 실행 adapter |
| `core/control/*` | maintenance/control sidecar의 초기 구현 |
| `core/memory_system/*` | UnifiedMemoryFacade, graph/episode/semantic memory 기반 |
| `core/document_index.py` | local hybrid retrieval 기반 |

AF의 현재 강점:

- project-level planning과 execution이 분리되어 있다.
- approval gate가 문서 hash 기반으로 존재한다.
- Claude/Gemini/Codex CLI를 provider로 감싸고 있다.
- multi-agent role materialization과 dynamic orchestrator가 있다.
- skill procurer/forge 계층이 있어 agent capability 확장 방향이 있다.
- memory facade와 knowledge graph 기반 장기 운영 청사진이 있다.

AF의 현재 약점:

- SaaS tenant/company/account 모델이 없다.
- UI가 아니라 CLI 중심이다.
- run/cost/audit/event schema가 분산되어 있다.
- `RunBudget`이 글로벌 싱글톤이며 agent별 cost attribution이 약하다.
- Codex App Server 같은 provider-native integration이 없다.
- subprocess stdout parsing 의존도가 높다.
- sandbox/secret isolation/worktree isolation이 SaaS 수준이 아니다.
- "사용자가 맡기고 나중에 결과를 보는" durable background service 구조가 아직 약하다.
- 영속 RAG가 설계 단계에 가깝고, evidence가 장기 자산으로 충분히 재사용되지 않는다.

---

## 4. 가치 판단

### 4.1 가치가 있는 이유

AF는 이미 단일 agent 실행기가 아니라 project delivery harness 방향으로 자라고 있다.
시장에서는 Claude/Codex/Manus 같은 실행 agent가 강해질수록 오히려 이를 통제하고 조합하는 상위 plane의 가치가 커진다.

사용자 입장에서 진짜 pain은 다음이다.

- agent가 코드는 쓰지만 전체 프로젝트를 끝까지 책임지지 않는다.
- 기존 대형 repo에 붙이면 context를 자주 잃는다.
- 여러 agent 탭/터미널을 사람이 직접 관리해야 한다.
- 비용과 실패 원인을 나중에 알기 어렵다.
- 기능 추가 후 테스트, 리뷰, 문서, 배포, 회귀 확인이 끊긴다.
- 같은 실수를 다음 작업에서 반복한다.

AF가 이 pain을 해결하면 SaaS 가치가 있다.

### 4.2 가치가 없어지는 방향

다음 방향으로 가면 가치가 약해진다.

1. Claude Code보다 좋은 로컬 coding CLI를 만들려는 방향
2. Manus처럼 모든 업무를 다 하는 범용 autonomous agent가 되려는 방향
3. Paperclip처럼 범용 AI company control plane만 복제하는 방향
4. planning 문서만 만들고 실제 PR/test/deploy 결과물이 약한 방향
5. skill forge를 강조하지만 실사용 품질/검증/비용 통제가 없는 방향

### 4.3 최종 포지션

추천 포지션:

```text
Agent Factory SaaS:
AI Software Delivery OS for new builds and existing codebase maintenance.
```

한글 제품 정의:

```text
사용자가 만들고 싶은 것 또는 고치고 싶은 것을 말하면,
AF가 repo/context를 이해하고, 작업을 분해하고, 적절한 AI worker를 실행하고,
테스트/리뷰/승인/PR/배포까지 이어서 결과물을 내는 소프트웨어 납품 운영체제.
```

---

## 5. SaaS 제품 방향

### 5.1 첫 ICP

초기 고객은 "AI를 써서 소프트웨어를 만들고 싶지만 agent orchestration을 직접 관리하기 싫은 팀"이다.

우선순위:

1. 기존 GitHub repo를 가진 작은 SaaS 팀
2. 반복 유지보수/버그 수정이 많은 에이전시
3. 레거시 코드베이스에 기능 추가가 필요한 개발팀
4. 빠른 MVP를 만들고 싶은 founder

초기부터 enterprise 전체를 노리면 안 된다.
먼저 repo 연결 후 실제 PR을 안정적으로 만드는 제품이 되어야 한다.

### 5.2 핵심 use case

| Use Case | 설명 | MVP 포함 여부 |
|----------|------|---------------|
| 새 프로젝트 생성 | 요구사항에서 repo/project skeleton, 기능 구현, 테스트, 실행 방법 생성 | 포함 |
| 기존 repo 기능 추가 | issue 입력, codebase 분석, branch/worktree 생성, PR 제출 | 최우선 |
| 버그 수정 | failing test/log 입력, 원인 분석, patch, regression test | 최우선 |
| dependency/security update | Dependabot/Snyk/GitHub alert 기반 patch | Phase 2 |
| recurring maintenance | heartbeat로 주기적 품질 점검 | Phase 3 |
| deploy/preview | Vercel/Render/Fly/Cloud Run preview URL 생성 | Phase 2 |
| product backlog execution | PM이 backlog 넣으면 AF가 순차 처리 | Phase 3 |

### 5.3 제품 3계층

AF SaaS는 반드시 3계층으로 분리해야 한다.

```text
1. Control Plane
   tenant, repo, issue, assignment, run, approval, cost, audit, heartbeat

2. Quality Plane
   evidence, spec, design, task board, code review, test gate, regression gate

3. Memory Plane
   repo memory, decisions, failures, successful patches, architecture map, project RAG
```

이 구조는 기존 `docs/super_harness_3_layer_architecture.md`의 방향과 일치한다.

---

## 6. 명시적 실행 단계

### Phase 0. 포지션 고정

목표:

- AF를 "AI Software Delivery OS"로 정의한다.
- "범용 autonomous company"와 "로컬 coding CLI"를 비목표로 문서화한다.

해야 할 일:

1. 제품 문구를 `new project + existing repo maintenance`로 고정한다.
2. landing/pitch 문서에서 "Claude/Codex 대체" 표현을 제거한다.
3. "Claude/Codex/Manus는 worker 또는 external execution service"라는 원칙을 확정한다.
4. repo 기준 성공 KPI를 정한다.

KPI:

- issue-to-PR 성공률
- PR test pass rate
- manual intervention count
- cost per accepted PR
- retry/failure recovery rate

---

### Phase 1. PR Factory MVP

목표:

사용자가 GitHub repo와 작업 설명을 넣으면 AF가 branch/worktree에서 수정하고 PR을 만든다.

MVP 흐름:

```text
User request
→ repo connect
→ baseline scan
→ issue/work-item 생성
→ plan/spec/task board
→ worker 실행
→ test/lint
→ code review
→ PR 생성
→ run report
```

필수 구현:

1. GitHub App 또는 PAT 기반 repo 연결
2. tenant/project/repo/run 최소 DB schema
3. worktree/branch isolation
4. worker adapter v1: `codex_cli`, `claude_cli` 유지
5. run event 저장: message, command, diff, approval, test, cost
6. PR 생성 API
7. 실패 시 원인과 다음 action 표시

기준:

- demo repo 5개에서 "작은 버그 수정" PR 자동 생성
- 테스트 성공/실패 로그가 UI 또는 run report에 남음
- 모든 파일 변경이 diff로 표시됨

---

### Phase 2. Provider-Native Adapter 승격

목표:

CLI stdout parsing 기반에서 벗어나 provider-native harness를 최대한 활용한다.

우선순위:

1. Codex App Server adapter
2. Claude Code hooks/session adapter 정식화
3. Gemini/OpenCode/OpenHands류는 generic process adapter로 유지

해야 할 일:

- Codex App Server JSON-RPC client 구현
- 내부 event schema를 `thread/turn/item` 유사 구조로 정리
- approval request를 UI event로 저장
- diff/test/tool event를 streaming 가능하게 저장
- worker adapter interface를 Paperclip처럼 server/ui/cli 역할로 분리

성공 기준:

- long-running Codex worker의 progress/diff/approval를 AF UI에서 실시간 표시
- 사용자가 tab을 닫아도 run이 계속 진행
- reconnect 시 동일 timeline 복원

---

### Phase 3. Persistent Project RAG 및 Memory

목표:

AF의 차별화인 기존 repo 이해와 유지보수 성능을 강화한다.

우선순위:

1. NotebookLM/web/local evidence를 청크화해 project-scoped store에 저장
2. repo 문서, architecture, test, run trace, PR diff를 인덱싱
3. 실패/성공 episode를 memory로 승격
4. cross-project memory는 opt-in으로 제한

해야 할 일:

- `project_id`, `tenant_id`, `repo_id` scope를 모든 memory record에 넣기
- `notebook_summary`를 plain text가 아니라 chunk/artifact로 저장
- `DocumentIndex`를 세션성 cache에서 persistent vector store로 승격
- recall 결과가 brief, task board, worker prompt에 들어가는 경로 만들기
- domain contamination 방지: project boundary hard filter

성공 기준:

- 같은 repo에서 두 번째 작업의 planning 품질이 개선됨
- 동일 원인 실패를 반복하지 않음
- evidence source가 run report에 남음

---

### Phase 4. SaaS Control Plane

목표:

Paperclip식 control plane을 AF에 software delivery 특화로 이식한다.

핵심 객체:

```text
Tenant
Company/Workspace
Project
Repo
Agent
Role
Issue
WorkItem
Run
RunEvent
Approval
CostEvent
AuditLog
MemoryRecord
Artifact
PR
Deployment
```

필수 기능:

- per-agent cost attribution
- company/project/repo budget
- monthly budget hard stop
- approval gate UI
- audit trail 일원화
- heartbeat scheduler
- pause/resume/terminate worker
- run replay
- multi-tenant isolation

성공 기준:

- 어떤 agent가 어떤 작업에 얼마를 썼는지 추적 가능
- 100% budget 도달 시 agent 자동 pause
- 모든 high-risk action이 approval event로 남음

---

### Phase 5. Quality Gate 상품화

목표:

AF를 단순 자동 코딩 도구가 아니라 "품질 보증이 붙은 AI 개발 납품 시스템"으로 만든다.

표준 gate:

| Gate | 내용 |
|------|------|
| Spec Gate | 요구사항/acceptance criteria 충분성 |
| Architecture Gate | 영향 범위, data model, API contract |
| Implementation Gate | diff 품질, dead code, security risk |
| Test Gate | unit/integration/e2e/lint 결과 |
| Regression Gate | 기존 기능 영향 확인 |
| Review Gate | AI reviewer + optional human approval |
| Release Gate | preview/deploy/rollback plan |

성공 기준:

- PR마다 quality report 자동 생성
- 실패 gate는 다음 worker task로 자동 전환
- 사용자가 "왜 막혔는지" 한 화면에서 이해 가능

---

### Phase 6. Background Maintenance

목표:

사용자가 매번 시키지 않아도 AF가 기존 프로젝트를 유지보수한다.

기능:

- dependency update sweep
- failing CI triage
- flaky test detection
- security alert fix
- stale PR review
- docs drift detection
- recurring refactor campaign
- weekly engineering report

성공 기준:

- GitHub issue 또는 CI failure가 heartbeat를 깨움
- AF가 issue를 분석하고 PR 또는 blocked report를 남김
- 사람이 승인해야 하는 action만 approval queue에 남음

---

### Phase 7. Templates 및 Marketplace

목표:

반복 delivery pattern을 제품 자산으로 만든다.

템플릿 후보:

- `SaaS MVP starter`
- `Existing React app feature`
- `Legacy Django maintenance`
- `FastAPI backend extension`
- `Vercel preview deploy`
- `Dependency/security update`
- `Test coverage recovery`
- `Design-to-code frontend`

수익화:

- seat 기반 SaaS
- repo/project 기반 usage
- accepted PR 기반 credit
- premium template/skill bundle
- managed maintenance plan

---

## 7. 우선순위 판정

가장 먼저 해야 할 것:

1. PR Factory MVP
2. run event/cost/audit schema 통합
3. persistent project RAG
4. Codex App Server adapter
5. approval/cost UI

나중에 해도 되는 것:

1. 완전한 org chart
2. multi-company 고급 governance
3. mobile dashboard
4. marketplace
5. fully autonomous company simulation

하지 말아야 할 것:

1. Claude/Codex보다 더 좋은 editor/CLI 만들기
2. Manus처럼 모든 vertical 자동화하기
3. 문서 생성만 고도화하고 PR/test 결과물을 약하게 두기
4. `bypassPermissions`, `yolo`, `ask-for-approval never`를 SaaS 기본값으로 운영하기

---

## 8. AF 내부 구현과 연결되는 다음 작업

### 8.1 즉시 정리할 코드/설계 지점

| 영역 | 현재 | 다음 |
|------|------|------|
| Provider | `core/providers/cli.py` subprocess 중심 | adapter interface + Codex App Server |
| Budget | `core/run_budget.py` 글로벌 싱글톤 | `CostEvent` + agent/project/month aggregation |
| Audit | trace, hook log, run ledger 분산 | unified `RunEvent` schema |
| Approval | `approval-gate.md` 파일 중심 | DB approval + file snapshot 병행 |
| Memory | facade 있음, evidence 영속화 약함 | project-scoped RAG store |
| Orchestration | dynamic board 있음 | durable queue + heartbeat |
| UI | CLI 중심 | run dashboard + approval queue + PR report |

### 8.2 추천 첫 구현 세트

1. `core/events/run_event.py` 신설
2. `core/cost/cost_event.py` 신설
3. `core/adapters/base.py` 신설
4. `core/adapters/codex_app_server.py` 설계
5. `core/control`의 RunLedger를 RunEvent 저장으로 확장
6. `projects/*/.af_runtime` 구조를 SaaS DB schema로 매핑
7. GitHub PR 생성 adapter 추가

### 8.3 첫 SaaS demo 시나리오

```text
사용자:
"이 repo에 로그인 실패 시 에러 메시지를 더 친절하게 보여주고 테스트까지 추가해줘."

AF:
1. repo 연결
2. 관련 파일 검색
3. work-item 생성
4. Codex/Claude worker 실행
5. test 실행
6. diff + quality report 생성
7. PR 생성
8. cost + audit + memory 저장
```

이 demo가 안정적으로 되면 SaaS 가치가 증명된다.

---

## 9. 리스크

| 리스크 | 설명 | 대응 |
|--------|------|------|
| 실행 품질 불안정 | worker가 patch를 실패하거나 테스트를 깨뜨림 | 작은 task 분해, test gate, retry/FSA, human approval |
| 비용 폭주 | 장기 run과 multi-agent가 token을 많이 씀 | per-agent budget, hard stop, cost dashboard |
| 보안 | secrets, destructive command, repo access | sandbox, worktree, permission policy, secret redaction |
| provider 종속 | Claude/Codex 변화에 영향 | adapter abstraction, multiple worker runtime |
| context 오염 | 대형 repo 로그/검색 결과가 prompt를 오염 | RAG, summarization, context fork |
| 제품 범위 과대 | Manus/Paperclip/Codex를 모두 따라가려 함 | software delivery OS로 범위 제한 |

---

## 10. 최종 판정

`agent-factory`는 가치가 있다.
하지만 가치는 "AI가 코드를 더 잘 쓰는 실행기"가 아니라 "AI worker들이 소프트웨어 프로젝트를 끝까지 납품하게 만드는 운영체제"에 있다.

따라서 제품 방향은 다음 한 문장으로 고정한다.

```text
Agent Factory는 Claude, Codex, Manus류 실행 에이전트를 대체하지 않는다.
Agent Factory는 그들을 고용하고, 통제하고, 검증하고, 기억하게 만드는
software delivery control/quality/memory plane이다.
```

우리가 이 방향으로 가면 Paperclip의 control plane 장점, Codex의 harness event 모델, Claude의 로컬 coding worker 장점, Manus의 sandbox/task UX를 모두 흡수하면서도 "기존 repo 유지보수와 새 프로젝트 납품"이라는 명확한 시장을 잡을 수 있다.

---

## 11. 참고 출처

외부 공식/공개 출처:

- Claude Code settings: https://code.claude.com/docs/en/settings
- Claude Code hooks: https://code.claude.com/docs/en/hooks
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- OpenAI Codex App Server / harness: https://openai.com/index/unlocking-the-codex-harness/
- Manus introduction: https://manus.im/docs/introduction/welcome
- Manus API documentation: https://open.manus.im/docs/v2/introduction
- Manus sandbox: https://manus.im/blog/manus-sandbox
- Paperclip overview: https://docs.paperclip.ing/start/what-is-paperclip
- Paperclip architecture: https://docs.paperclip.ing/start/architecture
- Paperclip costs and budgets: https://docs.paperclip.ing/guides/board-operator/costs-and-budgets

내부 참고:

- `docs/architecture.md`
- `docs/super_harness_3_layer_architecture.md`
- `docs/참고/2026-04-24-paperclip-ing-analysis.md`
- `docs/2026-04-03-design-paperclip-comparison-features-v2.1.md`
- `core/project_pipeline.py`
- `core/dynamic_orchestrator.py`
- `core/agent_runner.py`
- `core/providers/cli.py`
- `core/approval_gate.py`
- `core/run_budget.py`
- `core/control/run_ledger.py`
- `core/document_index.py`
- `core/memory_system/`
