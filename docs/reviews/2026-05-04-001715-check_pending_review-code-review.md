# Code Review: check_pending_review

> Source: scripts/check_pending_review.py
> Date: 2026-05-04 00:17
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The diff achieves its single stated goal (one-shot WARN-only suppression telemetry), but the integration is fragile in three independent ways. **Cross Review is unavailable** (provider error: Codex stdin/init failure — no findings returned). All judgments below rest on the Critic Review plus direct diff inspection. No Critical findings; merge can proceed if author documents the trade-offs or applies the trivially-cheap fixes below.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Semantic abuse of `_log_hook_event` parameter contract
- **Critic**: `file` slot receives `str(round_count)` (a number, not a path); `error` slot receives a JSON blob, breaking the pipe-delimited `ts|builtin|file|exit_code|error` schema. `exit_code=0` refers to no executed builtin.
- **Cross**: not flagged (provider unavailable).
- **Judgment**: ACCEPT — evidence is direct from the diff at `scripts/check_pending_review.py:137-146` against `_log_hook_event`'s documented signature in `scripts/hook_runner.py:100`. Mixing JSON into a pipe-delimited line will break any downstream `awk`/`grep` consumer; the Critic correctly identifies this as the same shape of cross-module key-contract bug as the prior H4 incident.
- **Action Required**: Either (a) extend `_log_hook_event` with a typed `metadata: dict | None = None` kwarg and emit a parallel JSONL line, or (b) write to a purpose-built sink (`.af_review_queue/suppression_events.jsonl`). Do not overload the hook-event schema.

#### 2. [ACCEPT] [High] `except Exception: pass` masks signature/serialization regressions
- **Critic**: Outer bare-except (line 147-148) compounds `_log_hook_event`'s own internal `try/except: pass`, double-armoring the telemetry sink against ever surfacing a problem. Future kwarg/schema drift silently disables the sink.
- **Cross**: not flagged (provider unavailable).
- **Judgment**: ACCEPT — pattern matches the documented anti-pattern in `code-review.md §3.2 / H3` (silent fallback). Combined with finding #1 (semantic mismatch), this is the highest-probability place a future refactor will silently break with zero log signal.
- **Action Required**: Narrow to `except (ImportError, AttributeError):`. Let `TypeError`/`JSONDecodeError`/etc. propagate so regressions are detectable in `hook_events.log` or stderr.

#### 3. [ACCEPT] [High] Dual `sys.path` entries risk duplicate module identity for `hook_runner`
- **Critic**: After the diff, both `scripts/` and project-root are on `sys.path`. With no `scripts/__init__.py` (verified absent), `hook_runner` is reachable as both `import hook_runner` and `import scripts.hook_runner`, producing two distinct entries in `sys.modules` with duplicated module-level state.
- **Cross**: not flagged (provider unavailable).
- **Judgment**: ACCEPT — verifiable from the diff and repo layout. The new code at line 136 imports `from scripts.hook_runner import _log_hook_event`, while pre-existing code at line 89 still does `from review_gate import _state_lock` (top-level). If `review_gate.py` itself imports `hook_runner` top-level anywhere, this caller will hit two distinct module objects within the same process. This is a latent hazard, not a confirmed regression — but it is exactly the kind of subtle dual-identity bug the Critic flags as bug-class déjà vu.
- **Action Required**: Pick one canonical style. Easiest fix: drop the new `sys.path.insert(0, os.path.dirname(_scripts_dir))` and change line 136 to `from hook_runner import _log_hook_event` (matches the existing `from review_gate import` style at line 89). Or add `scripts/__init__.py` and migrate all internal imports.

#### 4. [ACCEPT] [Medium] Cross-module import of underscore-prefixed private symbol
- **Critic**: `_log_hook_event` is module-private by convention; the `# type: ignore` further suppresses static signal that would catch a future rename.
- **Cross**: not flagged (provider unavailable).
- **Judgment**: ACCEPT — direct evidence at line 136. Compounds finding #2: private-symbol import + bare except = silent breakage on any internal `hook_runner` cleanup.
- **Action Required**: Promote to `log_hook_event` (keep `_log_hook_event` as internal alias for one release), or expose a domain-specific helper `record_suppression_event(round, agents)` so the schema lives in one place. Lower priority than #1–#3.

#### 5. [ACCEPT] [Low] Comment claim "라운드당 정확히 1건" is config-fragile
- **Critic**: Per-round uniqueness only holds because `MAX_ROUNDS=2` — `warn_only_notified_at` is set once and never cleared. If `MAX_ROUNDS` is raised, the claim silently becomes false.
- **Cross**: not flagged (provider unavailable).
- **Judgment**: ACCEPT — comment is documentation of an invariant that depends on a constant defined elsewhere. Either tighten the comment, or make the invariant true regardless of `MAX_ROUNDS`.
- **Action Required**: Either rewrite comment to "marker-lifetime당 1건", or have `record_review_done` in `review_gate.py` clear `warn_only_notified_at` when it resets `round_started_at`. Low priority.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_log_hook_event` schema abuse | High | ACCEPT | Critic + diff |
| 2 | Bare `except: pass` masks regressions | High | ACCEPT | Critic + diff |
| 3 | Dual sys.path → module identity hazard | High | ACCEPT | Critic + diff |
| 4 | Private symbol cross-import | Medium | ACCEPT | Critic |
| 5 | Comment invariant config-fragile | Low | ACCEPT | Critic |

### Recommendations

- **Cheapest viable fix** (resolves #1+#2+#4 in one shot): add a public `record_suppression_event(round_count: int, agents_present: list[str])` to `scripts/hook_runner.py` that writes a properly typed JSONL line to `.af_review_queue/suppression_events.jsonl`. Replace the inline `_log_hook_event` call with this. Narrow the except to `(ImportError, AttributeError)`.
- **For #3**: drop the second `sys.path.insert` and change line 136 to `from hook_runner import _log_hook_event` (or its public replacement). The diff's added comment claims project-root is needed for hook subprocess resolution — verify this claim before applying; if `scripts/` on sys.path is sufficient (as the existing `from review_gate import` proves), the second insert is unnecessary.
- **For #5**: one-line comment tightening or a 3-line clear in `review_gate.record_review_done`.
- **Cross Review gap**: the Tier 3 cross-verification provider failed. Per CLAUDE.md ("Tier 3 fan-out … 1개 이상 인증 만료가 있으면 BLOCK + 재인증 안내"), confirm whether the Codex provider error is auth expiry or transient. If auth, re-authenticate and rerun before merge; if transient and no other provider was available, document the SKIP in the commit message.