# Design Review: 2026-05-08-work-item-parallel-option-c-design-v2

> Source: docs/2026-05-08-work-item-parallel-option-c-design-v2.md
> Date: 2026-05-08 14:08
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

여러 건의 Critical/High 발견 사항이 동시에 존재. 두 리뷰어가 명백히 합치하는 코드 레벨 불일치가 3건 이상이며, cross-review의 코드 추적 결과 design이 가정한 호출 체인이 실제 코드와 끊겨있음. 구현 진입 전 v3 수정 필수.

---

### Aggregated Findings (13 total)

#### 1. [ACCEPT] [Critical] `cli_session_cleanup.py` import 경로 오류
- **Critic**: §9 line 616 `from core.workspace_paths import workspace_runtime_dir` — 해당 모듈 부재, 즉시 `ImportError`
- **Cross**: 동일 지적. 실제 함수는 `core/continuity/runtime_paths.py:9`에 존재
- **Judgment**: 양 리뷰어 합치 + 코드 grep으로 확인됨. `core/providers/session_adapter.py:14`에서 이미 `from core.continuity.runtime_paths import workspace_runtime_dir` 사용 중.
- **Action Required**: §9 import를 `from core.continuity.runtime_paths import workspace_runtime_dir`로 정정. §11 hiddenimports 표 주석 갱신.

#### 2. [ACCEPT] [Critical] Stage 2 병렬 호출 시 `_write_claude_settings`의 run_id 덮어쓰기 race
- **Critic**: lock은 JSON 깨짐만 막고, `_hook_command()`가 settings에 박은 `--run-id`는 **last-writer-wins** — 한 subprocess가 다른 형제의 run_id로 hook 발사
- **Cross**: not flagged
- **Judgment**: §4 lock은 R-M-W cycle만 보호. `_hook_command(session_adapter.py:220-236)`가 run_id를 명령어 문자열에 직접 새기는 구조이므로 critic 지적 타당. 텔레메트리/추적 정합성 직접 위협.
- **Action Required**: 다음 중 1택 — (a) `prepare_cli_session→subprocess.spawn` 윈도우 전체 락, (b) 호출별 settings 파일(`.claude/settings.local.{run_id}.json`) + env로 패스, (c) race 수용 + Step 0에 "각 subprocess의 hook event가 자기 run_id로 도착" assertion 추가. 가장 보수적인 (b) 권장.

#### 3. [ACCEPT] [High] `_extract_section_outline(expected_count=11)`이 실제 12 섹션과 불일치
- **Critic**: `_generate_feature_spec` prompt + `_fallback_feature_spec`가 12개 `##` 섹션 생성. `expected_count=11`이면 정상 실행마다 warning fire — assertion이 거꾸로 동작
- **Cross**: 동일 지적 (`work_item_generator.py:594-599`, `:315-335` 참조)
- **Judgment**: 양 리뷰어 합치 + 코드 라인 인용 일치.
- **Action Required**: §8 line 548 `expected_count=12`로 수정. 더 나아가 doc_type별 expected_count 맵 또는 prompt builder 상수 export로 분리.

#### 4. [ACCEPT] [High] `_refine_document` 경로가 timeout/run_id/workspace 전파 체인에서 끊김
- **Critic**: not flagged
- **Cross**: refine은 `ControlPlaneLLM().generate()` (`work_item_generator.py:933`, `control_plane_llm.py:122-123`) 사용 — Stage deadline·`run_id` 추적 단절. 별도 300s timeout
- **Judgment**: cross가 라인까지 인용. 설계 §3 호출 체인 다이어그램은 `_generate_and_refine → generators → _generate_doc_with_llm → execute_document_prompt`로 그리지만, refine은 별도 경로. 설계의 핵심 약속(전파)이 깨짐.
- **Action Required**: §5/§6에 명시 — `_refine_document`도 `workspace, run_id, timeout_sec`을 받아 `execute_document_prompt` 기반으로 통일하거나, `ControlPlaneLLM`에 timeout/workspace 주입 인터페이스 추가.

#### 5. [ACCEPT] [High] 텔레메트리 파일 키가 slug-only — N≥5 비교 데이터 유실
- **Critic**: not flagged (별도로 telemetry path 일관성 지적, finding #8)
- **Cross**: §11 dump 경로 `runtime/work_item_telemetry/{slug}.json` + §14 Step 4 N≥5 median 비교 요구가 상충. 같은 slug 반복 시 마지막 실행만 남음
- **Judgment**: cross 지적 타당. Step 4 비교 메트릭의 핵심 데이터(elapsed/refine/usage)가 매 실행마다 덮어써지면 의사결정 근거 부재.
- **Action Required**: `{slug}_{run_id}.json` 또는 JSONL append(record-per-run) 형식으로 변경. §5/§11 둘 다 갱신.

#### 6. [ACCEPT] [High] `locked_file(timeout=5)` vs stale-lock 정리 임계 10s 충돌
- **Critic**: not flagged
- **Cross**: `core/file_lock.py:24, :72` — stale 정리는 10s 후. 5s timeout이면 stale lock이 정리되기 전에 실패
- **Judgment**: cross가 라인 인용. 크래시 시 회복 시나리오에서 실패 경로로 빠짐. 직관적 정합성 깨짐.
- **Action Required**: `timeout`을 `>10s` (예: 12s)로 상향, 또는 `_FILE_LOCK_STALE_SEC`/`timeout`을 같은 상수로 묶는 정책 추가.

#### 7. [ACCEPT] [High] `_call_*_api(return_usage=True)` 추출 코드/dict shape 미명세
- **Critic**: 3개 SDK가 서로 다른 usage shape (anthropic raw HTTP `data["usage"]`, openai `client.responses.create`의 `ResponseUsage`, google `generate_content_with_self_heal`)인데 설계는 추출 스니펫 0건
- **Cross**: not flagged
- **Judgment**: critic이 SDK 별 차이를 코드 라인까지 인용. 명세 부재 시 구현자가 빈 dict 반환 → §14 Step 4의 token usage 비교 컬럼 무용지물(OQ1 resolved 무산).
- **Action Required**: §10에 dict shape 정식 정의 (`{"prompt": int, "completion": int, "total": int}`) + 3개 provider 각각의 추출 스니펫 명시. anthropic raw HTTP는 `data.get("usage", {})`에서 `input_tokens`/`output_tokens`.

#### 8. [ACCEPT] [Medium] `_write_claude_settings` `TimeoutError`가 현재 `prepare_cli_session`에서 미처리
- **Critic**: not flagged
- **Cross**: §4 line 222가 "호출자가 try/except로 wrap"이라 가정하나, 현재 `prepare_cli_session` (`session_adapter.py:474, :475`)은 그런 처리 없음. 전체 CLI 세션 준비 실패로 전파됨
- **Judgment**: cross 지적이 코드 인용 기반. 설계가 "wrap" 자체를 변경 대상에 명시해야 함.
- **Action Required**: §11 변경 표에 `prepare_cli_session` `_write_claude_settings` 호출 try/except 항목 추가. degraded reason을 state에 기록 후 진행하는 동작 명시.

#### 9. [ACCEPT] [Medium] `executor.shutdown(wait=False, cancel_futures=True)`은 Stage 2에서 no-op + 비-daemon 스레드 종료 지연
- **Critic**: max_workers=2 + 2 futures 즉시 시작이라 `cancel_futures`는 no-op. 비-daemon worker thread가 subprocess timeout(≈395s)까지 살아 Python 프로세스 exit 지연
- **Cross**: not flagged
- **Judgment**: critic이 CPython 동작 정확히 인용. §7 "wall-clock = max(spec, design)" 사용자 약속과 모순.
- **Action Required**: 다음 중 1택 — (a) `wait=True` + 짧은 추가 timeout, (b) daemon thread custom executor, (c) "CLI 종료가 per-future timeout까지 지연될 수 있음" 명시. `cancel_futures=True` 표현은 "Stage 2 무용·미래 확장 대비"로 주석.

#### 10. [ACCEPT] [Medium] 텔레메트리 경로 (target_path 기반 docs vs workspace 기반 telemetry) 불일치
- **Critic**: docs는 `target_path`, telemetry는 `workspace` — 외부 프로젝트 실행 시 분산
- **Cross**: not flagged (다른 문제로 #5 제기)
- **Judgment**: critic의 사용성 지적 타당. 단 #5와 합쳐 한 번에 수정 가능.
- **Action Required**: 명시적 결정 — A안(telemetry도 doc_root 기반) vs B안(workspace 고정 + AF 내부 관측 명시). §11 Step 2 assertion에도 반영.

#### 11. [ACCEPT] [Medium] Stage 1 budget 90s가 refine 발생 시 부족
- **Critic**: 실측 N=1, refine 0회 기반. `_PLACEHOLDER_REFINE_MAX=2` 시 95~120s 도달 가능
- **Cross**: HOLD로 별도 제기 (`TOTAL_BUDGET=600` 일반화 가능성) — 사실상 동일 우려의 다른 측면
- **Judgment**: critic의 정량 지적 타당. cross의 HOLD도 같은 데이터 부족을 가리킴.
- **Action Required**: Stage 1을 120-150s로 상향, 또는 refine 발생률을 N≥3 measurement에서 먼저 산정. §6 budget 표 갱신.

#### 12. [ACCEPT] [Medium] R1의 NFS/SMB 안전성 주장 부정확
- **Critic**: NFSv2/v3는 `O_EXCL` atomic 보장 X, NFSv4도 delegation 필요. POSIX-2008만 인용은 부정확
- **Cross**: not flagged
- **Judgment**: critic 사실 정확. Multi-PC 시나리오는 CLAUDE.md에 명시되어 있어 무관 위험 아님.
- **Action Required**: §15 R1을 정정 — (a) "로컬 FS 한정. NFS/SMB 미지원" 명시, 또는 (b) `core/file_lock.py`를 `link(2)` 기반 atomic primitive로 교체.

#### 13. [REJECT] [Low] `_call_*_api` 시그니처 확장이 기존 호출자를 깨뜨릴 우려
- **Source**: Cross #7 (자체 REJECT)
- **Original Finding**: `return_usage=False` default 유지 시 호환
- **Rejection Reason**: cross가 자체 검증 후 REJECT. critic도 별도로 wrapping 호출자 유지를 허용.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | cleanup import 경로 오류 | Critical | ACCEPT | Both |
| 2 | settings run_id last-writer-wins race | Critical | ACCEPT | Critic |
| 3 | expected_count=11 vs 실제 12 | High | ACCEPT | Both |
| 4 | _refine_document 경로 단절 | High | ACCEPT | Cross |
| 5 | telemetry slug-only 덮어쓰기 | High | ACCEPT | Cross |
| 6 | timeout=5 vs stale 10s 충돌 | High | ACCEPT | Cross |
| 7 | usage 추출 shape/스니펫 미명세 | High | ACCEPT | Critic |
| 8 | TimeoutError 미처리 (prepare_cli_session) | Medium | ACCEPT | Cross |
| 9 | cancel_futures no-op + thread 지연 | Medium | ACCEPT | Critic |
| 10 | telemetry 경로 (target vs workspace) | Medium | ACCEPT | Critic |
| 11 | Stage 1 budget 90s 부족 | Medium | ACCEPT | Critic+Cross |
| 12 | NFS/SMB 안전성 주장 부정확 | Medium | ACCEPT | Critic |
| 13 | `_call_*_api` 호환성 우려 | Low | REJECT | Cross self |

---

### Recommendations

구현 전 v3 작성 — 다음 항목을 동일 PR에서 처리:

1. **Critical 2건 우선** — §9 import 정정 (1줄), §4에 호출별 settings 파일 또는 광폭 락 결정.
2. **호출 체인 무결성** — §3 다이어그램에 `_refine_document` 포함시키고 timeout/run_id/workspace 전파 명시 (#4).
3. **텔레메트리 키 일원화** — `{slug}_{run_id}.json` 또는 JSONL append으로 변경, §5/§11/§14 동시 갱신 (#5, #10).
4. **Lock 정책 일관성** — `timeout`/stale 임계 같은 상수에 묶기 (#6). NFS/SMB 지원 범위 명시 (#12). `prepare_cli_session` try/except 변경 항목 추가 (#8).
5. **§10 usage 명세 보강** — dict shape 고정 + 3-provider 추출 스니펫 (#7).
6. **Budget·executor 정합** — Stage 1을 120s 이상, `cancel_futures=True` 주석 정정, thread 지연 동작 명시 (#9, #11).
7. **§14 Step 0에 추가 assertion** — (a) 각 subprocess hook event가 자기 run_id로 도착, (b) `_safe_slug(spec_run_id) != _safe_slug(design_run_id)` (critic missing 항목).

v3 작성 후 다시 cross-review 1회만 발화. critic 재실행 불필요 (v2 BLOCK 근거 명확).