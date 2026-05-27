# Code Review: spec_compiler

> Source: core/spec_compiler.py
> Date: 2026-05-26 01:30
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This changes executable planning behavior: `CompiledSpec.scope` feeds `core/planner.py:214` implementation steps and `core/premortem.py:88` verification commands.

### Findings

1. [High] Negative scope text drops valid file tokens
   - File: `core/spec_compiler.py:129`
   - Code: `if not answer or any(kw in answer for kw in _EXCLUDE):`
   - Issue: The exclusion check runs before token extraction. An answer like `core/utils.py, UI 제외` discards the valid `core/utils.py` token entirely, which can recreate the empty-plan failure this helper is meant to prevent.
   - Suggestion: Extract valid path tokens first. Apply `_EXCLUDE` only when there are no valid tokens.

2. [High] Directory/package scope answers are silently ignored
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t) and not t.startswith("//")]`
   - Issue: Scope answers like `core/providers/`, `tests/`, or `core/*.py` now produce no scope because `_PATH_TOKEN_RE` requires a known file extension and disallows globs. Downstream, `build_plan()` creates implementation steps only from `spec.scope`.
   - Suggestion: Support safe repo-relative directories/globs separately, or fall back to a validated path-like answer when no file token exists.

3. [Medium] Windows-style paths bypass downstream AF detectors
   - File: `core/spec_compiler.py:18`
   - Code: `_PATH_TOKEN_RE = re.compile(r'[\w.\-/\\]+\.(?:py|json|js|ts|md|yaml|yml|txt|sh|toml|cfg|ini)')`
   - Issue: This emits values like `core\utils.py`, but downstream checks use forward-slash regexes such as `core/premortem.py:62` and `core/planner.py:164`. Blueprint sync and packaging/verification logic can be skipped.
   - Suggestion: Normalize extracted tokens with `replace("\\", "/")` before returning scope.

4. [Medium] Out-of-workspace path tokens are admitted
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t) and not t.startswith("//")]`
   - Issue: Tokens such as `../outside.py` or `/tmp/outside.py` pass and flow into planner targets and premortem command text.
   - Suggestion: Reject absolute paths and `..` segments; store only normalized repo-relative paths.

### Comparison with Known Issues

- This addresses the slash false positive pattern, e.g. `(int/float)` no longer becomes scope.
- It introduces an adjacent F-PLAN-EMPTY risk for directory/glob scope answers.
- It repeats the known AF path-handling and scope-trust risks: user/interview-derived scope later becomes planner artifacts and verification command text.
- `af.spec` is not a concern here; `core.spec_compiler` is already listed.

### Positive Observations

- URL-like matches are now filtered in clarification-log extraction with `not t.startswith("//")`.
- Added tests cover the `(int/float)` false positive and normal file-token extraction.

Verification: `python -m py_compile core\spec_compiler.py` passed; `python -m pytest tests\test_spec_compiler.py -q` passed, 26 tests.