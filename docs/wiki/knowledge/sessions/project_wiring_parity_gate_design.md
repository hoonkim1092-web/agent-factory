---
name: project-wiring-parity-gate-design
description: 배선 단선 검증 게이트 — 설계+구현 완료(2026-06-12). WARN-only, dead-parameter 집중, utils 면제, deferred 마커.
metadata: 
  node_type: memory
  type: project
  originSessionId: 0ab7e78c-0e88-467c-81a6-33a53b62c627
---

반복 문제: 함수/파라미터 추가 시 production 배선 미연결로 dead code化 (blast_radius 사례 — [[feedback_pipeline_deploy_parity]]). 신규 게이트가 아니라 기존 3-Tier에 배선 검증 통합 결정. 사용자 지시: "이 문제는 AF 전체를 해야 한다."

**동결된 설계 원칙 (재분석 금지)**:
1. 함수 = 배선 + 통합테스트 한 세트 = 완료 (CLAUDE.md 배포 동등성). 배선 없으면 미완료. unit test만은 leaf만 검증.
2. dead-symbol보다 dead-parameter 집중 (기존 함수에 새 파라미터 → 어떤 caller도 안 넘김 = 핵심 신호).
3. 순수 유틸(weighted_mean류) 면제(test-only). 슬라이스 분할은 `# wiring: deferred` 마커 → 통과.
4. WARN로 시작 → false-positive 실측 후 BLOCK 승격. 단일커밋 BLOCK 금지(다음커밋 연결 정상워크플로 방해).

**통합 2-layer**:
- ① `scripts/test_gap_analyzer.py` `wiring_parity` 룰 (구조적·자동). af-test-runner가 전 경로 검사 → "AF 전체" 자동 달성.
- ② `.claude/agents/af-critic.md` Step3 High 항목 (review_bundle §5 Direct Callers 대조, 의미적·LLM). §5는 이미 입력에 있으나 대조 지시 부재.

**재사용 자산**: `core/ast_engine.py` `search_dir()`(ast-grep-py 설치됨, 정확) / `core/review_bundle.py:252 _find_direct_callers`(grep, 부정확) / `codebase_symbols.py`(정의 인덱스) / `blast_radius.py`(Tier 분류만, caller 추적 X — 오해 주의).

**실측 baseline (PoC 삭제됨)**: 공개 top-level 심볼 2,610 중 dead-symbol 후보 2,004(77%), core/scripts 191. 순수 dead-symbol 전수는 노이즈 77%라 게이트 부적합 → diff 기반이 본체. grep 검증: git_configure_and_push/run_cross_verification 실제 prod 미사용(PoC 정확).

**✅ 설계 문서 작성 완료 (2026-06-12, Opus)**: `docs/2026-06-12-wiring-parity-gate-design.md`. af-cross-review **PASS(BLOCK 0)** — 코드 좌표 전부 grep 정합, 내부 모순 없음(INV-1 "승격 전" vs §6 승격 양립 확인). 단 codex 비활성→single-vendor. Advisory 3건 반영: W-HUNK-SPLIT/W-INIT-PARAM 테스트 케이스 + §8 Step1 tests/ 제외 명시(search_dir는 tests/ skip 안 함, 호출측 처리). 문서 구조: §3 Layer① test_gap_analyzer wiring_parity 룰(diff 기반 신규함수/dead-parameter 추출+production caller 검사), §4 Layer② af-critic Step3 High 1줄, §6 WARN→BLOCK 승격(dead-parameter만, dead-symbol 영구WARN), §7 테스트 10케이스, §8 test-first 6단계, §9 INV-1~7.

**✅ 구현 완료 (2026-06-12, Sonnet, `5a16df39`)** — 메모리 stale 정정(2026-06-21 재확인). 6개 심볼 `scripts/test_gap_analyzer.py`에 실재: `_WIRING_EXEMPT_PATHS`(L61, `frozenset({"core/utils.py"})`)·`_WIRING_DEFERRED_MARKER`(L62)·`_extract_wiring_candidates`(L303)·`_find_production_callers`(L350)·`_any_caller_passes_param`(L403)·`_has_deferred_marker`(L420). `analyze_diff()`(L512-544)에 **WARN-only** 배선(verdict 미영향, `warnings.append("[wiring] ...")` 채널만). `tests/test_wiring_parity.py` 11케이스 PASS. af-test-runner가 `test_gap_analyzer.py --workspace .`로 호출.

**잔여 = 선택적 advisory 2건(의무 아님)**: ① `_any_caller_passes_param` file-level false-negative 정밀화(`sym(` 라인 한정 스캔) ② dead-parameter WARN→BLOCK 승격(false-positive 실측 N≥10 누적 선행 필요, 현재 미실행). 관련: [[feedback_pipeline_deploy_parity]] [[project_af_gate_efficiency_debate]] [[feedback_no_hardcode_single_type_source]]
