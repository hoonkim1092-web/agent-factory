---
id: "session/HOON-KIM-20260624T083724-164744Z-368919-자가진화-지식-도서관-git-vault-obsidian-llm-증류-st.md"
type: "session"
scope: "project"
title: "자가진화 지식 도서관(git vault + Obsidian + LLM 증류) STAGE 0~2 완료 및 S2"
author: "HOON-KIM\\HOON"
source_machine: "HOON-KIM"
created_commit: "66aa7377"
created_at: "2026-06-24T17:37:24+09:00"
visibility: "private"
links: []
---

자가진화 지식 도서관(git vault + Obsidian + LLM 증류) STAGE 0~2 완료 및 S2-3 실측 PASS 후, 다음 세션 순서를 동결하고 설계·코드 교차검증을 수행하는 세션.

## 결정 (Decisions)
- 지식 도서관 다음 세션 순서를 동결: ①S2-3 실측 → ②STAGE R(검색, advisory) → ③자동생성. 측정 없이 NEXT_STEPS↔증류 연결 금지 (커밋 `8eb6c71b`).
- S2-3 distillation 발화점(session_adapter) 배선 후 precision 실측 PASS, STAGE R 진입점으로 전진 (커밋 `66aa7377`, `68cd91c2`).
- STAGE 0에서 Knowledge Vault + Code Wiki를 docs/wiki/ 한 그래프로 통합 (커밋 `2108d34a`, `0848fc74`).
- Obsidian vault root를 docs/wiki/로 경로 이행(2026-06-23): code/(거울, 안 낡음)와 knowledge/(증류, doctor 필요)를 INV-K7로 물리 분리. Blueprint/symbols.md/code-review.md는 청킹 섹션만 read, 원본 통째 read 금지.
- 세션 증류기 + originating_pc 포인터 구현 (STAGE 2 S2-1+S2-2, 커밋 `4f4560ed`).
- 설계문서(docs/YYYY-MM-DD-*.md) 작성 후에는 af-cross-review만 실행한다.
- 지식 도서관 설계 최초 기록 (커밋 `06c2aa7d`).

## 기각 (Rejections)
- 단일 설계문서 검증에서 af-critic 제외 — 설계문서에서 소스 중복 탐색 비용만 발생하고 효과가 없기 때문(2026-05-01 변경).
- 설계문서 큐의 폴링 자동발화는 2026-06-17 제거 — 완료 이벤트 트리거로 대체, 자동발화를 기다리지 말 것.
- WARN은 advisory로 자동 수정 의무 없음 — BLOCK 판정 시에만 발견 사항을 수정(무한루프 방지).
- 직전 라운드가 BLOCK 없이(전부 WARN/PASS) 완료됐다면 재편집해도 자동 재발화하지 않음(WARN-only no-fire).

## 패턴 (Patterns)
- dogfood run의 worktree·state는 `~/.af-dogfood/<run_id>/`에 PC-로컬 저장 — 세션 종료 전 머지 완료 또는 NEXT_STEPS에 PC 식별자·worktree 경로 기록 의무. 미기록 시 회수 불가 (사례: Windows R1 11차 `1779867851-3611529e`).
- 교차검증 리뷰는 ACCEPT/REJECT/HOLD로 독립 판정하고, REJECT는 왜 문제 아닌지 증거와 함께 설명. critic 리뷰와 중복 발견 금지, 새 관점만 추가.
- 코드 리뷰 시 docs/code_review/code-review.md를 먼저 읽고 변경 함수의 호출자/피호출자를 직접 찾아 경계에서 버그 확인.
- ADR 파일명은 초 단위 포함 `ADR-YYYYMMDD-HHMMSS-<slug>.md` (예: `20260513` 야간 파이프라인 동시 생성 충돌 방지).
- 첫 BLOCK 패턴을 data/review-block-patterns.jsonl에 기록(review-learning, 커밋 `fa507e59`), 폐기 설계는 Superseded 개정 노트로 기록(커밋 `6a51932c`).
- 정밀참조(커밋 해시·file:line·INV명)는 요약·변형 없이 원문 그대로 인용.

## 정밀 참조 (verbatim, INV-K5)
- `0848fc74`
- `2108d34a`
- `06c2aa7d`
- `fa507e59`
- `6a51932c`
- `1779867851`
- `3611529e`
- `20260513`
- `66aa7377`
- `8eb6c71b`
- `6f4dd89d`
- `68cd91c2`
- `4f4560ed`

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: HOON-KIM
- session_file: D:/hoonProJect/worktrees/agent-factory/.af_runtime/codex_home/sessions/2026/06/24/rollout-2026-06-24T17-36-03-019ef8c5-a7e3-70f3-8897-156e3af9ac8f.jsonl
- lines: 3-64
