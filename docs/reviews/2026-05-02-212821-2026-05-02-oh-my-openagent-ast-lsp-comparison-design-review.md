# Design Review: 2026-05-02-oh-my-openagent-ast-lsp-comparison

> Source: docs/참고/2026-05-02-oh-my-openagent-ast-lsp-comparison.md
> Date: 2026-05-02 21:28
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

분석 전용 문서로서는 채택 가능하나, §5.4 측정값 4건의 데이터 소스/추출 명령 불명·내적 모순(Q-D vs Q-B, Q-F silent failure)이 남아 있어 "재현 가능한 분석"이라는 본 문서의 핵심 가치가 손상됐다. BLOCK 수준의 Critical은 없으므로 정정 후 게시 가능.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [High] §5.4 Q-F "데이터 수집 미발생" 진단 부정확 — silent failure 또는 hook 미배선

- **Critic #3**: 52번 시도(`append_metric`이 `try/except: pass`로 감싸짐) 중 0건 성공이면 "거의 발생 안 함"이 아니라 "100% silent 실패"
- **Cross #4**: `append_metric()`은 `_post_agent_record` 안에서만 호출되는데, `.claude/settings.local.json:188-208`은 `post_edit_code_review`/`post_edit_design_review`만 배선 → metrics 미작성의 직접 원인은 hook wiring 누락
- **Judgment**: 두 리뷰어가 같은 결론(measurement misdiagnosis)에 다른 각도에서 도달. Cross가 더 구체적 원인 제시.
- **Action Required**: §5.4 Q-F를 "52건 시도 / 0건 성공 — 원인 후보 (a) `post_agent_record` hook 미배선 (b) `_queue_dir` 쓰기 단계 silent 실패. settings.local.json:188-208에 직접 등록 부재 확인됨"으로 정정.

#### 2. [ACCEPT] [High] §5.4 Q-D vs Q-B 내적 모순 — af-test-runner 14건 vs test_gap_analyzer 0건

- **Critic #1**: `scripts/hook_runner.py:347-348`이 `af-test-runner` post_agent_record마다 `_apply_test_gap_verdict`를 무조건 호출하고, 모든 분기가 `_log_hook_event("test_gap_analyzer", ...)`를 발화 → 14건이면 hook log에 14건 이상 있어야 함. 0건은 (a) Q-D 데이터 소스가 hook log 아님 (b) 코드 경로 추측 오류 둘 중 하나
- **Cross**: not flagged
- **Judgment**: Critic의 코드 경로 추적이 정확하고 검증 가능. 이 모순은 측정 신뢰도 자체를 흔든다.
- **Action Required**: hook_events.log 기준 `post_agent_record|af-test-runner` 직접 카운트해서 14/51과 정합성 확인. 정합되지 않으면 Q-D 데이터 소스(예: `docs/reviews/*.md` 메타데이터, `.af_review_queue/cr_thread.json`)를 §5.4 Q-D 캡션에 명시.

#### 3. [ACCEPT] [High] §5.4 Q-C "fake vs 실 사용 비율 미분리" — 즉시 측정 가능

- **Critic #2**: 단일 grep으로 답 나옴. `core/foo.py`(테스트 fixture) = 316/552 = 57.2%, 실 사용 추정 234건. "측정 못함"으로 후속작업 후보로 미루는 것은 분석 문서 가치 훼손
- **Cross**: not flagged
- **Judgment**: Critic이 실제 grep 결과까지 제시. 명백히 채택.
- **Action Required**: §5.4 Q-C에 "core/foo.py(fixture) 316 / 그 외 236" 행 추가. §7.2/§8.1에서 해당 항목 제거.

#### 4. [ACCEPT] [High] §5.2 risk_id 7종 — AST/grep engine drift 미명시

- **Critic #4**: `core/review_bundle.py:36-44` (grep) = 7개, `:66-73` (AST) = 6개. AST에서 dynamic_import 누락. Q-A 유일 인용 risk_id가 dynamic_import이므로 production engine에 따라 인용률이 0/46이 될 가능성
- **Cross**: not flagged
- **Judgment**: 코드 라인 인용 명확. 결론(인용률 ~2%)에 직접 영향.
- **Action Required**: §5.2에 "engine=ast → 6종 / engine=grep → 7종 (dynamic_import 차이)" 명시. Q-A 표 캡션에 production engine 명시.

#### 5. [ACCEPT] [Medium] AST replace tool 노출 시 safety contract 누락

- **Critic**: not flagged
- **Cross #1**: `core/ast_engine.py:165-194` `replace_file()`은 `dry_run=False` 기본값, `open(..., "w")`, workspace/path 가드 없음. oh-my-openagent의 "Dry-run by default" 대비 안전성 격차
- **Judgment**: 본 문서가 "분석 전용"이지만 §7.3에서 "AST AI tool 노출 안 함"을 gap으로 제기하므로, 노출 시 safety contract가 어떻게 다른지 §3.2/§7.3에 caveat이 필요. Cross 코드 라인 인용 강함.
- **Action Required**: §7.3 또는 §8.4(후속 후보)에 "AST AI tool 노출 시 dry-run 기본값/path 가드/regex 거부 등 oh-my-openagent의 safety contract와 `core/ast_engine.py:165-194`의 현 동작 차이 분석 선행 필요" 한 줄 추가.

#### 6. [ACCEPT] [Medium] §5.4 Q-A "메타 review" 분류 기준·재현 명령 부재 (재현 가능성 일반 이슈)

- **Critic #7, #10, "Missing from Design"**: Q-D 데이터 소스 불명, Q-A 분류 휴리스틱 미명시, Q-A~Q-F 추출 명령(grep/awk/jq) 미수록
- **Cross**: not flagged
- **Judgment**: 분석 전용 문서의 핵심 가치는 재현 가능성. 추출 명령 누락은 시간이 지날수록 검증 불가능.
- **Action Required**: §9.3에 Q-A~Q-F 추출 명령 표 추가 (또는 부속서). Q-A 7건 파일명 각주로 나열.

#### 7. [ACCEPT] [Medium] Bundle 효과 측정 framing — risk_id 인용률 ≠ bundle 유용성

- **Critic**: not flagged
- **Cross #3**: `.claude/agents/af-critic.md:41-54`는 bundle을 읽으라고 하지만 risk_id 인용을 강제하지 않음. 리뷰어가 bundle을 읽고 파일 직접 검사 후 risk_id 미인용 finding을 낼 수 있음. `scripts/review_metrics_logger.py:144-168`은 bundle hit 정보 미수집
- **Judgment**: Cross의 코드 라인 인용 명확. §7.1 "raw risk_id 형식은 subagent reasoning에 거의 인용되지 않는다" 결론이 측정 framing에 따라 달라짐.
- **Action Required**: §7.1을 "**risk_id 인용률** 1/46 (≠ bundle 전체 유용성). bundle 읽기/file overlap 메트릭은 현재 미수집"으로 재구성.

#### 8. [ACCEPT] [Medium] §4 SST OpenCode 비교 baseline에 미해결 모순 inherit — caveat 누락

- **Critic #5**: §4 비교표 (LSP 9개 vs 6개)가 `docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md` §5의 미해결 모순을 inherit하지만 §4 본문 caveat 빠짐
- **Cross**: not flagged
- **Judgment**: 본 문서 §9.2가 caveat을 인지하지만 §4 표 자체에는 노출 안 됨. Critic의 지적 정확.
- **Action Required**: §4 표 캡션에 "SST OpenCode 열은 별도 분석 문서 §5의 미해결 모순에 의존 — 9개/push 동작은 재확인 필요" 추가.

#### 9. [ACCEPT] [Medium] §2.3/§3.3 push 모드 부재 결론 — fetch 범위 좁음 명시 필요

- **Critic #6**: §9.1 fetch 대상에 oh-my-openagent의 `src/tools/edit/` 또는 `src/tools/replace/` 미포함 채로 "push 부재" 시사. fetch 미수행 사실을 §9.1 또는 §2.3에 명시 필요
- **Cross**: not flagged
- **Judgment**: 결론이 보호적으로 작성됐지만 fetch 범위가 §9.1에서 LSP/AST-Grep 폴더로만 한정된 점이 §2.3의 추론 약점.
- **Action Required**: §9.1 끝에 "src/tools/lsp/, src/tools/ast-grep/만 fetch — edit/replace 폴더 미확인. push 부재는 잠정." 한 줄.

#### 10. [ACCEPT] [Medium] §7.3 gap framing — 패러다임 차이 caveat 누락

- **Critic #8**: §7.3 "없음/안 함/휴면" 부정형 3연속이 §1, §8 "권고 아님" 선언과 framing 충돌. AF (Python 런처+Claude Code subagent) vs oh-my-openagent (TS/Bun harness+1급 AI tool) 패러다임 차이를 §7.3에 노출 안 하면 후속 plan 작성자 오해 가능
- **Cross #2 (관련)**: AF 통합 면(integration surface) 미정 — CLI command/Claude skill/AgentRunner tool/reviewer prompt 중 어디 위치할지 결정 포인트 추가 필요. `core/providers/session_adapter.py:220-236`은 `cli_hook_bridge`만 설치, reviewer agent tools는 prompt-level
- **Judgment**: 두 리뷰어가 같은 framing 약점을 다른 각도에서 지적. 패러다임 caveat + 통합 surface 결정 포인트 모두 필요.
- **Action Required**: §7.3 첫 줄에 "동일 use case 전제 하 gap이며 AF는 다른 패러다임(subagent task 기반)을 채택했음을 전제로 해석할 것" 추가. §8에 "AST/LSP AI tool 노출 surface (CLI/Claude skill/AgentRunner tool/reviewer prompt) 결정 포인트" 항목 추가.

#### 11. [ACCEPT] [Low] §5.3 post_edit_enqueue 트리거 경로 미추적

- **Critic #9**: 552건이 어디서 발생하는지 추적 미완. `post_edit_code_review`(settings.local.json:194)가 내부적으로 `post_edit_enqueue`를 호출하는지 한 번만 확인하면 그림 닫힘
- **Cross**: not flagged
- **Judgment**: 트리거 경로 미추적은 552건 해석 자체를 막음. 단일 grep으로 검증 가능.
- **Action Required**: §5.3에 "post_edit_code_review 함수가 _post_edit_enqueue를 내부 호출하는지 확인" 추가하고 가능하면 검증.

#### 12. [REJECT] [Low] 본 문서가 deployment 변경을 명시해야 함

- **Source**: Cross #5 (자체 REJECT)
- **Original Finding**: AST/LSP 작업이 `requirements.txt`, `af.spec`, hook config, 문서 업데이트를 요구할 수 있음
- **Rejection Reason**: Cross 본인이 자체 reject. 본 문서는 분석 전용. 또한 `requirements.txt:12`에 `ast-grep-py` 이미 존재, `af.spec:38-40,268`에 `core.ast_engine`/`core.review_bundle`/`ast_grep_py` hidden import 등록됨. Deployment 세부는 후속 plan 영역.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Q-F silent failure / wiring 미진단 | High | ACCEPT | Both |
| 2 | Q-D vs Q-B 내적 모순 | High | ACCEPT | Critic |
| 3 | Q-C fake/실 사용 분리 가능 | High | ACCEPT | Critic |
| 4 | risk_id AST/grep engine drift | High | ACCEPT | Critic |
| 5 | AST replace safety contract | Medium | ACCEPT | Cross |
| 6 | Q-A~Q-F 추출 명령·분류 기준 | Medium | ACCEPT | Critic |
| 7 | Bundle 효과 framing | Medium | ACCEPT | Cross |
| 8 | §4 SST baseline caveat | Medium | ACCEPT | Critic |
| 9 | push 모드 부재 fetch 범위 | Medium | ACCEPT | Critic |
| 10 | §7.3 패러다임 framing + 통합 surface | Medium | ACCEPT | Both |
| 11 | post_edit_enqueue 트리거 경로 | Low | ACCEPT | Critic |
| 12 | Deployment 변경 명시 | Low | REJECT | Cross (self) |

### Recommendations

구현 전 (=후속 plan 작성 전) 본 분석 문서에 적용:

1. **즉시 검증 가능한 모순 해결** (Findings #1, #2, #3, #11): hook_events.log 기준 `post_agent_record|af-test-runner`·`core/foo.py 비중`·`post_edit_code_review→_post_edit_enqueue 호출 여부` 3건을 grep으로 직접 측정해서 §5.3, §5.4 Q-C/Q-D/Q-F 정정.
2. **재현 가능성 보강** (Finding #6): §9.3에 Q-A~Q-F 추출 명령(grep/awk/jq) 표 추가. Q-A 7건 파일명 각주.
3. **engine drift 노출** (Finding #4): §5.2에 ast/grep risk_id 차이 명시, Q-A 표에 production engine 메타데이터.
4. **fetch 범위·baseline caveat 명시** (Findings #8, #9): §4·§9.1에 SST baseline 미해결 모순과 oh-my-openagent edit/replace 폴더 미fetch 사실 추가.
5. **framing 정정** (Findings #7, #10): §7.1 "risk_id 인용률 ≠ bundle 유용성", §7.3 패러다임 차이 caveat, §8에 통합 surface 결정 포인트 추가.
6. **AST 노출 safety contract** (Finding #5): §7.3 또는 §8 후속 후보에 `core/ast_engine.py:165-194`의 현 동작과 oh-my-openagent safety contract 격차 분석 선행 항목 추가.

위 1~6번 정정 후 본 분석 문서는 후속 plan의 baseline으로 사용 가능. 정정 없이 plan 작성 시 NEXT_STEPS의 "분석 baseline은 실제 코드/출력이어야 한다" 메모리 규칙 위반 위험.