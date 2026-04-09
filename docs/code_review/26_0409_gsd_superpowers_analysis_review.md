# GSD Superpowers 분석 보고서

**작성일**: 2026-04-09
**대상 문서**: `docs/2026-04-08-agent_factory_harness_gsd_superpowers_analysis.md`

## 문서 요약

해당 문서는 Agent Factory를 하네스 시스템 관점에서 평가하고, GSD 워크플로우 OS 및 Claude Code Skills 2.0과 비교하여 4단계 개선 로드맵을 제시한다. 핵심 진단: 설계 사상은 우수하나 Context Fork, Semantic Matching, Pre-flight Evals, MCP 어댑터 등 핵심 인프라가 "결여"되어 있으며, Plan-Critique-Verify 루프와 문서 기반 UAT가 부족하다는 것.

## Agent Factory 개선/흡수 포인트 (문서 기준)

1. Context Fork/Sandbox — 무거운 작업의 격리 실행
2. Semantic Embedding 기반 매칭 — 스킬 검색 정확도
3. Pre-flight Evals — 스킬 배포 전 품질 검증
4. MCP 어댑터 — 외부 도구 통합
5. Knowledge Graph — 경험 축적/재활용
6. Plan-Critique-Verify 루프 — 실행 전 계획 검증
7. 문서 기반 UAT — 사용자 수용 테스트

## 현재 코드베이스 반영 현황

| 항목 | 문서 진단 | 실제 상태 | 근거 |
|------|-----------|-----------|------|
| Context Fork | 부재 | **구현 완료** (동기 요약) | `core/hooks/context_fork.py` — 500자 초과 시 서브 LLM 요약, fallback 포함 |
| Semantic Embedding | 부재 | **구현 완료** | `core/semantic_embedder.py` + `core/skill_loader.py` — Gemini 768차원, semantic 40%+keyword 35%+category 25% |
| Pre-flight Evals | 부재 | **2개 엔진 구현** | `core/skill_preflight.py` (N회 반복 신뢰도), `core/skill_eval_harness.py` (evals.yml 기반) |
| MCP Adapter | 부재 | **구현 완료** | `core/mcp_adapter.py` — JSON-RPC 2.0 over stdio, yaml 설정 기반 |
| Knowledge Graph | 부재 | **기본 프레임워크** | `core/memory_system/adapters/knowledge_graph.py` — Problem-Cause-Solution 삼중 저장소 |
| Plan-Critique-Verify | 부재 | **부분 구현** (사후 비평만) | `core/parallel_critique.py`, `core/evaluator.py`, `core/cross_verification.py` |
| 문서 기반 UAT | 부재 | **미구현** | 유일하게 정확한 진단 |

**7개 "부재" 진단 중 5개가 이미 구현되어 있다.** 문서는 코드 구현 이전 또는 코드 미확인 상태에서 작성된 것으로 추정.

---

## Claude 의견

### 문서 정확성
문서의 "부재" 진단은 대부분 **부정확**하다. 방향성 정리로서의 가치는 있으나, 현재 코드베이스와의 괴리가 크다.

### 실질적으로 남은 개선 포인트 (우선순위 순)

**높음 — 즉시 착수 권장:**
1. **Plan-Critique-Verify 사전 루프** (2-3일) — 현재는 "실행 후 분석"만 있고, GSD 방식의 "실행 전 계획 검증"이 없음. 기존 `parallel_critique.py` 재활용 가능
2. **Context Fork 비동기 격리 확장** (3-5일) — 현재 동기 요약만 존재. 무거운 작업의 완전 프로세스 격리 필요

**중간 — 점진적 개선:**
3. **Knowledge Graph 벡터 검색 통합** (2-3일)
4. **MCP 자동 디스커버리** (3-4일)

**낮음 — 장기 과제:**
5. **문서 기반 UAT** (5-7일, 제한적 도입)

---

## Codex 의견

### 핵심 판단
> "이 문서는 방향성은 좋지만 구현 부재 판정은 여러 곳에서 시차가 있다. 지금 Agent Factory가 흡수해야 할 핵심은 '새 기능 추가'보다 '이미 있는 planning/review/eval/resume를 GSD식 품질 루프로 승격시키는 것'이다."

### 항목별 정확도 평가
- **시맨틱 매칭 부재** → 부정확. `skill_loader.py`, `semantic_embedder.py`, `skill_evolution_bus.py`에 임베딩 기반 점수화 구현
- **Pre-flight Evals 부재** → 부정확. `skill_eval_harness.py`, `skill_preflight.py`, `skill_promotion.py`, `builder.py`에 eval/preflight/promotion 경로 존재
- **MCP 어댑터 부재** → 부정확. `mcp_adapter.py`에 서버 discovery, tool function 생성, registry 연동까지 구현. 다만 런타임 통합 연결은 약함
- **Context Sandbox 부재** → 부분적으로만 맞음. truncation + post-tool summarization 훅은 있으나 "진짜 forked executor"는 아직 아님. `context_mode=fork`가 실제 실행 분기로 연결되지 않음
- **Plan-Critique-Verify 루프 부족** → 대체로 정확. planning 자산은 풍부하나 `Plan Checker`와 `Goal-backward Verifier`가 독립 단계로 올라와 있지 않음. 여러 조각으로 흩어져 있음
- **문서 기반 UAT** → 정확. UAT.md나 user-acceptance workflow 없음

### Codex 우선순위
1. **Plan Checker + Goal-backward Verifier + UAT.md 통합** — 가장 정확한 진단이자 ROI 최고. 기존 자산 위에 얹으면 됨
2. **진짜 Context Fork 런타임화** — "결과 요약"이 아닌 "격리 실행". 영향도 크고 난도 중간 이상
3. **Eval 경로 통합과 강제화** — 신규 구현이 아닌 표준 경로 고정 + 우회 경로 제거
4. **MCP 런타임 통합** — 어댑터 존재하므로 value 대비 작업량 작음
5. **Semantic/Event-bus/Knowledge-graph 튜닝** — greenfield가 아닌 wiring backlog

---

## 종합 판단

### Claude와 Codex 공통점
- 문서의 **방향성은 유효**하나 "부재" 판정은 대부분 부정확
- **Plan-Critique-Verify 사전 루프**가 최우선 과제
- 새 컴포넌트 추가보다 **기존 자산의 통합/승격**이 핵심

### 차이점
| 관점 | Claude | Codex |
|------|--------|-------|
| 2순위 | Context Fork 비동기 격리 | Eval 경로 강제화 |
| MCP 판단 | 자동 디스커버리 필요 | 런타임 통합 우선 |
| 접근법 | 기능 단위 구현 | 품질 프로토콜 전면화 |

### 최종 권고
1. **문서 갱신 필요** — 현재 코드 상태 반영하여 "부재→구현됨" 항목 수정
2. **최우선 작업**: Plan Checker + Goal-backward Verifier를 1급 워크플로우로 묶기
3. **접근 방식**: 신규 모듈보다 기존 `parallel_critique.py` + `cross_verification.py` + `approval_gate.py` 위에 GSD식 품질 루프 구축
