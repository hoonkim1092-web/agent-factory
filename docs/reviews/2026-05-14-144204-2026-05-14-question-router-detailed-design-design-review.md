# Design Review: 2026-05-14-question-router-detailed-design

> Source: docs/2026-05-14-question-router-detailed-design.md
> Date: 2026-05-14 14:42
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] Stage 0 pause cannot stop Stage 1-3 in the proposed insertion point
   - Section: "`1095e: stage0 = StageRouter(...).run(...)`", "`paused_hitl 상태는 별도 채널 ... 반환 dict는 정상 구조`", "`project_pipeline.py 가 plan_verifier 진입 전 gate.is_execution_open() 체크`"
   - Issue: This does not match the current call flow. `core/work_item_generator.py:1104-1173` runs Stage 1-3 immediately after the proposed insertion, and `gate.initialize()` is only called at `core/work_item_generator.py:1233-1234`. `core/project_pipeline.py:970-1080` enters `PlanVerifier` and review gates after `generate_work_items()` returns. There is no existing gate check before Stage 1-3 because the gate does not exist yet.
   - Suggestion: Make Stage 0 an explicit preflight before Stage 1. If `paused_hitl` or BLOCK occurs, return immediately from `generate_work_items()` with only Stage 0 artifacts plus `approval-gate.md`, or move Stage 0 into `ProjectPipeline` before calling `generate_work_items()`. Add a concrete code block showing the early return path.

2. [Critical] `QuestionRouterCliLLMCaller` uses a non-existent `CliChatRequest` API
   - Section: "`CliChatRequest(provider_id=self._provider, messages=[...], timeout_sec=..., response_format={...})`"
   - Issue: The real dataclass in `core/providers/cli.py:31-39` requires `provider_id`, `model`, `system_prompt`, `task_input`, `workspace`, and has no `messages` or `response_format` fields. This design will fail at construction with `TypeError`.
   - Suggestion: Redesign this adapter against the real API:
     `CliChatRequest(provider_id=..., model=default_chat_model_for_provider(...), system_prompt=..., task_input=prompt, workspace=..., run_id=..., timeout_sec=int(timeout_sec))`. Enforce JSON through prompt/schema parsing, not `response_format`.

3. [High] Frozen build plan omits YAML data files
   - Section: "`core/control/questions/goal_clarification.yaml` 신규", "`core/control/questions/brainstorming.yaml` 신규", and "`af.spec hiddenimports 추가 대상`"
   - Issue: `af.spec:27-31` includes `skills`, `config`, `policy.yaml`, and `core/research/packs`, but not `core/control/questions`. The design only adds hidden imports for Python modules. In `dist/af/af.exe`, `QuestionRouter(schema_path=Path(...))` can import but fail to load YAML schemas.
   - Suggestion: Add an `af.spec` `datas` entry for `core/control/questions`, and add a frozen smoke test that loads both YAML files, not just imports Python modules.

4. [High] Acceptance criteria still use invalid `blast_radius` tokens
   - Section: "`unit test: NEEDS_ADR × {local, module, system_wide, security, data} 5케이스`"
   - Issue: The same document says valid tokens are `{isolated, module, cross_module, system_wide}` and maps `security/data` to `BlockCause`. Existing `core/control/change_impact.py` also emits only those four tokens. This P5 checklist will drive implementation/tests back into the rejected taxonomy.
   - Suggestion: Replace the P5 matrix with `NEEDS_ADR × {isolated, module, cross_module, system_wide}`. Add separate tests for `BlockCause.POLICY_VIOLATION` and `BlockCause.SAFETY`.

5. [Medium] `assumptions.md` locking strategy claims capabilities the current code does not provide
   - Section: "`assumptions.md ... _append_lock 패턴 재사용 + lock 파일 + msvcrt/fcntl locking`"
   - Issue: `core/control/run_ledger.py:20` has a private module-level `_append_lock`, and `append()` writes only to `.af_runtime/control/run_ledger.jsonl`. Also, `run_ledger.py:106-120` uses `msvcrt`; there is no `fcntl` path in the current implementation. Reusing this for `<work_dir>/assumptions.md` is not an existing API.
   - Suggestion: Define a concrete helper, e.g. `append_jsonl_with_lock(path, line)` in `core/file_io.py` or `core/control/run_ledger.py`, with Windows and POSIX behavior covered by tests.

6. [Medium] Resume design lacks a real RunLedger query path
   - Section: "`ProjectPipeline 시작 시 RunLedger에서 가장 최근 state='paused_hitl' entry 검색`"
   - Issue: `RunLedger` currently exposes `append`, `open_run`, `update_run`, and read-style internals, but the design does not specify the actual method to find the latest paused entry by `run_id`, `work_item_slug`, or workspace. Without that, resume can pick the wrong paused HITL in a multi-run workspace.
   - Suggestion: Add `RunLedger.latest_state(run_id, state)` or `find_latest_paused_hitl(work_item_slug)` to the design, including tie-breaking and stale-run handling.

### Missing from Design

- Exact early-return contract when Stage 0 pauses or blocks before Stage 1 files exist.
- `af.spec` `datas` addition for `core/control/questions/*.yaml`.
- Concrete JSON parsing/error handling for CLI outputs that are not valid JSON.
- Cleanup/retry behavior for partial Stage 0 artifacts after LLM timeout or schema validation failure.
- Multi-run disambiguation for paused HITL resume.

### Positive Observations

- The design correctly separates `QuestionRoute`, `DomainVerdict`, and `BlockCause`, which avoids mixing routing decisions with domain gate outcomes.
- The correction to use raw YAML bytes for schema hash and store the hash only in artifacts/ledger avoids the self-referential hash drift problem.