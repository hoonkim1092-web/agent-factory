---
id: "session/DESKTOP-JPHA09P-20260624T155318-375048Z-0bd7a3-scripts-af_provider-py-교차검증-리뷰-세션-시작-호출자.md"
type: "session"
scope: "project"
title: "scripts/af_provider.py 교차검증 리뷰 세션 시작 — 호출자/피호출자 경계 및 나머지 코드베"
author: "Jerry"
source_machine: "DESKTOP-JPHA09P"
created_commit: "eacd67dc"
created_at: "2026-06-25T00:53:18+09:00"
visibility: "private"
links: []
---

scripts/af_provider.py 교차검증 리뷰 세션 시작 — 호출자/피호출자 경계 및 나머지 코드베이스 유지보수 시각 점검

## 결정 (Decisions)
- 교차검증 리뷰 진행 순서: docs/code_review/code-review.md 선독 → scripts/af_provider.py 전문 → 호출자/피호출자 추적 → 기존 이슈 대조 → ACCEPT/REJECT/HOLD 판정
- 리뷰어 시각을 '나머지 코드베이스 유지보수자'로 고정 — 원 작성자가 변경에 집중하느라 놓쳤을 경계 영향(caller/callee signature mismatch, export 의존 파일)에 집중
- 발견 항목 판정 기준: ACCEPT는 구체적 수정 제안 필수, REJECT는 왜 문제없는지 근거(호출 경로·코드 발췌) 필수, af-critic 중복 발견 제외 의무

## 기각 (Rejections)
- 트랜스크립트 범위 내 명시적으로 기각된 기술적 선택 없음 — 세션은 리뷰 준비/지시 단계에서 종료됨

## 패턴 (Patterns)
- Dogfood run PC 핸드오프 교훈: run_id `1779867851-3611529e` (Windows R1 11차)는 세션 종료 전 머지 미완료 + PC 식별자 기록 누락으로 회수 불가 처리됨. 이후 규칙화: 세션 종료 전 머지 완료 또는 NEXT_STEPS.md에 보류 dogfood run run_id·발생 PC·worktree 경로 3줄 기록 의무.
- `20260513` 기준 제정 규칙 4종: 파이프라인 배포 동등성(픽스처만 PASS는 미완료, production caller까지 end-to-end 연결 필수), ADR 초단위 명명(`ADR-YYYYMMDD-HHMMSS-<slug>.md`), 스킬 외부 소스 흡수 귀속(`inspired_by:` 메타 필드), Review-Gate max_rounds=5 캡 및 `AF_SKIP_REVIEW_GATE=1` 우회 방법.
- 교차검증 리뷰 체크리스트 패턴: (1) code-review.md에서 known issue 선독 → (2) 변경 파일 전문 → (3) import/callers grep 추적 → (4) 기존 이슈 fix 여부 및 동일 패턴 도입 여부 비교 → (5) 단순 대안(core/utils.py 등 재사용 가능성) 점검 순서.

## 정밀 참조 (verbatim, INV-K5)
- `1779867851`
- `3611529e`
- `20260513`

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: DESKTOP-JPHA09P
- session_file: D:/warkSpaces/agent-factory/.af_runtime/codex_home/sessions/2026/06/25/rollout-2026-06-25T00-51-48-019efa54-95ef-7ab1-bc58-e7c7d406ad21.jsonl
- lines: 3-5
