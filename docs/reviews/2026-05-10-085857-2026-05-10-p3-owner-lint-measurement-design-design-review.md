# Design Review: 2026-05-10-p3-owner-lint-measurement-design

> Source: docs/2026-05-10-p3-owner-lint-measurement-design.md
> Date: 2026-05-10 08:58
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

2명의 리뷰어가 독립적으로 동일한 핵심 균열을 지적했습니다. v4 헤더는 cross-review v4 BLOCK 12건을 모두 흡수했다고 단언하지만, 본문이 헤더 결정과 정반대 상태로 잔존하는 self-contradiction이 다수입니다. 특히 v4 #4가 retract한 `_index.json` config/ 이동/packaging이 §3.2/§6/§7/§8.4/§10/§11에 그대로 남아 구현자가 따를 수 없는 상태입니다. Critical 2건 + High 6건 + Medium 7건을 해결한 v5가 필요합니다.

### Aggregated Findings (16 total)

#### 1. [ACCEPT] [Critical] `_index.json` 위치/packaging 다중 자기모순
- **Critic** (#1): §0.1 (그대로 유지) vs §2.1 #3/§3.2/§6.0/§6.6/§7 PR #6,#7,#8/§8.4/§10.2/§11.1/§11.6 (config/로 이동) 8 절이 정반대 지시
- **Cross** (#1): repo 실측 — `runtime/warnings/_index.json:1`만 존재. v4 헤더가 in-place 갱신 retract 명시했음에도 §2.1 등에 "이동" 잔존
- **Judgment**: 양 리뷰어 동일 ACCEPT. Critic이 8개 잔존 위치를 line-precise 열거. v4 #4 헤더 결정과 본문 정반대.
- **Action Required**: §0.1 제외 7개 절 일괄 정정 — §2.1 #3 "이동" → "in-place schema v2 갱신"; §3.2의 config 신규/runtime 삭제/.gitignore/af.spec datas 4 row 삭제 → schema v2 in-place row 1개; §6.0 절 폐기; §6.6 packaging 절 폐기; §7 #6 → in-place 갱신, #7/#8 삭제; §8.4 _internal/config 검증 삭제; §10.2/§11.1/§11.6 fact 정정.

#### 2. [ACCEPT] [Critical] §6.6 `_load_index` 코드 v4 #4 retract와 정면충돌
- **Critic** (#2): §6.6 코드 블록이 `from core.config_paths import BASE_DIR` + `_MEIPASS` + `config/` 검색 — retract된 두 회귀 동시 발생
- **Cross** (#2): `core/config_paths.py:91` 실측 — import 시점 `os.makedirs(...)` side-effect 발생, §3.5 read-only 단언과 모순
- **Judgment**: 양 리뷰어 동일 ACCEPT. Cross가 line-level evidence 제시.
- **Action Required**: §6.6을 8줄 이내 단순화 — `_load_index(workspace)`가 `<workspace>/runtime/warnings/_index.json`을 직접 read만 수행. `core.config_paths` import 금지. 부재/JSONDecodeError → None, validation skip 허용.

#### 3. [ACCEPT] [High] CSV `affected_ids` `\;` escape 잔존
- **Critic** (#3): §5.2 (`\;` escape) + §8.2 case 9 (escape 검증) — Python `csv` 모듈 backslash escape 미지원
- **Cross** (#4): v4 #2 ACCEPT 결정(`json.dumps`)과 본문 직접 충돌. 테스트 contract도 어긋남
- **Judgment**: 양 리뷰어 동일 ACCEPT, 출력 포맷 직접 충돌.
- **Action Required**: §5.2 affected_ids → `json.dumps(list, ensure_ascii=False)` 문자열 컬럼. §8.2 case 9 → `json.loads(row["affected_ids"]) == [...]` round-trip assert.

#### 4. [ACCEPT] [High] `warning-export --phase` §5.1 시그니처 미반영
- **Critic** (#4): §5.1 시그니처/인자표에 `--phase` 없음, §5.4는 forward 단언. argparse 도달 불가
- **Cross** (#3): §4 `warning-stats --phase`는 정의됐지만 §5는 누락 → 구현 분기 발생
- **Judgment**: 양 리뷰어 동일 ACCEPT.
- **Action Required**: §5.1 시그니처에 `[--phase PHASE]` + 인자표 1 row. records/summary 양 모드 적용 명시. §8.2에 records/summary `--phase` 케이스 각 1개 추가.

#### 5. [ACCEPT] [High] `--slug` path traversal 방어 §4.5/§5.1 미반영
- **Critic** (#6): `--slug ../../../etc` 형태에서 workspace 외부 jsonl 노출. v4 #7 ACCEPT지만 본문 잔존
- **Cross** (#7): §3.3/§4.5/§5.1 normative 검증 부재
- **Judgment**: 양 리뷰어 동일 ACCEPT.
- **Action Required**: §4.5/§5.1에 1줄 추가 — 빈 문자열, `/`, `\`, `..`, `os.path.basename(slug) != slug` 거부. `iter_warning_records` 동일 가드. §8.2 case 12에 traversal 거부 케이스 추가.

#### 6. [ACCEPT] [High] `--top` truncation §3.3/§3.4/§4.3 미반영
- **Source**: Critic only (#5)
- **Critic**: §3.3 dict에 `project_count_total`/`project_count_returned` 부재, distribution full-population 명세 없음
- **Judgment**: Cross 미언급이지만 evidence 강함 — 누락 시 P4 임계 모집단 일관성 깨짐.
- **Action Required**: §3.3 dict에 두 메타 필드 추가. §3.4에 "distribution.* / totals / by_phase_total은 항상 full matching population, `--top`은 `projects[]`만 truncate" 1줄. §4.3 예시 갱신. §8.2 case 8에 `distribution.by_project_count.n == project_count_total` assert.

#### 7. [ACCEPT] [High] `--out` atomic write §5 미반영
- **Source**: Critic only (#7)
- **Critic**: §5에 atomic write 절차 부재 → KeyboardInterrupt/디스크 full 시 partial write
- **Judgment**: Cross 미언급이지만 v4 #10 ACCEPT 명시 + 회의 자료 corruption risk.
- **Action Required**: §5에 atomic write 절 추가 — 같은 디렉토리 `tempfile.NamedTemporaryFile(delete=False)` + `os.replace()`. 예외 시 `os.unlink(temp_path)` cleanup. stdout 모드 제외.

#### 8. [ACCEPT] [High] `first_ts`/`last_ts` 시맨틱 §3.3 미반영
- **Source**: Critic only (#8)
- **Critic**: §3.3 ProjectStats가 ts 누락/0-record slug 처리 미명세 → `min(record["ts"] for ...)` 직역 시 KeyError
- **Judgment**: v4 #6 ACCEPT 본문 누락, evidence 강함.
- **Action Required**: §3.3에 ts 규약 4 bullet 추가 (있는 record만 sort, 누락은 count에 포함하되 first/last 제외, 전부 누락 → `""`, 0-record slug → `projects[]` 제외). §8.1 케이스 2개 추가.

#### 9. [ACCEPT] [High] malformed-line warnings 채널 분기 (§3.5 vs v4 #3)
- **Source**: Cross only (#5)
- **Cross**: v4 #3 "warnings list 항상 반환" vs §3.5 "JSONDecodeError → stderr only" vs §8.1 case 6 "warnings 비어도 OK" 3중 충돌
- **Judgment**: Critic 미언급이나 contract 직접 충돌. 사용자가 stdout JSON으로 malformed 감지 불가능해질 위험.
- **Action Required**: §3.5와 §8.1 case 6 정정 — malformed-line 진단을 반환 `warnings` array에 포함, stderr는 옵션 mirror로 명시.

#### 10. [ACCEPT] [High] `source_path` 정정이 dedup에 영향 있음 (§6.4 false 단언)
- **Source**: Cross only (#6)
- **Cross**: `core/warning_registry.py:107`에서 `source_path`가 `stable_payload`에 포함, `:122`에서 `record_id` 생성 → `:1401` → `:1455` 변경 시 동일 mismatch가 새 record_id로 dedup
- **Judgment**: Critic 미언급. Code-line evidence 명확.
- **Action Required**: §6.4 "dedup 영향 X" 문구 폐기. P3는 (a) 일회성 정정으로 same logical mismatch가 duplicate되는 risk를 명시 + 통계 해석 시 보정, 또는 (b) 별도 마이그레이션으로 `source_path`를 dedup payload에서 제외 — 사용자 결정 필요.

#### 11. [ACCEPT] [Medium] median float cast §3.4/§4.3 미반영
- **Source**: Critic only (#9)
- **Critic**: §4.3 예시 `"median": 2`/`"median": 1` 정수 누출. v4 #8 `float()` cast ACCEPT
- **Judgment**: Evidence 강함, JSON type 분기 깨짐 risk.
- **Action Required**: §3.4 "median 출력은 항상 `float()` 캐스팅" 1줄. §4.3/§4.3.1 예시 `2.0`/`1.0`/`3.5`로 갱신. §8.1 case 1/2에 `isinstance(median, float)` assert.

#### 12. [ACCEPT] [Medium] §6.4 정정 채널 1번 — finding #1과 동시 충돌
- **Source**: Critic only (#10)
- **Critic**: §6.4 "1. `config/warning_registry_index.json` ... :1455" — finding #1 정정 시 PR scope에서 누락된 파일을 정정 대상으로 가리킴
- **Judgment**: Finding #1 일괄 수정의 부속.
- **Action Required**: §6.4 1번 채널 → "`runtime/warnings/_index.json`의 `rules[].source` 필드".

#### 13. [ACCEPT] [Medium] changelog wording §6.5.1
- **Source**: Critic only (#11)
- **Critic**: "P4로 미룬다" → P4 설계자 자동 합의 위험. v4 #11 ACCEPT
- **Judgment**: 단순 wording이나 향후 의사결정 channel에 영향.
- **Action Required**: §6.5.1 "P4로 미룬다" → "P3 scope 제외, P4 설계에서 재평가".

#### 14. [ACCEPT] [Medium] §8.3 `:1401` fixture wording
- **Source**: Critic only (#12)
- **Critic**: "있다면 갱신" wording 불확실성 → grep 안 하고 fixture 만들 risk. v4 #12 ACCEPT
- **Action Required**: §8.3 row → "실측 결과 `:1401` assertion 부재 확인 (2026-05-10). fixture 갱신 불필요. 회귀 PASS만 확인".

#### 15. [ACCEPT] [Medium] §3.3 `iter_warning_records` `--phase` 채널 미정
- **Source**: Critic only (#13)
- **Critic**: 시그니처에 `phase` 인자 없음 → `--phase` argparse 통과해도 effect 0
- **Judgment**: Finding #4의 부속. 구현 채널 명시 필요.
- **Action Required**: §3.3 시그니처에 `phase: str | None = None` 추가 + 시맨틱 1줄 (collect_workspace_stats와 정합).

#### 16. [REJECT] [Low] `af.spec datas` 신규 entry 불필요
- **Source**: Cross only (#8)
- **Original Finding**: §6.6 `('config/warning_registry_index.json', 'config')` 추가 우려
- **Rejection Reason**: `af.spec:27`이 이미 `('config', 'config')` bundle. 어차피 finding #1 해결 시 config/ 이동 자체가 retract되어 무관해짐.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | `_index.json` 위치/packaging 자기모순 | Critical | ACCEPT | Both |
| 2 | §6.6 `_load_index` retract 미반영 | Critical | ACCEPT | Both |
| 3 | CSV `affected_ids` `\;` escape | High | ACCEPT | Both |
| 4 | warning-export `--phase` 시그니처 | High | ACCEPT | Both |
| 5 | `--slug` path traversal | High | ACCEPT | Both |
| 6 | `--top` truncation 메타 필드 | High | ACCEPT | Critic |
| 7 | `--out` atomic write | High | ACCEPT | Critic |
| 8 | first_ts/last_ts 시맨틱 | High | ACCEPT | Critic |
| 9 | warnings 채널 분기 | High | ACCEPT | Cross |
| 10 | source_path dedup 영향 | High | ACCEPT | Cross |
| 11 | median float cast | Medium | ACCEPT | Critic |
| 12 | §6.4 정정 채널 1번 | Medium | ACCEPT | Critic |
| 13 | changelog wording | Medium | ACCEPT | Critic |
| 14 | §8.3 fixture wording | Medium | ACCEPT | Critic |
| 15 | iter_warning_records phase 인자 | Medium | ACCEPT | Critic |
| 16 | af.spec datas 신규 entry | Low | REJECT | Cross |

### Recommendations

1. **v5 작성 시 finding #1 일괄 수정을 최우선으로** — 8개 절을 한 번에 정리해야 #2/#10/#15가 자동 해소됨. 단순 헤더 ACCEPT로는 부족.
2. **finding #10 (source_path dedup)은 사용자 결정 필요** — duplicate risk 명시(저비용) vs dedup payload 변경 마이그레이션(고비용) 중 선택.
3. **v4 헤더 ACCEPT 12건이 본문에 모두 반영됐는지 verify checklist를 §0 직후에 추가** — 헤더-본문 drift 재발 방지. 각 v4 #N에 대해 본문 line:section 포인터 명시.
4. **finding #4/#15 동시 해결** — argparse 시그니처와 iterator 시그니처가 한 PR에서 일치해야 함.
5. **재교차검증 필수** — v5는 self-contradiction이 모두 해소된 후 cross-review 재실행 권장.