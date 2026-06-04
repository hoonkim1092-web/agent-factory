# Code Review: planner

> Source: core/planner.py
> Date: 2026-06-02 14:30
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

Planner changes affect executable plan behavior and command generation. Plan commands flow into dogfood execution/verification, including shell-backed runners.

### Findings

1. [Critical] Planner still emits raw shell command strings into the dogfood runner
   - File: `core/planner.py:96`
   - Code: `cmds.append(v.command)`
   - Issue: `build_plan()` copies premortem verification strings directly into `verification_requirements` and verification steps. The caller `core/dogfood.py:1629` runs those strings via `_command_runner()`, which uses `shell=True` on Unix and interpolates into PowerShell on Windows. This repeats the known C4-adjacent plan-command risk.
   - Suggestion: Replace `commands: list[str]` with a structured command schema such as `{argv: list[str], timeout, cwd_policy}` and validate commands before execution. Until then, keep planner-produced commands non-executable metadata.

2. [High] Generated investigation commands assume Unix `grep` semantics on Windows
   - File: `core/planner.py:322`
   - Code: `shlex.join(["grep", "-n", f"def {func_name}", file_path])`
   - Issue: AF runs on Windows/frozen builds. In PowerShell, `grep` is commonly an alias for `Select-String`, and `-n` does not mean GNU grep line numbers. These investigation steps can return wrong output or fail on Windows, blocking or misleading AI implementation.
   - Suggestion: Use a cross-platform Python command or a structured internal file-search helper. If external search is required, prefer `rg` only after detecting it and use a fallback.

3. [High] Windows-style core scope skips Blueprint artifact injection
   - File: `core/planner.py:458`
   - Code: `if re.match(r"core/[^/]+\.py$", item):`
   - Issue: `core/spec_compiler.py` accepts backslash paths, but this planner check only matches forward slashes. A scope like `core\planner.py` still gets an implementation step, but does not add `Master_Blueprint.md` to artifacts, violating the AF rule that `core/*.py` changes sync the Blueprint.
   - Suggestion: Normalize all scope paths once with `item.replace("\\", "/")`, reject absolute/parent traversal paths, and use the normalized value for artifact and verification rules.

4. [Medium] `implementation_steps()` no longer recognizes planner-generated implementation steps
   - File: `core/planner.py:540`
   - Code: `return [s for s in plan.steps if "IMPLEMENT" in s.id]`
   - Issue: `build_plan()` now assigns IDs like `S1`, `S2`, while implementation steps are identified only by `action=f"Implement {item}"`. This helper returns an empty list for plans produced by this module, making the public API misleading and prone to silent caller bugs.
   - Suggestion: Identify implementation steps by an explicit `kind` field, or update the helper to use a stable marker such as `action.startswith("Implement ")`.

### Comparison with Known Issues

- Repeats the known shell-command execution risk documented in `docs/code_review/code-review.md` and prior dogfood/planner reviews.
- Repeats AF Windows/Unix path handling concerns: mixed `/`, `\`, `Path()`, regex, and shell commands.
- Does not introduce a new `core/*.py` hiddenimport issue because `af.spec` already includes `core.planner`.

### Positive Observations

- `core/planner.py` itself does not perform file writes, so it avoids the non-atomic write class in this file.
- The planner keeps investigation steps before implementation steps and wires implementation dependencies explicitly through `depends_on`.