from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest


class IndexHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {key: value or "" for key, value in attrs}))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


@pytest.fixture(scope="session")
def frontend_root() -> Path:
    return Path(__file__).resolve().parents[2] / "web"


@pytest.fixture(scope="session")
def render_contract() -> dict[str, object]:
    return {
        "assets": [
            "index.html",
            "styles/base.css",
            "styles/layout.css",
            "js/app.js",
            "js/state.js",
            "js/api.js",
            "js/components/CardList.js",
            "js/components/ParamPanel.js",
            "js/components/OfflineBanner.js",
        ],
        "selectors": {
            "app_root": 'id="app"',
            "session_status": 'id="session-status"',
            "param_panel_root": 'id="param-panel-root"',
            "card_list_root": 'id="card-list-root"',
            "offline_banner_root": 'id="offline-banner-root"',
            "submit_button": 'id="submit-button"',
            "empty_hint": 'id="empty-hint"',
        },
        "slots": [
            'data-slot="param-panel"',
            'data-slot="card-list"',
            'data-slot="offline-banner"',
        ],
        "required_exports": {
            "js/state.js": ["createStore", "initialState"],
            "js/api.js": ["fetchRecommendation", "OfflineError"],
            "js/components/CardList.js": ["renderCardList"],
            "js/components/ParamPanel.js": ["renderParamPanel"],
            "js/components/OfflineBanner.js": ["renderOfflineBanner"],
        },
    }


@pytest.fixture(scope="session")
def index_html(frontend_root: Path) -> str:
    return (frontend_root / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def parsed_index(index_html: str) -> IndexHtmlParser:
    parser = IndexHtmlParser()
    parser.feed(index_html)
    return parser


@pytest.fixture(scope="session")
def recommendation_stub() -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "recommendation_success.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def module_exports(frontend_root: Path):
    def _module_exports(relative_path: str) -> set[str]:
        source = (frontend_root / relative_path).read_text(encoding="utf-8")
        matches = re.findall(
            r"export\s+(?:async\s+function|function|class|const|let|var)\s+([A-Za-z_$][\w$]*)",
            source,
        )
        return set(matches)

    return _module_exports
