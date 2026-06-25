---
id: "session/HOON-KIM-20260625T030700-329189Z-d72f8e-stage-r-구현-진입-af-knowledge-search-cli-배선.md"
type: "session"
scope: "project"
title: "STAGE R 구현 진입 — af knowledge search CLI 배선(agent_launcher.py"
author: "HOON-KIM\\HOON"
source_machine: "HOON-KIM"
created_commit: "e245fb14"
created_at: "2026-06-25T12:07:00+09:00"
visibility: "private"
links: []
---

STAGE R 구현 진입 — af knowledge search CLI 배선(agent_launcher.py `2c74355c`→`9ea903df` + af.spec `5db13e7c`→`a9c72137`) 완료, core/knowledge/retrieve.py 신규 추가, 임베딩 연기·결정론 전용 MVP.

## 결정 (Decisions)
- core.knowledge.retrieve를 af.spec hiddenimports에 추가 — CLAUDE.md '새 core/*.py 파일은 hiddenimports에 반드시 추가' 규칙 준수 (5db13e7c→a9c72137)
- knowledge 서브커맨드를 _KNOWN_SUBCOMMANDS에 추가하고 agent_launcher.py에 af knowledge search CLI 배선 — 플래그: --query/-q, --files/-f, --diff, --type, --limit/-n(기본 8), --json, --vault (2c74355c→9ea903df)
- af knowledge search는 core.knowledge.retrieve.main으로 dispatch — 인자 재조립 방식(search_argv 리스트), default=8이면 --limit 생략
- data/review-block-patterns.jsonl에 production_caller_wiring(High) 패턴 추가 — sync_claude_memory.py:251 on_conflict 주장 baseline 검증 포함, created_at 2026-06-23T06:06:00Z (e1f4c1c5→f48f7d66)
- data/review-block-patterns.jsonl에 hiddenimport(High) 패턴 추가 — core/knowledge/__init__.py 관련 af-critic 발화 기록
- STAGE R 설계 완료 커밋 e245fb14 이후 구현 진입 결정 — core/knowledge/retrieve.py + tests/test_knowledge_retrieve.py 신규 파일 작성

## 기각 (Rejections)
- 임베딩/벡터 검색 연기 — 결정론 전용 MVP 채택, 이유: 복잡도 대비 즉시 필요 없음 (설계 문서 2026-06-23-knowledge-library-evolution-design.md 명시)
- af-cross-review deliberation 미수행 — codex usage limit으로 single-vendor SKIP (2026-06-25 04:24 PM KST까지 재시도 불가), Round 2·3 해당 없음 처리
- core/output_paths.py:69 즉시 수정 미실행 — BLOCK 패턴 88f6c557으로 등재만 하고 별도 fix로 분리 (projects/ 내 앱 경로를 AF repo 하위로 잘못 판정하는 버그)
- core/review_runner.py:67 즉시 수정 미실행 — BLOCK 패턴 88f6c557으로 등재만 하고 별도 fix로 분리 (Windows PowerShell/cmd에서 비작동 SKIP 탈출구 안내)

## 패턴 (Patterns)
- 신규 core/*.py 신설 시 af.spec hiddenimports 동시 추가 필수 — 누락 시 frozen build에서 ImportError 발생, 5db13e7c→a9c72137이 패턴 실증
- agent_launcher.py 서브커맨드 추가는 3-위치 동시 수정 — (1) _KNOWN_SUBCOMMANDS set, (2) argparse subparsers 정의, (3) __main__ elif dispatch 블록 (2c74355c→9ea903df)
- review-gate BLOCK 판정은 data/review-block-patterns.jsonl에 pattern_key·severity·changed_files·finding_excerpt로 누적 기록 — 이후 세션에서 동일 패턴 재탐지 기준으로 활용 (e1f4c1c5→f48f7d66)
- cross-review single-vendor 모드에서는 Round 2(Challenge)·Round 3(Defense) 생략, Round 1(Discovery) Claude 단독 분석만 수행하고 verdict 확정
- 서브커맨드 dispatch에서 default 값 동일 시 argv 생략 패턴 — args.limit == 8이면 --limit 전달 안 함, 하위 모듈 argparse default와 중복 방지

## 정밀 참조 (verbatim, INV-K5)
- `core/output_paths.py:69`
- `core/review_runner.py:67`
- `sync_claude_memory.py:251`
- `e245fb14`
- `1779867851`
- `3611529e`
- `20260513`
- `5db13e7c`
- `a9c72137`
- `2c74355c`
- `9ea903df`
- `e1f4c1c5`
- `f48f7d66`
- `88f6c557`
- `e3c0fca7`
- `a02e109d`
- `c1d5ecb7`
- `eacd67dc`
- `d75f3c49`

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: HOON-KIM
- session_file: D:/hoonProJect/worktrees/agent-factory/.af_runtime/codex_home/sessions/2026/06/25/rollout-2026-06-25T12-05-27-019efcbd-57cc-78a0-9ff7-ee6c0c6d7920.jsonl
- lines: 3-64
