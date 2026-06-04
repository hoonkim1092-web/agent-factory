# Design Review: 2026-06-02-dogfood-pipeline-realignment

> Source: docs/2026-06-02-dogfood-pipeline-realignment.md
> Date: 2026-06-02 14:36
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] VERIFY cannot work after removing PLAN unless a new contract is defined
   - Section: "`VERIFY ... pipeline 자기보고 불신`" and "`VERIFY 재배선 — plan_dict 부재로 깨지는 기존 계약(`_strict_contract_failure`, `dogfood.py:2144` VERIFY commands_run)`"
   - Issue: The design removes `PLAN` but still keeps dogfood VERIFY. Current `core/dogfood.py:1866` runs VERIFY with `context={"plan_dict": plan_dict}`, and `_run_verify_phase()` at `core/dogfood.py:1607` derives commands from `plan_dict["verification_requirements"]`. With `agent_launcher.py:1064` passing `strict_contract=True`, `_strict_contract_failure()` at `core/dogfood.py:2144` blocks if VERIFY ran no commands. `ProjectPipeline.run()` returns a project execution result, not a dogfood `plan_dict` with `verification_requirements`.
   - Suggestion: Define a concrete adapter: `ProjectPipeline.run()` must return or persist a dogfood verification artifact with explicit commands, expected changed files, and success criteria. Alternatively, keep dogfood `PLAN` only for verification/merge allowlist generation while delegating implementation to pipeline.

2. [Critical] Removing PLAN makes FINALIZE stage all pipeline artifacts if cleanup misses anything
   - Section: "`RESEARCH_BRIEF, RESEARCH / SPEC / PREMORTEM / PLAN / IMPLEMENT 제거`" and "`FINALIZE 직전 ... 산출물 경로 ... staging에서 제외하고 ... git clean/checkout으로 제거`"
   - Issue: `finalize_dogfood_result()` builds `plan_allowlist` only from `state.plan_path` at `core/dogfood.py:993-1001`. If Option 2 removes dogfood PLAN and does not set `state.plan_path`, `plan_allowlist` is empty. Then `core/dogfood.py:1032-1034` stages every dirty file. That directly conflicts with the design’s own concern that `ProjectPipeline` writes repo-local artifacts: `write_project_board()` at `core/project_pipeline.py:916` and `1324`, `.todo.md` via `_write_todo()` at `core/project_pipeline.py:561` and `920`, and generated `agents/*.yaml` / `agents/<role>/role_spec.json` in `_materialize_roles()` at `core/project_pipeline.py:569`.
   - Suggestion: Do not rely on best-effort cleanup. Make FINALIZE fail-closed unless every dirty file is classified as either source/test change or disposable pipeline artifact. Better: produce a pipeline-derived allowlist and update `state.plan_path` or a new `state.develop_result_path` before FINALIZE.

3. [High] Artifact isolation option A is too late and can delete real generated source
   - Section: "`권장: (A) ... FINALIZE 직전 ... git clean/checkout으로 제거. dogfood가 실제 소스 변경만 커밋.`"
   - Issue: The proposed cleanup happens after `ProjectPipeline.run()` has mixed runtime artifacts and implementation files in the same worktree. Some generated files under `docs/specs`, `docs/`, `agents/`, or `.todo.md` may be legitimate outputs for a documentation or agent-definition task, while the same paths are also pipeline scaffolding paths. A path-only cleanup list cannot distinguish intended source changes from disposable pipeline state.
   - Suggestion: Prefer option B, `artifact_root` / `runtime_workspace`, for board, todo, role projections, mailbox, checkpoints, and planning documents. If option A remains, require provenance metadata from `ProjectPipeline` listing every file it created as scaffolding, and fail rather than deleting ambiguous files.

4. [High] PREMORTEM and Triad loss is acknowledged but not resolved before implementation
   - Section: "`PREMORTEM 상실: dogfood의 사전 위험분석 phase가 사라진다. pipeline에 등가물 없음.`" and "`Triad ... 상실: PLAN의 critic/architect 교차검증이 사라진다.`"
   - Issue: The implementation steps still say to remove `PREMORTEM` and `PLAN`. Current dogfood has explicit contract checks for SPEC, PREMORTEM, and PLAN in `_strict_contract_failure()` at `core/dogfood.py:2132-2143`. Replacing those with post-hoc REVIEW changes the safety model from pre-implementation blocking to after-the-fact detection.
   - Suggestion: Keep PREMORTEM before DEVELOP, or add a pipeline preflight phase that emits equivalent `premortem` and `planning_review` artifacts and is checked under strict contract before agents edit files.

5. [High] Retry semantics become expensive and non-idempotent
   - Section: "`retry 의미 변화: 현 REVIEW=retry는 IMPLEMENT로 되돌아간다 ... Option 2에서 retry는 DEVELOP(=pipeline 재실행) 전체를 되돌릴 것인가`"
   - Issue: Current retry uses `retry_run()` to return to `DogfoodPhase.IMPLEMENT` (`core/dogfood.py:622`), preserving the existing spec/premortem/plan. Under Option 2, retrying DEVELOP means rerunning `ProjectPipeline.prepare()` plus auto-approval (`core/project_pipeline.py:1522`, `1551`) and rewriting board/todo/agent YAML before execution. That can overwrite previous failure evidence and compound repo-local artifacts.
   - Suggestion: Split DEVELOP into `PIPELINE_PREPARE` and `PIPELINE_EXECUTE`, or persist the `PreparedProject` and retry execute only. Define whether retry starts from clean worktree, previous failed diff, or restored base ref.

6. [Medium] Frozen build compatibility is assumed, not verified
   - Section: "`구현 단계 ... DEVELOP phase 신규 ... run_all pipeline 주입`"
   - Issue: The design does not mention frozen `dist/af/af.exe` behavior. `af.spec` already includes `core.dogfood` at `af.spec:104` and `core.project_pipeline` at `af.spec:127`, so hiddenimports may not need a new module if the change stays in those files. But adding a new adapter module, phase result dataclass, or cleanup helper will require an explicit `af.spec` check.
   - Suggestion: Add a verification item: run/import frozen build path or update `af.spec` for any new `core.*` module introduced by DEVELOP.

### Missing from Design

- Exact DEVELOP result schema: changed files, verification commands, disposable artifacts, run id, pipeline status, and retry cursor.
- Migration plan for persisted dogfood states containing removed phases such as `research_brief`, `spec`, `premortem`, `plan`, or `implement`.
- Fail-closed artifact classification before FINALIZE.
- Windows shell/path handling for verification commands, especially given existing reviews flag `_command_runner()` PowerShell interpolation.
- Concurrency behavior if two dogfood runs invoke `ProjectPipeline.run()` against separate worktrees but shared global provider, registry, dashboard, or skill state.

### Positive Observations

- The document correctly identifies the real dependency injection point: `AgentFactory.project_pipeline` is assembled in `agent_launcher.py:262`, while `dogfood run` currently calls module-level `run_all()` at `agent_launcher.py:1059`.
- The design correctly spots that `ProjectPipeline.run()` auto-approves via `_gate.approve(approver="auto")` at `core/project_pipeline.py:1551`, so a separate human approval bridge is not required for autonomous dogfood execution.