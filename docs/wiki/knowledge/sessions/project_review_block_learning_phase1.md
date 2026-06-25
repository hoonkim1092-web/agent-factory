---
name: project-review-block-learning-phase1
description: Review BLOCK Learning Phase 1 — capture+CLI 구현(41b9d08c) + 발화 검증 실증(2026-06-21). Phase 2는 자연 데이터(≥3 재발) 대기.
metadata: 
  node_type: memory
  type: project
  originSessionId: 8df098b4-4c58-4360-932e-d9d5dada394a
---

리뷰 BLOCK 판정을 자동 학습하는 진화 메커니즘. **Phase 1 = capture-only**(BLOCK finding → pattern_key 정규화 → JSONL 기록 + `af evolution list` 조회).

**구현 (2026-06-21, Sonnet, `41b9d08c`)**:
- `scripts/review_gate.py`: `capture_block_finding()` + `_normalize_pattern_key()` (7 known family: hiddenimport / production_caller_wiring / blueprint_update / absolute_path / fixture_only / pre_commit_bypass / provider_instruction_drift. 미매칭=`unknown:<sha256_8char>`, 집계 제외). `_BLOCK_PATTERNS_RELPATH = data/review-block-patterns.jsonl`.
- `scripts/hook_runner.py:419-422`: `_post_agent_record`에서 `verdict in ("block","fail")` 시 best-effort capture.
- `scripts/af_evolution.py`: `list_patterns()` 집계(재발 ≥2 강조, unknown 제외) + `af evolution list` CLI.

**✅ 발화 검증 실증 (2026-06-21, Opus)**: 임시 격리 디렉터리에서 production 경로 그대로 end-to-end PASS — A) capture 직접+7 family 정규화+unknown fallback / B) `_post_agent_record`(hook 진입점, `_detect_workspace` monkeypatch 필수=git root 폴백이 실레포 오염 막기 위함)가 BLOCK/FAIL 캡처·PASS 무시 / C) `list_patterns` 재발 감지+unknown 제외 / D) `agent_launcher.py evolution list` CLI dispatch. 실레포 `data/` 미오염. **기능 작동 실증 완료.**

**Phase 2 진입 = 데이터 대기 (미충족)**: `data/review-block-patterns.jsonl` 아직 미생성 — 커밋 후 자연 BLOCK 발화 0회. 실 데이터(≥3회 재발 패턴)가 쌓여야 Phase 2(재발 감지 + EVP 제안) 설계 의미. P4(novel clustering)는 out-of-scope. 검증은 임시 디렉터리에서만 했으므로 실 데이터는 여전히 0.

관련: [[feedback_analysis_doc_baseline_must_be_real_code]] [[feedback_code_review_workflow_v2]]

## 관련
- [[code/symbols]]

