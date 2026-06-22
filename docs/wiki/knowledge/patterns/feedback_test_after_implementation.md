---
name: 구현 완료 기준 — 테스트 + 문서 업데이트
description: 기능 구현 완료 = 테스트 통과 + code-review.md 자동 갱신 + Master_Blueprint.md 해당 섹션 업데이트까지
type: feedback
---

구현 완료 = 테스트 통과 + 문서 업데이트까지. 코드 작성 후 반드시 아래 순서를 자동 수행할 것.

**Why:** agent-factory는 하네스 시스템으로 루프를 돌며 자동 수정하는 구조. 하네스 자체 코드에 버그가 있으면 전체 자동화가 오작동함. 또한 Master_Blueprint.md는 이 제품이 무엇인지, 어떤 기능이 있는지를 파악하는 핵심 문서이므로 기능 변경 시 반드시 동기화되어야 함.

**How to apply:**
1. `python -m py_compile <파일>` — 문법 검사
2. `python -m pytest tests/ -q` — 기존 테스트 회귀 확인
3. 해당 모듈 테스트 파일 없으면 → 테스트 작성 후 실행
4. 전부 통과 확인
5. pre-existing 실패는 별도로 명시하고 내 변경과 무관함을 확인
6. **Master_Blueprint.md 해당 §섹션 업데이트** — 새 기능/변경된 기능을 반영
7. **code-review.md** — hook이 자동 갱신하지만, 누락 시 수동 확인
8. 위 전부 완료 후 완료 보고
