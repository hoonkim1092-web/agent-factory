# Design Review: 2026-05-10-p3-owner-lint-measurement-design

> Source: docs/2026-05-10-p3-owner-lint-measurement-design.md
> Date: 2026-05-10 08:23
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

At least 5 Critical/High findings that constitute genuine doc inconsistencies — body and §3.2/§7 still reference old `_index.json` path while §6 declares the move; CLI dispatch name mismatch (`_HANDLERS` vs actual `_STAGE1_DISPATCH`); §3.2 self-contradiction on `project_pipeline.py:1466`; install-af.ps1 count off (3 vs 8); off-by-one source line. v3 cross-review will re-raise these unless fixed.

**Important note**: Several of the critic's "Critical" findings (#1, #3, parts of #4) are **factually wrong** — the critic appears to have read an outdated copy. The actual document body §3.3/§4.1/§4.3/§5.1 *does* include `--slug`, `by_per_record_count`, `applied_filters`, `by_phase_total_unfiltered`. These are REJECTED below.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] `_index.json` location move is half-applied
- **Critic #5**: §3.2 row 5, §7 row 5, §10.3 still say `runtime/warnings/_index.json`; §6 says new `config/warning_registry_index.json`. `af.spec datas` entry not in §3.2.
- **Cross #1**: Same — "§2.1, §3.1, §6, §7, rollback, and Blueprint notes still describe editing `runtime/warnings/_index.json`".
- **Judgment**: Verified — §3.2 line 133 and §7 line 531 still reference `runtime/warnings/_index.json`; §10.2 line 592 says "_index.json.schema_version". §6 alone uses new path. Both reviewers agree, evidence is in the doc.
- **Action Required**: Replace all `runtime/warnings/_index.json` references with `config/warning_registry_index.json` in §3.2, §3.1, §7, §10. Add `af.spec datas: ('config/warning_registry_index.json', 'config')` row to §3.2's changed-files table. Add a test that `dist/af-1.2.26/_internal/config/warning_registry_index.json` exists post-build.

#### 2. [ACCEPT] [Critical] CLI wiring uses non-existent `_HANDLERS` name
- **Critic**: not flagged
- **Cross #2**: §3.2 says "`_HANDLERS`/`_STAGE1_USAGE` 2 entry 추가" but the current router uses `_STAGE1_DISPATCH` and `_STAGE1_USAGE`.
- **Judgment**: Verified at `run_factory_cli.py:429`/`:474`/`:580/:588` — no `_HANDLERS` exists. Implementer following §3.2 literally would either invent a new dict or miss the dispatch path.
- **Action Required**: §3.2 row 2 → "`_STAGE1_DISPATCH` + `_STAGE1_USAGE` 각 2 entry 추가". §8.2 add a CLI test asserting both subcommand names are present in `_STAGE1_DISPATCH`.

#### 3. [ACCEPT] [Critical] §3.2 self-contradiction: `project_pipeline.py:1466` literal edit vs "변경 없음" list
- **Critic #2**: §3.2 changed-files table omits the `source_path="...:1401"` literal edit at line 1466, AND footer explicitly lists `core/project_pipeline.py` under "변경 없음".
- **Cross**: not flagged (treats #6.4 narrative as sufficient)
- **Judgment**: Verified at `core/project_pipeline.py:1466` — literal `source_path="core/project_pipeline.py:1401"` exists. §6.4 mandates editing this literal but §3.2 says the file is untouched. The two sections are mutually inconsistent. Critic's evidence is concrete (file:line).
- **Action Required**: Add `core/project_pipeline.py | 1466 source_path 리터럴 정정 | 1줄` row to §3.2. Remove `core/project_pipeline.py` from the "변경 없음" line.

#### 4. [ACCEPT] [High] Source line number is off by one (1454 → should be 1455)
- **Critic #7**: 1454 = import statement; 1455 = `.record(` callsite. §6.4 says fix to "1454" — wrong line.
- **Cross**: not flagged
- **Judgment**: Verified — line 1454 is `from core.warning_registry import WarningRegistry as _WR`, line 1455 is `_WR(workspace=workspace).record(`. The conventional source pointer is the callsite, not the import.
- **Action Required**: §6.4 and §6.2 (`source` field example) → `core/project_pipeline.py:1455`. §1.1 baseline grep row → "`1454-1469`" should remain a range but the canonical pointer is `:1455`.

#### 5. [ACCEPT] [High] install-af.ps1 line count discrepancy (3 vs 8)
- **Critic #6**: §3.2 says "3 lines"; changelog header says 8; verified actual is 7-8 hits.
- **Cross**: not flagged
- **Judgment**: Verified `grep -c '1\.2\.25' install-af.ps1` returns **8** (lines 3, 6, 27, 34, 105, 106, 110, 251). §3.2/§7 row 7 still say "3곳".
- **Action Required**: §3.2 row 9 + §7 row 7 → "8곳 (lines 3, 6, 27, 34, 105, 106, 110, 251)". Add post-PR verification: `grep -c '1\.2\.25' install-af.ps1` must return 0.

#### 6. [ACCEPT] [High] §8.1 case 5 contradicts the §3.3/§4.3 phase-filter contract
- **Critic #4 (sub-point)**: §8.1 case 5 says "v1에서는 **필터된 phase만 by_phase_total에 출력**으로 정의" — but §3.3/§4.3.1 already specify both `by_phase_total` (filtered) AND `by_phase_total_unfiltered` (full distribution). Test case 5 ignores `by_phase_total_unfiltered`/`applied_filters` assertions.
- **Cross #4**: Same area — "Update all JSON examples to exactly match the declared schema."
- **Judgment**: §3.3 line 230 and §4.3.1 line 348 declare `by_phase_total_unfiltered`. §8.1 case 5 (line 548) still has stale "v1에서는…" wording that pre-dates the v2 schema. The schema itself in §3.3/§4.3 is correct (rejecting the cross/critic claim that schema is stale), but the test case wording is.
- **Action Required**: Rewrite §8.1 case 5 to assert (a) `applied_filters.phase == "build"`, (b) `by_phase_total` contains only `build`, (c) `by_phase_total_unfiltered` contains all phases pre-filter. Add the assertion to §8.2 case 9 too if export inherits the contract.

#### 7. [ACCEPT] [Medium] `--rule` validation silently zeros real data
- **Critic**: not flagged
- **Cross #6**: If `<rule>.jsonl` exists for an unregistered rule, returning 0 records discards data. SoT (`WarningRegistry.record`) doesn't require index registration.
- **Judgment**: Verified at `core/warning_registry.py:126` — `.record()` writes the jsonl regardless of index. §4.5 line 364 says unregistered → "0건 결과 반환" which throws away on-disk data. Reasonable concern; cross's evidence (registry SoT vs index meta) is solid.
- **Action Required**: §4.5 → "unregistered `--rule`: warnings에 1줄 + jsonl 스캔은 그대로 진행". Add `--strict-rule` flag if zero-on-unknown is genuinely needed.

#### 8. [ACCEPT] [Medium] §8.4 frozen-build smoke hardcodes `af.exe` despite changelog claim
- **Critic #9**: §8.4 line 565 still says `dist/af-1.2.26/af.exe` even though changelog item 10 claims macOS branching was added. Current dev host is darwin → smoke fails.
- **Cross**: not flagged
- **Judgment**: Confirmed at line 565. Changelog says one thing, body says another.
- **Action Required**: §8.4 → "host OS frozen build — Windows: `af.exe`, macOS/Linux: `af`". Verify `python build_exe.py` produces correct artifact name on host.

#### 9. [ACCEPT] [Medium] Test matrix doesn't cover `--slug` filter or `--mode summary --format csv` rejection
- **Critic #11**: Even after schema is honored, §8.1/§8.2 don't cover `--slug single`, `--slug missing`, `--mode summary --format csv` argparse error, `--out` with non-existent dir, malformed-mid-write race.
- **Cross #3 partial**: "Add tests for `warning-stats --slug one` and `warning-export --slug one`."
- **Judgment**: §8.1 6 cases + §8.2 3 cases (line 542-555) — none mention `--slug`. §5.4 line 430 mandates `--mode summary --format csv` argparse error but no test asserts it.
- **Action Required**: Add §8.1 case 7 `single_slug_filter` + case 8 `missing_slug_warning`. §8.2 add case 10 `cli_summary_csv_argparse_error`.

#### 10. [HOLD] [Medium] schema_version 1→2 bump with no reader
- **Critic #10**: §6.5 says "어떤 코드도 schema_version을 읽지 않음 — 메타데이터" / §10.3 "마이그레이션 불필요". Bumping is no-op.
- **Cross**: not flagged
- **Judgment**: Defensible to add a defensive reader (cheap), but equally defensible to defer the bump to P4 when there's a real semantic break. Critic's preference is reasonable but not load-bearing.
- **Question for Author**: Do you want a fail-fast check `assert schema_version <= 2` at index load time in P3, or defer the bump to P4 where it actually means something?

### Rejected Findings

#### R1. [REJECT] [Critical] Critic #1 — `--slug` missing from §4.1/§5.1 signatures
- **Source**: Critic
- **Original Finding**: "§4.1 signature is `af warning-stats --workspace PATH [--rule RULE_ID] [--top N] [--phase PHASE]`. Neither has `--slug`."
- **Rejection Reason**: Verified directly: §4.1 line 276 reads `af warning-stats --workspace PATH [--slug SLUG] [--rule RULE_ID] [--top N] [--phase PHASE]`. §5.1 line 376 reads `af warning-export --workspace PATH [--slug SLUG] --format {csv,json} ...`. Both include `--slug`. Argument tables (§4.1 line 282, §5.1 line 382) describe the option. Critic appears to have read a stale copy. (Cross #3 has the same error.)

#### R2. [REJECT] [Critical] Critic #3 — `by_per_record_count` distribution missing
- **Source**: Critic
- **Rejection Reason**: §3.3 line 224-227 declares all three Distribution dimensions including `by_per_record_count`. §4.3 line 323 includes `"by_per_record_count": {"n": 7, ...}` in the example. §3.4 line 257 explicitly defines its population. Already applied.

#### R3. [REJECT] [High] Cross #4 (schema example lag) — partially correct
- **Source**: Cross
- **Rejection Reason for schema field claim**: Cross says §4.3 still shows old `by_count`/`by_repeat_count_max`. Verified — §4.3 actually uses `by_project_count`, `by_project_repeat_count_max`, `by_per_record_count` (line 321-324) and includes `applied_filters`/`by_phase_total_unfiltered` (line 312, 326). Schema is consistent. (The §8.1 case 5 sub-point IS valid — captured in finding #6 above.)

#### R4. [REJECT] [Medium] Critic #8 — `iter_warning_records` not exposed as shared API
- **Source**: Critic
- **Rejection Reason**: §3.3 line 186-201 declares `iter_warning_records` as a public function with explicit slug/rule_id signature. §5.1 line 388 explicitly states "records 모드는 `iter_warning_records(workspace, rule_id=..., slug=...)`를 그대로 소비". Spec already mandates the shared iterator.

#### R5. [REJECT] [Low] Critic #12 — median rule conflict
- **Source**: Critic
- **Rejection Reason**: §3.4 line 253 reads "`median`: Python `statistics.median` (n 짝수면 두 중앙값의 평균)". No "nearest-rank" phrase. Critic again read stale copy.

#### R6. [REJECT] Cross #5 — Warning channel contradiction
- **Source**: Cross
- **Rejection Reason**: §4.4 line 358-359 explicitly defines the contract: stdout = single JSON with `warnings: []` array; stderr = optional mirror. These are complementary channels, not contradictory. §3.5 line 265 reinforces "stdout은 절대 오염시키지 않는다". The two channels coexist intentionally for human-readable mirroring. Not an issue.

#### R7-R8. [REJECT] Cross #7, #8 — self-rejected
- Both flagged then rejected by cross itself; no action.

#### R9. [REJECT] Critic #13 — withdrawn by critic
- p95 formula is correct; critic self-withdrew.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_index.json` move half-applied (§3.2/§7/§10 vs §6) | Critical | ACCEPT | Both |
| 2 | CLI dispatch dict name mismatch (`_HANDLERS`) | Critical | ACCEPT | Cross |
| 3 | §3.2 self-contradiction on `project_pipeline.py:1466` | Critical | ACCEPT | Critic |
| 4 | Source line off-by-one (1454→1455) | High | ACCEPT | Critic |
| 5 | install-af.ps1 count: doc 3, actual 8 | High | ACCEPT | Critic |
| 6 | §8.1 case 5 stale wording vs phase-filter contract | High | ACCEPT | Both |
| 7 | `--rule` unknown silently returns 0 records | Medium | ACCEPT | Cross |
| 8 | §8.4 frozen smoke hardcodes `af.exe` (host=darwin) | Medium | ACCEPT | Critic |
| 9 | Test matrix missing `--slug`, summary+csv reject | Medium | ACCEPT | Both |
| 10 | schema_version 1→2 bump with no reader | Medium | HOLD | Critic |
| R1 | `--slug` missing from CLI signatures | Critical | REJECT | Critic+Cross |
| R2 | `by_per_record_count` missing | Critical | REJECT | Critic |
| R3 | Schema examples use old keys | High | REJECT | Cross |
| R4 | `iter_warning_records` not shared | Medium | REJECT | Critic |
| R5 | median rule conflict | Low | REJECT | Critic |
| R6 | warnings channel contradiction | Medium | REJECT | Cross |

### Recommendations

Resolve before re-firing v3 cross-review:

1. **Path consistency** — single search-and-replace `runtime/warnings/_index.json` → `config/warning_registry_index.json` across §2.1, §3.1, §3.2 row 5, §7 row 5, §10.2/§10.3. Add `af.spec datas` row to §3.2.
2. **CLI dispatch name** — §3.2 row 2: `_HANDLERS` → `_STAGE1_DISPATCH`.
3. **§3.2 row for `project_pipeline.py:1466`** — add the literal edit row; remove from "변경 없음".
4. **Source line** — §6.4/§6.2 use `:1455` (callsite), not `:1454` (import).
5. **install-af.ps1** — §3.2/§7 say "8곳"; add post-PR `grep -c '1\.2\.25'` = 0 verification step.
6. **§8.1 case 5** — rewrite assertions to match v2 schema (`applied_filters` + `by_phase_total_unfiltered`).
7. **§4.5 unknown rule** — change "0건 반환" → "warnings 1줄 + jsonl 스캔 진행".
8. **§8.4** — branch frozen-build smoke by host OS.
9. **Tests** — add `--slug` cases (single, missing) + `--mode summary --format csv` argparse-error case.
10. **HOLD #10** — author decides: defensive reader now, or defer bump to P4.

The critic and cross both made factual errors on the schema/CLI signatures by reading an earlier draft; verify the document text directly during v3 to avoid a third round of stale-baseline false positives.