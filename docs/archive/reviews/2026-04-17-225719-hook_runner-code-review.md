# Code Review: hook_runner

> Source: scripts/hook_runner.py
> Date: 2026-04-17 22:57
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

WARN = High findings present. Can merge with documented risks, but venv issue and silent timeout should be tracked.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Builtin path bypasses venv resolution — interpreter drift risk
- **Critic**: not flagged
- **Cross**: `sys.executable` used for all builtin subprocess calls; non-builtin path uses `_find_venv_python(root)`. System `python3` may lack dependencies silently.
- **Judgment**: Strong evidence — `settings.local.json:138-168` launches via `python3 scripts/hook_runner.py`, and `Master_Blueprint.md:1082,1107` documents this exact prior failure. Only one reviewer flagged it, but evidence is unambiguous.
- **Action Required**: Resolve `python = _find_venv_python(_project_root())` once at start of `_post_edit_test` (and other builtins) and use it instead of `sys.executable`.

#### 2. [ACCEPT] [High] `TimeoutExpired` silently swallowed — no user signal on timeout
- **Critic**: broad `except Exception` catches `TimeoutExpired`; logs it but prints nothing to stderr; developer sees exit 0 with no feedback.
- **Cross**: coverage gap means timeout path is untested; finding 2 confirms no behavior coverage for timeout.
- **Judgment**: Both reviewers identify the same area. The current code logs via `_log_hook_event` but never surfaces the failure visibly. Exit 0 on timeout is a silent data loss of test results.
- **Action Required**: Add `except subprocess.TimeoutExpired` before the broad `except Exception` with `print(f"[af-test] TIMEOUT running {test_target} (>60s)", file=sys.stderr)`.

#### 3. [ACCEPT] [Medium] `r.stderr` excluded from failure output
- **Critic**: pytest writes import/collection errors to stderr; `r.stdout[-2000:]` is empty on import failure.
- **Cross**: not flagged
- **Judgment**: One reviewer, but the code evidence is clear — `capture_output=True` captures both, but the failure branch only prints `r.stdout`.
- **Action Required**: Change to `print(f"[af-test] FAIL in {fp}\n{r.stdout[-1500:]}\n{r.stderr[-500:]}", file=sys.stderr)`.

#### 4. [ACCEPT] [Medium] `timeout=60` magic number — repeats known M3 pattern
- **Critic**: matches M3 anti-pattern from `code-review.md §3.3` (hardcoded timeout in hooks).
- **Cross**: not flagged directly, but timeout handling is part of finding 2.
- **Judgment**: Consistent with a documented existing code quality issue. Not blocking but should be addressed.
- **Action Required**: Define `_POST_EDIT_TEST_TIMEOUT = int(os.getenv("AF_TEST_TIMEOUT", "60"))` and reference it.

#### 5. [ACCEPT] [Medium] No behavior-level test coverage for `post_edit_test`
- **Critic**: implicitly noted via the untested timeout path
- **Cross**: explicit finding — only dispatch-table membership is tested; target selection, fallback, failure logging, timeout all uncovered.
- **Judgment**: Both reviewers identify coverage gaps. Hook is now live in `settings.local.json:160-164`.
- **Action Required**: Add tests for: matched test file, full-suite fallback, non-`.py` no-op, failure output, and timeout logging, with `subprocess.run` monkeypatched.

#### 6. [HOLD] [Low] Builtin execution is repo-root-scoped; workspace-awareness unclear
- **Critic**: not flagged
- **Cross**: `_project_root()` used for cwd/queue; callees derive workspace from CWD — may write to wrong queue if used outside repo root.
- **Judgment**: Insufficient context to decide — the callee scripts appear repo-root-only in practice given `settings.local.json` wiring, but the contract is ambiguous.
- **Question for Author**: Are `post_edit_*` builtins intentionally repo-root-only, or should they respect `_detect_workspace()` like the non-builtin path?

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Builtin path bypasses venv resolution | High | ACCEPT | Cross |
| 2 | TimeoutExpired silently swallowed | High | ACCEPT | Both |
| 3 | r.stderr excluded from failure output | Medium | ACCEPT | Critic |
| 4 | Magic number timeout=60 | Medium | ACCEPT | Both |
| 5 | No behavior coverage for post_edit_test | Medium | ACCEPT | Both |
| 6 | Repo-root vs workspace-aware coupling | Low | HOLD | Cross |

---

### Recommendations

- **Fix before next release**: Add `except subprocess.TimeoutExpired` branch with visible stderr warning (finding 2).
- **Fix before next release**: Replace `sys.executable` with `_find_venv_python(root)` in the builtin path (finding 1).
- **Fix in same PR**: Include `r.stderr` in failure print (finding 3).
- **Minor cleanup**: Extract `_POST_EDIT_TEST_TIMEOUT` constant or env var (finding 4).
- **Follow-up PR**: Add `test_hook_runner_builtins.py` behavior tests for `_post_edit_test` (finding 5).
- **Clarify**: Document whether builtins are repo-root-only to resolve finding 6 ambiguity.