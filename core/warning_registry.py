"""Warning Registry — P2 패키지.

SoT: <workspace>/runtime/warnings/<slug>/<rule_id>.jsonl (append-only)
Cache: <workspace>/runtime/warnings/<slug>/_summary.json (read-on-demand)
Decision: <workspace>/runtime/warnings/<slug>/_decision.json (P2)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field

from core.file_lock import locked_file
from core.utils import now_iso

_LOGGER = logging.getLogger(__name__)

_PHASE_ORDER = {"scope", "build", "integrate", "code_review", "cross_validate", "verify"}

_PHASE_ALIAS: dict[str, str] = {
    "design": "scope",
    "test": "verify",
    "integration": "integrate",
}


def _normalize_phase(raw: str) -> tuple[str, str | None]:
    """(canonical_phase, original_if_aliased). 빈값은 그대로 반환."""
    if not raw:
        return "", None
    if raw in _PHASE_ORDER:
        return raw, None
    if raw in _PHASE_ALIAS:
        return _PHASE_ALIAS[raw], raw
    return "build", raw


def _hash8(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()[:8]


@dataclass
class WarningRecord:
    # Identity (필수)
    rule_id: str
    severity: str
    project_slug: str
    ts: str
    record_id: str
    schema_version: int = 1

    # Localization (필수)
    affected_phase: str = ""
    count: int = 1

    # Escalation 입력 (선택)
    repeat_count: int = 1
    baseline_delta: float = 0.0
    false_positive_override: bool = False
    rationale: str = ""

    # Diagnostic payload (선택)
    affected_ids: list[str] = field(default_factory=list)
    source_path: str = ""
    extra: dict = field(default_factory=dict)


class WarningRegistry:
    def __init__(self, workspace: str) -> None:
        if not workspace:
            raise ValueError(
                "WarningRegistry requires explicit workspace; cwd/doc_root fallback forbidden"
            )
        self.workspace = os.path.abspath(workspace)
        self.warnings_root = os.path.join(self.workspace, "runtime", "warnings")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(
        self,
        *,
        project_slug: str,
        rule_id: str,
        affected_phase: str = "",
        count: int = 1,
        severity: str = "warn",
        rationale: str = "",
        affected_ids: list[str] | None = None,
        source_path: str = "",
        extra: dict | None = None,
        baseline_delta: float = 0.0,
        false_positive_override: bool = False,
    ) -> None:
        """jsonl SoT append. _summary는 건드리지 않음 (read-on-demand 단일화)."""
        if affected_ids is None:
            affected_ids = []
        if extra is None:
            extra = {}

        canonical_phase, original_phase = _normalize_phase(affected_phase)
        extra_final = dict(extra)
        if original_phase is not None:
            extra_final["original_phase"] = original_phase

        stable_payload = json.dumps(
            {
                "rule_id": rule_id,
                "affected_phase": canonical_phase,
                "count": count,
                "affected_ids": sorted(affected_ids),
                "source_path": source_path,
                "extra": {
                    k: v for k, v in extra_final.items() if k != "original_phase"
                },
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        record_id = f"{project_slug}:{rule_id}:{_hash8(stable_payload)}"

        slug_dir = os.path.join(self.warnings_root, project_slug)
        os.makedirs(slug_dir, exist_ok=True)

        jsonl_path = os.path.join(slug_dir, f"{rule_id}.jsonl")

        with locked_file(jsonl_path, timeout=5):
            # dedup: same record_id → skip
            existing_ids: set[str] = set()
            if os.path.isfile(jsonl_path):
                with open(jsonl_path, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            r = json.loads(line)
                            existing_ids.add(r.get("record_id", ""))
                        except json.JSONDecodeError:
                            pass
            if record_id in existing_ids:
                return

            # repeat_count: SoT 풀스캔 (all rule files for this slug)
            repeat_count = _count_rule_records(slug_dir, rule_id) + 1

            rec = WarningRecord(
                rule_id=rule_id,
                severity=severity,
                project_slug=project_slug,
                ts=now_iso(),
                record_id=record_id,
                affected_phase=canonical_phase,
                count=count,
                repeat_count=repeat_count,
                baseline_delta=baseline_delta,
                false_positive_override=false_positive_override,
                rationale=rationale,
                affected_ids=affected_ids,
                source_path=source_path,
                extra=extra_final,
            )
            with open(jsonl_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

    def summarize(self, *, project_slug: str) -> dict:
        """_summary.json을 SoT 풀스캔으로 재계산해 원자적 write 후 반환.

        P2: 끝에서 decision report 작성 (fail-closed). import 실패도 fail-closed.
        """
        slug_dir = os.path.join(self.warnings_root, project_slug)
        os.makedirs(slug_dir, exist_ok=True)
        summary_path = os.path.join(slug_dir, "_summary.json")
        summary_lock_path = os.path.join(slug_dir, "_summary.json.lock")

        with locked_file(summary_lock_path, timeout=10):
            try:
                summary = _build_summary(project_slug, slug_dir)
            except Exception as exc:
                _LOGGER.error("_build_summary failed — fail-closed: %s", exc)
                _write_minimal_block_decision(
                    slug_dir, project_slug=project_slug,
                    summary_last_updated=now_iso(),
                    error_repr=repr(exc),
                )
                raise
            # P2: escalation_phase 마커 도입
            summary["escalation_phase"] = "P2"

            payload = json.dumps(summary, ensure_ascii=False, indent=2)
            fd, tmp = tempfile.mkstemp(dir=slug_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(payload)
                os.replace(tmp, summary_path)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise

            # P2: decision report (fail-closed — import 실패도 차단 처리)
            try:
                from core.escalation_evaluator import (  # noqa: PLC0415
                    compute_run_decision, load_policy,
                )
                from core.escalation_decision_report import (  # noqa: PLC0415
                    write_decision_report, write_error_decision,
                )
                decision = compute_run_decision(
                    summary, load_policy(), current_phase="P2"
                )
                write_decision_report(
                    decision, slug_dir,
                    summary_last_updated=summary["last_updated"],
                )
            except Exception as exc:
                _LOGGER.error("decision evaluator failure — fail-closed: %s", exc)
                try:
                    from core.escalation_decision_report import write_error_decision  # noqa: PLC0415
                    write_error_decision(
                        slug_dir, project_slug=project_slug,
                        summary_last_updated=summary["last_updated"],
                        error_repr=repr(exc),
                    )
                except Exception:
                    _write_minimal_block_decision(
                        slug_dir, project_slug=project_slug,
                        summary_last_updated=summary["last_updated"],
                        error_repr=repr(exc),
                    )

        return summary

    def load_global(self, *, rule_id: str) -> list[dict]:
        """P1 stub — global aggregation은 P4에서 활성."""
        raise NotImplementedError("global aggregation activates at P4")

    def rebuild_caches(self, *, project_slug: str) -> None:
        """SoT로부터 _summary.json 재생성. summarize()와 동일."""
        self.summarize(project_slug=project_slug)

    def repair(self, *, project_slug: str) -> None:
        """SoT로부터 _summary.json 재생성 (CLI repair 진입점)."""
        self.summarize(project_slug=project_slug)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _count_rule_records(slug_dir: str, rule_id: str) -> int:
    """slug_dir의 <rule_id>.jsonl에 있는 record 수 반환."""
    jsonl_path = os.path.join(slug_dir, f"{rule_id}.jsonl")
    if not os.path.isfile(jsonl_path):
        return 0
    count = 0
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                count += 1
    return count


def _write_minimal_block_decision(
    slug_dir: str,
    *,
    project_slug: str,
    summary_last_updated: str,
    error_repr: str,
) -> None:
    """write_error_decision import도 실패한 극단 케이스용 최소 _decision.json."""
    payload = {
        "decision_schema_version": 1,
        "project_slug": project_slug,
        "last_updated": now_iso(),
        "generated_from_summary_last_updated": summary_last_updated,
        "escalation_phase": "P2",
        "block": True,
        "blocking_rules": [],
        "reason": "evaluator_import_error",
        "error": error_repr,
    }
    path = os.path.join(slug_dir, "_decision.json")
    fd, tmp = tempfile.mkstemp(dir=slug_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _build_summary(project_slug: str, slug_dir: str) -> dict:
    """slug_dir의 모든 <rule_id>.jsonl을 스캔해 by_rule + by_phase 집계.

    P2 추가: any_override + repeat_count_max 두 필드.
    """
    by_rule: dict[str, dict] = {}
    by_severity: dict[str, int] = {"warn": 0, "block_candidate": 0, "block": 0}

    # P2: _overrides.json에서 override 상태 로드 (slug_dir의 _overrides.json 직접 읽기)
    overridden_rules: set[str] = set()
    overrides_file = os.path.join(slug_dir, "_overrides.json")
    if os.path.isfile(overrides_file):
        try:
            with open(overrides_file, encoding="utf-8") as _of:
                _od = json.load(_of)
            for entry in _od.get("overrides") or []:
                rid = entry.get("rule_id")
                if rid:
                    overridden_rules.add(rid)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"_overrides.json corrupt: {exc}") from exc

    if not os.path.isdir(slug_dir):
        pass
    else:
        for fname in os.listdir(slug_dir):
            if not fname.endswith(".jsonl"):
                continue
            jsonl_path = os.path.join(slug_dir, fname)
            with open(jsonl_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    rid = r.get("rule_id", fname[:-6])
                    sev = r.get("severity", "warn")
                    cnt = r.get("count", 1)
                    phase = r.get("affected_phase", "")
                    ts = r.get("ts", "")
                    repeat_cnt = r.get("repeat_count", 1)

                    if rid not in by_rule:
                        by_rule[rid] = {
                            "count": 0,
                            "first_ts": ts,
                            "last_ts": ts,
                            "severity": sev,
                            "by_phase": {},
                            "repeat_count_max": repeat_cnt,
                            "any_override": rid in overridden_rules,
                        }
                    entry = by_rule[rid]
                    entry["count"] += cnt
                    if ts < entry["first_ts"]:
                        entry["first_ts"] = ts
                    if ts > entry["last_ts"]:
                        entry["last_ts"] = ts
                        entry["severity"] = sev
                    if repeat_cnt > entry["repeat_count_max"]:
                        entry["repeat_count_max"] = repeat_cnt
                    if phase:
                        entry["by_phase"][phase] = entry["by_phase"].get(phase, 0) + cnt

                    by_severity[sev] = by_severity.get(sev, 0) + cnt

    return {
        "project_slug": project_slug,
        "last_updated": now_iso(),
        "by_rule": by_rule,
        "by_severity": by_severity,
    }
