# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:04
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `blast_radius` taxonomy conflicts with current project contract
   - Section: "`blast_radius ∈ {system_wide,security,data}`", "`blast_radius=\"local\"`", "`blast_radius=\"module\"`"
   - Issue: The design introduces `local`, `security`, and `data` as blast-radius values, but current code defines and tests only `isolated | module | cross_module | system_wide`. See `core/control/change_impact.py:16`, `core/control/execution_policy.py:103-108`, and `tests/test_approval_gate_domain_review.py:4-6`, which explicitly rejects invalid historical tokens like `"local"`.
   - Suggestion: Rework the matrix to use the existing four tokens. If `security`/`data` are risk categories, add them as `risk_level` or `BlockCause`, not `blast_radius`.

2. [High] `generate_work_items()` paused return shape is incompatible with its caller
   - Section: "`if stage0.paused_hitl: return _build_paused_response(work_dir, stage0)`"
   - Issue: `generate_work_items()` currently returns `dict[str, str]` of filenames to file paths. `ProjectPipeline` immediately iterates `work_item_files.values()` and tries to open each value as a file path at `core/project_pipeline.py:975-979`. A paused response object or status payload will break plan verification unless it preserves that exact contract.
   - Suggestion: Define a typed paused contract before implementation. Safer options: write real paused artifacts and return only file paths, or raise/return a distinct pipeline-level status that `ProjectPipeline` explicitly handles before plan verification.

3. [High] Schema hash policy is self-referential and cannot be stable as written
   - Section: "`schema_hash: \"\" # ... router가 startup 때 계산해 채워줌`" and "`raw bytes SHA-256`"
   - Issue: If the hash is computed over raw YAML bytes that include `schema_hash`, then writing the computed hash back into the YAML changes the bytes and invalidates the hash. This will cause perpetual drift or require undocumented normalization.
   - Suggestion: Either exclude the `schema_hash` field from the canonical hash, store the hash in a sidecar file, or make `schema_hash` output-only in artifacts/ledger rather than embedded in source YAML.

4. [High] ApprovalGate design misses current gating semantics
   - Section: "`approval_gate | execution_open=false (paused_hitl 상태)`" and "`Stage 1~3 건너뜀`"
   - Issue: `ApprovalGate.initialize()` only writes `approval-gate.md` with `execution_open: false` at `core/approval_gate.py:155-177`; it does not represent a paused HITL state. Also, domain review enforcement currently happens in `approve()` and only for `blast_radius == "system_wide"` at `core/approval_gate.py:228-249`. Stage 1-3 skipping must happen in `work_item_generator.py`, not ApprovalGate.
   - Suggestion: Add an explicit paused state either to `approval-gate.md` metadata or to `RunLedger`, and update `ProjectPipeline`/`MaintenancePipeline` execution checks to treat it as incomplete. Do not rely on `execution_open=false` alone, because that is also the normal review-pending state.

5. [Medium] LLM timeout signature is not backed by the current LLM abstraction
   - Section: "`LLMCaller.batch_route(... timeout_sec: float)`", "`Goal Clar QR ... 90s`", "`Brainstorming QR ... 180s`"
   - Issue: The existing likely adapter, `core/control_plane_llm.py`, exposes `generate()` and `generate_json()` only, and its CLI call uses `timeout_sec=300` hardcoded at `core/control_plane_llm.py:114-124`. The proposed per-batch budgets will be ignored unless the adapter is changed.
   - Suggestion: Add a concrete `QuestionRouterLLMCaller` design that passes timeout into `execute_cli_chat()` and documents provider fallback behavior.

6. [Medium] Frozen build impact is acknowledged nowhere in the implementation checklist
   - Section: "`core/control/question_router.py 신규`", "`core/control/stage_router.py 신규`", "`core/control/stage_artifacts.py 신규`"
   - Issue: New dynamically imported modules under `core.control` are not listed in `af.spec`. The file currently has many explicit hidden imports but no `core.control.stage_router`, `core.control.question_router`, `core.control.stage_artifacts`, or `core.control.verdicts`.
   - Suggestion: Add an acceptance criterion and patch plan for `af.spec` hiddenimports, then test `dist/af/af.exe` or the PyInstaller build path.

### Missing from Design

- Resume path for `paused_hitl`: OQ6 says undecided, but P7 requires paused behavior. This is too late; define whether resume enters through `ProjectPipeline`, `MaintenancePipeline`, or `work_item_generator`.
- Concrete `_build_paused_response()` schema and caller handling.
- Atomic write strategy for `assumptions.md`, `domain-review.md`, and generated artifacts under concurrent/nightly runs.
- Migration/update plan for existing tests that currently assert non-`system_wide` domain gate is skipped.
- `af.spec` hiddenimports update and frozen-build verification.
- Exact mapping between `BlockCause`, `risk_level`, `blast_radius`, and existing `ExecutionPolicyResolver`.

### Positive Observations

- The design correctly identifies the real insertion point: `core/work_item_generator.py` after `_copy_extra_templates()` and before Stage 1.
- It correctly preserves the existing `domain-review.md` parser contract by requiring a `- verdict: PASS|NEEDS_ADR|BLOCK` line for `ApprovalGate`.