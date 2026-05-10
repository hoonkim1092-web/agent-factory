# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-08 11:12
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### Findings

1. [High] Silent error suppression hides telemetry failures
   - File: [core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py):903
   - Code: `except Exception: pass`
   - Issue: Any I/O or encoding failure in the timing dump path is fully swallowed, so measurement data can silently disappear with no signal. This creates false confidence in perf baselines.
   - Suggestion: Catch `Exception as e` and log at least one warning with context (`doc_type`, `work_item_id`, target path). Do not use bare `pass` here.

2. [High] Timing output path ignores project/runtime path conventions
   - File: [core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py):892
   - Code: `_os.makedirs("runtime/timing", exist_ok=True)`
   - Issue: This writes to a CWD-relative `runtime/timing`, while the same function otherwise respects `target_path/doc_root` for artifact placement. In AF context, this can place files in unexpected locations and bypass existing `.af_runtime` convention.
   - Suggestion: Route timing output through a canonical runtime root (for example under `.af_runtime/...`) derived from workspace/doc root, and build paths via `os.path.join`.

3. [Medium] Measurement is skipped when placeholder refine is disabled
   - File: [core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py):858
   - Code: `if not placeholder_refine: return content`
   - Issue: Early return bypasses the timing dump entirely. If `AF_PLACEHOLDER_REFINE=0`, no baseline record is written, so metrics become biased/incomplete by env config.
   - Suggestion: Move timing write to a `finally` block so it always runs regardless of refine mode.

4. [Medium] Non-atomic/uncoordinated JSONL append can corrupt telemetry under concurrent runs
   - File: [core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py):901
   - Code: `with open(f"runtime/timing/{work_item_id}_baseline.jsonl", "a") as _f:`
   - Issue: Concurrent writers to the same slug file are not synchronized; line interleaving or partial writes can produce malformed JSONL and unreliable analysis data.
   - Suggestion: Add file locking (cross-platform) or per-run isolated files + merge step. Also specify `encoding="utf-8"` explicitly for deterministic output.

### Comparison with Known Issues
- This change does **not** address known M10 reliability patterns from [docs/code_review/code-review.md](/Users/hoon/workTree/agent-factory/docs/code_review/code-review.md):317-327.
- It introduces a **similar pattern**: direct file write for JSONL telemetry without atomicity/locking.
- It also reintroduces a **silent-fallback style** (`except ...: pass`), which is the same failure-obscuring behavior class previously called out in past reviews.

### Positive Observations
- The timing block is isolated from core document generation flow, so primary artifact generation is not hard-failed by telemetry code.
- `refine_attempts` is tracked only when forbidden tokens are actually detected, which is a meaningful metric rather than a blind retry counter.