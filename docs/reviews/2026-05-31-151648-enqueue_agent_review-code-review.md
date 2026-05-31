# Code Review: enqueue_agent_review

> Source: scripts/enqueue_agent_review.py
> Date: 2026-05-31 15:16
> Type: code
> Providers: critic=codex
> Mode: single-provider (code critic only)
> Trigger: unknown

---

## Code Critic Review

### Verdict: BLOCK

### T3 Advisory

t3_required: yes

This touches hook/gate policy, Tier 3 routing, review telemetry, and file-state mutation.

### Findings

1. [High] Telemetry skip can override a required Tier 3 review
   - File: `scripts/review_gate.py:297`
   - Code: `if _telemetry_skip_enacted(state): return [1, 2]`
   - Issue: The new telemetry path does not check `state["t3_required"]` or `af-critic` advisory. A semantic Python change can have `t3_required=True` from `enqueue_agent_review.py`, but `_required_tiers_for()` still skips Tier 3 if telemetry says `skip=True`. This violates the documented contract that `yes` and `unknown` require Tier 3.
   - Suggestion: Gate telemetry skip behind the same final advisory rule, or at minimum require `_critic_t3_advisory(state) == "no"` and `state.get("t3_required") is False` before returning `[1, 2]`.

2. [High] Enqueue hook can time out and fail to queue edits as metrics grow
   - File: `scripts/enqueue_agent_review.py:229`
   - Code: `telemetry_decision = compute_t3_telemetry_skip(workspace)`
   - Issue: This runs inside the PostToolUse enqueue subprocess, whose caller has a hard 3s timeout.
   - File: `scripts/hook_runner.py:158`
   - Code: `subprocess.run([sys.executable, script, fp], timeout=3, cwd=root, capture_output=True)`
   - File: `scripts/review_metrics_logger.py:210`
   - Code: `def _load_records(workspace: str) -> list[dict]:`
   - Issue: `compute_t3_telemetry_skip()` loads and scans all `review_metrics.jsonl` and `skip_audit.jsonl` records on every edit. Once telemetry grows, the hook can be killed before writing `pending_agent_review.json`, leaving changed files unqueued.
   - Suggestion: Keep enqueue O(1): maintain a bounded telemetry summary, cap records read to the recent window plus aggregate counters, or compute telemetry outside the critical PostToolUse path.

3. [Medium] Skip audit is written before the queue state is committed
   - File: `scripts/enqueue_agent_review.py:164`
   - Code: `if telemetry_skip_enacted_func(data):`
   - File: `scripts/enqueue_agent_review.py:165`
   - Code: `append_skip_audit_func(`
   - File: `scripts/enqueue_agent_review.py:179`
   - Code: `os.replace(tmp_path, marker)`
   - Issue: `skip_audit.jsonl` can record a Tier 3 skip before `pending_agent_review.json` is atomically replaced. If the process is killed or `os.replace()` fails after the audit append, telemetry history contains a skip that was never actually enacted.
   - Suggestion: Commit marker state first, then append skip audit, or include a queue-state id in both files and only count audit rows whose queue state was committed.

### Comparison with Known Issues

- This change preserves the known C2 fix pattern for the marker itself: `tempfile.mkstemp` plus `os.replace`.
- It introduces a pattern similar to known review-gate risks: policy skip paths can silently bypass required review agents.
- It also repeats known operational risks around silent/best-effort hook behavior and unbounded log scanning in a timeout-sensitive hook path.

### Positive Observations

- The marker update still uses atomic replacement and preserves existing queue fields.
- The risk-file safety net explicitly includes `scripts/enqueue_agent_review.py`, `scripts/review_gate.py`, hook scripts, provider files, and normalizes Windows path separators.