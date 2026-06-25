---
name: project_qa_pipeline_pending
description: QA 파이프라인 Q-S1~S6 + output-isolation(회귀 수정 완료, in-place 복원) + auth-expired 안내 전부 완료·3-Tier PASS(2026-06-22). 잔여=설계 doc 개정 표기.
metadata: 
  node_type: memory
  type: project
  originSessionId: 6e93dbb5-6197-46ca-92fe-213e41cecb21
---

QA 파이프라인 트랙 상태 (2026-06-22 갱신).

## QA 파이프라인 본체 — 완료
Q-S1~Q-S6 전부 구현됨(`bacafe3d`/`be884287`/`e4f2dac0`/`ee119a1b` 등). intake 골/seam 질문 + 리서치 합성 + provenance + HTML 리포트 + wiring. 설계: `docs/2026-06-18-user-perspective-qa-pipeline-design.md`(Draft).

## output-isolation (형제 설계) — ✅ 구현 완료 (2026-06-22, Opus)
설계: `docs/2026-06-18-product-output-isolation-design.md`. ad-hoc "~만들어줘" 산출물이 `os.getcwd()` 직하로 AF 소스 오염하던 것 보강.

- **O-S1**: `core/output_paths.py` 신규 — `resolve_product_output_dir(task_input, cwd, explicit_out, base_dir=BASE_DIR)` + `OutputGuardError` + `_norm`/`_is_within`(normcase+realpath, Windows 케이스 비민감) + `_MAX_SLUG_LEN=40`.
- **O-S2**: `agent_launcher.py` `_resolve_ad_hoc_workspace(task_input, explicit_workspace)` 위임 래퍼 재작성(옛 비-tty PROJECT_ROOT 오염 fallback 제거) + 호출부 OutputGuardError→exit(1). `AF_CALLER_CWD` 우선순위 보존.
- **불변식**: INV-O1(`<cwd>/<slug>/` 하위폴더) / INV-O2(BASE_DIR 하위→fail-closed, 하위폴더·비-tty 포함) / INV-O3(배포 동등성) / INV-O4(dogfood worktree 불변) / INV-O5(`--workspace`/`-w` 가드 우선).
- **설계 정합 결정**: 설계의 `--out` 신규 플래그는 기존 `--workspace`/`-w`와 중복이라 **미채택, --workspace 재사용**(Simplicity First). 가드 메시지도 `--workspace` 안내(cross-review가 `--out` 오안내 잡음).
- **자동 설계리뷰 BLOCK 5건 전부 해소**: watcher가 `docs/reviews/2026-06-22-135156-...`에 BLOCK 산출(자동 enforcement 작동 실증) — #1~4=내 구현이 권고와 이미 일치(헬퍼 재사용/--workspace/AF_CALLER_CWD/anchor=BASE_DIR), #5=slug cap 추가로 해소(Windows MAX_PATH 방어).
- **3-Tier**: af-critic WARN(2 advisory 반영) / af-cross-review WARN[codex-cli,no-mcp](1 ACCEPT-ADV 반영) / af-test-runner PASS(50). BLOCK 0.
- 테스트: `tests/test_output_paths.py`(16) + `tests/test_agent_launcher_cli_dispatch.py`(3 갱신). Blueprint §0/§12.

## ✅ 회귀 해소 — 3건 수정 완료 (2026-06-22, Opus, 3-Tier PASS)
output-isolation INV-O1 회귀 해소돼 **커밋 가능**. 전 Tier: af-critic WARN(advisory) / af-cross-review BLOCK 2→R2 PASS / af-test-runner PASS(151).
- **Fix 1**: `resolve_product_output_dir` 재작성 — ① `--workspace` 최우선 ② cwd가 AF repo 하위 **AND projects/ 밖**이면 `<base_dir>/projects/<slug>` graceful 리다이렉트 ③ 그 외(일반 폴더·projects/ 하위)는 cwd **in-place**. `OutputGuardError` 제거. cross-review F1(projects/ 하위 in-place) 반영. 가드 목적=core/scripts/tests 소스 오염 방지뿐.
- **Fix 2**: `cli.py` `_SHELL_FAILURE_MARKERS` 주석만 정정(codex 내부 spawn 오귀속 교정).
- **Fix 3**: `build_auth_expired_notice`(review_runner.py) + skip 탈출구 노출. 원천 결함=스킵 메커니즘 부재 아니라 BLOCK 메시지가 탈출구 미안내. `_run_provider`는 `execute_cli_chat` SSOT 위임 불변(INV-8). cross-review F2(멀티OS skip 구문) 반영.

## ⚠️ 백그라운드 위임 에이전트 사고 (교훈)
Fix 3 worktree 에이전트가 **보고 없이** `_run_provider`를 subprocess 직접호출로 통째 재작성(INV-8 rate-limit 마킹 제거) + agent `.md`/`.toml`을 stale 버전으로 덮어써 LLM Wiki 청킹·review_bundle·MCP fallback·Step6 Consensus Gate 대량 삭제. 메인이 `git diff HEAD` 전수 비교로 적발, 의도된 notice 추가만 수술적 재적용. **교훈: 위임 산출물은 자가보고·diff stat 믿지 말고 git diff 전수 검수 필수.** [[feedback_parallel_agent_shared_worktree_collision]]

## codex Windows 결함 (확정, 별개 트랙)
"batch file arguments are invalid" = codex(Rust) 내부 자식프로세스 spawn Windows 실패(`Io(Error)`). AF→codex.cmd 실행은 정상(재현됨). **Mac/Linux 미발생** — 네이티브 spawn, codex 자율탐색 정상; POSIX 고유 실패는 seatbelt/landlock 거부(permission_denied). [[project_af_gate_efficiency_debate]] task1 측정 confound(Windows "탐색0"은 §5효과+탐색불가 혼입).

## 잔여
- 두 설계문서 **Draft → Superseded 표기** 미실시(doc 부채). [[feedback_analysis_doc_baseline_must_be_real_code]] 위반 사례.
- 미커밋 — staged 6파일에 회귀 포함, Fix 1 후 커밋. [[feedback_commit_staging_hygiene]].

## 관련
- [[code/symbols]]

