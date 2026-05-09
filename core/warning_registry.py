"""Warning Registry — P1 패키지.

SoT: <workspace>/runtime/warnings/<slug>/<rule_id>.jsonl (append-only)
Cache: <workspace>/runtime/warnings/<slug>/_summary.json (read-on-demand)
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field

from core.file_lock import locked_file
from core.utils import now_iso

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
        """_summary.json을 SoT 풀스캔으로 재계산해 원자적 write 후 반환."""
        slug_dir = os.path.join(self.warnings_root, project_slug)
        os.makedirs(slug_dir, exist_ok=True)
        summary_path = os.path.join(slug_dir, "_summary.json")
        summary_lock_path = os.path.join(slug_dir, "_summary.json.lock")

        with locked_file(summary_lock_path, timeout=10):
            summary = _build_summary(project_slug, slug_dir)
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


def _build_summary(project_slug: str, slug_dir: str) -> dict:
    """slug_dir의 모든 <rule_id>.jsonl을 스캔해 by_rule + by_phase 집계."""
    by_rule: dict[str, dict] = {}
    by_severity: dict[str, int] = {"warn": 0, "block_candidate": 0, "block": 0}

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

                    if rid not in by_rule:
                        by_rule[rid] = {
                            "count": 0,
                            "first_ts": ts,
                            "last_ts": ts,
                            "severity": sev,
                            "by_phase": {},
                        }
                    entry = by_rule[rid]
                    entry["count"] += cnt
                    if ts < entry["first_ts"]:
                        entry["first_ts"] = ts
                    if ts > entry["last_ts"]:
                        entry["last_ts"] = ts
                        entry["severity"] = sev
                    if phase:
                        entry["by_phase"][phase] = entry["by_phase"].get(phase, 0) + cnt

                    by_severity[sev] = by_severity.get(sev, 0) + cnt

    return {
        "project_slug": project_slug,
        "last_updated": now_iso(),
        "by_rule": by_rule,
        "by_severity": by_severity,
    }
