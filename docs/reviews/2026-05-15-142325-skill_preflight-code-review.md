# Code Review: skill_preflight

> Source: core/skill_preflight.py
> Date: 2026-05-15 14:23
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff itself (replacing `os.environ.get(...)` with `_env_flag(...)`) is a correct, surgical harmonization with the codebase's truthy-parsing convention. Both reviewers agree this is the right fix. However, the **expanded docstring overpromises** ("모든 registry write 를 skip") relative to what the gate actually covers, and a known sibling write path (`workflow_apply()`) remains ungated. Mergeable with documented follow-ups.

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] Docstring claims "모든 registry write 를 skip" but `workflow_apply()` still bypasses the gate
- **Critic**: Diff harmonizes `skill_preflight` but the "second line of defense" promise (line 260) is false at the systemic level. `registry_manager.workflow_apply()` (lines 396-407) writes `WORKFLOW_PATH` directly without `_env_flag`, and `skill_procurer.py` invokes it after every successful build.
- **Cross**: Not flagged (scope limited to the diff lines).
- **Judgment**: Critic's evidence is concrete — the new docstring explicitly says "**모든** registry write 를 skip" but the diff does not extend the gate to `workflow_apply()`. This is a documentation/implementation mismatch introduced *by this very diff*. The functional regression from the previous behavior is zero (workflow_apply was already unguarded), but the docstring now states an invariant that isn't true.
- **Action Required**: Either (a) add `if _env_flag("AF_DISABLE_REGISTRY_WRITE"): return` at the top of `registry_manager.workflow_apply()` (registry_manager.py:397), making the docstring true; or (b) soften the docstring to "skill registry write" (the actual scope) and file a follow-up for `workflow_apply()`.

#### 2. [ACCEPT] [Medium] `_env_flag` is private (leading underscore) but now imported by 3+ modules
- **Critic**: `core/file_io._env_flag` is declared private but consumed by `registry_manager.py:15`, `skill_preflight.py:29`, and `tests/test_agent_launcher_cli_dispatch.py:155`. Convention drift signals "internal" while every consumer treats it as canonical.
- **Cross**: Not flagged.
- **Judgment**: Evidence is verifiable in the diff (`from core.file_io import _env_flag`) and matches the existing pattern in `registry_manager.py:15`. Style-level, not functional. Worth fixing while convention is still localized to a small surface.
- **Action Required**: Rename to `env_flag()` in `core/file_io.py` and update 3 call sites + the test in the same commit. Defer if a separate follow-up is preferred.

#### 3. [ACCEPT] [Medium] No behavior-level test pins the call-site contract
- **Critic**: `TestEnvFlagConvention` tests `_env_flag()` directly but not that `_update_registry_status` actually calls it. A future refactor reverting line 265 to `os.environ.get(...)` would still pass these tests.
- **Cross**: Not flagged.
- **Judgment**: Critic is correct that the regression-prone call site is uncovered. The fix being applied is exactly the kind of "easy to silently revert" change — and the diff doesn't add a guard test.
- **Action Required**: Add a test that constructs a `PreflightEvaluator`, sets `AF_DISABLE_REGISTRY_WRITE=0` (regression case) vs `=1` (skip case), and asserts the registry file mtime/content changes accordingly.

#### Reviewer-flagged but rejected after aggregation
- **Critic Finding #3** (silent semantic flip for `=0`): Cross correctly identifies this as the *intended* fix, not a regression. Critic's own follow-up confirmed no `=0` callers exist in the repo. **REJECT as an issue**, but the commit message should note the truthy-parsing change for external consumers (one-line mention sufficient).

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Docstring overpromises; `workflow_apply()` still ungated | High | ACCEPT | Critic |
| 2 | `_env_flag` private name leaked to public consumers | Medium | ACCEPT | Critic |
| 3 | Call-site behavior not pinned by tests | Medium | ACCEPT | Critic |
| — | `=0` semantic flip | — | REJECT | Critic (Cross overrides) |
| — | `af preflight` caller path broken | — | REJECT | Cross self-rejected |
| — | Syntax/encoding damage | — | REJECT | Cross self-rejected (py_compile passes) |

### Recommendations
1. **Fix or soften the docstring claim**: either gate `workflow_apply()` (preferred — completes the F12 invariant) or scope the docstring to "skill registry write".
2. **Promote `_env_flag` → `env_flag`** in `core/file_io.py` and update 3 import sites + test. Small atomic refactor.
3. **Add a call-site regression test** for `_update_registry_status` with both `AF_DISABLE_REGISTRY_WRITE=0` and `=1`.
4. **Add a one-line note in the commit message**: "AF_DISABLE_REGISTRY_WRITE truthy-parsing now matches `_env_flag` (1/true/yes/on/y); `=0` and `=false` now perform the write."