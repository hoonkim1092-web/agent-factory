# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-24 00:48
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change adds execution behavior, persistent state writes, and a new `core/*.py` module.

### Findings

1. [Critical] Dogfood state/artifact writes are non-atomic
   - File: `core/dogfood.py:134`
   - Code: `path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")`
   - Issue: `dogfood_state.json` is the durable resume source, but it is written directly. A crash or interruption can leave a truncated/corrupt state file. `_write_json()` repeats the same pattern for phase artifacts at `core/dogfood.py:354`.
   - Suggestion: use `tempfile.NamedTemporaryFile(..., dir=path.parent, delete=False)` plus `os.replace(tmp_path, path)`, matching `core/interview.py`’s existing atomic `_write_json()` pattern.

2. [High] Phase transitions mutate in memory but do not persist
   - File: `core/dogfood.py:193`
   - Code: `state.phase = _PHASE_ORDER[idx + 1]`
   - Issue: The module docstring promises state is persisted “after each phase transition”, but `advance_phase()` and `block_run()` only mutate the object. A resumed run reloads the old phase from disk and can repeat or skip work incorrectly.
   - Suggestion: either call `save_state(state)` inside transition functions, or expose a single orchestration wrapper that advances/runs/saves atomically after successful phase execution.

3. [High] Valid interview artifacts are rejected
   - File: `core/dogfood.py:209`
   - Code: `if artifact and "intent" not in artifact:`
   - Issue: `core.interview.run_interview()` returns a payload with `task_input`, `project_brief`, `output_path`, and `ok`; it does not return top-level `intent` (`core/interview.py:183-193`). Passing the actual interview artifact into the dogfood INTERVIEW phase raises `ValueError`.
   - Suggestion: accept the existing interview artifact shape, e.g. require `project_brief.goal` or `task_input`, or normalize it before validation.

4. [Medium] New `core/*.py` module is missing from frozen hiddenimports
   - File: `af.spec:97`
   - Code: `'core.interview',`
   - Issue: `af.spec` includes the adjacent pipeline modules (`core.research_brief`, `core.spec_compiler`, `core.premortem`, `core.planner`) but not new `core.dogfood`. This repeats the project’s known frozen-build compatibility risk for new `core/*.py` files.
   - Suggestion: add `'core.dogfood'` to `hiddenimports` and run the frozen-build smoke path.

### Comparison with Known Issues

- Repeats known C2/M10 pattern: non-atomic JSON writes.
- Repeats known M9/AF-specific pattern: new `core/*.py` not added to `af.spec`.
- The dogfood design docs explicitly depend on durable resume state; current transition persistence does not satisfy that contract.

### Positive Observations

- Path construction uses `Path(...) / ...`, so Windows/Unix path handling is mostly sound.
- Runtime state is separated via `AF_RUNTIME_DIR` / `.af_runtime`, which aligns with prior workspace-pollution lessons.