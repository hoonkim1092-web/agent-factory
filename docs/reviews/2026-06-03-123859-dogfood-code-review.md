# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-06-03 12:38
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This change affects dogfood execution behavior, subprocess command construction, merge policy inputs, and environment guards.

### Findings

1. [Critical] Pytest command is shell-injectable via changed file names
   - File: `core/dogfood.py:1699`
   - Code: `"python -m pytest " + " ".join(test_files) + " -q --tb=short"`
   - Issue: `test_files` comes from git status / pipeline output and is concatenated into a shell command. `_default_command_runner()` later executes command strings through PowerShell on Windows and `shell=True` on Unix, so a crafted or accidental filename with shell metacharacters can alter the command.
   - Suggestion: Stop building verification as a shell string. Pass argv through a runner that accepts `list[str]`, or quote each path with platform-correct escaping and add tests for spaces, quotes, and metacharacters in filenames.

2. [High] DEVELOP mutates process-global environment without serialization
   - File: `core/dogfood.py:1638`
   - Code: `os.environ["AGENT_PROJECT_ROOT"] = worktree`
   - Issue: `_run_develop_phase()` changes `os.environ` globally until `finally` restores it. Concurrent dogfood runs or other threads can observe the wrong `AGENT_PROJECT_ROOT`, `AF_SELF_RUN`, or `AF_SKIP_DOMAIN_REVIEW`, causing writes/routing to leak across runs.
   - Suggestion: Prefer an env override passed into the pipeline/orchestrator subprocess boundary. If the pipeline cannot accept env, guard the entire mutation + `pipeline.run()` block with a module-level `threading.Lock`.

3. [High] Git detection failures silently produce empty verification/allowlist input
   - File: `core/dogfood.py:1679`
   - Code: `except Exception:\n            pass`
   - Issue: If `git status` fails after the diff fallback also fails or returns nothing, `changed` remains empty. That means no derived verification requirements, `steps=[]`, and VERIFY can pass without evidence. This repeats the known “silent fallback hides real errors” pattern.
   - Suggestion: Convert git detection failure into a blocked DEVELOP result with the git error in `reason`, or at least set `normalized["ok"] = False` and persist diagnostic context.

4. [High] Dotfile changes are removed from DEVELOP tracking but can still be committed
   - File: `core/dogfood.py:1677`
   - Code: `if fname and not fname.startswith(("planning/", ".af", ".")):\n                        changed.append(fname)`
   - Issue: This excludes every dot-prefixed path, including meaningful project files such as `.github/workflows/...`, `.gitignore`, or config files. FINALIZE can still stage dirty files, but `state.develop_changed_paths` will not include them, so VERIFY may run no relevant checks and MERGE can later fail with an allowlist mismatch.
   - Suggestion: Only exclude explicit runtime/internal paths. Do not blanket-drop `"."` paths; use a named denylist such as `.af_runtime/`, `.git/`, and planning artifacts.

### Comparison with Known Issues

- The command construction repeats the known C4 shell-injection class from `code-review.md`.
- The environment mutation repeats the known global/thread-safety class.
- The broad `except Exception: pass` around git detection repeats the H3 silent fallback pattern.
- Recent dogfood reviews already flagged DEVELOP changed-file detection and merge allowlist drift; this patch improves working-tree detection but still leaves failure and dotfile paths unsafe.

### Positive Observations

- The new `git status --porcelain -u` fallback addresses the real production gap where `ProjectPipeline.run()` does not return `changed_files`.
- `build_merge_policy()` continues to derive allowed paths from `state.develop_changed_paths`, keeping manual and auto merge paths aligned when detection succeeds.