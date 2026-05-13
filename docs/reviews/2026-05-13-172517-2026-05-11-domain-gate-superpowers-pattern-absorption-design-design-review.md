# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:25
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

1 Critical finding (§3.3 trigger condition timing-incompatible) makes the central Phase A mechanism dead in production paths. Must be resolved before implementation.

> **Cross Review Note**: The cross-verification reviewer (Codex) terminated with a provider error and produced no findings. All judgments below rely solely on the Critic review. Per aggregation rule #2, findings with strong code/document evidence are ACCEPTED; weaker findings are HELD. A re-run of af-cross-review is recommended once the provider issue is resolved, but the Critical finding alone justifies BLOCK without it.

### Aggregated Findings (8 total + 4 missing-design items)

#### 1. [ACCEPT] [Critical] `blast_radius == "system_wide"` trigger is timing-incompatible
- **Critic**: Three code facts make the trigger nearly unfireable at gate-evaluation time: (a) `core/control/intake.py:110` excludes `new_project` from impact analysis → `change_impact == {}`; (b) `core/control/change_impact.py:119,222-227` computes `blast_radius` from `git diff --name-only HEAD`, but the gate runs at planning time before any commit; (c) `system_wide` requires `file_count >= 10` OR a `core/` file — both require post-implementation state.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Evidence is concrete — three independent code locations cited with line numbers. The design's central trigger condition fundamentally cannot fire when the gate is supposed to evaluate.
- **Action Required**: Rework §3.3. Either (a) trigger on planning-time signals (`work_kind == "new_project"`, new modules in `project_brief`, task-board diff), or (b) reposition the gate as a post-implementation "domain post-review" with honest naming.

#### 2. [ACCEPT] [High] `last_block_reason` enum contradicts rejected-frontmatter decision
- **Critic**: §3.2 line 112 explicitly rejects YAML frontmatter (uses Markdown `## Metadata` block), but the `last_block_reason` enum keeps the string `"missing_domain_frontmatter"`. Operators reading hook_events.log will search for a YAML block that doesn't exist.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Internal contradiction within the design itself; trivial to verify.
- **Action Required**: Rename enum value to `"missing_metadata_section"` (or `"missing_blast_radius_metadata"`). Apply same rename to §13 cross-review checklist.

#### 3. [ACCEPT] [High] Auto-approve path silently discards `approve()` False return — flow-stop unspecified
- **Critic**: `core/project_pipeline.py:1516` currently calls `_gate.approve(approver="auto", ...)` with bool discarded. §3.2 says "False면 자동 실행 흐름 중단" without specifying mechanism (exception? early return? caller contract?). The fail-closed contract is undefined exactly where it matters most.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Specification gap in the highest-risk code path.
- **Action Required**: Specify contract — e.g., "auto path returns `{"ok": False, "reason": gate.last_block_reason}` and skips `self.execute(...)`". Add regression test asserting `execute()` is NOT called when `approve()` returns False in auto mode.

#### 4. [ACCEPT] [High] `domain-review.md` excluded from `_DOC_FILES` creates tamper-evidence hole
- **Critic**: §3.2 line 122 deliberately excludes `domain-review.md` from `_DOC_FILES` (to avoid bulk-invalidating legacy work-items) — but this means a user can flip `- verdict: BLOCK` → `- verdict: PASS` post-approval undetected. Other 5 work-item docs have SHA snapshots; this one doesn't.
- **Cross**: not flagged
- **Judgment**: ACCEPT. The trade-off solves migration risk but creates a real integrity hole.
- **Action Required**: Add `_DOMAIN_REVIEW_HASH` slot snapshotted alongside `_DOC_FILES` but under distinct key, so `check_validity()` short-circuits cleanly when file is absent on legacy work-items.

#### 5. [ACCEPT] [Medium] §4.5 verification rule contradicts §4.3 priority-formula disposal
- **Critic**: §4.3 disposes the numeric priority formula and replaces with 3 named tiers; §4.5 #3 then asks reviewer to identify "priority ≥ 5" candidates — using the disposed metric.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Internal contradiction; trivial.
- **Action Required**: Replace §4.5 #3 with "최소 1개 '즉시 흡수' 또는 '선택적 흡수' 분류 산출".

#### 6. [ACCEPT] [Medium] §5.3 #3 demands synthetic `skill-usage.jsonl` entry for passive guidance skill
- **Critic**: `systematic-debugging` is a 4-phase guidance markdown for human/agent reading. The "≥1 ledger entry" gate forces a ceremonial invocation that produces no real signal.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Verification design doesn't match the artifact's nature.
- **Action Required**: Replace with load test (skill loader returns object) + content-shape assertion (4 phases present). Drop usage-count requirement.

#### 7. [HOLD] [Medium] Phase A LOC budget under-counts data-flow plumbing
- **Critic**: §7.5 estimates ~140 Python LOC for Phase A, but §3.2 itself enumerates 4+ wiring tasks (normalize() wiring, dataclass fields, signature propagation, two caller updates) plus ApprovalGate changes (init, 6-state enum, verdict parser, _DOMAIN_REVIEW_FILE, bypass, hook log). Honest estimate ~200–250 LOC.
- **Cross**: not flagged
- **Judgment**: HOLD. Estimation accuracy is a concern but not a correctness blocker. The ±50% disclaimer arguably covers this if interpreted broadly.
- **Question for Author**: Re-cost Phase A row-by-row in §3.2 — do you stand by 140 LOC after itemized rollup, or is the figure stale from before §3.2's latest wiring additions?

#### 8. [ACCEPT] [Medium] Bypass audit trail is local-only — breaks multi-PC governance
- **Critic**: `.af_runtime/hook_events.log` is gitignored and not in `start_db.py`/`end_db.py` sync set per CLAUDE.md. Bypass on PC A leaves no trace for reviewer on PC B.
- **Cross**: not flagged
- **Judgment**: ACCEPT. For a *domain governance* gate, local-only audit is the wrong durability tier.
- **Action Required**: Route bypass events to either `data/skill-usage.jsonl` (already synced) or a new `domain_gate_bypass` slot in the claude_memory push set.

#### 9. [ACCEPT] [Medium] ADR filename concurrency / race not handled for auto-pipeline
- **Critic** (Missing from Design): Same-minute ADR creations in `auto_run` parallel work-items are not "rare" in CI/cron. Need `-{4-char-uuid}` suffix or file-lock atomic creator.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Auto-pipeline parallelism makes this non-hypothetical.
- **Action Required**: Add UUID suffix to ADR filename format, or document atomic creation strategy.

#### 10. [ACCEPT] [Medium] Frozen build datas missing for docs/decisions and templates
- **Critic** (Missing from Design): §7.4 only checks `af.spec` hiddenimports. Doesn't verify `docs/decisions/` and `docs/PROJECT_CONTEXT.md` resolve from frozen-exe CWD, nor that `domain-review.md` template ships in PyInstaller `datas`.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Frozen-build resolution paths are a known AF blast surface (per Blueprint conventions).
- **Action Required**: Add explicit checklist item to §7.4: "templates and docs/decisions/ resolve from `_MEIPASS` or fallback to doc_root".

#### 11. [HOLD] [Medium] Legacy work-item migration impact unmeasured
- **Critic** (Missing from Design): When step 2 promotes `requires_domain_review = True` for `system_wide`, existing work-items with `blast_radius: system_wide` in their Metadata will fail. Migration plan doesn't enumerate count.
- **Cross**: not flagged
- **Judgment**: HOLD. Mitigation depends on actual count — could be 0 (if metadata field was just introduced) or many.
- **Question for Author**: Run `grep "blast_radius: system_wide" docs/work-items/*/approval-gate.md` and report count before promoting step 2.

#### 12. [ACCEPT] [Medium] `review_gate.py` vs `approval_gate.py` is a fork, not a design
- **Critic** (Missing from Design): §5.1 lists both as either-or — git-hook vs in-process contexts differ.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Either-or in a verification spec is unactionable.
- **Action Required**: Pick one in §5.1 and justify; or specify when each applies.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `blast_radius` trigger timing-incompatible | Critical | ACCEPT | Critic |
| 2 | Enum string contradicts frontmatter decision | High | ACCEPT | Critic |
| 3 | Auto-approve False return semantics unspecified | High | ACCEPT | Critic |
| 4 | `domain-review.md` integrity hole | High | ACCEPT | Critic |
| 5 | §4.5 vs §4.3 priority contradiction | Medium | ACCEPT | Critic |
| 6 | systematic-debugging ledger gate is ceremonial | Medium | ACCEPT | Critic |
| 7 | Phase A LOC estimate stale | Medium | HOLD | Critic |
| 8 | Bypass audit local-only | Medium | ACCEPT | Critic |
| 9 | ADR filename race in auto-pipeline | Medium | ACCEPT | Critic |
| 10 | Frozen build datas missing | Medium | ACCEPT | Critic |
| 11 | Legacy migration impact unmeasured | Medium | HOLD | Critic |
| 12 | `review_gate` vs `approval_gate` fork | Medium | ACCEPT | Critic |

### Recommendations

Before implementing Phase A:

1. **Rework §3.3 trigger** (Critical #1) — pick planning-time signals or reposition the gate. This is the BLOCK condition.
2. **Pin auto-approve fail-closed contract** (#3) — write the explicit `{"ok": False, "reason": ...}` shape and add the regression test.
3. **Add `_DOMAIN_REVIEW_HASH` slot** (#4) — preserve tamper evidence without bulk-invalidating legacy work-items.
4. **Rename `missing_domain_frontmatter` enum** (#2) — trivial, do it now.
5. **Fix §4.5 #3** (#5) — replace "priority ≥ 5" with tier-based criterion.
6. **Drop usage-count gate for systematic-debugging** (#6) — load + shape test only.
7. **Re-cost Phase A LOC bottom-up** (#7) — confirm or revise §7.5 estimate.
8. **Route bypass audit to synced channel** (#8) — skill-usage.jsonl or claude_memory.
9. **Add UUID suffix to ADR filenames** (#9) — auto-pipeline concurrency safety.
10. **Add §7.4 frozen-build datas checklist** (#10) — docs/decisions/, PROJECT_CONTEXT.md, domain-review.md template.
11. **Resolve §5.1 fork** (#12) — choose review_gate.py xor approval_gate.py with clear context.
12. **Re-run af-cross-review** once provider error is resolved, to surface anything Codex would have caught.