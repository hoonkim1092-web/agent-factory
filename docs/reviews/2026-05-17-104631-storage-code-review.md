# Code Review: storage

> Source: core/checkpoint/storage.py
> Date: 2026-05-17 10:46
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: WARN

### Findings

1. [High] Workspace checkpoint cache is not thread-safe
   - File: `core/checkpoint/storage.py:86`
   - Code: `_workspace_storage_cache: dict[str, CheckpointStorage] = {}`
   - Issue: `get_storage_for()` mutates a module-global dict with no lock, while the parallel `RunEvent` change correctly added `_workspace_store_lock`. In daemon / concurrent pipeline use, this repeats the known H5 “global dict accessed from multiple threads without Lock” pattern.
   - Suggestion: Add a `threading.Lock()` and use the same double-checked locking pattern as `core/events/run_event.py`.

2. [High] Workspace-scoped stores grow without eviction
   - File: `core/checkpoint/storage.py:104`
   - Code: `if key not in _workspace_storage_cache:`
   - Issue: Every distinct `runtime_workspace` absolute path is retained forever. AF creates/uses isolated runtime workspaces, so a long-lived process can leak one storage object per workspace. The same pattern exists in the changed `core/events/run_event.py:153` cache.
   - Suggestion: Avoid caching cheap file-store objects, or use a bounded `lru_cache(maxsize=...)` / explicit cleanup API.

3. [High] New scoped storage bypasses `AF_CHECKPOINT_DIR`
   - File: `core/checkpoint/storage.py:105`
   - Code: `base_dir=os.path.join(key, "runs")`
   - Issue: Callers were migrated from `get_default_storage()`, which honors `AF_CHECKPOINT_DIR`, to `get_storage_for(state_workspace)`, which always writes under `<workspace>/runs`. This breaks configured checkpoint isolation used by tests/frozen/runtime setups and can split checkpoint/event data across different roots.
   - Suggestion: Define env precedence for scoped storage. Either honor `AF_CHECKPOINT_DIR` consistently, or update all callers/tests/docs so scoped storage is the only supported path.

4. [Medium] Runtime event store failures are silently swallowed
   - File: `core/dynamic_orchestrator.py:770`
   - Code: `except Exception:\n                        pass`
   - Issue: After switching to `get_store_for(state_workspace)`, path/permission/config errors during event writes are hidden. Resume then cannot reconstruct completed steps from RunEvent history, but the operator gets no diagnostic.
   - Suggestion: Log at least a warning with `run_id`, `step_id`, and `state_workspace`, ideally rate-limited to avoid noisy loops.

### Comparison with Known Issues

- This change repeats known `code-review.md` patterns: H5 thread safety for global dicts, H2 unbounded cache growth, and H3 silent fallback.
- It partially addresses the prior runtime workspace split for checkpoints/events, but the migration is inconsistent with `AF_CHECKPOINT_DIR` and still leaves some default-store call sites elsewhere.

### Positive Observations

- `project_pipeline.py` now uses the same `state_workspace` for prepare, done-guard, and done-save checkpoint paths.
- `core/events/run_event.py` applies a lock for the workspace event-store cache, which is the right pattern to mirror in checkpoint storage.