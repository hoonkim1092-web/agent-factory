"""tests/test_skill_metadata_adapter.py — SKILL.md description fallback 검증"""
import textwrap
import pytest
from core.skill_metadata_adapter import auto_detect_and_convert


def _write(tmp_path, filename, content):
    path = tmp_path / filename
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestAutoDetectDescriptionFallback:
    def test_meta_yaml_empty_description_filled_from_skill_md(self, tmp_path):
        """meta.yaml에 description 없으면 SKILL.md 본문에서 채운다."""
        _write(tmp_path, "meta.yaml", """\
            name: my-skill
            type: action
        """)
        _write(tmp_path, "SKILL.md", """\
            # My Skill

            This skill does something useful.
        """)
        meta = auto_detect_and_convert(str(tmp_path), "my-skill")
        assert meta is not None
        assert "something useful" in meta.description
        assert meta.when_to_use  # when_to_use도 SKILL.md에서 채워짐

    def test_meta_yaml_existing_description_not_overridden(self, tmp_path):
        """meta.yaml에 description이 있으면 SKILL.md를 무시한다."""
        _write(tmp_path, "meta.yaml", """\
            name: my-skill
            description: From meta yaml
            when_to_use: Use when needed
        """)
        _write(tmp_path, "SKILL.md", """\
            # My Skill

            This should not appear.
        """)
        meta = auto_detect_and_convert(str(tmp_path), "my-skill")
        assert meta is not None
        assert meta.description == "From meta yaml"
        assert meta.when_to_use == "Use when needed"

    def test_skill_yaml_empty_description_filled_from_skill_md(self, tmp_path):
        """skill.yaml에 description 없으면 SKILL.md에서 채운다."""
        _write(tmp_path, "skill.yaml", """\
            name: my-skill
            type: action
        """)
        _write(tmp_path, "SKILL.md", """\
            # My Skill

            Handles edge-case processing.
        """)
        meta = auto_detect_and_convert(str(tmp_path), "my-skill")
        assert meta is not None
        assert "edge-case" in meta.description

    def test_no_skill_md_returns_metadata_as_is(self, tmp_path):
        """SKILL.md가 없으면 meta.yaml 결과를 그대로 반환한다."""
        _write(tmp_path, "meta.yaml", """\
            name: my-skill
            type: action
        """)
        meta = auto_detect_and_convert(str(tmp_path), "my-skill")
        assert meta is not None
        assert meta.description == ""

    def test_skill_md_frontmatter_when_to_use_takes_priority_over_body(self, tmp_path):
        """SKILL.md frontmatter의 when_to_use가 body 텍스트보다 우선한다."""
        _write(tmp_path, "meta.yaml", """\
            name: my-skill
            type: action
        """)
        _write(tmp_path, "SKILL.md", """\
            ---
            when_to_use: Specific frontmatter value
            ---

            Generic body text that should not win.
        """)
        meta = auto_detect_and_convert(str(tmp_path), "my-skill")
        assert meta is not None
        assert meta.when_to_use == "Specific frontmatter value"
        assert "Generic body text" not in meta.when_to_use
