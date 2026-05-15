# Code Review: skill_preflight

> Source: core/skill_preflight.py
> Date: 2026-05-15 14:25
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff is a narrow, correct improvement: it replaces a brittle `os.environ.get(...)` truthy check with the project's canonical `_env_flag()` whitelist helper and adds parity logging matching `core/registry_manager.py:_write_registry`. No Critical issues found. Two Medium findings (one from each reviewer) and two Lower-severity items deserve attention but do not block merge.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] Docstring "모든 registry write" overstates the gate's reach
- **Critic**: Docstring at L259-263 claims "모든 registry write 를 skip" but only this function's two candidate paths are gated; `workflow_apply()` (registry_manager.py:396) and `_install_skill_file()` (registry_manager.py:205-244) still write to global SKILLS_DIR before the gate. Prior reviews (140019, 141953, 142105, 142202) flagged these as merge-blocking leak surfaces.
- **Cross**: not flagged
- **Judgment**: Diff evidence confirms — the gate's `if _env_flag(...)` early-return is local to `_update_registry_status`. The docstring claim is technically true only within this function's scope but is misleading at the F12 architectural surface.
- **Action Required**: Either tighten docstring to `"이 함수의 양쪽 registry.yaml write 를 skip 한다 (workflow_apply / _install_skill_file 의 글로벌 경로는 별도 가드 필요)"`, OR extend the gate to those two call sites in the same diff.

#### 2. [ACCEPT] [Medium] Non-atomic registry write remains a corruption risk
- **Critic**: not flagged
- **Cross**: `_update_registry_status()` opens `registry.yaml` with `"w"` and writes YAML directly — interruption mid-write yields partial/corrupt files. CLI default path (`run_factory_cli.py:106-108` → `evaluate_and_gate(..., auto_promote=not args.no_promote)`) reaches this write. Code review §C2/M10 already flags this class of bug.
- **Judgment**: Evidence is strong (file path + CLI routing cited). Independent of this diff's scope (env-flag fix), but the write path being touched is the same line region — fair to surface now.
- **Action Required**: Write to `tmp_path` in the same directory, then `os.replace(tmp_path, registry_path)`. Optional: wrap read-modify-write with project file-lock helper for concurrent preflight runs.

#### 3. [ACCEPT] [Medium] Cross-module import of private `_env_flag` + duplicate divergent definitions
- **Critic**: `_env_flag` is PEP 8 private (leading underscore) but imported by `core/registry_manager.py:15` and `core/skill_preflight.py:29`. A second, semantically opposite definition exists at `core/implementation_language_policy.py:8` (blacklist vs whitelist). For `AF_DISABLE_REGISTRY_WRITE=0`, whitelist returns False (proceed) vs blacklist would return True (skip) — silent gate inversion if the wrong one is imported.
- **Cross**: not flagged
- **Judgment**: Critic provides concrete divergence evidence and a realistic future-import hazard. Severity Medium is appropriate (current diff is correct; risk is forward-looking).
- **Action Required**: Follow-up commit (not blocker on this diff) — promote `env_flag()` (whitelist) to `core/utils.py`; have `file_io.py` and `implementation_language_policy.py` call it. Matches existing convention at `approval_gate.py:279`, `review_gate.py:176`, `dynamic_orchestrator.py:844`.

#### 4. [ACCEPT] [Medium] Silent `except Exception` in `_update_registry_status` now visibly inconsistent with new logger
- **Critic**: Pre-existing `except Exception as e: if self.verbose: print(...)` at L317-319 swallows YAML I/O / import errors in non-verbose mode. The new `logger.debug(...)` line at L266 makes the success-path observable while failures stay silent — inconsistency newly exposed by this diff.
- **Cross**: not flagged
- **Judgment**: Pre-existing, but the diff introduces the logger that makes the asymmetry obvious. Critic explicitly notes "not introduced by this diff."
- **Action Required**: Replace bare `print` with `logger.warning("registry update failed for %s: %s", result.skill_id, e, exc_info=True)`. Narrowing `except Exception` is a separate follow-up.

#### 5. [ACCEPT] [Low] No regression test for the env-flag gate
- **Critic**: Multiple prior reviews requested parametrized test for `AF_DISABLE_REGISTRY_WRITE ∈ {"1","0","false",unset}`. Without it, a future refactor can silently regress to the old truthy semantics — exactly the F12 bug.
- **Cross**: not flagged (verification confirmed `py_compile` + 50 pytest passed, but no new test added for this gate)
- **Judgment**: Test gap is real and well-justified by the F12 history. Low severity since current behavior is correct.
- **Action Required**: Add `tests/test_skill_preflight_registry_gate.py` with `monkeypatch.setenv` + tmpdir registry fixture; three cases (`"1"` → no write, `"0"` → write, unset → write).

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Docstring overstates gate reach | Medium | ACCEPT | Critic |
| 2 | Non-atomic registry write | Medium | ACCEPT | Cross |
| 3 | Cross-module private import + duplicate divergent defs | Medium | ACCEPT | Critic |
| 4 | Silent except now inconsistent with logger | Medium | ACCEPT | Critic |
| 5 | No regression test for gate | Low | ACCEPT | Critic |

### Recommendations

- **Must-do this diff (or follow-up commit before next preflight refactor)**:
  1. Tighten docstring at `core/skill_preflight.py:259-263` to scope the "모든" claim accurately, OR extend the gate to `workflow_apply()` / `_install_skill_file()`.
  2. Add atomic-write pattern (`tmp + os.replace`) to `_update_registry_status` at `core/skill_preflight.py:301`.
- **Follow-up commits (separate PRs OK)**:
  3. Promote `env_flag()` to `core/utils.py` and de-duplicate the two private definitions.
  4. Convert silent `except Exception → print` at L317-319 to `logger.warning(..., exc_info=True)`.
  5. Add parametrized regression test for `AF_DISABLE_REGISTRY_WRITE` truthy/falsy/unset cases.
- **Positive notes preserved**: correct selection of whitelist `_env_flag` over blacklist variant (gate-inversion bug avoided); logger.debug at L266 structurally matches `registry_manager.py:52` (single grep target for F12 surface).