# Paperclip.ing 분석 — AF 흡수 전략 판정

> 날짜: 2026-04-24
> 출처: https://paperclip.ing/
> 분석 목적: Paperclip 기능 AF 이식 필요성 + 영속 RAG와의 우선순위 결정
> 관련 선행 문서: [`docs/2026-04-03-design-paperclip-comparison-features-v2.1.md`](../2026-04-03-design-paperclip-comparison-features-v2.1.md) — v1~v2.1 설계 (미구현 상태)

---

## 1. Paperclip이 하는 일

**AI 에이전트 오케스트레이션·거버넌스 플랫폼**. 챗봇/에이전트 프레임워크/워크플로 빌더가 **아니라**, 여러 AI 에이전트를 회사의 직원처럼 관리하는 **조직 관리 레이어**.

### 핵심 기능

| 기능 | 설명 |
|------|------|
| **Org Structure** | 역할·보고 라인·직무 기반 계층적 관리 |
| **Goal Alignment** | 태스크를 회사 미션까지 추적해 에이전트가 컨텍스트 이해 |
| **Heartbeats** | 스케줄링된 wake-up으로 작업 체크·할당 처리 |
| **Budget Control** | 에이전트별 월간 지출 한도 + 자동 강제 |
| **Ticket System** | 모든 대화 추적·모든 결정 설명 (감사 로그) |
| **Governance** | 인간 감독 — 채용 승인, 결정 오버라이드, 일시정지/종료 |
| **Multi-Company** | 단일 배포로 독립 조직 여러 개 |

### 기술 스택

- Agent-agnostic: Claude Code, OpenClaw, Cursor 등 heartbeat 받는 시스템이면 OK
- Node.js 백엔드 + Postgres (embedded or external)
- MIT 오픈소스, self-hosted

### 분류

**AI 에이전트 오케스트레이션·거버넌스 플랫폼** — RAG·지식관리·문서검색과는 **다른 축**.

---

## 2. AF 현재 상태와 매핑

### 2.1 이미 AF에 있는 것 (Codex 탐색 확인)

| Paperclip 기능 | AF 대응 구조 |
|---------------|------------|
| Heartbeats/Scheduler | `/schedule`, `/loop`, `nightly_tick.py`, `ScheduleWakeup` |
| Budget 기본 | `RunBudget` (단, 글로벌 싱글톤) |
| Audit/Ticket 기본 | `RunLedger`, `hook_events.log`, LangSmith trace JSONL, bridge state |
| Governance 기본 | `RuntimeSupervisor`, `ExecutionPolicyResolver`, `RegressionSafetyGate`, review gate |
| Hook 이벤트 | `HookEventBus` + `LangSmithTracingHook` |
| 코드 규모 | `core/control/` 16파일 3,882줄 — 거버넌스 sidecar 인프라 풍부 |

### 2.2 없는 것 (진짜 갭)

1. **Strict org tree** — reportsTo/chainOfCommand 스키마 부재
2. **Per-agent cost attribution** — `RunBudget` 싱글톤 + `len(text)//4` 4-char 휴리스틱, agent_id 분리 없음 (`core/run_budget.py:48`)
3. **Unified audit schema** — 현재 **4곳에 분산**: `run_ledger.jsonl` / `hook_events.log` / trace JSONL / bridge state
4. **Durable multi-ticket queue + UI** — 큐는 있으나 UI 없음
5. **Governance 웹 UI** — CLI 기반 AF와 UX 철학 다름

---

## 3. RAG vs Paperclip 우선순위 판정

### 3.1 사용자 초기 가설
> "Paperclip을 가져가려면 RAG를 포함하는 게 좋을까?"

**핵심 혼동**: Paperclip은 RAG가 아니다. 완전히 직교한 두 축.
- **RAG**: 에이전트가 **뭘** 참고하느냐 (evidence/knowledge)
- **Paperclip**: 에이전트를 **어떻게** 관리하느냐 (governance)

### 3.2 최종 판정: **FIRST_RAG** (영속 RAG 먼저)

Codex 독립 분석 + Claude 검증 결과 양쪽 일치.

#### 근거

**① 기술 부채 비대칭** — RAG 쪽이 압도적으로 부족
- `core/document_index.py` (406줄): 세션성 인덱스, 디스크 캐시는 메타데이터 스냅샷에 불과
- `core/researcher.py`의 NotebookLM synthesis가 `notebook_summary` **plain text 문자열**로만 흘러감 → 재활용 불가 자산
- 반대편 거버넌스 sidecar는 이미 3,882줄 규모 → 구조적 공백이 RAG에 집중

**② Paperclip 이식은 greenfield가 아니라 통합 작업**
- 이미 있는 `RunLedger`/`RuntimeSupervisor`/`ExecutionPolicyResolver`를 하나의 스키마로 통합 + per-agent cost + UI
- 신규 개발 비중이 생각보다 작음

**③ 순서상 리팩토링 비용 비대칭**
- **RAG 먼저**: query/ingest 비용이 자연스럽게 cost event로 `RunLedger`에 흘러 들어감 → 그 위에 Paperclip 방식 per-agent budget UI 얹기 **깨끗**
- **Paperclip 먼저**: 나중에 RAG 도입 시 cost schema를 다시 손봐야 함 **낭비**

**④ 사용자 체감 가치 차이**
- RAG = 모든 신규 프로젝트의 **첫 결과물 품질** 개선 (evidence plane이 brief→role plan→task board→work items로 전파)
- Paperclip = "운영자 가시성" 개선 (단기 결과 델타 작음)

**⑤ 구조적 공백**
- `core/memory_system/cross_project.py`에 cross-project memory 축이 **이미 있는데** 정작 evidence 수집은 세션성 DocumentIndex — 한쪽만 영속화된 기형

---

## 4. 추천 진행 순서

```
Week 1   : RunBudget per-agent 분리 (Paperclip 준비작업, RAG와 충돌 없음)
Week 1-3 : 영속 RAG 구축
           ├ Priority 1: NotebookLM synthesis 청크화 + 영속화 ← 체감 가장 큼
           ├ Priority 2: persistent vector store (Chroma/FAISS)
           └ Priority 3: cross-project 재사용 (memory_system과 연결)
Week 3-4 : nightly_tick.py에 background refresh + cost event → RunLedger 통합
이후     : Paperclip 이식 (unified audit schema + per-agent budget UI + governance)
```

### KPI (Paperclip 착수 타이밍 결정용)
- Tavily 호출 수 감소율
- 동일 도메인 재실행 시 brief 품질 개선 측정
- per-agent cost ledger 정합성

---

## 5. 주의사항

### 5.1 RAG 작업 범위를 3단계로 나눠라
"persistent store + NotebookLM 청크화 + cross-project 재사용"을 한 PR에 몰면 망한다.  
체감 가치 제일 큰 건 **NotebookLM 청크화**.

### 5.2 KPI 선행 정의
측정 없으면 Paperclip 착수 타이밍 못 잡음.

### 5.3 도메인 오염 대책
영속 RAG 도입 시 **project_id 스코프 필수**. 로또 프로젝트 컨텍스트가 포커 프로젝트에 섞이지 않도록.

### 5.4 기존 2026-04-03 설계와의 관계
선행 문서 `docs/2026-04-03-design-paperclip-comparison-features-v2.1.md`는 **DaemonSupervisor + Worker** 관점. 이번 판정은 그 설계의 구현 우선순위를 뒤로 미루고 RAG를 먼저 한다는 결정이지, 설계 자체를 폐기하는 게 아님.

---

## 6. 참조 파일 (Codex 탐색 결과)

- `/Users/hoon/workTree/agent-factory/core/run_budget.py` — per-agent 분리 필요 지점
- `/Users/hoon/workTree/agent-factory/core/researcher.py:507` — evidence 수집 메인 경로
- `/Users/hoon/workTree/agent-factory/core/document_index.py` — 현재 세션성 인덱스
- `/Users/hoon/workTree/agent-factory/core/memory_system/cross_project.py` — 이미 있는 cross-project memory
- `/Users/hoon/workTree/agent-factory/core/control/` — Paperclip 이식 대상 sidecar (3,882줄)
- `/Users/hoon/workTree/agent-factory/core/project_pipeline.py:634` — `collect_project_evidence` 호출점
