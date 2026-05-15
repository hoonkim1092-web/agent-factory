# Code Review: registry_manager

> Source: core/registry_manager.py
> Date: 2026-05-15 14:04
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

The two reviewers examined **non-overlapping code paths** in this commit's blast radius:
- **Critic** audited the F12 self-run isolation mechanism (`_maybe_isolate_project_root_for_self_run` + `AF_DISABLE_REGISTRY_WRITE`).
- **Cross** audited adjacent registry_manager paths (external skill promotion + `register_built` metadata).

No findings overlap. No reviewer reported a Critical (BLOCK-tier) defect. One High and four Medium findings warrant fixes before this area is considered stable; recommended action is to merge with a follow-up patch.

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] `AF_DISABLE_REGISTRY_WRITE` truthy evaluation diverges from AF convention
- **Critic**: `os.environ.get("AF_DISABLE_REGISTRY_WRITE")` at `core/registry_manager.py:49` and `core/skill_preflight.py:258` treats `"0"`, `"false"`, `"no"` as truthy — opposite of user intent. AF's existing skip-flag convention (`approval_gate.py:279,390`, `review_gate.py:176`, `dynamic_orchestrator.py:844`, `work_item_generator.py:958`) uses explicit `"1"`/`"true"`/`"yes"` checks.
- **Cross**: not flagged (different code path).
- **Judgment**: ACCEPT. Evidence is concrete — Critic cited 5 prior-art sites with the canonical pattern. Single-author writes the flag with `"1"` so the enable path works, but the disable/unset path is broken for any external user. Pattern divergence is exactly the kind of footgun the AF code-review skill targets.
- **Action Required**: Normalize both sites to `os.environ.get("AF_DISABLE_REGISTRY_WRITE", "").strip().lower() in {"1","true","yes","on"}`. Consider extracting `env_flag(name, default=False)` helper in `core/utils.py` to lock the convention in.

#### 2. [ACCEPT] [Medium] Failed external promotion leaves draft skill that blocks future fallback
- **Critic**: not flagged (different code path).
- **Cross**: `core/registry_manager.py:326` removes draft skill from `result["installed"]` but the copied files + registry/lock entry remain. Next procurement hits `core/skill_procurer.py:910` as exact local match, then `:927-941` skips install because `is_installable()` is false and `continue`s — no retry, no build fallback.
- **Judgment**: ACCEPT. Cross provided a complete call-chain trace (3 file:line citations) showing the dead-state effect. This is a correctness regression on the procurement fallback contract.
- **Action Required**: On `promotion=="draft"`, either (a) roll back the copied `SKILLS_DIR/<sid>` artifact + registry/lock entry, or (b) change the exact-match branch in `skill_procurer.py:910` to continue fallback when the exact match is non-installable.

#### 3. [ACCEPT] [Medium] `register_built()` drops promotion metadata produced by caller
- **Critic**: not flagged.
- **Cross**: `core/skill_procurer.py:750-759` populates `installable`, `last_eval_report`, `last_promotion_report`, `promotion_reason`, `promotion_updated_at`, `quality_stage` on `gated`, then calls `register_built(meta, ...)` at `:882`. `register_built()` at `core/registry_manager.py:382` only writes `id/name/status/version/capabilities/path/meta_path/updated_at/last_test_ok`. The external promotion path at `:279-285` preserves these fields — built-skill path diverges.
- **Judgment**: ACCEPT. Two-path inconsistency is verifiable from cited lines. Downstream readers of registry that expect promotion fields will see them only for externally-resolved skills.
- **Action Required**: Extend `register_built()` to copy promotion/eval fields from `gated`. Consider seeding `last_test_ok` from `gated.get("installable")` when explicit value absent.

#### 4. [ACCEPT] [Medium] Docstring drift — claims "글로벌만" skip but code blocks both registries
- **Critic**: `core/skill_preflight.py:248-259` main docstring says updates both `SKILLS_DIR` and `PROJECT_SKILLS_DIR`, F12 comment claims it skips "글로벌 registry write", but early `return` at L258 fires *before* the candidates loop at L265 — both registries blocked. Same drift in `core/registry_manager.py:46-48` comment.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. Diff inspection corroborates Critic's claim — `return` precedes the loop unconditionally. Today's behavior is safe because tempdir-isolated `PROJECT_SKILLS_DIR` carries no leak risk, but the docstring contract will mislead future callers who set the flag inside a real project tree.
- **Action Required**: Update docstring to "ad-hoc self-run 모드에서는 **모든** registry write를 skip한다 (isolation 보강용 second line of defense)". Alternatively, narrow the gate to skip only `SKILLS_DIR` candidate inside the loop.

#### 5. [ACCEPT] [Medium] `_KNOWN_SUBCOMMANDS` is dual source of truth
- **Critic**: `agent_launcher.py:41` (isolation guard) hardcodes `{"project"}`; `agent_launcher.py:767` defines `_KNOWN_SUBCOMMANDS = {"project"}`. Adding a new subcommand to one location silently misroutes it through isolation as ad-hoc task. Matches the F3 dual-source-of-truth category from prior rounds.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. The constant must be referenced from a single definition. Isolation must run before `core.*` imports, but that constraint only forces the *constant* to the top — not duplication.
- **Action Required**: Hoist `_KNOWN_SUBCOMMANDS = {"project"}` to module top, replace literal at L41 with the constant reference.

#### 6. [ACCEPT] [Medium] Isolated tempdir accumulation — no cleanup
- **Critic**: `core/config_paths.py:91-109` calls `os.makedirs(d, exist_ok=True)` on 9+ dirs derived from `PROJECT_ROOT` at import time. Each self-run leaves a `af_self_run_{ts}_{pid}/` tree with run artifacts in `tempfile.gettempdir()`. No `atexit`, no rotation. On Windows the OS won't reclaim for months.
- **Cross**: not flagged.
- **Judgment**: ACCEPT, but lower urgency than #1–#5. The leak is per-run, not per-call, so volume is bounded by dogfooding frequency. Still a hygiene gap worth a follow-up.
- **Action Required**: Add `atexit` cleanup gated by `AF_KEEP_SELF_RUN_TEMPDIR=1` (default = cleanup). Or pin isolation to `runs/self_run/` with N-deep rotation if post-run inspection matters.

#### 7. [ACCEPT] [Low] Silent skip — no diagnostic log when flag fires
- **Critic**: Both sites `return` without logging. `logger = logging.getLogger(__name__)` already exists at `core/registry_manager.py:17`. Debug log is zero-cost and saves future "why isn't registry updating?" investigation.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. Trivial fix, clear diagnostic value.
- **Action Required**: Add `logger.debug("registry write skipped (AF_DISABLE_REGISTRY_WRITE set)")` at both gate sites.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | env-var truthy semantics | High | ACCEPT | Critic |
| 2 | Draft external skill blocks fallback | Medium | ACCEPT | Cross |
| 3 | `register_built` drops promotion metadata | Medium | ACCEPT | Cross |
| 4 | Docstring drift on skip scope | Medium | ACCEPT | Critic |
| 5 | Subcommand allowlist dual source | Medium | ACCEPT | Critic |
| 6 | Tempdir accumulation, no cleanup | Medium | ACCEPT | Critic |
| 7 | Silent skip, no log | Low | ACCEPT | Critic |

Cross's two REJECTs (project policy passthrough, result mutation breaking caller) are not aggregated — Cross's own evidence (default `read_project_policies()` consistency; caller reads `results` not just `installed`) resolves them.

### Recommendations
- **Must-fix before reliance on the F12 fix as a stable boundary**: #1 (env-var semantics), #5 (dual source of truth) — both are convention-divergence bugs that will silently regress.
- **Must-fix in same area**: #2, #3 — these are pre-existing registry_manager defects surfaced by Cross; not introduced by F12 but adjacent and worth a single follow-up commit.
- **Same-PR cleanup if scope allows**: #4 (docstring), #7 (debug log) — both are trivial.
- **Follow-up issue**: #6 (tempdir cleanup) — defer to a hygiene patch; document accumulation in the docstring meanwhile.
- **Suggested commit shape**: one commit for F12 hardening (#1, #4, #5, #7), one commit for registry_manager promotion-path fixes (#2, #3), one tracked issue for tempdir cleanup (#6).