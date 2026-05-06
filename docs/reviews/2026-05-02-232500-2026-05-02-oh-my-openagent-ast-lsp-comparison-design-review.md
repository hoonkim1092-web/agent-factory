# Design Review: 2026-05-02-oh-my-openagent-ast-lsp-comparison

> Source: docs/참고/2026-05-02-oh-my-openagent-ast-lsp-comparison.md
> Date: 2026-05-02 23:25
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Two Critical findings from Critic + four ACCEPT-grade scope/contract gaps from Cross. Document body contradicts its own §10 changelog, and any future plan rooted in §7.3/§8 inherits unspecified contracts.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] §10 changelog over-promises corrections that don't appear in the body
- **Critic**: Listed v2 corrections (§9.4 신설, §9.1 SHA pin, §5.2 1-based, §5.3 line range, §6 권원 표시) — none verifiable in the document body; §9.4 doesn't exist, §9.1 still uses `/dev/`, §5.4 line 167 still says `188-208`.
- **Cross**: not flagged.
- **Judgment**: Strong line-by-line evidence from Critic (lines 167, 261-266, 111-122, 258-277). For an analysis document whose stated value is traceability (§1 line 7: "확인 범위 내에서 추정 사용 없음"), claiming corrections that weren't applied destroys the audit trail.
- **Action Required**: Apply each promised v2 correction to the body, OR walk back the §10 entries that weren't implemented. Reconcile §10 ↔ body in one pass.

#### 2. [ACCEPT] [Critical] Q-D 98% PASS lacks sample-bias / source caveat
- **Critic**: §5.4 Q-D line 169-177 presents 51/1 ≈ 98% PASS as flat statistic; §10 claims "표본 편향·silent failure 후보 정정" but body doesn't disclose source (`hook_events.log`) or that `docs/reviews/*.md` headers show 16 BLOCK + 25 WARN — 16× difference.
- **Cross**: not flagged.
- **Judgment**: Two divergent BLOCK counts from two sources, with the higher-reliability number presented. Readers will misinterpret as system-wide reliability.
- **Action Required**: Add source attribution and reconciliation with `docs/reviews/*.md` headers, OR remove the percentage.

#### 3. [ACCEPT] [High] §9.4 reproducibility commands missing
- **Critic**: §10 promises "§9.4 신설: Q-A~Q-F 추출 명령" but §9 ends at §9.3 (line 277). Q-A 1/46, Q-C 552, Q-D 51/1 etc. are not reproducible without these commands.
- **Cross**: not flagged.
- **Judgment**: The most concrete numbers in the document have no `grep`/`jq` recipe. Audit trail is incomplete.
- **Action Required**: Add §9.4 with exact extraction commands per Q-A~Q-F.

#### 4. [ACCEPT] [High] AGENTS.md / tool-descriptions.ts citations not pinned to commit SHA
- **Critic**: §9.1 source URLs use `/dev/` mutable branch; quotations at lines 44, 61 unverifiable as branch advances. §10 v2 explicitly promises SHA pin.
- **Cross**: not flagged.
- **Judgment**: Single-line evidence (URLs in §9.1 lines 263-266). Promised correction unimplemented.
- **Action Required**: Replace `/dev/` with permalinks at a specific commit SHA.

#### 5. [ACCEPT] [Medium] §5.3 line-range contradiction (188-208 vs 191-212)
- **Critic**: §10 claims 188-208 → 191-212 corrected, but line 167 still reads `188-208`. Three values in circulation with no resolution.
- **Cross**: not flagged.
- **Judgment**: Re-measurement deferred from prior round. Concrete contradiction.
- **Action Required**: Re-read `.claude/settings.local.json` now, write the verified range, sync §5.3/§5.4 body and §10 entry.

#### 6. [ACCEPT] [Medium] §5.2 schema missing line-numbering convention (1-based vs 0-based)
- **Critic**: schema doesn't disclose `review_bundle.py:55` does `+1` (1-based) while `ast_engine.py:91` returns 0-based raw. Plan-load-bearing contract.
- **Cross #1 (related)**: notes AST scope underspecified, including line conventions for non-Python files.
- **Judgment**: Both reviewers converge on §5.2 schema being underspecified for downstream consumption.
- **Action Required**: Add one line to §5.2: "line은 review_bundle.py:55 +1 정규화 → 1-based; ast_engine.py:91 raw는 0-based."

#### 7. [ACCEPT] [Medium] §5.2 schema missing file_path absolute/relative contract
- **Critic**: `build_review_bundle.py:53` does `Path(workspace) / f` → absolute paths; cross-PC non-portable. Schema silent.
- **Cross**: not flagged.
- **Judgment**: Direct code reference; multi-PC environment context (per CLAUDE.md) makes this real.
- **Action Required**: Document `{file_path}` as absolute, non-portable across workspace roots.

#### 8. [ACCEPT] [Medium] §2.3 추정 표현 contradicts §1 "추정 사용 없음" principle
- **Critic**: §2.3 line 49 contains "분리된 것으로 보이지만 단정 불가" while §1 line 7 declares no speculation.
- **Cross**: not flagged.
- **Judgment**: Internal inconsistency in stated principle.
- **Action Required**: Excise speculative clause; keep only "본 fetch 범위 내에서 미확인."

#### 9. [ACCEPT] [Medium] AST tool scope underspecified for any future plan
- **Critic #8 (related)**: line-numbering convention.
- **Cross**: `build_review_bundle.py:47` filters `.py` only; `ast_engine.py:29,53` defaults unknown to Python. §7.3 architectural gap mentions ast-grep AI tool exposure but no language scope.
- **Judgment**: Strong code evidence from Cross. §8 "AI tool wrapper 신설 시 비용 + 효과 가설" inherits this gap.
- **Action Required**: Add scope contract to §7.3/§8 follow-up: v1 Python-only OR declared language enum + unsupported-language behavior.

#### 10. [ACCEPT] [Medium] Rename-safe workflow gap mischaracterizes current LSPCheckHook
- **Critic**: not flagged.
- **Cross**: `lsp_check.py:103` shells `pyright --outputjson`; no JSON-RPC client, no `prepareRename`. §7.3 implies LSPCheckHook activation could close the gap, but it cannot.
- **Judgment**: Direct code evidence at `core/hooks/lsp_check.py:103`. §7.3 / §8 #5 ("pyright 동봉 비용 vs subagent 전파") understate the actual implementation surface.
- **Action Required**: §7.3 must note rename-safe requires a new LSP client (didOpen lifecycle, JSON-RPC, prepare/rename), not just enabling `LSPCheckHook`.

#### 11. [ACCEPT] [Medium] LSPCheckHook activation gap — `_WRITE_TOOLS` hardcoded
- **Critic**: not flagged.
- **Cross**: `_WRITE_TOOLS` at `core/hooks/lsp_check.py:29` doesn't include `apply_edit` / `apply_block_edit` (`skills/hash_edit/skill.py:23`, `skills/hashline_edit/skill.py:20`). Even if activated, hook misses existing edit tools.
- **Judgment**: Direct code evidence. Material to "LSPCheckHook 활성화/유지/제거" follow-up in §8.
- **Action Required**: Note in §5.1 / §8: activation requires either `_WRITE_TOOLS` extension or write-result metadata contract.

#### 12. [ACCEPT] [Medium] §8 비용 dimension promised but unsupplied
- **Critic**: §8 #4, #5 reference "비용" comparison axis without any sizing.
- **Cross #4 (related)**: future AST/LSP observability has no structured logging contract.
- **Judgment**: §8 makes cost claims without cost data; Cross adds that even basic event/skip logging is absent at `lsp_check.py:205`.
- **Action Required**: Either drop "비용" from §8 (defer to plan), or add order-of-magnitude estimate AND define event names (`lsp_check_skipped`, `lsp_check_result`, `ast_tool_search`) before any plan inherits unanchored numbers.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §10 changelog over-promises | Critical | ACCEPT | Critic |
| 2 | Q-D 98% no sample-bias caveat | Critical | ACCEPT | Critic |
| 3 | §9.4 reproducibility commands missing | High | ACCEPT | Critic |
| 4 | Citations not SHA-pinned | High | ACCEPT | Critic |
| 5 | §5.3 line-range contradiction | Medium | ACCEPT | Critic |
| 6 | §5.2 line-numbering convention missing | Medium | ACCEPT | Critic+Cross |
| 7 | §5.2 file_path absolute/relative missing | Medium | ACCEPT | Critic |
| 8 | §2.3 추정 contradicts §1 principle | Medium | ACCEPT | Critic |
| 9 | AST tool scope underspecified | Medium | ACCEPT | Cross |
| 10 | Rename-safe gap mischaracterized | Medium | ACCEPT | Cross |
| 11 | `_WRITE_TOOLS` hardcoded | Medium | ACCEPT | Cross |
| 12 | §8 비용 dimension + observability missing | Medium | ACCEPT | Critic+Cross |

Note: Critic #10 (§2.1 lsp_servers 출처 부재, Low) is consolidated into the broader citation-pin issue (#4) — same root cause.

### Recommendations

Before this analysis can be cited as evidence by any future plan:

1. **Reconcile §10 changelog with body in one pass.** Either apply the v2 corrections (§9.1 SHA pin, §9.4 신설, §5.2 line-base note, §5.3/§5.4 line-range, §6 권원, §5.4 sample-bias caveat) or delete the changelog entries that weren't implemented. (#1, #2, #3, #4, #5)
2. **Pin all external source URLs to commit SHAs in §9.1.** No `/dev/` references. (#4)
3. **Add §9.4 with reproduction commands** for Q-A~Q-F numbers (`grep`/`jq` invocations + denominators). (#3, "Missing: Q-A 분모 정의")
4. **Re-measure `.claude/settings.local.json` line range** and write the verified value once across §5.3, §5.4 body, §10 changelog. (#5)
5. **Document §5.2 schema contracts**: 1-based line normalization (with code reference) + absolute file_path + multi-PC non-portability. (#6, #7)
6. **Excise §2.3 speculation** to maintain §1 principle integrity. (#8)
7. **Add scope/contract notes to §7.3 and §8** before they seed a plan: AST tool language scope, LSP-client-vs-LSPCheckHook distinction, `_WRITE_TOOLS` extension requirement, observability event names. (#9, #10, #11, #12)
8. **Add document version field at top** so v1/v2 readers can self-identify. ("Missing from Design")

Once #1–#5 are addressed, severity drops to WARN; #6–#12 can be deferred into the plan documents that consume this analysis.