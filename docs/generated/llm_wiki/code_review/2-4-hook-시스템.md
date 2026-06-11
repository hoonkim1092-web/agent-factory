---
generated_at: 2026-06-11T15:54:20+09:00
source_commit: df3cb933
sources:
  - "docs/code_review/code-review.md"
---

# 2.4 Hook 시스템

> Source: `docs/code_review/code-review.md:93`
> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]

````markdown
### 2.4 Hook 시스템

| 파일 | 줄 | 역할 |
|------|-----|------|
| `hooks/event_bus.py` | 155 | HookEventBus. register_hook(), run_pre/post_execute() |
| `hooks/checkpoint.py` | 68 | CheckpointHook. runs/{run_id}/checkpoint.json 저장/복원. PRIORITY=90 |
| `hooks/context_fork.py` | 313 | 컨텍스트 분기 관리 |
| `hooks/memory_consolidation.py` | 217 | 메모리 통합 훅 |
| `hooks/skill_self_evolution.py` | 200 | 스킬 자기 진화 |
| `hooks/langsmith_tracing.py` | 360 | LangSmith 트레이싱 |
| `hooks/lsp_check.py` | 213 | LSP 기반 코드 검증 |
| `hooks/guardrails.py` | 87 | 안전 가드레일 |
| `hooks/human_interrupt.py` | 49 | 사람 개입 포인트 |
| `hooks/base.py` | 31 | ContinuationHook 베이스 클래스 |

**문제점:**
- `event_bus.py`: provider 이벤트 → AF 이벤트 매핑 없음 → v3 Phase 8B에서 `on_provider_event()` 추가
- `checkpoint.py`: wake_checkpoint 미구현 → v3 Phase 5A에서 추가
- checkpoint 진실의 원천이 3개: manifest_store, CheckpointHook, wake_checkpoint(미구현) → v3에서 우선순위 명시 필요
````
