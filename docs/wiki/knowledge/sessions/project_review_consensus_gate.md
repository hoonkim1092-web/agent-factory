---
name: project_review_consensus_gate
description: "리뷰 합의 게이트 S1~S6 전부 완료(2026-06-19). S3~S6=`6ec0d1bb`. 다음=자연 발화 검증 또는 신규 product work-item."
metadata: 
  node_type: memory
  type: project
  originSessionId: 3452b6e4-2fdc-4db1-ac9f-a567bdc8d7a2
---

**설계 파일**: `docs/2026-06-19-review-consensus-evidence-gate-design.md`
**브랜치**: `2026-06-04-right-sized-execution-slice1`

## ✅ S1~S6 전부 완료

### S1 (`5771abec`) — 설계문서 라운드 캡
`check_design_pending.py`: `MAX_DESIGN_ROUNDS=3` + `_normalize_entry()` + candidate 캡 체크 + `[af-design-review-capped]` 알림.

### S2 (`432872a7`) — 수렴감지 + 스코프게이트
`check_design_pending.py`: oscillation 체크(섹션 겹침 → `[af-design-review-oscillation]`).
`check_staged_design_review.py`: `_record_verdicts_to_fired_marker`/`_reset_verdict_in_fired_marker` 신규. BLOCK 기록 + PASS/WARN last_verdict 초기화.
`af-cross-review.md/.toml`: 스코프게이트(WHAT→BLOCK, HOW→ACCEPT-ADV 강등).

### S3~S6 (`6ec0d1bb`) — 증거수집 합의기
**S3**: af-cross-review.md/.toml Step 5 직후 finding 사이드카 `cr_findings.json` 저장 지시 추가.
**S4+S5**: `scripts/review_consensus.py` 신규 (LLM 미호출):
- `collect_evidence()`: ACCEPT/ACCEPT★ finding마다 surrounding_code·callers(grep 1-hop)·callees(AST 1-hop)·tests 수집
- `_find_callees()`: Python ast로 enclosing function → 1-hop 피호출자 추출
- file:line 누락/파일 미존재 → consensus=UNVERIFIED (INV-5)
- `cr_findings.json` 부재 → SKIP (INV-7)
**S6**: af-cross-review.md Step 6 신규 — review_consensus.py 호출 → cr_evidence.json 읽기 → LLM 합의판정(ACCEPT/REJECT/UNVERIFIED) → cr_consensus.json + verdict fence 재발행.
**verdict last-fence 정책**: `review_gate._extract_verdict_from_content` search()→finditer()[-1] — 마지막 fence 우선(S6 재발행이 S5 fence 대체).
테스트: 28케이스 PASS (INV-1/2/5/7 + enclosing-func + callees + callers + ACCEPT★).
3-Tier: af-critic BLOCK→수정(last-fence) / af-cross-review SKIP / af-test-runner 158 PASS.

## 다음 = 자연 발화 검증 또는 신규 product work-item
- 합의기는 af-cross-review 자연 발화 시 S3 사이드카 → S6 합의 판정으로 동작
- 검증 방법: .py 파일 편집 후 pre-commit 자연 발화 → cr_findings.json/cr_evidence.json/cr_consensus.json 생성 확인

**Why**: 5라운드 연속 BLOCK 자기유발 진동(실패 B=캡·수렴, S1~S2) + 증거 미수집(실패 A=합의기, S3~S6).

## 관련
- [[code/symbols]]

