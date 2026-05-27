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

This changes executable planning behavior: parsed scope feeds `CompiledSpec.scope`, then planner/premortem targets and verification commands.

### Findings

1. [High] Directory/glob scope answers now collapse to empty scope
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t) and not t.startswith("//")]`
   - Issue: Scope answers like `core/` or `core/*.py` no longer produce scope because `_PATH_TOKEN_RE` requires a known file extension and disallows `*`. I verified current behavior: `core/ => []`, `core/*.py => []`. That can recreate the empty-plan failure because `core/planner.py:214` builds implementation steps directly from `spec.scope`.
   - Suggestion: Support directory/glob scope tokens explicitly, or convert them into concrete repo-relative files before returning scope. Add tests for `core/`, `tests/`, and `core/*.py`.

2. [High] Compound extensions are silently truncated into wrong targets
   - File: `core/spec_compiler.py:18`
   - Code: `_PATH_TOKEN_RE = re.compile(r'[\w.\-/\\]+\.(?:py|json|js|ts|md|yaml|yml|txt|sh|toml|cfg|ini)')`
   - Issue: The regex has no boundary after the extension and lacks common compound/frontend extensions. `frontend/src/App.tsx` is parsed as `frontend/src/App.ts`; `.jsx` becomes `.js`, `.jsonl` becomes `.json`, `.pyi` becomes `.py`. This silently sends planner to nonexistent or wrong files.
   - Suggestion: Add a terminal boundary like `(?=$|[\\s,;:)\\]])`, include supported compound extensions, and add regression tests for `.tsx`, `.jsx`, `.jsonl`, and `.pyi`.

3. [Medium] Windows-style paths are emitted unnormalized and miss downstream AF rules
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t) and not t.startswith("//")]`
   - Issue: `core\utils.py` is accepted as `core\\utils.py`, but downstream checks use forward-slash patterns, e.g. `core/planner.py:164` has `re.match(r"core/[^/]+\.py$", item)` and `core/premortem.py:62` has `_CORE_PY_RE = re.compile(r"\bcore/\S+\.py\b")`. That means Windows-style scope can skip Master_Blueprint artifact injection and premortem blueprint sync checks.
   - Suggestion: Normalize extracted scope to repo-relative POSIX paths before returning, and test `core\\utils.py -> core/utils.py`.

4. [Medium] Parent traversal scope is accepted and later used as a plan target
   - File: `core/spec_compiler.py:18`
   - Code: `_PATH_TOKEN_RE = re.compile(r'[\w.\-/\\]+\.(?:py|json|js|ts|md|yaml|yml|txt|sh|toml|cfg|ini)')`
   - Issue: The token character class accepts `..`, so `../core/utils.py` is returned as scope. That value flows into planner targets/artifacts and premortem commands such as `core/premortem.py:88` `command=f"python -m py_compile {targets}"`. Even if not shell-executed today, this lets interview text point work outside the repo boundary.
   - Suggestion: Resolve tokens against project root, reject absolute paths and `..`, then store only normalized repo-relative paths.

### Comparison with Known Issues

- This change addresses the recent false-positive scope pattern where descriptive text containing `/`, such as type hints, was treated as file scope.
- It introduces/repeats the known F-PLAN-EMPTY class: scope extraction can return `[]`, and planner then produces no implementation steps.
- It also intersects AF-specific Windows path handling risk and the existing spec-to-premortem command-safety concern around user-derived scope.

### Positive Observations

- The new clarification-log path extraction no longer copies whole descriptive answers into scope.
- URL-like matches are filtered with `not t.startswith("//")`, matching the intent fallback behavior.

Verification run: `python -m py_compile core\spec_compiler.py` passed; `python -m pytest tests\test_spec_compiler.py -q` passed with 26 tests.