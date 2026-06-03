# Design Review: 2026-06-02-af-step0-product-decisions

> Source: docs/2026-06-02-af-step0-product-decisions.md
> Date: 2026-06-02 01:41
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: WARN

### Findings

1. [High] “메타-재귀 라우팅” is not enforceable in the current entry path
   - Section: “**메타-재귀 라우팅** — 대상 모듈이 파이프라인 의존(planner/premortem/dogfood/research_*)이면 dogfood run 금지, 손 구현 + 3-Tier.”
   - Issue: `agent_launcher.py:941-1066` exposes `dogfood run` directly and calls `core.dogfood.run_all()` with no route gate. `core/dogfood.py:1711-1811` always enters the dogfood pipeline phases once invoked. `core/review_skill_router.py:123` only routes review skills after changed files are known; it does not prevent dogfood from being selected.
   - Suggestion: Before Step 1, define a real routing decision point in `agent_launcher.py` or intake: `dogfood | manual_3tier | reject`, with tests proving `core/planner.py`, `core/premortem.py`, `core/dogfood.py`, and `core/research_router.py` cannot enter `run_all()`.

2. [High] The forbidden “pipeline dependency” list is under-specified and will miss real self-modifying paths
   - Section: “대상 모듈이 파이프라인 의존(planner/premortem/dogfood/research_*)이면…”
   - Issue: Actual dogfood pipeline imports also include `core.spec_compiler`, `core.research_brief`, `core.triad`, and `core.architect_agent` (`core/dogfood.py:1295-1453`). Top-level entry points `agent_launcher.py` and `run_factory_cli.py` also change execution behavior. Prior reviews already flagged path-form misses such as Windows `core\triad.py` and dotted `core.triad`.
   - Suggestion: Replace the text pattern with a closed, normalized route policy: forward slash, backslash, dotted module, and top-level entry-point handling. Include at least `agent_launcher.py`, `run_factory_cli.py`, `af.spec`, `core/interview.py`, `core/research_brief.py`, `core/spec_compiler.py`, `core/premortem.py`, `core/planner.py`, `core/triad.py`, `core/dogfood.py`, `core/research_router.py`, and `core/researcher.py`.

3. [Medium] “3-Tier” is named but no executable manual path is specified
   - Section: “dogfood run 금지, 손 구현 + 3-Tier”
   - Issue: The current concrete CLI path shown in `agent_launcher.py` is `dogfood`; there is no equivalent “manual + 3-Tier” command or state machine in the document. `core/review_skill_router.py` can compute tiers, but the document does not say how a manually implemented change is queued, blocked, reviewed, or recovered.
   - Suggestion: Add a Step 1 precondition: manual implementation must run a named command/script or documented sequence for Tier 1/2/3, including where review state is stored and what blocks completion.

4. [Medium] The design overstates current quality coverage
   - Section: “AF의 control+quality plane이 설계→구현→테스트→리뷰 전 과정을 이미 커버.”
   - Issue: `core/triad.py:9-11` says default Critic/Architect executors are PASS stubs until real wiring is provided. `core/dogfood.py:1449-1453` wires a real architect only inside dogfood, while the critic remains injectable/default. Recent dogfood reviews also flag partial failure, budget accounting, and worktree/merge edge cases.
   - Suggestion: Rephrase this as a hypothesis, not a settled capability. Step 1 should require explicit success criteria for verify pass, review pass, merge policy, budget accounting, and blocked-run recovery.

5. [Medium] “더미 금지” is subjective and will not prevent repeat low-value work-items
   - Section: “dogfood 검증용 throwaway 함수(`clamp`/`median`류)는 work-item이 아니다. AF가 실제로 아쉬워하는 기능만.”
   - Issue: The document gives examples of what not to do, but no objective selector for “실제로 아쉬워하는 기능.” The repo history shows many tiny utility additions in `core/utils.py` and `core/premortem.py`; without a measurable filter, Step 1 can still choose another low-impact feature.
   - Suggestion: Require each candidate to cite a friction source: failing test, repeated review finding, TODO/NEXT_STEPS item, dogfood blocked reason, or user workflow gap. Add one measurable success criterion before accepting the work-item.

### Missing from Design

- Concrete routing enforcement location and tests.
- Full list of self-modifying/pipeline-sensitive files.
- Windows path, dotted module, and top-level CLI path handling.
- Manual 3-Tier execution and rollback path.
- External CLI unavailable/auth/timeout behavior for “Claude Code CLI 우선.”
- Frozen build check: whether Step 1 can require `af.spec` hiddenimports when new `core/*.py` files are added.

### Positive Observations

- The document correctly narrows PMF scope to Python projects and AF dogfooding, which matches the current repository and avoids premature Docker/pricing work.
- The “더미 금지” rule directly addresses the recent low-signal utility-function pattern visible in the project history.