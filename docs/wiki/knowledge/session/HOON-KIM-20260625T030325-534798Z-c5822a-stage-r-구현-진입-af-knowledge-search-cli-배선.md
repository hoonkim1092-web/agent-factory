---
id: "session/HOON-KIM-20260625T030325-534798Z-c5822a-stage-r-구현-진입-af-knowledge-search-cli-배선.md"
type: "session"
scope: "project"
title: "STAGE R 구현 진입: af knowledge search CLI 배선 완료(agent_launcher."
author: "HOON-KIM\\HOON"
source_machine: "HOON-KIM"
created_commit: "e245fb14"
created_at: "2026-06-25T12:03:25+09:00"
visibility: "private"
links: ["[[code/symbols]]", "[[knowledge/session/DESKTOP-JPHA09P-20260624T155647-400180Z-a3a557-review-gate가-실제-수정-파일-agent_launcher-py]]", "[[knowledge/session/HOON-KIM-20260625T030653-952713Z-9c3f47-stage-r-구현-진입-af-knowledge-search-cli-배선]]", "[[knowledge/session/HOON-KIM-20260625T030656-600032Z-6d99ec-stage-r-retrieval-af-knowledge-search-cl]]", "[[knowledge/session/HOON-KIM-20260625T030700-329189Z-d72f8e-stage-r-구현-진입-af-knowledge-search-cli-배선]]", "[[knowledge/session/HOON-KIM-20260625T053107-308104Z-f5cab6-stage-r-af-knowledge-search-cli-배선-완료-0f]]"]
---

STAGE R 구현 진입: af knowledge search CLI 배선 완료(agent_launcher.py + af.spec hiddenimport) + cross-review BLOCK 패턴 2건(production_caller_wiring·hiddenimport) data/review-block-patterns.jsonl에 기록.

## 결정 (Decisions)
- core.knowledge.retrieve를 af.spec hiddenimports에 추가(5db13e7c→a9c72137) — frozen 빌드에서 누락 시 ImportError 발생하므로 신규 core/*.py 파일 생성 시 즉시 추가 의무(CLAUDE.md 규칙 반영)
- agent_launcher.py(2c74355c→9ea903df): 'knowledge'를 _KNOWN_SUBCOMMANDS에 추가 + knowledge search 서브파서 선언 + dispatch 블록 구현 — af knowledge search [--query Q] [--files F] [--diff] [--type T] [--limit N] [--json] [--vault V] MVP 노출
- dispatch 방식은 기존 provider_main과 동일한 argv 재조립 패턴(search_argv list 구성 후 knowledge_search_main(search_argv)) 채택 — 일관성 유지
- data/review-block-patterns.jsonl에 신규 BLOCK 패턴 2건 추가: production_caller_wiring(sync_claude_memory.py:251 on_conflict 주장 교차검증, 2026-06-23T06:06:00Z) + hiddenimport(core.knowledge.retrieve af.spec 누락, af-critic 발견)
- STAGE R 설계+cross-review 완료 커밋 e245fb14 — 다음 단계는 STAGE R 구현(Sonnet)

## 기각 (Rejections)
- production_caller_wiring 리뷰에서 codex_cli cross-review SKIP(single-vendor 모드): 2026-06-25 04:24 PM KST까지 usage limit — deliberation(Round 2·3) 미수행, Claude 단독 PRIMARY 6건만으로 판정
- --limit 기본값 8 비전달 로직(agent_launcher.py: `if getattr(args, 'limit', 8) != 8`)은 '--limit 8' 명시 시 전달 생략 — 의도적 YAGNI(기본값이면 argv 노이즈 줄임), 단 사용자가 8을 명시해도 동작은 동일하므로 무해
- cross-review BLOCK 시 sync_claude_memory.py:251 주장(on_conflict=project_id 미검증)을 추측 기각하지 않고 패턴으로 기록 — grep 반증 먼저 의무(feedback_grep_before_rejecting_crossreview)

## 패턴 (Patterns)
- 신규 core/*.py 추가 시 af.spec hiddenimports 동시 추가 안 하면 af-critic이 hiddenimport BLOCK 발화 — pre-commit 또는 af-spec 자동 검사 고려 가능
- single-vendor 모드에서 cross-review는 WARN[single-vendor]로 통과 간주(provider=0 SKIP 정책), BLOCK 패턴 기록은 별도 수동 추가
- review-block-patterns.jsonl은 finding_excerpt 원문을 JSON 내부에 직렬화해 보존 — 향후 replay·패턴 매칭의 SSOT로 활용
- af.spec(5db13e7c→a9c72137), agent_launcher.py(2c74355c→9ea903df), review-block-patterns.jsonl(e1f4c1c5→f48f7d66) 세 파일이 단일 STAGE R 진입 커밋(e245fb14 선행 설계 포함)에 묶임 — 새 knowledge 기능의 배선 완결 단위
- core/output_paths.py:69 + core/review_runner.py:67 는 이전 라운드(88f6c557 패턴)에서 이미 BLOCK된 미해결 버그 — 본 세션에서 수정 확인 없음, 잔존 위험

## 정밀 참조 (verbatim, INV-K5)
- `core/output_paths.py:69`
- `core/review_runner.py:67`
- `sync_claude_memory.py:251`
- `e245fb14`
- `e3c0fca7`
- `a02e109d`
- `c1d5ecb7`
- `eacd67dc`
- `d75f3c49`
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

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: HOON-KIM
- session_file: D:/hoonProJect/worktrees/agent-factory/.af_runtime/codex_home/sessions/2026/06/25/rollout-2026-06-25T12-02-02-019efcba-33cc-7373-bc97-a0dfe96f5606.jsonl
- lines: 3-5

## 관련
- [[code/symbols]]
- [[knowledge/session/DESKTOP-JPHA09P-20260624T155647-400180Z-a3a557-review-gate가-실제-수정-파일-agent_launcher-py]]
- [[knowledge/session/HOON-KIM-20260625T030653-952713Z-9c3f47-stage-r-구현-진입-af-knowledge-search-cli-배선]]
- [[knowledge/session/HOON-KIM-20260625T030656-600032Z-6d99ec-stage-r-retrieval-af-knowledge-search-cl]]
- [[knowledge/session/HOON-KIM-20260625T030700-329189Z-d72f8e-stage-r-구현-진입-af-knowledge-search-cli-배선]]
- [[knowledge/session/HOON-KIM-20260625T053107-308104Z-f5cab6-stage-r-af-knowledge-search-cli-배선-완료-0f]]

