# Design Review: 2026-05-10-p3-owner-lint-measurement-design

> Source: docs/2026-05-10-p3-owner-lint-measurement-design.md
> Date: 2026-05-10 08:04
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

여러 High 결함이 있으나 모두 구현 직전 보정 가능한 명세 결함이며, Critical(데이터 손실/회귀)은 없음. 구현 진입 전 아래 ACCEPT 항목들을 v2로 반영해야 함.

---

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [High] `source_path` zero-change 자기모순
- **Critic**: §3.2 "변경 없음"과 §6.4 "1401→1454 정정"이 충돌. `core/project_pipeline.py:1466` 실코드는 `source_path="...:1401"`을 record에 영구 박음.
- **Cross**: 동일 — `_index.json`만 정정하면 새로 누적될 record는 stale source 유지.
- **Judgment**: 두 리뷰가 코드 라인까지 일치. baseline grep으로 검증됨.
- **Action Required**: §3.2 변경 파일에 `core/project_pipeline.py:1466 source_path` 1줄 추가 + §7 PR 순서에 끼워넣기. 또는 §6.4 항목을 "메타데이터만 정정, 기존 record는 stale 유지"로 명시.

#### 2. [ACCEPT] [High] `--phase` 필터 시맨틱 v1 미결
- **Critic**: §8.1 case 5가 `by_phase_total`이 필터된 phase 합산인지 전체인지 cross-review에 결정 위임 — P4 임계 결정 입력의 의미가 갈림.
- **Cross**: 동일 — `count`/`record_lines`/`repeat_count_max`/`first_ts`/`last_ts`/`distribution` 모두 record-level filter인지 project-level include인지 불명확.
- **Judgment**: 두 리뷰 모두 implementable하지 않다고 판단. 구현자가 임의로 고르면 사용자가 출력 의미 오독.
- **Action Required**: `--phase`를 record-level filter로 정의. 모든 집계는 매칭 record만. 출력에 `applied_filters: {phase: "build"}` 명시. 권장: `by_phase_total_unfiltered`도 같이 (모집단 비율 가시화).

#### 3. [ACCEPT] [High] `_index.json` 패키징/조회 경로 미정의
- **Critic**: not flagged
- **Cross**: `af.spec`은 `_index.json`을 패키징하지 않음(`af.spec:21`). frozen 빌드/임의 `--workspace` 환경에서 unknown-rule 검증 경로 불명.
- **Judgment**: ACCEPT. frozen 빌드에서 사용자 워크스페이스에 repo의 `_index.json`이 없으면 `--rule` 검증이 어디서 로드하는지 정의 안 됨. CLAUDE.md 멀티 PC 환경 요구와 충돌.
- **Action Required**: canonical index 위치 1개 결정 — (A) `af.spec`에 packaging, (B) `config/`로 이동, (C) best-effort fallback 명시. §8.4 frozen smoke에 unknown-rule case 추가.

#### 4. [ACCEPT] [High] `Distribution.by_count`가 P4 임계 결정 차원과 어긋남
- **Critic**: `count`(per-record) vs `summary.count`(누적) 의미 차이. 현 distribution은 누적 분포만 — P4 `repeat_count_min: 3`은 record 수 임계라 직접 매핑 불가.
- **Cross**: not flagged
- **Judgment**: ACCEPT. critic이 §3.3 + §4.3 + escalation_policy.yaml까지 cross-reference로 검증한 강한 evidence. P3의 명시적 목적(P4 임계 회의 입력)에 직결되는 결함.
- **Action Required**: §3.3에 `distribution.by_per_record_count` 차원 추가 (모든 record의 `count` 필드 분포). 계산 비용 0.

#### 5. [ACCEPT] [Medium] stdout JSON 무결성 vs warning 라인 충돌
- **Critic**: §4.4의 stderr warning 1줄은 산출물에 흔적 없어 false-confidence 위험.
- **Cross**: stdout warning 라인이 JSON 파싱을 깨뜨림 — 기존 `warning-summary`는 stdout JSON-only.
- **Judgment**: 두 리뷰가 같은 결함을 다른 각도에서 지적. JSON 무결성과 traceability 모두 충족하는 해법은 동일.
- **Action Required**: stdout은 항상 단일 valid JSON. human warning은 JSON `"warnings": [...]` 필드. unknown rule_id, n=0 distribution, scanned_slug_count > threshold 모두 이 필드로. stderr는 옵션 미러.

#### 6. [ACCEPT] [Medium] export 모드 malformed-record 계약 미정의
- **Critic**: §8.2 export 테스트 case 9뿐 — JSON records 모드의 wrapper 형식 + scanned_slug_count threshold 미검증.
- **Cross**: `_iter_records` 안전 정책이 stats helper에만 명시. export가 같은 iterator 쓰는지 불명 — malformed jsonl이 export crash 유발 가능.
- **Judgment**: 부분 중첩이지만 cross가 더 본질적 (계약 정의 자체). critic은 테스트 갭.
- **Action Required**: `iter_warning_records(workspace, rule_id)` 단일 iterator 계약 정의 → stats/export 공유. §8.2에 (10) `cli_export_json_records_format`, (11) `cli_export_summary_csv_rejected`, (12) `cli_export_malformed_jsonl_skip` 추가.

#### 7. [ACCEPT] [Medium] `ProjectStats.count` docstring 자기모순
- **Critic**: §3.3 댓글 "record 수 (누적 sum of count)"이 모순. 실제는 `count` 필드 합산.
- **Cross**: not flagged
- **Judgment**: ACCEPT. critic이 `core/warning_registry.py:347-358` 실측까지 검증. 구현자가 `len(records)`로 잘못 구현할 위험.
- **Action Required**: 댓글을 `count: int   # sum of WarningRecord.count across records (per-run count 누적)`로 정정.

#### 8. [ACCEPT] [Medium] `_iter_records` slug 디렉토리 필터 누락
- **Critic**: `runtime/warnings/_index.json`이 slug 디렉토리와 같은 레벨에 존재. §3.5에 dir vs file 필터 명시 없음 → NotADirectoryError 또는 silent skip.
- **Cross**: not flagged
- **Judgment**: ACCEPT. baseline 파일 구조 실측 기반.
- **Action Required**: §3.5에 `os.scandir` + `entry.is_dir() and not entry.name.startswith("_")` 명시. 테스트 case 추가.

#### 9. [ACCEPT] [Low] schema_version v1→v2 revert 안전성 단서 누락
- **Critic**: §10.2 "1 commit revert"는 P3 단독 시점에만 사실. P4가 `measure_at`/`mode` 읽기 시작하면 거짓.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 명시적 단서 추가만으로 해결.
- **Action Required**: §10.2 첫 줄에 "P3 단독 시점에 한해" 단서. P4 진입 시 revert 정책은 P4 설계에 위임.

#### 10. [ACCEPT] [Low] frozen build smoke OS 분기 미명시
- **Critic**: §8.4가 `dist/af.exe`만 명시. macOS/Linux의 `dist/af` 미명시.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 멀티-OS 빌드 명시는 1줄 비용.
- **Action Required**: §8.4를 "host OS frozen build 1개 (`dist/af` 또는 `dist/af.exe`)"로 정정.

#### 11. [HOLD] [Low] `--slug SLUG` 옵션 추가 여부
- **Critic**: 기존 `warning-summary`는 single-slug 지원. fan-out만 지원하면 디버깅 시 불편.
- **Cross**: not flagged
- **Judgment**: HOLD. P3의 1차 목적은 fan-out 분포 산출. 디버깅 편의 추가는 사용자 선호 의존.
- **Question for Author**: P3 v1에 `--slug` filter를 포함시킬지, P3 후속 minor에 미룰지? (구현 비용 ~1줄)

#### 12. [HOLD] [Low] `install-af.ps1` 버전 수정 범위
- **Critic**: not flagged
- **Cross**: 1.2.25 occurrences가 3개 이상(`:3, :6, :27, :34, :105, :106, :110, :251`). 브랜치/태그 URL까지 옮길지 정책 불명.
- **Judgment**: HOLD. 릴리즈 정책 결정 사안.
- **Question for Author**: P3 release tag가 `af-fsa_v1.2.26`이라면, 브랜치/zip path/완료 텍스트 모두 일괄 갱신인지 일부만인지?

#### 13. [REJECT] [N/A] `WarningRegistry.summarize()` 회피 우려
- **Source**: Cross
- **Original Finding**: read-only 분석에서 summarize() 호출 회피.
- **Rejection Reason**: cross 본인이 정당하다고 결론. `summarize()`는 `_summary.json` 쓰기 + escalation decision report 부작용. read-only analytics가 fail-closed decision side effect를 트리거하면 안 됨. 설계가 옳음.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | source_path zero-change 자기모순 | High | ACCEPT | Both |
| 2 | --phase 필터 시맨틱 미결 | High | ACCEPT | Both |
| 3 | _index.json 패키징/조회 미정의 | High | ACCEPT | Cross |
| 4 | Distribution.by_count P4 차원 미스 | High | ACCEPT | Critic |
| 5 | stdout JSON 무결성 vs warning | Medium | ACCEPT | Both |
| 6 | export malformed-record 계약 | Medium | ACCEPT | Cross+Critic |
| 7 | ProjectStats.count docstring | Medium | ACCEPT | Critic |
| 8 | _iter_records slug 필터 누락 | Medium | ACCEPT | Critic |
| 9 | v1→v2 revert 안전성 단서 | Low | ACCEPT | Critic |
| 10 | frozen build OS 분기 | Low | ACCEPT | Critic |
| 11 | --slug 옵션 추가 | Low | HOLD | Critic |
| 12 | install-af.ps1 버전 수정 범위 | Low | HOLD | Cross |
| 13 | summarize() 회피 우려 | — | REJECT | Cross |

---

### Recommendations

구현 전 v2 설계에서 다음을 반영:

1. **High 4건 (#1~#4) 모두 본문에서 결정** — 구현자에게 위임 금지. 특히 `--phase` 시맨틱과 `by_per_record_count` 추가는 P3의 1차 목적(P4 임계 회의)에 직결.
2. **stdout 단일 JSON 계약** (#5) — `"warnings": []` 필드 추가, stderr는 옵션 미러.
3. **`iter_warning_records` 단일 iterator** (#6) — stats/export 공유. malformed jsonl + slug 디렉토리 필터(#8) 둘 다 여기서 흡수.
4. **§8 테스트 케이스 9 → 12로 확장** — JSON records format, summary CSV reject, malformed jsonl skip, n=2 edge.
5. **`af.spec` 또는 `config/`로 `_index.json` 위치 결정** (#3) — frozen smoke에 unknown-rule 케이스 추가.
6. **HOLD 2건 (#11, #12) 사용자에게 1회 질의** — 답변 후 v2 fix.
7. **Critic의 Missing 5항목 중 #1, #4는 위 ACCEPT에 흡수**, 나머지(n=2 edge, 모집단 임계, `affected_ids` `;` escape) 1줄씩 §11 자기검증에 명시.

저자 작업 후 v2로 다시 cross-review 1회 권장 (max_rounds=2 이내).