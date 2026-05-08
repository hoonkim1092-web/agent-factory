"""Work-item 생성 텔레메트리 — T1 retry atomic update."""
from __future__ import annotations

import json
from pathlib import Path

from core.file_lock import locked_file


def update_t1_refine_attempts(workspace: str, slug: str, doc_name: str, increment: int = 1) -> None:
    """T1 retry 발생 시 텔레메트리 파일의 해당 doc 컬럼을 atomic 증가."""
    tele_dir = Path(workspace) / "runtime" / "work_item_telemetry"
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
        tele_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
