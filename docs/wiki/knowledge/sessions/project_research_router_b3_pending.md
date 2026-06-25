---
name: research-router-b3-pending
description: Research Router Phase 2 — B-3 capability-gap 복구 완료(9eb14577). B-1~B-3 전부 완료. 다음은 A Phase 4.
metadata:
  node_type: memory
  type: project
  originSessionId: 124cbd22-f07f-4d7c-a8be-4ee052c84f21
---

Research Router Phase 2 **B-3 완료·push** (2026-05-18, `9eb14577`). B-1~B-3 전부 완료.

**B-3 구현 내용 (2026-05-18):**
- **#1 요구 capability 배선**: `project_pipeline.py` reqs에 `skill_gap_hypotheses` 추가 → `researcher.research()` → `_skill_gap_capabilities_map()` → per-need `required_capabilities` → `_rank_candidates_for_need()` target dict → `decide_reuse()` payload.
- **#2 후보 capability 키 불일치**: `decide_reuse:105` candidate_meta 정규화 — researcher candidate row에 `meta` 키 없이 `capabilities` top-level 보유 → `best.get("meta")` None/빈 dict면 `{"capabilities": best["capabilities"]}` 흡수.
- **추가 수정** (자동화 리뷰 High 2건): `_skill_gap_capabilities_map()`에 safe_id() 정규화 + 빈 need_id raw 체크, `ranked_reuse` 분기에 capability gap 체크 추가 (부재 시 enhance/forge로 강등).
- 테스트 16건 (신규 11건). 3-Tier: af-test-runner PASS / af-critic WARN / af-cross-review PASS.

**B-3 사후 정정 (`ddf392d9`, 2026-05-18):** Codex 교차검증 후속 — 초기 B-3가 reqs에 넣은 `required_capabilities`는 소비처 0건 死코드였음(`_skill_gap_capabilities_map`은 `skill_gap_hypotheses`만 소비, project-union 주입 금지 계약). reqs에서 제거하고 Blueprint §3.1/§12·NEXT_STEPS 표기 정정. **step 4(`ReuseDecision` 사유 → `skill_manifest.json` projection)는 미착수 — 후행 분리**.

**다음 진입점: A Phase 4** (스마트 라우팅) — 1주 실측 데이터 수집 후 진입. 감 기반 skip routing 금지. (B-3 step 4 manifest projection도 잔여 작업으로 남음)

**Why:** capability-gap 분석 경로가 항상 gap=None이어서 死코드 상태였음. B-3으로 end-to-end 연결 완료.
**How to apply:** NEXT_STEPS.md A Phase 4 섹션 참조. 관련: [[analysis-doc-baseline-must-be-real-code]]

## 관련
- [[code/symbols]]

