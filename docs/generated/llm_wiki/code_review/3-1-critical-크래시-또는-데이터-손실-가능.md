---
generated_at: 2026-06-11T02:11:43+09:00
source_commit: ebef36ee
sources:
  - "docs/code_review/code-review.md"
---

# 3.1 Critical — 크래시 또는 데이터 손실 가능

> Source: `docs/code_review/code-review.md:265`
> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]

````markdown
### 3.1 Critical — 크래시 또는 데이터 손실 가능

| ID | 파일 | 라인 | 문제 | 상태 |
|----|------|------|------|------|
| C1 | `ise_loop.py` | 274-278 | 에스컬레이션 결정에 도달 불가 코드 (return 2 unreachable) | ✅ 수정됨 |
| C2 | `hooks/checkpoint.py` | 63-64 | Non-atomic 파일 쓰기. 저장 중 크래시 시 checkpoint 손상 | ✅ 수정됨 |
| C3 | `hooks/context_fork.py` | 211-233 | Thread.join(timeout)이 실제 스레드를 중단하지 않음. 좀비 스레드 가능 | ✅ 수정됨 |
| C4 | `memory_system/issue_tracker.py` | 83-91 | `gh` CLI subprocess에 shell escape 누락. injection 위험 | ✅ 수정됨 |
````
