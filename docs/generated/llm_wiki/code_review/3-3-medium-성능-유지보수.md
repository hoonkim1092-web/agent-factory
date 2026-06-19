---
generated_at: 2026-06-20T00:11:25+09:00
source_commit: f5b43f0e
sources:
  - "docs/code_review/code-review.md"
---

# 3.3 Medium — 성능/유지보수

> Source: `docs/code_review/code-review.md:310`
> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]

````markdown
### 3.3 Medium — 성능/유지보수

| ID | 파일 | 라인 | 문제 |
|----|------|------|------|
| M1 | `control/run_ledger.py` | 276-292 | `_read_all()` 전체 JSONL 매번 순회. O(n) |
| M2 | `hooks/event_bus.py` | 40-46 | 훅 중복 체크 O(n²) |
| M3 | `hooks/lsp_check.py` | 40 | Pyright 타임아웃 15초 하드코딩. 에이전트 블로킹 |
| M4 | `ise_stall_detector.py` | 35,43 | 매직넘버 threshold (0.5, 0.8) 문서화 없음 |
| M5 | `agent_runner.py` | 352-489 | OpenAI/Anthropic 응답 처리 코드 거의 동일. 중복 |
| M6 | `dynamic_orchestrator.py` | 582-598 | Terminal 모드 0.5초 폴링. 이벤트 기반 전환 권장 |
| M7 | `ise_loop.py` | 91 | 외부 while True 루프에 max meta-cycles 없음 |
| M8 | `run_budget.py` | 전체 | 동시성 Lock 없음. 멀티스레드에서 race condition |
| M9 | `af.spec` | 19-173 | hiddenimports 100+개 수동 관리. 누락 시 frozen 빌드 런타임 크래시 |
| M10 | 다수 파일 | — | Non-atomic JSON 쓰기 패턴 잔존 (아래 참조) |

**M10 상세 — Non-atomic 파일 쓰기 잔존 목록** (C2/H5a와 동일 유형, 미수정):

| 파일 | 쓰기 대상 | 위험도 |
|------|----------|--------|
| `conversation_manager.py:130,145,181` | metadata/consensus/index.json | Medium |
| `document_index.py:351` | INDEX_CACHE_FILE | Low (캐시) |
| `ise_strategy_ledger.py:196` | ise_ledger_{run_id}.json | Medium |
| `pdca_state.py:92` | pdca_state.json | Medium |
| `project_pipeline.py:135` | checkpoint/{stage}.json | Medium |
````
