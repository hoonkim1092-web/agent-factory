# Code Review: registry_manager

> Source: core/registry_manager.py
> Date: 2026-05-15 14:22
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

Verified. The Critic's BLOCK findings are factually accurate:
- `workflow_apply()` at line 397-407 writes to `WORKFLOW_PATH` (global SKILLS_DIR-anchored) with no flag check.
- `_install_skill_file()` at lines 205-236 copies files and writes `meta.yaml` to global `SKILLS_DIR` before `_write_registry()` runs.
- Prior accepted review (140019) explicitly listed `workflow_apply()` guard as "머지 전 필수".

But these are pre-existing leaks, not regressions introduced by this diff — the diff strictly improves on the prior state (truthy-parse fix is correct). The Critic's BLOCK is really about scope/comment-accuracy, not a Critical regression.

## Final Code Review

### Verdict: WARN

Both reviewers confirm the truthy-parse fix at `core/registry_manager.py:51` is correct (whitelist semantics now match `core/file_io.py:22-26`). However, the Critic identified two pre-existing global-write paths (`workflow_apply`, `_install_skill_file`) that the new comment ("모든 registry write skip") overclaims to cover, and a prior cross-review (`docs/reviews/2026-05-15-140019-...md`) had already ACCEPTed those guards as "머지 전 필수". This is a scope/documentation accuracy issue, not a regression — merge with documented follow-ups.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `workflow_apply()` bypasses `AF_DISABLE_REGISTRY_WRITE` — prior-accepted finding not implemented
- **Critic**: `workflow_apply()` at line 396-407 still calls `write_yaml(WORKFLOW_PATH, wf)` directly. `WORKFLOW_PATH = os.path.join(SKILLS_DIR, "workflow_registry.yaml")` and `SKILLS_DIR = os.path.join(BASE_DIR, "skills")` (config_paths.py:43) — repo-root anchored, NOT redirected by `AGENT_PROJECT_ROOT`. Under `AF_DISABLE_REGISTRY_WRITE=1`, a self-run that builds any skill still mutates the global workflow file via `skill_procurer.py:1150 → registry.workflow_apply(built_metas)`.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Verified at `core/registry_manager.py:396-407` and `core/config_paths.py:43`. Prior cross-review (`docs/reviews/2026-05-15-140019-...md` Finding #2) explicitly ACCEPTed this as "머지 전 필수" with the exact suggested fix. This diff does not honor that accept.
- **Action Required**: Add early-return at top of `workflow_apply()`:
  ```python
  if _env_flag("AF_DISABLE_REGISTRY_WRITE"):
      logger.debug("workflow_apply skipped (AF_DISABLE_REGISTRY_WRITE set)")
      return
  ```

#### 2. [ACCEPT] [High] `_install_skill_file()` mutates global SKILLS_DIR before flag check
- **Critic**: At lines 205-236, `shutil.copytree(src, target_dir, ...)` and `write_yaml(target_meta, meta)` run unconditionally against `SKILLS_DIR/<sid>/...`. Only the subsequent `self._write_registry(reg)` at line 244 honors the flag — by then the global skill tree is already mutated.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Verified at `core/registry_manager.py:205-244`. Same architectural class as Finding #1: `SKILLS_DIR` is BASE_DIR-anchored, env flag is the only line of defense, and it fires too late.
- **Action Required**: Gate `_install_skill_file` entry on the flag (return `(False, "registry_write_disabled")`), OR re-anchor `SKILLS_DIR`/`WORKFLOW_PATH` resolution to honor isolated root for self-runs. One-line guard is the smaller change.

#### 3. [ACCEPT] [Medium] Comment overclaims scope — "모든 registry write skip" is false
- **Critic**: The new comment at lines 47-50 claims "모든 registry write skip", but only `_write_registry()` is gated. Readers will assume isolation is airtight and miss the unguarded paths in Findings #1/#2.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Code evidence is direct — comment vs. behavior mismatch is plain reading. Either fix the comment to match scope, OR fix the code to match the comment (preferred, by implementing #1+#2).
- **Action Required**: Tied to #1/#2 resolution. If guards are added, comment is accurate. If not, narrow comment to "이 메서드의 registry.yaml 쓰기만 skip — workflow_apply / _install_skill_file 별도 가드 필요".

#### 4. [ACCEPT] [Low] Missing direct regression test for `_write_registry` env-flag semantics
- **Critic**: Existing tests assert `== "1"` or absence only. A future revert to `os.environ.get(...)` would not be caught by current suite. Suggests parametric test against `_write_registry` with `""`, `"0"`, `"false"`, `"no"`, `"1"`, `"true"`, `"yes"`, `"on"`.
- **Cross**: ACCEPT — "no test directly verifies `_write_registry()` behavior for '1', '0', and 'false'." Suggests test in `tests/test_registry_manager_codex_skills.py` monkeypatching `REGISTRY_PATH`.
- **Judgment**: ACCEPT. Both reviewers independently flagged the same gap with the same fix shape. Per CLAUDE.md "파이프라인 배포 동등성 규칙", the assertion belongs at the production caller boundary (`_write_registry`), not just at the env-var setter (`agent_launcher.py`).
- **Action Required**: Add ~15-line parametric test in `tests/test_registry_manager_codex_skills.py`: monkeypatch `REGISTRY_PATH` to tempdir, parametrize over `_env_flag` truth table, assert write-vs-skip matches whitelist.

#### 5. [HOLD] [Medium] Private symbol `_env_flag` imported across modules
- **Critic**: PEP 8 violation; two divergent `_env_flag` definitions exist (`core/file_io.py` whitelist vs `core/implementation_language_policy.py` blacklist) — return opposite booleans for `AF_DISABLE_REGISTRY_WRITE=maybe`. Prior review (140019 Finding #1) recommended public helper in `core/utils.py`.
- **Cross**: REJECT — verified no circular import; tests pass.
- **Judgment**: Cross addressed the wrong concern (circular import) and missed the Critic's actual concern (helper fork + PEP 8). The two `_env_flag` definitions DO have divergent semantics — that's a latent bug surface. But consolidation is a follow-up refactor, not a blocker for this diff. HOLD pending a separate utility-consolidation PR.
- **Question for Author**: Is helper consolidation (promote to `core/utils.py:env_flag`) tracked as a follow-up? If so, this can be downgraded to a tracking item; if not, file it now.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `workflow_apply()` unguarded | High | ACCEPT | Critic |
| 2 | `_install_skill_file()` mutates global SKILLS_DIR before flag check | High | ACCEPT | Critic |
| 3 | Comment overclaims "모든 registry write skip" | Medium | ACCEPT | Critic |
| 4 | Missing `_write_registry` env-flag regression test | Low | ACCEPT | Both |
| 5 | Private `_env_flag` import + helper fork | Medium | HOLD | Critic |

### Recommendations

1. **This PR (truthy-parse fix) — merge with comment correction**: The diff itself is correct and improves over the prior state. To unblock merge without expanding scope, narrow the comment at lines 47-50 to accurately describe what this method gates (only `_write_registry`'s `registry.yaml` write).
2. **Immediate follow-up PR (Findings #1 + #2)**: Add `_env_flag` guard at top of `workflow_apply()` (1 line) and at top of `_install_skill_file()` (1 line + return shape). These were already ACCEPTed in `docs/reviews/2026-05-15-140019-...md` as "머지 전 필수" — landing them now completes the F12 architectural isolation the comment promises.
3. **Test addition (Finding #4)**: Parametric test in `tests/test_registry_manager_codex_skills.py` covering `_env_flag` truth table against `_write_registry`. Both reviewers independently asked for this.
4. **Tracking item (Finding #5)**: Promote `_env_flag` → `core/utils.py:env_flag` (public), update both callsites in `registry_manager.py` and `skill_preflight.py`, delete the diverging `implementation_language_policy.py` private duplicate. Separate refactor PR.

**Net assessment**: The Critic correctly identified that the F12 isolation guarantee the comment claims is not actually achieved — but those gaps are pre-existing (not regressions in this diff). WARN, not BLOCK, because (a) this diff strictly improves the prior state, (b) the high-severity findings are scope/doc-accuracy issues fixable in tight follow-up, and (c) all named gaps already have ACCEPT consensus in a prior cross-review awaiting implementation.