# Code Review: hook_runner

> Source: scripts/hook_runner.py
> Date: 2026-05-04 00:23
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical/High findings. Critic raises 2 Medium + 2 Low observability/quality issues, all advisory and non-blocking. Cross-review unavailable (provider error — Codex CLI returned only startup banner with no review payload), so single-reviewer evidence base. Change itself is semantically correct (centralizes verdict extraction via `_extract_verdict_from_content`, aligning hook_runner with Phase 2 v7 §5.3 fence + last-position semantics).

> ⚠️ **Cross-reviewer unavailable** — Codex provider errored before producing findings. All accepts below rely on Critic + diff evidence only. Per CLAUDE.md "Tier 3 fan-out" rule, if external providers all fail, gate should record SKIP rather than treat as PASS by default; recommend re-running cross-review before merge if any of the Medium items below are deferred.

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Medium] `verdict_fallback` no-match path uses `exit_code=0`, hiding it from anomaly queries
- **Critic**: No-match (L350) logs exit_code=0; exception path (L354) logs exit_code=1. Same builtin name for both makes the common silent-PASS case un-greppable by `exit_code != 0`, defeating the observability rationale stated in the inline comment.
- **Cross**: not flagged (provider error)
- **Judgment**: Diff confirms the asymmetry. The change's stated goal (per inline comment citing §5.5 / O5) is to *surface* silent PASS fallbacks; logging them with the success exit code contradicts that goal. Strong evidence.
- **Action Required**: Either set exit_code=2 for the no-match branch, or split builtin name into `verdict_no_match` / `verdict_extract_error` so each is independently filterable.

#### 2. [ACCEPT] [Medium] Pipe-delimited log line corrupted by `|` chars in `content[:200]!r`
- **Critic**: `_log_hook_event` writes `f"{ts}|{builtin}|{file}|{exit_code}|{error}\n"`; `repr()` does not escape `|`. Agent output frequently contains pipes (markdown tables, CLI option lists). Embedded pipes fragment the `error` field across columns under naïve parsers (`awk -F'|'`, `cut -d'|'`).
- **Cross**: not flagged (provider error)
- **Judgment**: Diff + L100-109 of the same file confirm the pipe-delimited format. `repr()` only handles newlines/quotes, not the field separator. This breaks the observability the change is adding. Strong evidence.
- **Action Required**: Sanitize before embedding: `content[:200].replace("|", "¦")` (or escape via `repr().replace("|","\\u007c")`). JSONL migration is preferable but out of scope.

#### 3. [ACCEPT] [Low] Raw agent content excerpt persisted to hook log = new exfiltration surface
- **Critic**: Up to ~200 chars of `tool_response` content land in `.af_review_queue/hook_events.log`. Pre-change this path logged nothing; this is strictly additive surface.
- **Cross**: not flagged (provider error)
- **Judgment**: Reasonable concern. Local path, bounded blast radius, but unnecessary if a fingerprint serves the triage purpose. Evidence is the diff itself.
- **Action Required** (advisory): Replace excerpt with `content_len:{N} sha8:{hash[:8]}` for incident triage without persisting body bytes. Defer if triage workflows actually need the prefix.

#### 4. [ACCEPT] [Low] Bare `except Exception` now also swallows `_extract_verdict_from_content` bugs under same builtin name
- **Critic**: Try-block spans import + helper call. Helper bugs (e.g., regex catastrophic backtracking on adversarial fence input) are silently rewritten to "pass" with the same `verdict_fallback` event name as the no-match path. Pre-change parity holds, but helper now contains nontrivial logic (fence + sort + last-position).
- **Cross**: not flagged (provider error)
- **Judgment**: Critic explicitly notes this is parity-not-regression; flagged because the helper's complexity grew. Evidence in diff + Phase 2 v7 §5.3 spec.
- **Action Required** (advisory): Narrow try-scope to `from scripts.review_gate import _extract_verdict_from_content`, let helper exceptions raise to outer metric block; or distinct event name (`verdict_helper_error`).

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | exit_code=0 hides no-match anomaly | Medium | ACCEPT | Critic |
| 2 | `\|` in `content[:200]!r` corrupts log columns | Medium | ACCEPT | Critic |
| 3 | Raw content excerpt = new exfiltration surface | Low | ACCEPT | Critic |
| 4 | Bare `except` masks helper logic bugs | Low | ACCEPT | Critic |

### Recommendations
- **Fix #1 + #2 before merge** if log queryability is load-bearing for the Phase 2 → Phase 3 enforcement decision (the very signal this change exists to capture). Both are <5 LOC fixes.
- **Re-run cross-review** (Codex provider) before BLOCK-relaxing — current PASS-equivalent verdict relies on a single reviewer due to provider error. If this is the Tier 3 fan-out invocation and Codex is the only available external provider, gate should record `cross_review_skip` rather than treat absence as agreement.
- **#3 and #4 are deferrable** — log either as follow-up or accept as known advisory.
- Critic's positive observation stands: centralizing on `_extract_verdict_from_content` correctly eliminates the regex-drift class that produced prior spec-vs-code divergence; this is the right structural direction.