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

This changes executable planning behavior by altering how user/interview scope is compiled into `CompiledSpec.scope`.

### Findings

1. [High] Directory and glob scope answers are now dropped, reintroducing empty-plan risk
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t) and not t.startswith("//")]`
   - Issue: Scope answers such as `core/`, `tests/`, or `core/*.py` no longer produce scope because `_PATH_TOKEN_RE` requires a concrete known-extension filename and excludes `*`. That can leave `CompiledSpec.scope` empty, and `build_plan()` creates implementation steps only from `spec.scope` at `core/planner.py:214`.
   - Suggestion: Support validated directory/glob scope tokens separately from descriptive slash text, e.g. allow repo-relative `core/`, `tests/`, `core/*.py` after rejecting type hints/URLs.

2. [High] Extension matching truncates `.tsx` / `.jsx` paths into wrong files
   - File: `core/spec_compiler.py:18`
   - Code: `_PATH_TOKEN_RE = re.compile(r'[\w.\-/\\]+\.(?:py|json|js|ts|md|yaml|yml|txt|sh|toml|cfg|ini)')`
   - Issue: Because `js` and `ts` are accepted without a token boundary, `packages/app/page.tsx` becomes `packages/app/page.ts`, and `.jsx` becomes `.js`. The planner then targets the wrong artifact.
   - Suggestion: Add missing extensions and require a boundary after the extension, e.g. `(?:tsx|jsx|ts|js|...)(?=$|[\s,;:)\\]})])`.

3. [Medium] Windows drive paths are parsed incorrectly
   - File: `core/spec_compiler.py:18`
   - Code: `_PATH_TOKEN_RE = re.compile(r'[\w.\-/\\]+\.(?:py|json|js|ts|md|yaml|yml|txt|sh|toml|cfg|ini)')`
   - Issue: The regex excludes `:`, so `C:\tmp\file.py` is extracted as `\tmp\file.py`. In AF’s Windows-first context this changes the target path and can produce root-relative artifacts instead of the requested file.
   - Suggestion: Normalize with `pathlib`/repo-relative validation instead of regex-only parsing, or explicitly handle drive prefixes while rejecting absolute/out-of-workspace paths.

4. [High] Parent-directory traversal is accepted into executable verification flow
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t) and not t.startswith("//")]`
   - Issue: `../outside.py` is accepted as scope. That flows into premortem verification commands such as `command=f"python -m py_compile {targets}"` at `core/premortem.py:88`, repeating the known `CompiledSpec.scope` trust risk.
   - Suggestion: Reject absolute paths and any path whose normalized repo-relative form escapes the workspace before storing it in `CompiledSpec.scope`.

### Comparison with Known Issues

- The change addresses the known false-positive pattern where descriptive slash text like `(int/float)` became scope.
- It repeats the known `CompiledSpec.scope` trust issue documented in prior reviews: user/interview-derived scope flows into planner artifacts and premortem command strings.
- No `af.spec` hiddenimport issue here; `core.spec_compiler` is already listed.

### Positive Observations

- The URL exclusion check is present in the new clarification-log extraction path.
- Added tests cover the specific `(int/float)` regression and normal file-token extraction.

Verification: `python -m py_compile core\spec_compiler.py` passed; `python -m pytest tests\test_spec_compiler.py -q` passed with 26 tests.