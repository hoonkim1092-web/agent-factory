# Code Review: skill_preflight

> Source: core/skill_preflight.py
> Date: 2026-05-15 14:23
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings. Diff itself is a clean improvement (truthy semantics + logger primitive), but two Medium-level scope/observability gaps remain — one is a docstring/scope mismatch that was already flagged in a prior review round and is still unaddressed.

### Aggregated Findings (2 actionable + 1 advisory note)

#### 1. [ACCEPT] [Medium] Docstring overpromises F12 coverage; `workflow_apply()` still bypasses the gate
- **Critic**: New docstring claims "**모든** registry write skip" / "second line of defense", but `core/registry_manager.py:407` `workflow_apply()` (called by `core/skill_procurer.py` after every build) writes `WORKFLOW_PATH` directly with no `_env_flag` guard. During ad-hoc self-run, global `workflow_registry.yaml` continues to mutate.
- **Cross**: Not flagged (cross scoped its review to regression risk from the diff itself, not adjacent gaps).
- **Judgment**: Strong evidence. Critic cites a prior review (`docs/reviews/2026-05-15-140019-registry_manager-code-review.md` Finding #2) that already named this gap; this diff leaves it and the new "second line of defense" wording makes the gap easier to overlook.
- **Action Required**: Either (a) tighten docstring to "이 함수의 candidates 진입 차단" (function-scoped wording), or — preferred — (b) add `if _env_flag("AF_DISABLE_REGISTRY_WRITE"): return` at the top of `RegistryManager.workflow_apply()` and update its docstring to mention workflow-registry coverage. Option (b) actually delivers what the current docstring promises.

#### 2. [ACCEPT] [Medium] New `logger` not used on the actual error path; failure still silent when `verbose=False`
- **Critic**: Diff adds `logger = logging.getLogger(__name__)` and routes only one debug-level event through it. The exception path at `core/skill_preflight.py:317-319` (`except Exception as e: if self.verbose: print(...)`) — which fires on read/write failures of `registry.yaml` — remains print-gated on `verbose`. Forge/preflight runs that fail to persist a promote/demote will leave the registry stale with no log line at any level. Same `silent fallback` family as `code-review.md` §3.2.
- **Cross**: Not flagged.
- **Judgment**: Pre-existing pattern, not introduced by this diff — but the diff added the exact primitive needed to fix it (one logger line away). Reasonable to bundle.
- **Action Required**: Replace the verbose-print with `logger.warning("Registry update failed for %s: %s", result.skill_id, e, exc_info=True)`. Optionally keep the verbose print for CLI parity.

#### Advisory (no action) — Low
- **Critic Finding #3** (mixed `os.getenv` for numeric thresholds vs `_env_flag` for boolean): Critic explicitly says "No action required" — numeric vs boolean distinction means no truthy-vs-string ambiguity. Captured here only to confirm `_env_flag` adoption was scoped correctly.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | `workflow_apply()` bypasses F12 gate; docstring overpromises | Medium | ACCEPT | Critic (cross out of scope) |
| 2 | Logger added but error path still print-gated on `verbose` | Medium | ACCEPT | Critic |
| — | Mixed `os.getenv`/`_env_flag` style | Low | Advisory | Critic (self-dismissed) |

Cross review's 3 initial concerns were all self-rejected after investigation (`_env_flag` switch is the intended fix, `_env_flag` import pattern is already established in `registry_manager.py:15` and `approval_gate.py:43`, and skipping both registries matches the docstring intent). No contradiction with critic — cross simply scoped tighter.

### Recommendations
1. **Fix the docstring/scope mismatch** — choose one: tighten the wording to function-scope, or extend the gate to `RegistryManager.workflow_apply()` so the "second line of defense" claim is true. Recommend the latter; it closes the F12 gap that prior review already named.
2. **Wire the new `logger` into the exception path** at `core/skill_preflight.py:317-319` — `logger.warning(..., exc_info=True)`. Tiny change, removes a silent-failure mode in registry persistence.
3. Diff is otherwise sound; merge after the two changes (or document them as follow-ups if blocked by an unrelated concern).