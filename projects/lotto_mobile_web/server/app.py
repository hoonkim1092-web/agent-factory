"""FastAPI 앱 팩토리 및 라우터 등록.

엔드포인트:
- `GET /api/health`
- `GET /api/recommend`
- `GET /api/draws/latest`
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .bootstrap import ensure_predictor_importable
from .dependencies import get_draw_cache_service, get_recommendation_service
from .errors import DataUnavailableError, install_error_handlers
from .schemas import (
    DRAWS_MAX,
    DRAWS_MIN,
    N_MAX,
    N_MIN,
    DrawCacheEntry,
    HealthResponse,
    RecommendationQuery,
)
from .services.draw_cache import DrawCacheService
from .services.recommendation import RecommendationService

logger = logging.getLogger("lotto_mobile_web.server")

APP_VERSION = "0.1.0"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """요청마다 `X-Request-ID`를 발급/전달해 로그 상관관계를 확보한다."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        logger.info(
            "요청 수신: id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("LOTTO_CORS_ORIGINS", "*")
    if raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _resolve_static_dir() -> Path | None:
    configured = os.getenv("LOTTO_STATIC_DIR")
    if configured:
        path = Path(configured).expanduser().resolve()
        return path if path.is_dir() else None
    default = Path(__file__).resolve().parent.parent / "web"
    return default if default.is_dir() else None


def create_app() -> FastAPI:
    """FastAPI 앱을 구성해 반환한다."""
    ensure_predictor_importable()

    app = FastAPI(
        title="로또 추천 REST API",
        version=APP_VERSION,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(),
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=APP_VERSION,
            time=datetime.now(timezone.utc),
        )

    @app.get("/api/recommend")
    def recommend(
        query: RecommendationQuery = Depends(),
        service: RecommendationService = Depends(get_recommendation_service),
    ) -> JSONResponse:
        payload = service.predict(n=query.n, draws=query.draws, offline=query.offline)
        return JSONResponse(status_code=200, content=_jsonify(payload))

    @app.get("/api/draws/latest", response_model=DrawCacheEntry)
    def latest_draw(
        service: DrawCacheService = Depends(get_draw_cache_service),
    ) -> DrawCacheEntry:
        latest = service.get_latest()
        if latest is None:
            raise DataUnavailableError("캐시된 회차가 없습니다.")
        return DrawCacheEntry(
            round=latest["round"],
            numbers=latest["numbers"],
            bonus=latest.get("bonus"),
            fetched_at=latest["fetched_at"],
        )

    static_dir = _resolve_static_dir()
    if static_dir is not None:
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    logger.info(
        "FastAPI 앱 초기화 완료: version=%s params n=[%d,%d] draws=[%d,%d]",
        APP_VERSION,
        N_MIN,
        N_MAX,
        DRAWS_MIN,
        DRAWS_MAX,
    )
    return app


def _jsonify(payload: Any) -> Any:
    """JSONResponse 직전에 datetime 등 비직렬화 타입을 문자열화한다."""
    if isinstance(payload, dict):
        return {key: _jsonify(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_jsonify(item) for item in payload]
    if isinstance(payload, tuple):
        return [_jsonify(item) for item in payload]
    if isinstance(payload, datetime):
        value = payload if payload.tzinfo else payload.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    return payload


app = create_app()
