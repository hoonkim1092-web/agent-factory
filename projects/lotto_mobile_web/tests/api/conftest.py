import asyncio
import importlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response


def _load_dotted_path(dotted_path: str) -> Any:
    module_name, attribute_name = dotted_path.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attribute_name)


def _resolve_app_target() -> str:
    configured = os.getenv("QA_API_APP_TARGET")
    if configured:
        return configured

    candidates = (
        "app.main:app",
        "main:app",
        "src.main:app",
        "backend.main:app",
        "backend.app:app",
    )
    for candidate in candidates:
        try:
            _load_dotted_path(candidate)
            return candidate
        except (ImportError, AttributeError, ValueError):
            continue

    pytest.skip(
        "QA_API_APP_TARGET이 설정되지 않았고 기본 앱 import 경로도 찾지 못했습니다."
    )


@dataclass
class PredictorStub:
    combos: list[dict[str, Any]]
    source: str = "offline"

    def predict(self, n: int, draws: int, offline: bool = False) -> dict[str, Any]:
        return {
            "generated_at": "2026-04-18T00:00:00Z",
            "source": "offline" if offline else self.source,
            "draws_used": draws,
            "combos": self.combos[:n],
        }


class ApiTestClient:
    def __init__(self, app: Any):
        self._app = app

    def get(self, path: str, params: dict[str, Any] | None = None) -> Response:
        async def _request() -> Response:
            transport = ASGITransport(app=self._app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.get(path, params=params)

        return asyncio.run(_request())


def _install_predictor_override(
    monkeypatch: pytest.MonkeyPatch, predictor_stub: PredictorStub
) -> Callable[[], None]:
    override_target = os.getenv("QA_API_PREDICTOR_TARGET")
    if not override_target:
        return lambda: None

    target = _load_dotted_path(override_target)

    if callable(target):
        module = importlib.import_module(target.__module__)
        monkeypatch.setattr(
            module,
            target.__name__,
            lambda: predictor_stub,
        )
        return lambda: None

    module_name, attribute_name = override_target.split(":", 1)
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, attribute_name, predictor_stub)
    return lambda: None


@pytest.fixture
def predictor_stub() -> PredictorStub:
    return PredictorStub(
        combos=[
            {
                "numbers": [3, 11, 18, 27, 35, 44],
                "score": 0.91,
                "odd_even_ratio": "3:3",
                "section_distribution": [2, 1, 1, 1, 1],
            },
            {
                "numbers": [1, 9, 14, 28, 33, 42],
                "score": 0.87,
                "odd_even_ratio": "2:4",
                "section_distribution": [2, 1, 0, 2, 1],
            },
            {
                "numbers": [5, 8, 19, 23, 38, 41],
                "score": 0.83,
                "odd_even_ratio": "4:2",
                "section_distribution": [2, 0, 2, 1, 1],
            },
        ]
    )


@pytest.fixture
def valid_query() -> dict[str, Any]:
    return {"n": 3, "draws": 200, "offline": "false"}


@pytest.fixture
def app_client(
    monkeypatch: pytest.MonkeyPatch, predictor_stub: PredictorStub
) -> ApiTestClient:
    app_target = _resolve_app_target()
    app = _load_dotted_path(app_target)

    if hasattr(app, "dependency_overrides"):
        dependency_target = os.getenv("QA_API_PREDICTOR_DEPENDENCY")
        if dependency_target:
            dependency = _load_dotted_path(dependency_target)
            app.dependency_overrides[dependency] = lambda: predictor_stub

    if hasattr(app, "state"):
        setattr(app.state, "predictor_stub", predictor_stub)

    _install_predictor_override(monkeypatch, predictor_stub)
    return ApiTestClient(app)
