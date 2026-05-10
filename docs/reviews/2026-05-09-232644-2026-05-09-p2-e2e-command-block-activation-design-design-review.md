# Design Review: 2026-05-09-p2-e2e-command-block-activation-design

> Source: docs/2026-05-09-p2-e2e-command-block-activation-design.md
> Date: 2026-05-09 23:26
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

4 Critical findings, 4 High, 3 Medium. Multiple v3 history claims are not reflected in the document body, and the core trigger chain (summarize → decision → BLOCK) is not wired.

### Aggregated Findings (11 total)

#### 1. [ACCEPT] [Critical] Decision generation not wired — BLOCK never fires
- **Critic**: `ApprovalGate.initialize()` does not call `summarize()`. grep confirms 0 hits for `summarize` or `WarningRegistry` in `approval_gate.py`. `_summary.json` is never created → `read_block_decision()` fail-opens → BLOCK permanently inactive.
- **Cross**: Same finding. `initialize()` only renders `approval-gate.md`. `_summary.json` absent at execute time.
- **Judgment**: Both reviewers agree with code-level evidence (grep, line refs). This is the design's central mechanism and it's broken.
- **Action Required**: §3.1/§3.2 must add explicit `WarningRegistry.summarize()` call either in `initialize()` or in `work_item_generator.py` between record writes and `gate.initialize()`. §9 must add acceptance test: "`prepare/generate_work_items` creates `_summary.json` and `_decision.json`".

#### 2. [ACCEPT] [Critical] §3.2/§7.3.3 — LLM prompt target is fallback, not main path
- **Critic**: line 556 is inside `_fallback_impl_tasks()` (static fallback on LLM failure). Actual LLM prompt at lines 773-800 has 0 occurrences of `e2e_command`. This was flagged in prior round and action was specified but v3 did not apply it.
- **Cross**: Not flagged directly, but Cross #2 depends on this (LLM can't fill what it's not asked for).
- **Judgment**: Strong single-source evidence with line-level verification. Prior-round regression confirms severity.
- **Action Required**: Retarget §3.2/§7.3.3 to `work_item_generator.py:787-788` (field enumerate) + `:798` (Rules block). Separate fallback path (line 556) into its own item.

#### 3. [ACCEPT] [Critical] §8.5 dispatch dict uses `SUBCOMMANDS` — baseline uses `_STAGE1_DISPATCH`
- **Critic**: v3 history item #2 claims this was fixed, but §8.5 body still says `SUBCOMMANDS`. Baseline dispatch router at line 553 reads `_STAGE1_DISPATCH`. Implementing as-written → `af warning-override` silently fails.
- **Cross**: Not flagged separately but covered by Cross #4 (deployment completeness).
- **Judgment**: Clear history ↔ body drift with baseline evidence. Implementer following §8.5 literally would produce dead code.
- **Action Required**: §8.5 replace `SUBCOMMANDS` → `_STAGE1_DISPATCH`, help block → `_STAGE1_USAGE`. §9 add: "`_STAGE1_DISPATCH['warning-override']` resolves to handler".

#### 4. [ACCEPT] [Critical] v3 history ↔ body multi-drift
- **Critic**: 3 of 7 v3 history items verified as not applied: (1) §5.4 fail-closed imports still outside `try:`, (2) `SUBCOMMANDS` persists (finding #3), (7) §9 title still says "23 케이스" but actual count is 26.
- **Cross**: Not flagged as a meta-finding, but individual instances overlap.
- **Judgment**: If claimed fixes aren't applied, v3 is effectively v2 with a new version number. All v2 BLOCK items remain live.
- **Action Required**: Author must grep-verify all 7 history items against body and apply each. Update §9 title to actual case count.

#### 5. [ACCEPT] [High] `# TODO:` placeholder contradicts "first run not blocked" goal
- **Critic**: `_task_template` emits `# TODO:` → `_is_e2e_missing()` treats it as missing → BLOCK on first P2 build. Combined with finding #2 (LLM prompt doesn't ask for `e2e_command`), there's no path to avoid BLOCK without manual override.
- **Cross**: Same finding. "The design's own missing rule makes those placeholders blocking."
- **Judgment**: Both reviewers agree. §0's core promise ("첫 실행이 즉시 막히지 않도록") is undeliverable under current design.
- **Action Required**: Choose one policy: (A) generate concrete defaults for inferable cases and only `# TODO:` for unknowns, treating generated placeholders as non-blocking; or (B) remove the "first run not blocked" claim from §0/§1 and make override the expected flow. Fix finding #2 (LLM prompt) regardless.

#### 6. [ACCEPT] [High] Frozen build gaps — hiddenimports + yaml bundling + smoke test
- **Critic**: Deferred imports won't be caught by PyInstaller static analysis. `config/escalation_policy.yaml` needs `datas` mapping for `_MEIPASS`. §9 has 0 frozen build acceptance tests.
- **Cross**: Flags deployment/version updates as incomplete. Notes `version.py` and `install-af.ps1` not listed.
- **Judgment**: Both reviewers flag deployment readiness from different angles. CLAUDE.md §3.3 M9 documents this as a known footgun.
- **Action Required**: §10 add `af.spec` `datas` entry for `config/escalation_policy.yaml`. §9 add frozen build smoke test: "`dist/af/af.exe warning-summary` runs without ImportError". Decide version bump and update `version.py`/`install-af.ps1` if applicable.

#### 7. [ACCEPT] [High] Phase upgrade migration not designed
- **Critic**: P2→P3 transition leaves old `_summary.json`/`_decision.json` with `escalation_phase: "P2"`. §6.1 fires `decision_phase_mismatch` BLOCK on all existing slugs. No migration policy.
- **Cross**: Not flagged.
- **Judgment**: Strong single-source evidence. Phase transitions are inevitable (P3/P4 explicitly planned). Without mitigation, every upgrade blocks all projects simultaneously.
- **Action Required**: §6.1 add "expected_phase ≥ decision_phase → pass (forward-compatible)" rule, or §3.1 mandate `summarize()` re-run on phase upgrade. Register in §11.1 risk table.

#### 8. [ACCEPT] [Medium] Override writes need locking + atomic replace
- **Critic**: `_build_summary` reads `_overrides.json` without lock specification. Race with CLI `warning-override`.
- **Cross**: Same finding. Notes existing registry uses `locked_file()` for jsonl and summaries.
- **Judgment**: Both agree. Consistency with existing locking patterns is straightforward.
- **Action Required**: §8.6 `warning_overrides.py` must use `locked_file(overrides_path + ".lock")` with read-modify-write + `os.replace`. §5.4 specify where `_build_summary` calls `load_overrides()`.

#### 9. [ACCEPT] [Medium] Backfill parser contract underspecified
- **Critic**: No regex, no task_id matching strategy, no failure handling. "best-effort, silent skip" for a critical BLOCK-avoidance mechanism.
- **Cross**: HOLD — needs exact accepted markdown pattern and conflict behavior.
- **Judgment**: Both flag. Escalating from HOLD to ACCEPT because this is a load-bearing mechanism (the only automatic BLOCK escape besides override). Without a parser contract, finding #5 remains unresolvable.
- **Action Required**: §7.4 define: (a) parser regex, (b) task_id extraction rule, (c) conflict/duplicate behavior, (d) §9 quantitative acceptance ("≥7/8 mock markdowns parsed correctly").

#### 10. [ACCEPT] [Medium] §11.2 rollback emergency env var missing from body
- **Critic**: v3 history item #4 promises "emergency env var" but §11.2 body has no `AF_DISABLE_*` variable. Only `AF_ESCALATION_PHASE` exists in §14 for a different purpose.
- **Cross**: Not flagged.
- **Judgment**: Another history ↔ body drift instance. Ops-critical: without env var, production unblock requires code hotfix.
- **Action Required**: §11.2 add `AF_DISABLE_ESCALATION_BLOCK=1` — checked at `read_block_decision()` entry. §9 add regression test.

#### 11. [REJECT] [Medium] Stale timestamp ISO 8601 timezone comparison
- **Critic**: Lexicographic comparison fails with mixed timezone offsets. Multi-PC scenario (§13 P6) would break.
- **Cross**: Rejects — `now_iso()` emits fixed-width local ISO without offsets. Lexicographic ordering is consistent for this code path.
- **Judgment**: Cross-review's evidence is stronger. Current `now_iso()` implementation produces consistent format. Multi-PC is P6 scope, not P2.
- **Note**: If future writers introduce offset-aware timestamps, revisit with `datetime.fromisoformat()` normalization.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Decision generation not wired | Critical | ACCEPT | Both |
| 2 | LLM prompt target is fallback | Critical | ACCEPT | Critic |
| 3 | Dispatch dict `SUBCOMMANDS` wrong | Critical | ACCEPT | Critic |
| 4 | v3 history ↔ body multi-drift | Critical | ACCEPT | Critic |
| 5 | `# TODO:` contradicts "not blocked" | High | ACCEPT | Both |
| 6 | Frozen build gaps | High | ACCEPT | Both |
| 7 | Phase upgrade migration missing | High | ACCEPT | Critic |
| 8 | Override locking missing | Medium | ACCEPT | Both |
| 9 | Backfill parser unspecified | Medium | ACCEPT | Both |
| 10 | Emergency env var missing from body | Medium | ACCEPT | Critic |
| 11 | Timezone comparison | Medium | REJECT | Critic vs Cross |

### Recommendations

1. **Fix v3 drift first**: grep-verify all 7 history items against body text, apply each, recount §9 cases
2. **Wire the trigger chain** (finding #1): add `summarize()` call after records, before/after `gate.initialize()`
3. **Retarget LLM prompt** (finding #2): move §3.2/§7.3.3 refs from fallback line 556 to actual prompt lines 787-798
4. **Fix dispatch variable** (finding #3): `SUBCOMMANDS` → `_STAGE1_DISPATCH` / `_STAGE1_USAGE` in §8.5
5. **Resolve TODO/first-run contradiction** (finding #5): pick a policy and align §0/§1/§7 consistently
6. **Add deployment + frozen build items** (finding #6): `af.spec` datas, hiddenimports, smoke test, version decision
7. **Add phase migration rule** (finding #7): forward-compatible phase comparison in §6.1
8. **Define backfill parser contract** (finding #9): regex + matching rules + quantitative acceptance
9. **Add emergency env var to §11.2 body** (finding #10): `AF_DISABLE_ESCALATION_BLOCK=1`
10. After all fixes applied, bump version to v4 and re-submit for review