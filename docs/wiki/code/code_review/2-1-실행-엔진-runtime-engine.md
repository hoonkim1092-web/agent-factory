---
generated_at: 2026-06-25T14:19:10+09:00
source_commit: 9a3f9fcc
sources:
  - "docs/code_review/code-review.md"
---

# 2.1 실행 엔진 (Runtime Engine)

> Source: `docs/code_review/code-review.md:37`
> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]

````markdown
### 2.1 실행 엔진 (Runtime Engine)

| 파일 | 줄 | 역할 |
|------|-----|------|
| `agent_runner.py` | 1,419 | 에이전트 실행 핵심. provider failover loop (L1076), _flush_trace (L863), multi-provider ordering (L966) |
| `agent_worker.py` | 109 | Worker subprocess 진입점. task.json → result.json 파일 IPC |
| `dynamic_orchestrator.py` | 887 | asyncio 5-concurrent 병렬 실행. board 기반 task dispatch, state_board 관리 |
| `model_router.py` | 262 | 역할→모델 매핑. provider-aware 라우팅 |
| `run_budget.py` | 58 | 글로벌 토큰 예산. 4char≈1token 휴리스틱, 80% 경고, 100% 중단 |
| `executor.py` | 120 | 단일 에이전트 실행 래퍼 |
| `evaluator.py` | 68 | 실행 결과 평가 |
| `failure_classifier.py` | 46 | INFRA/IMPLEMENTATION 이분류. _INFRA_PATTERNS로 quota/rate_limit/timeout 등 매칭 |

**문제점:**
- `run_budget.py`: 글로벌 싱글톤, 에이전트별 분해 없음 → v3 Feature 1로 해결 예정
- `agent_runner.py:1076`: failover에서 INFRA/IMPLEMENTATION 분류를 안 함 → v3 Phase 7로 해결 예정
- `dynamic_orchestrator.py:567-571`: frozen/source 분기가 inline → v3 Phase 1A `build_worker_cmd()`로 해결 예정
````
