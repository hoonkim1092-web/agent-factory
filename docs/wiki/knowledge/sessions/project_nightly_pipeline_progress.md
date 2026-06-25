---
name: 야간 자율 파이프라인 구현 진행 상황
description: Phase -1~4 구현 상태 추적 — 어디까지 됐고 무엇이 남았는지
type: project
originSessionId: 93e5c99d-7ea1-4e04-85d9-8faefaadb5cc
---
설계 문서: `docs/2026-04-18-nightly-autonomous-pipeline.md` (v3, 773줄)

## 완료

- **Phase -1** (commit `0b766b8d`): Blueprint 드리프트 6건 동기화
- **Phase 0** (commit `325dbbf2` + `d4b26d7d`): launchd tick 인프라
  - `core/watchdog.py`, `core/nightly_state.py`, `scripts/nightly_tick.py`
  - `scripts/nightly_summary.py`, `scripts/install_launchd.sh`
  - `DynamicOrchestrator.restore_from()`, nightly-start/stop/status/tick CLI
  - af-critic BLOCK 3건 해소 (from_dict 타입 안전성)

- **Phase 1** (commit `fdf31f60`): 외부 의존 3-티어 fallback + 금지 토큰 스캐너
  - `core/document_policy.py` (신규): FORBIDDEN_TOKENS, scan_forbidden_tokens(), jaccard_similarity()
  - `core/work_item_generator.py`: `_generate_and_refine()` LLM 보강 루프 max 2회
  - `projects/lotto_predictor_v2/seed_draws.json` (신규): 100회차 seed 데이터
  - `lotto_predictor_v2/http_client.py`: `ThreeTierLotteryClient` (live→cache→seed)
  - `lotto_mobile_web/recommendation.py`: `_load_seed()` Tier 3 경로
  - `docs/patterns/2026-04-18-external-api-3tier.md`, `scripts/refresh_lotto_seed.py`, `scripts/measure_goal_overlap.py`

- **Phase 4** (2026-04-19, 커밋 5d06674b~6b2182f1): 에피소드 학습 메모리
  - `core/memory_system/strategy_ledger.py` (신규): 역할 배정 성공/실패 기록, auto-save gate
  - `core/memory_system/episode_matcher.py`: query_similar top-k 확장, seed 에피소드 검색
  - `core/project_task_board.py`: _pick_owner_role ledger-first, logger.warning
  - `core/project_pipeline.py`: execute() 완료 후 record_role_success/failure 호출 (루프별 격리)
  - `memory/episodes/`: 3개 seed 에피소드 .md 파일
  - af-critic WARN (BLOCK 없음), af-cross-review BLOCK 없음, af-test-runner 73개 통과

- **Phase 2** (2026-04-19, 커밋 7db415ee + ea4e616d): approval-gate ← verification 연결 + e2e 계약 강제
  - `templates/verify-handoff.md.tpl` (신규): e2e_command/exit_code/verdict 필드 포함
  - `scripts/verify_handoff_checker.py`: BLOCK 2건 + af-critic WARN 4건 해소
    - {{e2e_command}} 미치환 bypass 수정, import 실패 fallback 수정
    - 이중 오류 보고 제거, dead key 제거, 주석 번호 수정, sys.path 중복 제거
  - `core/work_item_generator.py`: DoD 섹션에 verify-handoff.md.tpl 참조 추가

- **Phase 3** (커밋 `97366bed`): ISE 배선 + lineage 기반 Level 누적
  - `core/lineage_ledger.py` (신규): lineage별 level/attempts 추적
  - `core/dynamic_orchestrator.py`: 실패 시 FSALoop 위임 + lineage_ledger 연동

- **Appendix B 버그 수정** (2026-04-20, 커밋 `4afa8bf2` + `1f3fb884`): af-critic/cross-review 발견 버그 총정리
  - `core/lineage_ledger.py`: threading.Lock, _get_or_create 리네임(호출부 포함), _CACHE_LOCK, atomic write
  - `core/memory_system/strategy_ledger.py`: composite key(dp::role), _load 중복 합산, _CACHE_LOCK
  - `core/memory_system/episode_matcher.py`: facade=None 기본값 + seed-only 가드, _SEED_STOP_WORDS frozenset
  - `core/approval_gate.py`: 섹션 헤더 상수화, check_validity no-docs PASS 로직
  - `core/project_pipeline.py`: _write_json atomic write, gate.initialize() 전처리
  - `core/work_item_generator.py`: EpisodeMatcher() facade 없이 호출 가능
  - `core/project_task_board.py`: e2e_command 필드 추가, BOM 제거
  - `run_factory_cli.py`: spec None 가드, AGENT_CHAT_PROVIDER 항상 설정
  - `scripts/hook_runner.py`: AF_SKIP_REVIEW_GATE=1 인라인 env var 우회 감지 수정

- **B2-4** (2026-04-21, 커밋 `5cd96564`): strategy_ledger deliverables 패턴 등록 경로 추가
  - `core/project_pipeline.py`: record_role_batch 호출, 모듈명+deliverables(앞 4단어) 배치 저장
  - `core/memory_system/strategy_ledger.py`: record_role_batch 신규 (I/O 폭주 방지)
  - `tests/test_strategy_ledger.py`: 12개 단위·통합 테스트 신규
  - af-critic WARN 해소, af-cross-review PASS

- **B2-6** (2026-04-25, 커밋 `63990a71`): strategy ledger 모듈별 granularity ✅ 완료
  - C0: `write_project_board` atomic write (tempfile+os.replace)
  - C1: `_record_ledger_outcomes()` 추출 + `_task_is_infra_failure`, `_build_board_maps`, `module_outcome_from_board`, `detect_owner_drift` 헬퍼
  - C2: `nightly_summary.py` `_render_modules_section()` + 테스트 16건

- **Phase A Step 3+4+5** (2026-04-24~25) ✅ 완료
  - GateResult.quality_delta, SkillEvolutionBus/QualityGate/SelfEvolution 테스트 29건
  - MemoryScope.PROJECT, semantic_scores 전달, M8 에피소드 주입
  - version 1.2.22 bump

## 남은 작업

- **exe 빌드**: Windows에서 `python build_exe.py` → `dist/af-1.2.22.zip` → GitHub Release
- **pre-existing test failures**: `test_key_combos` 3건, `test_text_integrity`, `test_sync_wrappers` (내 코드와 무관)

**Why:** 전체 야간 자율 파이프라인 구현 완료. 남은 건 배포 빌드(Windows 전용)뿐.
**How to apply:** 다음 세션에서 Windows 환경으로 전환 후 빌드 진행.

## 관련
- [[code/symbols]]

