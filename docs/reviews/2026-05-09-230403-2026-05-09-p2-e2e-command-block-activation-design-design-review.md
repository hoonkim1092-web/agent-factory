# Design Review: 2026-05-09-p2-e2e-command-block-activation-design

> Source: docs/2026-05-09-p2-e2e-command-block-activation-design.md
> Date: 2026-05-09 23:04
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

5 Critical/High wiring & contradiction findings (4 unique to Critic, 1 of which overlaps Cross). Cross adds 3 independent ACCEPTs on the evaluator/gate trigger contract. v3 must resolve all six top-tier items before re-review.

### Aggregated Findings (15 total)

#### 1. [ACCEPT] [Critical] §3.2/§7.3 cite wrong source line — LLM prompt enhancement targets fallback template
- **Critic**: line 556 is `_fallback_impl_tasks()` hardcoded markdown (lines 511-558); real LLM prompt is `_generate_implementation_tasks()` lines 773-800 with no `e2e_command` mention.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — concrete grep evidence; spec as written would only modify the fallback path (LLM-failure-only), defeating §7.3's BLOCK-avoidance mechanism.
- **Action**: §3.2/§7.3 retarget to `_generate_implementation_tasks()` lines 787-788 prompt format spec; add `e2e_command` to line 798 Rules block.

#### 2. [ACCEPT] [Critical] LLM markdown ↔ task_board e2e_command disconnect — backfill round-trip undefined
- **Critic**: `task_board.tasks[*].e2e_command` is built by `_normalize_tasks()` (project_task_board.py:463-500) **before** LLM, but missing-detection (work_item_generator.py:1049-1054) reads task_board. LLM only writes implementation-tasks.md. `_backfill_e2e_from_tasks_md` location/re-write semantics not specified.
- **Cross**: not directly flagged (Cross #1 covers a related wiring gap).
- **Judgment**: ACCEPT — without task_board re-write, prompt enhancement never reaches the BLOCK detector.
- **Action**: §7.4 specify (i) call site = work_item_generator.py:1037 (after tasks_content) before line 1048, (ii) mutate task_board dict + `write_project_board(workspace, task_board)`, (iii) parse failure → `_LOGGER.warning` and keep board.

#### 3. [ACCEPT] [Critical] `gate.initialize()` doesn't call `summarize()` — `_decision.json` may not exist before `execute()`
- **Critic**: not flagged.
- **Cross**: approval_gate.py:90 only renders `approval-gate.md`; nothing triggers decision generation.
- **Judgment**: ACCEPT — Cross supplied direct line evidence; without this, P2 BLOCK enforcement is dead code.
- **Action**: After warning records emit in `generate_work_items()`, call `WarningRegistry(workspace=workspace).summarize(project_slug=slug)` before `gate.initialize()` (or move responsibility into `ApprovalGate.initialize()` with workspace context). Add acceptance test asserting `_summary.json` + `_decision.{md,json}` exist post-prepare without manual CLI.

#### 4. [ACCEPT] [Critical] First P2 build BLOCKs every project at verify phase — §0.1 promise broken
- **Critic**: `_task_template` adds verify task with empty `e2e_command` (project_task_board.py:380-388). Policy `count_per_run_min=1` + `affected_phase_in:[verify]` → all first runs BLOCK. §0.1 ("BLOCK 활성에 의해 첫 실행이 즉시 막히지 않도록") directly violated.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — policy + template combination is verifiable and self-defeating.
- **Action**: Recommend (b) — temporarily remove `verify/code_review/cross_validate` from `affected_phase_in` until P3, OR (a) populate verify task `e2e_command="# TODO: <verify command for {task_id}>"` *and* resolve finding #5 to make `# TODO:` BLOCK-avoiding.

#### 5. [ACCEPT] [High] `# TODO:` semantics contradict between §3.2 and §7.3
- **Critic**: §3.2 line 113 says `# TODO:` counts as missing → BLOCK; §7.3 says `# TODO:` evades BLOCK; §11.1 introduces a third interpretation.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — internal contradiction; implementer must guess.
- **Action**: Pick one policy (recommend `# TODO:` = missing → BLOCK; only override unblocks). Delete §7.3 "BLOCK 회피" line; rewrite §11.1 placeholder risk row.

#### 6. [ACCEPT] [High] `inject_review_tasks` blocking is dead — runtime injection bypasses prepare-time scan
- **Critic**: §3.2 (+6 LOC marker) vs §7.2 (BLOCK 유지) contradict; deeper issue: inject_review_tasks runs at orchestration time, but missing-check runs once at work-item generation.
- **Cross**: dynamic_orchestrator.py:221 → project_task_board.py:1025 confirms post-build injection; warning scan at work_item_generator.py:1048 is prepare-time only.
- **Judgment**: ACCEPT (both flag same wiring gap with different angles, severity High).
- **Action**: Pick one: (a) drop runtime-injected phases from P2 BLOCK scope and document P2 = prepare-time only, OR (b) add `WarningRegistry.record(...) → summarize() → recompute decision` inside `inject_review_tasks()` plus orchestrator pause-on-block path.

#### 7. [ACCEPT] [High] `compute_run_decision(policy, current_phase)` ignores both arguments
- **Critic**: §4.3 `repeat_count` uses rule-wide `repeat_count_max` instead of phase-scoped value — breaks P3/P4 reuse where `owner_role_mismatch.repeat_count_min=3` is phase-scoped.
- **Cross**: signature accepts `policy`/`current_phase`, but pseudocode delegates to `evaluate(record)` which reloads policy and hardcodes `current="P2"` (escalation_evaluator.py:45-70).
- **Judgment**: ACCEPT — both flag the same evaluator/runner contract gap; merging required.
- **Action**: Split: `_evaluate_rule(record, rule, current_phase)` private helper, public `evaluate(record, *, policy=None, current_phase="P2")`. `compute_run_decision()` threads both injected values. Phase-scope `repeat_count` via `info["by_phase_repeat"][phase]`. Resolve §14 Q4 in §4.3 body.

#### 8. [ACCEPT] [High] Fail-closed semantics contradicted by fail-open implementation sketch
- **Critic**: not flagged.
- **Cross**: §3.2 claims fail-closed + stale detection, but §6.1 + §11.1 sketch returns `(False, None)` on missing/corrupt/stale.
- **Judgment**: ACCEPT — Cross shows direct prose contradiction; project_pipeline.py:1268 is sole enforcement point so semantics must be unambiguous.
- **Action**: Specify exact contract: missing → fail-open ONLY before any summary exists; stale, schema mismatch, JSON parse error, wrong `activate_phase` → blocked with `reason="decision_unreadable"` or `"decision_stale"`. Add explicit comparisons (`generated_from_summary_last_updated == _summary.json.last_updated`, `decision_schema_version == 1`, `activate_phase == "P2"`).

#### 9. [ACCEPT] [High] §5.4 holds yaml load + 2 atomic writes inside `summary_lock_path` (10s timeout)
- **Critic**: cold-start yaml load + 2 disk writes + concurrent `gate.initialize()` + CLI users → likely timeout under parallel slugs. §14 Q1 left open while body adopts the risky path.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — verifiable via locked_file timeout=10 in summarize() + work_item_generator.py:1087 + CLI subcommands sharing the same lock.
- **Action**: Pick (a) hoist `_load_policy()` outside lock and pass dict in, OR (b) move decision report writing outside summary lock with separate `_decision.md.lock`. Document order between `_summary.json` lock and decision lock.

#### 10. [ACCEPT] [Medium] §3.2 vs §10 LOC estimates inconsistent across 6 rows; totals don't reconcile
- **Source**: Critic.
- **Judgment**: ACCEPT — review scope-creep gating becomes ambiguous.
- **Action**: Drop LOC column from §3.2 OR sync §3.2 to §10 values (§10 is the latest checklist).

#### 11. [ACCEPT] [Medium] Two override sources (record-level `false_positive_override` vs `_overrides.json`) lack priority spec
- **Critic**: WarningRecord has `false_positive_override` (P1), P2 adds `_overrides.json`; conflict resolution + `_build_summary.any_override` semantics undefined.
- **Cross**: HOLD on rule-wide override breadth (#6) — adjacent concern.
- **Judgment**: ACCEPT — spec gap; semantic priority must be fixed before code lands.
- **Action**: §8 specify: (i) record-level FP affects only that record at evaluate time, (ii) `_overrides.json` rule entry → all phases marked false_positive, (iii) `any_override = OR(both sources)`, (iv) record-level FP impact on `count` field.

#### 12. [ACCEPT] [Medium] `config/escalation_policy.yaml` not registered in `af.spec datas` → frozen builds fall through fallback policy and silently disable BLOCK
- **Critic**: escalation_evaluator.py:14 reads `BASE_DIR/config/escalation_policy.yaml`; missing in frozen build → `{"version": 0, "rules": []}` → all records `rule_not_active` → BLOCK only works in dev.
- **Cross**: REJECT raised on **modules** (#5) — different artifact (modules vs YAML data file). Cross #5 rejection does not apply to the YAML packaging concern.
- **Judgment**: ACCEPT — distinct from Cross #5; verify `af.spec datas` includes `config/escalation_policy.yaml`; if absent, register.
- **Action**: §10 add datas verification line item; if missing, add to `af.spec`.

#### 13. [ACCEPT] [Medium] `_overrides.json` lacks lock; concurrent CLI write vs `_build_summary` read can expose partial state
- **Source**: Critic.
- **Judgment**: ACCEPT — `summary_lock_path` does not cover overrides file.
- **Action**: Add `overrides_lock_path` in §8.6; wrap `upsert_override`/`load_overrides`/`remove_override` in `locked_file(...)` + atomic-rename. `_build_summary` short-locks during `load_overrides`.

#### 14. [ACCEPT] [Low] §8.5 argparse subparser pattern doesn't match `run_factory_cli.py` flat dispatch
- **Critic**: actual run_factory_cli.py:281-291, 410-420 uses `SUBCOMMANDS = {...}` flat dict, not `sp.add_parser`. §3.2 mentions correct pattern; §8.5 contradicts.
- **Judgment**: ACCEPT — implementer following §8.5 will skip `SUBCOMMANDS` registration and `_STAGE1_USAGE` help.
- **Action**: Rewrite §8.5 code block as `argparse.ArgumentParser(prog="af warning-override")` + `args = parser.parse_args(rest)` matching `_run_warning_summary_subcommand`. Explicitly note SUBCOMMANDS + _STAGE1_USAGE updates.

#### 15. [HOLD] [Medium] Rule-wide override scope possibly too broad
- **Critic**: not flagged.
- **Cross**: a single override silences whole `e2e_command_missing` rule including future build/verify records.
- **Judgment**: HOLD — depends on operator workflow intent (temporary unblock vs evidentiary FP marking).
- **Question for Author**: Is override (a) temporary project-wide grace (add `expires_at`/`created_by`), or (b) evidentiary FP per-incident (use phase-level scope)? Decide before P3 since P3 adds rules.

#### Rejected
- **[REJECT]** **Cross #5**: New frozen-build modules not accounted for. Design §10 explicitly lists `core.escalation_decision_report` + `core.warning_overrides` in `af.spec hiddenimports`, consistent with af.spec:29 manual convention. Rejected by Cross itself.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §7.3 wrong line 556 | Critical | ACCEPT | Critic |
| 2 | LLM↔task_board backfill round-trip | Critical | ACCEPT | Critic |
| 3 | gate.initialize→summarize trigger missing | Critical | ACCEPT | Cross |
| 4 | First P2 BLOCKs verify phase universally | Critical | ACCEPT | Critic |
| 5 | `# TODO:` semantics contradiction | High | ACCEPT | Critic |
| 6 | inject_review_tasks dead-code/wiring | High | ACCEPT | Both |
| 7 | compute_run_decision policy/phase ignored + repeat scope | High | ACCEPT | Both |
| 8 | Fail-closed contradicts fail-open sketch | High | ACCEPT | Cross |
| 9 | yaml load + 2 writes inside 10s lock | High | ACCEPT | Critic |
| 10 | §3.2 vs §10 LOC mismatch | Medium | ACCEPT | Critic |
| 11 | Two override sources priority undefined | Medium | ACCEPT | Critic |
| 12 | escalation_policy.yaml frozen-build packaging | Medium | ACCEPT | Critic |
| 13 | `_overrides.json` concurrency lock missing | Medium | ACCEPT | Critic |
| 14 | §8.5 argparse pattern wrong | Low | ACCEPT | Critic |
| 15 | Rule-wide override breadth | Medium | HOLD | Cross |
| — | af.spec hiddenimports for new modules | — | REJECT | Cross |

### Recommendations

1. **Resolve findings #1–#9 in v3 before any implementation** — these are wiring/semantic contradictions that block coherent implementation.
2. **Make finding #4 (verify phase BLOCK) the gating decision first** — picking option (b) (defer phase from `affected_phase_in`) cascades simplifications into #5 and #6.
3. **Lock the contract triplet**: `evaluate(record, *, policy, current_phase)` + `compute_run_decision(summary, policy, *, current_phase)` + `_evaluate_rule()` (finding #7); fix `repeat_count` phase scope here.
4. **Specify decision-report fail-closed contract concretely** (finding #8) with the four equality checks.
5. **Add §3.2/§7.3/§7.4 source-of-truth update** locating LLM prompt at `_generate_implementation_tasks` and defining the `_backfill_e2e_from_tasks_md` call site + task_board re-write (findings #1, #2).
6. **Move yaml load out of summary lock**, or split decision lock (finding #9).
7. **Verify `af.spec` packages `config/escalation_policy.yaml`** before tagging release (finding #12).
8. **Answer HOLD #15** (override scope intent) — design choice not blocker but determines schema for `_overrides.json`.
9. After v3 patch, re-run cross-review (Tier 3 fan-out per CLAUDE.md `af-review` policy) to confirm contradictions are resolved.