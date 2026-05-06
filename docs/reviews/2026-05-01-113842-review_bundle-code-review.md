# Code Review: review_bundle

> Source: core/review_bundle.py
> Date: 2026-05-01 11:38
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The Critic received an empty diff and correctly flagged the process anomaly. The Cross reviewer located and reviewed `core/review_bundle.py` directly, surfacing 4 substantive findings with specific file:line evidence. No findings were duplicated across both reviewers (Critic had nothing to compare against). Per Rule 2, Cross-only findings with strong evidence are ACCEPT.

No Critical findings exist, so BLOCK is not warranted. Four Medium-severity findings prevent a clean PASS.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] `workspace` parameter ignored — relative paths yield silent empty bundles
- **Critic**: not flagged (no diff provided)
- **Cross**: `core/review_bundle.py:86` — `workspace` accepted but unused; `_grep_risks()` returns `[]` on `OSError`, so a relative path resolving to a missing file produces a clean-looking bundle with no actual risk data
- **Judgment**: Strong evidence. `scripts/enqueue_agent_review.py:102` confirms relative paths are stored in the queue JSON; callers running outside the workspace silently get empty risk results rather than an error. This is a correctness defect.
- **Action Required**: Before passing `fp` to `_grep_risks()` / `_ast_risks()`, resolve non-absolute paths via `Path(workspace or '.') / fp`. Preserve the original relative path string in the emitted bundle output.

---

#### 2. [ACCEPT] [Medium] AST mode silently drops `dynamic_import` (`__import__`) detection
- **Critic**: not flagged
- **Cross**: `core/review_bundle.py:66` — `_RISK_PATTERNS` contains `__import__` as `dynamic_import`, but `_ast_risks()` has no equivalent rule; installing `ast-grep-py` makes the scanner *less* complete than the grep fallback
- **Judgment**: Strong evidence. The mode switch is capability-downgrade rather than upgrade for this pattern — a regression that installs silently.
- **Action Required**: Either add an AST rule for `__import__($A)` in `_ast_risks()`, or union grep-fallback hits for patterns not covered by AST rules.

---

#### 3. [ACCEPT] [Medium] Non-atomic write in `save()` — matches tracked technical debt pattern
- **Critic**: not flagged (but proactively warned that M10 non-atomic write pattern should be watched for this file)
- **Cross**: `core/review_bundle.py:116` — `out.write_text(...)` can leave a truncated bundle on interrupt; adjacent queue scripts (`review_gate.py:96`, `enqueue_agent_review.py:119`) already use `tempfile.mkstemp()` + `os.replace()`; `code-review.md:317` tracks this as known technical debt
- **Judgment**: Critic's advisory aligns with Cross's specific finding. The project's own tracked debt list and adjacent code both confirm the correct pattern. This is an established project convention being violated.
- **Action Required**: Write to `review_bundle.md.tmp` in the same directory, then call `os.replace()` into the final path. If concurrent hook invocations are possible, reuse the existing queue lock pattern.

---

#### 4. [ACCEPT] [Medium] Bundle header missing `generated_at` and `source_hash` — stale detection impossible
- **Critic**: not flagged
- **Cross**: `core/review_bundle.py:107` — header records only `engine`; `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md:303` explicitly requires `generated_at` and `source_hash` for stale-bundle detection; `enqueue_agent_review.py:104` already tracks `updated_at` per entry
- **Judgment**: The plan requirement is explicit and documented. Without these fields, the cost-reduction plan's cache invalidation logic has no basis to determine whether an existing bundle can be reused.
- **Action Required**: Add `generated_at` (ISO timestamp) and `source_hash` (deterministic hash of `changed_files` content) to `build()` return value and serialize both in the first section of `save()` output.

---

### Process Note (Critic Finding)

The Critic's observation that the review gate fired on an empty diff is a valid operational concern but is not a code defect in `review_bundle.py`. It wastes LLM budget and adds noise to `hook_events.log`. Consider adding a short-circuit guard to the pre-commit hook: if `git diff --name-only HEAD | grep -q 'core/'` returns no matches, emit `SKIP (no core changes)` and exit 0 without spawning reviewers.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `workspace` ignored → silent empty bundles | Medium | ACCEPT | Cross |
| 2 | AST mode drops `dynamic_import` detection | Medium | ACCEPT | Cross |
| 3 | Non-atomic write in `save()` | Medium | ACCEPT | Cross (+Critic advisory) |
| 4 | Missing `generated_at`/`source_hash` in header | Medium | ACCEPT | Cross |

---

### Recommendations

1. **Fix workspace resolution** in `build()` before calling risk scanners — one `Path(workspace or '.') / fp` guard covers all callers.
2. **Add `__import__` AST rule** or union AST+grep results so installing `ast-grep-py` does not regress detection coverage.
3. **Apply `mkstemp` + `os.replace()` pattern** in `save()` — already present in two adjacent scripts, just extend the convention.
4. **Inject `generated_at` and `source_hash`** into bundle header to unblock the Phase 1 stale-detection requirement from the cost-reduction plan.
5. **Add `core.review_bundle` to `af.spec` hiddenimports** in the same commit as the file creation (Cross confirmed it is already present at `af.spec:40` — verify it persists after any future spec regeneration).
6. **Add empty-diff short-circuit** to the pre-commit hook to avoid wasting review budget on null changesets.