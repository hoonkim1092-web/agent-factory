# Design Review: 2026-05-21-deep-interview-research-dogfood-pipeline

> Source: docs/2026-05-21-deep-interview-research-dogfood-pipeline.md
> Date: 2026-05-24 17:11
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] MVP command contract does not match the current CLI surface
   - Section: "`af dogfood start \"...\"` / `af dogfood run` / `af dogfood review` / `af dogfood resume` / `af dogfood complete \"...\"`"
   - Issue: The live parser in `agent_launcher.py:903` only registers `dogfood run`, `dogfood interview`, and `dogfood status`. `run_factory_cli.py:621` registers only `interview`, not `dogfood`. The design’s central command, `af dogfood complete`, has no current dispatch target, while the implemented command is named `run`.
   - Suggestion: Decide the canonical entrypoint first. Either update the design to `dogfood run/interview/status`, or add `start/review/resume/complete` to the same primary CLI path with tests in `tests/test_dogfood_cli.py` and `tests/test_run_factory_cli.py`.

2. [High] Intake artifact schema is underspecified and already diverges from callers
   - Section: "`Deep Interview must answer these categories: intent, scope, success_criteria, constraints, approval_policy, research_questions, risk_hints, assumptions`"
   - Issue: `core/interview.py:178` returns a wrapper with `task_input`, `questions`, `answers`, and nested `project_brief`, while `core/research_brief.py:37` accepts either nested `project_brief` or a bare brief. But `core/dogfood.py:283` validates only top-level `intent` or `goal`, so a valid `run_interview()` artifact can be rejected. The design does not define whether the canonical artifact is the wrapper or `project_brief`.
   - Suggestion: Add an exact JSON schema for the canonical intake artifact and require all callers to normalize through one function, e.g. `normalize_interview_artifact()`, before research brief/spec/dogfood use.

3. [High] Worktree isolation is listed too late for a self-modifying pipeline
   - Section: "`10. Add worktree/runtime isolation.`"
   - Issue: The design makes isolation a late implementation priority, after dogfood state, verify/review/retry, and skill review routing. But the same document says self-modifying work must use a real git worktree. Current `core/dogfood.py:385` executes commands in `state.workspace`, and there is no `git worktree add`, dirty-worktree refusal, or final diff allowlist in `core/dogfood.py`.
   - Suggestion: Move worktree/runtime isolation before any implementation or retry phase. Define `prepare_worktree()`, dirty policy, allowed source paths, runtime path allowlist, and rollback/finalization behavior as blocking MVP requirements.

4. [High] Triad/Architect Agent design conflicts with the current planner ownership of approval points
   - Section: "`The Architect Agent is the only role permitted to emit approval_points in the Triad output.`"
   - Issue: The current planner emits approval points directly in `core/planner.py:225`. The design also lists `core/architect_agent.py (planned)` but no such file exists, and no caller path currently routes Planner → Critic → Architect Agent before `build_plan()`. This creates an implementation trap: either the current planner schema must change, or the Architect Agent rule will be unenforceable.
   - Suggestion: Split plan generation into two artifacts: raw planner proposal without approval points, then Architect synthesis that owns `approval_points`. Add tests proving planner output cannot bypass Architect approval decisions.

5. [Medium] Review router surface names a new module but ignores the existing router
   - Section: "`core/review_skill_router.py: tier-specific skill profile routing for af-test-runner, af-critic, and af-cross-review`"
   - Issue: The repo already has `core/critic_skill_router.py`, with path-based critic skill mapping at `core/critic_skill_router.py:68`, plus review execution in `core/review_runner.py` and scripts such as `scripts/review_gate.py`. Adding `core/review_skill_router.py` without defining migration/caller changes risks a parallel router that review gates do not use.
   - Suggestion: Specify whether this extends `critic_skill_router.py` or replaces it. Name the exact caller changes in `scripts/review_gate.py`, `scripts/check_pending_review.py`, `core/review_runner.py`, and related tests.

6. [Medium] Research and external-service failure behavior is not designed
   - Section: "`Research should be constrained by the brief.`"
   - Issue: The design says research is required, but does not define behavior when web/API/LLM research is unavailable, partially fails, or returns no evidence. Current `core/dogfood.py:303` has a stub that returns context unchanged, while `core/spec_compiler.py:130` treats an empty brief as no constraint and produces no gaps.
   - Suggestion: Add failure states for `research_unavailable`, `partial_evidence`, and `no_on_brief_evidence`; define when the pipeline may continue with local-only evidence and when it must block.

7. [Medium] Verification examples are not Windows/frozen-build safe enough
   - Section: "`grep 'hiddenimports' af.spec`" and "`git diff --name-only HEAD | grep Master_Blueprint.md`"
   - Issue: The project targets Windows and frozen `dist/af/af.exe`, but the design uses Unix `grep` examples. Current `core/premortem.py:92`, `core/premortem.py:96`, and `core/premortem.py:114` also emit `grep` commands, which will fail in default PowerShell environments unless Git Bash tools are present.
   - Suggestion: Use Python-based checks or PowerShell-compatible commands in generated verification requirements. Include a frozen smoke path for `dist/af/af.exe dogfood --help` when packaging is in scope.

### Missing from Design

- Canonical JSON schemas for intake, research brief, spec, premortem, triad output, review output, and dogfood state.
- Exact CLI ownership between `run_factory_cli.py` and `agent_launcher.py`.
- Worktree creation, dirty-worktree refusal, merge/apply-back policy, and cleanup rules.
- External research outage and partial-evidence policy.
- Concurrency policy for multiple dogfood runs sharing `.af_runtime/dogfood`.
- Cross-platform verification command strategy.
- Migration plan for existing `core/critic_skill_router.py` and review gate scripts.
- Token/cost budget for loading full `Master_Blueprint.md` plus all ADRs into Architect Agent context.

### Positive Observations

- The pipeline order is directionally sound: interview before research, premortem after spec, and retry after verify/review failure matches the project’s known dogfooding failure modes.
- The design correctly calls out AF-specific risks: `Master_Blueprint.md` sync for `core/*.py`, `af.spec` hidden imports, runtime/source isolation, and bounded retry loops.