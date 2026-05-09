from __future__ import annotations
from core.research.quality_contract import QualityContractBuildError, QualityContractItem


class ChecklistMerger:
    """동일 id 항목 병합. overlay 항목이 required/priority/acceptance를 덮어쓸 수 있다.

    규칙:
    1. 모든 항목은 canonical id를 갖는다 (strip + lower).
    2. 같은 id → merge (overlay가 required/priority/acceptance override).
    3. llm_addition은 required=True 항목을 삭제할 수 없다.
    4. llm_addition은 reason 필드가 있어야 한다.
    5. 최종 체크리스트는 반드시 비어 있지 않아야 한다.
    """

    def merge(self, items: list[QualityContractItem]) -> list[QualityContractItem]:
        merged: dict[str, QualityContractItem] = {}
        for item in items:
            canonical_id = item.id.strip().lower()
            if not canonical_id:
                continue
            # Rule 4: llm_addition must have reason
            if item.source == "llm_addition" and not item.reason:
                continue
            if canonical_id not in merged:
                item_copy = QualityContractItem(
                    id=canonical_id,
                    title=item.title,
                    source=item.source,
                    required=item.required,
                    priority=item.priority,
                    acceptance=item.acceptance,
                    reason=item.reason,
                    match_keywords=item.match_keywords,
                )
                merged[canonical_id] = item_copy
            else:
                existing = merged[canonical_id]
                # Rule 3: overlay / llm_addition cannot delete required=True items
                if existing.required and item.source == "llm_addition" and not item.required:
                    continue
                if item.source in ("domain_overlay", "llm_addition"):
                    merged[canonical_id] = QualityContractItem(
                        id=canonical_id,
                        title=item.title or existing.title,
                        source=existing.source,
                        required=item.required if existing.source != "base_pack" else existing.required,
                        priority=item.priority if item.priority is not None else existing.priority,
                        acceptance=item.acceptance or existing.acceptance,
                        reason=item.reason or existing.reason,
                        match_keywords=item.match_keywords or existing.match_keywords,
                    )
        result = list(merged.values())
        if not result:
            raise QualityContractBuildError("checklist_merger produced empty checklist")
        return result
