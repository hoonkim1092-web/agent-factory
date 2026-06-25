---
id: "session/HOON-KIM-20260625T064519-254309Z-af34e2-stage-r-af-knowledge-search-0f423389-sta.md"
type: "session"
scope: "project"
title: "STAGE R(af knowledge search, `0f423389`) + STAGE 3(af knowle"
author: "HOON-KIM\\HOON"
source_machine: "HOON-KIM"
created_commit: "7aedfa55"
created_at: "2026-06-25T15:45:19+09:00"
visibility: "private"
links: ["[[code/symbols]]"]
---

STAGE R(af knowledge search, `0f423389`) + STAGE 3(af knowledge doctor, `6a1c1322`) 구현 완료 후 af.py 라우팅 누락 픽스(`10ff6a75`) · af doctor knowledge vault 점검 추가(`7aedfa55`), cross-review 게이트 발동(scripts/af_doctor.py 대상).

## 결정 (Decisions)
- STAGE R = `af knowledge search` 명령어-only MVP 구현(commit `0f423389`): 결정론 전용(임베딩 연기), --query 모드와 --files/--diff 정밀참조 2모드, read-only
- STAGE 3 = `af knowledge doctor` staleness/skew 점검기 구현(commit `6a1c1322`): 진단 전용 read-only 도구, knowledge vault 상태 점검
- af doctor 통합 진단에 knowledge vault 점검 항목 추가(commit `7aedfa55`): 평소 `[✓]`, 문제 시 `[!]` + `af knowledge doctor` 안내로 단일 진입점 유지
- af.py에서 knowledge/provider/ponytail 서브커맨드 라우팅 누락을 별도 픽스 커밋으로 분리(commit `10ff6a75`)
- STAGE 2 증류기 착수 전 BLOCK 3건 처리 의무를 NEXT_STEPS.md에 명시 기록(commit `a67c19a5`)
- Knowledge vault R2/R3 설계 솔로+팀 연속성 substrate 아키텍처로 개정(commit `9a3f9fcc`)
- scripts/af_doctor.py 변경 후 Tier 2~3 review-first 정책에 따라 af-cross-review 게이트 자동 발동(리뷰 파일 `docs/reviews/2026-06-25-143145-af_knowledge_doctor-code-review.md`, `docs/reviews/2026-06-25-145100-af_knowledge_doctor-code-review.md`)

## 기각 (Rejections)
- 임베딩 기반 의미 검색: STAGE R MVP에서 연기 결정 — 결정론 전용 exact 검색으로 먼저 확인 후 필요 시 추가
- STAGE 2 증류기 즉시 착수: BLOCK 3건 해소 전 착수 금지 — commit `a67c19a5`에서 의무 기록

## 패턴 (Patterns)
- 라우팅 누락 버그는 기능 커밋과 반드시 분리: `6a1c1322`(기능) → `10ff6a75`(라우팅 픽스) 순서
- af doctor = 단일 통합 진단 진입점 패턴: 하위 도구(`af knowledge doctor` 등)는 `[✓]`/`[!]` 요약 한 줄 + 상세 명령어 안내
- scripts/*.py 변경 시 review-gate 자동 발동 → `docs/reviews/YYYY-MM-DD-HHMMSS-<파일명>-code-review.md` 누적 패턴
- Dogfood run PC 핸드오프 교훈(사례 `1779867851-3611529e`): 세션 종료 전 머지 완료 또는 NEXT_STEPS.md에 run_id·발생PC·worktree 경로 3줄 기록 의무 — 미기록 시 회수 불가

## 정밀 참조 (verbatim, INV-K5)
- `1779867851`
- `3611529e`
- `20260513`
- `10ff6a75`
- `6a1c1322`
- `a67c19a5`
- `9a3f9fcc`
- `0f423389`

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: HOON-KIM
- session_file: D:/hoonProJect/worktrees/agent-factory/.af_runtime/codex_home/sessions/2026/06/25/rollout-2026-06-25T15-44-06-019efd85-8391-7e22-97a7-052c27d369e6.jsonl
- lines: 3-5

## 관련
- [[code/symbols]]

