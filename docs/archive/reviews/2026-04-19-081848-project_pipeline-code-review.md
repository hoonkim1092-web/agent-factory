# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-04-19 08:18
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

Two real defects accepted from Cross Review; Critic had no diff to evaluate.

---

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [High] `execute()` reads docs from wrong root when `target_path` is set

- **Critic**: Not flagged (no diff provided)
- **Cross**: `execute()` re-parses work-items from `prepared.workspace`, but gate/approval logic uses `_effective_doc_root()` → `doc_root`. When `target_path != workspace`, execution silently ignores the approved edits.
- **Judgment**: Strong evidence — `sync_board_from_work_items()` hard-codes `os.path.abspath(workspace)/docs/work-items/<slug>` while approval gates through a different path. This is a broken contract that causes silent data loss: approved edits under `target_path` are never applied.
- **Action Required**: Pass `prepared.doc_root or prepared.workspace` as the document root into `sync_board_from_work_items()`. Add regression test: separate `workspace`/`target_path`, edit `implementation-tasks.md` under target path, approve, assert board reflects the edit.

---

#### 2. [ACCEPT] [Medium] `enrich_role_plan()` learns from wrong ledger when `target_path` is set

- **Critic**: Not flagged (no diff provided)
- **Cross**: `enrich_role_plan()` receives `target_workspace` before effective project root is resolved from `project_brief["target_path"]`. Role assignment via `_pick_owner_role()` loads `strategy_ledger.json` from the launcher workspace, not the actual project directory.
- **Judgment**: Consistent with Finding #1 — the fix correctly addresses `workspace=None → "."` fallback but introduces a subtler root-confusion bug. `researcher.py:701` confirms `target_path` is the intended project root; `work_item_generator.py:520` already respects it downstream. The planning phase being out of sync is a real behavioral defect.
- **Action Required**: Compute effective project root immediately after `project_brief` is built, then pass that root uniformly to `enrich_role_plan()`, work-item generation, and execute-time parsing.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `execute()` reads docs from wrong root | High | ACCEPT | Cross |
| 2 | `enrich_role_plan` uses launcher ledger instead of project ledger | Medium | ACCEPT | Cross |
| 3 | `board=` arg in `_write_todo()` breaks callers | Low | REJECT | Cross |
| 4 | `enrich_role_plan` signature propagation | Low | REJECT | Cross |

---

### Recommendations

- **Fix #1 first** (higher severity, silent data loss): pass `prepared.doc_root or prepared.workspace` as a consistent document root throughout `execute()`.
- **Fix #2 in the same pass**: resolve effective project root from `project_brief["target_path"]` right after brief construction; use it uniformly for planning and execution.
- Add two regression tests: one for wrong-root document sync, one for wrong-root ledger selection.
- Critic was unable to review due to missing diff — resubmit with diff attached if further static analysis is needed.