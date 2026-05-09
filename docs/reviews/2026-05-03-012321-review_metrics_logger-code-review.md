# Code Review: review_metrics_logger

> Source: scripts/review_metrics_logger.py
> Date: 2026-05-03 01:23
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

> Cross Review is unavailable (provider error — OpenAI Codex session failed to initialize). Aggregation proceeds on Critic findings only; severity is unchanged because all three findings have strong diff-level evidence.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Medium] `evidence_present` / `evidence_items` 불일치 저장 가능

- **Critic**: 호출자가 `evidence_present=True, evidence_items=0` 또는 그 반대를 전달하면 JSONL에 모순 레코드가 영구 저장된다.
- **Cross**: 미응답 (provider error)
- **Judgment**: Diff에 두 독립 파라미터(`evidence_present: bool = False`, `evidence_items: int = 0`)가 동시에 존재하는 것이 직접 증거. `evidence_present`는 `evidence_items > 0`의 alias이므로 중복 파라미터 자체가 설계 결함이다.
- **Action Required**: `append_metric` 내부에서 `"evidence_present": evidence_items > 0`으로 강제하고 파라미터 `evidence_present`를 제거한다. 기존 호출자가 `evidence_present`를 명시적으로 전달하는 경우 → 컴파일 에러로 즉시 발견 가능하므로 하위 호환 위험 낮음.

---

#### 2. [ACCEPT] [Medium] `evidence_cited > evidence_items` 불변식 미검사 — ZeroDivisionError 잠재

- **Critic**: `evidence_items=0`(기본값) 상태에서 `evidence_cited=5`만 전달하면 `{evidence_items:0, evidence_cited:5}` 레코드가 JSONL에 기록된다. 후속 분석 코드가 `evidence_cited / evidence_items`를 계산하면 ZeroDivisionError 발생.
- **Cross**: 미응답 (provider error)
- **Judgment**: 두 기본값이 모두 `0`이고 두 파라미터가 독립이라는 것이 Diff 자체에서 확인된다. `compute_report()` 또는 외부 스크립트가 비율을 계산할 때 충돌이 발생하는 것은 명확한 잠재 결함이다.
- **Action Required**: `_append_jsonl` 호출 직전에 클램핑 추가:
  ```python
  evidence_cited = min(evidence_cited, evidence_items)
  ```
  또는 `evidence_items == 0`이면 `evidence_cited`도 0으로 리셋한다.

---

#### 3. [ACCEPT] [Low] 신규 3개 필드가 `compute_report()`에 미반영

- **Critic**: `evidence_present`, `evidence_items`, `evidence_cited`가 JSONL에는 기록되지만 유일한 analytics 함수 `compute_report()`(212–308행)에서 전혀 집계되지 않는다.
- **Cross**: 미응답 (provider error)
- **Judgment**: 의도적 "수집 먼저, 분석 나중" 패턴일 수 있어 즉각 수정 의무는 없다. 그러나 코드에 단서가 없어 추후 누락으로 오인될 수 있다.
- **Action Required**: `compute_report()` 내에 `# TODO: evidence coverage 집계 추가 예정` 주석 1줄 삽입, 또는 evidence 커버리지 블록을 즉시 구현한다.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `evidence_present` / `evidence_items` 불일치 | Medium | ACCEPT | Critic |
| 2 | `evidence_cited > evidence_items` 불변식 없음 | Medium | ACCEPT | Critic |
| 3 | 신규 필드 `compute_report()` 미반영 | Low | ACCEPT | Critic |

---

### Recommendations

- **즉시**: `evidence_present` 파라미터 제거 → logger 내부에서 `evidence_items > 0`으로 derivation
- **즉시**: `evidence_cited = min(evidence_cited, evidence_items)` 클램핑 추가
- **선택**: `compute_report()`에 evidence 집계 블록 추가 또는 TODO 주석 삽입
- **운영 주의**: Cross Review provider(OpenAI Codex)가 초기화 실패했다. 다음 커밋 전 provider 인증 상태를 확인한다.