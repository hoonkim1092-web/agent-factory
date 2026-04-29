# Design Review: 2026-04-29-multi-provider-cross-review

> Source: docs/2026-04-29-multi-provider-cross-review.md
> Date: 2026-04-29 15:36
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 3 providers)
> Trigger: claude

---

## Final Design Review

### Verdict: BLOCK

Critic flags 1 Critical (Windows/frozen-build path collision) and 3 High items (frozen `python -m`, unverified auth-ping commands, nightly regression). Cross adds 4 ACCEPT-grade contract gaps (exclude-self, auto-login safety, stderr PII, cache identity, exit codes) — most reinforcing Critic. Implementation must wait until §5.2 paths, §5.1 entry point, §2.3 ping matrix, and §10 R6 nightly fail-soft are resolved in the doc itself.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] `/tmp/cr-*.txt` fixed paths break Windows/frozen + race on parallel runs
- **Critic**: §5.2 uses `-o /tmp/cr-codex.txt` and `> /tmp/cr-gemini.txt`; Windows is primary target, fixed filenames collide on N-way fan-out and concurrent work-items.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. Evidence is direct (the commands are in §5.2 as quoted), and the existing `af-cross-review.md:53` already shows the same anti-pattern. With fan-out the collision surface multiplies.
- **Action Required**: Replace `/tmp/cr-*.txt` with a per-call `mktemp -d` directory; clean up on exit. Specify the cleanup hook in §5.2.

#### 2. [ACCEPT] [High] `python -m core.provider_detect` won't run from frozen `af.exe`
- **Critic**: §5.1 / §8 Sprint B Step 1 — frozen builds don't expose `-m` semantics; system Python likely lacks `core.provider_detect`.
- **Cross**: #6 — same call site is also missing exit-code contract.
- **Judgment**: ACCEPT. Frozen build constraint is documented in CLAUDE.md (`dist/af/af.exe`), and §1.1 doesn't list `run_factory_cli.py` changes — entry-point gap is real.
- **Action Required**: Add an `af provider-detect --json [--exclude-self ID] [--invalidate ID|all]` subcommand to `run_factory_cli.py`; update §1.1 matrix; have `af-cross-review.md` call `af provider-detect` (frozen) with `python -m core.provider_detect` fallback (dev). Specify exit codes per Cross #6: `0` on completed detection regardless of `blocked`, nonzero only on internal errors.

#### 3. [ACCEPT] [High] Auth-ping command matrix is unverified — feasibility deferred to implementation
- **Critic**: §2.3 Q1 / §12 Q4 — `codex login --check`, `gemini auth status`, `claude --version` for auth all marked "구현 시 결정". If 1차 status commands don't exist, every ping falls to token-burning 2차 → cost model in R1 invalidated.
- **Cross**: #3 — closely related: probe must be non-interactive and must not invoke `_run_cli_auth_preflight()` which can auto-login (`AGENT_AUTO_LOGIN_CLI` defaults true at `core/providers/cli.py:388`).
- **Judgment**: ACCEPT (escalate to High; both reviewers point at the same matrix). Cross adds a concrete constraint — auto-login on probe would mutate state and could hang the gate.
- **Action Required**: Run `claude --help`, `codex --help`, `gemini --help` once, finalize §2.3 with confirmed commands, and explicitly mark probe mode as `allow_login=False` / `AGENT_AUTO_LOGIN_CLI=0`. Add a test asserting "auth required does not trigger login".

#### 4. [ACCEPT] [High] AUTH_EXPIRED BLOCK is a known nightly-pipeline regression shipped intentionally
- **Critic**: §10 R6 acknowledges it but defers `AF_SKIP_PROVIDER=auth_expired_*` mitigation to a follow-up. CLAUDE.md confirms nightly pipeline is active.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. Critic's evidence is the design's own §10 wording — the document admits the regression. Shipping with a known stop-the-world failure mode is unacceptable for an active automated pipeline.
- **Action Required**: Include nightly fail-soft in P1 / Sprint B: when `AF_NIGHTLY=1` and only AUTH_EXPIRED reasons are blocking, auto-skip those providers (drop from `fan_out`) and log to `runs/.../auth_expired_alerts.jsonl`.

#### 5. [ACCEPT] [High] `stderr_excerpt` persistence is a PII/secrets leak
- **Critic**: "Missing from Design" — stderr may contain tokens/user IDs; cache stored as plaintext.
- **Cross**: #4 — same issue with concrete reference: `core/providers/cli.py:459` already collects auth stderr; design upgrades transient diagnostics into durable sensitive data at `~/.af/provider_cache.json:126`.
- **Judgment**: ACCEPT (both reviewers, same area). Cross provides the stronger reference.
- **Action Required**: Persist only `category` + `auth_hint` + redacted short message. Keep raw `stderr_excerpt` in memory only. Add a redaction filter for token/URL/path patterns before display.

#### 6. [ACCEPT] [High] `--exclude-self` is used but not in the API contract
- **Critic**: not flagged.
- **Cross**: #2 — `detect_provider_states()` signature has no `exclude` param, but Step 0 calls `--exclude-self claude_cli`.
- **Judgment**: ACCEPT. Direct doc-internal contradiction (lines 95 vs 175 of design doc).
- **Action Required**: Add `exclude: list[str] | None = None` to API; define `--exclude-self` and `--exclude ID[,ID]` in CLI contract; specify whether excluded providers appear in `states` JSON (recommend: omit from `fan_out`/`blocked`, retain in `states` for diagnostics).

#### 7. [ACCEPT] [Medium] `core/provider_detect.py` location violates `core/providers/` layout
- **Critic**: §5 — existing `registry.py`, `cli.py`, `session_adapter.py` all live under `core/providers/`. Splitting the new module to `core/` root creates import-direction ambiguity and scatters `af.spec` hiddenimports.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. Evidence is verifiable in repo layout; consistency-only argument is strong.
- **Action Required**: Move to `core/providers/detect.py`. Update §1.1, §7, and `af.spec` hiddenimport accordingly.

#### 8. [ACCEPT] [Medium] Cache identity is underspecified (AF_HOME convention + multi-user/multi-binary)
- **Critic**: #6 — `AF_HOME` has 0 references in repo; `~/.af/` is PC-local while CLAUDE.md mandates Supabase sync — sync policy unstated.
- **Cross**: #5 — additionally, cache keyed only by provider ID can cross-contaminate when `AGENT_GLOBAL_USER_KEY`/PATH/CLI binary changes.
- **Judgment**: ACCEPT (both reviewers, complementary angles). Merge into one entry — cache identity model is incomplete.
- **Action Required**: (a) Define `PROVIDER_CACHE_PATH` in `core/config_paths.py` (e.g., `RUNS_DIR.parent / "provider_cache.json"`), document why this is *not* Supabase-synced (auth state is per-PC). (b) Cache key = `(provider_id, resolved_executable_path, env_override_value)`; add version output if cheap. Spec this in §3.

#### 9. [ACCEPT] [Medium] §5.3 dedup algorithm is undefined
- **Critic**: #7 — "키워드 유사" has no threshold; codex vs gemini line numbering may differ (pre/post patch); consensus weighting depends 100% on dedup accuracy.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. The §5.3 wording is verifiably vague; downstream consensus logic is load-bearing.
- **Action Required**: Specify in §5.3: dedup matches when **all** of (a) file path exact, (b) line ±3, (c) severity label exact, (d) title Jaccard ≥ 0.5. Define parser fallback when codex/gemini output isn't structured.

#### 10. [ACCEPT] [Medium] R3 stale-cache fan-out failure hook is unimplemented in §5.2
- **Critic**: #8 — §10 R3 promises "force_refresh on failure" but §5.2 only does `wait` for exit codes.
- **Cross**: not flagged.
- **Judgment**: ACCEPT. R3 mitigation is referenced but not realized in the algorithm step.
- **Action Required**: In §5.2, add: "if any fan-out exit code != 0, invoke `af provider-detect --invalidate <id>` and report BLOCK without retry (avoid infinite loop)."

#### 11. [HOLD] [Medium] Reuse existing `ParallelCritiqueEngine` / `CrossVerificationLoop` instead of bash fan-out?
- **Critic**: not flagged.
- **Cross**: #1 — `core/parallel_critique.py:130` and `core/cross_verification.py:188` already implement parallel provider execution.
- **Judgment**: HOLD. Genuinely missing info: Tier 3 is currently a Claude subagent prompt; whether it can/should call into Python is an architectural choice not stated in the design. Reusing existing engines could eliminate Findings #1, #2, and most of §5.2's complexity — but may conflict with the agent-prompt-only constraint.
- **Question for Author**: Must Tier 3 stay a pure prompt-level subagent, or can `af-cross-review.md` shell out to a thin `core.review_runner` wrapper? Decide before §5.2 implementation; the answer reshapes Findings #1 and #2.

#### 12. [REJECT] [Low] None
- No findings rejected. All Critic and Cross items have direct evidence in the design doc or repo.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `/tmp/cr-*.txt` fixed paths (Windows/race) | Critical | ACCEPT | Critic |
| 2 | `python -m core.provider_detect` in frozen build | High | ACCEPT | Critic + Cross#6 |
| 3 | Auth-ping matrix unverified (+ no auto-login) | High | ACCEPT | Critic + Cross#3 |
| 4 | AUTH_EXPIRED BLOCK regresses nightly | High | ACCEPT | Critic |
| 5 | `stderr_excerpt` persistence leaks PII | High | ACCEPT | Critic + Cross#4 |
| 6 | `--exclude-self` missing from API contract | High | ACCEPT | Cross |
| 7 | `provider_detect.py` location mismatch | Medium | ACCEPT | Critic |
| 8 | Cache identity underspecified (AF_HOME + binary key) | Medium | ACCEPT | Critic + Cross#5 |
| 9 | §5.3 dedup algorithm undefined | Medium | ACCEPT | Critic |
| 10 | R3 stale-cache failure hook unimplemented | Medium | ACCEPT | Critic |
| 11 | Reuse existing parallel engines? | Medium | HOLD | Cross |
| 12 | (none rejected) | — | — | — |

### Recommendations

Before implementation begins, the design document must be updated with:

1. **§5.2** — replace `/tmp/cr-*.txt` with per-call `mktemp -d`; add cleanup. Add R3 force_refresh hook on fan-out failure.
2. **§1.1 + §5.1 + §8** — add `af provider-detect` subcommand to `run_factory_cli.py`; switch shell calls to `af provider-detect` with `python -m` dev fallback.
3. **§2.3** — actually run `claude/codex/gemini --help`, finalize the auth-ping matrix, mark probes as non-login (`AGENT_AUTO_LOGIN_CLI=0`).
4. **§10 R6 + Sprint B** — fold nightly fail-soft (`AF_NIGHTLY=1` + AUTH_EXPIRED-only → auto-skip) into P1 scope, not "후속".
5. **§3** — drop raw `stderr_excerpt` from cache; persist redacted hint only. Define cache key as `(provider_id, exec_path, env_override)`. Move file to `RUNS_DIR.parent / provider_cache.json` via `core/config_paths.py`. Document non-Supabase-sync rationale.
6. **§2.4 + §5.1** — add `exclude` parameter to API; specify `--exclude-self` + `--exclude` CLI flags; specify probe exit codes (0 on success even with `blocked`, nonzero on internal error only).
7. **§5 / §1.1 / §7 / af.spec** — relocate new module to `core/providers/detect.py`.
8. **§5.3** — write the concrete dedup rule (path exact + line ±3 + severity exact + title Jaccard ≥ 0.5) and parser-failure fallback.
9. **Architecture decision (Finding #11)** — decide whether Tier 3 may call into a Python `review_runner` wrapper. If yes, revisit §5.2 entirely; if no, document why before merging.