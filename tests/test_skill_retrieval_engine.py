from core.researcher import HimariResearchAgent
from core.skill_feedback import SkillFeedbackLoop, SkillFeedbackSummary
from core.skill_retrieval_engine import CapabilityGap, SkillRetrievalEngine



def test_retrieval_engine_reuses_high_confidence_verified_candidate():
    engine = SkillRetrievalEngine()
    decision = engine.decide_reuse(
        "pytest_regression_guard",
        {
            "top_candidate": "existing_skill",
            "top_score": 92,
            "verified": True,
            "matching_rationale": "strong match",
        },
    )

    assert decision.mode == "ranked_reuse"
    assert decision.candidate_skill_id == "existing_skill"
    assert decision.confidence == 0.92
    assert decision.used_historical_signal is False



def test_retrieval_engine_uses_shadow_reuse_for_medium_confidence_candidate():
    engine = SkillRetrievalEngine()
    decision = engine.decide_reuse(
        "pytest_regression_guard",
        {
            "top_candidate": "existing_skill",
            "top_score": 65,  # confidence=0.65 < enhance_confidence(0.70) → shadow_reuse band
            "verified": True,
        },
    )

    assert decision.mode == "shadow_reuse"
    assert decision.candidate_skill_id == "existing_skill"
    assert decision.score == 65



def test_retrieval_engine_forges_when_candidate_is_too_weak():
    engine = SkillRetrievalEngine()
    decision = engine.decide_reuse(
        "pytest_regression_guard",
        {
            "top_candidate": "existing_skill",
            "top_score": 25,
            "verified": False,
        },
    )

    assert decision.mode == "forge"
    assert decision.candidate_skill_id == "existing_skill"



def test_retrieval_engine_reranks_candidates_with_feedback_history(tmp_path):
    feedback_loop = SkillFeedbackLoop(str(tmp_path / "skill-usage.jsonl"), project_id="proj")
    for _ in range(3):
        feedback_loop.record_runtime_result(skill_id="stable_skill", ok=True, run_id="run_good")
        feedback_loop.record_runtime_result(skill_id="noisy_skill", ok=False, run_id="run_bad")
    feedback_loop.record_promotion(skill_id="stable_skill", status="changed", from_stage="candidate", to_stage="active")
    feedback_loop.record_promotion(skill_id="noisy_skill", status="changed", from_stage="active", to_stage="archived")

    evidence = {
        "top_candidate": "noisy_skill",
        "top_score": 86,
        "verified": True,
        "candidates": [
            {
                "candidate_skill_id": "noisy_skill",
                "score": 86,
                "verification": {"exists_skill_py": True},
                "matching_rationale": "semantic best match",
            },
            {
                "candidate_skill_id": "stable_skill",
                "score": 82,
                "verification": {"exists_skill_py": True},
                "matching_rationale": "semantic second match",
            },
        ],
    }

    decision = SkillRetrievalEngine().decide_reuse(
        "pytest_regression_guard",
        evidence,
        feedback_loop=feedback_loop,
    )

    assert decision.candidate_skill_id == "stable_skill"
    assert decision.used_historical_signal is True
    assert decision.ranked_candidates[0]["candidate_skill_id"] == "stable_skill"
    assert evidence["top_candidate"] == "stable_skill"
    assert decision.base_score == 82
    assert decision.score >= 80


# ── B-3: capability gap 테스트 ────────────────────────────────────────────────


def test_analyze_capability_gap_full_overlap():
    gap = SkillRetrievalEngine._analyze_capability_gap(
        {"capabilities": ["auth", "jwt", "oauth"]},
        ["auth", "jwt"],
    )
    assert gap.missing_capabilities == []
    assert gap.gap_ratio == 0.0


def test_analyze_capability_gap_partial_missing():
    gap = SkillRetrievalEngine._analyze_capability_gap(
        {"capabilities": ["auth", "jwt"]},
        ["auth", "jwt", "refresh_token", "revoke_token"],
    )
    assert set(gap.missing_capabilities) == {"refresh_token", "revoke_token"}
    assert gap.gap_ratio == 0.5


def test_analyze_capability_gap_boundary_enhance_vs_forge():
    # gap_ratio == 0.5 → enhance (<=0.5 조건)
    gap_enhance = SkillRetrievalEngine._analyze_capability_gap(
        {"capabilities": ["a", "b"]},
        ["a", "b", "c", "d"],
    )
    assert gap_enhance.gap_ratio == 0.5

    engine = SkillRetrievalEngine()
    # enhance_confidence=0.70, score=75 는 enhance range
    decision_enhance = engine.decide_reuse(
        "test_skill",
        {
            "top_candidate": "cand",
            "top_score": 75,
            "verified": False,
            "candidates": [{"candidate_skill_id": "cand", "score": 75,
                             "verification": {}, "capabilities": ["a", "b"]}],
            "required_capabilities": ["a", "b", "c", "d"],
        },
    )
    assert decision_enhance.mode == "enhance"

    # gap_ratio > 0.5 → forge (3 missing out of 4)
    decision_forge = engine.decide_reuse(
        "test_skill",
        {
            "top_candidate": "cand",
            "top_score": 75,
            "verified": False,
            "candidates": [{"candidate_skill_id": "cand", "score": 75,
                             "verification": {}, "capabilities": ["a"]}],
            "required_capabilities": ["a", "b", "c", "d"],
        },
    )
    assert decision_forge.mode == "forge"


def test_decide_reuse_researcher_candidate_shape_normalizes_capability_meta():
    """researcher.py:187-194 candidate row에는 meta 키 없음 — capabilities top-level에 살아있음.
    step 3b fix: best.get("meta") 없으면 {"capabilities": best["capabilities"]} 흡수.
    """
    engine = SkillRetrievalEngine()
    # researcher _rank_candidates_for_need가 반환하는 실제 candidate 형상
    decision = engine.decide_reuse(
        "test_skill",
        {
            "top_candidate": "cand",
            "top_score": 75,
            "verified": False,
            # meta 키 없음 — researcher candidate row 형상 (researcher.py:187-194)
            "candidates": [{"candidate_skill_id": "cand", "score": 75,
                             "verification": {}, "capabilities": ["auth", "jwt"]}],
            "required_capabilities": ["auth", "jwt"],
        },
    )
    # full overlap → gap_ratio=0.0 → enhance (not forge)
    assert decision.mode == "enhance"
    assert decision.capability_gap is not None
    assert decision.capability_gap.missing_capabilities == []
    assert decision.capability_gap.gap_ratio == 0.0


def test_decide_reuse_empty_required_caps_uses_score_based_enhance():
    """required_capabilities 비면 점수 기반 enhance 유지 (regression)."""
    engine = SkillRetrievalEngine()
    decision = engine.decide_reuse(
        "test_skill",
        {
            "top_candidate": "cand",
            "top_score": 75,
            "verified": False,
            "candidates": [{"candidate_skill_id": "cand", "score": 75,
                             "verification": {}, "capabilities": ["auth"]}],
            # required_capabilities 없음
        },
    )
    assert decision.mode == "enhance"


def test_skill_gap_capabilities_map_contract():
    hypotheses = [
        {"need_skill_id": "auth_skill", "required_capabilities": ["jwt", "oauth"]},
        {"need_skill_id": "db_skill", "required_capabilities": ["read", "write"]},
    ]
    result = HimariResearchAgent._skill_gap_capabilities_map(hypotheses)
    assert result["auth_skill"] == ["jwt", "oauth"]
    assert result["db_skill"] == ["read", "write"]
    assert result.get("missing_skill", []) == []  # miss → []


def test_skill_gap_capabilities_map_normalizes_safe_id():
    hypotheses = [{"need_skill_id": "Auth Skill!", "required_capabilities": ["cap"]}]
    result = HimariResearchAgent._skill_gap_capabilities_map(hypotheses)
    assert "auth_skill" in result


def test_skill_gap_capabilities_map_normalizes_cap_values():
    """required_capabilities 값도 safe_id()로 정규화 — registry caps과 비교 정합."""
    hypotheses = [{"need_skill_id": "auth_skill", "required_capabilities": ["JWT Auth", "OAuth 2.0"]}]
    result = HimariResearchAgent._skill_gap_capabilities_map(hypotheses)
    assert result["auth_skill"] == ["jwt_auth", "oauth_2_0"]


def test_skill_gap_capabilities_map_skips_blank_need_id():
    """빈 need_skill_id — safe_id('')='skill' 오염 방지."""
    hypotheses = [
        {"need_skill_id": "", "required_capabilities": ["cap"]},
        {"need_skill_id": "  ", "required_capabilities": ["cap"]},
        {"need_skill_id": "real_skill", "required_capabilities": ["cap"]},
    ]
    result = HimariResearchAgent._skill_gap_capabilities_map(hypotheses)
    assert "skill" not in result
    assert "real_skill" in result


def test_decide_reuse_ranked_reuse_downgraded_when_caps_missing():
    """고신뢰 verified라도 required capability 부재 시 enhance/forge로 강등."""
    engine = SkillRetrievalEngine()
    # gap_ratio=0.5 → enhance
    decision = engine.decide_reuse(
        "test_skill",
        {
            "top_candidate": "cand",
            "top_score": 92,
            "verified": True,
            "candidates": [{"candidate_skill_id": "cand", "score": 92,
                             "verification": {}, "capabilities": ["a", "b"]}],
            "required_capabilities": ["a", "b", "c", "d"],
        },
    )
    assert decision.mode == "enhance"

    # gap_ratio > 0.5 → forge
    decision_forge = engine.decide_reuse(
        "test_skill",
        {
            "top_candidate": "cand",
            "top_score": 92,
            "verified": True,
            "candidates": [{"candidate_skill_id": "cand", "score": 92,
                             "verification": {}, "capabilities": ["a"]}],
            "required_capabilities": ["a", "b", "c", "d"],
        },
    )
    assert decision_forge.mode == "forge"


def test_decide_reuse_ranked_reuse_preserved_when_no_gap():
    """required_capabilities 없거나 full overlap이면 ranked_reuse 유지 (regression)."""
    engine = SkillRetrievalEngine()
    decision = engine.decide_reuse(
        "test_skill",
        {
            "top_candidate": "cand",
            "top_score": 92,
            "verified": True,
            # required_capabilities 없음
        },
    )
    assert decision.mode == "ranked_reuse"


def test_retrieval_engine_uses_batched_feedback_summaries():
    class BatchOnlyFeedbackLoop:
        def summarize_skills(self, skill_ids=None):
            assert list(skill_ids or []) == ["noisy_skill", "stable_skill"]
            return {
                "noisy_skill": SkillFeedbackSummary(
                    skill_id="noisy_skill",
                    total_events=3,
                    runtime_failed=3,
                    current_stage="archived",
                    historical_score=18,
                ),
                "stable_skill": SkillFeedbackSummary(
                    skill_id="stable_skill",
                    total_events=4,
                    runtime_succeeded=3,
                    current_stage="active",
                    historical_score=94,
                ),
            }

    evidence = {
        "top_candidate": "noisy_skill",
        "top_score": 86,
        "verified": True,
        "candidates": [
            {
                "candidate_skill_id": "noisy_skill",
                "score": 86,
                "verification": {"exists_skill_py": True},
                "matching_rationale": "semantic best match",
            },
            {
                "candidate_skill_id": "stable_skill",
                "score": 82,
                "verification": {"exists_skill_py": True},
                "matching_rationale": "semantic second match",
            },
        ],
    }

    decision = SkillRetrievalEngine().decide_reuse(
        "pytest_regression_guard",
        evidence,
        feedback_loop=BatchOnlyFeedbackLoop(),
    )

    assert decision.candidate_skill_id == "stable_skill"
    assert decision.used_historical_signal is True
    assert decision.ranked_candidates[0]["candidate_skill_id"] == "stable_skill"
