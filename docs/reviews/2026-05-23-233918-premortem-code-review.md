# Code Review: premortem

> Source: core/premortem.py
> Date: 2026-05-23 23:39
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This adds a new behavioral `core/*.py` module that emits verification commands and affects planning/verification logic.

### Findings

1. [Critical] Verification command can be injected through spec scope
   - File: `core/premortem.py:88`
   - Code: `command=f"python -m py_compile {targets}",`
   - Issue: `targets` is built from `CompiledSpec.scope`, which comes from user/interview artifacts via `core/spec_compiler.py`. A value like `core/foo.py; bad_command` matches `_CORE_PY_RE` and is copied into an executable shell command string. If the planner/verifier later runs these commands, this becomes command injection.
   - Suggestion: validate scope entries as repo-relative paths, reject metacharacters, and emit structured argv such as `["python", "-m", "py_compile", path]` instead of shell strings.

2. [High] Windows core paths skip blueprint and packaging risks
   - File: `core/premortem.py:62`
   - Code: `_CORE_PY_RE = re.compile(r"\bcore/\S+\.py\b")`
   - Issue: AF runs on Windows and paths commonly appear as `core\premortem.py`. This regex only accepts `/`, so `scope=["core\\premortem.py"]` will not trigger R1 or R2.
   - Suggestion: normalize paths with `Path(path).as_posix()` before matching, or accept both separators with `core[\\/]...`.

3. [Medium] New core module is missing from frozen-build hiddenimports
   - File: `af.spec:98`
   - Code: `'core.research_brief',`
   - Code: `'core.spec_compiler',`
   - Issue: `core/premortem.py` is a new `core/*.py` module, but `af.spec` does not include `core.premortem`. AF’s known build rule requires new core modules in hiddenimports for PyInstaller compatibility.
   - Suggestion: add `'core.premortem'` near `core.spec_compiler` in `af.spec`.

4. [Medium] Blueprint verification uses a literal placeholder
   - File: `core/premortem.py:92`
   - Code: `command="grep -n '<module>' Master_Blueprint.md",`
   - Issue: This searches for the literal string `<module>`, not the changed module. The generated verification requirement is not actionable and will fail or be ignored.
   - Suggestion: generate a module-specific check, e.g. search for `core/premortem.py` or `core/premortem`, and avoid Unix-only `grep` if this must work on Windows.

5. [Medium] Premortem is not wired into the production spec pipeline
   - File: `core/premortem.py:214`
   - Code: `def run_premortem(spec: CompiledSpec) -> PremortomResult:`
   - Issue: Direct caller search shows `run_premortem` is referenced only by `tests/test_premortem.py`; no production caller invokes it after `compile_spec()`. The documented Step 5 says Premortem should run after Spec, but this change currently adds an unused module.
   - Suggestion: integrate `run_premortem()` into the dogfood/planning pipeline, or explicitly scope this commit as library-only groundwork and add integration next.

### Comparison with Known Issues

- Repeats the known `af.spec` hiddenimports issue for new `core/*.py` files.
- Introduces a shell-command construction risk similar to the known shell-injection class, even though the command is emitted rather than executed here.
- Repeats AF Windows/Unix path fragility by matching only `/` and emitting Unix `grep`.

### Positive Observations

- Detectors are small and unit-testable.
- The module consumes `CompiledSpec` as a structured object rather than passing loose dicts through the API.