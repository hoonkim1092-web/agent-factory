from __future__ import annotations

from pathlib import Path


def test_param_panel_slider_contract(frontend_root: Path) -> None:
    source = (frontend_root / "js/components/ParamPanel.js").read_text(encoding="utf-8")
    index_html = (frontend_root / "index.html").read_text(encoding="utf-8")
    sliders_css = (frontend_root / "styles/sliders.css").read_text(encoding="utf-8")

    assert '{ name: "n", min: 1, max: 10, step: 1, label: "추천 조합 수", unit: "개" }' in source
    assert '{ name: "draws", min: 100, max: 500, step: 50, label: "분석 회차", unit: "회" }' in source
    assert 'form.addEventListener("input", handleInput);' in source
    assert 'form.addEventListener("change", handleInput);' in source
    assert 'store.setState({ params: { [spec.name]: value } });' in source
    assert 'const loading = state?.status === "loading";' in source
    assert 'input.setAttribute("aria-valuetext", valueText);' in source
    assert 'output.textContent = valueText;' in source
    assert 'input.disabled = loading;' in source

    assert '<link rel="stylesheet" href="./styles/sliders.css" />' in index_html
    assert ".param-panel__slider::-webkit-slider-runnable-track" in sliders_css
    assert ".param-panel__slider::-moz-range-track" in sliders_css
    assert "prefers-reduced-motion: reduce" in sliders_css
