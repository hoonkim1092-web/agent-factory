# Code Review: skill_preflight

> Source: core/skill_preflight.py
> Date: 2026-05-15 14:24
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff is a correct, narrow consistency fix (string-truthy → `_env_flag` + parity logging with `registry_manager.py:51`). No regressions introduced. However, the docstring's "**모든** registry write / second line of defense" framing overpromises — `workflow_apply()` and adjacent write paths in `core/registry_manager.py` remain ungated (5 prior cross-reviews flagged this; still unfixed). Mergeable as incremental; **do not tag as the final F12 patch**.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `workflow_apply()` still bypasses `AF_DISABLE_REGISTRY_WRITE`
- **Critic**: Finding #1 — `core/registry_manager.py:407` `write_yaml(WORKFLOW_PATH, wf)` has no `_env_flag` guard; `skill_procurer.py:1150` invokes it on every build; 5 prior cross-reviews flagged the same.
- **Cross**: not flagged in this round (Cross focused on the diff boundary; this is a codebase-wide gap).
- **Judgment**: Pre-existing High. Diff does not regress it, but the new docstring ("모든 registry write") asserts a property the codebase does not have. Strong evidence: 5 prior ACCEPT-High reviews cited by path.
- **Action Required**: Either (a) add `if _env_flag("AF_DISABLE_REGISTRY_WRITE"): return` at `core/registry_manager.py:397` (function entry of `workflow_apply`), or (b) narrow the docstring (see Finding #4) and file a follow-up task. Pick one before tagging this as the F12 closure.

#### 2. [ACCEPT] [Low] No verbose-mode (`-v`) confirmation when skip path fires
- **Critic**: Finding #5 — only `logger.debug(...)` fires; `-v` doesn't enable debug logging.
- **Cross**: Finding #1 — `run_factory_cli.py:104` wires `verbose=...` into `PreflightEvaluator` but does not configure debug logging; users see no signal.
- **Judgment**: Both reviewers agree, with concrete trace through the CLI. The skip branch (`core/skill_preflight.py:265-267`) returns before the existing `if self.verbose: print(...)` lines at L311/L315/L319.
- **Action Required**: Add before the `return` at `core/skill_preflight.py:267`:
  ```python
  if self.verbose:
      print(f"[Preflight] Registry write skipped (AF_DISABLE_REGISTRY_WRITE set): {result.skill_id}")
  ```

#### 3. [ACCEPT] [Medium] Test coverage gap at the changed boundary
- **Critic**: not flagged.
- **Cross**: Finding #2 — `tests/test_agent_launcher_cli_dispatch.py:148-169` only exercises `_env_flag` itself; `tests/test_phase5_context_fork_preflight.py:144-284` calls `evaluate()` which never enters `_update_registry_status()`. The flag's effect on the actual write path is untested.
- **Judgment**: Single source, but evidence is concrete (specific test files and line ranges). The diff changes a write-suppression contract without a behavioral test.
- **Action Required**: Add a test that monkeypatches `core.config_paths.SKILLS_DIR` / `PROJECT_SKILLS_DIR` to a tmp dir, runs `_update_registry_status()` (or `evaluate_and_gate()`) with `AF_DISABLE_REGISTRY_WRITE=1` and asserts the registry file is untouched; repeat with unset/`=0` to assert the write does occur.

#### 4. [ACCEPT] [Medium] Docstring "모든 registry write" overpromises
- **Critic**: Finding #4 — bolded "**모든**" + "second line of defense" primes readers to assume codebase-wide coverage; Finding #1 shows that's false.
- **Cross**: not flagged.
- **Judgment**: Single source but evidence is direct from the diff text (`core/skill_preflight.py:259-263`). Tied to Finding #1 — either fix the gap or scope the claim. Within `_update_registry_status` alone the claim is structurally accurate (early-return precedes the candidates loop).
- **Action Required**: Rewrite docstring to "이 함수가 시도하는 모든 registry write 경로" / "all registry writes attempted by this function". Drop "second line of defense" unless Finding #1 is also fixed in this commit.

#### 5. [ACCEPT] [Medium] Cross-module import of private `_env_flag` — convention drift
- **Critic**: Finding #3 — `from core.file_io import _env_flag` already used in 5 sites; `core/implementation_language_policy.py` has its own `_env_flag` with **opposite** semantics (blacklist vs. whitelist), creating a future import-by-name footgun. Flagged in 3 prior cross-reviews.
- **Cross**: not flagged.
- **Judgment**: Single source but recurring pattern (3 prior ACCEPT findings). Diff repeats the convention drift rather than introducing it.
- **Action Required**: Out of scope for this hotfix. File follow-up: promote `core/file_io.py:_env_flag` → public `env_flag` (keep underscore alias one release), then collapse the divergent definition in `implementation_language_policy.py`.

#### — [REJECT] Behavior change for falsy strings (e.g. `"0"`, `"false"`)
- **Critic**: Finding #2 — `=0` previously skipped writes (any non-empty string was truthy); now lets writes through. Recommended commit-message callout + consumer sweep.
- **Cross**: Finding #3 (REJECT) — `core/file_io.py:22` whitelist is intentional; tests at `test_agent_launcher_cli_dispatch.py:148-169` cover truthy/falsy/unset; sole internal setter (`agent_launcher.py:54`) uses `"1"`. Tests pass (47/0).
- **Judgment**: Reviewers contradict. Reading the diff: the change is strictly correctness-improving (the old contract was "any non-empty string is truthy", a bug-prone convention). Critic's correctness concern is REJECTED; Critic's secondary recommendation (commit-message callout + grep sweep for external `=0` consumers) is reasonable hygiene but not a finding worth blocking on. Demoted to a recommendation.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `workflow_apply()` bypasses gate | High | ACCEPT | Critic |
| 2 | Verbose mode silent on skip | Low | ACCEPT | Both |
| 3 | Test gap at preflight boundary | Medium | ACCEPT | Cross |
| 4 | Docstring overpromises coverage | Medium | ACCEPT | Critic |
| 5 | Private `_env_flag` import drift | Medium | ACCEPT | Critic |
| — | Falsy-string semantic change | — | REJECT | Critic (rebutted by Cross) |

### Recommendations

1. **Required before tagging F12-final**: Pick one — either gate `core/registry_manager.py:workflow_apply()` (L397) with `_env_flag("AF_DISABLE_REGISTRY_WRITE")`, **or** narrow the docstring at `core/skill_preflight.py:259-263` to "this function's write attempts" and drop "second line of defense" (Findings #1 + #4 are tied).
2. **Mergeable in this PR**: Add the verbose-mode `print` at `core/skill_preflight.py:266` (Finding #2).
3. **Mergeable in this PR**: Add a behavioral test for `_update_registry_status()` / `evaluate_and_gate()` under `AF_DISABLE_REGISTRY_WRITE=1` with monkeypatched `SKILLS_DIR` (Finding #3).
4. **Commit-message hygiene**: Note the env-var contract tightening (`=0` no longer suppresses writes) and grep `scripts/`, `.githooks/`, env templates to confirm no consumer relies on the old behavior.
5. **Follow-up task** (out of scope): Promote `_env_flag` → public `env_flag` and unify with `core/implementation_language_policy.py`'s divergent definition (Finding #5).