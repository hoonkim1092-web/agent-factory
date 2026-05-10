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
import statistics
from dataclasses import asdict, dataclass
from typing import Iterator


@dataclass
class ProjectStats:
    project_slug: str
    count: int          # sum of WarningRecord.count across records (per-run count 누적)
    record_lines: int   # jsonl 라인 수 (count와 별개 — repeat/dedup 검증용)
    repeat_count_max: int
    by_phase: dict      # 매칭 record(phase filter 적용 후)의 phase별 count 누적
    first_ts: str       # ts가 있는 record만 ISO lexical min, 전부 누락이면 ""
    last_ts: str        # ts가 있는 record만 ISO lexical max, 전부 누락이면 ""


@dataclass
class Distribution:
    n: int
    min: int
    median: float
    p95: int      # nearest-rank 정수 (§3.4: 정수 필드는 정수로 직렬화)
    max: int


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


def _validate_slug(slug: str) -> None:
    """path traversal 방어. 위반 시 ValueError."""
    if not slug or "/" in slug or "\\" in slug or ".." in slug:
        raise ValueError(f"invalid slug: {slug!r}")
    if os.path.basename(slug) != slug:
        raise ValueError(f"invalid slug: {slug!r}")


def _compute_distribution(values: list[int]) -> Distribution | None:
    """nearest-rank p95, median은 항상 float 강제."""
    n = len(values)
    if n == 0:
        return None
    sorted_vals = sorted(values)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    med = float(statistics.median(sorted_vals))
    p95_idx = math.ceil(0.95 * n) - 1
    p95_val = sorted_vals[p95_idx]
    return Distribution(n=n, min=min_val, median=med, p95=p95_val, max=max_val)


def iter_warning_records(
    workspace: str,
    *,
    rule_id: str = "owner_role_mismatch",
    slug: str | None = None,
) -> Iterator[tuple[str, dict | None, str | None]]:
    """
    Yields (project_slug, record_dict) for every parseable jsonl line.

    - slug 디렉토리 필터: os.scandir + entry.is_dir() + not name.startswith("_")
    - slug 인자 지정 시 해당 slug만 yield (단일 디렉토리만 scan).
    - jsonl 미존재 → 해당 slug skip (예외 X).
    - JSONDecodeError 라인 → skip (caller가 warnings에 append).
    - workspace/runtime/warnings/ 자체 부재 → 빈 iterator.

    Yields: (slug_str, record_dict, None) for valid lines
            (slug_str, None, "malformed line in <path>:<lineno>") for bad lines
    실제로는 tuple[str, dict | None, str | None] 형태이지만,
    collect_workspace_stats / export가 None 체크로 분기.
    """
    warnings_root = os.path.join(os.path.abspath(workspace), "runtime", "warnings")
    if not os.path.isdir(warnings_root):
        return

    if slug is not None:
        _validate_slug(slug)
        slug_dir = os.path.join(warnings_root, slug)
        if os.path.isdir(slug_dir):
            entries = [slug_dir]
            entry_names = [slug]
        else:
            return
    else:
        entries = []
        entry_names = []
        try:
            with os.scandir(warnings_root) as it:
                for entry in it:
                    if entry.is_dir() and not entry.name.startswith("_"):
                        entries.append(entry.path)
                        entry_names.append(entry.name)
        except OSError:
            return

    for slug_name, slug_path in zip(entry_names, entries):
        jsonl_path = os.path.join(slug_path, f"{rule_id}.jsonl")
        if not os.path.isfile(jsonl_path):
            continue
        try:
            with open(jsonl_path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        yield (slug_name, record, None)
                    except json.JSONDecodeError:
                        rel = os.path.join(slug_name, f"{rule_id}.jsonl")
                        yield (slug_name, None, f"malformed line in {rel}:{lineno}")
        except OSError:
            continue


def collect_workspace_stats(
    workspace: str,
    *,
    rule_id: str = "owner_role_mismatch",
    slug: str | None = None,
    phase: str | None = None,
    top: int = 10,
) -> dict:
    """
    워크스페이스 전체 fan-out 통계.

    Returns dict with schema_version, rule_id, workspace, applied_filters,
    scanned_slug_count, project_count_total, project_count_returned,
    projects[], totals, distribution, by_phase_total, by_phase_total_unfiltered,
    warnings[].
    """
    if slug is not None:
        _validate_slug(slug)

    abs_workspace = os.path.abspath(workspace)
    result_warnings: list[str] = []

    # index 검증
    index_data = _load_index(workspace)
    if index_data is None:
        result_warnings.append("index file not found at runtime/warnings/_index.json")
    else:
        registered_ids = {r.get("rule_id") for r in index_data.get("rules", [])}
        if rule_id not in registered_ids:
            result_warnings.append(
                f"rule_id '{rule_id}' not in runtime/warnings/_index.json"
            )

    # slug 디렉토리 수집 (scanned_slug_count 계산용)
    warnings_root = os.path.join(abs_workspace, "runtime", "warnings")
    if not os.path.isdir(warnings_root):
        result_warnings.append("no slug directories under runtime/warnings/")
        return {
            "schema_version": 1,
            "rule_id": rule_id,
            "workspace": abs_workspace,
            "applied_filters": {"slug": slug, "phase": phase},
            "scanned_slug_count": 0,
            "project_count_total": 0,
            "project_count_returned": 0,
            "projects": [],
            "totals": {"count": 0, "record_lines": 0},
            "distribution": None,
            "by_phase_total": {},
            "by_phase_total_unfiltered": {},
            "warnings": result_warnings,
        }

    if slug is not None:
        slug_dir = os.path.join(warnings_root, slug)
        if os.path.isdir(slug_dir):
            scanned_slug_count = 1
        else:
            scanned_slug_count = 0
            result_warnings.append(f"slug '{slug}' not found")
            return {
                "schema_version": 1,
                "rule_id": rule_id,
                "workspace": abs_workspace,
                "applied_filters": {"slug": slug, "phase": phase},
                "scanned_slug_count": 0,
                "project_count_total": 0,
                "project_count_returned": 0,
                "projects": [],
                "totals": {"count": 0, "record_lines": 0},
                "distribution": None,
                "by_phase_total": {},
                "by_phase_total_unfiltered": {},
                "warnings": result_warnings,
            }
    else:
        scanned_slug_count = 0
        try:
            with os.scandir(warnings_root) as it:
                for entry in it:
                    if entry.is_dir() and not entry.name.startswith("_"):
                        scanned_slug_count += 1
        except OSError:
            pass

    # record 수집
    project_map: dict[str, dict] = {}  # slug -> {count, record_lines, repeat_count_max, by_phase, ts_list, per_record_counts}
    by_phase_total: dict[str, int] = {}
    by_phase_total_unfiltered: dict[str, int] = {}
    per_record_counts: list[int] = []

    for slug_name, record, err_msg in iter_warning_records(workspace, rule_id=rule_id, slug=slug):
        if err_msg is not None:
            result_warnings.append(err_msg)
            continue

        rec_count = int(record.get("count", 1))
        rec_phase = record.get("affected_phase", "")
        rec_ts = record.get("ts", "")

        # unfiltered by_phase 집계 (phase filter 무관)
        if rec_phase:
            by_phase_total_unfiltered[rec_phase] = by_phase_total_unfiltered.get(rec_phase, 0) + rec_count

        # phase filter 적용
        if phase is not None and rec_phase != phase:
            continue

        # matching record 집계
        if rec_phase:
            by_phase_total[rec_phase] = by_phase_total.get(rec_phase, 0) + rec_count

        per_record_counts.append(rec_count)

        if slug_name not in project_map:
            project_map[slug_name] = {
                "count": 0,
                "record_lines": 0,
                "repeat_count_max": 0,
                "by_phase": {},
                "ts_list": [],
            }
        proj = project_map[slug_name]
        proj["count"] += rec_count
        proj["record_lines"] += 1
        if rec_count > proj["repeat_count_max"]:
            proj["repeat_count_max"] = rec_count
        if rec_phase:
            proj["by_phase"][rec_phase] = proj["by_phase"].get(rec_phase, 0) + rec_count
        if rec_ts:
            proj["ts_list"].append(rec_ts)

    # ProjectStats 구성 (0-record slug 제외)
    project_stats: list[ProjectStats] = []
    for pslug, pdata in project_map.items():
        if pdata["count"] == 0 and pdata["record_lines"] == 0:
            continue
        ts_list = pdata["ts_list"]
        first_ts = min(ts_list) if ts_list else ""
        last_ts = max(ts_list) if ts_list else ""
        project_stats.append(ProjectStats(
            project_slug=pslug,
            count=pdata["count"],
            record_lines=pdata["record_lines"],
            repeat_count_max=pdata["repeat_count_max"],
            by_phase=pdata["by_phase"],
            first_ts=first_ts,
            last_ts=last_ts,
        ))

    # 정렬: count 내림차순, 동률 시 slug ASC
    project_stats.sort(key=lambda p: (-p.count, p.project_slug))

    project_count_total = len(project_stats)

    # top truncation (projects[]만)
    if top > 0:
        projects_out = project_stats[:top]
    else:
        projects_out = project_stats
    project_count_returned = len(projects_out)

    # totals — full population 기준
    total_count = sum(p.count for p in project_stats)
    total_record_lines = sum(p.record_lines for p in project_stats)

    # distribution — full population 기준
    by_project_count_vals = [p.count for p in project_stats]
    by_project_repeat_vals = [p.repeat_count_max for p in project_stats]

    dist_by_project_count = _compute_distribution(by_project_count_vals)
    dist_by_project_repeat = _compute_distribution(by_project_repeat_vals)
    dist_by_per_record = _compute_distribution(per_record_counts)

    if dist_by_project_count is not None and dist_by_project_count.n < 20:
        result_warnings.append(f"n={dist_by_project_count.n}, p95 may be unstable for n<20")

    def dist_to_dict(d: Distribution | None) -> dict | None:
        if d is None:
            return None
        return asdict(d)

    distribution: dict | None
    if dist_by_project_count is None and dist_by_project_repeat is None and dist_by_per_record is None:
        distribution = None
    else:
        distribution = {
            "by_project_count": dist_to_dict(dist_by_project_count),
            "by_project_repeat_count_max": dist_to_dict(dist_by_project_repeat),
            "by_per_record_count": dist_to_dict(dist_by_per_record),
        }

    return {
        "schema_version": 1,
        "rule_id": rule_id,
        "workspace": abs_workspace,
        "applied_filters": {"slug": slug, "phase": phase},
        "scanned_slug_count": scanned_slug_count,
        "project_count_total": project_count_total,
        "project_count_returned": project_count_returned,
        "projects": [asdict(p) for p in projects_out],
        "totals": {"count": total_count, "record_lines": total_record_lines},
        "distribution": distribution,
        "by_phase_total": by_phase_total,
        "by_phase_total_unfiltered": by_phase_total_unfiltered,
        "warnings": result_warnings,
    }
