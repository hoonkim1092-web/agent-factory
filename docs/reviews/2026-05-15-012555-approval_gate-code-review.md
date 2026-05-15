# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-15 01:25
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

Now I have everything I need. The critic reviewed an intermediate state; the file was updated before the cross-reviewer ran. Here is the final aggregated verdict.

---

## Final Code Review

### Verdict: WARN

**Context note**: The critic and cross-reviewer reviewed different snapshots of the same file. Between the critic's pass and the cross-reviewer's pass, three of the critic's findings were already corrected in the working tree. The cross-reviewer confirmed this by running `pytest` against the updated file. The verdict below reflects the state of the **actual current diff** (`git diff HEAD`), not the intermediate snapshot the critic saw.

---

### Aggregated Findings (4 total → 3 Superseded, 1 Open)

#### 1. [SUPERSEDED] [High] `last_block_reason` polluted on NEEDS_ADR + low-blast success path

- **Critic**: `self.last_block_reason = "needs_adr_warning"` is set then approve() returns True — callers treating non-empty `last_block_reason` as failure will falsely reject approved commits.
- **Cross**: Not flagged (reviewed updated file).
- **Judgment**: The current diff has already corrected this. Line 301 now reads `self.last_warning_reason = "needs_adr_warning"`, and a comment at line 300 explicitly records the intent: `# last_block_reason는 "" 유지 (#1 false-positive 방지)`. The bug described by the critic does not exist in the committed working tree.
- **Action Required**: None. Already resolved.

#### 2. [SUPERSEDED] [Medium] `_parse_domain_review` defined but never called

- **Critic**: Domain gate still calls `_read_domain_review_verdict` + `_read_block_cause` as two separate reads; `_parse_domain_review` has zero callers.
- **Cross**: Not flagged.
- **Judgment**: Current diff shows line 280 calls `verdict, block_cause = _parse_domain_review(domain_path)`. The two-read sequence and the dead code finding are both resolved. `_read_domain_review_verdict` is still present in the file but is no longer invoked from the gate block.
- **Action Required**: None. Already resolved.

#### 3. [SUPERSEDED] [Low] `last_warning_reason` field never written

- **Critic**: Field initialized in `__init__` but no code path sets it.
- **Cross**: Not flagged.
- **Judgment**: Resolved as part of finding #1's fix. Line 301 writes it.
- **Action Required**: None. Already resolved.

#### 4. [ACCEPT] [Medium] Low-blast items have a post-approval BLOCK blind spot

- **Critic**: Not flagged.
- **Cross**: Accepted finding — `check_validity()` only re-hashes `domain-review.md` when `domain_review_version` was stored; low-blast items where the file is absent or blank at approval time store no hash, so a later edit to `BLOCK` goes undetected before `execute()`.
- **Judgment**: Confirmed against current code. Two paths leave `domain_review_version = ""`:
  1. Low-blast + no `domain-review.md` at approval time → falls through `elif high_blast` guard, variable stays at default `""`.
  2. Low-blast + blank template (`verdict == ""`) → `if verdict:` guard at line 302 skips `_sha256_file`.
  
  `check_validity()` at line 498–503: `if saved_dr:` — when the stored hash is empty the recheck is skipped entirely. A post-approval write of `domain-review.md: BLOCK` for a low-blast item will not invalidate `is_execution_open()`.

  Severity is Medium (not High) because: low-blast items have inherently narrower blast radius, and exploiting this requires either a deliberate post-approval tamper or an automated tool writing the file after approval.
- **Action Required** (advisory — WARN, not BLOCK): When `domain-review.md` does not exist at approval time for a low-blast item, optionally store the path-absent sentinel so `check_validity()` can detect later addition. Or extend `check_validity()` to parse the current `domain-review.md` when no snapshot hash exists and treat `BLOCK` as an invalidation. Add a regression test: approve low-blast `module` with no `domain-review.md`, create file with `BLOCK`, assert `is_execution_open()` returns `False`.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `last_block_reason` on success path | High | SUPERSEDED | Critic |
| 2 | `_parse_domain_review` dead code | Medium | SUPERSEDED | Critic |
| 3 | `last_warning_reason` never written | Low | SUPERSEDED | Critic |
| 4 | Post-approval BLOCK blind spot (low-blast) | Medium | ACCEPT | Cross |

---

### Recommendations

- **No blocking action required.** The three High/Medium/Low findings from the critic are resolved in the current working tree; the `elif verdict == "NEEDS_ADR":` → `last_warning_reason` path is correct.
- **For finding #4** (advisory): the lowest-friction fix is to extend `check_validity()` — when `saved_dr == ""` and `domain-review.md` now exists, parse it and add it to `changed` if it contains `BLOCK`. This is a localized, two-line addition to `check_validity()` with no approve() side effects.
- `_read_domain_review_verdict` is now unreferenced from the gate block. Verify no other callers exist before removing it in a separate cleanup commit (per Surgical Changes policy — do not remove as part of this diff).