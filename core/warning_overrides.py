"""Warning Overrides — rule-level false-positive override 관리.

P2: scope="rule" (rule 전체 override)만 지원.
P4: scope="record" / scope="phase" 확장.
"""
from __future__ import annotations

import json
import os
import tempfile

from core.file_lock import locked_file
from core.utils import now_iso


def overrides_path(workspace: str, slug: str) -> str:
    return os.path.join(
        os.path.abspath(workspace), "runtime", "warnings", slug, "_overrides.json"
    )


def load_overrides(workspace: str, slug: str) -> dict:
    """_overrides.json 로드. 파일 부재 → 빈 dict, 손상 → RuntimeError."""
    path = overrides_path(workspace, slug)
    if not os.path.isfile(path):
        return {"schema_version": 1, "overrides": []}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"_overrides.json corrupt at {path}: {exc}") from exc


def upsert_override(workspace: str, slug: str, rule_id: str, reason: str) -> None:
    """override 추가 또는 갱신 — locked_file + atomic replace."""
    path = overrides_path(workspace, slug)
    lock_path = path + ".lock"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked_file(lock_path, timeout=10):
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"_overrides.json corrupt — repair before upsert: {exc}"
                ) from exc
        else:
            data = {"schema_version": 1, "overrides": []}

        # 동일 rule_id 중복 제거 후 upsert
        data["overrides"] = [
            e for e in data.get("overrides", [])
            if e.get("rule_id") != rule_id
        ]
        data["overrides"].append({
            "rule_id": rule_id,
            "reason": reason,
            "ts": now_iso(),
            "scope": "rule",
        })
        _atomic_write(path, data)


def remove_override(workspace: str, slug: str, rule_id: str) -> None:
    """override 제거 — locked_file + atomic replace."""
    path = overrides_path(workspace, slug)
    lock_path = path + ".lock"
    if not os.path.isfile(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with locked_file(lock_path, timeout=10):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"_overrides.json corrupt — repair before remove: {exc}"
            ) from exc
        data["overrides"] = [
            e for e in data.get("overrides", [])
            if e.get("rule_id") != rule_id
        ]
        _atomic_write(path, data)


def is_overridden(overrides: dict, rule_id: str) -> bool:
    """overrides dict에서 rule_id가 override됐는지 확인."""
    for entry in overrides.get("overrides") or []:
        if entry.get("rule_id") == rule_id:
            return True
    return False


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _atomic_write(path: str, data: dict) -> None:
    slug_dir = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=slug_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
