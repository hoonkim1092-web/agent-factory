# Code Review: premortem

> Source: core/premortem.py
> Date: 2026-05-23 23:34
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This is a new behavioral `core/*.py` module that affects planning/verification logic and emits executable verification commands.

### Findings

1. [Critical] Verification command is built from untrusted scope text
   - File: `core/premortem.py:80`
   - Code: `files = [s for s in scope if _CORE_PY_RE.search(s)]`
   - Code: `command=f"python -m py_compile {targets}",`
   - Issue: `scope` comes from `CompiledSpec`, which is compiled from interview/user artifacts. A value like `core/foo.py; <command>` passes the regex test and is copied into a shell command string. If a later verifier executes these commands, this becomes command injection. It also breaks on spaces.
   - Suggestion: validate scope entries as repo-relative paths, reject metacharacters, and emit structured command args instead of shell strings. If strings are required, quote with a platform-appropriate escaping strategy.

2. [High] Windows core paths do not trigger core risk detection
   - File: `core/premortem.py:62`
   - Code: `_CORE_PY_RE = re.compile(r"\bcore/\S+\.py\b")`
   - Issue: AF runs heavily on Windows, and the user/project context uses paths like `core\premortem.py`. This regex only matches `/`, so `scope=["core\\premortem.py"]` will skip blueprint and packaging risks.
   - Suggestion: normalize paths with `Path(s).as_posix()` before matching, or use a regex that accepts both separators, e.g. `r"(^|\\b)core[\\\\/][^\\s]+\\.py\\b"`.

3. [Medium] New `core/*.py` module is missing from frozen-build hiddenimports
   - File: `af.spec:96`
   - Code: `'core.interview',`
   - Code: `'core.research_brief',`
   - Code: `'core.spec_compiler',`
   - Issue: `core/premortem.py` is a new core module, but `af.spec` lists `core.spec_compiler` and not `core.premortem`. Known AF rule says new `core/*.py` files must be added to hiddenimports for frozen builds.
   - Suggestion: add `'core.premortem'` to `af.spec` near `core.spec_compiler`, and add/keep a packaging smoke check.

4. [Medium] Blueprint verification command is a placeholder and cannot verify the changed module
   - File: `core/premortem.py:92`
   - Code: `command="grep -n '<module>' Master_Blueprint.md",`
   - Issue: This will literally search for `<module>`, not the actual changed module. The premortem emits a verification requirement that is almost guaranteed to fail or be ignored, so blueprint sync risk is not actionable.
   - Suggestion: generate the actual module token, e.g. `core/premortem.py` or `core/premortem`, and prefer a Python/PowerShell-compatible check over Unix-only `grep`.

5. [Medium] Premortem is not wired into the production spec pipeline
   - File: `core/premortem.py:210`
   - Code: `def run_premortem(spec: CompiledSpec) -> PremortomResult:`
   - Issue: Direct search shows `run_premortem` is only referenced by `tests/test_premortem.py`; no production caller invokes it after `compile_spec()`. The documented Step 5 behavior says Premortem should run after Spec, but the change currently adds an unused module.
   - Suggestion: integrate `run_premortem()` into the dogfood/planning pipeline or explicitly mark this as library-only groundwork and add the integration in the same feature sequence.

### Comparison with Known Issues

- Repeats the AF hiddenimports pattern: new `core/*.py` file is not listed in `af.spec`.
- Introduces a shell-command construction pattern similar to the known shell-injection class, even though the command is emitted rather than executed in this file.
- Repeats Windows/Unix path fragility by matching only forward slashes and emitting Unix `grep`.

### Positive Observations

- The module keeps risk detectors small and independently testable.
- `CompiledSpec` is passed as a structured object instead of loosely passing many unrelated dicts.