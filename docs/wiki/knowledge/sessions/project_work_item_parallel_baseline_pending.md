---
name: work-item 병렬화 v3.1 설계 PASS 간주, Sonnet 본 구현 대기
description: v3.1 cross-review 2라운드 SKIP (Codex 한도, CLAUDE.md provider-0=PASS). 다음: Sonnet으로 §11 (c) 항목 본 구현 PR.
type: project
originSessionId: 8a19365e-b9e1-4fce-91fe-1320913841ed
---
# Work-Item 4종 병렬화 — v3.1 cross-review 2라운드 대기 (2026-05-11)

## 현재 상태
- 설계 v1 (`docs/2026-05-08-work-item-parallel-option-c-design.md`) — cross-review BLOCK (14+5건 ACCEPT)
- 설계 v2 (`docs/2026-05-08-work-item-parallel-option-c-design-v2.md`, 957 lines)
  - 1라운드 (`...-140854-...`): BLOCK
  - 2라운드 (`...-142400-...`): WARN (13건 ACCEPT)
- 설계 v3 (`docs/2026-05-08-work-item-parallel-option-c-design-v3.md`, 1421 lines) — v2 2라운드 13건 흡수
  - 1라운드 (`...2026-05-11-001451-...-v3-design-review.md`): **BLOCK 11건** (Critic 단독, Cross provider error)
- **설계 v3.1** (같은 파일, 1481 lines) — v3 1라운드 11건 흡수, **cross-review 2라운드 대기**

## v3 흡수 결과 (2026-05-11)
- **5 High 모두 처리**:
  - F1: refine loop budget guard (per-iteration `iter_timeout = max(1, deadline - time.monotonic() - 5)`, Stage 3 진입 전 5s grace wait) — §6 보강
  - F2: `_call_{anthropic,openai,google}_api(timeout_sec=)` 시그니처 통일 + SDK별 transport timeout 인젝션 — §10 보강
  - F3: Episode Hints 주입 (`_exec_stage1` 반환 직전 명시) — §7a 신설
  - F4: `_exec_stage1`/`_exec_stage3` 풀 구현 — §7a/§7b 신설
  - F5: asyncio NOT APPLICABLE (`project_pipeline.py:1231 def execute(`은 sync, grep 검증) — §3 불변식 + §14 Step 0.6 가드
- **2 Medium 처리**: F7 (telemetry 경로 `workspace_runtime_dir(workspace) / "work_item_telemetry"`) / F12 (Stage 3 budget trigger §14 Step 4.1)
- **2 Medium close**: F6 (fallback 4개 grep — `_fallback_feature_plan:199`, `_fallback_feature_spec:274`, `_fallback_impl_design:378`, `_fallback_impl_tasks:511` 모두 존재) / F8 (`_PLACEHOLDER_REFINE_MAX = 2` grep, budget 산정 그대로 유효)
- **2 Low 처리**: F9 (outline mismatch 시 빈 문자열 반환) / F10 (`_dname` doc_type 문자열 명세)
- **1 REJECT 유지**: F11 (`af.spec:76`에 이미 `core.work_item_telemetry` 등록 — cross 라운드 검증)

## 채택된 결정 (이미 합의, 변경 X)
- Stage 구조: **C-3stages** (`plan → [spec, design] 병렬 → tasks`)
- run_id 격리: (D′) `{base}_{doc_type}_{pid}_{time_ns}_{uuid_hex8}`
- prev_doc 합성: B3 (tasks ← design 전문 + spec 섹션 목차만)
- deadline: C3 (Stage별 + carry-over)
- executor: D3′ (`cf.wait(ALL_COMPLETED)` + per-future `timeout_sec` + `cancel_futures=True`)
- state cleanup: 30일 TTL
- TOTAL_BUDGET = 600s, STAGE_BUDGET = {1: 90s, 2: 400s, 3: 110s}
- v3 추가: refine loop budget guard, Stage 3 진입 전 5s grace, `_call_*_api` SDK별 transport timeout 인젝션

## 측정 결과 (2026-05-08 Sonnet 1회 실측, minesweeper)
| doc_type | elapsed_sec | refine_attempts | output_chars |
|----------|-------------|-----------------|-------------|
| plan | 62.9 | 0 | 202 |
| spec | 84.9 | 0 | 6,539 |
| design | **267.4** | **2** | 5,277 |
| tasks | (미측정 — fallback) | — | — |

Raw: `runtime/timing/build-a-playable-8x8-cli-minesweeper-game-where-the-player-c_baseline.jsonl`

## 다음 단계 흐름
1. ~~Sonnet baseline~~ ✅ 완료 (2026-05-08)
2. ~~Opus v2 작성~~ ✅ 완료 (2026-05-08, 2라운드 WARN)
3. ~~Opus v3 작성 (v2 13건 흡수)~~ ✅ 완료 (2026-05-11)
4. ~~v3 1라운드 cross-review~~ ✅ 완료 (BLOCK 11건, Critic 단독)
5. ~~Opus v3.1 작성 (1라운드 11건 흡수)~~ ✅ 완료 (2026-05-11)
6. ~~v3.1 cross-review 2라운드~~ **SKIP (Codex 한도, CLAUDE.md provider-0=PASS 정책)** — 2026-05-11
7. **Sonnet 본 구현 PR** (C-3stages 병렬화) ← **여기부터**
   - `core/work_item_generator.py:1184 _generate_and_refine` 시그니처에 `deadline: float` 추가
   - `core/requirement_llm.py:78/98/118 _call_*_api(timeout_sec=)` 시그니처 통일 (anthropic은 urllib)
   - `core/work_item_telemetry.py:14, 45` path `workspace_runtime_dir(workspace) / "work_item_telemetry"`
   - `_exec_stage1`/`_exec_stage3` 신설 + Episode Hints 주입
   - `_extract_section_outline:813` mismatch 시 빈 문자열 반환 (F9)
   - `cli_session_cleanup` 디렉토리 mtime 정책 (R8)
   - `_write_claude_settings` lock wrap (`session_adapter.py:281-304`)

## (선택) v3.1 cross-review 2라운드 재실행 조건
Codex 한도 reset 후 또는 copilot/gemini-cli 인증 시 명시 spawn:
```
af-cross-review subagent로 docs/2026-05-08-work-item-parallel-option-c-design-v3.md 검증
- 1라운드 BLOCK 11건이 v3.1에서 해결됐는지
- 새 finding 추가
```
정합성 추가 보장이 필요하면 본 구현 PR 진입 전 진행 권장.
   - `core/work_item_generator.py` (refine guard / `_exec_stage1`·3 신설 / `_generate_and_refine` deadline 시그니처)
   - `core/requirement_llm.py` (`_call_*_api(timeout_sec=)` 통일)
   - `core/work_item_telemetry.py` (신규, `workspace_runtime_dir` 사용)
   - `core/cli_session_cleanup.py` (신규)
   - `core/providers/session_adapter.py` (`_write_claude_settings` lock wrap)

## 상태 (2026-05-11)
- v2 / v3 모두 **untracked** (commit 미수행)
- v3 단독 commit 또는 v2 + cross-review 묶음 commit 결정 필요 (사용자 합의 후 진행)
- cross-review는 design 문서 commit 후 hook이 자동 발화 또는 직접 af-cross-review spawn
