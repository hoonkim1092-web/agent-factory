"""
EpisodeMatcher — 실패→성공 에피소드 쌍 자동 매칭 + top-k 유사 에피소드 조회.

Stage 4 (Phase 4 확장): 저장된 에피소드를 스캔하여 같은/유사한 task의
failure→success 쌍을 찾고, graph_builder.extract_triple()을 호출할
재료를 제공한다. 새 brief 진입 시 유사 과거 에피소드 top-k를 반환해
work_item_generator에 힌트를 주입한다.

매칭 전략:
  1. causal_links 기반 (FSALoop 재시도 → 가장 정확)
  2. task_input 키워드 유사도 (같은 task 표현)
  3. (미구현) SemanticEmbedder 유사도 — 향후 확장 예정
"""

from __future__ import annotations

import logging
import os
from typing import Any

from core.memory_system.models import EpisodeRecord, MemoryRecord, MemoryType

logger = logging.getLogger(__name__)

# task_input 키워드 유사도 임계치 (0-1)
_KEYWORD_THRESHOLD = 0.4
_TOP_K_DEFAULT = 5


def keyword_similarity(a: str, b: str) -> float:
    """Jaccard similarity on whitespace-split tokens."""
    if not a or not b:
        return 0.0
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


_keyword_similarity = keyword_similarity


class EpisodeMatcher:
    """Find failure→success episode pairs for knowledge extraction."""

    def __init__(self, facade: Any) -> None:
        self._facade = facade

    async def find_pairs(
        self,
        recent_success: EpisodeRecord,
        *,
        max_candidates: int = 50,
    ) -> list[tuple[EpisodeRecord, EpisodeRecord]]:
        """Given a recent *success* episode, find matching failure episodes.

        Returns list of (failure, success) pairs, best match first.
        """
        pairs: list[tuple[EpisodeRecord, float]] = []

        # ── Strategy 1: causal_links (최고 신뢰도) ──────────────
        for linked_id in recent_success.causal_links:
            failure_ep = await self._load_episode(linked_id)
            if failure_ep and failure_ep.outcome == "failure":
                pairs.append((failure_ep, 1.0))
                logger.info(
                    "EpisodeMatcher: causal link %s → %s",
                    linked_id[:12],
                    recent_success.episode_id[:12],
                )

        # causal_links로 충분하면 바로 반환
        if pairs:
            return [(f, recent_success) for f, _ in pairs]

        # ── Strategy 2: 같은 프로젝트의 최근 실패 에피소드 검색 ──
        failure_records = await self._search_failures(
            project_id=recent_success.project_id,
            limit=max_candidates,
        )

        for record in failure_records:
            failure_ep = self._record_to_episode(record)
            if not failure_ep or failure_ep.outcome != "failure":
                continue

            # 키워드 유사도
            sim = keyword_similarity(
                recent_success.task_input,
                failure_ep.task_input,
            )
            if sim >= _KEYWORD_THRESHOLD:
                pairs.append((failure_ep, sim))

        # 유사도 높은 순 정렬
        pairs.sort(key=lambda x: x[1], reverse=True)

        # 상위 3개만 반환 (노이즈 방지)
        return [(f, recent_success) for f, _ in pairs[:3]]

    # ── Internal helpers ───────────────────────────────────────────

    async def _load_episode(self, episode_id: str) -> EpisodeRecord | None:
        """Load a single episode by ID from the facade."""
        record = await self._facade.read(episode_id)
        if not record:
            return None
        return self._record_to_episode(record)

    async def _search_failures(
        self,
        project_id: str,
        limit: int,
    ) -> list[MemoryRecord]:
        """Search for recent failure episodes in the same project."""
        records = await self._facade.search_semantic(
            "failure error exception failed",
            limit=limit,
            memory_type=MemoryType.EPISODIC,
        )
        # Filter to actual failures, scoped to the given project
        return [
            r for r in records
            if (r.metadata.get("project_id", project_id) == project_id)
            and (
                r.metadata.get("outcome") == "failure"
                or "failure" in r.content.lower()
            )
        ]

    async def query_similar(
        self,
        brief_text: str,
        *,
        top_k: int = _TOP_K_DEFAULT,
        project_id: str = "",
    ) -> list[dict[str, Any]]:
        """새 brief와 유사한 과거 성공 에피소드 top-k를 반환한다.

        반환 형식: [{"episode_id", "task_input", "outcome", "similarity", "hints"}, ...]
        시드(.md) 결과와 메모리 결과를 스케일 혼합 없이 분리해 채운다:
          - 시드 최대 top_k // 2 슬롯, 나머지를 메모리로 채운다.
        """
        seed_slots = max(1, top_k // 2)

        # ── 파일 기반 시드 에피소드 검색 (coverage 기반 유사도) ────────
        seed_hits = _search_seed_episodes(brief_text, top_k=seed_slots)
        seed_ids = {h["episode_id"] for h in seed_hits}

        # ── 메모리 시스템 성공 에피소드 검색 (Jaccard 기반 유사도) ──────
        memory_hits: list[tuple[float, dict[str, Any]]] = []
        try:
            records = await self._facade.search_semantic(
                brief_text,
                limit=top_k * 3,
                memory_type=MemoryType.EPISODIC,
            )
            for record in records:
                ep = self._record_to_episode(record)
                if not ep or ep.outcome not in ("success", "partial"):
                    continue
                if project_id and ep.project_id and ep.project_id != project_id:
                    continue
                if ep.episode_id in seed_ids:
                    continue
                sim = keyword_similarity(brief_text, ep.task_input)
                if sim < _KEYWORD_THRESHOLD:
                    continue
                hints = ep.metadata.get("hints") or []
                memory_hits.append((sim, {
                    "episode_id": ep.episode_id,
                    "task_input": ep.task_input,
                    "outcome": ep.outcome,
                    "similarity": round(sim, 3),
                    "hints": hints,
                }))
        except Exception as exc:
            logger.warning("EpisodeMatcher.query_similar: facade 검색 실패 — %s", exc)

        memory_hits.sort(key=lambda x: x[0], reverse=True)
        memory_results = [item for _, item in memory_hits[: top_k - len(seed_hits)]]

        return seed_hits + memory_results

    @staticmethod
    def _record_to_episode(record: MemoryRecord) -> EpisodeRecord | None:
        """Reconstruct an EpisodeRecord from a MemoryRecord's metadata."""
        meta = record.metadata
        if not meta or "episode_id" not in meta:
            return None
        try:
            return EpisodeRecord.from_dict(meta)
        except Exception:
            return None


# ── 파일 기반 시드 에피소드 검색 헬퍼 ──────────────────────────────────────

def _search_seed_episodes(brief_text: str, *, top_k: int = 5) -> list[dict[str, Any]]:
    """memory/episodes/ 디렉토리의 .md 시드 파일을 검색한다."""
    repo_root = _find_repo_root()
    episodes_dir = os.path.join(repo_root, "memory", "episodes")
    if not os.path.isdir(episodes_dir):
        return []

    results: list[tuple[float, dict[str, Any]]] = []
    for fname in os.listdir(episodes_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(episodes_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        # 시드 파일: brief 토큰 중 파일 전체에 포함된 비율로 유사도 근사
        brief_tokens = set(brief_text.lower().split())
        content_lower = content.lower()
        matches = sum(1 for tok in brief_tokens if tok in content_lower)
        sim = matches / max(len(brief_tokens), 1)
        if sim < 0.05:
            continue

        hints = _extract_hints_from_md(content)
        results.append((sim, {
            "episode_id": fname.replace(".md", ""),
            "task_input": fname,
            "outcome": "success",
            "similarity": round(sim, 3),
            "hints": hints,
        }))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in results[:top_k]]


def _extract_hints_from_md(content: str) -> list[str]:
    """마크다운에서 ## Hints 또는 ## 교훈 섹션의 항목을 추출한다."""
    hints: list[str] = []
    in_hints = False
    for line in content.splitlines():
        if line.startswith("## ") and any(
            kw in line.lower() for kw in ("hint", "교훈", "lesson", "warning")
        ):
            in_hints = True
            continue
        if line.startswith("## ") and in_hints:
            break
        if in_hints and line.startswith("- "):
            hints.append(line[2:].strip())
    return hints[:10]


def _find_repo_root() -> str:
    """현재 파일 기준으로 레포 루트(memory/ 부모)를 찾는다."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(current, "memory")) or os.path.isfile(
            os.path.join(current, "CLAUDE.md")
        ):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.getcwd()
