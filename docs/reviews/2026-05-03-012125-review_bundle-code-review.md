# Code Review: review_bundle

> Source: core/review_bundle.py
> Date: 2026-05-03 01:21
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

> **Note**: Cross Review failed due to provider error (Codex session terminated mid-prompt). Judgment relies solely on Critic findings + diff evidence. All three findings are independently verifiable from the diff.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Medium] 다중 줄 코드 텍스트가 마크다운 bullet 포맷 붕괴

- **Critic**: `r['text'].strip()[:120]` 내부 `\n`이 남아 bullet 라인을 끊음
- **Cross**: 미참여 (provider error)
- **Judgment**: Diff line 131의 새 포맷 `` f"코드: `{r['text'].strip()[:120]}`\n" `` 에서 `r['text']`는 `_ast_risks()`의 AST 노드 텍스트로, 다중 줄 표현식(`__import__(\n    'os'\n)`)을 포함할 수 있음이 코드 구조상 자명하다. `.strip()`은 앞뒤만 처리한다. 증거 충분.
- **Action Required**: `r['text'].strip().replace('\n', ' ')[:120]`

#### 2. [ACCEPT] [Medium] 코드 텍스트 내 백틱이 인라인 코드 스팬 오염

- **Critic**: 소스 코드에 백틱이 포함되면 마크다운 인라인 코드 스팬이 중간에 닫힘
- **Cross**: 미참여 (provider error)
- **Judgment**: 동일 줄(L131)의 구조적 문제. Python 소스는 docstring이나 f-string 리터럴에 백틱을 포함할 수 있고, raw 텍스트를 backtick-span 안에 그대로 삽입하는 패턴은 이를 처리하지 못한다. Finding 1과 동일 위치이므로 단일 수정으로 두 이슈를 해결 가능.
- **Action Required**: `r['text'].strip().replace('`', "'").replace('\n', ' ')[:120]` — Finding 1과 합산 적용

#### 3. [ACCEPT] [Low] `__import__` 패턴 AF 스킬 서브시스템 고빈도 오탐

- **Critic**: `skill_loader.py` 등 AF 내부 코드가 정상적으로 `__import__`를 사용 → 모든 스킬 파일이 noise 항목으로 등장
- **Cross**: 미참여 (provider error)
- **Judgment**: Diff line 73에 `("__import__($A)", "dynamic_import")` 패턴이 추가됨. `_RISK_DESC`에 "외부 입력 경로 주입 시 위험"이라 기술되어 있으나, AF 스킬 시스템이 내부 경로로 `__import__`를 정상 사용함은 `core/skill_*.py` 구조에서 도출 가능. 배제 목록 없이 추가하면 리뷰 번들의 S/N비가 하락한다.
- **Action Required**: Low 심각도 — 즉시 수정 의무 없음. 다음 중 하나 추적:
  - `_RISK_DESC`에 `"dynamic_import"` 항목에 severity 레벨 필드 추가, 또는
  - `_ast_risks()` 호출 시 내부 경로(`core/skill_*.py`) 제외 파라미터 지원

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 다중 줄 코드 텍스트 마크다운 포맷 붕괴 | Medium | ACCEPT | Critic |
| 2 | 백틱 인라인 코드 스팬 오염 | Medium | ACCEPT | Critic |
| 3 | `__import__` 오탐 — AF 스킬 경로 | Low | ACCEPT | Critic |

---

### Recommendations

- **L131 단일 수정으로 #1 + #2 동시 해결**: `r['text'].strip().replace('`', "'").replace('\n', ' ')[:120]`
- **#3은 WARN advisory** — 이번 커밋을 막지 않음. `_RISK_DESC` severity 필드 추가를 다음 이슈로 등록 권장.
- **Cross Review 재실행 불필요** — 두 Medium 이슈는 diff 증거만으로 충분히 확인됨. Provider 오류 재시도는 비용 대비 효과 없음.