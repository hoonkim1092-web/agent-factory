# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-26 17:02
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

WARN = One Medium finding accepted (test name mismatch) + one Medium advisory on silent downstream semantics. No Critical issues. Production callers verified safe.

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Medium] Test name no longer reflects behavior
- **Critic**: `tests/test_dogfood.py:593` 함수명은 `blocks_empty_research_brief_and_premortem`인데 실제 단언은 빈 brief를 **허용**한다. grep으로 회귀 추적 시 정반대 의미를 보게 됨.
- **Cross**: not flagged
- **Judgment**: Diff 확인 결과 단언 라인(`== ""`)이 "허용"을 의미하는 게 맞고, 함수명은 그대로다. 거짓 광고 위험 실재. Critic의 단독 발견이지만 증거(파일·라인·코드)가 명확해 ACCEPT.
- **Action Required**: 함수를 두 케이스로 분리하거나 (`test_strict_contract_allows_empty_research_brief` + `test_strict_contract_blocks_premortem_missing_spec_intent`), 단일 이름이라면 `allows_empty_research_brief_and_blocks_premortem_missing_spec_intent`로 재명명.

#### 2. [ACCEPT-as-advisory] [Medium] 빈 brief = "비제약 research" 묵시 의미 — 문서화 필요
- **Critic**: `core/research_brief.py:65-66`의 `is_empty() → True` 경로가 RESEARCH_BRIEF strict 완화와 결합되면 §17 Step 3 "Constrain Research to the Research Brief" 보장을 단순 작업이 우회한다. 현재 `_run_research_phase`가 stub이라 무해하나 실제 연결 시 silent regression 위험.
- **Cross**: 동일 경로를 검증했으나 "intentional behavior"로 해석하며 REJECT (`compile_spec()`이 None/empty를 명시적으로 unconstrained로 처리).
- **Judgment**: 두 리뷰어가 **같은 코드 경로**를 보고 다른 결론. 코드 증거 — `research_brief.py:60`과 `spec_compiler.py:171`이 빈 brief를 의도적으로 unconstrained로 다루는 건 사실(Cross 맞음). 그러나 Critic의 우려는 "현재 버그"가 아니라 "**실제 research 연결 시점**의 회귀 위험"으로, 미래 시점 위험에 대한 advisory다. 코드 결함은 없음 — 단, semantic 변경 기록은 의무.
- **Action Required**: 다음 중 하나:
  - (a) `change_history.md`(또는 `Master_Blueprint.md §12`)에 "RESEARCH_BRIEF strict_contract 완화 — 단순 작업은 비제약 research 허용" 항목 추가
  - (b) `_run_research_phase`가 실제 LLM 호출로 연결될 때 `brief.is_empty()` 경로에 가드/로그 추가 TODO 주석 잔존 확보

#### 3. [HOLD] [Low] INTERVIEW phase가 `research_questions` 누락을 침묵 전파
- **Critic**: `core/dogfood.py:1169-1172` — INTERVIEW가 goal/intent만 통과시키면 research_questions가 비어도 strict_contract가 못 잡음. `_append_phase_trace`의 `critical_counts`에 `questions_count`/`risk_hints_count` 분리 기록 여부 확인 권고.
- **Cross**: not flagged
- **Judgment**: 즉시 수정 불필요(Critic도 인정). 단, phase_trace 가시성 한 줄 확인이면 끝나는 사안이라 HOLD.
- **Question for Author**: `_append_phase_trace`의 `critical_counts`에 `questions_count`, `risk_hints_count`가 분리 기록되는가? 없으면 후속 회귀 추적이 어려움 — 추가 1줄 패치 가치 있음.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Test name mismatch | Medium | ACCEPT | Critic |
| 2 | Empty brief = unconstrained — change_history 기록 필요 | Medium | ACCEPT (advisory) | Critic |
| 3 | INTERVIEW phase silent propagation | Low | HOLD | Critic |

### Recommendations
- **필수 (병합 전)**: `tests/test_dogfood.py:593` 함수명 수정 — 단언과 일치시키거나 두 테스트로 분리.
- **권장 (같은 커밋)**: `change_history.md` 또는 `Master_Blueprint.md §12`에 "RESEARCH_BRIEF strict_contract 완화 (단순 작업 비제약 research 허용)" 한 줄 기록 — 추후 `_run_research_phase` 실제 연결자가 의미를 알 수 있도록.
- **후속 검토 (선택)**: `_append_phase_trace`가 `questions_count`/`risk_hints_count`를 phase_trace에 분리 기록하는지 1회 확인. 없으면 1줄 추가.
- **Cross의 REJECT 2건은 타당** — production caller(`agent_launcher.py:1055`)에서 SPEC/PREMORTEM/PLAN/VERIFY strict 가드가 살아 있고, `compile_spec()`이 empty brief를 의도적으로 처리하므로 기능적 회귀는 없음. WARN은 *명명·문서화* 차원이지 코드 동작 결함이 아님.