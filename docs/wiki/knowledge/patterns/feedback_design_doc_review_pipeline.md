---
name: 설계문서 교차검증은 파이프라인으로 강제
description: 설계=cross-review만, 트리거는 완료 이벤트(폴링 자동발화 제거 2026-06-17)
type: feedback
originSessionId: 67d6486b-f778-4b6a-a162-2852377a775d
---
설계문서(`docs/YYYY-MM-DD-*.md`) 작성 후 교차검증 발화 규칙. **2026-06-17 트리거 모델 변경**.

**현재 규칙 (최신):**
- **단일 설계문서**: **af-cross-review 1개만** (2026-05-01: af-critic은 설계문서에서 소스중복 탐색 비용만 들고 효과 없어 제외).
- **Work-item 4-문서 세트**: af-doc-qa + af-cross-review **2개 병렬**.
- 코드/기능 구현 완료 = 풀 3-Tier (af-critic → af-cross-review → af-test-runner).

**트리거 = 완료 이벤트, 폴링 자동발화 제거 (2026-06-17):**
- 사용자가 어제(2026-06-17) **UserPromptSubmit 자동발화(`check_design_pending.py` `[af-design-review-pending]`)를 제거**했다. **프롬프트 제출로는 더 이상 리뷰가 자동으로 안 뜬다 — 정상 동작, 버그 아님.**
- 새 모델: **"문서/기능 구현이 끝났다고 판단되면" 3-Tier(설계는 cross-review만)를 발화한다** = 완료 이벤트 트리거(폴링 아님). 근거: 완료계약 §11.0 — 리뷰는 implement 완료 시 도는 스테이지여야지 사람 키입력 폴링과 디커플되면 안 됨.
- 남은 surface = **커밋 게이트**(`scripts/check_staged_design_review.py` + pre-commit): staged 설계문서의 `docs/reviews/` 최신 verdict가 BLOCK이면 커밋 차단. **단 이건 기존 verdict를 *검사*만 하지 cross-review를 *실행*하진 않는다.**

**How to apply:**
- 설계문서/기능을 다 썼다고 판단되면 **내가 af-cross-review(설계) 또는 3-Tier(코드)를 수동 발화**한다. 자동발화를 기다리지 말 것.
- BLOCK만 수정 의무, WARN/advisory는 선택([[feedback_review_verdict_vs_bug_substance]]). 수용 전에도 grep 재확인([[feedback_grep_before_rejecting_crossreview]]).

**Why:** CLAUDE.md 텍스트 규칙만으론 누락 가능 → 파이프라인화. 폴링 자동발화는 완료 이벤트와 디커플돼 틀린 트리거라 제거. [[feedback_code_review_workflow_v2]] [[feedback_design_review_mandatory]]
