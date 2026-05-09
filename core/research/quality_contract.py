from __future__ import annotations
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import yaml

from core.research.work_spec import WorkSpec

_logger = logging.getLogger(__name__)


class QualityContractBuildError(RuntimeError):
    """QualityContract를 빈 채로 만들려 할 때 발생."""


@dataclass
class QualityContractItem:
    id: str
    title: str
    source: str                              # "base_pack", "artifact_pack", "capability_pack", "domain_overlay", "llm_addition"
    required: bool = True
    priority: str | None = None   # None = "not set"; effective default is "medium"
    acceptance: str = ""
    reason: str = ""                         # llm_addition일 때 필수
    match_keywords: list[str] = field(default_factory=list)  # gap 체크용 키워드

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "required": self.required,
            "priority": self.priority,
            "acceptance": self.acceptance,
            "reason": self.reason,
            "match_keywords": self.match_keywords,
        }


@dataclass
class QualityContract:
    contract_id: str = "research_quality_contract"
    work_spec: WorkSpec = field(default_factory=WorkSpec)
    packs_applied: list[str] = field(default_factory=list)
    checklist: list[QualityContractItem] = field(default_factory=list)

    def required_items(self) -> list[QualityContractItem]:
        return [item for item in self.checklist if item.required]

    def keywords_for_gap_check(self) -> list[str]:
        """RecoverySearchLoop 호환: 체크리스트 키워드 목록 반환."""
        out: list[str] = []
        for item in self.checklist:
            if item.match_keywords:
                out.extend(item.match_keywords)
            else:
                out.append(item.id.replace("_", " "))
        return out

    def to_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "work_spec": self.work_spec.to_dict(),
            "packs_applied": self.packs_applied,
            "checklist": [item.to_dict() for item in self.checklist],
        }


_BASE = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent
_PACKS_DIR = _BASE / "packs"


class QualityContractBuilder:
    """WorkSpec → QualityContract 조립.

    pack 레이어 순서:
      1. base
      2. artifact:<artifact_type>
      3. capability:<cap> (각 capability마다)
      4. domain:<domain> (overlay)
    """

    @staticmethod
    def _safe_name(name: str) -> str:
        """LLM-extracted name → safe filesystem component (alphanumeric + underscore only)."""
        return re.sub(r"[^\w]", "", (name or "").strip().lower())

    def build(self, work_spec: WorkSpec) -> QualityContract:
        checklist: list[QualityContractItem] = []
        packs_applied: list[str] = []

        # 1. base pack (항상 적용)
        base_items = self._load_pack(_PACKS_DIR / "base.yaml", source="base_pack")
        if base_items:
            checklist.extend(base_items)
            packs_applied.append("base")

        # 2. artifact pack
        if work_spec.artifact_type:
            art_name = self._safe_name(work_spec.artifact_type)
            if art_name:
                art_path = _PACKS_DIR / "artifacts" / f"{art_name}.yaml"
                art_items = self._load_pack(art_path, source="artifact_pack")
                if art_items:
                    checklist.extend(art_items)
                    packs_applied.append(f"artifact:{art_name}")

        # 3. capability packs
        for cap in work_spec.capabilities:
            cap_name = self._safe_name(cap)
            if not cap_name:
                continue
            cap_path = _PACKS_DIR / "capabilities" / f"{cap_name}.yaml"
            cap_items = self._load_pack(cap_path, source="capability_pack")
            if cap_items:
                checklist.extend(cap_items)
                packs_applied.append(f"capability:{cap_name}")

        # 4. domain overlay (domain_hints 포함)
        domains_to_check = []
        if work_spec.domain:
            d = self._safe_name(work_spec.domain)
            if d:
                domains_to_check.append(d)
        for hint in work_spec.domain_hints:
            h = self._safe_name(hint)
            if h and h not in domains_to_check:
                domains_to_check.append(h)
        for domain in domains_to_check:
            dom_path = _PACKS_DIR / "domains" / f"{domain}.yaml"
            dom_items = self._load_pack(dom_path, source="domain_overlay")
            if dom_items:
                checklist.extend(dom_items)
                packs_applied.append(f"domain:{domain}")

        if not checklist:
            raise QualityContractBuildError(
                f"quality contract has no checklist items — "
                f"work_spec={work_spec.to_dict()}, packs_dir={_PACKS_DIR}"
            )

        return QualityContract(
            work_spec=work_spec,
            packs_applied=packs_applied,
            checklist=checklist,
        )

    def _load_pack(self, path: Path, source: str) -> list[QualityContractItem]:
        if not path.exists():
            return []
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            _logger.warning("_load_pack failed: %s — %s", path, exc)
            return []
        items = []
        for entry in (data.get("items") or []):
            raw_id = str(entry.get("id") or "").strip()
            if not raw_id:
                _logger.warning("_load_pack: item missing id in %s, skipping", path)
                continue
            items.append(QualityContractItem(
                id=raw_id,
                title=str(entry.get("title") or ""),
                source=source,
                required=bool(entry.get("required", True)),
                priority=entry.get("priority"),        # None = "not set" sentinel
                acceptance=str(entry.get("acceptance") or ""),
                reason=str(entry.get("reason") or ""),
                match_keywords=list(entry.get("match_keywords") or []),
            ))
        return items
