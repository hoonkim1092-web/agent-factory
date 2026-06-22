---
name: Master_Blueprint.md §3 갱신 정책
description: §3 서브시스템 내용은 수동 필수. LLM in-place replace 금지. hook 리마인더로 보완.
type: feedback
originSessionId: 9ba41419-7b0d-44f3-ba7f-8f5a3641f82f
---
core/*.py 변경 커밋 후 Master_Blueprint.md §3 서브시스템 내용은 수동으로 갱신한다.

**Why:** LLM이 §3 섹션을 in-place replace하면 섹션 경계 오판 시 Blueprint 전체가 손상될 수 있다. §12는 append-only라 안전하지만 §3는 아니다. Blueprint가 틀린 것 > Blueprint가 오래된 것.

**How to apply:**
- post-commit hook이 `📋 [blueprint] §3 수동 확인 필요` 메시지를 출력하면 해당 섹션 직접 편집
- 클래스/메서드 추가·변경·삭제 시 해당 §3 섹션 last_updated + 내용 갱신
- 단순 버그픽스(시그니처 변화 없음)는 §3 갱신 불필요, §12만으로 충분
- §0 빠른 참조 테이블은 AST 기반 자동화 ✅, §12 이력은 LLM/fallback 자동화 ✅
