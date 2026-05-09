# Code Review: research_router

> Source: core/research_router.py
> Date: 2026-05-07 17:32
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

One High finding (semantic gap between rename and actual downstream behavior) and one Medium finding (substring false-positive unaddressed). No Critical issues. Can merge with documented risks.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] `_detect_domain_hints` 레이블과 실제 hard-gate 사용 불일치

- **Critic**: "not flagged (docstring 개선으로 가중치 하향 평가)"
- **Cross**: "`plan()`이 결과를 `ResearchPlan.domain`에 저장 → `project_pipeline.py:890-897`이 `SpecGenerator`, ADR/traceability, `ResearchGateBlocked`에 hard gate로 사용. 'hint' 레이블과 동작이 다름."
- **Judgment**: Cross 단독이지만 증거가 구체적이다. 리네임은 `_detect_domain_hints`로 의미를 약화시켰으나 `plan()`의 `result.domain = self._detect_domain_hints(request)` 라인은 그대로다. downstream이 여전히 `domain`을 hard gate로 소비한다는 코드 경로가 명확하다. docstring의 "gate 아님" 선언이 거짓말이 된다.
- **Action Required**: `ResearchPlan`에 `domain_hints: str` 필드를 분리하거나, `plan()` 반환 시 `result.domain_hint = ...`으로 별도 필드로 라우팅하고 `project_pipeline.py`가 authoritative `domain`만 hard gate에 사용하도록 분리한다. 또는 docstring에서 "gate 아님" 주장을 제거하고 현 동작을 그대로 문서화한다(의미 변경 없이 네이밍만 수정한 경우).

---

#### 2. [ACCEPT] [Medium] 서브스트링 false-positive 위험 미해결

- **Critic**: "`antecedent`→`ante`, `delivery`→`river`, `floppy disk`→`flop` 모두 `'poker'` 반환. 리네임과 docstring이 'hint'로 가중치를 낮췄지만 코드 자체는 바뀌지 않았다."
- **Cross**: "not flagged"
- **Judgment**: Critic 단독이지만 코드 증거가 명확하다. `any(tok in text_lower for tok in self._POKER_TOKENS)` 는 word-boundary 없이 서브스트링 매칭한다. Finding 1이 해결되어 `domain`이 advisory로 격하되면 severity는 Low로 낮아지지만, 현재는 hard gate이므로 Medium 유지.
- **Action Required**: Finding 1 해결 방향에 따라 처리가 달라진다. hard gate 유지 시 `re.search(r'\b' + re.escape(tok) + r'\b', text_lower)` 적용. advisory로 격하 시 docstring에 "서브스트링 매칭, false-positive 허용" 명시로 대체 가능.

---

#### 3. [REJECT] `_detect_domain` wrapper 사망 코드 — caller 존재 확인됨

- **Critic**: "`plan()`이 이미 `_detect_domain_hints()`를 직접 호출하므로 wrapper는 시작부터 dead code."
- **Cross**: "`core/researcher.py:928`이 `ResearchRouter()._detect_domain(task_input)` 호출. wrapper가 backward compat을 유지하므로 REJECT."
- **Judgment**: Cross가 `pytest tests/test_research_router_modes.py tests/test_quality_contract.py` 132개 통과로 검증했다. `researcher.py:928`의 실제 caller가 존재하므로 wrapper는 dead code가 아니다. Critic의 전제(외부 호출자 없음)가 사실과 다르다. — **Rejected.**

---

#### 4. [HOLD] [Low] cross-module 동작 계약이 잘못된 docstring에 기술됨

- **Critic**: "`_detect_domain_hints` docstring이 `QualityContractBuilder` 동작을 기술 — 다른 클래스 변경 시 silently stale."
- **Cross**: "not flagged"
- **Judgment**: Low severity, Critic 단독. Finding 1 해결 후 docstring을 전면 개정하게 되면 자연히 같이 수정된다. 독립 수정 의무 없음.
- **Question for Author**: Finding 1을 어느 방향으로 해결할지 결정 후, docstring 개정을 그 변경에 포함할 것인지 확인.

---

### Failing Test (별도 추적)

- **Cross Finding 3**: `TestB1MaxRoundsCapPreventsInfiniteLoop` — web calls 148, expected ≤16. Cross 판단: 이번 diff와 무관한 기존 결함. 이번 리뷰 scope 외. 별도 이슈로 추적 권장.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Hint 레이블 vs hard-gate 실사용 불일치 | High | ACCEPT | Cross |
| 2 | 서브스트링 false-positive 미해결 | Medium | ACCEPT | Critic |
| 3 | `_detect_domain` wrapper dead code 주장 | — | REJECT | Critic (Cross 반박) |
| 4 | cross-module 계약 잘못된 docstring 위치 | Low | HOLD | Critic |

---

### Recommendations

- **Finding 1 먼저 결정**: `domain` 필드를 advisory vs. authoritative 중 하나로 확정한다. 리네임만 하고 동작을 바꾸지 않으면 docstring이 거짓이 된다.
- **Finding 1 결정 후 Finding 2 처리**: hard gate 유지 → word-boundary 적용; advisory 격하 → false-positive 허용 명시.
- **Finding 4는 Finding 1 수정 커밋에 편승**: docstring을 같이 개정하면 추가 커밋 불필요.
- **Failing test (`TestB1MaxRoundsCapPreventsInfiniteLoop`)**: 이번 PR과 별도로 원인 추적 — recovery loop / quality contract 경로 의심.