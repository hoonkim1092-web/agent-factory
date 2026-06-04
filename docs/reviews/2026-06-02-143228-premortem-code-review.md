# Code Review: premortem

> Source: core/premortem.py
> Date: 2026-06-02 14:32
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This touches meaningful behavior and emits verification commands that flow into dogfood execution.

### Findings

1. [Critical] Premortem emits shell strings with POSIX quoting into a shell-backed runner
   - File: `core/premortem.py:86`
   - Code: `command=f"python -m py_compile {' '.join(shlex.quote(f) for f in files)}",`
   - Issue: `VerificationStep.command` is a raw string. It flows through `core/planner.py:515-533` into `verification_requirements`, then `core/dogfood.py:1629` executes it via `_command_runner()`. On Windows, `_command_runner()` interpolates the string into PowerShell; `shlex.quote()` is POSIX shell quoting, not PowerShell escaping. A scope path containing PowerShell metacharacters or single quotes can break the command or become injection-prone.
   - Suggestion: Change verification steps to structured argv, e.g. `argv: ["python", "-m", "py_compile", *files]`, and execute with `shell=False`. If strings must remain, validate scope paths against a strict repo-relative allowlist before command generation and use shell-specific escaping.

2. [High] Windows-style `core\*.py` scope skips blueprint and packaging risks
   - File: `core/premortem.py:65`
   - Code: `_CORE_PY_RE = re.compile(r"\bcore/\S+\.py\b")`
   - Issue: `CompiledSpec` accepts both `/` and `\` path separators, but premortem only matches forward-slash `core/*.py`. A scope like `core\planner.py` will skip R1 blueprint sync and R2 packaging checks, despite being a core module change.
   - Suggestion: Normalize scope and risk hints once, e.g. `item.replace("\\", "/")`, before all matching. Also reject absolute and parent-traversal paths at the same boundary.

3. [High] Existing absolute or parent-traversal scope paths are treated as valid
   - File: `core/premortem.py:212`
   - Code: `missing = [f for f in scope if not os.path.exists(f)]`
   - Issue: R11 only checks existence. An existing `../outside.py` or absolute path outside the repo is not flagged, and later detectors may read/parse it (`with open(path, encoding="utf-8")`). This repeats the known `CompiledSpec.scope` trust issue: user/interview-derived scope can point outside the workspace.
   - Suggestion: Resolve each scope path against the AF project root, reject absolute paths and any resolved path outside the workspace, and use normalized repo-relative paths downstream.

4. [Medium] Duplicate function detector misses async functions and class methods
   - File: `core/premortem.py:247`
   - Code: `if re.search(rf"^def {re.escape(name)}\b", content, re.MULTILINE):`
   - Issue: This only detects top-level `def name` at column 0. Existing `async def foo()` or `class X: def foo(...)` will not trigger R13, so a real duplicate can proceed without an investigation step.
   - Suggestion: Use `ast.parse()` and inspect `FunctionDef` and `AsyncFunctionDef` nodes. Decide explicitly whether methods should count; if not, document and test that boundary.

### Comparison with Known Issues

- This repeats the known C4-adjacent shell-command risk from `docs/code_review/code-review.md`: user-derived planning/premortem data becomes executable command text.
- It also repeats AF Windows/Unix path handling concerns: forward-slash regexes and Unix `grep`/`shlex` assumptions in a Windows-first/frozen-build project.
- It does not introduce an `af.spec` hidden import issue: `af.spec` already includes `core.premortem`.

### Positive Observations

- `af.spec` includes `core.premortem`, so frozen-build hidden import coverage is present.
- The AST-based complexity/nesting detectors prune nested function bodies deliberately, avoiding the prior double-counting pattern.