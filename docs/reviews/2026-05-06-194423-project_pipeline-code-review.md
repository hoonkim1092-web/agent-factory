# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-05-06 19:44
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Two Critical findings (one from each reviewer) confirm this diff introduces a feature that both silently fails and has a permanent-contamination failure mode. Must fix before merge.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [Critical] Domain gate reads the wrong dict — C1 feature is a no-op
- **Critic**: not flagged
- **Cross**: "`project_brief["research_plan"]["domain"]` — normal path stores `research_plan` in `research_evidence`, not `project_brief`. `_merge_project_brief_evidence()` does not copy it. So `_domain == ""` almost always, skipping both spec generation and `coverage_report.block` enforcement."
- **Judgment**: Strong evidence from `core/researcher.py:1048` (puts `research_plan` in evidence) and `core/researcher.py:1092` (merge does not copy it). The entire C1 gate silently does nothing for the common path.
- **Action Required**: Derive domain from both locations — `(project_brief.get("research_plan") or {}).get("domain") or (research_evidence.get("research_plan") or {}).get("domain", "")`. Persist the resolved value so downstream logic is consistent.

---

#### 2. [ACCEPT] [Critical] Silent exception swallow — placeholder spec permanently blocks regeneration
- **Critic**: "`except Exception: pass` in `_call_llm` swallows all failures, returns placeholder string `'# {title}\n\n(spec generation unavailable)\n'`. `_save_specs` writes it as-is. `_verify_domain_spec` checks only file existence. Result: LLM failure → placeholder saved → next run returns `True` → regeneration skipped forever."
- **Cross**: not flagged independently, but Finding #1 (domain wrong) means this path is rarely reached — so the contamination risk is latent but real once Finding #1 is fixed.
- **Judgment**: Code at `core/spec_generator.py:114-116` is unambiguous. This is the same `bare except: pass` anti-pattern flagged in prior BLOCK sessions. Must fix before the domain-source fix from Finding #1 makes this code path live.
- **Action Required**: In `_call_llm`, change `except Exception: pass` → `except Exception as e: logger.warning(...)`, return `None`. In `_save_specs`, skip `write_text` when `content is None`. In `_verify_domain_spec`, also reject files whose content matches the placeholder pattern (e.g., contains `"spec generation unavailable"`).

---

#### 3. [ACCEPT] [High] Specs written before coverage gate — poisoned files survive a BLOCK
- **Critic**: "Spec files are saved before `_coverage_blocked` is checked. If LLM also fails (Finding #2), placeholder files land on disk. Gate then raises `ResearchGateBlocked`, but poisoned files remain. Next run sees files via `_verify_domain_spec` and skips regeneration."
- **Cross**: not flagged independently
- **Judgment**: Ordering is clear in the diff (`_save_specs` call at `+848`, `raise ResearchGateBlocked` at `+855`). The contamination is irreversible without manual intervention. Even with placeholder fix from Finding #2, saving valid specs before confirming coverage is adequate is architecturally wrong.
- **Action Required**: Reorder — check `_coverage_blocked` first and raise immediately. Only proceed to spec generation after confirming coverage is adequate.

---

#### 4. [ACCEPT] [Medium] Specs ignore `target_path` — specs land in the wrong directory
- **Critic**: not flagged
- **Cross**: "`_verify_domain_spec()` / `_save_specs()` use `target_workspace`, but `doc_root` is computed after the gate at `project_pipeline.py:856-858`. `generate_work_items()` writes docs under `target_path` when absolute. Result: work-items go to target project, domain specs go to Agent Factory workspace."
- **Judgment**: The diff clearly shows the spec gate block before `doc_root` is assigned. The inconsistency is real and produces mismatched output locations.
- **Action Required**: Compute `doc_root` before the domain gate, use it for both `_verify_domain_spec()` and `_save_specs()`.

---

#### 5. [ACCEPT] [Medium] Non-atomic write in `_save_specs` — new M10 instance
- **Critic**: "Direct `write_text` without `tempfile` + `os.replace`. A crash mid-write leaves a truncated file. `_verify_domain_spec` glob matches the partial file; next run skips regeneration on corrupted spec."
- **Cross**: Cross Review's Finding #3 (rejected) was about checkpoint writes — that location IS fixed by this diff. `_save_specs` is a different, new location not covered by the fix.
- **Judgment**: The diff introduces `write_text` at `project_pipeline.py:227` with no atomicity guard. The existing `_write_json()` pattern (`core/project_pipeline.py:133-147`) already shows the correct approach. This is a new M10 instance.
- **Action Required**: Write to `.tmp` sibling, then `os.replace(tmp, final)` — same pattern as `_write_json()`.

---

#### 6. [ACCEPT] [Medium] Non-poker domains re-invoke spec generation on every run
- **Critic**: "`domain != 'poker'` → `generate()` returns `{}` → `_save_specs` writes 0 files → `_verify_domain_spec` stays `False` → every next run re-enters and calls `execute_document_prompt` 5× for nothing."
- **Cross**: not flagged
- **Judgment**: Logic is clear: the entire spec block is gated on `bool(domain)` not `domain == "poker"`, so any non-poker domain with a non-empty domain string hits this loop forever.
- **Action Required**: Gate the spec block on `domain == "poker"` (or whatever the intended set is), or have `_verify_domain_spec` return `True` when the domain would produce no output.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Domain gate reads wrong dict — C1 is no-op | Critical | ACCEPT | Cross |
| 2 | Silent exception swallow → permanent placeholder | Critical | ACCEPT | Critic |
| 3 | Specs saved before coverage gate — poisoned on BLOCK | High | ACCEPT | Critic |
| 4 | Specs ignore `target_path` | Medium | ACCEPT | Cross |
| 5 | Non-atomic write in `_save_specs` (new M10) | Medium | ACCEPT | Critic |
| 6 | Non-poker domains re-invoke generation every run | Medium | ACCEPT | Critic |

---

### Recommendations

1. **Fix domain resolution first** (Finding #1) — without this, all other C1 logic is dead code. Resolve from `research_evidence.research_plan.domain` as primary, `project_brief.research_plan.domain` as fallback.
2. **Fix exception handling in `_call_llm`** (Finding #2) — return `None` on failure, skip write in `_save_specs` when `None`, add content check in `_verify_domain_spec`.
3. **Reorder coverage gate before spec save** (Finding #3) — `_coverage_blocked` check must precede `_save_specs` call.
4. **Compute `doc_root` before the gate block** (Finding #4) — use it for both spec and work-item writes.
5. **Make `_save_specs` atomic** (Finding #5) — write to `.tmp`, then `os.replace()`, mirroring `_write_json()`.
6. **Narrow the domain gate condition** (Finding #6) — use `domain == "poker"` (or explicit allowlist) instead of `bool(domain)`.