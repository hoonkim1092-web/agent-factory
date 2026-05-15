# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-15 01:14
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Two High findings require author decision before merge; three Medium findings are advisory.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `last_block_reason` set on gate pass — caller false-positive risk

- **Critic**: Gate returns `True` but sets `self.last_block_reason = "needs_adr_warning"`, meaning any caller checking `if gate.last_block_reason:` will incorrectly treat this as a block.
- **Cross**: Not flagged.
- **Judgment**: Strong evidence. The diff clearly shows fall-through to `domain_review_version = _sha256_file(...)` without `return False`, while `last_block_reason` is non-empty. The field name and the prior invariant (always `""` on pass path) make this a semantic contract violation.
- **Action Required**: Replace `self.last_block_reason = "needs_adr_warning"` with a separate `self.last_warning_reason = "needs_adr_warning"`, or clear `last_block_reason = ""` before the fall-through and log the warning instead.

---

#### 2. [ACCEPT] [High] Domain gate applies to low-blast tasks when file exists — unintended behavioral expansion + blank template trap

- **Critic**: Old code gated only on `blast_radius == "system_wide"`; new code gates on file existence regardless of blast radius. Stale `domain-review.md` files in low-blast work-item dirs can trigger unexpected blocks.
- **Cross**: Confirms and sharpens: `generate_work_items()` copies `domain-review.md` template (with empty `- verdict:` at `docs/work-items/_template/domain-review.md:57`) into every work-item at `core/work_item_generator.py:1420`. `module`/`isolated` tasks therefore hit `missing_verdict` and return `False` before Stage 0 populates the template.
- **Judgment**: Both reviewers agree on the same area; Cross provides the concrete reproduction path. This is a regression for any low-blast work-item created after this change. The test at `tests/test_approval_gate_domain_gate.py:174` only covers the "file absent" case, leaving this path untested.
- **Action Required**: For low blast radius, treat an unfilled template (empty verdict) as absent. Minimal fix:
  ```python
  if os.path.exists(domain_path):
      verdict = _read_domain_review_verdict(domain_path)
      if not verdict and not high_blast:
          pass  # unfilled template on low-blast → skip
      elif not verdict:
          self.last_block_reason = "missing_verdict"
          return False
      ...
  ```
  Also add a test covering `isolated`/`module` blast radius with a blank template.

---

#### 3. [ACCEPT] [Medium] `_read_block_cause` reads `domain-review.md` a second time — TOCTOU + version skew

- **Critic**: `_read_domain_review_verdict` reads the file, then `_read_block_cause` reads it again. In an automated pipeline these could return data from different file versions, producing a mismatched `(verdict=BLOCK, block_cause=<stale>)` pair in `hook_events.log`.
- **Cross**: Not flagged.
- **Judgment**: The double-read is visible in the diff: `verdict = _read_domain_review_verdict(domain_path)` followed by `block_cause = _read_block_cause(domain_path)`. The risk is real in any async pipeline where files can be rewritten between reads.
- **Action Required**: Merge into a single read: `_parse_domain_review(path) -> tuple[str, str]` returning `(verdict, block_cause)`.

---

#### 4. [ACCEPT] [Medium] `_read_block_cause` regex is case-sensitive; StageRouter writes lowercase values

- **Critic**: `re.findall` pattern matches uppercase literals only; `_read_domain_review_verdict` normalizes via `.upper()` but `_read_block_cause` does not.
- **Cross**: Confirms with evidence — `core/control/verdicts.py:18-23` defines enum values as lowercase (`high_risk`, etc.); `core/control/stage_router.py:480-481` writes `- block_cause: {a.block_cause.value}` (lowercase). Gate therefore silently loses cause detail and logs `domain_review_blocked` instead of `domain_review_blocked_high_risk`.
- **Judgment**: Both reviewers flag the same mechanism. Cross provides the concrete enum/writer path proving it is not hypothetical.
- **Action Required**: Add `re.IGNORECASE` to `re.findall` and normalize the result: `return causes[0].upper() if causes else ""`.

---

#### 5. [ACCEPT] [Medium] `"missing_domain_frontmatter"` error code misnames the actual condition

- **Critic**: Under the new logic this error code is emitted from the `elif high_blast:` branch when the file is absent (post–`os.path.exists` check). Previously it meant "file present but no readable frontmatter." The same string now covers two distinct conditions.
- **Cross**: Not flagged.
- **Judgment**: The diff confirms the structural change: `elif high_blast: self.last_block_reason = "missing_domain_frontmatter"` is reached only when `os.path.exists(domain_path)` returned `False`. The old meaning (file present, frontmatter unreadable) no longer applies here.
- **Action Required**: Rename to `"missing_domain_review_file"` in this branch.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `last_block_reason` set on gate pass | High | ACCEPT | Critic |
| 2 | Low-blast domain gate + blank template trap | High | ACCEPT | Both |
| 3 | Double file read — TOCTOU skew | Medium | ACCEPT | Critic |
| 4 | `_read_block_cause` case-sensitivity vs StageRouter lowercase | Medium | ACCEPT | Both |
| 5 | `"missing_domain_frontmatter"` error code mismatch | Medium | ACCEPT | Critic |

---

### Recommendations

- **Fix #1 before merge**: introduce `last_warning_reason` field (or clear `last_block_reason` on pass) — this is a silent behavioral regression for any caller using the truthy check pattern.
- **Fix #2 before merge**: guard low-blast blank-template path; add a test for `isolated`/`module` blast with a blank `domain-review.md`.
- **Fix #4 before merge**: add `re.IGNORECASE` + `.upper()` — StageRouter already writes lowercase; this is a confirmed data loss path, not hypothetical.
- **Fix #3 post-merge acceptable**: consolidate to single `_parse_domain_review()` call; risk is low in practice but worth cleaning up.
- **Fix #5 post-merge acceptable**: rename error code; no behavioral impact, only diagnostic clarity.