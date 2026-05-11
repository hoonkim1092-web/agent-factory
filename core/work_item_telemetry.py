"""Work-item 생성 텔레메트리 — T1 retry atomic update."""
from __future__ import annotations

import json
import os
import tempfile

from core.continuity.runtime_paths import workspace_runtime_dir
from core.file_lock import locked_file


def update_t1_refine_attempts(workspace: str, slug: str, doc_name: str, increment: int = 1) -> None:
    """T1 retry 발생 시 텔레메트리 파일의 해당 doc 컬럼을 atomic 증가."""
    tele_dir = workspace_runtime_dir(workspace) / "work_item_telemetry"
    tele_dir.mkdir(parents=True, exist_ok=True)
    tele_path = tele_dir / f"{slug}.json"

    with locked_file(str(tele_path), timeout=5):
        data = {}
        if tele_path.exists():
            try:
                data = json.loads(tele_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        docs = data.setdefault("docs", {})
        doc_entry = docs.setdefault(doc_name, {})
        doc_entry["t1_refine_attempts"] = int(doc_entry.get("t1_refine_attempts", 0)) + increment

        payload = json.dumps(data, ensure_ascii=False, indent=2)
        fd, tmp = tempfile.mkstemp(dir=str(tele_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, str(tele_path))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def write_initial_record(workspace: str, slug: str, results: list) -> None:
    """DocGenerationResult 리스트를 텔레메트리 파일에 atomic 기록 (초기 dump)."""
    tele_dir = workspace_runtime_dir(workspace) / "work_item_telemetry"
    tele_dir.mkdir(parents=True, exist_ok=True)
    tele_path = tele_dir / f"{slug}.json"

    data: dict = {"docs": {}}
    for r in results:
        data["docs"][r.doc_type] = {
            "elapsed_sec": r.elapsed_sec,
            "used_fallback": r.used_fallback,
            "timeout_fallback": r.timeout_fallback,
            "placeholder_refine_attempts": r.placeholder_refine_attempts,
            "provider_id": r.provider_id,
            "model": r.model,
            "t1_refine_attempts": 0,
        }

    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with locked_file(str(tele_path), timeout=5):
        fd, tmp = tempfile.mkstemp(dir=str(tele_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, str(tele_path))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
