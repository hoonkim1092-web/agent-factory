# P3 — Owner Lint 측정 데이터 분석 가능화 설계

- 작성일: 2026-05-10
- 모델: Opus 4.7 (1M)
- 의존: `docs/2026-05-09-warning-registry-and-gate-escalation-design.md` (v6, P1) / `docs/2026-05-09-p2-e2e-command-block-activation-design.md` (v4.1, P2)
- 브랜치: `2026-05-07-memory-gitignore-cleanup` (또는 P3 전용 후속 브랜치)
- 상태: v4 — cross-review v4 (2026-05-10 08:40) BLOCK ACCEPT 12 모두 반영 (사용자 처방 2026-05-10)
- 이력:
  - v1 (2026-05-10 KST 오전) — 초안 (B/D/C scope 합의)
  - v4 (2026-05-10 KST 저녁) — cross-review v4 BLOCK 12건 사용자 처방대로 흡수:
    1. (v4 #1) §7 row 3 `_STAGE1_DISPATCH`/`_STAGE1_USAGE` 2 entry — v3에서 이미 정정됨, false-positive 확인
    2. (v4 #2 High) CSV `affected_ids` `\;` escape 폐기 → **`json.dumps(list, ensure_ascii=False)` 문자열 컬럼**으로 고정 (Python `csv` 모듈은 backslash escape 미지원, pandas roundtrip 보장)
    3. (v4 #3 High) **warnings 채널 단일화** — `collect_workspace_stats()`는 항상 `warnings: list[str]` 반환 (malformed 있으면 append, 없으면 `[]`). CLI stderr는 부가 출력. 테스트도 warnings 필드 검증.
    4. (v4 #4 High) **`_load_index` retract — `core.config_paths` import 금지** (side-effect: `os.makedirs`). `_index.json`은 직접 read만, validation skip 허용. 이에 따라 **v3 #1 `config/`로의 위치 이동을 retract** — `runtime/warnings/_index.json` in-place 갱신으로 단순화 (frozen 빌드 packaging 회피).
    5. (v4 #5 High) `warning-export --phase` 시그니처 추가 — §5.1 인자표/argparse, records/summary 양 모드에 동일 filter 적용.
    6. (v4 #6 Medium) `first_ts`/`last_ts` 시맨틱 — ts가 있는 record만 ISO lexical sort, ts 누락은 count에는 포함하되 first/last 계산 제외, 전부 누락이면 `""`. 0-record slug은 `projects[]` 제외.
    7. (v4 #7 Medium) `--slug` path traversal 방어 — `/`, `\`, `..`, 빈 문자열 금지. `os.path.basename(slug) != slug`이면 argparse error.
    8. (v4 #8 Medium) median 출력 강제 float — `float(statistics.median(values))`로 캐스팅 (n=1, n=2 정수 누출 방지).
    9. (v4 #9 Medium) `--top` truncation 범위 — `projects[]`만 truncate, distribution/totals/by_phase_total은 full matching population. **`project_count_total` / `project_count_returned` 메타 필드 추가**.
    10. (v4 #10 Medium) `--out` atomic write — 같은 디렉토리 temp file + `os.replace()`, 실패 시 temp cleanup. stdout 모드는 atomic 불필요.
    11. (v4 #11 Medium) changelog wording — "P4로 미룸" → "P3 scope 제외, P4 설계에서 재평가"로 정정.
    12. (v4 #12 Low) §8.3 `:1401` 0건 실측 사실 명시 — `tests/test_warning_registry_migration_callsites.py`에 `:1401` assertion 부재 확인. fixture 갱신 불필요.
  - v3 (2026-05-10 KST 늦은 오후) — v2 작성 중 hook 자동 발화한 cross-review BLOCK 9 + HOLD 1 흡수:
    1. (#1 Critical) `_index.json` 위치 이동이 §3.2/§7/§10 본문에서 절반만 적용 — 모든 stale path를 `config/warning_registry_index.json`로 통일
    2. (#2 Critical) CLI dispatch 이름 `_HANDLERS` → 실측 baseline `_STAGE1_DISPATCH` (run_factory_cli.py:429,580)
    3. (#3 Critical) §3.2 self-contradiction — `core/project_pipeline.py:1466` row 추가 + footer "변경 없음" 분리 명시
    4. (#4 High) source line 1454(import)/1455(callsite) 구분 — canonical pointer는 `:1455`. baseline grep range는 `1454-1469` 유지.
    5. (#5 High) install-af.ps1 §3.2/§7 "3 lines" → "8곳" 정정 + 사후 검증 `grep -c '1\.2\.25' install-af.ps1` = 0
    6. (#6 High) §8.1 case 5 wording을 v2 schema에 맞춰 rewrite — `applied_filters` + `by_phase_total` (filtered) + `by_phase_total_unfiltered` (full) 모두 assert
    7. (#7 Medium) §4.5 unknown `--rule` "0건 반환" → "jsonl 스캔 그대로 진행 + warnings 1줄" — registry SoT(`record()`)는 index 등록 무관하게 jsonl 작성하므로 데이터 버리지 않음
    8. (#8 Medium) §8.4 frozen smoke OS 분기 명확화 — `af.exe` (Windows) / `af` (macOS/Linux) host detect
    9. (#9 Medium) §8.1에 `--slug` core 단위 테스트 추가 (case 7), §8.2 case 11(`cli_export_summary_csv_rejected`)/case 12(`cli_slug_filter`)는 v2에서 이미 포함 — review stale read false-positive
    10. (#10 HOLD) schema_version 1 → 2 bump의 reader 부재 → **P4로 미룸** (KISS, defensive reader 불필요). v3 본문에서 schema_version bump를 유지하되 §6.5에 "P3에서 reader 없음 — P4가 도입 시점"으로 명시.
    11. cross-review v3가 critic 일부 finding을 stale copy false-positive로 분류 (R1~R5: --slug/by_per_record_count/iter_warning_records/median rule 모두 v2에 이미 있음)
  - v2 (2026-05-10 KST 오후) — cross-review v1 12 finding 반영:
    1. (#1 High) `source_path` zero-change 자기모순 — §3.2 변경 파일에 `core/project_pipeline.py:1466` 1줄 추가, §6.4 정정
    2. (#2 High) `--phase` 시맨틱 — record-level filter로 정의, `applied_filters` + `by_phase_total_unfiltered` 출력
    3. (#3 High) `_index.json` 위치 — `runtime/warnings/` → `config/warning_registry_index.json` 이동, `af.spec datas` 묶음
    4. (#4 High) `Distribution.by_per_record_count` 차원 추가 (record-level count 분포 — P4 임계 차원 직결)
    5. (#5 Medium) stdout 단일 JSON 계약 — `warnings: []` 필드, stderr는 옵션 미러
    6. (#6 Medium) `iter_warning_records()` 단일 iterator — stats/export 공유, malformed jsonl + slug dir filter 흡수
    7. (#7 Medium) `ProjectStats.count` docstring 정정 — "sum of WarningRecord.count across records"
    8. (#8 Medium) slug 디렉토리 필터 — `os.scandir` + `is_dir()` + `not name.startswith("_")`
    9. (#9 Low) revert 안전성 단서 — "P3 단독 시점에 한해" 명시
    10. (#10 Low) frozen build OS 분기 — "host OS frozen build 1개 (`dist/af` 또는 `dist/af.exe`)"
    11. (#11 HOLD→ACCEPT) `--slug SLUG` 옵션 추가 (warning-stats + warning-export 둘 다, optional filter, 사용자 결정 2026-05-10)
    12. (#12 HOLD→ACCEPT) `install-af.ps1` 8곳 1.2.25 → 1.2.26 일괄 교체 (사용자 결정 2026-05-10)
    13. (#13 REJECT) `summarize()` 회피 우려 — read-only 보장 위해 그대로 유지

---

## §0 Goal — 한 줄 정의

> **P3 = 측정 데이터 "분석 가능화"**. P1에서 이미 `owner_role_mismatch` record는 누적되고 있으므로, P3는 **누적된 jsonl을 분포 통계로 환원하는 분석/추출 도구**를 추가하고, **policy/index에 measurement marker를 박는다**. **P3에서 BLOCK semantics 변경 금지** — `evaluate()`는 P4까지 inactive 유지.

### 0.1 P2 vs P3 경계 (사용자 가시 변화)

| 항목 | P2 (완료 v1.2.25) | P3 (본 설계) |
|------|-------------------|-------------|
| `owner_role_mismatch` jsonl 누적 | ✅ (P1부터 `project_pipeline.py:1454-1469`) | (그대로 — 호출처 확장 없음) |
| `owner_role_mismatch` BLOCK | ❌ (`activate_at: P4`) | ❌ (그대로 — **P3에서 활성하지 않는다**) |
| 분포 통계 출력 | ❌ (`warning-summary`는 single-slug `_summary.json` 덤프뿐) | ✅ **`af warning-stats`** — workspace 전체 fan-out, project별 분포, p50/p95, by_phase, **`--slug` optional filter**, **stdout 단일 JSON + `warnings: []` 필드** |
| jsonl/summary 산출물 추출 | ❌ | ✅ **`af warning-export`** — CSV/JSON으로 회의용 산출물 생성, **`--slug` optional filter**, **records/summary 모드 공통 iterator** |
| measurement phase 가시성 | `_index.json.activate_at` 한 필드 (위치: `runtime/warnings/_index.json`) | ✅ `measure_at` + `mode: observation` 명시. **위치 그대로 `runtime/warnings/_index.json`** (v4 #4: side-effect 없는 direct read 처방으로 v3의 config/ 이동 retract). schema_version 1 → 2로 in-place 갱신. |
| `evaluate()` 동작 변경 | inactive (P4 미달) | (그대로 — **rule loader도 건드리지 않는다**) |
| `source_path` 정정 | `1401` (P1 잔존) | `core/project_pipeline.py:1466` 실코드 1줄 동시 정정 (#1) — `_index.json.source` 메타데이터만 정정하면 향후 record가 stale 유지되는 자기모순 해소 |

> **P3 첫 실행 동작**: 사용자는 P2 빌드를 받은 채로 일정 기간 운영 → `owner_role_mismatch` jsonl이 `runtime/warnings/<slug>/owner_role_mismatch.jsonl`에 누적 → P3 빌드 설치 후 `af warning-stats --workspace <root> --rule owner_role_mismatch` 실행 → 모든 slug 합산 분포 출력. **빌드 동작/CI gate에는 변화 없음**.

---

## §1 문제 — 왜 P3가 "yaml 한 줄"이 아닌가

### 1.1 baseline grep 사실 (실측, 2026-05-10)

| 파일:줄 | 사실 |
|---------|------|
| `core/project_pipeline.py:1454-1469` | `owner_role_mismatch` record 호출 — **이미 P1에서 들어감** (NEXT_STEPS v6 §7.3 P1 PR scope #6) |
| `core/project_pipeline.py:1331` | `_record_ledger_outcomes`는 `status in {crashed, unknown}` 외 **모든 status에서 호출** — 정상 `completed`도 모집단 포함 |
| `core/project_task_board.py:227-252` | `detect_owner_drift` 시그니처 = `list[tuple[task_id, expected, actual]]` (P1 마이그레이션 완료) |
| `config/escalation_policy.yaml:15-19` | `owner_role_mismatch.activate_at: P4` + `repeat_count_min: 3` — **이미 등록** |
| `core/escalation_evaluator.py` (현 위치) | P2 본체 — `current_phase` 인자로 분기. P4 미달이면 `inactive_phase` 반환 (`block=False`) |
| `runtime/warnings/_index.json:11-14` | `owner_role_mismatch.activate_at: "P4"` + `source: "core/project_pipeline.py:1401"` — **이미 등록** |
| `core/warning_registry.py:170-238 summarize()` | **single-slug 한정**. workspace 전역 합산/분포 분석 기능 없음 |
| `core/warning_registry.py:240-242 load_global()` | `raise NotImplementedError("global aggregation activates at P4")` — P3는 이 stub을 풀지 않는다 |
| `run_factory_cli.py:444-446` | `warning-summary/repair/override` 3개만 등록. `warning-stats` / `warning-export` 없음 |
| `core/warning_registry.py:374` summary 반환 | `by_rule[<rid>] = {count, first_ts, last_ts, severity, by_phase, repeat_count_max, any_override}` — 통계 기본 입력 충분 |

### 1.2 결과: "B(분석 CLI) + D(추출) + C(marker)" 세 PR이 묶여야 의미

- B 없이 D만 있으면: raw jsonl만 외부에 떨어져 분석은 사람 손에 달림.
- D 없이 B만 있으면: 콘솔 출력은 있어도 회의/리뷰 산출물로 남길 수 없음.
- B/D 둘만 있으면: P4에서 phase 옮기는 사람이 "이 데이터가 measurement-only다"라는 맥락을 추적 못함 (`activate_at: P4`만 보면 "곧 활성"으로 오독).
- → **B → D → C 순서로 한 PR**. 코드는 분석 도구만, policy semantics는 0 변경.

### 1.3 모집단 충분성 자체 검증

`_record_ledger_outcomes`는 `project_pipeline.py:1331`에서 호출되며, 모듈별 `module_outcome_from_board`가 `completed/at_risk` 둘 중 하나일 때 `detect_owner_drift`를 부른다 (line 1436-1447). `mismatches`가 비지 않은 케이스만 record 발생 → **모집단 = "모듈 outcome이 결판난 정상/실패 빌드"**. 이는 P4 임계값 결정에 바로 쓸 수 있는 모집단이고, P3에서 호출처를 늘리면 generation-time/execution-time이 섞여 P4 enforcement 기준이 오염된다(사용자 결정, 2026-05-10). → **호출처 확장은 P3 scope 외**.

---

## §2 Scope (사용자 합의 — 2026-05-10)

### 2.1 포함 (한 PR)

1. **`af warning-stats`** subcommand — workspace 전체 fan-out, rule_id 필터(default `owner_role_mismatch`), project별 count/repeat_count_max/by_phase, 분포 통계(median/p95/min/max).
2. **`af warning-export`** subcommand — record SoT(`*.jsonl`) 또는 stats 결과를 CSV/JSON으로 추출. 기본은 stats summary JSON.
3. **`runtime/warnings/_index.json` in-place schema v2 갱신** (v4 #4 retract — v3의 config/ 이동 철회) — 각 rule에 `measure_at` 옵션 필드 + `mode` 필드 추가. `owner_role_mismatch.measure_at: "P3"`, `mode: "observation"`. **`activate_at: P4`는 유지**. retract 근거는 §6.0 — side-effect 없는 direct read + PR scope 단순화.
4. **`Master_Blueprint.md`** §3.8 + §12 갱신.
5. **테스트 9 케이스** — §8 참조.

### 2.2 제외 (P4 이상)

- `evaluate()` 본체 변경 (P4 임계값 결정 후).
- `escalation_policy.yaml` rule semantics 변경 (P4).
- `WarningRegistry.load_global()` stub 해제 (P4).
- record 호출처 확장 (보류 — 사용자 결정).
- `evidence_quality_warn` / `plan_verifier_warn` 분석 (필요 시 P3 후속에서 동일 CLI에 rule_id 인자만 바꿔 재사용 가능 — 코드 변경 0).
- 글로벌 dashboard / 시각화 (P5 doc_consistency_meter와 묶음).

---

## §3 Architecture

### 3.1 데이터 흐름 (P3 추가분 굵게)

```
  사용자가 P2 빌드 운영 (1주~)
    └─→ project_pipeline.execute()
          └─→ _record_ledger_outcomes() [P1, 변경 없음]
                └─→ WarningRegistry.record(owner_role_mismatch, ...)
                      └─→ runtime/warnings/<slug>/owner_role_mismatch.jsonl  [P1, 변경 없음]

  사용자가 P3 빌드 받고 회의 준비
    └─→ af warning-stats --workspace <root> [--rule owner_role_mismatch]   ★P3
          └─→ WorkspaceStats.collect(workspace, rule_id)                   ★P3 (신규)
                ├─→ slug fan-out: runtime/warnings/<slug>/<rule>.jsonl 모두 스캔
                ├─→ project별 by_rule entry 누적
                └─→ 분포 통계 계산 (median/p95)
          └─→ stdout JSON 출력

    └─→ af warning-export --workspace <root> --format csv [--rule ...]    ★P3
          └─→ CSV writer: per-record (slug, ts, count, repeat_count, affected_phase, affected_ids)
                또는 JSON summary 모드: WorkspaceStats.collect() 결과 그대로

  policy / index marker는 yaml/json만, 코드 동작 0 변경
    └─→ runtime/warnings/_index.json   ★P3 (in-place schema v2 갱신, v4 #4 — config/ 이동 retract)
          └─→ owner_role_mismatch: { activate_at: P4, measure_at: P3, mode: observation }   ★P3
```

> **wiring 위치 확정**: 신규 모듈은 **`core/warning_stats.py`** 1개. CLI는 dispatch dict에 2개 entry만 추가. `WarningRegistry`는 import만 (`record/summarize` 호출 없음 — read-only). `escalation_evaluator`는 import 자체 안 함 (decision semantics 무관).

### 3.2 모듈별 변경

| 파일 | 변경 | 라인 |
|------|------|------|
| `core/warning_stats.py` | **신규** — `collect_workspace_stats(workspace, *, rule_id, slug=None, phase=None) -> dict` + `iter_warning_records(workspace, *, rule_id, slug=None)` 공유 iterator + `_compute_distribution` | 약 160줄 |
| `run_factory_cli.py` | `_run_warning_stats_subcommand` + `_run_warning_export_subcommand` 신규 함수 + **`_STAGE1_DISPATCH`** + `_STAGE1_USAGE` 각 2 entry 추가 | ~60줄 추가 |
| `core/project_pipeline.py` | **(#1)** line 1466 `source_path="core/project_pipeline.py:1401"` → `:1455` 1줄 정정 (1454는 import, 1455가 `.record(` callsite) — record가 stale source를 영구 박는 자기모순 해소 | 1 line |
| `runtime/warnings/_index.json` | **in-place 갱신 (v4 #4 retract — 이동 안 함)**: schema_version 1 → 2, `measure_at`/`mode` optional 필드 추가, owner_role_mismatch에만 `measure_at: "P3"` + `mode: "observation"`, `source: "core/project_pipeline.py:1455"` 정정 | json edit (~6 lines) |
| `af.spec` | `core.warning_stats` hiddenimports 추가 (v4 #4 retract: `datas` 항목 추가 없음 — `_index.json`은 워크스페이스 runtime data, frozen 빌드에 포함하지 않는다) | 1 line |
| `Master_Blueprint.md` | §3.8 — measurement phase 표기 + warning-stats/export CLI / §0 — 신규 모듈 row / §12 — 변경 이력 | 3 섹션 |
| `tests/test_warning_stats.py` | **신규** — 6 케이스 (§8.1) | ~150줄 |
| `tests/test_warning_stats_cli.py` | **신규** — 6 케이스 (§8.2 #7~#12) | ~140줄 |
| `version.py` | `1.2.25` → `1.2.26` (P3 minor) | 1 line |
| `install-af.ps1` | **(#12)** `1.2.25` → `1.2.26` **8곳 일괄** (상단 설명 / 예시 URL / 관리자 재실행 URL / 설치 헤더 / zip 파일명 / 다운로드 메시지 / 다운로드 URI / 완료 메시지) | 8 lines |

> **변경 없음** (회귀 위험 0): `core/warning_registry.py`, `core/escalation_evaluator.py`, `core/escalation_decision_report.py`, `core/warning_overrides.py`, `core/approval_gate.py`, `core/work_item_generator.py`, `config/escalation_policy.yaml`.
>
> **변경 있음 (1줄 surgical, footer "변경 없음" 목록과 분리)**: `core/project_pipeline.py:1466` — `source_path` 리터럴 1개만 `:1401` → `:1455` 교정. record 스키마/호출 시점/매개변수 불변. (#3 self-contradiction 해소)

### 3.3 새 모듈 — `core/warning_stats.py` 시그니처 (실제 구현 가이드)

```python
"""Warning Stats — P3 분석 도구.

read-only: runtime/warnings/<slug>/<rule>.jsonl 풀스캔.
WarningRegistry.summarize() 호출 안 함 (decision report 부작용 회피).

iter_warning_records: stats / export 양쪽이 공유하는 단일 iterator.
malformed jsonl 라인 skip + slug 디렉토리 필터 + 동시 write 안전 (마지막 라인 잘림 skip).
"""
from __future__ import annotations
import json
import math
import os
from dataclasses import asdict, dataclass
from typing import Iterator


@dataclass
class ProjectStats:
    project_slug: str
    count: int                    # sum of WarningRecord.count across records (per-run count 누적)  ← (#7 정정)
    record_lines: int             # jsonl 라인 수 (count과 별개 — repeat/dedup 검증용)
    repeat_count_max: int
    by_phase: dict[str, int]      # 매칭 record(phase filter 적용 후)의 phase별 count 누적
    first_ts: str                 # ts가 있는 record만 ISO lexical min, 전부 누락이면 ""    ← (v4 #6)
    last_ts: str                  # ts가 있는 record만 ISO lexical max, 전부 누락이면 ""    ← (v4 #6)
    # 0-record slug (rule_id에 매칭되는 jsonl 자체 부재 또는 phase filter 후 0 라인) 은 projects[]에서 제외  ← (v4 #6)


@dataclass
class Distribution:
    n: int                        # data point 수
    min: int
    median: float
    p95: float
    max: int


def iter_warning_records(                                        # ← (#6, #8 흡수)
    workspace: str,
    *,
    rule_id: str = "owner_role_mismatch",
    slug: str | None = None,
) -> Iterator[tuple[str, dict]]:
    """
    Yields (project_slug, record_dict) for every parseable jsonl line.

    - slug 디렉토리 필터: os.scandir + entry.is_dir() + not name.startswith("_")  (#8)
    - slug 인자 지정 시 해당 slug만 yield (단일 디렉토리만 scan).
    - jsonl 미존재 → 해당 slug skip (예외 X).
    - JSONDecodeError 라인 → skip + stderr 1줄 ("[warning-stats] malformed line in <path>:<lineno>").
    - 마지막 라인 trailing newline 부재 → 정상 처리.
    - workspace/runtime/warnings/ 자체 부재 → 빈 iterator.
    """


def collect_workspace_stats(
    workspace: str,
    *,
    rule_id: str = "owner_role_mismatch",
    slug: str | None = None,                          # ← (#11 추가)
    phase: str | None = None,                         # ← (#2 record-level filter)
) -> dict:
    """
    Returns:
      {
        "schema_version": 1,
        "rule_id": rule_id,
        "workspace": <abs path>,
        "applied_filters": {                          # ← (#2) 출력에 항상 명시. None은 빈값 또는 생략.
          "slug": "<slug>" | null,
          "phase": "<phase>" | null,
        },
        "scanned_slug_count": int,                    # slug filter 적용 후 실제 scan된 디렉토리 수
        "project_count_total": int,                   # ← (v4 #9) matching project (count > 0) 총 개수 — top truncate 무관
        "project_count_returned": int,                # ← (v4 #9) projects[] 배열에 실제 출력된 개수 (top 적용 후)
        "projects": [ProjectStats as dict, ...],      # count 내림차순, 동률 시 project_slug ASC. **0-record slug 제외 (v4 #6)**. top truncate 적용. (v4 #9)
        "totals": {"count": int, "record_lines": int},# **full matching population 기준 — top truncate 무관 (v4 #9)**
        "distribution": {                             # **full matching population 기준 — top truncate 무관 (v4 #9)**. n=0 → null. n=1 → min=median=p95=max=동일값.
          "by_project_count": Distribution,           #   project별 누적 count 분포 (모집단=project)
          "by_project_repeat_count_max": Distribution,#   project별 repeat_count_max 분포
          "by_per_record_count": Distribution,        # ← (#4) record별 count 필드 분포 (모집단=record). P4 repeat_count_min 임계 직결 차원.
        },
        "by_phase_total": {phase: count, ...},        # filter 적용 후 phase별 record count 누적 (full population, top 무관)
        "by_phase_total_unfiltered": {phase: count},  # ← (#2) phase filter 미적용 시 모집단 비율 가시화. filter 미사용 시 by_phase_total과 동일.
        "warnings": [                                 # ← (#5 + v4 #3) **항상 list[str]** — malformed jsonl/unknown rule/n<20/slug not found 등 모든 진단을 append. 비어있어도 `[]`로 출력.
          # "n=3, p95 may be unstable for n<20",
          # "no slug directories under runtime/warnings/",
          # "rule_id 'foo' not in runtime/warnings/_index.json",
          # "malformed line in <slug>/<rule>.jsonl:<lineno>",     ← v4 #3: stderr 미러는 부가, warnings 필드가 SoT
          # ...
        ],
      }

    Filter semantics (#2 명시):
    - phase 인자: record-level filter. record.affected_phase != phase면 모든 집계에서 제외.
      → by_phase_total은 매칭 phase 1개만 포함 (또는 빈 dict if no record match).
      → by_phase_total_unfiltered는 모든 phase 포함 (filter 미적용).
      → projects[].count, projects[].record_lines, projects[].repeat_count_max,
        projects[].by_phase, totals, distribution.* 모두 매칭 record만 반영.
    - slug 인자: project_slug filter. 단일 slug만 scan → scanned_slug_count = 0 또는 1.
    """
```

### 3.4 분포 계산 규약 (실측 정의)

- `n=0`: distribution 전체를 `null` 반환 (분포 정의 불가). `warnings: ["no slug directories under runtime/warnings/"]` 또는 `["rule_id '<rid>' has no records"]` 1줄 추가.
- `n=1`: `min == median == p95 == max == 단일값`.
- `median`: **항상 float** — `float(statistics.median(values))` 강제 캐스팅 (v4 #8). n=1 또는 n=2의 정수 누출 (`statistics.median([1,1]) == 1`) 회피. 직렬화 schema 일관성.
- `p95`: nearest-rank percentile, **`math.ceil(0.95 * n) - 1`** 인덱스 (sort ascending, 0-based). n=1이면 `ceil(0.95) - 1 = 0` → `min == p95 == max`. n=20이면 `ceil(19) - 1 = 18` (95-percentile rank).
- n<20일 때 p95는 사실상 max에 수렴하므로 `warnings: ["n=<N>, p95 may be unstable for n<20"]` 추가 (단 distribution 자체는 그대로 출력).
- 입력은 `int` (count, repeat_count_max, per_record_count) → median은 float, p95는 int. 출력 JSON에서 정수 필드는 정수, median은 float.
- **`by_per_record_count`** 모집단 (#4): 모든 매칭 record의 `record["count"]` 필드 list. project별 합산 아님. P4 `repeat_count_min: 3` 임계 결정의 1차 차원.

### 3.5 read 안전성 (모두 `iter_warning_records()` 단일 channel에서 흡수, #6)

- 디렉토리 진입: `os.scandir(<workspace>/runtime/warnings/)` → `entry.is_dir() and not entry.name.startswith("_")` 만 yield (#8).
  - `_index.json`/`_summary.json`/`_overrides.json`/`_decision.json` 등 메타 파일 전부 자동 제외.
  - `_template`/`_legacy` 등 명시적 underscore prefix 디렉토리도 제외.
- jsonl 진입: `<slug_dir>/<rule_id>.jsonl` 부재 → 해당 slug skip (에러 X).
- 라인 파싱: `JSONDecodeError` → skip + **`warnings: []`에 `"malformed line in <slug>/<rule>.jsonl:<lineno>"` append (v4 #3 SoT)**. stderr 미러는 부가 출력 (디버그 편의). stdout JSON은 항상 valid.
- 동시 write 가능성 (`record()`가 진행 중일 수 있음): jsonl은 append-only이므로 EOF에서 잘려도 마지막 라인만 skip. `summarize()`의 lock(`_summary.json.lock`)은 사용 **안 함** — stats는 `_summary.json` 안 건드림 (read-only 보장 → cross-review #13 REJECT 근거).
- `<workspace>/runtime/warnings/` 자체가 없으면 `scanned_slug_count: 0` + `projects: []` 반환 (에러 아님). `warnings: [...]` 배열에 1줄.

---

## §4 핵심 출력 — `af warning-stats`

### 4.1 CLI 시그니처

```
af warning-stats --workspace PATH [--slug SLUG] [--rule RULE_ID] [--top N] [--phase PHASE]
```

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--workspace` | (필수) | AF 운영 데이터 루트 (`/runtime/warnings/` 부모) |
| `--slug` | (없음) | **(#11 신규)** 단일 project_slug filter. 지정 시 해당 디렉토리만 scan. |
| `--rule` | `owner_role_mismatch` | 분석 대상 rule_id |
| `--top` | `10` | **`projects[]` 배열만** 상위 N개로 truncate. `totals` / `distribution.*` / `by_phase_total` 은 full matching population 기준 (v4 #9). `--top 0` = 전체. `project_count_total` / `project_count_returned` 메타 필드로 truncate 영향 명시. |
| `--phase` | (없음) | **(#2 record-level filter)** 지정 시 매칭 record만 모든 집계에 반영. `applied_filters` + `by_phase_total_unfiltered`로 영향 가시화. |

### 4.2 stdout 예시 (n=0, 빈 workspace)

```json
{
  "schema_version": 1,
  "rule_id": "owner_role_mismatch",
  "workspace": "/abs/path",
  "applied_filters": {"slug": null, "phase": null},
  "scanned_slug_count": 0,
  "projects": [],
  "totals": {"count": 0, "record_lines": 0},
  "distribution": null,
  "by_phase_total": {},
  "by_phase_total_unfiltered": {},
  "warnings": ["no slug directories under runtime/warnings/"]
}
```

### 4.3 stdout 예시 (n=3, owner_role_mismatch, no filter)

```json
{
  "schema_version": 1,
  "rule_id": "owner_role_mismatch",
  "workspace": "/Users/hoon/workTree/agent-factory",
  "applied_filters": {"slug": null, "phase": null},
  "scanned_slug_count": 12,
  "project_count_total": 3,
  "project_count_returned": 3,
  "projects": [
    {"project_slug": "build-a-cli-snake-game-...", "count": 7, "record_lines": 4, "repeat_count_max": 3, "by_phase": {"build": 5, "verify": 2}, "first_ts": "2026-05-08T...", "last_ts": "2026-05-09T..."},
    {"project_slug": "implement-chat-ui-...", "count": 2, "record_lines": 2, "repeat_count_max": 1, "by_phase": {"build": 2}, "first_ts": "...", "last_ts": "..."},
    {"project_slug": "fix-auth-bug-...", "count": 1, "record_lines": 1, "repeat_count_max": 1, "by_phase": {"integrate": 1}, "first_ts": "...", "last_ts": "..."}
  ],
  "totals": {"count": 10, "record_lines": 7},
  "distribution": {
    "by_project_count":            {"n": 3, "min": 1, "median": 2.0, "p95": 7, "max": 7},
    "by_project_repeat_count_max": {"n": 3, "min": 1, "median": 1.0, "p95": 3, "max": 3},
    "by_per_record_count":         {"n": 7, "min": 1, "median": 1.0, "p95": 3, "max": 3}
  },
  "by_phase_total":            {"build": 7, "verify": 2, "integrate": 1},
  "by_phase_total_unfiltered": {"build": 7, "verify": 2, "integrate": 1},
  "warnings": ["n=3, p95 may be unstable for n<20"]
}
```

### 4.3.1 stdout 예시 (`--phase build` 적용 시 — record-level filter 효과)

```json
{
  "applied_filters": {"slug": null, "phase": "build"},
  "scanned_slug_count": 12,
  "project_count_total": 2,
  "project_count_returned": 2,
  "projects": [
    {"project_slug": "build-a-cli-snake-game-...", "count": 5, "record_lines": 3, "repeat_count_max": 3, "by_phase": {"build": 5}, "first_ts": "...", "last_ts": "..."},
    {"project_slug": "implement-chat-ui-...", "count": 2, "record_lines": 2, "repeat_count_max": 1, "by_phase": {"build": 2}, "first_ts": "...", "last_ts": "..."}
  ],
  "totals": {"count": 7, "record_lines": 5},
  "distribution": {
    "by_project_count":            {"n": 2, "min": 2, "median": 3.5, "p95": 5, "max": 5},
    "by_project_repeat_count_max": {"n": 2, "min": 1, "median": 2.0, "p95": 3, "max": 3},
    "by_per_record_count":         {"n": 5, "min": 1, "median": 1.0, "p95": 3, "max": 3}
  },
  "by_phase_total":            {"build": 7},
  "by_phase_total_unfiltered": {"build": 7, "verify": 2, "integrate": 1},
  "warnings": ["n=2, p95 may be unstable for n<20"]
}
```

> filter 효과: `fix-auth-bug-...`(integrate phase only)는 `count: 0`이 되어 projects에서 탈락. `by_phase_total_unfiltered`로 모집단 비율(7/10) 가시화.

### 4.4 stdout 단일 JSON 계약 (#5 + v4 #3 SoT 통일)

- **stdout은 항상 단일 valid JSON 1개만 출력**. `json.loads(stdout)`이 모든 케이스에서 성공해야 함.
- **`warnings: list[str]`은 SoT 채널** (v4 #3). `collect_workspace_stats()`가 항상 list 반환 (비어 있어도 `[]`). 모든 휴먼 진단(malformed line / unknown rule / n<20 / slug not found / index file missing)을 이 list에 append.
- stderr는 **부가 출력만** — argparse error 외에는 디버그 편의용 미러. stdout warnings 필드가 진짜 진실원천이고, 테스트는 stdout `warnings` 필드 포함 여부를 검증한다 (stderr는 검증 안 함).
- stdout JSON과 stderr는 별개 채널이므로 pipe redirect (`af warning-stats ... 2>/dev/null`)도 정상 결과를 깨뜨리지 않는다.

### 4.5 인자 검증 (argparse)

- `--workspace` 필수 — 누락 시 argparse SystemExit(2).
- `--rule`이 `runtime/warnings/_index.json`에 등록되지 않은 값이면: `warnings:`에 `"rule_id '<rid>' not in runtime/warnings/_index.json"` 1줄 + **jsonl 스캔은 그대로 진행** (#7 ACCEPT). 근거: `core/warning_registry.py:84-126 record()`는 index 등록 여부와 무관하게 `<rule>.jsonl` 작성 — index는 메타데이터일 뿐 SoT가 아니므로, unknown rule이라고 jsonl을 0건으로 강제하면 실재 데이터를 버리는 결함. 운영자가 지정한 rule_id의 jsonl이 디스크에 있다면 분석 결과를 그대로 출력. index 파일 자체가 없으면 검증 skip + `warnings:`에 그 사실 1줄.
- `--top` 음수 → argparse error.
- `--phase`가 `_PHASE_ORDER` (registry와 동일: `scope/build/integrate/code_review/cross_validate/verify`) 외이면 `warnings:`에 1줄 + filter 적용 (사용자 의도 보존). 정렬은 `count` 내림차순 후 `project_slug` ASC.
- **`--slug` sanitization (v4 #7 보안 결함 방어)**: 다음 중 하나라도 만족하면 **argparse error (SystemExit 2)**:
  - 빈 문자열 (`""`)
  - `/` 또는 `\` 포함
  - `..` 포함 (혹은 `os.path.basename(slug) != slug`)
  - 검증 통과한 slug만 `os.path.join(warnings_root, slug)`에 사용. read-only 도구라도 임의 디렉토리 정보 노출을 차단.
- `--slug`가 검증 통과 후에도 디렉토리로 존재하지 않으면 `scanned_slug_count: 0` + `warnings:`에 `"slug '<slug>' not found"` 1줄 (실패 X).

---

## §5 핵심 출력 — `af warning-export`

### 5.1 CLI 시그니처

```
af warning-export --workspace PATH [--slug SLUG] [--phase PHASE] --format {csv,json} [--rule RULE_ID] [--out PATH] [--mode {records,summary}]
```

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--workspace` | (필수) | AF 운영 데이터 루트 |
| `--slug` | (없음) | **(#11)** 단일 project_slug filter. **§4.5와 동일한 sanitization 적용 (v4 #7)**: 빈 문자열 / `/` / `\` / `..` / `os.path.basename(slug) != slug` 거부 → argparse error. |
| `--phase` | (없음) | **(v4 #5 신규)** record-level filter. records/summary 양 모드 모두 적용. `iter_warning_records(workspace, rule_id, slug, phase=phase)` 또는 post-filter로 매칭 record만 출력. `_PHASE_ORDER` 외 phase는 `warnings:`에 1줄 + filter 적용. |
| `--format` | (필수) | `csv` 또는 `json` |
| `--rule` | `owner_role_mismatch` | 대상 rule_id |
| `--out` | (없음 → stdout) | **(v4 #10 atomic write)** 출력 파일 절대경로. dir 자동 생성. **같은 디렉토리에 `<filename>.tmp.<pid>` 임시파일 작성 → `os.replace(tmp, out)` 원자적 교체**. write 실패 시 temp cleanup + nonzero exit + stderr 진단. stdout 모드 (`--out` 미지정)는 atomic 불필요. |
| `--mode` | `records` | `records` = jsonl 라인을 평탄화 / `summary` = `collect_workspace_stats()` 결과 |

> **iterator 공유 (#6)**: records 모드는 `iter_warning_records(workspace, rule_id=..., slug=..., phase=...)`를 그대로 소비. malformed jsonl 라인은 stats와 동일한 정책으로 skip + `warnings:`에 append (v4 #3 SoT). slug 디렉토리 필터(`is_dir() + not startswith("_")`, #8)도 동일 채널.

### 5.2 records 모드 CSV 컬럼 (고정 순서)

```
project_slug,record_id,ts,rule_id,severity,affected_phase,count,repeat_count,affected_ids,source_path
```

- **`affected_ids`: `json.dumps(list, ensure_ascii=False)` 문자열로 직렬화** (v4 #2 처방). 근거: Python 표준 `csv` 모듈은 backslash escape 미지원 → 항목 내 `;`/`,`/`"`가 들어올 때 roundtrip 깨짐. JSON 문자열은 `csv.QUOTE_MINIMAL`이 자동 quoting 처리하고, 분석 도구는 `df["affected_ids"].apply(json.loads)`로 즉시 복원 가능.
- 누락 필드는 빈 문자열 (`""`). list/dict 필드 누락 시에는 `[]`/`{}` 직렬화 결과.
- 한 슬러그당 jsonl 한 파일을 line 순서대로 dump (정렬 안 함 — append 순서 보존).
- multi-slug 시 slug 정렬은 ASCII ASC. 같은 slug 내 record는 jsonl 라인 순서.
- BOM 없음, UTF-8, 줄바꿈 `\n`. CSV writer는 표준 `csv` 모듈 (`quoting=csv.QUOTE_MINIMAL`).

### 5.3 records 모드 JSON wrapper 형식 (#6 명시)

stdout / `--out` 둘 다 동일한 single valid JSON 객체:

```json
{
  "schema_version": 1,
  "rule_id": "owner_role_mismatch",
  "workspace": "/abs/path",
  "applied_filters": {"slug": null, "phase": null},
  "exported_at": "2026-05-10T...Z",
  "scanned_slug_count": 12,
  "record_count": 7,
  "records": [
    {"project_slug": "build-a-cli-snake-game-...", "record": { ... full WarningRecord dict ... }},
    {"project_slug": "build-a-cli-snake-game-...", "record": { ... }},
    ...
  ],
  "warnings": []
}
```

- 메모리 폭주 방지: scanned_slug_count > 1000 또는 record_count > 100000일 때 `warnings:`에 1줄 + 그대로 진행 (P3에서 streaming 안 도입 — YAGNI).
- 빈 결과 (`record_count: 0`)도 동일 wrapper, `records: []`.

### 5.4 summary 모드

- `collect_workspace_stats(workspace, rule_id=..., slug=..., phase=...)` 결과를 그대로 stdout/--out에 출력.
- **`--mode summary --format csv`이면 argparse error** (구조적 dict는 CSV로 평탄화 부적합 — 출력 의미 보존을 위해 거부).
- **`--phase`는 summary/records 양 모드에 동일 적용** (v4 #5). summary는 `collect_workspace_stats(phase=...)` 위임. records는 `iter_warning_records(phase=...)` 또는 export loop 안에서 post-filter (`record.affected_phase == phase`만 직렬화).

### 5.5 산출물 활용

- summary JSON: 회의 자료 첨부 (1 KB 단위) → P4 임계값 결정 근거.
- records CSV: 외부 분석 (Excel/pandas) — 사용자가 직접 차트 그릴 때.

---

## §6 measurement marker — `runtime/warnings/_index.json` in-place 갱신 + 스키마 v2

### 6.0 위치 결정 (v4 #4 retract — v3 #1 config/ 이동 철회)

- **위치: `runtime/warnings/_index.json` 그대로** (in-place 갱신).
- v3 #1에서 `config/warning_registry_index.json`로 이동을 제안했으나 v4 #4 처방에 따라 retract:
  - 사용자 처방 (2026-05-10): "P3 read-only 원칙이면 `core.config_paths` 같은 경로 생성 가능 import는 피해야 합니다. `_index.json`은 `os.path.join(abs_workspace, "runtime", "warnings", "_index.json")` 직접 read. 없으면 validation skip."
  - 위치 이동의 frozen 빌드 호환 근거는 약함 — index 파일 부재 시 validation skip만 하면 충분 (사용자 데이터 손실 0건).
  - in-place 유지의 이점: (a) `af.spec datas` 추가 불필요, (b) `.gitignore` 화이트리스트 변경 없음, (c) frozen 빌드 packaging 회귀 위험 0, (d) PR scope 단순화 (변경 파일 -3건).
- **참조 부재 사실 검증 (cross-review 진입 전 grep 1차)**:
  - `grep -rn "_index.json" core/ scripts/ tests/ run_factory_cli.py af.spec` → P3 PR 도입 전엔 매칭 0건이어야 함 (메타데이터 only). 매칭이 있다면 해당 호출처도 PR scope에 포함.

### 6.1 schema_version 1 → 2 변경점

| 필드 | v1 | v2 |
|------|----|----|
| `schema_version` | `1` | `2` |
| `rules[].rule_id` | str | str (변경 없음) |
| `rules[].activate_at` | str | str (변경 없음) |
| `rules[].source` | str | str (변경 없음) |
| `rules[].measure_at` | (없음) | **신규 옵션 str** — measurement phase. 누락 = "측정 phase 미지정". |
| `rules[].mode` | (없음) | **신규 옵션 str** — `"observation"` 또는 `"enforcement"`. 누락 = `"enforcement"` (기본). |

### 6.2 P3 적용값 (owner_role_mismatch만)

```json
{
  "rule_id": "owner_role_mismatch",
  "activate_at": "P4",
  "measure_at": "P3",
  "mode": "observation",
  "source": "core/project_pipeline.py:1455"
}
```

### 6.3 다른 rule은 변경 없음 (회귀 0)

- `e2e_command_missing` — `mode: enforcement` 묵시 기본. yaml/json 모두 그대로.
- `evidence_quality_warn` / `plan_verifier_warn` — 변경 없음.
- 새 `mode` 필드는 **runtime에서 읽지 않는다** — 메타데이터 only. evaluator/registry가 import 안 함. 즉 코드 수정 0.

### 6.4 source 라인번호 정정 (1401 → 1455, #1 + #4 ACCEPT)

- baseline 실측 (`core/project_pipeline.py`):
  - line 1454: `from core.warning_registry import WarningRegistry as _WR`  (import 문)
  - line 1455: `_WR(workspace=workspace).record(`  (실제 callsite)
  - canonical pointer = **callsite (`:1455`)**, range는 `1454-1469` 그대로 (P1 grep 표).
- 정정 채널 **2곳** (cross-review v1 #1: 메타데이터만 정정하면 향후 record가 stale source를 영구 박는 자기모순 발생):
  1. `runtime/warnings/_index.json`의 `rules[].source` 필드 (메타데이터) → `:1455`
  2. **`core/project_pipeline.py:1466`의 `source_path="core/project_pipeline.py:1401"` 리터럴** (record 생성 시 jsonl에 박히는 값) → `:1455`
- 두 곳을 **같은 PR**에서 동시에 정정. record schema/시그니처/호출 시점/매개변수는 전부 불변 — 문자열 리터럴 1줄만 교정.
- 기존에 누적된 record는 `source_path: "...:1401"`로 영구 보존 (역사 데이터). 신규 record부터는 `:1455`. 이는 history 추적을 깨뜨리지 않음 — record_id가 phase/timestamp/mismatches로 결정되므로 source_path 변경이 dedup에 영향 X.
- **v4 #12 실측 단서**: baseline grep 기준 `core/project_pipeline.py:1401`에는 owner record 호출이 없고, 실제 호출은 `:1454-1469` 영역 (callsite `:1455`)에 위치. 따라서 `_index.json.source` 메타데이터는 stale이며, P3 PR에서 정정한다.

### 6.5 escalation_policy.yaml은 건드리지 않는다

- `mode` 필드를 yaml에도 추가하면 evaluator loader가 알 수 없는 키로 fail-fast 가능성. 현 baseline `core/escalation_evaluator.py`의 `load_policy()` 내부 unknown-key 정책을 점검할 필요가 있고 (구현 시 grep 1차 확인), 그 시점에 confirm. **단, P3 PR scope에서 yaml 변경은 0줄로 잡는다** — observability marker는 `warning_registry_index.json` 단일 채널.

#### 6.5.1 schema_version bump의 reader 부재 (v4 #11 wording 정정)

- v3 cross-review #10 질문: schema_version 1 → 2 bump의 defensive reader (`assert schema_version <= 2`)를 P3에 추가할지?
- **결정: schema_version은 P3에서 1 → 2로 bump하되, reader 도입은 P3 scope 제외 — P4 설계에서 재평가** (v4 #11 wording: "P4로 미룸"이 measure_at/mode bump와 충돌 인상 회피).
- 근거:
  1. P3에서 schema_version을 읽는 코드 0건 (메타데이터). defensive reader 추가는 KISS 위반 (Karpathy rule #2).
  2. P4가 `measure_at`/`mode`를 실제로 읽기 시작하는 시점에 reader가 자연스럽게 도입됨 — 그때 fail-fast 정책도 함께 결정.
  3. P3에서 schema_version을 1 → 2로 올리는 이유는 **"v2 스키마 의도가 도큐먼트 + json에 동시에 박혀 있어, P4 시점 reader가 schema_version으로 분기 가능"** 한 표지 역할만. 실 reader 부재 자체가 결함은 아님.

### 6.6 `_load_index()` 헬퍼 — side-effect 없는 direct read (v4 #4)

- v3 §6.6은 frozen 빌드 packaging을 도입했으나 v4 #4 처방 (`core.config_paths` import 금지) 으로 단순화.
- index 로드 헬퍼 (`core/warning_stats.py` 내부 함수):
  ```python
  def _load_index(workspace: str) -> dict | None:
      """side-effect-free direct read.

      core.config_paths import 금지 (os.makedirs side-effect 회피).
      <workspace>/runtime/warnings/_index.json 한 곳만 시도. 없거나 깨지면 None 반환.
      """
      path = os.path.join(os.path.abspath(workspace), "runtime", "warnings", "_index.json")
      if not os.path.isfile(path):
          return None
      try:
          with open(path, encoding="utf-8") as fh:
              return json.load(fh)
      except (OSError, json.JSONDecodeError):
          return None
  ```
- index 로드 실패 → `warnings:`에 `"index file not found at runtime/warnings/_index.json"` 1줄 + `--rule` 검증 skip + 정상 진행 (실패 X).
- frozen 빌드: index 파일은 `runtime/warnings/_index.json` (워크스페이스 runtime data 영역) — 워크스페이스에 없으면 validation skip만, 분석 도구 실행 자체는 정상.

---

## §7 PR 변경 파일 목록 (구현 순서)

| # | 파일 | 변경 | 의존 |
|---|------|------|------|
| 1 | `core/warning_stats.py` | 신규 (~160줄) — `iter_warning_records` + `collect_workspace_stats` + `_load_index` + `_compute_distribution` | (없음) |
| 2 | `tests/test_warning_stats.py` | 신규 6 케이스 (§8.1) | #1 |
| 3 | `run_factory_cli.py` | `_run_warning_stats_subcommand` + `_run_warning_export_subcommand` + `_STAGE1_DISPATCH` 2 entry + `_STAGE1_USAGE` 2 entry (v3 #2 baseline 정정) | #1 |
| 4 | `tests/test_warning_stats_cli.py` | 신규 6 케이스 (§8.2) | #1, #3 |
| 5 | `core/project_pipeline.py` | **(#1 + v3 #4)** line 1466 `source_path` 리터럴 `:1401` → `:1455` (callsite 기준) | (독립) |
| 6 | `runtime/warnings/_index.json` | **(v4 #4 retract — config/ 이동 철회) in-place 갱신**: schema_version 1 → 2, `measure_at: "P3"` + `mode: "observation"` (owner_role_mismatch만), `source: "core/project_pipeline.py:1455"` 정정 | json edit |
| 7 | `af.spec` | hiddenimports `core.warning_stats` 1줄 (v4 #4: `datas` 추가 없음 — `_index.json`은 워크스페이스 runtime data 영역) | 1 line |
| 8 | `version.py` | `1.2.25` → `1.2.26` | (마지막) |
| 9 | `install-af.ps1` | **(#12 + v3 #5)** `1.2.25` → `1.2.26` 8곳 일괄 (line :3, :6, :27, :34, :105, :106, :110, :251 — 실측 기준). 사후 검증: `grep -c '1\.2\.25' install-af.ps1` 결과가 0이어야 함. | (마지막) |
| 10 | `Master_Blueprint.md` | §0 신규 모듈 row + §3.8 measurement phase / CLI 표 / index in-place 갱신 / source_path 동시 정정 + §12 변경 이력 | 모든 코드 변경 후 |

> **Karpathy rule #3 surgical**: `core/warning_registry.py`/`core/escalation_evaluator.py`/`core/escalation_decision_report.py`/`core/warning_overrides.py`/`core/approval_gate.py`/`config/escalation_policy.yaml` 등 핵심 파일은 **0줄 변경**. record 호출 시점/매개변수 0 변경. policy yaml 0 변경. **`core/project_pipeline.py`의 #1 1줄은 surgical 정정 — record schema/호출 흐름은 모두 불변**. P3 PR이 P2 회귀를 만들 수 있는 면이 사실상 0.

---

## §8 테스트 — 16 케이스

### 8.1 `tests/test_warning_stats.py` (7 케이스)

1. **empty_workspace** — `runtime/warnings/` 부재 → `scanned_slug_count: 0`, `distribution: null`, `warnings: ["no slug directories under runtime/warnings/"]` 1건. 예외 안 던짐. `applied_filters: {slug: null, phase: null}` 출력.
2. **single_slug_single_record** — slug 1개, record 1개 → `n=1`, `min/median/p95/max == 동일값`, `record_lines == 1`, `count == 1`. `by_per_record_count.n == 1`. (#4 차원 검증)
3. **multi_slug_distribution** — slug 5개, count={1, 2, 3, 5, 8} → `by_project_count.n=5, median=3, p95=8, max=8, min=1`. p95 nearest-rank 검증. `by_per_record_count` 모집단=record 검증 (project 5개에 record 다수면 n>5 가능).
4. **rule_filter** — 한 slug에 `owner_role_mismatch.jsonl` + `e2e_command_missing.jsonl` 둘 다 → `--rule owner_role_mismatch`면 후자 무시. by_phase 합산도 owner만.
5. **phase_filter_record_level** (#2 + v3 #6 정정) — record 5건 (3건 build, 2건 verify) → `phase="build"`로 호출 시 모든 assertion을 v2 schema로 명시:
   - `applied_filters.phase == "build"`
   - `totals.count` = build record `count` 합
   - `by_phase_total == {"build": <합>}` (filter 적용 = 매칭 phase만)
   - `by_phase_total_unfiltered == {"build": ..., "verify": ...}` (전체 phase, filter 미적용)
   - `by_per_record_count.n == 3` (build record만, record 모집단)
   - `by_project_count.n == build phase가 있는 project 수`
   - 빈 결과 case (`phase="scope"`로 매칭 record 0건) → `by_phase_total == {}`, `by_phase_total_unfiltered`는 그대로, `distribution` 정상 (n=0이면 null).
6. **malformed_jsonl_skip_warnings_sot** (#6, #8 + v4 #3) — jsonl에 깨진 라인 1개 + 정상 2개 → 정상 2개만 카운트. **`warnings:` 필드에 `"malformed line in <slug>/<rule>.jsonl:<lineno>"` 1줄 append (SoT 검증)**. stderr 미러는 부가 출력 (테스트는 stderr 미검증). 예외 안 던짐. slug dir과 같은 레벨에 `_index.json`/`_summary.json` 존재해도 `iter_warning_records`가 `is_dir() + not startswith("_")`로 자동 필터.
7. **slug_filter_core_with_traversal_guard** (v3 #9 + v4 #7) — collect_workspace_stats 함수 단위. `slug=<existing>` → `scanned_slug_count == 1`, `applied_filters.slug == "<existing>"`. `slug=<missing>` → `scanned_slug_count == 0`, `warnings`에 `"slug '<missing>' not found"` 1줄. `slug=None` → fan-out 정상. **path traversal 검증**: `slug="../../etc"` 또는 `slug="a/b"` 또는 `slug=""` → `ValueError` 던짐 (CLI 단에서는 argparse error, core 단에서는 명시적 raise). `os.path.basename(slug) != slug` 거부.

### 8.2 `tests/test_warning_stats_cli.py` (9 케이스)

8. **cli_workspace_required** — `--workspace` 누락 시 argparse SystemExit(2). stderr "the following arguments are required" 포함.
9. **cli_top_truncation_meta** (v4 #9 갱신) — `--top 2` → `projects[]` 길이 == 2, `project_count_returned == 2`, `project_count_total == <full population>`. `totals` / `distribution` / `by_phase_total`은 full population 기준 (truncate 무관). `--top 0` → projects 전체 출력 + total == returned.
10. **cli_export_csv_affected_ids_json** (v4 #2) — fixture record `affected_ids = ["task_a", "task;b", "task,c"]` → CSV row의 `affected_ids` 컬럼이 `json.dumps(...)` 결과 그대로(`["task_a", "task;b", "task,c"]`). `csv.QUOTE_MINIMAL` 자동 quoting 검증. pandas roundtrip: `json.loads(row["affected_ids"]) == [...]` 복원 성공.
11. **cli_export_json_records_format** (#6) — JSON records 모드 wrapper 검증: `schema_version`/`rule_id`/`workspace`/`applied_filters`/`exported_at`/`scanned_slug_count`/`record_count`/`records: [{project_slug, record}, ...]`/`warnings` 필드 모두 존재. record_count == len(records). stdout이 single valid JSON.
12. **cli_export_summary_csv_rejected** (#6) — `--mode summary --format csv` → argparse error (SystemExit(2)). stderr에 "summary mode is incompatible with csv format" 또는 동등 메시지.
13. **cli_slug_filter_and_sanitization** (#11 + v4 #7) — `--slug <existing>` → `applied_filters.slug == "<existing>"`, `scanned_slug_count == 1`. `--slug <missing>` → `scanned_slug_count == 0` + `warnings: ["slug '<missing>' not found"]`. `--slug ../../etc` / `--slug a/b` / `--slug ""` → argparse error (SystemExit(2)).
14. **cli_export_phase_filter** (v4 #5 신규) — `warning-export --mode summary --format json --phase build` → 매칭 record만 records[] 또는 summary에 반영, `applied_filters.phase == "build"`. `--phase` 미지정 시 모든 phase 포함.
15. **cli_export_out_atomic** (v4 #10 신규) — `--out /tmp/out.csv` → 같은 디렉토리에 `<filename>.tmp.<pid>` temp 작성 후 `os.replace`. write 실패 시 (예: parent dir 권한 없음) temp cleanup + nonzero exit + stderr 진단. stdout 모드는 atomic 미적용 (한 번에 stdout flush).
16. **cli_warning_stats_unknown_rule_keeps_data** (v4 #7 v3 처방 검증) — `<existing>/owner_role_mismatch.jsonl`에 record 3건 + `--rule unknown` 호출 → `warnings:`에 `"rule_id 'unknown' not in runtime/warnings/_index.json"` + jsonl scan 진행 (즉 unknown.jsonl이 없으므로 0건이지만 정상 종료). 같은 fixture에 `<existing>/unknown.jsonl`이 있으면 그 데이터 출력.

### 8.3 회귀 검증 (별도 테스트 추가 없이 기존 64 케이스 재실행)

- `test_warning_registry.py` (8) — record/summarize 동작 0 변경 → 모두 PASS 기대.
- `test_warning_registry_cli.py` (4) — `warning-summary/repair/override` 진입점 변경 없음 → PASS.
- `test_escalation_evaluator.py` 등 P2 39 케이스 — evaluator/policy 변경 없음 → PASS.
- **`tests/test_warning_registry_migration_callsites.py` (4)** — **v4 #12 실측 (2026-05-10 기준): `:1401` 리터럴 assertion 0건** — 해당 fixture에는 `source_path="core/project_pipeline.py:757"` 1건만 있음. **fixture 갱신 불필요**. `core/project_pipeline.py:1466` 1줄 정정의 영향 범위 0.

### 8.4 통합 smoke (v1 #10 OS 분기 + v3 #8 hardcode 정정 + v4 #4 retract)

`python build_exe.py` 후 **host OS의 frozen build 1개**를 실행 (cross-OS 빌드는 `build_exe.py`/CI가 결정):

- Windows: `dist/af-1.2.26/af.exe`
- macOS / Linux: `dist/af-1.2.26/af`

다음 3개 명령이 모두 0 exit + ImportError 없음 + stdout single valid JSON:

```
<af> warning-stats --workspace . --rule owner_role_mismatch
<af> warning-stats --workspace . --rule unknown_rule    # warnings에 "rule_id 'unknown_rule' not in runtime/warnings/_index.json" + jsonl 스캔 진행 (v3 #7)
<af> warning-export --workspace . --format csv --rule owner_role_mismatch --out /tmp/out.csv
```

**v4 #4 retract 사실**: `dist/af-1.2.26/_internal/config/warning_registry_index.json` 등 frozen 빌드 packaging 검증은 **불필요** (위치 이동 철회, in-place 갱신).

`<af> warning-stats --workspace <빈 디렉토리>` → `runtime/warnings/_index.json` 부재 → `warnings:`에 "index file not found at runtime/warnings/_index.json" 1줄 + 정상 종료 (`scanned_slug_count: 0`).

추가 사후 검증: `grep -c '1\.2\.25' install-af.ps1` 결과 0 (v3 #5).

---

## §9 Master_Blueprint.md 갱신 포인트

- **§0 빠른 참조**: `core/warning_stats.py` 신규 row 추가.
- **§3.8 Warning Registry**: 절 제목을 "Warning Registry & Stats"로 확장. measurement phase 표 (rule × {activate_at, measure_at, mode}) 추가. CLI 4종 표 (`warning-summary`/`repair`/`override`/`stats`/`export`).
- **§12 변경 이력**: `2026-05-10 v1.2.26 (P3) — owner_role_mismatch 측정 데이터 분석 도구 (warning-stats/export) + _index.json schema v2`.

> CLAUDE.md 의무: Blueprint 업데이트는 **같은 commit**.

---

## §10 Rollback 시나리오

### 10.1 분석 결과 의심 — stats 출력이 이상

- 원인 후보: jsonl 깨짐 / 동시 write race / 분포 계산 버그.
- 1차 진단: `af warning-export --workspace . --rule owner_role_mismatch --format csv --out /tmp/raw.csv` → 사람이 직접 검사.
- 2차: `WarningRegistry.repair(project_slug=...)`로 `_summary.json` 재생성 후 비교.
- 3차: `core/warning_stats.py` 단위 테스트 격리 fixture로 회귀 테스트 작성.

### 10.2 회귀 발생 — P3 PR을 즉시 되돌리고 싶을 때

- **P3 단독 시점에 한해** (#9 ACCEPT — P4 진입 전 한정 단서) P3는 read-only 분석 도구 + `_index.json` in-place 갱신 + `source_path` 1줄 정정만이라 **revert 1 commit으로 완전 복구**.
- record/summarize/evaluate 동작은 P3 PR에 의존하지 않으므로, revert 후에도 P2 빌드와 동일하게 작동.
- `runtime/warnings/_index.json` schema_version 2 → 1로 되돌리는 마이그레이션은 불필요 (어떤 코드도 schema_version을 읽지 않음 — 메타데이터).
- `source_path` 1줄 정정 (`core/project_pipeline.py:1466` 리터럴 `:1401` → `:1455`)도 revert 시 `:1401`로 복귀 — record 스키마/dedup에 영향 0.
- v4 #4 retract 효과: `_index.json` 위치 이동/삭제 row가 PR scope에서 빠졌으므로 `git checkout runtime/warnings/_index.json` 단일 파일로 복구 (`.gitignore` 화이트리스트 변경 없음).
- **P4 진입 후**에는 본 rollback 정책이 깨질 수 있다 (P4 evaluator가 `measure_at`/`mode` 키를 읽기 시작하면). 그 시점의 revert 전략은 **P4 설계문서에 위임**한다.

### 10.3 P4로 진입할 때 폐기물

- `_index.json.measure_at` / `mode`는 P4에서 그대로 둬도 무해 (메타데이터). P4 PR에서 `mode: enforcement`로 토글하거나 `measure_at` 제거 — P4 설계 시점에 결정.

---

## §11 자기검증 체크리스트 (v2 cross-review 진입 전)

### 11.1 baseline / 구조

- [x] §1.1 모든 baseline grep은 실측 (Read tool로 확인) — 추가로 `_record_ledger_outcomes`가 `crashed/unknown` 외 모든 status에서 호출됨을 `core/project_pipeline.py:1331`에서 직접 확인.
- [x] §3.2 변경 파일 목록과 §7 PR 순서 일치. v1 대비 추가된 변경: `core/project_pipeline.py:1466` 1줄 (#1, callsite `:1455`로 정정), `runtime/warnings/_index.json` **in-place 갱신** (v4 #4 retract — config/ 이동 철회), `af.spec` hiddenimports 1줄 (datas 추가 없음). CLI dispatch dict 명칭은 `_STAGE1_DISPATCH` (v3 #2 baseline 정정).
- [x] §3.3 `ProjectStats.count` docstring = "sum of WarningRecord.count across records" (#7 정정).
- [x] §3.5 + iter_warning_records: `os.scandir` + `is_dir() + not startswith("_")` 명시 (#8). 이는 `runtime/warnings/_index.json` 삭제 후에도 `_summary.json`/`_overrides.json`/`_decision.json` 등 메타파일 자동 제외 보장.

### 11.2 시맨틱 / 출력 계약

- [x] §0.1 + §3.2 P3 동작에서 BLOCK semantics 변경 0 명시 (`evaluate()` 미import).
- [x] §6.5 yaml 미변경 + evaluator 미import 명시 (회귀 면적 0).
- [x] §4.4 stdout 단일 JSON 계약 — 모든 휴먼 경고는 `warnings: []` 필드 (#5).
- [x] §3.4 `by_per_record_count` 차원 추가 — P4 `repeat_count_min` 임계 결정 직결 (#4).
- [x] §3.3 + §4.5 + §5.1 `--phase`는 record-level filter, `--slug`은 directory filter — 시맨틱 명시 + `applied_filters` 필드로 출력에 흔적 남김 (#2 + #11).
- [x] §6.4 source 정정 채널 2곳 동시 정정 — `core/project_pipeline.py:1466` 리터럴 (`:1401` → `:1455`) + `warning_registry_index.json.source` 메타데이터 (#1 + v3 #4).

### 11.3 안전성 / rollback

- [x] §3.5 read 안전성 (동시 write 시 마지막 라인 skip + `_summary.json` 미터치 — read-only 보장).
- [x] §10.2 rollback이 1 commit revert로 완결 (#9 "P3 단독 시점에 한해" 단서 명시 — P4 진입 후는 P4에 위임).
- [x] §6.6 frozen 빌드 packaging — `_load_index` `sys._MEIPASS` 우선 + `BASE_DIR` fallback (#3).

### 11.4 비용 / 성공기준

- [x] Karpathy rule #2 simplicity: 신규 코드 ~170 + 테스트 ~370 ≈ 540 LOC. 외부 lib 0개 추가 (math/statistics/csv/json 표준만). v4 retract로 PR 변경 파일 11 → 8개로 단순화.
- [x] Karpathy rule #3 surgical: P3 PR에서 `core/warning_registry.py` 등 핵심 모듈 0줄 변경. `core/project_pipeline.py`는 1줄 (source_path 리터럴). v4 #4 retract로 `af.spec datas` / `.gitignore` / `config/` 신규 파일 / `runtime/warnings/_index.json` 삭제 4건 추가 변경 면적 0.
- [x] Karpathy rule #4 goal-driven: 성공 기준 = "stats 출력 JSON에서 P4 임계값 결정 회의 1회 진행 가능 — `by_per_record_count.median/p95`/`by_project_repeat_count_max.median/p95`/`by_phase_total` 4 차원으로 임계 결정".
- [x] 멀티-OS 빌드 명시 (#10) — host OS 1개 smoke로 충분 (cross-OS 빌드 행렬은 build_exe.py가 결정).

### 11.5 v1 대비 추가 검증 (cross-review 12 finding 흡수 확인)

| # | finding | v2 반영 위치 |
|---|---------|--------------|
| 1 | source_path zero-change 자기모순 | §3.2 row + §6.4 + §11.2 |
| 2 | --phase 시맨틱 미결 | §3.3 docstring + §4.1 인자표 + §4.3.1 예시 + §4.5 검증 + §8.1 case 5 |
| 3 | _index.json 패키징 미정의 | §6.0 위치 결정 + §6.6 packaging + §3.2 row + §7 #6,#7,#8 |
| 4 | by_per_record_count 차원 | §3.3 distribution + §3.4 모집단 정의 + §4.3 예시 + §8.1 case 2,3 |
| 5 | stdout JSON 무결성 | §4.4 단일 JSON 계약 + §3.3 warnings 필드 + 모든 §4.x 예시 |
| 6 | export 계약 + iterator 공유 | §3.3 iter_warning_records + §5.1 명시 + §5.3 wrapper + §8.2 case 10,11 |
| 7 | docstring 정정 | §3.3 ProjectStats.count |
| 8 | slug dir filter | §3.5 + iter_warning_records 명세 + §8.1 case 6 |
| 9 | revert 단서 | §10.2 |
| 10 | OS 분기 | §8.4 |
| 11 | --slug 추가 | §3.3 + §4.1 + §5.1 + §8.2 case 12 |
| 12 | install-af.ps1 | §7 #10 (8곳 일괄) |
| 13 | summarize 회피 우려 (REJECT) | §3.5 + §11.3 read-only 보장으로 정당화 유지 |

### 11.6 v3 cross-review (2026-05-10 08:23) BLOCK 9 + HOLD 1 흡수 확인

| v3 # | finding | 본문 위치 |
|------|---------|-----------|
| v3 #1 | `_index.json` 위치 이동 §3.2/§7/§10 본문 통일 | §3.1 다이어그램 + §3.2 row + §7 row + §10.2 |
| v3 #2 | CLI dispatch `_HANDLERS` → `_STAGE1_DISPATCH` | §3.2 row 2 + §11.1 |
| v3 #3 | §3.2 self-contradiction (project_pipeline.py 변경 명시) | §3.2 row 5 + footer 분리 명시 |
| v3 #4 | source line 1454 → 1455 (callsite) | §6.2 + §6.4 + §3.2 + §7 + §8.3 + §10.2 + §11.1 |
| v3 #5 | install-af.ps1 §3.2/§7 "8곳" + 사후 검증 | §3.2 row + §7 row + §8.4 |
| v3 #6 | §8.1 case 5 wording rewrite | §8.1 case 5 |
| v3 #7 | unknown rule "0건 반환" → jsonl 스캔 진행 | §4.5 |
| v3 #8 | §8.4 frozen smoke `af.exe` hardcode 정정 | §8.4 + §6.6 |
| v3 #9 | §8.1에 `--slug` core 단위 케이스 추가 | §8.1 case 7 (신설) |
| v3 #10 (HOLD) | schema_version bump P3에 reader 안 추가, P4로 미룸 | §6.5.1 |

> v3 critic이 R1~R5로 false-positive로 분류한 항목들 (`--slug`/`by_per_record_count`/`iter_warning_records`/median rule)은 v2에서 이미 반영됐으며 v3 본문 그대로 유지.

### 11.7 v4 cross-review (2026-05-10 08:40) BLOCK 12 사용자 처방 흡수 확인

| v4 # | finding | 본문 위치 |
|------|---------|-----------|
| v4 #1 | §7 row 3 `_STAGE1_DISPATCH` (false-positive — v3 정정 확인) | §7 line 555 + §11.1 |
| v4 #2 | CSV `affected_ids` `\;` → `json.dumps()` | §5.2 + §8.2 case 10 |
| v4 #3 | warnings 채널 단일화 (collect 항상 list 반환, stderr 부가) | §3.5 + §4.4 + §8.1 case 6 + §8.2 |
| v4 #4 | `_load_index` side-effect 제거 + **v3 #1 config/ 이동 retract** | §6.0 + §6.6 + §3.2 + §7 + §0.1 + §3.1 + §10.2 |
| v4 #5 | `warning-export --phase` 시그니처 추가 | §5.1 + §5.4 + §8.2 case 14 |
| v4 #6 | `first_ts`/`last_ts` 시맨틱 명시 + 0-record drop | §3.3 ProjectStats |
| v4 #7 | `--slug` path traversal 방어 | §4.5 + §5.1 + §8.1 case 7 + §8.2 case 13 |
| v4 #8 | median 강제 float | §3.4 + §4.3 예시 |
| v4 #9 | `--top` truncation 범위 + project_count_total/returned 메타 | §4.1 + §3.3 dict + §4.3 + §8.2 case 9 |
| v4 #10 | `--out` atomic write | §5.1 + §5.4 + §8.2 case 15 |
| v4 #11 | changelog wording "P3 scope 제외, P4 재평가" | §6.5.1 |
| v4 #12 | `:1401` 0건 실측 사실 박음 | §6.4 + §8.3 |

> v4 critic R1~R4 false-positive: `_STAGE1_DISPATCH` 정정 (이미 v3에서 처리), schema_version 필드명 중복 (위치 다름), source `:1455` 일관성 (canonical 정정 완료), af.spec datas 중복 entry (v4 #4 retract로 무관).

---

## §12 cross-review 안내

- 본 v4는 cross-review v1 (WARN, 12 finding) + v3 (BLOCK, 10 finding, hook 자동 발화) + v4 (BLOCK, 12 finding, hook 자동 발화) 누계 흡수 후 산출.
- CLAUDE.md max_rounds=2 캡 명목상 도달이지만 hook이 추가 발화 가능. 사용자 결정 (2026-05-10): v4 ACCEPT 12건 처방 그대로 흡수 후 **추가 cross-review 없이 구현 진입** — §7 PR 변경 파일 8개 순서대로 구현, §8 16 케이스 PASS + 기존 64 케이스 회귀 PASS + §8.4 frozen smoke + 사후 grep 검증 후 머지.
- 본 v4가 다음 hook 자동 발화로 또 BLOCK이 떠도 (가능성 있음 — review 자체가 완벽치 않으니), 본문 정합성 자체는 사용자 처방대로이므로 구현 진입을 막지 않는다.
