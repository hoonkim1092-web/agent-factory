---
id: "session/HOON-KIM-20260625T053107-308104Z-f5cab6-stage-r-af-knowledge-search-cli-배선-완료-0f.md"
type: "session"
scope: "project"
title: "STAGE R `af knowledge search` CLI 배선 완료(`0f423389`)하고, `core"
author: "HOON-KIM\\HOON"
source_machine: "HOON-KIM"
created_commit: "a67c19a5"
created_at: "2026-06-25T14:31:07+09:00"
visibility: "private"
links: []
---

STAGE R `af knowledge search` CLI 배선 완료(`0f423389`)하고, `core/output_paths.py:69`·`core/review_runner.py:67`·`sync_claude_memory.py:251` BLOCK 3건 미해소 상태로 커밋(`a67c19a5`)하며 STAGE 2 착수 전 처리 의무를 NEXT_STEPS에 기록.

## 결정 (Decisions)
- `af knowledge search` CLI 서브커맨드를 `run_factory_cli.py`에 연결 — `core/knowledge/retrieve.main`을 production caller로 배선 완료(커밋 `0f423389`); `--query`, `--files`, `--diff`, `--type`, `--limit`, `--json`, `--vault` 플래그 전부 argv로 전달.
- `data/review-block-patterns.jsonl`에 신규 패턴 2건 추가: (1) `unknown:88f6c557`(high, 2026-06-22) — `core/output_paths.py:69` 리다이렉트 조건이 projects/ 내 앱 경로를 AF repo 하위로 잘못 판정, `core/review_runner.py:67` Windows SKIP 탈출구 비작동; (2) `production_caller_wiring`(high, 2026-06-23) — `sync_claude_memory.py:251` `on_conflict=proje...` 검증 미완 포함.
- STAGE R cross-review에서 codex 사용 한도 소진(2026-06-25 04:24 PM KST까지 재시도 불가)으로 single-vendor Claude 단독 4라운드 진행 후 WARN으로 처리하고 진행 결정.
- BLOCK 3건(`core/output_paths.py:69`, `core/review_runner.py:67`, `sync_claude_memory.py:251`)을 즉시 수정하지 않고 NEXT_STEPS.md에 'STAGE 2 증류기 착수 전 처리 의무'로 명시 기록(커밋 `a67c19a5`) — 연기 허용, 단 STAGE 2 진입 차단 조건.

## 기각 (Rejections)
- codex 한도 재충전을 기다린 뒤 cross-review 재수행 — 이유: 단일 vendor WARN은 provider=0 PASS 정책에 따라 통과 간주하고 진행; 재시도 대기는 불필요한 블로킹.
- BLOCK 3건 즉시 수정 후 STAGE R 커밋 — 이유: 해당 버그는 output-isolation·review_runner 영역이고 STAGE R(knowledge retrieval) 구현과 직접 의존 없음; 별도 작업으로 분리해 NEXT_STEPS 추적이 더 적절.

## 패턴 (Patterns)
- production caller 배선 검증 패턴: `run_factory_cli.py`/`agent_launcher.py`까지 end-to-end argv 흐름을 grep으로 확인한 뒤 커밋 — 픽스처 통과만으로 완료 간주 금지(파이프라인 배포 동등성 규칙).
- review-block-patterns.jsonl 패턴 키 누적: BLOCK 판정 시 `pattern_key`·`severity`·`changed_files`·`finding_excerpt`를 JSONL에 추가하여 동일 패턴 재발 추적.
- single-vendor 모드 처리: 외부 프로바이더 한도 소진 시 WARN 기록 + 재시도 가능 시각 명시 후 Claude 단독 결과로 진행; BLOCK 없으면 SKIP이 아닌 PASS 간주.
- 미해소 BLOCK의 연기 기록 패턴: 즉시 수정이 어려운 BLOCK은 NEXT_STEPS.md에 '다음 단계 착수 전 필수 처리' 조건으로 명시하여 세션 간 컨텍스트 유지.

## 정밀 참조 (verbatim, INV-K5)
- `core/output_paths.py:69`
- `core/review_runner.py:67`
- `sync_claude_memory.py:251`
- `e1f4c1c5`
- `f48f7d66`
- `88f6c557`
- `e245fb14`
- `e3c0fca7`
- `a02e109d`
- `c1d5ecb7`
- `eacd67dc`
- `d75f3c49`
- `1779867851`
- `3611529e`
- `20260513`
- `a67c19a5`
- `9a3f9fcc`
- `0f423389`

## raw 포인터 (§3.3 — 원문은 originating PC 에만)
- originating_pc: HOON-KIM
- session_file: D:/hoonProJect/worktrees/agent-factory/.af_runtime/codex_home/sessions/2026/06/25/rollout-2026-06-25T14-29-38-019efd41-563c-71e3-9a65-f73488670784.jsonl
- lines: 3-64
