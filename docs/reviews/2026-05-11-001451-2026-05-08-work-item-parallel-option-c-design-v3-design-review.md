# Design Review: 2026-05-08-work-item-parallel-option-c-design-v3

> Source: docs/2026-05-08-work-item-parallel-option-c-design-v3.md
> Date: 2026-05-11 00:14
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

2건의 Critical finding(F1·F2 흡수 표기 vs 실제 코드 불일치)이 있고, "draft 설계"가 baseline 코드와 어긋나 있어 그대로 cross-review에 진입하면 흡수 표만 보고 PASS가 날 위험이 있다. v3가 §0a에서 "흡수(High)"로 표기한 항목 일부가 본문·코드 어디에도 구현되어 있지 않다.

> **주의**: Cross Review가 provider error로 실제 검토를 수행하지 못했음 (Codex CLI 시작 후 입력 단계에서 절단). 따라서 이 집계는 **Critic 단독 의견**을 근거로 한다. 모든 finding은 "Cross: not flagged" 상태이며, 각 항목의 근거는 Critic이 제시한 grep/line 인용을 1차 채택했다. Critic 평가의 evidence가 file:line 단위로 구체적이라 "Only one reviewer flags it, evidence is strong → ACCEPT" (Rule 2) 적용.

### Aggregated Findings (11 total)

#### 1. [ACCEPT] [Critical] F1 (refine loop per-iteration timeout) "흡수" 표기와 실제 코드 불일치
- **Critic**: §0a F1이 `iter_timeout = max(1, deadline - time.monotonic() - 5)` 산식·"잔여 ≤0 skip"·"Stage 3 진입 전 5s grace wait"를 명시하지만 `core/work_item_generator.py:1184-1260` `_generate_and_refine`/`_refine_document`에 `deadline`/`iter_timeout`/grace wait가 전혀 없음. `_refine_document(L1263)`은 `timeout` 파라미터 자체가 없다.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. file:line 근거 명확. v3 budget 정당성("507s가 400s 초과해도 F1 guard로 누계 보호")이 무효화돼 §6 산술이 닫히지 않음 (finding #9와 직결).
- **Action Required**: ① F1을 "구현 예정"으로 status 다운그레이드하거나, ② 본 PR에서 `_generate_and_refine`이 stage `deadline`을 인자로 받아 매 iteration 잔여 계산·`_refine_document(timeout=...)` 전달·≤0 skip+warn하도록 코드 추가. 둘 중 하나 선택 필수.

#### 2. [ACCEPT] [Critical] F2 (`_call_*_api` transport timeout) "흡수" 표기와 실제 시그니처 불일치
- **Critic**: §0a F2가 `_call_*_api(timeout_sec: int = 120)` 시그니처를 명시하지만 `core/requirement_llm.py:78,98,118` 세 함수 모두 `(model, prompt, *, return_usage)`만 받음. `_call_anthropic_api`는 `httpx.Client`가 아니라 `urllib.request.urlopen(request, timeout=60)`(L139) 하드코딩.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. L3 LLM 호출 timeout이 API 경로에서 작동하지 않음. evidence가 line 단위로 구체적.
- **Action Required**: F2를 본 PR에서 실제 plumbing(세 함수 시그니처에 `timeout_sec` 추가 + 각 SDK 별 timeout 전달)하거나, §0a F2 status를 `provisional`로 강등 + §15 R2 위험 격상.

#### 3. [ACCEPT] [High] "신규" 표기된 두 모듈이 이미 repo에 존재 — 설계 vs 코드 baseline 불일치
- **Critic**: §11에서 `core/cli_session_cleanup.py`·`core/work_item_telemetry.py`를 "(신규)"로 표기했지만 두 파일 모두 2026-05-10 시점 이미 작성됨. `_exec_stage2`/`_resolve_future_or_fallback`도 line 835/860에 이미 구현.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. 메모리 [feedback_analysis_doc_baseline_must_be_real_code] 패턴 위반. "draft 설계"가 아니라 "이미 머지된 코드의 사후 문서"가 되어 cross-review 해석이 달라짐.
- **Action Required**: §0/§11에 "Implementation Status" 컬럼 추가 — (a) 이미 구현, (b) 본 PR에서 수정, (c) 미구현 신규 3분류로 표기.

#### 4. [ACCEPT] [High] §11 path map 라인 번호 시스템적 오류
- **Critic**: 핵심 함수 라인 인용 다수 오류 — `_generate_doc_with_llm` 실제 562/문서 523-534, 4 generator 실제 613/656/698/755/문서 537-694, `generate_work_items` 실제 1025/문서 740-831, `_generate_and_refine` 실제 1184/문서 834-870, `execute_document_prompt` 실제 203/문서 173-230. §0a F11도 `af.spec:76`(실제 76은 `core.provider_detect`, `core.work_item_telemetry`는 line 83)으로 오기.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. implementer/리뷰어가 잘못된 위치를 보면 "spec과 다르게 구현됐다" 오해 발생. grep 1차 반증으로 즉시 검증 가능한 단순 오류.
- **Action Required**: §11 표를 grep 결과로 일괄 갱신, 2026-05-10 baseline 라벨링. F11의 line 76 → 83 정정.

#### 5. [ACCEPT] [High] §0a F9 vs §8 코드블록 vs 실제 코드 — `expected_count` 3중 불일치
- **Critic**: §0a F9는 12, §8 본문 코드 예시는 11, 실제 코드(`core/work_item_generator.py:813`)는 12. 또한 F9는 "불일치 시 빈 문자열 반환"이라 명시했지만 실제(L828-832)는 `_LOGGER.warning` 후 `"\n".join(lines)`로 부분 outline 반환.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. 같은 문서 내 표·코드·실제 동작 3자가 모두 다름. evidence 명확.
- **Action Required**: §8 코드 블록을 12로 수정. F9의 "빈 문자열 반환" 결정을 실제 구현에 반영하거나, 결정을 "warning만"으로 변경. §0a–§8–코드 3자 일치 강제.

#### 6. [ACCEPT] [High] §0a F7 path vs §11 update_t1 코드 path 충돌
- **Critic**: §0a F7은 `workspace_runtime_dir(workspace)/"work_item_telemetry"`(=`<workspace>/.af_runtime/...`) 표준 명시. §11 코드(L827)와 실제 `core/work_item_telemetry.py:14`는 `Path(workspace)/"runtime"/"work_item_telemetry"` 사용. cleanup(§9)은 `.af_runtime/cli_sessions/`, 텔레메트리는 `runtime/work_item_telemetry/`로 분리된 트리 발생.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. 운영자가 두 트리를 모두 알아야 하는 컨벤션 분기.
- **Action Required**: `workspace_runtime_dir(workspace)/"work_item_telemetry"`로 통일하고 `core/work_item_telemetry.py:14,45` 동시 수정.

#### 7. [ACCEPT] [High] §0a F4 (§7a/§7b 신설) 미실행 — Stage 1/3 풀 구현 본문 부재
- **Critic**: §0a F4가 약속한 §7a/§7b 섹션이 본문에 결락. §6 budget 코드는 `_exec_stage1`/`_exec_stage3`를 호출하지만 정의 없음. 코드에서도 `_exec_stage1`/`_exec_stage3`는 grep 미존재(line 860 `_exec_stage2`만 존재). F3·F4·F8·F12가 §7a/§7b를 전제로 묶여 있는데 결락이라 흡수 효과 0.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. budget 흐름이 코드 레벨로 닫혀 있지 않음.
- **Action Required**: §7a/§7b 본문 실제 추가 + 코드에도 `_exec_stage1`/`_exec_stage3` 정의 추가(본 PR 범위에 포함).

#### 8. [ACCEPT] [Medium] §6 budget 산정과 F8 "여전히 유효" 주장 — 산술 모순 잠재
- **Critic**: STAGE_BUDGET[2]=400.0, 352s 대비 마진 48s. F8이 worst-case 507s를 인정하면서 budget 400s는 F1 guard 동작 전제. F1이 #1처럼 미구현이면 §6 산술 미달.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. finding #1과 직접 연결.
- **Action Required**: ① F1 실 구현, ② STAGE_BUDGET[2]=520s + TOTAL_BUDGET=720s 상향, ③ refine 횟수를 design 한정 1회 제한 — 셋 중 하나 명시.

#### 9. [ACCEPT] [Medium] §7 abandoned future subprocess가 Stage 3와 race 가능
- **Critic**: `cf.wait` timeout 후 `not_done` future들의 subprocess는 SIGTERM까지 grace 5s 내 작동 가능. Stage 3가 시작되면 같은 `<workspace>/.af_runtime/cli_sessions/` + `_events.jsonl` 동시 기록. lock(§4)은 `_write_claude_settings` 본문만 보호 — hooks 호출 시점은 미보호. §15에 R로 미등록.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. F1의 "Stage 3 진입 전 5s grace wait"가 이 시나리오와 정합. 코드 합쳐야 함.
- **Action Required**: §15에 "R7: stage2 abandoned future subprocess와 stage3 hook 충돌" 추가. Stage 3 진입 전 `time.sleep(grace)` 또는 `not_done`에 `wait_for(timeout=grace)` 명시.

#### 10. [ACCEPT] [Medium] §9 cleanup 디렉토리 mtime 의미 미정의
- **Critic**: POSIX dir mtime은 자식 add/remove에만 갱신 (file modify 무관). 30일 동안 append만 되는 shell_guard 디렉토리는 dir mtime이 stale → rmtree로 활성 세션 파괴 가능. 반대로 자식 자주 추가되면 dir mtime 갱신 → 영원히 정리 안 됨.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. POSIX 동작 근거 명확.
- **Action Required**: 디렉토리는 자식 max(mtime) 기반 판정(`max((c.stat().st_mtime for c in entry.rglob("*")), default=...)`)으로 변경하거나 디렉토리 cleanup TTL 60일+로 분리.

#### 11. [HOLD] [Medium] Cross Review 미실행 (provider error)
- **Critic**: N/A
- **Cross**: provider error로 실제 검토 미수행 (CLI 시작 출력만 있음)
- **Judgment**: HOLD. 본 final review는 Critic 단독 근거. 정책상 "BLOCK 판정 시에만 발견 사항 수정"(CLAUDE.md)을 충족하기 위해 Critical/High는 ACCEPT 처리했지만, cross의 독립 perspective가 제공할 수 있는 추가 finding(특히 §15 위험 등록 적정성, §14 acceptance 기준 등)은 검증되지 못함.
- **Action Required**: 위 #1~#10 흡수 후 cross-review 재실행. 가능한 외부 provider(codex/copilot/gemini-cli) 인증 상태 확인 후 재시도.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | F1 refine loop per-iteration timeout 미구현 | Critical | ACCEPT | Critic |
| 2 | F2 `_call_*_api` transport timeout 미연결 | Critical | ACCEPT | Critic |
| 3 | "신규" 모듈이 이미 repo에 존재 (baseline 불일치) | High | ACCEPT | Critic |
| 4 | §11 path map 라인 번호 시스템적 오류 | High | ACCEPT | Critic |
| 5 | `expected_count` §0a/§8/실제 코드 3중 불일치 | High | ACCEPT | Critic |
| 6 | §0a F7 path vs 실제 코드 path 충돌 | High | ACCEPT | Critic |
| 7 | §7a/§7b 결락 + `_exec_stage1`/`_exec_stage3` 미정의 | High | ACCEPT | Critic |
| 8 | §6 budget 산술이 F1 guard에 의존 | Medium | ACCEPT | Critic |
| 9 | abandoned future subprocess와 Stage 3 race | Medium | ACCEPT | Critic |
| 10 | §9 cleanup 디렉토리 mtime 의미 미정의 | Medium | ACCEPT | Critic |
| 11 | Cross review 미실행 (provider error) | Medium | HOLD | — |

### Recommendations

구현 진입 전 다음 순서로 처리:

1. **baseline 정합부터** (#3, #4) — `core/cli_session_cleanup.py`/`core/work_item_telemetry.py` 실제 코드 vs 문서 §11 표를 grep으로 일괄 갱신, "Implementation Status" 컬럼 추가. 이게 안 되면 다른 finding의 근거 인용 자체가 흔들림.
2. **F1·F2 결정 확정** (#1, #2) — "구현 예정"으로 다운그레이드 vs 본 PR에서 실 코드 plumbing 중 택일. F1 결정이 #8(§6 budget 산술)에 직결.
3. **문서 내 자체 모순 해소** (#5, #6, #7) — `expected_count`·텔레메트리 path·§7a/§7b 본문 보충. 같은 문서의 §0a–§본문–코드가 한 방향으로 정렬되어야 cross-review에서 "흡수했다" 표가 의미를 가짐.
4. **race/cleanup 안전성** (#9, #10) — §15 R7 신설 + §9 디렉토리 mtime 정책 변경.
5. **Cross-review 재실행** (#11) — 위 1~4 반영 후 외부 provider로 재검증. 이번처럼 단일 critic 의견에만 의존하면 design 품질 보증이 미흡.

상기 항목 모두 처리되기 전에는 v3를 "draft (3라운드 대기)"가 아닌 **draft (1라운드 BLOCK)**로 표기 정정 권고.