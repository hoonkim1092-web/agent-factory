# Code Review: registry_manager

> Source: core/registry_manager.py
> Date: 2026-05-15 14:21
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical-severity findings, but two High findings call out that the F12 gate only patches one of the three write paths the prior reviews flagged. Diff is safe under self-run isolation today (PROJECT_ROOT is tempdir), but leaves the "second line of defense" comment overstated. Can merge with documented follow-ups; should not be the final F12 patch.

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] `workflow_apply()` not gated by `AF_DISABLE_REGISTRY_WRITE`
- **Critic**: `core/registry_manager.py:407` writes `WORKFLOW_PATH` directly with no `_env_flag` guard; `core/skill_procurer.py` calls it post-build, so ad-hoc self-run still mutates the global `workflow_registry.yaml`.
- **Cross**: not flagged.
- **Judgment**: Strong code evidence and a prior review (`docs/reviews/2026-05-15-140019-registry_manager-code-review.md` Finding #2) already named this gap. The new docstring promises "second line of defense" but the workflow write path is untouched.
- **Action Required**: Add `if _env_flag("AF_DISABLE_REGISTRY_WRITE"): return` at the top of `workflow_apply()` and update the `_write_registry` docstring to enumerate workflow coverage.

#### 2. [ACCEPT] [High] `_update_registry_status` early return still over-broad (PROJECT_SKILLS_DIR collateral)
- **Critic**: `core/skill_preflight.py:265-267` early-returns on the flag, but `candidates = [SKILLS_DIR, PROJECT_SKILLS_DIR]`. Under self-run, `PROJECT_SKILLS_DIR` is inside the isolated tempdir and is safe to write — the early return suppresses legitimate project-local preflight updates.
- **Cross**: not flagged.
- **Judgment**: Truthy parsing was fixed but the scope bug from the prior review's Finding #1 remains. The diff swapped operators without changing the loop.
- **Action Required**: Filter `candidates` to drop only entries that equal `SKILLS_DIR`, OR rename the env to `AF_DISABLE_GLOBAL_REGISTRY_WRITE` for accuracy.

#### 3. [ACCEPT] [Medium] Docstring overstates the gate's coverage
- **Critic**: `core/registry_manager.py:47-50` says "모든 registry write skip", but `ensure_registry_files()` (`registry_manager.py:25-26`) and `_install_skill_file()` (`:236`) still write the registry skeleton and copy skill files without consulting the flag.
- **Cross**: not flagged.
- **Judgment**: True per the diff. Future readers will assume "no I/O occurs when flag set"; safer to scope the comment than to broaden the gate now.
- **Action Required**: Narrow the comment to: "registry.yaml mutation via `_write_registry()` is skipped — `ensure_registry_files()` and `_install_skill_file()` file copies still occur."

#### 4. [ACCEPT] [Medium] Private-symbol import couples two modules to `core.file_io` internals
- **Critic**: `from core.file_io import _env_flag` at `core/registry_manager.py:15` and `core/skill_preflight.py:29` reaches into a leading-underscore name; two prior cross-reviews recommended a public `env_flag()` helper.
- **Cross**: not flagged (and Cross #2 correctly notes `af.spec` already covers `core.file_io`, so packaging is not the issue — convention is).
- **Judgment**: Cheap fix, prevents a refactor of `core/file_io` from breaking unrelated callers. Aligned with documented prior recommendation.
- **Action Required**: Rename to `env_flag` in `core/file_io.py`, re-export from `core/utils.py`, update two import sites.

#### 5. [HOLD] [Medium] Lock ↔ registry skew when gate fires
- **Critic**: `register_built()` / `_install_skill_file()` call `_write_registry()` (now no-ops under the flag) followed unconditionally by `lock_skill_state(...)`. Today blast radius is contained because `SKILL_LOCK_PATH` lives inside the isolated PROJECT_ROOT, but it's an undocumented invariant.
- **Cross**: not flagged.
- **Judgment**: Real concern but not actionable without confirming the intended contract — is the flag scoped exclusively to "use with isolated PROJECT_ROOT," or should it also gate locks? Carry-over HOLD from prior review.
- **Question for Author**: Should `AF_DISABLE_REGISTRY_WRITE` also skip `lock_skill_state`, or is the "isolated PROJECT_ROOT only" pairing the intended invariant? Pick (a) document it, or (b) make `_write_registry` return bool and short-circuit lock writes.

#### 6. [ACCEPT] [Medium] Missing direct regression test for truthy/falsy parsing
- **Critic**: not flagged.
- **Cross**: Tests cover that the launcher sets `"1"` (`tests/test_agent_launcher_cli_dispatch.py:111`) and that init is read-only (`tests/test_registry_manager_codex_skills.py:98`), but no test asserts `_write_registry()` skips on `"1"` and proceeds on `"0"`/`"false"`.
- **Judgment**: The whole purpose of this diff is the truthy fix; a regression test pins it.
- **Action Required**: Add a test pair: `AF_DISABLE_REGISTRY_WRITE=1` → `registry.yaml` unchanged; `AF_DISABLE_REGISTRY_WRITE=0` → write proceeds.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `workflow_apply()` ungated | High | ACCEPT | Critic |
| 2 | `_update_registry_status` scope over-broad | High | ACCEPT | Critic |
| 3 | Docstring overstates coverage | Medium | ACCEPT | Critic |
| 4 | `_env_flag` private import | Medium | ACCEPT | Critic |
| 5 | Lock/registry skew invariant | Medium | HOLD | Critic |
| 6 | Missing truthy/falsy regression test | Medium | ACCEPT | Cross |

### Recommendations

- Gate `workflow_apply()` (Finding #1) and split the preflight `candidates` filter (Finding #2) before this is considered the final F12 patch — both were already itemized in `docs/reviews/2026-05-15-140019-registry_manager-code-review.md` and the diff skipped them.
- Tighten the new docstring to enumerate exactly which write paths are gated (Finding #3).
- Promote `_env_flag` to a public `env_flag()` helper in `core/utils.py` (Finding #4) — small change, fixes both call sites.
- Add the truthy/falsy regression test on `_write_registry` (Finding #6).
- Decide and document the lock-write invariant (Finding #5): either document the "only safe with isolated PROJECT_ROOT" pairing, or gate `lock_skill_state` when `_write_registry` is suppressed.