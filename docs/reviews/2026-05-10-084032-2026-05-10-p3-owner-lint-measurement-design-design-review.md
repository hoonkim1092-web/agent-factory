# Design Review: 2026-05-10-p3-owner-lint-measurement-design

> Source: docs/2026-05-10-p3-owner-lint-measurement-design.md
> Date: 2026-05-10 08:40
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

이제 양쪽 리뷰를 검증해 종합 판단을 작성하겠습니다.

## Final Design Review

### Verdict: BLOCK

**근거**: §7 PR 변경 파일 표가 §3.2 본문과 모순(`_HANDLERS` vs `_STAGE1_DISPATCH`), CSV escape 처방이 표준 위반, `_load_index` import 경로 부작용, `warning-export --phase` 시그니처 누락, malformed-line 진단 채널 자기모순 — 5개 High 이슈가 구현 진입을 막음.

---

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [High] §7 PR 표 row 3에서 `_HANDLERS` 미정정
- **Critic**: §3.2 line 145는 `_STAGE1_DISPATCH`로 고쳤으나 §7 line 555 row 3은 여전히 `_HANDLERS` 2 entry로 남음. 실측 baseline은 `run_factory_cli.py:429,474,581`의 `_STAGE1_DISPATCH`/`_STAGE1_USAGE`.
- **Cross**: not flagged
- **Judgment**: 직접 확인 — line 555가 `_HANDLERS` 그대로. 구현자가 §7만 보고 작업 시 존재하지 않는 dict를 찾아 막힘. v3 changelog 주장과 본문 불일치.
- **Action**: line 555를 `_STAGE1_DISPATCH` + `_STAGE1_USAGE` 2 entry로 교정. §7에 라인 번호(429 정의 / 474 USAGE / 581 dispatch.get) 명시.

#### 2. [ACCEPT] [High] CSV `affected_ids` 내부 `\;` escape가 표준 CSV 아님
- **Critic**: §5.2의 `\;` escape는 `csv.QUOTE_MINIMAL`이 처리하지 못함. pandas/Excel reader는 backslash escape 모름 → roundtrip 깨짐.
- **Cross**: not flagged
- **Judgment**: 정확. Python `csv` 모듈은 backslash escape 미지원. 회의 산출물 분석 도구(pandas)에서 split 불가.
- **Action**: `affected_ids` 컬럼을 `json.dumps(list)`로 직렬화 권장. pandas는 `df["affected_ids"].apply(json.loads)`로 즉시 복원 가능. §5.2 + §8.2 case 9 수정.

#### 3. [ACCEPT] [High] malformed-line 진단 채널 §4.4 ↔ §8.1 case 6 자기모순
- **Critic**: not flagged  
- **Cross**: §4.4는 "모든 휴먼 경고는 `warnings: []` 배열에"를 강제하지만 §8.1 case 6는 "stderr 1줄 + warnings 비어있어도 OK"로 정반대.
- **Judgment**: 직접 확인 — 두 절이 직접 충돌. 구현자가 어느 채널이 SoT인지 결정 불가.
- **Action**: 둘 중 택일을 §3.5/§4.4/§8.1 case 6에 일관 명시. (a) machine 진단은 stderr 전용 + warnings 제외, 또는 (b) 양쪽 미러.

#### 4. [ACCEPT] [High] `_load_index()`가 side-effect 모듈 `core.config_paths` import
- **Critic**: not flagged
- **Cross**: `core/config_paths.py:91`에서 import 시 `os.makedirs(...)` 다수 실행. read-only 보장 위배.
- **Judgment**: 실측 확인 — `core/config_paths.py:91-100+` 다수 디렉토리 생성. `warning-stats`의 read-only 계약과 충돌.
- **Action**: §6.6의 `_load_index` 헬퍼를 `sys._MEIPASS`/`Path(__file__).resolve().parents[1] / "config" / ...`만 쓰도록 재작성. `core.config_paths` import 제거.

#### 5. [ACCEPT] [High] `warning-export --phase` 시그니처 누락
- **Critic**: not flagged
- **Cross**: §5.4가 "summary 모드에서 `--phase` 통과"라 명시하지만 §5.1 인자표/시그니처 라인에 `--phase` 없음.
- **Judgment**: 실측 확인 — §5.1에 `--phase` 부재.
- **Action**: §5.1 시그니처 + 인자표에 `--phase PHASE` 추가 (summary 모드 한정 또는 records 모드도 포함 결정). §8.2 case에 `warning-export --mode summary --format json --phase build` 추가.

#### 6. [ACCEPT] [Medium] ProjectStats `first_ts`/`last_ts` 집계 시맨틱 미정의
- **Critic**: §3.3 dataclass에 필드만 있고 min/max/정렬 정의 부재. 0-record slug 처리 미정.
- **Cross**: not flagged
- **Judgment**: 정확. 구현자별 결과 차이 가능.
- **Action**: §3.3에 "`first_ts = min(record.ts ...)`, `last_ts = max(...)`. 0-record slug은 `projects[]` 제외" 1줄 추가.

#### 7. [ACCEPT] [Medium] `--slug` path traversal 미검증
- **Critic**: `--slug ../../etc`로 workspace 외부 진입 가능성. argparse 기본은 string 그대로 통과.
- **Cross**: not flagged
- **Judgment**: 합당한 보안 우려. design이 sanitization 정책을 말하지 않으면 구현자가 누락.
- **Action**: §4.5/§5.1에 "`os.path.basename(slug) != slug` 또는 `/`/`\`/`..` 포함 시 argparse error" 1줄.

#### 8. [ACCEPT] [Medium] median float 타입 일관성 미보장
- **Critic**: `statistics.median([1, 1])` → int `1`. §8.1 case 2(n=1)가 정확히 이 케이스 — 외부 reader strict type 시 실패.
- **Cross**: not flagged
- **Judgment**: 정확한 Python 동작. 직렬화 schema 일관성 위해 수정 필요.
- **Action**: §3.4에 "median 출력은 항상 `float(statistics.median(values))`" 1줄.

#### 9. [ACCEPT] [Medium] `--top` truncation에서 totals/distribution 범위 불명확
- **Critic**: not flagged
- **Cross**: `projects`만 자르면 totals/distribution과 일관성 깨짐. 자르면 P4 측정 데이터 편향.
- **Judgment**: 합리적. design이 "projects만"인지 "전체 truncate"인지 미명시.
- **Action**: §4.1/§4.5에 "totals/distribution은 full filtered population, projects만 truncate. `project_count_total`/`project_count_returned` 메타 추가" 명시. §8.2에 회귀 케이스 추가.

#### 10. [ACCEPT] [Medium] `--out` 동작 (stdout/atomic write/partial error) 미정의
- **Critic**: not flagged
- **Cross**: 성공 시 stdout 내용, 원자적 write 여부, 부분 실패 처리 미정.
- **Judgment**: 합리적 — 산출물 파일 안정성 직결.
- **Action**: §5.1/§5.4에 "`--out` 설정 시 stdout 빈, 임시파일 + `os.replace()`, 실패 시 stderr + nonzero exit" 명시. §8.2에 1 케이스.

#### 11. [ACCEPT] [Medium] schema_version 1→2 bump이 changelog #10 "P4로 미룸" 문구와 표면 모순
- **Critic**: 이력 #10은 "P4로 미룸"인데 본문은 P3에서 bump. §6.5.1이 의도를 풀지만 changelog 단독 독해 시 오해.
- **Cross**: not flagged
- **Judgment**: §6.5.1이 정당화하므로 design 결함은 아니나 changelog 문구가 misleading. 약한 finding이지만 구현자/리뷰어 혼란 회피 차원에서 교정.
- **Action**: 이력 #10 문구를 "schema_version은 P3에서 bump하되 reader는 P4로 미룸"으로 정정. (schema_version=1 유지 옵션도 KISS 관점에서 검토 가치 있음.)

#### 12. [ACCEPT] [Low] `tests/test_warning_registry_migration_callsites.py` 영향 conditional
- **Critic**: §8.3 line 602 "있다면 갱신"은 conditional. 실측: 해당 파일에 `:1401` assertion 0건(`source_path="core/project_pipeline.py:757"`만 1건). 작업 범위 모호.
- **Cross**: not flagged
- **Judgment**: design이 사실 확정 안 함 → PR scope 모호. 1줄 사실 박으면 해소.
- **Action**: §8.3에 "실측 결과 `:1401` assertion 0건 (2026-05-10 기준) — fixture 갱신 불필요" 명시.

#### REJECTED Findings

#### R1. [REJECT] [Low] stderr prefix `[warning-stats]`이 export에서도 사용 (Critic #8)
- 사용자 혼란 가능성은 있으나 cosmetic. 둘 다 같은 모듈 내 함수이므로 prefix 통일이 오히려 단순.

#### R2. [REJECT] [Info] schema_version 필드명 중복 (Critic #10)
- stats 출력과 index 양쪽에 동명 필드. 위치가 다르므로 실제 충돌 0. 단순 grep 노이즈로 design 결함 아님.

#### R3. [REJECT] source line `:1455` vs `:1454` 불일치 (Cross #5)
- 직접 grep 확인: 모든 canonical 정정 reference가 `:1455`. `:1454` 등장 위치는 전부 "import vs callsite" 구분용 의도. cross의 stale read.

#### R4. [REJECT] af.spec datas 중복 entry (Cross #7 자기 reject)
- `af.spec:29`에 이미 `('config', 'config')` 묶음 존재 → `('config/warning_registry_index.json', 'config')` 추가는 redundant. 하지만 packaging은 동작하므로 BLOCK 아님. design에서 1줄 제거 권장 (선택).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §7 row 3 `_HANDLERS` 미정정 | High | ACCEPT | Critic |
| 2 | CSV `\;` escape 비표준 | High | ACCEPT | Critic |
| 3 | malformed-line warnings 채널 자기모순 | High | ACCEPT | Cross |
| 4 | `_load_index` core.config_paths import | High | ACCEPT | Cross |
| 5 | `warning-export --phase` 시그니처 누락 | High | ACCEPT | Cross |
| 6 | `first_ts`/`last_ts` 집계 미정의 | Medium | ACCEPT | Critic |
| 7 | `--slug` path traversal | Medium | ACCEPT | Critic |
| 8 | median float 타입 일관성 | Medium | ACCEPT | Critic |
| 9 | `--top` totals/distribution 범위 | Medium | ACCEPT | Cross |
| 10 | `--out` 동작(atomic/stdout) 미정의 | Medium | ACCEPT | Cross |
| 11 | schema_version 이력 #10 wording | Medium | ACCEPT | Critic |
| 12 | migration_callsites test conditional | Low | ACCEPT | Critic |
| R1 | stderr prefix 분기 | Low | REJECT | Critic |
| R2 | schema_version 필드명 중복 | Info | REJECT | Critic |
| R3 | source `:1455` vs `:1454` | High | REJECT | Cross |
| R4 | af.spec datas 중복 entry | Low | REJECT | Cross (자기) |

---

### Recommendations (구현 진입 전 필수)

1. **§7 row 3** `_HANDLERS` → `_STAGE1_DISPATCH` + `_STAGE1_USAGE` 2 entry 교정, 라인 번호 명시 (#1).
2. **§5.2 CSV escape**를 `json.dumps(affected_ids)`로 전환 + §8.2 case 9 갱신 (#2).
3. **§4.4 + §8.1 case 6** malformed-line 진단 채널 일관 결정 + 양쪽 명시 (#3).
4. **§6.6 `_load_index`** `core.config_paths` import 제거, `sys._MEIPASS` + `Path(__file__).resolve().parents[1]` 사용 (#4).
5. **§5.1 `warning-export`** 인자표/시그니처에 `--phase PHASE` 추가 + §8.2에 회귀 케이스 (#5).
6. **§3.3** `ProjectStats.first_ts/last_ts = min/max(record.ts)`, 0-record slug drop 명시 (#6).
7. **§4.5/§5.1** `--slug` sanitization (`os.path.basename(slug) != slug` 거부) 추가 (#7).
8. **§3.4** `median = float(statistics.median(...))` 강제 1줄 (#8).
9. **§4.1** `--top`은 projects만 truncate, totals/distribution은 full + 메타 필드 명시 (#9).
10. **§5.1/§5.4** `--out` atomic write + stdout 동작 + nonzero exit 명시 (#10).
11. **이력 #10** "P4로 미룸" 문구를 "bump는 P3, reader는 P4"로 정정 (#11).
12. **§8.3** migration_callsites 실측 사실(`:1401` assertion 0건) 박기 (#12).

이 12개 수정 후 v4 재발화. v3가 max_rounds=2 캡 도달이라면 사용자 수동 결정 필요.