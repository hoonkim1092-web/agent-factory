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

This change affects planning behavior and scope extraction, so it is meaningful execution behavior.

### Findings

1. [High] Directory/glob scope answers now disappear
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t)]`
   - Issue: Scope clarification answers like `core/`, `tests/`, or `core/*.py` no longer produce any scope because `_PATH_TOKEN_RE` requires a known file extension and does not allow `*`. That reintroduces the empty-plan class of failure: `compile_spec()` feeds `spec.scope` into `build_plan()` at `core/planner.py:214`, and an empty scope yields no implementation steps.
   - Suggestion: Accept explicit directory and glob scope forms separately, then normalize them as scope entries or expand them in a controlled workspace-local way.

2. [High] Clarification-log URL references become implementation targets
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t)]`
   - Issue: `_scope_from_intent()` filters URL-like matches with `not m.startswith("//")` at `core/spec_compiler.py:109`, but `_scope_from_clarification_log()` does not. A scope answer like `Use https://example.com/docs/guide.md as reference` extracts `//example.com/docs/guide.md`, which then becomes a planner target/artifact instead of supplemental context.
   - Suggestion: Apply the same URL exclusion in clarification-log extraction, or reject tokens with URI schemes / `//` prefixes before appending.

3. [Medium] Regex partially matches longer non-target filenames
   - File: `core/spec_compiler.py:18`
   - Code: `_PATH_TOKEN_RE = re.compile(r'[\w.\-/\\]+\.(?:py|json|js|ts|md|yaml|yml|txt|sh|toml|cfg|ini)')`
   - Issue: The pattern has no trailing boundary, so `core/foo.py.bak`, `core/foo.pyc`, or `docs/readme.mdx` are silently truncated to `core/foo.py` / `docs/readme.md`. That can cause the planner to modify or test the wrong file.
   - Suggestion: Add a boundary such as `(?![\w.-])` after the extension, or parse paths with a stricter tokenizer that validates the full matched token.

4. [High] Parent-directory paths are admitted into downstream command construction
   - File: `core/spec_compiler.py:132`
   - Code: `tokens = [t for t in _PATH_TOKEN_RE.findall(answer) if _PATH_RE.search(t)]`
   - Issue: `../outside.py` is accepted as scope. That value flows into premortem verification command strings such as `command=f"python -m py_compile {targets}"` at `core/premortem.py:88`. This repeats the known CompiledSpec scope trust problem and can push planning/verification outside the workspace.
   - Suggestion: Normalize each extracted token against the project root, reject absolute paths and `..` traversal, and only store repo-relative paths.

### Comparison with Known Issues

- This change partially addresses the known F-PLAN-EMPTY issue by avoiding descriptive slash text like `(int/float)`.
- It introduces adjacent F-PLAN-EMPTY risk for directory/glob answers.
- It repeats the known pattern where `CompiledSpec.scope` is user/interview-derived and later appears in planner artifacts and premortem command strings.
- No new `core/*.py` file was added, so the `af.spec` hiddenimports checklist item does not apply here.

### Positive Observations

- The change correctly stops treating arbitrary descriptive slash text as a scope path.
- The extraction deduplicates multiple path tokens while preserving order.