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

This is meaningful behavior and emits shell verification commands from user/spec-derived input.

### Findings

1. [High] User-controlled scope is interpolated into shell commands
   - File: `core/premortem.py:80`
   - Code: `files = [s for s in scope if _CORE_PY_RE.search(s)]` / `command=f"python -m py_compile {targets}"`
   - Issue: `scope` comes from `CompiledSpec`, which is compiled from interview/user artifacts. A value like `core/foo.py; <command>` matches the regex and is copied into a shell command string. If a later verifier executes these requirements, this becomes command injection and also breaks on spaces.
   - Suggestion: normalize scope entries as paths, reject anything outside `core/*.py`, and store verification as argv/list data instead of a shell string.

2. [High] Windows paths skip core-module risk detection
   - File: `core/premortem.py:62`
   - Code: `_CORE_PY_RE = re.compile(r"\bcore/\S+\.py\b")`
   - Issue: AF runs on Windows and the workspace uses paths like `core\premortem.py`. This regex only matches `/`, so `scope=["core\\premortem.py"]` misses blueprint and packaging risks.
   - Suggestion: normalize `\` to `/` before matching, or use `Path.parts`; add tests for both `core/foo.py` and `core\\foo.py`.

3. [Medium] New `core/*.py` module missing from frozen-build hiddenimports
   - File: `af.spec:98`
   - Code: `'core.spec_compiler',`
   - Issue: `core/premortem.py` is new but `af.spec` lists `core.spec_compiler` and not `core.premortem`. Known AF review pattern M9 says manual hiddenimports omissions can break `dist/af/af.exe`.
   - Suggestion: add `'core.premortem'` near `core.spec_compiler` and run/record a frozen import smoke check.

4. [Medium] Blueprint verification command is non-actionable and Unix-specific
   - File: `core/premortem.py:92`
   - Code: `command="grep -n '<module>' Master_Blueprint.md"`
   - Issue: This searches literally for `<module>`, not the changed module. The surrounding commands also use `grep`, which is not portable to the project’s Windows-first shell context.
   - Suggestion: emit the actual module token, and prefer a Python or PowerShell-compatible check.

5. [Medium] Premortem is not wired into the production pipeline
   - File: `core/premortem.py:214`
   - Code: `def run_premortem(spec: CompiledSpec) -> PremortomResult:`
   - Issue: Direct reference search shows `run_premortem` is only used by `tests/test_premortem.py` and docs/review artifacts, not after `compile_spec()` in production. The documented Step 5 says premortem should run after Spec, but this currently adds an unused module.
   - Suggestion: integrate `run_premortem()` into the dogfood/planning pipeline, or clearly split this as library groundwork with follow-up integration.

### Comparison with Known Issues

- Repeats known patterns from `docs/code_review/code-review.md`: shell-command injection risk, Windows/Unix path handling risk, and `af.spec` hiddenimports omissions.
- The change partially addresses the known hiddenimports/destructive-operation review culture by generating risks for them, but the implementation itself misses frozen-build registration and emits unsafe shell strings.

### Positive Observations

- The risk model is structured (`PremortomRisk`, `VerificationStep`, `to_dict()`), so downstream gates can consume it without parsing prose.
- Tests cover duplicate risk IDs and basic detector behavior; adding Windows-path and command-safety cases would strengthen the suite.