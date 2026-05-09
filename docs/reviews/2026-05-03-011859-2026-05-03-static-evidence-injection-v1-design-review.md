# Design Review: 2026-05-03-static-evidence-injection-v1

> Source: docs/plans/2026-05-03-static-evidence-injection-v1.md
> Date: 2026-05-03 01:18
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

Cross Review 프로바이더 오류(OpenAI Codex 초기화 실패)로 응답 없음 — Critic 단독 리뷰만 유효. Critic 모든 항목이 실측 라인 번호를 동반한 강한 증거를 포함하므로 Rule 2("단독이지만 evidence 강함") 기준으로 전부 ACCEPT 처리.

Critical 판정 없음. §4.3 [High] 미수정 시 구현 시 즉시 TypeError 발생 — 구현 전 설계 수정 필수.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [High] §4.3 — `append_metric()` 스니펫에 기존 파라미터 3개 누락

- **Critic**: 설계 스니펫(L132-144)에 `duration_ms`, `tokens`, `tool_calls` 없음. `review_metrics_logger.py:L144-153`에 3개 현존 확인. 스니펫 그대로 구현 시 기존 호출부 전체 TypeError.
- **Cross**: 미응답 (프로바이더 오류)
- **Judgment**: 실측 파일·라인 근거. 설계 스니펫은 추가 파라미터만 표시하고 기존 파라미터를 생략했으나, 구현자가 전체 교체로 오독할 위험이 높다.
- **Action Required**: §4.3 스니펫에 `duration_ms: int | None = None`, `tokens: int | None = None`, `tool_calls: int | None = None` 3개를 `extension_log_count` 다음에 명시. 또는 스니펫 전체를 "기존 파라미터 유지, 아래 3개 추가" 텍스트로 대체.

---

#### 2. [ACCEPT] [Medium] §4.4 — evidence 수집 블록이 try/except 바깥에 위치

- **Critic**: `_post_agent_record()`의 Phase 3.5 전체는 `try/except Exception: pass`(L358-374)로 래핑되어 있으나, 설계가 삽입을 지시하는 evidence 수집 블록은 그 바깥이다. `read_text()`/`re.findall()` 예외 시 `record_review_done()` 호출도 건너뜀 — "best-effort" 설계 의도와 배치.
- **Cross**: 미응답
- **Judgment**: 설계 §1에서 "best-effort" 원칙을 명시하고 있으므로, 구현 위치가 원칙과 모순됨.
- **Action Required**: §4.4 스니펫 삽입 위치 지시를 "Phase 3.5 try/except 내부"로 수정. 또는 evidence 수집 블록에 독립 `try/except Exception: pass` 래핑 명시.

---

#### 3. [ACCEPT] [Medium] §4.2 — `("__import__($A)", "dynamic_import")` 단일 인자만 매칭

- **Critic**: ast-grep `$A`는 단일 표현식. `__import__('m', globals(), locals(), ['attr'])` 4-인자 표준 패턴은 누락. `_grep_risks`의 `r"__import__"` 패턴과 결과 불일치 유지됨.
- **Cross**: 미응답
- **Judgment**: ast-grep multi-arg wildcard `$$$ARGS`를 사용하면 해결 가능. 설계 의도("두 engine 결과 통일")에 명백히 반함.
- **Action Required**: §4.2 스니펫을 `("__import__($$$ARGS)", "dynamic_import")`로 변경.

---

#### 4. [ACCEPT] [Low] §4.4 — `import re` 인라인 삽입 중복

- **Critic**: `hook_runner.py:L26`에 모듈 수준 `import re` 이미 존재. 인라인 `import re`는 동작하지만 불필요하고 리뷰 오해 유발.
- **Cross**: 미응답
- **Judgment**: 실측 라인 근거. 기능 문제 없으나 설계 스니펫이 그대로 복사되면 혼란 발생.
- **Action Required**: §4.4 스니펫에서 `import re` 라인 삭제.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §4.3 `append_metric()` 기존 파라미터 3개 누락 | High | ACCEPT | Critic |
| 2 | §4.4 evidence 수집이 try/except 바깥 | Medium | ACCEPT | Critic |
| 3 | §4.2 `__import__($A)` 단일 인자만 매칭 | Medium | ACCEPT | Critic |
| 4 | §4.4 `import re` 인라인 중복 | Low | ACCEPT | Critic |

---

### Recommendations

구현 시작 전 설계 문서에 반영 필수:

1. **[필수, High]** §4.3 스니펫에 기존 파라미터 3개(`duration_ms`, `tokens`, `tool_calls`) 명시 또는 텍스트 주석으로 "기존 유지 + 3개 추가" 의도 명확화
2. **[필수, Medium]** §4.4 evidence 수집 블록 삽입 위치를 Phase 3.5 `try/except` 내부로 이동 — 또는 독립 래핑 방식 명시
3. **[필수, Medium]** §4.2 `__import__($A)` → `__import__($$$ARGS)` 수정
4. **[권고, Low]** §4.4 스니펫에서 `import re` 제거
5. **[Advisory]** §4.3과 §4.4 연결 누락 — `_post_agent_record()`의 `append_metric()` 호출부에 3개 신규 파라미터 전달 스니펫을 §4.3 또는 §4.4 중 한 곳에서 명시적으로 안내 (두 섹션 분리로 구현자가 연결을 빠뜨릴 위험)
6. **[Advisory]** `_AGENT_TIER_MAP` 커버리지 조건(등록되지 않은 에이전트 타입 → `return 0`)을 §4.1 검증 방법에 추가 — "어떤 에이전트 타입으로 실행해야 하는지" 명시

> **Cross Review 부재 비고**: OpenAI Codex 프로바이더 초기화 오류로 응답 없음. 본 집계는 Critic 단독 기준. 고위험 항목(Finding #1)은 실측 라인 근거가 명확하므로 단독 ACCEPT 처리했으나, 필요 시 Cross Review 재실행 권장.