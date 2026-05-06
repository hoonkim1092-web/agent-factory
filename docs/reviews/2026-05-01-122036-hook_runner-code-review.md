# Code Review: hook_runner

> Source: scripts/hook_runner.py
> Date: 2026-05-01 12:20
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Critic received an empty diff and produced no code findings. Cross-reviewer independently audited the file and produced 2 accepted findings with strong evidence, 2 rejected. No Critical findings exist, but two functional correctness issues warrant attention before merge.

---

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [High] Review-gate builtins not wired by hook callers

- **Critic**: not flagged (no diff received)
- **Cross**: `post_edit_enqueue`, `pre_bash_review_gate`, `post_agent_record`, `post_commit_clear` are implemented but neither `.claude/settings.local.template.json` (line 88) nor `core/providers/session_adapter.py` (line 291) invoke them.
- **Judgment**: Evidence is specific and multi-file. Without `post_edit_enqueue`, `.af_review_queue/pending_agent_review.json` is never created, so the entire review queue is silently inert. Without `post_agent_record`, af-* agent completions go unrecorded. This is a functional gap, not a code quality issue — accepting at High.
- **Action Required**: Add `post_edit_enqueue`, `pre_bash_review_gate`, `post_agent_record`, and `post_commit_clear` to `settings.local.template.json` under `PostToolUse`/`Stop` and to `session_adapter.py`'s hook generation path. Add integration tests that verify generated hook config includes these entries.

---

#### 2. [ACCEPT] [Medium] Generic dispatch path can return non-zero, violating the always-exit-0 hook contract

- **Critic**: not flagged (no diff received)
- **Cross**: `hook_runner.py:500` propagates child return codes for non-builtin scripts. `cli_hook_bridge.py:34` can raise on malformed JSON, producing a non-zero exit that reaches the caller — contradicting the file-level contract that hooks always exit 0 (only `pre_bash_review_gate` intentionally exits 2 to block).
- **Judgment**: Contract violation is clearly evidenced by the call chain: `session_adapter.py:220` → `hook_runner.py cli_hook_bridge` → `cli_hook_bridge.py:34`. A non-zero exit from a hook can halt user shell sessions unexpectedly. Accepting at Medium.
- **Action Required**: In the generic (non-builtin) dispatch path, catch non-zero child exits, log the failure with the child's stderr, and return `0`. The only intentional blocking exit (`pre_bash_review_gate` returning `2`) is already a builtin and is unaffected.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Review-gate builtins not wired | High | ACCEPT | Cross only |
| 2 | Generic dispatch violates exit-0 contract | Medium | ACCEPT | Cross only |
| — | Test-gap FAIL blocks correctly | — | REJECT | Cross (tests pass) |
| — | `downgrade_blast_tier` silent path | — | REJECT | Cross (tombstoned) |

---

### Recommendations

- **Wire the four missing builtins** in both `settings.local.template.json` and `session_adapter.py` — without this, the review queue is a no-op in all generated sessions.
- **Wrap generic dispatch in a try/except** that swallows non-zero exits and logs them; keep the `pre_bash_review_gate` exit-2 path untouched.
- **Verify prior open item** (Critic finding #2): `build_review_bundle.py:42` non-string filter crash from the prior cross-review round — confirm that fix is committed before closing out that WARN verdict.
- The critic receiving an empty diff while the cross-reviewer found live issues suggests a staging/diff-assembly gap in the review gate. Run `python3 scripts/review_gate.py --debug` to confirm the correct changeset is being passed to each reviewer tier.