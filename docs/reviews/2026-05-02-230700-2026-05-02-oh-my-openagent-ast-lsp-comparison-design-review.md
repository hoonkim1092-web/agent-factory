# Design Review: 2026-05-02-oh-my-openagent-ast-lsp-comparison

> Source: docs/참고/2026-05-02-oh-my-openagent-ast-lsp-comparison.md
> Date: 2026-05-02 23:07
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

여러 High 발견사항(샘플 편향, 자가 모순, 재현성, 측정 범위 누락)이 분석문서의 baseline 역할을 약화시키지만, BLOCK 수준의 critical defect는 없다. 두 리뷰어 모두 정정 후 채택 가능하다고 판정.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [High] Q-D "98% PASS"는 review-recorded 표본만 본 PASS-편향 카운트
- **Critic**: hook_events.log의 `review-recorded` 52건만 셈했고, 실측 `docs/reviews/*.md` Verdict 헤더는 BLOCK 16+ / WARN 24 존재 — post_agent_record가 모든 review path에서 발화 안 함.
- **Cross**: 직접 다루지 않음 (Cross #1·#2가 동일한 "hook_events.log는 canonical sink가 아님" 패턴을 다른 Q에서 지적).
- **Judgment**: Critic 단독 발견이지만 실측 grep 명령과 결과 수치(BLOCK 12 + **BLOCK** 4 + WARN 24)가 강한 evidence. Cross #1·#2의 측정 범위 누락 패턴과도 정합.
- **Action Required**: Q-D에 "이 수치는 hook_events.log review-recorded 라인만 카운트, docs/reviews/ 헤더 verdict 분포와 별도 sink"라는 caveat 추가. §6 비교 매트릭스 row 4에서 "98%" 직접 인용 제거.

#### 2. [ACCEPT] [High] Q-A 표 vs §148 본문 자가 모순 — dynamic_import "1건"의 정체
- **Critic**: 표는 "dynamic_import | 1"로 표기하지만 본문은 "일반 코드 리뷰의 evidence 인용 0건". 그 1건은 `2026-05-01-113842-review_bundle-code-review.md`로 review_bundle.py 자체에 대한 메타 리뷰.
- **Cross**: 직접 다루지 않음.
- **Judgment**: Critic이 file 식별 + grep 명령 제시. 자가 모순은 분석문서 자기선언("재현 가능")과 어긋남.
- **Action Required**: 표 셀을 `1 (메타: review_bundle.py 자체 리뷰)`로 바꾸거나 표 위에 "메타 리뷰 제외 시 모두 0" 주석.

#### 3. [ACCEPT] [High] 재현성 결함 — 추출 명령 + commit SHA 부재
- **Critic** (#3): §9에 Q-A~Q-F의 grep/jq 추출 명령이 없어 다음 세션이 같은 수치 재현 불가. "재현 가능한 분석" 자기선언과 모순.
- **Cross** (#5): §9.1 외부 비교가 oh-my-openagent `dev` branch URL이라 같은 fetch가 다른 코드 반환 가능. commit SHA pin 필요.
- **Judgment**: 두 리뷰어가 다른 측면에서 동일한 재현성 약점을 지적. 분석문서가 baseline으로 쓰이려면 둘 다 필수.
- **Action Required**: §9.4 "추출 명령" 신설(Q-A~Q-F 각 1줄), §9.1에 fetch 시점 commit SHA 추가.

#### 4. [ACCEPT] [High] hook_events.log 외부 호출 경로 누락 (Q-B, Q-E)
- **Critic**: Q-F에서 silent failure 후보 미점검 (Finding 4) — 동일 패턴이 Q-E·Q-B로 확장됨.
- **Cross** (#1, #2): Q-E는 `LSPCheckHook`이 `print()`만 하고 `_log_hook_event`를 호출하지 않으므로 hook_events.log 0건은 "관측 불가" 의미. Q-B는 af-test-runner subagent가 직접 `python scripts/test_gap_analyzer.py`를 실행하는 manual 경로(`.claude/agents/af-test-runner.md:41`)가 hook log에 안 남음.
- **Judgment**: Cross가 file:line 근거(`core/hooks/lsp_check.py:205`, `scripts/hook_runner.py:144·347`) 강력 제시. Critic Finding 4의 silent failure 패턴과 같은 진단 결함.
- **Action Required**: Q-B 제목을 "hook-enforced test_gap_analyzer 호출"로 좁히고 manual subagent 경로 별도 표기. Q-E에 "hook_events.log sink 한정, 실제 측정은 chat_trace.json/stdout/신규 lsp_check event 중 명시 필요" 추가.

#### 5. [ACCEPT] [Medium] Q-F silent failure 후보 미점검
- **Critic**: 파일 부재의 원인 후보 중 `record_review` 호출 경로 미배선 / workspace mismatch 가능성 미분류.
- **Cross**: 직접 다루지 않음 (Cross #1·#2와 같은 측정 범위 패턴).
- **Judgment**: Q-E가 "원인 후보(실측)" 두 가지 제시한 일관성 기준에 Q-F만 미달.
- **Action Required**: Q-F에 "원인 후보: (a) record_review 호출 경로 미배선, (b) workspace mismatch. 분리는 §7.2와 동일 spike" 1줄 추가.

#### 6. [ACCEPT] [Medium] review_bundle line number contract — engine별 1-based vs 0-based
- **Source**: Cross only (#3)
- **Cross**: grep fallback은 `+1` (1-based), AST는 `rng.start.line` 그대로 (실측 두 번째 줄이 `line: 1`로 출력됨). `core/review_bundle.py:55` vs `core/ast_engine.py:91`.
- **Judgment**: Cross가 file:line 근거와 실행 결과 모두 제시. schema 계약 결함은 후속 plan에 직접 영향.
- **Action Required**: §5.2 schema 인용에 line 인덱스 기준 명시 + `ast_engine.search()` 반환 1-based 정규화 (또는 `review_bundle.save()` 직전 변환). `tests/test_review_bundle.py`에 동일 line 계약 테스트 추가.

#### 7. [ACCEPT] [Medium] Bundle `{file_path}` 절대/상대 경로 미명시
- **Source**: Cross only (#4)
- **Cross**: `scripts/build_review_bundle.py:47`이 절대경로 resolve 후 그대로 출력. reviewer prompt(`.claude/agents/af-critic.md:33`)와 queue state는 workspace-relative 전제.
- **Judgment**: 계약 모호성은 reviewer prompt와의 path 비교에 silent bug 유발 가능. file:line 근거 강함.
- **Action Required**: §5.2에 현재 절대경로 출력 사실 명시 + bundle schema는 workspace-relative로 고정 (필요 시 `abs_path` sidecar). 

#### 8. [ACCEPT] [Medium] §6 row 2 "확인됨"이 별도 미해결 문서에 의존
- **Source**: Critic only (#5)
- **Critic**: SST OpenCode "Diagnostics push 확인됨"은 `docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md`(잔존 모순 NEXT_STEPS 인계 상태)에 의존. 권원 표시 없으면 본 문서 신뢰도가 미해결 문서에 종속.
- **Cross**: 직접 다루지 않음.
- **Judgment**: 출처 위임이 명확하지 않으면 baseline으로 사용 시 동형 BLOCK 반복 위험.
- **Action Required**: 해당 셀에 "(opencode-lsp 분석 문서 §X.X 기준; 잔존 모순은 별도 인계)" 권원 표시.

#### 9. [ACCEPT] [Medium] §8 #5 "1주 메트릭 후 결정"이 "권고 아님" 자기선언과 충돌
- **Source**: Critic only (#6)
- **Critic**: 후보 목록과 의사결정 시퀀싱 권고 사이의 경계 흐림.
- **Cross**: 직접 다루지 않음.
- **Judgment**: 분석/plan 분리 자기선언을 §8 본문이 위반.
- **Action Required**: #5 두 번째 bullet을 "결정 입력으로 #1, #2 결과 + 1주 메트릭 수집 결과를 사용 가능"으로 톤다운 또는 §8 introduction에 "본 항목은 plan 작성 시 입력 자료" 명시.

#### 10. [ACCEPT] [Low] §5.3 settings.local.json 라인 범위 188-208 → 188-209
- **Source**: Critic only (#7)
- **Critic**: 실제 PostToolUse 블록은 closing `]` 포함 188-209.
- **Judgment**: file:line 정확도 강조 문서이므로 정정.
- **Action Required**: "188-209"로 수정.

#### 11. [ACCEPT] [Low] Q-C "fake event 비중 높음" 주관 판정
- **Source**: Critic only (#8)
- **Critic**: §7.2가 "측정 미확보"로 동일 사안 분류한 것과 일관성 결여.
- **Judgment**: epistemic discipline 일관성 차원에서 표현 정정.
- **Action Required**: "fake event 비중 높음" → "fake event 포함 가능성 (정확 비율은 §7.2 #1)".

#### 12. [REJECT] [Low] 분석 전용 문서가 즉시 af.spec/dependency 변경 요구
- **Source**: Cross (#6)
- **Original Finding**: AST/LSP 관련이라 frozen build 변경 범위가 빠진 것처럼 보임.
- **Rejection Reason**: Cross 본인이 self-reject — 본 문서는 baseline 분석이며 plan이 아님. Critic의 "Missing from Design" 항목(frozen build 영향)은 후속 plan 작성 시 입력으로 분류 가능하지만 본 문서 결함은 아님.

### Summary Table

| #  | Title                                       | Severity | Verdict | Source       |
|----|---------------------------------------------|----------|---------|--------------|
| 1  | Q-D 98% PASS 표본 편향                      | High     | ACCEPT  | Critic       |
| 2  | Q-A 표 vs §148 자가 모순                    | High     | ACCEPT  | Critic       |
| 3  | 재현성 — 추출 명령 + commit SHA 부재         | High     | ACCEPT  | Both         |
| 4  | hook_events.log 측정 범위 누락 (Q-B, Q-E)   | High     | ACCEPT  | Cross+Critic |
| 5  | Q-F silent failure 후보 미점검              | Medium   | ACCEPT  | Critic       |
| 6  | review_bundle line number contract          | Medium   | ACCEPT  | Cross        |
| 7  | Bundle {file_path} 절대/상대 미명시          | Medium   | ACCEPT  | Cross        |
| 8  | §6 row 2 SST 확인됨 권원 부재                | Medium   | ACCEPT  | Critic       |
| 9  | §8 #5 plan vs 분석 경계 흐림                 | Medium   | ACCEPT  | Critic       |
| 10 | §5.3 settings.local.json 188-209            | Low      | ACCEPT  | Critic       |
| 11 | Q-C "비중 높음" 주관 판정                    | Low      | ACCEPT  | Critic       |
| 12 | af.spec/dependency 즉시 변경 요구            | Low      | REJECT  | Cross        |

### Recommendations

구현(분석문서 정정) 진입 전 다음 작업을 한 PR에 묶어 처리:

1. **Q-D / Q-A 정정 (#1, #2)** — 표본 편향 caveat + 메타 리뷰 표기. §6 비교 매트릭스 row 4에서 "98%" 인용 제거.
2. **§9.4 신설 + commit SHA pin (#3)** — Q-A~Q-F 각 추출 명령 1줄 + oh-my-openagent fetch 시점 SHA.
3. **Q-B / Q-E / Q-F 측정 범위 명확화 (#4, #5)** — hook-enforced 경로 한정 명시, manual subagent / silent failure 후보 분리.
4. **review_bundle schema 계약 (#6, #7)** — line 1-based 정규화 + 테스트 추가, file_path workspace-relative 고정 (구현 변경은 본 PR에서 분리해도 무방하나 §5.2 schema 문서 정정은 본 PR에서).
5. **§6 권원 표시 (#8)** + **§8 #5 톤다운 (#9)** + **Low 정정 (#10, #11)** — 텍스트 수정.
6. 정정 후 단일 설계문서 정책에 따라 **af-cross-review 1개만** 재실행 (CLAUDE.md 2026-05-01 변경).