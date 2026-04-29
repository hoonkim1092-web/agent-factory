# Code Review: design_review_utils

> Source: core/design_review_utils.py
> Date: 2026-04-29 15:10
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

I'll verify the actual diff state since the critic flagged a recursive-pattern issue.

The current diff (`git diff HEAD`) actually contains **both** the flat and recursive patterns — the reviews appear to have analyzed an earlier interim version. The recursive-vs-flat asymmetry concern raised by the critic is already resolved in the file under review.

## Final Code Review

### Verdict: WARN

No Critical findings. One ACCEPT (Medium) for missing test coverage. Critic's primary findings (#1, #2) about non-recursive matching and pattern asymmetry are already mitigated in the current diff (`core/design_review_utils.py:39-40` includes both `docs/**/20??-??-??-*.md` and `docs/20??-??-??-*.md`). Mergeable with documented follow-up.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] No test coverage for new dated-doc classifier branch
- **Critic**: not flagged
- **Cross**: "INCLUDE_PATTERNS now includes `docs/20??-??-??-*.md`, but no tests exercise `is_design_doc()` or this root dated-doc case." Existing `tests/test_hook_runner_builtins.py` covers hook dispatch, not include/exclude matching.
- **Judgment**: Strong evidence (verified). `is_design_doc()` is the gating predicate consumed by `scripts/design_review_trigger.py:73`, `core/hooks/design_review_hook.py:116,157`. Silent regression would disable design-review enqueue.
- **Action Required**: Add `tests/test_design_review_utils.py` with: `docs/2026-04-29-foo.md → True`, `docs/code_review/code-review.md → False` (excluded), `docs/reviews/2026-04-29-x.md → False` (excluded), `docs/work-items/2026-04-29-x.md → True` (now covered by recursive pattern), `docs/task.md → False`.

#### 2. [REJECT] [Medium] Non-recursive pattern misses sub-directory dated docs
- **Critic**: "Python `glob`에서 `?`와 `*`는 `/`를 넘지 않는다 … `docs/reviews/2026-04-29-…` 형태의 하위 경로는 무시된다."
- **Cross**: not flagged (rejected via policy reference — single design docs live at `docs/` root)
- **Judgment**: Stale. Current diff (`git diff HEAD`) shows lines 39-40 contain BOTH `docs/**/20??-??-??-*.md` (recursive) and `docs/20??-??-??-*.md` (flat). The critic's example (`docs/reviews/...`) is also explicitly excluded by `EXCLUDE_PATTERNS` at `core/design_review_utils.py:48`. Concern is resolved in the version under final review.
- **Action Required**: None.

#### 3. [REJECT] [Medium] flat/recursive pattern pair asymmetry
- **Critic**: "패턴 쌍을 맞춘다 … `docs/**/20??-??-??-*.md` recursive + `docs/20??-??-??-*.md` top-level"
- **Cross**: not flagged
- **Judgment**: Stale. The recommended symmetric pair is already present in the current file. No further action.
- **Action Required**: None.

#### 4. [ACCEPT] [Low] `?` wildcard accepts non-digit characters
- **Critic**: "`?`는 임의의 단일 문자에 매칭된다 … `20AB-XY-ZW-foo.md`도 통과"
- **Cross**: not flagged
- **Judgment**: Real but theoretical — file-naming policy in CLAUDE.md enforces `YYYY-MM-DD-*.md`. No realistic false-positive surface, but pattern intent and behavior diverge. Low priority.
- **Action Required**: Either add a `re.match(r"\d{4}-\d{2}-\d{2}-", basename)` post-filter inside `is_design_doc()`, or add an inline comment "관례 의존: 형식 검증 없음" near `core/design_review_utils.py:39-40`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Missing tests for `is_design_doc()` dated-doc branch | Medium | ACCEPT | Cross |
| 2 | Non-recursive sub-dir miss | Medium | REJECT (stale) | Critic |
| 3 | flat/recursive asymmetry | Medium | REJECT (stale) | Critic |
| 4 | `?` allows non-digit characters | Low | ACCEPT | Critic |

---

### Recommendations
- Add `tests/test_design_review_utils.py` covering the include/exclude matrix above (top priority — only blocking follow-up).
- Optionally tighten date validation: regex post-filter or comment acknowledging convention-dependence.
- The reviewers analyzed a stale diff that lacked the recursive companion pattern; consider re-running cross-review on the final state to confirm no new issues.