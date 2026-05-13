# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:23
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

> **Note on Cross Review**: The cross-reviewer (Codex) errored out mid-prompt — output ends with "You will receive: 1. A design/f)" and never produced findings. All judgments below derive from the Critic alone; per aggregation rule 3, single-source findings with strong code evidence ACCEPT, weaker ones HOLD.
>
> **3-round cap reminder** (per [[feedback_design_review_rounds_stop_rule]]): `docs/reviews/` shows 10+ reviews of this same document on 2026-05-13. We are well past the 4th-round freeze. The findings below should be triaged as **immediate fixes vs. ADR-deferral**, not invite another full revision round.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] §3.2 vs §7.2 — caller files dropped from integration table
- **Critic**: §7.2 "전체 통합" view omits `agent_launcher.py` and `core/project_pipeline.py` despite §3.2 listing them.
- **Cross**: not produced (provider error).
- **Judgment**: Strong evidence — `grep` confirmed only two non-test bool-path callers exist, and §7 self-claims to be the integration view. Implementer reading §7.2 alone breaks the gate.
- **Action Required**: Add both callers to §7.2 with "Phase A required" tag.

#### 2. [ACCEPT] [Critical] `domain-review.md` excluded from snapshots ⇒ post-approve verdict edits bypass the gate
- **Critic**: `compute_snapshots()` only iterates `_DOC_FILES`; `is_execution_open()` won't see verdict flipped to BLOCK after `approve()`.
- **Cross**: not produced.
- **Judgment**: Strong — concrete attack/error path with line refs (`core/approval_gate.py:378-384`, L242-257). The design's own "fail-closed" claim in High #6 resolution is violated.
- **Action Required**: Either re-call `_read_domain_review_verdict()` inside `is_execution_open()`, or track verdict via sidecar hash. Add a Phase A test: flip verdict→BLOCK after approve() and assert `is_execution_open()==False`.

#### 3. [ACCEPT] [High] §3.2 example Metadata block conflates approval-gate.md and domain-review.md
- **Critic**: Single fenced block mixes `work_kind`/`blast_radius` (approval-gate.md) with `verdict` (domain-review.md). `_parse()` happily accepts the verdict if mis-placed.
- **Cross**: not produced.
- **Judgment**: Strong — invariant ("verdict file is source of truth") silently breakable.
- **Action Required**: Split into two fenced blocks with distinct headings; remove `verdict` line from the approval-gate sample.

#### 4. [ACCEPT] [High] `project_pipeline.py:1516` auto-approve path semantics under-specified
- **Critic**: `_gate.approve(approver="auto", ...)` discards return; design says "자동 실행 흐름 중단 + reason 로깅" but doesn't pick between raise/return-dict/silent-skip. §3.5 verification matrix lacks this row.
- **Cross**: not produced.
- **Judgment**: Strong — three valid interpretations, affects every CLI hot-path invocation.
- **Action Required**: Specify the exact shape (recommend structured dict matching `agent_launcher.py:441`). Add §3.5 row for the auto-approve False branch.

#### 5. [ACCEPT] [High] §4.4 priority column inconsistent with §4.3 retired formula
- **Critic**: §4.3 retired `(C-B)×(10/D)`; §4.4 still publishes integer priorities (9, 8, 3, -1, -2, -3) with no rule producing them.
- **Cross**: not produced.
- **Judgment**: Strong — published artifact has a column unsupported by any documented rule.
- **Action Required**: Replace "우선순위" with `즉시 흡수 / 선택적 / 보류` buckets, or drop the column and add the "분류 사유" column §4.3 promises.

#### 6. [ACCEPT] [Medium] `_copy_extra_templates()` installs `domain-review.md` unconditionally
- **Critic**: At `core/work_item_generator.py:1394`, `extra` is unconditional. Every work-item (incl. `isolated`/`module`) gets the empty template → users assume review is required → exactly the false-positive §3.3 was trying to avoid.
- **Cross**: not produced.
- **Judgment**: Strong, concrete code ref.
- **Action Required**: Gate copy on `blast_radius == "system_wide"`, or prefix template body with an applicability disclaimer.

#### 7. [ACCEPT] [Medium] `work_kind` in metadata is dead data per the design's own rule
- **Critic**: §3.3 says `require_domain_review(blast_radius)` is `work_kind`-agnostic. Storing `work_kind` violates CLAUDE.md "추측성 코드 금지".
- **Cross**: not produced.
- **Judgment**: Strong — design contradicts its own simplicity rule.
- **Action Required**: Drop `work_kind` from the Metadata write path; reintroduce in §10.2 단계 4 when actually consumed. Update the host-stack diagram.

#### 8. [ACCEPT] [Medium] §3.4 vs §9 Risk #1 — PROJECT_CONTEXT stale check scope contradiction
- **Critic**: §3.4 says "Phase A 포함"; §9 Risk #1 says "Phase D, 본 설계 범위 외". Binding scope ambiguous.
- **Cross**: not produced.
- **Judgment**: Clear doc-internal contradiction.
- **Action Required**: Pick one. If Phase A, add §3.5 row for the stale check; if Phase D, strip the Phase-A wording from §3.4.

#### 9. [ACCEPT] [Medium] Verdict parser strictness causes silent UX failures
- **Critic**: 4 checkbox lines + canonical line; a reviewer editing `- [x] verdict: PASS` triggers `multiple_verdicts`. Case `pass`/`Pass` silently rejected.
- **Cross**: not produced.
- **Judgment**: Mixed — the strictness rule is defensible (fail-closed), but UX collision with checkbox lines is real.
- **Action Required**: Either (a) make template checkbox lines NOT start with `- ` (cheap fix, avoids pattern collision), or (b) accept case-insensitive with documented `.upper()`. Add a §3.5 row for the case-mismatch failure mode.

#### 10. [ACCEPT] [Low] `ControlPlaneIntake()` double-instantiation
- **Critic**: §3.2 adds `ControlPlaneIntake().normalize(...)` to `prepare_documents()` while `project_pipeline.py:710` already calls `ControlPlaneIntake()._recall_from_memory()`. Two instances per request; ledger duplication risk.
- **Cross**: not produced.
- **Judgment**: Real but mostly cosmetic — downgrade to Low. Don't block on this; flag for cleanup.
- **Action Required**: Reuse a single instance across both call sites, or route `_recall_from_memory` through `normalize()`.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §3.2 vs §7.2 caller files missing | Critical | ACCEPT | Critic |
| 2 | `domain-review.md` snapshot gap → post-approve bypass | Critical | ACCEPT | Critic |
| 3 | Metadata block conflates two files | High | ACCEPT | Critic |
| 4 | Auto-approve `project_pipeline:1516` semantics | High | ACCEPT | Critic |
| 5 | §4.4 priority column with no rule | High | ACCEPT | Critic |
| 6 | `domain-review.md` unconditional copy | Medium | ACCEPT | Critic |
| 7 | `work_kind` dead data | Medium | ACCEPT | Critic |
| 8 | §3.4 ↔ §9 stale-check scope contradiction | Medium | ACCEPT | Critic |
| 9 | Verdict parser strictness vs checkbox UX | Medium | ACCEPT | Critic |
| 10 | `ControlPlaneIntake()` double-init | Low | ACCEPT | Critic |

### Recommendations

**Must fix before implementation (Critical):**
1. Resolve #2 by extending `is_execution_open()` to re-read the verdict (or sidecar-hash domain-review.md). This is the only finding that creates a security-grade gap.
2. Resolve #1 by syncing §7.2 with §3.2.

**Should fix in same revision (High):**
3. Split the §3.2 Metadata example into two fenced blocks (#3).
4. Specify auto-approve return semantics for `project_pipeline.py:1516` and add §3.5 row (#4).
5. Drop or redefine §4.4 priority column (#5).

**Medium — fix inline if cheap; otherwise track as ADR:**
6. Gate `_copy_extra_templates()` on blast_radius (#6).
7. Drop speculative `work_kind` write (#7).
8. Resolve §3.4 vs §9 scope (#8).
9. Adjust template checkbox lines to avoid `- ` pattern collision (#9 — cheapest fix).

**Defer (Low / housekeeping):**
10. `ControlPlaneIntake()` single-instance refactor (#10).

**Process note**: This is review round 10+ on 2026-05-13 for one document. Per [[feedback_design_review_rounds_stop_rule]], merge the Critical+High fixes in a single edit pass and freeze the doc — push remaining Medium/Low items into an ADR rather than spawning another full review cycle.

**Cross-review provider error**: The Codex cross-review failed before producing output (truncated at "1. A design/f"). Either rerun cross-review once, or accept this aggregation as Critic-only given the strong evidence per finding.