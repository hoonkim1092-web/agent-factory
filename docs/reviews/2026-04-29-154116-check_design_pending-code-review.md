# Code Review: check_design_pending

> Source: scripts/check_design_pending.py
> Date: 2026-04-29 15:41
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings, but three High-severity issues exist that should be fixed before merge: hook reliability (uncaught exceptions, silent marker-write failures) and a duplicate-firing race against the existing watcher. Several Medium findings around silent error swallowing reinforce the same theme.

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] `main()` uncaught exceptions bypass `sys.exit(0)` — blocks UserPromptSubmit
- **Critic**: `if __name__ == "__main__": main(); sys.exit(0)` lets any exception in `main()` propagate, exiting with code 1 — exactly the failure mode the docstring (line 16) promises to prevent.
- **Cross**: not flagged
- **Judgment**: Strong evidence — docstring contract directly contradicted by code shape at `scripts/check_design_pending.py:140-142`. Single-reviewer but unambiguous.
- **Action Required**: Wrap `main()` in `try/except Exception` with stderr log and `finally: sys.exit(0)`.

#### 2. [ACCEPT] [High] `_save_fired()` silent write-failure causes infinite re-fire loop
- **Critic**: Outer `except Exception: pass` at line 70 swallows EACCES / disk-full / AV-lock; marker never updates → every prompt re-fires `[af-design-review-pending]` for the same docs with no diagnostic.
- **Cross**: not flagged
- **Judgment**: Strong evidence. Same pattern code-review.md catalogs as silent-fallback anti-pattern (Sec 3.3 M10 / 3.2.1 H5a).
- **Action Required**: At minimum print stderr on failure: `except Exception as e: print(f"[check_design_pending] failed to save fired marker: {e}", file=sys.stderr)`.

#### 3. [ACCEPT] [High] Pending prompt can duplicate active watcher reviews
- **Critic**: not flagged
- **Cross**: Hook fires based only on queue age; doesn't check `design_review_watcher.py` heartbeat. Watcher can spend `REVIEW_TIMEOUT+30` per item (`scripts/design_review_watcher.py:404-410`), during which queued items pass the 90s threshold and the user gets a manual `af-critic + af-cross-review` prompt while the watcher is already processing them.
- **Judgment**: Strong evidence with concrete file:line citations on both sides of the race. Real duplicate-work risk.
- **Action Required**: Check watcher heartbeat (via `core.design_review_utils` helper) before emitting the pending message; suppress when watcher is healthy. Also recheck queue files still exist before marking fired.

#### 4. [ACCEPT] [Medium] `_load_fired()` swallows `JSONDecodeError` → resets all firing history
- **Critic**: `except Exception: return {}` at lines 45-51 treats corrupt marker the same as missing marker; combined with #2 yields one re-fire per past entry.
- **Cross**: not flagged
- **Judgment**: Reasonable mitigation needed; differentiate `FileNotFoundError` from `JSONDecodeError`.
- **Action Required**: Catch `FileNotFoundError` for empty-state, log + rename to `.corrupt` for `JSONDecodeError`.

#### 5. [ACCEPT] [Medium] Inner queue-entry read failures drop entries silently forever
- **Critic**: `try: ... except Exception: continue` at lines 90-97 — broken queue entries (mid-write, missing/invalid `timestamp`) lurk indefinitely; never reviewed, never surfaced.
- **Cross**: not flagged
- **Judgment**: Same silent-failure family. Diagnostic-only fix.
- **Action Required**: Print stderr per skipped entry; consider quarantining after N failures.

#### 6. [ACCEPT] [Medium] `MIN_BATCH_INTERVAL_SEC = 90` not env-overridable
- **Critic**: Hard-coded quiet window blocks CI smoke tests / demos. Other AF hooks (`review_gate`) accept env bypass.
- **Cross**: not flagged
- **Judgment**: Consistency with sibling hooks; trivial fix.
- **Action Required**: `MIN_BATCH_INTERVAL_SEC = int(os.environ.get("AF_DESIGN_REVIEW_QUIET_SEC", "90"))`.

#### 7. [HOLD] [Medium] Concurrent hook runs race the marker file
- **Critic**: Read-modify-write of marker has no locking; near-simultaneous prompts could double-fire the agent set. `core/file_lock.py` exists.
- **Cross**: not flagged
- **Judgment**: Critic itself notes "UserPromptSubmit hooks rarely race in practice." Real but low-probability; needs author input on whether to lock or just document.
- **Question for Author**: Acceptable to document the race assumption in the docstring, or do you want `core.file_lock` wrapping the read-decide-write block?

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `main()` exceptions bypass exit(0) | High | ACCEPT | Critic |
| 2 | `_save_fired` silent failure → re-fire loop | High | ACCEPT | Critic |
| 3 | Watcher duplicate-firing race | High | ACCEPT | Cross |
| 4 | `_load_fired` JSON corruption swallowed | Medium | ACCEPT | Critic |
| 5 | Inner queue-entry read silently drops | Medium | ACCEPT | Critic |
| 6 | `MIN_BATCH_INTERVAL_SEC` not env-overridable | Medium | ACCEPT | Critic |
| 7 | Marker-file concurrency race | Medium | HOLD | Critic |

### Recommendations

- Fix #1, #2, #3 before merge — all three break the script's own correctness contract.
- Bundle #4, #5 with #2: they are the same silent-failure family. Add stderr diagnostics consistently.
- #6 is a one-line change; do it now while touching the file.
- For #7, either add `core.file_lock` around lines 102-137 or add a docstring note acknowledging the race window — confirm preference with the author.
- Note: Cross Review's two REJECTs (commented-out `candidates.append`, shared-constants import) were self-rejected by Cross with valid evidence (`py_compile` passes; sys.path constraint from settings.local.json). Not carried forward.