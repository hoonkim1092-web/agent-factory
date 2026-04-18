from __future__ import annotations

from pathlib import Path


def test_frontend_smoke_assets_exist(frontend_root: Path, render_contract: dict[str, object]) -> None:
    missing = [
        asset for asset in render_contract["assets"] if not (frontend_root / asset).exists()
    ]
    assert not missing, f"프론트엔드 smoke 대상 산출물이 누락되었습니다: {missing}"


def test_index_html_declares_mobile_shell_contract(
    index_html: str,
    parsed_index,
    render_contract: dict[str, object],
) -> None:
    viewport_content = None
    stylesheet_hrefs: set[str] = set()
    script_sources: set[str] = set()

    for tag, attrs in parsed_index.tags:
        if tag == "meta" and attrs.get("name") == "viewport":
            viewport_content = attrs.get("content", "")
        if tag == "link" and attrs.get("rel") == "stylesheet":
            stylesheet_hrefs.add(attrs.get("href", ""))
        if tag == "script" and attrs.get("type") == "module":
            script_sources.add(attrs.get("src", ""))

    assert "<title>로또 6/45 번호 추천</title>" in index_html
    assert viewport_content and "width=device-width" in viewport_content
    assert "./styles/base.css" in stylesheet_hrefs
    assert "./styles/layout.css" in stylesheet_hrefs
    assert "./js/app.js" in script_sources

    for selector in render_contract["selectors"].values():
        assert selector in index_html, f"필수 DOM 슬롯이 누락되었습니다: {selector}"

    for slot in render_contract["slots"]:
        assert slot in index_html, f"필수 data-slot이 누락되었습니다: {slot}"


def test_javascript_modules_export_required_symbols(
    render_contract: dict[str, object],
    module_exports,
) -> None:
    for relative_path, expected_exports in render_contract["required_exports"].items():
        exported = module_exports(relative_path)
        missing = sorted(set(expected_exports) - exported)
        assert not missing, f"{relative_path} export 누락: {missing}"


def test_representative_render_state_contract(
    index_html: str,
    recommendation_stub: dict[str, object],
) -> None:
    assert "추천받기" in index_html
    assert "추천 결과가 없습니다." in (
        Path(__file__).resolve().parents[2] / "web/js/components/CardList.js"
    ).read_text(encoding="utf-8")
    assert "현재 네트워크가 불안정해 마지막 저장 결과를 보여주는 중입니다." in (
        Path(__file__).resolve().parents[2] / "web/js/components/OfflineBanner.js"
    ).read_text(encoding="utf-8")

    combos = recommendation_stub.get("combos")
    assert isinstance(combos, list) and combos, "추천 성공 fixture에 최소 1개 이상의 조합이 필요합니다."
    first_combo = combos[0]
    assert isinstance(first_combo.get("numbers"), list) and len(first_combo["numbers"]) == 6
    assert "odd_even_ratio" in first_combo
    assert "section_distribution" in first_combo
