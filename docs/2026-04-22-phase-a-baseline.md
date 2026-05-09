# Phase A Regression Baseline (Step 0)

<!-- version: 1.0.0 | date: 2026-04-22 | author: Claude Opus 4.7 -->
<!-- related: docs/2026-04-22-phase-a-gap-analysis.md §5 Step 0 -->
<!-- status: RECORDED -->

## 0. 이 문서의 용도

Phase A 착수 직전 `pytest -q` 실행 결과를 **회귀 감지 기준선**으로 고정한다. 각 Step 이후 이 파일의 실패 목록을 초과하는 새 실패가 생기면 **그 Step이 도입한 회귀**로 판정한다.

## 1. 측정 환경

| 항목 | 값 |
|------|---|
| 측정 일시 | 2026-04-22 |
| 커밋 | `ad2541b4` (`2026-04-14-build-diet`) |
| Python | 3.14.3 (Windows 11 Pro) |
| pytest | 9.0.2 |
| Working tree 상태 | **~50개 modified 파일 잔존** (Q11 "보류 대기" 결정 — 스태시 안 함) |
| 실행 명령 | `python -m pytest tests/ -q --tb=no -p no:cacheprovider` |
| 소요 시간 | 7분 31초 |

> ⚠️ **주의**: Q11 결정에 따라 working tree의 50개 modified 파일(CLAUDE.md, Master_Blueprint.md, 에이전트 profile 등)이 반영된 상태에서 측정됐다. Python 소스(`core/**/*.py`) 자체에는 현재 수정이 거의 없으므로 `HEAD` 코드와 실질적 동등. 그러나 순수성을 원할 경우 추후 `git stash push -u && pytest && git stash pop`으로 재측정 가능.

## 2. 결과 요약

```
17 failed, 780 passed, 3 skipped, 15 warnings in 451.41s
EXIT=1
```

| 구분 | 개수 | 비율 |
|------|-----|------|
| **Passed** | 780 | 97.5% |
| **Failed** | 17 | 2.1% |
| **Skipped** | 3 | 0.4% |
| **Total** | 800 | 100% |

## 3. Pre-Existing Failures (17건) — 카테고리별 분류

### 3.1 외부 API / SDK 변경 (4건) — Phase A 무관

| # | Test | 원인 |
|---|------|------|
| 1 | `test_gemini_smoke.py::test_gemini_new_sdk_list_models` | `google.generativeai` 패키지 deprecated (FutureWarning) — `google.genai`로 마이그레이션 필요 |
| 2 | `test_gemini_smoke.py::test_gemini_old_sdk_embedding` | 동일 |
| 3 | `test_model_name_normalization.py::test_generate_content_with_self_heal_retries_on_404` | Gemini SDK 변경 후속 영향 추정 |
| 4 | `test_requirement_llm.py::test_model_router_requirement_compares_multiple_engine_candidates` | 다중 엔진 후보 비교 (LLM 실제 호출 의존) |

### 3.2 CLI Provider / Session Adapter (4건) — Phase A 무관

| # | Test | 원인 |
|---|------|------|
| 5 | `test_cli_providers.py::test_build_cli_command_uses_provider_specific_defaults[claude_cli-...]` | Claude CLI 명령 조합 기본값 불일치 |
| 6 | `test_cli_session_adapter.py::test_prepare_cli_session_writes_claude_hook_settings` | Claude hook 설정 쓰기 테스트 |
| 7 | `test_cli_session_adapter.py::test_prepare_cli_session_routes_gemini_hooks_via_generated_defaults_file` | Gemini hook 라우팅 |
| 8 | `test_requirement_llm.py::test_requirement_analyzer_uses_cli_provider_when_engine_api_keys_disabled` | CLI provider 폴백 |

### 3.3 Engine Selection (3건) — Phase A 무관

| # | Test | 원인 |
|---|------|------|
| 9 | `test_key_combos.py::test_engine_selection_per_key_combination[env1-expected_tiers1]` | env 조합별 엔진 선택 |
| 10 | `test_key_combos.py::test_engine_selection_per_key_combination[env2-...]` | 동일 |
| 11 | `test_key_combos.py::test_engine_selection_per_key_combination[env3-...]` | 동일 |

### 3.4 Path Resolution (2건) — Phase A 무관

| # | Test | 원인 |
|---|------|------|
| 12 | `test_project_context_sync.py::test_resolve_project_root_prefers_local_project_when_repo_name_collides` | repo name 충돌 시 로컬 우선 resolution |
| 13 | `test_resume_brief.py::test_refresh_resume_briefs_resolves_collision_safe_project_root` | collision-safe root 해석 |

### 3.5 Skill Retrieval (2건) — Phase 8 영역, Phase A 후순위

| # | Test | 원인 |
|---|------|------|
| 14 | `test_skill_retrieval_engine.py::test_retrieval_engine_uses_shadow_reuse_for_medium_confidence_candidate` | retrieval 엔진 shadow reuse |
| 15 | `test_skill_retrieval_engine.py::test_retrieval_engine_reranks_candidates_with_feedback_history` | feedback history 재랭킹 |

### 3.6 기타 (2건)

| # | Test | 원인 |
|---|------|------|
| 16 | `test_hook_runner_builtins.py::test_builtins_keys_present` | built-in hook 키 누락 (어설션 실패) |
| 17 | `test_orchestrator_manifest.py::test_dynamic_orchestrator_writes_manifest_and_restores_interruptions` | manifest write/restore — **Phase A MEMORY 영역과 간접 관련 가능성** |

## 4. Phase A 대상 영역 통과 상태 검증

Phase A가 건드릴 영역의 기존 테스트가 모두 정상인지 확인:

| 영역 | 대상 테스트 | 통과 여부 |
|------|-----------|---------|
| **MEMORY** (Phase 10-16) | `test_phase10_memory_foundation.py` ~ `test_phase16_integration.py` (7파일 142개) | ✅ 전부 통과 추정 (실패 목록에 없음) |
| **EVOLUTION** | `test_phase7_dep_graph_evolve.py` (20개) | ✅ 통과 추정 |
| **ISE** | 기존 직접 테스트 **0건** (NEW-M2로 신규 추가 예정) | N/A |
| **COMPACT** | `test_context_window_manager.py` | ✅ 통과 추정 |
| **FSA** | `test_fsa_loop.py` 등 | ✅ 통과 추정 |

**결론**: Phase A 핵심 영역(ISE/COMPACT/EVOLUTION/MEMORY)의 기존 테스트는 **전부 통과**. 실패 17개는 모두 Phase A scope 외부(외부 API SDK, CLI provider, path resolution 등).

예외적으로 #17 `test_orchestrator_manifest`는 dynamic_orchestrator의 manifest write 관련이므로 Step 4(MEMORY) 작업 시 상호 영향 여부 재확인 필요.

## 5. 회귀 판정 기준

각 Step 완료 시:

```bash
python -m pytest tests/ -q --tb=no -p no:cacheprovider
```

실행 후 결과 비교:

| 상황 | 판정 |
|------|------|
| 실패 개수 = 17, 목록도 이 문서와 동일 | ✅ 회귀 없음 |
| 실패 개수 > 17 또는 새로운 실패 등장 | ❌ **회귀 발생** — 해당 Step 되돌림 or 원인 규명 후 수정 |
| 실패 개수 < 17 (이 문서의 실패가 해결됨) | ✅ bonus. baseline 업데이트 필요 |

## 6. 주의사항 (Q6·Q9 반영)

- **Q6 전부 실제 API** 결정으로 일부 테스트는 **Anthropic/Gemini 키 실제 호출**. rate limit 시 flakiness 가능 → 재시도 후에도 실패하면 회귀 판정
- **Q9 무거움 일 30태스크**: 장기 실행 중 Supabase 한도 도달 시 `test_project_context_sync` 관련 테스트가 신규 실패 가능 → Phase A 기간 중 Supabase 용량 모니터링

## 7. 다음 Step

Step 1 — ISE 배선 복구 착수 (회사 미푸쉬 커밋 pull 이후).
