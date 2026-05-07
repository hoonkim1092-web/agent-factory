"""Phase 6: QualityContract 회귀 테스트.

설계문서 §Phase 6 요구사항:
- 모든 프롬프트가 non-empty QualityContract를 생성
- 포커 프롬프트는 domain:poker overlay 적용
- 비포커 프롬프트도 base/artifact/capability pack 적용
- 체크리스트가 비어도 통과 처리 안 됨
"""
import pytest
from core.research.work_spec import WorkSpec
from core.research.quality_contract import (
    QualityContractBuilder,
    QualityContractBuildError,
    QualityContractItem,
)
from core.research.checklist_merger import ChecklistMerger


# ---------------------------------------------------------------------------
# QualityContractBuilder 단위 테스트
# ---------------------------------------------------------------------------

class TestQualityContractBuilder:
    def _builder(self):
        return QualityContractBuilder()

    def test_base_pack_always_applied(self):
        spec = WorkSpec(artifact_type="other")
        contract = self._builder().build(spec)
        ids = {item.id for item in contract.checklist}
        assert "requirements_coverage" in ids
        assert "architecture_rationale" in ids

    def test_game_artifact_pack_applied(self):
        spec = WorkSpec(artifact_type="game")
        contract = self._builder().build(spec)
        ids = {item.id for item in contract.checklist}
        assert "game_loop" in ids
        assert "game_state_model" in ids
        assert "action_validation" in ids
        assert "win_loss_condition" in ids

    def test_multiplayer_capability_pack_applied(self):
        spec = WorkSpec(artifact_type="game", capabilities=["multiplayer"])
        contract = self._builder().build(spec)
        ids = {item.id for item in contract.checklist}
        assert "authoritative_server" in ids
        assert "disconnect_recovery" in ids
        assert "server_client_responsibility" in ids

    def test_realtime_capability_pack_applied(self):
        spec = WorkSpec(artifact_type="game", capabilities=["realtime"])
        contract = self._builder().build(spec)
        ids = {item.id for item in contract.checklist}
        assert "latency_handling" in ids
        assert "state_synchronization" in ids

    def test_poker_domain_overlay_applied(self):
        spec = WorkSpec(artifact_type="game", domain="poker")
        contract = self._builder().build(spec)
        ids = {item.id for item in contract.checklist}
        assert "hand_ranking" in ids
        assert "blind_structure" in ids
        assert "side_pot" in ids
        assert "card_randomness" in ids
        assert "client_hidden_state" in ids

    def test_poker_overlay_via_domain_hints(self):
        """domain_hints로도 poker overlay가 적용된다."""
        spec = WorkSpec(artifact_type="game", domain="", domain_hints=["poker"])
        contract = self._builder().build(spec)
        ids = {item.id for item in contract.checklist}
        assert "hand_ranking" in ids

    def test_unknown_domain_does_not_raise(self):
        """알 수 없는 도메인 힌트는 overlay 없이 base/artifact/capability만 적용."""
        spec = WorkSpec(artifact_type="webapp", domain="unknown_xyz")
        contract = self._builder().build(spec)
        assert len(contract.checklist) > 0
        assert "domain:unknown_xyz" not in contract.packs_applied

    def test_empty_work_spec_uses_base_pack(self):
        """WorkSpec이 비어도 base pack으로 non-empty contract 생성."""
        spec = WorkSpec()
        contract = self._builder().build(spec)
        assert len(contract.checklist) > 0, "base pack이 없으면 QualityContractBuildError"

    def test_build_error_raised_when_no_items(self, tmp_path, monkeypatch):
        """packs 디렉터리가 비어있으면 QualityContractBuildError."""
        import core.research.quality_contract as qc_mod
        monkeypatch.setattr(qc_mod, "_PACKS_DIR", tmp_path)
        spec = WorkSpec(artifact_type="game", domain="poker")
        with pytest.raises(QualityContractBuildError):
            QualityContractBuilder().build(spec)

    def test_packs_applied_recorded(self):
        spec = WorkSpec(artifact_type="game", domain="poker", capabilities=["multiplayer"])
        contract = self._builder().build(spec)
        assert "base" in contract.packs_applied
        assert "artifact:game" in contract.packs_applied
        assert "capability:multiplayer" in contract.packs_applied
        assert "domain:poker" in contract.packs_applied

    def test_keywords_for_gap_check_non_empty(self):
        spec = WorkSpec(artifact_type="game", domain="poker")
        contract = self._builder().build(spec)
        keywords = contract.keywords_for_gap_check()
        assert len(keywords) > 0

    def test_to_dict_schema(self):
        spec = WorkSpec(artifact_type="game", domain="poker")
        contract = self._builder().build(spec)
        d = contract.to_dict()
        assert "contract_id" in d
        assert "work_spec" in d
        assert "packs_applied" in d
        assert "checklist" in d
        assert isinstance(d["checklist"], list)
        assert d["checklist"][0].get("id")


# ---------------------------------------------------------------------------
# ChecklistMerger 단위 테스트
# ---------------------------------------------------------------------------

class TestChecklistMerger:
    def _merger(self):
        return ChecklistMerger()

    def test_deduplicates_same_id(self):
        items = [
            QualityContractItem(id="a", title="A1", source="base_pack"),
            QualityContractItem(id="a", title="A2", source="domain_overlay"),
        ]
        merged = self._merger().merge(items)
        assert len(merged) == 1
        assert merged[0].id == "a"

    def test_overlay_cannot_delete_required(self):
        items = [
            QualityContractItem(id="a", title="A", source="base_pack", required=True),
            QualityContractItem(id="a", title="A", source="domain_overlay", required=False),
        ]
        merged = self._merger().merge(items)
        assert merged[0].required is True

    def test_llm_addition_cannot_delete_required(self):
        items = [
            QualityContractItem(id="a", title="A", source="base_pack", required=True),
            QualityContractItem(id="a", title="A", source="llm_addition", required=False),
        ]
        merged = self._merger().merge(items)
        assert merged[0].required is True

    def test_items_without_id_skipped(self):
        items = [
            QualityContractItem(id="", title="No id", source="base_pack"),
            QualityContractItem(id="b", title="B", source="base_pack"),
        ]
        merged = self._merger().merge(items)
        assert len(merged) == 1
        assert merged[0].id == "b"


# ---------------------------------------------------------------------------
# Phase 6 다중 도메인 회귀 테스트
# ---------------------------------------------------------------------------

MULTI_DOMAIN_CASES = [
    ("포커 만들기",          True,  "poker"),
    ("포커게임 만들기",      True,  "poker"),
    ("8인 네트워크 포커게임", True,  "poker"),
    ("체스 게임 만들기",     False, None),
    ("쇼핑몰 만들기",        False, None),
    ("블로그 시스템 만들기", False, None),
    ("실시간 채팅앱 만들기", False, None),
]


@pytest.mark.parametrize("prompt,expect_poker,_domain", MULTI_DOMAIN_CASES)
def test_non_empty_contract_for_all_domains(prompt, expect_poker, _domain):
    """모든 프롬프트가 non-empty QualityContract를 생성해야 한다."""
    from core.research_router import ResearchRouter
    domain_hint = ResearchRouter()._detect_domain_hints(prompt)
    spec = WorkSpec(
        artifact_type="game" if "게임" in prompt or "game" in prompt.lower() else "webapp",
        domain_hints=[domain_hint] if domain_hint else [],
    )
    contract = QualityContractBuilder().build(spec)
    assert len(contract.checklist) > 0, f"[{prompt}] checklist must not be empty"


@pytest.mark.parametrize("prompt,expect_poker,_domain", MULTI_DOMAIN_CASES)
def test_poker_overlay_applied_only_for_poker(prompt, expect_poker, _domain):
    """포커 프롬프트만 domain:poker overlay를 적용한다."""
    from core.research_router import ResearchRouter
    domain_hint = ResearchRouter()._detect_domain_hints(prompt)
    spec = WorkSpec(
        artifact_type="game",
        domain_hints=[domain_hint] if domain_hint else [],
    )
    contract = QualityContractBuilder().build(spec)
    has_poker_overlay = "domain:poker" in contract.packs_applied
    assert has_poker_overlay == expect_poker, (
        f"[{prompt}] poker overlay={'yes' if has_poker_overlay else 'no'}, "
        f"expected={'yes' if expect_poker else 'no'}"
    )
