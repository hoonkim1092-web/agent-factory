---
name: 설계 먼저, 코드는 승인 후
description: "설계하라"고 하면 docs/features/ 설계 문서만 작성. 코드 수정은 설계 승인 후에만 진행.
type: feedback
---

"설계해" = docs/features/에 Feature 문서만 작성하라는 뜻. 코드 수정 금지.

**Why:** Feature-driven workflow — 문서 승인 → 구현 순서가 프로젝트 규칙. Plan Mode 플랜 파일(~/.claude/plans/)은 설계 문서가 아님. 실제 설계 문서는 `docs/features/YYYY-MM-DD-제목.md`에 작성해야 함.

**How to apply:** "설계해/설계 다시해" 지시 시:
1. `docs/features/YYYY-MM-DD-제목.md` 작성
2. 코드 수정하지 않음
3. 사용자 승인 대기
4. 승인 후 구현 시작
