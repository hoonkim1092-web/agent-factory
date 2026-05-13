# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:23
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

> **Note**: Cross Review failed with a provider error (`gpt-5.5` model unavailable / Codex stdin read failure). Aggregation is based on Critic Review only. Recommend re-running Tier 3 cross-review with a valid model before final sign-off.

### Aggregated Findings (10 total + 4 missing-from-design)

#### 1. [ACCEPT] [Critical] Identifier regression — `"local"` not in `blast_radius` enum
- **Critic**: §3.2 line 157 lists `{"local","module","cross_module","system_wide"}`, but real enum in `core/control/change_impact.py:16,35,221-243` is `{"isolated","module","cross_module","system_wide"}` (line 243: `return "isolated"`).
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. Evidence is direct code reference, and memory `feedback_design_doc_grep_before_write.md` confirms this is regression #4 of the same class. The document itself documents prior identical regressions at §3.3 lines 184-187.
- **Action Required**: Replace `"local"` → `"isolated"` in §3.2 line 157. Add §3.5 verification #6 to forbid the literal token `"local"` from `core/approval_gate.py`. Run `grep -nE 'blast_radius\s*==\s*"[^"]+"' core/approval_gate.py` before publishing.

#### 2. [ACCEPT] [Critical] `new_project` work_kind silently skips `blast_radius` profiling
- **Critic**: `core/control/intake.py:110-115` invokes `_profile_change_impact()` only for `{"maintenance","bugfix","refactor","feature_update"}`. `new_project` (5th enum at `core/control/work_kind.py:9`) falls back to `"module"` literal → never triggers `require_domain_review()`.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Specific code-path reference. Greenfield projects are exactly where domain decisions matter most.
- **Action Required**: Choose option (a) extend `intake.normalize()` to profile `new_project`, OR (b) extend `require_domain_review()` to fire on `work_kind == "new_project"` regardless of blast_radius. Document chosen path in §3.3 + add §3.5 verification.

#### 3. [ACCEPT] [High] Phase A LOC totals self-contradict
- **Critic**: §3.2 sums to ~195 LOC Python; §7.1 lists test file as ~80 LOC (not 30); §7.5 declares ~140 LOC total. Three numbers disagree by ±55 LOC (~40% of budget).
- **Cross**: not flagged
- **Judgment**: ACCEPT. Arithmetic inconsistency, falsifiable.
- **Action Required**: Pick one test-file LOC (30 vs 80), recompute §7.5 explicitly.

#### 4. [ACCEPT] [High] `maintenance_pipeline.py:310` + `verify_handoff_checker.py:104` ApprovalGate callers unanalyzed
- **Critic**: 4 production `ApprovalGate(` call sites exist; doc only addresses 2 (`project_pipeline.py:1516`, `agent_launcher.py:437-441`). `maintenance_pipeline.py:310` passes `self._workspace` directly (no `runtime_workspace`, no `doc_root`) → breaks the §3.2 doc_root contract.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Missing callers will cause false blocks or stale reads in maintenance runs with external `target_path`.
- **Action Required**: Add both call sites to §3.2 "caller 갱신 필수" list; either pass `doc_root` consistently or document exemption.

#### 5. [ACCEPT] [High] §4.4 retains numeric `우선순위` column despite §4.3 retiring its formula
- **Critic**: §4.3 explicitly retires `(C-B)×(10/D)`; §4.4 table still shows numeric values (9, 8, 3, -1) computed by that formula. Readers cannot tell whether classification follows the retired formula or the new "정성 + trigger" rules.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Internal contradiction encourages silent re-introduction of the retired formula.
- **Action Required**: Replace `우선순위` numeric column with `분류` text column (즉시/선택적/보류) + 1-line trigger rule justification per row.

#### 6. [ACCEPT] [Medium] `AF_SKIP_DOMAIN_REVIEW=1` bypass logging has no defined owner
- **Critic**: §3.3 defines `require_domain_review()` as pure boolean function, but mandates audit log to `.af_runtime/hook_events.log`. Pure functions don't write logs.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Without a single owner, audit obligation will lapse (precedent: `AF_SKIP_REVIEW_GATE`).
- **Action Required**: Specify `ApprovalGate.approve()` as the single point that consults env var AND writes log (near `last_block_reason` write); keep `require_domain_review()` pure.

#### 7. [ACCEPT] [Medium] §3.5 verification #7 confuses dict-key vs filename semantics
- **Critic**: `compute_snapshots()` (core/approval_gate.py:378-384) iterates `_DOC_FILES.items()` keyed by dict key, not filename. Whether `domain_review` appears is a static-code property, not a runtime fixture outcome. Proposed test would trivially pass.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Test would not catch the intended regression.
- **Action Required**: Re-phrase #7 as static assertion: `assert "domain_review" not in core.approval_gate._DOC_FILES` + `assert _DOMAIN_REVIEW_FILE == "domain-review.md"`. Move runtime check elsewhere.

#### 8. [ACCEPT] [Medium] §10.2 stage-transition has no rollback / emergency-stop
- **Critic**: Forward path documented (manual commit to advance stage 2/3); reverse path absent. If stage 2 over-blocks, only per-invocation `AF_SKIP_DOMAIN_REVIEW=1` exists — no global demotion mechanism.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Operational gap.
- **Action Required**: Add `policy.yaml:domain_review_stage: 1|2|3` knob read by `require_domain_review()` for single-commit rollback.

#### 9. [HOLD] [Medium] MIT attribution pointer fan-out
- **Critic**: Hard-coding `obra/superpowers/<skill_id>` in every absorbed SKILL.md creates dead-pointer risk on upstream rename.
- **Cross**: not flagged
- **Judgment**: HOLD. MIT compliance does not require working URLs (only attribution); centralization is a durability nice-to-have, not a correctness issue. Author should decide centralization vs distribution based on maintenance preference.
- **Question for Author**: Prefer centralized `docs/ATTRIBUTIONS.md` (single point of update) or distributed per-skill `inspired_by` paths (locality)?

#### 10. [ACCEPT] [Low] §3.5 #6 grep is too broad
- **Critic**: Naive `grep blast_radius` catches comments/docstrings/parameters. Restrict to string literal comparison values.
- **Cross**: not flagged
- **Judgment**: ACCEPT. Trivial precision fix.
- **Action Required**: Specify regex `grep -nE 'blast_radius\s*==\s*"[^"]+"' core/approval_gate.py`; assert only `"system_wide"` appears.

#### Missing-from-Design (4 items, all ACCEPT)

**M1.** [Medium] Concurrent `domain-review.md` write semantics — §3.4 mandates exactly one `- verdict:` line, but file is plain markdown editable concurrently by humans/agents (multi-PC scenario §3.2 line 127). No file-lock or verdict-only-file alternative discussed.

**M2.** [High] Phase B execution path — §4 lists deliverable without specifying who runs the matrix (Claude? Codex per Q3?) or how Superpowers source is read (clone? cached zip?). §5.2 forbids importing/fetching Superpowers, but Phase B *measurement* needs source access. Boundary is ambiguous.

**M3.** [High] Frozen build compatibility — §7.4 covers `af.spec hiddenimports` for `.py` files, but new artifacts are markdown in `docs/`. Frozen builds don't bundle `docs/`. Specify whether `af.exe` needs runtime access to `PROJECT_CONTEXT.md` / ADRs / `_template/domain-review.md`; if yes, add PyInstaller `datas` entry.

**M4.** [Medium] Test coverage matrix drift — §3.5 lists 12 verification items; only 2 reference `tests/test_approval_gate_domain_review.py`. Items #5–#9 unassigned to specific test files.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `"local"` enum regression | Critical | ACCEPT | Critic |
| 2 | `new_project` skips trigger | Critical | ACCEPT | Critic |
| 3 | Phase A LOC inconsistency | High | ACCEPT | Critic |
| 4 | maintenance_pipeline.py caller unanalyzed | High | ACCEPT | Critic |
| 5 | §4.4 numeric column vs §4.3 retirement | High | ACCEPT | Critic |
| 6 | bypass logging owner undefined | Medium | ACCEPT | Critic |
| 7 | §3.5 #7 dict-key/filename confusion | Medium | ACCEPT | Critic |
| 8 | §10.2 rollback path missing | Medium | ACCEPT | Critic |
| 9 | MIT attribution fan-out | Medium | HOLD    | Critic |
| 10 | §3.5 #6 grep precision | Low | ACCEPT | Critic |
| M1 | concurrent verdict write | Medium | ACCEPT | Critic |
| M2 | Phase B execution path | High | ACCEPT | Critic |
| M3 | Frozen build markdown access | High | ACCEPT | Critic |
| M4 | Test coverage matrix drift | Medium | ACCEPT | Critic |

### Recommendations

1. **Fix the 2 Criticals first** (#1 enum regression, #2 new_project gap) — both involve code-level evidence and one is a 4th-time regression that memory `feedback_design_doc_grep_before_write.md` flagged.
2. **Run `grep -nE 'blast_radius\s*==\s*"[^"]+"' core/control/change_impact.py core/approval_gate.py core/work_item_generator.py` before re-publishing** — verify every literal in the design doc matches code verbatim.
3. **Inventory all `ApprovalGate(` call sites** with `grep -rn 'ApprovalGate(' core/ scripts/` and address all 4 (not just 2) in §3.2.
4. **Re-run Tier 3 af-cross-review** — Codex provider error means we have no second-vendor signal; current verdict relies on Critic alone.
5. **Resolve §4.3/§4.4 contradiction** by deleting numeric `우선순위` column.
6. **Add rollback knob** to §10.2 (policy.yaml stage gate) before stage 2 is enabled.
7. **Triage M2/M3** (Phase B execution path + frozen build) before any Phase B work begins.
8. **Defer #9** until author decides durability preference.

**Per memory `feedback_design_review_rounds_stop_rule.md`**: This is round 4 of identifier regression on the same document. If round 5 surfaces another identifier issue, freeze the document and migrate remaining items to an ADR rather than continuing to patch.