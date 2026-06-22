---
name: 코드리뷰 vs 마스터블루프린트 구분
description: code-review.md와 Master_Blueprint.md는 목적이 완전히 다른 문서 — 혼동 금지
type: feedback
---

code-review.md와 Master_Blueprint.md를 혼동하지 말 것.

## code-review.md = 코드 네비게이터
- **실제 파일**: `docs/code_review/2026-04-03-code-review.md`
- `docs/code_review/code-review.md`는 변경 로그일 뿐, 코드 네비게이터가 아님
1. 전체 코드를 분석해서 문서화한 것
2. 기능 추가/리팩토링/버그 수정 시 이 문서를 보고 해당 코드를 빠르게 찾아서 수정·구현
3. 컨텍스트 토큰 낭비를 최소화하기 위한 도구
4. 코드 변경 시 자동 업데이트

## Master_Blueprint.md = 제품 명세서
1. 이 제품이 어떤 제품인지, 어떤 기능들이 있는지, 뭘 할 수 있는지를 설명
2. 기능 구현 완료 시 자동 업데이트

**Why:** 두 문서의 역할을 혼동하면 잘못된 문서를 참조하거나 업데이트 타이밍을 놓침
**How to apply:** 코드 위치를 찾을 때 → `2026-04-03-code-review.md` 참조. 제품 기능/구조를 이해할 때 → Master_Blueprint.md 참조. 코드 변경 후 두 문서 모두 해당 부분 업데이트.
