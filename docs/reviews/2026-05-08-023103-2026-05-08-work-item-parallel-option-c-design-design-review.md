# Design Review: 2026-05-08-work-item-parallel-option-c-design

> Source: docs/2026-05-08-work-item-parallel-option-c-design.md
> Date: 2026-05-08 02:31
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Both reviewers independently flagged at least one Critical issue (Stage 2 wall-clock blowout) and four High issues converge across the two reviews. Several cited code references contradict §10 of the design ("이미 있음" claims). Resolve Critical/High findings before implementation.

---

### Aggregated Findings (14 total)

#### 1. [ACCEPT] [Critical] Stage 2 sequential `await` + thread cancel blow wall-clock budget
- **Critic #1**: Sequential `_await_or_fallback(fut_spec, ...)` then `_await_or_fallback(fut_design, ...)` each gets full `stage2_timeout`. Worst case = 360s wall-clock vs. §6 budget of 180s.
- **Cross #3**: `future.cancel()` doesn't stop running thread; `with ThreadPoolExecutor(...)` block waits on running futures, plus same 2× wall-clock issue.
- **Judgment**: Two independent reviewers, mechanical bug. §6 carry-over math becomes self-inconsistent.
- **Action Required**: Use absolute deadline. `concurrent.futures.wait({fut_spec, fut_design}, timeout=remaining, return_when=ALL_COMPLETED)`, post-process `done`/`not_done`, then `executor.shutdown(wait=False, cancel_futures=True)`. Pass remaining deadline to each `execute_document_prompt(timeout_sec=remaining)`.

#### 2. [ACCEPT] [Critical] `cleanup_stale_sessions` targets wrong directory
- **Critic #2**: §9 uses `Path("runtime/cli_sessions")` but actual path is `workspace_runtime_dir(workspace) / "cli_sessions"` (`core/providers/session_adapter.py:144-155`). Glob `claude_cli_*.*` is a no-op. Also misses `codex_cli_*` / `gemini_cli_*`. `.events` extension claim is wrong (actual: `_events.jsonl`).
- **Cross**: not flagged.
- **Judgment**: Verifiable via `core/providers/session_adapter.py:144-155`, `:151`. Cleanup silently does nothing as written.
- **Action Required**: `cleanup_stale_sessions(workspace, days=30)` with `root = workspace_runtime_dir(workspace) / "cli_sessions"`, generalize glob (`*` or per-provider patterns), pass workspace from `generate_work_items` call site.

#### 3. [ACCEPT] [High] Last-parameter signature inspection breaks `_prev_doc` injection
- **Critic #3** + **Cross #2**: Both cite `core/work_item_generator.py:847` — `list(_sig.parameters)[-1] in ("prev_plan", "prev_spec", "prev_design")`. Appending `run_id` makes `_has_prev` always False; prev-doc silently never injected.
- **Judgment**: Both reviewers, same line, same conclusion. Critic also notes consistency rubric scoring becomes invalid.
- **Action Required**: Replace introspection with explicit kwargs. Add `*, run_id="", timeout_sec=...` keyword-only, dispatch as `generator_fn(..., prev_plan=_prev_doc, run_id=full_run_id, timeout_sec=timeout)` or check `"prev_*" in _sig.parameters` (set membership, not last-position).

#### 4. [ACCEPT] [High] `DocGenerationResult` return-type contract underspecified
- **Critic Missing#1**: §10 says `_generate_and_refine` returns `DocGenerationResult` but `generate_work_items` body (lines 769, 780, 792, 804) uses bare strings as `_prev_doc` and `write_text(plan_path, plan_content)`.
- **Cross #1**: 4 generators today return `str`, called sites assume `str`. Design doesn't say which boundary unwraps to `.content`.
- **Judgment**: Both reviewers, complementary evidence. Without an explicit contract, every call site silently breaks.
- **Action Required**: Pick one contract: `_generate_doc_with_llm()` and each `_generate_feature_*()` return `DocGenerationResult`; `_generate_and_refine()` updates `.content`/`.refine_attempts`; `generate_work_items()` writes `result.content` and uses `result.content` as `_prev_doc`. Document this in §5 explicitly.

#### 5. [ACCEPT] [High] `design` generator's prev_plan injection has undefined prompt semantics
- **Critic #4**: `_generate_implementation_design` (`core/work_item_generator.py:614-651`) only renders `Feature Spec:` block when `prev_spec` truthy. Adding `prev_plan` requires either a new "Feature Plan:" block (unspecified) or relabeling. The §11 consistency rubric measures design vs. spec — if it's now design vs. plan, the "consistency 보존" claim in §2 is unverified.
- **Cross**: not flagged.
- **Judgment**: Critic backed by direct line references. Stage 2 design without a defined prev_plan injection point is implementation-blocked.
- **Action Required**: Spell out the new prompt block (e.g., "Feature Plan:" labeled section) inside §8. Restate which prev_doc the §11 Step 1 consistency rubric scores.

#### 6. [ACCEPT] [High] `execute_document_prompt` does not return `elapsed_sec`/usage — §10 "이미 있음" is false
- **Critic #5**: `core/requirement_llm.py:215-230` success dict = `{ok, provider_id, model, text, errors}`. No `elapsed_sec`, no token usage. `DocGenerationResult.elapsed_sec` (§5) needs real plumbing. OQ1 (token usage) is also a real code change, not an open question.
- **Cross**: not flagged directly.
- **Judgment**: Verifiable in `core/requirement_llm.py:215-230`. §10 explicitly claims "(이미 있음 — 확인)" — incorrect.
- **Action Required**: List in §10 as a new code change: capture `time.monotonic()` around `execute_document_prompt` call (or extend `execute_document_prompt` itself). Promote OQ1 to a §10 todo.

#### 7. [ACCEPT] [High] `timeout_sec` not wired through the call chain
- **Cross #4**: `_generate_doc_with_llm()` at `core/work_item_generator.py:527` calls `execute_document_prompt(prompt)` — no timeout. Default is 120s (`core/requirement_llm.py:178`).
- **Critic**: not separately flagged but consistent with #1.
- **Judgment**: Cross has direct line evidence. Without this plumbing, §6's stage budget never propagates to the LLM call.
- **Action Required**: Add `timeout_sec` to `_generate_and_refine()`, each generator, `_generate_doc_with_llm()`. Pass `timeout_sec=max(1, int(deadline - time.time()))` to `execute_document_prompt()`.

#### 8. [ACCEPT] [High] `refine_attempts` conflates two refine loops; T1 retry not capturable
- **Critic #6** + **Cross #6**: Two refine sites: (1) placeholder loop in `_generate_and_refine` (`work_item_generator.py:859-870`), (2) T1 QA retry in `project_pipeline.py:1003-1020`. By T1 retry time, `DocGenerationResult` objects are gone — files written and re-read. `project_pipeline.py:948` returns only `dict[name, path]`.
- **Judgment**: Both reviewers, both with line refs. Telemetry as designed cannot capture T1 retry.
- **Action Required**: Scope `refine_attempts` to placeholder loop, rename to `placeholder_refine_attempts`. Either (a) return `(files, generation_results)` from `generate_work_items`, or (b) write telemetry to `runtime/work_item_telemetry/{slug}.json` and expose `update_work_item_telemetry(slug, doc_name, t1_refine_attempts=1)` with atomic locked update.

#### 9. [ACCEPT] [Medium] run_id collision in same epoch second
- **Critic #7** + **Cross #5**: `int(time.time())` second precision. Retries / unit tests / concurrent invocations collide on same `<workspace>/.af_runtime/cli_sessions/claude_cli_<full_run_id>.json`. State path derived from slugified run_id (`core/providers/session_adapter.py:143`, `:507`).
- **Judgment**: Both reviewers. Cheap fix.
- **Action Required**: Use `time.time_ns()` plus `uuid.uuid4().hex[:8]` (or per-invocation monotonic counter): `{base}_{doc_type}_{pid}_{time_ns}_{nonce}`.

#### 10. [ACCEPT] [Medium] Future cancel leaves CLI subprocess running
- **Critic #9**: `execute_cli_chat` spawns real subprocess. Stage 2 timeout-fallback leaves background thread running until `_default_cli_timeout_sec()=900`. Worst case: 3 concurrent CLI subprocesses overlapping with Stage 3 — §7's "동시 6 호출" math undercounts.
- **Cross #3** (partial): related — `future.cancel()` doesn't stop running thread.
- **Judgment**: Both touch this. Critic has sharper consequence analysis.
- **Action Required**: Pass `timeout_sec=int(per_future_timeout) - 5` to `execute_document_prompt` so subprocess dies near future timeout. Or track subprocess handle and `kill()` on cancel.

#### 11. [ACCEPT] [Medium] Lock should wrap `_write_claude_settings`, not `prepare_cli_session`; reuse existing `core/file_lock.py`
- **Critic #10**: §4 wraps full `prepare_cli_session` (`core/providers/session_adapter.py:441`) in 5s lock — serializes all CLI calls box-wide. Real race is only `_write_claude_settings` (`:281-304`). §12 R1 misdescribes lock primitive (`core/file_lock.py:64` uses `O_CREAT | O_EXCL`, not `fcntl.flock`).
- **Cross #7**: `core/file_lock.py:37` already exists with `locked_file()` — thread+process protection, stale cleanup, timeout. Already in `af.spec:76`. Don't reinvent.
- **Judgment**: Combined: scope down + reuse existing primitive.
- **Action Required**: `with locked_file(str(settings_path), timeout=5):` *inside* `_write_claude_settings()` body wrapping load→merge→save. Update §12 R1 to reflect actual primitive (`O_CREAT|O_EXCL`).

#### 12. [ACCEPT] [Medium] `_extract_section_outline` regex fragile to LLM drift
- **Critic #8**: Regex `^##\s+(.+)$` breaks on `##Section`, `## **bold**`, extra `##` (TOC). traceability §N matching breaks deterministically on off-by-one.
- **Cross**: not flagged.
- **Judgment**: Critic alone, but argument is concrete and the rubric impact is tied to traceability scoring.
- **Action Required**: Add normalization (strip `*_`, collapse whitespace, dedupe), assert outline length matches expected spec template section count (currently 11).

#### 13. [ACCEPT] [Low] Wrong file path in §10
- **Critic #11**: §10 references `core/session_adapter.py:474, 476`. Actual path is `core/providers/session_adapter.py`.
- **Action Required**: Fix path. Spot-check other paths in §10.

#### 14. [ACCEPT] [Low] §11 Step 2 N=1 vs Step 1 N=5
- **Critic #12**: Step 2 single run + Step 5 acceptance "Total time 단축 ≥ 1.3배" near §2 estimate 1.33× — coin flip on LLM variance.
- **Action Required**: N≥3 for Step 2 with median; or call Step 2 a binary smoke and move time-comparison to Step 4 with N≥5.

---

### Additional Items from Critic's "Missing from Design"

| Item | Verdict | Action |
|------|---------|--------|
| Stage 1 fallback cascade (fallback plan → spec/design/tasks) | ACCEPT (Med) | Add explicit "skip downstream LLM if upstream fell back" rule, or document that fallback content propagates |
| Approval-gate sequencing under fallback/timeout | ACCEPT (Low) | Confirm `gate.initialize` still runs after Stage 3 fallback (currently always runs) |
| `af.spec` `hiddenimports` for `core.cli_session_cleanup` | ACCEPT (Low) | Add `af.spec` to §10 changed-files table |
| Step 0 lock contention test (artificially block to confirm 5s timeout) | ACCEPT (Low) | Add to §11 Step 0 |
| Cleanup vs. concurrent-pid-recycled sessions | HOLD (Low) | 30d TTL is conservative enough that pid recycle window is effectively zero; flag only if cleanup window shortens |

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Stage 2 sequential await wall-clock blowout | Critical | ACCEPT | Both |
| 2 | cleanup path wrong (`runtime/` vs `.af_runtime/`) | Critical | ACCEPT | Critic |
| 3 | Last-param signature inspection breaks prev_doc | High | ACCEPT | Both |
| 4 | DocGenerationResult return-type contract | High | ACCEPT | Both |
| 5 | design prev_plan prompt semantics undefined | High | ACCEPT | Critic |
| 6 | `elapsed_sec` not in `execute_document_prompt` | High | ACCEPT | Critic |
| 7 | `timeout_sec` not wired through call chain | High | ACCEPT | Cross |
| 8 | `refine_attempts` conflates 2 layers / T1 telemetry | High | ACCEPT | Both |
| 9 | run_id collision (same epoch second) | Medium | ACCEPT | Both |
| 10 | Future cancel doesn't kill CLI subprocess | Medium | ACCEPT | Both |
| 11 | Lock layer + reuse existing `core/file_lock.py` | Medium | ACCEPT | Both |
| 12 | Outline regex fragile | Medium | ACCEPT | Critic |
| 13 | Wrong path `core/session_adapter.py` → `core/providers/...` | Low | ACCEPT | Critic |
| 14 | §11 Step 2 N=1 vs Step 1 N=5 | Low | ACCEPT | Critic |
| M2 | Stage 1 fallback cascade undefined | Medium | ACCEPT | Critic |
| M3 | Approval-gate behavior under fallback | Low | ACCEPT | Critic |
| M4 | `af.spec` hiddenimports for cleanup module | Low | ACCEPT | Critic |
| M5 | Step 0 lock contention assertion | Low | ACCEPT | Critic |
| M6 | Cleanup vs pid recycle | Low | HOLD | Critic |

### Recommendations (in priority order)

Before implementation, update the design document with:

1. **§7 (Critical)**: Replace sequential `_await_or_fallback` with `concurrent.futures.wait(..., timeout=remaining, return_when=ALL_COMPLETED)` + `executor.shutdown(wait=False, cancel_futures=True)`. Pass remaining deadline to subprocess.
2. **§9 (Critical)**: Take `workspace` parameter, resolve via `workspace_runtime_dir(workspace) / "cli_sessions"`. Generalize glob. Fix `.events` → `_events.jsonl` claim.
3. **§3 + §10 (High)**: Replace last-param introspection with keyword-only dispatch. Add `*, run_id="", timeout_sec=...` to all 4 generators. Spell out where `prev_plan` injects in `_generate_implementation_design` prompt.
4. **§5 + boundary contract (High)**: State explicitly that all 4 generators return `DocGenerationResult` and `generate_work_items` writes `.content`. Update line-787-style call sites.
5. **§10 corrections (High)**: Remove "이미 있음" for `elapsed_sec`. Add real plumbing. Promote OQ1 (token usage) to §10 todo. Wire `timeout_sec` through `_generate_and_refine` → generators → `_generate_doc_with_llm` → `execute_document_prompt`. Fix `core/session_adapter.py` → `core/providers/session_adapter.py`.
6. **§5 (High)**: Rename `refine_attempts` → `placeholder_refine_attempts`. Decide: return `(files, results)` from `generate_work_items` OR add atomic locked telemetry update helper for T1 retry.
7. **§3 (Medium)**: Use `time.time_ns() + uuid4().hex[:8]` for run_id uniqueness.
8. **§7 (Medium)**: Pass `timeout_sec=int(per_future_timeout) - 5` to `execute_document_prompt` so subprocess dies with future.
9. **§4 + §12 R1 (Medium)**: Reuse existing `locked_file()` from `core/file_lock.py:37`. Scope inside `_write_claude_settings()` only. Correct §12 R1 primitive description.
10. **§8 (Medium)**: Normalize outline regex; assert section count.
11. **§11 (Low)**: N≥3 for Step 2 with median, or split smoke vs. timing.
12. **Add to §10**: `af.spec` hiddenimports for `core.cli_session_cleanup`.
13. **Add to §1 or §11**: Stage 1 fallback cascade rule + approval-gate sequencing under fallback.

After the design is updated, re-run af-cross-review on the revised document.