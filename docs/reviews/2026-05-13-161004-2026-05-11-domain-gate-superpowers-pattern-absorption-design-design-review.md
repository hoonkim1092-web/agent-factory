# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:10
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Domain gate trigger uses a non-existent `blast_radius`
   - Section: `return blast_radius == "system"`
   - Issue: Current code emits `"system_wide"`, not `"system"`. See [change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:35) and returns at [change_impact.py](/D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:217). If implemented literally, system-wide changes will not require `domain-review.md`.
   - Suggestion: Change the design to `blast_radius == "system_wide"` and add a test where a `core/` change produces `system_wide` and blocks without `domain-review.md`.

2. [Critical] Proposed `work_kind` / `blast_radius` data path does not match the project pipeline
   - Section: `ControlPlaneIntake.normalize() ... NormalizedRequest{work_kind, change_impact, ...} -> work_item_generator.create_work_item()`
   - Issue: The actual prepare path calls `generate_work_items()` directly with `project_brief`, `role_plan`, and `task_board`; it does not pass `NormalizedRequest`. See [project_pipeline.py](/D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:959) and [work_item_generator.py](/D:/hoonProJect/worktrees/agent-factory/core/work_item_generator.py:1069). Also, there is no `create_work_item()` in `core/work_item_generator.py`.
   - Suggestion: Either pass `work_kind` and `blast_radius` explicitly into `ProjectPipeline.prepare()` / `generate_work_items()`, or derive them inside `generate_work_items()` from available inputs. Update the design’s call stack to the real `ProjectPipeline.prepare() -> generate_work_items() -> ApprovalGate.initialize()` path.

3. [High] `ApprovalGate` has no frontmatter reader or metadata contract
   - Section: `ApprovalGate가 read`, `frontmatter read 시점: ApprovalGate.approve() 진입 직후`
   - Issue: Current `ApprovalGate.__init__` only accepts `workspace`, `slug`, and `runtime_workspace`, and `approve()` parses only `approval-gate.md`; no frontmatter file is read. See [approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:107) and [approval_gate.py](/D:/hoonProJect/worktrees/agent-factory/core/approval_gate.py:143). The design does not specify the exact frontmatter format, parser, missing-value behavior for existing generated docs, or how this interacts with target-path doc roots.
   - Suggestion: Add a concrete helper contract, e.g. `_read_work_item_metadata(work_item_dir) -> {work_kind, blast_radius}`, define YAML frontmatter syntax, and include tests for missing frontmatter, malformed YAML, target-path work-items, and legacy work-items.

4. [High] `domain-review.md` verdict parsing is underspecified and collision-prone
   - Section: `verdict 검증 (verdict ∈ {PASS, NEEDS_ADR, BLOCK})` and template lines with `PASS`, `NEEDS_ADR`, `BLOCK`
   - Issue: The proposed template contains all three verdict labels as checkbox options. A naive text search for `PASS` will always find `PASS`, even when `BLOCK` is checked. This project has prior review-gate verdict collision issues in `scripts/review_gate.py`, so this needs an exact parser contract before implementation.
   - Suggestion: Require exactly one checked checkbox, e.g. `- [x] PASS`, `- [x] NEEDS_ADR`, or `- [x] BLOCK`; reject zero or multiple checked options. Add tests for unchecked template, multiple checked verdicts, quoted prior verdicts, and lowercase/whitespace variants.

5. [Medium] Concurrent write failure scenario is not addressed
   - Section: `_DOC_FILES에 domain-review.md 추가`, `approval_gate 정책 확장`
   - Issue: `ApprovalGate` writes through `core.file_io.write_text()`, which is a direct `open(..., "w")` write, not atomic. See [file_io.py](/D:/hoonProJect/worktrees/agent-factory/core/file_io.py:117). `code-review.md` already flags non-atomic JSON/markdown write patterns as a recurring risk. Adding another approval-critical document without atomic write/lock semantics can corrupt gate state under concurrent prepare/approve/review flows.
   - Suggestion: Either scope Phase A to single-writer only and state that explicitly, or require atomic write for `approval-gate.md` and `domain-review.md` updates before enforcing the gate.

6. [Medium] Dead-code disposition underestimates test and frozen-build coupling
   - Section: `core/skill_pack_bootstrapper.py ... dead code`, `af.spec line 122 ... hiddenimports에서 제거`
   - Issue: It is not production-called, but it is still imported and tested in [test_compact_step2.py](/D:/hoonProJect/worktrees/agent-factory/tests/test_compact_step2.py:92), and `af.spec` includes `core.skill_pack_bootstrapper`. Calling it simply “dead code” is too broad unless the design distinguishes runtime dead code from test/build referenced code.
   - Suggestion: Rephrase to “no production call sites found; test and frozen hiddenimport references remain.” If deprecating, update tests and `af.spec` in the same scoped change or explicitly leave them unchanged.

### Missing from Design

- Exact `blast_radius` enum: must use `isolated | module | cross_module | system_wide`.
- Real `ProjectPipeline.prepare()` integration point for `work_kind` and `blast_radius`.
- Concrete frontmatter schema and parser behavior.
- Exact `domain-review.md` verdict parser rules.
- Frozen build check: whether new modules such as `core/brainstorm_prompts.py` need `af.spec` hiddenimports.
- Atomic write or lock strategy for approval-critical markdown files.
- Tests for target-path / multi-PC doc roots, since `generate_work_items()` may write docs under `project_brief["target_path"]`.

### Positive Observations

- The design correctly avoids direct Superpowers package import and keeps AF-owned implementation as the intended boundary.
- The design identifies the right existing gate surface: `core/approval_gate.py` and `core/work_item_generator.py` are the correct modules to inspect for Phase A.