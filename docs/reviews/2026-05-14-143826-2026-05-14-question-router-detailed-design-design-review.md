# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:38
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `work_kind` / `blast_radius` are consumed but not reliably produced
   - Section: "`core/project_pipeline.py:970-971` | 호출 시 `work_kind=str(project_brief.get(\"work_kind\") or \"\")` 전달"
   - Issue: Current `project_brief` is created with only `requested_role`, `route`, and `generated_at` in `core/project_pipeline.py:818-820`. `ControlPlaneIntake.normalize()` is not called in the project pipeline path, so `work_kind` and `blast_radius` will usually be empty when passed to `generate_work_items()` at `core/project_pipeline.py:963-971`.
   - Suggestion: Add an explicit source of truth before `generate_work_items()`: call `ControlPlaneIntake.normalize(task_input, target_workspace, route, board=task_board)`, then write `work_kind` and `blast_radius` into `project_brief` or `PreparedBrief`.

2. [Critical] Stage 0 BLOCK does not actually stop Stage 1-3
   - Section: "`StageRouter가 모든 side effect를 책임진다`" and responsibility matrix: "`pause/abort 결정 | ❌ | ❌ | | ✅`"
   - Issue: `ApprovalGate` is initialized only after Stage 1-3 finish at `core/work_item_generator.py:1237-1238`. The proposed insertion only skips Stage 1-3 for `stage0.paused_hitl` in §7.1. If BrainstormingQR returns `BLOCK`, the design says ApprovalGate decides, but ApprovalGate cannot decide until after plan/spec/design/tasks have already been generated.
   - Suggestion: Make `StageZeroResult` carry a terminal state such as `paused_hitl` / `blocked` / `needs_adr_pause`, and have `generate_work_items()` return before Stage 1 when execution should not proceed. Do not defer Stage 0 hard blocks to `ApprovalGate.approve()`.

3. [High] Blast radius taxonomy is still inconsistent
   - Section: "`v1 잘못된 토큰 정정`: `local` → `isolated`; `security`/`data` → BlockCause"
   - Section: "`if blast_radius in (\"system_wide\", \"security\", \"data\"):`" and E2E inputs "`blast_radius=\"local\"`", "`blast_radius=\"security\"`"
   - Issue: The document correctly defines valid tokens as `isolated | module | cross_module | system_wide`, but later sections still use invalid `local`, `security`, and `data`. Current regression tests explicitly guard invalid tokens in `tests/test_approval_gate_domain_review.py`.
   - Suggestion: Replace all blast radius examples/tests/matrix entries with the four valid tokens. Represent security/data via `BlockCause`, `risk_level`, or `domain_concerns`, not `blast_radius`.

4. [High] StageRouter constructor/signature conflicts inside the same design
   - Section: "`class StageRouter: def __init__(self, workspace: str, run_ledger: RunLedger):`"
   - Section: "`stage0 = StageRouter(workspace).run(...)`"
   - Issue: §5.6 requires a `RunLedger`, but §7.1 instantiates without one. Implementation will fail immediately unless `run_ledger` is optional or constructed internally.
   - Suggestion: Pick one API. Prefer `StageRouter(workspace=workspace, run_ledger=RunLedger(workspace))`, or make `run_ledger` optional and document the default.

5. [Medium] Schema hash policy contradicts itself
   - Section: "`schema_hash 필드 없음`" and "`YAML 원본 자동 수정 금지`"
   - Section: "`입력: brainstorming.yaml 의 schema_hash 값 vs raw bytes hash 불일치`"
   - Section: "`OQ8 | schema_hash 자동 채움 정책 | ... startup 시 계산해 파일에 기록`"
   - Issue: The design removes YAML `schema_hash`, then later tests drift by comparing a YAML `schema_hash`, then reopens startup file mutation. This reintroduces the perpetual drift problem §4.2 says it fixed.
   - Suggestion: Remove YAML `schema_hash` references from §8.6 and OQ8. Drift should compare stored artifact/ledger hash vs current raw YAML hash only.

6. [Medium] Frozen build impact is missing
   - Section: "`core/control/question_router.py 신규`", "`stage_router.py 신규`", "`stage_artifacts.py 신규`", "`verdicts.py 신규`"
   - Issue: `af.spec` has explicit hiddenimports and does not include the new `core.control.*` modules. Frozen `dist/af/af.exe` can miss dynamically imported modules such as `core.control.stage_router`.
   - Suggestion: Add `core.control.stage_router`, `core.control.question_router`, `core.control.stage_artifacts`, `core.control.verdicts`, and `core.control.context_scanner` to `af.spec`, plus a frozen/import smoke check.

### Missing from Design

- Concrete pipeline wiring that produces `project_brief["work_kind"]` and `project_brief["blast_radius"]`.
- Definition of `_build_paused_response()` and its return shape, since `generate_work_items()` currently returns `dict[str, str]`.
- Clear handling for `BLOCK` before Stage 1 starts.
- `af.spec` hiddenimports update.
- Resume entrypoint for `paused_hitl` beyond an open question.

### Positive Observations

- The design correctly verifies current call sites around `generate_work_items()` and `ApprovalGate.initialize()`.
- The QuestionRouter side-effect boundary is a good constraint; keeping YAML mutation and ledger writes out of the classifier is architecturally cleaner.