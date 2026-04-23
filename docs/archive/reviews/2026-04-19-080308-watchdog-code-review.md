# Code Review: watchdog

> Source: core/watchdog.py
> Date: 2026-04-19 08:03
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Critic review was unavailable (timeout/error). Verdict is based solely on Cross Review. Three independently verified, reproducible bugs were found — one of which causes JSON serialization failure on every `save_state()` call.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [Critical] `_VALID_LEVELS` dataclass field breaks JSON serialization
- **Critic**: not available
- **Cross**: `dataclasses.asdict()` includes `_VALID_LEVELS: frozenset`, causing `TypeError` on every `save_state()` call
- **Judgment**: Directly reproduced. Breaks `core/nightly_state.py:153-157`, `scripts/nightly_tick.py:199,217`, `run_factory_cli.py:197,226`. Zero workaround — the app cannot persist state.
- **Action Required**: Change `_VALID_LEVELS` to `ClassVar[frozenset[str]]` at `core/watchdog.py:86-88`, or move it to module scope.

#### 2. [ACCEPT] [High] `lineage_counters` outer type not validated in `from_dict()`
- **Critic**: not available
- **Cross**: `WatchdogState.from_dict({"lineage_counters": [1]})` raises `AttributeError: 'list' has no attribute 'items'`; matches BUG-15 in `docs/code_review/code-review.md`
- **Judgment**: Load path used by `scripts/nightly_tick.py:190` and `run_factory_cli.py:187,224,255`. A corrupted snapshot crashes the process rather than recovering.
- **Action Required**: Add `if not isinstance(raw_counters, dict): raw_counters = {}` at `core/watchdog.py:95` before the `.items()` iteration.

#### 3. [ACCEPT] [High] `WatchdogState` and `LineageLedger` write incompatible schemas to the same file
- **Critic**: not available
- **Cross**: `NightlyState` writes map-shape `{"L1": {"level": 6, ...}}` to `.af/lineage_ledger.json`, but `LineageLedger` expects `{"entries": [...]}`. Same file, two contracts — `is_maxed()` returns wrong results.
- **Judgment**: Directly affects `core/dynamic_orchestrator.py:759-812` and `core/fsa_loop.py:132-267` max/degrade decisions. Contradicts `docs/2026-04-18-nightly-autonomous-pipeline.md:154-168`.
- **Action Required**: Pick one schema. Either (a) teach `LineageLedger` to load the map shape, or (b) stop writing `.af/lineage_ledger.json` from `NightlyState` and use only `state_snapshot.json` as the persistence source.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_VALID_LEVELS` frozenset serialization crash | Critical | ACCEPT | Cross |
| 2 | `lineage_counters` outer type not guarded | High | ACCEPT | Cross |
| 3 | Dual schema on `lineage_ledger.json` | High | ACCEPT | Cross |

### Recommendations

- Fix finding #1 first — it is a hard crash on every save.
- Fix finding #2 with a one-liner guard before merging.
- For finding #3, decide on a single owner for `.af/lineage_ledger.json` and remove the competing write path. Document the chosen schema in `docs/code_review/code-review.md`.
- Add smoke tests: `save_state(NightlyState(), tmp_path)` round-trip; `from_dict({"lineage_counters": [1]})` graceful fallback; lineage max/history preserved across save→load cycle.
- Re-run the critic after fixes (it timed out this round); confirm no additional findings.