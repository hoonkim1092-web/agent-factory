# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:39
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Blast radius taxonomy is still internally inconsistent
   - Section: `if blast_radius in ("system_wide", "security", "data"):` and E2E inputs `blast_radius="local"` / `blast_radius="security"`
   - Issue: The same document says valid tokens are only `isolated | module | cross_module | system_wide`, matching `core/control/change_impact.py:16,35,217-239` and `tests/test_approval_gate_domain_review.py:4-6`. But later sections still use invalid `local`, `security`, and `data`. This will fail existing tests and reintroduce the exact bug those tests guard against.
   - Suggestion: Replace `local` with `isolated`. Remove `security` and `data` from `blast_radius`; represent them through `BlockCause`, `risk_level`, or `domain_concerns`.

2. [Critical] Proposed CLI adapter does not match the real provider API
   - Section: `CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=..., response_format={"type": "json"})`
   - Issue: `core/providers/cli.py:30-39` defines `CliChatRequest(provider_id, model, system_prompt, task_input, workspace, run_id, timeout_sec, auto_approve)`. It has no `messages` or `response_format`. Also provider IDs are `claude_cli`, `gemini_cli`, `codex_cli` in `core/providers/cli.py:65-80`, not `"claude"`.
   - Suggestion: Redesign `QuestionRouterCliLLMCaller` around the actual constructor:
     `CliChatRequest(provider_id="claude_cli", model="", system_prompt=..., task_input=..., workspace=..., timeout_sec=90)`.

3. [High] paused_hitl early return breaks the `generate_work_items()` downstream contract
   - Section: `if stage0.paused_hitl: return _build_paused_response(work_dir, stage0)`
   - Issue: `generate_work_items()` currently returns `dict[str, str]` of document name to file path (`core/work_item_generator.py:1069-1079`, `1233-1237`). `ProjectPipeline.prepare()` immediately iterates `work_item_files.values()` as paths and opens them for plan verification (`core/project_pipeline.py:975-981`). The design does not define `_build_paused_response`, nor how `ProjectPipeline` distinguishes paused state from a normal file map.
   - Suggestion: Define an explicit paused return contract and update `ProjectPipeline.prepare()` to branch on it, or raise/return a typed `PreparedProject` status. Also create `approval-gate.md` before returning paused, because the design claims execution is closed.

4. [High] ApprovalGate matrix conflicts with current domain gate semantics and tests
   - Section: `NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`
   - Issue: Current `ApprovalGate.approve()` only enforces domain review for `blast_radius == "system_wide"` (`core/approval_gate.py:228-249`). Existing tests explicitly assert invalid token absence in `core/approval_gate.py`. The design says to test five cases including three invalid tokens, so implementation will either fail tests or weaken the taxonomy.
   - Suggestion: Test only `{isolated, module, cross_module, system_wide}`. If `cross_module` should pause on `NEEDS_ADR`, state that explicitly and update the matrix.

5. [High] Frozen build impact is missing for new modules and YAML data files
   - Section: `core/control/question_router.py 신규`, `core/control/stage_router.py 신규`, `core/control/questions/goal_clarification.yaml 신규`
   - Issue: `af.spec` has manual hidden imports (`af.spec:33+`) and data collection only includes `skills`, `config`, `policy.yaml`, and `core/research/packs` (`af.spec:27-32`). The design adds new import modules and runtime YAML under `core/control/questions/` but does not list `af.spec` changes.
   - Suggestion: Add all new `core.control.*` modules to hiddenimports and add `core/control/questions` to `datas`, or implement package-resource loading that works under PyInstaller.

6. [Medium] Schema hash policy contradicts itself
   - Section: `YAML schema ... schema_hash 필드 없음` versus `8.6 ... brainstorming.yaml 내 schema_hash 값 vs raw bytes hash 불일치`
   - Issue: Section 4.2 removes `schema_hash` from YAML, but section 8.6 still tests YAML-embedded hash drift. OQ8 also mentions auto-filling schema hash into the file, contradicting the “no auto migration / no YAML mutation” rule.
   - Suggestion: Make drift detection exclusively compare artifact/ledger stored hash against current raw YAML hash. Delete YAML `schema_hash` drift tests and OQ8 auto-fill language.

7. [Medium] Ledger paused state can become a stale active run
   - Section: `state="paused_hitl"` and `success 카운트 제외`
   - Issue: `RunLedger.LedgerEntry.is_active` treats entries without `closed_at` as active (`core/control/run_ledger.py:48-50`), and `is_stale()` marks old active entries stale (`core/control/run_ledger.py:52-69`). The design adds `append_paused_hitl()` but does not define whether the run is closed, partial, or resumable.
   - Suggestion: Specify `closed_at/outcome` behavior for paused HITL, or add a non-stale paused lifecycle state consumed by supervisor/nightly reporting.

### Missing from Design

- Exact `ProjectPipeline.prepare()` behavior when Stage 0 returns paused or blocked.
- `af.spec` updates for new modules and `core/control/questions/*.yaml`.
- Concrete provider ID/model/workspace contract for `QuestionRouterCliLLMCaller`.
- Resume entry point for `paused_hitl`; OQ6 admits it is unresolved, but P7 requires E2E behavior.
- Migration plan for existing `tests/test_approval_gate_domain_gate.py`, which currently expects `NEEDS_ADR` to pass for `system_wide`.

### Positive Observations

- The design correctly grounds Stage 0 insertion around `core/work_item_generator.py:1090-1106` and preserves Stage 1-3 function signatures.
- It identifies the existing provider abstraction and intends to reuse `execute_cli_chat()` instead of raw shell commands, which is the right architectural direction.