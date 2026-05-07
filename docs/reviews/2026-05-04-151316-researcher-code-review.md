# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-04 15:13
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

두 결함 정정(G3 메타데이터 오염, G5 retry 예외 보존)은 정확하고 surgical하게 처리되었습니다. Cross Review는 provider error로 결과 부재 — Critic 단독 입력 기반 판정. Critic이 Critical 결함을 0건 보고했고 모두 Medium/Low advisory 수준이므로 PASS에 가깝지만, **G5 retry 예외 경로 직접 회귀 테스트 누락**이 정정 의도의 핵심을 잡지 못해 WARN으로 격상.

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] G5 retry 예외 경로 회귀 테스트 누락
- **Critic**: "결함 #2 정정의 핵심 의도(retry 예외 시 1차 `data` 보존)를 직접 검증하는 테스트가 없음. case 6는 정상 retry 성공만 검사."
- **Cross**: not flagged (provider error)
- **Judgment**: diff `core/researcher.py:500-505`의 핵심 행동 변경(retry try/except 분리 → 예외 시 1차 data 반환)이 테스트로 락인되지 않음. 누군가 try/except를 outer로 다시 합치는 회귀가 들어와도 잡히지 않음. 단일 리뷰어 발견이지만 코드 evidence로 확인 가능.
- **Action Required**: `tests/test_research_system_regression.py` G5 case에 `side_effects = [{"ok": True, "text": json.dumps(base)}, RuntimeError("transient")]` 케이스 추가 후 1차 data 필드(`goal_interpretation` 등) 보존 검증.

#### 2. [HOLD] [Medium] Silent exception swallow (`except Exception: pass`)
- **Critic**: "code-review.md §3.2 H3와 동일 패턴. retry 실패 사유가 묻힘. 운영 시 추적 어려움."
- **Cross**: not flagged
- **Judgment**: Critic 본인도 "파일 컨벤션과는 정합"하다고 인정. 본 diff의 신규 결함이라기보다 기존 패턴 답습. 정정 전(retry 예외 시 _FALLBACK 폐기)보다는 명백히 개선. 별도 후속 작업 적합.
- **Question for Author**: 운영 디버깅용 `logging.debug(..., exc_info=True)` 1줄 추가를 본 PR에서 처리할지, 아니면 §3.2 H3 일괄 정리 시 함께 처리할지.

#### 3. [ACCEPT] [Low] NotebookLM 입력에서 LLM-prior 묵음 (의도된 부수효과)
- **Critic**: "정정 후 fallback 경로의 `web_refs == []`라 NotebookLM은 LLM prior를 못 봄. 정합성 측면에선 옳은 변화."
- **Cross**: not flagged
- **Judgment**: `core/researcher.py:770` `_collect_notebook_summary(task_input, local_refs, web_refs)` 호출 — verified=False를 web으로 위장하지 않게 된 것은 올바른 결과. 다만 행동 변화가 commit/Blueprint에 명시되지 않음.
- **Action Required**: Master_Blueprint.md §12에 "Tavily 미설정 + AF_RESEARCH_LLM_FALLBACK=1 경로에서 NotebookLM은 더 이상 LLM prior를 입력받지 않음" 1줄 기록.

#### 4. [HOLD] [Low] `_synthesize_structured_evidence` 프롬프트가 authority/verified 미전달 (선재 문제)
- **Critic**: "본 diff가 만든 결함은 아니지만, 결함 #1 정정의 효과를 synthesizer가 무시하는 모순."
- **Cross**: not flagged
- **Judgment**: Critic 스스로 "본 diff 무관, 후속 작업"으로 분류. 본 PR 범위 외.
- **Question for Author**: 별도 work-item으로 분리 추적할지 결정.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | G5 retry 예외 회귀 테스트 누락 | Medium | ACCEPT | Critic |
| 2 | Silent exception swallow | Medium | HOLD | Critic |
| 3 | NotebookLM LLM-prior 묵음 (행동 변화 명시) | Low | ACCEPT | Critic |
| 4 | synthesizer authority 미전달 (선재) | Low | HOLD | Critic |

### Recommendations

- **본 PR에서 수정**: Finding #1 회귀 테스트 1케이스 추가 (`RuntimeError` retry → 1차 data 보존 검증). Finding #3 §12 1줄 기록.
- **본 PR 범위 외**: Finding #2 (silent except 일괄 정리), Finding #4 (synthesizer authority 노출) — 후속 work-item으로 분리.
- **Cross Review 재실행 권장**: provider error로 cross 의견 부재. WARN 판정의 신뢰도 보강을 위해 codex provider 정상화 후 재실행하면 PASS로 격상 가능.
- **긍정 평가 유지**: `_build_source_pack`/virtual chunk indexer의 기존 `llm_prior` 분기를 활용한 surgical 변경, retry try/except 분리가 `setdefault` 위치 보존 — Karpathy §3 정합.