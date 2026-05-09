"""
Canonical Checkpoint — T1-1의 단일 진실원천 체크포인트.

3곳에 분산된 기존 checkpoint(hooks/checkpoint.py, project_pipeline.py, lifecycle_bridge.py)를
이 dataclass로 수렴시킨다. 기존 코드는 이중 쓰기 phase 동안 유지된다.

4요소 (Codex 보강):
  - idempotency_key : 재개 시 중복 실행 방지
  - worktree_snapshot: 파일 상태 스냅샷
  - next_step_cursor : 다음 실행 단계
  - test_acceptance_results: 통과한 검증 영속화
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Checkpoint:
    run_id: str
    step_id: str
    idempotency_key: str
    worktree_snapshot: dict        # {rel_path: sha256_hex}
    next_step_cursor: str          # e.g. "prepare", "plan", "orchestrate", "done"
    test_acceptance_results: dict  # {test_id: "pass" | "fail"}
    saved_at: str = field(default_factory=_utcnow)
    project_id: str = ""
    metadata: dict = field(default_factory=dict)

    # ── factory ──────────────────────────────────────────────────────────

    @staticmethod
    def make_idempotency_key(
        work_item_id: str,
        step_index: int,
        external_input_digest: str,
    ) -> str:
        """external_input_digest = hash(user_request + repo_state_hash + tool_args).
        LLM output은 포함하지 않는다 — 재시도마다 달라지기 때문."""
        raw = f"{work_item_id}:{step_index}:{external_input_digest}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    @staticmethod
    def snapshot_worktree(workspace: str, extensions: tuple[str, ...] = (".py", ".md", ".json", ".yaml", ".yml")) -> dict:
        """workspace 아래 파일들의 {rel_path: sha256} 스냅샷을 생성한다."""
        import os
        snapshot: dict[str, str] = {}
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".git")]
            for fname in files:
                if not any(fname.endswith(ext) for ext in extensions):
                    continue
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, workspace)
                try:
                    with open(full, "rb") as f:
                        snapshot[rel] = hashlib.sha256(f.read()).hexdigest()[:16]
                except OSError:
                    pass
        return snapshot

    # ── serialisation ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "idempotency_key": self.idempotency_key,
            "worktree_snapshot": self.worktree_snapshot,
            "next_step_cursor": self.next_step_cursor,
            "test_acceptance_results": self.test_acceptance_results,
            "saved_at": self.saved_at,
            "project_id": self.project_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(
            run_id=data["run_id"],
            step_id=data.get("step_id", ""),
            idempotency_key=data.get("idempotency_key", ""),
            worktree_snapshot=data.get("worktree_snapshot", {}),
            next_step_cursor=data.get("next_step_cursor", "prepare"),
            test_acceptance_results=data.get("test_acceptance_results", {}),
            saved_at=data.get("saved_at", _utcnow()),
            project_id=data.get("project_id", ""),
            metadata=data.get("metadata", {}),
        )

    # ── helpers ──────────────────────────────────────────────────────────

    def is_stage_done(self, stage: str) -> bool:
        """next_step_cursor가 stage보다 앞서 있는지 확인 (stage를 건너뛸 수 있는지)."""
        order = ["prepare", "plan", "orchestrate", "done"]
        try:
            cursor_idx = order.index(self.next_step_cursor)
            stage_idx = order.index(stage)
            return cursor_idx > stage_idx
        except ValueError:
            return False
