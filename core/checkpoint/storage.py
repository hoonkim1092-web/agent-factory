"""
Checkpoint Storage — 어댑터 인터페이스 + FileCheckpointStorage.

Step 0 ⑥ 결정: 파일 SoT로 시작 → Postgres swap 가능.
이 인터페이스를 유지하면 swap 시 호출부 코드 변경 없음.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Optional

from core.checkpoint.canonical import Checkpoint


class CheckpointStorage(ABC):
    @abstractmethod
    def save(self, checkpoint: Checkpoint) -> None: ...

    @abstractmethod
    def load(self, run_id: str) -> Optional[Checkpoint]: ...

    @abstractmethod
    def list_runs(self) -> list[str]: ...

    @abstractmethod
    def delete(self, run_id: str) -> None: ...


class FileCheckpointStorage(CheckpointStorage):
    """파일 기반 checkpoint storage. runs/{run_id}/canonical_checkpoint.json."""

    def __init__(self, base_dir: str = "runs"):
        self._base_dir = base_dir

    def _path(self, run_id: str) -> str:
        return os.path.join(self._base_dir, run_id, "canonical_checkpoint.json")

    def save(self, checkpoint: Checkpoint) -> None:
        path = self._path(checkpoint.run_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            raise

    def load(self, run_id: str) -> Optional[Checkpoint]:
        path = self._path(run_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return Checkpoint.from_dict(json.load(f))
        except Exception:
            return None

    def list_runs(self) -> list[str]:
        if not os.path.exists(self._base_dir):
            return []
        runs = []
        for name in os.listdir(self._base_dir):
            if os.path.isdir(os.path.join(self._base_dir, name)):
                cp_path = self._path(name)
                if os.path.exists(cp_path):
                    runs.append(name)
        return sorted(runs)

    def delete(self, run_id: str) -> None:
        path = self._path(run_id)
        if os.path.exists(path):
            os.remove(path)


_default_storage: Optional[CheckpointStorage] = None


def get_default_storage(base_dir: str = "runs") -> CheckpointStorage:
    global _default_storage
    if _default_storage is None:
        resolved = os.environ.get("AF_CHECKPOINT_DIR") or base_dir
        _default_storage = FileCheckpointStorage(base_dir=resolved)
    return _default_storage
