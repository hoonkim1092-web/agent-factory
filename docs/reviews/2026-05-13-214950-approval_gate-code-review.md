# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-13 21:49
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. One High finding (domain gate permanently dead in production), four Medium findings. Can merge with documented risks, but Finding 1 makes the primary feature of this diff inoperative.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Domain gate is permanently dead — production caller never passes `blast_radius`

- **Critic**: "The sole production caller at `project_pipeline.py:963-970` omits `work_kind` and `blast_radius`, so the gate file always stores `blast_radius: ""`. The `blast_radius == "system_wide"` condition at `approval_gate.py:233` can never be true in production. The domain gate is unreachable on delivery."
- **Cross**: Not flagged as a separate finding, but Cross Finding 4 (REJECT) confirmed the gate machinery works correctly — which makes the dead caller even more clearly the bottleneck.
- **Judgment**: Strong evidence from the diff. The caller site (`project_pipeline.py:963-970`) is visible and omits both keyword args. The function signature at `work_item_generator.py:1080-1081` accepts them but receives `""`. This is the primary purpose of the diff and it does not achieve it.
- **Action Required**: In `PreparedBrief` or at the `prepare_documents()` stage, extract `work_kind` and `blast_radius` from `ControlPlaneIntake.normalize()` output and pass them into `generate_work_items()`. Add an integration test that asserts a gate file written with `blast_radius: system_wide` enforces the domain review.

---

#### 2. [ACCEPT] [Medium] TOCTOU: verdict and hash can describe different file versions in `approve()`

- **Critic**: "The file is opened independently twice — once inside `_read_domain_review_verdict` for parsing and once inside `_sha256_file` for hashing (`approval_gate.py:237-251`). A concurrent writer can swap the file between reads, resulting in a stored hash that describes a different file than the approved verdict."
- **Cross**: Not flagged.
- **Judgment**: The double-open is visible in the diff. The attack window is narrow but real in CI environments where artifact writers run concurrently. Fail-open risk exists if the timing is exploited.
- **Action Required**: Read the file once in binary mode, compute SHA256 while accumulating bytes, then decode and parse the text for the verdict. Return both from a single helper, eliminating the race window entirely.

---

#### 3. [ACCEPT] [Medium] `AF_SKIP_DOMAIN_REVIEW` bypass leaves gate permanently executable after env var is removed

- **Critic**: Not flagged.
- **Cross**: "When `AF_SKIP_DOMAIN_REVIEW=1`, `approve()` writes no `domain_review_version`. `check_validity()` only validates `domain-review.md` when a saved snapshot exists. A `system_wide` gate approved under the bypass remains executable after the env var is removed — no domain review is ever enforced."
- **Judgment**: Code evidence is clear: `domain_review_version` is only set inside the non-skip branch (`approval_gate.py:232-251`), and `check_validity()` only validates domain review when `snapshots["domain_review"]` is non-empty (`approval_gate.py:442-447`). This is a real correctness gap for the security gate.
- **Action Required**: In `check_validity()`, if `blast_radius == "system_wide"` and `AF_SKIP_DOMAIN_REVIEW != "1"`, require a saved `domain_review` snapshot. If missing, return `(False, ["domain-review.md not approved"])`.

---

#### 4. [ACCEPT] [Medium] Auto-approve idempotency returns `True` before domain validity is rechecked

- **Critic**: Not flagged.
- **Cross**: "The early return at `approval_gate.py:222-227` for already-approved `[auto-approve]` gates fires before domain validation at lines 229-251 and before snapshot recomputation. If `domain-review.md` changed post-approval, `approve(auto=True)` reports success with a stale snapshot."
- **Judgment**: The early return is visible in the diff context. `is_execution_open()` will catch the drift later via `check_validity()`, but callers treating `approve()` as the approval boundary get a false `True`. Inconsistent return semantics.
- **Action Required**: Move the auto idempotency early-return to after `check_validity()` succeeds, or add a validity pre-check before the early return.

---

#### 5. [ACCEPT] [Low] `_sha256_file` returns `""` on `EACCES`, surfacing as "file changed" rather than "permission error"

- **Critic**: "`_sha256_file` catches all `OSError` including `EACCES` and returns `""`. A permission error on `domain-review.md` is flagged as a change, triggering `invalidate()` with a misleading 'domain-review.md changed' log. Behavior is fail-closed (correct), but error message misleads operators."
- **Cross**: Not flagged.
- **Judgment**: Pre-existing pattern in `_sha256_file`, but the diff extends it to a security-critical gate file. Fail-closed is the right behavior; the diagnostic accuracy gap is the only issue. Severity lowered to Low (no security regression, pre-existing).
- **Action Required**: Distinguish `FileNotFoundError` from other `OSError` subtypes, or log `errno` before returning `""` so operators can distinguish a permissions regression from a genuine file edit.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Domain gate dead — caller omits `blast_radius` | High | ACCEPT | Critic |
| 2 | TOCTOU: double file open in `approve()` | Medium | ACCEPT | Critic |
| 3 | `AF_SKIP_DOMAIN_REVIEW` bypass leaves gate permanently open | Medium | ACCEPT | Cross |
| 4 | Auto-approve early return skips domain re-validation | Medium | ACCEPT | Cross |
| 5 | `_sha256_file` masks `EACCES` as "file changed" | Low | ACCEPT | Critic |

---

### Recommendations

- **Finding 1 is the blocker for functional completeness**: wire `blast_radius`/`work_kind` from `ControlPlaneIntake` through `prepare_documents()` → `generate_work_items()` → `gate.initialize()`. Without this, the entire domain gate subsystem added by this diff is dead code.
- **Finding 3 closes a bypass escape hatch**: add the missing enforcement in `check_validity()` for `system_wide` gates that have no stored `domain_review` snapshot.
- **Finding 4 is a one-liner**: move the auto idempotency return after validity check, or add `check_validity()` as a guard before the early return.
- **Finding 2** (TOCTOU) is the hardest structural fix — consolidate the two file reads into a single binary-mode read that returns both hash and parsed verdict.
- **Finding 5** can be addressed in a follow-up; it is fail-closed and pre-existing.