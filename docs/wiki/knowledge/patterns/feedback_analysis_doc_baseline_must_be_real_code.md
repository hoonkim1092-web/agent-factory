---
name: 분석/설계 문서의 baseline은 plan이 아닌 실제 코드여야 함
description: cross-review가 baseline 불일치를 동형 finding으로 반복 BLOCK한다. 분석 문서 작성 전 실제 코드의 출력/schema를 직접 확인할 것.
type: feedback
originSessionId: d27768c4-68e0-46ea-b4d3-7adcd5ec51b7
---
분석 문서·설계 문서·권고 문서를 작성할 때 "baseline" (현재 시스템이 어떻게 동작하는가)은 **plan 문서나 추측이 아니라 실제 코드의 출력/schema/호출 그래프**에 기반해야 한다.

**Why:** 2026-05-02 OpenCode LSP 분석 작성 시 `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md` Phase 2의 **계획된** review_bundle 구조(§1 Pending Files / §2 Git Diff / §4 Related Tests / §5 Direct Callers / §6 Risk Flags)를 **실제 출력 형식**처럼 분석 문서에 적었다. 실제 `core/review_bundle.py:107-117 save()`는 헤더 + per-file `## {path}` + risk 라인만 출력 (계획된 § 섹션은 미구현). cross-review가 이 baseline 불일치를 Critical로 잡고 BLOCK. 부분 수정해도 다른 위치(§5.1)에서 같은 가정이 재발해 동형 BLOCK. 결국 3회 BLOCK 받고 권고 문서 폐기.

또한 분석 과정에서 `core/hooks/lsp_check.py`(2026-04-09 작성, OpenCode 모드 A 등가 구현, `AGENT_LSP_CHECK` 게이트)가 이미 존재함을 모르고 평행 통합을 제안했다. cross-review가 이를 추가 Critical로 잡음.

**How to apply:**
- 분석/권고 문서 작성 직전, 대상 모듈의 실제 출력 형식·schema·호출 그래프를 코드/실행 결과로 1회 캡처: `cat core/X.py`, 실제 `.af_review_queue/*.md` 샘플, `grep -rn "함수명"`.
- plan 문서(`docs/plans/`)의 §섹션 명칭/구조를 실제 구현으로 가정하지 말 것. plan은 **미래 의도**, 코드는 **현재 사실**.
- 같은 도메인에 기존 hook/모듈이 이미 있는지 grep으로 확인: 신규 통합 제안 전 평행 자산 검색 의무 (`grep -rn "pyright\|lsp" core/hooks/`).
- 분석 문서와 권고 문서를 분리: 분석은 사실·해석, 권고는 운영 파라미터. 한 문서에 섞으면 reviewer가 양쪽 기준 모두 적용.
- 분석 문서 §3.1 같은 baseline 다이어그램은 **실제 출력 샘플 코드 블록**으로 작성. 추상 § 표기 금지.

**기준일:** 2026-05-02. OpenCode LSP 분석 작성 시 cross-review BLOCK 3회.

## 관련
- [[code/symbols]]

