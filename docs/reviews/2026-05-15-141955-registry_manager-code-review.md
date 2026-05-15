# Code Review: registry_manager

> Source: core/registry_manager.py
> Date: 2026-05-15 14:19
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: PASS

The core fix (`_env_flag` substitution at `core/registry_manager.py:51`) is correct and aligned with the AF canonical pattern (`core/approval_gate.py:43`, `core/skill_preflight.py:260-261`). Both reviewers agree the diff resolves the prior-round HIGH truthy-string bug. Remaining findings are test-coverage and hygiene items — no blockers.

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Low] Missing end-to-end regression for `_write_registry` gate
- **Critic**: "_env_flag unit coverage only, no _write_registry end-to-end assertion … future refactor that drops the import or inverts the condition would still pass the unit suite"
- **Cross**: "no direct test proving RegistryManager._write_registry() now treats '0'/'false' as disabled and '1' as write-blocking"
- **Judgment**: Both reviewers independently flagged the same gap. Per CLAUDE.md "파이프라인 배포 동등성 규칙", the assertion belongs at the production caller boundary (`RegistryManager._write_registry`), not just the helper.
- **Action Required**: Add a test in `tests/test_registry_manager_codex_skills.py` that constructs `RegistryManager()` with `AF_DISABLE_REGISTRY_WRITE=1`/`0`/`false`, calls `_write_registry({...})`, and asserts the file is/isn't written.

#### 2. [ACCEPT] [Low] Diff scope partial — verify paired commit includes `core/skill_preflight.py`
- **Critic**: "diff you posted only changes `core/registry_manager.py`, but the second registry-write path (`PreflightEvaluator._update_registry_status`) carries the same truthy bug … if the commit lands with only registry_manager.py, parity is broken"
- **Cross**: not flagged
- **Judgment**: Only Critic flagged, but evidence is strong — `git diff HEAD` shows both files modified, and the L47-50 docstring explicitly advertises the pairing. Posted diff is partial.
- **Action Required**: Confirm `core/skill_preflight.py:265` is staged in the same commit. If split, land them together.

#### 3. [ACCEPT] [Low] Test env-var hygiene — use `monkeypatch.setenv`
- **Critic**: "Two of the three new tests bypass pytest's monkeypatch fixture … inconsistent with the third test in the same class (line 173)"
- **Cross**: not flagged
- **Judgment**: Single-reviewer finding, but evidence is concrete (line numbers + inconsistency within the same test class). Trivial fix, prevents env leak on assertion-then-exception paths.
- **Action Required**: Replace `os.environ[...] = val` / `try/finally` blocks at L156, L165 with `monkeypatch.setenv("AF_DISABLE_REGISTRY_WRITE", truthy_val)`.

### Cross Review Rejections (acknowledged)

- **`_env_flag` private import** — correctly rejected by Cross. `core/skill_preflight.py:260-261` and `core/approval_gate.py:43` already use this exact pattern; it's the local convention.
- **Non-string env values risk** — correctly rejected. `os.environ` values are always strings.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Missing end-to-end `_write_registry` test | Low | ACCEPT | Both |
| 2 | Diff scope partial (skill_preflight.py pairing) | Low | ACCEPT | Critic |
| 3 | Use `monkeypatch.setenv` in 2/3 new tests | Low | ACCEPT | Critic |

### Recommendations

- Add `test_write_registry_skipped_when_disabled` in `tests/test_registry_manager_codex_skills.py` covering `1`/`0`/`false` cases at the `RegistryManager()` boundary.
- Verify `git status` shows both `core/registry_manager.py` and `core/skill_preflight.py` staged before commit.
- Refactor the two new tests at `tests/test_agent_launcher_cli_dispatch.py:153-167` to use `monkeypatch.setenv` for consistency with line 173.
- Optional: consider adding an asymmetry check in `scripts/blast_radius.py` for paired-fix files (`registry_manager.py` ↔ `skill_preflight.py`) — Critic's suggestion, but out of scope for this PR.