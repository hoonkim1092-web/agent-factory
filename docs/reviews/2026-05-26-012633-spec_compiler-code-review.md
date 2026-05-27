# Code Review: spec_compiler

> Source: core/spec_compiler.py
> Date: 2026-05-26 01:26
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change affects planning/spec behavior and downstream verification commands.

### Findings

1. [High] Negative scope text drops valid file tokens
   - File: `core/spec_compiler.py:129`
   - Code: `if not answer or any(kw in answer for kw in _EXCLUDE): continue`
   - Issue: The exclusion check runs before token extraction. A valid answer like `core/utils.py, UI는 불필요` will discard `core/utils.py` entirely because the whole answer contains an exclusion keyword. That can recreate the empty-plan failure this helper is meant to prevent.
   - Suggestion: Extract path tokens first, then ignore exclusion keywords only when no valid tokens are present.

2. [High] Directory/package scope answers are now silently ignored
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t)]`
   - Issue: The old behavior accepted path-like scope answers such as `core/providers/` or `core/providers/*.py`. The new regex only accepts known file extensions, so directory/package scope answers produce no `spec.scope`, causing planner implementation steps to disappear.
   - Suggestion: Support directory/package scope explicitly, or fall back to the full path-like answer when no file token exists but the answer is a safe repo-relative path.

3. [Medium] Windows backslash paths are extracted but downstream AF detectors miss them
   - File: `core/spec_compiler.py:18`
   - Code: `_PATH_TOKEN_RE = re.compile(r'[\w.\-/\\]+\.(?:py|json|js|ts|md|yaml|yml|txt|sh|toml|cfg|ini)')`
   - Issue: This emits values like `core\utils.py`, but downstream premortem uses forward-slash-only matching: `core/premortem.py:62` has `_CORE_PY_RE = re.compile(r"\bcore/\S+\.py\b")`, and planner only appends `Master_Blueprint.md` for `core/[^/]+\.py$`. On Windows-style input, blueprint sync and packaging risks can be skipped.
   - Suggestion: Normalize extracted tokens with `replace("\\", "/")` before returning them.

4. [Medium] Scope extraction still permits out-of-workspace path tokens
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t)]`
   - Issue: Tokens such as `../outside.py` or `/tmp/outside.py` satisfy the regex. These flow into planner targets and premortem commands, including `core/premortem.py:88`: `command=f"python -m py_compile {targets}"`. Even if commands are later reviewed, the compiled plan can point outside the AF workspace.
   - Suggestion: Require normalized, repo-relative paths and reject absolute paths or `..` segments.

### Comparison with Known Issues

- `af.spec` hiddenimport risk is not present here: `af.spec` already includes `core.spec_compiler`.
- The change repeats the AF-specific Windows/Unix path handling risk: backslash paths are accepted without normalizing for downstream regex consumers.
- It also touches command-bearing planning data, adjacent to the known subprocess/shell safety pattern, because scope values become verification command text later.

### Positive Observations

- The new token extraction fixes the prior false positive where descriptive answers containing `/`, such as `(int/float)`, could become planner scope.
- `tests/test_spec_compiler.py` covers explicit scope priority, clarification-log fallback, URL exclusion, and JSON extension extraction.

Verification run: `python -m py_compile core\spec_compiler.py` passed, and `python -m pytest tests\test_spec_compiler.py -q` passed with 24 tests.