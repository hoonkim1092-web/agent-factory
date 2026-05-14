"""
Regression tests for Domain Gate Phase A + P5 DomainVerdict 매트릭스.

F3-(a): approve() stores domain_review_version hash in snapshot.
F4-(b): verdict parser supports `- verdict:` first, checkbox fallback.
F5:     DomainVerdict 매트릭스 적용 — NEEDS_ADR×blast_radius 조합으로 proceed/pause 결정.
F6:     AF_SKIP_DOMAIN_REVIEW=1 → domain gate bypassed.
"""
from __future__ import annotations

import os

import pytest

from core.approval_gate import (
    GATE_FILENAME,
    ApprovalGate,
    _DOMAIN_REVIEW_FILE,
    _parse_domain_review,
    _read_domain_review_verdict,
)


# ---------------------------------------------------------------------------
# _read_domain_review_verdict unit tests
# ---------------------------------------------------------------------------

def _write(tmp_path, content: str) -> str:
    p = tmp_path / "domain-review.md"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_verdict_explicit_pass(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\n- verdict: PASS\n")
    assert _read_domain_review_verdict(path) == "PASS"


def test_verdict_explicit_block(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\n- verdict: BLOCK\n")
    assert _read_domain_review_verdict(path) == "BLOCK"


def test_verdict_explicit_needs_adr(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\n- verdict: NEEDS_ADR\n")
    assert _read_domain_review_verdict(path) == "NEEDS_ADR"


def test_verdict_checkbox_fallback(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\n- [ ] BLOCK\n- [x] PASS\n")
    assert _read_domain_review_verdict(path) == "PASS"


def test_verdict_multiple_explicit(tmp_path):
    path = _write(tmp_path, "- verdict: PASS\n- verdict: BLOCK\n")
    assert _read_domain_review_verdict(path) == "MULTIPLE"


def test_verdict_multiple_checkbox(tmp_path):
    path = _write(tmp_path, "- [x] PASS\n- [x] BLOCK\n")
    assert _read_domain_review_verdict(path) == "MULTIPLE"


def test_verdict_missing(tmp_path):
    path = _write(tmp_path, "# Domain Review\n\nNo verdict here.\n")
    assert _read_domain_review_verdict(path) == ""


def test_verdict_file_not_found(tmp_path):
    assert _read_domain_review_verdict(str(tmp_path / "nonexistent.md")) == ""


# ---------------------------------------------------------------------------
# ApprovalGate domain gate integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def gate_system_wide(tmp_path):
    """blast_radius=system_wide 게이트 픽스처."""
    g = ApprovalGate(str(tmp_path), "dg-test")
    g.initialize(work_item_id="WI-DG", work_kind="feature_update", blast_radius="system_wide")
    return g


@pytest.fixture
def gate_module(tmp_path):
    """blast_radius=module 게이트 픽스처."""
    g = ApprovalGate(str(tmp_path), "dg-module")
    g.initialize(work_item_id="WI-MOD", work_kind="bugfix", blast_radius="module")
    return g


@pytest.fixture
def gate_isolated(tmp_path):
    """blast_radius=isolated 게이트 픽스처."""
    g = ApprovalGate(str(tmp_path), "dg-isolated")
    g.initialize(work_item_id="WI-ISO", work_kind="bugfix", blast_radius="isolated")
    return g


@pytest.fixture
def gate_cross_module(tmp_path):
    """blast_radius=cross_module 게이트 픽스처."""
    g = ApprovalGate(str(tmp_path), "dg-cross")
    g.initialize(work_item_id="WI-CROSS", work_kind="feature_update", blast_radius="cross_module")
    return g


def _write_domain_review(gate: ApprovalGate, content: str) -> None:
    path = os.path.join(gate.work_item_dir, "domain-review.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class TestDomainGateSystemWide:
    def test_blocks_when_domain_review_missing(self, gate_system_wide):
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "missing_domain_review_file"

    def test_blocks_when_verdict_missing(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "# Domain Review\n\nNo verdict.\n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "missing_verdict"

    def test_blocks_when_verdict_block(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: BLOCK\n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "domain_review_blocked"

    def test_blocks_when_multiple_verdicts(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n- verdict: BLOCK\n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "multiple_verdicts"

    def test_passes_with_pass_verdict(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        result = gate_system_wide.approve(approver="user")
        assert result is True
        assert gate_system_wide.last_block_reason == ""

    def test_needs_adr_system_wide_pauses(self, gate_system_wide):
        # P5 매트릭스: NEEDS_ADR + system_wide → pause
        _write_domain_review(gate_system_wide, "- verdict: NEEDS_ADR\n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "needs_adr_paused"

    def test_stores_domain_review_version_on_approve(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        gate_system_wide.approve(approver="user")
        parsed = gate_system_wide._parse()
        snapshots = parsed.get("snapshots", {})
        assert snapshots.get("domain_review"), "domain_review_version must be stored"

    def test_domain_review_version_changes_when_file_changes(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        gate_system_wide.approve(approver="user")
        v1 = gate_system_wide._parse().get("snapshots", {}).get("domain_review")

        # Invalidate and re-approve with changed content
        gate_system_wide.invalidate(reason="test")
        _write_domain_review(gate_system_wide, "- verdict: PASS\n\nAdditional content.\n")
        gate_system_wide.approve(approver="user")
        v2 = gate_system_wide._parse().get("snapshots", {}).get("domain_review")

        assert v1 != v2


class TestDomainGateNonSystemWide:
    def test_no_domain_review_module_proceeds(self, gate_module):
        # domain-review.md 없는 low blast_radius → domain gate optional, 진행
        result = gate_module.approve(approver="user")
        assert result is True

    def test_no_domain_review_version_stored_for_module(self, gate_module):
        gate_module.approve(approver="user")
        snapshots = gate_module._parse().get("snapshots", {})
        assert not snapshots.get("domain_review")

    def test_module_pass_verdict_proceeds(self, gate_module):
        _write_domain_review(gate_module, "- verdict: PASS\n")
        result = gate_module.approve(approver="user")
        assert result is True
        assert gate_module.last_block_reason == ""

    def test_needs_adr_module_proceeds_with_warning(self, gate_module):
        # P5 매트릭스: NEEDS_ADR + module → warning + proceed
        _write_domain_review(gate_module, "- verdict: NEEDS_ADR\n")
        result = gate_module.approve(approver="user")
        assert result is True
        assert gate_module.last_block_reason == ""
        assert gate_module.last_warning_reason == "needs_adr_warning"

    def test_module_block_verdict_blocks(self, gate_module):
        _write_domain_review(gate_module, "- verdict: BLOCK\n")
        result = gate_module.approve(approver="user")
        assert result is False
        assert gate_module.last_block_reason == "domain_review_blocked"


class TestDomainGateCheckValidity:
    def test_domain_review_change_invalidates_gate(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        gate_system_wide.approve(approver="user")
        assert gate_system_wide.is_execution_open()

        # Modify domain-review.md after approval
        _write_domain_review(gate_system_wide, "- verdict: BLOCK\n")
        assert not gate_system_wide.is_execution_open()

    def test_domain_review_unchanged_stays_valid(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: PASS\n")
        gate_system_wide.approve(approver="user")
        assert gate_system_wide.is_execution_open()

    def test_no_domain_review_version_no_dr_check(self, gate_module):
        gate_module.approve(approver="user")
        valid, changed = gate_module.check_validity()
        assert valid
        assert _DOMAIN_REVIEW_FILE not in changed


class TestDomainGateSkipEnv:
    def test_skip_env_bypasses_domain_gate(self, gate_system_wide, monkeypatch):
        monkeypatch.setenv("AF_SKIP_DOMAIN_REVIEW", "1")
        # no domain-review.md present
        result = gate_system_wide.approve(approver="user")
        assert result is True

    def test_skip_env_no_version_stored(self, gate_system_wide, monkeypatch):
        monkeypatch.setenv("AF_SKIP_DOMAIN_REVIEW", "1")
        gate_system_wide.approve(approver="user")
        snapshots = gate_system_wide._parse().get("snapshots", {})
        assert not snapshots.get("domain_review")


class TestDomainGateNeedsAdr:
    """P5: NEEDS_ADR × blast_radius 매트릭스 테스트."""

    def test_needs_adr_isolated_proceeds_with_warning(self, gate_isolated):
        _write_domain_review(gate_isolated, "- verdict: NEEDS_ADR\n")
        result = gate_isolated.approve(approver="user")
        assert result is True
        assert gate_isolated.last_block_reason == ""  # proceed path에서 block_reason 미설정
        assert gate_isolated.last_warning_reason == "needs_adr_warning"

    def test_needs_adr_cross_module_pauses(self, gate_cross_module):
        _write_domain_review(gate_cross_module, "- verdict: NEEDS_ADR\n")
        result = gate_cross_module.approve(approver="user")
        assert result is False
        assert gate_cross_module.last_block_reason == "needs_adr_paused"


class TestDomainGateBlockCause:
    """P5: BlockCause 파싱 테스트."""

    def test_block_cause_parsed_from_domain_review_md(self, tmp_path):
        content = "- verdict: BLOCK\n- block_cause: DESIGN_CONFLICT\n"
        path = str(tmp_path / "domain-review.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        verdict, cause = _parse_domain_review(path)
        assert verdict == "BLOCK"
        assert cause == "DESIGN_CONFLICT"

    def test_block_cause_lowercase_normalized(self, tmp_path):
        # StageRouter가 소문자로 기록 — IGNORECASE + upper() 정규화 검증
        content = "- verdict: BLOCK\n- block_cause: high_risk\n"
        path = str(tmp_path / "domain-review.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        _, cause = _parse_domain_review(path)
        assert cause == "HIGH_RISK"

    def test_block_cause_absent_returns_empty(self, tmp_path):
        path = str(tmp_path / "domain-review.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("- verdict: BLOCK\n")
        _, cause = _parse_domain_review(path)
        assert cause == ""

    def test_block_cause_sets_last_block_reason(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "- verdict: BLOCK\n- block_cause: HIGH_RISK\n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "domain_review_blocked_high_risk"

    def test_blank_template_low_blast_proceeds(self, gate_module):
        # generate_work_items()가 빈 템플릿을 복사할 때 low_blast에서 false-block 방지
        _write_domain_review(gate_module, "# Domain Review\n\n- verdict: \n")
        result = gate_module.approve(approver="user")
        assert result is True
        assert gate_module.last_block_reason == ""

    def test_blank_template_high_blast_blocks(self, gate_system_wide):
        _write_domain_review(gate_system_wide, "# Domain Review\n\n- verdict: \n")
        result = gate_system_wide.approve(approver="user")
        assert result is False
        assert gate_system_wide.last_block_reason == "missing_verdict"
