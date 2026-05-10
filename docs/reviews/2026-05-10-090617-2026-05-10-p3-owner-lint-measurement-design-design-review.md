# Design Review: 2026-05-10-p3-owner-lint-measurement-design

> Source: docs/2026-05-10-p3-owner-lint-measurement-design.md
> Date: 2026-05-10 09:06
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

3 Critical (2 stale-wording 자기모순 + 1 CSV-warnings 계약 충돌) + 5 High (자기검증 체크리스트·테스트 카운트·핵심 API 누락) + 5 Medium + 2 Low. v4 헤더가 retract 12건을 흡수했다고 단언하나 §2.1·§6.4·§11.5·§11.6 4 곳에 stale wording 잔존 + iter_warning_records/CSV 계약이 v4 #3 "warnings SoT" 결정과 충돌. 구현 전 본문 정합화 필수.

### Aggregated Findings (15 total)

#### 1. [ACCEPT] [Critical] §2.1 Scope #3가 v4 #4 retract와 정반대 — config/ 이동 wording 잔존
- **Critic**: §2.1 line 108이 "`runtime/warnings/_index.json` → `config/warning_registry_index.json` 이동" 그대로. baseline 검증으로 retract 결정 자체는 정합 (`_index.json` reader 0건).
- **Cross**: 동일 finding. .gitignore가 `runtime/warnings/_index.json`을 이미 화이트리스트, `config/warning_registry_index.json` 미존재.
- **Judgment**: 양 reviewer 동의 + repo 실측. §0.1/§3.1/§3.2/§6.0/§7 #6은 in-place로 통일됐으나 §2.1만 stale.
- **Action Required**: §2.1 #3 → "`runtime/warnings/_index.json` in-place schema v2 갱신 (v4 #4 retract 적용 — config/ 이동 철회) — `owner_role_mismatch`에 `measure_at: P3` + `mode: observation` 추가 + `source` `:1401`→`:1455` 정정. `activate_at: P4` 유지."

#### 2. [ACCEPT] [Critical] §6.4 source 정정 채널이 stale path 지칭
- **Critic**: §6.4 line 528이 `config/warning_registry_index.json.rules[].source`를 정정 대상으로 적시 → 존재하지 않는 파일. 실제는 `runtime/warnings/_index.json:13` + `core/project_pipeline.py:1466` 두 곳.
- **Cross**: 직접 거론은 없으나 #1과 동일 origin issue.
- **Judgment**: Critic 단독이지만 baseline grep으로 검증된 강한 증거 (`runtime/warnings/_index.json:13`에 실제 `source` 필드 존재).
- **Action Required**: §6.4 정정 채널 1)을 "`runtime/warnings/_index.json`의 owner_role_mismatch entry `source` 필드 → `core/project_pipeline.py:1455`"로 교체.

#### 3. [ACCEPT] [Critical] CSV Export가 "warnings: list[str] is SoT" 계약 위반
- **Critic**: not flagged
- **Cross**: §3.3은 warnings를 SoT 채널로 단언, §5.2 CSV columns은 metadata row 없음. malformed JSONL skip 시 warnings 전달 채널 부재.
- **Judgment**: Cross 단독이지만 §5.2 column 명세 직접 인용 + v4 #2/#3 결정과의 정합성 충돌이라는 강한 evidence. CSV vs JSON 출력 contract divergence는 implementer가 임의 선택할 위험.
- **Action Required**: CSV 모드는 (a) stderr로 warnings 출력 + exit 0 명시, 또는 (b) `--out` 사용 시 companion `<filename>.warnings.json` 동시 작성 중 택1. §8.2에 해당 동작 assertion 추가.

#### 4. [ACCEPT] [High] `iter_warning_records` 시그니처가 warnings/scanned_slug_count 운반 불가
- **Critic**: not flagged
- **Cross**: `iter_warning_records(...) -> Iterator[tuple[str, dict]]`만으론 malformed/missing slug warnings 및 `scanned_slug_count` 운반 불가. 현재 `WarningRegistry.summarize()`는 단일 호출로 dict 반환.
- **Judgment**: 강한 code-ref evidence (`core/warning_registry.py:270`). v4 #6 "공유 iterator" 결정과 v4 #3 "warnings SoT" 결정이 시그니처 차원에서 호환 불가.
- **Action Required**: `WarningScan(records, warnings, scanned_slug_count)` dataclass 도입, 또는 mutable `warnings: list[str]` 파라미터 추가. records export도 동일 path 공유 시 `phase` 파라미터도 추가.

#### 5. [ACCEPT] [High] `--top` 소유권 — core API에 `top` 파라미터 부재
- **Critic**: not flagged
- **Cross**: `collect_workspace_stats()` 시그니처에 `top` 없음. truncation이 core인지 CLI인지 불명. 기존 CLI는 thin wrapper convention(`run_factory_cli.py:281`).
- **Judgment**: 강한 evidence + convention 일관성 인용. ambiguity 해소 미루면 구현자 임의 결정.
- **Action Required**: `collect_workspace_stats(workspace, *, rule_id, slug=None, phase=None, top=0) -> dict` (`top=0`은 unlimited). summary export는 `top=0` 호출 명시.

#### 6. [ACCEPT] [High] `--phase` 필터가 기존 phase normalization과 충돌
- **Critic**: not flagged
- **Cross**: `_normalize_phase()`가 write 시 `design→scope`/`test→verify`/unknown→`build` 변환(`core/warning_registry.py:24,75`). `--phase design` 필터는 0건 반환. 테스트도 alias 동작 assert(`tests/test_warning_registry.py:102`).
- **Judgment**: 코드/테스트 직접 인용으로 재현 가능한 회귀 시나리오. 명세 미정의 시 implementer가 raw match로 만들 가능성.
- **Action Required**: §5.1에 "CLI `--phase`도 `_normalize_phase()` 거쳐 canonical phase로 비교" 1줄. original-phase 필터 필요 시 `--original-phase` 별도 옵션은 P4 deferred로 명시.

#### 7. [ACCEPT] [High] 테스트 케이스 수가 절마다 다름 (4가지 인용)
- **Critic**: §2.1 "9 케이스" / §3.2 "6+6=12" + "§8.2 #7~#12 (6 인용)" / §8 header "16" / §8.1 "(7)" + §8.2 "(9)". 본문 카운트 7+9=16만 §8 header와 일치.
- **Cross**: 동일 finding, "16 = 7 core + 9 CLI"로 통일 권고.
- **Judgment**: 양 reviewer 동의 + 본문 직접 카운트로 정답 확정.
- **Action Required**: §2.1 #5 → "테스트 16 케이스 — §8.1 (7) + §8.2 (9)". §3.2 row 7,8 → 각각 "7 케이스 (§8.1 #1~#7)" / "9 케이스 (§8.2 #8~#16)". `tests/test_warning_registry_cli.py` 4 case와 PR 성공 기준 동기화.

#### 8. [ACCEPT] [High] §11.5 row 3이 사라진 §7 packaging 행 reference
- **Source**: Critic
- **Original Finding**: row 3이 §7 #6,#7,#8 packaging 행을 가리키나 §7 #7=af.spec hiddenimports, #8=version.py — packaging 무관. v3 packaging 행은 retract로 모두 제거됨.
- **Judgment**: 자기검증 체크리스트가 retract 미반영 — 본문과 직접 충돌하는 self-contradiction.
- **Action Required**: §11.5 row 3 → "_index.json packaging 미정의 (v4 #4 retract로 §6.0 in-place + §6.6 `_load_index` direct read로 흡수)". reference에서 §7 #7,#8 제거.

#### 9. [ACCEPT] [High] §11.6 row v3 #1이 retract된 결정을 "흡수했다"로 단언
- **Source**: Critic
- **Original Finding**: §11.6 line 739가 "v3 #1 `_index.json` 위치 이동"을 본문 통일 항목으로 잔존. §11.7 v4 #4 retract 주장과 정면 충돌.
- **Judgment**: 자기검증 체크리스트의 자기모순. critic #1/#2와 동일 root cause.
- **Action Required**: row v3 #1 → "v3 #1 `_index.json` 위치 이동 — v4 #4가 retract (config/ 이동 철회, in-place 유지). 본문 정합 위치: §0.1/§3.1/§3.2 row 4/§6.0/§7 #6/§10.2".

#### 10. [ACCEPT] [High] §11.5 마지막 줄: PR 변경 파일 11→8 단언이 §7과 불일치
- **Source**: Critic
- **Original Finding**: §11.5 line 712 "11→8개로 단순화"인데 §7 표는 row 1~10. 두 숫자 모두 불일치.
- **Judgment**: 직접 카운트로 검증 가능. self-validation 체크리스트가 본문과 직접 충돌.
- **Action Required**: §7 표 재카운트 후 정확한 수치(10 추정)로 수정.

#### 11. [ACCEPT] [Medium] §4.2 n=0 stdout 예시가 신규 메타 필드 누락
- **Source**: Critic
- **Original Finding**: §3.3에 v4 #9로 추가한 `project_count_total/returned`가 §4.2 n=0 JSON에 부재. §4.3 n=3은 포함 — 비대칭.
- **Judgment**: schema↔example 비대칭, 단순 stale.
- **Action Required**: §4.2 JSON에 `"project_count_total": 0, "project_count_returned": 0` 추가. §8.1 case 1 assertion 보강.

#### 12. [ACCEPT] [Medium] schema_version 동음이의 (stats output v1 vs _index.json v2)
- **Source**: Critic
- **Original Finding**: §3.3 `schema_version: 1`(stats output)과 §6.1 `schema_version: 2`(_index.json) 동시 존재, 분리 표기 부재.
- **Judgment**: P4에서 stats output bump 시 혼동 위험. 1줄 disclaimer로 해소 가능.
- **Action Required**: §3.3, §6.1 schema 위에 "(stats output schema, _index.json schema와 별개)" 각각 1줄 추가.

#### 13. [ACCEPT] [Medium] records+csv+phase 조합 테스트 부재
- **Source**: Critic
- **Original Finding**: §8.2 case 14는 summary+json+phase만 검증. v4 #5 records 모드 phase filter 회귀 가능.
- **Judgment**: v4 #5 신규 결정 검증 갭.
- **Action Required**: case 14에 sub-case "records --format csv --phase build → CSV row 수 = build affected_phase record 수" 추가.

#### 14. [ACCEPT] [Medium] `--slug` sanitization이 argparse 단에만 — core 직접 호출 우회 가능
- **Source**: Critic
- **Original Finding**: v4 #7은 argparse error만. `collect_workspace_stats(slug="../etc")` 직접 호출 방어 부재. §8.1 case 7은 raise 명시하나 §3.3 docstring엔 없음.
- **Judgment**: defense-in-depth + docstring↔테스트 정합.
- **Action Required**: §3.3 `collect_workspace_stats`/`iter_warning_records` docstring에 "slug sanitization: 빈/슬래시/`..`/`os.path.basename(slug) != slug`이면 `ValueError`" 1줄 추가.

#### 15. [ACCEPT] [Medium+Low] tmp 파일 충돌 + ISO timezone 명시 + partial-line fixture (3건 묶음)
- **Source**: Critic
- **Findings**:
  - §5.1 `<filename>.tmp.<pid>` — 컨테이너 PID 재사용/사용자가 `--out *.tmp.csv` 지정 시 충돌. → `tempfile.NamedTemporaryFile(dir=parent, prefix=f".{filename}.tmp.", delete=False)` 권고.
  - §5.3 `exported_at` "Z" suffix가 spec 본문에 미명시. → "`datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')`" 1줄 추가.
  - §8.1 case 6에 "trailing newline 부재 + 잘린 JSON" sub-fixture 추가.
- **Judgment**: 3건 모두 implementer 임의 선택 위험. low-effort 명시화로 해소.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §2.1 #3 stale config/ wording | Critical | ACCEPT | Both |
| 2 | §6.4 stale path 정정 채널 | Critical | ACCEPT | Critic |
| 3 | CSV가 warnings SoT 계약 위반 | Critical | ACCEPT | Cross |
| 4 | iter_warning_records 시그니처 결함 | High | ACCEPT | Cross |
| 5 | `--top` core API 부재 | High | ACCEPT | Cross |
| 6 | `--phase` normalization 충돌 | High | ACCEPT | Cross |
| 7 | 테스트 카운트 4가지 불일치 | High | ACCEPT | Both |
| 8 | §11.5 row 3 packaging stale | High | ACCEPT | Critic |
| 9 | §11.6 v3 #1 retract 자기모순 | High | ACCEPT | Critic |
| 10 | §11.5 PR 파일 11→8 wrong | High | ACCEPT | Critic |
| 11 | §4.2 n=0 메타 필드 누락 | Medium | ACCEPT | Critic |
| 12 | schema_version 동음이의 | Medium | ACCEPT | Critic |
| 13 | records+csv+phase 테스트 갭 | Medium | ACCEPT | Critic |
| 14 | core slug sanitization 정책 | Medium | ACCEPT | Critic |
| 15 | tmp 충돌 + tz + partial-line | Medium/Low | ACCEPT | Critic |

### Recommendations

1. **본문 정합화 1차** (#1, #2, #8, #9, #10) — v4 retract 4개 stale 절(§2.1 #3, §6.4, §11.5 row 3 + 마지막 줄, §11.6 row v3 #1)과 §7 PR 파일 카운트를 한 번에 sweep. grep `config/warning_registry_index.json` / `위치 이동` / `packaging` 으로 회귀 검증.
2. **계약 명확화** (#3, #4, #5, #6) — v4 #2/#3/#5/#6/#9 결정이 시그니처/CSV column 차원에서 호환되도록 §3.3 시그니처 4건 (`collect_workspace_stats(top, phase 추가)`, `iter_warning_records → WarningScan`, `--phase canonical normalize`, CSV warnings 채널) 동시 패치.
3. **테스트 spec 통일** (#7) — "16 케이스 = §8.1 (7) + §8.2 (9)" 4 곳 동기화 + PR 성공 기준 명시.
4. **세부 명세 보강** (#11~#15) — §4.2 메타 필드, schema_version 분리 표기, records+csv+phase sub-case, core sanitization docstring, tmp/tz/partial-line 명세 한꺼번에.
5. **v5 헤더에 "본문 정합 sweep" 명시** — v4가 retract 12건 흡수했다고 단언했으나 본문 stale 4 곳 + 계약 충돌 3 곳 잔존이 BLOCK 원인이었음을 명시해 향후 self-validation 체크리스트가 본문과 cross-check되도록 protocol 보강.