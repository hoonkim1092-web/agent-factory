# Design Review: 2026-04-29-multi-provider-cross-review

> Source: docs/2026-04-29-multi-provider-cross-review.md
> Date: 2026-04-29 15:41
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 3 providers)
> Trigger: claude

---

## Final Design Review

### Verdict: BLOCK

At least 2 Critical findings (one factual command-syntax error per Critic, one architectural bypass of existing CLI infra per Cross) plus a stack of High-severity bugs. Do not implement until §2.3 auth matrix is rewritten and the fan-out is moved off hand-written bash into the existing `execute_cli_chat()` path.

---

### Aggregated Findings (15 total)

#### 1. [ACCEPT] [Critical] Auth ping matrix invents wrong commands and duplicates SSOT
- **Critic**: `codex login --check` doesn't exist; real command is `codex login status` per `core/providers/cli.py:105` (`auth_status_command=("login", "status")`). All codex users → permanent AUTH_EXPIRED → BLOCK.
- **Cross**: Same area. `claude_cli` already has `("auth", "status")` at `core/providers/cli.py:78`; design says Claude has no explicit auth status. Whole matrix is a second source of truth that already disagrees with code.
- **Judgment**: Both reviewers flag the same defect with concrete code references. Critic also catches `gemini --yolo` (real is `--approval-mode yolo`, `core/providers/cli.py:92`).
- **Action Required**: Delete §2.3 auth matrix. Reuse `get_cli_provider_spec()` and expose `probe_cli_auth(provider_id, timeout_sec=5)` wrapping existing preflight/classification. Make `core/providers/cli.py` the single source of truth for auth/edit commands.

#### 2. [ACCEPT] [Critical] Fan-out bypasses existing CLI execution contracts (`CliChatRequest` / `execute_cli_chat()`)
- **Critic**: not flagged at this level (but #2/#3/#4 are downstream symptoms of the same cause).
- **Cross**: Design hand-writes `codex exec ... gemini --yolo -p ...` in bash, bypassing env stripping (`core/providers/cli.py:348`), auth preflight (`:414`), execution (`:698`), and prior parallel art at `core/cross_verification.py:179`.
- **Judgment**: Strong evidence. Moving fan-out to a Python runner using `CliChatRequest(timeout_sec=180)` + `execute_cli_chat()` automatically fixes Critic #2, #3, and partially #4.
- **Action Required**: Implement fan-out as `core/review_fanout.py`. `af-cross-review.md` calls the runner; do not author shell commands inline.

#### 3. [ACCEPT] [High] Fixed `/tmp/cr-codex.txt` / `/tmp/cr-gemini.txt` paths collide under concurrent work-items
- **Critic**: Two work-items in parallel (or nightly + interactive) overwrite the same path → result loss.
- **Cross**: Not flagged (but Cross #4 is the analogous defect on the cache file).
- **Judgment**: Resolved by adopting Finding #2 (Python runner with `tempfile`). If kept in bash: use `mktemp -t cr-<provider>.XXXXXX`.
- **Action Required**: Eliminate fixed `/tmp/*` paths.

#### 4. [ACCEPT] [High] Cache write is not concurrency-safe; T12 is inadequate
- **Critic**: not flagged.
- **Cross**: Fixed `path.with_suffix('.json.tmp')` is atomic per replace but not multi-writer safe. Prior art in `core/dynamic_orchestrator.py` uses `NamedTemporaryFile`. T12 must run multi-thread + multi-process.
- **Judgment**: Cited prior art in repo. Strong.
- **Action Required**: `tempfile.NamedTemporaryFile(delete=False, dir=cache_dir, suffix=".tmp")` + `os.replace()` + `filelock` for read-modify-write. Strengthen T12.

#### 5. [ACCEPT] [High] `exit 0` PASS-THROUGH does not terminate a Claude Code subagent; review-gate parsing untested
- **Critic**: Subagent terminates on model stream end, not bash exit code. Also `scripts/review_gate.py` regex compatibility with "SKIP — 외부 프로바이더 없음" header is unverified.
- **Cross**: not flagged.
- **Judgment**: Critic's runtime model is correct; gate is the Tier 3 chokepoint per CLAUDE.md.
- **Action Required**: Specify final report wording (e.g. `**Verdict: PASS (no external providers)**`). Add a regression test against `scripts/review_gate.py` accepting that wording. Add §1.1 row for `scripts/review_gate.py` (Critic #11 absorbed here).

#### 6. [ACCEPT] [High] Provider scope is ambiguous — opportunistic stale CLI can block Tier 3
- **Critic**: not flagged.
- **Cross**: `providers=None → CLI_PROVIDER_IDS 전체` + auth_expired BLOCK means an old Gemini install blocks Tier 3 even if only Codex is configured. `core/providers/registry.py:52, :246` already supports configured-vs-installed distinction.
- **Judgment**: Strong code reference. Default-strict on every installed CLI is wrong.
- **Action Required**: Define candidate set: configured providers (via `AGENT_CHAT_PROVIDER`/runtime config) → strict; opportunistic providers → warn-only unless `AF_STRICT_PROVIDER_AUTH=1`.

#### 7. [ACCEPT] [High] 2nd-fallback cost estimate "1~10 tokens" is unrealistic
- **Critic**: `claude -p "ok"` etc. are full model calls; system prompt + tool defs make input tokens hundreds-to-thousands. Hourly TTL × 3 providers × N machines is non-trivial for Opus.
- **Cross**: not flagged.
- **Judgment**: Critic's mental model of CLI cost is correct.
- **Action Required**: Mandate token-free status command per provider where one exists; forbid drop-through to `-p "ok"` for `claude_cli` (already self per R7). Lock the matrix; remove "구현 시 결정".

#### 8. [ACCEPT] [Medium] `provider_detect` CLI output contract underspecified
- **Cross**: `2>&1` capture corrupts JSON if any warning hits stderr. Unknown `AF_SKIP_PROVIDER` IDs warn to stderr while same command must be JSON-readable.
- **Judgment**: Concrete contradiction in design.
- **Action Required**: `{"version":1,"states":{...},"fan_out":[],"blocked":[],"warnings":[]}`. stdout JSON-only under `--json`; warnings inside JSON; nonzero exit only for malformed args / fatal errors, not for `blocked`.

#### 9. [ACCEPT] [Medium] AUTH_EXPIRED classification is too broad
- **Critic**: Timeout/network/IO hang all collapse to AUTH_EXPIRED → user gets wrong "re-login" guidance.
- **Judgment**: `_AUTH_REQUIRED_MARKERS` already exists at `core/providers/cli.py:119-132`; design ignores it.
- **Action Required**: Add `DEGRADED` state. Only mark AUTH_EXPIRED when stderr matches `_AUTH_REQUIRED_MARKERS`; otherwise `DEGRADED`/`UNKNOWN` with different user-facing message.

#### 10. [ACCEPT] [Medium] `AF_HOME` is a new undefined convention
- **Critic**: `AF_HOME` not in repo (only this design doc). `core/config_paths.py` already has `PROJECT_ROOT`, `RUNS_DIR` etc.
- **Action Required**: Add `AF_USER_CACHE_DIR` (or equivalent) to `core/config_paths.py` as SSOT. Document `~/.af` fallback verified under frozen `af.exe`.

#### 11. [ACCEPT] [Medium] `python -m core.provider_detect` semantics under frozen `af.exe` undefined
- **Critic**: `python -m` works only on host Python; `hiddenimports` only matters for in-process import. Two call sites (subagent bash vs core module) must be distinguished.
- **Action Required**: §1.1 / §8 Sprint A: state explicitly the module is invoked from the subagent host Python; `af.spec` change is precautionary. If a core caller exists, name it.

#### 12. [ACCEPT] [Medium] R3 mitigation hook doesn't exist
- **Critic**: §10 R3 says "Step 2 명령 실패 hook" but §5.2 has only `&` + `wait`.
- **Action Required**: Either inspect each provider's stderr/exit for `_AUTH_REQUIRED_MARKERS` and call `--invalidate <id>` + retry once, or downgrade R3 to "1h stale-cache window is accepted risk".

#### 13. [ACCEPT] [Medium] Dedup / consensus not implementable
- **Cross**: "same file:line + wording similarity" with no schema/threshold/fallback. Existing `af-cross-review.md` outputs free-form prose.
- **Action Required**: Require provider results in `{title, section, issue, evidence, suggestion, severity}` JSON. Dedup by normalized evidence path/line + title similarity threshold; uncertain → `possible_duplicate_of`.

#### 14. [ACCEPT] [Medium] Deployment checklist missing `version.py` and `install-af.ps1`
- **Cross**: CLAUDE.md:23/25 mandates both; current `version.py = 1.2.22`.
- **Action Required**: Add both to Sprint B / deployment section.

#### 15. [ACCEPT] [Medium] §12 Open Questions deferred to "implementation time"
- **Critic**: Q1/Q4 (matrix commands) are interface decisions, not implementation details. Q3 "ACCEPT 우선순위 상향" is undefined.
- **Action Required**: Resolve Q1/Q4 in this doc (covered by Findings #1, #2, #7). Define Q3 concretely (report ordering vs verdict weighting).

---

### Held / Rejected

#### 16. [HOLD] [Medium] Shell portability (bash vs PowerShell on Windows)
- **Cross**: Repo is Windows-primary; design assumes bash + `/tmp`.
- **Question for Author**: Does Claude agent `Bash` tool always run a POSIX-compatible shell on this Windows host? If not guaranteed, Finding #2 (Python runner) becomes mandatory rather than recommended.

#### 17. [REJECT] Concern that `core/providers/registry.py` should change
- **Source**: Cross
- **Rejection Reason**: Keeping registry stable is correct — `core/model_router.py`, `core/project_task_board.py`, `core/parallel_critique.py`, `core/cross_verification.py` rely on installation-only semantics. New auth-aware layer should sit beside, not replace.

---

### Summary Table

| #  | Title                                                       | Severity | Verdict | Source |
|----|-------------------------------------------------------------|----------|---------|--------|
| 1  | Auth matrix invents wrong commands; duplicates SSOT         | Critical | ACCEPT  | Both   |
| 2  | Fan-out bypasses `CliChatRequest`/`execute_cli_chat()`      | Critical | ACCEPT  | Cross  |
| 3  | Fixed `/tmp/cr-*.txt` collision under concurrent runs       | High     | ACCEPT  | Critic |
| 4  | Cache write not concurrency-safe; T12 inadequate            | High     | ACCEPT  | Cross  |
| 5  | `exit 0` PASS-THROUGH; review-gate regex untested           | High     | ACCEPT  | Critic |
| 6  | Provider scope ambiguous; opportunistic CLI blocks Tier 3   | High     | ACCEPT  | Cross  |
| 7  | 2nd-fallback "1~10 tokens" cost estimate unrealistic        | High     | ACCEPT  | Critic |
| 8  | `provider_detect` CLI output contract underspecified        | Medium   | ACCEPT  | Cross  |
| 9  | AUTH_EXPIRED too broad (timeout/net/auth merged)            | Medium   | ACCEPT  | Critic |
| 10 | `AF_HOME` is new undefined convention                       | Medium   | ACCEPT  | Critic |
| 11 | `python -m core.provider_detect` frozen-build semantics     | Medium   | ACCEPT  | Critic |
| 12 | R3 mitigation hook doesn't exist                            | Medium   | ACCEPT  | Critic |
| 13 | Dedup/consensus not implementable                           | Medium   | ACCEPT  | Cross  |
| 14 | Missing `version.py` / `install-af.ps1` updates             | Medium   | ACCEPT  | Cross  |
| 15 | Open Questions deferred to "implementation time"            | Medium   | ACCEPT  | Critic |
| 16 | Shell portability on Windows                                | Medium   | HOLD    | Cross  |
| 17 | Keep `registry.py` unchanged                                | —        | REJECT  | Cross  |

---

### Recommendations (concrete actions before implementation)

1. **Delete §2.3 auth matrix.** Build `probe_cli_auth(provider_id)` that reuses `CliProviderSpec.auth_status_command` from `core/providers/cli.py`. One source of truth.
2. **Re-architect fan-out as `core/review_fanout.py`** using `CliChatRequest` + `execute_cli_chat()` with `ThreadPoolExecutor` (mirror `core/cross_verification.py:179`). `af-cross-review.md` shells out to this runner; no inline `codex exec`/`gemini` commands.
3. **Lock the candidate-provider policy.** Configured-strict + opportunistic-warn, gated by `AF_STRICT_PROVIDER_AUTH` for the override.
4. **Define a 4th state `DEGRADED`** for timeout/network and only mark `AUTH_EXPIRED` on `_AUTH_REQUIRED_MARKERS` match.
5. **Specify CLI JSON contract** (`{version, states, fan_out, blocked, warnings}`) — stdout JSON-only; warnings inside payload; non-zero exit only for fatal errors.
6. **Resolve Open Questions Q1/Q3/Q4 in the doc** (not at implementation time).
7. **Specify Tier-3 SKIP report wording** and add a regression test against `scripts/review_gate.py`. Add `scripts/review_gate.py` to §1.1 matrix.
8. **Add `version.py` bump and `install-af.ps1` 3-spot update** to Sprint B.
9. **Replace `AF_HOME`** with `AF_USER_CACHE_DIR` in `core/config_paths.py`; document frozen-build verification.
10. **Cache write**: `NamedTemporaryFile` + `filelock`; T12 multi-thread + multi-process.
11. **Resolve HOLD #16** by confirming Windows `Bash` shell guarantees, otherwise Finding #2 (Python runner) becomes blocking, not recommended.