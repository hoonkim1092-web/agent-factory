"""Regression tests for scripts.blueprint_updater."""
from __future__ import annotations

from pathlib import Path

from scripts import blueprint_updater as bu


def _minimal_blueprint() -> str:
    return """# Master Blueprint

## §3 핵심 서브시스템

### §3.1 Existing

Existing prose.

---

## §4 Other

---

## §12 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
"""


def test_update_blueprint_writes_section3_auto_summary(tmp_path, monkeypatch):
    workspace = tmp_path
    core_dir = workspace / "core"
    core_dir.mkdir()
    (core_dir / "example.py").write_text(
        '"""Example subsystem contract."""\n\n'
        "class ExampleState:\n"
        "    pass\n\n"
        "def run_example():\n"
        "    return True\n",
        encoding="utf-8",
    )
    blueprint = workspace / "Master_Blueprint.md"
    blueprint.write_text(_minimal_blueprint(), encoding="utf-8")

    monkeypatch.setattr(bu, "_changed_files", lambda _workspace: ["core/example.py"])
    monkeypatch.setattr(bu, "_short_commit", lambda _workspace: "abc1234")
    monkeypatch.setattr(bu, "_read_version", lambda _workspace: "v1.2.3")

    updated = bu.update_blueprint(str(workspace), "test update", no_llm=True)

    text = blueprint.read_text(encoding="utf-8")
    assert updated is True
    assert bu.SECTION3_AUTO_START in text
    assert "### §3.12 자동 Core 변경 요약" in text
    assert "`core/example.py`" in text
    assert "Example subsystem contract." in text
    assert "`ExampleState`" in text
    assert "`run_example()`" in text


# ── change-relative §3.12 symbol extraction (positional-cap regression) ──────


def test_changed_public_symbols_extracts_toplevel_added(monkeypatch):
    """diff '+' 라인에서 들여쓰기 없는 public def/class만 추출 (메서드·private 제외)."""
    fake_diff = (
        "diff --git a/core/utils.py b/core/utils.py\n"
        "--- a/core/utils.py\n"
        "+++ b/core/utils.py\n"
        "@@ -1,1 +1,9 @@\n"
        "+def root_mean_square(values):\n"
        "+    return 0.0\n"
        "+class NewThing:\n"
        "+    def method_inside(self):\n"
        "+        pass\n"
        "+def _private_helper():\n"
        "+    pass\n"
    )
    monkeypatch.setattr(bu, "_git", lambda *a, **k: fake_diff)

    classes, funcs = bu._changed_public_symbols("", "core/utils.py")

    assert "root_mean_square" in funcs
    assert "NewThing" in classes
    assert "method_inside" not in funcs  # 들여쓰기된 메서드 제외
    assert "_private_helper" not in funcs  # private 제외
    # head_diff·staged_diff 양쪽에 동일 fake_diff가 반환되어도 중복 없음 (not in 방어)
    assert funcs.count("root_mean_square") == 1
    assert classes.count("NewThing") == 1


def test_changed_public_symbols_attributes_body_only_via_hunk_context(monkeypatch):
    """본문만 수정돼도 @@ 헌크 컨텍스트의 enclosing top-level 함수를 귀속한다.

    (positional-cap 회귀의 두 번째 갈래: '+def' 없이 본문만 바뀐 깊은 함수.)
    """
    fake_diff = (
        "+++ b/core/utils.py\n"
        "@@ -421 +421,2 @@ def root_mean_square(values: list[int | float]) -> float:\n"
        "+    total = sum(x * x for x in values)\n"
        "+    return math.sqrt(total / len(values))\n"
    )
    monkeypatch.setattr(bu, "_git", lambda *a, **k: fake_diff)
    classes, funcs = bu._changed_public_symbols("", "core/utils.py")
    assert "root_mean_square" in funcs  # 본문만 수정해도 enclosing 함수 반영


def test_changed_public_symbols_empty_when_no_toplevel(monkeypatch):
    """top-level 심볼 신호가 전혀 없으면(모듈레벨·메서드 내부) 빈 리스트 → preview 폴백."""
    fake_diff = (
        "+++ b/core/utils.py\n"
        "@@ -10,2 +10,3 @@\n"  # enclosing 컨텍스트 없음
        "+    x = sum(values)\n"
        "+    return x\n"
    )
    monkeypatch.setattr(bu, "_git", lambda *a, **k: fake_diff)
    classes, funcs = bu._changed_public_symbols("", "core/utils.py")
    assert classes == []
    assert funcs == []


def test_section3_reflects_changed_symbol_regardless_of_position(tmp_path, monkeypatch):
    """positional 캡 회귀: 파일 뒤쪽에 추가된 신규 함수도 §3.12에 반영된다."""
    workspace = tmp_path
    core_dir = workspace / "core"
    core_dir.mkdir()
    # 앞에 함수 7개 + 마지막에 신규 함수 — 과거 코드는 앞 3개만 반영했음
    body = '"""Big module."""\n\n'
    body += "".join(f"def f{i}():\n    return {i}\n\n\n" for i in range(7))
    body += "def root_mean_square(values):\n    return 0.0\n"
    (core_dir / "utils.py").write_text(body, encoding="utf-8")
    blueprint = workspace / "Master_Blueprint.md"
    blueprint.write_text(_minimal_blueprint(), encoding="utf-8")

    monkeypatch.setattr(bu, "_changed_files", lambda _w: ["core/utils.py"])
    monkeypatch.setattr(bu, "_short_commit", lambda _w: "abc1234")
    monkeypatch.setattr(bu, "_read_version", lambda _w: "v1.2.3")
    # change-relative 추출이 신규 함수만 짚도록 직접 주입 (git 비의존 단위 검증)
    monkeypatch.setattr(bu, "_changed_public_symbols", lambda _w, _p: ([], ["root_mean_square"]))

    updated = bu.update_blueprint(str(workspace), "add rms", no_llm=True)

    text = blueprint.read_text(encoding="utf-8")
    assert updated is True
    assert "`root_mean_square()`" in text  # 8번째 함수도 반영됨
