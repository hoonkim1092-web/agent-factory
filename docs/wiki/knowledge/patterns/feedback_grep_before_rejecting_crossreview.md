---
name: feedback_grep_before_rejecting_crossreview
description: "cross-review finding을 '도달 불가/기존 결함'으로 기각하기 전, 트리거 조건을 grep으로 검증할 것"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 34b7e6f6-22dc-4363-9f1b-de79f26b3359
---

cross-review가 제기한 finding을 "실제로는 도달 불가" 또는 "기존 패턴 미러링이라 신규 결함 아님"으로 기각하려 할 때, **기각 근거(특히 '이 경로는 안 탄다')를 grep으로 먼저 검증**해야 한다.

**Why:** 2026-06-01 dogfood docs/reviews scope fix에서, build_merge_policy의 `has_core_allowed` 게이트 비대칭을 "dogfood plan은 항상 core/라 non-core 경로 미도달"이라며 기각했으나, cross-review가 `scripts/blueprint_updater.py:32 TRIGGER_PREFIXES = ("core/","scripts/","skills/")`를 근거로 skills-only plan도 doc sync를 트리거해 도달 가능함을 입증. 내 기각은 트리거 조건을 grep하지 않은 추측이었고 틀렸다. (cf. [[feedback_cross_review_stale_baseline_repeat]]는 반대 방향 — cross-review false-positive를 grep으로 반증. 양방향 공통 원칙: **verdict 전에 grep**.)

**How to apply:** finding을 ACCEPT/REJECT 판정할 때 근거가 "X 경로는 발생 안 함"이면, 그 경로의 트리거/조건 상수(prefix 목록, 분기 조건, 호출처)를 grep으로 실제 확인한 뒤에만 기각. 확인 없이 "실무상 드묾"으로 넘기지 말 것. [[feedback_review_verdict_vs_bug_substance]]
