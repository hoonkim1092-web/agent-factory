"""공통 에러 응답 및 예외 → HTTP 매핑.

모든 에러 응답은 `{"error": {"code", "message", "details"}}` 포맷을 따른다.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """API 계층에서 발생시키는 도메인 에러."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class DataUnavailableError(ApiError):
    """온라인/오프라인 모두 회차 데이터를 확보하지 못했을 때."""

    def __init__(self, message: str = "회차 데이터가 없습니다.") -> None:
        super().__init__(
            code="data_unavailable",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def _envelope(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return {"error": body}


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_envelope(
            code="invalid_parameter",
            message="질의 파라미터가 유효하지 않습니다.",
            details={"errors": exc.errors()},
        ),
    )


async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(exc.code, exc.message, exc.details or None),
    )


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code = "http_error"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "not_found"
    elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        code = "invalid_parameter"
    message = exc.detail if isinstance(exc.detail, str) else "요청 처리 중 오류가 발생했습니다."
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(code, message),
    )


async def _unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_envelope(
            code="internal_error",
            message="내부 서버 오류가 발생했습니다.",
        ),
    )


def install_error_handlers(app: FastAPI) -> None:
    """FastAPI 앱에 공통 에러 핸들러를 등록한다."""
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unexpected_exception_handler)
