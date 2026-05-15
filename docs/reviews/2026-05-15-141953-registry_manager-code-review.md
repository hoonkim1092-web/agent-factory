# Code Review: registry_manager

> Source: core/registry_manager.py
> Date: 2026-05-15 14:19
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Four Medium findings around the same theme — the new `AF_DISABLE_REGISTRY_WRITE` gate is incomplete and leaks partial-write footprints. No Critical, so merge-with-fix is acceptable.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] `workflow_apply()` writes WORKFLOW_PATH unconditionally
- **Critic**: Gate covers only `_write_registry`; `workflow_apply()` still does `write_yaml(WORKFLOW_PATH, wf)` at `core/registry_manager.py:396-407`.
- **Cross**: not flagged
- **Judgment**: Diff confirms gate is scoped to `_write_registry` only. The stated intent — "second line of defense" for ad-hoc self-run — fails as soon as `workflow_apply()` runs.
- **Action Required**: Add `if _env_flag("AF_DISABLE_REGISTRY_WRITE"): return` at the head of `workflow_apply()` with parity `logger.debug`.

#### 2. [ACCEPT] [Medium] `_install_skill_file` / `_eval_and_promote_external` leave partial on-disk footprint
- **Critic**: `shutil.copytree(src, target_dir)` + `write_yaml(target_meta, meta)` run before the (now-gated) `_write_registry`. Self-run leaves `SKILLS_DIR/<sid>/meta.yaml` with no registry entry.
- **Cross**: not flagged
- **Judgment**: Strong code evidence in `core/registry_manager.py:205-244` and :298. Same "gate one of several writes" pattern as code-review.md §3.3 M10.
- **Action Required**: Early-return at top of `_install_skill_file` and `_eval_and_promote_external` when flag is set, OR add an invariant test pinning "no skill dirs created during self-run".

#### 3. [ACCEPT] [Medium] `ensure_registry_files()` bypasses the gate
- **Critic**: not flagged
- **Cross**: `RegistryManager.__init__()` calls `ensure_registry_files()` (writes `REGISTRY_PATH` via raw `write_yaml`) before any `_write_registry` is reached.
- **Judgment**: Verified — when `REGISTRY_PATH` is missing, instantiation alone creates the file, defeating self-run isolation at construction time.
- **Action Required**: Early-return in `ensure_registry_files()` when `_env_flag("AF_DISABLE_REGISTRY_WRITE")` is true; add a test setting the env var with a missing `REGISTRY_PATH` and asserting no file creation.

#### 4. [ACCEPT] [Medium] Missing regression test for `_env_flag` truthy/falsy contract
- **Critic**: No test exercises `("0", False), ("false", False), ("1", True), ("yes", True), ("", False)` against `_write_registry`. The previous 14:00:19 review's Action Required explicitly asked for this and it landed unaddressed.
- **Cross**: not flagged (Cross verified behavior manually via `_env_flag` source, but no regression test was added)
- **Judgment**: The bug that motivated the entire change — `"0"`/`"false"` being truthy — has no test guarding it. Without it, future refactors of `_env_flag` will silently regress.
- **Action Required**: Parametrized test in `tests/test_agent_launcher_cli_dispatch.py` (or sibling) monkeypatching `write_yaml` and asserting call count per env-var value.

#### 5. [REJECT] [Low] Cross-module import of `_env_flag` (underscore name)
- **Critic**: `from core.file_io import _env_flag` crosses an "internal" boundary; suggested promoting to public `env_flag` or importing via `core.utils` re-export.
- **Cross**: REJECT — `core/approval_gate.py:21` already imports `_env_flag` from `core.file_io`; this is established project pattern.
- **Judgment**: Cross's rebuttal is grounded in concrete prior usage. The new import aligns with established convention rather than violating it. A future public-rename refactor is a separate concern, not a blocker on this change.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `workflow_apply()` ungated | Medium | ACCEPT | Critic |
| 2 | `_install_skill_file` partial footprint | Medium | ACCEPT | Critic |
| 3 | `ensure_registry_files()` ungated | Medium | ACCEPT | Cross |
| 4 | `_env_flag` regression test missing | Medium | ACCEPT | Critic |
| 5 | Underscore-prefixed import | Low | REJECT | Critic (Cross rebutted) |

### Recommendations
- Extend the `_env_flag("AF_DISABLE_REGISTRY_WRITE")` gate to **all** write sites in `core/registry_manager.py`: `ensure_registry_files()`, `workflow_apply()`, `_install_skill_file()`, `_eval_and_promote_external()`. Add `logger.debug` parity at each.
- Add one parametrized regression test pinning `_env_flag` truthy/falsy contract (this was the original 14:00:19 Action Required item still unmet).
- Add one invariant test: env var set + missing `REGISTRY_PATH` + missing `SKILLS_DIR/<sid>` → no files created after `RegistryManager()` construction and a no-op `_install_skill_file()` call.
- Skip the underscore-import rename — established pattern, not a blocker.