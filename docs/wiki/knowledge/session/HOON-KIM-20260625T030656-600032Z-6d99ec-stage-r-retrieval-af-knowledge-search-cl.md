---
id: "session/HOON-KIM-20260625T030656-600032Z-6d99ec-stage-r-retrieval-af-knowledge-search-cl.md"
type: "session"
scope: "project"
title: "STAGE R(retrieval) `af knowledge search` CLI MVP 구현 진입 — `co"
author: "HOON-KIM\\HOON"
source_machine: "HOON-KIM"
created_commit: "e245fb14"
created_at: "2026-06-25T12:06:56+09:00"
visibility: "private"
links: ["[[code/symbols]]", "[[knowledge/session/DESKTOP-JPHA09P-20260624T155647-400180Z-a3a557-review-gate가-실제-수정-파일-agent_launcher-py]]", "[[knowledge/session/HOON-KIM-20260625T030325-534798Z-c5822a-stage-r-구현-진입-af-knowledge-search-cli-배선]]", "[[knowledge/session/HOON-KIM-20260625T030653-952713Z-9c3f47-stage-r-구현-진입-af-knowledge-search-cli-배선]]", "[[knowledge/session/HOON-KIM-20260625T030700-329189Z-d72f8e-stage-r-구현-진입-af-knowledge-search-cli-배선]]", "[[knowledge/session/HOON-KIM-20260625T053107-308104Z-f5cab6-stage-r-af-knowledge-search-cli-배선-완료-0f]]", "[[knowledge/session/HOON-KIM-20260625T030520-996672Z-7a7ff6-stage-r-설계-완료-e245fb14-후-구현-진입-core-know]]", "[[knowledge/session/HOON-KIM-20260625T030849-381582Z-800601-stage-r-retrieval-설계-cross-review-흡수-완료]]", "[[knowledge/session/HOON-KIM-20260625T031043-991411Z-e1462b-stage-r-retrieval-설계를-e245fb14에-확정하고-구현]]"]
---

STAGE R(retrieval) `af knowledge search` CLI MVP 구현 진입 — `core/knowledge/retrieve.py` 신설 + `agent_launcher.py` knowledge subcommand 배선 + `af.spec` hiddenimport 추가; cross-review는 codex usage limit으로 single-vendor(Claude 단독) PASS.

## 결정 (Decisions)
- `agent_launcher.py`에 `knowledge` subcommand 추가하고 `core.knowledge.retrieve.main(search_argv)` 로 라우팅 — getattr 기반 args 재조립 후 list 형태로 전달하는 기존 provider subcommand 패턴 재사용
- `af.spec` hiddenimports에 `core.knowledge.retrieve` 즉시 추가 — 새 `core/*.py` 생성 시 freeze 빌드 패키징 규칙(CLAUDE.md) 준수
- `review-block-patterns.jsonl`에 `production_caller_wiring`(고심도: `core/output_paths.py:69` 리다이렉트 오판 + `core/review_runner.py:67` Windows SKIP 탈출구 비작동) 및 `hiddenimport` 패턴 2건 추가 등록
- cross-review single-vendor 모드로 진행 — codex-cli가 usage limit 도달(2026-06-25 04:24 PM KST까지 재시도 불가)하여 Round 2(Challenge)/Round 3(Defense) deliberation 미수행, PRIMARY 6건 Discovery만 수행 후 PASS 간주

## 기각 (Rejections)
- codex-cli 기반 다라운드 deliberation 미수행 — usage limit SKIP, `[single-vendor]` 모드 강제 전환(Challenge·Defense 라운드 없음)
- embedding 기반 검색 도입 연기 — 결정론 전용(exact keyword) MVP 우선, 임베딩은 추후 STAGE로 분리

## 패턴 (Patterns)
- subcommand 배선 패턴: `getattr(args, 'key', default)` 로 args 속성 추출 → `search_argv: list[str]` 재조립 → `main(search_argv)` 호출 — `provider` subcommand와 동일 구조, 신규 subcommand 추가 시 재사용
- hiddenimport 즉시 등록 규칙: 새 `core/*.py` 신설 시 `af.spec` hiddenimports 같은 커밋에 추가하지 않으면 freeze 빌드에서 `ImportError` 발생 — `88f6c557` BLOCK 패턴이 이를 강제
- review-block-patterns.jsonl 활용: 반복 BLOCK 원인을 `pattern_key`로 등록하여 다음 세션에서 동일 패턴 사전 탐지 가능 — `production_caller_wiring`(core/output_paths.py:69, core/review_runner.py:67) + `hiddenimport` 2건 추가됨
- cross-review BLOCK 흡수 결과물 커밋: `e245fb14`에 설계 개선 + cross-review 산출물을 함께 묶어 커밋 — 설계문서 수정과 리뷰 결과를 분리하지 않는 AF 커밋 규칙 준수
- `sync_claude_memory.py:251` `on_conflict=proje...` 라인이 cross-review baseline 검증 대상으로 등장 — memory sync 충돌 처리 로직이 반복 검증 항목임을 시사

## 정밀 참조 (verbatim, INV-K5)
- `core/output_paths.py:69`
- `core/review_runner.py:67`
- `sync_claude_memory.py:251`
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
- `e245fb14`
- `e3c0fca7`
- `a02e109d`
- `c1d5ecb7`
- `eacd67dc`
- `d75f3c49`

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: HOON-KIM
- session_file: D:/hoonProJect/worktrees/agent-factory/.af_runtime/codex_home/sessions/2026/06/25/rollout-2026-06-25T12-05-38-019efcbd-8287-7962-a691-ea31f363e9e9.jsonl
- lines: 3-5

## 관련
- [[code/symbols]]
- [[knowledge/session/DESKTOP-JPHA09P-20260624T155647-400180Z-a3a557-review-gate가-실제-수정-파일-agent_launcher-py]]
- [[knowledge/session/HOON-KIM-20260625T030325-534798Z-c5822a-stage-r-구현-진입-af-knowledge-search-cli-배선]]
- [[knowledge/session/HOON-KIM-20260625T030653-952713Z-9c3f47-stage-r-구현-진입-af-knowledge-search-cli-배선]]
- [[knowledge/session/HOON-KIM-20260625T030700-329189Z-d72f8e-stage-r-구현-진입-af-knowledge-search-cli-배선]]
- [[knowledge/session/HOON-KIM-20260625T053107-308104Z-f5cab6-stage-r-af-knowledge-search-cli-배선-완료-0f]]
- [[knowledge/session/HOON-KIM-20260625T030520-996672Z-7a7ff6-stage-r-설계-완료-e245fb14-후-구현-진입-core-know]]
- [[knowledge/session/HOON-KIM-20260625T030849-381582Z-800601-stage-r-retrieval-설계-cross-review-흡수-완료]]
- [[knowledge/session/HOON-KIM-20260625T031043-991411Z-e1462b-stage-r-retrieval-설계를-e245fb14에-확정하고-구현]]

