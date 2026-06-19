---
generated_at: 2026-06-20T01:20:24+09:00
source_commit: 3bff2b1c
sources:
  - "docs/code_review/code-review.md"
---

# 3.4 이미 수정된 버그 (control/ 영역)

> Source: `docs/code_review/code-review.md:335`
> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]

````markdown
### 3.4 이미 수정된 버그 (control/ 영역)

| ID | 파일 | 내용 | 상태 |
|----|------|------|------|
| BUG-2 | `rollback.py:248` | path traversal 방어 (pathlib.is_relative_to) | ✅ 수정됨 |
| BUG-3 | `run_ledger.py:96` | 스레드/프로세스 lock 추가 | ✅ 수정됨 |
| BUG-7 | `maintenance_pipeline.py:66` | conflict 무한 대기 → 1시간 timeout | ✅ 수정됨 |
| BUG-8 | `issue_context.py:179` | issue ID 중복 → UUID suffix | ✅ 수정됨 |
| BUG-9 | `continuity_snapshot.py:116` | conflict 시 health 격하 | ✅ 수정됨 |
| BUG-10 | `rollback.py:326` | checkpoint 체크섬 검증 시 dict 변형 방지 | ✅ 수정됨 |
| BUG-14 | `maintenance_state.py:135` | transition_log metadata 타입 통일 | ✅ 수정됨 |
| BUG-15 | `maintenance_state.py:109` | 파일 손상 시 재초기화 금지 | ✅ 수정됨 |
````
