# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-24 00:49
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change adds executable `core/*.py` behavior, persistent state writes, and dogfood orchestration behavior.

### Findings

1. [Critical] State/artifact writes are non-atomic and can corrupt resumable runs
   - File: `core/dogfood.py:134`
   - Code: `path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")`
   - Issue: `save_state()` writes directly to the durable resume file. A crash, process kill, or concurrent reader during this write can leave `dogfood_state.json` truncated or partially written. The same pattern is repeated for artifacts at `core/dogfood.py:354`.
   - Suggestion: Use `tempfile.NamedTemporaryFile` or `mkstemp` in the target directory, write+flush, then `os.replace(tmp_path, path)`. Clean up temp files on exceptions.

2. [High] Interview phase rejects the actual interview artifact schema
   - File: `core/dogfood.py:209`
   - Code: `if artifact and "intent" not in artifact:`
   - Issue: `core.interview.run_interview()` returns `task_input` and nested `project_brief.goal`, not top-level `intent`:
     `core/interview.py:178` code: `"task_input": task,`
     `core/interview.py:187` code: `"project_brief": enriched,`
     This makes the dogfood interview phase reject valid upstream output. I confirmed `python -m pytest tests/test_dogfood.py -q` fails 2 tests on this exact `ValueError`.
   - Suggestion: Accept the real shape: top-level `project_brief`, `task_input`, or bare brief with `goal`. If validation is needed, validate `project_brief.goal`/`goal`/`task_input`, not only `intent`.

3. [High] Phase transitions mutate memory but are not persisted
   - File: `core/dogfood.py:193`
   - Code: `state.phase = _PHASE_ORDER[idx + 1]`
   - Issue: The module doc says state is persisted “after each phase transition,” but `advance_phase()` and `block_run()` only mutate the in-memory object. A crash after `advance_phase()` but before a caller remembers to call `save_state()` resumes from the old phase and can repeat work or overwrite artifacts.
   - Suggestion: Persist inside transition helpers, or provide a single transition API that updates and saves atomically. At minimum, make the contract explicit and test that callers save immediately.

4. [Medium] New `core/*.py` module is missing from frozen build hiddenimports
   - File: `af.spec:97`
   - Code:
     ```python
     'core.interview',
     'core.research_brief',
     'core.spec_compiler',
     'core.premortem',
     'core.planner',
     ```
   - Issue: `core/dogfood.py` is a new core module, but `af.spec` does not include `core.dogfood`. The known AF review checklist flags this as a frozen-build compatibility risk. `rg` also shows no `core.dogfood` entry in `af.spec`.
   - Suggestion: Add `'core.dogfood'` to `hiddenimports`, then run the project’s frozen-build smoke or at least `python run_factory_cli.py --help`.

### Comparison with Known Issues

- This change repeats known C2/M10 non-atomic JSON write patterns from `docs/code_review/code-review.md`.
- It repeats the AF-specific hiddenimports risk for new `core/*.py` files.
- It touches the dogfood workflow, which prior reviews call out as sensitive to workspace/runtime isolation and frozen packaging.

### Positive Observations

- The phase enum and serialized state model are simple and explicit, which makes resume-state debugging easier.
- The spec/premortem/plan phases reuse existing `core.research_brief`, `core.spec_compiler`, `core.premortem`, and `core.planner` APIs instead of duplicating that logic.