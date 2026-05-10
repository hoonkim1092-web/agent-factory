# Design Review: 2026-05-10-p3-owner-lint-measurement-design

> Source: docs/2026-05-10-p3-owner-lint-measurement-design.md
> Date: 2026-05-10 09:20
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

이유: Cross #1(`source_path` 변경이 dedup에 영향)은 설계의 핵심 zero-change 약속과 코드 사실(`record_id` payload에 `source_path` 포함, `core/warning_registry.py:98,116,123`)이 직접 충돌하는 Critical 수준 사실모순이다. v2 #1 흡수 시 §3.2 row 추가/§6.4 정정에 그치고 **dedup discontinuity 자체는 설계 본문이 여전히 명시하지 않았다**. 이를 명시 추가(또는 `:1466` literal 변경 보류)하기 전에는 구현 진입 시 P4 모집단이 잠재적으로 dedup boundary를 가로지른다.

추가로 iterator 계약(Critic #1 + Cross #2 + Cross #3)이 세 검토에서 모두 다른 각도로 동일 영역을 지목 — 설계상 단일 SoT iterator의 책임 경계가 underspecified. 합쳐서 BLOCK 1건 + High/Medium 다수.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] `source_path` 변경이 dedup record_id에 영향 — 설계 본문은 여전히 "영향 없음"으로 읽힘
- **Critic**: 직접 다루지 않음
- **Cross**: `record_id`는 `stable_payload`에 `source_path`를 포함(core/warning_registry.py:98,116,123). `:1401` → `:1455` 변경 시 동일 owner mismatch라도 dedup key가 달라짐
- **Judgment**: Cross의 line-level 증거가 명확하다. v2 #1에서 §3.2 row만 추가하고 §6.4를 "정정"했으나, **§0.1·§2.1 zero-change 약속과의 정합성은 본문에서 해소되지 않음**. P4 임계값 결정 시 모집단이 변경 시점 전후로 dedup boundary를 가로지르면 임계 산정이 오염된다.
- **Action Required**: §6.4 또는 §1.3에 "P3에서 `:1466` literal 변경은 dedup-affecting one-time discontinuity. 변경 시점 이후 record_id는 새 source_path 기반으로 계산되어 변경 전 동일 mismatch와 dedup되지 않는다"를 1단락 명시. 또는 `:1466` literal 변경을 P3에서 빼고 `_index.json.source` 메타데이터만 정정(이 경우 §0.1 row 7 동시 수정).

#### 2. [ACCEPT] [High] `iter_warning_records()` 계약 — 정렬·스캔 메타데이터·phase 인자 모두 underspecified
- **Critic** #1: `os.scandir`는 정렬 미보장인데 export는 `slug ASC` 약속 → sort 책임 위치 미명세
- **Cross** #2: 시그니처가 `(slug, dict)`만 yield → malformed warnings, `scanned_slug_count`, index warnings 전달 채널 부재 → 구현 시 hidden side effects 또는 중복 스캔
- **Cross** #3: §3.3은 `phase` 인자 없는데 §5.1 export는 `phase` 호출 → 두 가지 구현(인자 추가 vs post-filter) 모두 가능, warning/count 행동 갈림
- **Judgment**: 동일 단일 iterator의 세 가지 별개 underspec 영역 — 모두 강한 코드/설계 증거 있음. 단일 SoT 약속이 구현 시 산산조각 날 위험.
- **Action Required**: §3.3 시그니처 재정의 — (a) `phase: str | None = None` 인자 추가, (b) docstring에 "yield 순서: slug ASCII ASC, slug 내 jsonl 라인 순서" 명시, (c) `WarningScan(records, warnings, scanned_slug_count)` 결과 객체 또는 `warnings: list[str]` out-param 추가 + `discover_warning_slug_dirs()` helper 분리 중 택1.

#### 3. [ACCEPT] [High] `--slug` × `--phase` 병행 시맨틱 미정의 + 테스트 0건
- **Critic** #2: 가장 흔한 운영 시나리오("특정 프로젝트의 특정 phase 조사") 무명세. `by_phase_total_unfiltered`의 baseline이 slug-restricted인지 full-workspace인지 모호
- **Cross**: 직접 다루지 않음
- **Judgment**: 단일 출처 finding이지만 §8.1 case 5(phase only)/case 7(slug only)만 있고 결합 케이스 부재가 사실. 단순한 wording 추가가 아니라 시맨틱 결정(unfiltered baseline 정의) 필요.
- **Action Required**: §4에 결합 시맨틱 단락 신설(권장: `by_phase_total_unfiltered`는 항상 full-workspace baseline. slug filter는 `projects[]`/`distribution`만 좁힘). §8.1에 `slug_and_phase_combined` case 추가.

#### 4. [ACCEPT] [High] `--top` truncation이 `collect_workspace_stats()` 시그니처에 wiring 안 됨
- **Critic**: 직접 다루지 않음
- **Cross** #4: 시그니처에 `top` 인자 없는데 반환 schema는 `project_count_total/returned`/truncated `projects[]`. summary export가 "그대로" 반환 → CLI 경로마다 truncation 분기되어 drift 위험
- **Judgment**: Cross의 단일 finding이지만 code/contract mismatch가 명확. v4 #9에서 truncation 범위는 정했으나 어디서 truncation을 수행할지가 빠짐.
- **Action Required**: §3.3 `collect_workspace_stats(workspace, *, rule_id, slug, phase, top: int = 10)` 추가, `top=0`이면 무절단. summary export(§5)는 `top` 패스스루 또는 무절단으로 명시.

#### 5. [ACCEPT] [High] CSV `--format csv` 모드의 `warnings: []` 필드 위치 미정의
- **Critic** #7: CSV 인코딩(BOM/cp949)과 별개로 CSV 자체가 `warnings:` JSON 필드를 못 담는다는 점은 Cross #5와 일치
- **Cross** #5: CSV stdout/`--out`은 valid CSV여야 하는데 `warnings:`를 어디 넣을지 contract 부재
- **Judgment**: 두 검토가 다른 각도로 같은 영역을 지목. v4 #3 "warnings 채널 단일화"가 JSON 모드만 cover, CSV 모드 예외 미정의.
- **Action Required**: §5.2/§5.3에 명시 — "CSV 모드에서는 진단을 stderr로만 보내고 CSV 본문에는 `warnings:` 임베드 금지. JSON records/summary 모드만 `warnings: []` 필드 포함". §8.2에 malformed jsonl + CSV export 시 CSV가 parseable 유지되는지 검증 case 추가.

#### 6. [ACCEPT] [Medium] `_load_index()`가 missing/malformed/unreadable 구분 못함
- **Critic** #4: `_index.json`이 frozen 빌드 사용자에게 안 보여 `_load_index()`가 항상 None 반환 → `--rule` validation 영구 skip
- **Cross** #6: None만 반환하면 reason 손실, 출력 contract는 missing/malformed/unknown rule 별도 진단 요구
- **Judgment**: 두 finding이 합쳐져 하나의 영역(`_load_index` contract). Critic은 가시성·packaging 측면, Cross는 반환 signal 측면. 모두 ACCEPT.
- **Action Required**: §6 `_load_index()` 시그니처를 `(index: dict | None, reason: str | None)` 또는 typed status로 변경. §0.1 "measurement phase 가시성" row를 "AF repo 컨트리뷰터에게만 가시 (frozen 빌드 사용자는 marker 부재 → validation skip이 정상 경로)"로 정정 — 또는 frozen 빌드용 packaging(`af.spec datas`) 재검토(v4 #4 retract와의 trade-off 명시).

#### 7. [ACCEPT] [Medium] `schema_version` 필드명이 3개 무관 schema에 동시 사용
- **Critic** #3: stats output / export records wrapper / `_index.json` 셋이 같은 키 — P4 reader 분기 시 충돌
- **Cross**: 직접 다루지 않음
- **Judgment**: 단일 출처지만 미래 reader 도입 시 명확한 confusion 위험. naming 분리 비용은 수정 1회.
- **Action Required**: 필드명 분리 — `output_schema_version`(CLI 산출물), `index_schema_version`(`_index.json`). v3 #10 합의(P3는 reader 없음)에 맞춰 P3에서는 `_index.json`만 bump하고 stats/export wrapper의 schema 필드는 도입 보류 또는 다른 이름으로.

#### 8. [ACCEPT] [Medium] CSV 인코딩 — `--out` 파일과 stdout 인코딩 분기 미정의
- **Critic** #7: BOM 없는 UTF-8 CSV는 Windows Excel에서 한글 project_slug mojibake. 회의 산출물 1차 소비자가 Excel이면 의미 손실
- **Cross**: 직접 다루지 않음
- **Judgment**: 단일 출처지만 P3 산출물의 1차 사용 시나리오(§5.5)와 직결.
- **Action Required**: `--out` 파일은 `utf-8-sig`(BOM), stdout은 `utf-8`(BOM 없음) 분기. 또는 `--encoding {utf-8,utf-8-sig}` 옵션. §5.2 인코딩 단락 갱신.

#### 9. [ACCEPT] [Medium] `_PHASE_ORDER` 진실원천 미명시
- **Critic** #5: `core/warning_registry.py:21`(set, private) vs `core/project_task_board.py:17`(dict) — 이름 같지만 다른 symbol. `core/warning_stats.py`가 어느 쪽을 import할지 미정의
- **Cross**: 직접 다루지 않음
- **Judgment**: private symbol cross-module import 결정은 향후 drift 원인. 단순한 명시 1줄로 해결 가능.
- **Action Required**: §4.5에 "`core/warning_stats.py`는 `core.warning_registry._PHASE_ORDER`를 직접 import하지 않고 자체 frozenset으로 복제. registry SoT와의 동기화 검증을 §8.1에 단위 테스트로 추가" 또는 그 반대를 명시.

#### 10. [ACCEPT] [Medium] §3.2 LOC/케이스 수 산정과 §8 본문 불일치
- **Critic** #6: §3.2 (6+6=12 case, ~290 LOC) vs §8 (7+9=16 case, §11.4 ~370≈540) — 도큐먼트 내부 sync 깨짐. 큰 결정 영향은 없지만 Karpathy rule #2 self-check 수치가 stale
- **Cross**: 직접 다루지 않음
- **Judgment**: 단일 출처, 영향은 자기검증 수치 정확성. 수정 비용 낮음.
- **Action Required**: §3.2 row 2개와 §11.4 합계를 §8 실제 케이스 수에 맞춰 갱신.

#### 11. [ACCEPT] [Low] §10.1 rollback 진단의 `WarningRegistry.repair` 인용
- **Critic** #9: §3.5는 read-only 보장을 자랑하지만 §10.1은 `repair` 호출 권고 — `repair`는 `summarize()`를 거쳐 `_decision.json`까지 fail-closed 실행. P3 "0 변경" 약속과 약한 충돌
- **Cross**: 직접 다루지 않음
- **Judgment**: 진단 절차 권고일 뿐 설계 자체의 read-only 약속을 깨진 않음. 그래도 wording은 정정 가치 있음.
- **Action Required**: §10.1 진단 1순위를 `iter_warning_records`로 raw jsonl dump로 전환. `repair`는 사용자가 의식적으로 호출하는 별도 단계로 분리.

#### 12. [REJECT] [Low] `core.warning_stats` af.spec hiddenimports 추가가 충돌
- **Source**: Cross #7 (자기 reject)
- **Original Finding**: lazy import 패턴 때문에 PyInstaller가 새 모듈 누락 가능성
- **Rejection Reason**: af.spec:25에 이미 `core.warning_registry`, `core.warning_overrides` 등 동일 패턴으로 등록되어 있어 관례 따른 정상 처방. Cross 본인이 reject.

### 추가 REJECT — Critic-only

#### Critic #8 (max_rounds=2 캡 우회 시인) — [REJECT]
- **Rejection Reason**: 사용자가 §12에서 명시적으로 "추가 cross-review 없이 구현 진입" 결정. memory(`feedback_cross_review_stale_baseline_repeat.md`)와 일관. 프로세스 안전망 무력화는 BLOCK semantic 위반 0건 + wording-only 정정이라는 사용자 판단 근거가 §11.7에 매핑되어 있어 추가 라운드 한계 효용 부정 — 별도 1줄 추가 명시는 nice-to-have.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `source_path` dedup discontinuity 미명시 | Critical | ACCEPT | Cross |
| 2 | iterator 정렬·메타데이터·phase 인자 underspec | High | ACCEPT | Critic+Cross |
| 3 | `--slug` × `--phase` 결합 시맨틱·테스트 부재 | High | ACCEPT | Critic |
| 4 | `--top` truncation wiring 부재 | High | ACCEPT | Cross |
| 5 | CSV 모드 `warnings:` 필드 위치 미정의 | High | ACCEPT | Critic+Cross |
| 6 | `_load_index()` 가시성·반환 signal | Medium | ACCEPT | Critic+Cross |
| 7 | `schema_version` 3중 사용 | Medium | ACCEPT | Critic |
| 8 | CSV 인코딩 분기 (BOM/Excel) | Medium | ACCEPT | Critic |
| 9 | `_PHASE_ORDER` 진실원천 | Medium | ACCEPT | Critic |
| 10 | §3.2 LOC/케이스 수 stale | Medium | ACCEPT | Critic |
| 11 | §10.1 `repair` side-effect | Low | ACCEPT | Critic |
| 12 | af.spec hiddenimports | Low | REJECT | Cross |
| — | max_rounds=2 process | Low | REJECT | Critic |

### Recommendations

구현 진입 전 다음 순서로 v5 단일 패치를 권장:

1. **(BLOCK 해소)** §6.4 또는 §1.3에 dedup discontinuity 1단락 명시. 또는 `core/project_pipeline.py:1466` literal 변경을 P3 scope에서 제외하고 §0.1 row 7·§2.1·§6.4 동시 갱신.
2. **(High 4건 일괄)** §3.3 iterator 시그니처/docstring 재정의 — `phase` 인자, sort 보장, `WarningScan`/out-param 채택; §3.3에 `top` 인자 추가; §4에 slug×phase 결합 시맨틱 단락 신설; §5에 CSV 모드 `warnings:` 처리 명시(stderr only).
3. **(Medium 5건)** §6 `_load_index()` 반환 시그니처 + §0.1 가시성 row 정정; `schema_version` 필드명 분리; CSV 인코딩 분기; §4.5 `_PHASE_ORDER` SoT 명시; §3.2 수치 갱신.
4. **(Low 1건)** §10.1 진단 1순위 변경.
5. §8.1/§8.2에 추가 테스트 case 등록 — `slug_and_phase_combined`, `csv_export_malformed_jsonl`, `_PHASE_ORDER_sync`.

위 항목 중 #1만 BLOCK 해소에 해당. 나머지는 v5 라운드에서 함께 흡수하되 `max_rounds=2` 캡 + 사용자 v4 결정에 따라 추가 cross-review 없이 v5 머지 후 구현 진입 가능.