---
name: 문서 파일명 날짜 포함 규칙
description: code-review.md를 제외한 모든 문서 파일명에 YYYY-MM-DD 날짜 접두사 필수
type: feedback
---

code-review.md는 날짜 없이 고정 파일명 유지 (살아있는 단일 문서, in-place 갱신).
기타 모든 문서(Feature, 버그픽스, 설계, 플랜 등)는 파일명에 날짜 포함 필수: `YYYY-MM-DD-제목.md`

**Why:** 문서 생성 시점을 파일명에서 즉시 파악 가능. 날짜 없는 문서는 언제 만들어진 건지 알 수 없어 관리가 어려움.

**How to apply:** 새 문서 파일 생성 시 항상 `YYYY-MM-DD-` 접두사 포함. CLAUDE.md에도 규칙 추가됨.
